"""When the two reads a show makes may be answered from memory, and when not.

`Session` caches `status()` and `workspace_config()` so that one show does not
ask the same question six times. The cache is scoped to that show and to
nothing else: outside one, a caller asking `status()` is asking what the viewer
looks like *now*, and an answer from the cache is the state before they touched
it.

That was reported from build123d Studio as "status() only reports stale values,
independent of what I set in the viewer UI" - the cache was emptied only at the
end of the *next* show, so it could be arbitrarily old.
"""

import pytest

from ocp_viewer_core.comms import Comms, Session


class CountingComms(Comms[None]):
    """A viewer whose state changes between questions, as a user's does."""

    def __init__(self):
        super().__init__()
        self.statuses = 0
        self.configs = 0

    def status(self):
        self.statuses += 1
        return {"axes": self.statuses % 2 == 1}

    def workspace_config(self):
        self.configs += 1
        return {"_splash": False, "reads": self.configs}


@pytest.fixture(name="session")
def _session():
    return Session(CountingComms())


def test_outside_a_show_every_question_reaches_the_viewer(session):
    first = session.status()
    second = session.status()
    assert first != second, "the second answer came from the cache"
    assert session.comms.statuses == 2


def test_the_same_holds_for_the_workspace_config(session):
    """A settings dialog can be open while Python sits at a prompt."""
    assert session.workspace_config() != session.workspace_config()
    assert session.comms.configs == 2


def test_inside_a_show_each_question_is_asked_once(session):
    """The reason the cache exists: `combined_config`, `_tessellate` and
    `get_changed_config` all ask, and a show used to open six connections."""
    session.begin({})
    try:
        assert session.status() == session.status()
        assert session.workspace_config() == session.workspace_config()
    finally:
        session.clear()

    assert (session.comms.statuses, session.comms.configs) == (1, 1)


def test_the_next_show_asks_again(session):
    """`_splash` is the case that proves it: true while the logo is up and false
    from the first model on, so an answer held across shows would keep forcing a
    camera reset and discard every explicit reset_camera."""
    for _ in range(2):
        session.begin({})
        session.status()
        session.clear()

    assert session.comms.statuses == 2


def test_a_show_does_not_inherit_an_answer_from_the_prompt(session):
    """The scope opens empty as well as closing empty. Measured before this:
    a show sent two commands from a fresh process and one after a direct
    status()."""
    session.status()
    session.begin({})
    try:
        session.status()
    finally:
        session.clear()

    assert session.comms.statuses == 2
