# Value-flow audit: settings that arrive nowhere

Audited 2026-08-13 across `ocp-viewer-core` (main), `vscode-ocp-cad-viewer` (viewer-core), `ocp-viewer` (main), `jupyter-cadquery` + `cad-viewer-widget` (viewer-core), against `three-cad-viewer` (master). The hunted class: values that three-cad-viewer silently drops, keys mapped but consumed by nobody, applied-once traps, setter mismatches, and cross-host inconsistencies.

**11 findings: 8 CONFIRMED (5 by experiment, 3 by full end-to-end code trace), 3 SUSPECTED/minor.** Ranked by severity: a crash first, then values silently lost, then inconsistencies. Every apply.js setter and getter signature was verified against three-cad-viewer and found correct; the coverage list is at the end.

---

## 1. `buildDisplayOptions` drops the `pinning` and `studioTool` overrides — the widget's pin button is silently gone — CONFIRMED

**Where:** `/Users/bernhard/Development/CAD/ocp-viewer-core/js/src/options.js:226-247` (`buildDisplayOptions`), consumed by `/Users/bernhard/Development/CAD/cad-viewer-widget/js/lib/widget.js:440-459` (`getDisplayOptions`).

**Mechanism.** `buildDisplayOptions` merges `defaults = { ...DISPLAY_DEFAULTS, ...overrides }` but then builds its return object by hand, copying only `glass`/`tools`/`keymap`/`newTreeBehavior` from the config, `theme`, the three geometry keys, and six capability flags: `measureTools`, `selectTool`, `explodeTool`, `zscaleTool`, `zebraTool`, `externalMeasurementBackend`. Two keys that are in the merged defaults never make it into the return: **`pinning`** (present in `DISPLAY_DEFAULTS` at options.js:90) and **`studioTool`** (missing from `DISPLAY_DEFAULTS` entirely). Proved with node: `buildDisplayOptions({}, { pinning: true, studioTool: true }, geom)` returns an object with neither key.

**End to end.** cad-viewer-widget passes `pinning: this.model.get("pinning")` and `studioTool: true` as overrides (widget.js:445, 450). three-cad-viewer's `Display` constructor reads `this.showPinning(options.pinning)` (`src/ui/display.ts:746`) — it receives `undefined`, which hides the pin button. `open_viewer()` defaults to `pinning=True` for cell viewers (`cad_viewer_widget/__init__.py:82-114`), and `show(obj, pinning=True)` through jupyter_cadquery flows `config → display_args → CadViewer(pinning=True) → trait → getDisplayOptions → dropped`. The runtime change handler (`HOST_TRAITS` → `viewer.showPinning`) only fires on a *change* after render, never for the construction value.

**User-visible:** the pin-as-PNG button never appears in any Jupyter cell viewer, with `pinning=True` explicitly requested or defaulted. Nothing is said anywhere.

`studioTool` is masked today because the renderer's own default is `true` (`viewer-state.ts` `DISPLAY_DEFAULTS.studioTool: true`); but any host passing `studioTool: false` to hide the Studio tab would silently keep it — `display.ts:497` tests `options.studioTool === false`, and `undefined` fails that test.

**Fix:** copy `pinning` and `studioTool` from `defaults` in the return object (they are capability flags like the six that are copied), and add `studioTool` to `DISPLAY_DEFAULTS` so the flag has a stated shared default.

---

## 2. `set_defaults(grid=True)` / `set_viewer_config(grid=True)` — a TypeError in the page, then every later show silently loses the grid — CONFIRMED

**Where:** `/Users/bernhard/Development/CAD/ocp-viewer-core/ocp_viewer_core/config.py:416` (`set_viewer_config`) and `:517` (`set_defaults`) — no bool→list conversion; the conversion exists only on the show path (`show.py:1137`, `_show_impl`: `isinstance(kwargs["grid"], bool)` → `[b]*3`).

**Mechanism.** Both docstrings document `grid: Show grid (default=False)` — a boolean. `show(grid=True)` is converted to `[True, True, True]` in `_show_impl`; `set_defaults(grid=True)` and `set_viewer_config(grid=True)` are not. Proved with a fake transport: `set_defaults(grid=True)` stores `defaults["grid"] = True` and puts `{"grid": true}` on the wire as a ui message.

