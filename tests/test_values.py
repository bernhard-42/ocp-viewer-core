"""The keys whose value must be one of a few named things.

three-cad-viewer drops an option it does not recognise without a word, so a
misspelt value has no symptom at all - `theme="drak"` is indistinguishable from
passing no theme. These tests exist because that silence is the whole reason
`validate_values` was added: nothing downstream will ever complain.

Two properties are checked, and the second matters as much as the first: every
value a caller is *told* to use has to pass. A validator that rejects a typo but
also rejects `Camera.BACK` would be worse than none.
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

import pytest

from ocp_viewer_core.comms import Comms, Session
from ocp_viewer_core.config import (
    ALLOWED_VALUES,
    AnalysisTool,
    Camera,
    Collapse,
    Config,
    StudioBackground,
    StudioTextureMapping,
    StudioToneMapping,
    UiTab,
)

# The enums a caller is handed, against the key each one belongs to. Written out
# rather than derived from ALLOWED_VALUES, so that a key losing its enum shows up
# here as a failure instead of as a test that quietly stops checking anything.
ENUM_KEYS = {
    "analysis_tool": AnalysisTool,
    "collapse": Collapse,
    "reset_camera": Camera,
    "tab": UiTab,
    "studio_background": StudioBackground,
    "studio_texture_mapping": StudioTextureMapping,
    "studio_tone_mapping": StudioToneMapping,
}

# The keys with no enum: three-cad-viewer's own sets, and the value it takes for
# each. Spelled out here rather than read from ALLOWED_VALUES, because a test
# that reads the table it is testing proves only that the table equals itself.
PLAIN_KEYS = {
    "theme": ("light", "dark", "browser"),
    "up": ("Z", "Y"),
    "zebra_color_scheme": ("blackwhite", "colorful", "grayscale"),
    "zebra_mapping_mode": ("reflection", "normal"),
}


class RecordingComms(Comms):
    """A transport that keeps what it was given instead of sending it."""

    def __init__(self):
        super().__init__()
        self.sent = []

    def send_config(self, config, timeit=False):
        self.sent.append(config)

    def send_command(self, data, timeit=False):
        return {}


@pytest.fixture
def config():
    return Config(Session(RecordingComms()), (), ())


# --------------------------------------------------------------------------- #
# What the table covers
# --------------------------------------------------------------------------- #


def test_every_validated_key_is_accounted_for():
    """No key is validated without this file saying what it accepts."""
    assert set(ALLOWED_VALUES) == set(ENUM_KEYS) | set(PLAIN_KEYS)


def test_studio_environment_is_deliberately_open():
    """It takes an enum member *or* a URL to a custom HDR map, so it is not a set."""
    assert "studio_environment" not in ALLOWED_VALUES


# --------------------------------------------------------------------------- #
# Everything a caller is told to use must pass
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("key,enum_class", sorted(ENUM_KEYS.items()))
def test_every_enum_member_passes(config, key, enum_class):
    for member in enum_class:
        config.validate_values({key: member})
        # and the bare value, since the docstrings say strings are accepted too
        config.validate_values({key: member.value})


@pytest.mark.parametrize("key,values", sorted(PLAIN_KEYS.items()))
def test_every_plain_value_passes(config, key, values):
    for value in values:
        config.validate_values({key: value})


def test_camera_back_is_rear(config):
    """The one enum whose name and value differ, and so the one most likely to
    be broken by a validator that compares against names."""
    assert Camera.BACK.value == "rear"
    config.validate_values({"reset_camera": Camera.BACK})
    config.validate_values({"reset_camera": "rear"})
    with pytest.raises(ValueError):
        config.validate_values({"reset_camera": "back"})


def test_collapse_takes_the_renderers_numbers(config):
    """Collapse's values are three-cad-viewer's CollapseState, not letters."""
    assert sorted(c.value for c in Collapse) == [-1, 0, 1, 2]
    for number in (-1, 0, 1, 2):
        config.validate_values({"collapse": number})


# --------------------------------------------------------------------------- #
# And a wrong value must not travel
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("key", sorted(ALLOWED_VALUES))
def test_an_unknown_value_raises(config, key):
    with pytest.raises(ValueError) as excinfo:
        config.validate_values({key: "definitely-not-a-value"})
    message = str(excinfo.value)
    assert key in message
    # the message has to say what to use instead - the point is that the
    # renderer would have said nothing at all
    assert all(repr(v) in message for v in ALLOWED_VALUES[key])


def test_a_near_miss_raises(config):
    """The reported case: one transposed letter, silently ignored before."""
    with pytest.raises(ValueError, match="theme='drak'"):
        config.validate_values({"theme": "drak"})


def test_up_is_not_settable_at_runtime():
    """It cannot be, so it must not claim to be.

    `Camera` reads its up direction once, when it is constructed, so assigning
    to a live viewer changes nothing - and the value the config carries is "Z"
    where that lookup is keyed by "z_up", so what it actually did was corrupt
    `presetCamera` and kill the next click on ISO or TOP.

    `Viewer.render` builds a new camera every time and honours `viewerOptions.up`,
    so it belongs there: `set_defaults(up=...)` and the next show.
    """
    from ocp_viewer_core import keys

    assert "up" in keys.ALL, "still a config key"
    assert "up" not in keys.SETTABLE, "but not one that can be set on a live viewer"


def test_the_legacy_up_is_gone(config):
    """three-cad-viewer still maps 'L' to its legacy orientation and may keep
    doing so; no host offers it any more."""
    with pytest.raises(ValueError):
        config.validate_values({"up": "L"})


# --------------------------------------------------------------------------- #
# What must not be validated
# --------------------------------------------------------------------------- #


def test_none_always_passes(config):
    """`None` means "not given" everywhere else and must mean it here."""
    for key in ALLOWED_VALUES:
        config.validate_values({key: None})


def test_unvalidated_keys_pass(config):
    config.validate_values(
        {"metalness": 0.3, "axes": True, "tree_width": 240, "default_color": "#ff0000"}
    )


def test_studio_environment_takes_a_url(config):
    config.validate_values({"studio_environment": "https://example.com/map.hdr"})


# --------------------------------------------------------------------------- #
# Reached from every entry point, not only when called directly
# --------------------------------------------------------------------------- #


def test_set_defaults_rejects(config):
    with pytest.raises(ValueError, match="theme"):
        config.set_defaults(theme="drak")


def test_set_viewer_config_rejects(config):
    with pytest.raises(ValueError, match="theme"):
        config.set_viewer_config(theme="drak")


def test_set_viewer_config_sends_a_good_value(config):
    config.set_viewer_config(theme="dark")
    assert config.session.comms.sent, "a valid value must still reach the viewer"


def test_a_rejected_call_sends_nothing(config):
    with pytest.raises(ValueError):
        config.set_viewer_config(theme="drak")
    assert not config.session.comms.sent


# --------------------------------------------------------------------------- #
# The other vocabulary: what a host stores in its settings
# --------------------------------------------------------------------------- #


def test_workspace_spellings_translate_to_valid_values(config, monkeypatch):
    """A host's settings speak a different vocabulary, and it must land here.

    `collapse` is stored as "leaves"/"root" or as "1"/"R", and `reset_camera` as
    "KEEP" - none of which is a value `validate_values` accepts. They are not
    meant to be: `workspace_config` translates them into `Collapse` and `Camera`
    first. This is the test that the two vocabularies actually meet, which is
    the only reason a host may store the other one.
    """
    for stored, expected in [
        ("none", Collapse.NONE),
        ("leaves", Collapse.LEAVES),
        ("all", Collapse.ALL),
        ("root", Collapse.ROOT),
        ("E", Collapse.NONE),
        ("1", Collapse.LEAVES),
        ("C", Collapse.ALL),
        ("R", Collapse.ROOT),
    ]:
        monkeypatch.setattr(
            config.session, "workspace_config", lambda s=stored: {"collapse": s}
        )
        translated = config.workspace_config()
        assert translated["collapse"] is expected
        config.validate_values(translated)

    for stored in ("RESET", "KEEP", "CENTER", "ISO", "TOP", "BOTTOM", "LEFT",
                   "RIGHT", "FRONT", "BACK"):
        monkeypatch.setattr(
            config.session, "workspace_config", lambda s=stored: {"reset_camera": s}
        )
        translated = config.workspace_config()
        assert isinstance(translated["reset_camera"], Camera)
        config.validate_values(translated)
