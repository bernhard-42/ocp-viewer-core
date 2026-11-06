"""Python backend for the OCP Viewer"""

#
# Copyright 2025 Bernhard Walter
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

import base64
import sys
import traceback
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from ocp_tessellate.ocp_utils import (
    Placement,
    deserialize,
    downcast,
    make_compound,
    tq_to_loc,
)
from ocp_tessellate.tessellator import (
    get_edges,
    get_faces,
    get_vertices,
)
from ocp_tessellate.trace import Trace

from .comms import MessageType
from .logo import logo
from .measure import (
    distance_response,
    occt_center,
    occt_closest_directions,
    occt_closest_points,
    occt_kind,
    occt_properties,
    properties_response,
)
from .plugins import (
    BackendProtocol,
    ShapeProperties,
    backend_of,
    is_kernel_shape,
    register_plugin,
)

if TYPE_CHECKING:
    from ocp_tessellate.types import TopoDS_Shape  # noqa: F401 - named as a string by OcctBackend

# `register_plugin` is a kernel plugin's one call into the core, made here by name
# (`from ocp_viewer_core.backend import register_plugin`); the registry itself lives
# in `plugins.py`, which the package root can carry without loading a kernel.
__all__ = ["BackendProtocol", "OcctBackend", "ShapeProperties", "Tool", "ViewerBackend", "register_plugin"]

@dataclass
class Tool:
    """The tools available in the viewer"""

    Distance = "DistanceMeasurement"
    Properties = "PropertiesMeasurement"


def _placement_of(loc) -> Placement | None:
    """A leaf's `loc` as it travels, JSON's `[[x, y, z], [x, y, z, w]]` or null, as what
    `BackendProtocol.moved` takes."""
    return None if loc is None else Placement(tuple(loc[0]), tuple(loc[1]))


def print_to_stdout(*msg):
    """
    Write the given message to the stdout
    """
    print(*msg, flush=True, file=sys.stdout)


def error_handler(func):
    """Decorator for error handling"""

    def wrapper(*args, **kwargs):  # pylint: disable=redefined-outer-name
        try:
            return func(*args, **kwargs)
        # Deliberately everything: one malformed message from the viewer must
        # not take the backend down, since nothing would restart it.
        except Exception as exc:  # noqa: BLE001
            print_to_stdout(exc)
            traceback.print_exception(*sys.exc_info(), file=sys.stdout)

    return wrapper


class OcctBackend(BackendProtocol["TopoDS_Shape"]):
    """OCCT's implementation of the protocol, for OCP and nanocct alike. An OCCT leaf of
    edges or vertices arrives as one serialized shape per item, a body as one."""

    def deserialize(self, data: bytes | list[bytes]):
        """The shape of OCCT's BREP bytes, or of the list of them an OCCT leaf of edges or
        vertices travels as: the codec writes OCCT's leaves, a plugin's come as one blob."""
        if isinstance(data, list):
            shapes = [deserialize(item) for item in data]
            return make_compound(shapes) if len(shapes) > 1 else shapes[0]  # ty: ignore[invalid-argument-type]
        return deserialize(data)

    def moved(self, shape, placement):
        return shape.Moved(tq_to_loc(*placement))

    def parts(self, shape):
        return (
            [downcast(face) for face in get_faces(shape)],
            [downcast(edge) for edge in get_edges(shape)],
            [downcast(vertex) for vertex in get_vertices(shape)],
        )

    def kind(self, shape):
        return occt_kind(shape)

    def center(self, shape):
        return occt_center(shape)

    def properties(self, shape):
        return occt_properties(shape)

    def closest_points(self, shape1, shape2):
        return occt_closest_points(shape1, shape2)

    def closest_directions(self, shape1, shape2):
        return occt_closest_directions(shape1, shape2)


OCCT = "OCCT"
_OCCT_BACKEND = OcctBackend()


