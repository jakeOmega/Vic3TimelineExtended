# Tourism Heritage, Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make every monument's tourism an output bonus, and move the heritage that existing landmarks, archaeology sites and vanilla wonders stand for out of base appeal through a gated, generated term.

**Architecture:** Paradox script edits (static modifiers, script values, one `.gui` card, loc) plus one new one-shot Python generator. The generator reads a CSV of per-state moves and writes `tourism_heritage_moved`, a state-scope script value whose branches are gated on whether the monuments that take the points can exist. `tourism_bonus_from_base_appeal` becomes base appeal less that term. The scores in `tourism.txt` keep their values and gain a note.

**Tech Stack:** Victoria 3 Clausewitz script, Python 3.11/3.12 with `unittest`, `organize_loc.py`, the player guide build (pandoc + Typst).

**Spec:** `docs/superpowers/archive/specs/2026-10-23-tourism-heritage-design.md` (phase 1 of § 13). Per-state data: `docs/superpowers/archive/specs/2026-10-23-tourism-heritage-moves.csv`.

Phases 2 (To History and the 52 new landmarks, after the policy and prestige pass) and 3 (the 14 new sites) get their own plans. This plan builds the generator so they only append CSV rows.

## Global Constraints

- Work in the worktree `/home/jakef/src/vic3te-tourism-heritage` (branch `feat/tourism-heritage`). Never `POST /reload` from it. Use the main checkout's interpreter: `PY=/home/jakef/src/Vic3TimelineExtended/.venv/bin/python`, `RUFF=/home/jakef/src/Vic3TimelineExtended/.venv/bin/ruff`.
- Tests that import `mod_state_server` need the dummy env: `VIC3_BASE_GAME=/nonexistent VIC3_MOD_DEPLOY_TARGET=/nonexistent VIC3_VANILLA_REPO=/nonexistent VIC3_VANILLA_DOCS_RUNTIME=/nonexistent VIC3_GAME_LOGS=/nonexistent`.
- Read unittest results with `grep -E '^(Ran |OK|FAILED)'` on a redirected file, never `| tail`.
- Brace-based `.txt` files: tab indentation, exactly one UTF-8 BOM. Loc `.yml`: one BOM, `#b X#!` markup (never `[b]`), names spliced as `$key$`, never spelled out.
- Python must compile on 3.11: no f-string that reuses its own quote inside braces.
- Never hand-edit a generated file: edit the generator or its CSV and re-run.
- Run `$PY organize_loc.py` after loc edits and commit what it rewrites.
- Commits: stage by path (never `-a`); end every message with
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` and
  `Claude-Session: https://claude.ai/code/session_018Dbkw7hXDhNUyNmcLCmeX9`.
- Spec values, verbatim: monument tourism **+10% Tourism output a step** (`goods_output_tourism_mult = 0.10`, `gm_step_tourism = 0.10`); Ancestral Antiquity **+0.05** output a step; First Emperor's Army **+0.10**; Pilgrim Hostels **+0.05**; vanilla wonders' output **Taj Mahal 0.40, Angkor Wat 0.30, Hagia Sophia, Vatican City, Forbidden City, Saint Basil's Cathedral, White House and Great Mosque of Djenné 0.20, every other `bg_monuments` building 0.10**; Skyscraper keeps **+0.10 throughput**.

## Review Focus

1. **The Grand Monuments rule is off:** points moved to landmarks and sites must come back, and only the vanilla wonders' moves apply (Task 3, `test_gates_follow_the_rule_and_the_seeding`).
2. **A save without the 1836 landmarks** (`gm_landmarks_seeded` unset): landmark moves stay off (same test).
3. **A `bg_monuments` building that isn't one of the eight named wonders** (the mod's 37 wonders, the Space Program, a power bloc statue) gets +0.10, and two wonders in one state add up (Task 2, `test_other_monuments_get_the_default`).
4. **The net appeal can't go negative** when moves exceed a score, and a National Park still reads the raw score (Task 3, `test_base_appeal_nets_the_moves`).
5. **Stale throughput wording**: no Grand Monument loc line or guide passage may still promise Tourism Industry *throughput* (Task 1, `test_no_monument_loc_promises_throughput`).

