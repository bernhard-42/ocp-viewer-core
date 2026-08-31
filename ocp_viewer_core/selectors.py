"""Selector helpers for naming faces, edges and vertices in the viewer."""

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
#

from ocp_tessellate.ocp_utils import (
    get_edges,
    get_faces,
    get_vertices,
    is_build123d,
    is_build123d_shape,
    is_cadquery,
    is_cadquery_sketch,
)

__all__ = [
    "select_edge",
    "select_edges",
    "select_face",
    "select_faces",
    "select_vertex",
    "select_vertices",
]


def _warn_once(message):
    def decorator(func):
        # A closure flag rather than an attribute on the wrapper: the state is
        # the decorator's, and a function attribute is invisible to the type
        # checker for the same reason it is invisible to a reader.
        warned = False

        def wrapper(*args, **kwargs):
            nonlocal warned
            if warned is False:
                print(message)
                warned = True
            return func(*args, **kwargs)

        return wrapper

    return decorator


def _ensure_build123d():
    """Import build123d at the call and hand back the module and the selector.

    Not a core dependency - the requirement surfaces here, when a build123d
    object is actually selected on, never at import.
    """
    import build123d as bd

    def _select_build123d(obj, indices, cls, getter):
        if hasattr(obj, "part"):
            obj = obj.part
        elif hasattr(obj, "sketch"):
            obj = obj.sketch
        elif hasattr(obj, "line"):
            obj = obj.line

        objects = list(getter(obj.wrapped))
        result = []
        for i in indices:
            object = cls(objects[i])
            object.topo_parent = obj
            result.append(object)

        return bd.ShapeList(result)

    return bd, _select_build123d


def _ensure_cadquery():
    """Import cadquery at the call and hand back the module and the selector.

    Not a core dependency - the requirement surfaces here, when a cadquery
    object is actually selected on, never at import.
    """
    import cadquery as cq

    def _select_cadquery(obj, indices, cls, getter):
        if len(obj.vals()) > 1:
            raise ValueError("CadQuery objects can only have 1 value in vals()")

        objects = list(getter(obj.val().wrapped))
        result = []
        for i in indices:
            result.append(objects[i])

        if is_cadquery(obj):
            return obj.newObject([cls(e) for e in result])

        elif is_cadquery_sketch(obj):
            obj._selection = [cls(e) for e in result]
            return obj

        return []

    return cq, _select_cadquery


@_warn_once(
    "Warning: The indices for 'select_vertices' are only valid as long the topology before this call will not be changed!"
)
def select_vertices(obj, indices):
    if is_build123d(obj) or is_build123d_shape(obj):
        bd, _select = _ensure_build123d()
        return _select(obj, indices, bd.Vertex, get_vertices)
    elif is_cadquery(obj) or is_cadquery_sketch(obj):
        cq, _select = _ensure_cadquery()
        return _select(obj, indices, cq.Vertex, get_vertices)
    else:
        raise ValueError(f"Wrong obj {type(obj)}")


@_warn_once(
    "Warning: The indices for 'select_edges' are only valid as long the topology before this call will not be changed!"
)
def select_edges(obj, indices):
    if is_build123d(obj) or is_build123d_shape(obj):
        bd, _select = _ensure_build123d()
        return _select(obj, indices, bd.Edge, get_edges)
    elif is_cadquery(obj) or is_cadquery_sketch(obj):
        cq, _select = _ensure_cadquery()
        return _select(obj, indices, cq.Edge, get_edges)
    else:
        raise ValueError(f"Wrong obj {type(obj)}")


@_warn_once(
    "Warning: The indices for 'select_faces' are only valid as long the topology before this call will not be changed!"
)
def select_faces(obj, indices):
    if is_build123d(obj) or is_build123d_shape(obj):
        bd, _select = _ensure_build123d()
        return _select(obj, indices, bd.Face, get_faces)
    elif is_cadquery(obj):
        cq, _select = _ensure_cadquery()
        return _select(obj, indices, cq.Face, get_faces)
    elif is_cadquery_sketch(obj):
        raise ValueError("select_faces not availbale for CadQuery sketches")
    else:
        raise ValueError(f"Wrong obj {type(obj)}")


def select_vertex(obj, index):
    vertices = select_vertices(obj, [index])
    if len(vertices) == 0:
        print("No vertex found")
        return None
    elif len(vertices) > 1:
        print("Found more than one vertex, returning the first")
    return vertices[0]


def select_edge(obj, index):
    edges = select_edges(obj, [index])
    if len(edges) == 0:
        print("No edge found")
        return None
    elif len(edges) > 1:
        print("Found more than one edge, returning the first")
    return edges[0]


def select_face(obj, index):
    faces = select_faces(obj, [index])
    if len(faces) == 0:
        print("No face found")
        return None
    elif len(faces) > 1:
        print("Found more than one face, returning the first")
    return faces[0]
