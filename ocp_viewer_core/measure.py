"""Measurements over BREP: distances, angles and properties.

Answers the questions the viewer's measurement tools ask - the distance
between two shapes, the properties of one - in the geometry kernel rather than
in the renderer, which sees only triangles. The OCCT work is ocp_tessellate's
(for OCP and nanocct objects alike); this module only reports it.
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

from math import pi, sqrt

from ocp_tessellate.ocp_utils import (
    BoundingBox,
    angle_between,
    area,
    center_of_geometry,
    center_of_mass,
    closest_directions,
    dist_shapes,
    downcast,
    face_normal,
    get_curve,
    get_point,
    get_surface,
    is_closed,
    is_topods_compound,
    is_topods_compsolid,
    is_topods_edge,
    is_topods_face,
    is_topods_shell,
    is_topods_solid,
    is_topods_vertex,
    is_topods_wire,
    is_vector,
    length,
    position_at,
    tangent_at,
    volume,
)

from .plugins import ShapeProperties


def with_supplement(angle):
    """An angle in degrees and its supplement, as the panel shows them: "60.000 (120.000)".

    Both angles two directions form, as one string: the panel prints a string
    as it is, where a number gets a row of its own. Clamped, so an angle a
    rounding error past 180 does not show its supplement as -0.000
    (vscode-ocp-cad-viewer issue 236).
    """
    return f"{angle:.3f} ({max(180 - angle, 0.0):.3f})"


def get_shape_type(shape):
    if is_topods_vertex(shape) or is_vector(shape):
        return "Vertex"
    elif is_topods_edge(shape):
        return "Edge"
    elif is_topods_wire(shape):
        return "Wire"
    elif is_topods_face(shape):
        return "Face"
    elif is_topods_shell(shape):
        return "Shell"
    elif is_topods_solid(shape):
        return "Solid"
    elif is_topods_compsolid(shape):
        return "CompSolid"
    elif is_topods_compound(shape):
        return "Compound"
    else:
        print(shape, "unknown")
        return "Unknown"


def get_geom_type(shape):
    if is_topods_vertex(shape) or is_vector(shape):
        return "Point"
    elif is_topods_edge(shape):
        # `.name` on the enum is annotated optional and never is for a curve
        # that exists; the annotation is ocp_tessellate's to fix.
        return get_curve(shape).GetType().name.split("_")[-1]  # ty: ignore[unresolved-attribute]
    elif is_topods_face(shape):
        return get_surface(shape).GetType().name.split("_")[-1]  # ty: ignore[unresolved-attribute]
    elif (
        is_topods_wire(shape)
        or is_topods_shell(shape)
        or is_topods_solid(shape)
        or is_topods_compound(shape)
        or is_topods_compsolid(shape)
    ):
        return "Other"
    else:
        print(shape, "unknown")
        return "Unknown"


def _xyz(direction) -> tuple[float, float, float]:
    return (direction.X(), direction.Y(), direction.Z())


def occt_kind(shape) -> tuple[str, str]:
    """What an OCCT shape is, as `BackendProtocol.kind` gives it."""
    shape = downcast(shape)
    return get_shape_type(shape), get_geom_type(shape)


def occt_center(shape):
    """The center of an OCCT shape, as `BackendProtocol.center` gives it: None for a degenerated
    edge, which has none."""
    try:
        return get_center(downcast(shape))
    except Exception:  # noqa: BLE001
        return None


def occt_properties(shape) -> ShapeProperties:
    """What OCCT knows about a shape, as `BackendProtocol.properties` gives it."""
    shape = downcast(shape)
    geom_type = get_geom_type(shape)
    props: ShapeProperties = {"refpoint": None}

    # The dispatch repeats get_shape_type's tests rather than comparing its
    # string: the predicates are TypeIs, so each branch holds the exact
    # TopoDS subtype its calls require. `is_vector` is not repeated - nothing
    # wrapped survives the downcast above.
    if is_topods_vertex(shape):
        pt = get_point(shape)
        props["refpoint"] = pt
        props["point"] = pt

    elif is_topods_edge(shape):
        # A degenerated edge has no positions, and no row for them: what it has, its kind,
        # still answers the distance tool.
        try:
            props["refpoint"] = get_point(position_at(shape, 0.5))

            if geom_type == "Circle":
                circle = get_curve(shape).Circle()
                props["center"] = get_point(circle.Location())
                props["radius"] = circle.Radius()
                props["start"] = get_point(position_at(shape, 0))
                if not is_closed(shape):
                    props["end"] = get_point(position_at(shape, 1))
                else:
                    props["refpoint"] = get_point(position_at(shape, 0))

            elif geom_type == "Ellipse":
                ellipse = get_curve(shape).Ellipse()
                props["center"] = get_point(ellipse.Location())
                props["major_radius"] = ellipse.MajorRadius()
                props["minor_radius"] = ellipse.MinorRadius()
                props["start"] = get_point(position_at(shape, 0))
                if not is_closed(shape):
                    props["end"] = get_point(position_at(shape, 1))
                else:
                    props["refpoint"] = get_point(position_at(shape, 0))

            elif geom_type == "Hyperbola":
                props["start"] = get_point(position_at(shape, 0))
                props["vertex"] = get_point(get_curve(shape).Hyperbola().Location())
                props["end"] = get_point(position_at(shape, 1))

            elif geom_type == "Parabola":
                props["start"] = get_point(position_at(shape, 0))
                props["vertex"] = get_point(get_curve(shape).Parabola().Location())
                props["end"] = get_point(position_at(shape, 1))

            elif geom_type == "OffsetCurve":
                props["offset"] = get_curve(shape).OffsetCurve().Offset()
                props["start"] = get_point(position_at(shape, 0))
                if is_closed(shape):
                    props["end"] = get_point(position_at(shape, 1))
                props["refpoint"] = get_point(position_at(shape, 0))

            else:
                props["start"] = get_point(position_at(shape, 0))
                props["middle"] = get_point(position_at(shape, 0.5))
                props["end"] = get_point(position_at(shape, 1))

        except Exception:  # noqa: BLE001, S110
            pass

        props["length"] = length(shape)
        for key, parameter in (("tangent_start", 0), ("tangent_end", 1)):
            try:
                _, tangent_dir = tangent_at(shape, parameter)
                props[key] = _xyz(tangent_dir)
            # An angle that cannot be computed is left out of the section
            # rather than failing the measurement.
            except Exception:  # noqa: BLE001, S110
                pass

    elif is_topods_face(shape):
        if geom_type == "Plane":
            props["center"] = get_point(get_surface(shape).Plane().Location())

        elif geom_type == "Cylinder":
            cylinder = get_surface(shape).Cylinder()
            props["center"] = get_point(cylinder.Location())
            props["radius"] = cylinder.Radius()

        elif geom_type == "Cone":
            cone = get_surface(shape).Cone()
            props["center"] = get_point(cone.Location())
            props["base_radius"] = cone.RefRadius()
            props["half_angle"] = cone.SemiAngle() / pi * 180

        elif geom_type == "Sphere":
            sphere = get_surface(shape).Sphere()
            props["center"] = get_point(sphere.Location())
            props["radius"] = sphere.Radius()

        elif geom_type == "Torus":
            torus = get_surface(shape).Torus()
            props["center"] = get_point(torus.Location())
            props["minor_radius"] = torus.MinorRadius()
            props["major_radius"] = torus.MajorRadius()

        elif geom_type == "SurfaceOfRevolution":
            revolution = get_surface(shape)
            props["axis_location"] = get_point(revolution.AxeOfRevolution().Location())
            props["axis_direction"] = _xyz(revolution.AxeOfRevolution().Direction())

        props["refpoint"] = center_of_geometry(shape)
        props["area"] = area(shape)
        try:
            normal = face_normal(shape)
            if normal is not None:
                props["normal"] = _xyz(normal)
        # As above: the angle is one line of a report, not the report.
        except Exception:  # noqa: BLE001, S110
            pass

    elif is_topods_wire(shape):
        props["length"] = length(shape)
        props["refpoint"] = center_of_mass(shape)

    elif is_topods_shell(shape):
        props["area"] = area(shape)
        props["refpoint"] = center_of_mass(shape)

    elif (
        is_topods_solid(shape)
        or is_topods_compsolid(shape)
        or is_topods_compound(shape)
    ):
        props["volume"] = volume(shape)
        props["refpoint"] = center_of_mass(shape)

    else:
        print(f"unknown shape {type(shape)}")

    if get_shape_type(shape) != "Vertex":
        bb = BoundingBox(shape, optimal=True)
        props["bb_min"] = (bb.xmin, bb.ymin, bb.zmin)
        props["bb_max"] = (bb.xmax, bb.ymax, bb.zmax)

    return props


# the panel's rows of a shape, in their order: (key of its properties, the row's label, how
# the value is shown)


def _radius_and_diameter(radius: float) -> str:
    return f"{radius:.3f} /  {2 * radius:.3f}"


def _angle_to_xy(direction) -> str:
    return with_supplement(angle_between(direction, (0, 0, 1)) / pi * 180)


def _edge_angle_to_xy(direction) -> str:
    return with_supplement(abs(90 - angle_between(direction, (0, 0, 1)) / pi * 180))


def _as_is(value):
    return value


_EDGE_GEOMETRY_ROWS = (
    ("center", "center", _as_is),
    ("radius", "radius / diam", _radius_and_diameter),
    ("major_radius", "major radius / diam", _radius_and_diameter),
    ("minor_radius", "minor radius / diam", _radius_and_diameter),
    ("offset", "offset", _as_is),
)
_EDGE_POSITION_ROWS = (
    ("start", "start", _as_is),
    ("vertex", "vertex", _as_is),
    ("middle", "middle", _as_is),
    ("end", "end", _as_is),
)
_EDGE_MEASURE_ROWS = (
    ("length", "length", _as_is),
    ("tangent_start", "angle@0 to XY", _edge_angle_to_xy),
    ("tangent_end", "angle@1 to XY", _edge_angle_to_xy),
)
_FACE_GEOMETRY_ROWS = (
    ("center", "center", _as_is),
    ("radius", "radius", _as_is),
    ("base_radius", "base radius", _as_is),
    ("half_angle", "half angle", _as_is),
    ("minor_radius", "minor radius", _as_is),
    ("major_radius", "major radius", _as_is),
    ("axis_location", "axe loc", _as_is),
    ("axis_direction", "axe dir", _as_is),
)
_FACE_MEASURE_ROWS = (
    ("area", "area", _as_is),
    ("normal", "angle to XY", _angle_to_xy),
)
_BODY_ROWS = (
    ("length", "length", _as_is),
    ("area", "area", _as_is),
    ("volume", "volume", _as_is),
)


def _section(props: ShapeProperties, rows) -> dict:
    return {label: show(props[key]) for key, label, show in rows if key in props}


def properties_response(kind: tuple[str, str], props: ShapeProperties) -> dict:
    """The properties tool's response, the panel's rows and sections, from what a kernel
    knows about a shape. Kernel-free: the same for OCCT and every plugin."""
    shape_type, geom_type = kind
    if shape_type == "Vertex":
        if "point" not in props:
            raise ValueError("the properties of a Vertex need 'point'")
        sections = [{"xyz": props["point"]}]
    elif shape_type == "Edge":
        sections = [_section(props, _EDGE_GEOMETRY_ROWS), _section(props, _EDGE_POSITION_ROWS), _section(props, _EDGE_MEASURE_ROWS)]
    elif shape_type == "Face":
        sections = [_section(props, _FACE_GEOMETRY_ROWS), _section(props, _FACE_MEASURE_ROWS)]
    else:
        sections = [_section(props, _BODY_ROWS)]
    sections = [section for section in sections if len(section) > 0]

    if "bb_min" in props and "bb_max" in props:
        low, high = props["bb_min"], props["bb_max"]
        size = [high[i] - low[i] for i in range(3)]
        sections.append(
            {
                "bb": {
                    "min": list(low),
                    "center": tuple(low[i] + size[i] / 2.0 for i in range(3)),
                    "max": list(high),
                    "size": size,
                }
            }
        )

    return {
        "shape_type": shape_type,
        "geom_type": "Revolution" if geom_type == "SurfaceOfRevolution" else geom_type,
        "refpoint": props["refpoint"],
        "result": sections,
    }


def get_properties(shape):
    """The properties tool's response for an OCCT shape."""
    return properties_response(occt_kind(shape), occt_properties(shape))


