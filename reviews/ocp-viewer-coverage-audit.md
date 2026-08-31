# Coverage audit: requs.md §7 against reviews/ocp-viewer-architecture-review.md

Audited 2026-08-07. Scope: every substantive claim in the review's Verdict, Findings 1-10, Design qualities, Could not verify, and all nine Recommended changes, checked against `requs.md` lines 474-567 (`### 7. OCP VS Code integration` through the end of Not in scope). Every line citation that requs.md copied from the review was spot-checked against the cited source file.

**52 items checked: 45 covered, 4 partial, 2 absent, 1 contradicted.**

## CONTRADICTED

**C1. The viewer.html function count (finding 7).** requs.md:549 still says "Of its seventeen functions only `getSize`, `normalizeWidth`, `normalizeHeight`, `send` and `debugLog` are host-specific" and then appends the review's correction as "That census counted named functions only". The review measured 16 named functions plus two anonymous handlers, 18 `function` tokens in total ("has **16 named functions** plus two anonymous `function` handlers (18 `function` tokens; the plan says seventeen)", review line 68), and I re-measured: `grep -c "function "` on `ocp_vscode/templates/viewer.html` returns 18. "Seventeen" matches neither count, and the appended clause makes the sentence self-inconsistent — a named-only census would say sixteen. Fix: "Of its sixteen named functions (eighteen counting the two anonymous handlers) only ... are host-specific". Cosmetic in weight, but it is the one place requs.md still asserts a number the review refuted.

## ABSENT

**A1. The Comms command vocabulary and the full Comms surface (finding 1 assessment, review line 17; Design qualities "Well-definedness", line 109).** The review: the command vocabulary the four Comms carry — `status`, `config`, `screenshot`, `set_relative_time`, `clear`, `ui`, `animation`, `backend_response` (dispatched at `src/controller.ts:206-253`, `ocp_vscode/standalone.py:358-467`, `viewer.html:692-922`) — "is itself shared semantics and must be specified in `ocp-viewer` as the interface each Comms implements, even though every transport is per-host. The plan names only `status()`; the rest should be named with it." requs.md names only `status()` on Comms (requs.md:541) and nowhere lists the command set or the four-function surface (`send_data`/`send_command`/`send_backend`/`send_config`, already implemented twice with deliberately matching signatures per review finding 1). Belongs in item 7 or the `status()` paragraph at requs.md:515: one sentence naming the full command vocabulary as part of the shared interface specification.

**A2. The `send_data` return-handle contract (finding 4 "Transport tail", review line 40; Design qualities "Well-definedness", line 109).** The review: the `_show` tail branch at `show.py:920-927` — jcq's `send_backend` takes `jcv_id=viewer.widget.id` and `_show` returns the viewer, VS Code's takes `port=` and returns `None` — "Injection dissolves the branch only if the Comms contract says `send_data` returns an opaque viewer handle that `send_backend` accepts and `Session.show` returns. That is a real interface decision, not a deletion — the plan should write it down." requs.md item 7 (requs.md:541) deletes the identifiers and injects the objects but never states this return-value contract; nothing else in the section does either. Belongs in item 7, one sentence: `send_data` returns an opaque viewer handle, `send_backend` accepts it, `Session.show` returns it (which is `None` for hosts with nothing to hand back).

## PARTIAL

**P1. The table's reach into cad-viewer-widget (finding 8, review lines 76-80).** requs.md:534 has the generation requirement — "the table is **generated into both Python and JavaScript from one source**, or it is simply the thirteenth hand-kept list" — which absorbs the "roughly a dozen" count. Missing is the review's concrete Phase-5 consequence: the widget's own hand-kept collections — the `display_args`/`viewer_args` whitelists (`cad_viewer_widget/utils.py:125-139, 142-208`), its ~60 synced traitlets (`widget.py:150+`), and `js/lib/widget.js`'s option assembly — are among those dozen, and the review specifies "plus, in Phase 5, the widget's trait filters" as generated artifacts. Item 15 (requs.md:557) says the widget's aligned policy copy is "expected to be replaced by the core" but says nothing about its key whitelists and trait filters being generated from the table. Add to item 15: the widget's `display_args`/`viewer_args` whitelists and trait sync filters are generated from the item 3 table at adoption, as Studio's settings already are in item 13 ("Settings is generated from the table's persistent rows").

