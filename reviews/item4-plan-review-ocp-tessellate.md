# Item 4 plan review — ocp_tessellate architect

Reviewing `plans/phase1-item4-config-key-table.md` (all 512 lines) under `APPROACH.md`. Sources read at ocp-tessellate `6851b23` plus one uncommitted working-tree change (§0 below), vscode-ocp-cad-viewer and cad-viewer-widget as checked out today.

## Verdict

**Agree with required changes.**

The plan's spine is right and I want to say so before the findings, because most of what follows is scoped corrections rather than disagreement. The extracted-versus-judged split (§5.12), the refusal to generate the inbound direction (§4), the `legacy` quarantine (§5.13) and the reachability check (§7.4) are all mechanisms rather than intentions, and they are the right ones. The grading discipline works: every claim I was asked to check was checkable from what the plan said, which is the whole point of it.

Eight things must change before implementation. Six are in my domain and are scoping or ownership errors that would put wrong values in rows attributed to me. One (**M5**) is a false statement in §1 about item 8, which is the section the plan itself says is the most valuable thing to attack. One (**M6**) is a correction to my own memory that the plan quoted in good faith.

## 0. A note on the working tree

`ocp_tessellate/defaults.py` carries one uncommitted change: `apply_defaults` now uses `if k in result` instead of the unreachable NaN comparison, mirroring `Defaults.set_defaults`. It is Bernhard's, it is not part of this plan, and I have not touched it. It does not affect any finding here — `apply_defaults` has no caller in any project — but it does make one line of my own memory stale, which I have corrected (§5).

---

# Must change before implementation

## M1 — §10.3 family 1 is `CONFIG_CONTROL_KEYS` renamed, and inherits its incoherence

**What is wrong.** "Tessellation control (10) — `debug`, `edge_accuracy`, `helper_scale`, `render_joints`, `render_mates`, `render_normals`, `reset_camera`, `show_parent`, `show_locals`, `timeit`" is not a family derived from what ocp_tessellate does. It is `ocp_vscode/config.py:238-249` copied verbatim, same ten members, same alphabetical order. I did not infer that from the shape of the list; I extracted every `CONFIG_*` list by AST and compared.

**Why it matters.** §5.13 argues, correctly and at length, that the five legacy lists "are not derivable from semantics — they were never coherent", and quarantines them in a column with a scheduled death. Using one of those same lists as the **work-breakdown structure** re-imports the incoherence through the back door, in the one place §5.12 cannot catch it: the judged columns get filled family by family by the architect the family was handed to, so a mis-drawn family means the wrong person supplies `lifetime`, `type` and `default` for a key — and their citation will be truthful, which is what makes it hard to spot later.

Concretely, the list is wrong in both directions:

- **`reset_camera` never reaches ocp_tessellate in any form.** It is in the `DEFAULTS` dict (`defaults.py:159`) and in the dead `add_shape_args` filter (`defaults.py:274`), and it is read by nothing. Every `get_default(` and `preset(` call site in the package is listed in M6 below; `reset_camera` is not among them, and it is not a parameter of `to_ocpgroup`, `to_ocp` or `tessellate_group`. Its `type` is `Camera`, an enum ocp_tessellate has never heard of. I cannot supply its columns and should not be asked to.
- **`debug` is not in ocp_tessellate's `DEFAULTS` at all** (51 keys, AST-extracted, list in M6). It is a `to_ocpgroup` parameter (`convert.py:1760`, `debug: bool = False`) that ocp_vscode passes at `show.py:338`. So its default comes from a function signature, not from a defaults dict — a different source with a different lifetime, which the `default` column has to be able to say.
- **`render_edges` is missing from every family in §10.3**, and it is one of the nine keys ocp_tessellate actually reads (`convert.py:1922`). It decides `compute_edges`, which changes the payload *and* is part of the tessellation cache key (`tessellator.py:114-123`). ocp_vscode force-sets it to `True` on every show (`show.py:399`) and it is in no `CONFIG_*` list and not in `package.json` — which is exactly why copying a legacy list lost it.

**What should replace it.** A family defined by the mechanism, which I can state exactly. Sixteen keys, in three groups that differ in where their `default` comes from — and that difference is itself a schema requirement, not a detail:

1. **Read from `DEFAULTS` (9)** — `default_color`, `default_facecolor`, `default_thickedgecolor`, `default_vertexcolor`, `deviation`, `angular_tolerance`, `edge_accuracy`, `render_edges`, `render_normals`. Default source: `defaults.py:109-175`.
2. **Passed as parameters, shadowing a `DEFAULTS` entry that is never read (6)** — `helper_scale`, `render_mates`, `render_joints`, `show_parent`, `show_locals`, `timeit`. Default source: the `to_ocpgroup` signature (`convert.py:1749-1760`) and `tessellate_group`'s `timeit` argument (`convert.py:1819`). **These keys have two ocp_tessellate defaults that can disagree** and nothing enforces agreement; today they agree except `helper_scale`, which is `1` in the dict and `1.0` in the signature.
3. **Passed as a parameter with no `DEFAULTS` entry (1)** — `debug`.

