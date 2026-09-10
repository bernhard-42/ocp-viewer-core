# Upgrading the viewer ecosystem

What to do in every host when `three-cad-viewer` or `ocp-viewer-core` moves. The versioning contract itself - what makes a patch a patch and a minor a minor - is in `Development.md`; this file is the mechanics, per host, per kind of upgrade.

## Why a checklist exists at all

No host loads this repository's sources. Each takes its own copy, by a different mechanism, and every one of them can be stale independently - which shows up as a setting that does nothing rather than as an error. The JavaScript half is where this bites: the Python half is installed editable in development, so a Python change is live the moment it is saved.

| host | JavaScript, and how it arrives | Python | refresh |
| --- | --- | --- | --- |
| **ocp_vscode** (`vscode-ocp-cad-viewer`) | npm dependencies in `node_modules/`, packed into the `.vsix` | `ocp-viewer-core[cli]` floor in `pyproject.toml` | `yarn install`, then `make vsix` / `make dist` |
| **ocp_viewer** (`ocp-viewer`) | npm dependencies **copied** into `ocp_viewer/server/static/` (gitignored - regenerated, never committed) | `ocp-viewer-core[cli]` floor in `pyproject.toml` | `make assets` after any dependency change |
| **cad-viewer-widget** | webpack-bundled into `cad_viewer_widget/labextension/` | no core dependency; the widget is pure ipywidgets | `PATH=<env>/bin:$PATH yarn --cwd js build` |
| **jupyter-cadquery** | none of its own - it renders through cad-viewer-widget | `ocp-viewer-core` floor, plus `cad-viewer-widget>=4.1.0,<4.2` | nothing to build; a widget release is what reaches it |
| **build123d Studio** | npm dependencies bundled by vite | `runtime/pyproject.toml`, group `core_cad` | `yarn build`, then `uv lock` for the runtime |

build123d Studio is maintained by its own session. Everything below describes what it needs; hand it over rather than editing that tree.

Two properties worth remembering before any of this:

- **The core's JavaScript declares a peer dependency on three-cad-viewer**: `">=5.0.3 <5.1.0"` in `js/package.json`. A tcv release inside 5.0.x needs no core release. A 5.1 does - the peer range is part of the core's JavaScript half, so moving it is a core JS change.
- **Safe-chain hides a package version younger than 48 hours from the resolver - but not this ecosystem's own packages.** `~/.safe-chain/config.json` excludes `ocp-viewer-core` and `three-cad-viewer` on npm, and `ocp-viewer-core`, `ocp-viewer` and `ocp-tessellate` on pip, so a pin or floor can be bumped the minute the release is up. **Not excluded**: `ocp_vscode`, `cad-viewer-widget` and `jupyter-cadquery` on pip - a floor pointing at a just-published version of one of *those* (jupyter-cadquery's `cad-viewer-widget>=...` after a widget release, say) resolves to the previous one for two days, silently, with only an `ℹ Safe-chain: Some package versions were suppressed ...` line to say so. Add it to the exclusions or wait.

---

## 1. three-cad-viewer upgrade

**In three-cad-viewer**: `yarn test:run` (1446 tests), `yarn build`, bump the version, publish to npm, tag.

Then, in each host, the pin is exact and moving it is the whole change:

**ocp_vscode**

```bash
cd ~/Development/CAD/vscode-ocp-cad-viewer
# edit package.json: "three-cad-viewer": "5.0.6"
yarn install
make vsix          # or `make install-vsix` to try it in VS Code
```

**ocp_viewer**

```bash
cd ~/Development/CAD/ocp-viewer
# edit package.json: "three-cad-viewer": "5.0.6"
make assets        # yarn install --check-files, then copies dist/*.js + css into static/
make tests
```

**cad-viewer-widget**

```bash
cd ~/Development/CAD/cad-viewer-widget
# edit js/package.json: "three-cad-viewer": "5.0.6"
yarn --cwd js install
PATH=$HOME/.uv-global/ocp79-vtk/.venv/bin:$PATH yarn --cwd js build
```

`yarn --cwd js build` **without `jupyter` on PATH half-fails and still says "Done"**: webpack succeeds, then `jupyter labextension build` dies with `/bin/sh: jupyter: command not found` and the labextension is never rebuilt. Always run it with the environment's `bin` on PATH, and check the timestamp of `cad_viewer_widget/labextension/build_log.json` afterwards.

**jupyter-cadquery**: nothing. It gets the new renderer when cad-viewer-widget is rebuilt (development) or released (users).

**build123d Studio**: bump `three-cad-viewer` in `package.json`, `yarn build`.