**P2. The event-key list and the standalone's identical exposure (finding 9, review lines 84-88).** requs.md:533 has the partition ("a live status object may accumulate the keys that describe *state* and must not accumulate the ones that report an *event*") and names `selectedShapeIDs`. Missing, first: the review names "selection/tool keys (`selectedShapeIDs`, `activeTool`)" — `activeTool` should be named beside `selectedShapeIDs` as the second known event key. Missing, second: the review shows the standalone has the same stale-selection exposure today — it folds deltas into `self.status` (`ocp_vscode/standalone.py:435-439`) and forwards each delta batch to the backend (:440), "the same stale-selection exposure the Studio comment describes" — so the partition applies to item 14's adoption too, and item 14 (requs.md:556) is currently one bare line. One clause there, or in item 2, saying the standalone's server-side accumulation adopts the same key partition.

**P3. Animation in the shared/per-host table (finding 10 bullet 3, review line 94).** The review: animation "is absent from the shared column, the Session family and the JS extraction, yet it is a cross-host feature with wire presence in three hosts". Two of the three are fixed — `Animation` is in the Session family (requs.md:540) and the animation application is in the item 10 extraction (requs.md:549) — but the shared/per-host table at requs.md:512-513 still lists neither `Animation` in the Python shared column nor animation policy in the JS shared column. One word in each cell.

**P4. Show-signature alignment asserted as fact (Could not verify, review line 120).** requs.md:521 states "their show signatures and `viewer.html` logic have been aligned with ocp_vscode's - deliberately" and requs.md:565 leans on it: "the show signatures the other three call are aligned - which makes deriving the interface from their call sites a reading rather than a reconciliation". The review could not verify full alignment: "Spot-checked ... but no exhaustive parameter-by-parameter comparison was made. Answered by: the interface-derivation reading the plan itself schedules." requs.md does keep the derivation step (565, last sentence), which is the mitigating half; what is missing is the hedge — the alignment is spot-checked, not exhaustively verified, and the derivation reading at requs.md:565 is also the step that verifies it. One clause: "aligned (spot-checked; the derivation reading is the exhaustive check)".

## COVERED

