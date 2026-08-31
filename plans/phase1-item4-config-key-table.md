# Phase 1, item 4 — the config key table

Migration architect's plan. First draft 2026-08-10; **second draft, revised against the three project architects' reviews**, same day. Governance is `APPROACH.md`: all three architects returned *agree with required changes*, this draft folds those changes in, and it goes back to them for sign-off before Bernhard decides whether implementation starts. **Nothing is implemented on the strength of this document.**

---

## 0. What this plan is, and what it is not

Item 4 builds **one machine-readable description of every configuration key in the viewer ecosystem, and two generated artefacts from it — one Python, one JavaScript.** It changes no runtime behaviour except in one deliberately-chosen place (§9.1). It does not move `config.py`, does not introduce `Session`, does not touch `Comms`, and does not generate any host's settings UI. Those are items 5, 6, 7, 14 and 16, and each of them consumes this table rather than being built by it.

The previous attempt at this item was discarded because it asserted behaviour it had inferred from greps. This plan therefore separates three grades of claim throughout:

- **[A]** — established by a project architect with a `file:line` citation **and re-confirmed by that architect in their review of this plan**. The second half is new in this draft and it matters: in the first draft `[A]` meant "their memory says so", and the review round proved that is not the same thing.
- **[M]** — derived by me from the source. Every one names how it was derived and is a request for confirmation by the owning architect.
- **[?]** — open. Written down as a question and not built on.

### 0.1 What the review round did to the grading scheme, and why it is recorded here

**Three `[A]` claims were wrong, and in each case the architect who owned them found it and said so.** That is the grading scheme working, and it is worth stating plainly because it is the plan's main defence against the failure that discarded the previous attempt.

- **three-cad-viewer:** `STATE_TO_NOTIFICATION_KEY` is **47** entries, not the 40 its memory stated. The architect re-derived it scoped to the declaration, corrected the memory, and diagnosed its own defect: *"I published a bare integer with a `file:line` citation attached, and the citation made it look measured when it was not. **A number is not a mechanism either.**"* Its closing observation is the one to keep: **had this plan deferred to the `[A]` grade instead of flagging its own count as suspect, §7.2's C3 would have been built on 40 and would have silently skipped seven keys.**
- **ocp_vscode:** the "nineteen keys settable through `set_viewer_config` with no `ui` branch" claim was graded `[A]` and sourced to it, and its memory does not say it. The memory records a *coverage* fact (those keys have no `ui` branch); this plan had silently upgraded it into a *behavioural* one (they are sent and dropped). The real number is **11** (F1, §5.11).
- **ocp_tessellate:** §2's `"so a host can round-trip them"` was quoted as `[A]` from its memory, and the architect has withdrawn it — *"my own unsupported rationale, written as if it were a finding"*, contradicted by the sentence beside it in the same file. Replaced by measurement: of 51 keys, **9 are read, 6 are shadowed by signature defaults, 36 are inert**.

Two of the three were memory defects rather than reading errors, and both owners fixed their memory rather than the plan.

**The rule generalised, after the sign-off round caught two more instances — both in the plan's own prose, both reproduced faithfully from an architect's wording, and neither caught by the citation, because the citations were correct:**

> **An assertion of a property is judged, not extracted, unless the instance that exhibits it travels with it.** A count needs its enumeration. A claimed disagreement needs the pair that disagrees. A claimed derivation needs the two facts it derives from, named.

The two instances were §7.2's *"C1′ and C2 genuinely disagree in both directions"* — where only one direction existed on today's data — and §5.12's *"(a′) is decidable from two extracted facts"*, where the second fact was not extractable as the schema stood. Both read as demonstrations; neither demonstration had been run. **§5.12 now closes the gap the three-cad-viewer architect identified: its evidence discipline attaches to *columns*, and these were claims in *prose*, so nothing was checking them.**

The narrow original still holds as the leading case: **a count is judged unless the enumeration it came from is carried beside it.** Prose that summarises a set ("all the `*Tool` visibility flags") is fine; a number derived from that prose is not.

### 0.2 Settled by Bernhard, 2026-08-10, before the review round

- **`zscale_tool` is refused — no row.** *"zscale_tool is not a CAD tool, but a GDS tool (chip tool), hence it doesn't appear in ocp_vscode and doesn't need to be tracked in this project."* Out of the table's **domain**, not missing from its coverage (§8.4).
- **`new_tree_behavior` is a display option** — *"whether the navigation tree behaves the default or the legacy way"*. ocp_vscode's placement is correct, cad-viewer-widget's is not. The three-cad-viewer architect has since confirmed the renderer agrees, **and established that the widget's filing is non-canonical rather than broken** (§8.2).
- **`studio_ao_intensity` stays an explicit manual translation** to `studioAOIntensity` — *"like for some others, we can keep studio_ao_intensity a manual translation"* — joining the existing override family rather than changing the derivation rule. A direct confirmation of §3 and §4: axis 1 is a datum.

### 0.2a Settled by Bernhard, 2026-08-10, after the review round

The three escalations of §19 are all answered. **Nothing is open with him on this item.**

- **§9.1a — fix ocp_vscode 4.x now.** *"ocp_vscode 4.x should get the one-line `optionKeyOverrides` fix during its fix-freeze."* §8.2 therefore carries **no exception at all**, permanent or scheduled, and §15's "two repositories during a fix-freeze" stops being a risk and becomes a decision taken.
- **§16.12 — the `DEFAULTS` reduction goes on ocp_tessellate's 4.0.0 list now.** *"ocp_tessellate's DEFAULTS reduction should go on the 4.0.0 list now."* The ocp_tessellate architect's argument carried: leaving it as a question is exactly how the 3.5.0 fallbacks become permanent by neglect. **The halves are split in §14** — item 4 *records* the fossils mechanically; ocp_tessellate *deletes* them upstream.
- **§16.13 — assume direct `to_ocpgroup` callers exist.** *"it is a public API, so it could be. We should assume someone does."* So the reduction is **breaking**, which is consistent with it being 4.0.0 work, and no row may assume ocp_tessellate's dict is the only way its value is set (§5.9).
- **And the authoritative account of `_splash`**, which supersedes both this plan's first two drafts and the ocp_vscode architect's memory. It is narrower than either: the flag exists for **one guard**. Folded into §8.5.

### 0.3 Changes since the first draft, for re-review

Every change below is driven by a numbered review finding, so a reviewer can go straight to what moved. TCV = three-cad-viewer, OV = ocp_vscode, OT = ocp_tessellate.

| section | what changed | driven by |
| ------- | ------------ | --------- |
| §0.1 | new — the three corrected `[A]` claims and the counts-are-judged rule | TCV blocking answer, OV F1, OT M6 |
| §1 | item 5's sentence gains the transitive-OCP caveat; **item 8's sentence was false and is rewritten**; item 8 now takes one row's classification | OT M5, OT §1, TCV §1 |
| §2 | six bullets corrected or replaced; three added | TCV F1/F3/F7, OV F1/W1, OT M6 |
| §3 | axis 2's exclusion re-argued (it is the *runtime gate*); axis 4 gains renderer-side evidence; §16.7 closed | TCV §3 |
| §4 | amended: inbound **names** classified, inbound **values** decoded and the decoding is the core's | OV F4 |
| §5.3 | zebra derivation was wrong; `destination(ZebraOptions)` is an explicit datum; TS excess-property consequence for item 16 | TCV F5 |
| §5.5 | `derived` added as a fourth `lifetime` | OT M5/W1 |
| §5.6 | refusal message is per-key; the fifth host-naming site claimed; scope stated honestly | OV F5 |
| §5.7 | **the classification rule is replaced**; all six re-derived; `class` becomes mostly derived rather than judged | TCV F2 |
| §5.8 | colour `repr` mandatory; collapse is five representations; clip normals' state ≠ wire; `0` is a distinct off | OT M4/M7, TCV "would improve" |
| §5.9 | never source a default from TSDoc; ocp_tessellate authoritative for 9 of 16 only; resolved values for the three `None` colours; normalised colour comparison | TCV §5.9, OT §5.9/§16.9 |
| §5.11 | `ui` split into `ui` + `live_settable`; item 10's checklist is **11**, not 19 | OV F1 |
| §5.12 | `default_source` added; counts are judged | OT W2, §0.1 |
| §7.1 | silence #1 restated: **no diagnostic at all** on the render path | TCV F3 |
| §7.2 | 47 adopted; **C1 replaced by C1′**; strip-list as data; export accepted with conditions; fixture kept regardless | TCV F1/F4/§7.2 |
| §7.4 | reachability gains the protocol/handshake category | OV F3 |
| §8.2 | the widget is non-canonical, not buggy, and must not be bug-reported; `viewer.html:100` re-attributed | TCV F6 |
| §8.3 | ocp_tessellate's `DEFAULTS` added as a coverage source; renderer section comments added | OT W3, TCV "would improve" |
| §8.5 | **new** — the protocol/handshake inventory, and `_splash`'s mechanism | OV F2/F3 |
| §9.1 | "permanent exception" corrected; the studio-mode test instructions added | OV W4, TCV §16.5 |
| §9.2 | `_splash` open question replaced by measurement; "fix" now requires an independent implementation to agree | OV F2, OT W5 |
| §10.3 | **families 1–4 rebuilt**; family 1 was `CONFIG_CONTROL_KEYS` renamed | OT M1/M2/M3, OV W5 |
| §11 | `CONFIG_UI_KEYS` dies at item 7, not item 5 | OV F6 |
| §16 | §16.1, §16.3, §16.4, §16.5, §16.6, §16.7, §16.8 all closed; three new | all three |
| §17 | three corrections added, one withdrawn as wrong | OT M8 and its three missed corrections |
| §19 | **new** — the coverage audit of the review round | coordinator's requirement |
| §0.2a, §9.1, §9.1a, §13, §15 | **§9.1a closed: 4.x is fixed now.** No exception in the equivalence test; commits 7 and 8 merge; the fix-freeze risk becomes a decision | Bernhard |
| §14, §16.12, §17.13 | **the `DEFAULTS` reduction goes on ocp_tessellate 4.0.0 now**, with the two halves split — item 4 records, ocp_tessellate deletes | Bernhard, OT §16.9 |
| §5.9, §14, §16.13 | **direct `to_ocpgroup` callers are assumed to exist**, so the reduction is breaking and no row may treat the dict as the only writer | Bernhard |
| §2, §8.5 | **`_splash`'s authoritative account**, which is narrower than either draft: one guard, and the forwarded `False` is load-bearing | Bernhard |
| §8.5a, §12, §15 | **post-review addition:** the outbound `_splash` path confirmed including the `_tessellate` ordering, and the migration constraint it proves — a session-lifetime settings cache forces `Camera.RESET` on every show after the first. No decision changes; item 6's per-show cache acquires a proof case and item 9 an assertion | Bernhard, relayed |

**Third draft — the sign-off round.** All three architects signed off with conditions; §18 lists every condition against the section that applies it, and this table carries the same set for anyone reading top to bottom.

| section | what changed | driven by |
| ------- | ------------ | --------- |
| §0.1, §5.12 | **the judged/extracted rule generalised** — an assertion of a property is judged unless the instance exhibiting it travels with it; and §5.12 gains a bullet for claims made in *prose*, which its column-attached evidence never checked | TCV observation |
| §7.2 | **"disagree in both directions" was overstated** — one direction on today's data; the second is a mis-filed `iface`, which is the better argument | TCV C1 |
| §5.7, §5.8, §5.12, §13 | **(a′)'s domain half made derivable** via `wire_repr`'s three states, verified on all eight keys; `class` genuinely derived; a sequencing constraint in commit 4 | TCV C2 |
| §7.2, §16.2 | **the export is committed as 5.0.4**, with `STATE_TO_NOTIFICATION_KEY` included and the breaking-by-contract cost on the record | TCV C3 |
| §5.5, §12 | **`lifetime = derived` redefined** as *no host-independent input path*, because the widget sets `normal_len`; item 16 must not filter traitlets on `lifetime` | OT C1 |
| §2, §8.5, §8.5a, §15 | **`_splash`: the field is inert, the event is normative** — neither host reads the payload; §15's third route restated as a lost delivery; the normative statement gains three clauses | OV A |
| §8.2, §9.2, §5.12 | **`viewer.html:100` is live and `:79` is dead** — my `[M]` was inverted; the lesson generalised | OV B |
| §16.11 | **six, not five**, with the six/three row-note split | OV C |
| §9.2, §12 | the cad-viewer-widget `Viewer.normal_len` property defect recorded as a *fix* candidate, out of scope, flagged for item 16 | OT note 2 |
| §16.10 | the `normal_len` objection **withdrawn**, with its author's diagnosis kept | OT |
| §17.13 | the `DEFAULTS` reduction is breaking via the **read-back** path, not the write path | OT note 1 |
| §18 | rewritten from *asks* into **the conditions record** — what goes to Bernhard | this round |

---

## 1. Item 4 inside Phase 1

Phase 1 is items 4 to 9. Item 4 is first because 7, 14 and 16 all generate from it and because it is the only one of the six whose deliverable is *data* rather than code motion — it can be built, checked and proved equivalent to today's behaviour while `config.py` has not moved, which makes it the cheapest place in the migration to be wrong and find out.

What each of the other five takes from it. **The first draft offered these five sentences as the most valuable thing to attack, and the attack landed: the fifth was false.**

- **Item 5 (the move)** takes the generated Python module as the thing `config.py` imports once it lands in the core, so the move is a move rather than a rewrite. The artefact must import without OCP and without a host. **Scope correction (OT):** that constrains the *generated module only*. `ocp_viewer_core.config` will still pull OCP transitively through `ocp_tessellate`'s `Color`, for the reason `requs.md:587` already records, and this sentence does not claim otherwise.
- **Item 6 (`Session`)** takes the filters. `combined_config` reads host settings and live status over separate connections and filters the status with `workspace_filter` **[A** — `config.py:670`, `:753`, OV**]**. A `Session` caching one settings read for one `show()` needs to know which keys the filter will ask for before it asks; a table predicate answers that. **Confirmed by OV**, with the arithmetic: 6 of the 9 connections are the identical `config` command and 3 of those exist only so `preset("timeit", …)` can read a value already in `DEFAULTS`, so caching one settings read removes 5 of 9. Item 4 removes no round trip; it removes the reason the reduction would be guesswork.
- **Item 7 (inject)** takes the `owner` column (§5.6). **Confirmed by TCV** — the `document`/`surface` split is a property of the key and needs nothing from the renderer — and **by OT** — none of its sixteen keys is `surface`, all are `document`.
- **Item 8 (codec).** The first draft said *"item 8 takes nothing"*. **That is false, and OT found it.** `normal_len` is not configuration: it is a field of the model payload computed by the tessellator, and it flows **model → config**, the opposite direction from every other row. `tessellate_group` computes `shapes["normal_len"] = max_accuracy / deviation * 4 if render_normals else 0` (`convert.py:1988`); `get_normal_len(render_normals, shapes, deviation)` (`convert.py:2073-2074`) is a compatibility shim that **ignores its first and third arguments** and returns `shapes["normal_len"]`, carrying its own `# TODO` to that effect; and `show.py:422-426` writes it into the config dict unconditionally, overwriting anything a caller supplied **[A, OT]**. So the corrected sentence is: **item 8 takes one row's classification, and the boundary between "configuration" and "model payload" runs through `params` in `show.py`, not around it.** §7.4 resolves the row (it is kept, as `lifetime = derived`) and §16.10 records that I took the option OT did not prefer, with the reason it did not have. Separately and compatibly, **TCV confirms that the codec surface proper takes nothing**: the encoded-buffer format `{shape, dtype, buffer, codec}` and the config surface share no vocabulary, no code path and no file, and `decodeBuffers`/`resolveInstances` touch only `Shape` payloads. Both statements are true; §19 explains why they are not in conflict.
- **Item 9 (the kit)** takes the checks that need a live `Session`; the host-free checks of §8 migrate into it when it lands rather than being written twice. **Confirmed by TCV and OT.**

---

## 2. What is established, and by whom

All **[A]**, and every one below either survived its owner's review unchanged or is the corrected replacement for something that did not.

**three-cad-viewer**