**End to end, websocket hosts.** apply.js `grid` setter calls `setGrids(true, notify)`; three-cad-viewer's `setGrids` (`viewer.ts:2405`) does `this.rendered.gridHelper.setGrids(...grids)` — spreading a boolean throws `TypeError: grids is not iterable` (proved in node). The throw escapes `applyConfig`'s loop, so **every key after `grid` in the same config block is also lost**, and from Python nothing is visible at all. Then the stored boolean default rides into every subsequent show's config (`combined_config` overlays `self.defaults` last), reaches `viewerOptions.grid = true`, and `ViewerState._update` stores a boolean where `[boolean, boolean, boolean]` is expected — the grid never appears and nothing is said.

**Jupyter host:** `send_config` does `setattr(cv, "grid", True)` against the `Tuple(Bool(), Bool(), Bool())` trait (`cad_viewer_widget/widget.py:243`) — a loud `TraitError` in the kernel, so this host crashes instead of losing the value.

**User-visible:** `set_defaults(grid=True)` — nothing happens, and depending on what else was in the block, other settings quietly stop applying too.

**Fix:** normalize `grid` (bool → `[b, b, b]`) in `set_defaults`/`set_viewer_config` — one shared spot in `Config` (e.g. beside `check_deprecated` or in `validate_values`) covers both.

---

## 3. jupyter_cadquery `send_config` overwrites its `title` and never reads `viewer` — a named sidecar's config lands on the default sidecar — CONFIRMED

**Where:** `/Users/bernhard/Development/CAD/jupyter-cadquery/jupyter_cadquery/comms.py:233-263` (`send_config`), called from `JupyterComms.send_config` at `:311` with `title=self.title` (the `viewer=` keyword from the call scope, `:294`).

**Mechanism.** The first line of the body is `title = config["config"].get("title")` (comms.py:239) — it unconditionally overwrites the correctly-passed `title` parameter. The config block never contains `"title"`: `set_viewer_config` puts the host keyword in as `"viewer"` (`ocp_viewer_core/config.py`, `set_viewer_config` builds `config` from `locals()`, which includes `port` and `viewer`). Same shape as the fixed `viewer_args`/`orbit_control` bug: reading a key nothing produces.

**End to end.** `set_viewer_config(axes=True, viewer="Sidecar B")` → `Session.begin({"viewer": "Sidecar B"})` → `JupyterComms.send_config(config)` → `send_config(config, title="Sidecar B")` → line 239 replaces it with `None` → `get_default_sidecar()` → the **default** sidecar is configured instead of Sidecar B. Additionally, the loop skips only `["port", "title"]` (comms.py:252), so the `"viewer"` key itself reaches `setattr` — and `_is_settable("viewer")` returns `True` for a name that is not a property at all (verified by running it: `getattr(CadViewer, "viewer", None)` is `None`, `not isinstance(None, property)` → `True`), so `setattr(cv, "viewer", "Sidecar B")` plants a junk attribute on the CadViewer, silently.

**User-visible:** in a notebook with two sidecars, configuring the non-default one by name changes the default one; the named one does nothing.

**Fix:** `title = title if title is not None else config["config"].get("viewer")`, and add `"viewer"` to the skip list. Consider tightening `_is_settable` to also require the attribute to exist, so unknown keys are skipped rather than planted.

---

## 4. `DEFAULT_DEFAULTS["collapse"]` masks every host's stored collapse setting and the user's toolbar choice on every show — CONFIRMED

**Where:** `/Users/bernhard/Development/CAD/ocp-viewer-core/ocp_viewer_core/config.py:180-189` (`DEFAULT_DEFAULTS` contains `"collapse": Collapse.ROOT`), `:401` (`combined_config` applies `self.defaults` last), `:199`/`:747` (`NOT_RESTORED_ON_RESET` removes `collapse` — but only on `reset_defaults()`).