Not mine, and to be reassigned: `reset_camera`, `normal_len` (see M5), `default_edgecolor` and `default_opacity` (see M2).

The plan's note that "two of them (`reset_camera`, `timeit`) also reach the viewer and need the ocp_vscode architect too" is half right. `timeit` genuinely is joint — it reaches me as `tessellate_group`'s fifth argument and controls `Timer` output (`utils.py:128-166`), and it reaches the viewer as well. `reset_camera` is not joint; it is not mine at all.

## M2 — §10.3 family 2 assigns me two colour keys ocp_tessellate never reads

**What is wrong.** Family 2 is "Colours (6) — `default_color`, `default_edgecolor`, `default_facecolor`, `default_thickedgecolor`, `default_vertexcolor`, `default_opacity`. **ocp_tessellate architect**, whose memory already establishes the three-way precedence".

The three-way precedence I established covers exactly three keys — `default_facecolor`, `default_thickedgecolor`, `default_vertexcolor` — plus `default_color`, which follows a two-way version of it. It does not cover the other two, because **`default_edgecolor` and `default_opacity` are never read anywhere in ocp_tessellate.** They occur only as entries in the `DEFAULTS` dict (`defaults.py:127`, `:136`) and as members of the dead `add_shape_args` / `tessellation_args` filters (`defaults.py:275`, `:306`, `:310`). No `get_default("default_edgecolor")` and no `get_default("default_opacity")` exists.

**Where they do belong.** Both are renderer keys with a live path that has nothing to do with me:

- `default_edgecolor` is in `CONFIG_SET_KEYS`, in `package.json`, in `viewer.html`, and the plan's own §8.2 records it as one of the three `optionKeyOverrides` entries (`default_edgecolor→edgeColor`). It is an axis-1 render option.
- `default_opacity` is in `CONFIG_SET_KEYS`, in `package.json` as `OcpCadViewer.view.default_opacity` (`:396`), in `viewer.html`, and in `standalone_defaults.py:39`.

**What should replace it.** Family 2 is four keys, and `default_edgecolor` / `default_opacity` move to whichever family carries render options, owned by the ocp_vscode and three-cad-viewer architects. Their `default` in the table must be three-cad-viewer's `ViewerState` value under §5.9's rule, not ocp_tessellate's dict entry — and note that `defaults.py:127`'s `"#707070"` happens to equal `standalone_defaults.py:38`, so an author filling this row from my dict would get the right number for the wrong reason and would not notice when they diverge.

## M3 — §10.3 has `edge_accuracy` in two families and `render_edges` in none

**What is wrong.** `edge_accuracy` is listed in family 1 ("Tessellation control (10)") and again in family 3 ("Geometry and quality (4) — `deviation`, `angular_tolerance`, `edge_accuracy`, `normal_len`"). §5 is explicit that the table is one row per key, and §13.4 makes each family one commit; a key in two families is either two rows or two commits touching one row, and neither is what the plan intends.

`render_edges` is in no family at all (M1).

**What should replace it.** Merge families 1 and 3 into the sixteen-key family of M1, or keep the split and place each key once: quality inputs (`deviation`, `angular_tolerance`, `edge_accuracy`, `render_edges`) in one, converter behaviour (`helper_scale`, `render_joints`, `render_mates`, `show_parent`, `show_locals`, `debug`, `timeit`) in another, colours (the four of M2) in a third. Either is fine; the duplicate is not.

## M4 — §5.8: `type = color` is not sufficient, and the failure is silent

**The question asked.** "Is `type = color` the right encoding given the `Color` int-versus-float discrimination trap?"

**Answer: `color` is the right *type*, and it is not sufficient on its own. The row must also carry the representation, in `domain`.**

`Color.__init__` (`utils.py:34-99`) discriminates a tuple's scale by content, not by declaration: `any(isinstance(c, float)) and all(0.0 <= c <= 1.0)` takes the fractional branch, `all(isinstance(c, int) and 0 <= c <= 255)` takes the 0-255 branch, and anything else falls through to `_invalid`. Measured:

| input | result |
| --- | --- |
| `(232, 176, 36)` | `#e8b024` |
| `(0.9098, 0.6902, 0.1412)` | `#e8b024` |
| `"#e8b024"` | `#e8b024` |
| `"Violet"` | `#ee82ee` |
| `(1.0, 1.0, 1.0)` | `#ffffff` |
| `(1, 1, 1)` | `#010101` |
| `(0.5, 255, 1)` | `#a0a0a0` — grey, with a `RuntimeWarning` and no exception |
| `(232, 176, 36, 128)` | `#e8b024`, alpha `0.502` |
| `(0.9, 0.7, 0.1, 0.5)` | `#e6b21a`, alpha `0.5` |

