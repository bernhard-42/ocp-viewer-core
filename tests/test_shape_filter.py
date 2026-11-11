"""`shape_filter`: three-cad-viewer 5.2's shape filter, set on a live viewer.

A user feature of `set_viewer_config` only. three-cad-viewer resets the filter
to "none" for every new model, so it is no show option, and it is kept out of
`keys.CONFIG`: the page reports it in its status, and `combined_config` must
not put a stale filter back over that reset.
"""

import inspect

import pytest
from ocp_viewer_core import keys
from ocp_viewer_core.comms import Comms, Session
from ocp_viewer_core.config import Config
from ocp_viewer_core.show import Viewer

VALUES = ("none", "vertex", "edge", "face", "solid")


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


def test_the_renderer_name():
    assert keys.to_javascript({"shape_filter": "edge"}) == {"shapeFilter": "edge"}


def test_settable_on_a_live_viewer_but_not_carried_into_the_next_show():
    assert "shape_filter" in keys.SETTABLE
    assert "shape_filter" not in keys.CONFIG


def test_set_viewer_config_takes_it():
    assert "shape_filter" in inspect.signature(Config.set_viewer_config).parameters


@pytest.mark.parametrize(
    "function", [Viewer.show, Viewer.show_object, Viewer.show_objects, Config.set_defaults]
)
def test_no_show_option(function):
    # A value given with a show would be reset by that same render.
    assert "shape_filter" not in inspect.signature(function).parameters


@pytest.mark.parametrize("value", VALUES)
def test_set_viewer_config_sends_the_value(config, comms, value):
    config.set_viewer_config(shape_filter=value)
    assert comms.sent == [{"type": "ui", "config": {"shapeFilter": value}}]


def test_an_unknown_value_is_refused(config, comms):
    with pytest.raises(ValueError, match="shape_filter='edges' is not valid"):
        config.set_viewer_config(shape_filter="edges")
    assert comms.sent == []


def test_a_reported_filter_is_not_put_back_by_the_next_show(config):
    assert "shape_filter" not in config.config_filter({"shape_filter": "edge", "axes": True})
