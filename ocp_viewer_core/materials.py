"""Conversions between OCCT's XCAFDoc_VisMaterial and threejs-materials' PbrProperties.

OCCT documents carry visual materials as `XCAFDoc_VisMaterial` - a PBR block
(base color, metallic, roughness, refraction index, emissive) plus alpha mode
and double-sidedness. cadquery's `Material` wraps one in `wrapped_vis`, and any
STEP/glTF round trip through XCAF produces them. The viewer side speaks
`PbrProperties`. These two functions translate between the paradigms so a
material can enter the show pipeline from an OCCT document and a catalogue
material can be written back into one.

Both directions are scalar-only and lossy where the vocabularies differ:
`XCAFDoc_VisMaterialPBR` has no clearcoat, sheen, transmission or texture maps,
so those `PbrProperties` fields do not survive the trip into OCCT.

Color spaces: `PbrValues.color` is sRGB ratios, `PbrValues.emissive` is linear -
per that class's docstring. `Quantity_Color` stores linear RGB, converting at
the boundary via `Quantity_TOC_sRGB`; `EmissiveFactor` is a linear `gp_Vec3f`,
so it crosses without conversion.
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

from OCP.gp import gp_Vec3f
from OCP.Graphic3d import Graphic3d_AlphaMode
from OCP.Quantity import Quantity_Color, Quantity_ColorRGBA, Quantity_TypeOfColor
from OCP.TCollection import TCollection_HAsciiString
from OCP.XCAFDoc import XCAFDoc_VisMaterial, XCAFDoc_VisMaterialPBR
from threejs_materials import PbrProperties, PbrValues

__all__ = ["pbr_to_vis_material", "vis_material_to_pbr"]

# Three.js side constants (three/src/constants.js): FrontSide=0, BackSide=1
THREEJS_DOUBLE_SIDE = 2


def vis_material_to_pbr(vis_material, name=None):
    """Convert an `XCAFDoc_VisMaterial` to a `PbrProperties`.

    Reads the PBR block when the material has one; a common (Phong-style)
    material is converted through OCCT's own `ConvertToPbrMaterial`, which
    leaves the input untouched. An empty material holds nothing to render,
    so the answer is None - callers must check.

    @param vis_material: The `XCAFDoc_VisMaterial` to read
    @param name: Material name; falls back to the material's raw name, then "material"

    @return: A `PbrProperties`, or None if the material is empty
    """
    if vis_material.IsEmpty():
        return None

    if vis_material.HasPbrMaterial():
        pbr = vis_material.PbrMaterial()
    else:
        pbr = vis_material.ConvertToPbrMaterial()

    if name is None:
        raw_name = vis_material.RawName()
        if raw_name is not None:
            name = raw_name.ToCString()
    if name is None or name == "":
        name = "material"

    srgb = pbr.BaseColor.GetRGB().Values(Quantity_TypeOfColor.Quantity_TOC_sRGB)
    alpha = pbr.BaseColor.Alpha()

    values = PbrValues(
        color=list(srgb),
        metalness=pbr.Metallic,
        roughness=pbr.Roughness,
        ior=pbr.RefractionIndex,
    )

    emissive = pbr.EmissiveFactor
    if not (emissive.r() == 0.0 and emissive.g() == 0.0 and emissive.b() == 0.0):
        values.emissive = [emissive.r(), emissive.g(), emissive.b()]

    if vis_material.AlphaMode() == Graphic3d_AlphaMode.Graphic3d_AlphaMode_Mask:
        values.alpha_test = vis_material.AlphaCutOff()
    if alpha < 1.0:
        values.opacity = alpha
        values.transparent = True

    if vis_material.IsDoubleSided() is True:
        values.side = THREEJS_DOUBLE_SIDE

    return PbrProperties(
        id=name,
        name=name,
        source="occt",
        url="",
        license="",
        values=values,
    )


def pbr_to_vis_material(pbr_properties):
    """Convert a `PbrProperties` to a new `XCAFDoc_VisMaterial`.

    Only the fields `XCAFDoc_VisMaterialPBR` can hold survive: color plus
    opacity (as base color RGBA), metalness, roughness, ior, and emissive
    with `emissive_intensity` folded in. `alpha_test` becomes alpha mode
    Mask with its cutoff, a translucent material becomes mode Blend, and
    `side` double-sided marks the material double-sided. Everything else -
    clearcoat, sheen, transmission, texture maps - is not representable
    and is dropped.

    @param pbr_properties: The `PbrProperties` to write

    @return: A new `XCAFDoc_VisMaterial` with the PBR block set
    """
    values = pbr_properties.values
    pbr = XCAFDoc_VisMaterialPBR()

    opacity = values.opacity
    if opacity is None:
        opacity = 1.0

    if values.color is not None:
        rgb = Quantity_Color(
            values.color[0],
            values.color[1],
            values.color[2],
            Quantity_TypeOfColor.Quantity_TOC_sRGB,
        )
        pbr.BaseColor = Quantity_ColorRGBA(rgb, opacity)
    else:
        base_color = pbr.BaseColor
        base_color.SetAlpha(opacity)
        pbr.BaseColor = base_color

    if values.metalness is not None:
        pbr.Metallic = values.metalness
    if values.roughness is not None:
        pbr.Roughness = values.roughness
    if values.ior is not None:
        pbr.RefractionIndex = values.ior

    if values.emissive is not None:
        intensity = values.emissive_intensity
        if intensity is None:
            intensity = 1.0
        pbr.EmissiveFactor = gp_Vec3f(
            values.emissive[0] * intensity,
            values.emissive[1] * intensity,
            values.emissive[2] * intensity,
        )

    vis_material = XCAFDoc_VisMaterial()
    vis_material.SetPbrMaterial(pbr)
    vis_material.SetRawName(TCollection_HAsciiString(pbr_properties.name))

    if values.alpha_test is not None:
        vis_material.SetAlphaMode(
            Graphic3d_AlphaMode.Graphic3d_AlphaMode_Mask, values.alpha_test
        )
    elif values.transparent is True or opacity < 1.0:
        vis_material.SetAlphaMode(Graphic3d_AlphaMode.Graphic3d_AlphaMode_Blend)

    if values.side == THREEJS_DOUBLE_SIDE:
        vis_material.SetDoubleSided(True)

    return vis_material