def get_center(shape):
    """The center of a shape as (x, y, z): of a circle, ellipse, hyperbola or
    parabola its location, of a cylinder, cone, sphere, torus or revolution
    surface the location of its axis, else the middle of an edge or the center
    of mass (of a wire, shell, solid, compsolid or compound by its highest
    dimension, see ocp_tessellate's center_of_mass)."""
    shape_type = get_shape_type(shape)
    geom_type = get_geom_type(shape)

    if shape_type == "Vertex":
        center = shape

    elif shape_type == "Edge":
        if geom_type == "Circle":
            circle = get_curve(shape).Circle()
            center = circle.Location()

        elif geom_type == "Ellipse":
            ellipse = get_curve(shape).Ellipse()
            center = ellipse.Location()

        elif geom_type == "Hyperbola":
            hyperbola = get_curve(shape).Hyperbola()
            center = hyperbola.Location()

        elif geom_type == "Parabola":
            parabola = get_curve(shape).Parabola()
            center = parabola.Location()

        else:
            center = position_at(shape, 0.5)

    elif shape_type == "Face":
        if geom_type == "Cylinder":
            cylinder = get_surface(shape).Cylinder()
            center = cylinder.Location()

        elif geom_type == "Cone":
            cone = get_surface(shape).Cone()
            center = cone.Location()

        elif geom_type == "Sphere":
            sphere = get_surface(shape).Sphere()
            center = sphere.Location()

        elif geom_type == "Torus":
            torus = get_surface(shape).Torus()
            center = torus.Location()

        elif geom_type == "SurfaceOfRevolution":
            revolution = get_surface(shape)
            center = revolution.AxeOfRevolution().Location()

        else:
            center = center_of_mass(shape)

    elif shape_type in ("Wire", "Shell", "Solid", "CompSolid", "Compound"):
        center = center_of_mass(shape)

    else:
        raise ValueError(f"no center for a shape of type {shape_type}: {shape}")

    # coordinates, not a vertex: a vertex built from a tuple would be in the
    # default binding, not necessarily in the shape's (center_of_mass returns
    # a tuple)
    if isinstance(center, tuple):
        return center
    return get_point(center)


