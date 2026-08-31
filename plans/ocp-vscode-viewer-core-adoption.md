# Integrating ocp-viewer-core into ocp_vscode

Branch `viewer-core` in `~/Development/CAD/vscode-ocp-cad-viewer`, against `ocp-viewer-core 0.1.0` (`ea955b9`) and `three-cad-viewer 5.0.3`.

Everything below is measured from the two working trees on 2026-08-11, not inferred. Line numbers are `resources/viewer.html` unless stated otherwise.

## What the repo looks like right now

`main` is at `934e1fa` and **is not pushed** — `origin/main` is `1bcfccf`, one behind. The only working-tree change is `yarn.lock`, four lines, `three-cad-viewer 5.0.1 → 5.0.2`. That is exactly the bump `934e1fa` made to `package.json:793`, so the lock belongs to that commit and was left out of it.

Two facts that shape every step below:

- **`resources/viewer.html` is the source. `ocp_vscode/templates/viewer.html` is a copy** made by `make dist`. They are byte-identical today. Editing the copy looks right until the next `make dist` overwrites it.
- **The webview loads three-cad-viewer straight out of `node_modules`** (`src/controller.ts:140-152`, `asWebviewUri` on `node_modules/three-cad-viewer/dist/`), and the standalone loads it from `ocp_vscode/static/js/`, populated by the same `make dist`. No bundler is involved on either path, so the core's plain ESM modules can be served the same two ways.

## 1. yarn.lock

It should have been part of `934e1fa`, and that commit is unpushed, so amending is safe and is the honest history.

```
git add yarn.lock
git commit --amend --no-edit
```

Step 3 replaces this dependency with a tarball on the branch, but `main` should still be self-consistent.

**Needs your go before the amend runs.**

## 2. Branch

```
git switch -c viewer-core
```

From the amended `main`.

## 3. The two tarballs

Sources: `~/Development/CAD/ocp-viewer-core/dist/ocp-viewer-core-v0.1.0.tgz` (built by `make dist`, 9.1 kB) and `~/Development/CAD/three-cad-viewer/three-cad-viewer-v5.0.3.tgz` (3.6 MB). 5.0.3 is not optional: `js/package.json` declares `"three-cad-viewer": ">=5.0.3 <5.1.0"` as a peer dependency.

The repo already has the pattern — `proper-lockfile: "./proper-lockfile-4.1.2-esm.tgz"` sits in the root, and `make reload-tcv` does `yarn remove` / `yarn cache clean` / `yarn add ./three-cad-viewer-v*.tgz` from the root. Your instruction names the core tarball bare and the viewer tarball as `../three-cad-viewer/...`, so:

```
cp ~/Development/CAD/ocp-viewer-core/dist/ocp-viewer-core-v0.1.0.tgz .
yarn remove three-cad-viewer
yarn cache clean
yarn add ../three-cad-viewer/three-cad-viewer-v5.0.3.tgz
yarn add ./ocp-viewer-core-v0.1.0.tgz
```

`yarn cache clean` matters: yarn caches a file dependency by name and version, so a rebuilt tarball with an unchanged version installs the stale one. Every rebuild of either package needs the remove/clean/add cycle, which is what `reload-tcv` exists for — I will add a `reload-core` target beside it so this is one command rather than four remembered ones.

Two more edits in the same step:

- **`make dist`** copies three-cad-viewer's `dist/` into `ocp_vscode/static/`. It gains `cp -r node_modules/ocp-viewer-core/src ocp_vscode/static/js/ocp-viewer-core`, so the standalone serves the core the same way it serves the renderer.
- **`pyproject.toml`** gains `ocp-viewer-core>=0.1.0,<0.2.0`. Nothing is published, so that does not resolve from PyPI — on this branch the package is an editable install (`uv pip install -e ~/Development/CAD/ocp-viewer-core`) in whichever env you test from. **This is what gates merging the branch, not the code.**

`ocp-viewer-core-v0.1.0.tgz` and the rewritten `package.json`/`yarn.lock` are a development state, as the core's own Makefile says. They live on this branch and must not reach `main` as they are.

## 4. viewer.html

The single `<script type="module">` block is 916 lines. Six pieces come out, and the host-specific half stays: `getSize`, `normalizeWidth`, `normalizeHeight`, `send`, `debugLog`, the vector helpers, the whole camera policy in `render()`, the splash zoom, and the theme `MutationObserver`.

