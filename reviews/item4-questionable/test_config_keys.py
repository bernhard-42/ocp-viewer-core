"""The config key table holds itself to the renderer's own naming.

ocp_vscode derives JS names with a `toCamelCase` plus three hand-kept overrides, and
three-cad-viewer publishes the authoritative pairing in `src/core/viewer-state.ts`.
Those two drifted: `studio_ao_intensity` was sent as `studioAoIntensity` where the
renderer calls it `studioAOIntensity`, so that option did nothing and said nothing.

These tests exist so the next drift is a failure rather than a silence.
"""

import json
import pathlib
import re
import tomllib

import pytest

ROOT = pathlib.Path(__file__).parent.parent
TABLE = ROOT / "ocp_viewer_core" / "config_keys.toml"
NOTIFICATIONS = ROOT / "tests" / "fixtures" / "three_cad_viewer_notifications.json"

GROUPS = {
    "",
    "DisplayOptions",
    "RenderOptions",
    "ViewerOptions",
    "StudioModeOptions",
    "ZebraOptions",
}
ROLES = {"option", "tessellation", "action", "command", "diagnostic", "tree-state"}
KINDS = {"state", "event"}


@pytest.fixture(scope="module")
def rows():
    return tomllib.loads(TABLE.read_text())["key"]


@pytest.fixture(scope="module")
def renderer_names():
    """snake_case python name -> camelCase renderer name."""
    pairs = json.loads(NOTIFICATIONS.read_text())
    return {snake: camel for camel, snake in pairs.items()}


def test_table_parses_and_is_not_empty(rows):
    assert len(rows) > 50


def test_every_python_name_is_unique(rows):
    names = [r["python"] for r in rows]
    assert len(names) == len(set(names))


def test_every_js_name_is_unique(rows):
    """Two python keys mapping to one JS name means one of them silently wins."""
    seen = {}
    for r in rows:
        seen.setdefault(r["js"], []).append(r["python"])
    assert {js: py for js, py in seen.items() if len(py) > 1} == {}


def test_js_names_are_option_fields_of_the_renderer(rows, option_fields):
    """`js` is the name the renderer accepts as an *option*.

    Not the same axis as the notification table: `tab` goes in as `viewerOptions.tab`
    (viewer.ts:1797), becomes the internal state key `activeTab`, and is reported back
    as `tab` again. Validating option names against the notification table conflates
    the two and produces a wrong answer for exactly that key.
    """
    wrong = [r["python"] for r in rows if r["role"] == "option" and r["js"] not in option_fields]
    assert wrong == [], f"js name is not an option field of any renderer interface: {wrong}"


def test_reportable_keys_come_back_under_their_python_name(rows, renderer_names):
    """The check that would have caught studioAOIntensity.

    For every key the renderer reports, the wire name it uses must be the python
    name - that is what makes the round trip symmetric for the host.
    """
    wrong = {
        r["python"]: renderer_names[r["python"]]
        for r in rows
        if r["reportable"] and renderer_names.get(r["python"]) is None
    }
    assert wrong == {}, f"reportable but not in the renderer's notification table: {wrong}"


def test_reportable_matches_the_renderer(rows, renderer_names):
    """`reportable` is measured from the renderer, never hand-maintained."""
    for r in rows:
        assert r["reportable"] == (r["python"] in renderer_names), r["python"]


def test_groups_roles_and_kinds_are_from_the_known_sets(rows):
    for r in rows:
        assert r["group"] in GROUPS, r
        assert r["role"] in ROLES, r
        assert r["kind"] in KINDS, r


def test_a_renderer_group_is_set_exactly_when_the_renderer_consumes_it(rows):
    for r in rows:
        if r["role"] in ("tessellation", "tree-state"):
            assert r["group"] == "", f"{r['python']} is not a renderer option"


def test_actions_are_events(rows):
    """An action must never be accumulated into a status snapshot.

    Activating a tool or selecting a tab is something that happened, not something
    that is. Replaying one from an accumulated snapshot re-fires it - which is the
    shape of the stale-selection bug build123d Studio already fixed once.
    """
    for r in rows:
        if r["role"] == "action":
            assert r["kind"] == "event", r["python"]


def test_reportable_events_are_declared_as_such(rows):
    """A key can be an event *and* be reported back, and `tab` is the proof.

    Sending `tab` selects a tab - an action - while the viewer reports the current
    tab as part of its state. So "events are not reportable" is false, and the rule
    that matters is narrower: an event may appear in a status snapshot but must never
    be *replayed* from one, or a later show re-fires it. Any such key carries
    `replayable = false` so the show path can filter on data rather than on a name
    somebody remembered.
    """
    for r in rows:
        if r["kind"] == "event":
            assert r.get("replayable") is False, (
                f"{r['python']} is an event; it must declare replayable = false "
                "whether or not the renderer reports it back"
            )


def test_camel_case_is_the_rule_and_exceptions_are_declared(rows):
    """Anything the mechanical transform cannot produce must say so in a comment."""
    mechanical = lambda s: re.sub(r"_([a-z0-9])", lambda m: m.group(1).upper(), s)
    text = TABLE.read_text()
    for r in rows:
        if r["js"] != mechanical(r["python"]):
            line = f'js = "{r["js"]}"'
            idx = text.find(line)
            assert idx != -1, r["python"]
            eol = text.find("\n", idx)
            assert "#" in text[idx:eol], (
                f"{r['python']} -> {r['js']} is not the mechanical transform "
                "and carries no comment saying why"
            )
