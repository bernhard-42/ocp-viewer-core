"""The Animation class: three.js keyframe tracks on the objects of the last show.

The JavaScript half was shared from the start - `js/src/animation.js` plays the
tracks in every host's page, and cad-viewer-widget calls the same `animate`.
This class is the Python half, ported from ocp_vscode where it stayed behind
during the core adoption: everything it needs was already here (`get_last_paths`
on the Viewer, the data and command channels on the session), only the class
still spoke ocp_vscode's transport.

Bound like the show family: the core `Viewer` carries an `animation()` factory,
and a host exports `Animation = viewer.animation` - so `Animation()` reads as a
constructor everywhere while the instance knows which viewer it animates.
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

import json
import tempfile
import time

from ocp_tessellate.utils import numpy_to_json
from PIL import Image


def _frame_times(n_frames, endpoint):
    """`n_frames` values from 0 to 1000, the counterpart of numpy's linspace.

    Written out so the class does not need numpy: `numpy_to_json` (an
    ocp-tessellate util) still handles numpy values a caller puts into tracks,
    but nothing here creates any.
    """
    if n_frames <= 0:
        return []
    if endpoint is True:
        if n_frames == 1:
            return [0.0]
        step = 1000.0 / (n_frames - 1)
    else:
        step = 1000.0 / n_frames
    return [i * step for i in range(n_frames)]


class Animation:
    """Class to create animations for the viewer"""

    def __init__(self, viewer, assembly=None):
        if assembly is not None:
            print("Deprecation: The parameter `assembly` is not needed any more\n")

        self._viewer = viewer
        self.tracks = []
        self.paths = viewer.get_last_paths()

        print(
            "Note: The paths for animation are only valid for the specific `show` statement"
            "\n(so do not change the objects between `show` and creating the Animation)."
            "\nAvailable paths:"
        )
        for p in self.paths:
            print(f"- {p}")

        self.max_duration = 0

    def add_track(self, path, action, times, values, animate_joints=False):
        # pylint: disable=line-too-long
        """
        Adding a three.js animation track.

        Parameters
        ----------
        path : string
            The path (or id) of the cad object for which this track is meant.
            Usually of the form `/top-level/level2/...`
        action : {"t", "tx", "ty", "tz", "q", "rx", "ry", "rz"}
            The action type:

            - "tx", "ty", "tz" for translations along the x, y or z-axis
            - "t" to add a position vector (3-dim array) to the current position of the CAD object
            - "rx", "ry", "rz" for rotations around x, y or z-axis
            - "q" to apply a quaternion to the location of the CAD object
        times : list of float or int
            An array of floats describing the points in time where CAD object (with id `path`) should be at the location
            defined by `action` and `values`
        values : list of float or int
            An array of same length as `times` defining the locations where the CAD objects should be according to the
            `action` provided. Formats:

            - "tx", "ty", "tz": float distance to move
            - "t": 3-dim tuples or lists defining the positions to move to
            - "rx", "ry", "rz": float angle in degrees
            - "q" quaternions of the form (x,y,z,w) the represent the rotation to be applied

        See also
        --------

        - [three.js NumberKeyframeTrack](https://threejs.org/docs/index.html?q=track#api/en/animation/tracks/NumberKeyframeTrack)
        - [three.js QuaternionKeyframeTrack](https://threejs.org/docs/index.html?q=track#api/en/animation/tracks/QuaternionKeyframeTrack)

        """
        if len(times) != len(values):
            raise ValueError("Parameters 'times' and 'values' need to have same length")

        if path not in self.paths:
            raise ValueError(f"Path '{path}' does not exist in assembly")

        self.tracks.append((path, action, times, values))

        if times[-1] > self.max_duration:
            self.max_duration = float(times[-1])

        if animate_joints is True:
            self.tracks.append((f"{path}.joints", action, times, values))

    def animate(self, speed):
        """Animate the tracks"""
        if self.max_duration == 0:
            raise RuntimeError("Use add_track to add animation tracks")

        data = {"data": self.tracks, "type": "animation", "config": {"speed": speed}}
        self._viewer.config.session.send_data(json.loads(numpy_to_json(data)))

    def set_relative_time(self, fraction, port=None):
        """
        Set the animation playback position.

        Parameters
        ----------
        fraction : float
            A value between 0 and 1 representing the relative position
            in the animation timeline (0 = start, 1 = end).
        port : int, optional
            The viewer to address, for a host that runs more than one
            (default=None).
        """
        self._viewer.config.session.begin({"port": port})
        try:
            self._viewer.comms.send_command(
                {"type": "set_relative_time", "value": float(fraction)}
            )
        finally:
            self._viewer.config.session.clear()

    def save_as_gif(
        self,
        output,
        fps=25,
        loops=0,
        endpoint=False,
        bg_color="white",
        pause=0.02,
    ):
        """
        Save the animation as a GIF file.

        Parameters
        ----------
        output : str
            The output file path for the GIF.
        fps : int, default=25
            Frames per second. GIF format stores frame delays in centiseconds
            (1/100s), so only certain fps values produce exact timing:

            - 10 fps → 100 ms/frame (exact)
            - 20 fps → 50 ms/frame (exact)
            - 25 fps → 40 ms/frame (exact)
            - 50 fps → 20 ms/frame (exact)
            - 100 fps → 10 ms/frame (exact)

            Other values like 30 fps (33.33 ms) or 60 fps (16.67 ms) will be
            rounded, causing the GIF to play faster or slower than expected.
        loops : int, default=0
            Number of times to loop the animation:

            - 0 = loop infinitely
            - N = play N times

            Note: Some viewers might ignore the loop settings for GIFs.
            Typically, web browsers respect the loop count.
        endpoint : bool, default=False
            Whether to include the final frame at t=1.0.
        bg_color : str, default="white"
            Background color for transparent areas.
        pause : float, default=0.02
            Delay in seconds between capturing frames (for rendering stability).
        """
        if fps not in [10, 20, 25, 50, 100]:
            print(
                "For exact duration in gif (using 1/100s), use fps 10, 20, 25, 50, or 100"
            )

        if loops == 0:
            loop = 0
        elif loops == 1:
            loop = None
        elif isinstance(loops, int) and loops > 1:
            loop = loops - 1
        else:
            raise ValueError(f"{loops} is not a positive integer or 0")

        n_frames = int(self.max_duration * fps)
        frame_duration = round(1000 / fps)

        print(n_frames, frame_duration)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            filename = tmp.name
            frames = []
            for i, t in enumerate(_frame_times(n_frames, endpoint)):
                self.set_relative_time(t / 1000)
                time.sleep(pause)
                self._viewer.save_screenshot(filename, progress_only=True)
                img = Image.open(filename)
                # Convert RGBA to RGB with a solid background to avoid
                # transparency issues
                if img.mode == "RGBA":
                    background = Image.new("RGB", img.size, bg_color)
                    background.paste(
                        img, mask=img.split()[3]
                    )  # Use alpha channel as mask
                    img = background
                else:
                    img = img.convert("RGB")
                frames.append(img)
                if i % 20 == 0:
                    print(f"{100 * i / n_frames:3.0f}%", end=" ")
            print()

            print("Saving animation ...")

            frames[0].save(
                output,
                save_all=True,
                append_images=frames[1:],
                duration=frame_duration,
                loop=loop,
            )
        print(f"Animation saved as {output}")