def occt_closest_points(shape1, shape2):
    """The minimum distance of two OCCT shapes and the points it is taken between."""
    dist, p1, p2 = dist_shapes(downcast(shape1), downcast(shape2))
    return dist, get_point(p1), get_point(p2)


def occt_closest_directions(shape1, shape2):
    """The tangents of edges and normals of faces at the closest points of two OCCT shapes."""
    # edges or faces: `_angle_values` asks only for those, which downcast's type cannot say
    directions = closest_directions(downcast(shape1), downcast(shape2))  # ty: ignore[invalid-argument-type]
    if directions is None:
        return None
    return _xyz(directions[0]), _xyz(directions[1])


def _distance_values(shape1, shape2, center, center_of, closest_points):
    if center:
        p1 = center_of(shape=shape1)
        p2 = center_of(shape=shape2)
        if p1 is None or p2 is None:
            return None
        # the distance of two points, as BRepExtrema computes it for two vertices
        dx, dy, dz = p2[0] - p1[0], p2[1] - p1[1], p2[2] - p1[2]
        dist = sqrt(dx * dx + dy * dy + dz * dz)
    else:
        dist, p1, p2 = closest_points(shape1=shape1, shape2=shape2)
    return {
        "distance": dist,
        "⇒ X | Y | Z": [abs(p2[0] - p1[0]), abs(p2[1] - p1[1]), abs(p2[2] - p1[2])],
        "point 1": p1,
        "point 2": p2,
        "info": "center" if center else "min",
        "refpoint1": p1,
        "refpoint2": p2,
    }


