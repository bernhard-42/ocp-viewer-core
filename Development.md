# Development

## Versioning: major.minor is the contract

The core is one project in two halves — `ocp-viewer-core` on PyPI and `ocp-viewer-core` on npm — and the two halves share a wire: the protocol, the config vocabulary (`keys.py` and its JavaScript counterparts), the message shapes, the splash formats. The version scheme says exactly one thing about that wire:

**major.minor names the contract and must match between the halves; the patch level is each half's own.**

| Python | JavaScript | valid? |
| ------ | ---------- | ------ |
| 4.1.2 | 4.1.2 | yes |
| 4.1.2 | 4.1.5 | yes — a JS-only fix shipped |
| 4.1.5 | 4.1.2 | yes — a Python-only fix shipped |
| 4.1.2 | 4.2.0 | **no** |
| 4.2.0 | 4.1.2 | **no** |

The point of the asymmetry: a pure Python fix ships by publishing PyPI alone — the viewers' floors (`>=X.Y.Z,<X.(Y+1).0`) already accept it, and no viewer needs an artificial release. A pure JS fix ships on npm, and only the viewers that want it rebuild (the JS half is bundled into each viewer at build time).

### The discipline that makes it hold

A patch release may touch **one side's internals only**. The moment a change crosses the wire — a new config key, a changed message shape, anything in `keys.py`'s two-language mapping, a splash format — it is a **minor bump of both halves**, however small the diff looks. When in doubt, it crosses the wire.

### Enforcement at runtime

The contract is checked in code, not only in this file:

- `Session.send_data` (Python) injects `_core_version` into every model's config block — after encoding, so the key arrives spelled literally.
- `page.js` (JavaScript) takes it out before applying the config, compares major.minor against `js/src/version.js`, and on mismatch raises a `console.error` and sends a `log` message to the host — once per page.
- The VS Code extension additionally compares its own version against the `ocp_vscode` library at major.minor (`semver.diff` of `patch`/`null` passes).

Known gap: Jupyter CadQuery's frontend is cad-viewer-widget, not the core page, and its arg filters drop `_core_version` before the widget — so the runtime check does not fire there yet. The risk is small (the widget pins the JS core exactly at build), but a widget-side check is the open TODO.

## Bumping versions

Each half tracks its own version in its own config: `.bumpversion-py.toml` (writes `pyproject.toml`, `ocp_viewer_core/_version.py`) and `.bumpversion-js.toml` (writes `js/package.json`, `js/src/version.js`).

```bash
make bump-py part=patch   # Python-only fix
make bump-js part=patch   # JavaScript-only fix
make bump part=minor      # contract change: both halves move together
make bump part=major      # likewise
```

`make bump part=minor|major` runs both bumps; because both sides always agree on major.minor, bumping each from its own current lands both on the same `X.Y.0`.

## Releasing

- **Python-only patch**: `make bump-py part=patch` → `make wheel` → `make upload`. Done — users get it with `pip install -U`, no viewer releases.
- **JS-only patch**: `make bump-js part=patch` → `make tarball` → `cd js && npm publish`. Viewers pick it up on their next build, deliberately.
- **Minor/major**: `make bump part=minor` → publish both halves → bump the four viewers' Python floors to the new minor (`>=X.Y.0,<X.(Y+1).0`) and their npm pins as they rebuild.

Viewer consumption, for reference: Python floors are minor-ranged (`>=1.1.0,<1.2.0`), npm pins are exact — the JS half is bundled per viewer build, so exact pins plus deliberate rebuilds are the right shape there.

## Toolchain

`make check` is the whole of it: `ruff` lints, `ty` type-checks, nothing reformats (deliberately — see the note in `pyproject.toml`). `make tests` runs pytest including the conformance kit.
