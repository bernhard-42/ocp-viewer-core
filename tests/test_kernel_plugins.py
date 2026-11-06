"""Kernel plugins of the measurement backend (`plugins.py`): the registry and its
entry point, the bodies' way onto the wire, and the backend answering for a plugin's
shapes beside OCCT's.

The plugin under test is `toy_kernel.py`, a kernel of points that registers itself
when imported, as a real plugin's package does."""

import base64
import importlib
import json
import sys
from importlib.metadata import EntryPoint

import orjson
import pytest
from build123d import Box, Location, Sphere
from ocp_tessellate.kernels import KERNEL_ENTRY_POINT_GROUP, encode_kernel_shapes
from ocp_tessellate.ocp_utils import (
    Placement,
    downcast,
    get_edges,
    loc_to_tq,
    serialize,
)
from ocp_tessellate.plugin import ShowProtocol, TessellationProtocol, register_show

from ocp_viewer_core import backend as backend_module
from ocp_viewer_core import measure as measure_module
from ocp_viewer_core import plugins
from ocp_viewer_core.backend import BackendProtocol, ViewerBackend, register_plugin
from ocp_viewer_core.codec import default
from ocp_viewer_core.comms import MessageType
from ocp_viewer_core.measure import (
    distance_response,
    get_distance,
    get_properties,
    occt_center,
    occt_properties,
    properties_response,
)
from ocp_viewer_core.plugins import (
    ENTRY_POINT_GROUP,
    backend_of,
    is_kernel_shape,
)

POINTS = [(0.0, 0.0, 0.0), (3.0, 4.0, 0.0)]


class _NothingDrawn(TessellationProtocol):
    def tessellate(self, *args, **kwargs):
        raise AssertionError("these tests draw nothing")

    def discretize_edges(self, *args, **kwargs):
        raise AssertionError("these tests draw nothing")

    def convert_vertices(self, *args, **kwargs):
        raise AssertionError("these tests draw nothing")

    def bounding_box(self, shape):
        raise AssertionError("these tests draw nothing")


class _ToySerializes(ShowProtocol):
    """The show side of the toy kernel: all these tests need of it is the bytes of a leaf."""

    def is_object(self, obj):
        return False

    def convert(self, obj, name, color, alpha, helper_scale):
        raise AssertionError("these tests draw nothing")

    def line(self, start, end):
        raise AssertionError("these tests draw nothing")

    def serialize(self, shape):
        return json.dumps(shape).encode("utf-8")


register_show("toy", _NothingDrawn(), _ToySerializes(), api=1)


@pytest.fixture
def unregistered():
    """No toy kernel yet, and afterwards the registry as it was: other test modules register
    their own plugins for the whole run."""
    saved = dict(plugins.PLUGINS)
    plugins.PLUGINS.pop("toy", None)
    sys.modules.pop("toy_kernel", None)
    yield
    plugins.PLUGINS.clear()
    plugins.PLUGINS.update(saved)
    sys.modules.pop("toy_kernel", None)


@pytest.fixture
def toy(unregistered):
    """The toy kernel registered, as its import does, and forgotten afterwards."""
    return importlib.import_module("toy_kernel")


def section(response, key):
    for s in response["result"]:
        if key in s:
            return s[key]
    raise KeyError(key)


def occt_entry(id_, shape):
    """A model entry as OcpObject.collect emits it for an OCCT solid (the instance)."""
    return {"id": id_, "shape": {"obj": shape, "cache_id": "x", "name": id_}, "loc": None}


def toy_entry(id_, points, loc=None):
    """A model entry as OcpObject.collect emits it for a kernel body."""
    return {"id": id_, "shape": {"kernel": "toy", "obj": points}, "loc": loc}


def on_the_wire(mapping):
    """The model as the backend receives it: the kernel pre-pass, the codec, JSON."""
    return orjson.loads(orjson.dumps(encode_kernel_shapes(mapping), default=default))