---

### Task 1: Grand Monument tourism becomes output

**Files:**
- Modify: `common/static_modifiers/gm_modifiers.txt` (`gm_local_tourism` ~l.281, `gm_local_sig_antiquity` ~l.349, `gm_local_sig_first_emperor` ~l.359, `gm_evt_pilgrim_hostels` ~l.410)
- Modify: `common/script_values/gm_values.txt:129` (`gm_step_tourism`)
- Modify: `common/script_values/gm_signature_values.txt:30,32` (`gm_step_sig_local_antiquity`, `gm_step_sig_local_first_emperor`)
- Modify: `localization/english/te_miscellaneous_l_english.yml` (`gm_state_lbl_tourism`, `gm_state_tourism_tt`, `gm_state_sig_tourism_tt`, `gm_state_lbl_sig_tourism`, `gm_sig_antiquity_effect`, `gm_sig_first_emperor_effect`, `gm_policy_effects_open`, `gm_policy_open_effect_tt`), `localization/english/te_events_l_english.yml` (`monument_events.2.common_tt`)
- Modify: `docs/player_guide/02-timeline.md` (l.518, l.726, l.787, l.859, l.872, l.1053: each "Tourism Industry throughput" figure for monuments)
- Test: `test_grand_monument_registry.py` (`test_local_pairs` l.377; `SIGNATURES` rows l.5001, l.5038)

**Interfaces:**
- Produces: `gm_local_tourism` carries `goods_output_tourism_mult = 0.10`; `gm_step_tourism = 0.10`. Task 5's docs cite these.

- [ ] **Step 1: Change the pins.** In `test_local_pairs`, assert `("gm_local_tourism", "goods_output_tourism_mult", "gm_step_tourism", 0.10)`. In `SIGNATURES`, antiquity's local becomes `("goods_output_tourism_mult", 0.05)` and first_emperor's `("goods_output_tourism_mult", 0.10)`. Add to the same test class:

```python
def test_pilgrim_hostels_is_output(self):
    body = block(read(MODIFIERS), "gm_evt_pilgrim_hostels")
    self.assertAlmostEqual(number(body, "goods_output_tourism_mult"), 0.05)
    self.assertNotIn("throughput", body)

def test_no_monument_loc_promises_throughput(self):
    L = loc()
    keys = [k for k in L if k.startswith(("gm_state_", "gm_sig_", "gm_policy_")) or k == "monument_events.2.common_tt"]
    for k in keys:
        self.assertNotIn("building_tourism_industry_throughput_add", L[k], k)
        self.assertNotIn("Tourism Industry throughput", L[k], k)
```

(`loc()` returns key → text; check its shape in the file and adapt the iteration if it returns something else.)

- [ ] **Step 2: Run, expect failures.** `$PY test_grand_monument_registry.py > /tmp/t1.txt 2>&1; grep -E '^(Ran |OK|FAILED)' /tmp/t1.txt` → FAILED (the pins, the hostels test, the loc test).

- [ ] **Step 3: Edit the modifiers and values.** Each of the four modifiers swaps `building_tourism_industry_throughput_add` for `goods_output_tourism_mult` at the figures in Global Constraints. Set `gm_step_tourism = 0.10`, `gm_step_sig_local_antiquity = 0.05`, `gm_step_sig_local_first_emperor = 0.10`. Update each header comment that says "throughput". `gui_chart_script_values.txt:190` and `:242–250` only test `has_modifier`, so they need no change.

- [ ] **Step 4: Edit the loc.** Labels and tooltips say Tourism output: `gm_state_lbl_tourism` becomes `$goods_output_tourism_mult$`; the tooltips' bold heading and the policy lines say "tourism output from each monument". The two signature effect lines read `#G +5%#!` and `#G +10%#!` "Tourism output in its state". The `common_tt` line splices `$goods_output_tourism_mult$`. Then run `$PY organize_loc.py`.

