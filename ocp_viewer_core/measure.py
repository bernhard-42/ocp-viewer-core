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


def get_properties(shape):
    shape = downcast(shape)
    shape_type = get_shape_type(shape)
    geom_type = get_geom_type(shape)

    refpoint = None
    sections = []

    # The dispatch repeats get_shape_type's tests rather than comparing its
    # string: the predicates are TypeIs, so each branch holds the exact
    # TopoDS subtype its calls require. `is_vector` is not repeated - nothing
    # wrapped survives the downcast above.
    if is_topods_vertex(shape):
        pt = get_point(shape)
        refpoint = pt
        sections.append({"xyz": pt})

    elif is_topods_edge(shape):
        geom_section = {}
        pos_section = {}

        if geom_type == "Line":
            pos_section["start"] = get_point(position_at(shape, 0))
            pos_section["middle"] = get_point(position_at(shape, 0.5))
            pos_section["end"] = get_point(position_at(shape, 1))
            refpoint = get_point(position_at(shape, 0.5))

        elif geom_type == "Circle":
            circle = get_curve(shape).Circle()
            geom_section["center"] = get_point(circle.Location())
            geom_section["radius / diam"] = (
                f"{circle.Radius():.3f} /  {2 * circle.Radius():.3f}"
            )
            pos_section["start"] = get_point(position_at(shape, 0))
            if not is_closed(shape):
                pos_section["end"] = get_point(position_at(shape, 1))
                refpoint = get_point(position_at(shape, 0.5))
            else:
                refpoint = get_point(position_at(shape, 0))

        elif geom_type == "Ellipse":
            ellipse = get_curve(shape).Ellipse()
            geom_section["center"] = get_point(ellipse.Location())
            geom_section["major radius / diam"] = (
                f"{ellipse.MajorRadius():.3f} /  {2 * ellipse.MajorRadius():.3f}"
            )
            geom_section["minor radius / diam"] = (
                f"{ellipse.MinorRadius():.3f} /  {2 * ellipse.MinorRadius():.3f}"
            )
            pos_section["start"] = get_point(position_at(shape, 0))
            if not is_closed(shape):
                pos_section["end"] = get_point(position_at(shape, 1))
                refpoint = get_point(position_at(shape, 0.5))
            else:
                refpoint = get_point(position_at(shape, 0))

        elif geom_type == "Hyperbola":
            hyperbola = get_curve(shape).Hyperbola()
            pos_section["start"] = get_point(position_at(shape, 0))
            pos_section["vertex"] = get_point(hyperbola.Location())
            pos_section["end"] = get_point(position_at(shape, 1))
            refpoint = get_point(position_at(shape, 0.5))

        elif geom_type == "Parabola":
            parabola = get_curve(shape).Parabola()
            pos_section["start"] = get_point(position_at(shape, 0))
            pos_section["vertex"] = get_point(parabola.Location())
            pos_section["end"] = get_point(position_at(shape, 1))
            refpoint = get_point(position_at(shape, 0.5))

        elif geom_type in ["Bezier", "Bspline"]:
            pos_section["start"] = get_point(position_at(shape, 0))
            pos_section["middle"] = get_point(position_at(shape, 0.5))
            pos_section["end"] = get_point(position_at(shape, 1))
            refpoint = get_point(position_at(shape, 0.5))

        elif geom_type == "OffsetCurve":
            offset = get_curve(shape).OffsetCurve()
            geom_section["offset"] = offset.Offset()
            pos_section["start"] = get_point(position_at(shape, 0))
            if is_closed(shape):
                pos_section["end"] = get_point(position_at(shape, 1))
            refpoint = get_point(position_at(shape, 0))

        else:
            pos_section["start"] = get_point(position_at(shape, 0))
            pos_section["middle"] = get_point(position_at(shape, 0.5))
            pos_section["end"] = get_point(position_at(shape, 1))
            refpoint = get_point(position_at(shape, 0.5))

        if geom_section:
            sections.append(geom_section)
        if pos_section:
            sections.append(pos_section)

        meas_section = {"length": length(shape)}
        for i in [0, 1]:
            try:
                _, tangent_dir = tangent_at(shape, i)
                angle = abs(90 - angle_between(tangent_dir, (0, 0, 1)) / pi * 180)
                meas_section[f"angle@{i} to XY"] = with_supplement(angle)
            # An angle that cannot be computed is left out of the section
            # rather than failing the measurement.
            except Exception:  # noqa: BLE001, S110
                pass
        sections.append(meas_section)

    elif is_topods_face(shape):
        geom_section = {}

        if geom_type == "Plane":
            plane = get_surface(shape).Plane()
            geom_section["center"] = get_point(plane.Location())

        elif geom_type == "Cylinder":
            cylinder = get_surface(shape).Cylinder()
            geom_section["center"] = get_point(cylinder.Location())
            geom_section["radius"] = cylinder.Radius()

        elif geom_type == "Cone":
            cone = get_surface(shape).Cone()
            geom_section["center"] = get_point(cone.Location())
            geom_section["base radius"] = cone.RefRadius()
            geom_section["half angle"] = cone.SemiAngle() / pi * 180

        elif geom_type == "Sphere":
            sphere = get_surface(shape).Sphere()
            geom_section["center"] = get_point(sphere.Location())
            geom_section["radius"] = sphere.Radius()

        elif geom_type == "Torus":
            torus = get_surface(shape).Torus()
            geom_section["center"] = get_point(torus.Location())
            geom_section["minor radius"] = torus.MinorRadius()
            geom_section["major radius"] = torus.MajorRadius()

        elif geom_type == "SurfaceOfRevolution":
            revolution = get_surface(shape)
            geom_section["axe loc"] = get_point(
                revolution.AxeOfRevolution().Location()
            )
            # A direction, deliberately - the label says so. `get_point` reads
            # X(), Y() and Z() and nothing else, which gp_Dir has; its
            # annotation is narrower than what it actually requires.
            geom_section["axe dir"] = get_point(
                revolution.AxeOfRevolution().Direction()  # ty: ignore[invalid-argument-type]
            )
            geom_type = "Revolution"

        # Two unimplemented cases rather than one: they are separate pieces of
        # work, and collapsing them into one branch would hide that.
        elif geom_type == "Bezier":  # noqa: SIM114
            ...

        elif geom_type == "Bspline":
            ...

        if geom_section:
            sections.append(geom_section)

        refpoint = center_of_geometry(shape)

        meas_section = {"area": area(shape)}
        try:
            normal = face_normal(shape)
            if normal is not None:
                a = angle_between(normal, (0, 0, 1)) / pi * 180
                meas_section["angle to XY"] = with_supplement(a)
        # As above: the angle is one line of a report, not the report.
        except Exception:  # noqa: BLE001, S110
            pass
        sections.append(meas_section)

    elif is_topods_wire(shape):
        sections.append({"length": length(shape)})
        refpoint = center_of_mass(shape)

    elif is_topods_shell(shape):
        sections.append({"area": area(shape)})
        refpoint = center_of_mass(shape)

    elif (
        is_topods_solid(shape)
        or is_topods_compsolid(shape)
        or is_topods_compound(shape)
    ):
        sections.append({"volume": volume(shape)})
        refpoint = center_of_mass(shape)

    else:
        print(f"unknown shape {type(shape)}")

    if shape_type != "Vertex":
        bb = BoundingBox(shape, optimal=True)
        sections.append({
            "bb": {
                "min": [bb.xmin, bb.ymin, bb.zmin],
                "center": bb.center,
                "max": [bb.xmax, bb.ymax, bb.zmax],
                "size": [bb.xsize, bb.ysize, bb.zsize],
            }
        })

    return {
        "shape_type": shape_type,
        "geom_type": geom_type,
        "refpoint": refpoint,
        "result": sections,
    }


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


