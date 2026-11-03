# Measuring the objects of another kernel: the backend plugin protocol

The viewer's distance and properties tools are answered by the measurement backend, `ocp_viewer_core.backend.ViewerBackend`, from the exact geometry behind the mesh rather than from triangles. For OCCT shapes that is `ocp_viewer_core/measure.py`. For the bodies of another kernel it is a kernel plugin: five functions the plugin registers under its kernel tag, which the backend calls for every shape of that kernel.

This document describes that protocol: where the backend runs, what reaches it, what it asks a plugin, and what the plugin answers. Drawing the objects is the other half of a kernel plugin and is described in ocp-tessellate's `docs/ExternalKernel.md` (the tessellation and show contracts). The reference plugin is ocp-viewer-smlibpy (`ocp_viewer_smlibpy/backend.py`) for SMLib; `tests/toy_kernel.py` here is a minimal one, shown in section 5.

## 1. Where the backend runs

In every host the backend runs in another process than the user's script, so no object reaches it as a Python object and no import of the user's reaches it either:

| host | where the backend runs | how the model reaches it |
|---|---|---|
| OCP CAD Viewer for VS Code | `python -m ocp_vscode --backend --port <port>`, started by the extension with the configured interpreter | websocket to the extension, which relays it to the backend as it came |
| Jupyter CadQuery | the Jupyter server extension (`jupyter_cadquery/app.py`), one backend per viewer | HTTP post from the kernel |
| ocp-viewer | the viewer's server process (`ocp_viewer/server`) | websocket |
| build123d Studio | the sidecar's measure process | a local socket to the sidecar, a pipe to its measure process |

Three consequences shape the protocol:

- A body travels as bytes. The plugin's `serialize` turns it into bytes in the user's process, the plugin's `load` rebuilds it in the backend's.
- The plugin is found by an entry point. The backend process imports the plugin's package by the entry point named like the kernel tag, the first time a model carries that tag (section 4).
- The plugin must be installed in the environment the backend runs in. For VS Code that is the interpreter the extension starts the backend with, for Jupyter CadQuery the environment of the Jupyter server, which need not be the kernel's.

## 2. The protocol

### 2.1 The model

After every show the core sends the backend `{"model": mapping}`, at one place for all hosts (`Viewer._show_impl` in `show.py`). The mapping is the tree ocp-tessellate's `tessellate_group` builds next to the mesh: groups with `id` and `parts`, and one leaf per measurable object.

```json
{"id": "/Group", "parts": [
  {"id": "/Group/box",    "shape": {"obj": "<base64 BREP>", "cache_id": "...", "name": "box"}, "loc": [[0, 0, 0], [0, 0, 0, 1]]},
  {"id": "/Group/edges",  "shape": ["<base64 BREP>", "<base64 BREP>"], "loc": null},
  {"id": "/Group/shape0", "shape": {"kernel": "smlib", "obj": "<base64 of serialize(body)>"}, "loc": null}
]}
```

- An OCCT solid, face or shell leaf holds its instance (`obj` is the shape at its origin), an edge or vertex leaf a list of shapes. The codec (`codec.py`) writes OCCT shapes as base64 of OCCT's binary BREP.
- A kernel leaf holds `{"kernel": tag, "obj": body}`. ocp-tessellate's `OcpExternalObject.collect` emits it for a solid, face or shell converted with `external_tessellate(..., kernel=tag)`; objects without a tag, and a kernel's edges and vertices, have no leaf and cannot be measured. Before the model is sent, `plugins.encode_kernel_shapes` replaces `obj` by base64 of the plugin's `serialize(body)`, so the codec never sees a kernel's object.
- `loc` is the leaf's placement, from the locations of the groups above it and its own: `[[tx, ty, tz], [qx, qy, qz, qw]]`, a translation and a unit quaternion in the order of ocp-tessellate's `loc_to_tq`, or `null`. The point p of the body is drawn at R(q) p + t.

### 2.2 The ids

The viewer selects sub-shapes by id, and the backend keeps one shape per id. For a leaf `{id}`:

| id | shape |
|---|---|
| `{id}` | the whole object: sent for a solid picked as a whole; the faces and shells of a shown face or shell are selected one by one |
| `{id}/faces/faces_{i}` | the face of index i |
| `{id}/edges/edges_{i}` | the edge of index i |
| `{id}/vertices/vertices_{i}` | the vertex of index i |

