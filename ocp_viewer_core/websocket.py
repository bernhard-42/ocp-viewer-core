"""The websocket client every host that talks to a viewer over one uses.

ocp_vscode and ocp_viewer speak the same protocol to the same kind of server -
one opens a viewer in a panel and the other in a browser, and neither
difference reaches this far down. It was ocp_vscode's, and a second host
needing it is what said it was never one host's.

Not every host wants it: build123d Studio sends length-prefixed binary frames
over a local socket, and implements `Comms` directly. That is why `Comms` is
an interface and this is one implementation of it.

The port is instance state rather than a module global, so that two clients in
one process address two viewers. Hosts expose `set_port()` and `get_port()` as
wrappers over their own instance.
"""

#
# Copyright 2026 Bernhard Walter
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import base64
import enum
import json
import os
import socket
import sys
import traceback
import warnings

import orjson
from ocp_tessellate.ocp_utils import (
    is_toploc_location,
    is_topods_shape,
    loc_to_tq,
    serialize,
)
from ocp_tessellate.utils import Timer
from websockets.exceptions import WebSocketException
from websockets.sync.client import connect

from .comms import Comms, MessageType
from .config import Collapse
from .state import get_config_file, get_ports, update_state

DEFAULT_PORT = 3939
DEFAULT_HOST = "127.0.0.1"

# Whether a Jupyter kernel could be writing a connection file worth recording.
try:
    import jupyter_console  # noqa: F401

    JCONSOLE = True
except Exception:  # noqa: BLE001
    JCONSOLE = False

_WARNED = False


class CommsWarning(UserWarning):
    """A connection that did not work, said once."""


def comms_warning(message):
    """Warn about the transport, at most once per session.

    Once, because the failure mode is a viewer that is not running and every
    subsequent call would say the same thing - a wall of identical warnings
    tells a user less than one does.
    """
    global _WARNED
    if not _WARNED:
        # ty treats a module-level `def` as a binding rather than a variable,
        # so replacing one is an error however well the replacement matches.
        # The stdlib offers no other way to change how a warning is formatted.
        warnings.formatwarning = _one_line  # ty: ignore[invalid-assignment]
        warnings.warn(message, CommsWarning, stacklevel=2)
        _WARNED = True


def _one_line(
    message: Warning | str,
    category: type[Warning],
    filename: str,
    lineno: int,
    line: str | None = None,
) -> str:
    """One line per warning: the file and line number help nobody here."""
    return f"{category.__name__}: {message}\n"


def _ipython():
    """The running IPython shell, if there is one, without importing IPython.

    Asking `sys.modules` rather than importing: a host that is not in a
    notebook has no IPython to find, and making the core depend on it to
    discover that would be paying for the answer everywhere to use it in one
    place.
    """
    module = sys.modules.get("IPython")
    return module.get_ipython() if module is not None else None


