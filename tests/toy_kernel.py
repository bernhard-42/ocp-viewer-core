"""A kernel plugin of nothing but points, registering itself when imported - the way a
real plugin's module does, and what an entry point of the group
`ocp_viewer.kernels.backend` loads in the backend process.

A body is a list of points; it has no faces and no edges, and its points are its
vertices. `serialize` writes them as JSON, which is `ShowProtocol`'s to call, `deserialize`
reads them back, and `moved` applies the translation of a placement (a quaternion is not
applied: the toy is a transport test, not a geometry kernel)."""

import json
from math import sqrt

from ocp_viewer_core.backend import BackendProtocol, register_plugin

KERNEL = "toy"


def serialize(body):
    return json.dumps(body).encode("utf-8")


def deserialize(data):
    return [tuple(p) for p in json.loads(data.decode("utf-8"))]


def moved(shape, placement):
    (tx, ty, tz), _ = placement
    return [(x + tx, y + ty, z + tz) for x, y, z in shape]


def parts(shape):
    return [], [], shape


def kind(shape):
    return ("Compound", "Other") if isinstance(shape, list) else ("Vertex", "Point")


def center(shape):
    return shape[0] if isinstance(shape, list) else shape


def properties(shape):
    if isinstance(shape, list):
        return {"refpoint": shape[0]}
    return {"refpoint": shape, "point": shape}


def closest_points(shape1, shape2):
    p1 = shape1[0] if isinstance(shape1, list) else shape1
    p2 = shape2[0] if isinstance(shape2, list) else shape2
    return sqrt(sum((b - a) ** 2 for a, b in zip(p1, p2))), p1, p2


def closest_directions(shape1, shape2):
    return None


class ToyBackend(BackendProtocol):
    def deserialize(self, data):
        return deserialize(data)

    def moved(self, shape, placement):
        return moved(shape, placement)

    def parts(self, shape):
        return parts(shape)

    def kind(self, shape):
        return kind(shape)

    def center(self, shape):
        return center(shape)

    def properties(self, shape):
        return properties(shape)

    def closest_points(self, shape1, shape2):
        return closest_points(shape1, shape2)

    def closest_directions(self, shape1, shape2):
        return closest_directions(shape1, shape2)


BACKEND = ToyBackend()
register_plugin(KERNEL, BACKEND, api=1)