**ocp_viewer's copies are not in git.** `.gitignore` excludes `server/static/js/three-cad-viewer.esm.js`, the css and the whole `server/static/js/ocp-viewer-core/` directory, so `make assets` produces nothing to commit: the only committed record of what the viewer ships is `package.json` and `yarn.lock`. `make dist` depends on `assets` and re-runs it, so the wheel carries whatever `node_modules` held at build time - which is why the pin, not the working copy, is what has to be right before a release.

**Verify** in one host at least, in the browser: three-cad-viewer changes are visual, and nothing in any test suite here looks at pixels.

---

## 2. ocp-viewer-core, Python patch level

A Python-only fix. The JavaScript half does not move, so `js/package.json`, `js/src/version.js` and every npm pin stay exactly where they are.

**In this repository**

```bash
make bump-py part=patch     # pyproject.toml + ocp_viewer_core/_version.py
# write the CHANGELOG entry - "## Python v1.0.8 (date)"
make check && make tests
make clean && make dist     # wheel, sdist, and the JS tarball at its unchanged version
make check_dist
make release                # commit + tag v<py-version>
make upload                 # PyPI - irreversible
make create-release         # push, push --tags, gh release
```

**In the hosts**: nothing, unless the fix is one a host needs to require. The floors are minor-ranged (`>=1.0.6,<1.1.0`), so a patch reaches users on its own. Move a floor when a host now *depends* on the fix, and remember that moving it means releasing that host:

```toml
"ocp-viewer-core[cli]>=1.0.8,<1.1.0",   # ocp_viewer, ocp_vscode
"ocp-viewer-core>=1.0.8,<1.1.0",        # jupyter-cadquery
"ocp-viewer-core>=1.0.8,<1.1.0",        # build123d Studio, runtime/pyproject.toml, group core_cad
```

**If the patch adds or removes a core dependency**, the hosts that name the core's transitive dependencies have to follow:

- build123d Studio's `core_cad` group names them deliberately - "so Upgrade reaches them" - and `tests/unit/requirements.test.mjs:327` ("every dependency of ocp-viewer-core is declared, so an upgrade reaches it") reads `runtime/uv.lock` and fails when a dependency of the core is declared nowhere in `runtime/pyproject.toml`. **It checks that one direction only**: a name Studio still declares after the core has dropped it passes silently, so removals have to be noticed by hand - which is exactly what happened when `questionary` became an extra.
- A dependency that becomes an **extra** (as `questionary` did in 1.0.8) is the same event in reverse: the hosts that can reach the code ask for `ocp-viewer-core[cli]`, and the hosts that cannot lose the package.

---

## 3. ocp-viewer-core, JavaScript patch level

A JavaScript-only fix. `pyproject.toml` and `_version.py` do not move, no PyPI upload happens, and the Python floors in the hosts stay as they are.

**In this repository**

```bash
make bump-js part=patch     # js/package.json + js/src/version.js
# CHANGELOG entry - "## JavaScript v1.0.4 (date)"
make tarball                # dist/ocp-viewer-core-v1.0.4.tgz
cd js && npm publish        # npm - irreversible
```

**In every host that ships the JavaScript** - and that is all four - the npm pin is exact, so nothing moves until it is edited:

```bash
# ocp_vscode
# package.json: "ocp-viewer-core": "1.0.4"
yarn install && make vsix

# ocp_viewer
# package.json: "ocp-viewer-core": "1.0.4"
make assets

# cad-viewer-widget
# js/package.json: "ocp-viewer-core": "1.0.4"
yarn --cwd js install
PATH=$HOME/.uv-global/ocp79-vtk/.venv/bin:$PATH yarn --cwd js build

# build123d Studio
# package.json: "ocp-viewer-core": "1.0.4"
yarn build
```

**jupyter-cadquery** again ships no JavaScript of its own: it needs a cad-viewer-widget rebuild in development, and a cad-viewer-widget *release* for users.

**A user only gets the fix when the host is released** - the `.vsix`, the ocp_viewer wheel with its copied assets, the cad_viewer_widget wheel with its labextension, the Studio package. A published core JS patch that no host has taken is invisible.

**Check that the copies really moved**, before saying anything is testable:

```bash
cd ~/Development/CAD && for p in \
  "vscode-ocp-cad-viewer/node_modules/ocp-viewer-core/src" \
  "ocp-viewer/ocp_viewer/server/static/js/ocp-viewer-core" \
  "cad-viewer-widget/js/node_modules/ocp-viewer-core/src" \
  "build123d-studio/node_modules/ocp-viewer-core/src"; do
  for f in apply.js page.js render.js options.js index.js notify.js states.js animation.js logo.js version.js; do
    diff -q "$p/$f" "ocp-viewer-core/js/src/$f" >/dev/null 2>&1 || echo "STALE $p/$f"
  done
done
```