def _direction_label(kind, shape_index):
    """What the direction of a shape is: a tangent or a normal."""
    shape_type, geom_type = kind
    if shape_type == "Edge":
        if geom_type == "Line":
            return "line"
        return f"tangent at P{shape_index}"
    if geom_type == "Plane":
        return "face normal"
    return f"surface normal at P{shape_index}"


def _angle_values(kind1, kind2, shape1, shape2, closest_directions):
    is_edge1 = kind1[0] == "Edge"
    is_edge2 = kind2[0] == "Edge"
    if not (is_edge1 or kind1[0] == "Face") or not (is_edge2 or kind2[0] == "Face"):
        return None

    # tangents of edges, normals of faces, at the closest points
    directions = closest_directions(shape1=shape1, shape2=shape2)
    if directions is None:
        return None
    dir1, dir2 = directions

    angle = angle_between(dir1, dir2) / pi * 180

    # If exactly one shape is an edge (tangent vs normal), convert to
    # edge-to-surface angle
    if is_edge1 != is_edge2:
        angle = abs(90 - angle)

    response = {"angle": angle}
    response["reference 1"] = _direction_label(kind1, 1)
    response["direction 1" if is_edge1 else "normal 1"] = dir1
    response["reference 2"] = _direction_label(kind2, 2)
    response["direction 2" if is_edge2 else "normal 2"] = dir2
    return response


