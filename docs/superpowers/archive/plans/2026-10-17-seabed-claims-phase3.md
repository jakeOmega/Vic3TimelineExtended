# Seabed Claims, Phase 3 (navies and the rush) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Count naval power projection rather than fleet size toward seabed claims, let blockades cut Deep-Sea Mine output, and announce the seabed rush.

**Architecture:** Three independent script changes, each resting on an engine fact nobody has verified, so each ships the preferred version with a once-a-game `TE_SELF_CHECK` line or a play-test row naming its fallback (CLAUDE.md, "In-game checks"). The model needs no change: it takes the navy figure as an input.

**Tech Stack:** Victoria 3 Paradox script, notifications (`common/messages/`), localization YAML, Python `unittest`.

**Spec:** `docs/superpowers/archive/specs/2026-10-17-seabed-claims-and-panel-design.md` §§ 6, 7, 9. Independent of phases 1 and 2; if phase 1 has merged, Task 1 also updates the readout's unit text.

## Global Constraints

- Phase 1's Global Constraints on files, loc, BOM, tabs and Python 3.11 hold.
- Preferred version plus self-check, never a guess shipped silently: each task names its fallback in `docs/testing/global-commons-playtest.md`.
- Self-check lines: `TE_SELF_CHECK OK|BROKEN <name>` with the figures, once a game, excluding degenerate inputs (a country with no navy can't make OK pass).
- Notifications go only to countries that are not `decentralized`, as `te_seabed_un_regime_notices` does.

## Review Focus

1. **`naval_power_projection` can't be read as a number**: the weight's navy term would silently read 0 for everyone. Test: Task 1's self-check BROKEN branch, and the contract test that the fallback path exists in the play-test list.
2. **A country with no navy at all**: power projection 0 must not trip BROKEN. Test: Task 1 `test_self_check_excludes_no_navy`.
3. **A basin that fills and empties repeatedly**: "fully licensed" is sent once per filling, not every year it stays full. Test: Task 3 `test_full_notice_rearms_only_after_falling_below`.
4. **The first claimant appears in a game loaded mid-rush** (an old save already past the first research): no "rush begins" notice fires late. Test: Task 3 `test_rush_notice_skips_old_saves`.
5. **A newcomer in a basin where the receiver has no share** (no licences there, or it relinquished its claims and holds none): no notice. Test: Task 3 `test_new_claimant_notice_only_to_sharers`.

---

### Task 1: Naval power projection counts toward claim weight

**Files:**
- Modify: `common/script_values/te_global_commons_seabed_values.txt` (`te_seabed_navy_effective`, new `te_seabed_power_projection_scale`), `common/scripted_effects/te_global_commons_seabed_effects.txt` (self-check), `localization/english/te_miscellaneous_l_english.yml` (`te_seabed_how_weight`, `te_seabed_col_weight_tt`, and phase 1's `te_seabed_col_next_tt` if present), `scripts/analysis/seabed_model.py` (docstring: `Country.navy` is now the scaled power projection), `docs/testing/global-commons-playtest.md`
- Test: `test_seabed_script.py` (class `NavyMeasureTest`)

**Interfaces:**
- Produces: `te_seabed_power_projection_scale` (first estimate `5`: vanilla scales navy power projection modifiers up to 1,000 (`NAVY_POWER_PROJECTION_MODIFIER_MAX_SCALING`), a great power's fleet is ~100–300 flotillas); `te_seabed_navy_effective = naval_power_projection ÷ scale` (× the assertive multiplier as now); phase 1's stored readout `te_seabed_need_navy_<b>` is multiplied by `te_seabed_power_projection_scale` before display, so "+X" is raw naval power projection, the figure the military panel shows; effect `te_seabed_power_projection_check` (country, from the yearly pass, once a game) logging `TE_SELF_CHECK OK|BROKEN seabed_power_projection npp=<> navy_size=<> ratio=<>`.

- [ ] **Step 1: Engine check, offline.** Search `docs/engine/` and `~/src/vic3/game` for `naval_power_projection` read as a value (a script value's `value =` / `add =`, or a `.ScriptValue`-style read). Vanilla uses it only as a comparison operand (`ryukyu_rivalry_buttons.txt:403`, `static_treaty_acceptance.txt:270`). If the mod state server is up, `curl -s localhost:8950/engine-docs/origin/naval_power_projection`. Record the finding in the play-test list's "Engine facts the build assumes, unverified" section either way.
- [ ] **Step 2: Write the failing tests**

```python
class NavyMeasureTest(unittest.TestCase):
    def test_power_projection_is_the_navy_term(self):
        body = strip_comments(block(read(VALUES), "te_seabed_navy_effective"))
        self.assertIn("naval_power_projection", body)
        self.assertIn("te_seabed_power_projection_scale", body)
        self.assertNotIn("navy_size", body)

    def test_scale_constant(self):
        self.assertEqual(literal(read(VALUES), "te_seabed_power_projection_scale"), 5)

    def test_self_check_excludes_no_navy(self):
        body = strip_comments(block(read(EFFECTS), "te_seabed_power_projection_check"))
        self.assertIn("navy_size > 0", body)
        self.assertIn("seabed_power_projection", body)

    def test_fallback_is_named(self):
        with open(os.path.join(REPO, "docs/testing/global-commons-playtest.md"), encoding="utf-8") as f:
            self.assertIn("seabed_power_projection", f.read())
```

- [ ] **Step 3: Run** `.venv/bin/python -m unittest test_seabed_script.NavyMeasureTest -v` — `FAILED`.
- [ ] **Step 4: Implement.** Self-check: the first yearly pass with a claimant whose `navy_size > 0`; OK when `naval_power_projection > 0`, BROKEN when it reads 0; print both and their ratio so the play-test can set the scale. Play-test row: BROKEN → revert `te_seabed_navy_effective` to `navy_size`; OK → set `te_seabed_power_projection_scale` to the logged median ratio. Loc says "naval power projection" where it said "navy".
- [ ] **Step 5: Run** `test_seabed_script`, `test_seabed_allocation` — `OK`.
- [ ] **Step 6: Commit** — `"Seabed: naval power projection counts toward claims"`

### Task 2: Blockades cut Deep-Sea Mine output

**Files:**
- Modify: `common/buildings/extra_buildings.txt` (`REPLACE_OR_CREATE:building_ocean_mine`: `city_type = city` → `port`), `docs/testing/global-commons-playtest.md`, `docs/player_guide/02-timeline.md` (one sentence), the PDF
- Test: `test_seabed_script.py` (class `BlockadeTest`)

- [ ] **Step 1: Write the failing test**

```python
class BlockadeTest(unittest.TestCase):
    def test_the_deep_sea_mine_is_a_port_building(self):
        body = block(read(BUILDINGS), "REPLACE_OR_CREATE:building_ocean_mine")
        self.assertIn("city_type = port", body)
```

- [ ] **Step 2: Run** — `FAILED`.
- [ ] **Step 3: Implement** the one-line change; keep `levels_per_mesh = -1`. Play-test rows: (a) blockade a state with Deep-Sea Mine levels and read the building's throughput breakdown for the blockade line (up to −75% at blockade level 1, `BLOCKADE_THROUGHPUT_IMPACT_SCALING`); (b) the state's map look is unchanged or acceptable. Fallback named in the row: a unit state modifier `te_seabed_blockaded` (`building_ocean_mine_throughput_add = -0.75`, already a registered type) applied from `on_monthly_pulse_state` with `multiplier = blockade_level`, its one refresh site. Guide: one sentence in the Deep-Sea Mine paragraph.
- [ ] **Step 4: Run** `test_seabed_script` — `OK`; rebuild the PDF and `build_player_guide.py --check`.
- [ ] **Step 5: Commit** — `"Seabed: blockades cut Deep-Sea Mine output"`

### Task 3: The rush, announced

**Files:**
- Create: `common/messages/te_global_commons_seabed_messages.txt`
- Modify: `common/scripted_effects/te_global_commons_seabed_effects.txt` (`te_seabed_global_monthly`, `te_seabed_yearly_pass` after the sharing, `te_seabed_world_totals`), `localization/english/te_notifications_l_english.yml`
- Test: Create `test_seabed_notices.py`

**Interfaces:**
- Produces: messages `te_seabed_rush_notice`, `te_seabed_new_claimant_notice`, `te_seabed_basin_full_notice_<b>` (or one message with the basin named through a saved scope; builder's choice, loc must name the basin) in the `te_global_commons_un_messages.txt` shape (`type = country`, `notification_type = feed`); loc `notification_<msg>_name/_desc/_tooltip` (the existing pattern, e.g. `notification_te_seabed_regime_open_notice_*`); flags: global `te_seabed_rush_announced`, country `te_seabed_claimed_<b>` (first share > 0 there), global `te_seabed_full_<b>` (set when the world's licences reach the pool, cleared when below).

- [ ] **Step 1: Write the failing tests**

```python
class SeabedNoticeTest(unittest.TestCase):
    def test_rush_notice_once(self):
        body = strip_comments(block(read(EFFECTS), "te_seabed_global_monthly"))
        self.assertIn("te_seabed_rush_announced", body)
        self.assertIn("post_notification = te_seabed_rush_notice", body)

    def test_rush_notice_skips_old_saves(self):
        # an old save with a sharing already done sets the flag without posting
        body = strip_comments(block(read(EFFECTS), "te_seabed_global_monthly"))
        self.assertIn("has_global_variable = te_seabed_pass_year", body)

    def test_new_claimant_notice_only_to_sharers(self):
        body = strip_comments(read(EFFECTS))
        self.assertRegex(body, r"te_seabed_ent_\$B\$ > 0[\s\S]{0,400}post_notification = te_seabed_new_claimant_notice")

    def test_full_notice_rearms_only_after_falling_below(self):
        body = strip_comments(block(read(EFFECTS), "te_seabed_world_totals"))
        self.assertIn("te_seabed_full_$B$", body)
        self.assertIn("remove_global_variable = te_seabed_full_$B$", body)

    def test_loc(self):
        loc = read("localization/english/te_notifications_l_english.yml")
        for k in ("te_seabed_rush_notice", "te_seabed_new_claimant_notice"):
            for part in ("name", "desc", "tooltip"):
                self.assertIn(f"notification_{k}_{part}:", loc)
```

(Helpers imported from `test_seabed_script.py`.)

- [ ] **Step 2: Run** `.venv/bin/python -m unittest test_seabed_notices -v` — `FAILED`.
- [ ] **Step 3: Implement.** Rush: in `te_seabed_global_monthly`, the first month any claimant exists and no sharing has run (`NOT has_global_variable = te_seabed_pass_year`), post to every non-decentralized country; set the flag in either case. New claimant: after the five sharings, a country whose `te_seabed_ent_<b>` turned > 0 without `te_seabed_claimed_<b>` gets the flag, is saved as `scope:te_seabed_newcomer`, and every other participant with `te_seabed_ent_<b> > 0` is told (`[SCOPE.sCountry('te_seabed_newcomer').GetName]` names it, the colonial-notice pattern). Full: in `te_seabed_world_totals`, post to every claimant in the basin when records reach the pool and the flag is unset; clear the flag when below. Desc text names the basin and points to the Seabed tab.
- [ ] **Step 4: Run** `test_seabed_notices`, `test_seabed_script` — `OK`; `python3 loc_coverage_audit.py --strict` → exit 0.
- [ ] **Step 5: Commit** — `"Seabed: the rush, announced"`
