"""The config key vocabulary: one name in Python, one in JavaScript.

A module of its own because both halves of the package need it and neither may
import the other - `config` groups and validates keys with it, `comms`
translates a payload with it. The renderer names describe three-cad-viewer
rather than any host, so they belong with neither.
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

__all__ = [
    "ALL",
    "CAMERA",
    "CONFIG",
    "CONTROL",
    "DISPLAY",
    "GRID",
    "MOUSE",
    "NOT_CONFIG",
    "RENDERER",
    "SETTABLE",
    "UI",
    "UI_CLIP",
    "UI_MATERIAL",
    "UI_STUDIO",
    "UI_TOOLBAR",
    "UI_TREE",
    "UI_ZEBRA",
    "merge",
    "to_javascript",
]


def _snake_to_camel(name):
    """The mechanical spelling, for keys the renderer has no option name for."""
    head, *rest = name.split("_")
    return head + "".join(word[:1].upper() + word[1:] for word in rest)


def merge(*mappings):
    """Merge {python_name: javascript_name} mappings, refusing a redefinition.

    A key belonging to more than one group is ordinary - UI_MATERIAL is both a
    ui group and a renderer group - and is not a conflict as long as every group
    names the same renderer option. Two groups disagreeing is a bug, and taking
    the last silently is what concatenating tuples does, and it hides a
    disagreement rather than reporting one.
    """
    merged = {}
    for mapping in mappings:
        for key, js_name in mapping.items():
            if key in merged and merged[key] != js_name:
                raise ValueError(
                    f"'{key}' is mapped to both {merged[key]!r} and {js_name!r}"
                )
            merged[key] = js_name
    return merged


UI_TOOLBAR = {
    "axes": "axes",
    "axes0": "axes0",
    "grid": "grid",
    "ortho": "ortho",
    "transparent": "transparent",
    "black_edges": "blackEdges",
    "explode": None,  # applied by code (setExplode)
    "analysis_tool": None,  # tool activation, not an option
    "tab": "tab",
}

UI_TREE = {
    "collapse": "collapse",
    "states": None,  # applied by code (setStates)
}

UI_CLIP = {
    "clip_intersection": "clipIntersection",
    "clip_normal_0": "clipNormal0",
    "clip_normal_1": "clipNormal1",
    "clip_normal_2": "clipNormal2",
    "clip_object_colors": "clipObjectColors",
    "clip_planes": "clipPlaneHelpers",
    "clip_slider_0": "clipSlider0",
    "clip_slider_1": "clipSlider1",
    "clip_slider_2": "clipSlider2",
}

UI_ZEBRA = {
    "zebra_color_scheme": "zebraColorScheme",
    "zebra_count": "zebraCount",
    "zebra_direction": "zebraDirection",
    "zebra_mapping_mode": "zebraMappingMode",
    "zebra_opacity": "zebraOpacity",
}

UI_STUDIO = {
    "studio_4k_env_maps": "studio4kEnvMaps",
    "studio_ao_intensity": "studioAOIntensity",
    "studio_background": "studioBackground",
    "studio_env_intensity": "studioEnvIntensity",
    "studio_env_rotation": "studioEnvRotation",
    "studio_environment": "studioEnvironment",
    "studio_exposure": "studioExposure",
    "studio_shadow_intensity": "studioShadowIntensity",
    "studio_shadow_softness": "studioShadowSoftness",
    "studio_texture_mapping": "studioTextureMapping",
    "studio_tone_mapping": "studioToneMapping",
}

UI_MATERIAL = {
    "ambient_intensity": "ambientIntensity",
    "direct_intensity": "directIntensity",
    "metalness": "metalness",
    "roughness": "roughness",
}

UI = merge(
    UI_TOOLBAR,
    UI_TREE,
    UI_CLIP,
    UI_ZEBRA,
    UI_STUDIO,
    UI_MATERIAL,
)

DISPLAY = {
    "tree_width": "treeWidth",
    "cad_width": "cadWidth",
    "height": "height",
    "tools": "tools",
    "glass": "glass",
    # "light", "dark" or "browser" - what three-cad-viewer's setTheme takes and
    # what every host's setting already holds. `dark`, a boolean, preceded it
    # and was superseded in September 2025; from then on it never travelled on
    # the wire, because the extension converted it to `theme` before answering a
    # config request. It stayed in the vocabulary for another year regardless,
    # which is what a key nothing produces costs: nothing, until something
    # checks.
    "theme": "theme",
    "modifier_keys": "keymap",
    "orbit_control": "control",
    "up": "up",
}

MOUSE = {
    "pan_speed": "panSpeed",
    "rotate_speed": "rotateSpeed",
    "zoom_speed": "zoomSpeed",
}

GRID = {
    "grid_font_size": "gridFontSize",
    "ticks": "ticks",
    "center_grid": "centerGrid",
}

RENDERER = merge(
    UI_MATERIAL,
    {
        "angular_tolerance": None,
        "deviation": None,
        "edge_accuracy": None,
        "default_color": None,
        "default_facecolor": None,
        "default_edgecolor": "edgeColor",
        "default_thickedgecolor": None,
        "default_vertexcolor": None,
        "default_opacity": "defaultOpacity",
    },
)

CONTROL = {
    "debug": None,
    "helper_scale": None,
    "render_joints": None,
    "render_mates": None,
    "render_normals": None,
    "reset_camera": None,  # applied by code (setView)
    "show_parent": None,
    "show_locals": None,
    "timeit": "timeit",
}

CAMERA = {
    "position": "position",
    "quaternion": "quaternion",
    "target": "target",
    "zoom": "zoom",
}

ALL = merge(
    UI,
    DISPLAY,
    MOUSE,
    GRID,
    RENDERER,
    CONTROL,
    CAMERA,
)

# The keys of a viewer's own state that are configuration, and so survive into
# the next show. `Config.config_filter` keeps these out of the viewer's reported
# status and drops the rest, which is what stops a second `show()` undoing what
# the user just did at the toolbar.
#
# Derived rather than listed, because a hand-written copy is what this used to
# be: an identical 61-key tuple in each of three hosts, named
# WORKSPACE_CONFIG_KEYS as though a host chose its own. None ever did - the set
# is a property of three-cad-viewer's state vocabulary, not of any host's
# settings - and three copies that must stay identical is a drift waiting to
# happen. What a host *persists* is a different question, and one only the host
# can answer; it answers it with values, in `Comms.workspace_config`, and needs
# no key list here.
#
# The four exclusions, each because the key is not viewer state that survives:
#   CONTROL  - per-show instructions (timeit, render_normals, reset_camera).
#              A viewer never reports them back; they are said once, per call.
#   CAMERA   - position/quaternion/target/zoom are the camera *now*, carried by
#              the camera policy in render.js, not restored as configuration.
#   cad_width, height - the surface's geometry, decided by whoever owns the
#              surface. See each host's exclude_keys, which runs both ways.
#   edge_accuracy - a tessellation input, consumed before a viewer sees it.
NOT_CONFIG = (*CONTROL, *CAMERA, "cad_width", "height", "edge_accuracy")

CONFIG = {key: value for key, value in ALL.items() if key not in NOT_CONFIG}

# The extras are keys the groups above already name, so they are taken
# from the catalogue rather than spelled a second time: a typo here is a
# KeyError, not a second spelling of a renderer option.
SETTABLE = merge(
    UI_TREE,
    UI_TOOLBAR,
    UI_MATERIAL,
    UI_CLIP,
    UI_ZEBRA,
    # The studio family is settable because the shared dispatch applies
    # it. A host whose page does not call into the shared dispatch cannot
    # act on them, and would drop such a message without a word.
    UI_STUDIO,
    MOUSE,
    CAMERA,
    {
        key: ALL[key]
        for key in (
            "tree_width",
            "tools",
            "glass",
            "center_grid",
            "default_edgecolor",
            "default_opacity",
            "reset_camera",
            # Changeable on a live viewer, not only at construction: the
            # renderer has setTheme, and a host whose surface changes theme
            # under it - a VS Code colour theme - needs to say so.
            "theme",
            # Likewise, and for the same reason it was missed: the renderer has
            # had `setKeyMap` all along and nothing called it, so the keymap
            # looked like a construction-time option and was not one.
            "modifier_keys",
        )
    },
)


def to_javascript(config):
    """Rename Python keys to the names the JavaScript half uses.

    Python speaks snake_case and enums; JavaScript speaks camelCase and the enum
    values. The sender translates to the receiver's paradigm, and this is that
    translation going out - three-cad-viewer's own notification map is the same
    rule coming back.

    A key the renderer knows as an option is renamed to that name, taken from
    the groups above rather than derived: a mechanical transform gets
    clip_planes, default_edgecolor and studio_ao_intensity wrong, and gets them
    wrong silently, because the renderer drops an option it does not recognise
    without a word. A key applied by calling a method instead of by setting an
    option has no renderer name, so its wire spelling is the mechanical
    transform of ours - explode, states, reset_camera.
    """
    renamed = {}
    for key, value in config.items():
        if key.startswith("_"):
            # Protocol keys, not configuration: `_splash` is a handshake the host
            # and Python share, and the browser reads it under exactly that name.
            # They also break the transform - "_splash".split("_") starts with an
            # empty segment, so the mechanical spelling is "Splash" and the flag
            # silently never arrives. The underscore is the marker for "not part
            # of the config vocabulary", so these pass through untouched.
            renamed[key] = value
            continue
        js_name = ALL.get(key)
        name = js_name if js_name is not None else _snake_to_camel(key)
        if name in renamed:
            # Two config keys landing on one renderer option is always a bug,
            # and a silent one: the later key wins and the value it overwrites
            # was usually the correct one. `merge` refuses this for the group
            # tables; this is the same refusal for a payload.
            raise ValueError(
                f"'{key}' and another key both map to '{name}' - "
                f"the value {renamed[name]!r} would be replaced by {value!r}"
            )
        renamed[name] = value
    return renamed