# ---------------------------------------------------------------------------
# the registry
# ---------------------------------------------------------------------------


def test_importing_the_plugin_registers_it(toy):
    assert backend_of("toy") is toy.BACKEND


def test_register_plugin_is_reachable_from_the_backend_module():
    from ocp_viewer_core import backend

    assert backend.register_plugin is register_plugin is plugins.register_plugin


def test_an_unknown_kernel_names_both_ways_to_register(unregistered, monkeypatch):
    monkeypatch.setattr(plugins, "entry_points", lambda group: [])
    with pytest.raises(LookupError, match=f"register_plugin.*'{ENTRY_POINT_GROUP}'"):
        backend_of("toy")


def test_the_entry_point_loads_the_plugin_in_a_process_that_never_imported_it(unregistered, monkeypatch):
    """The backend process of VS Code and Studio: nothing imported the plugin, the
    entry point named like the kernel does, and importing registers."""
    seen = []

    def fake_entry_points(group):
        seen.append(group)
        return [EntryPoint(name="toy", value="toy_kernel", group=group)]

    monkeypatch.setattr(plugins, "entry_points", fake_entry_points)
    assert "toy" not in plugins.PLUGINS
    plugin = backend_of("toy")
    assert seen == [ENTRY_POINT_GROUP]
    assert "toy_kernel" in sys.modules and plugin is sys.modules["toy_kernel"].BACKEND
    # registered now: the entry points are not consulted again
    monkeypatch.setattr(plugins, "entry_points", lambda group: pytest.fail("looked up twice"))
    assert backend_of("toy") is plugin


# ---------------------------------------------------------------------------
# the wire
# ---------------------------------------------------------------------------


def test_a_kernel_body_travels_as_base64_of_its_serialize_bytes(toy):
    box = Box(1, 2, 3).wrapped
    mapping = {"parts": [toy_entry("/scene/points", POINTS), {"parts": [occt_entry("/scene/group/box", box)]}]}
    encoded = encode_kernel_shapes(mapping)

    assert is_kernel_shape(encoded["parts"][0]["shape"])
    assert base64.b64decode(encoded["parts"][0]["shape"]["obj"]) == toy.serialize(POINTS)
    # the OCCT entry is the codec's, and untouched here
    assert encoded["parts"][1]["parts"][0]["shape"]["obj"] is box
    # the mapping given is not changed
    assert mapping["parts"][0]["shape"]["obj"] is POINTS

    model = on_the_wire(mapping)
    assert json.loads(base64.b64decode(model["parts"][0]["shape"]["obj"])) == [list(p) for p in POINTS]
    assert isinstance(model["parts"][1]["parts"][0]["shape"]["obj"], str)


# ---------------------------------------------------------------------------
# the backend
# ---------------------------------------------------------------------------


def _backend_with(toy, *entries):
    backend = ViewerBackend()
    backend.load_model(on_the_wire({"parts": list(entries)}))
    return backend


def test_the_backend_holds_a_plugin_body_beside_occt_shapes(toy):
    backend = _backend_with(
        toy, toy_entry("/points", POINTS, loc=((10.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0))), occt_entry("/box", Box(1, 2, 3).wrapped)
    )
    assert backend.model["/points"] == [(10.0, 0.0, 0.0), (13.0, 4.0, 0.0)]
    assert backend.model["/points/vertices/vertices_1"] == (13.0, 4.0, 0.0)
    assert backend.kernels["/points/vertices/vertices_1"] == "toy"
    assert "/box/faces/faces_5" in backend.model and backend.kernels["/box/faces/faces_5"] == "OCCT"


def test_a_plugin_may_name_its_shape_type(toy):
    class Named(toy.ToyBackend, BackendProtocol[list]):
        pass

    register_plugin("named", Named(), api=1)
    assert isinstance(backend_of("named"), BackendProtocol)
    assert backend_module.OcctBackend.__orig_bases__[0] is not BackendProtocol


