"""What `Animation.add_track` refuses, and that numpy is a number too.

The checks used to live in cad-viewer-widget, on the far side of the
transport and against the tree the browser had reported - which under "Run
All Cells" had not arrived when the animation cell ran. They live here now,
once, for every host.
"""

import numpy as np
import pytest
from ocp_viewer_core.animation import Animation


class PathsOnly:
    """The one thing an Animation asks its viewer for at construction."""

    def get_last_paths(self):
        return ["/base", "/base/disk", "/base/arm"]


@pytest.fixture(name="animation")
def _animation(capsys):
    a = Animation(PathsOnly())
    capsys.readouterr()  # the path listing
    return a


def test_a_scalar_track_from_numpy(animation):
    animation.add_track("/base/disk", "rz", np.linspace(0, 5, 3), np.linspace(0, 360, 3))
    assert len(animation.tracks) == 1
    assert animation.max_duration == 5.0


def test_a_vector_track_from_lists_tuples_and_numpy_rows(animation):
    animation.add_track("/base/arm", "t", [0, 1], [[0, 0, 0], (1, 2, 3)])
    animation.add_track("/base/arm", "q", [0, 1], np.array([[0, 0, 0, 1], [0, 0, 1, 0]]))
    assert len(animation.tracks) == 2


def test_the_raw_class_names_the_bound_import():
    """`from ocp_viewer_core.animation import Animation` then `Animation(assembly)`
    is the wrong translation of a host's import; say so instead of failing on
    `get_last_paths` inside the assembly."""

    class Assembly:
        pass

    with pytest.raises(TypeError, match="Got Assembly instead of a viewer"):
        Animation(Assembly())
    with pytest.raises(TypeError, match="Got no argument instead of a viewer"):
        Animation()


def test_an_unknown_path_is_refused(animation):
    with pytest.raises(ValueError, match="does not exist"):
        animation.add_track("/base/leg", "rz", [0, 1], [0, 90])


def test_an_unknown_action_is_refused(animation):
    with pytest.raises(ValueError, match="not one of"):
        animation.add_track("/base/disk", "spin", [0, 1], [0, 90])


def test_lengths_must_agree(animation):
    with pytest.raises(ValueError, match="same length"):
        animation.add_track("/base/disk", "rz", [0, 1, 2], [0, 90])


def test_scalar_values_must_be_numbers(animation):
    with pytest.raises(ValueError, match="numbers"):
        animation.add_track("/base/disk", "rz", [0, 1], [0, "ninety"])


def test_vector_values_must_have_the_action_size(animation):
    with pytest.raises(ValueError, match="3-dim"):
        animation.add_track("/base/arm", "t", [0, 1], [[0, 0], [1, 1]])
    with pytest.raises(ValueError, match="4-dim"):
        animation.add_track("/base/arm", "q", [0, 1], [[0, 0, 0], [0, 0, 1]])


def test_times_must_be_numbers(animation):
    with pytest.raises(ValueError, match="'times'"):
        animation.add_track("/base/disk", "rz", ["0", "1"], [0, 90])
