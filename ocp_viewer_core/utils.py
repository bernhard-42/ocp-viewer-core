"""Utility geometry, usable from every host: the shader ball for material demonstrations.

`from ocp_viewer_core.utils import create_shader_ball` is the import in any
viewer's environment - the core is a dependency of all of them, so nothing
per host is needed and no host binds the name at package level.

Built with build123d, which the core deliberately does not depend on - the
pyproject names no CAD library for the same reason it names no OCP provider,
because the host or the user chooses. The imports are at the top of this
module anyway: importing `ocp_viewer_core.utils` is the statement "I have
build123d", and a package import never pays for it.
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

__all__ = ["create_shader_ball"]


def create_shader_ball(name="shader_ball"):
    """A shader ball compound to demonstrate materials on"""
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
