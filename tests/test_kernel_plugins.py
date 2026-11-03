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
from build123d import Box

from ocp_viewer_core import backend as backend_module
from ocp_viewer_core import plugins
from ocp_viewer_core.backend import ViewerBackend, register_plugin
from ocp_viewer_core.codec import default
from ocp_viewer_core.comms import MessageType
from ocp_viewer_core.measure import distance_response
from ocp_viewer_core.plugins import (
    ENTRY_POINT_GROUP,
    encode_kernel_shapes,
    is_kernel_shape,
    plugin_of,
)

POINTS = [(0.0, 0.0, 0.0), (3.0, 4.0, 0.0)]


@pytest.fixture
def toy():
    """The toy kernel registered, as its import does, and forgotten afterwards."""
    sys.modules.pop("toy_kernel", None)
    module = importlib.import_module("toy_kernel")
    yield module
    plugins.PLUGINS.clear()
    sys.modules.pop("toy_kernel", None)


@pytest.fixture
def unregistered():
    plugins.PLUGINS.clear()
    sys.modules.pop("toy_kernel", None)
    yield
    plugins.PLUGINS.clear()
    sys.modules.pop("toy_kernel", None)


def section(response, key):
    for s in response["result"]:
        if key in s:
            return s[key]
    raise KeyError(key)


def occt_entry(id_, shape):
    """A model entry as OcpObject.collect emits it for an OCCT solid (the instance)."""
    return {"id": id_, "shape": {"obj": shape, "cache_id": "x", "name": id_}, "loc": None}


def toy_entry(id_, points, loc=None):
    """A model entry as OcpExternalObject.collect would emit it for a kernel body."""
    return {"id": id_, "shape": {"kernel": "toy", "obj": points}, "loc": loc}


def on_the_wire(mapping):
    """The model as the backend receives it: the kernel pre-pass, the codec, JSON."""
    return orjson.loads(orjson.dumps(encode_kernel_shapes(mapping), default=default))


# ---------------------------------------------------------------------------
# the registry
# ---------------------------------------------------------------------------


def test_importing_the_plugin_registers_it(toy):
    plugin = plugin_of("toy")
    assert plugin.kernel == "toy"
    assert plugin.serialize is toy.serialize and plugin.load is toy.load
    assert plugin.get_properties is toy.get_properties
    assert plugin.calc_distance is toy.calc_distance and plugin.calc_angle is toy.calc_angle


def test_register_plugin_is_reachable_from_the_backend_module():
    from ocp_viewer_core import backend

    assert backend.register_plugin is register_plugin is plugins.register_plugin


def test_an_unknown_kernel_names_both_ways_to_register(unregistered, monkeypatch):
    monkeypatch.setattr(plugins, "entry_points", lambda group: [])
    with pytest.raises(LookupError, match=f"register_plugin.*'{ENTRY_POINT_GROUP}'"):
        plugin_of("toy")


def test_the_entry_point_loads_the_plugin_in_a_process_that_never_imported_it(unregistered, monkeypatch):
    """The backend process of VS Code and Studio: nothing imported the plugin, the
    entry point named like the kernel does, and importing registers."""
    seen = []

    def fake_entry_points(group):
        seen.append(group)
        return [EntryPoint(name="toy", value="toy_kernel", group=group)]

    monkeypatch.setattr(plugins, "entry_points", fake_entry_points)
    assert "toy" not in plugins.PLUGINS
    plugin = plugin_of("toy")
    assert seen == [ENTRY_POINT_GROUP]
    assert plugin.kernel == "toy" and "toy_kernel" in sys.modules
    # registered now: the entry points are not consulted again
    monkeypatch.setattr(plugins, "entry_points", lambda group: pytest.fail("looked up twice"))
    assert plugin_of("toy") is plugin


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
    assert backend.plugins["/points/vertices/vertices_1"].kernel == "toy"
    assert "/box/faces/faces_5" in backend.model and backend.plugins["/box/faces/faces_5"] is None


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


def test_a_model_without_a_plugin_installed_fails_at_loading_with_the_message(unregistered, monkeypatch):
    monkeypatch.setattr(plugins, "entry_points", lambda group: [])
    backend = ViewerBackend()
    with pytest.raises(LookupError, match="no measurement backend plugin for kernel 'toy'"):
        backend.load_model({"parts": [{"id": "/p", "shape": {"kernel": "toy", "obj": "W10="}, "loc": None}]})


def test_the_distance_response_is_assembled_from_a_plugins_functions(toy):
    response = distance_response(POINTS[0], POINTS[1], False, toy.calc_distance, toy.calc_angle)
    assert response["result"][0]["distance"] == pytest.approx(5) and len(response["result"]) == 2
    assert response["refpoint2"] == POINTS[1]


# ---------------------------------------------------------------------------
# the backend's output
# ---------------------------------------------------------------------------


@pytest.fixture
def unannounced(monkeypatch):
    """A process that has announced no plugin yet."""
    monkeypatch.setattr(backend_module, "_ANNOUNCED_KERNELS", set())


def test_a_plugin_is_announced_once_per_process(toy, unannounced, capsys):
    _backend_with(toy, toy_entry("/points", POINTS))
    assert capsys.readouterr().out.splitlines() == ["Measurement plugin for kernel 'toy' loaded (toy_kernel)"]
    # a second model, and a backend of its own (Jupyter CadQuery makes one per show)
    _backend_with(toy, toy_entry("/points", POINTS))
    assert capsys.readouterr().out == ""


def test_the_identifiers_are_logged_with_their_kernel(toy, unannounced, capsys):
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


def test_an_id_the_model_does_not_hold_is_logged_as_unknown(toy, unannounced, capsys):
    backend = _backend_with(toy, toy_entry("/points", POINTS))
    capsys.readouterr()
    backend.handle_event({"activeTool": "PropertiesMeasurement"}, MessageType.UPDATES)
    backend.handle_event({"selectedShapeIDs": ["/nothing/faces/faces_0", "shift"]}, MessageType.UPDATES)
    # the error handler prints the KeyError after the line
    assert capsys.readouterr().out.splitlines()[0] == "unknown identifier received '/nothing/faces/faces_0'"