def calc_distance(shape1, shape2, center=False):
    shape1 = downcast(shape1)
    shape2 = downcast(shape2)

    if center:
        p1 = get_center(shape1)
        p2 = get_center(shape2)
        # the distance of two points, as BRepExtrema computes it for two vertices
        dx, dy, dz = p2[0] - p1[0], p2[1] - p1[1], p2[2] - p1[2]
        dist = sqrt(dx * dx + dy * dy + dz * dz)
    else:
        dist, p1, p2 = dist_shapes(shape1, shape2)
        p1 = get_point(p1)
        p2 = get_point(p2)
    xdist = abs(p2[0] - p1[0])
    ydist = abs(p2[1] - p1[1])
    zdist = abs(p2[2] - p1[2])
    return {
        "distance": dist,
        "⇒ X | Y | Z": [xdist, ydist, zdist],
        "point 1": p1,
        "point 2": p2,
        "info": "center" if center else "min",
        "refpoint1": p1,
        "refpoint2": p2,
    }


def _direction_label(shape, shape_index):
    """What the direction of a shape in calc_angle is: a tangent or a normal."""
    if is_topods_edge(shape):
        if get_geom_type(shape) == "Line":
            return "line"
        return f"tangent at P{shape_index}"
    if get_geom_type(shape) == "Plane":
        return "face normal"
    return f"surface normal at P{shape_index}"


def calc_angle(shape1, shape2):
    shape1 = downcast(shape1)
    shape2 = downcast(shape2)

    is_edge1 = is_topods_edge(shape1)
    is_face1 = is_topods_face(shape1)
    is_edge2 = is_topods_edge(shape2)
    is_face2 = is_topods_face(shape2)

    if not (is_edge1 or is_face1) or not (is_edge2 or is_face2):
        return None

    # tangents of edges, normals of faces, at the closest points
    directions = closest_directions(shape1, shape2)
    if directions is None:
        return None
    dir1, dir2 = directions
    info1 = _direction_label(shape1, 1)
    info2 = _direction_label(shape2, 2)

    angle = angle_between(dir1, dir2) / pi * 180

    # If exactly one shape is an edge (tangent vs normal), convert to
    # edge-to-surface angle
    if is_edge1 != is_edge2:
        angle = abs(90 - angle)

    def _dir_tuple(d):
        return (d.X(), d.Y(), d.Z())

    response = {"angle": angle}

    response["reference 1"] = info1
    if is_edge1:
        response["direction 1"] = _dir_tuple(dir1)
    else:
        response["normal 1"] = _dir_tuple(dir1)

    response["reference 2"] = info2
    if is_edge2:
        response["direction 2"] = _dir_tuple(dir2)
    else:
        response["normal 2"] = _dir_tuple(dir2)

    return response


def get_distance(shape1, shape2, center):
    """The distance tool's response for two OCCT shapes."""
    return distance_response(shape1, shape2, center, calc_distance, calc_angle)


def distance_response(shape1, shape2, center, calc_distance, calc_angle):
    """The distance tool's response: the distance, the points, and the angle where
    there is one, from a kernel's `calc_distance(shape1, shape2, center)` and
    `calc_angle(shape1, shape2)`. Kernel-free: `get_distance` passes this module's
    OCCT functions, the backend a kernel plugin's (`plugins.py`)."""
    dist = calc_distance(shape1, shape2, center)

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

    angle = calc_angle(shape1, shape2)

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