So the same three numbers spell white or near-black depending on their Python type; a mixed tuple silently becomes grey; and a 4-tuple's alpha scale is inferred from whether the value exceeds 1.0. A generated Settings control (item 14) or traitlet (item 16) that emits the wrong representation produces a wrong colour with **no error a user will see** — the `_invalid` path warns to stderr and returns grey, which is the same class of silence §7.1 exists to end. `type = color` alone gives a generator no way to know which to emit.

**Why this is not hypothetical.** One key, `default_color`, carries three representations across three sources today, all meaning the same colour: `(232, 176, 36)` at `ocp_tessellate/defaults.py:126`, `"#e8b024"` at `standalone_defaults.py:41`, and — for its siblings — `(238, 130, 238)` / `(186, 85, 211)` at `ocp_vscode/config.py:704-706` against `"Violet"` / `"MediumOrchid"` at `standalone_defaults.py:42-46`. §5.9's disagreement check would fire on all of these and report a finding, when in fact only the *representation* differs and the colours are identical. That is a false positive the schema can prevent.

**What should replace it.** `type = color`, plus a mandatory `repr` in `domain` drawn from a closed set: `css_name | hex | hex_alpha | rgb_int | rgb_float | rgba_int | rgba_float`. Two consequences worth stating: the §5.9 disagreement check should compare **normalised** colours (`Color(x).web_color` plus alpha) and report a finding only when the resolved colour differs, listing the representation skew separately; and the `default` column for a colour key must record the representation it is written in, or item 16's traitlet default is a coin flip.

I will supply `repr` for the four keys of M2's corrected family. For `default_edgecolor` and `default_opacity` that is the render-option owner's to supply — and `default_opacity` is a `float`, not a `color`, which is a third reason it does not belong in family 2.

## M5 — §1's "item 8 takes nothing" is false for `normal_len`, and §10.3 family 3 mis-files it

This is the finding the coordinator asked me to look for, and it is real.

**What is wrong.** §1 states "Item 8 (codec) takes nothing. The table describes configuration, not the model payload." §10.3 family 3 then lists `normal_len` as a key I own, with a `lifetime`, a `type` and a `default`.

`normal_len` is not configuration. It is a **field of the model payload, computed by the tessellator**, and it flows model → config, which is the opposite direction from every other row in the table:

1. `tessellate_group` computes it into the payload: `shapes["normal_len"] = max_accuracy / deviation * 4 if render_normals else 0` (`convert.py:1988`). `max_accuracy` is the largest per-instance quality over the model, so the value is a function of the geometry.
2. ocp_vscode reads it back out with `get_normal_len(render_normals, shapes, deviation)` (`convert.py:2073-2074`) — a compatibility shim that **ignores its first and third arguments** and returns `shapes["normal_len"]`, carrying the comment `# TODO: change show.py to directly get normal_length from shapes`.
3. It is then written into the config dict: `params["normal_len"] = get_normal_len(...)` at `show.py:422-426`, unconditionally, overwriting anything a caller supplied.

So there is no path by which a user sets `normal_len`; it has no entry in ocp_tessellate's `DEFAULTS` (51 keys, and it is not one of them); and it has no static default — it is `0` or it is derived from the model. `defaults.py:325-326` in the dead `show_args` is the only place that would ever read it as an input, and `show_args` has no caller.

**Why it matters beyond one row.** §7.4's reachability check requires "a Python API path, a host settings path, or a wire path". `normal_len` has a wire path and nothing else, and its wire path is *outbound as payload*, not as config. If the schema admits it as an ordinary row it will get a fabricated `default` — the most likely one being `0`, which is right only when `render_normals` is false. And the boundary §1 draws is exactly the boundary item 8 is going to have to police: `normal_len` is where "configuration" and "model payload" are already the same dict in ocp_vscode.

**What should replace it.** One of two, and I do not mind which, but the plan has to choose:

- Give it `lifetime = derived` (a fourth value) with `applied_by = none` and an explicit note that its value is produced by the tessellator per model, and amend §1 to say item 8 takes **one row's classification** rather than nothing; or
- Exclude it under §7.4 as not a config key — the same treatment §9.2 gives `_debugStarted` — and amend §10.3 family 3 to three keys.

The second is cleaner and I would prefer it, but the first is more honest about the fact that `params` and the payload are not disjoint today. Either way, §1's fifth sentence as written is false, and §1 says that is the most valuable comment available.

## M6 — §2's last `[A]` bullet attributes a rationale to me that I did not establish

