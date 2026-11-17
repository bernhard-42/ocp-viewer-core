"""The center of a cylinder or cone face is the axis point at the face's middle.

Their `Location()` - what the Properties tool and the Distance tool's
center-to-center showed - is the origin of the surface's own coordinate system,
somewhere on an axis that is infinite: wherever the shape was built from. The
center is the face's center of mass projected onto the axis instead: the axis
point at mid-height for a full face, the center of curvature at mid-height for a
partial one (a fillet), whatever the placement. Sphere and torus keep their
`Location()`, which is fixed by their own geometry.
"""

import math

import build123d as bd
import pytest

from ocp_viewer_core.measure import occt_center, occt_properties


def centers(face):
    """What the Properties tool shows as center, and what center-to-center uses."""
    return occt_properties(face.wrapped)["center"], occt_center(face.wrapped)


def assert_center(face, expected):
    for value in centers(face):
        assert value == pytest.approx(expected, abs=1e-6)


@pytest.mark.parametrize("z", [-7.0, 0.0, 3.0], ids=["below", "origin", "above"])
def test_a_full_cylinder_is_centered_on_its_axis_at_mid_height(z):
    """The same cylinder, built at different heights: the center moves with it."""
    face = (bd.Pos(0, 0, z) * bd.Cylinder(10, 20)).faces().filter_by(bd.GeomType.CYLINDER)[0]
    assert_center(face, (0, 0, z))


def test_a_hole_is_centered_on_its_axis_at_mid_height():
    """`Hole` builds its cylinder from the top face down: Location() was z = 8."""
    part = bd.Box(30, 30, 16) - bd.Pos(5, 0, 8) * bd.Hole(4, depth=16)
    face = part.faces().filter_by(bd.GeomType.CYLINDER)[0]
    assert_center(face, (5, 0, 0))


def test_a_fillet_is_centered_on_its_axis_at_mid_height():
    """A quarter cylinder: its center of curvature, not a point near the surface."""
    part = bd.fillet(bd.Box(10, 10, 20).edges().filter_by(bd.Axis.Z).group_by(bd.Axis.X)[-1].sort_by(bd.Axis.Y)[-1], 2)
    face = part.faces().filter_by(bd.GeomType.CYLINDER)[0]
    assert_center(face, (3, 3, 0))


def test_a_rotated_cylinder_is_centered_on_its_axis():
    face = (bd.Rot(30, 40, 0) * bd.Pos(0, 0, 5) * bd.Cylinder(3, 10)).faces().filter_by(bd.GeomType.CYLINDER)[0]
    expected = (bd.Rot(30, 40, 0) * bd.Location((0, 0, 5))).position
    assert_center(face, tuple(expected))


def test_a_cone_is_centered_on_its_axis():
    """The cone's Location() is its reference plane (here the base at z = -7)."""
    cone = (bd.Pos(0, 0, 3) * bd.Cone(10, 4, 20)).faces().filter_by(bd.GeomType.CONE)[0]
    com = cone.center(bd.CenterOf.MASS)
    assert (com.X, com.Y) == pytest.approx((0, 0), abs=1e-9)
    assert com.Z != pytest.approx(-7)
    assert_center(cone, (0, 0, com.Z))


def test_a_torus_keeps_the_center_of_its_ring():
    """A fillet on a circular edge: the center of the circle the fillet follows."""
    part = bd.fillet((bd.Pos(0, 0, 3) * bd.Cylinder(10, 20)).edges().filter_by(bd.GeomType.CIRCLE), 2)
    bottom = part.faces().filter_by(bd.GeomType.TORUS).sort_by(bd.Axis.Z)[0]
    assert_center(bottom, (0, 0, -5))


def test_a_sphere_keeps_its_center():
    assert_center((bd.Pos(1, 2, 3) * bd.Sphere(4)).faces()[0], (1, 2, 3))


@pytest.mark.parametrize("rotation", [0.0, 30.0], ids=["along X", "rotated"])
def test_a_hyperbola_shows_its_vertex(rotation):
    """OCCT's Location() of a hyperbola is its center; the vertex is one major radius
    from it along the major axis, on the branch the edge is on."""
    edge = bd.HyperbolicCenterArc((10, 0), 3, 2, start_angle=-60, arc_size=120, rotation=rotation)
    a = math.radians(rotation)
    assert occt_properties(edge.wrapped)["vertex"] == pytest.approx((10 + 3 * math.cos(a), 3 * math.sin(a), 0), abs=1e-6)


def test_a_parabola_shows_its_vertex():
    edge = bd.ParabolicCenterArc((1, 2), 2, start_angle=-60, arc_size=120)
    assert occt_properties(edge.wrapped)["vertex"] == pytest.approx((1, 2, 0), abs=1e-6)


@pytest.mark.parametrize("x", [0.0, 40.0], ids=["origin", "moved"])
def test_a_planar_face_is_centered_at_its_center_of_mass(x):
    """A plane's Location() is the origin of the plane: for a box's top face a corner."""
    face = (bd.Pos(x, 0, 0) * bd.Box(10, 20, 30)).faces().sort_by(bd.Axis.Z)[-1]
    assert_center(face, (x, 0, 15))