def test_the_core_runs_a_plugins_sequence(toy, monkeypatch):
    """`deserialize`, `moved` with a real `Placement` and only when there is one, `parts`. The
    wire holds JSON lists; a plugin gets the type `BackendProtocol.moved` declares."""
    calls = []
    for name in ("deserialize", "moved", "parts"):
        original = getattr(toy.BACKEND, name)

        def spying(*args, name=name, original=original, **kwargs):
            calls.append((name, kwargs))
            return original(*args, **kwargs)

        monkeypatch.setattr(toy.BACKEND, name, spying)
    backend = _backend_with(
        toy, toy_entry("/at", POINTS, loc=((10.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0))), toy_entry("/origin", POINTS)
    )
    assert [name for name, _ in calls] == ["deserialize", "moved", "parts", "deserialize", "parts"]
    placement = calls[1][1]["placement"]
    assert isinstance(placement, Placement)
    assert placement == Placement((10.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0))
    assert backend.model["/at"] == [(10.0, 0.0, 0.0), (13.0, 4.0, 0.0)]
    assert backend.model["/origin"] == POINTS


def test_an_occt_shape_is_moved_by_the_placement_of_its_loc(toy):
    entry = occt_entry("/box", Box(1, 2, 3).wrapped)
    entry["loc"] = ((10.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0))
    backend = _backend_with(toy, entry)
    assert loc_to_tq(backend.model["/box"].Location())[0] == (10.0, 0.0, 0.0)


def test_the_tools_answer_for_either_kernel(toy):
    backend = _backend_with(toy, toy_entry("/points", POINTS), occt_entry("/box", Box(1, 2, 3).wrapped))

    backend.handle_event({"activeTool": "PropertiesMeasurement"}, MessageType.UPDATES)
    toy_response = backend.handle_event({"selectedShapeIDs": ["/points/vertices/vertices_1", "shift"]}, MessageType.UPDATES)
    assert toy_response["tool_type"] == "PropertiesMeasurement"
    assert toy_response["shape_type"] == "Vertex" and section(toy_response, "xyz") == (3.0, 4.0, 0.0)
    occt_response = backend.handle_event({"selectedShapeIDs": ["/box/faces/faces_0", "shift"]}, MessageType.UPDATES)
    assert occt_response["shape_type"] == "Face" and occt_response["geom_type"] == "Plane"

    backend.handle_event({"activeTool": "DistanceMeasurement"}, MessageType.UPDATES)
    response = backend.handle_event(
        {"selectedShapeIDs": ["/points/vertices/vertices_0", "/points/vertices/vertices_1", False]}, MessageType.UPDATES
    )
    assert response["tool_type"] == "DistanceMeasurement"
    assert response["result"][0]["distance"] == pytest.approx(5)
    assert len(response["result"]) == 2  # no angle for points
    assert response["refpoint1"] == (0.0, 0.0, 0.0)  # as the plugin returned it; JSON makes a list of it

    response = backend.handle_event({"selectedShapeIDs": ["/box/faces/faces_0", "/box/faces/faces_1", False]}, MessageType.UPDATES)
    assert response["result"][0]["distance"] == pytest.approx(1)
    assert "angle" in response["result"][2]


def test_a_distance_across_kernels_is_a_line_in_the_panel(toy):
    backend = _backend_with(toy, toy_entry("/points", POINTS), occt_entry("/box", Box(1, 2, 3).wrapped))
    backend.handle_event({"activeTool": "DistanceMeasurement"}, MessageType.UPDATES)
    response = backend.handle_event(
        {"selectedShapeIDs": ["/points/vertices/vertices_0", "/box/faces/faces_0", False]}, MessageType.UPDATES
    )
    assert response["result"] == [{"distance": "not measured: shapes of two kernels (toy, OCCT)"}]
    assert response["refpoint1"] is None and response["refpoint2"] is None
    assert orjson.dumps(response)


