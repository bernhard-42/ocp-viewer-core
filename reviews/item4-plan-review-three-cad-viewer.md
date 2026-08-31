# Item 4 plan review — three-cad-viewer architect

Reviewing `plans/phase1-item4-config-key-table.md` (511 lines, read in full) against three-cad-viewer at **v5.0.3**, working tree clean at `620c230`. Every claim below was re-derived from the source; no repository was modified.

---

## Verdict

**Agree with required changes.**

The plan is sound in its central decisions. §3's axis analysis, §4's generate-outbound/classify-inbound split, §5.12's extracted-versus-judged rule and §7.2's fixture-plus-version-stamp are all correct, and §5.12 in particular is the right answer to how the previous attempt failed. I would be content to see this implemented once the seven **must-change** findings below are folded in.

**The blocking question resolves against my memory, not against the plan.** `STATE_TO_NOTIFICATION_KEY` has **47** entries. I have corrected my memory. Details and method in F1.

Two findings are more serious than the count: **F2**, where the plan's §5.7 classification rule does not actually produce the answers §5.7 attributes to it, and **F3**, where the mechanism the whole item exists to fix is *quieter* than the plan believes — there is no warning at all on the path `studio_ao_intensity` actually travels. F3 strengthens the plan's motivation; F2 must be fixed before item 13 consumes the column.

---

## Answer to the blocking question (§16.1)

**47. The plan is right; my memory was wrong.**

Method — counted mechanically, scoped to the declaration and nothing else, which is the scoping failure that killed the discarded draft:

```
awk '/^const STATE_TO_NOTIFICATION_KEY/{f=1;next} /^};/{if(f)exit} f' src/core/viewer-state.ts | grep -c ': "'
→ 47
```

Per comment section: View 11, Render 6, Control 4, Clipping 9, Zebra 5, Studio 11, Animation 1 = **47**.

The derived claim is also right: `STATE_KEYS` (`viewer-state.ts:169-252`) has **76** entries, so **29** are absent from the map, and 47 + 29 = 76 exactly.

`project_notification_contract` has been corrected: the false "40 entries" is replaced with the measured 76/47/29, the per-section breakdown, and the 29 absent keys enumerated in full so the set cannot be mis-derived from prose again. The plan's §7.2 fixture may be built on 47.

**One correction to the plan's framing of the disagreement.** §16.1 says my memory implies "~24" absent keys. It implies exactly 29 — the list contained the collective phrase "all the `*Tool` visibility flags", which expands to six keys (`measureTools`, `selectTool`, `explodeTool`, `zscaleTool`, `zebraTool`, `studioTool`). So the memory's *list* was complete and correct and only its *count* was wrong. That distinction matters: the defect was a number I never measured, not a reading of the map. The remedy — enumerate, never summarise, when a count is downstream — is now applied in the memory.

I want the failure recorded plainly, because §0's grading scheme is what caught it: I published a bare integer with a `file:line` citation attached, and the citation made it look measured when it was not. **A number is not a mechanism either.** The plan was right to mark its own extraction as the suspect one and right not to assert I was wrong; had it deferred to the `[A]` grade instead, the fixture would have been built on 40 and §7.2's C3 would have silently skipped seven keys.

---

## Must change before implementation

### F1 — §16.1, §7.2: adopt 47

Covered above. `STATE_TO_NOTIFICATION_KEY` = 47, `STATE_KEYS` = 76, absent = 29. Remove the "40 vs 47" open question; cite the memory's corrected section. **Severity: blocking, now unblocked.**

### F2 — §5.7: the classification rule does not produce the classifications it claims

**This is the most serious design finding in the review.** I agree with all six of §5.7's *outcomes*. I do not agree that the stated rule yields them, and three of the six are justified by reasoning the rule does not contain.

The rule is: *a wire key may be accumulated iff (a) it is state-backed in `ViewerState` and (b) re-applying its last value to a different model is meaningful.*

Applying it literally:

| key | plan says | rule actually says | why |
| --- | --- | --- | --- |
| `explode` | "passes both" → state | **fails (a)** → event | there is no `explode` state key. `STATE_KEYS` has `animationMode` and `animationSliderValue`; `explode` is a derived boolean emitted directly (`viewer.ts:4489`) |
| `states` | "passes (a) **in spirit**" → state | **fails (a)** → event | tree state lives in `TreeModel`/`TreeView`, not `ViewerState`. There is no `states` state key |
| `activeTool` | "fails (a): the wire vocabulary is `ToolTypes`" | **passes (a)** | `activeTool` *is* a state key (`viewer-state.ts:246`). What differs is the vocabulary, which is not what (a) tests |

"In spirit" is precisely the move §0 exists to forbid, and here it is load-bearing for the column item 13 consumes. A rule that reaches the right answers by three different unstated routes will reach a wrong answer on the next key added.

The input set is wrong too. §2's *"Six wire keys are not state keys at all: `states`, `lastPick`, `selectedShapeIDs`, `activeTool`, `explode`, `tab`"* is false for two of the six, and it is my wording it inherited — see F7. Precisely: four are genuinely not state-backed (`states`, `lastPick`, `selectedShapeIDs`, `explode`); `activeTool` has a same-named state key carrying a *different vocabulary* (state holds the lowercase button name `"distance"`, the wire holds `"DistanceMeasurement"` — `display.ts:1840-1859`, `tools.ts:13-18`); and `tab` is fully state-backed as `activeTab` (`viewer-state.ts:278`) with a *second* direct producer at `display.ts:2221`. What is true of all six is that they are emitted by a **direct `checkChanges` call rather than by the state-notification adapter** — that is the property, and it is not the same property as "not a state key".