**What is wrong.** §2's final bullet reads: "ocp_tessellate's own defaults dict holds ~50 keys, most of them viewer settings it never reads, **'so a host can round-trip them'** (ocp_tessellate architect, `project_colors_and_defaults`)."

The quoted clause is in my memory file, and it should not have been. It is **my own unsupported rationale**, written as if it were a finding, and it is contradicted by the sentence immediately beside it in the same file: nothing anywhere imports `ocp_tessellate.defaults`, so no host round-trips anything through it. I have corrected my memory (§5 below) and I am flagging it here rather than quietly fixing it, because the plan relied on it in good faith and because the plan's whole grading apparatus depends on `[A]` meaning measured.

**What should replace it**, all of it measured this pass and citable:

- The dict holds **51** keys, not "~50" — AST-extracted from `defaults.py:109-175`.
- **Exactly nine** are ever read from it, at these five call sites: `default_color` (`convert.py:214`, `cad_objects.py:424`), `default_facecolor` / `default_thickedgecolor` / `default_vertexcolor` (`convert.py:221`, `:224`, `:227`), `deviation` and `edge_accuracy` (`convert.py:1877-1878`), `deviation`, `angular_tolerance`, `render_edges`, `render_normals` (`convert.py:1919-1923`). That is the complete set of `get_default(` and `preset(` call sites in the package.
- **Six more** name a `to_ocpgroup` / `tessellate_group` parameter whose default lives in the signature and which never consults the dict: `helper_scale`, `render_mates`, `render_joints`, `show_parent`, `show_locals`, `timeit`.
- The remaining **thirty-six are inert**: read by nothing, reachable through nothing. `optimal_bb` is the sharpest example — `bounding_box` does take an `optimal` argument, but the only call in the tessellation path passes it literally: `bounding_box(shape, loc=None, optimal=False)` at `convert.py:1933`.

## M7 — §16.9's "five keys that appear nowhere else" is four

`viewer` is not one of them. It is the sidecar/viewer-title key and it is everywhere in ocp_vscode: 30 occurrences in `config.py` (including the host branch at `:645`), 10 in `package.json`, 119 in `resources/viewer.html`. ocp_tessellate's own `create_args` documents the correspondence by renaming it: `"title" if key == "viewer" else key` (`defaults.py:231-232`).

The four that genuinely appear in no other source I checked (ocp_vscode `config.py`, `package.json`, `viewer.html`, `standalone_defaults.py`) are `anchor`, `optimal_bb`, `show_bbox`, `js_debug`.

The rest of §16.9's factual claims I confirm: `collapse: 3` (`defaults.py:170`) is outside every member of `Collapse` (`config.py:76-82`, values `{2, -1, 0, 1}`); `reset_camera: True` (`defaults.py:159`) is a bool where `Camera` is a string enum (`config.py:61-71`) — and where `standalone_defaults.py:35` has the string `"KEEP"`, which matches no `Camera` value either since `Camera.KEEP` is `"keep"`; `ticks: 10` (`defaults.py:152`) against `standalone_defaults.py:36`'s `5`; `tree_width: 250` (`defaults.py:116`) against `standalone_defaults.py:13`'s `240`. `collapse` is worth one extra line: ocp_tessellate's `3` is a *fourth* representation beside the `Collapse` enum, the wire int, VS Code's setting string and the widget's `COLLAPSE_MAPPING` keyed on `"1"/"R"/"C"/"E"` (`cad-viewer-widget/js/lib/widget.js:14-19`) — and `standalone_defaults.py:34` has `"1"`, so §5.8's "four representations" is five.

## M8 — §17.10's proposed correction to the `ocp_utils.py` citation is wrong

The plan proposes changing requs.md's `ocp_tessellate/ocp_utils.py:26-38` to "approximately `:25-38`". Line 25 is `import numpy as np` and line 27 is `from cachetools import LRUCache, cached`; neither is an OCP import. The OCP module-scope imports are **line 26 (`import OCP`) and lines 28-99**, ending with the `from OCP.TopTools import (...)` block that closes at `:99`.

requs.md's existing `:26-38` at least begins in the right place; the proposed edit moves the start onto a numpy import and still stops sixty lines early. Replace with `:26,28-99`, or simply `:26`, which is the line that makes the point.

---

# Answers to the questions put to me

## §16.9 — is `ocp_tessellate.defaults` in scope for the table?

**No as a source of truth, yes as a defect record, and the dict's reduction is a separate change that is not item 4's.** Three parts.

