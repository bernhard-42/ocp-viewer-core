/**
 * The viewer page, held once for every host that shows one.
 *
 * A host's HTML supplies only what is genuinely its own: where it loaded these
 * modules from, where its settings come from, and how to send a message. Even
 * measuring the surface is here - every host so far measures the window and
 * subtracts the same chrome, and one that does not can pass its own geometry.
 *
 * This is the one module in the package that touches the DOM, and it does so
 * because it *is* the page. Everything else here takes a viewer and plain data
 * and could run headless; that distinction is worth keeping, so new DOM work
 * belongs in this file or in a host, not spread through the others.
 */

/*
   Copyright 2026 Bernhard Walter

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

      http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
*/

import { animate } from "./animation.js";
import { applyConfig } from "./apply.js";
import { logo } from "./logo.js";
import { createNotifier } from "./notify.js";
import { buildDisplayOptions, preset } from "./options.js";
import { createRenderer } from "./render.js";
import { currentStates, restoreStates } from "./states.js";

const MIN_WIDTH = 450;

/**
 * Build the page.
 *
 * @param Viewer, Display, Timer  three-cad-viewer's three, passed in because
 *                                only the host knows where it loaded them from
 * @param send        (command, message) => void - the host's channel to Python
 * @param overrides   {display, viewer} - the settings this host differs on
 * @param theme       the host's resolved theme, for the observer below
 * @returns `{ showSplash, setTheme }` - the page listens for its own messages,
 *          which both hosts deliver as a `message` event: the extension posts
 *          into the webview, and the standalone's socket shim posts what came
 *          off the wire.
 */