def test_a_leaf_without_a_plugin_installed_says_so_at_loading(unregistered, monkeypatch, capsys):
    monkeypatch.setattr(plugins, "entry_points", lambda group: [])
    backend = ViewerBackend()
    backend.load_model({"parts": [{"id": "/p", "shape": {"kernel": "toy", "obj": "W10="}, "loc": None}]})
    assert "no measurement backend plugin for kernel 'toy'" in capsys.readouterr().out
    assert backend.model == {}


def test_the_distance_response_is_assembled_from_a_plugins_functions(toy):
    response = distance_response(POINTS[0], POINTS[1], False, toy.kind, toy.center, toy.closest_points, toy.closest_directions)
    assert response["result"][0]["distance"] == pytest.approx(5) and len(response["result"]) == 2
    assert response["refpoint2"] == POINTS[1]


# ---------------------------------------------------------------------------
# the backend's output
# ---------------------------------------------------------------------------


def test_loading_a_model_says_nothing_registering_has_said(toy, capsys):
    capsys.readouterr()
    _backend_with(toy, toy_entry("/points", POINTS))
    assert capsys.readouterr().out == ""


def test_the_identifiers_are_logged_with_their_kernel(toy, capsys):
    backend = _backend_with(toy, toy_entry("/points", POINTS), occt_entry("/box", Box(1, 2, 3).wrapped))
    capsys.readouterr()

    backend.handle_event({"activeTool": "PropertiesMeasurement"}, MessageType.UPDATES)
    backend.handle_event({"selectedShapeIDs": ["/points/vertices/vertices_1", "shift"]}, MessageType.UPDATES)
    backend.handle_event({"selectedShapeIDs": ["/box/faces/faces_0", "shift"]}, MessageType.UPDATES)
    backend.handle_event({"activeTool": "DistanceMeasurement"}, MessageType.UPDATES)
    backend.handle_event(
        {"selectedShapeIDs": ["/points/vertices/vertices_0", "/points/vertices/vertices_1", False]}, MessageType.UPDATES
    )
    backend.handle_event({"selectedShapeIDs": ["/box/faces/faces_0", "/box/faces/faces_1", False]}, MessageType.UPDATES)
    backend.handle_event({"selectedShapeIDs": ["/points/vertices/vertices_0", "/box/faces/faces_0", False]}, MessageType.UPDATES)

    assert capsys.readouterr().out.splitlines() == [
        "toy identifier received '/points/vertices/vertices_1'",
        "OCCT identifier received '/box/faces/faces_0'",
        "toy identifiers received '/points/vertices/vertices_0', '/points/vertices/vertices_1'",
        "OCCT identifiers received '/box/faces/faces_0', '/box/faces/faces_1'",
        "toy/OCCT identifiers received '/points/vertices/vertices_0', '/box/faces/faces_0'",
    ]


def test_an_id_the_model_does_not_hold_is_logged_as_unknown(toy, capsys):
    backend = _backend_with(toy, toy_entry("/points", POINTS))
    capsys.readouterr()
    backend.handle_event({"activeTool": "PropertiesMeasurement"}, MessageType.UPDATES)
    backend.handle_event({"selectedShapeIDs": ["/nothing/faces/faces_0", "shift"]}, MessageType.UPDATES)
    # the error handler prints the KeyError after the line
    assert capsys.readouterr().out.splitlines()[0] == "unknown identifier received '/nothing/faces/faces_0'"



def test_occt_implements_the_protocol_and_round_trips():
    box = Box(1, 2, 3).wrapped
    occt = backend_module.OcctBackend()
    assert isinstance(occt, plugins.BackendProtocol)
    assert occt.deserialize(serialize(box)).ShapeType() == box.ShapeType()
    body = occt.moved(occt.deserialize(serialize(box)), Placement((10.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0)))
    faces, edges, vertices = occt.parts(body)
    assert len(faces) == 6 and len(edges) == 12 and len(vertices) == 8
    assert body.Location().Transformation().TranslationPart().X() == pytest.approx(10)


