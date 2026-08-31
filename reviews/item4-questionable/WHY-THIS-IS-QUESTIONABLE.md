# Item 4 draft — set aside 2026-08-10, not trustworthy

Produced by inferring three-cad-viewer's and ocp_vscode's behaviour from greps rather than
from reading the projects. Kept only so the *questions* it raised are not lost. Do not
re-import any of it without re-deriving the claim from the sources.

## What is probably real (each still needs confirming)

- The five key lists in `ocp_vscode/config.py` are nested: UI (38) subset of WORKSPACE (61)
  subset of KEYS (72), with CONTROL (10) and SET (39) cutting across. 75 distinct keys.
- `ocp_vscode/templates/viewer.html` converts config keys to renderer option names with
  `optionKeyOverrides[k] || toCamelCase(k)` (~line 401), with exactly three overrides:
  `default_edgecolor -> edgeColor`, `clip_planes -> clipPlaneHelpers`,
  `studio_4k_env_maps -> studio4kEnvMaps`.
- `three-cad-viewer/src/core/viewer-state.ts` has `STATE_TO_NOTIFICATION_KEY`, mapping
  **internal state keys** to wire names. It is NOT a table of option names — `tab` goes in
  as `viewerOptions.tab` (viewer.ts:1797), is held internally as `activeTab`, and comes back
  as `tab`. Treating it as "the JS name" produced a wrong answer for that key.
- `studio_ao_intensity`: the renderer's option field is `studioAOIntensity`
  (types.ts:428) and viewer.html's own defaults object uses that spelling (~line 109), but the
  conversion above yields `studioAoIntensity` and there is no override. **This looked like a
  live silent bug and is the single most valuable thing here — but it was found by grep, not
  by understanding, so it needs confirming by someone who knows the option path.**
- `orbit_control` is a python boolean converted to `control = "orbit"|"trackball"` in
  `ocp_vscode/show.py:522-523`; `control=` as a python kwarg is deprecated (config.py:857-859).
- `modifier_keys` reaches the renderer as `keymap`, hand-coded in viewer.html (~292, ~306).

## What was wrong, and why

- `group` was first invented from VS Code setting namespaces. The renderer's own interfaces
  (DisplayOptions / RenderOptions / ViewerOptions / StudioModeOptions / ZebraOptions) are the
  real grouping — only found because Bernhard pointed at them.
- The notification fixture was extracted by regex over the whole file, so an unrelated
  `activeTab: "tree"` overwrote the real `activeTab: "tab"`. Numbers derived from it (62
  entries, "zero disagreements", the first `reportable` column) are worthless.
- A `replayable` guard was written that failed to catch its own un-apply until strengthened.
- `tab` was reported as broken. It is not.

## Questions worth carrying into a proper design

- Which axis does a shared table need: option name in, wire name out, internal state key -
  are they three columns or two?
- Is `role` (option / tessellation / action / command / diagnostic / tree-state) a real
  distinction in the code, or one I imposed?
- `states` behaves as optional input, preserved-across-render state, and delta output. Where
  does that belong?
