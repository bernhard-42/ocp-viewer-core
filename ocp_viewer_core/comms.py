"""The transport a host implements, and the session over it.

`Comms` is the whole of what a host must provide: five ways to send, one to
listen, and a test for its own viewer handle. `Session` is the shared half -
it caches the two reads a show makes and scopes both those answers and the
call's keywords to one call.
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

import enum
import os
from typing import Any, Generic, TypeVar

from .keys import to_javascript


class MessageType(enum.IntEnum):
    """What a message on the wire is.

    The protocol itself, so it belongs with the transport contract rather than
    with any one implementation of it. Every host encodes these numbers the same
    way; what differs is the socket underneath.
    """

    DATA = 1
    COMMAND = 2
    UPDATES = 3
    LISTEN = 4
    BACKEND = 5
    BACKEND_RESPONSE = 6
    CONFIG = 7

# What a host's transport hands back when a model is sent. Jupyter CadQuery
# returns its widget, so its users can go on to call methods on it; ocp_vscode
# and the standalone have nothing to hand back and return None. Carrying it as a
# type parameter is what lets one `show` give each host's users the right return
# type - and their editor the right completion on it - from one signature.
H = TypeVar("H")


class Comms(Generic[H]):
    """The transport a host implements.

    Everything above this line is host-neutral; everything below it is the
    host's business - a websocket, a comm channel, a socket of our own. The
    vocabulary is fixed, which is what makes the layer above swappable.
    """

    def __init__(self):
        # The keywords of the call in flight. A host reads the ones it owns
        # out of this inside its own send methods - `port` for the hosts that
        # address a viewer by one, `title` for those that name a sidecar.
        self.keywords: dict = {}

    # Each raises rather than having a docstring for a body. A body of only a
    # docstring types as returning None, which contradicts `send_data`'s promise
    # of a handle and spreads: `Session.workspace_config()` would be typed None,
    # `get_defaults()` would call `dict(None)`. It is also the right runtime
    # behaviour - a host that omits one should fail rather than silently send
    # nothing.

    def send_data(self, data: Any, timeit: bool = False) -> H:
        """Send a model to the viewer, and return the host's handle for it."""
        raise NotImplementedError

    def send_config(self, config: Any, timeit: bool = False) -> None:
        """Send config to the viewer"""
        raise NotImplementedError

    def send_command(self, data: Any, timeit: bool = False) -> Any:
        """Send a command to the viewer and return its answer."""
        raise NotImplementedError

    def send_backend(self, data: Any, timeit: bool = False) -> None:
        """Send data to the measurement backend"""
        raise NotImplementedError

    def send_response(self, data: Any, timeit: bool = False) -> None:
        """Answer a request from the viewer"""
        raise NotImplementedError

    def listen(self, callback) -> None:
        """Take messages from the viewer until it stops, calling back for each.

        The other direction, and the one only the measurement backend needs: it
        is a process of its own that waits to be asked. `callback(payload,
        message_type)` per message, and the call does not return until the
        viewer says stop.

        A host with no such channel need not override this - Jupyter CadQuery
        answers in-process and never listens.
        """
        raise NotImplementedError

    def is_handle(self, obj: Any) -> bool:
        """Whether `obj` is this host's viewer handle.

        Used to keep a viewer out of what it is being asked to draw: `show_all`
        walks the user's namespace, and in a notebook that namespace contains
        the widget itself. ocp_vscode tests it by looking for a host's module
        name inside `str(obj.__class__)`, which is a host named in a string and
        cannot move into shared code. Asking the transport is the same question
        put to the one object that can answer it without naming anybody.

        Hosts with no handle need not override this.
        """
        return False

    # `begin` and `end` have a working default, like `is_handle` and unlike the
    # five above: every host gets the keywords whether or not it wants them.

    def begin(self, keywords: Any) -> None:
        """Take the keywords of the call about to be made.

        The show family is the superset of every host's parameters, and each
        host acts on its own and ignores the rest - `Config.validate_keyword` is
        the half of that rule which refuses a keyword this host cannot act on,
        and this is the half that delivers one it can. What a keyword means is
        the host's business; the core only says which call it belongs to.

        It has to be a scope rather than an argument because the reads come
        first: `_tessellate` asks for `status` and `workspace_config` before any
        model is sent, so a `port` carried only in the model's config block
        would reach the transport two round trips too late, and

            show(obj, port=3939)
            show(obj, port=3940)

        would read the second model's camera and tree state from the first
        viewer. Binding `show = viewer.show` fixes one Comms per Viewer for its
        whole life, so the port cannot be a constructor argument either.
        """
        self.keywords = dict(keywords) if keywords else {}

    def end(self) -> None:
        """Forget the keywords, at the end of the call that set them."""
        self.keywords = {}


