"""The agent's wire, in Python 1.2.0 so that the agent tools can come as patches.

Underscore methods on `Viewer`, not user API: they send the config keys and the
screenshot message the JavaScript half of 1.2.0 already understands
(`plans/agent-js-surface.md`, `plans/python-wire-1.2.md`).
"""

import pytest
from ocp_viewer_core import keys
from ocp_viewer_core.comms import Comms, Session
from ocp_viewer_core.config import Config
from ocp_viewer_core.show import Viewer

AGENT_KEYS = {
    "agent_highlight": "agentHighlight",
    "selection": "selection",
    "clear_selection": "clearSelection",
}


class RecordingComms(Comms[None]):
    def __init__(self):
        super().__init__()
        self.sent = []
        self.commands = []

    def workspace_config(self):
        return {"_splash": False}

    def status(self):
        return {}

    def send_config(self, config, timeit=False):
        self.sent.append(config)

    def send_command(self, data, timeit=False):
        self.commands.append(data)


@pytest.fixture(name="comms")
def _comms():
    return RecordingComms()


@pytest.fixture(name="viewer")
def _viewer(comms):
    return Viewer(Config(Session(comms), exclude_keys=()))


@pytest.mark.parametrize(("key", "js_name"), AGENT_KEYS.items())
def test_the_renderer_names(key, js_name):
    assert keys.ALL[key] == js_name
    assert keys.to_javascript({key: 1}) == {js_name: 1}


@pytest.mark.parametrize("key", AGENT_KEYS)
def test_actions_are_neither_configuration_nor_user_settable(key):
    assert key not in keys.CONFIG
    assert key not in keys.SETTABLE


def test_agent_highlight(viewer, comms):
    viewer._agent_highlight(["/box/edges/edges_1", "/plate"])
    assert comms.sent == [
        {"type": "ui", "config": {"agentHighlight": ["/box/edges/edges_1", "/plate"]}}
    ]


def test_agent_highlight_empty_clears(viewer, comms):
    viewer._agent_highlight([])
    assert comms.sent == [{"type": "ui", "config": {"agentHighlight": []}}]


def test_agent_select(viewer, comms):
    viewer._agent_select(("/box/faces/faces_3",))
    assert comms.sent == [{"type": "ui", "config": {"selection": ["/box/faces/faces_3"]}}]


def test_agent_clear_selection(viewer, comms):
    viewer._agent_clear_selection()
    assert comms.sent == [{"type": "ui", "config": {"clearSelection": True}}]


def test_agent_capture_sends_the_view(viewer, comms, tmp_path):
    target = tmp_path / "front.png"
    viewer._agent_capture(str(target), "front", ortho=True, clip=True, polling=False)
    assert comms.commands == [
        {"type": "screenshot", "filename": str(target), "view": "front", "ortho": True, "clip": True}
    ]


def test_agent_capture_defaults(viewer, comms, tmp_path):
    target = tmp_path / "iso.png"
    viewer._agent_capture(str(target), "iso", polling=False)
    assert comms.commands == [
        {"type": "screenshot", "filename": str(target), "view": "iso", "clip": False}
    ]


def test_agent_capture_refuses_an_unknown_view(viewer, comms, tmp_path):
    with pytest.raises(ValueError, match="sideways"):
        viewer._agent_capture(str(tmp_path / "x.png"), "sideways", polling=False)
    assert comms.commands == []


def test_save_screenshot_is_unchanged(viewer, comms, tmp_path):
    target = tmp_path / "plain.png"
    viewer.save_screenshot(str(target), polling=False)
    assert comms.commands == [{"type": "screenshot", "filename": str(target)}]
