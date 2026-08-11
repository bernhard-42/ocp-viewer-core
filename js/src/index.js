/**
 * The shared viewer policy, as one entry point.
 *
 * Everything here is host-neutral: it takes a three-cad-viewer instance and
 * plain data, and touches no DOM, no transport and no host. What stays with a
 * host is its canvas and its lifecycle, how it measures its own surface, and
 * the sending half of its Comms.
 *
 * Names are camelCase and values are plain JSON, because that is what this side
 * of the wire speaks. Python converts once, at the boundary, on its way out.
 */

export { applyConfig, isApplicable, GEOMETRY_KEYS } from "./apply.js";

export {
  buildDisplayOptions,
  buildRenderOptions,
  buildViewerOptions,
  preset,
  RENDER_OPTION_KEYS,
  VIEWER_OPTION_KEYS,
} from "./options.js";

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