def test_a_registration_refuses_what_is_no_backend():
    with pytest.raises(TypeError, match="BackendProtocol"):
        register_plugin("wrong", object(), api=1)


@pytest.mark.parametrize("api", [0, 2])
def test_a_plugin_written_for_another_interface_is_refused(toy, api):
    with pytest.raises(ValueError, match="plugin interface"):
        register_plugin("from the future", toy.ToyBackend(), api=api)


def test_a_plugin_has_to_state_its_interface(toy):
    with pytest.raises(TypeError, match="api"):
        register_plugin("no api", toy.ToyBackend())


def test_registering_goes_to_stdout_and_says_when_it_replaces(toy, capsys):
    capsys.readouterr()
    register_plugin("twice", toy.ToyBackend(), api=1)
    register_plugin("twice", toy.ToyBackend(), api=1)
    out, err = capsys.readouterr()
    assert err == ""
    assert "Kernel plugin 'twice' registered for measuring" in out
    assert "Kernel plugin 'twice' re-registered for measuring" in out
    plugins.PLUGINS.pop("twice")


def test_the_lookup_error_lists_what_is_registered(toy, monkeypatch):
    monkeypatch.setattr(plugins, "entry_points", lambda group: [])
    with pytest.raises(LookupError, match=r"Registered: \[.*'toy'.*\]"):
        backend_of("other tag")


def test_each_package_reads_its_entry_point_group():
    assert plugins.ENTRY_POINT_GROUP == "ocp_viewer.kernels.backend"
    assert KERNEL_ENTRY_POINT_GROUP == "ocp_viewer.kernels.show"


def test_the_core_runs_a_plugin_by_keyword(toy, monkeypatch):
    """A plugin's parameter names are the interface."""

    class KeywordOnly(toy.ToyBackend):
        def deserialize(self, *, data):
            return toy.deserialize(data)

        def parts(self, *, shape):
            return toy.parts(shape)

        def moved(self, *, shape, placement):
            return toy.moved(shape, placement)

        def kind(self, *, shape):
            return toy.kind(shape)

        def center(self, *, shape):
            return toy.center(shape)

        def properties(self, *, shape):
            return toy.properties(shape)

        def closest_points(self, *, shape1, shape2):
            return toy.closest_points(shape1, shape2)

        def closest_directions(self, *, shape1, shape2):
            return None

    register_plugin("toy", KeywordOnly(), api=1)
    backend = _backend_with(toy, toy_entry("/points", POINTS, loc=((1.0, 0.0, 0.0), (0.0, 0.0, 0.0, 1.0))))
    backend.handle_event({"activeTool": "PropertiesMeasurement"}, MessageType.UPDATES)
    assert backend.handle_event({"selectedShapeIDs": ["/points", "shift"]}, MessageType.UPDATES)["shape_type"] == "Compound"
    backend.handle_event({"activeTool": "DistanceMeasurement"}, MessageType.UPDATES)
    ids = ["/points/vertices/vertices_0", "/points/vertices/vertices_1", False]
    assert backend.handle_event({"selectedShapeIDs": ids}, MessageType.UPDATES)["result"][0]["distance"] == pytest.approx(5)
    ids = ["/points/vertices/vertices_0", "/points/vertices/vertices_1", True]
    assert backend.handle_event({"selectedShapeIDs": ids}, MessageType.UPDATES)["result"][0]["distance"] == pytest.approx(5)


# ---------------------------------------------------------------------------
# the panel: the core makes it from what a kernel knows
# ---------------------------------------------------------------------------

AT = (1.0, 2.0, 3.0)
BOX = {"bb_min": (0.0, 0.0, 0.0), "bb_max": (2.0, 4.0, 6.0)}
BB = {"bb": {"min": [0.0, 0.0, 0.0], "center": (1.0, 2.0, 3.0), "max": [2.0, 4.0, 6.0], "size": [2.0, 4.0, 6.0]}}


