"""`show(builder, colors=..., alphas=...)` draws a build123d builder in that color and alpha.

`show` puts each alpha into its color before converting, and ocp-tessellate used
to drop the color of a builder - build123d's builders carry a `color` attribute
that is None until it is set - so the builder came out in its default color at
alpha 1.0 (ocp-tessellate's tests/test_builder_colors.py has the converter's side).
"""

from build123d import BuildSketch, Circle, Rectangle

from ocp_viewer_core.comms import Comms, Session
from ocp_viewer_core.config import Config
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


def leaves(parts):
    for part in parts:
        if "parts" in part:
            yield from leaves(part["parts"])
        else:
            yield part


def test_a_builder_takes_the_given_color_and_alpha_beside_a_sketch():
    with BuildSketch() as circle:
        Circle(1)
    with BuildSketch() as rect:
        Rectangle(1, 2)
    viewer = Viewer(Config(Session(SinkComms()), exclude_keys=()))
    viewer.show(
        circle, rect.sketch, names=["circle", "rect"], colors=["green", "red"], alphas=[0.5, 0.8], progress=None
    )
    drawn = {leaf["name"]: (leaf["color"], leaf["alpha"]) for leaf in leaves(viewer.comms.sent[-1]["data"]["shapes"]["parts"])}
    assert drawn == {
        "sketch": ("#008000", 0.5),
        # what the builder was built from, drawn faint on purpose
        "sketch_local": ("#008000", 0.2),
        "rect": ("#ff0000", 0.8),
    }
