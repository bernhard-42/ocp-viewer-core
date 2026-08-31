# Item 4 plan review — ocp_vscode / vscode-ocp-cad-viewer architect

Reviewing `plans/phase1-item4-config-key-table.md` (511 lines, drafted 2026-08-10) against `vscode-ocp-cad-viewer` at `934e1fa` (4.0.2). Everything below was re-derived from source during this review; where I ran a script it is named so it can be re-run.

## Verdict

**Agree with required changes.**

The plan is sound in its architecture and unusually honest in its grading. Decisions 1–3 (§3 axes, §4 direction, §5 schema) are right, §5.12's extracted/judged split is the correct answer to how the previous attempt failed, and §7.2's fixture-plus-re-extraction is a better safeguard than anything currently in this ecosystem. §1's five scoping sentences are true as far as my repository is concerned.

Six things must change before implementation. Two of them are errors of fact about my codebase that the plan grades **[A]** and attributes to me, and one of those materially changes item 10's scope. One is a section built on a memory of mine that I have since retracted. The remaining three are places where the schema or a decision does not survive a case the plan itself lists.

---

## Must change before implementation

### F1 — §5.11, §9.1(3), §18: the "nineteen keys with `ui = false` while settable through `set_viewer_config`" is wrong in number, in composition, and in attribution

§5.11 states: *"Roughly 19 keys are `ui = false` while being settable through `set_viewer_config` **[A]**"*, and §9.1(3) builds on it: *"it is shared by all eleven `studio_*` keys plus `ticks`, `grid_font_size`, `deviation`, `angular_tolerance`, `default_color`, `modifier_keys`, `theme`, `timeit` and `control`"*, concluding *"fixing it for one key and not the other eighteen would be arbitrary"*.

**Measured** (`inspect.signature(set_viewer_config)` against the `data.type === "ui"` dispatch scraped from `ocp_vscode/templates/viewer.html:772-909`):

| set | count | members |
| --- | ----- | ------- |
| settable via `set_viewer_config` **and** no `ui` branch | **11** | the eleven `studio_*` keys, exactly |
| the plan's nine non-studio keys | 9 | **none is a `set_viewer_config` parameter** |

Three separate problems:

1. **Arithmetic.** 11 + 9 = 20, not 19. The plan says "nineteen" in §5.11 and §18, and "the other eighteen" in §9.1(3).
2. **Composition, and this is the one that matters.** Not one of `ticks`, `grid_font_size`, `deviation`, `angular_tolerance`, `default_color`, `modifier_keys`, `theme`, `timeit`, `control` is a parameter of `set_viewer_config` (config.py:334-391). They therefore **cannot** "post a message the browser drops" — there is no way to send them. Five of them (`ticks`, `grid_font_size`, `deviation`, `angular_tolerance`, `default_color`, `timeit`) *are* `set_defaults` parameters, none is in `CONFIG_SET_KEYS`, so `set_defaults` stores them in `DEFAULTS` and they take effect on the next `show()` — which is correct behaviour for show-time parameters, not a defect. `modifier_keys`, `theme` and `control` are settable from Python **at all** by neither function.
3. **Attribution.** This is graded **[A]** and sourced to me. My memory does not say it. `project_defects_and_open_questions` §2 says those keys have **no `ui` dispatch branch** — a weaker and different claim than "settable through `set_viewer_config` and dropped". The plan has silently upgraded a coverage fact into a behavioural one.

**Consequence.** Item 10's checklist is **11 keys, not 19**, and the other nine are not a gap at all. §9.1's "fixing it for one key and not the other eighteen would be arbitrary" survives — but only over the eleven studio keys, where it is a stronger argument, not a weaker one.

**What should replace it.** Split the single `ui` boolean into two facts, both extracted, neither judged:
- `ui` — does the live-set dispatch handle this key (the coverage fact §3 already defines).
- `live_settable` — is this key a `set_viewer_config` parameter.

Item 10's checklist is then exactly the predicate `live_settable ∧ ¬ui`, which evaluates to the eleven studio keys and needs no hand-maintained count. Keys that are `¬live_settable ∧ ¬ui` get a row that says "show-time only, by construction", which is a fact worth having and is currently being mis-recorded as a defect.

### F2 — §9.2 and §16: the `_splash` paragraph cites a memory of mine that I have retracted twice

§9.2 ends: *"That architect's memory explicitly says the `_splash` browser-side branches should not be deleted without asking, because whether they are leftovers or a guard someone intends to re-arm is not answerable from the sources."* §16's closing paragraph repeats it as an unresolved question.

That memory was wrong and has been withdrawn. It is answered now, and measured (`project_splash_flag_two_values`).

