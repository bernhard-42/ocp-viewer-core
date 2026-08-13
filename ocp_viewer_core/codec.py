"""How the things JSON cannot carry are written down.

A model message holds more than numbers: the mapping handed to the measurement
backend is full of raw OCCT objects, and a config block can hold enums. One
answer for all of them, because it is the *protocol* that says a shape travels
as base64 BREP and a location as translation-plus-quaternion - not any one
socket.

It lived in `websocket.py`, where two of the four hosts happened to find it.
That module imports a websocket client at the top, so a host speaking its own
socket - build123d Studio sends length-prefixed binary frames over a local one -
had to drag that client in to reach a JSON encoder. The same reasoning that put
`MessageType` in `comms.py` puts this here.

It is not in `comms.py` itself for the property that module has and is worth
keeping: the transport contract does not reach OCP. This does, and says so.
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

from ocp_tessellate.ocp_utils import (
    is_toploc_location,
    is_topods_shape,
    loc_to_tq,
    serialize,
)


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
