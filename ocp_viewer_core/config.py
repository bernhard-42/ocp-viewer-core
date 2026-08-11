"""Configuration: the defaults, the precedence over them, and the enums.

`Config` answers what a show is drawn with, from three sources - the workspace
settings a host stores, the viewer's own reported state, and the defaults set
in code. A host supplies two lists: the keys it stores, and the keys it may not
be told because its surface decides them.
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
from enum import Enum

from ocp_tessellate.utils import Color

from . import keys
from .comms import Session, is_pytest

__all__ = []


class Camera(Enum):
    """Camera reset modes"""

    RESET = "reset"
    CENTER = "center"
    KEEP = "keep"
    ISO = "iso"
    TOP = "top"
    BOTTOM = "bottom"
    LEFT = "left"
    RIGHT = "right"
    BACK = "rear"  #  intentionally
    FRONT = "front"


class Collapse(Enum):
    """Collapse modes for the CAD navigation tree"""

    NONE = 2
    LEAVES = -1
    ALL = 0
    ROOT = 1


class Render(Enum):
    """Per-object render modes"""

    ALL = "all"
    EDGES = "edges"
    FACES = "faces"
    NONE = "none"


class StudioEnvironment(Enum):
    """Studio mode environment/HDR map presets"""

    PROCEDURAL_STUDIO = "studio"
    SOFT_LIGHT = "studio_small_08"
    HIGH_CONTRAST_STUDIO = "studio_small_03"
    BRIGHT_NEUTRAL = "white_studio_05"
    CLEAN_SOFTBOX = "white_studio_03"
    SPOTLIT_SETUP = "photo_studio_01"
    CONTROLLED_LIGHT = "studio_small_09"
    HARD_CONTRAST_LIGHT = "cyclorama_hard_light"
    URBAN_OVERCAST = "canary_wharf"
    OUTDOOR_WARM = "kiara_1_dawn"
    NEUTRAL_INDUSTRIAL = "empty_warehouse_01"
    SAN_GIUSEPPE_BRIDGE = "san_giuseppe_bridge"


class StudioBackground(Enum):
    """Studio mode background options"""

    ENVIRONMENT = "environment"
    TRANSPARENT = "transparent"
    GRADIENT = "gradient"
    GRADIENT_DARK = "gradient-dark"
    WHITE = "white"
    GREY = "grey"
    DARKGREY = "darkgrey"


class StudioToneMapping(Enum):
    """Studio mode tone mapping options"""

    NEUTRAL = "neutral"
    ACES = "ACES"
    NONE = "none"


class StudioTextureMapping(Enum):
    """Studio mode texture mapping options"""

    TRIPLANAR = "triplanar"
    PARAMETRIC = "parametric"


class AnalysisTool(Enum):
    """Analysis tools for the CAD viewer (mutually exclusive with explode)."""

    PROPERTIES = "properties"
    DISTANCE = "distance"
    SELECT = "select"
    OFF = "off"


class UiTab(Enum):
    """UI tabs in the CAD viewer side panel."""

    TREE = "tree"
    CLIP = "clip"
    ZEBRA = "zebra"
    MATERIAL = "material"
    STUDIO = "studio"


COLLAPSE_REVERSE_MAPPING = {
    2: Collapse.NONE,
    -1: Collapse.LEAVES,
    0: Collapse.ALL,
    1: Collapse.ROOT,
}


# The defaults that are ours rather than the viewer's - the ones no workspace
# setting and no viewer state supplies. Module level and copied per instance,
# so construction and reset_defaults() read one source instead of two literals
# that drift.
DEFAULT_DEFAULTS = {
    "render_normals": False,
    "render_mates": False,
    "render_joints": False,
    "helper_scale": 1.0,
    "show_parent": False,
    "show_locals": True,
    "timeit": False,
    "collapse": Collapse.ROOT,
    "debug": False,
}

# The defaults `reset_defaults` does *not* put back, and the asymmetry is
# load-bearing. `combined_config` applies the defaults last, so a key listed
# among them masks whatever the viewer reports for it. `collapse` is the
# viewer's own - the user changes it by clicking, and it comes back in
# `status` - so keeping it after a reset would make `combined_config` answer
# `Collapse.ROOT` however the tree actually stands, and the next show would
# re-collapse a tree the user had opened.
NOT_RESTORED_ON_RESET = ("collapse",)


class Config:
    def __init__(self, session: Session, workspace_config_keys, exclude_keys):
        self.session = session
        self.workspace_config_keys = workspace_config_keys
        self.exclude_keys = exclude_keys

        # Each group maps the Python name to the name three-cad-viewer knows the
        # option by. None means the key never reaches the renderer as an option:
        # either it is ours alone (tessellation, Python-side control) or it is
        # applied by calling a method rather than by passing an option.
        #
        # The renderer names are not derived. A mechanical snake-to-camel
        # transform is right for most of them and silently wrong for the rest -
        # _update drops an unknown option without a diagnostic - so the name is
        # written down beside the key it belongs to.

        # The key vocabulary lives in keys.py: it describes three-cad-viewer
        # rather than this host, both halves of the package need it, and neither
        # config nor comms may import the other. Bound to attributes here so the
        # methods below read the same as they did when they built it.
        self.ui_toolbar = keys.UI_TOOLBAR
        self.ui_tree = keys.UI_TREE
        self.ui_clip = keys.UI_CLIP
        self.ui_zebra = keys.UI_ZEBRA
        self.ui_studio = keys.UI_STUDIO
        self.ui_material = keys.UI_MATERIAL
        self.ui = keys.UI
        self.display = keys.DISPLAY
        self.mouse = keys.MOUSE
        self.grid = keys.GRID
        self.renderer = keys.RENDERER
        self.control = keys.CONTROL
        self.camera = keys.CAMERA
        self.all = keys.ALL
        self.settable = keys.SETTABLE

        self.defaults = dict(DEFAULT_DEFAULTS)

    def validate_keyword(self, key):
        """Why this host cannot act on `key`, or None if it can.

        One question, one mechanism. `exclude_keys` already answers it for the
        keys a host does not own - ocp_vscode cannot set `cad_width` or
        `height`, because the webview decides them - so that list is the default
        implementation rather than a second thing to keep in step.

        A host overrides this when a keyword is meaningless to it rather than
        merely not its to set: `port` selects which viewer to address when
        several are open, which is real in VS Code and has no meaning in a
        notebook. Returning a sentence rather than a boolean is deliberate, so
        the warning can say why instead of only that.
        """
        # TODO: `theme` may belong in every host's exclusion list, since a
        # surface generally decides its own. Left out until a host is found
        # that needs to be told one.
        if key in self.exclude_keys:
            return f"{key} is determined by the host and cannot be set here"
        return None

    def validate_tool_args(
        self, explode: bool | None, analysis_tool: AnalysisTool | str | None
    ):
        """Shared validation for ``explode`` / ``analysis_tool`` — used by both
        ``set_viewer_config`` and ``show``. Accepts either ``AnalysisTool`` enum
        members or their string values. Raises ``ValueError`` on invalid input
        or on the mutually-exclusive combination."""

        if isinstance(analysis_tool, AnalysisTool):
            analysis_tool = analysis_tool.value

        if analysis_tool is not None and analysis_tool not in (
            "properties",
            "distance",
            "select",
            "off",
        ):
            raise ValueError(
                f"analysis_tool must be an AnalysisTool member or one of "
                f'"properties", "distance", "select", "off"; got {analysis_tool!r}'
            )
        if explode is True and analysis_tool in ("properties", "distance", "select"):
            raise ValueError(
                "explode=True and analysis_tool=... are mutually exclusive — "
                "the viewer disables one when the other activates. "
                "Pass at most one of them in a single call."
            )

    def get_defaults(self):
        """Get all defaults"""
        result = dict(self.workspace_config())
        result.update(self.defaults)
        return result

    def get_default(self, key):
        """Get default value for key"""
        return self.get_defaults().get(key)

    def preset(self, key, value):
        """Set default value for key"""
        return self.get_default(key) if value is None else value

    def workspace_filter(self, conf):
        """Filter out all non-workspace keys from the config dict"""
        return {k: v for k, v in conf.items() if k in self.workspace_config_keys}

    def status(self, debug=False):
        """Get viewer status"""

        if is_pytest():
            return {}

        response = self.session.status()
        if debug:
            return response.get("_debugStarted", False)

        collapse_val = response.get("collapse")
        if collapse_val is not None:
            if collapse_val in COLLAPSE_REVERSE_MAPPING:
                response["collapse"] = COLLAPSE_REVERSE_MAPPING[collapse_val]
            else:
                warnings.warn(f"Unknown collapse value from viewer: {collapse_val}")

        return dict(sorted(response.items()))

    def workspace_config(self):
        """Get viewer workspace config"""

        if is_pytest():
            return {
                "_splash": False,
                "default_facecolor": (238, 130, 238),
                "default_thickedgecolor": (186, 85, 211),
                "default_vertexcolor": (186, 85, 211),
            }

        try:
            conf = self.session.workspace_config()
            mapping = {
                "none": Collapse.NONE,
                "leaves": Collapse.LEAVES,
                "all": Collapse.ALL,
                "root": Collapse.ROOT,
                "E": Collapse.NONE,
                "1": Collapse.LEAVES,
                "C": Collapse.ALL,
                "R": Collapse.ROOT,
            }
            if isinstance(conf.get("collapse"), str):
                conf["collapse"] = mapping[conf.get("collapse", "R")]
            if isinstance(conf.get("reset_camera"), str):
                conf["reset_camera"] = Camera[conf.get("reset_camera", "KEEP").upper()]
            return dict(conf)

        except Exception as ex:
            raise RuntimeError(
                "Cannot access viewer config. Is the viewer running?\n" + str(ex.args)
            ) from ex

    def combined_config(self):
        """Get combined config from workspace and status"""

        try:
            wspace_config = self.workspace_config()
            wspace_status = self.status()

        except Exception as ex:
            raise RuntimeError(
                "Cannot access viewer config. Is the viewer running?\n" + str(ex.args)
            ) from ex

        use_status = not wspace_config.get("_splash", False)

        if use_status:
            wspace_config.update(self.workspace_filter(wspace_status))

        wspace_config.update(self.defaults)

        return dict(sorted(wspace_config.items()))

    def get_changed_config(self, key=None):
        """Get changed config from workspace and status"""

        wspace_config = self.workspace_config()
        wspace_config.update(self.defaults)
        if key is None:
            return wspace_config
        else:
            return wspace_config.get(key)

    # pylint: disable=too-many-arguments,unused-argument,too-many-locals
    def set_viewer_config(
        self,
        axes=None,
        axes0=None,
        grid=None,
        center_grid=None,
        ortho=None,
        transparent=None,
        black_edges=None,
        explode=None,
        zoom=None,
        position=None,
        quaternion=None,
        target=None,
        default_edgecolor=None,
        default_opacity=None,
        ambient_intensity=None,
        direct_intensity=None,
        metalness=None,
        roughness=None,
        zoom_speed=None,
        pan_speed=None,
        rotate_speed=None,
        glass=None,
        tools=None,
        tree_width=None,
        # Every key in `keys.SETTABLE` needs a parameter here: `reset_defaults`
        # builds its call from that list, and one without a parameter raises
        # TypeError as soon as a viewer reports it.
        up=None,
        collapse=None,
        reset_camera=None,
        states=None,
        tab=None,
        clip_slider_0=None,
        clip_slider_1=None,
        clip_slider_2=None,
        clip_normal_0=None,
        clip_normal_1=None,
        clip_normal_2=None,
        clip_intersection=None,
        clip_planes=None,
        clip_object_colors=None,
        zebra_count=None,
        zebra_opacity=None,
        zebra_direction=None,
        zebra_color_scheme=None,
        zebra_mapping_mode=None,
        studio_environment=None,
        studio_env_intensity=None,
        studio_env_rotation=None,
        studio_background=None,
        studio_tone_mapping=None,
        studio_exposure=None,
        studio_shadow_intensity=None,
        studio_shadow_softness=None,
        studio_ao_intensity=None,
        studio_texture_mapping=None,
        studio_4k_env_maps=None,
        analysis_tool=None,
    ):
        """Set viewer config"""
        self.validate_tool_args(explode, analysis_tool)

        # Every argument that was given, with enums unwrapped to their values.
        # The values are what the viewer already expects - Collapse's are
        # three-cad-viewer's CollapseState numbers, Camera's and UiTab's are the
        # strings it takes - so unwrapping is the whole of the translation.
        #
        # Done for every argument rather than for a list of names. The list was
        # six long and reset_camera, which takes a Camera, was not on it, so
        # set_viewer_config(reset_camera=Camera.KEEP) put an enum object on the
        # wire. `self` is excluded because locals() has it too.
        config = {
            key: value.value if isinstance(value, Enum) else value
            for key, value in locals().items()
            if value is not None and key != "self"
        }

        if config.get("default_edgecolor") is not None:
            config["default_edgecolor"] = Color(config["default_edgecolor"]).web_color

        self.session.set_viewer(config)

    def set_defaults(
        self,
        glass=None,
        tools=None,
        tree_width=None,
        axes=None,
        axes0=None,
        grid=None,
        ortho=None,
        transparent=None,
        default_opacity=None,
        black_edges=None,
        orbit_control=None,
        collapse=None,
        ticks=None,
        center_grid=None,
        grid_font_size=None,
        up=None,
        explode=None,
        analysis_tool=None,
        tab=None,
        zoom=None,
        reset_camera=None,
        clip_slider_0=None,
        clip_slider_1=None,
        clip_slider_2=None,
        clip_normal_0=None,
        clip_normal_1=None,
        clip_normal_2=None,
        clip_intersection=None,
        clip_planes=None,
        clip_object_colors=None,
        zebra_count=None,
        zebra_opacity=None,
        zebra_direction=None,
        zebra_color_scheme=None,
        zebra_mapping_mode=None,
        pan_speed=None,
        rotate_speed=None,
        zoom_speed=None,
        deviation=None,
        angular_tolerance=None,
        edge_accuracy=None,
        default_color=None,
        default_edgecolor=None,
        ambient_intensity=None,
        direct_intensity=None,
        metalness=None,
        roughness=None,
        render_edges=None,
        render_normals=None,
        render_mates=None,
        render_joints=None,
        show_parent=None,
        show_locals=None,
        show_sketch_local=None,  # DEPRECATED
        helper_scale=None,
        mate_scale=None,  # DEPRECATED
        studio_environment=None,
        studio_env_intensity=None,
        studio_env_rotation=None,
        studio_background=None,
        studio_tone_mapping=None,
        studio_exposure=None,
        studio_shadow_intensity=None,
        studio_shadow_softness=None,
        studio_ao_intensity=None,
        studio_texture_mapping=None,
        studio_4k_env_maps=None,
        debug=None,
        timeit=None,
        # Jupyter CadQuery
        cad_width=None,
        height=None,
    ):
        # pylint: disable=line-too-long
        """Set viewer defaults
        Keywords to configure the viewer:
        - UI
            glass:              Use glass mode where tree is an overlay over the cad object (default=False)
            tools:              Show tools (default=True)
            tree_width:         Width of the object tree (default=240)

        - Viewer
            axes:               Show axes (default=False)
            axes0:              Show axes at (0,0,0) (default=False)
            grid:               Show grid (default=False)
            ortho:              Use orthographic projections (default=True)
            transparent:        Show objects transparent (default=False)
            default_opacity:    Opacity value for transparent objects (default=0.5)
            black_edges:        Show edges in black color (default=False)
            orbit_control:      Mouse control use "orbit" control instead of "trackball" control (default=False)
            collapse:           Collapse.LEAVES: collapse all single leaf nodes,
                                Collapse.ROOT: expand root only,
                                Collapse.ALL: collapse all nodes,
                                Collapse.NONE: expand all nodes
                                (default=Collapse.ROOT)
            ticks:              Hint for the number of ticks in both directions (default=5)
            center_grid:        Center the grid at the origin or center of mass (default=False)
            grid_font_size:     Size for the font used for grid axis labels (default=12)
            up:                 Use z-axis ('Z') or y-axis ('Y') as up direction for the camera (default="Z")
            explode:            Turn on explode mode (default=False)
            analysis_tool:      Activate one of the analysis tools (mutually exclusive
                                with explode=True):
                                AnalysisTool.PROPERTIES, AnalysisTool.DISTANCE,
                                AnalysisTool.SELECT, AnalysisTool.OFF.
                                String values also accepted ("properties", "distance",
                                "select", "off"). Default=None (no change).
            tab:                Switch the side panel tab:
                                UiTab.TREE, UiTab.CLIP, UiTab.ZEBRA, UiTab.MATERIAL,
                                UiTab.STUDIO. String values also accepted
                                ("tree", "clip", "zebra", "material", "studio").
                                Default=None (no change).

            zoom:               Zoom factor of view (default=1.0)
            position:           Camera position
            quaternion:         Camera orientation as quaternion
            target:             Camera look at target
            reset_camera:       Camera.RESET: Reset camera position, rotation, zoom and target
                                Camera.CENTER: Keep camera position, rotation, zoom, but look at center
                                Camera.KEEP: Keep camera position, rotation, zoom, and target
                                Or, choose one of the presets Camera.ISO, Camera.LEFT, Camera.RIGHT,
                                Camera.TOP, Camera.BOTTOM, Camera.FRONT, Camera.BACK
                                (default=Camera.RESET)
            clip_slider_0:      Setting of clipping slider 0 (default=None)
            clip_slider_1:      Setting of clipping slider 1 (default=None)
            clip_slider_2:      Setting of clipping slider 2 (default=None)
            clip_normal_0:      Setting of clipping normal 0 (default=[-1,0,0])
            clip_normal_1:      Setting of clipping normal 1 (default=[0,-1,0])
            clip_normal_2:      Setting of clipping normal 2 (default=[0,0,-1])
            clip_intersection:  Use clipping intersection mode (default=[False])
            clip_planes:        Show clipping plane helpers (default=False)
            clip_object_colors: Use object color for clipping caps (default=False)

            zebra_count:        Setting of zebra stripe count (default=9, range: 2-50)
            zebra_opacity:      Setting of zebra opacity (default=1, range: 0-1)
            zebra_direction:    Setting of zebra direction angle (default=0, range: 0-90)
            zebra_color_scheme: Zebra color scheme: "blackwhite", "grayscale", or "colorful" (default="blackwhite")
            zebra_mapping_mode: Zebra mapping mode: "reflection" or "normal" (default="reflection")

            studio_environment:      Environment HDR map, use StudioEnvironment enum or a custom HDR URL
                                     (default=StudioEnvironment.PROCEDURAL_STUDIO)
            studio_env_intensity:    Intensity of environment lighting, 0-3.0 (default=1.0)
            studio_env_rotation:     Rotation of environment map in degrees, 0-360 (default=0)
            studio_background:       StudioBackground.ENVIRONMENT, .TRANSPARENT, .GRADIENT, .GRADIENT_DARK,
                                     .WHITE, .GREY, .DARKGREY (default=StudioBackground.ENVIRONMENT)
            studio_tone_mapping:     StudioToneMapping.NEUTRAL, .ACES, .NONE (default=StudioToneMapping.NEUTRAL)
            studio_exposure:         Tone mapping exposure, 0-3.0 (default=1.0)
            studio_shadow_intensity: Shadow intensity, 0-1.0 (default=0.5)
            studio_shadow_softness:  Shadow softness, 0-1.0 (default=0.2)
            studio_ao_intensity:     Ambient occlusion intensity, 0-3.0 (default=0.5)
            studio_texture_mapping:  StudioTextureMapping.TRIPLANAR or .PARAMETRIC
                                     (default=StudioTextureMapping.TRIPLANAR)
            studio_4k_env_maps:      Use 4K resolution environment maps (default=False)

            pan_speed:          Speed of mouse panning (default=1)
            rotate_speed:       Speed of mouse rotate (default=1)
            zoom_speed:         Speed of mouse zoom (default=1)

        - Renderer
            deviation:          Shapes: Deviation from linear deflection value (default=0.1)
            angular_tolerance:  Shapes: Angular deflection in radians for tessellation (default=0.2)
            edge_accuracy:      Edges: Precision of edge discretization (default: mesh quality / 100)

            default_color:      Default mesh color (default=(232, 176, 36))
            default_edgecolor:  Default mesh color (default=(128, 128, 128))
            ambient_intensity:  Intensity of ambient light (default=1.00)
            direct_intensity:   Intensity of direct light (default=1.10)
            metalness:          Metalness property of the default material (default=0.30)
            roughness:          Roughness property of the default material (default=0.65)

            render_edges:       Deprecated, use mode=Render.FACES or Render.ALL in show() instead
            render_normals:     Render normals (default=False)
            render_mates:       Render mates for MAssemblies (default=False)
            render_joints:      Render mates for MAssemblies (default=False)
            show_parent:        Render parent of faces, edges or vertices as wireframe (default=False)
            show_locals:        In build123d show local part/sketch/line in addition to the relocated
                                object (default=True)
            helper_scale:       Scale of rendered helpers (locations, axis, mates for MAssemblies) (default=1)
                                If it is a float < 1, used the max distance to nested bounding box times
                                helper_scale to determine the absolut value of it

        - Debug
            debug:              Show debug statements to the VS Code browser console (default=False)
            timeit:             Show timing information from level 0-3 (default=False)

        - Jupyter Cadquery only:
            cad_width:          The viewer width in  Jupyter CadQuery
            height:             The viewer height in  Jupyter CadQuery
        """

        self.validate_tool_args(explode, analysis_tool)

        # `self` is excluded explicitly: `locals()` includes it, it is never
        # None, and the loop below would report it as an unknown config key.
        kwargs = {k: v for k, v in locals().items() if v is not None and k != "self"}

        kwargs = self.check_deprecated(kwargs)

        for key, value in kwargs.items():
            if key in self.all and not key in self.exclude_keys:
                self.defaults[key] = value
            else:
                print(f"'{key}' is an unknown config, ignored!")

        self.set_viewer_config(
            **{k: v for k, v in kwargs.items() if k in self.settable},
        )

    def reset_defaults(self, apply=True):
        """Reset defaults not given in workspace config"""

        if apply:
            config = {
                key: value
                for key, value in self.workspace_config().items()
                if key in self.settable
            }
            config["reset_camera"] = Camera.KEEP

            self.set_viewer_config(**config)

            if config.get("transparent") is not None:
                self.set_viewer_config(transparent=config["transparent"])

        self.defaults = {
            key: value
            for key, value in DEFAULT_DEFAULTS.items()
            if key not in NOT_RESTORED_ON_RESET
        }

    def check_deprecated(self, kwargs, _length=1):
        """Check for deprecated arguments"""
        if kwargs.get("mate_scale") is not None:
            print("\nmate_scale is deprecated, use helper_scale instead\n")
            kwargs["helper_scale"] = kwargs["mate_scale"]
            del kwargs["mate_scale"]

        if kwargs.get("reset_camera") is True:
            print(
                "\n'reset_camera=True' is deprecated, use 'reset_camera=Camera.RESET' instead\n"
            )
            kwargs["reset_camera"] = Camera.RESET

        if kwargs.get("reset_camera") is False:
            print(
                "\n'reset_camera=False' is deprecated, use 'reset_camera=Camera.CENTER' instead\n"
            )
            kwargs["reset_camera"] = Camera.CENTER

        if kwargs.get("collapse") == "C":
            print(
                "\n'collapse=\"C\"' is deprecated, use 'collapse=Collapse.ALL' instead\n"
            )
            kwargs["collapse"] = Collapse.ALL

        if kwargs.get("collapse") == "1" or kwargs.get("collapse") == 1:
            print(
                "\n'collapse=\"1\"' is deprecated, use 'collapse=Collapse.LEAVES' instead\n"
            )
            kwargs["collapse"] = Collapse.LEAVES

        if kwargs.get("collapse") == "R":
            print(
                "\n'collapse=\"R\"' is deprecated, use 'collapse=Collapse.ROOT' instead\n"
            )
            kwargs["collapse"] = Collapse.ROOT

        if kwargs.get("collapse") == "E":
            print(
                "\n'collapse=\"E\"' is deprecated, use 'collapse=Collapse.NONE' instead\n"
            )
            kwargs["collapse"] = Collapse.NONE

        if kwargs.get("render_edges") is not None:
            warnings.warn(
                "render_edges is deprecated, use modes=Render.FACES or Render.ALL in show() instead",
                DeprecationWarning,
                stacklevel=3,
            )
            if kwargs.get("modes") is None:
                if kwargs["render_edges"] is True:
                    kwargs["modes"] = [Render.ALL] * _length
                else:
                    kwargs["modes"] = [Render.FACES] * _length

            del kwargs["render_edges"]

        if kwargs.get("control") is not None:
            print(
                "\n'control=\"orbit\" or \"trackball\"' is deprecated, use 'orbit_control=True' or 'False' instead\n"
            )
            kwargs["orbit_control"] = kwargs["control"] == "orbit"

        if kwargs.get("show_sketch_local") is not None:
            print("\n'show_sketch_local' is deprecated, use 'show_locals' instead\n")
            kwargs["show_locals"] = kwargs["show_sketch_local"]
            del kwargs["show_sketch_local"]

        return kwargs