**What should replace it.** The mechanism, not a question:

> `_splash` is a host-owned session flag (`controller.ts:49`, cleared `:226-227`; `standalone.py:227`, cleared `:403-404`), injected into the `config` command reply at `controller.ts:126` / `standalone.py:379`. It reaches Python through `workspace_config()` → `combined_config()`, and — this is the part that matters to item 5 — **`params` inherits it**: `show.py:345-364` builds `params` from `conf.items()` excluding only `position`/`quaternion`/`target` (+ the surface keys), so `_splash` is carried through and can be `True`. Three live consumers read it in that state: `config.py:750` (skip merging the splash logo's status), `show.py:242-256` (force `Camera.RESET`), `show.py:376-381` (drop an explicit `reset_camera=` kwarg). `show.py:383` then overwrites it to `False` **on the last line before the payload is built**, so the key *is* transmitted to `viewer.html` in every model message, always as `False`. The two browser branches (`viewer.html:705`, `:766`) therefore never fire; they are the browser half of the same policy, receiving the field but never a true value — **not** dead code, and not a deletion question.

Proof that it is genuinely `True` mid-flight, since this is the part that reads as contradictory: with the host stubbed to report `_splash: True`, `show(b, reset_camera=Camera.KEEP)` emits `reset_camera: "reset"` on the wire; with the host past splash the same call emits `"keep"`. The `:378` guard is live.

The one observable defect to record instead of the open question: a `set_defaults(...)` issued before the first `show()` restyles the splash logo, because `:766` never returns early.

Nothing in §9.2's "record, don't tidy" policy changes — but its example is now a mechanism with a citation rather than an unanswerable.

### F3 — §10, §5.2, §5.6, §5.11: the schema cannot express `_splash`'s row

§10 lists `_splash` among the ~90-100 rows. Having now settled what it does, it does not fit:

| column | value it needs | can the schema say it? |
| ------ | -------------- | ---------------------- |
| `option` | none — it never enters an options object | yes, `null` |
| `group` | none — never reaches three-cad-viewer | yes, `none` |
| `applied_by` | read by **host-glue JavaScript** in `viewer.html`, which is neither `options`, nor `code` (which implies a renderer setter), nor `display-ctor`, nor `none` (it *is* applied, twice) | **no** |
| `wire` | not notified back → `null`; but it *is* transmitted outbound in the model config, and the schema has no outbound-payload column | **no** |
| `owner` | neither `document` nor `surface` — the host process owns it | **no** |
| `lifetime` | not `persistent`, not `session` (§5.5 defines `session` as code-set via `set_defaults`/a `show()` kwarg; this is host-set and flips once), not `transient` | **no** |
| `class` | neither `state` nor `event` — never in a status snapshot | **no** |

And no column at all expresses the property that makes it dangerous to relocate: **the value the core forwards is not the value the core received.**

This is a genuine test of §5's schema and it fails it. Two ways out; I recommend the second.

- **Add members** — `applied_by = "host-glue"`, `owner = "session"`, and an outbound-payload flag. This makes the schema carry a shape only one key has.
- **Refuse it a row (recommended)** and add a short, explicitly separate **protocol/handshake inventory** beside the table, for fields that cross the wire but are not configuration. `_splash` is its first member. It must be inventoried *somewhere* — items 5, 6 and 7 relocate every one of its three consumers, and a move that preserves the propagation but drops the `show.py:383` rewrite (or vice versa) puts the first `show()` after a viewer opens on the splash logo's camera — but it is not a config key and forcing it into the table costs four column extensions to model one thing.

Whichever is chosen, §7.4's reachability check needs to know about the category, or `_splash` will fail coverage.

### F4 — §4: inbound value translation exists today and the decision leaves it homeless

§4 decides *"Inbound is classified, not translated… the table contributes only classification."*

On **names** this is correct and I confirm it: `combined_config` does `wspace_config.update(workspace_filter(wspace_status))` (config.py:753) — a filter over identically-named keys, no rename anywhere. The one place a rename would be needed (`activeTool` → `analysis_tool`) is exactly where the feature is broken today, and §9.2 already records that under "Record". Consistent; no contradiction.

But there **is** an inbound *value* translation, and the core owns it:

- `status()`, config.py:688-693 — the viewer's **int** `collapse` → the `Collapse` enum via `COLLAPSE_REVERSE_MAPPING`, with a `warnings.warn` on an unknown value. This is a viewer→python decoding, not a host one.
- `workspace_config()`, config.py:723-726 — the **host's** string `collapse` → `Collapse`, and string `reset_camera` → `Camera[...upper()]`. Host-side; §5.8's "host decodings stay host data" covers these correctly.

§5.8's `domain` column says the table carries "the **core's** representation and names it". That handles the host decodings. It does not give the `status()` int→enum decoding anywhere to live, and §4's flat "not translated" implies it does not exist.

**What should replace it.** Amend §4 to *"inbound names are classified, not translated; inbound **values** are decoded, and the decoding is the core's"*, and give §5.8's `domain` an explicit wire-representation sub-field for the inbound direction, distinct from the host representations it already excludes. Otherwise item 6 will move `combined_config` and lose the `collapse` decoding — which fails silently, because an undecoded int is truthy and flows straight into `conf["collapse"] = collapse.value`, raising `AttributeError` on an int, or worse, passing through if the value happens to be an enum already.

### F5 — §5.6 and §15: the `owner` mechanism addresses one of the four host-naming sites its own risk bullet cites, and the refusal message cannot be per-host

Two problems, one small and one that affects the design's claim.

**(a) The refusal message is per-key, not per-host.** §5.6 says the core refuses a surface key *"using a **refusal message the host supplies**"* — singular. Today there are **two** categories with **two** different messages, and they are not interchangeable:

```
show.py:365-375
  cad_width, height  ->  "Setting {k} cannot be set, it is determined by the VSCode panel size"
  theme              ->  "Setting {k} can only be set in VSCode config"
```

`cad_width`/`height` are viewport geometry the panel computes; `theme` is a host *setting* the user configures. §5.6's prose — *"the value is a property of the viewport the host supplies"* — describes the first accurately and the second only by stretching. The mechanism must let a host supply a message **per key** (or per reason), or the relocation flattens a distinction the current code makes deliberately.

Note also that the two lists are not the same list: the `params` filter (`show.py:345-364`) excludes `cad_width`, `height`, `theme`; the kwargs loop (`:365-375`) splits those same three across two branches. A single `owns(key)` predicate reproduces the filter but not the split.

**(b) The mechanism addresses one of four.** §15's risk bullet cites four sites as evidence that item 7's criterion is broader than imports, and I confirm all four line references are correct:

| site | what it is | does §5.6 fix it? |
| ---- | ---------- | ----------------- |
| `show.py:368` | the user-facing "VSCode panel size" message | **yes** — this is §5.6's stated target |
| `show.py:1634` | `"cad_viewer_widget.widget" in str(obj.__class__)`, inside `show_all`'s exclusion chain | **no** — a drawability predicate, unrelated to config keys |
| `comms.py:40` | unconditional `from IPython import get_ipython` at module top | **no** — port discovery |
| `comms.py:320` | `get_ipython().__class__.__name__ == "ZMQInteractiveShell"` | **no** — port discovery |

§15 is not wrong to list all four as evidence of the *risk*. But the sentence *"§5.6's design puts the refusal message in the host precisely because `show.py:368` is where the last attempt at this leaked"* invites the reader to conclude the risk is mitigated, when three of the four are untouched by item 4 and belong to item 7's broader "inject don't identify" work.

There is also a **fifth** that §5.6 should claim explicitly because it is on the very branch being relocated: the branch is guarded by `not is_jupyter_cadquery` (`show.py:366`, `:371`), which is environment-sniffed host identity (`JUPYTER_CADQUERY`, `show.py:66`). An injected config object that answers `owns(key)` dissolves that guard naturally — a jupyter_cadquery config claims nothing — but only if the injection replaces the guard as well as the key set. The plan does not say so, and it is the strongest thing §5.6 actually achieves.

### F6 — §11: `CONFIG_UI_KEYS` is not referenced only by `ui_filter`

§11's first row: *"`ui_filter` | dies at item 5 | nothing — **it has no caller** **[M]**; `CONFIG_UI_KEYS` is referenced only by it"*.

**First half confirmed.** `ui_filter` is defined at config.py:665 and has **no caller** anywhere in the repository. `workspace_filter` (config.py:670) has exactly one, config.py:753.

**Second half is wrong.** `CONFIG_UI_KEYS` has two references: `ui_filter` at config.py:667, **and config.py:205**, where `CONFIG_WORKSPACE_KEYS = CONFIG_UI_KEYS + [...]` is built from it. Retiring `ui_filter` therefore does *not* free `CONFIG_UI_KEYS`; it survives until `CONFIG_WORKSPACE_KEYS` goes at item 7, which is what the table's last-but-one row already says. The correction is one clause, but the schedule in §11 currently implies a key list dies two items earlier than it can.

---

## Confirmed — no change needed

These are the §18 items I was asked to settle, and the plan is right about all of them.

**§8.1 — the duplicates, confirmed exactly.** By AST over `config.py` at `934e1fa`:

```
CONFIG_UI_KEYS         literal= 38  distinct= 38  dups=[]
CONFIG_WORKSPACE_KEYS  literal= 65  distinct= 61  dups=[ambient_intensity, direct_intensity, metalness, roughness]
CONFIG_CONTROL_KEYS    literal= 10  distinct= 10  dups=[]
CONFIG_KEYS            literal= 76  distinct= 72  dups=[ambient_intensity, direct_intensity, metalness, roughness]
CONFIG_SET_KEYS        literal= 39  distinct= 39  dups=[]
union of all five: 75 distinct
```

65/61 and 76/72 are exact, the four duplicate names are exact, and the union of 75 matches §10's "75 distinct Python config keys". The duplication arises because `CONFIG_WORKSPACE_KEYS = CONFIG_UI_KEYS + [...]` and the appended "render settings" block re-lists four keys already in `CONFIG_UI_KEYS`. **Set equality is the right test** and sequence equality would be wrong — not only because of the duplicates but because `CONFIG_KEYS`'s order is an artefact of concatenation order, which no consumer observes: every use is an `in` test (config.py:644, :656, :667, :672, :777). It was not recorded in my table; it is now (added to `project_config_key_table`).

**§9.3 and §16.8 — `tree_width`'s exclusion is deliberate, and there is commit evidence.** It is commented out of both the `params` filter (`show.py:358`) and the kwargs refusal list (`show.py:372`), by `743696a` — *"respect tree_width from VS Code config and make tree_width adaptable with show"* — which touched `show.py`, both copies of `viewer.html`, and `src/controller.ts` together. So `tree_width` is a `document` key by intent: settable per-`show()`, with the VS Code setting as its default. `viewer.html:577-585` acts on it (`if (_config.tree_width) … resizeCadView`), which is the other half of that commit. §16.8 can be closed and §9.3's **[M]** promoted, citing `743696a`.

**§5.6/§9.3 — `cad_width`, `height`, `theme` are the complete surface-key set today.** Confirmed by reading both lists; no other key is branched on the host in `_tessellate`. Subject to F5(a): they are one set in the filter and two categories in the refusal.

**§11 — nothing outside `config.py` imports the five lists.** Confirmed across `ocp_vscode` (the only hit is a comment at `show.py:411`), and across `jupyter-cadquery`, `cad-viewer-widget` and `build123d-studio` — no hits at all. Stronger than the plan claims: none of the five names is in `config.py`'s `__all__`, so `from ocp_vscode import CONFIG_KEYS` already fails today; only the explicit `from ocp_vscode.config import ...` form would work, and nothing uses it. The item 15 deletion is safe.

**§8.2 — the [M] inputs are exact.** `renderOptionKeys` = 7, `viewerOptionKeys` = 43, `optionKeyOverrides` = 3, read from `ocp_vscode/templates/viewer.html`. `resources/viewer.html` and the template copy are byte-identical (`diff`, empty). The observation that `studio_4k_env_maps → studio4kEnvMaps` is redundant is correct — `toCamelCase` produces it, because `_4` matches `_([a-z0-9])` and `"4".toUpperCase()` is `"4"`.

**§17.6 — nine and eight, and the numbers survived a correction to my own harness.** Re-measured during this review: 9 connections for a first `show()`, 8 for a repeat (the missing one is `get_defaults` at `show.py:462`, the clip-insight reset branch, which is skipped when the bbox is unchanged and the camera is kept). `status()` alone is 1, `get_defaults()` alone is 1. I recently corrected a *note* in `project_show_roundtrips_measured` — I had written that patching `comms._send` alone is insufficient; it is in fact sufficient, because `send_data` and friends resolve `_send` from `comms`'s module globals at call time. That correction does **not** touch the counts: they were captured inside the patched `_send`, which is on the real path. §17.6 and item 9's assertion can be written against 9/8.

**§2's [A] citations to me are faithful**, with the exceptions in F1 and the wording point in W1 below. Specifically confirmed: the `toCamelCase` / `STATE_TO_NOTIFICATION_KEY` opposite-directions claim; `studio_ao_intensity` as the only mapping miss (re-verified against the bundle's 76-entry `STATE_KEYS`); the precedence chain with `config.py:735-757`; `reset_camera` in three roles; `position`/`quaternion`/`target` in `CONFIG_SET_KEYS` and not `CONFIG_KEYS`; `analysis_tool` never reported back; `_debugStarted` produced by nothing. I also independently confirm §2's ocp_tessellate bullet for my half: **`ocp_vscode` imports nothing from `ocp_tessellate.defaults`** — no hit in any `ocp_vscode/*.py`.