The viewer numbers faces and edges by the order of the tessellation's face blocks (`triangles_per_face`) and edge blocks (`segments_per_edge`), vertices by the order of `obj_vertices`. The backend must number them the same way, or a click reports another face than the one clicked: a plugin's `load` returns the sub-shapes in exactly the order its tessellator lists them, seam edges included where the tessellator lists them.

### 2.3 The requests

The viewer reports every change of its state; the backend acts on two keys of a change set:

| key | value |
|---|---|
| `activeTool` | `"DistanceMeasurement"`, `"PropertiesMeasurement"` or `"None"` |
| `selectedShapeIDs` | `[id, shift]` for the properties tool, `[id1, id2, shift]` for the distance tool |

`shift` is whether the shift key was held. For the distance tool it asks for the distance of the two centers instead of the minimum distance (`center` below); the properties tool ignores it. A selection with another number of entries is not a request.

### 2.4 The responses

The backend answers a request by returning a dict, which the host sends to the viewer. The backend adds `type: "backend_response"`, `subtype: "tool_response"` and `tool_type`; the rest is the plugin's.

A properties response:

| key | value |
|---|---|
| `shape_type` | `"Vertex"`, `"Edge"`, `"Face"`, `"Shell"`, `"Solid"` (the panel translates Vertex, Edge, Face and Solid, and shows other names as they are) |
| `geom_type` | the GeomAbs name without the prefix: `"Point"`, `"Plane"`, `"Cylinder"`, `"Cone"`, `"Sphere"`, `"Torus"`, `"BSplineSurface"`, `"SurfaceOfRevolution"`, `"Line"`, `"Circle"`, `"Ellipse"`, `"BSplineCurve"`, ..., or `"Other"` for a body; the same names the tessellation's `face_types` and `edge_types` codes stand for, so the panel and the status line agree |
| `refpoint` | `[x, y, z]`, where the panel's marker points to |
| `result` | the panel's sections, a list of dicts |

A distance response:

| key | value |
|---|---|
| `result` | the panel's sections: the distance with `⇒ X \| Y \| Z` and `info` (`"min"` or `"center"`), the two points, and the angle where there is one |
| `refpoint1`, `refpoint2` | `[x, y, z]`, the ends of the distance arrow; `null` draws no arrow |

The panel renders a section key by key, in order, with a separator between sections:

- `bb` holding a dict of three-number lists: one vector row per entry (`bb min`, `bb center`, `bb max`, `bb size`).
- a list of three numbers: a vector row.
- a number: a value row with three decimals. A section's `info` string is shown beside its `distance` number.
- a string: a row with the text as it is (angles are sent as `"60.000 (120.000)"`, the angle and its supplement, see `measure.with_supplement`).
- anything else, and the keys `type`, `tool_type`, `subtype`, `info`, `refpoint`, `refpoint1`, `refpoint2`, `shape_type`, `geom_type`, `groups`, `result`: nothing.

The values must be JSON: numbers, strings, lists, tuples (they become lists), dicts, `None`. No kernel object may be left in a response.

## 3. The plugin contract

Five functions. The shapes they take are what `load` returned: the plugin's own objects, never seen by the core.

| function | what it does |
|---|---|
| `serialize(body) -> bytes` | the body as bytes, in the user's process. Exact, and complete for what `load` needs, since the backend has nothing else |
| `load(data, loc) -> (body, faces, edges, vertices)` | in the backend's process: the body rebuilt from `serialize`'s bytes and moved by `loc` (section 2.1, or `None`), with three lists of its sub-shapes in the order of section 2.2 |
| `get_properties(shape) -> dict` | the properties response of section 2.4 for the body or one of its faces, edges or vertices |
| `calc_distance(shape1, shape2, center) -> dict` | the distance of two shapes: of their centers when `center` is true, else the minimum. Keys: `distance`, `⇒ X \| Y \| Z` (the absolute differences of the two points), `point 1`, `point 2`, `info` (`"center"` or `"min"`), `refpoint1`, `refpoint2` |
| `calc_angle(shape1, shape2) -> dict \| None` | the angle of two edges or faces at their closest points, in degrees: of the tangents of two edges, of the normals of two faces, of an edge to a face (90 minus the angle of tangent and normal). Keys: `angle` (a number), `reference 1` and `reference 2` (`"line"`, `"tangent at P1"`, `"face normal"`, `"surface normal at P2"`, ...), and per shape `direction 1` / `direction 2` for an edge or `normal 1` / `normal 2` for a face. `None` for any other pair |

