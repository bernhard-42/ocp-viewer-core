"""`show` and `show_all` take objects of another kernel directly.

A kernel plugin registers with `ocp_tessellate.plugin.register_show`; a host then
needs no function of the plugin to show its objects, alone or beside OCCT objects.
"""

import numpy as np
import pytest
from build123d import Box
from ocp_tessellate._show_registry import _show_plugins
from ocp_tessellate.ocp_utils import BoundingBox
from ocp_tessellate.plugin import (
    CoordSystem,
    OcpObject,
    Placement,
    ShowProtocol,
    TessellationProtocol,
    register_show,
)

from ocp_viewer_core.backend import BackendProtocol, register_plugin
from ocp_viewer_core.comms import Comms, Session
from ocp_viewer_core.config import Config
from ocp_viewer_core.show import Viewer, is_drawable


class ToyPoint:
    """An object of a toy kernel, with a color of its own, which is the kernel's to read."""

    color = "red"


class ToyLocation:
    """An object of the toy kernel that becomes a coordinate system."""


class ToyFar:
    """An object of the toy kernel that spans 10 along x."""


class ToyAssembly:
    """A container of the toy kernel. Not iterable, and its `color` is no `Color`."""

    color = object()

    def __init__(self, links, at=None):
        self.links, self.at = links, at


AT_100 = Placement((100.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0))
AT_Y5 = Placement((0.0, 5.0, 0.0), (0.0, 0.0, 0.0, 1.0))


class ToySegment:
    def __init__(self, start, end):
        self.start, self.end = start, end


class Tessellation(TessellationProtocol):
    def tessellate(self, *args, **kwargs):
        raise AssertionError("the toy has no bodies")

    def discretize_edges(self, edges, deflection=0.1, shape_id=""):
        points = np.array([(e.start, e.end) for e in edges], dtype=np.float32)
        return {
            "edges": points.ravel(),
            "segments_per_edge": np.ones(len(points), dtype=np.int32),
            "edge_types": np.zeros(len(points), dtype=np.int32),
            "obj_vertices": points.reshape(-1, 3).ravel(),
        }

    def convert_vertices(self, vertices, shape_id=""):
        points = [p for v in vertices for p in ([(0, 0, 0), (10, 0, 0)] if isinstance(v, ToyFar) else [(0, 0, 0)])]
        return {"obj_vertices": np.array(points, dtype=np.float32).ravel()}

    def bounding_box(self, shape):
        items = shape if isinstance(shape, (list, tuple)) else [shape]
        if any(isinstance(item, ToyLocation) for item in items):
            raise TypeError("a location has no extent")
        if any(isinstance(item, ToySegment) for item in items):
            return BoundingBox({"xmin": 0, "xmax": 1, "ymin": 0, "ymax": 1, "zmin": 0, "zmax": 1})
        xmax = 10 if any(isinstance(item, ToyFar) for item in items) else 0
        return BoundingBox({"xmin": 0, "xmax": xmax, "ymin": 0, "ymax": 0, "zmin": 0, "zmax": 0})


class Show(ShowProtocol):
    def __init__(self):
        self.colors = []

    def is_object(self, obj):
        return isinstance(obj, (ToyPoint, ToyLocation, ToyFar, ToyAssembly, ToySegment))

    def line(self, start, end):
        return ToySegment(start, end)

    def serialize(self, shape):
        return b"toy"

    def convert(self, obj, name, color, alpha, helper_scale):
        self.colors.append(color)
        if isinstance(obj, ToyLocation):
            return CoordSystem(name, (0, 0, 0), (1, 0, 0), (0, 0, 1), size=helper_scale, like=obj)
        return OcpObject("vertex", [obj], name=name, color=color)

    def get_children(self, obj):
        return obj.links if isinstance(obj, ToyAssembly) else None

    def get_location(self, obj):
        return obj.at if isinstance(obj, ToyAssembly) else None


class Backend(BackendProtocol):
    """Nothing here is measured, but every kernel leaf has an entry in the model."""

    def deserialize(self, data):
        return data

    def moved(self, shape, placement):
        return shape

    def parts(self, shape):
        return [], [], []

    def kind(self, shape):
        return "Vertex", "Point"

    def center(self, shape):
        return 0, 0, 0

    def properties(self, shape):
        return {"refpoint": (0, 0, 0), "point": (0, 0, 0)}

    def closest_points(self, shape1, shape2):
        return 0.0, (0, 0, 0), (0, 0, 0)

    def closest_directions(self, shape1, shape2):
        return None


SHOW = Show()
register_show("toyshow", Tessellation(), SHOW, api=1)
register_plugin("toyshow", Backend(), api=1)