class Session(Generic[H]):
    """One show's worth of conversation with the viewer.

    Both reads are cached, and the cache is why the session is short-lived: a
    host builds one per `show`. Holding a Session across shows would replay the
    first answer for ever - and `_splash` is the case that proves it matters,
    since it is true only while the logo is up and false from the first real
    model on. A cache that outlived the show would keep forcing a camera reset
    and quietly discard every explicit `reset_camera=`.
    """

    def __init__(self, comms: Comms[H]):
        self.comms = comms
        self._status = None
        self._workspace_config = None

    def begin(self, keywords: Any) -> None:
        """Open a call's scope: the transport hears this call's keywords.

        Paired with `clear`, and for the same reason - the keywords and the
        cached answers have exactly one lifetime between them, which is one
        call. Routed through the Session rather than reaching into `comms`
        from `show`, so that a host overriding `Comms.begin` sees every call
        the core makes and not only the ones show happens to know about.
        """
        self.comms.begin(keywords)

    def status(self) -> Any:
        if self._status is None:
            self._status = self.comms.send_command("status")
        return self._status

    def workspace_config(self) -> Any:
        if self._workspace_config is None:
            self._workspace_config = self.comms.send_command("config")
        return self._workspace_config

    def clear(self) -> None:
        """Forget this show's cached reads.

        Called at the end of every show. The cache exists to stop one show
        opening the same connection six times, and must not outlive it: the
        answers change between shows. `_splash` is the case that proves it - it
        is true only while the logo is on screen, and an answer held past that
        forces a camera reset and discards every explicit `reset_camera=`.

        A host binds `show = viewer.show` once, so the Session lives as long as
        the Viewer; only its answers are short-lived, and clearing them is what
        makes that safe.

        The call's keywords end here too, having the same lifetime.
        """
        self._status = None
        self._workspace_config = None
        self.comms.end()

    def send_data(self, data: Any, timeit: bool = False) -> H:
        """Send a model, translating its config block on the way out.

        Here rather than in `Comms`, because `Comms` is what a host overrides -
        a conversion on the base class would be skipped by every host that
        implements the method, which is all of them. `Session` is the last
        shared code before the host's transport, so it is where "the sender
        translates to the receiver's paradigm" can actually be enforced.

        Only the config block is renamed. The rest of the envelope is geometry
        with its own keys, and walking it would be both wrong and expensive.
        """
        if isinstance(data, dict) and isinstance(data.get("config"), dict):
            data = {**data, "config": to_javascript(data["config"])}
        return self.comms.send_data(data, timeit=timeit)

    def set_viewer(self, config: Any) -> None:
        data = {
            "type": "ui",
            "config": to_javascript(config),
        }

        try:
            self.comms.send_config(data)

        except Exception as ex:
            raise RuntimeError(
                "Cannot set viewer config. Is the viewer running?\n" + str(ex.args)
            ) from ex


def is_pytest():
    """Whether to answer from canned data instead of asking a viewer.

    Opt-in, and it must stay opt-in. A variable pytest sets itself - such as
    `PYTEST_CURRENT_TEST` - would turn the stub on for every test in a suite
    with no way to turn it off, including the ones that spawn a real viewer and
    ask it real questions; those would receive canned data and fail on the
    first key they looked for.
    """
    return os.environ.get("OCP_VIEWER_PYTEST") == "1"
