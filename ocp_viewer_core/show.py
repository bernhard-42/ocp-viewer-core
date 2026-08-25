"""The show pipeline: CAD objects in, a model the viewer draws out."""

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

import inspect
import math
import os
import pathlib
import re
import time
import traceback
import types
import warnings
from enum import Enum
from logging import Logger
from typing import Generic

from ocp_tessellate import OcpGroup
from ocp_tessellate.cad_objects import (
    OCP_Edges,
    OCP_Faces,
    OCP_Part,
    OCP_PartGroup,
    OCP_Vertices,
    OcpWrapper,
)
from ocp_tessellate.convert import (
    Progress,
    combined_bb,
    tessellate_group,
    to_ocpgroup,
)
from ocp_tessellate.ocp_utils import (
    is_build123d,
    is_build123d_axis,
    is_build123d_location,
    is_build123d_locationlist,
    is_build123d_plane,
    is_cadquery,
    is_cadquery_assembly,
    is_cadquery_sketch,
    is_toploc_location,
    is_topods_compound,
    is_topods_shape,
    is_vector,
    nested_bounding_box,
)
from ocp_tessellate.utils import Color, Timer, numpy_to_buffer_json
from threejs_materials import PbrProperties

from .animation import Animation
from .colors import BaseColorMap
from .comms import Comms, H, is_pytest
from .config import Camera, Collapse, Config, Render

# This module reaches OCP, through ocp_tessellate. That is why the package's
# `__init__` does not import it: a host that only needs config or comms must not
# pay for the kernel. See the note in `__init__.py`.

__all__ = [
    "BaseColorMap",
    "ShowProgress",
    "Viewer",
    "align_attrs",
    "ignore_camera_warnings",
    "none_filter",
]


# ============================ Warnings ============================ #
#
# These stay module-level rather than becoming instance state, and deliberately:
# `warnings` is a process-wide registry, and "warn once per session" means once
# per process. Two Viewers in one process warning twice about the same thing
# would be a regression, not isolation. Contrast the show state below, which is
# per-Viewer precisely because two Viewers must not share a camera or a stack.


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


def is_drawable(obj):
    """Whether the tessellator could make anything of this value.

    A whitelist of what is known to tessellate rather than a blacklist of what
    obviously does not - the tessellator's own predicates, asked of the package
    that owns them.

    It exists for containers. `show_all` walks a scope and used to accept any
    `list`, `tuple` or `dict` on sight, and a scope is full of lists of numbers:
    one of those reaches `_convert`, which produces a model with a header and no
    geometry, and three-cad-viewer does not come back from one - the application
    it was found in had to be force-quit. A container is drawable when its
    contents are, and an empty one is not.

    It came from build123d Studio, which had written the recursive version for
    itself; this is the one place the golden master is deliberately not
    preserved.
    """
    if isinstance(obj, (list, tuple)):
        return len(obj) > 0 and all(is_drawable(item) for item in obj)
    if isinstance(obj, dict):
        # By value: the keys become names in the viewer's tree, and a mapping of
        # shapes is an ordinary way to hold an assembly.
        return len(obj) > 0 and all(is_drawable(item) for item in obj.values())
    if hasattr(obj, "wrapped") and (
        is_topods_shape(obj.wrapped)
        or is_topods_compound(obj.wrapped)
        or is_toploc_location(obj.wrapped)
    ):
        return True
    for test in (
        is_build123d,
        is_build123d_axis,
        is_build123d_location,
        is_build123d_locationlist,
        is_build123d_plane,
        is_cadquery,
        is_cadquery_assembly,
        is_cadquery_sketch,
        is_vector,
    ):
        try:
            if test(obj):
                return True
        except Exception:  # noqa: BLE001,S112 - a test that dislikes a value is a no
            continue
    return False


def same_bounding_box(bb1, bb2, tol=1e-6):
    """Whether two bounding boxes (dicts with xmin/ymin/zmin/xmax/ymax/zmax) match
    within a diagonal-relative tolerance. Either being None → False.

    Used as the "same model" heuristic deciding whether to keep the viewer's current
    clip settings on a reset_camera=KEEP show: same bbox ⇒ same clip-slider range, so
    keeping the current clip values makes sense regardless of the exact geometry.
    """
    if bb1 is None or bb2 is None:
        return False
    diag = math.hypot(
        bb1["xmax"] - bb1["xmin"],
        bb1["ymax"] - bb1["ymin"],
        bb1["zmax"] - bb1["zmin"],
    )
    eps = tol * max(1.0, diag)
    return all(
        abs(bb1[k] - bb2[k]) <= eps
        for k in ("xmin", "ymin", "zmin", "xmax", "ymax", "zmax")
    )


def check_camera_warnings(old_bb, new_bb):
    """Check if new bounding box may cause visibility issues with fixed camera.

    Takes the previous bounding box as an argument rather than reading it from a
    module global. That global is now `Viewer.LAST_BBOX` - per-Viewer state, so
    two Viewers in one process no longer compare each other's models - and a
    function that reached for it would have to be handed a Viewer to do so.
    """

    if old_bb is None:
        return

    # Diagonal comparison
    old_diag = math.hypot(
        old_bb["xmax"] - old_bb["xmin"],
        old_bb["ymax"] - old_bb["ymin"],
        old_bb["zmax"] - old_bb["zmin"],
    )
    new_diag = math.hypot(
        new_bb["xmax"] - new_bb["xmin"],
        new_bb["ymax"] - new_bb["ymin"],
        new_bb["zmax"] - new_bb["zmin"],
    )
    if old_diag > 0:
        ratio = new_diag / old_diag
        if ratio < 0.01:
            camera_warning(
                "Object may be too small to see (%.1f%% of previous size). Skip warnings with `ignore_camera_warnings()`"
                % (ratio * 100)
            )
        elif ratio > 1.5:
            camera_warning(
                "Object may extend beyond view (%.1f%% of previous size). Skip warnings with `ignore_camera_warnings()`"
                % (ratio * 100)
            )
    # Overlap check
    overlap = (
        max(old_bb["xmin"], new_bb["xmin"]) < min(old_bb["xmax"], new_bb["xmax"])
        and max(old_bb["ymin"], new_bb["ymin"]) < min(old_bb["ymax"], new_bb["ymax"])
        and max(old_bb["zmin"], new_bb["zmin"]) < min(old_bb["zmax"], new_bb["zmax"])
    )
    if not overlap:
        camera_warning(
            "Object may be outside visible area (no overlap with previous view). Skip warnings with `ignore_camera_warnings()`"
        )


# ========================= Small shared helpers ========================= #


# To avoid a dependency on build123d
def is_build123d_material(material):
    """Duck-type test for a build123d Material, so the core need not import build123d."""
    return (
        hasattr(material, "pbr")
        and hasattr(material, "finish")
        and hasattr(material, "material")
    )


class ShowProgress(Progress):
    """Progress indicator for tessellation"""

    def __init__(self, levels=None):
        if levels is None:
            self.levels = "+c-*"
        else:
            self.levels = levels

    def update(self, mark="+"):
        """Update progress indicator"""
        if mark in self.levels:
            print(mark, end="", flush=True)

    @property
    def none(self):
        return self.levels == ""


_MODE_STATES = {
    Render.ALL: (1, 1),
    Render.EDGES: (0, 1),
    Render.FACES: (1, 0),
    Render.NONE: (0, 0),
}


def _apply_mode_to_node(node, state_faces, state_edges):
    """Recursively set state_faces/state_edges on all OcpObject leaves."""
    if isinstance(node, OcpGroup):
        for obj in node.objects:
            _apply_mode_to_node(obj, state_faces, state_edges)
    else:
        node.state_faces = state_faces
        node.state_edges = state_edges


def _apply_mode(part_group, mode_list):
    """Apply per-object mode settings to the top-level entries of part_group.

    Currently unreachable: `_show` turns each mode into its `_MODE_STATES` pair
    and hands the pairs to `to_ocpgroup`, which applies them while building the
    tree. Kept because per-object modes are part of this module's contract and
    a caller may want to apply them to an already-built group.
    """
    for i, mode in enumerate(mode_list):
        if mode is None or i >= len(part_group.objects):
            continue
        state_faces, state_edges = _MODE_STATES[mode]
        _apply_mode_to_node(part_group.objects[i], state_faces, state_edges)


