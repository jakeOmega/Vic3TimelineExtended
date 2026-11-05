# Grand Monuments policy, upkeep and prestige Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Four monument policies, each best at one thing (Open: tourism; Ceremonial: a quarter of every monument's
grandeur toward legitimacy and authority; Cultural Promotion: pull, or prestige with Cultural Hegemony off; Public
Education: +1% education access a step). No upkeep. Prestige becomes +10 a step plus +1% a step.

**Architecture:** Everything stays in the Grand Monuments script. The policy is the `gm_policy` country flag read by
`gm_policy_is`. Its effects are factor script values on step counts (`gm_policy_scale_steps`, after the curve), plus two
new inputs before the curve (Ceremonial's venue share and Education's steps). National effects are JE-held static
modifiers refreshed by `gm_apply_national_modifiers`. Mothballed and Standard go, along with every code path that
read them. Older saves migrate by dropping the flag.

**Tech Stack:** Paradox script (`common/`, `gui/`, `localization/`), Python unittest (`test_grand_monument_registry.py`,
`test_grand_monuments_layout.py`), the player guide build (`scripts/build_player_guide.py`).

**Spec:** `docs/superpowers/archive/specs/2026-10-23-gm-policy-prestige-design.md` (read it whole first). The heritage spec it
amends is `docs/superpowers/archive/specs/2026-10-23-tourism-heritage-design.md`.

## Global Constraints

- Brace files use tabs and exactly one UTF-8 BOM. Run `python3 scripts/format_paradox_tabs.py --check <files>`.
- After any loc edit, run `python3 organize_loc.py` and commit everything it rewrote. Loc uses `#b X#!`, never `[b]`.
  Splice names with `$key$`, never spell them.
- Never hand-edit generated files (`docs/auto_generated_files.md`).
- No `POST /reload` from this worktree. Use GET endpoints only, or none.
- Python must run on 3.11: no f-string that reuses its own quote inside braces.
- Each round runs only the targeted tests and lints; CI runs the whole suite. Run Python from the main checkout:
  `PY=/home/jakef/src/Vic3TimelineExtended/.venv/bin/python`.
- Commits:
  - stage by path, never `-a`;
  - each message ends with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>` and
    `Claude-Session: https://claude.ai/code/session_018Dbkw7hXDhNUyNmcLCmeX9`;
  - no push and no PR until the owner asks.
- Spec values:
  - `gm_step_prestige = 10`, `gm_step_prestige_pct = 0.01`;
  - `gm_policy_ceremonial_share = 0.25`, for legitimacy and for the Leader's authority;
  - `gm_step_education = 0.01`, on the open 1/n curve with a first step of 10, over standing grandeur;
  - Open ×1.5 on monument tourism;
  - Cultural Promotion ×1.5 on pull with `cultural_hegemony_enabled`, and ×1.5 on prestige otherwise;
  - the five-year wait unchanged.
- Policy keys: `open`, `ceremonial`, `culture` (the default, `STANDARD = yes`) and `education`. The buttons run in that
  order, two to a row.
- Vanilla wonders' figures and maintenance are untouched. `pmg_maintenance` stays on `building_grand_monument`.

## Review Focus

1. **An older save on Mothballed in its five-year wait** loads as Cultural Promotion, and the wait keeps running.
   Migration must not clear `gm_policy_cooldown` or `gm_policy_chosen`. (Task 3 pins it.)
2. **Switching away from Public Education** leaves no education modifier behind:
   - `gm_remove_national_modifiers` removes `gm_national_education`;
   - `gm_s_education` is 0 under the other three policies, so the row hides and the empty state counts it.

   (Task 6 pins it.)
3. **Ceremonial for a country with no regime monuments:** the legitimacy and authority rows' bar, hover and next step
   read the curve's real input, never `gm_g_regime` alone. (Task 5 pins it.)
