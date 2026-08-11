/**
 * Assembling the three option objects `Viewer.render` and `new Display` take.
 *
 * `viewer.html` built these inline in `render()` and `getDisplayOptions()`;
 * cad-viewer-widget builds them in `getDisplayOptions`, `getRenderOptions` and
 * `getViewerOptions`. Same three objects, three copies of the key lists.
 *
 * Which option belongs to which object is three-cad-viewer's fact rather than
 * Python's, so the lists live here in renderer names. What used to sit beside
 * them - `toCamelCase` and its override table - does not: the config arrives
 * already in renderer names, because Python converts once at the boundary. A
 * key that is still snake_case here is a host that has not converted, and it
 * will miss its entry and fall back to a default rather than be silently
 * renamed into something plausible.
 */

// The defaults themselves, not only the key lists. They describe
// three-cad-viewer, so every client should start from the same numbers and
// override only what is genuinely its own - a viewer whose ambient light or
// whose metalness differs from another's for no stated reason is a difference
// nobody chose.

/** Defaults for `Viewer.render`'s second argument. */
export const RENDER_DEFAULTS = {
  ambientIntensity: 1.0,
  directIntensity: 1.1,
  metalness: 0.3,
  roughness: 0.65,
  edgeColor: 0x707070,
  defaultOpacity: 0.5,
  normalLen: 0,
  angularTolerance: 0.2,
  deviation: 0.1,
  defaultColor: "#e8b024",
};

/** Defaults for `Viewer.render`'s third argument. */
export const VIEWER_DEFAULTS = {
  timeit: false,
  zoom: 1.0,
  position: null,
  quaternion: null,
  target: null,
  centerGrid: false,
  gridFontSize: 12,
  newTreeBehavior: true,
  studioEnvironment: "studio",
  studioEnvIntensity: 1.0,
  studioEnvRotation: 0,
  studioBackground: "environment",
  studioToneMapping: "neutral",
  studioExposure: 1.0,
  studioShadowIntensity: 0.5,
  studioShadowSoftness: 0.2,
  studioAOIntensity: 0.5,
  studioTextureMapping: "parametric",
  studio4kEnvMaps: false,
};

/**
 * Defaults for `new Display(container, options)`.
 *
 * `cadWidth`, `height` and `treeWidth` are here for completeness and are always
 * replaced by the geometry the host measures. The tool flags say which tools
 * exist in this surface at all, which is a host's decision - these are the
 * common answer, not the only one.
 */
export const DISPLAY_DEFAULTS = {
  cadWidth: 730,
  height: 525,
  treeWidth: 240,
  glass: false,
  tools: true,
  theme: "browser",
  pinning: false,
  newTreeBehavior: true,
  keymap: {
    shift: "shiftKey",
    ctrl: "ctrlKey",
    meta: "metaKey",
    alt: "altKey",
  },
  measureTools: true,
  selectTool: true,
  explodeTool: true,
  zebraTool: true,
  zscaleTool: false,
  externalMeasurementBackend: true,
};

/** Options `Viewer.render` takes as its second argument. */
export const RENDER_OPTION_KEYS = [
  "ambientIntensity",
  "directIntensity",
  "metalness",
  "roughness",
  "edgeColor",
  "defaultOpacity",
  "normalLen",
];

/** Options `Viewer.render` takes as its third argument. */
export const VIEWER_OPTION_KEYS = [
  "axes",
  "axes0",
  "blackEdges",
  "grid",
  "collapse",
  "ortho",
  "ticks",
  "centerGrid",
  "gridFontSize",
  "timeit",
  "tools",
  "glass",
  "up",
  "transparent",
  "control",
  "panSpeed",
  "zoomSpeed",
  "rotateSpeed",
  "clipSlider0",
  "clipSlider1",
  "clipSlider2",
  "clipNormal0",
  "clipNormal1",
  "clipNormal2",
  "clipIntersection",
  "clipPlaneHelpers",
  "clipObjectColors",
  "zebraCount",
  "zebraOpacity",
  "zebraDirection",
  "zebraColorScheme",
  "zebraMappingMode",
  "studioEnvironment",
  "studioEnvIntensity",
  "studioEnvRotation",
  "studioBackground",
  "studioToneMapping",
  "studioExposure",
  "studioShadowIntensity",
  "studioShadowSoftness",
  "studioAOIntensity",
  "studioTextureMapping",
  "studio4kEnvMaps",
];

/**
 * The config's value for a key, or the fallback.
 *
 * `null` and `undefined` both mean "not given": a host that sends an explicit
 * null is asking for the default, not for null. Every other falsy value -
 * `false`, `0`, `""` - is a value the caller meant, so the test is against null
 * rather than truthiness. Getting that wrong turns `axes: false` into `axes:
 * true` wherever the default is on.
 */
export function preset(config, key, fallback) {
  return config == null || config[key] == null ? fallback : config[key];
}

/** Pick a list of keys out of the config, defaulting each. */
function pick(keys, config, defaults) {
  const options = {};
  for (const key of keys) {
    options[key] = preset(config, key, defaults == null ? undefined : defaults[key]);
  }
  return options;
}

// Each builder starts from the core's defaults and lets a host override the
// ones that are genuinely its own. A host that passes nothing gets the shared
// answer, which is the point: the numbers describe three-cad-viewer, so a
// client differing from another for no stated reason is a difference nobody
// chose.

export function buildRenderOptions(config, overrides) {
  return pick(RENDER_OPTION_KEYS, config, { ...RENDER_DEFAULTS, ...overrides });
}

export function buildViewerOptions(config, overrides) {
  return pick(VIEWER_OPTION_KEYS, config, { ...VIEWER_DEFAULTS, ...overrides });
}

/**
 * The display options, which are what `new Display(container, options)` reads
 * and what seeds the viewer's state.
 *
 * `geometry` is the host's: only it knows the size of the surface it is drawing
 * on and what to subtract for its own chrome. It supplies `cadWidth`, `height`
 * and `treeWidth` already normalised.
 *
 * `theme` is the one value that is not carried across as-is. ocp_vscode's
 * config says `dark`, a boolean, while the renderer wants "dark" or "light" -
 * a change of value rather than of name, which the name mapping deliberately
 * does not express. Taken from `theme` when the host sends one, derived from
 * `dark` when it does not, and left to the default otherwise.
 */
export function buildDisplayOptions(config, overrides, geometry) {
  const defaults = { ...DISPLAY_DEFAULTS, ...overrides };
  const fromConfig = pick(["glass", "tools", "keymap", "newTreeBehavior"], config, defaults);

  let theme = preset(config, "theme", null);
  if (theme == null && config != null && config.dark != null) {
    theme = config.dark ? "dark" : "light";
  }
  if (theme == null) {
    theme = defaults.theme;
  }

  return {
    ...fromConfig,
    theme,
    cadWidth: geometry.cadWidth,
    height: geometry.height,
    treeWidth: geometry.treeWidth,

    // Capability flags the host owns: whether a tool exists in this surface at
    // all is not something a document can ask for.
    measureTools: defaults.measureTools,
    selectTool: defaults.selectTool,
    explodeTool: defaults.explodeTool,
    zscaleTool: defaults.zscaleTool,
    zebraTool: defaults.zebraTool,
    externalMeasurementBackend: defaults.externalMeasurementBackend,
  };
}