1. Entanglement is import-time env-var rewiring in three modules, removed outright by injection (finding 1/4) — requs.md:541 "Delete every `port=`/`viewer=` pair and every `is_jupyter_cadquery` and `is_pytest()` branch".
2. The shared/per-host split matches the real call graphs (finding 1) — requs.md:508-513, the table.
3. Four genuinely different per-host settings sources (finding 1) — requs.md:512 "a settings source" per host; requs.md:541 `Config` "over a host-provided settings source".
4. Measurement backend shareable, subclass-and-return shape proven (finding 1) — requs.md:512 and :555 (`backend_logo.py` through the shared backend).
5. The tessellator is `ocp_tessellate` and the package boundary is named; ownership line drawn (finding 1/6) — requs.md:529 (item 0), :542 "**ocp_tessellate produces arrays, `ocp_viewer` decides the wire format**", "which is why ocp_tessellate is in scope for this item as well as for item 0".
6. Six blocking command connections per default show, not two (finding 2) — requs.md:540 "opens **six** blocking command connections, each a fresh websocket (`ocp_vscode/comms.py:159-161`), not the two this plan claimed".
7. Session removes four of six as a side effect of design, stated as such (finding 2) — requs.md:540 "removes four of them without anyone optimising anything".
8. Kit asserts the per-show fetch count, one settings read and one status read (finding 2, rec 4) — requs.md:545.
9. Session is the right unit: one entry point, argument adapters, an accumulator, none host-specific (finding 3) — requs.md:540.
10. Extended globals inventory: `LAST_CALL`, `COLORMAP`, `LAST_BBOX`, `LAST_PATHS`, warning once-flags, comms port state (finding 3, rec 1) — requs.md:540.
11. `oc.FACE_COLOR`/`THICK_EDGE_COLOR`/`VERTEX_COLOR` writes as the limit of per-session isolation, upstream parameterization as prerequisite of the two-viewers property (finding 3, rec 1) — requs.md:529 (item 0, additive, shipped as 3.5.0, the `<3.5.0` ceiling refuses the bad pairing) and :540 "Until item 0 lands, 'two viewers in one process' is not delivered by this item alone ... a prerequisite and not a nicety".
12. Family extended with `remove_object`, `save_screenshot`, `set_viewer_config`, `reset_defaults`, `Animation` (finding 3, rec 1) — requs.md:540.
13. Import rewiring deleted outright; `is_pytest` sites dissolved by loopback Comms plus injected settings (finding 4) — requs.md:541, :545.
14. Capability branches (`cad_width`/`height`/`theme`, `show.py:351-375`) become owner-column table rows rather than resurfacing per host (finding 4, rec 3) — requs.md:534 "injection **relocates** that decision rather than dissolving it".
15. Success criterion broadened beyond imports to strings, messages and environment sniffing, kit-enforced (`show.py:1634`, `show.py:368`, `comms.py:40,320`) (finding 4, rec 8) — requs.md:541.
16. The `show_all` widget filter is a genuine behaviour needing a host-neutral answer, not a deletion (finding 4) — requs.md:541 last sentence.
17. `combined(status)` as a pure merge over an injected status value (finding 5) — requs.md:515, :541.
18. VS Code `status` answered from the extension's cache; all four transports are cached-state reads, the strongest form of the argument (finding 5, rec 9) — requs.md:515, quoting `src/controller.ts:163-166` and `:210-211`.
19. Staleness caveat kept: best-effort reapplication, stale status merged never depended on, Studio's freshness a property to keep not to use (finding 5) — requs.md:517.
20. Comms failure contract: one defined behaviour, dead-Comms conformance case, today's three answers cited (`comms.py:191-214`, `:236-242`, per-host exception) (finding 5, rec 4) — requs.md:545.
21. Studio has no status path yet; item 2 supplies the reply hop on the existing channel (finding 5/9) — requs.md:533 "`modelsock.py` only reads ... not a new channel".
22. `numpy_to_buffer_json` lives in `ocp_tessellate`, at `utils.py:233` (finding 6, rec 5) — requs.md:542.
23. Byte-exactness held by a test pinned against `numpy_to_buffer_json`, not by hoping (finding 6, rec 5) — requs.md:542.
24. The two walks own dtype coercion and alignment; `decode(encode(model))` extended to dtype identity and view alignment (finding 6, rec 5) — requs.md:542.
25. Widget's dormant binary encoder: unblocks, does not add; ipywidgets round trip still unmeasured and wanted before the item commits the widget to binary (finding 6, Could not verify 1) — requs.md:544.
26. Item 1's split verified: `decodeBuffers`/`resolveInstances`, `EncodedBuffer` seam, 23-line copy, serves three hosts once item 8 lands (finding 7) — requs.md:530-532.
27. Five host-specific named functions and the extraction list (finding 7) — requs.md:549.
28. The anonymous listener's policy — `ui` dispatch (`:765-910`), tree-state preservation (`:692-746`), animation application (`:133-164`, `:911-922`) — extracted as named functions with `send` injected (finding 7, rec 2) — requs.md:549.
29. Item 13's gains live in that listener; without extraction there is nothing to adopt (finding 7) — requs.md:549.
30. Size stays per host (finding 7) — requs.md:513 "the canvas, its size, its lifecycle".
31. Five overlapping lists plus `toCamelCase` replaced; `optionKeyOverrides` as the existing half-answer; silent-miss failure mode (finding 8) — requs.md:534.
32. Table generated into both languages from one source or it is the thirteenth hand-kept list (finding 8, rec 3) — requs.md:534.
33. Lifetime, owner and key-class columns (findings 4/8/9, rec 3) — requs.md:534.
34. State/event key partition; the review's most expensive catch named as such; `viewer.js:169-177` fix preserved (finding 9, rec 3/4) — requs.md:533.
35. Logo becomes one `ocp-viewer` asset replacing five copies; measurable splash follows from data (finding 10, rec 6) — requs.md:539, :555, goals bullet at :492.
36. `ocp_tessellate` in the versioning contract with an owner: `ocp_viewer` pins it at the item 0 floor, hosts inherit (finding 10, rec 7) — requs.md:525.
37. Shared `show_all` adopts the recursive drawability check (`kernel/build123d_studio/__init__.py:167-204`) over `show.py:1662`, documented as the one deliberate behaviour change (finding 10, rec 9) — requs.md:555.
38. Nothing over-engineered: separate distribution carried by the cross-talk receipt, kit as the only string-catcher, item 2 reuses an existing channel, versioning matches observed pins (finding 10) — requs.md:500, :502, :523, :533, :561.
39. Adoption order matches the measured dependency structure; jcq last; standalone credible first thin host (Design qualities) — requs.md:496, :551, :557.
40. Interface derived from the other three hosts' call sites before ours is implemented (Design qualities) — requs.md:504, :565.
41. Import-free `__init__` structurally necessary; measured sidecar costs quoted (Design qualities, Performance) — requs.md:539.
42. Studio loses an encode and a decode per show; `buffers.py` made avoidable (Performance) — requs.md:542.
43. ipywidgets memoryview lift kept open, not asserted (Could not verify 1) — requs.md:544 "Still not measured end to end, by me or by the review".
44. `WebviewPanel` checked rather than assumed; ArrayBuffer transfer kept undocumented-therefore-unused, #115807 not #148429 (Could not verify 3, Decided) — requs.md:559.
45. Historical measurements (2.63→0.78 s, 6.52→1.80 s, 2.2 MB) still presented as recorded measurements, which the review found nothing to contradict (Could not verify 2) — requs.md:498, :539.