- **Four independent naming axes** — option-interface field, `ViewerState` key, wire name, setter — plus a fifth vocabulary for the deprecated `shapes.studioOptions`. `STATE_TO_NOTIFICATION_KEY` maps axes 2→3 only. Worked example: `viewerOptions.tab` / state `activeTab` / wire `tab` / setter `setActiveTab` (`types.ts:388`, `viewer-state.ts:135`/`:251`/`:278`, `viewer.ts:1364-1366`). **Re-confirmed exact.**
- **The map has 47 entries; `STATE_KEYS` has 76; 29 state keys are absent from the map, and 47 + 29 = 76.** Corrected during review, method recorded, the 29 now enumerated in the memory rather than summarised (`viewer-state.ts:169-252`, `:266-321`).
- **`checkChanges` is a deduplicating state diff, not an event stream**; `lastNotification` survives `clear()` and is **not** seeded by `render()`'s direct config dump, which bypasses it and sends everything with `old: null` (`viewer.ts:826-867`, `:1134`, `:1770-1787`).
- **`selectedShapeIDs` carries a boolean appended to a string array**, and clearing sends a bare `[]` with no trailing boolean — an asymmetry (`measure.ts:404`, `:334`; consumer `tools.ts:215-234`).
- **Six wire keys are produced by a direct `checkChanges` call rather than by the state-notification adapter**: `states`, `lastPick`, `selectedShapeIDs`, `activeTool`, `explode`, `tab`. **This replaces the first draft's "six wire keys are not state keys at all", which was false for two of them** and which the plan inherited from an imprecise heading the architect has since retitled. Precisely: four are genuinely not state-backed (`states`, `lastPick`, `selectedShapeIDs`, `explode`); `activeTool` **is** a state key (`viewer-state.ts:246`) carrying a *different vocabulary* on the wire (state holds the lowercase button name `"distance"`, the wire holds `"DistanceMeasurement"` — `display.ts:1840-1859`, `tools.ts:13-18`); and `tab` is fully state-backed as `activeTab` (`viewer-state.ts:278`) with a second direct producer at `display.ts:2221`.
- **The camera quartet `position`/`quaternion`/`target`/`zoom` ARE state keys** (`viewer-state.ts:219-222`) — the first draft said they were not. The accurate and sharper fact: they are **never notified from state and never written back from the camera**. `updateViewerState` is their only writer (`viewer-state.ts:700-714`); the camera setters mutate the camera and call `update()` with no `state.set` (`viewer.ts:3199-3301`); the wire values come from the live `Camera`/`Controls` (`viewer.ts:1035-1043`). So **`state.get("position")` holds whatever the embedder passed at the last `render()`, forever, and diverges from the wire on the first orbit.** Consequence for item 13: read camera values from the wire or from `getCameraPosition()`/`getCameraQuaternion()`/`getCameraTarget()`/`getCameraZoom()` — **never** from `viewer.state`.
- **There are two option-filter paths and they differ in loudness.** The **constructor** path `new ViewerState(options)` → `_applyOptions` warns on an unknown key (`viewer-state.ts:583-586`). The **`render()`** path `setRenderDefaults`/`setViewerDefaults` → `updateRenderState`/`updateViewerState`/`updateStudioState` → `_update` **has no `logger` call on that branch at all** (`viewer-state.ts:628-630`). The runtime gate on both is `isStateKey`, never the TypeScript interface.
- **`ZebraOptions` is a standalone interface** (`types.ts:392-403`); `ViewerOptions` does **not** extend it. `ViewerOptions extends StudioModeOptions` (`types.ts:320`) is true of the studio half only. The two are joined only in `CombinedOptions` (`types.ts:431-436`), which is not the type of any `render()` argument.
- **`ViewerState.set`'s change detection is `===` or elementwise array comparison** (`viewer-state.ts:337-343`, `:613`), so a `THREE.Vector3` never compares equal to another and **every** `setClipNormal` notifies even when the numbers are identical.

**ocp_vscode**

- **`toCamelCase` and `STATE_TO_NOTIFICATION_KEY` run in opposite directions** and are not two copies of one mapping (`viewer.html:360-365`).
- **`studio_ao_intensity` is inert end to end** — `toCamelCase` yields `studioAoIntensity`, the state key is `studioAOIntensity`, no override exists, no `ui` handler exists; verified as the *only* mapping miss against the bundle's 76-entry `STATE_KEYS`. **Re-verified during review.**
- **Eleven keys are `set_viewer_config` parameters with no `ui` branch: the eleven `studio_*` keys, exactly.** This replaces the first draft's "nineteen". The nine non-studio keys the draft listed (`ticks`, `grid_font_size`, `deviation`, `angular_tolerance`, `default_color`, `modifier_keys`, `theme`, `timeit`, `control`) are **not** `set_viewer_config` parameters at all (`config.py:334-391`), so they cannot be sent and dropped. Most are `set_defaults` parameters, none is in `CONFIG_SET_KEYS`, so `set_defaults` stores them in `DEFAULTS` and they take effect on the next `show()` — **correct behaviour for show-time parameters, not a defect.** `modifier_keys`, `theme` and `control` are not settable from Python by either function.
- **Precedence is kwargs > `DEFAULTS` > live viewer status > host settings**, with the status half gated on `_splash` (`config.py:735-757`).
- **`cad_width`, `height` and `theme` are the complete surface-key set**, branched on the host in two places with **two different messages**: `cad_width`/`height` → *"determined by the VSCode panel size"*, `theme` → *"can only be set in VSCode config"* (`show.py:365-375`). The `params` filter (`show.py:345-364`) excludes all three as one set; the kwargs loop splits the same three across two branches.
- **`tree_width` is a `document` key by intent**, commented out of both lists by `743696a` — *"respect tree_width from VS Code config and make tree_width adaptable with show"* — which touched `show.py`, both `viewer.html` copies and `src/controller.ts` together; `viewer.html:577-585` acts on it. **Promoted from `[M]`; §16.8 closed.**
- **`_splash` exists for exactly one guard**, and Bernhard's account is authoritative on its purpose (§8.5): when the viewer is opened the first time the flag is true and `workspace_config()` returns `_splash == True` while the logo is shown, and `_tessellate` uses that to stop `reset_camera` being `KEEP`. **It is not a general handshake and it is not dead code.** Citations: `controller.ts:49`/`:126`, `standalone.py:227`/`:379`, `config.py:750`, `show.py:242-256`, `:345-364`, `:376-381`, `:383`; and the proof that the flag is genuinely `True` mid-flight — with the host stubbed to report `_splash: True`, `show(b, reset_camera=Camera.KEEP)` emits `reset_camera: "reset"` on the wire, while past splash the same call emits `"keep"`.
- **The host clears the flag on the *arrival* of the first model message, not by reading the forwarded value.** This corrects the second draft, which said the forwarded `False` "is how the host learns to flip its own property". Settled from source by the ocp_vscode architect: `_splash` occurs in host code in exactly three places and **all three are writes** — `controller.ts:126`, `standalone.py:379` and the literal in `src/logo.ts:205`. **There is no read.** `controller.ts:219-227` takes `data` as `message.toString().substring(2)`, a raw string, forwards it verbatim with `postMessage(data)` and **never parses it** (the `C:` branch immediately above *does* `JSON.parse`), then unconditionally does `if (this.splash) this.splash = false;`. `standalone.py:396-404` is identical. So the **field in the payload is inert** and the **event is what matters**. Bernhard was describing the design; the code realises it a different way with an identical observable result, **because `show.py:383` makes the payload constant — two mechanisms that agree today only because the value never varies.**
- **`status()` decodes the viewer's int `collapse` into the `Collapse` enum** via `COLLAPSE_REVERSE_MAPPING`, warning on an unknown value (`config.py:688-693`). This is a viewer→python decoding and it is the **core's**, not a host's. `workspace_config`'s string decodings (`config.py:723-726`) are the host's.
- **Nine round trips for a first `show()`, eight for a repeat** — the missing one is `get_defaults` at `show.py:462`, the clip-insight reset branch, skipped when the bbox is unchanged and the camera is kept. Six of the nine are the identical `config` command. **Re-measured during review.**
- **`ui_filter` has no caller** (`config.py:665`); `workspace_filter` has exactly one (`config.py:753`). **`CONFIG_UI_KEYS` has two references** — `ui_filter` at `:667` and `CONFIG_WORKSPACE_KEYS = CONFIG_UI_KEYS + [...]` at `:205`.
- **None of the five list names is in `config.py`'s `__all__`**, so `from ocp_vscode import CONFIG_KEYS` already fails today; only the explicit submodule import would work, and nothing anywhere uses it.

**ocp_tessellate**

- **`ocp_tessellate` declares no OCP provider deliberately**, and the rule propagates to `ocp_viewer_core` (`ocp-tessellate/pyproject.toml:29`; `ocp_utils.py:26`).
- **`ocp_tessellate.defaults.DEFAULTS` holds 51 keys, of which exactly 9 are ever read, 6 more are shadowed by a `to_ocpgroup`/`tessellate_group` signature default that never consults the dict, and 36 are inert** — read by nothing, reachable through nothing. The nine are read at five call sites: `default_color` (`convert.py:214`, `cad_objects.py:424`), `default_facecolor`/`default_thickedgecolor`/`default_vertexcolor` (`convert.py:221`, `:224`, `:227`), `deviation` and `edge_accuracy` (`convert.py:1877-1878`), and `deviation`, `angular_tolerance`, `render_edges`, `render_normals` (`convert.py:1919-1923`). That is the complete set of `get_default(` and `preset(` call sites in the package. **This replaces the first draft's `[A]` quotation of "so a host can round-trip them", which the architect has withdrawn as its own unsupported rationale.**
- **`ocp_vscode` imports nothing from `ocp_tessellate.defaults`** — confirmed independently by both the ocp_tessellate and ocp_vscode architects.
- **`Color` discriminates a tuple's scale by content, not by declaration** (`utils.py:34-99`), so `(1, 1, 1)` is near-black and `(1.0, 1.0, 1.0)` is white, a mixed tuple silently becomes grey with a warning and no exception, and a 4-tuple's alpha scale is inferred from whether the value exceeds 1.0.
- **`default_edgecolor` and `default_opacity` are never read anywhere in ocp_tessellate** — they occur only as `DEFAULTS` entries (`defaults.py:127`, `:136`) and in the dead `add_shape_args`/`tessellation_args` filters. They are renderer keys.
- **`default_facecolor`, `default_thickedgecolor` and `default_vertexcolor` are `None` in `DEFAULTS` deliberately** (`defaults.py:133-135`) so `_default_or` falls through to the module constants (`convert.py:220-228`); the operative defaults are `"Violet"`, `"MediumOrchid"`, `"MediumOrchid"` (`convert.py:30-32`).
- **`render_edges` is one of the nine read keys** (`convert.py:1922`), decides `compute_edges`, is part of the tessellation cache key (`tessellator.py:114-123`), is force-set to `True` by ocp_vscode on every show (`show.py:399`), and **is in no `CONFIG_*` list and in no settings schema**.

**Cross-cutting**

- **`status()` is an interface, not a protocol**, and in every host the answer is a value somebody pushed earlier; in most hosts it is **stale by design** (`requs.md`, and `ocp-viewer-design-discussion`).

---

## 3. Decision 1 — which naming axes the table carries

Six vocabularies, not four: the five axes three-cad-viewer establishes, plus the Python snake_case config key.

| # | axis | example | in the table? |
| - | ---- | ------- | ------------- |
| 0 | Python config key | `studio_ao_intensity` | **yes — the primary key** |
| 1 | renderer option field | `studioAOIntensity` | **yes — the `option` column** |
| 2 | `ViewerState` key (`STATE_KEYS`) | `studioAOIntensity`, but `activeTab` for `tab` | **no — verification fixture only** |
| 3 | wire / notification name | `studio_ao_intensity`, but `tab` for `activeTab` | **yes — the `wire` column** |
| 4 | setter method | `setActiveTab` | **no** |
| 5 | deprecated `shapes.studioOptions` shorthand | `aoIntensity` | **no** |

**Axis inventory confirmed exact by the three-cad-viewer architect**, worked example included.

**Axis 0 is the primary key** because it is the only vocabulary all four hosts speak in both directions: the Python API takes it as a kwarg, all five `CONFIG_*` lists are written in it, every host settings schema is keyed on it, and the *values* of `STATE_TO_NOTIFICATION_KEY` are themselves snake_case names that are almost all Python config keys. Inbound and outbound already meet in axis 0.

**Axis 1 is included because it is the mapping that is silently wrong today**, and Bernhard's ruling that `studio_ao_intensity` stays a manual translation is a direct confirmation: axis 1 is a datum, not a guess.

**Axis 2 is excluded from the table and used only by the checks — and the reason has been sharpened by review.** The first draft's leading argument was "nothing in the contract ever transmits an axis-2 name". True of the wire, and **it understates axis 2's role**: `_update` and `_applyOptions` both gate on `isStateKey`, never on the TypeScript interface, so **axis 2 is the runtime acceptance gate**. It is not a shadow of axis 1; it decides whether an option survives at all. That makes keeping it in the fixture *more* important than the first draft argued — it is what C1′ tests (§7.2) — and leaves the case for keeping it out of the *table* resting on the argument that was always the strongest: axis 2 is *nearly* equal to axis 1, and "nearly equal" is exactly the shape that invites a reader to treat one as the other, which is how the discarded draft declared `tab` broken.

**Axis 4 is excluded, and there are now two independent reasons.** The first is ocp_vscode's: the `ui` dispatch is not uniform — `reset_camera === "reset"` maps to `setView("iso")` *plus* a `resize()`, `analysis_tool` deactivates the current tool first, and `states` must go through a **batched** `setStates` because a per-key loop is an O(n²) repaint storm that freezes VS Code, with a comment in the source saying so. The second is the renderer's, supplied by its architect: **the setters are non-uniform in arity and identity too.**

- `setClipNormal(index, normal, value, notify)` (`viewer.ts:4213-4222`) — **one setter serves three wire keys**, distinguished by an argument, and it writes the *slider* as well, so `clip_normal_i` and `clip_slider_i` are not independent through it (`viewer.ts:1736-1739`).
- `setGrid(action: string, flag, notify)` (`viewer.ts:2384-2390`) takes an **action string plus a flag** and then reads the resulting 3-tuple back off the grid helper to write state. The wire key `grid` is a `tuple3<bool>`; the setter's signature resembles nothing of the sort. A separate `setGrids([a,b,c], notify)` also exists (`viewer.ts:2405`).

A `setter` column would be a lie for four wire keys before anyone reaches the dispatch. (`setOrtho` was checked as a tempting third example and does **not** qualify — it is a plain delegation to `switchCamera`, `viewer.ts:3165-3167`. Recorded so nobody re-derives it.) What the table carries instead is coverage facts (§5.11), which are facts, not mechanisms.

**Axis 5 is excluded, and §16.7 is now closed.** `shapes.studioOptions` is applied only from `render()`, behind `logger.warn`, with `notify=false` (`viewer.ts:1444-1452`, `viewer-state.ts:723-748`), and nothing in Python reaches it. The first draft asked whether the core should *refuse* it. **The three-cad-viewer architect's answer is no**: refusing would be the core policing a renderer-internal deprecation it does not own, and the renderer already handles it correctly. If anything changes it is that three-cad-viewer eventually deletes the branch, which is that project's call and not item 4's.

**Consequence a reviewer should test the schema against:** rows with `python` and no `wire` (`deviation`, `render_mates`, every tessellation control), rows with `wire` and no `python` (`selectedShapeIDs`, `lastPick`, `activeTool`, `holroyd`, `relative_time`, the `*0` reset-location quartet), rows with `python` and `wire` but no `option` (`states`, `reset_camera`, `explode`), and one row with an `option` and no input path at all (`normal_len`, §7.4). If any of those four shapes cannot be expressed, the schema is wrong.

---

## 4. Decision 2 — which direction is generated, and which is derived

**Amended after review.** The first draft said *"inbound is classified, not translated"*. That holds for **names** and not for **values**, and the ocp_vscode architect showed where the gap falls.

- **Outbound (Python config → renderer options) is generated.** The table generates a `{python_key: (group, option_name)}` map into Python and into JavaScript, replacing every current implementation of that rename (§11). This is the direction `toCamelCase` + `optionKeyOverrides` occupies.
- **Inbound *names* are classified, not translated — confirmed.** `combined_config` does `wspace_config.update(workspace_filter(wspace_status))` (`config.py:753`): a filter over identically-named keys, with no rename anywhere. The one key that *would* need a rename, `activeTool` → `analysis_tool`, is exactly the one the feature is broken on today, which §9.2 records under *record*. Generating an inbound name map would create a second authority for a mapping that has exactly one, and the two would eventually disagree by dropping a key silently. So inbound, the table contributes **classification**: state or event, and consumable by the merge or not.
- **Inbound *values* are decoded, and the decoding is the core's.** `status()` converts the viewer's **int** `collapse` into the `Collapse` enum through `COLLAPSE_REVERSE_MAPPING`, warning on an unknown value (`config.py:688-693`). That is viewer→python, not host→python, so §5.8's "host decodings stay host data" does not cover it and the first draft left it homeless. **Why it matters:** item 6 moves `combined_config`, and a move that loses this decoding **fails silently** — an undecoded int is truthy and flows straight into `conf["collapse"] = collapse.value`, raising `AttributeError` on an int, or passing through unnoticed if the value happens already to be an enum. §5.8 now carries a `wire_repr` sub-field for exactly this.

The two directions are tied together by an assertion rather than by a shared table: for every row with both an `option` and a `wire`, the generator asserts `STATE_TO_NOTIFICATION_KEY[state_of(option)] == wire`, reading both from the fixture. A rename on either side breaks generation. **We generate one direction, we assert the other, we own neither end of the assertion, and we decode one value domain.**

---

## 5. Decision 3 — the schema, column by column

### 5.1 `python` — the Python config key (nullable)

Primary key where it exists. `null` means the key exists in no Python API; it does not mean "unknown".

### 5.2 `option` — the renderer option field, axis 1 (nullable)

`null` means the key never reaches the renderer through an options object. Three sub-cases, distinguished by `group` and `applied_by`: never reaches the renderer at all; reaches it through code rather than options (`states`, `explode`, `reset_camera`); reaches it in the `Display` constructor only.

### 5.3 `group` — the destination object: `display` | `render` | `viewer` | `none`

A destination, not a namespace. The discarded draft invented this from VS Code setting namespaces, which is a host's filing system. The real grouping is which object the value is written into: `new Display(container, displayOptions)`, or `viewer.render(shapes, renderOptions, viewerOptions)`.

**Studio and zebra keys are both `group = viewer`, but for two different reasons, and the first draft got the zebra half wrong.**

- **Studio:** `ViewerOptions extends StudioModeOptions` (`types.ts:320`), so studio fields *are* `ViewerOptions` fields. Derivable from the `extends` clause.
- **Zebra:** `ZebraOptions` is a **standalone interface** (`types.ts:392-403`) and `ViewerOptions` does **not** extend it; the two meet only in `CombinedOptions` (`types.ts:431-436`), which types no `render()` argument. The conclusion survives on a different mechanism: the five zebra keys are `STATE_KEYS` members (`viewer-state.ts:228-232`), and `_update` filters by **state key**, not by interface — so a zebra key carried inside the `viewerOptions` argument **is applied**. There is no separate zebra argument, no `updateZebraState`, and no other application path; the only other writers are the `viewer.setZebra*` runtime setters. So **`destination(ZebraOptions) = viewer` must be recorded as an explicit datum**, because unlike `StudioModeOptions` it cannot be derived.
- Also worth a row note: zebra settings are **deferred at render time** — `render()` deliberately does not push them, and `enableZebraTool(true)` applies them on first activation (`viewer.ts:1812-1817`).

