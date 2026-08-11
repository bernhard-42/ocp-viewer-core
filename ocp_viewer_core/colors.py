"""The base every colormap derives from.

Here, and not in `show.py`, for one reason: `_show` decides whether `colors=`
is a colormap with `isinstance(colors, BaseColorMap)`, so a host's
`ColorMap.tab10()` has to be an instance of *this* class rather than of a
second copy with the same name. Two identical definitions is exactly the case
`isinstance` cannot see through, and it fails silently - the colormap is taken
for a list of colors.

Its own module rather than `show.py` because `show.py` imports ocp_tessellate
and so reaches OCP. A host's colour catalogue needs colorsys, random and
webcolors and nothing else, and importing one should not pull the kernel in.

Only the base class has moved. The catalogue - the mappers, `web_to_rgb`, the
listed and segmented maps, `ColorMap` itself - is still each host's, which is a
smaller claim than the split deserves: every client wants the same tab10. That
is worth doing as its own step rather than folded into an adoption.
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

__all__ = ["BaseColorMap"]


class BaseColorMap:
    """Base class for color maps"""

    def __init__(self):
        self.index = 0
        self.alpha = 1.0

    def __iter__(self):
        return self

    def __next__(self):
        raise NotImplementedError()

    def reset(self):
        """Reset the color map"""
        self.index = 0
