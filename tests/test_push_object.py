"""push_object keeps a registry of named objects for show_objects; `update` replaces in place."""

import pytest
from ocp_viewer_core.comms import Comms, Session
from ocp_viewer_core.config import Config
from ocp_viewer_core.show import Viewer


class NoComms(Comms[None]):
    """push_object touches the registry only; nothing is sent."""


@pytest.fixture(name="viewer")
def _viewer():
    return Viewer(Config(Session(NoComms()), exclude_keys=()))


def test_a_pushed_object_is_registered(viewer):
    viewer.push_object("a", name="first", color="red")
    assert viewer.objects["names"] == ["first"]
    assert viewer.objects["objs"] == ["a"]
    assert viewer.objects["colors"] == ["red"]
    assert viewer.objects["alphas"] == [1.0]


def test_update_replaces_in_place(viewer):
    viewer.push_object("a", name="first")
    viewer.push_object("b", name="second")
    viewer.push_object("a2", name="first", color="blue", update=True)
    assert viewer.objects["names"] == ["first", "second"]
    assert viewer.objects["objs"] == ["a2", "b"]
    assert viewer.objects["colors"] == ["blue", None]


def test_update_of_an_unknown_name_adds_it(viewer):
    """The guard from vscode-ocp-cad-viewer PR #238: `update=True` for a name that
    was never pushed used to raise ValueError from `list.index`."""
    viewer.push_object("a", name="first")
    viewer.push_object("b", name="second", update=True)
    assert viewer.objects["names"] == ["first", "second"]
    assert viewer.objects["objs"] == ["a", "b"]


def test_a_name_comes_from_the_object_when_not_given(viewer):
    class Named:
        name = "from_attr"

    class Labelled:
        label = "from_label"

    viewer.push_object(Named())
    viewer.push_object(Labelled())
    assert viewer.objects["names"] == ["from_attr", "from_label"]
    with pytest.raises(ValueError, match="No name provided"):
        viewer.push_object(object())
