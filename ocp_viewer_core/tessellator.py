"""What the hosts need from the tessellator, so they need nothing else from it.

Two things reached past the core into `ocp_tessellate` from every host's
`__init__`, identically: `ImageFace`, re-exported into the star surface, and
the three native-tessellator toggles. That was the only reason a viewer had to
name `ocp-tessellate` among its own dependencies - the pipeline that actually
tessellates is in `show.py`, here, and it carries the dependency for everyone.

The toggles exist in `ocp_tessellate.tessellator` only when `ocp_addons` is
installed, which is why each host wrapped the import in `try`/`except` and left
the names out of its `__all__` - a name that may not exist breaks every star
import when it does not. They are always defined here, and honest when the
accelerator is absent: `is_native_tessellator_enabled()` answers False, and
`enable_native_tessellator()` says why it cannot. `init_native_tessellator()`
applies the `NATIVE_TESSELLATOR` environment variable once at host import and
returns what it achieved, so the host - not the core - decides what to print.

Importing this module loads the tessellator and with it the OCP kernel, so the
package root does not import it. A host does, as it does `show`.
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

import os

from ocp_tessellate.cad_objects import ImageFace
from ocp_tessellate.tessellator import NATIVE as NATIVE_TESSELLATOR_AVAILABLE

__all__ = [
    "NATIVE_TESSELLATOR_AVAILABLE",
    "ImageFace",
    "disable_native_tessellator",
    "enable_native_tessellator",
    "init_native_tessellator",
    "is_native_tessellator_enabled",
]

# The environment variable is the whole state: `ocp_tessellate.tessellator`
# reads it per tessellation (`if NATIVE and is_native_tessellator_enabled()`),
# so setting it is what the toggles do there and what they do here.
ENV_VAR = "NATIVE_TESSELLATOR"


def enable_native_tessellator() -> None:
    """Tessellate with the native accelerator from here on."""
    if NATIVE_TESSELLATOR_AVAILABLE is False:
        raise RuntimeError(
            "The native tessellator needs the ocp_addons package, "
            "which is not installed."
        )
    os.environ[ENV_VAR] = "1"


def disable_native_tessellator() -> None:
    """Tessellate in Python from here on."""
    os.environ[ENV_VAR] = "0"


def is_native_tessellator_enabled() -> bool:
    """Whether the next tessellation will use the native accelerator."""
    if NATIVE_TESSELLATOR_AVAILABLE is False:
        return False
    return os.environ.get(ENV_VAR) == "1"


def init_native_tessellator() -> bool:
    """Apply `NATIVE_TESSELLATOR` from the environment, once, at host import.

    Enabled unless the variable says `0`, which is the choice every host made
    on its own. Returns whether the accelerator is on afterwards - the caller
    prints, because a core that writes to stdout is a trap for the host whose
    stdout is a protocol.
    """
    if NATIVE_TESSELLATOR_AVAILABLE is False:
        return False
    if os.environ.get(ENV_VAR) == "0":
        disable_native_tessellator()
    else:
        enable_native_tessellator()
    return is_native_tessellator_enabled()