export function createPage({ Viewer, Display, Timer, send, overrides, theme }) {
    var viewer = null;
    var display = null;
    var _shapes = null;
    var _meshData = null;
    var _config = null;
    var _camera_distance = null;
    var viewerOptions = {};
    var last_bb_radius = null;

    // The viewer's own state, as the renderer reports it: one object the
    // notifier keeps, under the names the renderer notifies with - camelCase
    // for the camera, which is sent straight to checkChanges, and snake_case
    // for everything that goes through its notification map. render() writes
    // into it too, after
    // reading the camera back off the viewer.
    //
    // It is also what goes on the wire. The extension answers a status
    // request with the last message the webview sent, replacing rather
    // than merging, so a delta would lose every earlier value - and
    // combined_config merges the viewer's state into the next show. The
    // notifier's delta plus this snapshot is what preserves both.
    var notifier = null;
    var renderer = null;
    var status = {};

    function debugLog(tag, obj) {
        console.log(tag, obj);
        var msg = tag + (obj ? " " + JSON.stringify(obj) : "");
        send("log", msg);
    }

    function nc(change) {
        return notifier == null ? null : notifier.notify(change);
    }

    function makeRenderer() {
        renderer = createRenderer({
            viewer: viewer,
            status: status,
            overrides: { viewer: overrides.viewer, theme: overrides.display.theme },
            // A tree width is a resize, and only this host knows the
            // other two dimensions.
            resize: () => {
                const displayOptions = getDisplayOptions(_config.theme);
                viewer.resizeCadView(
                    displayOptions.cadWidth,
                    displayOptions.treeWidth,
                    displayOptions.height,
                    displayOptions.glass
                );
            },
            sendStatus: (snapshot) => send("status", snapshot),
            debug: _config != null && _config.debug ? debugLog : null
        });
    }

    function makeNotifier() {
        notifier = createNotifier({
            viewer: viewer,
            // The delta is what changed; the snapshot is what the
            // extension will answer the next status request with.
            // Event keys - a selection, a pick, the active tool - ride
            // on the delta only, so a selection made minutes ago is not
            // replayed into an unrelated update.
            send: (delta) => send("status", { ...status, ...delta }),
            debug: _config != null && _config.debug ? debugLog : null
        });
        status = notifier.status;
    }

    function normalizeWidth(width, glass, tools) {
        const treeWidth =
            glass || !tools
                ? 0
                : preset(_config, "treeWidth", overrides.display.treeWidth);
        return Math.max(MIN_WIDTH - treeWidth, width - treeWidth - 20);
    }

    function normalizeHeight(height) {
        return height - 65;
    }

    function getSize() {
        return {
            width: window.innerWidth,
            height: window.innerHeight
        };
    }

    function getGeometry() {
        const size = getSize();
        const glass = preset(_config, "glass", overrides.display.glass);
        const tools = preset(_config, "tools", overrides.display.tools);
        return {
            cadWidth: normalizeWidth(size.width, glass, tools),
            height: normalizeHeight(size.height),
            treeWidth: preset(
                _config,
                "treeWidth",
                overrides.display.treeWidth
            )
        };
    }

    function getDisplayOptions(theme) {
        const options = buildDisplayOptions(
            _config,
            overrides.display,
            getGeometry()
        );
        // An explicit theme argument still wins: showViewer is called
        // with config.theme, and the observer below with the host's.
        if (theme) {
            options.theme = theme;
        }
        return options;
    }

    function showViewer(meshData, config) {
        debugLog("showViewer called");
        _meshData = meshData;
        _shapes = meshData.shapes || meshData;
        _config = config;
        const displayOptions = getDisplayOptions(config.theme);
        if (display == null) {
            const container = document.getElementById("cad_viewer");
            container.innerHTML = "";
            display = new Display(container, displayOptions);
        }
        if (_config == null) {
            debugLog("OCP CAD Viewer: config is null");
            _config = {};
        }
        if (_config.debug) {
            debugLog("_config", _config);
            debugLog("displayOptions", displayOptions);
        }
        // Reuse the viewer across shows: clear() tears down the scene and
        // resets activeTab to "tree" (which triggers leaveStudioMode if the
        // previous show was in Studio mode), but keeps the WebGL context,
        // ViewerState (preferences), and StudioManager (incl. PMREM env
        // cache) alive — saving a context teardown and HDR re-fetch per show.
        if (viewer != null) {
            viewer.clear();
        } else {
            viewer = new Viewer(display, displayOptions, nc, null);
            // After the viewer, because both read it. `nc` is the
            // trampoline that bridges the notifier to the constructor.
            makeNotifier();
            makeRenderer();
        }

        if (_shapes) renderer.render(_meshData, _config);

        // Three display options are re-applied on every show, for one reason:
        // the Display is built once, so everything it was constructed with is
        // dropped by every show after the first. The theme is the one that was
        // missing - `show(theme=...)` and a changed workspace setting both
        // computed it into displayOptions and then threw it away, because by
        // then `display` was no longer null.
        viewer.setTheme(displayOptions.theme);
        viewer.glassMode(displayOptions.glass);
        viewer.showTools(displayOptions.tools);

        debugLog("showViewer finished");

        return viewer;

        // viewer.trimUI(["axes", "axes0", "grid", "ortho", "more", "help"])
    }

    window.addEventListener(
        "resize",
        function (event) {
            if (viewer != null) {
                const displayOptions = getDisplayOptions(_config.theme);
                viewer.resizeCadView(
                    displayOptions.cadWidth,
                    displayOptions.treeWidth,
                    displayOptions.height,
                    displayOptions.glass
                );
                viewer.gridHelper.clearCache();
                viewer.gridHelper.update(viewer.getCameraZoom(), true);
                viewer.update(true, true);
            }
        },
        true
    );


    window.addEventListener("message", (event) => {
        var data =
            typeof event.data === "string" || event.data instanceof String
                ? JSON.parse(event.data)
                : event.data;

        if (data.type === "init") {
            init(data.paths, data.settings);
            return;
        }

        if (data.type === "logo") {
            // The splash lives in the core, so a host asks for it by name and
            // sends only what it alone knows: its theme, its tree width and
            // its modifier keys.
            const splash = logo();
            data = {
                ...splash,
                config: { ...splash.config, ...(data.config || {}) }
            };
        }

        if (data.type === "data" && data?.data?.shapes?.parts?.length > 0) {
            const timer = new Timer("webView", data.config.timeit);

            const oldStates = currentStates(viewer);

            let meshData = data.data;
            let config = data.config;

            if (config._splash) {
                const displayOptions = getDisplayOptions(config.theme);
                config.zoom = Math.min(
                    1.0,
                    displayOptions.cadWidth / displayOptions.height
                );
                // debugLog("logo zoom =", config.zoom);
            }

            showViewer(meshData, config);

            // Explicit states win, otherwise the user's prior visibility
            // choices are restored for whatever survived into the new
            // model - in one batched setStates either way, because a
            // per-key loop is a repaint per key and freezes the host.
            restoreStates(viewer, meshData.shapes, oldStates, config.states);
            timer.split("states updated");

            timer.stop();
        } else if (data.type === "screenshot") {
            var promise = viewer.getImage(data.filename);
            promise.then((result) => {
                send("screenshot", {
                    filename: result.task,
                    data: result.dataUrl
                });
            });
        } else if (data.type === "set_relative_time") {
            if (viewer) {
                viewer.setRelativeTime(data.value);
            }
        } else if (data.type === "backend_response") {
            viewer.handleBackendResponse(data);
        // No `clear` or `show` branch: nothing in any host sends either, and
        // `show` was a landmine rather than merely dead - `showViewer()` with
        // no arguments evaluates `getDisplayOptions(config.theme)` against an
        // undefined config and throws before reaching its own null guard, and
        // it assigns `_meshData = undefined` on the way, destroying the stored
        // model so that even a corrected call could not re-show. If a host
        // ever needs to re-render what it already has, that is `showViewer(
        // _meshData, _config)` guarded on `_meshData` being present.
        } else if (data.type === "ui") {
            if (_config["_splash"]) {
                return;
            }
            if (data.config.debug) {
                debugLog("data.config", data.config);
            }
            // One dispatch for every key, shared with every other host, so
            // that a setter cannot exist in one client and not another.
            applyConfig(viewer, data.config, {
                // Only the host knows the other two dimensions, so a
                // viewport key is a resize rather than a setter.
                resize: (key, value) => {
                    const displayOptions = getDisplayOptions(data.config.theme);
                    const glass =
                        data.config.glass !== undefined
                            ? data.config.glass
                            : displayOptions.glass;
                    viewer.resizeCadView(
                        key === "cadWidth" ? value : displayOptions.cadWidth,
                        key === "treeWidth" ? value : displayOptions.treeWidth,
                        key === "height" ? value : displayOptions.height,
                        glass
                    );
                },
                onUnknown: (key) => {
                    debugLog(`ui: no setter for '${key}'`);
                }
            });
        } else if (data.type === "animation") {
            // Explode goes off first: both transform the same objects,
            // and animating an already-displaced model is wrong.
            animate(viewer, data.data, data.config.speed, (action) => {
                console.error(`Unknown animation action: ${action}`);
            });
        }
    });

    return {
        /** Draw the splash, with whatever the host knows that the core cannot. */
        showSplash(config) {
            const splash = logo();
            showViewer(splash.data, { ...splash.config, ...config });
        },

        /** The host's theme changed under it - a VS Code colour theme, say. */
        setTheme(next) {
            if (viewer != null) {
                viewer.setTheme(next);
            }
        }
    };
}
