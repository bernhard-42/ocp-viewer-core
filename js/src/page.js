/**
 * The viewer page: everything a host's HTML used to hold, held once.
 *
 * ocp_vscode's webview and ocp_viewer's page were the same file with a few
 * values injected, then two files with the injection removed - single-source
 * logic with a template problem, traded for a template fix with a duplication
 * problem. This is both: the logic lives here, in the package the hosts already
 * import, and each page keeps only what is genuinely its own.
 *
 * Which turns out to be very little. Of the 436 lines the two pages shared,
 * 295 were identical - including `getSize`, `normalizeWidth` and
 * `normalizeHeight`, which look host-specific and are not: both hosts measure
 * the window and subtract the same chrome. What differs is how the page is
 * started and how a message is sent, and those arrive as arguments.
 *
 * This is the one module in the package that touches the DOM, and it does so
 * because it *is* the page. Everything else here takes a viewer and plain data
 * and could run headless; that distinction is worth keeping, so new DOM work
 * belongs in this file or in a host, not spread through the others.
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

    // The viewer's own state, as the renderer reports it. What used to
    // be a variable per value here - status.zoom, status.position, _clipping,
    // _zebra - is one object the notifier keeps, under the names the
    // renderer notifies with: camelCase for the camera, which is sent
    // straight to checkChanges, and snake_case for everything that goes
    // through its notification map. render() writes into it too, after
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
            // The splash lives in the core, so the host asks for it by
            // name and sends only what it alone knows - its theme, its
            // tree width, its modifier keys. It used to ship its own
            // 200 kB copy and post the whole model across; two hosts had
            // the same file byte for byte.
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
        } else if (data.type === "clear") {
            viewer.clear();
        } else if (data.type === "show") {
            showViewer();
        } else if (data.type === "ui") {
            if (_config["_splash"]) {
                return;
            }
            if (data.config.debug) {
                debugLog("data.config", data.config);
            }
            // One dispatch, shared with cad-viewer-widget, in place of
            // thirty-eight else-ifs that had drifted from its copy. It
            // also brings the eleven studio setters this host never had:
            // set_viewer_config accepted them and the webview dropped
            // them without a word.
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