**It must not be a `default` source for any row.** With 36 of 51 keys inert (M6), a value in that dict carries no information about what anything does — it is an abandoned copy of a viewer configuration from before ocp_vscode had its own. The four measured disagreements (`collapse`, `reset_camera`, `ticks`, `tree_width`) are not disagreements between two live opinions; they are one live opinion and one fossil. §5.9's rule already excludes it correctly for `group = display|render|viewer` keys. The amendment needed is to §5.9's clause "For a `group = none` key it is the core's own (today ocp_vscode's `DEFAULTS` or ocp_tessellate's)": for my sixteen keys the ocp_tessellate default is authoritative **only** for the nine that are read from the dict, and for the other seven the signature is authoritative and the dict entry must be ignored. Otherwise the table will record `helper_scale = 1` when the operative default is `1.0`, and will record dict values for `render_mates`, `render_joints`, `show_parent`, `show_locals`, `timeit` and `debug` that nothing consults.

**It should appear in the coverage assertion of §8.3, as a source whose keys must all resolve.** This costs one extractor and buys something the plan wants anyway: running the 51 keys against the table is how the four fossils get *found* rather than argued about, and the extractor is trivial (one AST walk of one dict literal, no import, no OCP). Recording it as a source also means a future ocp_tessellate release that adds a key to that dict is noticed by the core's tests.

**The dict's reduction is real work and it is not item 4's.** §14 already says so and is right. For the record, so the decision has somewhere to land: the correct end state is that `Defaults` holds the sixteen keys ocp_tessellate can act on and nothing else, which is a breaking change for any direct `to_ocpgroup` caller doing `set_defaults(ticks=…)` — today that call is accepted and silently does nothing, and after the reduction it would print "not a valid argument". That belongs with the other 4.0.0 removals already scheduled in the CHANGELOG (`FACE_COLOR`, `THICK_EDGE_COLOR`, `VERTEX_COLOR`, `EDGE_COLOR`, the two root re-exports), not in a Phase 1 item. **I recommend it be added to that 4.0.0 list now**, while the measurement is fresh, because §14's "asks the question; does not answer it" is exactly how the 3.5.0 fallbacks are already at risk of becoming permanent by neglect — which requs.md itself warns about at line 566.

One thing I will not assert: whether any real user calls `to_ocpgroup` directly and relies on `set_defaults`. ocp_tessellate is on PyPI and the README documents `to_ocpgroup` as public API, so the population is not zero and is not knowable from here. That is a Bernhard question, and it is the only thing standing between "reduce the dict" and "reduce the dict in a major".

## §10.3 families 1-3 — is the ownership split right, and will the columns come from me?

**Ownership: yes, for the corrected sixteen-key family of M1-M3. Columns: `type` and `default` yes; `lifetime` only jointly.**

`type` is mine and is unambiguous for all sixteen. `default` is mine with the two-source caveat of M1 (dict versus signature), which I would like recorded as a schema requirement rather than a note: for these seven keys the row needs to say *which* ocp_tessellate default it carries, and a check should assert the two agree, because today the only skew is `1` versus `1.0` and that is the kind of gap that widens quietly.

**`lifetime` is not mine alone and the plan should not assign it to me.** Whether a key is `persistent` is decided by whether a host stores it, which is a fact about the host, not about the tessellator. Measured for my family: `deviation` and `angular_tolerance` are `persistent` because `package.json` declares them (`OcpCadViewer.render.angular_tolerance` at `:437`, `.deviation` at `:443`); `edge_accuracy`, `helper_scale`, `render_joints`, `render_mates`, `render_normals`, `show_parent`, `show_locals`, `timeit` and `debug` are in `CONFIG_CONTROL_KEYS` and in no settings schema, so `session`; `render_edges` is in no list and no schema at all and is force-set on every show. I can supply the ocp_tessellate half of each — "this key is read per-`to_ocpgroup` call and nothing in ocp_tessellate persists it" is true of all sixteen — but the `persistent`/`session` verdict needs the ocp_vscode architect's schema facts. Mark `lifetime` joint for family 1-3, the way §10.3 already marks `timeit` joint.

One addition for item 6 rather than item 4, which I mention because §12 says item 6 caches a settings read for the duration of one `show()`: four of my keys — `deviation`, `angular_tolerance`, `render_edges`, and `edge_accuracy` through the deflection it computes — are part of the **tessellation cache key** (`tessellator.py:114-123`). Changing one of them invalidates every cached mesh. A `Session` that caches config across shows is caching something that a mesh cache is keyed on, and the two need to agree about when a value changed. Not item 4's problem; worth a line in item 6's plan so it is not discovered there.

## §5.9 — is the one-default rule workable for my keys?

**Yes, with the amendment in §16.9 above and one correction to the disagreement check.**

The rule itself is right and the reasoning for it is right: recording six defaults would mean the table has an opinion about hosts, and §5.9's "show the shared default and the host's override side by side" is the honest presentation. For my nine dict-read keys the shared default is ocp_tessellate's and I can cite each one.

The correction is M4's: **the disagreement check must normalise colours before comparing.** As written it will report `default_color = (232,176,36)` versus `"#e8b024"` as a finding, and it is not one — they are the same colour written twice. Compare `Color(x).web_color` and alpha; report a representation skew as a separate, lower-severity note. Without that, the first run of the check produces four or five false findings in the colour rows and the reviewer who dismisses them will be right, which is how a check earns a reputation for crying wolf.