def known(shape_type, geom_type, **rest):
    """What `kind` and `properties` of a kernel give."""
    return (shape_type, geom_type), {"refpoint": AT, **rest}


@pytest.mark.parametrize(
    ("answers", "sections"),
    [
        (known("Vertex", "Point", point=AT), [{"xyz": AT}]),
        (
            known("Edge", "Circle", center=AT, radius=2.0, start=AT, end=AT, length=3.0, tangent_start=(1.0, 0.0, 0.0), tangent_end=(0.0, 0.0, 1.0), **BOX),
            [{"center": AT, "radius / diam": "2.000 /  4.000"}, {"start": AT, "end": AT}, {"length": 3.0, "angle@0 to XY": "0.000 (180.000)", "angle@1 to XY": "90.000 (90.000)"}, BB],
        ),
        (
            known("Edge", "Ellipse", center=AT, major_radius=3.0, minor_radius=1.0, start=AT, length=1.0, **BOX),
            [{"center": AT, "major radius / diam": "3.000 /  6.000", "minor radius / diam": "1.000 /  2.000"}, {"start": AT}, {"length": 1.0}, BB],
        ),
        (known("Edge", "Hyperbola", start=AT, vertex=AT, end=AT, length=1.0, **BOX), [{"start": AT, "vertex": AT, "end": AT}, {"length": 1.0}, BB]),
        (known("Edge", "OffsetCurve", offset=0.5, start=AT, length=1.0, **BOX), [{"offset": 0.5}, {"start": AT}, {"length": 1.0}, BB]),
        (known("Edge", "Line", start=AT, middle=AT, end=AT, length=1.0, **BOX), [{"start": AT, "middle": AT, "end": AT}, {"length": 1.0}, BB]),
        (known("Face", "Plane", center=AT, area=2.0, normal=(0.0, 0.0, 1.0), **BOX), [{"center": AT}, {"area": 2.0, "angle to XY": "0.000 (180.000)"}, BB]),
        (known("Face", "Cylinder", center=AT, radius=2.0, area=2.0, **BOX), [{"center": AT, "radius": 2.0}, {"area": 2.0}, BB]),
        (known("Face", "Cone", center=AT, base_radius=2.0, half_angle=30.0, area=2.0, **BOX), [{"center": AT, "base radius": 2.0, "half angle": 30.0}, {"area": 2.0}, BB]),
        (known("Face", "Torus", center=AT, minor_radius=1.0, major_radius=5.0, area=2.0, **BOX), [{"center": AT, "minor radius": 1.0, "major radius": 5.0}, {"area": 2.0}, BB]),
        (known("Face", "BSplineSurface", area=2.0, **BOX), [{"area": 2.0}, BB]),
        (known("Wire", "Other", length=4.0, **BOX), [{"length": 4.0}, BB]),
        (known("Shell", "Other", area=4.0, **BOX), [{"area": 4.0}, BB]),
        (known("Solid", "Other", volume=4.0, **BOX), [{"volume": 4.0}, BB]),
        (known("Compound", "Other"), []),
    ],
)
def test_the_panels_rows_come_from_what_a_kernel_knows(answers, sections):
    response = properties_response(*answers)
    assert response["result"] == sections
    # the order of a section is the panel's order
    assert [list(s) for s in response["result"]] == [list(s) for s in sections]
    assert response["shape_type"] == answers[0][0] and response["refpoint"] == AT


def test_a_surface_of_revolution_is_named_for_the_panel():
    response = properties_response(*known("Face", "SurfaceOfRevolution", axis_location=AT, axis_direction=(0.0, 0.0, 1.0), area=1.0))
    assert response["geom_type"] == "Revolution"
    assert response["result"][0] == {"axe loc": AT, "axe dir": (0.0, 0.0, 1.0)}