class ViewerBackend:
    """Exact geometry for a viewer's measurement tools.

    Given a model and a change set, it answers with the measurement the viewer
    asked for - and it answers by **returning**, never by sending. It holds no
    transport at all.

    That is not an omission. A change set only ever arrives because something
    already reached in: a socket message, an HTTP request, a line on a pipe. So
    whoever drove this already holds the channel the answer goes back on, and
    giving the backend its own would be a second route to a destination the
    caller can already reach. Every host proved it: two ended up with a no-op
    `send_response`, one with a class of four dead methods, and build123d
    Studio - which built the same thing independently - never gave its
    `Measurements` a transport in the first place.

    `handle_event` returns the response, or None when there is nothing to say -
    every DATA message, and any UPDATES with no active tool, no selection, or a
    selection the active tool cannot use. **Callers must check.**

    The model holds OCCT shapes, and the bodies of kernel plugins (`plugins.py`)
    beside them: an entry whose shape carries a `kernel` tag is rebuilt and measured
    through that plugin's `BackendProtocol`, every other entry through `OcctBackend`.
    A distance between shapes of two kernels is answered with a line saying so.
    """

    def __init__(self) -> None:
        # An empty model rather than None. It is only ever assigned a dict and
        # never compared against None, and typed as None every subscript into it
        # reads as an error - twelve of them, all describing the annotation
        # rather than the code.
        self.model: dict = {}
        # the kernel and its backend of every id in the model
        self.kernels: dict[str, str] = {}
        self.backends: dict[str, BackendProtocol] = {}
        self.activated_tool = None
        self.filter_type = "none"  # The current active selection filter

    def start(self):
        """Load the splash, so it is measurable before any model is shown.

        What used to follow this - handing `handle_event` to a listener - is the
        host's, because only the host knows whether its backend is driven by a
        loop it owns or called by a server that already has the request.
        """
        print("Viewer backend started", flush=True)
        self.load_model(logo)
        print("Logo model loaded", flush=True)

    @error_handler
    def handle_event(self, message, event_type: MessageType):
        """
        Handle the event received from the websocket
        Dispatch the event to the appropriate handler
        """
        if event_type == MessageType.DATA:
            self.load_model(message)
        elif event_type == MessageType.UPDATES:
            changes = message

            if "activeTool" in changes:
                active_tool = changes.get("activeTool")

                if active_tool != "None":
                    self.activated_tool = active_tool
                else:
                    self.activated_tool = None

            if self.activated_tool is not None:
                return self.handle_activated_tool(changes)

    def handle_activated_tool(self, changes):
        """
        Handle the activated tool, there is a special behavior for each tool
        """
        if "selectedShapeIDs" not in changes:
            return

        selected_objs = changes["selectedShapeIDs"]
        if self.activated_tool == Tool.Distance and len(selected_objs) == 3:
            shape_id1 = changes["selectedShapeIDs"][0]
            shape_id2 = changes["selectedShapeIDs"][1]
            shift = changes["selectedShapeIDs"][2]

            return self.handle_distance(shape_id1, shape_id2, shift)

        elif self.activated_tool == Tool.Properties and len(selected_objs) == 2:
            shape_id = changes["selectedShapeIDs"][0]
            return self.handle_properties(shape_id)

    def load_model(self, raw_model):
        """Read the transferred model from websocket"""

        def walk(model):
            for v in model["parts"]:
                if v.get("parts") is not None:
                    walk(v)
                elif is_kernel_shape(v["shape"]):
                    self._load_kernel_entry(v, trace)
                elif isinstance(v["shape"], dict):
                    data = base64.b64decode(v["shape"]["obj"].encode("utf-8"))
                    self._load_entry(v["id"], OCCT, _OCCT_BACKEND, data, v["loc"], trace)
                else:
                    data = [base64.b64decode(s.encode("utf-8")) for s in v["shape"]]
                    self._load_entry(v["id"], OCCT, _OCCT_BACKEND, data, v["loc"], trace)

        self.model = {}
        self.backends = {}
        self.kernels = {}
        trace = Trace("ocp-vscode-backend.log")
        walk(raw_model)
        trace.close()

    def _load_kernel_entry(self, v, trace):
        """A leaf of a kernel plugin. What fails with it, a missing plugin too, is the leaf's:
        everything else of the scene stays measurable, and this leaf is an unknown id."""
        kernel = v["shape"]["kernel"]
        try:
            data = base64.b64decode(v["shape"]["obj"].encode("utf-8"))
            self._load_entry(v["id"], kernel, backend_of(kernel), data, v["loc"], trace)
        except Exception as ex:  # noqa: BLE001
            print_to_stdout(f"{kernel} shape '{v['id']}' not loaded: {ex!r}")

    def _load_entry(self, id_, kernel, backend, data, loc, trace):
        """A shape rebuilt by its kernel's backend, and its faces, edges and vertices under
        the ids the viewer numbers them by."""
        shape = backend.deserialize(data=data)
        placement = _placement_of(loc)
        if placement is not None:
            shape = backend.moved(shape=shape, placement=placement)
        faces, edges, vertices = backend.parts(shape=shape)
        self._add(id_, shape, kernel, backend)
        # the trace reads OCCT's objects
        is_occt = kernel == OCCT
        for i, face in enumerate(faces):
            if is_occt:
                trace.face(f"{id_}/faces/faces_{i}", face)
            self._add(f"{id_}/faces/faces_{i}", face, kernel, backend)
        for i, edge in enumerate(edges):
            if is_occt:
                trace.edge(f"{id_}/edges/edges_{i}", edge)
            self._add(f"{id_}/edges/edges_{i}", edge, kernel, backend)
        for i, vertex in enumerate(vertices):
            if is_occt:
                trace.vertex(f"{id_}/vertices/vertex_{i}", vertex)
            self._add(f"{id_}/vertices/vertices_{i}", vertex, kernel, backend)

    def _add(self, id_, shape, kernel: str, backend: BackendProtocol) -> None:
        self.model[id_] = shape
        self.kernels[id_] = kernel
        self.backends[id_] = backend

    def _kernel_of(self, id_) -> str:
        """The kernel an id's shape belongs to, for the log: a plugin's tag, OCCT, or
        unknown for an id the model does not hold."""
        return self.kernels.get(id_, "unknown")

    def handle_properties(self, shape_id):
        """
        Request the properties of the object with the given id
        """
        print_to_stdout(f"{self._kernel_of(shape_id)} identifier received '{shape_id}'")

        backend, shape = self.backends[shape_id], self.model[shape_id]
        response = properties_response(backend.kind(shape=shape), backend.properties(shape=shape))

        response["type"] = "backend_response"
        response["subtype"] = "tool_response"
        response["tool_type"] = Tool.Properties

        return response

    def handle_distance(self, id1, id2, center):
        """
        Request the distance between the two objects that have the given ids
        """
        kernel1, kernel2 = self._kernel_of(id1), self._kernel_of(id2)
        kernels = kernel1 if kernel1 == kernel2 else f"{kernel1}/{kernel2}"
        print_to_stdout(f"{kernels} identifiers received '{id1}', '{id2}'")

        shape1 = self.model[id1]
        shape2 = self.model[id2]
        backend1 = self.backends[id1]

        response: dict[str, Any]
        if backend1 is not self.backends[id2]:
            # one row: the panel prints a string value as it is, under its key's label
            # (it skips a section's `info` key, which only annotates a distance
            # number); without points there are no markers
            response = {
                "result": [{"distance": f"not measured: shapes of two kernels ({kernel1}, {kernel2})"}],
                "refpoint1": None,
                "refpoint2": None,
            }
        else:
            response = distance_response(
                shape1,
                shape2,
                center,
                backend1.kind,
                backend1.center,
                backend1.closest_points,
                backend1.closest_directions,
            )
        response["type"] = "backend_response"
        response["subtype"] = "tool_response"
        response["tool_type"] = Tool.Distance

        return response
