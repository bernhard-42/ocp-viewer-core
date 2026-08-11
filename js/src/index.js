/**
 * The shared viewer policy, as one entry point.
 *
 * Everything here is host-neutral. All of it but `page.js` takes a
 * three-cad-viewer instance and plain data and touches no DOM, no transport
 * and no host; `page.js` is the page, so it does. What stays with a host is
 * how it starts - where it loaded these modules from, where its settings come
 * from - and the sending half of its Comms.
 *
 * Names are camelCase and values are plain JSON, because that is what this side
 * of the wire speaks. Python converts once, at the boundary, on its way out.
 */

export { applyConfig, isApplicable, GEOMETRY_KEYS, VIEWS } from "./apply.js";

export {
  buildDisplayOptions,
  buildRenderOptions,
  buildViewerOptions,
  preset,
  DISPLAY_DEFAULTS,
  RENDER_DEFAULTS,
  RENDER_OPTION_KEYS,
  VIEWER_DEFAULTS,
  VIEWER_OPTION_KEYS,
} from "./options.js";

// Drawing a model and deciding where the camera ends up - the policy every
// client has to agree on, and the one that was hardest to get right.
export { createRenderer } from "./render.js";

// The page itself: the viewer, the message handling and the resizing that
// every host's HTML used to hold a copy of. The one module here that touches
// the DOM, because it is the page.
export { createPage } from "./page.js";

export {
  collectStates,
  currentStates,
  restoreStates,
  statesToRestore,
} from "./states.js";

export { addAnimationTrack, animate, animationDuration } from "./animation.js";

export { createNotifier, EVENT_KEYS } from "./notify.js";

// The splash. Data rather than policy, and here for the same reason the policy
// is: every client shows it, and four of them had their own copy.
export { logo } from "./logo.js";
