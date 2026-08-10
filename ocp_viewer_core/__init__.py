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

"""Shared viewer core.

**This module stays import-free on purpose.** Importing the package must not
pull in the tessellator, OCP, or anything else expensive: hosts import the
submodule they need. build123d Studio's sidecar is the reason - it deliberately
never loads OCP, and moving that import out of its path took listening-to-ready
from 2.63 s to 0.78 s on macOS and 6.52 s to 1.80 s on Windows.

So no `from .config import ...` here, and no re-exports. Import
`ocp_viewer_core.config`, `ocp_viewer_core.codec`, `ocp_viewer_core.comms`,
`ocp_viewer_core.tessellate` or `ocp_viewer_core.backend` directly.

Of those, `tessellate` and `backend` reach OCP; the others do not reach it
themselves, though `config` loads it transitively through `ocp_tessellate`'s
`Color`. Keeping the geometry-touching surface small and named is what keeps
the OCCT-version discipline confined to the modules that need it.
"""

from ._version import __version__

__all__ = ["__version__"]
