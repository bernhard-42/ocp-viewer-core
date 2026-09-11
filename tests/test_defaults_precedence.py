"""The four levels of a config, and where the built-in defaults sit: underneath.

Level 1 is the host's stored config, level 2 the viewer's reported state, level
3 what `set_defaults` was told, level 4 a show's own keywords. `DEFAULT_DEFAULTS`
is the fallback under all of them - it used to be seeded into level 3 at
construction and applied last, so a stored `timeit` or `debug` could never take
effect (ocp-viewer's `--timeit`), and `collapse` had been carved out of the seed
one key at a time.
"""

import pytest
from ocp_viewer_core.comms import Comms, Session
from ocp_viewer_core.config import DEFAULT_DEFAULTS, Collapse, Config


class StoredComms(Comms[None]):
    """A host that stores a config and a viewer that reports a state, both settable."""

    def __init__(self):
        super().__init__()
        self.stored = {"_splash": False, "axes": False, "timeit": True, "debug": True, "collapse": Collapse.LEAVES}
        self.reported = {"axes": True}
        self.sent = []

    def workspace_config(self):
        return dict(self.stored)

    def status(self):
        return dict(self.reported)

    def send_config(self, config, timeit=False):
        self.sent.append(config)


@pytest.fixture(name="config")
def _config():
    return Config(Session(StoredComms()), exclude_keys=())


def test_a_stored_setting_shows_through_every_read(config):
    assert config.get_default("timeit") is True
    assert config.get_default("debug") is True
    assert config.get_changed_config("timeit") is True
    assert config.combined_config()["timeit"] is True
    assert config.get_defaults()["debug"] is True


def test_level_3_holds_only_what_set_defaults_was_told(config):
    assert config.defaults == {}
    config.set_defaults(timeit=False)
    assert config.defaults == {"timeit": False}
    assert config.get_default("timeit") is False, "set_defaults beats the stored setting"
    config.reset_defaults(apply=False)
    assert config.defaults == {}
    assert config.get_default("timeit") is True, "a reset returns to the stored setting, not to False"


def test_a_key_nobody_supplies_falls_back_to_the_table(config):
    for key in ("render_normals", "helper_scale", "show_locals"):
        assert config.get_default(key) == DEFAULT_DEFAULTS[key]
        assert config.combined_config()[key] == DEFAULT_DEFAULTS[key]
    config.reset_defaults(apply=False)
    assert config.get_default("show_locals") is True


def test_the_viewer_beats_the_store_and_set_defaults_beats_the_viewer(config):
    assert config.combined_config()["axes"] is True  # level 2 over level 1
    config.set_defaults(axes=False)
    assert config.combined_config()["axes"] is False  # level 3 over level 2
    config.reset_defaults(apply=False)
    assert config.combined_config()["axes"] is True


def test_while_the_splash_is_up_the_viewer_is_not_asked(config):
    config.session.comms.stored["_splash"] = True
    assert config.combined_config()["axes"] is False  # level 1, level 2 skipped
    assert config.get_defaults()["axes"] is False


def test_collapse_is_no_longer_a_special_case(config):
    # The stored setting takes effect at construction and after a reset, and the
    # table's ROOT is only what a host with no collapse setting gets.
    assert config.combined_config()["collapse"] == Collapse.LEAVES
    config.reset_defaults(apply=False)
    assert config.combined_config()["collapse"] == Collapse.LEAVES
    del config.session.comms.stored["collapse"]
    assert config.combined_config()["collapse"] == Collapse.ROOT


class ScopedComms(StoredComms):
    """Records the scope each config was sent under, as the transport sees it."""

    def send_config(self, config, timeit=False):
        self.sent.append((dict(self.keywords), config))


def test_reset_defaults_keeps_the_scope_it_was_called_in():
    # A host wrapper opens the scope - `reset_defaults(port=3939)` - and every
    # send the reset makes must happen inside it. It called `set_viewer_config`,
    # which opened a fresh scope with no port and cleared it in its finally, so
    # both sends went to whichever viewer discovery found.
    comms = ScopedComms()
    comms.stored["transparent"] = True
    session = Session(comms)
    config = Config(session, exclude_keys=())
    session.begin({"port": 3939})
    try:
        config.reset_defaults()
    finally:
        session.clear()
    assert len(comms.sent) == 2
    assert [scope for scope, _ in comms.sent] == [{"port": 3939}, {"port": 3939}]
