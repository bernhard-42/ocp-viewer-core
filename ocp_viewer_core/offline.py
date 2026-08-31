"""Tessellation without a viewer - for tests and fixture generation.

Private on purpose: nothing in the package's `__init__` or any host imports
this module. It exists so a test or fixture script can run the `_convert`
pipeline with no host package installed, no viewer running and no connection
warning.

This module may import the websocket transport (for `NO_VIEWER_CONFIG`)
precisely because it is opt-in; `show.py` stays transport-neutral.
"""

from .comms import Comms, Session
from .config import Config
from .show import Viewer
from .websocket import NO_VIEWER_CONFIG


class _OfflineComms(Comms[None]):
    """The transport behind `_convert`: there is none.

    Status and workspace config answer exactly what the websocket client
    answers when no viewer is listening, so offline output matches what a
    host produces with its viewer down. Every sender keeps the base class's
    `NotImplementedError` - nothing on the `_convert` path sends.
    """

    def status(self):
        return {}

    def workspace_config(self):
        return dict(NO_VIEWER_CONFIG)


def _convert(*cad_objs, **kwargs):
    """Tessellate CAD objects without any viewer.

    Behaves like `viewer._convert` in a host whose viewer is not running.
    Returns `(data, mapping)`: with OCP_VIEWER_PYTEST unset or "0" the data
    is the buffer-JSON envelope a viewer would receive; with "1" it is the
    raw `(instances, shapes, config, count_shapes)` tuple, arrays untouched.
    """
    return Viewer(Config(Session(_OfflineComms()), ()))._convert(*cad_objs, **kwargs)
