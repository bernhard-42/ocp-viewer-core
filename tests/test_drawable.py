"""What `is_drawable` lets through show_all's container gate.

The gate exists to refuse containers the tessellator could make nothing of - a
scope is full of lists of numbers, and one of those reaching `_convert` produces
a model with a header and no geometry, which three-cad-viewer does not come back
from. But a container is drawable when *anything* in it is: the show pipeline
filters the rest, exactly as it does for a mixed list passed to `show` directly.
Requiring *everything* to be drawable silently dropped a dict holding shapes
beside a stray int or string, which is a real way to hold an assembly.
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

import pytest
from build123d import Box, Pos, Vector

from ocp_viewer_core.show import is_drawable


@pytest.fixture(scope="module")
def box():
    return Pos(1, 1, 1) * Box(1, 2, 3)


def test_shape_is_drawable(box):
    assert is_drawable(box) is True


def test_vector_is_drawable():
    assert is_drawable(Vector(1, 2, 3)) is True


def test_scalars_are_not_drawable():
    assert is_drawable(0) is False
    assert is_drawable("wert") is False
    assert is_drawable(None) is False


def test_all_drawable_container(box):
    assert is_drawable([box, Vector(1, 2, 3)]) is True


def test_number_containers_are_not_drawable():
    # The case the gate exists for: a list of floats must never reach _convert.
    assert is_drawable([1.0, 2.0, 3.0]) is False
    assert is_drawable((1, 2)) is False
    assert is_drawable({"x": 1, "y": 123}) is False


def test_empty_containers_are_not_drawable():
    assert is_drawable([]) is False
    assert is_drawable(()) is False
    assert is_drawable({}) is False


def test_mixed_list_is_drawable(box):
    assert is_drawable([box, "wert", 123]) is True


def test_mixed_dict_is_drawable(box):
    assert is_drawable({"c": Vector(5, 2, 3), "d": box, "e": 123}) is True


def test_nested_mixed_containers(box):
    assert is_drawable([(1, 2, 3), {"d": box, "e": 123}]) is True
    assert is_drawable([(1, 2, 3), {"e": 123}]) is False