Second, smaller: `default_facecolor`, `default_thickedgecolor` and `default_vertexcolor` have `None` as their `DEFAULTS` value (`defaults.py:133-135`), deliberately, so that `_default_or` falls through to the module constants (`convert.py:220-228`). The **operative** default is `"Violet"` / `"MediumOrchid"` / `"MediumOrchid"` from `convert.py:30-32`, which is what a user sees and what item 14 must show. A `default` column filled from the dict literal would say `null` for all three and be technically accurate and completely useless. The row needs the resolved value, with the two-step resolution cited.

## §17.2-17.4 — the requs.md corrections in my domain

All three confirmed, each re-verified this pass rather than taken from the plan:

- **§17.2 — item 1 is done.** `ocp_tessellate/_version.py:31` reads `__version__ = "3.5.0"`, `pyproject.toml:7` agrees, and the 3.5.0 CHANGELOG entry describes exactly the additive change requs.md line 558 asks for. **Confirmed.**
- **§17.3 — line 542's editable-metadata example is stale.** Both shared environments report metadata `3.5.0` and `__version__ 3.5.0`, and both resolve `ocp_tessellate.__file__` to the editable checkout. **Confirmed**, and I agree with the plan's judgement that the lesson survives and only the numbers go.
- **§17.4 — the `convert.py` line numbers moved.** `export_three_cad_viewer_js` is at `:2121` and the `numpy_to_buffer_json` call is at `:2155`. **Confirmed.**

**Three corrections §17 missed, all in my domain:**

- **§17.1 is understated, and it changes a Phase 0 dependency.** The plan says `ocp_vscode/pyproject.toml:30` reads `>=3.4.0,<3.6.0` and that the release "is done". What it does not say is the consequence requs.md line 544 draws from the old ceiling: that `pip install ocp_viewer` fails in any environment containing ocp_vscode 4.x from step 3 to step 5, and that this is why an extra 4.x patch was scheduled. With the ceiling already widened *and* `ocp-viewer-core/pyproject.toml:31` declaring `ocp-tessellate>=3.5.0,<3.6.0`, the ranges now intersect and the disjointness that motivated the extra release is gone. The correction should say the *blocker* is gone, not just that a release happened, because line 544's reasoning is what a reader will otherwise carry forward.
- **requs.md line 598's characterisation of the second `numpy_to_buffer_json` call site is wrong, not merely mis-numbered.** It says the call "sits inside `export_three_cad_viewer_js`", which reads as "the exporter base64-encodes". It does not, on its default path. `keep_instances=False` takes a completely different branch: `decode()` inlines each instance into the leaf's `shape` and `numpy_to_js` dumps plain JSON number lists (`convert.py:2157-2159`) — measured, 2195 bytes for `Box(1,2,3)`, no base64 anywhere. Only `keep_instances=True` reaches `numpy_to_buffer_json` (`convert.py:2155`), and on that branch the `var` argument is silently ignored and no `var name =` prefix is emitted. This matters for item 8's byte-stability requirement: the output that the two three-cad-viewer example scripts actually produce is the *non*-base64 one, so "keeps its output byte-stable" has to mean both branches, and the branch requs.md names is the one nobody calls.
- **requs.md line 562's list of `Color` users is incomplete in a way that strengthens its own argument.** It cites `ocp_utils.py:102`, `cad_objects.py:20`, `tessellator.py:65` and `__init__.py:40` as proof that moving `Color` into the core would create a distribution cycle. `tessellator.py:65` imports `Timer` and `round_sig`, not `Color`. The correct fourth citation is `convert.py:24` (`from ocp_tessellate.utils import *`), and `stepreader.py:47` imports `warn` from the same module. The conclusion is unchanged and if anything better supported; the citation is wrong.

---

# Would improve

## W1 — §5.5's `lifetime` has no value for a computed key

Raised by M5 and worth stating on its own: if `normal_len` stays in the table, none of `persistent`/`session`/`transient` describes it. It is not stored, not set by code, and not "something that just happened" — it is derived per model. If the plan chooses M5's first option, `derived` is the fourth value and §5.5's rule of thumb gains a fourth clause: *derived if nobody sets it and something computes it*.

## W2 — §5.12's judged/extracted split puts `default` on the wrong side for my keys

`default` is listed as extracted. For the seven signature-defaulted keys of M1 and the three `None`-in-dict colour keys of §5.9 above, the extraction has to know *which of two sources* to read and, for the colours, has to run a two-step resolution through `_default_or` and the module constants. That is a judgement encoded in the extractor rather than in the row, which is exactly the thing §5.12 exists to prevent. Either mark `default` judged for these rows, or have the extractor emit `default_source` alongside `default` so the choice is visible and reviewable.

