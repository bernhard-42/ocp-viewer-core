"""A kernel plugin of nothing but points, registering itself when imported - the way a
real plugin's package does, and what an entry point of the group
`ocp_viewer_core.backend` loads in the backend process.

A body is a list of points; it has no faces and no edges, and its points are its
vertices. `serialize` writes them as JSON, `load` reads them back and applies the
translation of a location (a quaternion is not applied: the toy is a transport
test, not a geometry kernel)."""

import json
from math import sqrt

from ocp_viewer_core.backend import register_plugin

KERNEL = "toy"


def serialize(body):
    return json.dumps(body).encode("utf-8")


def load(data, loc):
    points = [tuple(p) for p in json.loads(data.decode("utf-8"))]
    if loc is not None:
        (tx, ty, tz), _ = loc
        points = [(x + tx, y + ty, z + tz) for x, y, z in points]
    return points, [], [], points


def get_properties(shape):
    if isinstance(shape, list):
        return {"shape_type": "Compound", "geom_type": "Other", "refpoint": shape[0], "result": [{"points": len(shape)}]}
    return {"shape_type": "Vertex", "geom_type": "Point", "refpoint": shape, "result": [{"xyz": shape}]}


def calc_distance(shape1, shape2, center=False):
    p1 = shape1[0] if isinstance(shape1, list) else shape1
    p2 = shape2[0] if isinstance(shape2, list) else shape2
    dx, dy, dz = p2[0] - p1[0], p2[1] - p1[1], p2[2] - p1[2]
    return {
        "distance": sqrt(dx * dx + dy * dy + dz * dz),
        "⇒ X | Y | Z": [abs(dx), abs(dy), abs(dz)],
        "point 1": p1,
        "point 2": p2,
        "info": "center" if center else "min",
        "refpoint1": p1,
        "refpoint2": p2,
    }


def calc_angle(shape1, shape2):
    return None


register_plugin(KERNEL, load, serialize, get_properties, calc_distance, calc_angle)