class SinkComms(Comms[None]):
    def __init__(self):
        super().__init__()
        self.sent = []

    def workspace_config(self):
        return {"_splash": False}

    def status(self):
        return {}

    def send_data(self, data, port=None, timeit=False):
        self.sent.append(data)

    def send_backend(self, data, port=None, timeit=False):
        pass


@pytest.fixture(name="viewer")
def _viewer():
    return Viewer(Config(Session(SinkComms()), ()))


def paths(viewer):
    """The tree paths of the model the viewer was sent last."""

    def walk(node):
        yield node["id"]
        for part in node.get("parts", []):
            yield from walk(part)

    return list(walk(viewer.comms.sent[-1]["data"]["shapes"]))


def test_show_takes_an_object_of_another_kernel(viewer):
    viewer.show(ToyPoint(), names=["point"])
    assert "/Group/point" in paths(viewer) or "/point" in paths(viewer)


def test_show_takes_it_beside_an_occt_object(viewer):
    viewer.show(ToyPoint(), Box(1, 1, 1), names=["point", "box"])
    shown = paths(viewer)
    assert any(path.endswith("/point") for path in shown)
    assert any(path.endswith("/box") for path in shown)


def test_show_takes_a_coordinate_system_of_another_kernel(viewer):
    viewer.show(ToyLocation(), names=["location"])
    assert any("location" in path for path in paths(viewer))


def test_show_takes_it_inside_a_list_beside_an_occt_object(viewer):
    viewer.show([ToyPoint(), Box(1, 1, 1)], names=["mixed"])
    assert any("mixed" in path for path in paths(viewer))


def test_a_relative_helper_scale_sees_the_converted_object(viewer):
    viewer.show(Box(1, 1, 1), ToyPoint(), names=["box", "point"], helper_scale=0.5)
    assert any(path.endswith("/point") for path in paths(viewer))


@pytest.mark.parametrize(
    "objects",
    [(ToyFar(),), ([ToyFar()],), ({"far": ToyFar()},)],
    ids=["top level", "list", "dict"],
)
def test_a_relative_helper_scale_measures_it_in_any_container(viewer, capsys, objects):
    """No "very small objects": the box of 10 x 0 x 0 gives a helper_scale of 2.5."""
    viewer.show(*objects, ToyLocation(), helper_scale=0.5)
    assert "Very small objects" not in capsys.readouterr().out


class NotDrawable:
    """No kernel owns it, and no plugin."""


@pytest.mark.parametrize(
    "objects",
    [lambda: (NotDrawable(),), lambda: ([NotDrawable()],)],
    ids=["directly", "in a list"],
)
def test_show_with_nothing_it_can_draw_says_so(viewer, capsys, objects):
    """Nothing is left to draw, so nothing is sent: the viewer keeps what it shows. The
    object itself is left out quietly, passed directly as in a list."""
    assert viewer.show(*objects()) is None
    out = capsys.readouterr().out
    assert "show: No CAD objects to show" in out
    assert "cannot draw" not in out
    assert viewer.comms.sent == []


@pytest.mark.parametrize(
    "objects",
    [lambda: (ToyPoint(), NotDrawable()), lambda: ([ToyPoint(), NotDrawable()],)],
    ids=["directly", "in a list"],
)
def test_show_draws_what_it_can_beside_an_object_nothing_can_draw(viewer, capsys, objects):
    viewer.show(*objects())
    out = capsys.readouterr().out
    assert "cannot draw" not in out
    assert "No CAD objects to show" not in out
    assert len(viewer.comms.sent[-1]["data"]["shapes"]["parts"]) == 1


def test_show_without_objects_says_so(viewer, capsys):
    """The same message as for objects nothing can draw."""
    assert viewer.show() is None
    assert "show: No CAD objects to show" in capsys.readouterr().out
    assert viewer.comms.sent == []


def test_show_all_leaves_it_out_of_a_scope(viewer):
    viewer.show_all({"point": ToyPoint(), "other": NotDrawable()})
    assert [p["name"] for p in viewer.comms.sent[-1]["data"]["shapes"]["parts"]] == ["point"]


def test_show_all_draws_the_rest_when_it_is_named_by_include(viewer, capsys):
    """Named by include, it is passed to show directly, and left out like any other."""
    viewer.show_all({"point": ToyPoint(), "other": NotDrawable()}, classes=[ToyPoint], include=["other"])
    assert "cannot draw" not in capsys.readouterr().out
    assert [p["name"] for p in viewer.comms.sent[-1]["data"]["shapes"]["parts"]] == ["point"]


