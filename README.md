# ocp-viewer-core

The shared half of the OCP viewer ecosystem: one show suite, one tessellation, one set of config semantics, used by four viewers that each keep their own transport and their own settings storage.

- **ocp_vscode** — the VS Code extension and its Python client
- **ocp_viewer** — the standalone viewer, `python -m ocp_viewer`
- **Jupyter CadQuery** — through cad-viewer-widget
- **build123d Studio**

Published as one project under one version to two registries: `ocp-viewer-core` on PyPI for the Python half, `ocp-viewer-core` on npm for the JavaScript half. The two are shipped and versioned together, so which version of the pair a host has is one question rather than two.

## The idea

Each host provides a `Comms` — a Python encoder and a JavaScript decoder, shipped as a pair — and a settings source. Everything above that is shared and knows nothing about which host it is running in. **No host is nameable inside this package**: no `port=`/`viewer=` pairs, no `is_jupyter_cadquery`, no environment sniffing, and no host name in a string. A conformance kit enforces that by running the shared half end to end over an in-memory loopback with no host at all.

Per-host imports stay per host: `from ocp_vscode import show` beside `from build123d_studio import show`. A single universal import with the host discovered at runtime is deliberately not offered — it is how a `show()` once silently drew into somebody else's viewer.

## Status

Early development. Nothing here is published, and the API changes without notice until the first host adopts it.

## Layout

| path                        | what                                                                                                |
| --------------------------- | --------------------------------------------------------------------------------------------------- |
| `ocp_viewer_core/`          | the Python half                                                                                     |
| `ocp_viewer_core/config.py` | the config keys, each mapped to the name three-cad-viewer knows it by, and the precedence over them |
| `ocp_viewer_core/comms.py`  | the transport a host implements, and the session that caches what it answers                        |
| `js/`                       | the JavaScript half, published to npm                                                               |
| `tests/`                    | including the conformance kit                                                                       |

`ocp_viewer_core/__init__.py` is import-free by design: hosts import the submodule they need, so that importing the package never pulls in the tessellator or OCP.

## Use

### ocp vscode:

Every client knows its workspace config keys:

```python
workspace_config_keys = (
    "center_grid",
    "collapse",
    "dark",
    "glass",
    "grid_font_size",
    "orbit_control",
    "states",
    "ticks",
    "tools",
    "tree_width",
    "up",
    "pan_speed",
    "rotate_speed",
    "zoom_speed",
    "ambient_intensity",
    "angular_tolerance",
    "default_color",
    "default_edgecolor",
    "default_facecolor",
    "default_opacity",
    "default_thickedgecolor",
    "default_vertexcolor",
    "deviation",
    "direct_intensity",
    "metalness",
    "modifier_keys",
    "roughness",
)
```

For every `show` statement use this block:

```python
comms = Comms(...)
session = Session(comms) # sets session cache to None
config = Config(session, workspace_config_keys, ("cad_width", "height"))
show(objects)
```

## Dependencies

`ocp-tessellate` for tessellation, and `three-cad-viewer` as a peer dependency of the JavaScript half. **No OCP provider is declared** — the same `OCP` namespace is supplied by `cadquery_ocp`, `cadquery_ocp_novtk` and conda's `OCP`, and naming one would break users of the other two. The host or the user chooses.

## Licence

Apache-2.0.