def _extract_materials_from_node(node, extracted, id_to_key, name_counts):
    """Recursively replace Material objects on OcpObject.material with string keys.
    Supported materials:
    - threejs-materials PbrProperties
    - py-materials Material
    - build123d Material
    """
    if isinstance(node, OcpGroup):
        for child in node.objects:
            _extract_materials_from_node(child, extracted, id_to_key, name_counts)
    else:
        if not hasattr(node, "material"):
            return

        if node.material is None or isinstance(node.material, str):
            return

        # threejs-material.PbrProperties
        if isinstance(node.material, PbrProperties):
            mat = node.material
            node.normalize_uvs = mat.normalize_uvs

        elif is_build123d_material(node.material):
            mat = node.material.pbr
            node.normalize_uvs = mat.normalize_uvs
        else:
            print(f"Unkonwn material {type(node.material)}")

        mat_dict = mat.to_dict()
        mat_content_key = mat.to_json(sort_keys=True)
        if mat_content_key in id_to_key:
            node.material = id_to_key[mat_content_key]
        else:
            base_name = mat.name
            if base_name not in name_counts:
                key = base_name
                name_counts[base_name] = 2
            else:
                key = f"{base_name}_{name_counts[base_name]}"
                name_counts[base_name] += 1
            extracted[key] = mat_dict
            id_to_key[mat_content_key] = key
            node.material = key


def _extract_material_objects(part_group):
    """Extract Material objects from OcpGroup tree, replacing them with string keys.

    Returns dict mapping string keys to Material objects, or None if none found.
    """
    extracted = {}
    _extract_materials_from_node(part_group, extracted, {}, {})
    return extracted if extracted else None


def _collect_paths(node, path):
    """All paths in a nested OcpGroup/OcpObject tree, root first."""
    results = []
    current_path = f"{path}/{node.name}"

    if isinstance(node, OcpGroup):
        results.append(current_path)
        for obj in node.objects:
            results.extend(_collect_paths(obj, current_path))
    else:  # OcpObject
        results.append(current_path)

    return results


def align_attrs(attr_list, length, default, tag, explode=True):
    """Align attributes to the length of the cad_objs"""
    if attr_list is None:
        return [None] * length if explode else None
    elif len(attr_list) < length:
        print(f"Too few {tag}, using defaults to fill")
        return list(attr_list) + [default] * (length - len(attr_list))
    elif len(attr_list) > length:
        print(f"Too many {tag}, trimming to length {length}")
        return attr_list[:length]
    else:
        return attr_list


def none_filter(d, excludes=None):
    if excludes is None:
        excludes = []
    return {
        k: v
        for k, v in dict(d).items()
        if v is not None and not callable(v) and k not in excludes
    }


def _take_color_default(kwargs, conf, key):
    """The value for one of ocp_tessellate's three "shown on its own" colors.

    An explicit keyword to `show` wins over the workspace config, and is
    *removed* from kwargs when used. That removal matters: whatever stays in
    kwargs is later copied into the params the renderer receives, so a value
    taken from the workspace config reaches it and an explicit one does not.

    Returning None when neither source says anything leaves ocp_tessellate to
    apply its own precedence - `set_defaults`, then its module constant.
    """
    if kwargs.get(key) is not None:
        value = kwargs[key]
        del kwargs[key]
    else:
        value = conf.get(key)
    return None if value is None else Color(value).percentage


