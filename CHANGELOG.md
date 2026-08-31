# Changelog

Since 1.0.2 the Python and JavaScript halves version separately on the patch level and agree on major.minor - see `Development.md`. Entries say which half they belong to.

## Python v1.0.4 (2026-08-31)

- `commands.py` is renamed to `viewer.py`: `from ocp_viewer_core.viewer import *` (or any named subset) is the portable spelling for multi-viewer scripts - it resolves the host from the environment and offers its complete flat surface, star-identical to `from <host> import *`.
- The package root imports the light submodules - `animation`, `colors`, `comms`, `config`, `keys`, `state`, `utils` - so `dir(ocp_viewer_core)` and tab completion show the package structure. `utils` defers its build123d import to the `create_shader_ball` call, so no CAD library is required to import the package.
- The camera warnings (`ignore_camera_warnings`, `camera_keep_warning` and their classes) moved from `show.py` to `utils.py`, matching where ocp_vscode kept them; `ocp_viewer_core.show` still re-exports them, so hosts are untouched.
- `selectors.py` imports its CAD library at the call through `_ensure_build123d`/`_ensure_cadquery` - a missing library is an honest ImportError at the selection instead of a silent no-op, and importing the module no longer pays for whichever CAD libraries happen to be installed.
- Every root submodule now has a complete `__all__`; `config`'s was empty, so `from ocp_viewer_core.config import *` yielded nothing where the nine enums were meant.

## Python v1.0.3 (2026-08-31)

- New `materials.py`: `vis_material_to_pbr` and `pbr_to_vis_material` translate between OCCT's `XCAFDoc_VisMaterial` and threejs-materials' `PbrProperties` - scalar PBR values, with color spaces converted at the boundary (base color sRGB, emissive linear); texture maps and the fields `XCAFDoc_VisMaterialPBR` cannot hold are dropped.
- `show` accepts a cadquery `Material` and renders its vis material when it holds visual properties. Today it never does - cadquery's constructor stores only the physical half and its STEP importer reads only `XCAFDoc_Material` - so it is reported and ignored until cadquery populates `wrapped_vis`, or the user does via `pbr_to_vis_material`.
- A material `show` cannot translate is reported and ignored instead of crashing: the unknown-material branch printed a misspelt message and then raised `UnboundLocalError` on the next line.

## v1.0.2 (2026-08-27, Python and JavaScript)

- Animation ported from ocp_vscode: `animation.py` speaks the core session (`send_data` for tracks, `send_command` for the clock, `save_screenshot` for frames), and `Viewer` carries an `animation()` factory each host binds as `Animation`. `save_as_gif` brings pillow in as a core dependency. Two latent bugs fixed on the way: the loops `ValueError` read an unassigned name, and `animate()`'s error named a method that does not exist.
- Versioning contract: the two halves agree on major.minor, patch is each half's own. Enforced at runtime - `Session.send_data` sends `_core_version` with every model, `page.js` strips it before `applyConfig` and warns once per page when major.minor differ. The bump tooling split into `.bumpversion-py.toml` / `.bumpversion-js.toml` with `make bump-py` / `bump-js` / `bump`.
- `utils.create_shader_ball` and the `select_*` helpers (`selectors.py`) move into the core from ocp_vscode.
- `commands.py`: opt-in `from ocp_viewer_core.commands import *` picks the host from the environment and says which one it chose - one import line for running the same script against several hosts. The default story is unchanged: import from your viewer's own package.
- `colors.__all__` carries the whole public colormap vocabulary, so a host's `from ocp_viewer_core.colors import *` re-export is complete (`ListedColorMap` and friends).
- `is_drawable`: a container is drawable when anything in it is - `show_all` no longer silently drops a dict or list holding shapes beside a stray int or string.

## v1.0.1 (2026-08-19, Python and JavaScript)

First release of both halves - PyPI and npm.

- The universal-import machinery from 1.0.0 is deleted: users import from their viewer's own package, and the four packages offer the same show family because they all bind it from the core.
- `show_clear` works in every host again: the page's `clear` branch is restored (`show_clear` and `show_all` on an empty namespace send `{"type": "clear"}`), a cleared model cannot be re-rendered, and the page guards `resize` and config frames against the emptied-viewer state `clear` makes reachable.
- `get_properties` dispatches on the TypeIs predicates instead of comparing a type string, ending 47 ty diagnostics.

## v1.0.0 (2026-08-19, Python; yanked)

First PyPI release, yanked the same day: it shipped the universal-import machinery that was deleted before 1.0.1.

## v0.1.0

Initial development version. Not released.
