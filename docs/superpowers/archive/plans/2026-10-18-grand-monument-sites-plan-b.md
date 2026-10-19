# Grand Monuments: grandeur set by world wealth — Implementation Plan B

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A level's starting grandeur is world GDP in 1836 divided by world GDP the year it finishes, and every rule that counts what a monument means counts that grandeur, so the same share of the world's wealth buys the same grandeur in any era.

**Architecture:** One global rate, written each January. Plan A's site tracker (`gm_state_count_site_levels`) multiplies each new level by it, so the dedication records weighted grandeur with no other change. Opportunities, vanity and infamy move from levels to grandeur; the card, the panel and the build menu show the rate before a level is built. One PR, after Plan A's A2 has merged.

**Tech Stack:** as Plan A.

**Spec:** `docs/superpowers/archive/specs/2026-10-18-grand-monument-sites-and-world-wealth-design.md` (§3.2, §3.6, §5). Code map: `docs/superpowers/archive/plans/2026-10-18-gm-sites-inventory/C_levels_grandeur_upkeep.md` (opportunities §2, vanity and infamy §3, world GDP §4).

## Global Constraints

- Rate = `gm_world_gdp_1836` ÷ `global_gdp_script_value`, a global variable `gm_world_rate`, written on the January pass of `gm_monument_monthly` (`month = 0`, the `gw_rebase_annual_emissions_effect` pattern) and on any pass that finds it missing. No smoothing. Never above 1 in normal play; no clamp.
- `gm_world_gdp_1836` is a fixed constant (spec §5), the same for every save.
- Levels that existed before Plan B, landmarks, trophies, returns and digs keep starting grandeur = levels (the 1836 rate).
- Every Plan A constraint holds.

## Review Focus

1. **A site built across the January change** counts each level at the rate of the month it was counted, not at the rate of dedication day. Pinned in Task 2 (`RateTests.test_each_level_at_its_month`).
2. **Rate missing on load** (an old save, or a game started before Plan B): the first pass writes it before any site counts a level. Pinned in Task 1 (`RateTests.test_written_before_counting`).
3. **An opportunity late in the game** asks for grandeur; Raise It queues ceil(missing ÷ rate) levels, capped at what one `while` should queue (100), and the AI queues what's missing, not the whole target. Pinned in Task 3.
4. **Vanity in hard times** adds the grandeur a level added, so twenty modern levels worth one 1836 level draw one level's outrage. Pinned in Task 4.
5. **Fractional grandeur on screen:** a starting grandeur below 10 shows one decimal everywhere it's printed, and a step bar never divides by zero. Pinned in Task 5.

---

### Task 1: The rate and its baseline

**Files:** `common/script_values/gm_values.txt`, `common/scripted_effects/gm_monument_effects.txt` (`gm_monument_monthly`), `gm_effects.txt` (self-check); tests new `RateTests`.

**Interfaces — Produces:** `gm_world_gdp_1836` (script value, constant); `gm_world_rate` (global variable); `gm_world_rate_value` (script value: the global, 1 if missing).

- [ ] Measure the constant: world GDP (Σ every country's `gdp`) on 1836.1.1. Use the earliest save in the owner's save folder with the save decoder (`~/src/vic3te-save-analysis-2026-10-17`; `reference_save_file_reading` memory); if no 1836 save exists, ship a provisional constant from the nearest one, say which, and rely on the self-check below.
- [ ] Write `RateTests.test_written_before_counting` (`gm_monument_monthly` writes the rate before anything else when missing, and on `month = 0`), `test_rate_is_base_over_world`. FAIL. Implement.
- [ ] `TE_SELF_CHECK OK|BROKEN gm_world_base`: once, on a new game's first pass before 1836.2.1, log world GDP beside the constant; BROKEN when they differ by more than 10%.
- [ ] Run the four GM files: OK. Commit.

### Task 2: Sites count at the rate

**Files:** `gm_effects.txt` (`gm_state_count_site_levels`); tests `RateTests`.

- [ ] Write `test_each_level_at_its_month`: each new level adds `gm_world_rate_value` to `gm_site_grandeur`; a lost level scales it as Plan A did; site levels a merge brought with nothing to explain them count at the current rate. FAIL. Implement. Commit.

### Task 3: Opportunities in grandeur

**Files:** `common/script_values/gm_commission_values.txt`, `common/scripted_effects/gm_commission_effects.txt`, `common/scripted_triggers/gm_commission_triggers.txt`, `gm_monument_triggers.txt` (`gm_mon_com_counts`); tests `OpportunityLevelTests` (rename `OpportunityGrandeurTests`), `CommissionLifeTests`, `UsabilityTests`. Map: inventory C §2.

**Interfaces — Produces:** `gm_com_fit_grandeur` = Σ fitting `gm_state_primary_start` + `gm_mon_start` (never age); baseline and progress as today on it; `gm_com_levels_to_go` = ceil((target − progress) ÷ `gm_world_rate_value`), at most 100; raise and accept costs = that × 1000; `gm_com_ai_queue` queues `gm_com_levels_to_go`.

- [ ] Tests for each line above, plus `gm_com_pick_build_state` and `gm_com_fulfil` ordering by the same `gm_state_grandeur` they did. FAIL. Implement. Commit.

### Task 4: Vanity, infamy, anniversaries

**Files:** `gm_effects.txt` (`gm_state_vanity_backlash`, called from the site tracker), `common/script_values/gm_trophy_values.txt` (`gm_tr_infamy`, `gm_state_tr_infamy`; delete dead `gm_tr_infamy_of_trophy`), `gm_values.txt` / `gm_monument_values.txt` (`gm_evt_grandeur`, `gm_mon_evt_grandeur`), loc (`gm_je_how_hard_times`, `gm_tr_take_occupation_tt`); tests `VanityTests`, `AnniversaryAgeTests`, trophies `TakingTests`. Map: inventory C §3.

- [ ] Tests: in hard times the tracker adds the grandeur it counted to `gm_vanity_ledger` (radicals once a month when any level counted); infamy = (start grandeur + age taken) ÷ 5 + 2, at most 8, ×2 under UNESCO; an anniversary adds a tenth of starting grandeur, at least 1. FAIL. Implement. Commit.

### Task 5: Showing the rate

**Files:** `gui/te_state_panel_widgets.gui` (site block), `gui/journal_entry_widgets/grand_monuments_widget.gui` (National Effects), `common/buildings/grand_monument_site.txt` (a `possible` custom tooltip with `[SCOPE.ScriptValue('gm_world_rate_value')|2]`: the proven way to put a live number in the build tooltip, inventory D §4), loc, `gm_values.txt` (display values); tests layout, `StateCardTests`.

- [ ] The site block: "A level finished now adds X grandeur" and grandeur so far; the panel: the same line nationally; the build tooltip line. Decimals per Review Focus 5. Tests pin the three places and the format. FAIL. Implement. `check_gui_lint`, `gui_reference_audit --strict`, `loc_coverage_audit --strict`: OK. Commit.

### Task 6: Docs, guide, play-test list

- [ ] `mod_systems.md` § Grand Monuments: the rate, what counts levels and what counts grandeur. Player guide 02 (Grand monuments: cost and grandeur, opportunities, vanity) and 08 (the card's rate line), PDF rebuilt. Play-test list: the rate line in all three places (the build tooltip may not render: fallback is card and panel only), a site across January, a late opportunity's Raise It, the `gm_world_base` self-check. Final gate as Plan A Task 10. Open the PR (`--base main`; Player guide: chapters 02 and 08).