`iface` (the TypeScript interface) is carried alongside `group`, and its only consumer is C2 (§7.2): it asserts `option ∈ fields(iface)` and `destination(iface) == group`.

**A consequence item 16 must carry.** Passing a zebra key inside a `ViewerOptions`-typed object literal **works at runtime but is a TypeScript error** — the excess-property check, under three-cad-viewer's `strict` + `exactOptionalPropertyTypes`. Any generated `.d.ts` or typed wrapper that types `render()`'s third argument as `ViewerOptions` will reject exactly the keys the runtime accepts. The three-cad-viewer architect has identified this as a real defect in its own public types and will fix it in the same patch as the §7.2 export, **so the core must not generate around it** — the table records the fact and waits.

**A free third opinion on `group`, added on the architect's recommendation:** `STATE_KEYS`'s declaration carries section comments (`// Display`, `// Render`, `// Viewer`, `// Zebra`, `// Studio`, `// Runtime` — `viewer-state.ts:170-251`). They are the renderer's own filing of each key into a destination family, independent of both the interface (C2) and the key set (C1′). The extractor records them (§8.3); it is how `new_tree_behavior` was settled in one step.

### 5.4 `wire` — the notification name, axis 3 (nullable)

`null` means the viewer never reports the key. Populated from the fixture, never typed.

### 5.5 `lifetime` — `persistent` | `session` | `transient` | `derived`

`requs.md` calls this the important column and defines two values. There are four:

- `persistent` — a host stores it and it survives a restart.
- `session` — set by code (`set_defaults`, a `show()` kwarg) and lives for the process: every `clip_*`, `zebra_*`, `studio_*`, `analysis_tool`, `tab`.
- `transient` — never stored by anyone because storing it would be meaningless: `selectedShapeIDs`, `lastPick`, `activeTool`, `relative_time`.
- **`derived` — no *host-independent* input path: on at least one host the value is computed rather than set, and no host can rely on setting it.** `normal_len` is the sole member (§1, §7.4).

**`derived`'s definition was corrected at sign-off, and the correction is the more interesting half.** The second draft defined it as *"nobody sets it; something computes it per model"* — and the ocp_tessellate architect showed that is **not host-invariant**. cad-viewer-widget never tessellates: it has no `ocp_tessellate` import anywhere and takes already-tessellated shapes, so there is no `shapes["normal_len"]` and no `show.py:422-426`. What it has instead is a **full public setting path** — a synced traitlet (`cad_viewer_widget/widget.py:265`), a `show()` keyword (`__init__.py:178`) resolved as `preset("normal_len", normal_len, 0)` (`:366`), an assignment at `widget.py:930`, and membership in `viewer_args` (`utils.py:154`). So the old wording was true on the two hosts that tessellate and false on the one that does not.

**This is §5.6's trap recurring in a different column: a value that is a property of the *host* wearing the shape of a property of the *key*.** §5.6 solved it for `owner` by moving the host-varying part into `owns(key)`; `lifetime` has no equivalent, so the fix has to be in the definition. Two resolutions were offered and **I take the second**:

- *(a) `lifetime = session`, plus a note that the tessellating hosts overwrite it from the payload.* **Rejected**, because `session` means "set by code and lives for the process", and on two of the three hosts a user who sets it has the value overwritten from the payload on the very next show. Item 14 generates Settings from `lifetime`, so `session` would produce a control that silently does nothing on the hosts most users are on — a generated lie, which is the class of failure this table exists to end.
- *(b) keep `derived` and redefine it as "no host-independent input path".* **Taken.** It states a property of the key truthfully: there is no input path a host can rely on. The host-specific setter is recorded as row data rather than smuggled into the column, and the value stays available for any future computed key rather than being collapsed into `session`.

**Two obligations come with (b), and both are requirements rather than notes.** The row records cad-viewer-widget's setting path with its four citations alongside the tessellating hosts' three (`convert.py:1988`, `convert.py:2073-2074`, `show.py:422-426`). And **item 16's traitlet generation must not filter on `lifetime`** — it still has to emit a `normal_len` traitlet, because the widget's public API sets it. That is stated in §12 as a constraint on item 16, not left for whoever writes the generator to infer.

The rule for where a new option goes: `persistent` if a user would be annoyed to set it twice, `session` if it describes this `show()`, `transient` if it describes something that just happened, **`derived` if no host can rely on setting it because at least one computes it**.

### 5.6 `owner` — `document` | `surface`

The column that keeps `show.py:365-375` from growing back somewhere less visible. `document` = the value belongs to the model and the user's intent, portable across hosts. `surface` = the value is a property of the viewport the host supplies.

The relocation: the core asks the injected config object `owns(key)` for each `surface` key and refuses a Python-supplied value for the ones it claims, using a message the host supplies. A panel host claims `cad_width`, `height`, `theme`; a notebook widget claims none and the same code lets them through. **`cad_width`, `height`, `theme` are the complete surface set today — confirmed.**

**Three corrections from review, two of which change the mechanism.**