**Replacement rule.** Drop (a) — being a `ViewerState` key predicts nothing useful — and test round-trippability instead:

> A wire key may be accumulated into a status snapshot iff
> **(a′) it is round-trippable**: an inbound path exists that accepts *the same vocabulary and domain the wire emits*, and
> **(b) model-independence**: re-applying the last value to a different model is meaningful, possibly after a documented filter.

Re-running all six, each conclusion now following from stated mechanism:

- `selectedShapeIDs` — **(a′) fails**: output-only, no inbound path at all. (b) fails: the ids are paths into the previous model. → **event.**
- `lastPick` — **(a′) fails**: output-only. (b) fails. → **event.**
- `activeTool` — **(a′) fails**: three vocabularies, none equal — wire `ToolTypes`, state lowercase button name, Python `analysis_tool`. Not round-trippable. → **event.** (Same conclusion as the plan, now for the actual reason, and it is a reason this project has already been bitten by: `project_id_picking_migration` records dispatching on `state.get("activeTool")` instead of `enabledTool` as the "4c bug".)
- `explode` — **(a′) holds**: boolean out, `setExplode(flag)` in, same domain. (b) holds. → **state**, without needing a state key to exist.
- `tab` — **(a′) holds**: `ActiveTab` out, `setActiveTab` and `viewerOptions.tab` in, same domain. (b) holds. → **state.**
- `states` — **(a′) holds**: `setStates(Record<path,[f,e]>)` accepts exactly the shape `getStates()` emits. (b) holds **with the model-relative filter** the plan already names. → **state.**

This costs the plan nothing — same six answers — and it makes `class` largely *derivable* from `applied_by` plus one vocabulary-identity fact per row, which is a strictly better place for it than a judged column defended by prose.

**Required:** replace the rule in §5.7, correct the six-key characterisation in §2 and §5.7, and re-derive each row's justification from the new rule.

### F3 — §7.1 silence #1 and §2 bullet 6: the render path emits **no warning at all**

The plan says the first silence is *"dropped with a browser-console warning nobody reads (`studio_ao_intensity`)"*. It is worse than that, and the correction strengthens the case for item 4.

There are two option-filter paths, and they differ in loudness:

- **Constructor path** — `new ViewerState(options)` → `_applyOptions` → `if (!isStateKey(key)) { logger.warn('Unknown option "X" - ignored'); continue; }` (`viewer-state.ts:583-586`). **Warns.**
- **`render()` path** — `setRenderDefaults`/`setViewerDefaults` → `updateRenderState`/`updateViewerState`/`updateStudioState` → `_update` → `if (!isStateKey(key)) continue;` (`viewer-state.ts:628-630`). **Silent. No `logger` call on that branch at all.**

`studio_ao_intensity` is a *viewer* option. It travels `render()` → `setViewerDefaults` → `updateViewerState` → `_update`, fails `isStateKey`, and is discarded **without any console output whatsoever**. The warning the plan relies on never fires for it.

Only the display-options object, which passes through the `Viewer` constructor, produces the warning — and there the warning is mostly noise, because `canvas` and `gl` are legitimate `DisplayOptions` fields (`types.ts:296-298`) that are not state keys and so warn on every normal boot.

**Required:** restate §7.1 silence #1 as "silently discarded, with no diagnostic of any kind, on the `render()` path; the constructor path warns and is not the path config keys travel". Adjust §2 bullet 6 to attribute the warning to `_applyOptions` specifically. This makes §9.1's "fix it in item 4" argument stronger, not weaker: today the defect is undetectable at runtime by any means.

### F4 — §7.2: C1 is entirely subsumed by C2 as written

C1 is `option ∈ STATE_KEYS ∪ fields(iface)`. C2 is `option ∈ fields(iface)` ∧ `destination(iface) == group`. Whenever C2 holds, C1's union holds automatically. **C1 cannot fail unless C2 also fails**, so it is not an independent check, and §7.2's claim that *"C1 is the check that catches `studio_ao_intensity`"* credits the wrong check — C2 catches it.

This matters because the two checks are meant to be independent opinions and the plan sells them as such (§5.3: "a genuine second opinion on the same fact").

There *is* a genuinely independent check available, and it is the more valuable one, because it tests the **runtime** acceptance path rather than the compile-time one:

> **C1′** — for every row with a non-null `option` and `applied_by = options`: `option ∈ STATE_KEYS`, unless the row is on the documented strip-list.

That is exactly what `_update`/`_applyOptions` do — the runtime gate is `isStateKey`, *not* the TypeScript interface (F3). C1′ and C2 then genuinely disagree in both directions, which is what makes a second opinion worth having:

- `tab` is in `fields(ViewerOptions)` (`types.ts:388`) and **not** in `STATE_KEYS` — passes C2, fails C1′, and is the one legitimate exception, because `updateViewerState` strips it before `_update` ever sees it (`viewer-state.ts:673`) and `render()` applies it separately (`viewer.ts:1797-1806`). The strip-list has exactly one member today.
- The zebra keys are in `STATE_KEYS` (`viewer-state.ts:228-232`) and **not** in `fields(ViewerOptions)` — pass C1′, and pass C2 only if `iface = ZebraOptions` is recorded with `destination = viewer` (see F5).

**Required:** replace C1 with C1′, record the strip-list as data (one member, `tab`, with the citation), and move the "catches `studio_ao_intensity`" credit to C1′ — where it belongs, since the runtime gate is what actually drops it.

