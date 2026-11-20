"""Two `show` keywords as documented.

`progress=None` is "no progress indicator", but `none_filter` dropped the None
before `show` saw it, so the default progress was printed. `modes=Render.FACES`
is what the docstring recommends instead of `render_edges`, but only a list
worked: a single mode failed with "object of type 'Render' has no len()".
"""

import build123d as bd
import pytest

from ocp_viewer_core.comms import Comms, Session
from ocp_viewer_core.config import Config, Render
from ocp_viewer_core.show import Viewer


class SinkComms(Comms[None]):
    """A host whose viewer reports nothing, with a model sink."""

    def __init__(self):
        super().__init__()
        self.sent = []

    def workspace_config(self):
        return {"_splash": False}

    def status(self):
        return {}

    def send_data(self, data, port=None, timeit=False):
        self.sent.append(data)

    def send_backend(self, data, port=None, timeit=False):
        pass

    def send_config(self, config, timeit=False):
        pass


@pytest.fixture(name="viewer")
def fixture_viewer():
    return Viewer(Config(Session(SinkComms()), exclude_keys=()))


def leaves(parts):
    for part in parts:
        if "parts" in part:
            yield from leaves(part["parts"])
        else:
            yield part


def progress_lines(out):
    """The lines of `out` made only of progress marks: + new, c from the cache, - and *."""
    return [line for line in out.splitlines() if line.strip() and set(line.strip()) <= set("+-*c")]


def states(viewer):
    return [leaf["state"] for leaf in leaves(viewer.comms.sent[-1]["data"]["shapes"]["parts"])]


def test_progress_none_prints_no_progress(viewer, capsys):
    viewer.show(bd.Box(1, 1, 1), progress=None)
    assert progress_lines(capsys.readouterr().out) == []


def test_progress_none_in_show_object_prints_no_progress(viewer, capsys):
    viewer.reset_show()
    viewer.show_object(bd.Box(1, 1, 1), progress=None)
    assert progress_lines(capsys.readouterr().out) == []


def test_the_default_progress_is_still_printed(viewer, capsys):
    viewer.show(bd.Box(1, 1, 1))
    assert len(progress_lines(capsys.readouterr().out)) == 1


def test_a_single_mode_applies_to_every_object(viewer):
    viewer.show(bd.Box(1, 1, 1), bd.Pos(3, 0, 0) * bd.Box(1, 1, 1), modes=Render.FACES, progress="")
    assert states(viewer) == [[1, 0], [1, 0]]


def test_a_list_of_modes_still_works(viewer):
    viewer.show(bd.Box(1, 1, 1), bd.Pos(3, 0, 0) * bd.Box(1, 1, 1), modes=[Render.EDGES, Render.ALL], progress="")
    assert states(viewer) == [[0, 1], [1, 1]]
