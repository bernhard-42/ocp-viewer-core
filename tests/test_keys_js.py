"""`js/src/keys.js` is generated from keys.py and config.py, and `settingsToConfig`
translates a host's settings the way Python does on its way to the viewer."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from ocp_viewer_core import _keys_js, keys
from ocp_viewer_core.config import COLLAPSE_NAME_MAPPING

ROOT = Path(__file__).resolve().parent.parent
KEYS_JS = ROOT / "js" / "src" / "keys.js"
SETTINGS_JS = ROOT / "js" / "src" / "settings.js"
NODE = shutil.which("node")

needs_node = pytest.mark.skipif(NODE is None, reason="needs node to run the JavaScript half")


def settings_to_config(settings):
    """`settingsToConfig(settings)`, run by node on the repository's file."""
    script = (
        f"import {{ settingsToConfig }} from {json.dumps(SETTINGS_JS.as_uri())};\n"
        f"process.stdout.write(JSON.stringify(settingsToConfig({json.dumps(settings)})));"
    )
    assert NODE is not None
    run = subprocess.run(
        [NODE, "--input-type=module", "-e", script], capture_output=True, text=True, check=True
    )
    return json.loads(run.stdout)


def test_keys_js_is_up_to_date():
    assert KEYS_JS.read_text() == _keys_js.module_text(), "js/src/keys.js is stale: run `make keys-js`"


# What a host pushes: the settings an open viewer reports in its status - only those
# would win over a changed setting at the next show - and can apply.
LIVE = sorted(set(keys.CONFIG) & set(keys.SETTABLE))


@needs_node
def test_every_live_setting_gets_pythons_name():
    settings = {key: 1 for key in LIVE if key not in _keys_js.value_names()}
    result = settings_to_config(settings)
    assert result["skipped"] == []
    assert result["config"] == keys.to_javascript(settings)


@needs_node
def test_collapse_names_are_converted_as_workspace_config_does():
    result = settings_to_config({"collapse": "leaves"})
    assert result == {"config": {"collapse": COLLAPSE_NAME_MAPPING["leaves"].value}, "skipped": []}


@needs_node
def test_what_an_open_viewer_does_not_report_or_cannot_take_is_skipped():
    """The next show applies these from the stored settings.

    `reset_camera` is not reported (a policy for the next show; applied live it would
    move the camera), `ticks` and `deviation` cannot be applied live, `sideways` is no
    collapse value."""
    result = settings_to_config(
        {"reset_camera": "keep", "ticks": 10, "deviation": 0.1, "pan_speed": 2, "collapse": "sideways"}
    )
    assert result["config"] == {"panSpeed": 2}
    assert sorted(result["skipped"]) == ["collapse", "deviation", "reset_camera", "ticks"]


@needs_node
@pytest.mark.parametrize("value", ["KEEP", "keep", "RESET", "iso"])
def test_reset_camera_is_skipped_in_any_spelling(value):
    """Not by accident of a spelling: it is not reported, so a host never needs to push it."""
    assert settings_to_config({"reset_camera": value}) == {"config": {}, "skipped": ["reset_camera"]}
