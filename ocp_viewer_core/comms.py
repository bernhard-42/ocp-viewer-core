import os
from typing import Any, Generic, TypeVar

from .keys import to_javascript

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

    def __init__(self): ...

    # Each raises rather than returning None. A body of just a docstring types
    # as returning None, which is both a lie - send_data promises a handle - and
    # infectious: Session.workspace_config() would return None, get_defaults()
    # would call dict(None), and everything downstream of that inherits a
    # nonsense type. It is also the honest runtime behaviour: a host that
    # forgets one of these should fail loudly, not send nothing and return None.

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

        Called at the end of every show, so the next one asks again. The cache
        exists to stop one show opening the same connection six times; it must
        not survive into the next show, because the answers change between them
        - `_splash` is true only while the logo is up, and a cache that outlived
        the show would keep forcing a camera reset and quietly discard every
        explicit `reset_camera=`.

        Clearing rather than rebuilding the Session matters now that a host
        binds `show = viewer.show` once: the objects stay put for the life of
        the Viewer and only the answers are short-lived.
        """
        self._status = None
        self._workspace_config = None

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
    return "PYTEST_CURRENT_TEST" in os.environ