## W3 — §8.3's coverage list should name ocp_tessellate's dict explicitly

Per §16.9 above. It is currently absent from the list of sources in §8.3, and adding it is one extractor.

## W4 — §7.2's fixture idea is worth copying downward

Not a criticism. The re-extraction-asserted-in-tests mechanism would work just as well against ocp_tessellate's `DEFAULTS`, and it is the only thing that would have caught the four fossils before they became a plan question. If item 4 builds the machinery, ocp_tessellate is nearly free to add.

## W5 — a caution about §9.1's precedent

I have no standing on the `studio_ao_intensity` decision, but one observation from my side of the fence: §9.1 argues the fix must land because otherwise the equivalence test carries a permanent exception. That reasoning generalises, and the same argument will be available for every defect the table surfaces. It is right here — one line, two repositories, an independent implementation already agrees on the value. It will be less right the third time it is used. Worth a sentence in §9.2's policy saying that "fix" requires an independent implementation to agree on the correct value, which is what makes this case safe and is not a property of defects in general.

---

# On the five sentences of §1

Asked of all three architects. Four of the five I can assess from my side and they hold: item 5's requirement that the generated artefact import without OCP is satisfiable and is the right constraint to state (note that it constrains the *generated* module only — `ocp_viewer_core.config` will still pull OCP transitively through `ocp_tessellate`'s `Color`, for the reason requs.md line 587 already records, and §1's sentence does not claim otherwise); item 6's use of the filters as predicates is unaffected by anything I own; item 7's `owner` column touches none of my keys, since all sixteen are `document`; item 9's migration of the host-free checks is fine.

**The fifth is false as written** — that is M5. `normal_len` is a payload field the table currently proposes to describe as configuration, and the boundary between "tessellation parameter" and "wire format" runs through `params` in `show.py`, not around it.

---

# Memory files touched

Two, both in `/Users/bernhard/.claude/projects/-Users-bernhard-Development-CAD-ocp-tessellate/memory/`:

- `project_colors_and_defaults.md` — removed the unsupported "so a host can round-trip them" rationale that §2 quoted as `[A]` (M6); replaced it with the measured 51 / 9 / 6 / 36 breakdown and the call-site list; recorded that `default_edgecolor` and `default_opacity` are live *viewer* keys elsewhere even though ocp_tessellate never reads them (M2); added the colour-representation matrix and the normalisation point (M4); recorded that `apply_defaults` is fixed in the working tree while HEAD `6851b23` still has the NaN test.
- `reference_data_format.md` — recorded that `normal_len` flows model → config and has no input path (M5), so the next reader does not have to re-derive it.

---

# Sign-off — second draft (776 lines), 2026-08-10

## Verdict: sign off with one condition

All 51 addressed items landed faithfully. I re-checked each against the sources rather than against the change table: family 1 is rebuilt by mechanism and the `CONFIG_CONTROL_KEYS` diagnosis is stated better than I stated it (§10.3); family 2 is four colour keys with `default_edgecolor`/`default_opacity` moved to family 8 (§10.3); `edge_accuracy` sits in family 1 only; `type = color` carries a mandatory `repr` from a closed set and §5.9 rule 4 normalises before comparing (§5.8, §5.9); §2's fabricated rationale is replaced by the 51/9/6/36 measurement with the five call sites enumerated; `default_source` is in (§5.12), `derived` is in (§5.5), `lifetime` is marked joint for families 1–3 (§10.4), the ocp_tessellate `DEFAULTS` is a coverage source (§8.3), and §9.2's "fix" now requires an independent implementation to agree. My three missed `requs.md` corrections are §17.11, §17.12 and §17.13, and §17.10 is correctly withdrawn as wrong — including the reason it was wrong, which I would have let pass.

**Bernhard's two answers, both confirmed as landed.** The `DEFAULTS` reduction is on the 4.0.0 list with the halves split three ways in §14, and §17.13's two statements are right: `requs.md:566` does enumerate exactly those five removals, and the "differs in kind" clause holds. The assumption that direct `to_ocpgroup` callers exist is stated in §5.9 rule 2, in §14's third sub-bullet and in §16.13, and §16.13 explicitly extends it to keep `apply_defaults`'s fix-versus-delete question open. That is strong enough — it names the shortcut ("no caller") and forbids it by name, which is what stops it reappearing.

## `normal_len` — the decline answers me, and I withdraw the objection

I verified all four legs of the ground I did not have: `normal_len` is the 7th entry of `renderOptionKeys` (`viewer.html:370`) and of build123d Studio's `RENDER_KEYS` (`viewer.js:32`); the widget maps `normal_len → normalLen` in `getRenderOptions` (`widget.js:366`); and `normalLen` is a `RenderOptions` field (`types.ts:316`), a `STATE_KEYS` member (`viewer-state.ts:195`), a `ViewerStateShape` field (`types.ts:470`) with a `ViewerState` default of `0` (`:459`) and a live consumer at `nestedgroup.ts:863` fed from `viewer.ts:633`.

