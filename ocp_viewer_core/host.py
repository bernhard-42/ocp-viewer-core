"""Which host `from ocp_viewer_core import show` means.

Four packages export the same show family, each bound to its own transport.
A script that names one of them has chosen; a script that imports from the
core instead leaves the choice to this module, by three rules:

1. `OCP_VIEWER_HOST` names one - no question asked. A host that owns its
   kernel sets it (build123d Studio does, in `kernel_environment()`), and so
   can a user or a CI script. It comes first because two of the four hosts
   have no terminal to ask on.
2. Exactly one host is installed - it is meant. Decided with `find_spec`,
   which reads metadata and executes nothing.
3. Several are installed - ask, on whatever channel exists: `input()` in a
   ZMQ kernel (questionary does not survive one), questionary on a real
   terminal, and a loud refusal naming `OCP_VIEWER_HOST` anywhere else.
   Never "first found": a silently chosen host is the bug class the
   core/host split was shaped to make unrepresentable, and asking - or
   being told - is what keeps this feature on the right side of that line.

The choice is made once per process and cached. Every resolved name is then
the chosen host's own bound method, so `show` and `set_defaults` share that
host's one Viewer/Config chain by construction.

The host tuple is hard-coded deliberately - his ruling, 2026-08-17: there
are no third-party hosts and the set is closed, so a plain tuple beats
entry-point indirection. A fifth host means editing it, which is accepted.

No core submodule may import this one. It sits above the whole stack, used
only by `__init__.py` - if `show.py` ever imports it, the layer has leaked
and the import graph says so.
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

import importlib
import importlib.util
import os
import sys

HOSTS = ("ocp_vscode", "ocp_viewer", "jupyter_cadquery", "build123d_studio")

ENV_VAR = "OCP_VIEWER_HOST"

# The chosen host module, once per process. None means "not chosen yet" -
# choosing is triggered by the first name that needs it, never by
# `import ocp_viewer_core` alone.
_chosen = None


def installed_hosts():
    """The host packages present in this environment, without importing any.

    `find_spec` is the whole point: it answers from metadata, so discovery
    has no side effects and no cost until a host is actually chosen.
    """
    return [name for name in HOSTS if importlib.util.find_spec(name) is not None]


def resolve(installed, named):
    """The host that is meant, or None when only asking can settle it.

    Pure - the installed list and the environment variable's value come in as
    arguments - so the whole decision matrix is testable with no packages and
    no prompt. Raises rather than guesses: every error case is an ImportError
    that says what to do, and "several, nobody said" is the one outcome the
    caller must take to `ask`.
    """
    if named is not None:
        if named not in HOSTS:
            raise ImportError(
                f"{ENV_VAR}={named!r} is not a viewer host; "
                f"one of {', '.join(HOSTS)} was expected"
            )
        if named not in installed:
            raise ImportError(
                f"{ENV_VAR}={named!r}, but that host is not installed "
                f"in this environment"
            )
        return named

    if len(installed) == 0:
        raise ImportError(
            "No viewer host is installed. Install one of "
            f"{', '.join(HOSTS)} to import the show family from ocp_viewer_core."
        )
    if len(installed) == 1:
        return installed[0]
    return None


def _ipython():
    """The running IPython shell, if there is one, without importing IPython."""
    module = sys.modules.get("IPython")
    if module is None:
        return None
    return module.get_ipython()


def ask(installed):
    """Ask which host is meant, on whatever channel exists - or refuse.

    Mirrors `WebSocketComms.choose_port`: ZMQ kernels get `input()` because
    questionary does not survive them, a real terminal gets questionary, and
    an environment with neither gets a refusal that says exactly what to set.
    """
    shell = _ipython()
    if shell is not None and shell.__class__.__name__ == "ZMQInteractiveShell":
        answer = input(f"Select the viewer host to use, one of {installed}: ")
        if answer not in installed:
            raise ImportError(f"{answer!r} is not one of the installed hosts {installed}")
        return answer

    if sys.stdin.isatty() and sys.stdout.isatty():
        # Lazy by his explicit carve-out for this feature, and only on the
        # one path that is interactive anyway.
        import questionary

        answer = questionary.select(
            "Several viewer hosts are installed. Which one is meant?",
            choices=list(installed),
        ).ask()
        if answer is None:
            raise ImportError("No viewer host chosen")
        return answer

    raise ImportError(
        f"Several viewer hosts are installed ({', '.join(installed)}) and there "
        f"is no terminal to ask on. Set {ENV_VAR} to the one that is meant."
    )


def chosen():
    """The chosen host module, importing it on first need and never again."""
    global _chosen
    if _chosen is None:
        installed = installed_hosts()
        name = resolve(installed, os.environ.get(ENV_VAR))
        if name is None:
            name = ask(installed)
        _chosen = importlib.import_module(name)
        # His wording. After the import, so the line is only ever true.
        print(f"Using viewer {name}")
    return _chosen