**The import.** A new `{{ coreSrc }}` template variable beside `{{ scriptSrc }}`, resolved in `src/display.ts:20-44` (`asWebviewUri` on `node_modules/ocp-viewer-core/src/index.js`) and in `ocp_vscode/standalone.py:44` (`./static/js/ocp-viewer-core/index.js`). The core's modules import each other relatively with extensions (`from "./apply.js"`), so serving the directory is enough — no bundling, no CSP change. `src/viewer.ts:61` sets `enableScripts` and no `localResourceRoots`, so the default roots already cover `node_modules`, exactly as they do for the renderer today.

**The five replacements.**

| out | in | lines |
| --- | --- | --- |
| the `ui` dispatch, 38 `else if` branches | `applyConfig(viewer, data.config, {resize, onUnknown})` | 765-910 |
| `toCamelCase` + `optionKeyOverrides` + the two option loops | `buildRenderOptions` / `buildViewerOptions` / `preset` | 360-405 |
| `getDisplayOptions`'s body | `buildDisplayOptions(config, defaults, geometry)`, keeping `getSize`/`normalizeWidth`/`normalizeHeight` as the geometry it is handed | 285-315 |
| `getStates` + the restore block | `collectStates` / `currentStates` / `restoreStates` | 671-742 |
| `addAnimationTrack` + the animation branch | `animate(viewer, tracks, speed, onUnknown)` | 133-163, 911-922 |
| `nc` | `createNotifier({viewer, send, debug})` | 193-253 |

**I checked the dispatch coverage rather than assuming it.** Every one of the 38 keys viewer.html's `ui` branch handles is in `keys.ALL` (77 entries), every one translates to a name `applyConfig` has a setter for, and the clip sliders and normals land on the indexed setter. `normal_len` has no table entry and does not need one — the mechanical fallback spells it `normalLen`, which is what `RENDER_OPTION_KEYS` wants. Nothing is lost, and ocp_vscode **gains the eleven `studio_*` setters** it has never had: they are accepted by `set_viewer_config` today and dropped by the webview without a word.

**`nc` is the risky one, and it is not a like-for-like swap.** Today `nc` writes the module globals `_zoom`, `_position`, `_quaternion`, `_target`, `_clipping.*` and `_zebra.*`, and `render()`'s camera policy reads them back. `createNotifier` keeps that picture in its own `status` object instead, under the renderer's notification names. So the camera policy has to read `status.position` where it read `_position`, and `render()`'s own `send("status", message)` at the end — which is outside the notifier — has to keep working. Get this wrong and the symptom is not an error: it is `reset_camera=KEEP` quietly resetting the camera. It also fixes a real bug on the way, since the notifier sends the delta rather than the accumulated `message` object, so a stale `selectedShapeIDs` stops riding along with an unrelated update.

**A third config producer nobody has listed: `src/logo.ts`.** It carries a **47-key snake_case config literal** and `controller.ts:67-73` patches `modifier_keys`, `theme` and `tree_width` into it before posting it straight to `showViewer()` — Python is not in that path at all. The same file is copied to `ocp_vscode/static/js/logo.js` for the standalone. Once viewer.html speaks camelCase, that literal must be converted too, or **the splash logo breaks on both hosts**. I propose renaming the literal once, by `keys.ALL`, rather than adding a converter — it is static data and the browser is its only reader. The three patched keys in `controller.ts` go with it.

## 5. The Python side

**`ocp_vscode/comms.py`** gains a `VSCodeComms(Comms[None])` wrapping the existing `_send`: `send_data`, `send_config`, `send_command`, `send_backend`, `send_response`, and `is_handle` returning False. The module-level `send_*` functions stay, since `animation.py`, `backend.py` and `standalone.py` use them directly.

**`ocp_vscode/config.py`** loses the `is_jupyter_cadquery` import branch at the top (environment sniffing at import time, which is what made `from ocp_vscode import config` behave differently depending on a variable), the five `CONFIG_*` lists, `DEFAULTS`, and every function now on `Config`. What remains is the host's two lists — the 27-key `WORKSPACE_CONFIG_KEYS` from the core's README, and `exclude_keys = ("cad_width", "height")` — plus re-exports of the enums so `from ocp_vscode import Camera, Collapse, ...` keeps working. `CONFIG_UI_KEYS` and `CONFIG_SET_KEYS` are consumed by `set_viewer_config`, which now lives on `Config`, so they go with it.