def test_the_center_mode_measures_from_the_kernels_center():
    def closest_points(shape1, shape2):
        raise AssertionError("not asked in the center mode")

    response = distance_response(
        (0.0, 0.0, 0.0), (3.0, 4.0, 0.0), True, lambda shape: ("Vertex", "Point"), lambda shape: shape, closest_points, lambda **kwargs: None
    )
    assert response["result"][0]["distance"] == pytest.approx(5) and response["result"][0]["info"] == "center"
    assert response["refpoint2"] == (3.0, 4.0, 0.0)


@pytest.mark.parametrize(
    ("kinds", "angle", "labels"),
    [
        ((("Edge", "Line"), ("Edge", "Circle")), "90.000 (90.000)", {"reference 1": "line", "direction 1": (1.0, 0.0, 0.0), "reference 2": "tangent at P2", "direction 2": (0.0, 1.0, 0.0)}),
        ((("Face", "Plane"), ("Face", "Sphere")), "90.000 (90.000)", {"reference 1": "face normal", "normal 1": (1.0, 0.0, 0.0), "reference 2": "surface normal at P2", "normal 2": (0.0, 1.0, 0.0)}),
        ((("Edge", "Line"), ("Face", "Plane")), "0.000 (180.000)", {"reference 1": "line", "direction 1": (1.0, 0.0, 0.0), "reference 2": "face normal", "normal 2": (0.0, 1.0, 0.0)}),
    ],
)
def test_the_angle_section_comes_from_the_kinds_and_directions(kinds, angle, labels):
    of_shape = {id(SHAPE1): kinds[0], id(SHAPE2): kinds[1]}
    response = distance_response(
        SHAPE1, SHAPE2, False,
        lambda shape: of_shape[id(shape)],
        lambda shape: AT,
        lambda shape1, shape2: (1.0, AT, AT),
        lambda shape1, shape2: ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),
    )
    assert response["result"][2] == {"angle": angle, **labels}
    assert list(response["result"][2]) == ["angle", *labels]


SHAPE1, SHAPE2 = object(), object()


def test_a_body_has_no_angle_section_and_its_directions_are_not_asked():
    def closest_directions(shape1, shape2):
        raise AssertionError("not asked for a body")

    response = distance_response(
        SHAPE1, SHAPE2, False,
        lambda shape: ("Solid", "Other"),
        lambda shape: AT,
        lambda shape1, shape2: (1.0, AT, AT),
        closest_directions,
    )
    assert len(response["result"]) == 2


def test_a_degenerate_edge_answers_what_it_can():
    """A sphere's pole edge has no positions: the properties tool shows what it has, and the
    distance tool's minimum mode needs none of what is missing."""
    edges = [downcast(edge) for edge in get_edges(Sphere(3).wrapped)]
    poles = [edge for edge in edges if occt_properties(edge)["refpoint"] is None]
    seams = [edge for edge in edges if occt_properties(edge)["refpoint"] is not None]
    assert len(poles) == 2
    assert len(seams) > 0

    response = get_properties(poles[0])
    assert response["shape_type"] == "Edge"
    assert response["refpoint"] is None
    assert "length" in response["result"][0]

    distance = get_distance(poles[0], seams[0], center=False)
    assert distance["result"][0]["distance"] == pytest.approx(0.0, abs=1e-6)


# ---------------------------------------------------------------------------
# the second review
# ---------------------------------------------------------------------------


def test_the_distance_tool_asks_for_no_properties(toy, monkeypatch):
    """They take most of a second on a large solid, for a box the distance does not show."""

    def not_asked(*args, **kwargs):
        raise AssertionError("the distance tool does not need them")

    monkeypatch.setattr(toy.BACKEND, "properties", not_asked)
    backend = _backend_with(toy, toy_entry("/points", POINTS))
    backend.handle_event({"activeTool": "DistanceMeasurement"}, MessageType.UPDATES)
    ids = ["/points/vertices/vertices_0", "/points/vertices/vertices_1"]
    assert backend.handle_event({"selectedShapeIDs": [*ids, False]}, MessageType.UPDATES)["result"][0]["info"] == "min"
    assert backend.handle_event({"selectedShapeIDs": [*ids, True]}, MessageType.UPDATES)["result"][0]["info"] == "center"