4. **Venue membership:** contested monuments and anything To History are out; heritage is in; held trophies are in.
   (Task 5 pins the trigger. To History doesn't exist yet, so its exclusion is a comment and an assertion on the
   trigger's text.)
5. **The Cultural Hegemony rule:** with it on, prestige never moves by policy; with it off, pull never does. Each
   factor gates on the rule. (Task 4 pins it.)

---

### Task 1: Prestige becomes +10 a step plus +1% a step

**Files:**
- Modify: `common/script_values/gm_values.txt` (`gm_step_prestige` near line 124; displays near line 888)
- Modify: `common/static_modifiers/gm_modifiers.txt:11-14`
- Modify: `common/scripted_effects/gm_effects.txt` (`gm_apply_national_modifiers`, `gm_remove_national_modifiers`)
- Modify: `localization/english/te_miscellaneous_l_english.yml` (`gm_je_tt_prestige`, `gm_je_val_prestige`, the new
  modifier's name)
- Test: `test_grand_monument_registry.py` (the `assert_pair` block near line 361)

**Interfaces:**
- Produces:
  - `gm_step_prestige_pct = 0.01`;
  - the static modifier `gm_national_prestige_pct` (`country_prestige_mult = 0.01`);
  - `gm_display_prestige_pct` (country scope: `gm_s_standing` × `gm_step_prestige_pct` × 100, guarded like
    `gm_display_prestige`).

- [ ] **Step 1: Write the failing test.** In `test_grand_monument_registry.py`, change the `gm_national_prestige` pair
  to 10 and add:

```python
self.assert_pair("gm_national_prestige", "country_prestige_add", "gm_step_prestige", 10)
self.assert_pair("gm_national_prestige_pct", "country_prestige_mult", "gm_step_prestige_pct", 0.01)

def test_prestige_pct_rides_the_standing_steps(self):
    apply = squash(block(read(EFFECTS), "gm_apply_national_modifiers"))
    self.assertIn("gm_add_national = { NAME = gm_national_prestige_pct VAR = gm_s_standing }", apply)
    self.assertIn("remove_modifier = gm_national_prestige_pct",
                  squash(block(read(EFFECTS), "gm_remove_national_modifiers")))
    self.assertIn("gm_display_prestige_pct", loc()["gm_je_val_prestige"])
```

- [ ] **Step 2:** Run `$PY test_grand_monument_registry.py -k prestige`. Expected: FAIL on 25 ≠ 10 and on the missing
  modifier.
- [ ] **Step 3: Implement.**
  - Set `gm_step_prestige = 10` and `country_prestige_add = 10`.
  - Add `gm_step_prestige_pct`, `gm_national_prestige_pct` (the same icon as `gm_national_prestige`) and
    `gm_display_prestige_pct`.
  - Add and remove the modifier beside `gm_national_prestige`.
  - Show both parts in `gm_je_val_prestige` ("+X and +Y%") and in `gm_je_tt_prestige`'s step line.
  - Give `gm_national_prestige_pct` loc like `gm_national_prestige`'s.
  - Run `organize_loc.py`.
- [ ] **Step 4:** Run `$PY test_grand_monument_registry.py -k prestige`, `$PY test_nation_tab.py` (the `"gm_*"` glob
  in `NOT_ON_COUNTRY` covers the new modifier) and `$PY scripts/analysis/loc_coverage_audit.py --strict` (or the
  audit's CI command). Expected: all pass.
- [ ] **Step 5: Commit** "Grand Monuments: prestige +10 a step plus +1% a step".

### Task 2: Grand Monuments cost nothing to maintain

**Files:**
- Modify: `common/script_values/gm_values.txt:1753-1790` (`gm_policy_factor_upkeep`, `gm_state_upkeep_mult`)
- Modify: `common/static_modifiers/gm_modifiers.txt:380-401` (comments only; the two old modifiers stay for removal)
- Modify: `localization/english/te_miscellaneous_l_english.yml` (`gm_upkeep`, `gm_upkeep_desc`)
- Test: `test_grand_monument_registry.py` `UpkeepTests` (line 6291)

**Interfaces:**
- Produces: `gm_state_upkeep_mult` constant −1. `gm_policy_factor_upkeep` deleted.

- [ ] **Step 1: Write the failing test.** Rewrite `UpkeepTests.test_one_modifier_sized_by_the_records` as
  `test_upkeep_is_cancelled`:

```python
self.assertEqual(squash(block(read(VALUES), "gm_state_upkeep_mult")), "value = -1")
self.assertIsNone(block(read(VALUES), "gm_policy_factor_upkeep"))
self.assertNotIn("gm_policy_factor_upkeep", "".join(read(p.relative_to(ROOT).as_posix())
                                                    for p in ROOT.glob("common/**/*.txt")))
self.assertIn("pmg_maintenance", squash(block(read("common/buildings/grand_monuments.txt"),
                                                "building_grand_monument")))
```

  `test_the_state_pulse_is_its_one_refresh` stays as is: the multiplier still resolves through
  `root.var:gm_upkeep_mult`.
- [ ] **Step 2:** Run `$PY test_grand_monument_registry.py -k Upkeep`. Expected: FAIL.
- [ ] **Step 3: Implement.**
  - `gm_state_upkeep_mult = { value = -1 }`. Its comment says −1 cancels `pm_maintenance`'s level-scaled input
    whatever the level (owner 2026-10-23, spec § 5).
  - Delete `gm_policy_factor_upkeep`.
  - Rewrite `gm_upkeep`'s loc: no upkeep, the building's maintenance input cancelled.
  - In `test_grand_monument_registry.py`, `PolicyTests.test_upkeep_is_on_the_building` keeps only its removal checks
    (Task 3 rewrites the table).
  - In `docs/testing/grand-monuments-ageing-playtest.md:45`, the expected upkeep becomes none.
- [ ] **Step 4:** Run `$PY test_grand_monument_registry.py -k "Upkeep or Policy"`. Expected: PASS.
- [ ] **Step 5: Commit** "Grand Monuments: no upkeep".

### Task 3: Four policies (keys, buttons, migration), and Mothballed's paths gone

**Files:**
- Modify: `common/scripted_effects/gm_policy_effects.txt` (header, `gm_policy_set`, new `gm_policy_migrate`)
- Modify: `common/scripted_effects/gm_effects.txt` (`gm_country_refresh` calls `gm_policy_migrate = yes` first;
  `gm_compute_totals` loses the `standing`/`culture` scale calls for now; `gm_state_local_steps_one` loses
  `multiply = gm_policy_factor_local`)
- Modify: `common/scripted_effects/gm_signature_effects.txt` (`gm_sig_set_steps` loses its scale call;
  `gm_sig_set_steps_lin_open` keeps a call for Task 4; `gm_state_sig_local_steps_one` takes `FACTOR`, see below)
- Modify: `common/script_values/gm_values.txt` (delete `gm_policy_factor_standing`, `_local` and `_age`;
  `gm_state_age_step` loses `multiply = gm_policy_factor_age`)
- Modify: `common/script_values/gm_monument_values.txt:100-116` (`gm_mon_age_step` loses its Mothballed branch)
- Modify: `common/on_actions/monument_events_on_actions.txt:26-45` (no Mothballed gate, no Open weight)
- Modify: `common/scripted_guis/gm_sguis.txt:285-420` (four sguis: `gm_policy_open_sgui`, `gm_policy_ceremonial_sgui`,
  `gm_policy_culture_sgui`, `gm_policy_education_sgui`)
- Modify: `common/customizable_localization/gm_custom_loc.txt:2982-3025` (`gm_policy_name`, `gm_policy_effects`)
- Modify: `gui/journal_entry_widgets/grand_monuments_widget.gui:2443-2467` (the button order)
- Modify: `localization/english/te_miscellaneous_l_english.yml` (the `gm_policy_*`, `gm_button_policy_*` and
  `gm_je_how_policy` keys)
- Test: `test_grand_monument_registry.py` `PolicyTests` (line 2931); `test_grand_monuments_layout.py` (lines 386, 884)

**Interfaces:**
- Produces:
  - `gm_policy_is = { P = culture STANDARD = yes }` is the default;
  - `P = open|ceremonial|education STANDARD = no`;
  - `gm_policy_migrate` (country scope);
  - `gm_state_sig_local_steps_one = { SIG = <key> FACTOR = <script value or literal> }`;
  - the sgui names above;
  - loc keys `gm_policy_<p>`, `gm_policy_effects_<p>`, `gm_button_policy_<p>`, `gm_button_policy_<p>_tooltip` and
    `gm_policy_<p>_effect_tt` for the four.
- Consumes: Task 2's deletion of `gm_policy_factor_upkeep`.

- [ ] **Step 1: Write the failing tests.**
  - Replace `POLICIES` with the four keys. Each lists its default flag: `STANDARD = yes` only for `culture`.
  - `test_buttons_and_cooldown` iterates the new keys. `FACTOR_VALUES` and `test_factors_match_the_table` shrink to
    `tourism`: 1.5 under `open` and 1 under the other three. `gm_policy_factor_tourism`'s ×0.5 branch names
    `mothballed`, so it goes in this task. Task 4 restores the rest of the table.
  - Layout test: `self.assertEqual(order, ["open", "ceremonial", "culture", "education"])`.
  - Add:

```python
def test_migration_drops_old_flags_only(self):
    body = squash(block(self.e, "gm_policy_migrate"))
    for old in ("mothballed", "standard"):
        self.assertIn(f"var:gm_policy = flag:{old}", body)
    self.assertIn("remove_variable = gm_policy", body)
    for kept in ("gm_policy_cooldown", "gm_policy_chosen"):
        self.assertNotIn(kept, body)          # Review Focus 1
    self.assertTrue(squash(block(read(EFFECTS), "gm_country_refresh")).startswith("gm_policy_migrate = yes"))

def test_no_policy_reads_the_old_keys(self):
    for path in ROOT.glob("common/**/*.txt"):
        text = strip_comments(read(path.relative_to(ROOT).as_posix()))
        if path.name == "gm_policy_effects.txt":
            text = text.replace(block(text, "gm_policy_migrate"), "")
        self.assertNotRegex(text, r"P = (mothballed|standard)\b|flag:(mothballed|standard)\b", path)
        self.assertNotRegex(text, r"gm_policy_factor_(standing|local|age|upkeep)\b", path)

def test_anniversaries_ignore_the_policy(self):
    self.assertNotIn("gm_policy_is", squash(block(read(ON_ACTIONS), "monument_events_on_action")))

def test_signature_local_steps_take_a_factor(self):
    monthly = squash(block(read(EFFECTS), "gm_state_monthly"))
    self.assertIn("gm_state_sig_local_steps_one = { SIG = antiquity FACTOR = gm_policy_factor_tourism }", monthly)
    self.assertIn("gm_state_sig_local_steps_one = { SIG = first_emperor FACTOR = gm_policy_factor_tourism }", monthly)
    self.assertIn("gm_state_sig_local_steps_one = { SIG = archive FACTOR = 1 }", monthly)
```

  Delete `test_anniversaries` and the layout test's `multiply = gm_policy_factor_local` assertion, and keep the line's
  other check.
- [ ] **Step 2:** Run `$PY test_grand_monument_registry.py -k Policy` and `$PY test_grand_monuments_layout.py -k Policy`.
  Expected: FAIL (old keys and old sguis).
- [ ] **Step 3: Implement.**
  - **`gm_policy_migrate`:** if `gm_policy` is `flag:mothballed` or `flag:standard`, remove it, and do nothing else.
  - **The sguis:** `culture`'s current-policy check is `NOT = { gm_policy_is = { P = culture STANDARD = yes } }`. The
    other three use `STANDARD = no`. Delete the standard and mothballed sguis.
  - **Custom loc:** the fall-through text is `culture`.
  - **Loc:** one-line effects, from the spec's § 3 table. Culture's effect names pull with the rule on and prestige
    with it off. The choice is made in script, never in the GUI: two keys (`gm_policy_culture_effect_tt` and
    `gm_policy_culture_prestige_effect_tt`) behind an `if` on `has_game_rule = cultural_hegemony_enabled` in the
    sgui's effect, and a matching trigger in the `gm_policy_effects` custom loc. Adjust `test_buttons_and_cooldown`'s
    exact `custom_tooltip` string for `culture` to match. Delete the standard and mothballed keys, and any stale copy
    in `te_unused_l_english.yml`. `gm_je_how_policy` describes the four in a paragraph.
  - **`gm_state_sig_local_steps_one`:** multiplies by `$FACTOR$` in place of `gm_policy_factor_local`.
  - **The AI chooser** keeps its current shape, with flags swapped (`mothballed` → `education`,
    `standard` → `culture`), until Task 7.
- [ ] **Step 4:** Run `$PY test_grand_monument_registry.py -k "Policy or Upkeep"`,
  `$PY test_grand_monuments_layout.py`, `$PY scripts/analysis/check_gui_lint.py`,
  `$PY script_argument_audit.py --strict` and `$PY organize_loc.py --check`. Expected: all pass.
- [ ] **Step 5: Commit** "Grand Monuments: four monument policies; Mothballed and Standard go".

### Task 4: Open and Cultural Promotion's factors

**Files:**
- Modify: `common/script_values/gm_values.txt` (new `gm_policy_factor_culture` and `gm_policy_factor_prestige`;
  `gm_policy_factor_tourism` is already final from Task 3)
- Modify: `common/scripted_effects/gm_effects.txt` (`gm_compute_totals`: scale `standing` by `_prestige`, `culture` by
  `_culture`)
- Modify: `common/scripted_effects/gm_signature_effects.txt` (`gm_sig_set_steps_lin_open` scales by `_culture`)
- Test: `test_grand_monument_registry.py` `PolicyTests`

**Interfaces:**
- Produces:
  - `gm_policy_factor_tourism` (state scope, owner's policy): 1.5 under `open`, else 1.
  - `gm_policy_factor_culture` (country scope): 1.5 under `culture` with `has_game_rule = cultural_hegemony_enabled`,
    else 1.
  - `gm_policy_factor_prestige` (country scope): 1.5 under `culture` without that rule, else 1.
- Consumes: Task 3's keys.

- [ ] **Step 1: Write the failing test.** `POLICIES` grows the columns back:

```python
POLICIES = {
    "open": {"tourism": 1.5, "culture": 1, "prestige": 1},
    "ceremonial": {"tourism": 1, "culture": 1, "prestige": 1},
    "culture": {"tourism": 1, "culture": 1.5, "prestige": 1.5},   # one or the other, by the rule
    "education": {"tourism": 1, "culture": 1, "prestige": 1},
}

def test_cultural_promotion_follows_the_rule(self):          # Review Focus 5
    culture = squash(block(self.values, "gm_policy_factor_culture"))
    prestige = squash(block(self.values, "gm_policy_factor_prestige"))
    self.assertIn("has_game_rule = cultural_hegemony_enabled", culture)
    self.assertIn("NOT = { has_game_rule = cultural_hegemony_enabled }", prestige)
    totals = squash(block(read(EFFECTS), "gm_compute_totals"))
    self.assertIn("gm_policy_scale_steps = { S = standing FACTOR = gm_policy_factor_prestige }", totals)
    self.assertIn("gm_policy_scale_steps = { S = culture FACTOR = gm_policy_factor_culture }", totals)
    sig = squash(block(read(SIG_EFFECTS), "gm_sig_set_steps_lin_open"))
    self.assertIn("FACTOR = gm_policy_factor_culture", sig)
```

  `_policy_value` needs to ignore the rule clause when it reads a factor's value under a key. The builder adapts the
  helper.
- [ ] **Step 2:** Run `$PY test_grand_monument_registry.py -k Policy`. Expected: FAIL.
- [ ] **Step 3: Implement** the three values and the three scale calls. Comments cite the spec § 4.1 and § 4.3.
- [ ] **Step 4:** Run `$PY test_grand_monument_registry.py -k "Policy or Signature"`. Expected: PASS.
- [ ] **Step 5: Commit** "Grand Monuments: Open's tourism, and Cultural Promotion's pull or prestige".

### Task 5: State Ceremonial counts a quarter of every venue

**Files:**
- Modify: `common/scripted_triggers/monument_triggers.txt` (new `gm_state_counts_venue`), and the container twin next
  to `gm_mon_counts_standing` (new `gm_mon_counts_venue`)
- Modify: `common/script_values/gm_values.txt`:
  - new `gm_policy_ceremonial_share = 0.25`;
  - new `gm_sum_venues`;
  - `gm_disp_frac_legitimacy` and `gm_disp_frac_leader` read the `_in` variables;
  - new `gm_display_g_ceremonial`;
  - delete `gm_policy_factor_regime`.
- Modify: `common/scripted_effects/gm_effects.txt` (`gm_compute_totals`)
- Modify: `localization/english/te_miscellaneous_l_english.yml` (`gm_je_tt_legitimacy`, `gm_je_tt_leader`, a
  ceremonies line)
- Test: `test_grand_monument_registry.py` `PolicyTests`; `test_grand_monuments_layout.py` (the frac tests)

**Interfaces:**
- Produces (country variables written each refresh):
  - `gm_g_venues` (V, under every policy);
  - `gm_g_ceremonial` (V × share under `ceremonial`, else 0);
  - `gm_g_regime_in` = `gm_g_regime` + `gm_g_ceremonial`;
  - `gm_g_leader_in` = `gm_g_leader` + `gm_g_ceremonial`.

  The legitimacy curve reads `gm_g_regime_in`, and the authority curve reads `gm_g_leader_in`.
- Consumes: Task 3's keys.

- [ ] **Step 1: Write the failing tests.**

```python
def test_ceremonial_adds_before_the_curve(self):
    totals = squash(block(read(EFFECTS), "gm_compute_totals"))
    self.assertIn("set_variable = { name = gm_g_venues value = gm_sum_venues }", totals)
    self.assertIn("gm_set_steps = { IN = gm_g_regime_in OUT = gm_s_regime NEXT = gm_n_regime F = 10 }", totals)
    self.assertIn("gm_set_steps = { IN = gm_g_leader_in OUT = gm_s_leader NEXT = gm_n_leader F = 5 }", totals)
    self.assertNotIn("FACTOR = gm_policy_factor_regime", totals)
    self.assertRegex(strip_comments(self.values), r"(?m)^gm_policy_ceremonial_share = 0\.25\s*$")

def test_venues(self):                                       # Review Focus 4
    trig = squash(block(read(TRIGGERS), "gm_state_counts_venue"))
    self.assertIn("gm_state_is_contested = no", trig)
    self.assertNotIn("gm_state_is_heritage = no", trig)
    venues = squash(block(self.values, "gm_sum_venues"))
    self.assertIn("gm_state_counts_venue = yes", venues)
    self.assertIn("gm_mon_counts_venue = yes", venues)
    self.assertIn("add = gm_tr_disp_held_grandeur", venues)

def test_rows_read_the_real_input(self):                     # Review Focus 3
    for frac, var in (("gm_disp_frac_legitimacy", "gm_g_regime_in"), ("gm_disp_frac_leader", "gm_g_leader_in")):
        self.assertIn(f"value = var:{var}", squash(block(self.values, frac)), frac)
    for key in ("gm_je_tt_legitimacy", "gm_je_tt_leader"):
        self.assertIn("gm_display_g_ceremonial", loc()[key], key)
```

  Update the layout test that pins `gm_disp_frac_legitimacy`'s body to the `_in` variable.
- [ ] **Step 2:** Run `$PY test_grand_monument_registry.py -k Policy` and `$PY test_grand_monuments_layout.py`.
  Expected: FAIL.
- [ ] **Step 3: Implement.**
  - **`gm_state_counts_venue`:** the state has `building_grand_monument`, is not contested, and is either dedicated or
    heritage. A comment says that once tourism heritage phase 2 adds `pm_monument_historic`, it joins at half
    (spec § 4.5).
  - **`gm_sum_venues`:** follows `gm_sum_standing`'s shape (primaries, `gm_monuments_held`, held trophies).
  - **The order in `gm_compute_totals`:** set `gm_g_regime`, `gm_g_leader` and `gm_g_venues`; then `gm_g_ceremonial`;
    then the two `_in` sums; then the curves.
  - **The tooltips:** a ceremonies line, shown when `gm_display_g_ceremonial > 0`, naming the share's grandeur. The
    "Next step at" figure reads the `_in` variable.
- [ ] **Step 4:** Run the two test files with `-k "Policy or Layout or Frac"`, then
  `$PY je_multiplier_scope_audit.py --strict`. Expected: PASS.
- [ ] **Step 5: Commit** "Grand Monuments: State Ceremonial counts a quarter of every monument".

### Task 6: Public Education

**Files:**
- Modify: `common/static_modifiers/gm_modifiers.txt` (new `gm_national_education`,
  `state_education_access_add = 0.01`)
- Modify: `common/script_values/gm_values.txt`:
  - new `gm_step_education = 0.01`;
  - `gm_display_education`;
  - `gm_disp_frac_education`;
  - `gm_disp_national_any` reads `gm_s_education`.
- Modify: `common/scripted_effects/gm_effects.txt`:
  - `gm_compute_totals`: `gm_set_steps_lin_open = { IN = gm_g_standing OUT = gm_s_education NEXT = gm_n_education
    WIDTH = gm_w_education F = 10 }` under `education`, else `gm_s_education` 0;
  - add and remove the modifier;
  - the self-check.
- Modify: `gui/journal_entry_widgets/grand_monuments_widget.gui` (a `gm_step_row` after the culture row)
- Modify: `localization/english/te_miscellaneous_l_english.yml` (`gm_je_lbl_education`, `gm_je_val_education`,
  `gm_je_tt_education`, the modifier's name)
- Create: `docs/testing/grand-monuments-policy-playtest.md` (its Self-checks table row here; the rest in Task 8)
- Test: `test_grand_monument_registry.py`; `test_grand_monuments_layout.py` (`FRACS`, `NationalEmptyStateTest`)

**Interfaces:**
- Produces: the variables `gm_s_education`, `gm_n_education` and `gm_w_education`; the modifier
  `gm_national_education`; the debug line `TE_SELF_CHECK OK|BROKEN gm_education_reaches_states`.
- Consumes: Task 3's `education` key.

- [ ] **Step 1: Write the failing tests.**

```python
self.assert_pair("gm_national_education", "state_education_access_add", "gm_step_education", 0.01)

def test_education_only_under_its_policy(self):              # Review Focus 2
    totals = squash(block(read(EFFECTS), "gm_compute_totals"))
    self.assertIn("OUT = gm_s_education", totals)
    self.assertIn("P = education STANDARD = no", totals)
    self.assertIn("set_variable = { name = gm_s_education value = 0 }", totals)
    self.assertIn("gm_add_national = { NAME = gm_national_education VAR = gm_s_education }",
                  squash(block(read(EFFECTS), "gm_apply_national_modifiers")))
    self.assertIn("remove_modifier = gm_national_education",
                  squash(block(read(EFFECTS), "gm_remove_national_modifiers")))
```

  Add `education` to the layout test's `FRACS`. `NationalEmptyStateTest` then requires
  `AND = { has_variable = gm_s_education NOT = { var:gm_s_education = 0 } }` in `gm_disp_national_any`.
- [ ] **Step 2:** Run `$PY test_grand_monument_registry.py -k "education or Policy"` and
  `$PY test_grand_monuments_layout.py`. Expected: FAIL.
- [ ] **Step 3: Implement.**
  - **The self-check:** once a game (a global flag), in a state of a country under `education` with
    `gm_s_education >= 1`, a month after the modifier went on. It reads the state's education access modifier and
    compares it with `owner.var:gm_s_education` × `gm_step_education`. The builder picks the read: `modifier:` in state
    scope if the engine docs show it works there, otherwise another observable.
    - It prints OK with both numbers. BROKEN names the fallback: add `gm_national_education` to the country instead
      of the JE, and give it its own `gen_nation_tab.py` row.
    - The Self-checks table row goes in the new play-test file.
  - **Loc:** the row's value reads "+N% education access".
- [ ] **Step 4:** Run both test files, `$PY test_nation_tab.py`, `$PY scripts/analysis/check_gui_lint.py` and
  `$PY scripts/analysis/loc_coverage_audit.py --strict` (or its CI command). Expected: PASS.
- [ ] **Step 5: Commit** "Grand Monuments: Public Education".

### Task 7: The AI picks among the four

**Files:**
- Modify: `common/scripted_effects/gm_policy_effects.txt` (`gm_policy_ai_choose`)
- Test: `test_grand_monument_registry.py` `PolicyTests.test_the_ai`

**Interfaces:**
- Consumes: `gm_g_regime`, `gm_g_venues` and `gm_policy_ceremonial_share` (Task 5); the four keys (Task 3).

- [ ] **Step 1: Write the failing test.** Rewrite `test_the_ai`:

```python
ai = squash(block(self.e, "gm_policy_ai_choose"))
for s_ in ("is_ai = yes", "month = 0", "gm_policy_can_change = yes",
           "set_variable = { name = gm_policy_pick value = flag:culture }",
           "government_legitimacy < 40", "literacy_rate < 0.5",
           "has_building = building_tourism_industry"):
    self.assertIn(s_, ai)
order = [ai.find(f"value = flag:{p} }}") for p in ("ceremonial", "open", "education")]
self.assertEqual(order, sorted(order))
self.assertNotIn("scaled_debt", ai)
self.assertNotIn("gm_country_hard_times", ai)
for p in ("open", "ceremonial", "culture", "education"):
    self.assertIn(f"gm_policy_ai_apply = {{ P = {p} STANDARD = {'yes' if p == 'culture' else 'no'} }}", ai)
```

- [ ] **Step 2:** Run `$PY test_grand_monument_registry.py -k test_the_ai`. Expected: FAIL.
- [ ] **Step 3: Implement.**
  - The pick starts at `culture`.
  - **Ceremonial** when `government_legitimacy < 40` and `gm_g_regime + gm_g_venues × gm_policy_ceremonial_share >= 10`
    (a script value, for example `gm_policy_ceremonial_input_if_chosen`).
  - Else **Open** when a monument stands with a Tourism Industry.
  - Else **Education** when `literacy_rate < 0.5`.
  - The comment cites spec § 7.
- [ ] **Step 4:** Run `$PY test_grand_monument_registry.py -k Policy`. Expected: PASS.
- [ ] **Step 5: Commit** "Grand Monuments: the AI's monument policy".

### Task 8: Docs, the guide and the play-test list

**Files:**
- Modify: `docs/player_guide/02-timeline.md`:
  - about lines 610–612: no maintenance;
  - line 757: ageing at one rate;
  - line 855: no "Mothballed halves them";
  - lines 1043–1062: the policy table and its AI paragraph;
  - line 1276: anniversaries;
  - the Prestige figures wherever the chapter gives +25.
- Modify: `docs/player_guide/Vic3TimelineExtended_Player_Guide.pdf` (rebuilt)
- Modify: `docs/systems/mod_systems.md` (the "Monument policy" bullet, line 1459; the ageing bullet's Mothballed
  clause, line 1462; the prestige figure)
- Modify: `docs/superpowers/archive/specs/2026-10-23-tourism-heritage-design.md`:
  - § 7: the To History rule from the policy spec § 4.5, with its upkeep line marked moot;
  - § 13: phase 2's gate is this pass;
  - § 15: resolved, and the Mothballed line corrected.
- Modify: `docs/testing/grand-monuments-policy-playtest.md` (the checks from spec § 11)
- Modify: `docs/testing/grand-monuments-ageing-playtest.md:36` (drop the Mothballed check)

- [ ] **Step 1:** Edit the chapter to the spec's § 3 table, at the depth that's there now (a table row per policy, one
  AI sentence). Run `$PY scripts/analysis/check_player_guide_style.py --strict`. Expected: clean.
- [ ] **Step 2:** Run `$PY scripts/build_player_guide.py`, then `$PY scripts/build_player_guide.py --check`. Expected:
  "up to date".
- [ ] **Step 3:** Edit `mod_systems.md`, the heritage spec, and the two play-test files.
- [ ] **Step 4: Final gate.** Run:
  - `$PY test_grand_monument_registry.py`, `$PY test_grand_monuments_layout.py`, `$PY test_grand_monument_trophies.py`,
    `$PY test_grand_monument_archaeology.py`, `$PY test_tourism_heritage.py`, `$PY test_nation_tab.py`,
    `$PY test_hidden_state_modifiers.py` and `$PY test_bom_normalizer.py`;
  - `$PY organize_loc.py --check`, `$PY scripts/analysis/check_localization_files.py`,
    `python3 scripts/format_paradox_tabs.py --check` on the changed `.txt` files, `$PY scripts/analysis/check_gui_lint.py`
    and `/home/jakef/src/Vic3TimelineExtended/.venv/bin/ruff check .`;
  - the `--strict` audits `loc_coverage`, `script_loc_reference`, `gui_reference`, `loc_render`,
    `modifier_multiplier_var`, `je_multiplier_scope`, `script_argument`, `duplicate_key` and `empty_effect`, with
    CI's dummy `VIC3_*` env vars where a module needs them.

  Expected: all pass.
- [ ] **Step 5: Commit** "Grand Monuments policy pass: guide, docs and play-test list".