### F5 — §5.3: zebra keys are `group = viewer`, but **not** for the reason given, and `ViewerOptions` does not extend `ZebraOptions`

Confirming the conclusion and refuting the derivation.

The plan writes: *"Zebra and studio keys are **not** separate groups — they are `viewer`, because `ViewerOptions extends StudioModeOptions` and both families are carried in `viewerOptionKeys` [M]"*.

- **Studio half: correct.** `ViewerOptions extends StudioModeOptions` (`types.ts:320`), so studio fields are literally `ViewerOptions` fields.
- **Zebra half: the premise is false.** `ZebraOptions` is a **standalone interface** (`types.ts:392-403`). `ViewerOptions` does **not** extend it. The two are joined only in `CombinedOptions` (`types.ts:431-436`), which is not the type of any `render()` argument.

The conclusion survives on a different mechanism. `zebraCount`, `zebraOpacity`, `zebraDirection`, `zebraColorScheme` and `zebraMappingMode` are all `STATE_KEYS` members (`viewer-state.ts:228-232`), and `_update` filters by state key rather than by interface (F3). So a zebra key carried inside the `viewerOptions` argument **is applied**, and there is no separate zebra argument, no `updateZebraState`, and no other application path — the only other writers are the `viewer.setZebra*` setters, which are runtime calls, not options. Zebra settings are additionally deferred at render time: `render()` deliberately does not push them, and `enableZebraTool(true)` applies them on first activation (`viewer.ts:1812-1817`).

So: **`group = viewer` — confirmed. `iface = ZebraOptions` — and `destination(ZebraOptions) = viewer` must be recorded as an explicit datum**, because unlike `StudioModeOptions` it cannot be derived from an `extends` clause.