**§1's five sentences are true** as they concern my repository. Item 6's in particular: `combined_config` does read host settings and live status over separate connections and filter the status with `workspace_filter` (config.py:670, :753), and a `Session` caching one settings read would remove 5 of the 9 connections, since 6 of the 9 are the identical `config` command and 3 of those exist only to let `preset("timeit", …)` read a value already in `DEFAULTS`.

---

## Would improve

**W1 — §2, bullet 8: "cannot be changed without a re-`show()`" is misleading for four of the nine.** The underlying coverage fact (no `ui` branch) is true for all nine — I verified it. But `modifier_keys`, `theme` and `control` cannot be changed from Python **at all** (neither `set_viewer_config` nor `set_defaults` takes them), and `timeit` is a Python-side flag the viewer does not need. "Cannot be changed without a re-`show()`" implies a `show()` *would* change them, which is true only for `ticks`, `grid_font_size`, `deviation`, `angular_tolerance` and `default_color`. Suggest splitting the bullet. This is the same conflation as F1 and fixing F1 probably fixes it.

**W2 — §15's four host-naming sites are graded [A] and attributed to me; they should be [M].** All four citations are correct — I re-checked each line. But the *synthesis* ("a host is named in four ways") is the migration architect's, not something my memory states; the individual facts are scattered across three of my files. Under the plan's own grading discipline that makes it [M], derived-and-confirmable, which is what it now is. Worth fixing precisely because the plan's grading is its main defence against the previous attempt's failure mode.