**`ocp_vscode/show.py`, 1745 lines, is deleted.** A new small module builds the four objects and binds the names:

```python
comms   = VSCodeComms()
session = Session(comms)
config  = Config(session, WORKSPACE_CONFIG_KEYS, ("cad_width", "height"))
viewer  = Viewer[None](config)

show, show_object, show_objects, show_all, ... = viewer.show, ...
```

`show.py`'s `__all__` (12 names) and `config.py`'s (16) are the compatibility contract and all of them must still resolve from `ocp_vscode`. Bound methods, never `partial` or `wraps` — that is what keeps the 84-kwarg hover.

**Three callers move with it.** `animation.py:27-28` imports `save_screenshot` from `.show` and `get_last_paths` from `.utils`; both are on the `Viewer` instance now. `utils.py` loses the camera-warning helpers and the `last_bbox`/`last_paths` globals, which are instance state in the core. `colors.py` is untouched.

**`make tests` / `make native_tests`** cover four files; `test_show.py` and `test_measure.py` run against the `is_pytest()` stub, and `test_standalone_cli.py` spawns a real `python -m ocp_vscode` on port 39777 and queries it over a real websocket — that one is a genuine headless end-to-end check of comms and config, and I will run it in the background rather than stalling on it. `test_viewer_config.py` deliberately turns the stub off and needs a **real viewer on 3939**, so it is yours to run.

## The one thing I need you to decide: how `port` reaches the command calls

`show(port=3940)` today threads that port explicitly into `combined_config(port=)`, `get_changed_config(port=)`, `get_defaults(port=)`, `send_data(port=)` and `send_backend(port=)` — so the status and workspace-config reads go to 3940 as well as the model.

In the core it survives as a show keyword and lands in the config block via `_tessellate`'s `params[k] = v`, so `Comms.send_data` can read `config["port"]`. But `Session.status()` and `Session.workspace_config()` call `comms.send_command("status")` with no port, and they run *inside* `_tessellate`, before any model is sent. So as it stands, `show(port=3940)` would read config from the default port and send the model to 3940.

Three ways out:

- **(a)** Leave it. `set_port()` selects which viewer the commands talk to, `show(port=)` only routes the model. Cheapest, and silently asymmetric.
- **(b)** A per-show hook in the core: `_show` hands the kwargs to `comms` before anything else and clears it in the same `finally` as `Session.clear()`. About six lines, keeps `show(port=)` meaning exactly what it means today, and names no host. **My recommendation.**
- **(c)** One `Viewer` per port, built on demand. Truest to the design and the largest change, and it breaks `show(port=)` as a keyword.

## Order, and where it can be tested

Steps 4 and 5 are one functional unit: with only the Python half done, Python sends camelCase to an HTML that reads snake_case; with only the JS half done, the reverse. Either way the viewer is broken. So they get implemented together and **committed as one commit**, so no commit on the branch is a viewer that does not work — worth more here than the reviewability of splitting a 1745-line deletion from an HTML rewrite, because you find these defects by running the thing.

That gives four commits: the `main` amend, then on the branch — dependencies and build wiring; the adoption; and whatever the testing turns up.

Verification, in order: `make tests` and `make native_tests` in the background; `test_standalone_cli.py` as the headless end-to-end; then `make install-vsix` and a numbered UI test for you, covering the splash logo (the `logo.ts` path), a plain `show()`, a second `show()` with `reset_camera=Camera.KEEP` (the notifier rewrite), a `set_viewer_config` round trip (the `ui` dispatch), one `studio_*` key that has never worked before, and the standalone viewer in a browser.

## Known consequences worth stating before starting

- **This branch breaks `jupyter_cadquery`**, which imports `_show`/`_show_object` from `ocp_vscode.show` across six files. That is the expected order — it is ported after ocp_vscode — but it will not run against this branch.
- **`theme`** is still the open exclusion question: the golden master excluded it, `exclude_keys` is `("cad_width", "height")`. This branch is where it gets settled, and I will flag it when the answer shows up rather than guessing now.
- **`ocp_vscode/templates/viewer.html`** must be regenerated by `make dist`, never edited.