One consequence the plan should carry, since item 16 generates a TypeScript-facing whitelist: passing a zebra key inside a `ViewerOptions`-typed object literal **works at runtime but is a TypeScript error** (excess-property check, under this repo's `strict` + `exactOptionalPropertyTypes`). Any generated `.d.ts` or typed wrapper that types the third `render()` argument as `ViewerOptions` will reject exactly the keys the runtime accepts. That is a real defect in three-cad-viewer's public types, it is mine to fix, and I would rather fix it than have the core generate around it — see O2.

### F6 — §16.3: `new_tree_behavior` is a **display** option — Bernhard's ruling, and the renderer mechanism agrees

Bernhard has settled the placement (*"new_tree_behavior is a display option — whether the navigation tree behaves the default or the legacy way"*). My job here is only to confirm the renderer is consistent with that, and to establish whether the widget's contrary filing is a **defect** or merely **non-canonical**. It is non-canonical. The mechanism, traced end to end:

**Where the key lives.** `DisplayDefaults` (`viewer-state.ts:39`), `DISPLAY_DEFAULTS` default `true` (`:439`), the **Display block** of `STATE_KEYS` (`:180`), `DisplayOptions.newTreeBehavior?: boolean` (`types.ts:276`), the Display block of `ViewerStateShape` (`types.ts:454`). **Not** in `ViewerOptions`. No wire name — one of the 29 absent keys. The renderer's own section comment files it under Display, which is an independent third opinion agreeing with Bernhard (and is the free signal I recommend extracting, under "Would improve").

**What it drives.** Exactly one consumer, and it is a `state.get`, not an option read:

```
state.get("newTreeBehavior")            viewer.ts:1343 (buildInitialGroup) and :3446 (_rebuildTreeView)
  → TreeView ctor 9th arg `linkIcons`   treeview.ts:98, :109
  → new TreeModel(tree, { linkIcons })  treeview.ts:125
  → TreeModel.linkIcons                 tree-model.ts:78
```

with four effects: the icon set in `toggleNodeState` (`tree-model.ts:351`), two branches in the parent/child propagation (`:454`, `:465`), and the re-application in `TreeView._handleStateChange` (`treeview.ts:146`). `true` = the default behaviour, where toggling the faces icon also toggles edges. That matches Bernhard's description of the flag exactly.

**Path A — `displayOptions` (canonical). Works.** `new Viewer(display, options)` → `new ViewerState(options)` → `_applyOptions`, `isStateKey("newTreeBehavior")` is true → assigned to state (`viewer-state.ts:583-591`). Note `Display` itself **never reads `options.newTreeBehavior`** — there is no occurrence in `display.ts`, unlike `glass`/`tools`/`cadWidth`/`height`/`treeWidth`, which `Display` stores directly. So even on the canonical path the key is *purely* a `ViewerState` seed consumed later by `buildInitialGroup`.

**Path B — `viewerOptions` (the widget's placement). Also works, and is exactly equivalent.** `render()` → `setViewerDefaults` (`viewer.ts:1442`) → `updateViewerState` → the destructure at `viewer-state.ts:673-681` strips only `tab`, the three clip normals and `position`/`quaternion`/`target`, so `newTreeBehavior` falls into `...rest` → `_update` → `isStateKey` true → assigned (`viewer-state.ts:628-643`). And it lands **in time**: `setViewerDefaults` is line 1442, `buildInitialGroup` line 1464.

The two paths are equivalent in every case I can construct, because the sole consumer is a single `state.get` that runs after both writers, and because both paths skip `undefined`/`null` identically (`viewer-state.ts:588` and `:631-637`). Nothing subscribes to the key (no `subscribe("newTreeBehavior")` anywhere), so there is no reactive path either could miss.

**Conclusion for item 16: the widget's placement is non-canonical, not broken. The correction is cosmetic** — it aligns the filing with the interface and with Bernhard's ruling, and it will not change any observable behaviour. It should not be reported to cad-viewer-widget as a bug. The general reason is F3: `_update` gates on `isStateKey`, never on the TypeScript interface, so *any* state key routed through the "wrong" options object still lands. That is also why three placements coexisted without anyone noticing.

**Table values: `group = display`, `iface = DisplayOptions`, `wire = null`, `status = false`.**

**On the third copy, `viewer.html:100` — I can bound it but not close it.** From the renderer's side there is no mechanism by which an entry in ocp_vscode's `viewerDefaultOptions` could be read *other than* by ocp_vscode placing it into the object it passes as `render()`'s third argument; the renderer sees only its constructor options and the three `render()` arguments. So the renderer-side consequence is fully determined by ocp_vscode's assembly loop: if that loop copies only keys listed in `viewerOptionKeys` and `new_tree_behavior` is not among them, the entry is definitively dead; if it copies the object wholesale, the entry is live and behaves as Path B. **That last step is the ocp_vscode architect's to confirm, not mine** — I have no basis to assert which, and the plan should attribute it accordingly rather than to me.

**§9.4 and §13 should be updated:** `new_tree_behavior` leaves the disputed set, its `known_divergence` field is unnecessary, and §13's commit 6 should no longer expect the equivalence test to fail on it — leaving `studio_ao_intensity` as the single expected failure. `zscale_tool` is likewise closed and is out of the table's domain entirely (Bernhard: it is a GDS/chip tool, not a CAD one), so §16.6 and §9.4's second dispute both go away and §8.3's "one key found by writing this section" needs rewording — with both disputes resolved, §9.4 has no members left and the `known_divergence` mechanism is needed for exactly one row.

### F7 — §2 and §10.3 family 5: two `[A]` citations to me are unfaithful, and both inherited my own imprecision

Checked all eight §2 attributions plus the §5.7, §7.2 and §15 leans. Six are faithful and exact — I verified `types.ts:388`, `viewer-state.ts:135`/`:251`/`:278`, `viewer.ts:1364-1366`, `viewer.ts:826-867`/`:1134`/`:1770-1787`, `measure.ts:404`/`:334`, `tools.ts:215-234`, `viewer-state.ts:580-593` and §7.2's `tab`-is-not-a-state-key claim. Two are wrong, and in both cases the plan faithfully reproduced a heading in my memory that was itself imprecise. I have corrected both memories; the plan needs the corrected wording.

1. **§2 bullet 5 — "Six wire keys are not state keys at all".** False for `activeTool` and `tab`. Correct statement in F2. My heading read "Wire keys that are NOT state keys"; it now reads "Wire keys with no state-adapter producer", with the three-way distinction spelled out.

2. **§10.3 family 5 — "note these are re-reported on every paint and are not state-backed [A]"**, of `position`/`quaternion`/`target`/`zoom`. False: all four **are** `STATE_KEYS` members (`viewer-state.ts:219-222`). The accurate fact is sharper and more useful to item 13:

   > They are `ViewerState` keys that are **never notified from state and never written back from the camera.** `updateViewerState` is their only writer (`viewer-state.ts:700-714`); the camera setters mutate the camera and call `update()` with no `state.set` (`viewer.ts:3199-3301`); and the wire values come from the live `Camera`/`Controls` (`viewer.ts:1035-1043`). So **`state.get("position")` holds whatever the embedder passed at the last `render()`, forever**, and diverges from the wire on the first orbit.

   Item 13 must read camera values from the wire or from `getCameraPosition()`/`getCameraQuaternion()`/`getCameraTarget()`/`getCameraZoom()` — **never** from `viewer.state`. If the plan wants a `[A]` here, cite that instead.

---

## Answers to the remaining §18 questions

### §3 — the six axes, and the two exclusions

**The axis inventory is correct** and the worked example is exact. Three specific rulings:

**Axis 2 excluded from the table, fixture only — agree, and the second reason is the strongest one.** "Nearly equal is exactly the shape that invites a reader to treat one as the other" is the correct diagnosis of how the discarded draft declared `tab` broken. One refinement: the plan's *first* reason ("nothing in the contract ever transmits an axis-2 name") is true of the wire but understates axis 2's runtime role — **axis 2 is the runtime acceptance gate** (`isStateKey`, F3), so it is not merely a shadow of axis 1, it is the thing that decides whether an option survives. That makes keeping it in the fixture *more* important than the plan argues, and it is what C1′ (F4) tests. Excluding it from the table stays right.

**Axis 4 excluded — strongly agree, and I can add renderer-side evidence the plan does not have.** The plan's case rests on ocp_vscode's dispatch being non-uniform. The setters are non-uniform *in arity and identity* too, which is a second, independent reason:

- `setClipNormal(index, normal, value, notify)` (`viewer.ts:4213-4222`) — **one setter serves three wire keys** (`clip_normal_0/1/2`), distinguished by an argument, and it writes the *slider* as well, so `clip_normal_i` and `clip_slider_i` are not independent through it (`viewer.ts:1736-1739`).
- `setGrid(action: string, flag, notify)` (`viewer.ts:2384-2390`) — takes an **action string plus a flag**, then reads the resulting 3-tuple back off the grid helper to write state. The wire key `grid` is a `tuple3<bool>`; its setter's signature resembles nothing of the sort. A separate `setGrids([a,b,c], notify)` also exists (`viewer.ts:2405`).

A `setter` column would be a lie for four wire keys before anyone even reaches the dispatch. (I checked one tempting extra example and it does *not* hold: `setOrtho` is a plain delegation to `switchCamera`, `viewer.ts:3165-3167`, not a competing setter. Stating it so nobody re-derives it.)

**Axis 5 excluded — agree.** `shapes.studioOptions` is applied only from `render()`, behind `logger.warn`, with `notify=false` (`viewer.ts:1444-1452`, `viewer-state.ts:723-748`). Nothing in Python reaches it. On §16.7 (should the core *refuse* it): **no** — refusing would be the core policing a renderer-internal deprecation it does not own, and the renderer already handles it correctly. If anything should change it is that three-cad-viewer eventually deletes the branch, which is my call and not item 4's.

### §5.7 — see F2. Rule refuted, conclusions confirmed, replacement supplied.

### §5.9 / §16.4 — the defaults framing, and `relative_time`

**The framing "a disagreement is a finding, not a value to encode" — agree, unreservedly.** It is the correct policy and §5.9's "the generator reports every disagreement it finds; it does not silently pick one" is exactly right.

**But the evidence cited for it is not mine to give.** §5.9 says *"The three-cad-viewer architect has already found several such disagreements between the TSDoc and the code (`reference_docs_vs_code_drift`: …)"* and offers it in support of a claim about **`viewer.html`'s** default block. My drift memory establishes disagreements *within three-cad-viewer* — TSDoc versus `ViewerState`, and `Data Format.md` versus `ViewerState`. It says nothing whatever about `viewer.html`, which is not a file I have read. Used as evidence for the general proposition "hand-kept second copies of defaults drift in this ecosystem", it is fair and I stand behind it. Used as evidence that `viewer.html` specifically disagrees, it is a citation to a file that is silent on the question. **Required (minor):** reword to make it support the general proposition, and let the ocp_vscode architect supply the `viewer.html` evidence.

For the record, the five drifting studio defaults are TSDoc-versus-code within `types.ts`/`viewer-state.ts`: `studioEnvIntensity` (TSDoc 0.5, actual 1.0), `studioShadowIntensity` (0 / 0.5), `studioShadowSoftness` (0.3 / 0.2), `studioAOIntensity` (0 / 0.5), `studioTextureMapping` ("triplanar" / "parametric"), plus `treeWidth` (250 / 260). **The table's `default` column must be sourced from `ViewerState`'s defaults blocks (`viewer-state.ts:395-541`), never from the TSDoc** — the TSDoc is wrong in six known places. Worth stating explicitly in §5.9, because "three-cad-viewer's `ViewerState` default" is ambiguous to an extractor author who reaches for the doc comment.

**`relative_time` — classify as `event`.** It is the case that proves criterion (b) has to be a real test, because it passes (a′) cleanly:

- Round-trippable: out as `animationSliderValue / 1000` (`viewer-state.ts:320`, `:331`), in as `viewer.setRelativeTime(fraction)` which multiplies by 1000 (`viewer.ts:804-807`). Same 0–1 domain both directions. **(a′) holds.**
- **(b) fails.** Animation tracks are per-model, bound to `nestedGroup.groups[selector]` at `addPositionTrack`-time; `clear()` disposes the animation and sets `animationMode: "none"` (`viewer.ts:1181-1185`), and `render()` calls `animation.cleanBackup()` (`:1454`). After a new model there is nothing to position.

And the failure mode is not inert, which is the part item 13 needs. `Animation.setRelativeTime` early-returns without a `clipAction` (`animation.ts:296-297`) — safe — but `Viewer.setRelativeTime` writes `state.set("animationSliderValue", fraction * 1000)` **unconditionally afterwards** (`viewer.ts:806`). So replaying a stale `relative_time` into a fresh model moves no geometry but *does* write state, which fires the notification adapter and **re-emits `relative_time` back onto the wire**, where an accumulating snapshot will absorb it again. A stale animation position would become self-sustaining. → **`event`, `lifetime = transient`.** §16.4 closed.

### §16.5 — `studioAOIntensity` has a real effect, conditional on studio mode

Mechanism confirmed; the visual confirmation remains Bernhard's.

- The value is consumed **only** by the studio composer, which exists only in studio mode. On studio entry: `const aoIntensity = state.get("studioAOIntensity"); this._composer.setAOIntensity(aoIntensity); this._composer.setAOEnabled(aoIntensity > 0);` (`studio-manager.ts:268-271`).
- `setAOIntensity` writes `_n8aoPass.configuration.intensity` (`studio-composer.ts:284-285`). The pass is constructed with a hardcoded `intensity = 1.5` and `enabled = false` (`studio-composer.ts:194`, `:199`), both overridden at entry.
- **`0` disables the pass entirely** — `setAOEnabled(intensity > 0)`. So the value is not merely a scale; zero is a distinct off state. Relevant to §5.8's `domain` for this key.
- Live changes go through a subscription that **early-returns when studio is inactive** (`studio-manager.ts:470-472`), but the value stays in state and is picked up by the entry path at `:269`.

**Therefore:** setting it at `render()` time (which is what §9.1's fix enables) lands it in state and it takes effect **the first time studio mode is entered** — no re-`show()` needed for it to apply, contrary to what one might assume from §2's "no `studio_*` key can be changed without a re-`show()`" (that claim is about ocp_vscode's dispatch gap, item 10's problem, and remains true on its own terms). And §9.1(2) is confirmed exactly: `viewer.html:109`'s unread `0.5` matches `STUDIO_MODE_DEFAULTS.studioAOIntensity = 0.5` (`viewer-state.ts:528`), so it has no observable consequence.

A user testing the fix must **enter studio mode** and use a value far from 0.5 (try `0` and `2.0`) — at 0.5 the fix is indistinguishable from the bug.

### §7.2 — the export proposal: **accepted, with one condition and one correction**

**I accept.** I will export the state-key vocabulary from three-cad-viewer as an additive patch (5.0.4) when item 4 needs it. Reasons: the fixture-staleness risk is real and evidenced in this very repository, and C1′ (F4) is a runtime-gate check, so running it against the *installed* renderer is not a convenience but a correctness improvement.

**Correction to the cost.** The plan says "one line". `STATE_KEYS` and `STATE_TO_NOTIFICATION_KEY` are **module-private** — `viewer-state.ts` exports only `ViewerState` and three types (`viewer-state.ts:938-939`). So it is two lines per symbol (module export, then `index.ts` re-export), not one. Still trivial, still additive, still a patch.

**Condition, on the second half of the proposal — "a frozen record of the option-interface field names".** The option interfaces are TypeScript **interfaces**: erased at runtime, with no value to export. A hand-written array would be a second copy of the interface living inside three-cad-viewer — the exact drift the proposal exists to remove, merely relocated. A plain `as const satisfies readonly (keyof ViewerOptions)[]` does not fix it either: it catches a typo but **not an omission**, so a newly-added option field would silently fail to appear.

I will only ship it in the exhaustive form:

```ts
const VIEWER_OPTION_FIELDS: Record<keyof ViewerOptions, true> = { control: true, axes: true, /* … */ };
export const viewerOptionFields = Object.keys(VIEWER_OPTION_FIELDS);
```

`Record<keyof I, true>` is checked in **both** directions — a missing field and an extra field are each a compile error — so the compiler maintains the mirror. Five such objects (`DisplayOptions`, `RenderOptions`, `ViewerOptions`, `ZebraOptions`, `StudioModeOptions`). If that form is not acceptable, I would rather the core keep extracting the field lists from my source than that I ship an unenforced list.

**And keep the fixture regardless.** The export makes the checks *current*; only the re-extraction diff makes a rename *alert* somebody. With `STATE_KEYS` exported, C1′ would silently re-baseline against a renamed key and pass. §7.2's two mechanisms are complementary, not alternatives, and the plan should say so rather than describing the export as "strictly better".

I will also fix the `ViewerOptions`/`ZebraOptions` typing gap of F5 in the same patch, so that the exported field lists and the accepted runtime keys agree.

### §1 — the five scoping sentences

Only two are mine to judge. **Item 7 (inject)** and **item 9 (the kit)** are consistent with everything I have established; the `owner` column's `document`/`surface` split is a property of the key and needs nothing from the renderer. **Item 8 (codec) takes nothing** — I confirm this from my side: the encoded-buffer format (`{shape, dtype, buffer, codec}`) and the config surface share no vocabulary, no code path and no file. `decodeBuffers`/`resolveInstances` touch only `Shape` payloads. Keeping them apart is right, and §1's explicit refusal of "one table for everything" is the correct instinct.

---

## Would improve

- **§5.8 `domain` for `studioAOIntensity`** — record that `0` is a distinct disable, not the low end of a scale (`studio-manager.ts:271`). The same is true of `studioShadowIntensity` (`0` = off, per `Data Format.md:760`, which agrees with the code here). An item-14 slider that treats these as plain 0–3 ranges will present "off" as "very faint".
- **§5.8 `type` for the clip normals** — `clipNormal0/1/2` are `Vector3Tuple` inbound (`types.ts:344-348`) and are converted to `THREE.Vector3` in state (`viewer-state.ts:689-697`), then back to arrays for the wire by the adapter (`viewer.ts:429-431`) and, separately, by `getAllNotifiable` (`viewer-state.ts:828-830`). **Two independent implementations of the same conversion.** If item 4's `type = vector3` is to mean anything, it should note that the renderer's state representation is not the wire representation for exactly these three keys — the only such case.
- **§5.7 / item 13, a related trap not in the plan** — `ViewerState.set`'s change detection is `===` or elementwise array comparison (`viewer-state.ts:337-343`, `:613`). A `THREE.Vector3` never compares equal to another, so **every** `setClipNormal` notifies even when the numbers are identical. An accumulating snapshot will see `clip_normal_i` churn on values that never changed. Harmless for correctness, noisy for any change-driven UI, and worth a note on those three rows.
- **§8.3 coverage** — when the extractor pulls `STATE_KEYS`, have it also record the **section comments** (`// Display`, `// Render`, `// Viewer`, `// Zebra`, `// Studio`, `// Runtime` — `viewer-state.ts:170-251`). They are the renderer's own filing of each key into a destination family and are a free third opinion on `group`, independent of both the interface (C2) and the key set (C1′). That is how F6 was settled in one step.
- **§10.3 family 6** — `states`' `applied_by` is `code`, and the code is `Viewer.setStates` → `treeview.setStates` (`viewer.ts:3367-3370`, `treeview.ts:753`). Two behaviours belong in that row's notes: the batching the plan already knows about, and that `Viewer.setState`'s `notify=false` argument **does not suppress the `states` notification** — `treeview.setState` calls the notification handler unconditionally (`treeview.ts:740`), so `notify` gates only the camera-level `update()`. A host that sets states quietly will still receive a `states` echo.
- **§15, risk 2** — the drift evidence would be stronger with the count: `Changes.md` has no v5.0.3 entry *and* the tree is three commits ahead of `origin/master`, so the shipped changelog does not describe the installed code. That is the same class of failure as a stale fixture, in the same repository, right now.

---

## Memory files touched

- **`project_notification_contract.md`** — corrected the false "40 entries" to the measured **76 / 47 / 29** with the per-section breakdown, the method, and the 29 absent keys enumerated in full; retitled and rewrote "Wire keys that are NOT state keys" → "Wire keys with no state-adapter producer" with the three-way distinction (F2/F7); corrected the camera section's "not state-backed" heading and added the `state.get("position")` staleness trap (F7); added the `clip_slider_*` second producer.
- **`project_options_and_state_axes.md`** — added the `_applyOptions`-warns / `_update`-silent asymmetry, the `isStateKey`-not-the-interface runtime gate, and the `ZebraOptions`-is-not-extended fact (F3/F5).

No repository source was modified, and I did not edit the plan.

---

# Sign-off — second draft (776 lines), 2026-08-10

Read in full: §0.1/§0.2a/§0.3 first, then every section my 64 items touched, then §16, §18 and §19. Verified in the document, not taken on trust; the load-bearing claims were re-derived from the source again.

## Verdict: **sign off with conditions**

All 64 items landed, and — the thing this round exists to catch — they landed as **substance, not summary**. The three I checked hardest for the summary-not-substance failure all survived intact:

- **F3 is not softened anywhere.** The only occurrence of "browser-console warning nobody reads" in the whole document is §7.1's own quotation of the first draft, immediately corrected. Every other mention (§0.3, §2, §7.1, §9.1) carries the two-path mechanism with `viewer-state.ts:583-586` versus `:628-630` and the conclusion *"undetectable at runtime by any means"*.
- **F2's rule is genuinely replaced, not patched.** §5.7's table re-derives all seven keys from stated mechanism, `"in spirit"` is gone, and §5.12 actually moves the column: *"judged columns are now `lifetime`, `owner`, and (b)-of-`class`"*. The structural gain — the reason to adopt the rule rather than merely fix the outcomes — was the part most at risk of being dropped, and it is the part §5.12 implements.
- **F5's conclusion survives on the replacement mechanism, not the refuted one.** §5.3 states the studio half is derivable from `extends` and the zebra half is not, and makes `destination(ZebraOptions) = viewer` an explicit datum for exactly that reason.

Spot-checked and confirmed exact against the source: the section comments are at `viewer-state.ts:170, 188, 196, 227, 233, 245`, inside the cited `:170-251`; `normalLen` is a `RenderOptions` field (`types.ts:316`), a `STATE_KEYS` member (`:195`, in the Render section), default `0` (`:459`) — so §7.4's renderer-side basis is correct and the section comment independently confirms `group = render`.

The three conditions below are small, and **none of them blocks commits 1–3.** Two are corrections to text; one is my own commitment being recorded completely.

## Condition 1 — the C1′/C2 "both directions" claim is overstated, and the error is mine

§7.2 asserts C1′ and C2 *"genuinely disagree in both directions"* and offers two bullets. Only the first is a disagreement.

- `tab`: in `fields(ViewerOptions)` (`types.ts:388`), not in `STATE_KEYS` → **passes C2, fails C1′.** A real, live, one-member direction.
- The zebra keys: in `STATE_KEYS` (`viewer-state.ts:228-232`), not in `fields(ViewerOptions)` — but with `iface = ZebraOptions` recorded, `zebraCount ∈ fields(ZebraOptions)` and `destination(ZebraOptions) == viewer`, so they **pass both**. That is agreement contingent on a datum, not disagreement.

The plan reproduced my wording faithfully; the imprecision is mine, and it is the same pattern as F7 — a phrase that reads as a demonstration and is not one. The substance is unharmed, because the two checks *are* independent: each catches a class of error invisible to the other. The honest statement:

> C1′ tests the runtime acceptance gate (`isStateKey`), C2 the compile-time interface. On today's correct data they disagree in one direction — `tab` — and the second direction is reachable only by a **mis-filed `iface`**: a zebra key recorded as `iface = ViewerOptions` passes C1′ (it is a state key) and fails C2 (`zebraCount ∉ fields(ViewerOptions)`). That mis-filing is the natural error, since ocp_vscode carries zebra keys in `viewerOptionKeys`, and catching it is precisely what C2 is for.

Replace the second bullet with that. It is a better argument for keeping both checks than the one it replaces.

## Condition 2 — (a′)'s domain half needs `wire_repr` to be derivable, and the schema already has the field

§5.12 claims `class` is mostly derived because *"(a′) is decidable from two extracted facts"*. The first fact — does an inbound path exist — is `applied_by ≠ none`, cleanly extracted. The second — does the inbound domain equal the wire's — is **not** extractable as the schema currently stands, because a row carries one `domain`, and deciding `activeTool` requires comparing two.

This is again my wording reproduced, and it is fixable without adding a column, because §5.8's `wire_repr` already is the two-domain field. The rule that closes it:

> **`wire_repr` absent** → the domains agree → (a′)'s domain half holds.
> **`wire_repr` present *with* a named decoder** → round-trippable after decoding → holds.
> **`wire_repr` present *without* a decoder** → **not round-trippable** → `class = event`.

Checked against all eight classified keys: `selectedShapeIDs` and `lastPick` fail on `applied_by = none`; `activeTool` has `wire_repr = ToolTypes` (`tools.ts:13-18`) and **no decoder anywhere**, which is exactly why it is broken today, → event; `explode`, `tab`, `states` have no `wire_repr` → state; `relative_time` has none either (both sides are 0–1) → (a′) holds and it fails on (b), which is the outcome §5.7 already reaches; and `collapse` has `wire_repr = int→Collapse` **with** the decoder at `config.py:688-693` → round-trippable → state. Correct on all eight, and it makes §4's inbound-value decoding and §5.7's classification the same fact rather than two.

**One sequencing consequence for §10.3 and §13:** `class` is now derived from `domain`/`wire_repr`, and `type` remains judged. So within each family commit, `domain` and `wire_repr` must be filled **before or with** `class`, never after — otherwise `class` is computed from an empty domain and silently defaults to "domains agree". Worth one sentence in §13's commit-4 description.

## Condition 3 — the export: confirmed, with one addition and one cost stated on the record

§7.2 and §16.2 state my position correctly and completely: accepted as an additive patch (5.0.4) when item 4 needs it; **two lines per symbol**, not one, since `viewer-state.ts:938-939` exports only `ViewerState` and three types; the option-interface half ships only as `Record<keyof I, true>` with `Object.keys` exported, because `as const satisfies` catches a typo but not an omission; five such objects; and — the correction that matters most — **fixture and export are complementary, not alternatives**, because the export makes the checks *current* while only the re-extraction diff makes a rename *alert* anybody. §7.2 line 384 also correctly records that the `ViewerOptions`/`ZebraOptions` typing fix ships in the same patch.

**I am committing to ship it.** Two things to add to the record:

1. **`STATE_TO_NOTIFICATION_KEY` goes in the same export.** The plan says "the state-key vocabulary", which is ambiguous, and C3 reads that map. The same argument that justifies exporting `STATE_KEYS` for C1′ justifies exporting the notification map for C3, and there is an asymmetry worth naming: the **wire names are already a de-facto public contract** — every host depends on them — so exporting the map formalises something that is true anyway, whereas exporting `STATE_KEYS` newly promotes an internal to a contract.
2. **The cost of (1)'s second half, accepted deliberately.** After 5.0.4, renaming a `ViewerState` key becomes a **breaking change by contract**, not merely an accident that happens to break a snapshot. Today three-cad-viewer is free to rename internal state keys because they are not the wire vocabulary. I accept that constraint — it is the price of the checks running against the installed renderer — but it belongs in three-cad-viewer's own release notes for 5.0.4, and I will put it there rather than let it be discovered later.

Nothing would change my mind short of the exhaustive form being refused, in which case §7.2 already records the fallback: the core keeps extracting from source rather than my shipping an unenforced list.

## Confirmed without conditions, from §18's list

- **§5.7** — the rule as written and all seven re-derivations, including `relative_time` as `event`/`transient` and the self-sustaining re-emission via `viewer.ts:806`. Confirmed.
- **§7.2** — C1′, C2, C3 as stated; the strip-list as data with `tab` its only member and `viewer-state.ts:673` its citation; fixture-plus-export complementary. Confirmed, subject to Condition 1's wording fix.
- **§5.3** — `destination(ZebraOptions) = viewer` as an explicit datum, and the deferred-application note (`viewer.ts:1812-1817`). Confirmed.
- **§2** — the corrected six-key characterisation and the corrected camera-quartet facts, as restated. Confirmed; both now say what my memory says after I fixed it.
- **§7.4 / §16.10** — the *renderer-side basis* for keeping `normal_len` a row is exact, verified above. Whether the decision is right is ocp_tessellate's to press; the facts it rests on are correct, and I have no objection from my side.
- **§1's five sentences** — item 8's rewrite preserves both my statement and ocp_tessellate's without papering over a conflict. §19 asks whether I think it does; **I do not.** The codec surface and `normal_len`'s payload→config flow are genuinely different halves, and the rewritten sentence says so.
- **§3** — axis 2 as the runtime acceptance gate, and axis 4's two independent exclusions including the `setOrtho` negative result recorded so nobody re-derives it. Confirmed.
- **§8.2** — `new_tree_behavior` non-canonical rather than defective, not to be bug-reported, correction cosmetic; and `viewer.html:100` correctly re-attributed to **[M]** and routed to the ocp_vscode architect rather than to me. Confirmed.
- **§9.1 / §16.5** — the studio-mode mechanism and the test instructions (`0` and `2.0`, because at 0.5 the fix is indistinguishable from the bug). Confirmed.

## One observation, not a condition

§0.1 draws the right lesson from my defect and states it as a schema rule (*"a count is judged unless its enumeration travels with it"*). Conditions 1 and 2 above are the same failure in a different costume: a phrase that **reads as a demonstration** — "disagree in both directions", "decidable from two extracted facts" — where the demonstration was never actually run. Both were mine, both were reproduced faithfully, and neither was caught by the citation being correct, because the citations *were* correct.

So the rule generalises usefully: **an assertion of a property is judged, not extracted, unless the instance that exhibits it travels with it.** A count needs its enumeration; a claimed disagreement needs the pair that disagrees; a claimed derivation needs the two facts it derives from, named. That is worth adding beside §0.1's sentence, because it is the same defect and §5.12's evidence discipline does not currently catch it — evidence attaches to columns, and these were claims in prose.

## Memory

No further changes this round. The three files corrected during the review round (`project_notification_contract.md`, `project_options_and_state_axes.md`, `project_tree_states_machinery.md`) already carry everything established here. The 5.0.4 breaking-change note of Condition 3 goes into three-cad-viewer's release notes when the patch ships, not into memory now.

No repository source modified; the plan not edited.