**W3 — §5.13's `set_defaults(position=…)` example needs its reachability caveat.** The behaviour is real and my memory says so, but `set_defaults` has no `position` parameter, so the path is only reachable through `reset_defaults()` (config.py:774-781), which passes the `CONFIG_SET_KEYS` subset including the camera keys. As written a reader may try `set_defaults(position=[…])` and get a `TypeError` rather than the described warning-plus-apply, and conclude the plan is wrong.

**W4 — §9.1: "a permanent exception" overstates the alternative, and there is a third option worth recording.** I support fixing `optionKeyOverrides` in 4.x: it is one line in `resources/viewer.html` plus the `make dist` copy (Makefile:35), it cannot regress any user because the key is currently unreachable, and cad-viewer-widget's independent `optionsMapping` already agrees on `studioAOIntensity`. But the exception would **not** be permanent — §11 retires `viewer.html`'s `toCamelCase` at item 10, so a named divergence would have a scheduled death two items out, exactly like the `legacy` column. The honest framing is "an exception that outlives item 4 by two items" rather than "permanent", and the fix-freeze question (§15's last bullet) should be decided against that, not against "forever". It remains Bernhard's call; my input is that the mechanical argument is weaker than stated and the fix is still worth making.

One correctness note if the fix lands: adding the override fixes the show-time path only. `studio_ao_intensity` will still have no `ui` branch, so it will behave exactly like the other ten studio keys. That is consistent and the plan says so — worth keeping that sentence, because a reader may otherwise expect `set_viewer_config(studio_ao_intensity=…)` to start working.

**W5 — §10.3 family 4 ("Surface (6) — `cad_width`, `height`, `theme`, `tree_width`, `pinning`, `glass`").** `glass` is not a surface key by any reading: it is a persistent VS Code setting (`OcpCadViewer.view.glass`), a standalone setting (`no_glass`), a `CONFIG_SET_KEYS` member with a live `ui` branch (`viewer.html:816-817`), and it is reported back in status. Grouping it with `cad_width` invites the `owner = surface` value. It belongs with the tree/tab family. `pinning` is genuinely surface-ish (`displayDefaultOptions.pinning: false`, `viewer.html:72`, never set from Python), and `tree_width` is `document` per §9.3 — so family 4 is really two keys plus three that belong elsewhere.

---

## Answers to the two questions put to me directly

**Does §5.6's mechanism survive all four host-naming sites, or only the import axis?** Neither, precisely. It survives the axis it targets — the user-facing message at `show.py:368` — and, if the injection also replaces the `not is_jupyter_cadquery` guard on the same branch, it dissolves a fifth site the plan does not currently claim. It does not touch `show.py:1634` or `comms.py:40`/`:320`, which are a drawability predicate and port-discovery environment sniffing respectively, in different modules and with different mechanisms. See F5.

**Does §4's "inbound is classified, not translated" hold for `combined_config`'s merge as it exists today?** For **names**, yes — confirmed, the merge is a filter over identically-named keys with no rename anywhere, and the one key that would need a rename (`activeTool`) is the one the plan already records as degenerate. For **values**, no — `status()` decodes the viewer's int `collapse` into the `Collapse` enum at config.py:688-693, and that decoding is the core's, not a host's. See F4.

---

## Summary of required changes

| # | section | change |
| - | ------- | ------ |
| F1 | §5.11, §9.1(3), §18 | `ui = false ∧ live_settable` is **11 keys** (the studio family), not 19/20; drop the [A]; split `ui` from a new `live_settable` fact |
| F2 | §9.2, §16 | replace the retracted `_splash` open question with the measured mechanism |
| F3 | §10, §5.2, §5.6, §5.11 | `_splash` has no expressible row — give it a protocol/handshake inventory outside the table (recommended) or extend four columns |
| F4 | §4, §5.8 | inbound **values** are decoded by the core (`collapse` int→enum, config.py:688-693); amend the decision and give `domain` a wire sub-field |
| F5 | §5.6, §15 | refusal message must be per-key (two categories today); state that the mechanism addresses one of four sites, plus the `is_jupyter_cadquery` guard |
| F6 | §11 | `CONFIG_UI_KEYS` is also referenced at config.py:205; it dies with `CONFIG_WORKSPACE_KEYS`, not with `ui_filter` |

With those six settled I agree the plan should go to Bernhard for the implementation decision.

---

# Sign-off — second draft (776 lines)

**Verdict: sign off with conditions.** Three conditions, all narrow; two of them are corrections to claims that are mine to settle and that the plan currently has backwards or unsettled. None blocks the commit sequence.

## Faithfulness check

I read §0.3, §0.1, §0.2a, then every section my 42 items touched. **41 landed faithfully, and the one escalation is answered below.** I checked specifically for the failure mode where a finding is folded in as its summary while the argument built on it survives — and did not find it. In particular, every remaining occurrence of "nineteen" in the plan (§0.1, §0.3, §2, §5.11, §9.1) is part of the correction narrative; **no section still reasons from 19**. §5.11's split into `ui` + `live_settable` is real, and §7.1's silence #5 and §9.1(3) were both re-derived to eleven rather than merely re-worded.

Also confirmed as faithful: §4's inbound-values amendment carries the `AttributeError` consequence, not just the fact; §5.6 keeps all three corrections including the honest one-of-four scope; §11 corrects both the schedule and the reason; §8.1 carries the exact counts; §10.2 carries my harness correction; §15's four-host-naming-sites bullet is regraded `[M]`; §5.13 gains the `reset_defaults` reachability caveat; §10.3 family 4 drops `glass`.

## The three items

### 1. §16.15 — `_splash`: neither host reads the payload. Both flip on arrival.

Settled from source. `_splash` occurs in host code in exactly three places, all **writes**: `controller.ts:126` and `standalone.py:379` (into the `config` reply) and the literal in `src/logo.ts:205`. **There is no read.**

- `controller.ts:219-227` — `data` is `message.toString().substring(2)`, a raw string. The `D:` branch forwards it verbatim with `postMessage(data)` and **never parses it** (the `C:` branch immediately above *does* `JSON.parse`). Then, unconditionally, `if (this.splash) this.splash = false;`.
- `standalone.py:396-404` — identical: raw slice, forwarded verbatim, never parsed, then the flip.

So the trigger is **the arrival of a model message**, not its content. This is not Bernhard being wrong — he is describing the design, and the code realises it a different way with an identical observable result, because `show.py:383` makes the payload constant. Two mechanisms that agree today only because the value never varies.

Two facts that fall out and that the inventory needs more than the field/event distinction itself:

- **Neither logo path goes through the `D:` branch**, which is *why* the guard survives the logo: VS Code's `controller.logo()` posts straight to the webview, and standalone's `standaloneViewer()` builds the logo in the browser (`standalone.py:72-78`) so the server never sees it. The flag therefore flips on the first model **from the Python client**, which is the precise edge.
- **A per-host divergence:** standalone's flip sits *after* `if self.javascript_client is None: … continue`, so with no browser attached the model is dropped and **the flag never flips**. A standalone viewer that has never had a browser connected keeps forcing `Camera.RESET` on every `show()`. VS Code's flip is unconditional.

**Condition A — the "conservative requirement" is protecting the wrong half, and one risk bullet is now false as written.** §8.5 says the entry is written "with the field's survival as the conservative requirement". The field is inert: no host reads it, and `viewer.html` reads a value that is always `False`. What must survive is the **event**. Concretely:

- §15's new risk bullet says *"dropping the forwarding leaves the host stuck on splash for ever."* **That is not true as stated** — dropping the `_splash` field from the model payload changes nothing, because the host flips on arrival. What would leave the host stuck is dropping or coalescing the **first model message's delivery to the host**, which a `Comms` redesign that batches, or that routes model data past the host to the frontend, could easily do while preserving every field.
- §2's OV bullet (line 119) and §8.5's second bullet both say the forwarded `False` "is how the host learns to flip its own property". Same correction, in two more places — this is exactly the pattern I was asked to watch for, so it needs fixing in all three.

Recommended replacement for the inventory's requirement, which survives a `Comms` redesign because it names the edge rather than the payload:

> **Normative:** the host clears its splash flag when it handles the **first model message originating from the Python client**, and not when it injects its own splash content. The flag must be reported as `_splash` in every `config` reply until then. The `_splash` field inside the model payload is currently inert — no host reads it — and a host may implement "read the payload" instead only while `show.py:383` keeps that value constant; the two mechanisms are equivalent today and would diverge the moment any producer emitted a model with `_splash: true`.

With that, `[?]` §16.15 closes and §8.5's entry becomes implementable without ambiguity.

### 2. §16.11 — it is **six**, and the six names are right

`ticks`, `grid_font_size`, `deviation`, `angular_tolerance`, `default_color`, `timeit` are all `set_defaults` parameters. `modifier_keys`, `theme`, `control` are not. My review's word "Five" was the typo; the parenthesised list was correct. Verified by `inspect.signature(set_defaults)`.

Consequence for the rows, since the plan notes they depend on it: those **six** get `live_settable = false`, `ui = false`, and the row note **show-time only, by construction** — they reach the viewer through `DEFAULTS` → `conf` → `params` on the next `show()`. The other **three** get `live_settable = false`, `ui = false` and a *different* note: **not settable from Python at all**, `modifier_keys` and `theme` being host-supplied and `control` being derived from `orbit_control`.

### 3. `viewer.html:100` — the plan's `[M]` is inverted. Line 100 is **live**; line **79** is the dead one.

The plan reasons: *"`render()`'s loop iterates `viewerOptionKeys` and looks up `viewerDefaultOptions[optionKey]` by the produced camelCase name, so an entry whose key no `configKey` produces is never read; `new_tree_behavior` is not in `viewerOptionKeys`; therefore the entry is dead."* The premises are all true — I confirmed `new_tree_behavior` is in neither `viewerOptionKeys` nor `renderOptionKeys` — but the conclusion does not follow, because **`viewerDefaultOptions` has a second reader that `render()`'s loop knows nothing about**:

```
viewer.html:293-297   const newTreeBehavior = preset(
                          _config, "new_tree_behavior",
                          viewerDefaultOptions.newTreeBehavior);   // <-- reads line 100
viewer.html:307       newTreeBehavior: newTreeBehavior,            // into the returned displayOptions
viewer.html:322/326/344   getDisplayOptions(...) -> new Display(container, displayOptions)
                                                 -> new Viewer(display, displayOptions, nc, null)
```

So `viewer.html:100` is the **operative fallback default** for `newTreeBehavior`, and it reaches the renderer as a `DisplayOptions` field — consistent with §8.2's own finding that the key belongs to `DisplayOptions`/`DISPLAY_DEFAULTS`/the Display block of `STATE_KEYS`.

**The dead entry is `viewer.html:79`, `displayDefaultOptions.newTreeBehavior`.** Nothing reads it: the only two reads of `newTreeBehavior` anywhere in the file are line 296 (from `viewerDefaultOptions`) and line 307 (the local). Every *other* member of `displayDefaultOptions` is read in `getDisplayOptions` — `glass`, `theme`, `tools`, `treeWidth`, `keymap` via `preset`, and the six tool flags copied through. `newTreeBehavior` is the single member that reaches into the other object.

So the oddity is real but it is the mirror image of what the plan records: a **display** option whose default is read out of the **viewer** defaults object, with an unread duplicate sitting in the display defaults where you would expect the live one.

**Condition B — correct §8.2, §9.2's *record* bullet, and §18's first ocp_vscode line before this becomes a row's evidence.** The risk is concrete: a future tidy-up that trusts the plan would delete line 100. That is *behaviourally* harmless today — `preset` would yield `undefined`, `_applyOptions` skips `undefined`, and the renderer's own `DISPLAY_DEFAULTS.newTreeBehavior` is also `true` — but only by coincidence of the two defaults agreeing, and it would silently transfer default ownership from ocp_vscode to the renderer, which is precisely the class of thing §5.9 exists to make visible. The right table value is `default_source = three-cad-viewer DISPLAY_DEFAULTS` per §5.9's rule, with a row note recording that ocp_vscode's copy lives at `viewer.html:100` and that `viewer.html:79` is an unread duplicate.

I also note this is the same error I made with `_splash`: deciding reachability from one consumer without enumerating the others. It is worth the plan recording it that way, because it is the second instance in two rounds.

## Conditions, restated

| | section | change |
| - | ------- | ------ |
| **A** | §8.5, §2 (line 119), §15's `_splash` risk bullet, §16.15 | the requirement is the **event**, not the field; `_splash` in the payload is inert and no host reads it; the risk is a lost first-model delivery, not a lost field. Record the per-host divergence (standalone does not flip with no browser attached) and that neither logo path goes through the `D:` branch |
| **B** | §8.2, §9.2, §18 | `viewer.html:100` is **live** and `viewer.html:79` is the dead duplicate — the `[M]` is inverted |
| **C** | §16.11 | **six**, with the six/three row-note split above |

Conditions A and B are corrections of fact; C is an answer. None affects the schema, the checks, the commit sequence or any other architect's section, so I do not think they need another full round — a corrected draft is enough. **With them applied I sign off.**

§1's five sentences, re-read in their rewritten form, are true as far as my repository is concerned; I have no objection to the item-8 rewrite or to §19's reading that the two apparent contradictions are not conflicts.

## Addendum to condition A — the ordering requirement, and why `_splash` is the proof case for a per-`show()` cache

Bernhard has since confirmed the outbound half (`controller.ts:49` → `:126` → `config()` → Python's `workspace_config` → the `_tessellate` test). **It confirms and sharpens my answer; it does not reframe it.** The payload-versus-arrival finding stays confined to the *inbound* flip, which is a different hop. What his ordering point adds is a **requirement**, not an observation, and it is stronger than the argument the plan currently carries for §1's item 6.

**The mechanism.** `_tessellate`'s first act is `conf = combined_config(...)` (`show.py:241`), whose first act is `workspace_config(...)` (`config.py:742`, before `status` at `:743`); the guard on the very next line (`show.py:242`) tests **that read's** value. So the guard is correct only because the settings read and the test are inside one `_tessellate`.

**And the window is provably safe, which is the part worth writing down.** Measured over one `show()`: all six `config` reads happen at steps 1, 2, 3, 5, 6 and 7, and the model send is step **8**. The only event that flips `_splash` is the host handling that model message. So **`_splash` cannot change during a `show()` — it changes exactly once, at the last step of the first one.** That is why caching the settings read for the duration of one `show()` is not merely a style preference:

> **Requirement.** A `Session` may cache `workspace_config` for the duration of **one** `show()` and no longer. The value is invariant within a show because the only transition is triggered by the model send, which is the show's final step; a cache spanning that event replays a stale `_splash: True`.

**The failure a longer cache produces is exactly the one nobody would diagnose.** `_splash` is `True` for the first show and `False` for every one after. A `Session`-lifetime cache replays `True` forever, so `show.py:242` forces `Camera.RESET` and `show.py:378` discards every explicit `reset_camera=`, on every show, for ever. No exception, no warning, no log line — the symptom is "the camera keeps resetting and `reset_camera=Camera.KEEP` is ignored", with nothing in any traceback pointing at a cache. This is a considerably better argument for the per-`show()` boundary than "requs.md says so", and **§8.5 should name `_splash` as its proof case** so the constraint carries evidence.

**The per-host divergence is the same failure by a different route, and a contract that only forbids caching would miss it.** Standalone's flip sits after `if self.javascript_client is None: … continue` (`standalone.py:399-404`), so with no browser attached the model is dropped and the flag never clears — a stale `True` reached without any cache at all, producing the identical forced-`RESET` symptom. Note this is **defensible rather than simply a bug**: no model was displayed, so arguably the splash state genuinely has not changed. VS Code flips unconditionally after a fire-and-forget `postMessage` (no delivery guarantee either); standalone flips only when it had somewhere to route to. **The two hosts have picked different points on the same edge — "on delivery attempt" versus "on successful routing" — and the contract must name which is normative rather than leave it to be rediscovered.**

So condition A's replacement text gains a third clause:

> **Normative:** (i) the host clears its splash flag when it handles the first model message originating from the Python client, not when it injects its own splash content; (ii) the settings read that the guard tests must be taken within the same `show()` as the guard — no cross-`show()` cache; (iii) the contract must state whether the flag clears on *delivery attempt* or on *successful routing to a frontend*, because the two shipped hosts differ and both stale states produce the same silent forced-`Camera.RESET`.