So the row must stay, and my premise was too strong rather than my reasoning wrong. I established the *provenance* of the value and inferred from it that the key was not configuration; provenance and path are two separate facts and this key has both — a real config→renderer axis-1 path in all three implementations, and a value whose content is computed from the model. The resolution taken is not "keep it because a test would fail": it is the schema widening I offered as option 1, and the new evidence shows my preferred option 2 would have been actively wrong. `default = 0` also agrees with `ViewerState`, so §5.9 rule 1 produces no conflict.

## The condition: `lifetime = derived` is not host-invariant

This is the one thing that must change, and it is a consequence of keeping the row rather than an argument against keeping it.

**On the cad-viewer-widget path `normal_len` is an ordinary user-set render option, and nothing computes or overwrites it.** cad-viewer-widget never tessellates — it has no `ocp_tessellate` import anywhere and takes already-tessellated shapes — so there is no `shapes["normal_len"]` and no `show.py:422-426`. What it has instead is a full public setting path: a synced traitlet `normal_len = Float(allow_none=True).tag(sync=True)` (`cad_viewer_widget/widget.py:265`), a `show()` keyword (`__init__.py:178`) resolved as `preset("normal_len", normal_len, 0)` (`:366`), an assignment at `widget.py:930`, and membership in `viewer_args` (`utils.py:154`).

So `derived` is true on the two hosts that tessellate and false on the one that does not, and §5.5's defining sentence — *"nobody sets it; something computes it per model"* — is the sentence whoever fills the column will read. **This is the same trap §5.6 solved for `owner`**: a column that must state a property of the *key* has acquired a value that is a property of the *host*. §5.6 solved it by moving the host-varying part into `owns(key)`; `lifetime` has no equivalent.

Either resolution satisfies me, and the choice is the migration architect's:

- **(a)** `lifetime = session` — its widget lifetime, the one that describes a value somebody sets — plus a mandatory note that ocp_vscode and build123d Studio overwrite it from the payload, carrying the three citations §7.4 already has; or
- **(b)** keep `derived`, redefine it in §5.5 as *"no host-independent input path"* rather than *"nobody sets it"*, record the widget's setter on the row, and assert that item 16's traitlet generation does not filter on `lifetime` — because it must still emit a `normal_len` traitlet.

What I cannot sign off is `derived` with §5.5's current wording, because item 16 generates the widget's traitlets and this row currently tells it that nobody sets a value the widget's public API sets.

## Two notes, neither blocking

1. **§17.13's "breaking" is right, but for a better reason than the one implied.** `Defaults.set_defaults` prints and never raises (`defaults.py:104`), so after the reduction `set_defaults(ticks=10)` still does not stop anything working — it gains a warning. The durable reason it belongs in a major is the **read-back path**: `get_default("ticks")` returns `10` today and `None` afterwards, so a direct caller using `Defaults` as a general config store silently changes behaviour. That is precisely the caller §16.13 instructs us to assume exists, which ties the two rulings together. Worth one clause in §17.13, since the enumeration is the mechanism that stops neglect and a weak justification invites someone to reopen it.

2. **A live defect found while verifying §7.4's ground, reported rather than acted on.** `cad_viewer_widget/widget.py:1408-1414`: the `Viewer.normal_len` property getter returns `self.widget.black_edges` — the wrong attribute, copy-pasted from the `black_edges` block immediately above — and unlike both its neighbours it has **no setter at all**, despite its docstring saying "Get or set". The traitlet and the `show()` path are fine; only the public property is broken, in both directions. It belongs to whoever owns cad-viewer-widget and is out of item 4's scope, but it qualifies as **fix** rather than **record** under §9.2's new limit, since the traitlet and the neighbouring properties independently agree on what it should say. Flagging it because §16 generates from this surface.

## On §19's two "apparent contradictions"

§19 invites an objection if either has been papered over. Neither has. On §1's item-8 sentence, three-cad-viewer and I were assessing different halves and the rewrite preserves both statements verbatim — the codec surface genuinely takes nothing, and `normal_len` genuinely crosses from payload into `params`. On §9.1's "permanent exception", the ocp_vscode correction and my caution are complementary, and §19 is right that my half survives §9.1a's closure *because* the argument that prompted it has gone: the next defect the table surfaces will not have a one-line fix landing beside it, which is when §9.2's limit has to do the work.

No repository source was modified, and Bernhard's uncommitted `defaults.py` fix is untouched. No memory files changed this round — the second draft introduced no new ocp_tessellate facts beyond those already recorded.
