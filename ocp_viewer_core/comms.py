"""The transport a host implements, and the session over it.

`Comms` is what the shared show pipeline needs from a host: four ways to send,
a name translation, a test for its own viewer handle, and the scope that
carries a call's keywords. `Session` is the shared half - it caches the two
reads a show makes and scopes both those answers and the call's keywords to one
call.

It is a *client* transport, and only that. The measurement backend has none:
it is always called by something that already holds a channel, so it answers by
returning and its caller does the sending. See `ViewerBackend`.
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

from ._version import __version__
from .keys import to_javascript

__all__ = ["Comms", "H", "MessageType", "Session", "is_pytest"]


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

    Every method here exists because the *core* has to initiate something: a
    show sends a model, a config or a command; a session asks the viewer two
    questions. Where the core is instead answering someone who reached in -
    which is the whole of the measurement backend - no method is needed, and
    there is none.
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
        """Send a command to the viewer and return its answer.

        Commands are things done to a viewer - take a screenshot, set the
        animation time. The two questions a session asks are `status` and
        `workspace_config` below: they were once command strings, which left
        "a host must be able to answer these two" as a convention with no
        signature behind it, and every host dispatching on the string itself.
        """
        raise NotImplementedError

    def status(self) -> Any:
        """The viewer's live state - what the user has changed at the toolbar.

        The half of a show's picture that only the running viewer knows. A host
        with no viewer up answers with an empty dict rather than raising: no
        viewer means nothing has been changed in one, which is what an empty
        answer says.
        """
        raise NotImplementedError

    def workspace_config(self) -> Any:
        """The settings this host persists between sessions.

        The other half, and the host's own: a settings dialog, a VS Code
        settings section, a config file. Neither this nor `status` is knowable
        from Python - `get_defaults` covers what `set_defaults` was told and a
        show's keywords are in hand, but the stored settings and the toolbar are
        outside the process - which is why the core asks rather than keeps them.
        """
        raise NotImplementedError

    def send_backend(self, data: Any, timeit: bool = False) -> None:
        """Send data to the measurement backend"""
        raise NotImplementedError

    def encode_config(self, config: Any) -> Any:
        """Put a config block into the names this host's viewer reads.

        The sender translates to the receiver's paradigm, and for most hosts
        the receiver is three-cad-viewer reached over a wire, which speaks
        camelCase - so the default renames. A host whose two halves share one
        name, as an ipywidgets traitlet does, receives what Python sent and
        overrides this with the identity.

        On `Comms` rather than applied by the caller, because only the host
        knows what is at the other end.
        """
        return to_javascript(config)

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
        # Whether a show is in flight. The cache exists to stop one show asking
        # the same question six times; outside a show there is no such run of
        # questions, and answering from it is answering with the past.
        self._in_show = False

    def begin(self, keywords: Any) -> None:
        """Open a call's scope: the transport hears this call's keywords.

        Paired with `clear`, and for the same reason - the keywords and the
        cached answers have exactly one lifetime between them, which is one
        call. Routed through the Session rather than reaching into `comms`
        from `show`, so that a host overriding `Comms.begin` sees every call
        the core makes and not only the ones show happens to know about.

        The scope opens *empty*, which `clear` alone did not guarantee. A read
        made outside a show - `status()` and `workspace_config()` are exported
        by every host - filled the cache, and nothing emptied it until the end
        of the next show, so that show answered out of an older reading instead
        of asking. Measured: a show sent two commands from a fresh process and
        one after a direct `status()` call. `_splash` is the sharp end, since a
        cached `True` from while the logo was up forces a camera reset and
        discards an explicit `reset_camera=`.
        """
        self._status = None
        self._workspace_config = None
        self._in_show = True
        self.comms.begin(keywords)

    def status(self) -> Any:
        """The viewer's live state, asked once per show and freshly otherwise.

        **Cached only while a show is in flight.** A user calling `status()` at
        the prompt is asking what the viewer looks like *now*: they toggle
        something in the viewer and ask again, and an answer from the cache is
        the state before they touched it. That cache was emptied only at the end
        of the next show, so it could be arbitrarily old - reported as "status()
        only reports stale values, independent of what I set in the viewer UI".
        """
        if not self._in_show:
            return self.comms.status()
        if self._status is None:
            self._status = self.comms.status()
        return self._status

    def workspace_config(self) -> Any:
        """The host's stored settings, on the same terms as `status`.

        A settings dialog can be open while Python sits at a prompt, so the same
        argument applies: outside a show, ask.
        """
        if not self._in_show:
            return self.comms.workspace_config()
        if self._workspace_config is None:
            self._workspace_config = self.comms.workspace_config()
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
        self._in_show = False
        self.comms.end()

    def send_data(self, data: Any, timeit: bool = False) -> H:
        """Send a model, putting its config block into the host's names.

        Applied here rather than left to each host: `Session` is the last
        shared code before the transport, so this is where the rule holds for
        everyone. What the names should be is the host's answer, which is why
        the renaming itself is `Comms.encode_config`.

        Only the config block is renamed. The rest of the envelope is geometry
        with its own keys, and walking it would be both wrong and expensive.
        """
        if isinstance(data, dict) and isinstance(data.get("config"), dict):
            config = dict(self.comms.encode_config(data["config"]))
            # The version handshake: major.minor of the two halves is the
            # contract, the patch level is each half's own. Injected after the
            # encoding, so the key arrives spelled exactly like this and the
            # page can take it out again before applying the config.
            config["_core_version"] = __version__
            data = {**data, "config": config}
        return self.comms.send_data(data, timeit=timeit)

    def set_viewer(self, config: Any) -> None:
        data = {
            "type": "ui",
            "config": self.comms.encode_config(config),
        }

        # Sent, not guarded. The `except Exception` that was here re-raised
        # "Cannot set viewer config. Is the viewer running?" for anything at
        # all, and a viewer that is not running does not raise: the websocket
        # client catches its own connection errors, warns, and returns. What
        # this caught instead were bugs, wearing a message that sent the reader
        # to look at the viewer.
        self.comms.send_config(data)


def is_pytest():
    """Whether to answer from canned data instead of asking a viewer.

    Opt-in, and it must stay opt-in. A variable pytest sets itself - such as
    `PYTEST_CURRENT_TEST` - would turn the stub on for every test in a suite
    with no way to turn it off, including the ones that spawn a real viewer and
    ask it real questions; those would receive canned data and fail on the
    first key they looked for.
    """
    return os.environ.get("OCP_VIEWER_PYTEST") == "1"