- [ ] **Step 5: Edit the guide.** At the six lines listed, "+25% Tourism Industry throughput" becomes "+10% tourism output", and "throughput" becomes "output" wherever it means a monument's tourism. Line 518 is about wonders: it becomes "+10% tourism output in its state" (Task 2 sets that figure). Line 1053 (Open to the Public): "The tourism output each monument gives ×1.5".

- [ ] **Step 6: Run, expect a pass.** Same command as Step 2 → OK. Then `$PY test_grand_monuments_layout.py` and `VIC3_…=/nonexistent $PY test_hidden_state_modifiers.py` (dummy env) → OK.

- [ ] **Step 7: Commit.** Stage the files above plus whatever `organize_loc.py` rewrote, with the message "Grand Monuments: tourism is +10% output a step, not +25% throughput".

### Task 2: Monuments in the tourism card become an output source

**Files:**
- Modify: `common/script_values/tourism.txt` (`tourism_throughput_from_monuments` ~l.2833, `total_tourism_output_bonus_percent`, `total_tourism_throughput_bonus_percent`, the "Monuments are uncapped" comment near the fill values)
- Modify: `gui/te_state_panel_widgets.gui` (card `te_state_tourism_card`: the Monuments meter ~l.445–463 moves from the throughput column into the output column after Cities; the throughput column gets a Skyscraper meter in its place)
- Modify: `localization/english/te_miscellaneous_l_english.yml` (`te_state_tourism_monuments_tt`; new `te_state_tourism_skyscraper_tt`), `localization/english/te_concepts_l_english.yml` (`concept_tourism_monuments_desc`: "boosting [concept_tourism_output]")
- Modify: `common/building_groups/extra_building_groups.txt:109` (comment)
- Modify: `docs/player_guide/08-states.md:228,235` (the Monuments row moves to the output table; Skyscraper +10% stays in throughput)
- Test: `test_tourism_heritage.py` (create)

**Interfaces:**
- Produces: script values `tourism_bonus_from_monuments` (state scope, output, a fraction) and `tourism_throughput_from_skyscraper` (state scope, 0 or 0.10). `tourism_throughput_from_monuments` no longer exists anywhere in `common/` or `gui/`.

- [ ] **Step 1: Write the failing test.** Create `test_tourism_heritage.py` with `ROOT = Path(__file__).resolve().parent`, a `block(text, name)` helper (the top-level `name = { … }` body, braces balanced) and these tests:

```python
WONDERS = {"building_taj_mahal": 0.40, "building_angkor_wat": 0.30, "building_hagia_sophia": 0.20,
           "building_vatican_city": 0.20, "building_forbidden_city": 0.20,
           "building_saint_basils_cathedral": 0.20, "building_white_house": 0.20,
           "building_mosque_of_djenne": 0.20}

class MonumentsAreOutput(unittest.TestCase):
    def test_each_wonder_has_its_figure(self):
        body = squash(block(read(TOURISM), "tourism_bonus_from_monuments"))
        for b, v in WONDERS.items():
            self.assertRegex(body, rf"is_building_type = {b} \}} add = {v:g} \}}", b)

    def test_other_monuments_get_the_default(self):
        body = squash(block(read(TOURISM), "tourism_bonus_from_monuments"))
        self.assertIn("every_scope_building = { limit = { is_building_group = bg_monuments }", body)
        self.assertRegex(body, r"else = \{ add = 0\.1 \}")

    def test_totals(self):
        t = read(TOURISM)
        self.assertIn("add = tourism_bonus_from_monuments", block(t, "total_tourism_output_bonus_percent"))
        thr = block(t, "total_tourism_throughput_bonus_percent")
        self.assertIn("add = tourism_throughput_from_skyscraper", thr)
        self.assertNotIn("monuments", thr)

    def test_old_value_is_gone(self):
        for path in list((ROOT / "common").rglob("*.txt")) + list((ROOT / "gui").rglob("*.gui")):
            self.assertNotIn("tourism_throughput_from_monuments", path.read_text(encoding="utf-8-sig"), path)

    def test_card_shows_monuments_with_output(self):
        card = block(read(ROOT / "gui" / "te_state_panel_widgets.gui"), "type te_state_tourism_card")
        out_col, thr_col = card.split("te_state_tourism_throughput_tt", 1)
        self.assertIn("tourism_bonus_from_monuments", out_col)
        self.assertIn("tourism_throughput_from_skyscraper", thr_col)
```