## Non-per-item check 1: line citations copied into requs.md, verified against source

Every citation below was read in the cited file; all check out unless noted.

- `ocp_vscode/show.py:263-283` (requs.md:529): confirmed — the `oc.FACE_COLOR`, `oc.THICK_EDGE_COLOR`, `oc.VERTEX_COLOR` assignments into `ocp_tessellate.convert` sit at 264-283.
- `src/controller.ts:163-166` and `:210-211` (requs.md:515): confirmed — `onDidReceiveMessage` stores `this.viewer_message` when `msg.command === "status"` at ~163-166; the C-frame `status` command is answered with `socket.send(JSON.stringify(this.viewer_message))` at ~210-211.
- `ocp_vscode/comms.py:159-161` (requs.md:540): confirmed — `with connect(f"{CMD_URL}:{port}", close_timeout=0.05)` inside `_send`, a fresh connection per call.
- `ocp_vscode/comms.py:191-214` (requs.md:545): confirmed — both exception arms return the dummy dict containing `Collapse.ROOT` (an enum where consumers expect the wire value).
- `ocp_vscode/comms.py:236-242` (requs.md:545): confirmed — `send_command` calls `result.get(...)` on `_send`'s return, which is `None` on the outer exception path, giving the latent `AttributeError`.
- `ocp_vscode/comms.py:40` and `:320` (requs.md:541): confirmed — `from IPython import get_ipython` at 40; the `ZMQInteractiveShell` class-name sniff at 319-320.
- `ocp_vscode/show.py:368` (requs.md:541): line confirmed — the `print(f"Setting {k} cannot be set, it is determined by the VSCode panel size")` inside a `not is_jupyter_cadquery` branch. One wording nit: requs.md calls this "a capability sniff"; it is a host-naming user-facing *message* inside a capability branch — the review classed it under messages, and requs.md's own criterion sentence ("imports, strings, messages and environment probing") already has the right category, so only the label is loose.
- `ocp_vscode/show.py:1634` (requs.md:541): confirmed — `"cad_viewer_widget.widget" in str(obj.__class__)`.
- `ocp_vscode/show.py:1662` (requs.md:555): confirmed — `isinstance(obj, (list, tuple, dict))`, the permissive test.
- `ocp_tessellate/utils.py:233` (requs.md:542): confirmed — `def numpy_to_buffer_json` at 233.
- `cad_viewer_widget/utils.py:61` (requs.md:544): confirmed — `def to_json` walking `np.ndarray`s (with the `int32/int64/uint64 → uint32` coercion at 63-64).
- `cad_viewer_widget/widget.py:202` (requs.md:544): confirmed — `shapes = Dict(allow_none=True).tag(sync=True, to_json=to_json)`.
- `js/lib/widget.js:696` (requs.md:544): confirmed — the comment "decodes the b64 buffers and instance refs natively (like ocp_vscode)".
- `ocp_vscode/templates/viewer.html:671-923`, `:765-910`, `:692-746`, `:133-164`, `:911-922` (requs.md:549): all confirmed — `addAnimationTrack` at 133, `window.addEventListener("message", …)` at 671, the `data.type === "data"` tree-state capture beginning ~693 and ending ~746, the `data.type === "ui"` dispatch beginning ~765 and its key mapping ending ~909, the `data.type === "animation"` branch at ~911-922, the listener closing at 923. Also re-confirmed: `resources/viewer.html` and `ocp_vscode/templates/viewer.html` are byte-identical (`diff -q`).
- `kernel/build123d_studio/__init__.py:167-204` (requs.md:555): confirmed — `_can_draw`, recursive over list/tuple/dict contents, with the docstring explaining the divergence from ocp_vscode and the hung-viewer incident.
- `src/viewer/viewer.js:169-177` (requs.md:533): confirmed — the comment block explaining delta-only notification and the stale `selectedShapeIDs` re-measurement it prevents.
- `src/viewer.ts:56` / `:32`, `extension.ts:756` (requs.md:559): confirmed — `createWebviewPanel` at 56, the `vscode.WebviewPanel` field at 32, `registerWebviewPanelSerializer` at 756, and zero `registerWebviewViewProvider` across `src/*.ts`.
- `vscode-ocp-cad-viewer/pyproject.toml:30` (requs.md:529): confirmed — `"ocp-tessellate>=3.4.0,<3.5.0"` at line 30, the only ceiling in the ecosystem as claimed.
- requs.md:521's own checks: confirmed — exactly 7 `is_jupyter_cadquery` mentions in `config.py`, `is_pytest()` returning canned data at exactly two call sites (678, 701), and all five lists at `config.py:164/205/238/251/253`.
- requs.md:530's "23-line copy": `resolveInstances` in `src/viewer/rehydrate.js` measures ~25 lines with braces; the review itself judged "23-line" accurate to within the function braces, so no correction needed.
- One count that does not check out: requs.md:549's "seventeen functions" — see C1. Measured: 18 `function ` tokens in `viewer.html` (16 named + 2 anonymous).