`get_properties`, `calc_distance` and `calc_angle` follow `ocp_viewer_core.measure`'s functions of the same names, which are the reference for which sections, rows and centers the panel shows: the center of a circle, cylinder, cone, sphere, torus or surface of revolution is the origin of its axis, of any other edge its middle, of a face its centroid, of a body its center of mass. The backend assembles the distance tool's response from `calc_distance` and `calc_angle` with `measure.distance_response(shape1, shape2, center, calc_distance, calc_angle)`, the same function `measure.get_distance` uses for OCCT shapes, so a plugin does not build that response itself.

The backend measures two shapes of the same kernel only. A distance between shapes of two kernels (two plugins, or a plugin and OCCT) is answered with one row, `distance: not measured: shapes of two kernels (smlib, OCCT)`, and no arrow.

An exception in a plugin function is caught and printed by the backend's error handler, and the request gets no answer; the backend keeps running.

## 4. Registration

A plugin registers its five functions when its package is imported:

```python
from ocp_viewer_core.backend import register_plugin

register_plugin(KERNEL, load, serialize, get_properties, calc_distance, calc_angle)
```

and declares an entry point of the group `ocp_viewer_core.backend` named like its kernel tag, whose value is the module whose import registers it:

```toml
[project.entry-points."ocp_viewer_core.backend"]
smlib = "ocp_viewer_smlibpy"
```

The import covers the user's process: the user imports the plugin to show its objects, and `encode_kernel_shapes` finds it registered. The entry point covers the backend's process, which imports nothing of the user's: `plugins.plugin_of(kernel)` looks in the registry first, and loads the entry point named like the kernel only when the kernel is not registered yet. A kernel neither registered nor declared fails the model's loading with a `LookupError` that names both ways. A second registration of the same tag replaces the first.

The backend's log says when a kernel's plugin is first used, once per process, and names the kernel of every selected id:

```
Measurement plugin for kernel 'smlib' loaded (ocp_viewer_smlibpy.backend)
smlib identifiers received '/Group/shape0/edges/edges_9', '/Group/shape0/edges/edges_1'
OCCT identifier received '/Group/box/faces/faces_0'
smlib/OCCT identifiers received '/Group/shape0/faces/faces_3', '/Group/box/faces/faces_0'
```

## 5. A complete toy plugin

`tests/toy_kernel.py`: a kernel whose bodies are lists of points, with no faces and no edges, so that every vertex is selectable. It is a test of the transport, not of geometry: `load` applies only the translation of `loc`.

```python
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
```

## 6. What to test

`tests/test_kernel_plugins.py` tests the core's side with the toy kernel: importing the plugin registers it, the entry point loads it in a process that never imported it, an unknown kernel names both ways to register, a body travels as base64 of its `serialize` bytes while OCCT entries are left to the codec, the backend holds a plugin's body beside OCCT shapes under the ids of section 2.2, both tools answer for either kernel, a distance across kernels is one row, and the log lines of section 4.

For a real kernel, add on the plugin's side:

- the order: every triangle of the tessellation's face block i lies on the face `load` returns at index i, every segment of edge block i on edge i, and the vertices are `obj_vertices`. This is the test that catches a click reporting the wrong face
- the round trip: `load(serialize(body))` gives the same geometry, also for a body that was measured before it was serialized, and a `loc` moves it as OCCT's `tq_to_loc` moves an OCCT shape
- the measurements against an oracle: where the kernel's objects convert to OCCT, `ocp_viewer_core.measure` on the converted shapes, paired by geometry (OCCT numbers sub-shapes in its own order); otherwise analytic values, such as the distance of two straight segments
- the whole way: the show pipeline's mapping, `encode_kernel_shapes`, the codec and JSON, `ViewerBackend.load_model`, and `handle_event` with ids taken from the mesh

ocp-viewer-smlibpy's `tests/test_backend.py` does all four.

## 7. Versioning

The kernel leaf is a new message shape between the core's two Python sides, the show and the backend, so both need a core that knows it: ocp-viewer-core with `ocp_viewer_core/plugins.py`, and ocp-tessellate 3.7 with the `kernel` tag. No JavaScript reads the backend's model: the core's JavaScript half never receives it, and VS Code's extension relays it as it came. The viewer's requests and responses keep their shape.
