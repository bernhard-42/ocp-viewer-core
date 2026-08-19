"""Shared viewer logic for the OCP CAD viewers.

The show pipeline, the configuration semantics, the render and camera policy,
the measurement backend and the wire protocol, used by ocp_vscode, ocp_viewer,
Jupyter CadQuery and build123d Studio. Each host supplies a transport and its
own settings; everything above that is here.

This module imports nothing. A host imports the submodule it needs, so that
importing the package never loads the tessellator or OCP - `show`, `backend`
and `measure` reach the kernel, and `comms`, `config`, `keys`, `state` and
`websocket` do not.

It also carries the universal import: `from ocp_viewer_core import show`
works in every host's environment and resolves to the host that is meant -
`host.py` says how that is decided. The resolution is lazy (PEP 562), so the
paragraph above stays true: a bare import still loads nothing, a star import
resolves at the import statement, and a named import on first access. The
resolved names are the chosen host's own bound methods.
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

from ._version import __version__

# The shared vocabulary: the intersection of the hosts' public names,
# measured 2026-08-16. Everything here exists in every host, so a script
# using only these runs unchanged under any of them - which is what makes
# the star import safe to write.
__all__ = [
    "__version__",
    "combined_config",
    "get_default",
    "get_defaults",
    "push_object",
    "remove_object",
    "reset_defaults",
    "reset_show",
    "save_screenshot",
    "set_defaults",
    "set_viewer_config",
    "show",
    "show_all",
    "show_clear",
    "show_object",
    "show_objects",
    "status",
    "workspace_config",
]

# Names some hosts have and others honestly lack, because they are shaped by
# the transport: a port means nothing to a sidecar, a sidecar means nothing
# to a websocket. Importable by name from the chosen host; absent from
# `__all__` so a star import never carries a name that may not exist. Asked
# of a host that lacks them, the ImportError below names that host rather
# than letting the name silently not work.
#
# This tuple is also the explicit list of *accepted* feature asymmetries
# under the "all hosts behave the same" rule - anything host-specific that is
# not a transport shape does not belong here, it belongs fixed.
_HOST_ONLY = (
    # websocket hosts (ocp_vscode, ocp_viewer): which viewer a port addresses
    "get_port",
    "set_port",
    # jupyter_cadquery: the sidecar lifecycle its host process owns
    "close_viewer",
    "close_viewers",
    "get_default_viewer",
    "get_user_defaults",
    "get_viewer",
    "open_viewer",
    "save_user_defaults",
    "set_default_viewer",
)


def __getattr__(name):
    """PEP 562: called only for names this module does not really have.

    Restricted to the two published tuples. Delegating every unknown name
    would make any typo - or any `hasattr` probe by tooling - import a host
    and possibly prompt, which is a side effect no attribute miss should
    have. The import of `host` lives here and not at the top so that a bare
    `import ocp_viewer_core` keeps importing nothing.
    """
    if name in __all__ or name in _HOST_ONLY:
        from . import host

        viewer = host.chosen()
        try:
            value = getattr(viewer, name)
        except AttributeError:
            raise ImportError(
                f"{name!r} exists in some hosts but not in {viewer.__name__}"
            ) from None
        # Written back as a real attribute, and not only as a cache. `show` is
        # also a submodule of this package, and importing the chosen host - who
        # imports `ocp_viewer_core.show` like every host - makes the import
        # machinery set that submodule as this package's `show` attribute,
        # *during* this call. A real attribute wins over `__getattr__`, so
        # without this line the `from ocp_viewer_core import show` that
        # triggered the resolution would bind the submodule, not the host's
        # function: the import statement reads the attribute again after
        # `__getattr__` returns.
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    """Completion without side effects: listing names must not choose a host."""
    return sorted(set(globals().keys()) | set(__all__) | set(_HOST_ONLY))