1. **The message is per key, not per host.** There are two categories today with two different messages and they are not interchangeable: `cad_width`/`height` are *viewport geometry the panel computes* (*"determined by the VSCode panel size"*), `theme` is a *host setting the user configures* (*"can only be set in VSCode config"*). The first draft's prose — "a property of the viewport the host supplies" — describes the first accurately and the second only by stretching. So the contract is `owns(key)` **plus `refusal(key)`**, per key or per reason, or the relocation flattens a distinction the current code makes deliberately.
2. **The two lists are not the same list.** The `params` filter (`show.py:345-364`) excludes all three as one set; the kwargs loop (`:365-375`) splits the same three across two branches. **A single `owns(key)` predicate reproduces the filter but not the split** — which is the mechanical reason (1) is required rather than cosmetic.
3. **The mechanism addresses one of the four host-naming sites, and claims a fifth the first draft missed.** Honestly stated: it fixes `show.py:368`. It does **not** touch `show.py:1634` (a drawability predicate in `show_all`'s exclusion chain) or `comms.py:40`/`:320` (port-discovery environment sniffing) — those are item 7's broader work. But the branch being relocated is itself guarded by `not is_jupyter_cadquery` (`show.py:366`, `:371`), which is environment-sniffed host identity (`JUPYTER_CADQUERY`, `show.py:66`), and **an injected config that answers `owns(key)` dissolves that guard naturally — a jupyter_cadquery config claims nothing.** The architect's assessment is that this is *the strongest thing §5.6 actually achieves*, and it only holds if the injection replaces the **guard** as well as the key set. Stated here as a requirement on item 7, not an aspiration.

### 5.7 `class` — `state` | `event`

Item 13's column. **The rule is replaced.** The first draft's rule was *"(a) state-backed in `ViewerState` and (b) re-applying to a different model is meaningful"*, and the three-cad-viewer architect showed it does not produce the six answers the draft attributed to it: `explode` fails (a) (there is no `explode` state key; it is emitted directly at `viewer.ts:4489`), `states` fails (a) (tree state lives in `TreeModel`/`TreeView`), and `activeTool` *passes* (a) (it **is** a state key at `viewer-state.ts:246` — what differs is the vocabulary, which (a) does not test). The draft reached three of its six answers by unstated routes, one of them the phrase *"passes (a) in spirit"* — which is exactly the move §0 exists to forbid, in the column item 13 consumes.

**The replacement rule, supplied by the architect and adopted:**

> A wire key may be accumulated into a status snapshot iff
> **(a′) round-trippable** — an inbound path exists that accepts *the same vocabulary and domain the wire emits*; and
> **(b) model-independent** — re-applying the last value to a different model is meaningful, possibly after a documented filter.

Re-derived, each conclusion now following from stated mechanism:

| wire key | (a′) | (b) | class | mechanism |
| --- | --- | --- | --- | --- |
| `selectedShapeIDs` | fails — output-only, no inbound path | fails — ids are paths into the previous model | **event** | `measure.ts:404` |
| `lastPick` | fails — output-only | fails | **event** | `viewer.ts:2225-2232` |
| `activeTool` | fails — three vocabularies, none equal: wire `ToolTypes`, state lowercase button name, Python `analysis_tool` | — | **event** | `display.ts:1840-1859`, `tools.ts:13-18` |
| `explode` | holds — boolean out, `setExplode(flag)` in, same domain | holds | **state** — without needing a state key to exist | `viewer.ts:4489` |
| `tab` | holds — `ActiveTab` out, `setActiveTab` and `viewerOptions.tab` in | holds | **state** | `viewer-state.ts:278`, `display.ts:2221` |
| `states` | holds — `setStates(Record<path,[f,e]>)` accepts exactly what `getStates()` emits | holds, **with the model-relative filter** | **state** | `viewer.ts:3367-3370` |
| `relative_time` | holds — out as `animationSliderValue / 1000`, in as `setRelativeTime(fraction)` × 1000, same 0–1 domain | **fails** | **event**, `lifetime = transient` | below |

`activeTool`'s reclassification comes with a precedent from the renderer's own history: dispatching on `state.get("activeTool")` instead of the enabled tool is recorded there as the "4c bug".

**`relative_time` closes §16.4, and its failure mode is not inert** — which is the part item 13 needs. Animation tracks are per-model, bound at `addPositionTrack` time; `clear()` disposes the animation and sets `animationMode: "none"` (`viewer.ts:1181-1185`) and `render()` calls `animation.cleanBackup()` (`:1454`), so after a new model there is nothing to position. `Animation.setRelativeTime` early-returns without a `clipAction` (`animation.ts:296-297`) — safe — **but `Viewer.setRelativeTime` writes `state.set("animationSliderValue", fraction * 1000)` unconditionally afterwards (`viewer.ts:806`)**, which fires the notification adapter and re-emits `relative_time` onto the wire, where an accumulating snapshot absorbs it again. **A stale animation position would be self-sustaining.**

**The structural gain, and the mechanism that makes it real.** The second draft claimed (a′) is *"decidable from two extracted facts — does an inbound path exist, and does its domain equal the wire's"*. The first is `applied_by ≠ none`, cleanly extracted. **The second was not extractable as the schema stood**, because a row carries one `domain` and deciding `activeTool` requires comparing two — another claim that read as a demonstration without one having been run (§0.1). The three-cad-viewer architect supplied the fix, and it needs no new column, because §5.8's `wire_repr` already *is* the two-domain field:

> **`wire_repr` absent** → the inbound and wire domains agree → (a′)'s domain half **holds**.
> **`wire_repr` present *with* a named decoder** → round-trippable after decoding → **holds**.
> **`wire_repr` present *without* a decoder** → **not round-trippable** → `class = event`.

Verified by that architect against all eight classified keys: `selectedShapeIDs` and `lastPick` fail earlier, on `applied_by = none`; **`activeTool` has `wire_repr = ToolTypes` (`tools.ts:13-18`) and no decoder anywhere — which is exactly why it is broken today** → event; `explode`, `tab` and `states` have no `wire_repr` → state; `relative_time` has none either, both sides being 0–1, so (a′) holds and it fails on (b), which is the outcome the table above already reaches; and `collapse` has `wire_repr = int→Collapse` **with** the decoder at `config.py:688-693` → round-trippable → state.

So `class` is genuinely **mostly derived** — only model-independence stays judged — and **§4's inbound-value decoding and §5.7's classification become the same fact rather than two**: a key needs a decoder exactly when its wire domain differs from its inbound domain, and a key whose domains differ *without* a decoder is by definition an event. §5.12 records the split accordingly, and §13 records the sequencing constraint that follows.

**Two row-level notes for item 13**, both from review:

- **`clip_normal_0/1/2` churn.** `ViewerState.set` compares with `===` or elementwise for arrays, and a `THREE.Vector3` never equals another, so **every** `setClipNormal` notifies even when the numbers are unchanged (`viewer-state.ts:337-343`, `:613`). An accumulating snapshot sees these three keys change constantly. Harmless for correctness, noisy for any change-driven UI.
- **`states` echoes even when told not to.** `Viewer.setState`'s `notify=false` does **not** suppress the `states` notification: `treeview.setState` calls the notification handler unconditionally (`treeview.ts:740`), so `notify` gates only the camera-level `update()`. A host that sets states quietly still receives a `states` echo.

### 5.8 `type` and `domain`

`type` ∈ {`bool`, `int`, `float`, `string`, `enum`, `color`, `vector3`, `quaternion`, `tuple3<bool>`, `dict`, `list`}. `tuple3<bool>` exists for `grid`, which the standalone splits into `grid_xy`/`grid_xz`/`grid_yz` and re-joins.

`domain` carries the value space **and its representation**, and review added three requirements to it.

- **Colours need a mandatory `repr`**, from a closed set: `css_name | hex | hex_alpha | rgb_int | rgb_float | rgba_int | rgba_float`. `type = color` alone is not sufficient because `Color` discriminates by *content*: `(1, 1, 1)` is near-black, `(1.0, 1.0, 1.0)` is white, `(0.5, 255, 1)` is silently grey with a warning and no exception. A generated Settings control (item 14) or traitlet (item 16) that emits the wrong representation produces a wrong colour **with no error a user will see** — the same class of silence §7.1 exists to end. It is not hypothetical: `default_color` is written three ways across three sources today, all the same colour — `(232, 176, 36)` (`ocp_tessellate/defaults.py:126`), `"#e8b024"` (`standalone_defaults.py:41`) — and its siblings `(238, 130, 238)`/`(186, 85, 211)` (`config.py:704-706`) against `"Violet"`/`"MediumOrchid"` (`standalone_defaults.py:42-46`).
- **`collapse` has five representations, not four.** The `Collapse` enum, the wire int, VS Code's setting string with legacy `"E"/"1"/"C"/"R"` codes, cad-viewer-widget's `COLLAPSE_MAPPING` keyed on those same legacy strings (`js/lib/widget.js:14-19`), **and ocp_tessellate's `collapse: 3`** (`defaults.py:170`), which is outside every member of `Collapse` (`{2, -1, 0, 1}`). `standalone_defaults.py:34` carries `"1"`.
- **`wire_repr` is a distinct sub-field, and it carries more weight than the second draft gave it.** It states the wire's representation where that differs from the inbound one, **and names the decoder, or records that there is none.** That third state is what makes it load-bearing: §5.7's (a′) is decided from it, so `wire_repr` present without a decoder *is* the definition of a key that cannot round-trip. Two members today: `collapse` (wire int → `Collapse`, decoder at `config.py:688-693`) and **`activeTool` (wire `ToolTypes`, state lowercase button name, Python `analysis_tool` — three vocabularies and no decoder anywhere**, `tools.ts:13-18`), which is precisely why that key is broken and why it classifies as an event without anybody judging it.

Two more from review, both affecting item 14's generated controls:

- **`0` is a distinct *off*, not the low end of a scale**, for `studioAOIntensity` (`setAOEnabled(intensity > 0)`, `studio-manager.ts:271`) and for `studioShadowIntensity`. A slider that treats these as plain ranges presents "off" as "very faint".
- **For `clipNormal0/1/2` the renderer's state representation is not the wire representation** — `Vector3Tuple` inbound (`types.ts:344-348`), `THREE.Vector3` in state (`viewer-state.ts:689-697`), array again on the wire, converted by **two independent implementations** (`viewer.ts:429-431` and `viewer-state.ts:828-830`). These three are the only such keys, and `type = vector3` should say so.

### 5.9 `default` — one default, and six ways to get it wrong

There are at least six sources and they disagree. **The table carries exactly one: the shared layer's.** For `group ∈ {display, render, viewer}` that is three-cad-viewer's `ViewerState` default; for `group = none` it is the core's own. Host defaults stay host data, and item 14 shows the shared default and the host's override side by side. Four review-driven rules make that workable:

1. **Source it from `ViewerState`'s defaults blocks (`viewer-state.ts:395-541`), never from the TSDoc.** The TSDoc is wrong in six known places — `studioEnvIntensity` (says 0.5, is 1.0), `studioShadowIntensity` (0 / 0.5), `studioShadowSoftness` (0.3 / 0.2), `studioAOIntensity` (0 / 0.5), `studioTextureMapping` (triplanar / parametric), `treeWidth` (250 / 260). "Three-cad-viewer's default" is ambiguous to an extractor author who reaches for the doc comment, so the extractor names its file and lines.
2. **ocp_tessellate is authoritative for 9 of its 16 keys, not all 16.** For the nine read from `DEFAULTS` the dict is the source; for the six shadowed by a signature default **the signature is authoritative and the dict entry must be ignored**, and for `debug` there is no dict entry at all. Otherwise the table records `helper_scale = 1` when the operative default is `1.0` — today's only skew, and the kind that widens quietly. A check asserts the two agree wherever both exist.

   **And the dict is not the only writer, which is now an explicit assumption rather than a silence.** Bernhard's ruling on §16.13 — *"it is a public API, so it could be. We should assume someone does"* — means a direct `to_ocpgroup` caller may have set any of those nine through `ocp_tessellate.set_defaults` without any host being involved. So a row whose `default` resolves through the dict records **where the default comes from**, never **that the dict is how the value is set**; and item 14 must not present an ocp_tessellate default as though the host owned it. This is written down deliberately, because "nobody calls it directly" is the kind of shortcut that reappears as a justification later, and the same reasoning keeps `apply_defaults`'s fix-versus-delete question open rather than closing it by assuming no callers.
3. **The three `None` colours need their resolved value.** `default_facecolor`/`default_thickedgecolor`/`default_vertexcolor` are `None` in the dict deliberately; the operative defaults are `"Violet"`/`"MediumOrchid"`/`"MediumOrchid"` (`convert.py:30-32`). A `default` filled from the dict literal would say `null` for all three — technically accurate and completely useless to item 14. The row carries the resolved value with both resolution steps cited.
4. **The disagreement check compares normalised colours.** As first drafted it would report `(232,176,36)` versus `"#e8b024"` as a finding, and it is not one. Compare `Color(x).web_color` plus alpha; report representation skew as a separate, lower-severity note. Without this the first run produces four or five false findings in the colour rows, and the reviewer who dismisses them is right — which is how a check earns a reputation for crying wolf.

**The framing stays: a disagreement is a finding, not a value to encode**, and the generator reports every one rather than silently picking. **But the evidence for it has been re-scoped.** The first draft cited the three-cad-viewer architect's drift memory in support of a claim about **`viewer.html`'s** default block; that memory establishes drift *within three-cad-viewer* and says nothing about `viewer.html`, a file that architect has not read. It is fair evidence for the general proposition — hand-kept second copies of defaults drift in this ecosystem — and it is cited that way now. `viewer.html`-specific evidence is the ocp_vscode architect's to supply.

### 5.10 `status` — does the viewer report this key back

Derived, never typed: `status = (wire is not null)`. Computed from the fixture; the generator refuses a hand-written value that disagrees.

### 5.11 `applied_by`, `ui`, `live_settable`

`applied_by` ∈ {`options`, `code`, `display-ctor`, `none`} — how the value reaches the renderer.

**`ui` is split into two extracted facts, which is the review's fix for the "nineteen keys" error:**

- **`ui`** — does the live-set dispatch handle this key.
- **`live_settable`** — is this key a `set_viewer_config` parameter.

**Item 10's checklist is then the predicate `live_settable ∧ ¬ui`, which evaluates to the eleven `studio_*` keys and needs no hand-maintained count.** The first draft asserted nineteen keys that were "settable through `set_viewer_config` and dropped"; nine of them are not `set_viewer_config` parameters at all and therefore cannot be sent, let alone dropped. Keys that are `¬live_settable ∧ ¬ui` get a row saying **show-time only, by construction** — a fact worth having, and one the first draft was mis-recording as a defect.

### 5.12 `evidence`, `default_source`, and the extracted/judged split

**Every row carries, per judged column, the `file:line` that settles it, and the generator refuses a row whose judged columns have no evidence.** This is the plan's central anti-inference mechanism and review left it intact — the ocp_tessellate architect called it *"mechanisms rather than intentions"*. Three amendments:

- **Judged columns are now `lifetime`, `owner`, and (b)-of-`class`.** `class` moves mostly to derived (§5.7): (a′) is decided from `applied_by` and `wire_repr` (§5.7's three-way rule), so only model-independence is judged. `type` stays judged for the colour representation.
- **A claim made in prose about a row carries the instance that exhibits it.** New, and it closes a gap the sign-off round found: the evidence discipline above attaches to **columns**, so a claim written in the surrounding text — "these two checks disagree", "this is derivable", "this key is dead" — is checked by nothing. Three of this plan's own errors were of that shape (§0.1). So a prose claim about the table's mechanics names its instance: the pair that disagrees, the two facts it derives from, or the consumer whose absence makes a key dead. **And where the claim is that something is unreachable, the enumeration has to be of *consumers*, not of one consumer** — the `viewer.html:100` inversion (§8.2) and the earlier `_splash` error were both "decided reachability from one consumer without enumerating the others", which the ocp_vscode architect notes is now the second instance in two rounds.
- **`default` gains a mandatory `default_source`.** It was listed as extracted, and for ten rows the extraction has to *choose* between two sources (dict versus signature) or run a two-step resolution through `_default_or` and the module constants. That is a judgement encoded in the extractor rather than in the row — precisely what this rule exists to prevent. The extractor emits `default_source` alongside `default` so the choice is visible and reviewable.
- **A count is judged, not extracted, unless the enumeration it came from is carried beside it.** §0.1's rule, and it applies to the plan as much as to the table.

### 5.13 `legacy` — transitional, and deleted at the end

Membership in the five `CONFIG_*` lists, so §8.1's equivalence tests can reconstruct them exactly; deleted when the last list is retired (§11).

The objection stated plainly: *a column that encodes today's accidents makes the table the sixth list plus five extra columns.* The answer is that the five lists **are not derivable from semantics** — `reset_camera` is simultaneously a CONTROL key, a persistent host setting and a `CONFIG_SET_KEYS` member, the only key in all three roles; `position`/`quaternion`/`target` are in `CONFIG_SET_KEYS` and not in `CONFIG_KEYS`, so the value is rejected from `DEFAULTS` with a printed warning **and applied anyway**. (Reachability caveat, added on review: `set_defaults` has no `position` parameter, so that path is reachable only through `reset_defaults()` at `config.py:774-781`, which passes the `CONFIG_SET_KEYS` subset. A reader who tries `set_defaults(position=[…])` gets a `TypeError` and would conclude the plan is wrong.) Any predicate reproducing those from `group`/`lifetime`/`owner` would encode the accident in a worse place. So it is quarantined in one column with a scheduled death.

**The ocp_tessellate architect found the sharp edge of this argument and it is folded into §10.3: the first draft quarantined the legacy lists and then used one of them as the work-breakdown structure.**

---

## 6. Decision 4 — where the source of truth lives, and what is generated

**The repository** is `~/Development/CAD/ocp-viewer-core`, whose committed skeleton (`8d45415`) already declares `ocp_viewer_core = ["config_keys.toml"]` as package data and already names that file in its README as "the source both languages generate from". Item 4 is the first content in a repository built to receive it. Nothing is published: Python is consumed as an editable install, JavaScript via `yarn pack`, so the generated artefacts must work under an editable install and the JavaScript half must need no build step.

**The source format** is `ocp_viewer_core/config_keys.toml`. TOML because every row needs prose — `evidence` is a sentence with a citation. **It is a build-time input, never read at runtime**: `requires-python = ">=3.10"` while `tomllib` is 3.11+, the JavaScript half cannot read it at all, and parsing a data file at import time fights the import-free-`__init__` rule.

**The generated artefacts, both committed:** `ocp_viewer_core/config_keys.py` (plain literals, no imports beyond `typing`, importable without OCP and without a host) and `js/src/config-keys.js` (a frozen object plus accessors, no dependencies, ESM). A test asserts regeneration produces no diff. Generating at build time was rejected: neither consumption path in this phase reliably runs a build step, and a stale generated file in an editable checkout is the class of failure this item exists to end.

**The generator** is `tools/generate_config_keys.py` plus `tools/extract/*`, one extractor per source. It is a pure function of the TOML plus the fixtures, runs the checks of §7 first, and emits nothing if any fails. Every extractor records the source path and the commit it read.

---

## 7. Decision 5 — how a wrong or missing row fails loudly

### 7.1 The silences being replaced

1. **A key whose renderer option name is not the mechanical transform is discarded with no diagnostic of any kind.** The first draft said "a browser-console warning nobody reads". **It is worse, and the correction strengthens the case for item 4.** There are two option-filter paths: the **constructor** path warns (`_applyOptions`, `viewer-state.ts:583-586`), and the **`render()`** path — `setRenderDefaults`/`setViewerDefaults` → `updateRenderState`/`updateViewerState`/`updateStudioState` → `_update` — has **no `logger` call on that branch at all** (`viewer-state.ts:628-630`). `studio_ao_intensity` is a *viewer* option and travels the silent path. **Today the defect is undetectable at runtime by any means.** (And where the warning does fire it is mostly noise: `canvas` and `gl` are legitimate `DisplayOptions` fields that are not state keys, so a normal boot warns twice.)
2. A key a host stores but no list mentions is never applied, and nothing says so.
3. A key filtered out of the status merge silently stops surviving a `show()`.
4. A key in `CONFIG_SET_KEYS` and not in `CONFIG_KEYS` is rejected from `DEFAULTS` with a printed warning **and applied anyway**.
5. A `set_viewer_config` for a key with no `ui` branch posts a message the browser drops — **true of the eleven `studio_*` keys**, and of nothing else (§5.11).

### 7.2 The verification fixture, and the checks

`tests/fixtures/three_cad_viewer.json`, carrying: `STATE_KEYS` (76) **and its section comments**; `STATE_TO_NOTIFICATION_KEY` (**47**); the field lists of `DisplayOptions`, `RenderOptions`, `ViewerOptions`, `ZebraOptions`, `StudioModeOptions`; the six defaults blocks; the option→state map where the two differ; and the `version` string it came from.

**The 47 is settled.** The three-cad-viewer architect re-derived it scoped to the declaration (`awk` from `const STATE_TO_NOTIFICATION_KEY` to the closing brace, counting `: "`), corrected its memory, and enumerated the 29 absent keys there rather than summarising them. The fixture is built on 47.

**Three checks, and C1 has been replaced.** The first draft's C1 (`option ∈ STATE_KEYS ∪ fields(iface)`) is **entirely subsumed by C2** — whenever C2 holds, C1's union holds automatically, so C1 cannot fail unless C2 also fails. It was sold as an independent second opinion and was not one, and the draft credited it with catching `studio_ao_intensity` when C2 is what catches it.

- **C1′** — for every row with a non-null `option` and `applied_by = options`: `option ∈ STATE_KEYS`, unless the row is on the documented **strip-list**. This is the check that catches `studio_ao_intensity`, and it earns the credit because **it tests the runtime acceptance path**: `_update` and `_applyOptions` gate on `isStateKey`, not on the TypeScript interface (§7.1).
- **C2** — `option ∈ fields(iface)` ∧ `destination(iface) == group`. The compile-time opinion.
- **C3** — for every row with both `option` and `wire`: `STATE_TO_NOTIFICATION_KEY[state_of(option)] == wire`.

**C1′ and C2 are independent because each catches a class of error invisible to the other — but the second draft overstated how, and the corrected statement is a better argument than the one it replaces.** The claim was that they *"genuinely disagree in both directions"*, offering `tab` and the zebra keys. Only `tab` is a disagreement; the zebra keys pass **both** once `iface = ZebraOptions` is recorded, which is agreement contingent on a datum. The three-cad-viewer architect's own wording is imprecise in the same way and it has said so, calling it the same pattern as F7 — a phrase that reads as a demonstration and is not one (§0.1). The honest statement:

> C1′ tests the runtime acceptance gate (`isStateKey`); C2 tests the compile-time interface. **On today's correct data they disagree in one direction — `tab` — and the second direction is reachable only by a mis-filed `iface`:** a zebra key recorded as `iface = ViewerOptions` **passes C1′** (it is a state key) and **fails C2** (`zebraCount ∉ fields(ViewerOptions)`). That mis-filing is the *natural* error, because ocp_vscode carries the zebra keys in `viewerOptionKeys`, and catching it is precisely what C2 is for.

- `tab` is a `ViewerOptions` field (`types.ts:388`) and **not** a `STATE_KEYS` member — passes C2, fails C1′, and is the one legitimate exception, because `updateViewerState` strips it before `_update` sees it (`viewer-state.ts:673`) and `render()` applies it separately (`viewer.ts:1797-1806`). **The strip-list is data, with that citation, and has exactly one member today.**
- The five zebra keys are `STATE_KEYS` members and **not** `ViewerOptions` fields; with `iface = ZebraOptions` and `destination = viewer` recorded (§5.3) they pass both checks. They are the *reason C2 exists*, not an example of it disagreeing.

**The version trap.** `STATE_KEYS` and `STATE_TO_NOTIFICATION_KEY` are module-private (`viewer-state.ts` exports only `ViewerState` and three types, `:938-939`), so the fixture is a snapshot. Two mechanisms, and **review established they are complementary rather than alternatives**:

- The core's own test suite **re-extracts against the installed three-cad-viewer and asserts the fixture is unchanged**, so a renamed or removed state key breaks the core's tests the moment a developer installs it.
- The fixture records its version; a check asserts that version satisfies the peer floor (`>=5.0.3,<5.1.0`), deliberately **not** equality, because "own your patch" allows a host above the floor.

**The export is committed, not merely accepted, and it ships as three-cad-viewer 5.0.4.** The architect has undertaken to ship it when item 4 needs it, on the grounds that C1′ is a *runtime-gate* check, so running it against the installed renderer is a correctness improvement rather than a convenience. Two additions from its sign-off complete the record:

- **`STATE_TO_NOTIFICATION_KEY` goes in the same export.** "The state-key vocabulary" was ambiguous, and **C3 reads that map**, so it has to be exported too. There is an asymmetry worth naming: the **wire names are already a de-facto public contract** — every host depends on them — so exporting the map *formalises something already true*, whereas exporting `STATE_KEYS` **newly promotes an internal to a contract**.
- **The cost of that promotion, accepted deliberately and recorded here because it is permanent.** After 5.0.4, **renaming a `ViewerState` key is a breaking change by contract**, not merely an accident that happens to break a snapshot. Today three-cad-viewer is free to rename internal state keys precisely because they are not the wire vocabulary. The architect accepts the constraint as the price of the checks running against the installed renderer, and will put it in three-cad-viewer's 5.0.4 release notes rather than let it be discovered later. **Item 4 is the reason that freedom is given up, so item 4 is where it is written down.**

Three amendments to the first draft's framing:

- **The cost is two lines per symbol, not one** — module export, then `index.ts` re-export.
- **The option-interface half ships only in an exhaustive form.** TypeScript interfaces are erased at runtime, so a hand-written array would be a second copy inside three-cad-viewer — the very drift the proposal removes, relocated. `as const satisfies readonly (keyof ViewerOptions)[]` catches a typo but **not an omission**, so a newly-added field would silently fail to appear. The form that ships is `const VIEWER_OPTION_FIELDS: Record<keyof ViewerOptions, true> = {…}` with `Object.keys` exported — checked in both directions, so the compiler maintains the mirror. Five such objects. If that form is refused, the architect would rather the core keep extracting from source than ship an unenforced list.
- **The fixture stays regardless, and the first draft was wrong to call the export "strictly better".** The export makes the checks *current*; only the re-extraction diff makes a rename *alert* somebody. With `STATE_KEYS` exported, C1′ would silently re-baseline against a renamed key and pass.

The same patch will fix the `ViewerOptions`/`ZebraOptions` typing gap of §5.3, so the exported field lists and the accepted runtime keys agree.

### 7.3 Where a runtime guard is deliberately not added

Rejected: making the generated applier refuse an unknown option at runtime. The generation-time check makes a wrong row unshippable; a runtime refusal would turn a cosmetic mis-map into a failed `show()` in a user's hands. The discipline is *make it unrepresentable*, not *check it twice*. The one runtime assertion that stays is the peer-floor check item 11 already schedules for the vendored copy.

### 7.4 A missing row, an unreachable row, and the two categories that are neither

A key present in a host's settings schema, in one of the five lists, or in the widget's whitelists and absent from the table fails §8.3's coverage. A row reachable from nowhere fails the **reachability** check: every row must have at least one of a Python API path, a host settings path, or a wire path.

Review produced two cases the first draft's binary could not express, and each gets a category rather than a stretched column:

- **Out of domain (§8.4)** — the key exists and is deliberately not this table's business. `zscale_tool`, by Bernhard's ruling.
- **Protocol, not configuration (§8.5)** — the field crosses the wire but is not a config key. `_splash`, on the ocp_vscode architect's recommendation.

**And one row that reachability nearly refused: `normal_len`.** It has no Python input path, no host settings entry and no notification — `show.py:422-426` overwrites whatever a caller supplied with a value the tessellator computed. The ocp_tessellate architect offered two resolutions and preferred excluding it as not a config key, the same treatment `_debugStarted` gets. **I am taking the other option, and the reason is one that review did not have in front of it:** `normal_len` *is* in `renderOptionKeys` in `viewer.html`, in build123d Studio's `RENDER_KEYS`, and in cad-viewer-widget's `getRenderOptions`, and `normalLen` is a `RenderOptions` field and a `STATE_KEYS` member — so it has a **live outbound axis-1 path in all three implementations**. Excluding it would make the generated outbound map non-equivalent to today's and break §8.2. So it keeps a row: `option = normalLen`, `group = render`, `applied_by = options`, `wire = null`, **`lifetime = derived`**, `default` recorded as *computed per model, `0` when `render_normals` is false*, with `convert.py:1988`, `convert.py:2073-2074` and `show.py:422-426` as evidence and a note that the config value is overwritten unconditionally. §16.10 carries this as a decision the architect may still push back on.

`studio_ao_intensity` remains the case that proves the loudness rule, and it now demonstrates the whole cycle rather than half of it: with the row asserting `option = "studioAOIntensity"` and ocp_vscode 4.x producing `studioAoIntensity`, §8.2 **fails** — that failure *is* the bug report — and the same commit fixes 4.x, at which point the test passes with no exception recorded (§9.1a). The rule the sequence establishes: **a wrong row and a wrong implementation are indistinguishable to the check, which is what makes the check worth having; what distinguishes them is a second implementation to compare against** (§9.2).

---

## 8. Decision 6 — verification against today's behaviour

### 8.1 List equivalence

Reconstruct each of the five lists from the `legacy` column and assert **set** equality against a committed snapshot. **Confirmed exactly by the ocp_vscode architect**, by AST at `934e1fa`: `CONFIG_UI_KEYS` 38/38, `CONFIG_WORKSPACE_KEYS` **65 literal / 61 distinct** with four duplicates (`ambient_intensity`, `direct_intensity`, `metalness`, `roughness`), `CONFIG_CONTROL_KEYS` 10/10, `CONFIG_KEYS` **76 literal / 72 distinct** with the same four, `CONFIG_SET_KEYS` 39/39, union **75 distinct**. The duplication arises because `CONFIG_WORKSPACE_KEYS = CONFIG_UI_KEYS + [...]` and the appended render-settings block re-lists four keys already present.

**Set equality is right for a second reason the first draft did not have:** `CONFIG_KEYS`'s *order* is an artefact of concatenation order and no consumer observes it — every use is an `in` test (`config.py:644`, `:656`, `:667`, `:672`, `:777`). A sequence-equality test would fail on the duplicates *and* would be asserting something no code depends on.

### 8.2 Outbound map equivalence

Reimplement `toCamelCase` in the test, apply it plus `optionKeyOverrides` to the snapshotted `renderOptionKeys` and `viewerOptionKeys`, and assert the result equals the generated map. **Inputs confirmed exact** by the ocp_vscode architect: 7, 43 and 3 respectively; `resources/viewer.html` and the template copy byte-identical; and the `studio_4k_env_maps → studio4kEnvMaps` override is indeed redundant, because `_4` matches `_([a-z0-9])` and `"4".toUpperCase()` is `"4"`.

**The third implementation is a second opinion, never an authority — and review has now proved it both ways.** `cad-viewer-widget/js/lib/widget.js:383-424` carries an explicit 44-entry `optionsMapping` with no `toCamelCase` anywhere: the shape item 4 proposes, already built. It differs from ocp_vscode's derived map in exactly two places, and Bernhard settled them one each way:

- **`studio_ao_intensity: "studioAOIntensity"` — present in the widget, missing in ocp_vscode, and the widget is right.**
- **`new_tree_behavior` — filed as a viewer option in the widget, a display option in ocp_vscode, and ocp_vscode is right.** The three-cad-viewer architect traced it end to end and confirmed the renderer agrees: the key lives in `DisplayDefaults` (`viewer-state.ts:39`), `DISPLAY_DEFAULTS` (`:439`), the **Display** block of `STATE_KEYS` (`:180`), `DisplayOptions.newTreeBehavior` (`types.ts:276`) and the Display block of `ViewerStateShape` (`types.ts:454`); it is not in `ViewerOptions`; it has no wire name. Its single consumer is `state.get("newTreeBehavior")` (`viewer.ts:1343`, `:3446`) feeding `TreeView`'s `linkIcons` (`treeview.ts:98`, `:109`, `:125`; `tree-model.ts:78`), which is exactly the "default versus legacy tree behaviour" Bernhard described.

**The widget's placement is non-canonical, not broken, and must not be reported to cad-viewer-widget as a bug.** Both paths work and are exactly equivalent: on the canonical path `Display` itself never reads `options.newTreeBehavior` — there is no occurrence in `display.ts` — so even there the key is purely a `ViewerState` seed consumed later by `buildInitialGroup`; on the widget's path `updateViewerState`'s destructure strips only `tab`, the three clip normals and the camera triple, so the key falls into `...rest` → `_update` → `isStateKey` true → assigned (`viewer-state.ts:673-681`, `:628-643`), and it lands in time (`setViewerDefaults` at `viewer.ts:1442`, `buildInitialGroup` at `:1464`). Nothing subscribes to the key, and both paths skip `undefined`/`null` identically. **The general reason three placements coexisted unnoticed is §7.1's: `_update` gates on `isStateKey`, never on the interface, so any state key routed through the "wrong" options object still lands.** So the item 16 correction is **cosmetic** — it aligns the filing with the interface and with Bernhard's ruling and changes no observable behaviour. Table values: `group = display`, `iface = DisplayOptions`, `wire = null`, `status = false`.

**On the third copy: my `[M]` was inverted, and the ocp_vscode architect has settled it. `viewer.html:100` is LIVE; `viewer.html:79` is the dead duplicate.**

I reasoned that `render()`'s loop iterates `viewerOptionKeys` and looks up `viewerDefaultOptions[optionKey]` by the produced camelCase name, that `new_tree_behavior` is in neither `viewerOptionKeys` nor `renderOptionKeys`, and therefore that the `viewerDefaultOptions` entry is dead. **Every premise is true and the conclusion does not follow**, because `viewerDefaultOptions` has a **second reader that `render()`'s loop knows nothing about**:

```
viewer.html:293-297   const newTreeBehavior = preset(_config, "new_tree_behavior",
                                                    viewerDefaultOptions.newTreeBehavior);  // reads :100
viewer.html:307       newTreeBehavior: newTreeBehavior,          // into the returned displayOptions
viewer.html:322/326/344   getDisplayOptions(...) -> new Display(...) -> new Viewer(display, displayOptions, nc, null)
```

So **`viewer.html:100` is the operative fallback default** for `newTreeBehavior`, reaching the renderer as a `DisplayOptions` field — consistent with this section's own finding that the key belongs to `DisplayOptions`. **The dead entry is `viewer.html:79`, `displayDefaultOptions.newTreeBehavior`:** the only two reads of `newTreeBehavior` in the file are `:296` (out of `viewerDefaultOptions`) and `:307` (the local). Every *other* member of `displayDefaultOptions` is read in `getDisplayOptions`. `newTreeBehavior` is the single member that reaches into the other object.

So the oddity is real and is the mirror image of what the second draft recorded: **a display option whose default is read out of the viewer defaults object, with an unread duplicate sitting in the display defaults where you would expect the live one.**

**Why this had to be fixed before the row was written, in the architect's words: a future tidy-up that trusted the plan would delete line 100.** That is behaviourally harmless *today* — `preset` would yield `undefined`, `_applyOptions` skips `undefined`, and the renderer's `DISPLAY_DEFAULTS.newTreeBehavior` is also `true` — **but only by the coincidence of two defaults agreeing**, and it would silently transfer default ownership from ocp_vscode to the renderer, which is exactly the class of thing §5.9 exists to make visible. **Table values: `default_source = three-cad-viewer DISPLAY_DEFAULTS` per §5.9 rule 1, with a row note recording that ocp_vscode's copy lives at `viewer.html:100` and that `viewer.html:79` is an unread duplicate.**

**And the shape of my error is the point, not the line number.** I decided reachability from one consumer without enumerating the others. The ocp_vscode architect notes it made the same error on `_splash` in the previous round — **the second instance in two rounds** — which is why §5.12 now requires that a prose claim of unreachability enumerate *consumers*, plural.

### 8.3 Coverage

Every key in each source must appear as a row, be listed out-of-domain (§8.4), or be in the protocol inventory (§8.5), with the source recorded:

- the five `CONFIG_*` lists and `DEFAULTS`;
- VS Code's 51 `contributes.configuration` properties;
- `standalone_defaults.DEFAULTS`;
- cad-viewer-widget's `display_args` (7) and `viewer_args` (`utils.py:125-208`), its synced traitlets, and `optionsMapping`;
- build123d Studio's `RENDER_KEYS`, `VIEWER_KEYS`, `KEY_OVERRIDES` and `displayOptions`;
- three-cad-viewer's `STATE_KEYS` **and its section comments** (§5.3);
- **`ocp_tessellate.defaults.DEFAULTS`, added on review** — 51 keys, one AST walk of one dict literal, no import and no OCP. It is not a `default` source for any row (§5.9), but running its keys against the table is **how the four fossils get found rather than argued about**, and recording it as a source means a future ocp_tessellate release that adds a key is noticed by the core's tests.

### 8.4 Out of domain, which is not the same as missing

**`zscale_tool` is refused — no row.** It is a GDS (chip layout) tool, not a CAD tool, which is why ocp_vscode does not have it. The coverage extractor walks build123d Studio's option lists, so it will be found there; silently skipping unknown keys would destroy the assertion §8.3 exists to make. So the extractor carries an explicit `out_of_domain` list, one entry per key with a reason and a citation:

```
out_of_domain = [
  # A GDS (chip layout) tool, not a CAD tool. Deliberately absent from
  # ocp_vscode and out of scope for the CAD config table.
  # build123d-studio/src/viewer/viewer.js:138
  "zscale_tool",
]
```

Coverage then has four outcomes: **covered**, **out of domain**, **protocol** (§8.5), **missing** (fails). Adding to either list is a reviewed decision with a written reason.

### 8.5 The protocol / handshake inventory — new, and `_splash` is its first member

The ocp_vscode architect tested the schema against `_splash` and **it failed**: five columns have no member for it. `applied_by` — it is read by host-glue JavaScript in `viewer.html`, which is neither `options`, nor `code` (which implies a renderer setter), nor `display-ctor`, nor `none` (it *is* applied, twice). `wire` — not notified back, but it *is* transmitted outbound in the model config, and there is no outbound-payload column. `owner` — neither `document` nor `surface`; the host *process* owns it. `lifetime` — host-set and flips once, so none of the four. `class` — never in a status snapshot, so neither.

**And no column expresses the property that makes it dangerous to relocate: the value the core forwards is not the value the core received.**

Two ways out were offered — extend four columns, or refuse it a row and inventory it separately. **I take the second, as recommended**, because forcing it into the table costs four column extensions to model one key.

So: a short, explicitly separate **protocol/handshake inventory** beside the table, for fields that cross the wire and are not configuration. It is not generated into either language; it is a document with the same evidence discipline.

**`_splash`'s entry, from Bernhard's account, which is authoritative over both earlier drafts of this plan and the ocp_vscode architect's memory.** His words, and they are narrower than either:

> When the viewer is opened the first time, `_splash` is set to true in the object and returned by the config call, hence `workspace_config()` returns `_splash == True` when the logo is shown. Based on this, `_tessellate` guards from `reset_camera` being KEEP. Afterwards it is set to False in Python, forwarded to the extension where it sets the viewer property, and from there on `_splash` is False. So it is only needed to avoid `reset_camera=KEEP` while the logo is shown.

Two things follow, and they change how the inventory's first entry reads:

- **The flag's entire purpose is one guard** — stopping a `reset_camera=KEEP` from inheriting the splash logo's camera. It is not a general handshake, and the previous draft's framing of it as one was too broad. The inventory entry is therefore *narrow and specific*, which is the more useful thing for items 5–7 to preserve: not "a host session flag with three consumers" but "the mechanism that stops the first real `show()` adopting the logo's camera".
- **The field is inert; the *event* is load-bearing.** Both earlier drafts got this half wrong in opposite directions — the first treated the outbound `False` as transmitted and never acted on, the second as "how the host learns to flip its own property". **Neither host reads it** (§2): both flip unconditionally on the arrival of a model message, and `viewer.html` reads a value that is always `False`. So what must survive a relocation is the **delivery of the first model message to the host**, not the presence of a field. That is a sharper requirement and a harder one: a `Comms` redesign that batches model sends, or that routes model data past the host straight to the frontend, would preserve every field and still break the flag.

The architect's measurement supplies the citations and is consistent with the account: set at `controller.ts:49` / `standalone.py:227`, injected into the `config` reply at `controller.ts:126` / `standalone.py:379`, reaching Python through `workspace_config()` → `combined_config()`, with `params` inheriting it because `show.py:345-364` builds `params` from `conf.items()` excluding only the camera triple and the surface keys; read in the `True` state at `config.py:750`, `show.py:242-256` and `show.py:376-381`; overwritten to `False` at `show.py:383` on the last line before the payload is built.

**The outbound half is confirmed end to end by Bernhard, and the ordering inside `_tessellate` is the load-bearing part.** `controller.ts:49` sets `this.splash = true` at start, `:126` puts it into the `config` reply, `workspace_config` resolves that — and **in `_tessellate` the `workspace_config` call comes first, and the `_splash` test reads *that call's* value.** The ocp_vscode architect has pinned the mechanism: `_tessellate`'s first act is `conf = combined_config(...)` (`show.py:241`), whose first act is `workspace_config(...)` (`config.py:742`, ahead of `status` at `:743`), and the guard on the very next line (`show.py:242`) tests **that read's** value. **So the guard is correct only because the settings read and the test sit inside one `_tessellate`.**

#### 8.5a The migration constraint that falls out, and it is item 6's

**`_splash` is `True` for the first `show()` and `False` for every one after.** Combine that with the ordering above and one concrete failure mode appears, in the item this plan feeds:

> A `Session` that caches the settings read **for its own lifetime** rather than **for the duration of one `show()`** replays a stale `_splash: True` and forces `Camera.RESET` on every subsequent show — silently, with no error, presenting to a user as *"the camera keeps resetting"*.

**No decision changes.** `requs.md`'s item 6 already specifies a per-`show()` cache and §1 already restates it. What changes is that the constraint stops resting on general prudence and **acquires a proof case with a measurement behind it**.

**The window is provably safe, which is the part worth writing down.** Measured by the ocp_vscode architect over one `show()`: the six `config` reads happen at steps 1, 2, 3, 5, 6 and 7, and **the model send is step 8**. The only event that flips `_splash` is the host handling that model message. **So `_splash` cannot change during a `show()` — it changes exactly once, at the last step of the first one.** Hence:

> **Requirement.** A `Session` may cache `workspace_config` for the duration of **one** `show()` and no longer. The value is invariant within a show because the only transition is triggered by the model send, which is the show's final step; a cache spanning that event replays a stale `_splash: True`.

**And the failure a longer cache produces is exactly the one nobody would diagnose.** A `Session`-lifetime cache replays `True` for ever, so `show.py:242` forces `Camera.RESET` **and** `show.py:378` discards every explicit `reset_camera=`, on every show, permanently. No exception, no warning, no log line; the symptom is *"the camera keeps resetting and `reset_camera=Camera.KEEP` is ignored"*, with nothing in any traceback pointing at a cache. **Item 9's kit gains the matching assertion: two successive shows must produce two settings reads, not one** — which sits beside the per-show fetch-count assertion `requs.md` already asks item 9 for.

**The same failure is reachable by a second route that a naive contract would miss, and it is now confirmed from source rather than relayed.** Standalone's flip sits after `if self.javascript_client is None: … continue` (`standalone.py:399-404`), so with no browser attached the model is dropped and the flag never clears — a stale `True` reached **with no cache at all**, producing the identical forced-`RESET` symptom. It is **defensible rather than simply a bug** (§8.5 clause iii). The two have to be stated together, because **a contract phrased only as "do not cache the settings read across shows" would not catch the standalone's version** — there is nothing there to un-cache. The invariant covering both is about the *value*, not the *cache*: **`_splash` is re-resolved from the host on every `show()`, and a `True` that was not produced by this show's `workspace_config` call is a bug wherever it came from.**

**The inbound half is now settled too, and it closes the `[?]`: neither host reads the payload; both flip on arrival** (§2). Two further facts fall out that the inventory needs beyond the field/event distinction itself:

- **Neither logo path goes through the `D:` branch**, which is *why* the guard survives the logo being drawn: VS Code's `controller.logo()` posts straight to the webview, and standalone's `standaloneViewer()` builds the logo in the browser (`standalone.py:72-78`) so the server never sees it. **The flag therefore flips on the first model originating from the Python client**, which is the precise edge and the thing a relocation must preserve.
- **A per-host divergence, and it is defensible rather than simply a bug.** Standalone's flip sits *after* `if self.javascript_client is None: … continue` (`standalone.py:399-404`), so with no browser attached the model is dropped and **the flag never clears** — a standalone viewer that has never had a browser connected keeps forcing `Camera.RESET` on every `show()`. VS Code's flip is unconditional, after a fire-and-forget `postMessage` that carries no delivery guarantee either. So **the two shipped hosts have picked different points on one edge — *delivery attempt* versus *successful routing* — and neither is obviously wrong**: standalone can argue no model was displayed, so the splash state genuinely has not changed.

**So the inventory entry is normative in three clauses rather than descriptive, and it names the edge instead of the payload so that it survives a `Comms` redesign:**

> **Normative.** (i) The host clears its splash flag when it handles the **first model message originating from the Python client**, and not when it injects its own splash content; the flag is reported as `_splash` in every `config` reply until then. (ii) The settings read that the guard tests must be taken **within the same `show()` as the guard** — no cross-`show()` cache (§8.5a). (iii) **The contract must state whether the flag clears on *delivery attempt* or on *successful routing to a frontend***, because the two shipped hosts differ and both stale states produce the same silent forced-`Camera.RESET`.
>
> The `_splash` field inside the model payload is currently inert — no host reads it — and a host may implement "read the payload" instead **only while `show.py:383` keeps that value constant**; the two mechanisms are equivalent today and would diverge the moment any producer emitted a model with `_splash: true`.

**Clause (iii) is a decision item 7 must take, not a fact item 4 records.** It is listed here because this is the only document in which the divergence is written down.

One observable defect goes in the inventory too, replacing the first draft's open question: **a `set_defaults(...)` issued before the first `show()` restyles the splash logo**, because `viewer.html:766` never returns early.

---

## 9. Decision 7 — dead, host-owned and disputed keys

### 9.1 `studio_ao_intensity`

**Bernhard's decision: the bug is fixed as part of this migration, and the fix is an explicit manual translation** — joining `default_edgecolor→edgeColor`, `clip_planes→clipPlaneHelpers` and `studio_4k_env_maps→studio4kEnvMaps`. **Nothing about the derivation rule changes**, which forecloses the tempting alternative: teaching `toCamelCase` about acronyms would "fix" this key, quietly mis-map the next, and keep axis 1 a guess.

Three distinct facts, and only the first is a defect item 4 can own.

1. **No `optionKeyOverrides` entry**, so `toCamelCase` produces `studioAoIntensity`, the runtime `isStateKey` gate drops it, and the show-time path never sets the value. **A *mapping* defect** — item 4's business, and the correct value is not a guess, because cad-viewer-widget's independent map already says `studioAOIntensity`. **Review sharpened the severity: the drop is completely silent** (§7.1), because a viewer option travels `_update`, which has no `logger` call at all. Today the defect is undetectable at runtime by any means.
2. **`viewerDefaultOptions.studioAOIntensity = 0.5` at `viewer.html:109` is never read**, because the loop looks the default up by the produced name. A consequence of (1) that disappears with it, and **confirmed to have no observable effect**: it matches `STUDIO_MODE_DEFAULTS.studioAOIntensity = 0.5` (`viewer-state.ts:528`) exactly.
3. **No `ui` dispatch branch**, so `set_viewer_config(studio_ao_intensity=…)` posts a message the browser drops. **A separate defect, shared with the other ten `studio_*` keys and with nothing else** (§5.11 — the first draft said nineteen keys and it is eleven). Fixing it for one and not the other ten would be arbitrary.

**So the fix lands as follows.** (1) is fixed in item 4, in one commit, in **three** places: the table row (`option = "studioAOIntensity"`), build123d Studio's `src/viewer/viewer.js` `KEY_OVERRIDES`, and — **decided by Bernhard, §9.1a** — ocp_vscode 4.x's `resources/viewer.html` `optionKeyOverrides` plus its `make dist` copy. One line each. cad-viewer-widget needs nothing. (3) is **not** fixed here: it is recorded as `live_settable ∧ ¬ui` on eleven rows and handed to **item 10**, which extracts the dispatch and is the only place "extend it, or declare these keys show-time-only by design" can be decided once for the family.

**What the fix does and does not buy, now mechanically established by the three-cad-viewer architect.** `studioAOIntensity` is consumed only by the studio composer, which exists only in studio mode: on entry, `const aoIntensity = state.get("studioAOIntensity"); this._composer.setAOIntensity(aoIntensity); this._composer.setAOEnabled(aoIntensity > 0);` (`studio-manager.ts:268-271`), writing `_n8aoPass.configuration.intensity` (`studio-composer.ts:284-285`) over a hardcoded construction default. **So setting it at `render()` time lands it in state and it takes effect the first time studio mode is entered — no re-`show()` needed for the value to apply.** Live changes go through a subscription that early-returns while studio is inactive (`studio-manager.ts:470-472`), but the value survives in state and the entry path picks it up. And `0` **disables the pass entirely**, so it is a distinct off rather than the low end of a scale (§5.8). Consistency note that the first draft made and review asked to keep: after the fix, `set_viewer_config(studio_ao_intensity=…)` will still do nothing, exactly like the other ten studio keys, because (3) is untouched.

**How Bernhard should test it, from the architect:** enter studio mode, and use a value **far from 0.5** — try `0` and `2.0`. At 0.5 the fix is indistinguishable from the bug.

#### 9.1a Closed: 4.x gets the fix now

**Bernhard, 2026-08-10:** *"ocp_vscode 4.x should get the one-line `optionKeyOverrides` fix during its fix-freeze."*

So the branch the previous draft held open closes on the side both architects with standing argued for. One line in `resources/viewer.html`'s `optionKeyOverrides` plus the `make dist` copy (`Makefile:35`). It cannot regress any user, because the key is currently unreachable by any route, and an independent implementation already agrees on the value.

**Consequences, all of which simplify the plan.** §8.2's equivalence test carries **no exception at all** — not permanent, not scheduled. §13's commits 7 and 8 merge, because the fix and the test that would otherwise have needed excusing land together. And §15's *"two repositories touched during a fix-freeze"* stops being a risk carried and becomes a decision taken.

**One correction from the review round survives the closure and is worth keeping on the record**, because it is why the argument for fixing was weaker than the first draft claimed. That draft said an unfixed 4.x leaves *"a permanent exception"* in the certifying test. It would not have been permanent: §11 retires `viewer.html`'s `toCamelCase` at **item 10**, so the divergence would have died two items out, exactly like the `legacy` column. The decision was therefore taken on the merits of a one-line, unregressable fix rather than on a mechanical necessity that did not exist — which is the healthier basis, and it is what §9.2's policy limit now generalises.

### 9.2 Keys that are dead, and the policy — with a limit on "fix"

Three outcomes, decided per key:

- **Fix** — the key should work, the correct behaviour is known, and the fix is small. **Review added a precondition and it is kept, even though the argument that prompted it has now evaporated.** The ocp_tessellate architect observed that §9.1's *fix it, or the equivalence test carries an exception* reasoning **generalises to every defect the table surfaces and will be less right the third time it is used**. §9.1a's closure removes that particular argument entirely — there is no exception to avoid any more — but the limit it produced is worth having on its own merits, so it stands as policy: **a defect qualifies for *fix* only when an independent implementation already agrees on the correct value.** That is what makes `studio_ao_intensity` safe (cad-viewer-widget's map says `studioAOIntensity`) and it is not a property of defects in general. Anything without a second implementation to point at is *record*, however tempting the one-line fix looks.
- **Record** — the key is live but degenerate. `analysis_tool` is settable and never reported back, because the viewer reports `activeTool` in a different vocabulary that is in no Python list; `reset_camera` sits in three roles at once; and **`new_tree_behavior`'s dead duplicate is `displayDefaultOptions.newTreeBehavior` at `viewer.html:79`, not the `viewerDefaultOptions` entry at `:100`, which is the operative fallback default and must not be deleted** (§8.2 — the second draft had this inverted, settled by the ocp_vscode architect).
- **Refuse** — no path in any direction, so no row. `_debugStarted` is the clean example: `status(debug=True)` reads it and nothing produces it.

**One defect found while verifying §7.4's ground, reported rather than acted on, and it is the policy's first live test.** `cad_viewer_widget/widget.py:1408-1414`: the `Viewer.normal_len` property getter returns `self.widget.black_edges` — the wrong attribute, copy-pasted from the `black_edges` block immediately above — and, unlike both its neighbours, it has **no setter at all**, despite its docstring saying "Get or set". The traitlet and the `show()` path are fine; only the public property is broken, in both directions. **It qualifies as *fix* rather than *record* under the limit above**, because the traitlet and the neighbouring properties independently agree on what it should say — which is the same test cad-viewer-widget's `optionsMapping` passed for `studio_ao_intensity`. It is **out of item 4's scope** and belongs to whoever owns cad-viewer-widget, but it is recorded here because **item 16 generates from that surface** and would otherwise generate against a broken accessor.

**`_splash` is no longer an example of anything in this section.** The first draft cited it as the case for "record, don't tidy", quoting an ocp_vscode memory that said whether the browser branches are intentional is unanswerable. **That memory has been retracted and the question is answered by measurement** (§8.5). The policy is unchanged; its example is now a mechanism with citations rather than an unanswerable, and `_splash` itself has moved out of the table entirely.

### 9.3 Host-owned keys

`cad_width`, `height`, `theme` get `owner = surface`, in **two categories with two messages** (§5.6). **`tree_width` is `document`, and this is now established rather than inferred**: it is commented out of both lists by `743696a` — *"respect tree_width from VS Code config and make tree_width adaptable with show"* — a commit that touched `show.py`, both `viewer.html` copies and `src/controller.ts` together, with `viewer.html:577-585` acting on the value. **§16.8 closed; the first draft's `[M]` promoted.**

### 9.4 Disputed keys — none remain, and the mechanism is redefined

Both first-draft disputes are settled: `new_tree_behavior` is a display option and the widget's filing is **non-canonical rather than defective** (§8.2), and `zscale_tool` is out of domain (§8.4). So **`known_divergence` is a field for recording a scheduled correction, not for parking an argument** — every entry names the item that must remove it, and a check asserts none outlives its named item.

**With §9.1a closed, it has exactly one occupant: `new_tree_behavior`, until item 16.** `studio_ao_intensity` never becomes one, because the fix lands in every implementation in the same commit that adds the row.

**The general point, which matters more than either key.** Both were resolved by asking Bernhard, and neither was answerable from any source: whether a slider belongs to chip layout rather than CAD, and whether a tree behaviour is display or viewer, are statements about what the software is *for*. §10.4 is right to route `owner`, `lifetime` and the domain boundary to a person rather than to an extractor.

---

## 10. Populating the table

~90 to 100 rows: 75 distinct Python config keys, plus the wire-only keys (`selectedShapeIDs`, `lastPick`, `activeTool`, `holroyd`, `relative_time`, the `*0` reset-location quartet), plus the host keys in no list (`cad_width`, `height`, `theme`, `viewer`, `pinning`, `new_tree_behavior`, `normal_len`, `control`, `dark`, and the widget's `anchor`/`aspect_ratio`) — **minus** `zscale_tool` (out of domain, §8.4) and **minus `_splash`** (protocol inventory, §8.5).

### 10.1 The rule

**Extracted columns are never typed. Judged columns are never guessed. A count is judged unless its enumeration travels with it.**

### 10.2 The extractors

One per source, each committed, each stamping its source path and commit into its fixture. The ocp_vscode architect's `project_config_key_table` already carries the recipe for most of this; the extractors are that recipe made executable and version-stamped. Eight: `config.py`; `viewer.html`; three-cad-viewer (state keys **and section comments**, notification map, interface fields, defaults blocks); VS Code's `package.json`; `standalone_defaults.py`; cad-viewer-widget; build123d Studio's `viewer.js`; **and `ocp_tessellate.defaults.DEFAULTS`**.

They read **checked-out sources, not installed packages**, so a re-run against a different commit can be diffed — which is how a host's change is noticed. They never import what they read: importing `ocp_vscode.config` pulls OCP and importing three-cad-viewer needs a DOM.

**One correction to the recipe, from review.** The ocp_vscode architect has withdrawn a note in `project_show_roundtrips_measured` saying that patching `comms._send` alone is insufficient because `show.py` binds `send_*` by value at import time. It **is** sufficient: `send_data` and friends resolve `_send` from `comms`'s module globals at call time. The measured counts are unaffected — they were captured inside the patched `_send`, on the real path — but anyone re-running the measurement should use the corrected recipe.

### 10.3 The families — rebuilt

**The first draft's family 1 was `CONFIG_CONTROL_KEYS` copied verbatim**, same ten members in the same order, and the ocp_tessellate architect established that by AST rather than by eye. That is a serious structural error and the diagnosis is worth keeping: §5.13 quarantines the legacy lists precisely because they are incoherent, and then the draft used one of them as the **work-breakdown structure** — which re-imports the incoherence in the one place §5.12 cannot catch it, because the judged columns are filled family by family by the architect the family was handed to. **A mis-drawn family means the wrong person supplies `lifetime`, `type` and `default` for a key, and their citation will be truthful, which is exactly what makes it hard to spot later.**

The replacement families are defined by mechanism. Families 1–3 are the ocp_tessellate architect's own division, which it can state exactly; families 4–9 are corrected where review found them wrong.

1. **Read from ocp_tessellate's `DEFAULTS` (9)** — `default_color`, `default_facecolor`, `default_thickedgecolor`, `default_vertexcolor`, `deviation`, `angular_tolerance`, `edge_accuracy`, `render_edges`, `render_normals`. Default source: `defaults.py:109-175`. **ocp_tessellate architect** for `type` and `default`.
2. **Passed as parameters, shadowing a `DEFAULTS` entry that is never read (6)** — `helper_scale`, `render_mates`, `render_joints`, `show_parent`, `show_locals`, `timeit`. Default source: the `to_ocpgroup` signature (`convert.py:1749-1760`) and `tessellate_group`'s `timeit` argument (`convert.py:1819`). **These keys have two ocp_tessellate defaults that can disagree, and nothing enforces agreement** — today the only skew is `helper_scale`, `1` in the dict against `1.0` in the signature. §5.9 rule 2 and the `default_source` field exist for this family.
3. **Passed as a parameter with no `DEFAULTS` entry (1)** — `debug`, a `to_ocpgroup` parameter (`convert.py:1760`) that ocp_vscode passes at `show.py:338`. Its default lives in a function signature and nowhere else.

Three keys the first draft mis-assigned, each moved:

- **`reset_camera` is not ocp_tessellate's at all.** It is in that package's `DEFAULTS` (`defaults.py:159`) and in the dead `add_shape_args` filter, and is read by nothing; it is not a parameter of `to_ocpgroup`, `to_ocp` or `tessellate_group`; and its type is `Camera`, an enum ocp_tessellate has never heard of. It moves to the camera/tree families. The draft's note that "`reset_camera` and `timeit` also reach the viewer and need the ocp_vscode architect too" was **half right**: `timeit` genuinely is joint — it reaches ocp_tessellate as `tessellate_group`'s fifth argument controlling `Timer` output (`utils.py:128-166`) and reaches the viewer as well — and `reset_camera` is not joint, it is simply not ocp_tessellate's.
- **`default_edgecolor` and `default_opacity` are never read anywhere in ocp_tessellate.** The three-way colour precedence covers `default_facecolor`, `default_thickedgecolor`, `default_vertexcolor` plus a two-way version for `default_color` — four keys, not six. Both move to the render-option family, owned by the ocp_vscode and three-cad-viewer architects, and their `default` must come from `ViewerState` under §5.9's rule, **not** from ocp_tessellate's dict. The trap that makes this worth stating: `defaults.py:127`'s `"#707070"` happens to equal `standalone_defaults.py:38`, so an author filling the row from the wrong source gets the right number for the wrong reason and will not notice when they diverge. (`default_opacity` is a `float`, not a `color`, which is a third reason it did not belong there.)
- **`render_edges` was in no family at all** — and it is one of the nine keys ocp_tessellate actually reads (`convert.py:1922`). It decides `compute_edges`, changes the payload, is part of the tessellation cache key, is force-set to `True` by ocp_vscode on every show (`show.py:399`), and is in no `CONFIG_*` list and no settings schema. **Copying a legacy list is exactly why it was lost.**

And one duplicate removed: **`edge_accuracy` appeared in both family 1 and family 3** of the first draft. §5 is one row per key and §13 is one commit per family, so a key in two families is either two rows or two commits touching one row. It sits in family 1 only.

The remaining families:

4. **Surface (2, was 6)** — `cad_width`, `height`, plus `theme` in its own category (§5.6). **`glass` is removed**: it is a persistent VS Code setting, a standalone setting, a `CONFIG_SET_KEYS` member with a live `ui` branch (`viewer.html:816-817`) and it is reported back in status — grouping it here invites `owner = surface`, which is wrong. It joins the tree/tab family. `pinning` is genuinely surface-ish (`viewer.html:72`, never set from Python) and stays. `tree_width` is `document` (§9.3) and moves out.
5. **Camera (8)** — `position`, `quaternion`, `target`, `zoom` and the reset-location quartet. **The first draft's note that these "are not state-backed" was wrong** — all four *are* `STATE_KEYS` members (`viewer-state.ts:219-222`). The accurate fact, and it is sharper: they are never notified from state and never written back from the camera, so `state.get("position")` holds whatever the embedder passed at the last `render()` **forever** and diverges from the wire on the first orbit. **Item 13 must read camera values from the wire or from the `getCamera*()` accessors, never from `viewer.state`.**
6. **Tree, tabs and visibility (6)** — `states`, `collapse`, `tab`, `explode`, `analysis_tool`, `glass`. Where §5.7's rule earns or loses its keep. Two row notes: `states`' `applied_by` is `code`, via `Viewer.setStates` → `treeview.setStates` (`viewer.ts:3367-3370`, `treeview.ts:753`), it must be **batched** or it is an O(n²) repaint storm, and **`notify=false` does not suppress its echo** (`treeview.ts:740`).
7. **Clip (9), Zebra (5), Studio (11)** — mostly mechanical after the above; §9.1 lands here, and §5.8's `0`-is-off and clip-normal notes attach here.
8. **Lighting and material (7 + 2)** — the render options, now including `default_edgecolor` and `default_opacity`, plus `normal_len` (§7.4).
9. **Wire-only (5)** — `selectedShapeIDs`, `lastPick`, `activeTool`, `holroyd`, `relative_time`. The smallest family and the most consequential for item 13.

### 10.4 Who fills what

The migration architect drafts every row; each family goes to the architect who owns the code that settles it. **One correction from review: `lifetime` is not the tessellation architect's to give.** Whether a key is `persistent` is decided by whether a *host* stores it, which is a fact about the host. The ocp_tessellate architect can supply its half — "this key is read per-`to_ocpgroup` call and nothing in ocp_tessellate persists it", true of all sixteen — but the `persistent`/`session` verdict needs the ocp_vscode architect's schema facts. It has already measured the split for its family: `deviation` and `angular_tolerance` are `persistent` (`package.json:437`, `:443`); `edge_accuracy`, `helper_scale`, `render_joints`, `render_mates`, `render_normals`, `show_parent`, `show_locals`, `timeit` and `debug` are `session`; `render_edges` is in no list and no schema at all. **So `lifetime` is marked joint for families 1–3**, as `timeit` already was.

**Bernhard settles the rows where two hosts disagree**, because those are product decisions rather than readings — demonstrated rather than proposed: `new_tree_behavior` and `zscale_tool` were both referred up and came back settled in a sentence each. The same route applies to every key where the VS Code default and the standalone default differ, and to any future `out_of_domain` candidate.

---

## 11. Retiring the five lists and `toCamelCase`

Nothing is retired in item 4. The table is proved equivalent first, and each list dies where its owner adopts.

| what | dies at | replaced by |
| ---- | ------- | ----------- |
| `ui_filter` | item 5 | nothing — **it has no caller**, confirmed |
| `workspace_filter` | item 7 | a table predicate over `lifetime`/`class` |
| `CONFIG_SET_KEYS` | item 7 | a predicate; call sites `config.py:656`, `:777` |
| `CONFIG_KEYS` | item 7 | a predicate (`set_defaults` membership) |
| `CONFIG_CONTROL_KEYS` | item 7 | `group = none` |
| `CONFIG_WORKSPACE_KEYS` | item 7 | a predicate |
| **`CONFIG_UI_KEYS`** | **item 7, not item 5** | dies with `CONFIG_WORKSPACE_KEYS` |
| the five names as importable symbols | item 15 (a major) | deleted |
| `toCamelCase` in `ocp_vscode/templates/viewer.html` | item 10 | the generated JS map |
| `SNAKE_TO_CAMEL` in `build123d-studio/src/viewer/viewer.js` | item 14 | the generated JS map |
| the widget's `optionsMapping` | item 16 | the generated JS map |

**Correction from review:** the first draft claimed `CONFIG_UI_KEYS` is referenced only by `ui_filter` and therefore dies with it at item 5. It has **two** references — `ui_filter` at `config.py:667` **and `config.py:205`**, where `CONFIG_WORKSPACE_KEYS = CONFIG_UI_KEYS + [...]` is built from it. Retiring `ui_filter` does not free it; it survives to item 7. The draft's schedule had a key list dying two items earlier than it can.

**And the item 15 deletion is safer than the draft claimed.** Nothing outside `config.py` imports any of the five — confirmed across ocp_vscode (one comment at `show.py:411`), jupyter-cadquery, cad-viewer-widget and build123d Studio. **Stronger: none of the five names is in `config.py`'s `__all__`, so `from ocp_vscode import CONFIG_KEYS` already fails today**; only the explicit submodule import would work, and nothing uses it.

**`toCamelCase` has three graves, not one** — `viewer.html`, our `viewer.js`, and the widget's explicit map. `requs.md` names only the first. The standalone shares `viewer.html` and dies with it.

The `legacy` column cannot be deleted until all five lists are gone, so it outlives item 4 by three items. Scheduled, not forgotten.

---

## 12. Sequencing

**Item 4 is first in Phase 1 and blocks nothing in flight.** It is additive: a new repository's first content, plus two one-line fixes in existing repositories (§9.1a).

- **Item 5** imports the generated Python module when `config.py` moves; item 9's kit lands with that first moved module and absorbs the host-free checks of §8.
- **Item 6** builds `Session`. **Nine connections for a first `show()` and eight for a repeat** — the repeat loses `get_defaults` at `show.py:462`, the clip-insight reset branch, which is skipped when the bbox is unchanged and the camera is kept. Six of the nine are the identical `config` command and three of those exist only so `preset("timeit", …)` can read a value already in `DEFAULTS`; caching one settings read removes five. **`requs.md` says six in two places and item 9 inherits the error** — §17.6. **Two warnings for item 6, recorded here so they are not discovered there.**

  **The cache must be per-`show()`, and `_splash` is the proof case with a measurement behind it.** `requs.md` already specifies a per-show cache and §1 restates it, so this changes no decision — but the constraint now rests on a mechanism rather than on prudence. `_tessellate`'s first act is `combined_config` → `workspace_config`, and the guard on the very next line tests *that* read (`show.py:241-242`, `config.py:742`); the six `config` reads of a `show()` are steps 1, 2, 3, 5, 6 and 7 while the model send is step **8**, and the model send is the only thing that flips the flag — **so `_splash` is invariant within a show and changes exactly once, at the last step of the first one** (§8.5a). A `Session` caching for its own lifetime replays a stale `True`, forcing `Camera.RESET` **and** discarding every explicit `reset_camera=` on every subsequent show, permanently and silently. **Item 9's kit gains the matching assertion: two successive shows produce two settings reads, not one.** And the invariant is phrased about the *value* rather than the *cache*, because the standalone reaches the same stale `True` with no cache at all: **`_splash` is re-resolved from the host on every `show()`, and a `True` not produced by this show's `workspace_config` call is a bug wherever it came from.**

  **And a `Session` cache overlaps a mesh cache**, from the ocp_tessellate architect: `deviation`, `angular_tolerance`, `render_edges` and `edge_accuracy` (through the deflection it computes) are part of the **tessellation cache key** (`tessellator.py:114-123`). Changing any of them invalidates every cached mesh. A `Session` caching config across shows is caching something a mesh cache is keyed on, and the two have to agree about when a value changed.
- **Item 7** consumes `owner`, `refusal(key)` and the surface-key capability, deletes the `show.py:365-375` branch, and — the strongest thing §5.6 achieves — **dissolves the `not is_jupyter_cadquery` guard on that same branch**, but only if the injection replaces the guard and not merely the key set.
- **Item 10** consumes `live_settable ∧ ¬ui` as its checklist — **eleven keys, the studio family** — and replaces `toCamelCase` with the generated map. It is also where `viewer.html`'s copy dies — which, had §9.1a gone the other way, is where the divergence would have expired.
- **Item 13** consumes `class`, and the camera rule of §10.3 family 5.
- **Item 14** generates our Settings from the `lifetime = persistent` rows using `type`, `domain` and `default`; §5.8's `repr` and `0`-is-off notes are what stop it generating a wrong colour or a mislabelled slider.
- **Item 16** generates the widget's whitelists from `group` and its traitlets from `type`/`default`, corrects `new_tree_behavior`'s filing (cosmetic, §8.2), and **must wait for three-cad-viewer's `ViewerOptions`/`ZebraOptions` typing fix** rather than generating around it (§5.3). **Two constraints from the sign-off round.** Its traitlet generation **must not filter on `lifetime`**: `normal_len` is `derived` and the widget's public API nonetheless sets it, so a generator that skips `derived` rows would drop a traitlet the widget has today (§5.5). And it generates against `cad_viewer_widget/widget.py`'s property surface, where `Viewer.normal_len`'s getter is broken and its setter missing (§9.2) — that wants fixing upstream before item 16 rather than being generated around.

---

## 13. Deliverables and commit sequence

All in `ocp-viewer-core` unless stated.

1. `tools/extract/*` — eight extractors and their fixtures, with source paths and commits recorded. **No table yet.** Checkable purely by re-running.
2. `tools/generate_config_keys.py` and the checks **C1′, C2, C3**, against an empty table. Proves the machinery fails correctly before there is anything to protect.
3. `config_keys.toml` — extracted columns only, all rows, no judged columns. Generation refuses, because every row lacks evidence. The failure is the demonstration.
4. Nine commits, one per family of §10.3, each adding judged columns with citations. **Within each commit, `domain` and `wire_repr` are filled before or with `class`, never after** — §5.7 derives (a′) from `wire_repr`, so a `class` computed against an empty `domain` silently defaults to "the domains agree" and would classify `activeTool` as state. The generator enforces the ordering by refusing a row that has a `class` and no `domain`.
5. The generated `config_keys.py` and `js/src/config-keys.js`, plus the no-diff-on-regeneration test.
6. `docs/protocol-inventory.md` — §8.5, `_splash` its first entry, plus the `out_of_domain` list of §8.4.
7. `tests/test_equivalence.py` — §8.1, §8.2, §8.3 — **together with the `studio_ao_intensity` fix in all three places** (§9.1a is closed, so these are one commit rather than two): the table row, `build123d-studio/src/viewer/viewer.js`'s `KEY_OVERRIDES`, and `vscode-ocp-cad-viewer/resources/viewer.html`'s `optionKeyOverrides` plus its `make dist` copy. One line each. **`new_tree_behavior` passes** with a `known_divergence` carrying its answer and its removal item (16) — the second draft's expectation that it would fail here was wrong, since the widget is non-canonical rather than defective. **So no test in this commit is expected to fail and no exception is recorded.**

   The un-apply for this commit is the one that matters most: **removing the 4.x override alone must fail §8.2 and only §8.2.** That is what proves the equivalence test is actually comparing against `viewer.html` rather than against the table it was generated from.

**Seven commits, not eight** — §9.1a's closure merged the last two.

**Proving the tests fail first** is not optional, per this repository's standing rule: a row's `option` corrupted must fail C1′ and only C1′; a `wire` corrupted must fail C3 and only C3; a key deleted must fail coverage and nothing else; a `default_source` removed must fail generation. The un-apply is a throwaway script outside any repository, deleted once the check is validated.

---

## 14. Out of scope for item 4

- Any change to `config.py`'s runtime behaviour, including the precedence chain, `set_defaults`, `set_viewer_config`, `reset_defaults`. Items 5 and 7.
- The `ui` dispatch gap for the eleven studio keys. Item 10.
- Reducing the connection count. Item 6, asserted by item 9.
- Generating any host's settings UI or traitlets. Items 14 and 16.
- The `Comms` command vocabulary and `status()`'s failure behaviour. Items 7 and 9.
- The wire format, the codec, and `numpy_to_buffer_json`. Item 8 — **except `normal_len`'s one-row classification** (§1, §7.4).
- Any change to three-cad-viewer beyond the export it has accepted (§7.2) and the `ViewerOptions`/`ZebraOptions` typing fix that ships with it. Both are that project's.
- **Deleting the 36 inert keys from `ocp_tessellate.defaults.DEFAULTS` — out of scope here, and now scheduled elsewhere.** The two halves must not be confused, so they are stated separately:
  - **Item 4's half, which is in scope:** the §8.3 coverage extractor walks all 51 keys, so the fossils are *recorded* mechanically rather than argued about, and a future ocp_tessellate release that adds a key to that dict is noticed by the core's tests. Item 4 records; it does not delete, and it does not treat the dict as a `default` source for any row (§5.9).
  - **ocp_tessellate's half, which is not:** the deletion itself. **Bernhard's decision, 2026-08-10: it goes on the ocp_tessellate 4.0.0 list now**, beside the colour constants (`FACE_COLOR`, `THICK_EDGE_COLOR`, `VERTEX_COLOR`, `EDGE_COLOR`) and the two root re-exports already scheduled there. The architect's argument carried: leaving it as an open question is exactly how the 3.5.0 fallbacks become permanent by neglect, which `requs.md:566` warns about in the same words. The correct end state is that `Defaults` holds the sixteen keys ocp_tessellate can act on and nothing else.
  - **And it is treated as breaking.** Whether any real user calls `to_ocpgroup` directly and relies on `set_defaults` is not knowable from the sources; **Bernhard's ruling is to assume they do** — *"it is a public API, so it could be. We should assume someone does."* Today `set_defaults(ticks=…)` is accepted and silently does nothing; afterwards it prints "not a valid argument". That is a breaking change, which is consistent with 4.0.0 and not with a 3.x patch, and §5.9 carries the consequence for the table.
- Deleting any dead branch found along the way (§9.2).
- The ocp_tessellate cache-id instability, which is on `ROADMAP.md` at Bernhard's direction and is not migration work.

---

## 15. Risks, each with its evidence

- **The table becomes the thirteenth list.** A twelfth already exists: cad-viewer-widget's `optionsMapping` is an explicit, hand-kept, 44-entry map that is *more* correct than ocp_vscode's derived one on one key and *less* canonical on another. Mitigation: generation from one source, committed artefacts with a no-diff test, and the extracted/judged split. Residual: the judged columns are hand-kept by construction, and only review protects them — which is exactly what happened this round, three times (§0.1).
- **The fixture goes stale and the checks quietly weaken.** Evidence, strengthened by review: three-cad-viewer's `Data Format.md` and `Design.md` have drifted from the code in a dozen verified places including a whole interface shape and six default values, `Changes.md` has **no v5.0.3 entry at all**, and the working tree is three commits ahead of `origin/master` — **so the shipped changelog does not describe the installed code, right now, in the repository the fixture is extracted from.** That is the same class of failure as a stale fixture. Mitigation: re-extraction asserted in the core's own tests, plus the version stamp, plus the accepted export — and the first draft was wrong that the export supersedes the fixture (§7.2).
- **The table encodes today's accidents and outlives them.** Evidence: `reset_camera` in three roles; `CONFIG_SET_KEYS ⊄ CONFIG_KEYS` producing a warning that is wrong and a value that is applied. Mitigation: the `legacy` quarantine with a scheduled death. **Residual risk demonstrated this round:** the first draft used one of the quarantined lists as its work-breakdown structure (§10.3), so quarantining a list in the schema does not stop it leaking into the *process*.
- **`class` is wrong for one key and item 13 reintroduces a fixed bug.** Evidence: this repository had that bug and fixed it (`src/viewer/viewer.js:169-177`), and the standalone still has it (`standalone.py:435-440`). Mitigation: §5.7's replacement rule, whose (a′) is decidable from extracted facts rather than argued in prose — which matters, because the first draft's rule reached three of six answers by unstated routes and one of them was the phrase "in spirit".
- **The `owner` mechanism leaks a host name into the core.** Evidence, and the grade is corrected: the four host-naming sites (`show.py:368`, `show.py:1634`, `comms.py:40`, `comms.py:320`) are individually confirmed, but the *synthesis* "a host is named in four ways" is mine, assembled from three of the architect's files, so it is **[M]**, not **[A]** — a correction that matters precisely because this plan's grading is its main defence. And the scope is now stated honestly: §5.6 addresses **one** of the four plus a fifth the draft missed (the `is_jupyter_cadquery` guard on the same branch); the other three are item 7's.
- **We are the atypical host and the table is derived mostly from ocp_vscode.** ocp_vscode and the widget are the primary sources; our `viewer.js` is a third opinion, not the arbiter. **The first draft's residual risk here is withdrawn** — it read "we have keys nobody else has and no natural home for them", and `zscale_tool` was its only evidence, which turns out to be a GDS tool out of the table's domain (§8.4). No second instance is known.
- ~~**The fix-freeze question.**~~ **No longer a risk: it is a decision taken.** Bernhard has ruled that ocp_vscode 4.x gets the one-line fix during its freeze (§9.1a). What remains is the ordinary risk of any change to a frozen branch, and it is as small as it gets — one line, in a mapping table, for a key that is unreachable by any route today, with an independent implementation already agreeing on the value, landing in the same commit as the test that would otherwise have caught it.
- **"Fix what the table finds" generalises badly.** From the ocp_tessellate architect: §9.1's *fix it or carry an exception* argument would have been available for every defect the table surfaces and would be less right the third time. **§9.1a's closure removes that argument outright** — there is no exception to avoid any more — but the risk it pointed at is real and outlives it, because the table will surface more defects and each will look like a one-line fix. Mitigation is policy rather than vigilance: *fix* requires an independent implementation to already agree on the correct value (§9.2). Residual: nothing prevents a future defect from acquiring a second implementation that is *also* wrong, which is why the check compares against the renderer's own vocabulary rather than across implementations (§7.2).
- **`_splash` ends up permanently true, by any of three routes.** The flag is `True` for the first `show()` only, and three separate mistakes produce a `True` that never clears: **cache it too long** — a `Session` caching the settings read for its own lifetime instead of per-`show()` (§8.5a); **never flip it** — the standalone's flag when no browser is attached, reached with no cache at all; and **lose the first model message's delivery to the host** — which a `Comms` redesign that batches model sends, or that routes model data past the host straight to the frontend, could do **while preserving every field**. All three present identically as *"the camera keeps resetting and `reset_camera=Camera.KEEP` is ignored"*, and none produces an error.

  **The third route is stated correctly here for the first time.** The second draft had it as *"dropping the forwarding leaves the host stuck on splash"*, and that is **false**: dropping the `_splash` field from the model payload changes nothing, because no host reads it (§2). The field is inert and the **event** is what carries the transition — which makes the risk harder rather than easier, because a redesign that faithfully preserves the payload can still break it. Mitigation: §8.5's normative clause (i) names the edge rather than the payload, §8.5a's value-level invariant covers the first two routes, and item 9's two-shows-two-reads assertion catches the first mechanically.

---

## 16. Open questions

**Fifteen of sixteen are closed after the sign-off round**, struck through in place so a reviewer can see what was asked and what the answer changed. **Nothing is open with Bernhard, and nothing is open with any architect.** One remains, and it is a commitment rather than a question: #2, the three-cad-viewer export patch, which that architect has undertaken to ship as 5.0.4.

1. ~~**Is `STATE_TO_NOTIFICATION_KEY` 40 entries or 47?**~~ **Closed: 47.** `STATE_KEYS` 76, absent 29, 47 + 29 = 76. The architect's memory was wrong and it corrected it, enumerating the 29 rather than summarising them (§0.1).
2. **The three-cad-viewer export.** **Committed, not merely accepted**: it ships as **5.0.4**, in the exhaustive `Record<keyof I, true>` form, **with `STATE_TO_NOTIFICATION_KEY` in the same patch** because C3 reads that map, and with the accepted cost recorded — after 5.0.4 a `ViewerState` key rename is breaking *by contract* (§7.2). The only thing still outstanding is the patch existing; nothing about it is undecided.
3. ~~**Where does `new_tree_behavior` belong?**~~ **Closed: display.** Bernhard ruled, the renderer's own filing agrees, and the widget's placement is **non-canonical rather than defective** — not a bug report (§8.2).
4. ~~**Is `relative_time` state or event?**~~ **Closed: event, `lifetime = transient`.** It passes round-trippability cleanly and fails model-independence, and replaying it is not inert — it re-emits itself onto the wire, so a stale animation position would be self-sustaining (§5.7).
5. ~~**Does `studioAOIntensity` have an observable effect?**~~ **Closed on mechanism: yes, conditional on studio mode**, taking effect on the first studio entry after the value is set, with `0` a distinct disable (§9.1). The **visual confirmation on a real build remains Bernhard's**, and the architect supplied the test conditions: enter studio mode, use `0` and `2.0`, because at 0.5 the fix is indistinguishable from the bug.
6. ~~**What happens to host-specific keys like `zscale_tool`?**~~ **Closed: refused, out of domain** (§8.4). The general question underneath — *may a host have a genuine CAD config key the shared table does not carry?* — is **not** answered by this and is not currently live, because the one candidate turned out not to be a CAD config key. It becomes live the first time a real one appears.
7. ~~**Should the core refuse `shapes.studioOptions`?**~~ **Closed: no.** Refusing would be the core policing a renderer-internal deprecation it does not own, and the renderer handles it correctly already (§3).
8. ~~**Is `tree_width`'s exclusion from the surface list deliberate?**~~ **Closed: yes**, with commit evidence `743696a` (§9.3).
9. ~~**Is `ocp_tessellate.defaults` in scope?**~~ **Closed:** not as a `default` source for any row; **yes** as a coverage source (§8.3); and its reduction is ocp_tessellate 4.0.0 work rather than item 4's (§14).
10. ~~**`normal_len`: I took the option the ocp_tessellate architect did not prefer.**~~ **Closed — the objection is withdrawn.** That architect verified all four legs of the ground I had and it did not: `normal_len` is the 7th entry of `renderOptionKeys` (`viewer.html:370`) and of our `RENDER_KEYS` (`viewer.js:32`); the widget maps `normal_len → normalLen` (`widget.js:366`); and `normalLen` is a `RenderOptions` field (`types.ts:316`), a `STATE_KEYS` member (`viewer-state.ts:195`), a `ViewerStateShape` field (`types.ts:470`) with a `ViewerState` default of `0` (`:459`) and a live consumer at `nestedgroup.ts:863` fed from `viewer.ts:633`. Its own diagnosis is worth keeping: **its premise was too strong rather than its reasoning wrong** — it established the *provenance* of the value and inferred that the key was not configuration, and provenance and path are two separate facts that this key has both of. Its preferred option 2 would have been **actively wrong**, and `default = 0` agrees with `ViewerState` so §5.9 rule 1 produces no conflict. What the closure left behind is the *condition* on §5.5's wording, applied above.
11. ~~**Five or six, in the ocp_vscode review's F1 list?**~~ **Closed: six.** `ticks`, `grid_font_size`, `deviation`, `angular_tolerance`, `default_color` and `timeit` are all `set_defaults` parameters, verified by `inspect.signature`; `modifier_keys`, `theme` and `control` are not. The word "Five" was the typo and the parenthesised list was right — **the same shape as every other defect this round: the enumeration was correct and the count derived from it was not** (§0.1). **The row values split accordingly:** those **six** get `live_settable = false`, `ui = false` and the note *show-time only, by construction* — they reach the viewer through `DEFAULTS` → `conf` → `params` on the next `show()`. The other **three** get `live_settable = false`, `ui = false` and a **different** note: *not settable from Python at all*, `modifier_keys` and `theme` being host-supplied and `control` being derived from `orbit_control`.
12. ~~**Should ocp_tessellate's `DEFAULTS` reduction go onto the 4.0.0 list now?**~~ **Closed: yes.** Bernhard, 2026-08-10 — the architect's argument carried, and the 36 inert keys join the colour constants already on that list. Item 4 records the fossils; ocp_tessellate deletes them (§14).
13. ~~**Do direct `to_ocpgroup` callers exist?**~~ **Closed by assumption, which is the answer that matters:** *"it is a public API, so it could be. We should assume someone does."* So the reduction is **breaking** — consistent with 4.0.0, not with a 3.x patch — and no row may treat the dict as the only way its value is set (§5.9 rule 2). **The same assumption keeps `apply_defaults`'s fix-versus-delete question open**: it has no caller in any project, and "no caller" is exactly the reasoning this ruling forbids as a shortcut.
14. ~~**§9.1a — does ocp_vscode 4.x get the one-line fix during its fix-freeze?**~~ **Closed: yes** (§9.1a).
15. ~~**Does the extension read the forwarded `False`, or flip on the arrival of any model?**~~ **Closed: neither host reads the payload; both flip on arrival.** `_splash` appears in host code in exactly three places and all three are writes; the `D:` branch forwards the payload verbatim without parsing it and then flips unconditionally (`controller.ts:219-227`, `standalone.py:396-404`). So **the field is inert and the event is normative**, which inverts the "conservative requirement" the second draft chose and makes §15's third route a lost *delivery* rather than a lost field (§8.5).
16. ~~**Does the standalone's `_splash` stay `True` when no browser is attached?**~~ **Closed: yes, and it is defensible rather than a bug.** The flip sits after `if self.javascript_client is None: … continue` (`standalone.py:399-404`), so the model is dropped and the flag never clears; VS Code flips unconditionally after a `postMessage` that carries no delivery guarantee either. **The two hosts have picked different points on one edge — *delivery attempt* versus *successful routing* — and §8.5's normative clause (iii) requires item 7 to say which is normative** rather than leaving it to be rediscovered.

Carried unresolved from the architects' memory and untouched: whether `send_backend`'s `{"ok": false}` path fires in the standalone; whether `analysis_tool`'s absence from the notify table is intended; the intended `jupyter_cadquery` contract including the `JUPYTER_CADQUERY == "1"` versus `is not None` divergence across three files; and whether `states` — optional input, preserved-across-render state, and delta output — needs more than one row. **The `_splash` question is no longer on this list**: it was retracted by its owner, answered by measurement, and then superseded by Bernhard's own account, which is narrower than either (§8.5).

---

## 17. Where `requs.md` is stale or wrong

Proposed corrections only. **I have not edited `requs.md` and will not.** Items 1–4 were re-verified by the ocp_tessellate architect this round; items 11–13 are new from it; item 10 is **withdrawn as wrong**.

1. **Phase 0's extra release is done — and, more importantly, the blocker it existed for is gone.** `ocp_vscode/pyproject.toml:30` reads `ocp-tessellate>=3.4.0,<3.6.0` at `934e1fa`. The first draft said only that the release happened. **What a reader carries forward is line 544's *reasoning*** — that `pip install ocp_viewer` fails in any environment containing ocp_vscode 4.x from step 3 to step 5. With the ceiling widened *and* `ocp-viewer-core/pyproject.toml:31` declaring `ocp-tessellate>=3.5.0,<3.6.0`, **the ranges now intersect and the disjointness is gone.** Say the blocker is gone, not that a release happened.
2. **Item 1 is done.** `ocp_tessellate/_version.py:31` reads `3.5.0`, `pyproject.toml:7` agrees, and the CHANGELOG entry describes exactly the additive change line 558 asks for. Line 558's "measured, ocp_tessellate is at 3.4.1" is history in the present tense.
3. **Line 542's editable-install example is stale.** Both shared environments report `3.5.0` in metadata and in `__version__`, and both resolve to the editable checkout. The lesson survives; the numbers go.
4. **`convert.py` line numbers moved.** Line 598 cites `:2105` inside `export_three_cad_viewer_js` (`:2071`); they are **`:2155`** and **`:2121`**.
5. **Stale item numbers survived the renumbering, and one is actively dangerous.** Line 523's *"Item 4 below is done upstream"* means what is now **item 3**; under current numbering item 4 is this table and is emphatically not done. Line 606's *"Item 1 adds two exports"* means **item 2**. Line 572's "4a"/"4b" are 3a/3b. Line 568's "Numbered zero" refers to an item zero that does not exist.
6. **The round-trip count is nine, not six.** Item 6 (line 592) says six; the measurement is **nine** for a first `show()` and **eight** for a repeat — the repeat loses `get_defaults` at `show.py:462` — with six of the nine the identical `config` command. Re-measured this round. Item 9 (line 601) inherits the error, and **its assertion must be written against 9/8**.
7. **"Roughly sixty synced traitlets" (line 630) is low.** `cad_viewer_widget/widget.py` carries **88** `sync=True` declarations **[M]**, a minority of them plumbing. The `utils.py:125-208` range is exact.
8. **Item 4's own text undercounts what it replaces.** It names five lists plus `viewer.html`'s `toCamelCase`; there are at least three more implementations of the same outbound mapping, and item 16 in the same section already says "three more of the dozen overlapping lists". The two paragraphs disagree about the size of the problem.
9. **`show.py:351-375` is cited for the `params` filter; the filter starts at `:345`.** The kwargs loop at `:365-375` is exact.
10. ~~**`ocp_utils.py:26-38` should be `:25-38`.**~~ **Withdrawn — the proposed correction was wrong.** Line 25 is `import numpy as np` and line 27 is a `cachetools` import; neither is an OCP import. The OCP module-scope imports are **line 26 (`import OCP`) and lines 28-99**, ending with the `from OCP.TopTools import (...)` block. requs.md's existing `:26-38` at least starts in the right place; the proposed edit moved the start onto a numpy import and still stopped sixty lines early. **Replace with `:26,28-99`, or simply `:26`, which is the line that makes the point.** (Recorded rather than quietly dropped, because it is an instance of the same failure the plan is built to prevent: I proposed a citation correction from a quick read rather than from the declaration's extent.)
11. **New — line 598's characterisation of the second `numpy_to_buffer_json` call site is wrong, not merely mis-numbered.** It says the call "sits inside `export_three_cad_viewer_js`", which reads as *the exporter base64-encodes*. **It does not, on its default path.** `keep_instances=False` takes a different branch entirely: `decode()` inlines each instance into the leaf's `shape` and `numpy_to_js` dumps plain JSON number lists (`convert.py:2157-2159`) — measured at 2195 bytes for `Box(1,2,3)`, no base64 anywhere. Only `keep_instances=True` reaches `numpy_to_buffer_json` (`:2155`), and on that branch the `var` argument is silently ignored and no `var name =` prefix is emitted. **This matters for item 8's byte-stability requirement:** the output the two three-cad-viewer example scripts actually produce is the *non*-base64 one, so "keeps its output byte-stable" has to mean both branches, and the branch requs.md names is the one nobody calls.
12. **New — line 562's list of `Color` users is wrong in one citation, in a way that strengthens its own argument.** It cites `ocp_utils.py:102`, `cad_objects.py:20`, `tessellator.py:65` and `__init__.py:40` as proof that moving `Color` into the core would create a distribution cycle. **`tessellator.py:65` imports `Timer` and `round_sig`, not `Color`.** The correct fourth citation is `convert.py:24` (`from ocp_tessellate.utils import *`), and `stepreader.py:47` imports `warn` from the same module. The conclusion is unchanged and better supported.
13. **New — `requs.md:566`'s list of what ocp_tessellate 4.0.0 removes is now short by one item.** It warns that the additive parts of 3.5.0 must not "become permanent by neglect" and enumerates the removals: the three colour constants, the already-dead `EDGE_COLOR`, and the two root re-exports. **Bernhard has since added a fifth: the 36 inert keys in `Defaults`** (§14, §16.12). The line should name it, both because the enumeration is the mechanism that stops neglect and because the addition is a *breaking* change while everything else on that list is a removal of something already dead. **And the reason it is breaking is the read-back path, not the write path** — a correction from the ocp_tessellate architect worth carrying, because a weak justification invites someone to reopen it: `Defaults.set_defaults` prints and never raises (`defaults.py:104`), so after the reduction `set_defaults(ticks=10)` merely gains a warning and stops nothing working. What changes silently is that **`get_default("ticks")` returns `10` today and `None` afterwards**, so a direct caller using `Defaults` as a general config store changes behaviour with no diagnostic — which is precisely the caller §16.13 instructs us to assume exists, tying the two rulings together.

---

## 18. Sign-off: the conditions, and where each one landed

**All three architects signed off on the second draft with conditions.** Their original findings stay in `reviews/` as the record; the conditions are below with the section that applies each. This is the list that goes to Bernhard, so the gate can be seen to be closed rather than declared closed.

### three-cad-viewer — 3 conditions, all applied

| # | condition | applied in |
| - | --------- | ---------- |
| **1** | §7.2's *"C1′ and C2 genuinely disagree in both directions"* is overstated — only `tab` is a disagreement; the zebra keys pass both. Replace the second bullet with the mis-filed-`iface` argument, which is stronger | **§7.2**, replaced with its wording verbatim in substance; zebra recast as *the reason C2 exists*, not an example of disagreement |
| **2** | (a′)'s domain half is not extractable as the schema stood; close it with `wire_repr`'s three states, and record the sequencing consequence | **§5.7** (the three-way rule and the eight-key verification), **§5.8** (`wire_repr` gains the decoder/no-decoder state and `activeTool` as its second member), **§5.12** (the judged/derived split), **§13 commit 4** (`domain`/`wire_repr` before or with `class`, enforced by the generator) |
| **3** | the export: record it completely — `STATE_TO_NOTIFICATION_KEY` in the same patch, and the accepted cost that a `ViewerState` rename becomes breaking by contract | **§7.2** (both additions, and 5.0.4 as a commitment rather than an acceptance), **§16.2** |
| *obs.* | generalise §0.1's rule; §5.12's evidence discipline does not catch claims made in prose | **§0.1** (the generalised rule), **§5.12** (a new bullet closing the gap, including that an unreachability claim must enumerate *consumers*) |

### ocp_tessellate — 1 condition, applied; objection withdrawn

| # | condition | applied in |
| - | --------- | ---------- |
| **1** | `lifetime = derived` is not host-invariant — cad-viewer-widget never tessellates and has a full public setting path for `normal_len`. Pick (a) `session` + note, or (b) keep `derived` with a redefinition, and say why | **§5.5**, taking **(b)**: `derived` redefined as *no host-independent input path*, with the reason (a) was rejected stated — `session` would make item 14 generate a Settings control that silently does nothing on two of three hosts. Both obligations recorded: the widget's four citations on the row, and **§12**'s constraint that item 16's traitlet generation must not filter on `lifetime` |
| *note 1* | §17.13's "breaking" is right for a better reason — the read-back path, not the write path | **§17.13** |
| *note 2* | a live defect in `cad_viewer_widget/widget.py:1408-1414` — `Viewer.normal_len`'s getter returns `black_edges` and it has no setter; qualifies as *fix* under §9.2's limit | **§9.2** (recorded, out of scope, flagged as the policy's first live test) and **§12** (item 16 generates from that surface) |
| *withdrawn* | the `normal_len` objection — all four legs verified, its premise was too strong, its preferred option would have been actively wrong | **§16.10**, closed with its diagnosis kept |

### ocp_vscode — 3 items, 2 of them conditions, all applied

| # | item | applied in |
| - | ---- | ---------- |
| **A** | `_splash`: neither host reads the payload; both flip on arrival. The field is inert, the **event** is normative, and the same wrong claim appears in three places | **§2** (the bullet rewritten and a second bullet added with the three-writes-no-read finding), **§8.5** (the `[?]` closed; the logo-path edge; the per-host divergence; the three-clause normative statement), **§8.5a** (the measured step-8 window and the requirement), **§15** (the third route restated as a lost *delivery*, with the false claim named as false) |
| **B** | `viewer.html:100` is **live**; `:79` is the dead duplicate — the `[M]` is inverted | **§8.2** (corrected in full, with `getDisplayOptions`'s read chain and the `default_source` value), **§9.2**'s *record* bullet, **§18** (this table replaces the ask), **§5.12** (the generalised lesson: reachability needs *consumers*, plural) |
| **C** | §16.11 is **six**, with the six/three row-note split | **§16.11** |

### What no longer needs asking

Every §18 item from the second draft was answered in the sign-off sections and is folded above or into §16. **Nothing in this plan is now waiting on an architect**, and the single open item (#2, the export patch) is a commitment with a version number rather than a question.

---

## 19. Coverage audit, both rounds

Extracted at claim-and-consequence granularity from all six documents — three reviews and three sign-off sections — each read in full, including the parts not headed "must change".

| review | distinct items | addressed | deliberately not taken | escalated | escalations now answered |
| ------ | -------------- | --------- | ---------------------- | --------- | ------------------------ |
| three-cad-viewer | 64 | 64 | 0 | 0 | — |
| ocp_vscode | 42 | 41 | 0 | 1 (§16.11) | 0 — still with that architect |
| ocp_tessellate | 52 | 51 | 1 (§16.10) | 2 (§16.12, §16.13) | **2 of 2** |
| **total** | **158** | **156** | **1** | **3** | **2, plus §9.1a** |

**Sign-off round**, applied in full:

| review | conditions | other items | applied |
| ------ | ---------- | ----------- | ------- |
| three-cad-viewer | 3 | 1 observation, 9 confirmations | **4 of 4** |
| ocp_tessellate | 1 | 2 notes, 1 withdrawal | **4 of 4** |
| ocp_vscode | 2 | 1 answer, 1 addendum | **4 of 4** |
| **total** | **6** | **6** | **12 of 12** |

**Every condition from all three sign-off sections is applied, and §18 lists each one against the section that applies it.** Nothing was declined this round: the one item declined in the first round (`normal_len`) was withdrawn by its author after verification.

**All three escalations to Bernhard are answered** (§0.2a): §9.1a fixes 4.x now, §16.12 puts the `DEFAULTS` reduction on ocp_tessellate 4.0.0, §16.13 assumes direct `to_ocpgroup` callers exist. He additionally supplied the authoritative `_splash` account, which superseded material in this plan *and* in the ocp_vscode architect's memory, and which left exactly one implementation detail `[?]` (§16.15). **Nothing is now open with him on this item.**

**The one item deliberately not taken** is ocp_tessellate's preferred resolution for `normal_len` (exclude it as not a config key). I took its alternative — a row with `lifetime = derived` — for a reason the review did not have in front of it, and §16.10 records the disagreement rather than dropping it.

**Two apparent contradictions between reviewers, neither of which is one.** Surfaced rather than averaged, per the rule that a real disagreement is Bernhard's to settle:

- **§1's item-8 sentence.** three-cad-viewer confirms *"item 8 takes nothing"* from its side; ocp_tessellate says the sentence is false. They are assessing different halves and both are right: the *codec surface* — the encoded-buffer format, `decodeBuffers`, `resolveInstances` — shares no vocabulary, code path or file with configuration, which is three-cad-viewer's claim; and `normal_len` flows from the tessellator's payload into `params` in `show.py`, which is ocp_tessellate's. §1's rewrite preserves both statements verbatim, so nothing needs settling. **Both architects were asked at sign-off whether this papers over a real conflict and both said it does not** — three-cad-viewer: *"the codec surface and `normal_len`'s payload→config flow are genuinely different halves, and the rewritten sentence says so"*; ocp_tessellate: *"neither has been papered over"*.
- **§9.1's "permanent exception".** ocp_vscode says the exception is not permanent because `toCamelCase` retires at item 10; ocp_tessellate cautions that the "fix it or carry an exception" argument generalises badly. Complementary rather than opposed, and both were folded — after which **Bernhard's §9.1a ruling made the exception itself moot**, since 4.x is fixed in the same commit. The corrections still earn their place: the first is why the decision rests on the merits of an unregressable one-line fix rather than on a mechanical necessity that did not exist, and **the second survives as policy in §9.2 precisely because the argument that prompted it has gone** — the next defect will not have a fix landing alongside it.

**One gap, now closed — and it turned out to be an error rather than a gap.** The three-cad-viewer architect referred the `viewer.html:100` question to ocp_vscode and the first review did not reach it, so I supplied an **[M]** with the mechanism. **The sign-off found that `[M]` inverted**: `:100` is the live fallback default and `:79` is the dead duplicate (§8.2). The premises were all true and the conclusion did not follow, because I decided reachability from one consumer without enumerating the others — the same error the ocp_vscode architect had made on `_splash` a round earlier, and the reason §5.12 now requires an unreachability claim to enumerate *consumers*, plural.

**Three `[A]` claims were corrected by their own owners**, each of whom fixed their memory rather than the plan (§0.1). Five memory files were touched across the three reviews: `project_notification_contract.md`, `project_options_and_state_axes.md`, `project_colors_and_defaults.md`, `reference_data_format.md`, and — newly written — `project_splash_flag_two_values`. **None of them, and no repository source, was modified by me.**





