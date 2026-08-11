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

from ocp_tessellate.ocp_utils import (
    deserialize,
    downcast,
    identity_location,
    make_compound,
    tq_to_loc,
)
from ocp_tessellate.tessellator import (
    get_edges,
    get_faces,
    get_vertices,
)
from ocp_tessellate.trace import Trace

from .comms import Comms, MessageType
from .logo import logo
from .measure import get_distance, get_properties


@dataclass
class Tool:
    """The tools available in the viewer"""

    Distance = "DistanceMeasurement"
    Properties = "PropertiesMeasurement"


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


class ViewerBackend:
    """
    Represents the backend of the viewer, it listens to the websocket and handles the events
    It's job is to send responses to the vscode extension that goes through the three cad
    viewer view.
    The responses holds all the data needed to display the measurements.
    """

    def __init__(self, comms: Comms) -> None:
        # The transport, not a port. Which viewer this backend answers, and how
        # it answers, is the host's business - the same injection the show
        # pipeline takes, one layer down. `jcv_id` went with it: it named the
        # widget a response belonged to, which is something an injected Comms
        # holds without anybody being told about widgets.
        self.comms = comms
        # An empty model rather than None. It is only ever assigned a dict and
        # never compared against None, and typed as None every subscript into it
        # reads as an error - twelve of them, all describing the annotation
        # rather than the code.
        self.model: dict = {}
        self.activated_tool = None
        self.filter_type = "none"  # The current active selection filter

    def start(self):
        """
        Start the backend
        """
        print("Viewer backend started", flush=True)
        self.load_model(logo)
        print("Logo model loaded", flush=True)
        self.comms.listen(self.handle_event)

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

        def walk(model, trace):
            for v in model["parts"]:
                if v.get("parts") is not None:
                    walk(v, trace)
                else:
                    id_ = v["id"]
                    loc = (
                        identity_location()
                        if v["loc"] is None
                        else tq_to_loc(*v["loc"])
                    )
                    # `deserialize` is annotated as returning an optional
                    # shape and never returns None for a payload the viewer
                    # sent; the ignores describe ocp_tessellate's annotation,
                    # not this code, and belong upstream.
                    if isinstance(v["shape"], dict):
                        compound = deserialize(
                            base64.b64decode(v["shape"]["obj"].encode("utf-8"))
                        )
                    else:
                        shape = [
                            deserialize(base64.b64decode(s.encode("utf-8")))
                            for s in v["shape"]
                        ]
                        compound = (
                            make_compound(shape)  # ty: ignore[invalid-argument-type]
                            if len(shape) > 1
                            else shape[0]
                        )
                    self.model[id_] = compound.Moved(loc)  # ty: ignore[unresolved-attribute]
                    faces = get_faces(compound)  # ty: ignore[invalid-argument-type]
                    for i, face in enumerate(faces):
                        trace.face(f"{id_}/faces/faces_{i}", face)

                        self.model[f"{id_}/faces/faces_{i}"] = downcast(face.Moved(loc))
                    edges = get_edges(compound)  # ty: ignore[invalid-argument-type]
                    for i, edge in enumerate(edges):
                        trace.edge(f"{id_}/edges/edges_{i}", edge)

                        self.model[f"{id_}/edges/edges_{i}"] = (
                            edge if loc is None else downcast(edge.Moved(loc))
                        )
                    vertices = get_vertices(compound)  # ty: ignore[invalid-argument-type]
                    for i, vertex in enumerate(vertices):
                        trace.vertex(f"{id_}/vertices/vertex_{i}", vertex)

                        self.model[f"{id_}/vertices/vertices_{i}"] = (
                            vertex if loc is None else downcast(vertex.Moved(loc))
                        )

        self.model = {}
        trace = Trace("ocp-vscode-backend.log")
        walk(raw_model, trace)
        trace.close()

    def handle_properties(self, shape_id):
        """
        Request the properties of the object with the given id
        """
        print_to_stdout(f"Identifier received '{shape_id}'")

        shape = self.model[shape_id]

        response = get_properties(shape)

        response["type"] = "backend_response"
        response["subtype"] = "tool_response"
        response["tool_type"] = Tool.Properties

        self.comms.send_response(response)
        print_to_stdout(f"Data sent {response}")
        return response

    def handle_distance(self, id1, id2, center):
        """
        Request the distance between the two objects that have the given ids
        """
        print_to_stdout(f"Identifiers received '{id1}', '{id2}'")

        shape1 = self.model[id1]
        shape2 = self.model[id2]

        response = get_distance(shape1, shape2, center)
        response["type"] = "backend_response"
        response["subtype"] = "tool_response"
        response["tool_type"] = Tool.Distance

        self.comms.send_response(response)
        print_to_stdout(f"Data sent {response}")
        return response
