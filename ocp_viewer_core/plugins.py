"""Kernel plugins of the measurement backend: the registry, and what their bodies travel as.

The backend (`backend.py`) answers the viewer's measurement tools from the geometry
behind the mesh. That geometry is OCCT's unless an ocp-tessellate kernel plugin
(`ocp_tessellate.plugin`, e.g. ocp-viewer-smlibpy for SMLib) drew the object; then
the plugin's kernel holds it, and the plugin registers here what the backend needs:

- `serialize(body) -> bytes`: the body as bytes, since every host runs the backend
  in another process than the user's (VS Code's `python -m ocp_vscode --backend`,
  Jupyter CadQuery's server extension, ocp-viewer's server, build123d Studio's
  sidecar) and the model reaches it as JSON
- `load(data, loc) -> (body, faces, edges, vertices)`: the body rebuilt from the bytes
  and moved by `loc` (a translation and a quaternion, as `loc_to_tq` writes them, or
  None), with its faces, edges and vertices in the order the mesh numbers them -
  the viewer selects `{id}/faces/faces_{i}` and the backend answers for index i
- `get_properties(shape)`, `calc_distance(shape1, shape2, center)` and
  `calc_angle(shape1, shape2)`: the measurements, answering in the layout of
  `measure.py`'s functions of the same names

`register_plugin(kernel, ...)` is the one mechanism. A plugin calls it when it is
imported, which covers the process that shows. The backend process imports no user
code, so there it is reached through an entry point of the group
`ocp_viewer_core.backend` named like the kernel, whose value is the plugin's module:
`plugin_of` loads it on the first model that carries the kernel.

The protocol as a whole is described in ExternalKernel.md.

On the wire a kernel body is a model entry whose shape is `{"kernel": tag, "obj":
body}`, as `OcpExternalObject.collect` emits it; `encode_kernel_shapes` turns the body
into base64 of `serialize(body)` before the model is sent, so the codec never sees it.
An OCCT entry has no `kernel` key.

This module is light on purpose: the package root carries it, and it must not load
a kernel (see `__init__.py`).
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

import base64
from collections.abc import Callable
from dataclasses import dataclass
from importlib.metadata import entry_points
from typing import Any

# the entry point group a plugin's package declares, so the backend process finds it:
# `[project.entry-points."ocp_viewer_core.backend"] smlib = "ocp_viewer_smlibpy"`
ENTRY_POINT_GROUP = "ocp_viewer_core.backend"


@dataclass(frozen=True)
class KernelPlugin:
    """The five functions a kernel plugin registers, under its kernel tag."""

    kernel: str
    load: Callable[[bytes, Any], tuple[Any, list[Any], list[Any], list[Any]]]
    serialize: Callable[[Any], bytes]
    get_properties: Callable[[Any], dict[str, Any]]
    calc_distance: Callable[[Any, Any, bool], dict[str, Any]]
    calc_angle: Callable[[Any, Any], dict[str, Any] | None]


PLUGINS: dict[str, KernelPlugin] = {}


def register_plugin(kernel, load, serialize, get_properties, calc_distance, calc_angle) -> None:
    """Register a kernel's backend functions under its tag; a second registration
    of the same tag replaces the first."""
    PLUGINS[kernel] = KernelPlugin(kernel, load, serialize, get_properties, calc_distance, calc_angle)


def plugin_of(kernel: str) -> KernelPlugin:
    """The plugin registered for a kernel, loading its entry point first if it is not.

    LookupError when neither registered nor declared: the message names both ways.
    """
    plugin = PLUGINS.get(kernel)
    if plugin is not None:
        return plugin
    for entry_point in entry_points(group=ENTRY_POINT_GROUP):
        if entry_point.name == kernel:
            # importing the plugin's module is what registers it
            entry_point.load()
            break
    plugin = PLUGINS.get(kernel)
    if plugin is None:
        raise LookupError(
            f"no measurement backend plugin for kernel '{kernel}': the plugin's package "
            f"registers it with ocp_viewer_core.backend.register_plugin when imported, and "
            f"declares an entry point '{kernel}' in the group '{ENTRY_POINT_GROUP}' so the "
            f"backend process can import it"
        )
    return plugin


def is_kernel_shape(shape: Any) -> bool:
    """Whether a model entry's shape belongs to a kernel plugin: `{"kernel": tag, "obj": ...}`."""
    return isinstance(shape, dict) and "kernel" in shape


def encode_kernel_shapes(mapping: dict[str, Any]) -> dict[str, Any]:
    """The mapping with every kernel body replaced by base64 of its `serialize` bytes:
    the pre-pass before the model goes to the backend. OCCT entries are untouched (the
    codec writes them), and the mapping given is not changed."""

    def walk(parts: list[dict[str, Any]]) -> list[dict[str, Any]]:
        result = []
        for part in parts:
            if part.get("parts") is not None:
                result.append({**part, "parts": walk(part["parts"])})
                continue
            shape = part["shape"]
            if is_kernel_shape(shape):
                data = plugin_of(shape["kernel"]).serialize(shape["obj"])
                shape = {"kernel": shape["kernel"], "obj": base64.b64encode(data).decode("utf-8")}
            result.append({**part, "shape": shape})
        return result

    return {**mapping, "parts": walk(mapping["parts"])}
