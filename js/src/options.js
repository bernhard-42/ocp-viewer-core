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

export function buildRenderOptions(config, defaults) {
  return pick(RENDER_OPTION_KEYS, config, defaults);
}

export function buildViewerOptions(config, defaults) {
  return pick(VIEWER_OPTION_KEYS, config, defaults);
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
export function buildDisplayOptions(config, defaults, geometry) {
  const fromConfig = pick(["glass", "tools", "keymap", "newTreeBehavior"], config, defaults);

  let theme = preset(config, "theme", null);
  if (theme == null && config != null && config.dark != null) {
    theme = config.dark ? "dark" : "light";
  }
  if (theme == null) {
    theme = defaults == null ? undefined : defaults.theme;
  }

  return {
    ...fromConfig,
    theme,
    cadWidth: geometry.cadWidth,
    height: geometry.height,
    treeWidth: geometry.treeWidth,

    // Capability flags the host owns: whether a tool exists in this surface at
    // all is not something a document can ask for.
    measureTools: defaults == null ? undefined : defaults.measureTools,
    selectTool: defaults == null ? undefined : defaults.selectTool,
    explodeTool: defaults == null ? undefined : defaults.explodeTool,
    zscaleTool: defaults == null ? undefined : defaults.zscaleTool,
    zebraTool: defaults == null ? undefined : defaults.zebraTool,
    externalMeasurementBackend:
      defaults == null ? undefined : defaults.externalMeasurementBackend,
  };
}