(`squash` collapses whitespace runs to one space. The card is a `type X = flowcontainer {` block, so `block` must accept the `type …` prefix and the `= flowcontainer` before the brace.)

- [ ] **Step 2: Run, expect failure.** `$PY test_tourism_heritage.py > /tmp/t2.txt 2>&1; grep -E '^(Ran |OK|FAILED)' /tmp/t2.txt` → FAILED.

- [ ] **Step 3: Write the script values.** In `tourism.txt`, replace `tourism_throughput_from_monuments` with:

```
tourism_bonus_from_monuments = {
	value = 0
	every_scope_building = {
		limit = { is_building_group = bg_monuments }
		if = { limit = { is_building_type = building_taj_mahal } add = 0.4 }
		else_if = { limit = { is_building_type = building_angkor_wat } add = 0.3 }
		… one else_if per remaining WONDERS entry at 0.2 …
		else = { add = 0.1 }
	}
}

tourism_throughput_from_skyscraper = {
	value = 0
	if = { limit = { has_building = building_skyscraper } add = 0.1 }
}
```

Add each to its total, with a comment that the wonders' figures equal the appeal points they take (spec § 5.2). Fix the fill-section comment: Monuments are uncapped and have no bar, now in the output column.

- [ ] **Step 4: Move the card row.** Cut the Monuments `te_state_meter` from the throughput column and paste it after the Cities meter in the output column, reading `tourism_bonus_from_monuments`. Put a Skyscraper meter where it was: icon `gfx/interface/icons/building_icons/skyscraper.dds` (vanilla's), label `$building_skyscraper$`, value `tourism_throughput_from_skyscraper`, tooltip `te_state_tourism_skyscraper_tt`. Keep the `### Monuments are uncapped` comment, with the new figures.

- [ ] **Step 5: Loc and comments.** `te_state_tourism_monuments_tt`: each wonder's figure and "#v +10%#! for every other monument", plus the existing Grand Monument line, now saying its bonus is in the output "All modifiers" line. `te_state_tourism_skyscraper_tt`: "#bold $building_skyscraper$#!\nA $building_skyscraper$ adds #v +10%#! throughput." Update the `extra_building_groups.txt:109` comment. Run `$PY organize_loc.py`.

- [ ] **Step 6: Guide.** In `08-states.md`, the Monuments row moves from the throughput table into the output section, as a line or row matching its peers ("each monument +10%; the Taj Mahal +40%, Angkor Wat +30%, Hagia Sophia, the Vatican, the Forbidden City, Saint Basil's, the White House and the Great Mosque of Djenné +20%"). The throughput table keeps a Skyscraper row (+10%). Line 235's Grand Monument figure becomes "+10% tourism output for each step", in the output paragraph.

- [ ] **Step 7: Run, expect a pass.** Step 2's command → OK. `$PY scripts/analysis/check_gui_lint.py` → no new errors. `$PY scripts/format_paradox_tabs.py --check common/script_values/tourism.txt gui/te_state_panel_widgets.gui` → clean.

- [ ] **Step 8: Commit.** "Tourism: monuments are an output source; the Skyscraper keeps its throughput row".

### Task 3: The heritage moves: CSV, generator, gated term

**Files:**
- Create: `scripts/generators/data/tourism_heritage_moves.csv` (phase-1 rows, below)
- Create: `scripts/generators/gen_tourism_heritage.py`
- Create (generated): `common/script_values/tourism_heritage_generated.txt`
- Modify: `common/script_values/tourism.txt` (`tourism_bonus_from_base_appeal`, `tourism_fill_base_appeal_pct` comment)
- Modify: `localization/english/te_miscellaneous_l_english.yml` (`te_state_tourism_appeal_tt`; new `te_state_tourism_appeal_moved_line`), `localization/english/te_concepts_l_english.yml` (`concept_tourism_base_appeal_desc`: "natural features, climate, geography and townscape; a state's historical monuments count in the monuments instead")
- Modify: `docs/auto_generated_files.md` (a "Mod scripting & data" row, in the format of `te_demog_capital_generated.txt`'s), `scripts/nightly_audit_select.py` (`EXCLUDED_REGISTRY_GLOBS` gains the generated file; classify the CSV if `test_nightly_audit_select.py` names it)
- Test: `test_tourism_heritage.py` (extend)

**Interfaces:**
- Consumes: nothing from Tasks 1–2.
- Produces, in `gen_tourism_heritage.py`:
  - `Move = namedtuple("Move", "state points monument kind reason")`
  - `KINDS = ("vanilla_wonder", "existing_landmark", "existing_site", "new_landmark", "new_site")`
  - `GATES: dict[str, str | None]` = `{"vanilla_wonder": None, "existing_landmark": "gm_system_enabled = yes has_global_variable = gm_landmarks_seeded", "existing_site": "gm_system_enabled = yes", "new_landmark": "gm_system_enabled = yes has_global_variable = gm_landmarks_seeded_2", "new_site": "gm_system_enabled = yes"}`
  - `load_moves(path: str = CSV) -> list[Move]` (rows with points > 0 only, CSV order)
  - `render(moves: list[Move]) -> str`
  - `main() -> int` with `--check` (exit 1 when stale, write nothing)
  - Task 4 adds `annotate(text: str, moves: list[Move]) -> str` and `--annotate`.
  - Script value `tourism_heritage_moved` (state scope, a fraction: points / 100).

**The CSV.** Copy `docs/superpowers/archive/specs/2026-10-23-tourism-heritage-moves.csv` (header `state,points,monument,kind,reason`). Keep every row with 0 points (revisit, pilgrimage, pass2_townscape), plus the moved rows of each state whose moves are all of kinds `vanilla_wonder`, `existing_landmark` or `existing_site`. That is 30 states: District of Columbia, Tuscany, Lazio, Île-de-France, Zealand, Rajputana, Delhi, Attica, Upper Egypt, Lebanon, Baghdad, Fars, Eastern Thrace, Annam, Kanto, Beijing, Ingria, Campania, Cambodia, Agra, Syria, Peloponnese, Crete, Sindh, Mosul, Xi'an, Ica, Chiapas, Lima, Western Mali. Moscow waits for phase 2.

**The rendered format** (exact, so the tests can pin it). A header like `gen_planned_capital.py`'s ("AUTO-GENERATED by scripts/generators/gen_tourism_heritage.py — do not edit manually", the spec's § 6.3, how to re-run). Then:

```
tourism_heritage_moved = {
	value = 0
	if = {
		limit = { state_region = s:STATE_LAZIO }
		add = 20
		if = { limit = { gm_system_enabled = yes has_global_variable = gm_landmarks_seeded } add = 20 }
	}
	else_if = {
		…
	}
	divide = 100
}
```

States in CSV order of first appearance. Within a state, sum the points by gate, emitted in `KINDS` order of the gate's first kind, with ungated points as a bare `add`. Two kinds sharing a gate (`existing_site`, `new_site`) merge into one line.

- [ ] **Step 1: Write the failing tests** (in `test_tourism_heritage.py`, loading the generator with `importlib.util.spec_from_file_location`, as `test_demographics_place.py` does):

```python
class HeritageMoves(unittest.TestCase):
    def test_generated_file_is_current(self):
        self.assertEqual(read(GENERATED), gen.render(gen.load_moves()))

    def test_gates_follow_the_rule_and_the_seeding(self):
        out = squash(gen.render([gen.Move("STATE_X", 20, "a", "vanilla_wonder", ""),
                                 gen.Move("STATE_X", 30, "b", "existing_landmark", ""),
                                 gen.Move("STATE_X", 10, "c", "existing_site", ""),
                                 gen.Move("STATE_X", 5, "d", "new_site", "")]))
        self.assertIn("limit = { state_region = s:STATE_X } add = 20 if =", out)
        self.assertIn("if = { limit = { gm_system_enabled = yes has_global_variable = gm_landmarks_seeded } add = 30 }", out)
        self.assertIn("if = { limit = { gm_system_enabled = yes } add = 15 }", out)
        self.assertTrue(out.rstrip().endswith("divide = 100 }"))

    def test_every_monument_exists(self):
        seeds = read(ROOT / "common/scripted_effects/gm_landmark_effects.txt")
        sites = read(ROOT / "common/scripted_effects/gm_archaeology_effects.txt")
        vanilla = json.loads((ROOT / "vanilla_parsed/common/buildings.json").read_text(encoding="utf-8"))
        for m in gen.load_moves():
            if m.kind in ("existing_landmark", "new_landmark"):
                self.assertIn(f"KEY = {m.monument} ", seeds, m)
            elif m.kind in ("existing_site", "new_site"):
                self.assertIn(f"KEY = {m.monument} ", sites, m)
            else:
                self.assertIn('"bg_monuments"', json.dumps(vanilla[f"building_{m.monument}"]), m)

    def test_every_state_is_scored(self):
        scored = set(re.findall(r"state_region = s:(STATE_\w+)", block(read(TOURISM), "base_tourism_appeal_value")))
        for m in gen.load_moves():
            self.assertIn(m.state, scored, m)

    def test_base_appeal_nets_the_moves(self):
        t = read(TOURISM)
        body = squash(block(t, "tourism_bonus_from_base_appeal"))
        self.assertIn("value = base_tourism_appeal_value subtract = tourism_heritage_moved min = 0", body)
        parks = block(t, "tourism_throughput_from_parks")
        self.assertIn("base_tourism_appeal_value", parks)
        self.assertNotIn("tourism_bonus_from_base_appeal", parks)

    def test_scores_left_match_the_spec(self):
        scores = appeal_scores()          # STATE -> int, parsed from base_tourism_appeal_value
        moved = collections.Counter()
        for m in gen.load_moves():
            moved[m.state] += m.points
        for state, left in {"STATE_ATTICA": 60, "STATE_EASTERN_THRACE": 60, "STATE_BEIJING": 55,
                            "STATE_ILE_DE_FRANCE": 70, "STATE_TUSCANY": 90, "STATE_CAMBODIA": 60,
                            "STATE_CRETE": 75, "STATE_UPPER_EGYPT": 50}.items():
            self.assertEqual(scores[state] - moved[state], left, state)
```

(`appeal_scores()` pairs each `state_region = s:STATE_X` with the `value = N` that follows it inside `base_tourism_appeal_value`.)

- [ ] **Step 2: Run, expect failure** (no generator, no generated file): `$PY test_tourism_heritage.py > /tmp/t3.txt 2>&1; grep -E '^(Ran |OK|FAILED)' /tmp/t3.txt` → FAILED/ERROR.

- [ ] **Step 3: Write the CSV and `gen_tourism_heritage.py`** to the interfaces and format above. Module docstring in `gen_planned_capital.py`'s style: what it writes, the spec, "Needs nothing but the repo. Re-run after editing the CSV; test_tourism_heritage.py fails CI when the committed file is stale." It reads with `utf-8-sig` and writes with `utf-8-sig`, `newline="\n"`.

- [ ] **Step 4: Generate.** `$PY scripts/generators/gen_tourism_heritage.py` → "wrote 30 states …". Then `--check` → "current", exit 0.

- [ ] **Step 5: Wire it in.** `tourism_bonus_from_base_appeal` becomes `value = base_tourism_appeal_value`, `subtract = tourism_heritage_moved`, `min = 0`, with a comment naming the generated file and spec § 6.3. `tourism_throughput_from_parks` is untouched. `te_state_tourism_appeal_tt`: "A score for each state, set by its landscape, climate and townscape." Then `[SelectLocalization(GreaterThan_CFixedPoint(State.MakeScope.ScriptValue('tourism_heritage_moved'), '(CFixedPoint)0'), 'te_state_tourism_appeal_moved_line', 'te_state_tourism_appeal_none_line')]`, then "Maximum: #v +100%#!". The moved line: "\n\n#v [State.MakeScope.ScriptValue('tourism_heritage_moved')|0%]#! of it is counted in its monuments instead (Monuments above), and goes with them." The none line is empty (`""`). Run `$PY organize_loc.py`.

- [ ] **Step 6: Registries.** Add the `docs/auto_generated_files.md` row: output, generator, input `scripts/generators/data/tourism_heritage_moves.csv`, "One-shot, not a post-load generator; … `test_tourism_heritage.py` fails CI when stale". Add the output to `EXCLUDED_REGISTRY_GLOBS`. Run `$PY test_nightly_audit_select.py`: if it names the CSV, add it to `INTENTIONALLY_NOT_EXCLUDED` ("input to gen_tourism_heritage.py").

- [ ] **Step 7: Run, expect a pass.** Step 2's command → OK; `$PY test_nightly_audit_select.py` → OK; `$PY scripts/format_paradox_tabs.py --check common/script_values/tourism.txt common/script_values/tourism_heritage_generated.txt` → clean; `$RUFF check scripts/generators/gen_tourism_heritage.py test_tourism_heritage.py` → clean.

- [ ] **Step 8: Commit.** "Tourism: heritage moved to existing monuments comes off base appeal, gated on the monuments existing".

### Task 4: Notes on the scores

**Files:**
- Modify: `scripts/generators/gen_tourism_heritage.py` (`annotate`, `--annotate`)
- Modify: `common/script_values/tourism.txt` (written by `--annotate`: the 30 states' comments)
- Test: `test_tourism_heritage.py` (extend)

**Interfaces:**
- Consumes: `load_moves`, `Move` (Task 3).
- Produces: `annotate(text: str, moves: list[Move]) -> str`. It appends to the comment on each moved state's `value = N # …` line ` (N moved to monuments: tourism_heritage_generated.txt)`, replacing any earlier note of that form (idempotent), and changes nothing else. N is the state's total points.

- [ ] **Step 1: Write the failing tests:**

```python
    def test_annotate_is_idempotent_and_touches_only_comments(self):
        moves = gen.load_moves()
        once = gen.annotate(read(TOURISM), moves)
        self.assertEqual(gen.annotate(once, moves), once)
        strip = lambda t: re.sub(r"#.*", "", t)
        self.assertEqual(strip(once), strip(read(TOURISM)))

    def test_scores_carry_their_note(self):
        t = read(TOURISM)
        for state, n in moved_totals().items():   # STATE -> total points > 0
            self.assertRegex(t, rf"s:{state} \}}\n\t\tvalue = \d+ #[^\n]*\({n} moved to monuments: "
                                rf"tourism_heritage_generated\.txt\)", state)
```

(Check the exact indentation of the `value =` line under each branch in `tourism.txt`, and match it in the regex.)

- [ ] **Step 2: Run, expect failure** (no `annotate`).

- [ ] **Step 3: Implement `annotate` and `--annotate`** (writes `tourism.txt` in place with `utf-8-sig`, `newline="\n"`; the file is hand-written, so this is a one-shot editor, never a regenerator).

- [ ] **Step 4: Run `$PY scripts/generators/gen_tourism_heritage.py --annotate`**, then the tests → OK. `git diff --stat common/script_values/tourism.txt` shows 30 changed lines.

- [ ] **Step 5: Commit.** "Tourism: each moved score says where its heritage went".

### Task 5: Docs, play-test list, guide PDF, full gate

**Files:**
- Modify: `docs/systems/mod_systems.md` (l.21 Tourism; l.470 card columns; § Grand Monuments: tourism is output, +10% a step)
- Modify: `docs/testing/tourism-playtest.md` (new section "Monuments move to output, heritage leaves base appeal")
- Modify: `docs/player_guide/08-states.md` (the Base Appeal paragraph: landscape, climate and townscape; historical monuments count in the monuments), then rebuild `docs/player_guide/Vic3TimelineExtended_Player_Guide.pdf`

- [ ] **Step 1: `mod_systems.md`.** Tourism: name `tourism_heritage_moved`, its generator and gates, and `tourism_bonus_from_monuments` with the wonders' figures. Card: Monuments in the output column, Skyscraper in throughput. Grand Monuments: `gm_local_tourism` is `goods_output_tourism_mult` 0.10 a step; the signatures 0.05 and 0.10.

- [ ] **Step 2: Play-test rows**, in the file's Check / Expect / If it fails table format:
  - Attica on day one: Base Appeal +60%, the tooltip says 40% is counted in its monuments; with the Parthenon standing, the output "All modifiers" line shows the Grand Monument's +40% (×1.5 under Open).
  - Agra: Monuments row +40% in the output column; Base Appeal +45%.
  - A game with the Grand Monuments rule off: Attica's Base Appeal reads +100%; Agra's still +45%.
  - Western Mali: Base Appeal +40% until the Great Mosque of Djenné is built, then Monuments +20%.
  - A state with a Skyscraper: the throughput column's Skyscraper row reads +10%.

- [ ] **Step 3: Guide paragraph and rebuild.** Edit the Base Appeal text in `08-states.md` (spec § 1, § 6.1). Run `$PY scripts/analysis/check_player_guide_style.py --strict` → clean, then `$PY scripts/build_player_guide.py`, then `--check` → current.

- [ ] **Step 4: Full gate** (the system's tests and lints; CI runs the rest):

```bash
for t in test_tourism_heritage test_grand_monument_registry test_grand_monuments_layout test_hidden_state_modifiers test_nightly_audit_select test_tax_code_bypass; do
  env VIC3_BASE_GAME=/nonexistent VIC3_MOD_DEPLOY_TARGET=/nonexistent VIC3_VANILLA_REPO=/nonexistent VIC3_VANILLA_DOCS_RUNTIME=/nonexistent VIC3_GAME_LOGS=/nonexistent $PY $t.py > /tmp/$t.txt 2>&1; echo "$t: $(grep -E '^(OK|FAILED)' /tmp/$t.txt)"
done
$PY organize_loc.py --check && $PY scripts/analysis/check_localization_files.py && $RUFF check . && $PY -m compileall -q scripts test_tourism_heritage.py
$PY scripts/analysis/check_gui_lint.py
for a in loc_coverage script_loc_reference modifier_multiplier_var gui_reference; do $PY ${a}_audit.py --strict > /tmp/$a.txt 2>&1; echo "$a: $?"; done
grep -nE "f\"[^\"]*\{[^}\"]*\"|f'[^']*\{[^}']*'" scripts/generators/gen_tourism_heritage.py test_tourism_heritage.py
```

Expected: every test OK, every check exit 0, the last grep prints nothing.

- [ ] **Step 5: BOM check on changed files.** For each changed `.txt` and `.yml`: `head -c 6 <file> | xxd` shows exactly one `efbbbf`.

- [ ] **Step 6: Commit** the docs, the play-test list, the guide and the PDF together: "Tourism heritage phase 1: docs, play-test list, player guide".