def port_check(port, host=DEFAULT_HOST):
    """Check whether the port is listening.

    A module function rather than a method: discovery has to probe ports before
    there is a client pointed at any of them.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1)
    result = s.connect_ex((host, port)) == 0
    if result:
        s.close()
    return result


def default(obj):
    """Default JSON serializer."""
    if is_topods_shape(obj):
        # `serialize` is annotated as optionally returning None and does not
        # for a shape that exists; the annotation is ocp_tessellate's to fix.
        return base64.b64encode(serialize(obj)).decode("utf-8")  # ty: ignore[invalid-argument-type]
    elif is_toploc_location(obj):
        return loc_to_tq(obj)
    elif isinstance(obj, enum.Enum):
        return obj.value
    else:
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")


class WebSocketComms(Comms[None]):
    """A viewer at the other end of a websocket, addressed by port.

    `port=None` means "discover one", and the discovery is deliberately lazy:
    it reads a state file, probes what it finds and may ask the user which
    viewer they meant, none of which should happen because somebody imported a
    module.
    """

    def __init__(self, host: str = DEFAULT_HOST, port: int | None = None):
        super().__init__()
        self.host = host
        self._port = port
        self._resolved = port is not None

    @property
    def url(self):
        return f"ws://{self.host}"

    @property
    def port(self):
        """The port to talk to, discovering one on first use."""
        if not self._resolved:
            self.find_and_set_port()
            self.set_connection_file()
        return self._port

    def set_port(self, port, host: str = DEFAULT_HOST):
        """Pin this client to a viewer, skipping discovery."""
        self._port = port
        self.host = host
        self._resolved = True

    def choose_port(self, ports):
        """Ask which viewer, when more than one is listening.

        A hook, because the asking is the host's: in a kernel the answer comes
        from an input box the editor raises, and a host that raises one wants
        to say so. The mechanism below is what every host would write anyway.
        """
        if _ipython().__class__.__name__ == "ZMQInteractiveShell":
            return input(f"Select port from {[int(p) for p in ports]} ")

        import questionary

        return questionary.select(
            "Multiple viewers found. Select a port:",
            choices=[str(p) for p in ports],
        ).ask()

    def find_port(self):
        """The one live viewer, or the one the user picked, or None."""
        live = [p for p in get_ports() if port_check(int(p), self.host)]

        if not live:
            return None
        if len(live) == 1:
            return int(live[0])

        port = self.choose_port(live)
        return int(port) if port not in (None, "") else None

    def find_and_set_port(self):
        """Run the discovery: the environment, then the state file, then 3939."""
        try:
            port = int(os.environ.get("OCP_PORT", "0"))
        except ValueError:
            print(
                f"Port {os.environ.get('OCP_PORT')} taken from environment "
                "variable OCP_PORT is invalid"
            )
            port = 0

        if port > 0:
            print(
                f"Using predefined port {port} taken from environment variable OCP_PORT"
            )
        else:
            port = self.find_port()
            if port is not None:
                print(f"Using port {port}")
            elif port_check(DEFAULT_PORT, self.host):
                port = DEFAULT_PORT
                print(f"Default port {port} is open, using it")

        self.set_port(port, self.host)

    def _send(self, data, message_type, port=None, timeit=False):
        """Send one message, opening a connection for it and closing it after.

        A connection per message rather than one held open, which is the golden
        master's choice and worth keeping: the viewer may be restarted between two
        shows, and a socket held across that is a socket that has to be noticed as
        dead and rebuilt.
        """
        if port is None:
            port = self.port
        try:
            with Timer(timeit, "", "json dumps", 1):
                j = orjson.dumps(data, default=default)  # pylint: disable=no-member
                if message_type == MessageType.COMMAND:
                    j = b"C:" + j
                elif message_type == MessageType.DATA:
                    j = b"D:" + j
                elif message_type == MessageType.LISTEN:
                    j = b"L:" + j
                elif message_type == MessageType.BACKEND:
                    j = b"B:" + j
                elif message_type == MessageType.BACKEND_RESPONSE:
                    j = b"R:" + j
                elif message_type == MessageType.CONFIG:
                    j = b"S:" + j

            with Timer(timeit, "", f"websocket connect ({message_type.name})", 1):
                try:
                    with connect(f"{self.url}:{port}", close_timeout=0.05) as ws:
                        ws.send(j)

                        with Timer(
                            timeit, "", f"websocket send {len(j) / 1024 / 1024:.3f} MB", 1
                        ):
                            result = None
                            no_response_commands = ("screenshot", "set_relative_time")
                            if message_type == MessageType.COMMAND and not (
                                isinstance(data, dict)
                                and data.get("type") in no_response_commands
                            ):
                                try:
                                    result = json.loads(ws.recv())
                                except Exception as ex:  # pylint: disable=broad-except  # noqa: BLE001
                                    print(ex)
                            elif message_type == MessageType.COMMAND and (
                                isinstance(data, dict)
                                and data.get("type") in no_response_commands
                            ):
                                result = {}
                            elif message_type == MessageType.BACKEND:
                                ack = json.loads(ws.recv())
                                if not ack.get("ok"):
                                    print(
                                        "Warning: OCP CAD Viewer backend is not connected "
                                        "— measurements/properties unavailable",
                                        flush=True,
                                    )

                except (ConnectionRefusedError, OSError, WebSocketException) as ex:
                    comms_warning(f"Connection error: {ex}\nMessage: {data}")
                    # set some dummy values to avoid errors
                    return {
                        "collapse": Collapse.ROOT,
                        "_splash": False,
                        "default_facecolor": (238, 130, 238),
                        "default_thickedgecolor": (186, 85, 211),
                        "default_vertexcolor": (186, 85, 211),
                    }
                except Exception as ex:  # noqa: BLE001
                    comms_warning(f"Unexpected error: {ex}\n{traceback.format_exc()}")
                    # set some dummy values to avoid errors
                    return {
                        "collapse": Collapse.ROOT,
                        "_splash": False,
                        "default_facecolor": (238, 130, 238),
                        "default_thickedgecolor": (186, 85, 211),
                        "default_vertexcolor": (186, 85, 211),
                    }

            return result

        except Exception as ex:  # pylint: disable=broad-except  # noqa: BLE001
            print(
                f"Cannot connect to viewer on port {port}, is it running and the right port provided?"
            )
            print(ex)
            return None

    def listener(self, callback):
        """Drive a measurement backend from this viewer's notifications.

        `callback` is `ViewerBackend.handle_event`, which computes and returns
        rather than sending - so delivering its answer is this loop's job, and
        this loop is the thing that has a connection to deliver it on.

        Delivered with `_send`, which opens a connection of its own, rather than
        on the socket held open here. Both reach the same server and the same
        handler; using `_send` keeps this a pure move of the line that used to
        sit inside the backend.
        """

        def _listen():
            last_config = {}
            with connect(f"{self.url}:{self.port}", max_size=2**28) as websocket:
                websocket.send(b"L:Python listener")
                while True:
                    try:
                        message = websocket.recv()
                        if message is None:
                            continue

                        message = json.loads(message)
                        if "model" in message:
                            callback(message["model"], MessageType.DATA)

                        if message.get("command") == "status":
                            changes = message["text"]
                            new_changes = {}
                            for k, v in changes.items():
                                if k in last_config and last_config[k] == v:
                                    continue
                                new_changes[k] = v
                            last_config = changes
                            response = callback(new_changes, MessageType.UPDATES)
                            # None is the common case by far: every change set
                            # with no active tool, no selection, or a selection
                            # the active tool cannot use.
                            if response is not None:
                                self._send(response, MessageType.BACKEND_RESPONSE)

                        elif message.get("command") == "stop":
                            print("Stopping Python listener")
                            break
                    except Exception as ex:  # pylint: disable=broad-except  # noqa: BLE001
                        print(ex)
                        break

        return _listen

    def set_connection_file(self):
        """Set the connection file for Jupyter in the state file .ocpvscode"""
        if JCONSOLE and hasattr(_ipython(), "kernel"):
            kernel = _ipython().kernel
            cf = kernel.config["IPKernelApp"]["connection_file"]
            with open(cf, "r", encoding="utf-8") as f:
                connection_info = json.load(f)

            if port_check(connection_info["iopub_port"]):
                print("Jupyter kernel running")
                try:
                    _ = int(self.port)
                    update_state(str(self.port), cf)
                    print(f"Jupyter connection file path written to {get_config_file()}")
                except ValueError:
                    print(
                        f"Cannot set Jupyter connection file, port {self.port}' is non-numeric"
                    )
            else:
                print("Jupyter kernel not responding")

    # The four the contract asks for. Each is one line because the framing is
    # `_send`'s and the vocabulary is MessageType's.

    @property
    def call_port(self):
        """The port this call is addressed to, or None for the current one.

        `show(obj, port=3940)` puts it in the keyword scope, which is open for
        the whole of that show - so the reads it makes before the model is sent
        go to the same viewer the model does.
        """
        return self.keywords.get("port")

    def send_data(self, data, timeit: bool = False) -> None:
        self._send(data, MessageType.DATA, self.call_port, timeit)

    def send_config(self, config, timeit: bool = False) -> None:
        self._send(config, MessageType.CONFIG, self.call_port, timeit)

    def send_command(self, data, timeit: bool = False):
        return self._send(data, MessageType.COMMAND, self.call_port, timeit)

    def status(self):
        result = self._send("status", MessageType.COMMAND, self.call_port)
        # The answer arrives wrapped, because that is how the viewer's own
        # status message is shaped on the wire - the same frame it pushes
        # unprompted when the user changes something.
        if isinstance(result, dict) and result.get("command") == "status":
            return result["text"]
        return result

    def workspace_config(self):
        return self._send("config", MessageType.COMMAND, self.call_port)

    def send_backend(self, data, timeit: bool = False) -> None:
        self._send(data, MessageType.BACKEND, self.call_port, timeit)