## Non-per-item check 2: internal consistency of requs.md after the edits

- Numbering: Phase 0 runs 0-4, Phase 1 runs 5-9, Phase 2 runs 10-12, Phases 3-5 run 13-15, all sequential. Every cross-reference was resolved and points at the right item: item 0 (requs.md:525, :529, :540, :559 — ocp_tessellate globals/floor), item 1 (:550 — the additive split and its minor floor), item 2 (:517 reply hop, :533, :534 key-class finding), item 3 (:521, :533 — the table), item 4 (:521 — done upstream), item 5 (:500 — the move and re-export), item 6 (:529 — the same defect one package up), item 7 (:502, :521 — success criterion), item 8 (:532, :542, :544 — codecs/binary), item 9 (:502, :540 — kit, fetch count), item 13 (:539 logo, :549 gains, :555), item 15 (:521 — second reason spent). The renumbering that made Phase 0 begin at item 0 broke nothing.
- One stale sentence: requs.md:521 "items 3 and 7 stand exactly as written and are now the bulk of the Python work" — items 3 and 7 have since been amended with the review's corrections (owner and key-class columns; strings/messages/env-sniffing in the criterion), so "exactly as written" is no longer literally true. The sentence's point (the upstream alignment did not do the config work) survives; the wording could become "stand and are now the bulk of the Python work".
- One self-inconsistency: requs.md:549, the seventeen-vs-named-only clash — see C1.
- Markdown corruption at requs.md:542: "ocp*vscode's wire stays byte-identical; ours loses an encode \_and* a decode per show" — mangled emphasis markers from an edit; should read "ocp_vscode's wire stays byte-identical; ours loses an encode *and* a decode per show".
- Grammar glitch at requs.md:544: "It never fires, because since the alignment `shapes` arrives from `_show`/`_convert` already base64'd, so the walk meets strings" — a "because … so" double connective left over from an edit; meaning intact.
- No claim in one paragraph was found contradicted by another, beyond C1.

## Non-per-item check 3: Could-not-verify items now asserted as fact

- **Show-signature alignment: asserted as fact — flagged as P4.** requs.md:521 and :565 state the other hosts' show signatures "are aligned"; the review's Could-not-verify says this was spot-checked only, with the exhaustive check being the scheduled derivation reading. requs.md keeps the derivation step but presents the alignment as settled; it should carry the spot-checked hedge.
- ipywidgets memoryview lift: correctly kept open — requs.md:544 says "Still not measured end to end, by me or by the review … One live Jupyter round trip settles it … **before this item commits the widget to binary**".
- VS Code ArrayBuffer transfer: correctly kept open — requs.md:559 "undocumented is undocumented … it leaves the door ajar rather than shut". The locally verifiable halves (WebviewPanel, serializer, no WebviewViewProvider) are asserted and were re-verified here.
- Historical measurements (2.63→0.78 s, 6.52→1.80 s, 2.2 MB, 713 ms): still quoted as recorded measurements, which is what they are; the review found nothing contradicting them. No change needed.
- `~/Desktop/viewer-ecosystem.pptx`: still referenced at requs.md:478 as "Current design", not asserted as reviewed. No change needed.