def test_a_kernel_objects_own_color_is_left_to_its_plugin(viewer):
    """`show` makes a color of a CAD object's `color` attribute for OCCT objects; a plugin
    reads its object's color in `convert`, so it gets nothing here."""
    SHOW.colors.clear()
    viewer.show(ToyPoint(), names=["p"])
    assert SHOW.colors == [None]
    viewer.show(ToyPoint(), names=["p"], colors=["blue"])
    assert SHOW.colors[-1].web_color == "#0000ff"


def test_show_all_finds_it_in_a_scope(viewer):
    viewer.show_all({"point": ToyPoint(), "number": 1, "text": "x", "numbers": [1, 2]})
    shown = paths(viewer)
    assert any(path.endswith("/point") for path in shown)
    assert not any("number" in path or "text" in path for path in shown)


def test_show_all_draws_a_mixed_scope(viewer):
    viewer.show_all(
        {
            "point": ToyPoint(),
            "location": ToyLocation(),
            "box": Box(1, 1, 1),
            "points": [ToyPoint(), ToyPoint()],
        }
    )
    shown = paths(viewer)
    for name in ("point", "location", "box", "points"):
        assert any(name in path for path in shown), (name, shown)


def test_is_drawable_sees_it_inside_containers():
    assert is_drawable(ToyPoint())
    assert is_drawable([1, ToyPoint()])
    assert is_drawable({"a": ToyPoint()})
    assert not is_drawable([1, 2])
    assert not is_drawable({"a": "b"})


def test_show_object_takes_it(viewer):
    viewer.show_object(ToyPoint(), name="point")
    assert any(path.endswith("/point") for path in paths(viewer))


def assembly():
    return ToyAssembly([("far", ToyFar(), AT_Y5), ("sub", ToyAssembly([("p", ToyPoint(), None)]), None)], at=AT_100)


def part(node, path):
    if node["id"] == path:
        return node
    for child in node.get("parts", []):
        found = part(child, path)
        if found is not None:
            return found
    return None


def test_show_takes_a_container_of_another_kernel(viewer):
    viewer.show(assembly(), names=["top"])
    shown = paths(viewer)
    assert "/top/far" in shown and "/top/sub/p" in shown
    shapes = viewer.comms.sent[-1]["data"]["shapes"]
    assert shapes["loc"][0] == pytest.approx(AT_100[0])
    assert part(shapes, "/top/far")["loc"][0] == pytest.approx(AT_Y5[0])


def test_the_scene_box_of_a_container_holds_its_locations(viewer):
    viewer.show(assembly(), names=["top"])
    box = viewer.comms.sent[-1]["data"]["shapes"]["bb"]
    assert (box["xmin"], box["xmax"]) == pytest.approx((100, 110))


def test_show_takes_it_beside_an_occt_object_and_in_a_list(viewer):
    viewer.show(Box(1, 1, 1), [assembly()], names=["box", "list"])
    shown = paths(viewer)
    assert any(path.endswith("/box") for path in shown)
    assert any(path.endswith("/far") for path in shown)


def test_a_relative_helper_scale_measures_a_container(viewer, capsys):
    viewer.show(assembly(), ToyLocation(), names=["top", "loc"], helper_scale=0.5)
    assert "Very small objects" not in capsys.readouterr().out


def test_is_drawable_and_show_all_see_a_container(viewer):
    assert is_drawable(assembly()) is True
    top = assembly()
    viewer.show_all({"top": top})
    assert any(path.endswith("/top/far") for path in paths(viewer))


def test_a_serialize_that_fails_sends_nothing(viewer):
    """The show raises, and the viewer and the backend stay on the scene they had."""

    class Written:
        pass

    class Show2(Show):
        def is_object(self, obj):
            return isinstance(obj, Written)

        def convert(self, obj, name, color, alpha, helper_scale):
            return OcpObject("vertex", [obj], name=name)

        def serialize(self, shape):
            raise RuntimeError("the plugin's writer failed")

    class Tessellation2(Tessellation):
        def convert_vertices(self, vertices, shape_id=""):
            return {"obj_vertices": np.zeros(3, dtype=np.float32)}

        def bounding_box(self, shape):
            return BoundingBox({"xmin": 0, "xmax": 1, "ymin": 0, "ymax": 1, "zmin": 0, "zmax": 1})

    register_show("written", Tessellation2(), Show2(), api=1)
    try:
        with pytest.raises(RuntimeError, match="the plugin's writer failed"):
            viewer.show(Written())
        assert viewer.comms.sent == []
    finally:
        _show_plugins.pop("written")