**Mechanism.** `combined_config`'s precedence is workspace config ← viewer status ← `self.defaults`, defaults last and masking. `Config.__init__` copies `DEFAULT_DEFAULTS` including `collapse`, so from construction until someone calls `reset_defaults()`, **every** show answers `collapse = Collapse.ROOT` no matter what the host's stored setting or the viewer's live state says. Proved with a fake transport: workspace `"collapse": "leaves"` and status `collapse: 2` (user expanded everything) both come back as `Collapse.ROOT` from `combined_config`; removing the default lets the status value through.

The file's own comment explains exactly why this masking is wrong for `collapse` ("the next show would re-collapse a tree the user had just opened") and removes it on reset — but the construction-time defaults still carry it, so the common case (a session that never calls `reset_defaults`) has the defect the comment describes.

**Cross-host evidence that the setting is dead:** all three hosts ship a stored collapse default of LEAVES — VS Code `OcpCadViewer.view.collapse` default `'leaves'` (package.json), the standalone `"collapse": "1"` (`server/settings.py`), Jupyter CadQuery `"collapse": "1"` (`jupyter_cadquery/settings.py`) — and none of them can ever take effect. A user changing the VS Code setting sees nothing.

**Inherited:** the golden master (`vscode-ocp-cad-viewer` branch `main`) has the identical shape, so this is not a migration regression — but it is squarely the hunted class: a setting every host offers, arriving nowhere.

**User-visible:** the collapse setting does nothing; the tree re-collapses to root-only on every show after the user expanded it from the toolbar.

**Fix:** initialize `self.defaults` the way `reset_defaults` does — `{k: v for k, v in DEFAULT_DEFAULTS.items() if k not in NOT_RESTORED_ON_RESET}` — so construction and reset agree, and `collapse` flows workspace → status → show like every other toolbar key.

---

## 5. `modifier_keys` arrives nowhere in two hosts and is applied-once in the third — CONFIRMED

**Where:** apply.js has no `keymap` setter (`/Users/bernhard/Development/CAD/ocp-viewer-core/js/src/apply.js:72-197`, `SETTERS`), although three-cad-viewer has a working `setKeyMap(config)` (`src/core/viewer.ts:4538`). `buildDisplayOptions` applies `keymap` only at `new Display(...)`, which runs once per page.

**Standalone (`ocp_viewer`) — dead.** `server/settings.py:52` carries `modifier_keys` (with a 2.9.0 compat shim at `:152` that patches in the missing `alt` — so it is clearly meant to work), but the page shows the splash on load with `page.showSplash({ theme: settings.theme })` only (`server/templates/viewer.html:85`) — no keymap. The Display is therefore built during the splash with the logo's default keymap (`logo.js` config), and every later show computes `displayOptions.keymap` and throws it away because `display != null` (`page.js:173-186`). A ui config can't fix it either: no `keymap` setter, `onUnknown` logs into the debug channel only. The user's `modifier_keys` in `~/.ocpvscode_standalone` never applies.

**Jupyter CadQuery — dead.** `jupyter_cadquery/settings.py:51` stores `modifier_keys`, it survives into `combined_config`, and then `display_args` (`cad_viewer_widget/utils.py:125`) and `viewer_args` (`:142`) both filter it out — `cad_viewer_widget.show()` has no `modifier_keys` parameter at all. The widget's `modifier_keys` trait exists and maps to `keymap` in `TRAIT_TO_OPTION`, but `APPLIED_TRAITS` filters through `isApplicable("keymap")` which is false, so even a manual trait change after the viewer exists is heard by nobody. The `~/.jcq_config` value never applies.