def calc_distance(shape1, shape2, center=False):
    """The distance values of two OCCT shapes, None in the center mode if one has no center."""
    return _distance_values(shape1, shape2, center, occt_center, occt_closest_points)


def calc_angle(shape1, shape2):
    """The angle values of two OCCT shapes, None for anything but edges and faces."""
    return _angle_values(occt_kind(shape1), occt_kind(shape2), shape1, shape2, occt_closest_directions)


def get_distance(shape1, shape2, center):
    """The distance tool's response for two OCCT shapes."""
    return distance_response(shape1, shape2, center, occt_kind, occt_center, occt_closest_points, occt_closest_directions)


def distance_response(shape1, shape2, center, kind, center_of, closest_points, closest_directions):
    """The distance tool's response: the distance, the points, and the angle where there is
    one, from what a kernel gives. Kernel-free: `get_distance` passes this module's OCCT
    functions, the backend a kernel plugin's (`plugins.py`)."""
    dist = _distance_values(shape1, shape2, center, center_of, closest_points)
    if dist is None:
        # one row, without points there are no markers, as for shapes of two kernels
        return {"result": [{"distance": "not measured: a shape without a center"}], "refpoint1": None, "refpoint2": None}

    result = [
        {
            "distance": dist["distance"],
            "⇒ X | Y | Z": dist["⇒ X | Y | Z"],
            "info": dist["info"],
        },
        {
            "point 1": dist["point 1"],
            "point 2": dist["point 2"],
        },
    ]

    angle = _angle_values(kind(shape=shape1), kind(shape=shape2), shape1, shape2, closest_directions)

    if angle is not None:
        angle_section = {"angle": with_supplement(angle["angle"])}
        angle_section["reference 1"] = angle["reference 1"]
        if "direction 1" in angle:
            angle_section["direction 1"] = angle["direction 1"]
        if "normal 1" in angle:
            angle_section["normal 1"] = angle["normal 1"]
        angle_section["reference 2"] = angle["reference 2"]
        if "direction 2" in angle:
            angle_section["direction 2"] = angle["direction 2"]
        if "normal 2" in angle:
            angle_section["normal 2"] = angle["normal 2"]
        result.append(angle_section)

    return {
        "result": result,
        "refpoint1": dist["refpoint1"],
        "refpoint2": dist["refpoint2"],
    }
