"""Kernel plugins of the measurement backend: the protocol, the registry, and what their
shapes travel as.

The backend (`backend.py`) answers the viewer's measurement tools from the geometry
behind the mesh. A plugin (`ocp_tessellate.plugin`, e.g. ocp-viewer-smlibpy for SMLib)
implements `BackendProtocol` for its kernel, and `backend.OcctBackend` does for OCCT, so
the backend treats them alike. It is required of a plugin, because every leaf of a shown
object has an entry in the model.

`register_plugin(kernel, backend, api=1)` is the one mechanism. A plugin calls it in a module of
its own. The backend process imports no user code, so that module is reached through an entry
point of the group `ocp_viewer.kernels.backend` named like the kernel: `backend_of` loads it on
the first model that carries the kernel. The process that shows needs none of this: what
draws and what serializes is `ShowProtocol` of ocp_tessellate.

The protocol as a whole is described in the docs: https://bernhard-42.github.io/ocp_viewer_docs/plugins/backend/

On the wire a kernel's shape is a model entry whose shape is `{"kernel": tag, "obj":
shape}`, as `OcpObject.collect` emits it; `ocp_tessellate.kernels.encode_kernel_shapes` turns
it into base64 of the plugin's `ShowProtocol.serialize` before the model is sent, so the codec
never sees it. An OCCT entry has no `kernel` key.

This module is light on purpose: the package root carries it, and it must not load
a kernel (see `__init__.py`).
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

from __future__ import annotations

from abc import abstractmethod
from importlib.metadata import entry_points
from typing import TYPE_CHECKING, Any, Protocol, TypedDict, TypeVar, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Sequence

    # types only: this module must not load a kernel
    from ocp_tessellate.ocp_utils.location import Placement

# the entry point group of what a kernel plugin measures with, keyed by its kernel tag, whose
# value is the module that registers it, so the backend process finds it:
# `[project.entry-points."ocp_viewer.kernels.backend"] smlib = "ocp_viewer_smlibpy.backend"`.
# ocp_tessellate reads `ocp_viewer.kernels.show` in the process that shows
ENTRY_POINT_GROUP = "ocp_viewer.kernels.backend"


# What a plugin's shapes are, named when it subclasses the protocol, as in
# `BackendProtocol[Body | Face | Edge | Vertex]`, so a type checker checks it against them.
ShapeT = TypeVar("ShapeT")


Point = tuple[float, float, float]


class _KnownOfEveryShape(TypedDict):
    refpoint: Point | None


class ShapeProperties(_KnownOfEveryShape, total=False):
    """What a kernel knows about a shape, as plain numbers. The core makes the panel's rows
    and strings of it, for OCCT and every plugin alike. Only the properties tool asks for it, so
    it may take its time: an exact bounding box of a large solid takes most of a second.

    `refpoint`: where the panel's marker points to. The rest is what the kernel has for the
    shape: a key that is left out has no row. A vertex needs `point`."""

    point: Point
    center: Point
    radius: float
    major_radius: float
    minor_radius: float
    base_radius: float
    half_angle: float
    offset: float
    axis_location: Point
    axis_direction: Point
    start: Point
    middle: Point
    end: Point
    vertex: Point
    length: float
    area: float
    volume: float
    tangent_start: Point
    tangent_end: Point
    normal: Point
    bb_min: Point
    bb_max: Point


@runtime_checkable
class BackendProtocol(Protocol[ShapeT]):
    """What the measurement backend needs of a kernel: small functions, one for each step
    OCCT takes. The core runs the sequence and makes the panel's rows. A plugin subclasses
    it, so that a method it forgot fails when its object is created, and registers it."""

    @abstractmethod
    def deserialize(self, data: bytes) -> ShapeT:
        """The shape of the bytes of `ShowProtocol.serialize` of ocp_tessellate, which wrote them
        in the process that shows: `deserialize(serialize(x))` is x again. Raise on a format
        version it cannot read: the two processes can have different versions of the plugin."""

    @abstractmethod
    def moved(self, shape: ShapeT, placement: Placement) -> ShapeT:
        """The shape moved by a placement. Not called for a shape without one."""

    @abstractmethod
    def parts(self, shape: ShapeT) -> tuple[Sequence[ShapeT], Sequence[ShapeT], Sequence[ShapeT]]:
        """Its faces, edges and vertices, in the order the mesh numbers them: the viewer
        selects `{id}/faces/faces_{i}` and the backend answers for index i."""

    @abstractmethod
    def kind(self, shape: ShapeT) -> tuple[str, str]:
        """What a shape is. Its type: `Vertex`, `Edge`, `Wire`, `Face`, `Shell`, `Solid`,
        `CompSolid`, `Compound`. Its geometry: the names of `SURFACE_TYPES` and `CURVE_TYPES`,
        `Point` for a vertex, `Other` for a body. Asked at every click of the distance tool, so
        it must be cheap."""

    @abstractmethod
    def center(self, shape: ShapeT) -> Point | None:
        """The point the distance tool's center mode measures from, None if the shape has none.
        Asked at every such click, so it must not compute more than it needs."""

    @abstractmethod
    def properties(self, shape: ShapeT) -> ShapeProperties:
        """What the kernel knows about a shape. See `ShapeProperties`."""

    @abstractmethod
    def closest_points(self, shape1: ShapeT, shape2: ShapeT) -> tuple[float, Point, Point]:
        """The minimum distance of two shapes, and the points it is taken between."""

    @abstractmethod
    def closest_directions(self, shape1: ShapeT, shape2: ShapeT) -> tuple[Point, Point] | None:
        """The tangent of an edge or the normal of a face at the closest points of two
        edges or faces, None if there are no such directions."""


PLUGINS: dict[str, BackendProtocol] = {}
# the version of the plugin interface each of them stated
PLUGIN_APIS: dict[str, int] = {}

# The version of the plugin interface this ocp-viewer-core serves. A plugin states the one it
# was written against, as a number of its own: a later version passes new arguments only to
# plugins that state it, so an existing plugin keeps working.
PLUGIN_API = 1


def register_plugin(kernel: str, backend: BackendProtocol, *, api: int) -> None:
    """Register a kernel's `BackendProtocol` under its tag. `api` is the version of the
    plugin interface the plugin was written against, a number of its own."""
    if not isinstance(backend, BackendProtocol):
        raise TypeError(f"{type(backend).__name__} does not implement BackendProtocol")
    if kernel == "" or kernel == "OCCT":
        raise ValueError(f"'{kernel}' is no kernel tag of a plugin: 'OCCT' names OCCT's own shapes")
    if type(api) is not int:
        raise TypeError(f"Kernel plugin '{kernel}': api must be an int, not {api!r}")
    if api < 1 or api > PLUGIN_API:
        raise ValueError(
            f"Kernel plugin '{kernel}' was written for plugin interface {api}, "
            f"this ocp-viewer-core serves interface 1 to {PLUGIN_API}"
        )
    action = "re-registered" if kernel in PLUGINS else "registered"
    PLUGINS[kernel] = backend
    PLUGIN_APIS[kernel] = api
    # flushed, as the backend's other lines are: a host may read its stdout through a pipe
    print(f"Kernel plugin '{kernel}' {action} for measuring ({type(backend).__module__})", flush=True)


def backend_of(kernel: str) -> BackendProtocol:
    """The backend registered for a kernel, loading its entry point first if it is not.

    LookupError when neither registered nor declared: the message names both ways and
    what is registered.
    """
    backend = PLUGINS.get(kernel)
    if backend is not None:
        return backend
    for entry_point in entry_points(group=ENTRY_POINT_GROUP):
        if entry_point.name == kernel:
            # importing the module it names is what registers the plugin
            entry_point.load()
            break
    backend = PLUGINS.get(kernel)
    if backend is None:
        raise LookupError(
            f"no measurement backend plugin for kernel '{kernel}': the plugin's package "
            f"registers it with ocp_viewer_core.backend.register_plugin in a module, and "
            f"declares that module as an entry point '{kernel}' in the group '{ENTRY_POINT_GROUP}' "
            f"so the backend process can import it. Registered: {sorted(PLUGINS)}"
        )
    return backend


def is_kernel_shape(shape: Any) -> bool:
    """Whether a model entry's shape belongs to a kernel plugin: `{"kernel": tag, "obj": ...}`."""
    return isinstance(shape, dict) and "kernel" in shape