class Viewer(Generic[H]):
    """The show pipeline over one host's transport.

    Everything the module-level functions in `ocp_vscode/show.py` reached for
    through globals is instance state here: the incremental object stack, the
    last bounding box, the last tessellated paths, the colormap and the
    last-call marker. Two Viewers in one process - two notebook sidecars, a
    kernel and a debuggee - no longer overwrite each other's, which is the
    defect this class exists to close.

    `H` is the host's viewer handle, carried from `Comms`. `show` returns
    `H | None`, so a host whose transport hands a widget back gives its users
    a widget with the right type on it, and a host with nothing to return gives
    them None - from one signature and with no branch. Bind it at construction:
    `Viewer[MyWidget](config)`.

    The bound methods are the public surface: a host does `show = viewer.show`
    and its users keep the full keyword signature, completion and hover.
    `functools.partial`, `functools.wraps` and `**kwargs` all lose that under a
    static analyser, which is why the ~50 keywords below are written out three
    times rather than forwarded.
    """

    def __init__(self, config: Config):
        # The session cache lasts exactly one show, which is what makes it
        # safe: `_splash` is true only while the logo is up, so an answer held
        # across shows would force a camera reset and discard every explicit
        # `reset_camera=`. `_show` clears it in a finally, and is the single
        # choke point every model send routes through.
        self.config = config
        # Annotated rather than inferred: `Session.comms` is a bare `Comms`, so
        # the handle type would otherwise be lost here and every `show` would
        # return Unknown. Making `Session` and `Config` generic in `H` would
        # carry it automatically.
        self.comms: Comms[H] = config.session.comms

        # The stack `show_object` and `push_object` accumulate into.
        self.objects = {
            "objs": [],
            "names": [],
            "colors": [],
            "alphas": [],
            "modes": [],
            "materials": [],
        }

        # Whether the previous call was a real `show`. `show_all(_visual_debug=True)`
        # reads it to skip the debugger's automatic step right after a user's show.
        self.last_call = "other"

        # The previous model's bounding box, used for the "same model" test that
        # decides whether the viewer's clip insight survives a KEEP show, and for
        # the camera visibility warnings.
        self.last_bbox = None

        # Every path in the last tessellated tree, in tree order. The animation
        # module reads it to resolve a path a user names.
        self.last_paths = []

        # The colormap `show` and `show_object` draw per-object colors from.
        self.colormap = None

    # ============================ Colormap ============================ #

    def get_colormap(self):
        """Get the current colormap.

        Resets it as a side effect, so that every `show` starts at the first
        color rather than continuing where the previous one stopped. Removing
        the reset would make a second `show` of the same objects draw them in
        different colors.
        """
        if self.colormap is not None:
            self.colormap.reset()
        return self.colormap

    def set_colormap(self, colormap):
        """Set the current colormap"""
        self.colormap = colormap

    def unset_colormap(self):
        """Unset the current colormap"""
        self.colormap = None

    def get_last_paths(self):
        """The paths of the last tessellated tree, for the animation module."""
        return self.last_paths

    def animation(self, assembly=None) -> Animation:
        """An Animation over the objects of the last show.

        A host exports this bound method as `Animation`, so that
        `Animation()` reads as a constructor everywhere while the instance
        knows which viewer it animates - the same shape as the show family.
        """
        return Animation(self, assembly)

    # =========================== Tessellation =========================== #

    def _tessellate(
        self,
        *cad_objs,
        names=None,
        colors=None,
        alphas=None,
        modes=None,
        materials=None,
        progress=None,
        **kwargs,
    ):
        conf = self.config.combined_config()
        if conf.get("_splash"):
            if conf.get("reset_camera") not in [
                Camera.ISO,
                Camera.LEFT,
                Camera.RIGHT,
                Camera.BACK,
                Camera.FRONT,
                Camera.TOP,
                Camera.BOTTOM,
            ]:
                reset_camera = Camera.RESET
            else:
                reset_camera = conf.get("reset_camera")
        else:
            reset_camera = conf.get("reset_camera", Camera.KEEP)

        conf["reset_camera"] = reset_camera.value

        collapse = conf.get("collapse", Collapse.ROOT)
        conf["collapse"] = collapse.value

        # Passed as parameters rather than by assigning ocp_tessellate's
        # FACE_COLOR, THICK_EDGE_COLOR and VERTEX_COLOR module globals: those
        # are another package's state and rewriting them on every show lets two
        # Viewers in one process overwrite each other's colours. Requires
        # ocp_tessellate 3.5.0, which added these to `to_ocp`, `to_ocpgroup` and
        # `to_assembly`.
        default_facecolor = _take_color_default(kwargs, conf, "default_facecolor")
        default_thickedgecolor = _take_color_default(
            kwargs, conf, "default_thickedgecolor"
        )
        default_vertexcolor = _take_color_default(kwargs, conf, "default_vertexcolor")

        if kwargs.get("helper_scale") is not None:
            conf["helper_scale"] = kwargs["helper_scale"]

        timeit = self.config.preset("timeit", kwargs.get("timeit"))

        if timeit is None:
            timeit = False

        with Timer(timeit, "", "to_ocpgroup", 1):
            changed_config = self.config.get_changed_config()

            if (
                isinstance(conf.get("helper_scale"), float)
                and conf.get("helper_scale") < 1.0
            ):
                bb = nested_bounding_box(cad_objs)
                if bb.max_dist_from_center() > 1e50:
                    helper_scale = 1.0
                    print(
                        "Warning: Infinite objects detected with helper_scale < 1.0: Setting helper_scale to 1"
                    )
                if bb.max_dist_from_center() < 1e-6:
                    helper_scale = 1.0
                    print(
                        "Warning: Very small objects detected with helper_scale < 1.0: Setting helper_scale to 1"
                    )
                else:
                    helper_scale = bb.max_dist_from_center() * conf.get("helper_scale")
                    if kwargs.get("debug"):
                        print(f"Helper scale set to {helper_scale}")
            else:
                helper_scale = kwargs.get(
                    "helper_scale", changed_config.get("helper_scale")
                )

            part_group, instances = to_ocpgroup(
                *cad_objs,
                names=names,
                colors=colors,
                alphas=alphas,
                materials=materials,
                modes=modes,
                render_mates=kwargs.get(
                    "render_mates", changed_config.get("render_mates")
                ),
                render_joints=kwargs.get(
                    "render_joints", changed_config.get("render_joints")
                ),
                helper_scale=helper_scale,
                default_color=kwargs.get(
                    "default_color", changed_config.get("default_color")
                ),
                default_facecolor=default_facecolor,
                default_thickedgecolor=default_thickedgecolor,
                default_vertexcolor=default_vertexcolor,
                show_parent=kwargs.get(
                    "show_parent", changed_config.get("show_parent")
                ),
                show_locals=kwargs.get(
                    "show_locals", changed_config.get("show_locals")
                ),
                progress=progress,
                debug=kwargs.get("debug", False),
            )

        self.last_paths = _collect_paths(part_group, "")

        extracted_materials = _extract_material_objects(part_group)

        # The keys this host owns rather than the user: a panel decides its own
        # geometry, where a notebook cell is told one. The host supplies the
        # list, so nothing here needs to know which host it is running in.
        exclude_keys = self.config.exclude_keys
        params = {
            k: v
            for k, v in conf.items()
            if not (k in ("position", "quaternion", "target") or k in exclude_keys)
        }

        for k, v in kwargs.items():
            refusal = self.config.validate_keyword(k)
            if refusal is not None:
                # Asked rather than tested, so that a host can say why. A panel
                # decides its own width; a notebook has no port at all, and the
                # two deserve different sentences.
                print(refusal)

            elif v is not None:
                if k == "reset_camera" and params.get("_splash") is True:
                    # do not keep the position and rotation of the splash screen
                    continue
                params[k] = v

        params["_splash"] = False  # after the first show, _splash is False

        # replace enums with their values
        #
        # Every enum-valued key belongs here, including `collapse` - which is
        # unwrapped earlier on the *config* path and was missing here, so a
        # `collapse=` keyword rode out as a Collapse. Nothing broke, because
        # both transports happen to rescue it: orjson's `default` unwraps any
        # Enum and Jupyter CadQuery's `_collapse_to_letter` handles one on
        # purpose. A host serialising with plain json.dumps - the next one to
        # adopt - would have got a TypeError instead.
        for key in (
            "studio_environment",
            "studio_background",
            "studio_tone_mapping",
            "studio_texture_mapping",
            "analysis_tool",
            "tab",
            "reset_camera",
            "collapse",
        ):
            if isinstance(params.get(key), Enum):
                params[key] = params[key].value

        # Always compute edges so per-object mode and UI toggling work
        params["render_edges"] = True

        if kwargs.get("debug") is not None and kwargs["debug"]:
            print("\ntessellation parameters:\n", params)

        with Timer(timeit, "", "tessellate", 1):
            # `instances` is rebound to the tessellated form here.
            instances, shapes, mapping = tessellate_group(
                part_group, instances, params, progress, params.get("timeit", False)
            )

        # `params["states"]` is normally populated from `conf["states"]` (the
        # user's current tree selections, pulled from status() via combined_config
        # — see keys.CONFIG, which is what survives that filter). This preserves
        # interactive deselections across show() calls.
        #
        # If the user passed `modes=`, override with mode-derived states so the
        # tree visibility actually reflects the requested render modes.
        #
        # `modes` becomes a list-of-Nones via align_attrs() even when the user
        # didn't pass `modes=`, so gate on "any actual mode" not "is not None".
        if modes is not None and any(m is not None for m in modes):
            params["states"] = part_group.to_state()

        # Read, not computed: the tessellator has already turned
        # `render_normals` and `deviation` into a length by this point -
        # `max_accuracy / deviation * 4 if render_normals else 0`. The
        # `get_normal_len` this replaces took all three and used only `shapes`,
        # so the two preset lookups were resolved and discarded, and the call
        # read as though `render_normals` were still being consulted here.
        # ocp_tessellate's own TODO asks for exactly this.
        params["normal_len"] = shapes["normal_len"]

        with Timer(timeit, "", "bb", 1):
            bb = combined_bb(shapes)
            if bb is None:
                bb = {
                    "xmin": -1e-6,
                    "ymin": -1e-6,
                    "zmin": -1e-6,
                    "xmax": 1e-6,
                    "ymax": 1e-6,
                    "zmax": 1e-6,
                }
            else:
                bb = bb.to_dict()

        # add global bounding box
        shapes["bb"] = bb

        # clip_slider_* / clip_normal_* are model-dependent "insight" params: a slider
        # position or plane normal only makes sense for a given geometry. Keep the
        # viewer's current values only when keeping the camera AND it's the same model
        # (reset_camera==KEEP is reused as the "keep insight" signal); otherwise reset
        # them to the defaults (+ explicit kwargs). The clip checkboxes (intersection /
        # planes / object_colors) and zebra are viewer modes like axes/transparent —
        # they always persist via the viewer status and are NOT reset here. Compared
        # BEFORE self.last_bbox is updated below, so it is still the previous model.
        same_model = same_bounding_box(bb, self.last_bbox)
        if not (
            (reset_camera == Camera.KEEP or kwargs.get("reset_camera") == Camera.KEEP)
            and same_model
        ):
            insight_keys = [
                "clip_slider_0",
                "clip_slider_1",
                "clip_slider_2",
                "clip_normal_0",
                "clip_normal_1",
                "clip_normal_2",
            ]
            clip_defaults = {
                k: v for k, v in self.config.get_defaults().items() if k in insight_keys
            }

            for key in insight_keys:
                if params.get(key) is not None:
                    del params[key]

            # Reset the model-dependent clip insight to defaults (+ explicit kwargs)
            params.update(clip_defaults)

            for k, v in kwargs.items():
                if k in insight_keys:
                    params[k] = v

        if params["reset_camera"] == "keep":
            camera_keep_warning(
                "reset_camera is set to KEEP. If shown objects are not visible use "
                "the 'resize' and a 'view' button"
            )
            check_camera_warnings(self.last_bbox, bb)
        self.last_bbox = bb

        return (
            instances,
            shapes,
            params,
            part_group.count_shapes(),
            mapping,
            extracted_materials,
        )

    def _convert(
        self,
        *cad_objs,
        names=None,
        colors=None,
        alphas=None,
        modes=None,
        materials=None,
        progress=None,
        **kwargs,
    ):
        timeit = self.config.preset("timeit", kwargs.get("timeit"))

        instances, shapes, config, count_shapes, mapping, extracted_materials = (
            self._tessellate(
                *cad_objs,
                names=names,
                colors=colors,
                alphas=alphas,
                modes=modes,
                materials=materials,
                progress=progress,
                **kwargs,
            )
        )

        if extracted_materials:
            shapes["materials"] = extracted_materials

        # `orbit_control` is a boolean and the renderer takes a name, so this is
        # a change of value rather than of name and the key mapping cannot
        # express it. It used to sit in an `elif` behind a `dark` branch, which
        # meant a config carrying `dark` silently skipped it - unreachable in
        # practice only because nothing had produced `dark` since 2025.
        if config.get("orbit_control") is not None:
            # Popped, not copied. Both keys map to `control` on the way out -
            # this one by the rename in keys.ALL, the renderer's name by the
            # mechanical fallback - so leaving both meant whichever came last in
            # the dict won. A host that sends `control` in its workspace config,
            # as the VS Code extension does, put the boolean there and
            # three-cad-viewer's `switch (type)` matched neither case, leaving
            # its controls unbuilt.
            config["control"] = (
                "orbit" if config.pop("orbit_control") else "trackball"
            )

        if config.get("debug") is not None and config["debug"]:
            print("\nconfig:\n", config)

        if kwargs.get("explode") is not None:
            config["explode"] = kwargs["explode"]
        if kwargs.get("analysis_tool") is not None:
            val = kwargs["analysis_tool"]
            config["analysis_tool"] = val.value if isinstance(val, Enum) else val

        with Timer(timeit, "", "create data obj", 1):
            if is_pytest():
                return (instances, shapes, config, count_shapes), mapping
            data = numpy_to_buffer_json(
                {"instances": instances, "shapes": shapes},
            )
            return {
                "data": data,
                "type": "data",
                "config": config,
                "count": count_shapes,
            }, mapping

    # ============================== show ============================== #

    # pylint: disable=unused-argument
    def show(
        self,
        *cad_objs,
        names=None,
        colors=None,
        alphas=None,
        modes=None,
        materials=None,
        # Host keywords. The signature is the superset of what every client
        # takes, so one definition serves all of them: a host acts on the ones
        # it owns, and `Config.validate_keyword` refuses the others by name.
        # `cad_width` and `height` are a surface's own in a panel or a browser
        # window, and a caller's in a notebook cell - which is the clearest case
        # for why the list is per host rather than per key.
        port=None,
        viewer=None,
        anchor=None,
        cad_width=None,
        height=None,
        pinning=None,
        theme=None,
        progress="-+*c",
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
        explode=None,
        analysis_tool=None,
        tab=None,
        ticks=None,
        center_grid=None,
        grid_font_size=None,
        up=None,
        zoom=None,
        position=None,
        quaternion=None,
        target=None,
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
        default_facecolor=None,
        default_thickedgecolor=None,
        default_vertexcolor=None,
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
        _force_in_debug=False,
    ) -> H | None:
        # pylint: disable=line-too-long
        """Show CAD objects in the viewer
        Parameters
            cad_objs:                All cad objects that should be shown as positional parameters

        Keywords for show:
            names:                   List of names for the cad_objs. Needs to have the same length as cad_objs
            colors:                  List of colors for the cad_objs. Needs to have the same length as cad_objs
            alphas:                  List of alpha values for the cad_objs. Needs to have the same length as cad_objs
            modes:                   A Render value or list of Render values for the cad_objs (default=None, i.e. Render.ALL).
                                     Render.ALL: show faces and edges
                                     Render.EDGES: show edges only
                                     Render.FACES: show faces only
                                     Render.NONE: hide object
            materials:               List of Material objects or material name strings for the cad_objs. Needs to have the same length as cad_objs (default=None)
            progress:                Show progress of tessellation with None is no progress indicator. (default="-+*c")
                                     for object: "-": is reference,
                                                 "+": gets tessellated with Python code,
                                                 "*": gets tessellated with native code,
                                                 "c": from cache
            port:                    The viewer to address, for a host that runs more than one
            viewer:                  The sidecar to draw into, for a host that has sidecars
            anchor:                  Where to open that sidecar
            cad_width:               Width of the viewer, where the caller decides it
            height:                  Height of the viewer, where the caller decides it
            pinning:                 Whether the view can be pinned as a PNG
            theme:                   "light", "dark" or "browser"

        Valid keywords to configure the viewer (**kwargs):
        - UI
            glass:                   Use glass mode where tree is an overlay over the cad object (default=False)
            tools:                   Show tools (default=True)
            tree_width:              Width of the object tree (default=240)

        - Viewer
            axes:                    Show axes (default=False)
            axes0:                   Show axes at (0,0,0) (default=False)
            grid:                    Show grid (default=False)
            ortho:                   Use orthographic projections (default=True)
            transparent:             Show objects transparent (default=False)
            default_opacity:         Opacity value for transparent objects (default=0.5)
            black_edges:             Show edges in black color (default=False)
            orbit_control:           Mouse control use "orbit" control instead of "trackball" control (default=False)
            collapse:                Collapse.LEAVES: collapse all single leaf nodes,
                                     Collapse.ROOT: expand root only,
                                     Collapse.ALL: collapse all nodes,
                                     Collapse.NONE: expand all nodes
                                     (default=Collapse.ROOT)
            ticks:                   Hint for the number of ticks in both directions (default=5)
            center_grid:             Center the grid at the origin or center of mass (default=False)
            grid_font_size:          Size for the font used for grid axis labels (default=12)
            up:                      Use z-axis ('Z') or y-axis ('Y') as up direction for the camera (default="Z")
            explode:                 Turn on explode mode (default=False)
            analysis_tool:           Activate one of the analysis tools (mutually exclusive
                                     with explode=True):
                                     AnalysisTool.PROPERTIES, AnalysisTool.DISTANCE,
                                     AnalysisTool.SELECT, AnalysisTool.OFF.
                                     String values also accepted ("properties", "distance",
                                     "select", "off"). Default=None (no change).
            tab:                     Switch the side panel tab:
                                     UiTab.TREE, UiTab.CLIP, UiTab.ZEBRA, UiTab.MATERIAL,
                                     UiTab.STUDIO. String values also accepted
                                     ("tree", "clip", "zebra", "material", "studio").
                                     Default=None (no change).

            zoom:                    Zoom factor of view (default=1.0)
            position:                Camera position
            quaternion:              Camera orientation as quaternion
            target:                  Camera look at target
            reset_camera:            Camera.RESET: Reset camera position, rotation, zoom and target
                                     Camera.CENTER: Keep camera position, rotation, zoom, but look at center
                                     Camera.KEEP: Keep camera position, rotation, zoom, and target
                                     Or, choose one of the presets Camera.ISO, Camera.LEFT, Camera.RIGHT,
                                     Camera.TOP, Camera.BOTTOM, Camera.FRONT, Camera.BACK
                                     (default=Camera.RESET)

            clip_slider_0:           Setting of clipping slider 0 (default=None)
            clip_slider_1:           Setting of clipping slider 1 (default=None)
            clip_slider_2:           Setting of clipping slider 2 (default=None)
            clip_normal_0:           Setting of clipping normal 0 (default=None)
            clip_normal_1:           Setting of clipping normal 1 (default=None)
            clip_normal_2:           Setting of clipping normal 2 (default=None)
            clip_intersection:       Use clipping intersection mode (default=False)
            clip_planes:             Show clipping plane helpers (default=False)
            clip_object_colors:      Use object color for clipping caps (default=False)

            zebra_count:             Setting of zebra stripe count (default=9, range: 2-50)
            zebra_opacity:           Setting of zebra opacity (default=1, range: 0-1)
            zebra_direction:         Setting of zebra direction angle (default=0, range: 0-90)
            zebra_color_scheme:      Zebra color scheme: "blackwhite", "grayscale", or "colorful" (default="blackwhite")
            zebra_mapping_mode:      Zebra mapping mode: "reflection" or "normal" (default="reflection")

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

            pan_speed:               Speed of mouse panning (default=1)
            rotate_speed:            Speed of mouse rotate (default=1)
            zoom_speed:              Speed of mouse zoom (default=1)

        - Renderer
            deviation:               Shapes: Deviation from linear deflection value (default=0.1)
            angular_tolerance:       Shapes: Angular deflection in radians for tessellation (default=0.2)
            edge_accuracy:           Edges: Precision of edge discretization (default: mesh quality / 100)

            default_color:           Default mesh color (default=(232, 176, 36))
            default_edgecolor:       Default color of the edges of a mesh (default=#707070)
            default_facecolor:       Default color of faces (default=#ee82ee)
            default_thickedgecolor:  Default color of thick edges (default=#ba55d3)
            default_vertexcolor:     Default color of vertices (default=#ba55d3)
            ambient_intensity:       Intensity of ambient light (default=1.00)
            direct_intensity:        Intensity of direct light (default=1.10)
            metalness:               Metalness property of the default material (default=0.30)
            roughness:               Roughness property of the default material (default=0.65)

            render_edges:            Deprecated, use modes=Render.FACES or Render.ALL instead
            render_normals:          Render normals (default=False)
            render_mates:            Render mates for MAssemblies (default=False)
            render_joints:           Render build123d joints (default=False)
            show_parent:             Render parent of faces, edges or vertices as wireframe (default=False)
            show_locals:             In build123d show local part/sketch/line in addition to the relocated
                                     object (default=True)
            helper_scale:            Scale of rendered helpers (locations, axis, mates for MAssemblies) (default=1)
                                     If it is a float < 1, used the max distance to nested bounding box times
                                     helper_scale to determine the absolut value of it
        - Debug
            debug:                   Show debug statements in the viewer's browser console (default=False)
            timeit:                  Show timing information from level 0-3 (default=False)
        """

        self.config.validate_tool_args(explode, analysis_tool)
        return self._show(*cad_objs, **none_filter(locals(), ["cad_objs", "self"]))

    def _show(self, *cad_objs, **kwargs) -> H | None:
        """Send one model, and forget what this show read.

        Every model send routes through here - `show` calls it directly, and
        `_show_object` and `show_objects` reach it through `show` - so it is the
        one place the session cache can be scoped to a single show. That scope
        is the whole reason the cache is safe: `_splash` is true only while the
        logo is up, and answers held across shows would keep forcing a camera
        reset and discard every explicit `reset_camera=`.

        In a `finally`, because a show that raises must not leave the next one
        trusting answers from a viewer that has since moved on.

        `begin` opens the same scope for this call's keywords, so the transport
        can act on the ones that are its own - `port` here, `title` in a
        notebook - from the first read onwards rather than from the model send.
        """
        self.config.session.begin(kwargs)
        try:
            return self._show_impl(*cad_objs, **kwargs)
        finally:
            self.config.session.clear()

    def _show_impl(self, *cad_objs, **kwargs) -> H | None:
        timeit = kwargs.get("timeit")
        names = kwargs.get("names")
        colors = kwargs.get("colors")
        alphas = kwargs.get("alphas")
        materials = kwargs.get("materials")
        modes = kwargs.get("modes")
        default_edgecolor = kwargs.get("default_edgecolor")
        progress = ShowProgress(kwargs.get("progress", "+-*c"))
        _force_in_debug = kwargs.get("_force_in_debug")

        if (
            cad_objs is None
            or len(cad_objs) == 0
            or (
                len(cad_objs) == 1
                and (
                    cad_objs[0] is None
                    or (
                        isinstance(cad_objs[0], (dict, list, tuple, set))
                        and len(cad_objs[0]) == 0
                    )
                )
            )
        ):
            print("show: No CAD objects to show")
            return None

        kwargs = {
            k: v
            for k, v in kwargs.items()
            if v is not None
            and k
            not in [
                "cad_objs",
                "names",
                "colors",
                "alphas",
                "materials",
                "modes",
                "progress",
                "LAST_CALL",
            ]
        }

        kwargs = self.config.check_deprecated(kwargs, _length=len(cad_objs))
        self.config.validate_values(kwargs)
        if modes is None:
            modes = kwargs.pop("modes", None)

        kwargs = self.config.normalize_values(kwargs)

        timeit = self.config.preset("timeit", timeit)

        names = align_attrs(names, len(cad_objs), None, "names")

        modes = align_attrs(modes, len(cad_objs), None, "modes")
        modes = [mode if mode is None else _MODE_STATES[mode] for mode in modes]

        materials = align_attrs(materials, len(cad_objs), None, "materials")

        # Handle colormaps

        if isinstance(colors, BaseColorMap):
            colors = [next(colors) for _ in range(len(cad_objs))]
            alphas = [None] * len(cad_objs)  # alpha is encoded in colors
        else:
            colors = align_attrs(colors, len(cad_objs), None, "colors")
            alphas = align_attrs(alphas, len(cad_objs), None, "alphas")

        map_colors = None
        colormap = self.get_colormap()
        if colormap is not None:
            map_colors = [next(colormap) for _ in range(len(cad_objs))]

        for i in range(len(cad_objs)):
            if colors[i] is None:
                if map_colors is not None:
                    colors[i] = Color(map_colors[i][:3])
                    if alphas[i] is not None:
                        colors[i].a = alphas[i]

                if hasattr(cad_objs[i], "color") and cad_objs[i].color is not None:
                    # ensure that the explicitly given color is kept
                    colors[i] = Color(cad_objs[i].color)
            else:
                colors[i] = Color(colors[i])

            if colors[i] is not None and alphas[i] is not None:
                colors[i].a = alphas[i]

        if default_edgecolor is not None:
            default_edgecolor = Color(default_edgecolor)

        with Timer(timeit, "", "overall"):
            t, mapping = self._convert(
                *cad_objs,
                names=names,
                colors=colors,
                alphas=alphas,
                modes=modes,
                materials=materials,
                progress=progress,
                **kwargs,
            )

            if not _force_in_debug:
                self.last_call = "show"
            else:
                self.last_call = "other"

        if not progress.none:
            print()

        if is_pytest():
            # The one place the `H | None` annotation is not the truth: under
            # the test stub `_convert` returns the tessellation rather than a
            # wire message and nothing is sent, so there is no handle. The tests
            # read that tuple, which is why the signature is not narrowed.
            return (
                t,
                mapping,
            )  # pyright: ignore[reportReturnType]  # ty: ignore[invalid-return-type]

        with Timer(timeit, "", "send"):
            handle = self.config.session.send_data(t, timeit=timeit)

        # `send_data` returning the host's handle is what lets this be one
        # line for every host. One addresses its measurement backend by the
        # widget it was just handed and another by a port; both keep whatever
        # they need inside their own Comms, where knowing about widgets or
        # ports is legitimate.
        self.comms.send_backend({"model": mapping}, timeit=timeit)
        return handle

    def reset_show(self):
        """Reset the stack of objects to be shown"""
        self.objects = {
            "objs": [],
            "names": [],
            "colors": [],
            "alphas": [],
            "modes": [],
            "materials": [],
        }

    # =========================== show_object =========================== #

    # pylint: disable=too-many-locals,too-many-arguments
    def show_object(
        self,
        obj,
        name=None,
        options=None,
        parent=None,
        clear=False,
        update=False,
        mode=None,
        material=None,
        # Host keywords. The signature is the superset of what every client
        # takes, so one definition serves all of them: a host acts on the ones
        # it owns, and `Config.validate_keyword` refuses the others by name.
        # `cad_width` and `height` are a surface's own in a panel or a browser
        # window, and a caller's in a notebook cell - which is the clearest case
        # for why the list is per host rather than per key.
        port=None,
        viewer=None,
        anchor=None,
        cad_width=None,
        height=None,
        pinning=None,
        theme=None,
        progress="-+*c",
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
        explode=None,
        analysis_tool=None,
        tab=None,
        ticks=None,
        center_grid=None,
        grid_font_size=None,
        up=None,
        zoom=None,
        position=None,
        quaternion=None,
        target=None,
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
        default_facecolor=None,
        default_thickedgecolor=None,
        default_vertexcolor=None,
        default_edgecolor=None,
        ambient_intensity=None,
        metalness=None,
        roughness=None,
        direct_intensity=None,
        render_edges=None,
        render_normals=None,
        render_mates=None,
        render_joints=None,
        show_parent=None,
        show_locals=None,
        show_sketch_local=None,  # DEPRECATED
        helper_scale=None,
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
    ) -> H | None:
        # pylint: disable=line-too-long
        """Incrementally show CAD objects in the viewer

        Parameters:
            obj:                     The CAD object to be shown

        Keywords for show_object:
            name:                    The name of the CAD object
            options:                 A dict of color and alpha value: {"alpha":0.5, "color": (64, 164, 223)}
                                     0 <= alpha <= 1.0 and color is a 3-tuple of values between 0 and 255
            parent:                  Add another object, usually the parent of e.g. edges or vertices with alpha=0.25
            clear:                   In interactive mode, clear the stack of objects to be shown
                                     (typically used for the first object)
            update:                  Update the object (remove old version)
            mode:                    A Render value for this object (default=None, i.e. Render.ALL).
                                     Render.ALL: show faces and edges
                                     Render.EDGES: show edges only
                                     Render.FACES: show faces only
                                     Render.NONE: hide object
            material:                Material object or material name string for this object (default=None)
            port:                    The viewer to address, for a host that runs more than one
            viewer:                  The sidecar to draw into, for a host that has sidecars
            anchor:                  Where to open that sidecar
            cad_width:               Width of the viewer, where the caller decides it
            height:                  Height of the viewer, where the caller decides it
            pinning:                 Whether the view can be pinned as a PNG
            theme:                   "light", "dark" or "browser"
            progress:                Show progress of tessellation with None is no progress indicator. (default="-+*c")
                                     for object: "-": is reference,
                                                 "+": gets tessellated with Python code,
                                                 "*": gets tessellated with native code,
                                                 "c": from cache


        Valid keywords to configure the viewer (**kwargs):
        - UI
            glass:                   Use glass mode where tree is an overlay over the cad object (default=False)
            tools:                   Show tools (default=True)
            tree_width:              Width of the object tree (default=240)

        - Viewer
            axes:                    Show axes (default=False)
            axes0:                   Show axes at (0,0,0) (default=False)
            grid:                    Show grid (default=False)
            ortho:                   Use orthographic projections (default=True)
            transparent:             Show objects transparent (default=False)
            default_opacity:         Opacity value for transparent objects (default=0.5)
            black_edges:             Show edges in black color (default=False)
            orbit_control:           Mouse control use "orbit" control instead of "trackball" control (default=False)
            collapse:                Collapse.LEAVES: collapse all single leaf nodes,
                                     Collapse.ROOT: expand root only,
                                     Collapse.ALL: collapse all nodes,
                                     Collapse.NONE: expand all nodes
                                     (default=Collapse.ROOT)
            ticks:                   Hint for the number of ticks in both directions (default=5)
            center_grid:             Center the grid at the origin or center of mass (default=False)
            grid_font_size:          Size for the font used for grid axis labels (default=12)
            up:                      Use z-axis ('Z') or y-axis ('Y') as up direction for the camera (default="Z")
            explode:                 Turn on explode mode (default=False)
            analysis_tool:           Activate one of the analysis tools (mutually exclusive
                                     with explode=True):
                                     AnalysisTool.PROPERTIES, AnalysisTool.DISTANCE,
                                     AnalysisTool.SELECT, AnalysisTool.OFF.
                                     String values also accepted ("properties", "distance",
                                     "select", "off"). Default=None (no change).
            tab:                     Switch the side panel tab:
                                     UiTab.TREE, UiTab.CLIP, UiTab.ZEBRA, UiTab.MATERIAL,
                                     UiTab.STUDIO. String values also accepted
                                     ("tree", "clip", "zebra", "material", "studio").
                                     Default=None (no change).

            zoom:                    Zoom factor of view (default=1.0)
            position:                Camera position
            quaternion:              Camera orientation as quaternion
            target:                  Camera look at target
            reset_camera:            Camera.RESET: Reset camera position, rotation, zoom and target
                                     Camera.CENTER: Keep camera position, rotation, zoom, but look at center
                                     Camera.KEEP: Keep camera position, rotation, zoom, and target
                                     Or, choose one of the presets Camera.ISO, Camera.LEFT, Camera.RIGHT,
                                     Camera.TOP, Camera.BOTTOM, Camera.FRONT, Camera.BACK
                                     (default=Camera.RESET)

            clip_slider_0:           Setting of clipping slider 0 (default=None)
            clip_slider_1:           Setting of clipping slider 1 (default=None)
            clip_slider_2:           Setting of clipping slider 2 (default=None)
            clip_normal_0:           Setting of clipping normal 0 (default=[-1,0,0])
            clip_normal_1:           Setting of clipping normal 1 (default=[0,-1,0])
            clip_normal_2:           Setting of clipping normal 2 (default=[0,0,-1])
            clip_intersection:       Use clipping intersection mode (default=[False])
            clip_planes:             Show clipping plane helpers (default=False)
            clip_object_colors:      Use object color for clipping caps (default=False)

            zebra_count:             Setting of zebra stripe count (default=9, range: 2-50)
            zebra_opacity:           Setting of zebra opacity (default=1, range: 0-1)
            zebra_direction:         Setting of zebra direction angle (default=0, range: 0-90)
            zebra_color_scheme:      Zebra color scheme: "blackwhite", "grayscale", or "colorful" (default="blackwhite")
            zebra_mapping_mode:      Zebra mapping mode: "reflection" or "normal" (default="reflection")

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

            pan_speed:               Speed of mouse panning (default=1)
            rotate_speed:            Speed of mouse rotate (default=1)
            zoom_speed:              Speed of mouse zoom (default=1)

        - Renderer
            deviation:               Shapes: Deviation from linear deflection value (default=0.1)
            angular_tolerance:       Shapes: Angular deflection in radians for tessellation (default=0.2)
            edge_accuracy:           Edges: Precision of edge discretization (default: mesh quality / 100)

            default_color:           Default mesh color (default=(232, 176, 36))
            default_edgecolor:       Default color of the edges of a mesh (default=(128, 128, 128))
            default_facecolor:       Default color of faces (default=#ee82ee / Violet)
            default_thickedgecolor:  Default color of thick edges (default=#ba55d3 / MediumOrchid)
            default_vertexcolor:     Default color of vertices (default=#ba55d3 / MediumOrchid)
            ambient_intensity:       Intensity of ambient light (default=1.00)
            direct_intensity:        Intensity of direct light (default=1.10)
            metalness:               Metalness property of the default material (default=0.30)
            roughness:               Roughness property of the default material (default=0.65)


            render_edges:            Deprecated, use modes=Render.FACES or Render.ALL instead
            render_normals:          Render normals (default=False)
            render_mates:            Render mates for MAssemblies (default=False)
            render_joints:           Render build123d joints (default=False)
            show_parent:             Render parent of faces, edges or vertices as wireframe (default=False)
            show_locals:             In build123d show local part/sketch/line in addition to the relocated
                                     object (default=True)
            helper_scale:            Scale of rendered helpers (locations, axis, mates for MAssemblies) (default=1)
                                     If it is a float < 1, used the max distance to nested bounding box times
                                     helper_scale to determine the absolut value of it
        - Debug
            debug:                   Show debug statements in the viewer's browser console (default=False)
            timeit:                  Show timing information from level 0-3 (default=False)
        """
        self.config.validate_tool_args(explode, analysis_tool)
        return self._show_object(obj, **none_filter(locals(), ["obj", "self"]))

    def remove_object(
        self, name, call_show=False, port=None, progress="-+*c"
    ) -> H | None:
        """Remove object from the stack of objects by name"""
        try:
            index = self.objects["names"].index(name)
            for key in ["objs", "names", "colors", "alphas", "modes", "materials"]:
                del self.objects[key][index]
        except ValueError:
            pass  # Name not found; silently do nothing

        if call_show:
            return self.show(
                *self.objects["objs"],
                names=self.objects["names"],
                colors=self.objects["colors"],
                alphas=self.objects["alphas"],
                modes=self.objects["modes"],
                materials=self.objects["materials"],
                port=port,
                progress=progress,
            )
        return None

    def _show_object(self, obj, **kwargs) -> H | None:
        port = kwargs.get("port")
        name = kwargs.get("name")
        clear = kwargs.get("clear")
        update = kwargs.get("update")
        parent = kwargs.get("parent")
        options = kwargs.get("options")
        progress = kwargs.get("progress")
        mode = kwargs.get("mode")
        material = kwargs.get("material")

        kwargs = {
            k: v
            for k, v in kwargs.items()
            if v is not None
            and k
            not in [
                "obj",
                "name",
                "options",
                "parent",
                "clear",
                "port",
                "progress",
                "update",
                "mode",
                "material",
            ]
        }

        if clear:
            self.reset_show()

        if update:
            self.remove_object(name)

        if parent is not None:
            self.objects["objs"].append(parent)
            self.objects["names"].append("parent")
            self.objects["colors"].append(None)
            self.objects["alphas"].append(None)
            self.objects["modes"].append(None)
            self.objects["materials"].append(None)

        color = None
        alpha = None
        if options is None:
            colormap = self.get_colormap()
            if colormap is not None:
                for _ in range(len(self.objects["names"]) + 1):
                    *color, alpha = next(colormap)
        else:
            color = options.get("color")
            alpha = options.get("alpha", 1.0)
            if options.get("material") is not None:
                material = options.get("material")

        self.objects["objs"].append(obj)
        self.objects["names"].append(name)
        self.objects["colors"].append(color)
        self.objects["alphas"].append(alpha)
        self.objects["modes"].append(mode)
        self.objects["materials"].append(material)

        return self.show(
            *self.objects["objs"],
            names=self.objects["names"],
            colors=self.objects["colors"],
            alphas=self.objects["alphas"],
            modes=self.objects["modes"],
            materials=self.objects["materials"],
            port=port,
            progress=progress,
            **kwargs,
        )

    def push_object(
        self,
        obj,
        name=None,
        color=None,
        alpha=None,
        material=None,
        mode=None,
        clear=False,
        update=False,
    ):
        """
        Adds or updates an object in this Viewer's OBJECTS registry with optional name,
        color, alpha transparency, and display mode.

        Parameters:
            obj: The object to be added or updated. Must have 'name', 'label', 'color', or 'alpha'
                ttributes if corresponding arguments are not provided.
            name (str, optional): The name to associate with the object. If not provided,
                attempts to use 'name' or 'label' attribute of obj.
            color (any, optional): The color to associate with the object. If not provided,
                attempts to use 'color' attribute of obj.
            alpha (float, optional): The alpha (transparency) value for the object. If not provided,
                attempts to use 'alpha' attribute of obj, defaults to 1.0.
            mode (Render, optional): The display mode for this object (Render.ALL, Render.EDGES, Render.FACES,
                Render.NONE). If not provided, defaults to Render.ALL.
            material (Material or str, optional): Material object or name string for this object (default=None).
            clear (bool, optional): If True, clears the OBJECTS registry before adding the new object.
            update (bool, optional): If True, updates an existing object with the same name;
                otherwise, appends as a new object.
        Raises:
            ValueError: If no name is provided and the object does not have a 'name' or 'label' attribute.
        """
        if clear:
            self.reset_show()

        if name is None:
            if hasattr(obj, "name"):
                name = obj.name
            elif hasattr(obj, "label"):
                name = obj.label
            else:
                raise ValueError("No name provided and no name attribute found.")
        if color is None and hasattr(obj, "color"):
            color = obj.color
        if alpha is None:
            if hasattr(obj, "alpha"):
                alpha = obj.alpha
            else:
                alpha = 1.0

        if update:
            index = self.objects["names"].index(name)
            self.objects["objs"][index] = obj
            self.objects["colors"][index] = color
            self.objects["alphas"][index] = alpha
            self.objects["modes"][index] = mode
            self.objects["materials"][index] = material
        else:
            self.objects["objs"].append(obj)
            self.objects["names"].append(name)
            self.objects["colors"].append(color)
            self.objects["alphas"].append(alpha)
            self.objects["modes"].append(mode)
            self.objects["materials"].append(material)

    def show_objects(
        self,
        modes=None,
        # Host keywords. The signature is the superset of what every client
        # takes, so one definition serves all of them: a host acts on the ones
        # it owns, and `Config.validate_keyword` refuses the others by name.
        # `cad_width` and `height` are a surface's own in a panel or a browser
        # window, and a caller's in a notebook cell - which is the clearest case
        # for why the list is per host rather than per key.
        port=None,
        viewer=None,
        anchor=None,
        cad_width=None,
        height=None,
        pinning=None,
        theme=None,
        progress="-+*c",
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
        explode=None,
        analysis_tool=None,
        tab=None,
        ticks=None,
        center_grid=None,
        grid_font_size=None,
        up=None,
        zoom=None,
        position=None,
        quaternion=None,
        target=None,
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
        default_facecolor=None,
        default_thickedgecolor=None,
        default_vertexcolor=None,
        default_edgecolor=None,
        ambient_intensity=None,
        metalness=None,
        roughness=None,
        direct_intensity=None,
        render_edges=None,
        render_normals=None,
        render_mates=None,
        render_joints=None,
        show_parent=None,
        show_locals=None,
        show_sketch_local=None,  # DEPRECATED
        helper_scale=None,
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
    ) -> H | None:
        # pylint: disable=line-too-long
        """Show incrementally pushed CAD objects in the viewer

        Keywords for show_objects:
            progress:                Show progress of tessellation with None is no progress indicator. (default="-+*c")
                                     for object: "-": is reference,
                                                 "+": gets tessellated with Python code,
                                                 "*": gets tessellated with native code,
                                                 "c": from cache


        Valid keywords to configure the viewer (**kwargs):
        - UI
            glass:                   Use glass mode where tree is an overlay over the cad object (default=False)
            tools:                   Show tools (default=True)
            tree_width:              Width of the object tree (default=240)

        - Viewer
            axes:                    Show axes (default=False)
            axes0:                   Show axes at (0,0,0) (default=False)
            grid:                    Show grid (default=False)
            ortho:                   Use orthographic projections (default=True)
            transparent:             Show objects transparent (default=False)
            default_opacity:         Opacity value for transparent objects (default=0.5)
            black_edges:             Show edges in black color (default=False)
            orbit_control:           Mouse control use "orbit" control instead of "trackball" control (default=False)
            collapse:                Collapse.LEAVES: collapse all single leaf nodes,
                                     Collapse.ROOT: expand root only,
                                     Collapse.ALL: collapse all nodes,
                                     Collapse.NONE: expand all nodes
                                     (default=Collapse.ROOT)
            ticks:                   Hint for the number of ticks in both directions (default=5)
            center_grid:             Center the grid at the origin or center of mass (default=False)
            grid_font_size:          Size for the font used for grid axis labels (default=12)
            up:                      Use z-axis ('Z') or y-axis ('Y') as up direction for the camera (default="Z")
            explode:                 Turn on explode mode (default=False)
            analysis_tool:           Activate one of the analysis tools (mutually exclusive
                                     with explode=True):
                                     AnalysisTool.PROPERTIES, AnalysisTool.DISTANCE,
                                     AnalysisTool.SELECT, AnalysisTool.OFF.
                                     String values also accepted ("properties", "distance",
                                     "select", "off"). Default=None (no change).
            tab:                     Switch the side panel tab:
                                     UiTab.TREE, UiTab.CLIP, UiTab.ZEBRA, UiTab.MATERIAL,
                                     UiTab.STUDIO. String values also accepted
                                     ("tree", "clip", "zebra", "material", "studio").
                                     Default=None (no change).

            zoom:                    Zoom factor of view (default=1.0)
            position:                Camera position
            quaternion:              Camera orientation as quaternion
            target:                  Camera look at target
            reset_camera:            Camera.RESET: Reset camera position, rotation, zoom and target
                                     Camera.CENTER: Keep camera position, rotation, zoom, but look at center
                                     Camera.KEEP: Keep camera position, rotation, zoom, and target
                                     Or, choose one of the presets Camera.ISO, Camera.LEFT, Camera.RIGHT,
                                     Camera.TOP, Camera.BOTTOM, Camera.FRONT, Camera.BACK
                                     (default=Camera.RESET)

            clip_slider_0:           Setting of clipping slider 0 (default=None)
            clip_slider_1:           Setting of clipping slider 1 (default=None)
            clip_slider_2:           Setting of clipping slider 2 (default=None)
            clip_normal_0:           Setting of clipping normal 0 (default=[-1,0,0])
            clip_normal_1:           Setting of clipping normal 1 (default=[0,-1,0])
            clip_normal_2:           Setting of clipping normal 2 (default=[0,0,-1])
            clip_intersection:       Use clipping intersection mode (default=[False])
            clip_planes:             Show clipping plane helpers (default=False)
            clip_object_colors:      Use object color for clipping caps (default=False)

            zebra_count:             Setting of zebra stripe count (default=9, range: 2-50)
            zebra_opacity:           Setting of zebra opacity (default=1, range: 0-1)
            zebra_direction:         Setting of zebra direction angle (default=0, range: 0-90)
            zebra_color_scheme:      Zebra color scheme: "blackwhite", "grayscale", or "colorful" (default="blackwhite")
            zebra_mapping_mode:      Zebra mapping mode: "reflection" or "normal" (default="reflection")

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

            pan_speed:               Speed of mouse panning (default=1)
            rotate_speed:            Speed of mouse rotate (default=1)
            zoom_speed:              Speed of mouse zoom (default=1)

        - Renderer
            deviation:               Shapes: Deviation from linear deflection value (default=0.1)
            angular_tolerance:       Shapes: Angular deflection in radians for tessellation (default=0.2)
            edge_accuracy:           Edges: Precision of edge discretization (default: mesh quality / 100)

            default_color:           Default mesh color (default=(232, 176, 36))
            default_edgecolor:       Default color of the edges of a mesh (default=(128, 128, 128))
            default_facecolor:       Default color of faces (default=#ee82ee / Violet)
            default_thickedgecolor:  Default color of thick edges (default=#ba55d3 / MediumOrchid)
            default_vertexcolor:     Default color of vertices (default=#ba55d3 / MediumOrchid)
            ambient_intensity:       Intensity of ambient light (default=1.00)
            direct_intensity:        Intensity of direct light (default=1.10)
            metalness:               Metalness property of the default material (default=0.30)
            roughness:               Roughness property of the default material (default=0.65)


            render_edges:            Deprecated, use modes=Render.FACES or Render.ALL instead
            render_normals:          Render normals (default=False)
            render_mates:            Render mates for MAssemblies (default=False)
            render_joints:           Render build123d joints (default=False)
            show_parent:             Render parent of faces, edges or vertices as wireframe (default=False)
            show_locals:             In build123d show local part/sketch/line in addition to the relocated
                                     object (default=True)
            helper_scale:            Scale of rendered helpers (locations, axis, mates for MAssemblies) (default=1)
                                     If it is a float < 1, used the max distance to nested bounding box times
                                     helper_scale to determine the absolut value of it
        - Debug
            debug:                   Show debug statements in the viewer's browser console (default=False)
            timeit:                  Show timing information from level 0-3 (default=False)
        """
        self.config.validate_tool_args(explode, analysis_tool)
        kwargs = none_filter(locals(), ["self"])
        # Use per-object modes stored in OBJECTS
        stored_modes = self.objects["modes"]
        if any(m is not None for m in stored_modes):
            kwargs["modes"] = stored_modes
        return self.show(
            *self.objects["objs"],
            names=self.objects["names"],
            colors=self.objects["colors"],
            alphas=self.objects["alphas"],
            materials=self.objects["materials"],
            **kwargs,
        )

    def show_clear(self):
        """Clear the viewer"""
        data = {
            "type": "clear",
        }
        self.config.session.send_data(data)

    def show_all(
        self,
        variables=None,
        exclude=None,
        classes=None,
        include=None,
        _visual_debug=False,
        **kwargs,
    ) -> H | None:
        """
        Show all variables in the current scope

        Parameters:
            variables:     Only show objects with names in this list of variable names,
                           i.e. do not use all from locals()
            exclude:       List of variable names to exclude from "show_all"
            classes:       Only show objects which are instances of the classes in this list
            include:       List of variable names to additionally include in "show_all" when classes is None
            _visual_debug: private variable, do not use!

        Keywords for show_all:
            Valid keywords for "show_all" are the same as for "show"
        """
        if not _visual_debug:
            self.last_call = "other"

        if _visual_debug and self.last_call == "show":
            self.last_call = "other"
            print("\nSkip visual debug step after a show() command")
            return None

        if variables is None:
            cf = inspect.currentframe()
            variables = cf.f_back.f_locals  # ty:ignore[unresolved-attribute]

        if exclude is None:
            exclude = []

        objects = []
        names = []
        for name, obj in variables.items():
            if (
                # ignore classes and the interactive shell's own variables
                isinstance(obj, type)
                or name
                in exclude + ["_", "__", "___", "_ih", "_oh", "_dh", "Out", "In"]
                or name.startswith("__")
                or re.search("^_i\\d+", name) is not None
                or re.search("^_\\d+", name) is not None
                # pylint: disable=protected-access
                or (hasattr(obj, "_obj") and obj._obj is None)
                or (hasattr(obj, "_wrapped") and obj._wrapped is None)
                or callable(obj)
                or isinstance(obj, (int, float, str, bool, types.ModuleType))
                or obj is None
                or isinstance(obj, Enum)
                or (
                    obj.__class__.__name__ == "_Feature"
                    and obj.__class__.__module__ == "__future__"
                )
                or isinstance(obj, Logger)
                # A viewer must not be asked to draw itself, and in a notebook
                # the namespace being walked contains the widget. The transport
                # is the one object that can recognise its own handle, and
                # answers False for a host that has none.
                or self.comms.is_handle(obj)
            ):
                continue

            if classes is None or isinstance(obj, tuple(classes)):
                if (
                    (
                        hasattr(obj, "wrapped")
                        and (
                            is_topods_shape(obj.wrapped)
                            or is_topods_compound(obj.wrapped)
                            or is_toploc_location(obj.wrapped)
                        )
                    )
                    or is_build123d_plane(obj)
                    or is_build123d_location(obj)
                    or is_build123d_plane(obj)
                    or is_build123d_axis(obj)
                    or is_build123d_locationlist(obj)
                    or is_vector(obj)  # Vector
                    or is_cadquery(obj)
                    or is_build123d(obj)
                    or is_cadquery_assembly(obj)
                    or (
                        hasattr(obj, "wrapped")
                        and hasattr(obj, "position")
                        and hasattr(obj, "direction")
                    )
                    # A container is drawable when its contents are. Accepting
                    # any list on sight is what let a list of floats through.
                    or (isinstance(obj, (list, tuple, dict)) and is_drawable(obj))
                ):
                    objects.append(obj)
                    names.append(name)

                elif isinstance(
                    obj, (OCP_PartGroup, OCP_Edges, OCP_Faces, OCP_Part, OCP_Vertices)
                ):
                    objects.append(obj)
                    obj.name = name
                    names.append(name)

                elif is_cadquery_sketch(obj):
                    pg, instances = to_ocpgroup([obj], names=[name])
                    pg.name = name
                    objects.append(instances)
                    names.append(name)

                elif isinstance(obj, OcpWrapper):
                    objects.append(obj)
                    names.append(name)

                else:
                    if kwargs.get("debug", False):
                        print(
                            f"show_all: Type {type(obj)} for name {name} cannot be visualized"
                        )

            if (
                classes is not None
                and include is not None
                and isinstance(include, (tuple, list))
                and name in include
                and name not in names
            ):
                objects.append(obj)
                names.append(name)

        if len(objects) > 0:
            try:
                result = self.show(
                    *objects,
                    names=names,
                    collapse=Collapse.ROOT,
                    _force_in_debug=_visual_debug,
                    **kwargs,
                )
                # Whatever the transport returned: a widget for a host that
                # has one, None for a host that does not.
                return result
            except Exception as ex:  # pylint: disable=broad-exception-caught  # noqa: BLE001
                print("show_all:", ex)
                traceback.print_exc()
        else:
            if is_pytest():
                return None
            self.show_clear()
        return None

    def save_screenshot(self, filename, port=None, polling=True, progress_only=False):
        """Save a screenshot of the current view

        `port` is a host keyword like any other: it is handed to the transport
        for the length of this call and means whatever that host makes of it.
        """
        if not filename.startswith(os.sep):
            prefix = pathlib.Path(".").absolute()
            full_path = str(prefix / filename)
        else:
            full_path = filename
        p = pathlib.Path(full_path)
        mtime = p.stat().st_mtime if p.exists() else 0

        self.config.session.begin({"port": port})
        try:
            self.comms.send_command({"type": "screenshot", "filename": f"{full_path}"})
        finally:
            self.config.session.clear()

        if polling:
            done = False
            for i in range(20):
                if p.exists() and p.stat().st_mtime > mtime:
                    if progress_only:
                        print(".", end="")
                    else:
                        print("Screenshot saved to ", full_path)
                    done = True
                    break
                time.sleep(0.1)

            if not done:
                print("Warning: Screenshot not found in 2 seconds, aborting")
