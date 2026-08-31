# Fixtures

`three_cad_viewer_notifications.json` is the camelCase -> snake_case table three-cad-viewer
uses for change notifications, extracted from `src/core/viewer-state.ts` of the version named
in the peer dependency. It is checked in so that `test_config_keys.py` can hold the key table
against the renderer's own naming without a live checkout.

Regenerate it after a three-cad-viewer upgrade:

    python tools/extract_notifications.py <path-to-three-cad-viewer>

A disagreement between this file and `config_keys.toml` is the bug the table exists to prevent:
ocp_vscode derived JS names with a `toCamelCase` plus three hand-kept overrides, and got
`studio_ao_intensity` wrong - the renderer calls it `studioAOIntensity`, so that option was
silently ignored with no error anywhere.