**ocp_vscode — applied once.** Works only because `viewer.html:88` passes `keymap: settings.keymap` into `showSplash`, so the Display built at splash gets it. Changing the `OcpCadViewer.view.modifier_keys` setting while a panel is open never applies (the extension's `onDidChangeConfiguration` watches only `python.defaultInterpreterPath`, `extension.ts:292`; later shows drop keymap as above).

**User-visible:** editing modifier keys does nothing (standalone, JCQ: ever; VS Code: until the panel is rebuilt).

**Fix:** add `keymap: (v, value) => v.setKeyMap(value)` to apply.js `SETTERS` (this also auto-enrolls the widget's trait via `APPLIED_TRAITS`), pass `keymap` in the standalone's `showSplash`, and let `display_args` / `cad_viewer_widget.show` carry `modifier_keys`.

---

## 6. `new_tree_behavior` setting is dead in both page hosts — CONFIRMED (by full trace; not run in a browser)

**Where:** `vscode-ocp-cad-viewer/package.json:267` defines `OcpCadViewer.view.new_tree_behavior`; `controller.ts:116` sends it in the config answer; the standalone's `settings.py` has it too. Nothing applies it after the splash.

**Mechanism.** The value is not in the `init` message settings (`controller.ts:87-95`) nor in either host's `showSplash` config, so the Display and Viewer are built during the splash with the logo config's `newTreeBehavior: true`. On later shows, `buildDisplayOptions` computes it and page.js drops it (`display != null`). It is not in `VIEWER_OPTION_KEYS` (options.js), so `Viewer.render` → `updateViewerState` never writes it into state — although the renderer reads `state.get("newTreeBehavior")` on every tree build (`viewer.ts:1343`, `:3446`), so the state path would honour it. And apply.js has no setter for it. Every route is closed.

**Jupyter CadQuery is the contrast that proves the trace:** there it works, because `viewer_args` carries `new_tree_behavior`, the trait is set before the widget's first render, and `traitsAsConfig` feeds it to `buildDisplayOptions` at Display construction.

**User-visible:** setting `new_tree_behavior: false` in VS Code or the standalone config file changes nothing, ever.

**Fix:** add `newTreeBehavior` to `VIEWER_OPTION_KEYS` — `ViewerState._update` accepts it (it is a state key) and the tree builder reads it per render — or pass it through init/splash and re-apply like theme/glass/tools.

---

## 7. `show(collapse=Collapse.ALL)` leaks the Enum into the outgoing config — latent, rescued by accident in all current hosts — CONFIRMED

**Where:** `/Users/bernhard/Development/CAD/ocp-viewer-core/ocp_viewer_core/show.py:630-639` — `_tessellate`'s enum-unwrap tuple lists `studio_environment`, `studio_background`, `studio_tone_mapping`, `studio_texture_mapping`, `analysis_tool`, `tab`, `reset_camera` — **not `collapse`**.

**Mechanism.** The config-path collapse is unwrapped early (`conf["collapse"] = collapse.value`, show.py:519-520), but a *kwarg* `collapse=Collapse.ALL` is overlaid afterwards (`params[k] = v`) and the unwrap loop does not name it. Proved under `OCP_VIEWER_PYTEST=1`: the returned config carries `<Collapse.ALL: 0>` while `reset_camera` is correctly `'keep'`.

**Why nothing breaks today:** the websocket hosts serialize with `orjson.dumps(data, default=default)` and `websocket.py:137` unwraps any `Enum` to its value — which happens to be the right number, since `Collapse`'s values are `CollapseState`'s. The Jupyter host's `_collapse_to_letter` (`jupyter_cadquery/comms.py:64`) explicitly handles `Enum`. So the defect is masked by two independent transport-level rescues. A new host (build123d Studio's `Comms` will not inherit `websocket.py`'s `default`) or plain `json.dumps` gets `TypeError: Object of type Collapse is not JSON serializable` (proved).

**Fix:** add `"collapse"` to the unwrap tuple in `_tessellate`.

---

## 8. `reset_camera=Camera.CENTER` on a live viewer is a silent no-op — SUSPECTED (behavior CONFIRMED, intent unclear)

**Where:** `/Users/bernhard/Development/CAD/ocp-viewer-core/js/src/apply.js:157-164` (`resetCamera` setter) and `:53` (`VIEWS`, which has no `"center"`).

**Mechanism.** The setter handles `"reset"` (iso + resize) and the seven preset views; everything else falls through. `"keep"` doing nothing is correct. But `"center"` is a value the ecosystem actively offers on the live path: `ALLOWED_VALUES["reset_camera"]` includes it, `set_viewer_config(reset_camera=Camera.CENTER)` validates and sends it, and the widget's `reset_camera` trait is `Enum(["reset", "keep", "center"])`. At show time `render.js` implements center (direction survives, target moves to the model centre) — on a live viewer the analogous action (`setCameraTarget` to the model centre) exists but is never called. The code comment claims everything beyond `VIEWS` is deliberate, so this may be a decision — but validation accepting a value whose application is a guaranteed no-op is exactly the audited shape.

**User-visible:** `set_viewer_config(reset_camera=Camera.CENTER)` — nothing happens, nothing said. Same for setting the widget trait.

**Fix:** either implement center (target := current model centre via the bounding box, e.g. `viewer.setCameraTarget(center)`) or refuse `center`/`keep` in `set_viewer_config`'s validation so the no-op is loud.

---

## 9. page.js `"show"` message handler would crash; `"show"` and `"clear"` have no producer — CONFIRMED (by trace)

**Where:** `/Users/bernhard/Development/CAD/ocp-viewer-core/js/src/page.js:309-312`.

**Mechanism.** `data.type === "show"` calls `showViewer()` with no arguments; `showViewer` immediately evaluates `getDisplayOptions(config.theme)` (page.js:178) with `config === undefined` — a guaranteed `TypeError` before the `_config == null` guard is reached. It also assigns `_meshData = undefined`, destroying the stored model, so even a fixed call could not re-show. Grep across both page hosts (`controller.ts`, `sockets.py`, `comms.js`) finds nothing that sends `type: "show"` or `type: "clear"` — both branches are dead code today, one of them a landmine.

**Fix:** either delete both branches or make `"show"` re-render the stored state: guard `_meshData == null`, and call `showViewer(_meshData, _config)`.

---

## 10. Host inconsistencies — same setting, different answers, nobody chose

- **`reset_camera` shipped default**: VS Code `KEEP` (package.json), standalone `"KEEP"` (`server/settings.py`), Jupyter CadQuery `"reset"` (`jupyter_cadquery/settings.py:60`). Consequence: a re-`show()` in JCQ throws the camera away by default while the other two hosts keep it — the exact behavior the shared camera policy exists to unify. CONFIRMED by reading all three defaults; severity: behavioral divergence, not loss.
- **`ticks` default**: VS Code 5, standalone 5, JCQ 10 (`settings.py:62` `"ticks": 10`), Python docstrings say 5, renderer's own default 10. JCQ grids are labelled differently from the other hosts'.
- **JCQ `modifier_keys` still lacks `"alt"`** (`jupyter_cadquery/settings.py:51-55`): VS Code and the standalone ship the four-key map, and the standalone even patches `alt` into old config files — JCQ's own stored default is the un-patched three-key form. (Currently moot because of finding 5, but it will surface the moment that is fixed.)
- **Core `VIEWER_DEFAULTS.gridFontSize` is 12 where the renderer's own default is 10** (`options.js` vs `viewer-state.ts`). Consistent across hosts, so tolerable — but options.js states its numbers "describe three-cad-viewer", and this one does not.
- **Stale docstrings that promise the wrong value**: `set_defaults`/`show` document `studio_texture_mapping` default `TRIPLANAR`; the actual shared default is `"parametric"` everywhere (core `VIEWER_DEFAULTS`, renderer `STUDIO_MODE_DEFAULTS`, with a comment explaining why). And `set_defaults`'s docstring documents `position`/`quaternion`/`target`, which are not parameters — calling `set_defaults(position=...)` raises `TypeError` (loud, so low severity; `set_viewer_config` is the intended route).
- **`cad_viewer_widget.show()` preset defaults `zoom_speed`/`pan_speed` to 0.5** (`__init__.py`, show body) where every other place in the ecosystem says 1.0. Unreachable through jupyter_cadquery (its workspace defaults always supply 1), but direct cad-viewer-widget users get half-speed mice.

---

## 11. Minor / latent

- **The browser-side `_splash` guard is dead.** `logo.js` ships `_splash: false` in the splash config, and neither host's `showSplash` call overrides it, so `page.js`'s `ui` refusal (`if (_config["_splash"]) return`) can never fire, and the splash-zoom branch in the `data` handler (`if (config._splash)`) is unreachable through `showSplash` (which computes nothing and uses the logo's fixed `zoom: 0.8`). The Python-side `_splash` handshake (workspace config) is intact and does the load-bearing work (forcing the camera reset after the splash); what is dead is the documented browser-side half. Inherited — the old `src/logo.ts` on `main` also says `_splash: false`. SUSPECTED (no browser run), low.
- **The standalone accumulates event keys into its status picture.** `server/viewer.py:record` does `self.status.update(changes)` on the full wire message, which is `{...status, ...delta}` — the delta side carries `selectedShapeIDs`/`lastPick`/`activeTool`/`selected`, so a `status()` from Python returns a selection made minutes ago. `combined_config` filters them out (none is in the 61 workspace keys), so shows are unaffected; only the public `status()` answer is polluted. CONFIRMED by trace, low.
- **Dead entries in `RENDER_DEFAULTS`** (`options.js`): `angularTolerance`, `deviation`, `defaultColor` are never picked (`RENDER_OPTION_KEYS` has seven other keys) — those three reach the renderer through the tessellated data instead. Harmless today; a trap for someone who edits the default there and sees nothing change.
- **`holroyd` is a renderer option no host can set.** three-cad-viewer accepts it as a viewer option, has `setHolroyd`/`getHolroyd` and notifies it; the core vocabulary has no key for it, and there is no toolbar toggle, so nothing is being lost — a capability gap, noted in Design.md's parked list, not a defect.
- **`orbit_control`, `up`, `modifier_keys`, `theme` in `WORKSPACE_CONFIG_KEYS`** match nothing the status overlay can ever contain (the renderer never notifies them). Dead list entries, harmless — the workspace-config side of the same keys is live.

---

## Checked and found correct

So the next audit need not re-tread:

- **Every `apply.js` setter against its real three-cad-viewer signature**: `setAxes`, `setAxes0`, `setGrids` (takes `[b,b,b]` — matches what Python sends after `_show_impl`'s bool conversion), `setGridCenter`, `setOrtho`, `setTransparent`, `setBlackEdges`, `setCameraZoom`, `setCameraPosition(position, relative, notify)` (the explicit `relative=false` fix is in place and correct), `setCameraQuaternion`, `setCameraTarget`, `setEdgeColor`, `setOpacity`, `setAmbientLight`, `setDirectLight`, `setMetalness`, `setRoughness`, `setZoomSpeed`/`setPanSpeed`/`setRotateSpeed`, `setTheme`, `glassMode`, `showTools`, `setActiveTab`, `setExplode`, `collapseNodes`, `setClipIntersection`, `setClipPlaneHelpers`, `setClipObjectColorCaps`, all five `setZebra*` (on the Viewer, taking a value not an Event — the Display's Event-taking versions are not what apply.js calls), all eleven `setStudio*`, `setView(direction, focus=false)`, `setStates(states)` (no notify parameter; the extra trailing arg apply.js passes is inert), `setClipSlider(index, value, notify)`, and `setClipNormal(index, normal, slider, notify)` — apply.js's re-passing of `getClipSlider(index)` matches the third parameter exactly. `analysisTool`'s use of `display.setTool(name, flag)` and `state.get("activeTool")` both check out.
- **Every `currentValue` getter exists with the right shape**: `getAxes`, `getAxes0`, `getGrids` (returns the 3-array, comparable with the trait), `getOrtho`, `getTransparent`, `getBlackEdges`, `getTools`, `getCameraZoom/Position/Quaternion/Target`, `getEdgeColor`, `getOpacity`, `getAmbientLight`, `getDirectLight`, `getMetalness`, `getRoughness`, the three speeds, `getClipIntersection`, `getClipPlaneHelpers`, `getObjectColorCaps` (asymmetric name, correct), `getClipSlider(i)`, `getClipNormal(i)`. Missing getters (glass, collapse, theme, tab, explode, zebra, studio) are write-only by design and read as "apply it" — correct for the widget's accept hook.
- **No wire-name collisions**: scripted check over `keys.ALL` and `keys.SETTABLE` including the mechanical fallback for `None`-mapped keys — every wire name is produced by exactly one Python key. Every `SETTABLE` key's wire name has a handler in apply.js (setter, clip dispatcher, or geometry/resize). Every `set_viewer_config` parameter covers every `SETTABLE` key, as the comment demands.
- **`VIEWER_OPTION_KEYS` and `RENDER_OPTION_KEYS` versus `ViewerState.STATE_KEYS`**: every listed option is a real state key; `updateViewerState`'s special extraction of `tab` is matched by render.js putting `config.tab` into `viewerOptions` explicitly, so the tab reaches the renderer the intended flash-free way. `up` is correctly a render-time option only (`Camera` reads it in its constructor; `Viewer.render` rebuilds the camera per render), absent from `SETTABLE` and from apply.js, present in `VIEWER_OPTION_KEYS` — the earlier `up` defect is properly closed.
- **`Collapse` ↔ `CollapseState`**: Python's numbers (NONE=2, LEAVES=-1, ALL=0, ROOT=1) match `types.ts` exactly (EXPANDED=2, LEAVES=-1, COLLAPSED=0, ROOT=1), and both letter/word/number conversions in `Config.workspace_config`, `jupyter_cadquery._collapse_to_letter` and widget.js `COLLAPSE_MAPPING`/`REVERSE` agree.
- **The `orbit_control` → `control` value conversion** is done exactly once per path: `_convert` pops `orbit_control` (websocket hosts), `viewer_args` synthesizes `orbit_control` from `control` (Jupyter, the fixed bug #4 — verified present and guarded with `"orbit_control" not in config`), widget.js `traitsAsConfig`/`handle_change` convert the trait. The extension sending renderer-named `control` in its workspace config coexists correctly with a Python-side `orbit_control` default (the pop makes the default win without a collision).
- **`to_javascript`'s collision refusal and underscore pass-through** behave as documented (`_splash` crosses untranslated), and `merge` refuses group redefinitions.
- **The three hosts' `WORKSPACE_CONFIG_KEYS` are byte-identical** (61 keys, scripted set comparison), and `EXCLUDE_KEYS` runs the documented opposite directions (panel hosts exclude geometry+sidecar keys; JCQ excludes only `port`).
- **`reset_camera` string handling**: VS Code's uppercase enum (`'BACK'` included) round-trips through `Camera[...upper()]` to `Camera.BACK = "rear"`, which is in apply.js `VIEWS` and the renderer's directions; the standalone's `str(...).upper()` shim and JCQ's lowercase `"reset"` both convert correctly; JCQ renders preset views as `"reset"` + `set_camera(view)` afterwards, matching the page hosts' `setView`.
- **Theme flow**: page.js re-applies `setTheme`/`glassMode`/`showTools` on every show (bug #2's fix, verified), the VS Code MutationObserver drives `page.setTheme`, the widget applies runtime theme via the shared dispatch, and `"browser"` resolution is left to the renderer everywhere.
- **`send_command` unwrapping** (`{"command": "status", "text": ...}` vs bare config dict) matches what both servers actually send; the standalone's backend answer is decoded to text before the browser frame as documented.
- **`notify.js`** keeps `EVENT_KEYS` out of the accumulated status on the page side, and `render.js`'s read-back list matches real getters (`getZebra*`, `getClipPlaneHelpers`, `getObjectColorCaps`, `getClipIntersection`, `controls.getTarget()`); `CARRY_OVER`'s option/status name pairs all agree with `STATE_TO_NOTIFICATION_KEY`.
- **`states` batching and path filtering** in apply.js and `states.js` line up with `treeview.getStates()`'s id form; `restoreStates` prefers explicit config states.
- **`backend.py`'s `changes["activeTool"]`/`changes["selectedShapeIDs"]`** are the renderer's actual (camelCase) notification spellings — the known, deliberately parked upstream inconsistency, working as-is in all four flows.
- **`_convert`'s enum unwrap for the seven listed keys**, `default_edgecolor` → `web_color`, the `_splash`-guarded `reset_camera` skip, and the clip-insight reset logic were traced and consume what they are sent (with the two exceptions reported as findings 2 and 7).