def test_occts_distance_asks_for_no_properties(monkeypatch):
    def not_asked(*args, **kwargs):
        raise AssertionError("the distance tool does not need them")

    monkeypatch.setattr(measure_module, "occt_properties", not_asked)
    box1, box2 = Box(1, 1, 1).wrapped, Box(1, 1, 1).moved(Location((5, 0, 0))).wrapped
    assert get_distance(box1, box2, False)["result"][0]["distance"] == pytest.approx(4)
    assert get_distance(box1, box2, True)["result"][0]["distance"] == pytest.approx(5)


def test_a_shape_without_a_center_is_one_row_in_the_panel():
    response = distance_response(
        SHAPE1, SHAPE2, True,
        lambda shape: ("Edge", "OtherCurve"),
        lambda shape: None,
        lambda shape1, shape2: (1.0, AT, AT),
        lambda shape1, shape2: None,
    )
    assert response == {"result": [{"distance": "not measured: a shape without a center"}], "refpoint1": None, "refpoint2": None}


def test_occts_degenerate_edge_has_no_center():
    edges = [downcast(edge) for edge in get_edges(Sphere(3).wrapped)]
    poles = [edge for edge in edges if occt_properties(edge)["refpoint"] is None]
    assert occt_center(poles[0]) is None
    assert get_distance(poles[0], poles[1], center=True)["result"] == [{"distance": "not measured: a shape without a center"}]


def test_the_properties_of_a_vertex_need_its_point():
    with pytest.raises(ValueError, match="properties of a Vertex need 'point'"):
        properties_response(("Vertex", "Point"), {"refpoint": AT})


def test_half_a_box_has_no_row():
    response = properties_response(("Face", "Plane"), {"refpoint": AT, "area": 1.0, "bb_min": AT})
    assert response["result"] == [{"area": 1.0}]


@pytest.mark.parametrize("failure", ["unknown tag", "deserialize", "parts"])
def test_a_failing_leaf_takes_nothing_else_of_the_scene_with_it(toy, monkeypatch, capsys, failure):
    def raising(*args, **kwargs):
        raise RuntimeError("the plugin's bug")

    wire = on_the_wire(
        {"parts": [occt_entry("/box1", Box(1, 2, 3).wrapped), toy_entry("/points", POINTS), occt_entry("/box2", Box(1, 2, 3).wrapped)]}
    )
    if failure == "unknown tag":
        monkeypatch.setattr(plugins, "entry_points", lambda group: [])
        wire["parts"][1]["shape"]["kernel"] = "no such kernel"
    else:
        monkeypatch.setattr(toy.BACKEND, failure, raising)
    backend = ViewerBackend()
    backend.load_model(wire)

    assert "/box1/faces/faces_0" in backend.model
    assert "/box2/faces/faces_0" in backend.model
    assert "/points" not in backend.model
    assert "shape '/points' not loaded: " in capsys.readouterr().out


@pytest.mark.parametrize("tag", ["OCCT", ""])
def test_a_tag_that_names_no_plugin_is_refused(toy, tag):
    with pytest.raises(ValueError, match="no kernel tag"):
        register_plugin(tag, toy.ToyBackend(), api=1)
    assert tag not in plugins.PLUGINS


@pytest.mark.parametrize("api", [True, "1", None, 1.0])
def test_the_interface_version_has_to_be_an_int(toy, api):
    with pytest.raises(TypeError, match="api must be an int"):
        register_plugin("no int", toy.ToyBackend(), api=api)
    assert "no int" not in plugins.PLUGINS


def test_the_interface_version_a_plugin_stated_is_kept(toy):
    assert plugins.PLUGIN_APIS["toy"] == 1


def test_shape_properties_come_from_where_the_protocol_comes_from():
    assert backend_module.ShapeProperties is plugins.ShapeProperties
