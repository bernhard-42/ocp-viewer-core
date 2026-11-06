"""Every measured angle the panel shows comes with its supplement.

The distance tool's angle and the properties tool's angles to XY answer the
panel, which prints a string as it is, so they go there as
"angle (180 - angle)" - vscode-ocp-cad-viewer issue 236. `calc_angle` stays
numeric for whoever computes with it, and a cone's half angle is a parameter
of the cone, not an angle between two directions, so it stays a number.
"""

from math import cos, pi, sin, sqrt

import build123d as bd
import pytest

from ocp_viewer_core import measure
from ocp_viewer_core.measure import calc_angle, get_distance, get_properties


def _angle_row(shape1, shape2):
    return get_distance(shape1.wrapped, shape2.wrapped, center=False)["result"][2]["angle"]


def test_perpendicular_lines_show_90_twice():
    assert _angle_row(bd.Line((0, 0, 0), (10, 0, 0)), bd.Line((0, 0, 0), (0, 10, 0))) == "90.000 (90.000)"


def test_60_degrees_show_their_supplement():
    line1 = bd.Line((0, 0, 0), (10, 0, 0))
    line2 = bd.Line((0, 0, 0), (5, 5 * sqrt(3), 0))
    assert _angle_row(line1, line2) == "60.000 (120.000)"


def test_calc_angle_stays_a_number():
    line1 = bd.Line((0, 0, 0), (10, 0, 0))
    line2 = bd.Line((0, 0, 0), (5, 5 * sqrt(3), 0))
    assert calc_angle(line1.wrapped, line2.wrapped)["angle"] == pytest.approx(60)


def test_a_vertex_has_no_angle_row():
    result = get_distance(bd.Vertex(5, 5, 0).wrapped, bd.Line((0, 0, 0), (10, 0, 0)).wrapped, center=False)["result"]
    assert len(result) == 2


def test_a_rounding_error_past_180_shows_no_negative_zero(monkeypatch):
    monkeypatch.setattr(measure, "angle_between", lambda dir1, dir2: 180.0000000001 / 180 * pi)
    row = _angle_row(bd.Line((0, 0, 0), (10, 0, 0)), bd.Line((0, 0, 0), (0, 10, 0)))
    assert row == "180.000 (0.000)"


def _property(shape, key):
    for section in get_properties(shape.wrapped)["result"]:
        if key in section:
            return section[key]
    raise KeyError(key)


def test_an_edge_shows_both_angles_to_xy_at_both_ends():
    line = bd.Line((0, 0, 0), (10 * cos(pi / 6), 0, 10 * sin(pi / 6)))
    assert _property(line, "angle@0 to XY") == "30.000 (150.000)"
    assert _property(line, "angle@1 to XY") == "30.000 (150.000)"


def test_a_face_shows_both_angles_to_xy():
    face = bd.Plane.XY.rotated((45, 0, 0)) * bd.Rectangle(10, 10)
    assert _property(face.faces()[0], "angle to XY") == "45.000 (135.000)"


def test_a_cones_half_angle_stays_a_number():
    cone = bd.Cone(5, 0, 10).faces().filter_by(bd.GeomType.CONE)[0]
    assert isinstance(_property(cone, "half angle"), float)