For the widget and Studio the bundle is what runs, not `node_modules`, so also grep the built artefact for the new `VERSION`:

```bash
grep -o 'VERSION = "[0-9.]*"' cad-viewer-widget/cad_viewer_widget/labextension/static/*.js
```

---

## 4. ocp-viewer-core, Python minor or major

**A minor on one side is a minor on both.** major.minor is the contract - the protocol, the `keys.py` vocabulary, the message shapes - and anything that crosses the wire moves both halves. So this scenario is never Python alone:

```bash
make bump-py part=minor
make bump-js part=minor     # separately, on purpose: there is no combined target
```

Both halves are then published - PyPI and npm - and the CHANGELOG carries an entry for each.

**Every host takes both**, in one release each:

| host | what changes |
| --- | --- |
| ocp_vscode | floor `>=1.1.0,<1.2.0`, npm pin `1.1.0`, `yarn install`, `make vsix`, release |
| ocp_viewer | floor `>=1.1.0,<1.2.0`, npm pin `1.1.0`, `make assets`, `make tests`, release |
| cad-viewer-widget | npm pin `1.1.0`, rebuild the labextension, release |
| jupyter-cadquery | floor `>=1.1.0,<1.2.0`, and a cad-viewer-widget release to match |
| build123d Studio | `core_cad` floor `>=1.1.0,<1.2.0`, npm pin `1.1.0`, `yarn build`, `uv lock` |

**The handshake will tell you if a host is left behind, and it is meant to.** `Session.send_data` (`comms.py:302`) puts `_core_version` into every model's config, and `page.js`'s `consumeCoreVersion` strips it before `applyConfig` and `console.error`s once per page when major.minor differ. That check runs wherever the shared page runs: ocp_vscode (`controller.ts` loads the core's `index.js`), ocp_viewer (`viewer.html:37`) and build123d Studio (`src/viewer/viewer.js:4`) all call `createPage`.

**cad-viewer-widget does not, and so jupyter-cadquery has no frontend check at all.** The widget imports `applyConfig`, `createRenderer`, `buildDisplayOptions` and the rest by name and builds its own UI from three-cad-viewer's `Viewer`/`Display`; `createPage` is never called, so `consumeCoreVersion` never runs and `_core_version` simply never reaches any code that would look at it. Upgrade that pair with extra care.

A separate mechanism, easy to confuse with this one: ocp_vscode's `check_upgrade` (`extension.ts:56`) compares the **ocp_vscode library version with the extension version** - not the core's - and treats `semver.diff` values of `null`, `"patch"` and `"prepatch"` as compatible, warning otherwise.

**A major** is the same procedure with `part=major`, plus the thing a major exists for: the wire vocabulary changed, so every host's own dispatch has to be re-read rather than assumed to still fit.

---

## 5. ocp-viewer-core, JavaScript minor or major

The mirror of section 4, and the same rule produces it: a JavaScript change that crosses the wire moves the Python half's minor too, even when no Python line changed. Run `make bump-js part=minor` **and** `make bump-py part=minor`, publish both, and take the table from section 4 unchanged.

The one case that is genuinely JavaScript-only at minor level is the **peer range**: moving `"three-cad-viewer": ">=5.0.3 <5.1.0"` to a new tcv minor is a change to what the core's JavaScript promises. It still crosses no wire, so by the contract it is a JS patch - but it means section 1 has to run in the same sitting, because every host resolves that peer against the tcv version it pins.

---

## The order that avoids re-work

1. **three-cad-viewer** first, if it is in play - the core's peer range and every host's pin depend on it.
2. **ocp-viewer-core** next: bump, changelog, check, tests, dist, upload, release, create-release.
3. **Bump the pins straight away** - the core and three-cad-viewer are excluded from safe-chain's minimum-age rule. Verify what actually resolved anyway (`grep '"version"' <host>/node_modules/ocp-viewer-core/package.json`), and remember that a floor on a freshly released *host* package is not excluded.
4. **cad-viewer-widget** before **jupyter-cadquery**: jc's floor is on the widget, so the widget has to exist first.
5. **ocp_viewer** and **ocp_vscode** in either order.
6. **build123d Studio** last, by its own session, with a note of what changed.

And the rule that survives every reordering: **never hand a host over for testing without refreshing its copy first.** A stale artefact tests the old code and reports the old behaviour, which has cost more rounds here than any bug.
