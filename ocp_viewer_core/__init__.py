"""Shared viewer logic for the OCP CAD viewers.

The show pipeline, the configuration semantics, the render and camera policy,
the measurement backend and the wire protocol, used by ocp_vscode, ocp_viewer,
Jupyter CadQuery and build123d Studio. Each host supplies a transport and its
own settings; everything above that is here.

This module imports nothing. A host imports the submodule it needs, so that
importing the package never loads the tessellator or OCP - `show`, `backend`
and `measure` reach the kernel, and `comms`, `config`, `keys`, `state` and
`websocket` do not.

Users never import from here: everything a user calls comes from their
viewer's own package (`from ocp_vscode import *`), and all four packages
offer the same show family because they all bind it from this one. A
universal import that resolved `from ocp_viewer_core import show` to "the
host that is meant" was built, shipped in 1.0.0 and deleted the same week -
its one benefit was a host-neutral import line in shared scripts, and it
cost a resolution machine whose edge cases (multi-host environments, star
imports, static tooling) each needed machinery of their own. The uniformity
of the hosts is what makes scripts portable; the import line names the
viewer, and that is documentation, not a defect.
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

__all__ = ["__version__"]
