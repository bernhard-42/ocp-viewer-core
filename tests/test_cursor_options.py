"""`cursor_pivot` and `zoom_to_cursor`: three-cad-viewer 5.2's rotation and zoom under the cursor."""

import inspect

import pytest
from ocp_viewer_core import keys
from ocp_viewer_core.comms import Comms, Session
from ocp_viewer_core.config import Config
from ocp_viewer_core.show import Viewer

OPTIONS = {"cursor_pivot": "cursorPivot", "zoom_to_cursor": "zoomToCursor"}


class RecordingComms(Comms[None]):
    def __init__(self):
        super().__init__()
        self.sent = []

    def workspace_config(self):
        return {"_splash": False}

    def status(self):
        return {}

    def send_config(self, config, timeit=False):
        self.sent.append(config)


@pytest.fixture(name="comms")
def _comms():
    return RecordingComms()


@pytest.fixture(name="config")
def _config(comms):
    return Config(Session(comms), exclude_keys=())


@pytest.mark.parametrize(("key", "js_name"), OPTIONS.items())
def test_the_renderer_name(key, js_name):
    assert keys.to_javascript({key: False}) == {js_name: False}


@pytest.mark.parametrize("key", OPTIONS)
def test_viewer_state_survives_into_the_next_show_and_can_be_set_live(key):
    assert key in keys.CONFIG
    assert key in keys.SETTABLE


@pytest.mark.parametrize("key", OPTIONS)
@pytest.mark.parametrize("function", [Viewer.show, Viewer.show_object, Viewer.show_objects, Config.set_defaults, Config.set_viewer_config])
def test_every_entry_point_takes_it(function, key):
    assert key in inspect.signature(function).parameters


@pytest.mark.parametrize("key", OPTIONS)
def test_set_defaults_is_what_a_show_reads(config, key):
    config.set_defaults(**{key: False})
    assert config.get_default(key) is False


@pytest.mark.parametrize(("key", "js_name"), OPTIONS.items())
def test_set_viewer_config_sends_the_value(config, comms, key, js_name):
    config.set_viewer_config(**{key: False})
    assert comms.sent == [{"type": "ui", "config": {js_name: False}}]
