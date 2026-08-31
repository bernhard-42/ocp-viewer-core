"""Host-neutral utilities: the camera warnings and the shader ball.

`from ocp_viewer_core.utils import ignore_camera_warnings` matches where
ocp_vscode's utils kept it; `create_shader_ball` is the shader ball for
material demonstrations. The core is a dependency of every viewer, so
nothing per host is needed and no host binds these names at package level.

Built with build123d, which the core deliberately does not depend on - the
pyproject names no CAD library for the same reason it names no OCP provider,
because the host or the user chooses. The import is inside the function,
deliberately: this module is imported by the package `__init__`, so a
top-level import would make every `import ocp_viewer_core` - and with it
every host - require build123d, crashing a cadquery-only environment.
Calling `create_shader_ball` is the statement "I have build123d"; importing
never is.
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

import warnings

__all__ = [
    "camera_keep_warning",
    "create_shader_ball",
    "ignore_camera_warnings",
]


# ============================ Warnings ============================ #
#
# These stay module-level rather than becoming instance state, and deliberately:
# `warnings` is a process-wide registry, and "warn once per session" means once
# per process. Two Viewers in one process warning twice about the same thing
# would be a regression, not isolation. Contrast the show state in `show.py`,
# which is per-Viewer precisely because two Viewers must not share a camera or
# a stack.


class CameraWarning(UserWarning):
    """Warning for potential camera visibility issues."""


class CameraKeepWarning(UserWarning):
    """Warning that reset camera is set to KEEP."""


# Manual "once" handling below rather than warnings' own "once" filter: where one
# process serves several clients, that filter would show the warning to whoever
# triggered it first and silence it for everybody after.
warnings.simplefilter("always", CameraWarning)
warnings.simplefilter("always", CameraKeepWarning)

_camera_keep_warning_shown = False


def _warning_on_one_line(
    message: Warning | str,
    category: type[Warning],
    filename: str,
    lineno: int,
    line: str | None = None,
) -> str:
    """Warnings on one line, without the source echo.

    The signature matches `warnings.formatwarning`, which is what this replaces.
    The version carried over from ocp_vscode had an extra `file=None` in fifth
    position - a parameter `showwarning` has and `formatwarning` does not - so
    the `line` argument was being bound to `file` on every call. Harmless only
    because the body reads neither.
    """
    return f"{category.__name__}: {message}\n"


def camera_warning(message):
    """Issue a camera warning"""
    # ty models warnings.formatwarning as a fixed function rather than a
    # rebindable hook, so it rejects the assignment even though the two
    # signatures are now identical. Replacing it is the documented way to
    # change warning formatting.
    warnings.formatwarning = _warning_on_one_line  # ty: ignore[invalid-assignment]
    warnings.warn(message, CameraWarning, stacklevel=2)


def camera_keep_warning(message):
    """Issue a reset camera set to KEEP warning (only once per session)"""
    global _camera_keep_warning_shown  # pylint: disable=global-statement
    if not _camera_keep_warning_shown:
        warnings.formatwarning = _warning_on_one_line  # ty: ignore[invalid-assignment]
        warnings.warn(message, CameraKeepWarning, stacklevel=2)
        _camera_keep_warning_shown = True


def ignore_camera_warnings():
    """Suppress all camera visibility warnings."""
    warnings.filterwarnings("ignore", category=CameraWarning)
    warnings.filterwarnings("ignore", category=CameraKeepWarning)


# ============================ Shader ball ============================ #


def create_shader_ball(name="shader_ball"):
    """A shader ball compound to demonstrate materials on"""
    # Lazy on purpose - build123d is not a core dependency, and this module is
    # imported by the package __init__. See the module docstring.
    from build123d import (
        Align,
        CenterArc,
        Compound,
        Cone,
        Cylinder,
        Pos,
        Rot,
        SlotArc,
        Sphere,
        Triangle,
        extrude,
        fillet,
    )

    ccm = (Align.CENTER, Align.CENTER, Align.MIN)
    cM = (Align.CENTER, Align.MAX)

    r1 = 10
    r2 = 8.5
    r3 = 8
    h = 2
    s1 = Sphere(r1)
    s2 = Sphere(r2)
    s3 = Sphere(r3)
    s = Rot(0, 60, 0) * (s1 - s2 - Pos(0, 0, 14.3) * s3 - Pos(0, 0, -14.3) * s3)

    d = -r1 + 0.0

    c1 = Pos(0, 0, d - h) * Cylinder(7, h, align=ccm)
    c2 = Pos(0, 0, d - 0.1) * Cylinder(6, h, align=ccm)
    c3 = Pos(0, 0, d - 0.2) * Cylinder(5, h, align=ccm)
    c1 = fillet(c1.edges(), 0.2)
    c = c1 - c2 - c3

    b1 = Pos(0, 0, d - h) * (Cylinder(11, 2, align=ccm) - Cylinder(7.4, 2, align=ccm))

    sl1 = Pos(0, 0, d) * SlotArc(CenterArc((0, 0, 0), 10.0, 270 - 35, 70), 0.4)
    sl2 = Pos(0, 0, d) * SlotArc(CenterArc((0, 0, 0), 8.0, 270 - 25, 50), 0.4)
    sl3 = Pos(0, 0, d + 1e-2) * SlotArc(CenterArc((0, 0, 0), 9.0, 270 - 15, 30), 0.4)

    a1 = extrude(sl1, 0.2)
    a1 = fillet(a1.edges().group_by()[-1], 0.05)
    a2 = extrude(sl2, 0.2)
    a2 = fillet(a2.edges().group_by()[-1], 0.05)
    a3 = extrude(sl3, -0.2)
    a3 = fillet(a3.edges().group_by()[0], 0.05)

    b1 = b1 - a3 + a1 + a2

    t = Pos(0, 0, d) * Triangle(a=6, b=12, c=12, align=cM)
    h = 4
    n = 5

    def mask(r):
        return Pos(0, 0, -r1) * Cylinder(r, 20, align=ccm)

    b2 = Rot(0, 0, 180) * extrude(t, h)
    cn = Pos(0, 0, -r1 + 2.8) * Cone(7, 15, 4, align=ccm)
    b = b1 + (b2 & mask(10) - cn)

    for i in range(1, n):
        for sign in [-1, 1]:
            b += (
                Rot(0, 0, 180 + sign * i * 28.6) * extrude(t, h - 1.5 - i * h / n / 2)
            ) & mask(10 - i * 0.4)

    b -= Cylinder(7.4, 20)
    b &= Cylinder(11, 50)
    b = b.solid()

    b = fillet(b.edges(), 0.1)

    s4 = Rot(0, 0, 90) * Sphere(r2 - 1)

    compound = Compound([b, s, c, s4])
    compound.label = name
    return compound
