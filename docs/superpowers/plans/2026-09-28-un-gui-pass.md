# UN GUI Pass, Round 1: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the UN's panels a visual overview and a status-first layout, the same in the journal entry and the Diplomacy panel's UN tab.

**Architecture:** Script snapshots and display values expose everything the GUI shows as numbers on the viewer's country (country-scoped `un_disp_*` script values, and the `un_p5_seat_*` variables). The chamber and authority widgets are split into one type per section. A new layout file composes the sections in the agreed order, and both hosts instance that composition. A new overview type draws the icons, bars, pies, flags and agencies.

**Tech Stack:** Paradox Clausewitz/Jomini script (`common/`), `.gui` markup, YAML loc, Python `unittest` static tests.

**Spec:** `docs/superpowers/specs/2026-09-28-un-gui-pass-design.md`

## Global Constraints

- Work in the worktree `~/src/vic3te-banking-budget-tab` (branch `feat/banking-budget-tab`, PR #567). Never `POST /reload` from it. Run audits through a local ModState.
- Run Python from the main checkout's venv: `/home/jakef/src/Vic3TimelineExtended/.venv/bin/python`. Tests need CI's dummy paths: `VIC3_BASE_GAME=/nonexistent VIC3_MOD_DEPLOY_TARGET=/nonexistent VIC3_VANILLA_REPO=/nonexistent VIC3_VANILLA_DOCS_RUNTIME=/nonexistent VIC3_GAME_LOGS=/nonexistent`. Also move `paths.local.json` aside for the run and restore it afterwards (the scratchpad script `check_all.sh` does both).
- Every new `.gui` and `.txt` starts with a UTF-8 BOM. `.gui` and `.txt` use tab indentation.
- Placeholder art is vanilla textures referenced by path. Add no files under `gfx/`.
- Loc: `#b X#!`, never `[b]`. Use no ▲/▼ glyphs in loc; the trend icons are textures.
- The GUI never reads a variable that may be missing. Gate on a display value or an `is_shown`-only scripted GUI first (gotcha #23).
- A `visible` gate is never a saved scope reaching `is_shown` (gotcha #22). Use scope-free scripted GUIs, or `EqualTo_CFixedPoint` / `GreaterThanOrEqualTo_CFixedPoint` on a display value, in the form `EqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope.ScriptValue('x'), '(CFixedPoint)N' )` (precedent: `grand_monuments_widget.gui:105`).
- Never write two `visible` properties on one widget (gotcha #17). Wrap the widget instead.
- Display values read snapshots and the viewer's own variables only, never an `every_country` sweep: the panel re-renders every frame.
- Commits are staged by path (never `-a`) and end with the two attribution lines:
  `Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>` and
  `Claude-Session: https://claude.ai/code/session_014jF545581tAFTuaEJZKG2t`

## Review Focus

1. **No UN, or a dissolved one** (`un_founded` absent). The overview shows only the membership row ("No UN"), and no `global_var:` read fails. Pinned by Task 1's `test_every_global_read_is_guarded`, and by Task 3's check that rows 2–5 sit under `un_authority_ready_sgui`.
2. **A save from before this change,** or a UN before its first monthly update. There are no `un_p5_seat_*` variables, no `_prev` pillars and no shares yet. The seats show vacant, the trends show no change, and the pies show 0%. Pinned by the same guard test, plus Task 1's check that the seat count reads `var:un_p5_seat_count` behind `has_variable`.
3. **A permanent seat granted or lost mid-month** (event, vote, debug). The flags change at once. Pinned by Task 1's `test_every_seat_change_refreshes_the_council_display`.
4. **A resolution with no "no" vote yet** (`un_res_oppose` unset), and a supermajority topic. The tally bar draws all grey past the yes share, and the ⅔ mark shows only for the two supermajority topics. Pinned by Task 1's guard test (container reads under `has_variable`), and by Task 4's check that the mark is gated on `un_disp_res_supermajority`.
5. **Opening the tab the first time.** Dynamic sections are open and explanations are collapsed. Pinned by Task 2's flag-suffix test.

---

## File map

| File | Status | Responsibility |
|---|---|---|
| `common/script_values/un_overview_display_values.txt` | create | every `un_disp_*` value the overview, the session strip and the pillar bars read |
| `common/scripted_effects/un_overview_display_effects.txt` | create | `un_p5_display_refresh`, `un_p5_display_seat` |
| `common/script_values/un_authority_values.txt` | modify | world/member count, GDP and population values, the three share values |
| `common/scripted_effects/un_authority_effects.txt` | modify | `_prev` pillar copies, the share and eligible-count snapshots, the refresh call |
| `common/scripted_triggers/un_resolution_triggers.txt` | modify | `un_session_open`, `un_session_topic_is` |
| `common/scripted_guis/un_chamber_sguis.txt` | modify | membership, standing and tier tooltip builders; the session gate |
| seat sites (8, Task 1 Step 6) | modify | call `un_p5_display_refresh = yes` |
| `gui/journal_entry_widgets/un_chamber_widget.gui` | modify | one type per chamber section (no root widget) |
| `gui/journal_entry_widgets/un_authority_widget.gui` | modify | one type per authority section (no root widget); pillar bar rows |
| `gui/journal_entry_widgets/un_layout_widget.gui` | create | the order: `te_un_sec_assembly`, `te_un_status_sections`, `te_un_reference_sections`, the journal's named roots |
| `gui/journal_entry_widgets/un_overview_widget.gui` | create | `te_un_overview_panel` and its small types |
| `common/journal_entries/je_united_nations.txt` | modify | attach overview, status and reference to slots 1–3, and the marker to slot 7 |
| `gui/diplomatic_overview.gui` | modify | tab: header → overview → status → Actions → reference → link; the probe |
| `localization/english/te_journal_entries_l_english.yml` | modify | new `je_un_ov_*`, `je_un_assembly_*`, `je_un_tally_*`, `je_un_auth_bar_*` keys |
| `localization/english/te_diplomacy_l_english.yml` | modify | `te_diplomacy_un_tab_actions_header` |
| `test_un_overview_data.py` | create | seat refresh, agency coverage, pillar `_prev`, guarded reads, overview coverage |
| `test_un_layout.py` | create | section order, flag suffixes and semantics, session gating |
| docs (Task 6) | modify | `journal_entry_systems.md`, `gui_modding_guide.md`, the feasibility doc, the spec's status line |

---

### Task 1: Script data for the overview

**Files:**
- Create: `common/script_values/un_overview_display_values.txt`
- Create: `common/scripted_effects/un_overview_display_effects.txt`
- Modify: `common/script_values/un_authority_values.txt` (after `un_member_power_share_value`, ~line 137)
- Modify: `common/scripted_effects/un_authority_effects.txt` (step 3 of `un_authority_monthly_update`, ~lines 109–125, and the end of that effect)
- Modify: `common/scripted_triggers/un_resolution_triggers.txt` (end of file)
- Modify: `common/scripted_guis/un_chamber_sguis.txt` (`un_chamber_status_sgui` at ~line 35; add three handlers after it)
- Modify: the eight seat sites listed in Step 6
- Modify: `localization/english/te_journal_entries_l_english.yml`
- Test: `test_un_overview_data.py`

**Interfaces:**
- Produces script values (country scope; all 0 when their data is missing):
  - `un_disp_member_code`: 0 no UN · 1 cannot join · 2 can join · 3 member · 4 permanent member · 5 suspended with the seat carried · 6 suspended
  - `un_disp_tier_code`: −1 none, else 0–4
  - `un_disp_standing`, `un_disp_standing_frac`
  - `un_disp_authority_frac`, `un_disp_target_frac`
  - `un_disp_share_{countries,gdp,pop}` (0–1), `un_disp_share_{countries,gdp,pop}_pct`
  - `un_disp_p5_count`
  - `un_disp_agency_{who,unesco,icj,unhrc,iaea,unep,unhcr,unoosa,itlos,icc,cppnm}` (0/1)
  - for each p in participation, commitment, credibility, funding, order, delivery: `un_disp_pillar_<p>_pos` (0–1), `_neg` (−1–0), `_delta`, `_trend` (−1/0/1)
  - `un_disp_res_yes`, `un_disp_res_no`, `un_disp_res_eligible`, `un_disp_res_yes_frac`, `un_disp_res_no_frac`, `un_disp_res_not_no_frac`, `un_disp_res_months`, `un_disp_res_months_frac`, `un_disp_res_supermajority` (0/1), `un_disp_res_topic_code` (−1, or 0–17)
- Produces: the effect `un_p5_display_refresh`; country variables `un_p5_seat_1..5` (capital states) and `un_p5_seat_count`.
- Produces: the triggers `un_session_open` and `un_session_topic_is = { TOPIC = x }`.
- Produces scripted GUIs (scope = country): `un_chamber_status_sgui` (membership lines, every state), `un_chamber_standing_sgui`, `un_overview_tier_sgui`, and `un_session_open_sgui` (`is_shown` only).
- Consumes (existing): `un_disp_authority`, `un_disp_target`, `un_disp_pillar_<p>` (`un_authority_values.txt`), `un_prestige_order_value`, `un_vote_eligible_member_count`, `un_resolution_needs_supermajority`, `un_authority_ready_sgui`.

- [ ] **Step 1: Write the failing tests** (`test_un_overview_data.py`)

```python
"""Static checks for the UN overview's script data.

Spec: docs/superpowers/specs/2026-09-28-un-gui-pass-design.md, section 4.
"""
import glob
import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
DISPLAY = os.path.join(REPO, "common", "script_values", "un_overview_display_values.txt")
AUTH_EFFECTS = os.path.join(REPO, "common", "scripted_effects", "un_authority_effects.txt")
UN_VALUES = os.path.join(REPO, "common", "script_values", "un_script_values.txt")
PILLARS = ("participation", "commitment", "credibility", "funding", "order", "delivery")

SEAT_CHANGE = re.compile(
    r"MODIFIER\s*=\s*un_permanent_member_modifier"
    r"|add_modifier\s*=\s*\{\s*name\s*=\s*un_permanent_member_modifier"
    r"|remove_modifier\s*=\s*un_permanent_member_modifier"
)


def _read(path):
    with open(path, encoding="utf-8-sig") as f:
        return f.read()


def _strip_comments(text):
    return "\n".join(line.split("#", 1)[0] for line in text.split("\n"))


def _top_blocks(text):
    """(name, body) for every top-level `name = { ... }`, comments removed."""
    text = _strip_comments(text)
    for m in re.finditer(r"^([\w.]+)\s*=\s*\{", text, re.M):
        depth, i = 0, m.end() - 1
        for j in range(i, len(text)):
            if text[j] == "{":
                depth += 1
            elif text[j] == "}":
                depth -= 1
                if depth == 0:
                    yield m.group(1), text[i + 1:j]
                    break


def _block(text, name):
    for n, body in _top_blocks(text):
        if n == name:
            return body
    raise AssertionError(f"no top-level block {name}")


class SeatRefreshTest(unittest.TestCase):
    def test_every_seat_change_refreshes_the_council_display(self):
        paths = glob.glob(os.path.join(REPO, "common", "scripted_effects", "*.txt"))
        paths += glob.glob(os.path.join(REPO, "events", "*.txt"))
        sites = 0
        for path in paths:
            for name, body in _top_blocks(_read(path)):
                if SEAT_CHANGE.search(body):
                    sites += 1
                    self.assertIn("un_p5_display_refresh = yes", body,
                                  f"{os.path.basename(path)}: {name} changes a permanent seat "
                                  "but does not call un_p5_display_refresh")
        self.assertGreaterEqual(sites, 7)


class DisplayValueTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.display = _read(DISPLAY)

    def test_every_counted_agency_has_a_display_value(self):
        agencies = re.findall(r"un_agency_(\w+)", _block(_read(UN_VALUES), "un_agency_count"))
        self.assertEqual(len(agencies), 11)
        for a in agencies:
            self.assertRegex(self.display, rf"(?m)^un_disp_agency_{a} = \{{")

    def test_every_pillar_has_bar_and_trend_values(self):
        for p in PILLARS:
            for suffix in ("pos", "neg", "delta", "trend"):
                self.assertRegex(self.display, rf"(?m)^un_disp_pillar_{p}_{suffix} = \{{")

    def test_every_global_read_is_guarded(self):
        """A global_var:X read sits in a block that first checks has_global_variable = X."""
        for name, body in _top_blocks(self.display):
            for var in set(re.findall(r"global_var:(\w+)", body)):
                self.assertIn(f"has_global_variable = {var}", body,
                              f"{name} reads global_var:{var} without checking it exists")
            for var in set(re.findall(r"\bvar:(\w+)", body)):
                self.assertIn(f"has_variable = {var}", body,
                              f"{name} reads var:{var} without checking it exists")


class MonthlySnapshotTest(unittest.TestCase):
    def test_each_pillar_keeps_last_months_value_before_the_snapshot(self):
        body = _block(_read(AUTH_EFFECTS), "un_authority_monthly_update")
        for p in PILLARS:
            prev = body.find(f"name = un_pillar_{p}_prev")
            snap = body.find(f"name = un_pillar_{p} value")
            self.assertGreaterEqual(prev, 0, f"no un_pillar_{p}_prev copy")
            self.assertLess(prev, snap, f"un_pillar_{p}_prev must be copied before the snapshot")

    def test_the_shares_and_the_council_are_refreshed_monthly(self):
        body = _block(_read(AUTH_EFFECTS), "un_authority_monthly_update")
        for g in ("un_member_country_share", "un_member_gdp_share", "un_member_pop_share",
                  "un_vote_eligible_count"):
            self.assertIn(f"name = {g} value", body)
        self.assertIn("un_p5_display_refresh = yes", body)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd ~/src/vic3te-banking-budget-tab && <dummy env> /home/jakef/src/Vic3TimelineExtended/.venv/bin/python -m unittest test_un_overview_data -v`
Expected: FAIL/ERROR (`FileNotFoundError` for the display values file; the seat-refresh assertion names the first site).

- [ ] **Step 3: Add the share values** to `common/script_values/un_authority_values.txt`, directly after `un_member_power_share_value`:

```
# Members' share of the world's countries, GDP and population, 0..1: the
# overview's three pies (gui/journal_entry_widgets/un_overview_widget.gui).
# Swept by the monthly update and read by the display from its snapshots
# (un_member_*_share), never here. A member is any country whose journal entry
# carries un_member_modifier, suspended or not.
un_world_country_count_value = {
	value = 0
	every_country = { add = 1 }
}
un_member_country_count_value = {
	value = 0
	every_country = {
		limit = { je:je_united_nations ?= { has_modifier = un_member_modifier } }
		add = 1
	}
}
un_world_gdp_value = {
	value = 0
	every_country = { add = gdp }
}
un_member_gdp_value = {
	value = 0
	every_country = {
		limit = { je:je_united_nations ?= { has_modifier = un_member_modifier } }
		add = gdp
	}
}
un_world_pop_value = {
	value = 0
	every_country = { add = total_population }
}
un_member_pop_value = {
	value = 0
	every_country = {
		limit = { je:je_united_nations ?= { has_modifier = un_member_modifier } }
		add = total_population
	}
}
un_member_country_share_value = {
	value = 0
	if = {
		limit = { un_world_country_count_value > 0 }
		value = un_member_country_count_value
		divide = un_world_country_count_value
	}
	min = 0
	max = 1
}
un_member_gdp_share_value = {
	value = 0
	if = {
		limit = { un_world_gdp_value > 0 }
		value = un_member_gdp_value
		divide = un_world_gdp_value
	}
	min = 0
	max = 1
}
un_member_pop_share_value = {
	value = 0
	if = {
		limit = { un_world_pop_value > 0 }
		value = un_member_pop_value
		divide = un_world_pop_value
	}
	min = 0
	max = 1
}
```

Validate `gdp` and `total_population` as country-scope values before relying on them: `curl -s 'http://localhost:8950/engine-docs/origin/total_population'` and the same for `gdp`. `extra_script_values.txt:299` already uses `add = total_population`. If either is not a script value, stop and report.

- [ ] **Step 4: Snapshot the pillars, shares and eligible count** in `un_authority_monthly_update` (`common/scripted_effects/un_authority_effects.txt`). Insert this immediately **before** the line `set_global_variable = { name = un_pillar_participation value = un_pillar_participation_value }`:

```
	# Last month's pillars, for the overview's trend icons (a pillar's change
	# since the previous snapshot; un_overview_display_values.txt).
	if = {
		limit = { has_global_variable = un_pillar_participation }
		set_global_variable = { name = un_pillar_participation_prev value = global_var:un_pillar_participation }
	}
	if = {
		limit = { has_global_variable = un_pillar_commitment }
		set_global_variable = { name = un_pillar_commitment_prev value = global_var:un_pillar_commitment }
	}
	if = {
		limit = { has_global_variable = un_pillar_credibility }
		set_global_variable = { name = un_pillar_credibility_prev value = global_var:un_pillar_credibility }
	}
	if = {
		limit = { has_global_variable = un_pillar_funding }
		set_global_variable = { name = un_pillar_funding_prev value = global_var:un_pillar_funding }
	}
	if = {
		limit = { has_global_variable = un_pillar_order }
		set_global_variable = { name = un_pillar_order_prev value = global_var:un_pillar_order }
	}
	if = {
		limit = { has_global_variable = un_pillar_delivery }
		set_global_variable = { name = un_pillar_delivery_prev value = global_var:un_pillar_delivery }
	}
```

Insert this immediately **after** the line `set_global_variable = { name = un_authority_target value = un_authority_target_value }`:

```
	# The overview's pies, and the tally bar's denominator (the members with a
	# vote, as un_vote_supermajority_passed counts them).
	set_global_variable = { name = un_member_country_share value = un_member_country_share_value }
	set_global_variable = { name = un_member_gdp_share value = un_member_gdp_share_value }
	set_global_variable = { name = un_member_pop_share value = un_member_pop_share_value }
	set_global_variable = { name = un_vote_eligible_count value = un_vote_eligible_member_count }
```

Append `un_p5_display_refresh = yes` as the last statement of `un_authority_monthly_update`, with the comment `# The Security Council's seats, for the overview's flags.`

- [ ] **Step 5: Create `common/scripted_effects/un_overview_display_effects.txt`** (with a BOM):

```
# ============================================================================
# UN OVERVIEW — the Security Council's seats for the GUI
# ============================================================================
# gui/journal_entry_widgets/un_overview_widget.gui draws a flag for each
# permanent member. The GUI can reach a country only through a stored state
# (gui_modding_guide.md gotcha #11: Var().GetCountry is unreliable, and
# Var('x').GetState.GetCountry is what the covert widget uses), so every player
# country holds the permanent members' capitals, most prestigious first, in
# un_p5_seat_1..5. un_p5_seat_count says how many are filled, so the GUI never
# reads a seat that is not set (gotcha #23).
#
# Called from un_authority_monthly_update and from every effect that grants or
# removes un_permanent_member_modifier; test_un_overview_data.py fails if a new
# seat site forgets it. Only players are written: nobody else looks.
# Scope: any
# ============================================================================

un_p5_display_refresh = {
	every_country = {
		limit = { is_player = yes }
		save_scope_as = un_p5_viewer
		remove_variable = un_p5_seat_1
		remove_variable = un_p5_seat_2
		remove_variable = un_p5_seat_3
		remove_variable = un_p5_seat_4
		remove_variable = un_p5_seat_5
		set_variable = { name = un_p5_seat_count value = 0 }
		un_p5_display_seat = { N = 1 POS = 0 }
		un_p5_display_seat = { N = 2 POS = 1 }
		un_p5_display_seat = { N = 3 POS = 2 }
		un_p5_display_seat = { N = 4 POS = 3 }
		un_p5_display_seat = { N = 5 POS = 4 }
	}
}

# Seat $N$ (1-5) gets the permanent member at position $POS$ ($N$ - 1) of the
# council's prestige order, when there are at least $N$. An ordered_ position
# past the end of the list clamps to the last element instead of skipping, so
# the count is checked first (un_chamber_council_in_line does the same).
# Scope: the viewer (scope:un_p5_viewer is set)
un_p5_display_seat = {
	if = {
		limit = {
			any_country = {
				is_un_permanent_member = yes
				count >= $N$
			}
		}
		ordered_country = {
			limit = { is_un_permanent_member = yes }
			order_by = un_prestige_order_value
			position = $POS$
			capital = { save_scope_as = un_p5_capital }
		}
		scope:un_p5_viewer = {
			set_variable = { name = un_p5_seat_$N$ value = scope:un_p5_capital }
			set_variable = { name = un_p5_seat_count value = $N$ }
		}
	}
}
```

- [ ] **Step 6: Call the refresh at every seat site.**
  - **The sites:** `common/scripted_effects/un_ladder_effects.txt` (lines ~536 and ~599), `un_membership_effects.txt` (~31), `un_seat_effects.txt` (~114), `un_state_effects.txt` (~227, the restore), `events/un_vote_events.txt` (~802), and `te_debug_un_effects.txt` (~62 and ~427).
  - **Where the call goes:** open each site and add `un_p5_display_refresh = yes` in the same top-level block, **after** the seat change and **outside** any `every_*` / `ordered_*` loop around it, so it runs once. If the change sits in a loop, put the call after the loop's closing brace.
  - **Check:** run `git grep -n "un_permanent_member_modifier" -- common/scripted_effects events | grep -v has_modifier` and confirm no site was missed. The Step 1 test enforces it.

- [ ] **Step 7: Add the session triggers** at the end of `common/scripted_triggers/un_resolution_triggers.txt`:

```
# A resolution is before the General Assembly: the chamber's session card and
# its tally and time bars (un_overview_display_values.txt). un_active_resolution
# is removed when the vote is archived (un_vote_effects.txt).
# Scope: any
un_session_open = {
	has_global_variable = un_active_resolution
	exists = global_var:un_active_resolution
}

# The resolution in session carries topic $TOPIC$ (the un_topic_<topic> tag).
# Scope: any
un_session_topic_is = {
	un_session_open = yes
	global_var:un_active_resolution = { has_tag = un_topic_$TOPIC$ }
}
```

- [ ] **Step 8: Create `common/script_values/un_overview_display_values.txt`** (with a BOM). Every `global_var:` / `var:` read sits behind a `has_global_variable` / `has_variable` of the same name in the same block (the Step 1 test).

```
# ============================================================================
# UN OVERVIEW — display values
# ============================================================================
# Read by gui/journal_entry_widgets/un_overview_widget.gui, un_layout_widget.gui
# (the session strip) and un_authority_widget.gui (the pillar bars). Rendered
# every frame the panels are open, so these read snapshots and the viewer's
# own variables only; the sweeps behind them run in un_authority_monthly_update.
# Every read is guarded: a save from before the overview, or a UN before its
# first monthly update, reads 0 (test_un_overview_data.py).
# Spec: docs/superpowers/specs/2026-09-28-un-gui-pass-design.md.
# Scope: country (the viewer)
# ============================================================================

# ---- Membership and tier -----------------------------------------------------

# 0 no UN · 1 cannot join · 2 can join · 3 member · 4 permanent member ·
# 5 suspended, the seat carried · 6 suspended. Same order of tests as
# un_chamber_status_sgui, which is the icon's tooltip.
un_disp_member_code = {
	value = 0
	if = {
		limit = { je:je_united_nations ?= { has_modifier = un_member_modifier } }
		value = 3
		if = {
			limit = { is_un_permanent_member = yes }
			value = 4
		}
		if = {
			limit = { un_representation_suspended = yes }
			value = 6
			if = {
				limit = { un_seat_carried = yes }
				value = 5
			}
		}
	}
	else_if = {
		limit = { has_global_variable = un_founded }
		value = 1
		if = {
			limit = { un_membership_eligible = yes }
			value = 2
		}
	}
}

# -1 while there is no tier (no UN, or before its first monthly update), else
# global_var:un_tier: 0 moribund, 1 contested, 2 established, 3 strong,
# 4 supranational (un_ladder_triggers.txt).
un_disp_tier_code = {
	value = -1
	if = {
		limit = {
			has_global_variable = un_founded
			has_global_variable = un_tier
		}
		value = global_var:un_tier
	}
}

un_disp_standing = {
	value = 0
	if = {
		limit = { has_variable = un_standing }
		value = var:un_standing
	}
}
un_disp_standing_frac = {
	value = un_disp_standing
	divide = 100
	min = 0
	max = 1
}

# ---- Authority ------------------------------------------------------------------

un_disp_authority_frac = {
	value = un_disp_authority
	divide = 100
	min = 0
	max = 1
}
un_disp_target_frac = {
	value = un_disp_target
	divide = 100
	min = 0
	max = 1
}

# ---- Members' share of the world (the three pies) -----------------------------

un_disp_share_countries = {
	value = 0
	if = {
		limit = { has_global_variable = un_member_country_share }
		value = global_var:un_member_country_share
	}
}
un_disp_share_gdp = {
	value = 0
	if = {
		limit = { has_global_variable = un_member_gdp_share }
		value = global_var:un_member_gdp_share
	}
}
un_disp_share_pop = {
	value = 0
	if = {
		limit = { has_global_variable = un_member_pop_share }
		value = global_var:un_member_pop_share
	}
}
un_disp_share_countries_pct = {
	value = un_disp_share_countries
	multiply = 100
}
un_disp_share_gdp_pct = {
	value = un_disp_share_gdp
	multiply = 100
}
un_disp_share_pop_pct = {
	value = un_disp_share_pop
	multiply = 100
}

# ---- Security Council -----------------------------------------------------------

# How many of un_p5_seat_1..5 are set (un_p5_display_refresh). Seat N is drawn
# when this is at least N.
un_disp_p5_count = {
	value = 0
	if = {
		limit = { has_variable = un_p5_seat_count }
		value = var:un_p5_seat_count
	}
}

# ---- Agencies (the un_agency_count list, un_script_values.txt) ------------------

un_disp_agency_who = {
	value = 0
	if = { limit = { has_global_variable = un_agency_who } value = 1 }
}
un_disp_agency_unesco = {
	value = 0
	if = { limit = { has_global_variable = un_agency_unesco } value = 1 }
}
un_disp_agency_icj = {
	value = 0
	if = { limit = { has_global_variable = un_agency_icj } value = 1 }
}
un_disp_agency_unhrc = {
	value = 0
	if = { limit = { has_global_variable = un_agency_unhrc } value = 1 }
}
un_disp_agency_iaea = {
	value = 0
	if = { limit = { has_global_variable = un_agency_iaea } value = 1 }
}
un_disp_agency_unep = {
	value = 0
	if = { limit = { has_global_variable = un_agency_unep } value = 1 }
}
un_disp_agency_unhcr = {
	value = 0
	if = { limit = { has_global_variable = un_agency_unhcr } value = 1 }
}
un_disp_agency_unoosa = {
	value = 0
	if = { limit = { has_global_variable = un_agency_unoosa } value = 1 }
}
un_disp_agency_itlos = {
	value = 0
	if = { limit = { has_global_variable = un_agency_itlos } value = 1 }
}
un_disp_agency_icc = {
	value = 0
	if = { limit = { has_global_variable = un_agency_icc } value = 1 }
}
un_disp_agency_cppnm = {
	value = 0
	if = { limit = { has_global_variable = un_agency_cppnm } value = 1 }
}

# ---- Pillars (the bars in "Why authority is moving") ----------------------------
# Each bar is vanilla's double_direction_progressbar: the left half takes a
# -1..0 fraction, the right half 0..1. A pillar is scaled by the larger end of
# its own range (un_authority_values.txt), so zero is always the centre line.
# _trend is 1 / -1 when the pillar moved more than a twentieth of a point since
# last month's snapshot (un_pillar_<p>_prev), else 0.

un_disp_order_span = {
	value = un_order_floor
	multiply = -1
}
```

For each pillar p with span S from this table, append the same four values:

| p | S |
|---|---|
| participation | `un_participation_weight` |
| commitment | `un_commitment_weight` |
| credibility | `un_credibility_cap` |
| funding | `un_funding_pillar_max` |
| order | `un_disp_order_span` |
| delivery | `un_delivery_cap` |

The four values, written out for credibility; repeat them for every row of the table with p and S substituted:

```
un_disp_pillar_credibility_pos = {
	value = un_disp_pillar_credibility
	divide = un_credibility_cap
	min = 0
	max = 1
}
un_disp_pillar_credibility_neg = {
	value = un_disp_pillar_credibility
	divide = un_credibility_cap
	min = -1
	max = 0
}
un_disp_pillar_credibility_delta = {
	value = 0
	if = {
		limit = {
			has_global_variable = un_pillar_credibility
			has_global_variable = un_pillar_credibility_prev
		}
		value = global_var:un_pillar_credibility
		subtract = global_var:un_pillar_credibility_prev
	}
}
un_disp_pillar_credibility_trend = {
	value = 0
	if = {
		limit = { un_disp_pillar_credibility_delta > 0.05 }
		value = 1
	}
	else_if = {
		limit = { un_disp_pillar_credibility_delta < -0.05 }
		value = -1
	}
}
```

Then the session values:

```
# ---- The resolution in session (the General Assembly's tally and time bars) -----
# The tally bar spans the members with a vote (global_var:un_vote_eligible_count,
# snapshotted monthly from un_vote_eligible_member_count: the denominator the
# supermajority rule uses). Three stacked bars draw it: red to 1, grey to
# not_no_frac, green to yes_frac.

un_disp_res_eligible = {
	value = 1
	if = {
		limit = {
			has_global_variable = un_vote_eligible_count
			global_var:un_vote_eligible_count > 0
		}
		value = global_var:un_vote_eligible_count
	}
}
un_disp_res_yes = {
	value = 0
	if = {
		limit = {
			has_global_variable = un_active_resolution
			un_session_open = yes
		}
		global_var:un_active_resolution = {
			if = {
				limit = { has_variable = un_res_support }
				add = var:un_res_support
			}
		}
	}
}
un_disp_res_no = {
	value = 0
	if = {
		limit = {
			has_global_variable = un_active_resolution
			un_session_open = yes
		}
		global_var:un_active_resolution = {
			if = {
				limit = { has_variable = un_res_oppose }
				add = var:un_res_oppose
			}
		}
	}
}
un_disp_res_yes_frac = {
	value = un_disp_res_yes
	divide = un_disp_res_eligible
	min = 0
	max = 1
}
un_disp_res_no_frac = {
	value = un_disp_res_no
	divide = un_disp_res_eligible
	min = 0
	max = 1
}
un_disp_res_not_no_frac = {
	value = 1
	subtract = un_disp_res_no_frac
}

# Months in session, of the twelve a vote runs (un_vote.2 fires 365 days after
# the resolution opens; un_vote_effects.txt).
un_disp_res_months = {
	value = 0
	if = {
		limit = {
			has_global_variable = un_active_resolution
			un_session_open = yes
		}
		global_var:un_active_resolution = {
			if = {
				limit = { has_variable = un_res_months }
				add = var:un_res_months
			}
		}
	}
}
un_disp_res_months_frac = {
	value = un_disp_res_months
	divide = 12
	min = 0
	max = 1
}

un_disp_res_supermajority = {
	value = 0
	if = {
		limit = {
			has_global_variable = un_active_resolution
			un_session_open = yes
			global_var:un_active_resolution = { un_resolution_needs_supermajority = yes }
		}
		value = 1
	}
}

# The topic, in the proposal op order (un_chamber_propose_sgui): 0 condemn,
# 1 sanctions, 2 expulsion, 3 military_mandate, 4 peacekeeping_request,
# 5 aid_request, 6 reform, 7 human_rights, 8 icc, 9 npt, 10 climate,
# 11 pandemic, 12 refugee, 13 heritage, 14 decolonization, 15 space,
# 16 law_of_sea, 17 physical_protection. -1 with nothing in session.
un_disp_res_topic_code = {
	value = -1
	if = { limit = { un_session_topic_is = { TOPIC = condemn } } value = 0 }
	if = { limit = { un_session_topic_is = { TOPIC = sanctions } } value = 1 }
	if = { limit = { un_session_topic_is = { TOPIC = expulsion } } value = 2 }
	if = { limit = { un_session_topic_is = { TOPIC = military_mandate } } value = 3 }
	if = { limit = { un_session_topic_is = { TOPIC = peacekeeping_request } } value = 4 }
	if = { limit = { un_session_topic_is = { TOPIC = aid_request } } value = 5 }
	if = { limit = { un_session_topic_is = { TOPIC = reform } } value = 6 }
	if = { limit = { un_session_topic_is = { TOPIC = human_rights } } value = 7 }
	if = { limit = { un_session_topic_is = { TOPIC = icc } } value = 8 }
	if = { limit = { un_session_topic_is = { TOPIC = npt } } value = 9 }
	if = { limit = { un_session_topic_is = { TOPIC = climate } } value = 10 }
	if = { limit = { un_session_topic_is = { TOPIC = pandemic } } value = 11 }
	if = { limit = { un_session_topic_is = { TOPIC = refugee } } value = 12 }
	if = { limit = { un_session_topic_is = { TOPIC = heritage } } value = 13 }
	if = { limit = { un_session_topic_is = { TOPIC = decolonization } } value = 14 }
	if = { limit = { un_session_topic_is = { TOPIC = space } } value = 15 }
	if = { limit = { un_session_topic_is = { TOPIC = law_of_sea } } value = 16 }
	if = { limit = { un_session_topic_is = { TOPIC = physical_protection } } value = 17 }
}
```

Before relying on the topic list, confirm the `un_topic_condemn`, `un_topic_sanctions` and `un_topic_military_mandate` tags: `git grep -n "un_resolution_open = { TOPIC" -- common events`.

The session values name `has_global_variable = un_active_resolution` in their limits, although `un_session_open` already checks it, so the guard test sees the check where the read is.

- [ ] **Step 9: Tooltip builders and the session gate** in `common/scripted_guis/un_chamber_sguis.txt`.
  - Replace the body of `un_chamber_status_sgui` (~line 35) with the version below. It prints the membership line for every state, and no longer prints the standing block, which moves to its own builder.
  - Add the three new handlers right after it.

```
un_chamber_status_sgui = {
	scope = country

	effect = {
		if = {
			limit = { je:je_united_nations ?= { has_modifier = un_member_modifier } }
			# §0.8: a member whose representation is suspended is told so, and
			# whether its overlord carries its seat.
			if = {
				limit = { un_representation_suspended = yes }
				if = {
					limit = { un_seat_carried = yes }
					custom_tooltip_no_bullet = je_un_chamber_status_suspended_carried
				}
				else = {
					custom_tooltip_no_bullet = je_un_chamber_status_suspended
				}
			}
			else_if = {
				limit = { is_un_permanent_member = yes }
				custom_tooltip_no_bullet = je_un_chamber_status_permanent
			}
			else = {
				custom_tooltip_no_bullet = je_un_chamber_status_member
			}
		}
		else_if = {
			limit = { NOT = { has_global_variable = un_founded } }
			custom_tooltip_no_bullet = je_un_ov_status_no_un
		}
		else_if = {
			limit = { NOT = { un_membership_eligible = yes } }
			custom_tooltip_no_bullet = je_un_status_not_eligible
		}
		else = {
			custom_tooltip_no_bullet = je_un_chamber_status_nonmember
		}
	}
}

# Our international standing: the overview's standing meter's tooltip.
un_chamber_standing_sgui = {
	scope = country

	effect = {
		un_standing_status_block = yes
	}
}

# The authority tier's line, as the journal entry's status_desc words it: the
# overview's tier icon's tooltip.
un_overview_tier_sgui = {
	scope = country

	effect = {
		if = {
			limit = { un_tier_is_supranational = yes }
			custom_tooltip_no_bullet = je_un_tier_line_supranational
		}
		else_if = {
			limit = { un_tier_at_least_strong = yes }
			custom_tooltip_no_bullet = je_un_tier_line_strong
		}
		else_if = {
			limit = { un_tier_at_least_established = yes }
			custom_tooltip_no_bullet = je_un_tier_line_established
		}
		else_if = {
			limit = { un_tier_at_least_contested = yes }
			custom_tooltip_no_bullet = je_un_tier_line_contested
		}
		else_if = {
			limit = { un_tier_is_moribund = yes }
			custom_tooltip_no_bullet = je_un_tier_line_moribund
		}
	}
}

# Scope-free gate: a resolution is in session. The General Assembly shows its
# tally, delegations and ballot, or, when this is false, the proposals.
un_session_open_sgui = {
	scope = country
	is_shown = { un_session_open = yes }
	ai_is_valid = { always = no }
	is_valid = { always = no }
	effect = { }
}
```

Search for other callers of `un_chamber_status_sgui`: `git grep -n "un_chamber_status_sgui" -- gui`. Its only caller today is the chamber's top panel, whose standing and council rows Task 2 removes, so none needs the standing block any more.

- [ ] **Step 10: Loc.** Add to `localization/english/te_journal_entries_l_english.yml`, next to the other `je_un_` keys:

```
 je_un_ov_status_no_un:0 "#v There is no [concept_un].#! None has been founded, or the last one was dissolved.\n"
```

(Task 3 adds the overview's labels.) Then run `/home/jakef/src/Vic3TimelineExtended/.venv/bin/python organize_loc.py`.

- [ ] **Step 11: Run the tests.**

Run: `<dummy env> /home/jakef/src/Vic3TimelineExtended/.venv/bin/python -m unittest test_un_overview_data -v`
Expected: PASS (6 tests).

Then run the full suite and the checks: `SKIP_TESTS= <scratchpad>/check_all.sh`. The file list in its tab check must include the two new `.txt` files; they are tracked once staged, so stage them first. Expected: suite OK, every check exits 0, and the three local audits report 0 unreviewed. If `effect_trigger_validity_audit` flags `gdp`, `total_population`, `un_prestige_order_value` or `count >=`, fix that before continuing.

- [ ] **Step 12: Commit**

```bash
git add common/script_values/un_overview_display_values.txt common/scripted_effects/un_overview_display_effects.txt \
  common/script_values/un_authority_values.txt common/scripted_effects/un_authority_effects.txt \
  common/scripted_triggers/un_resolution_triggers.txt common/scripted_guis/un_chamber_sguis.txt \
  <the eight seat-site files> localization/english/*.yml test_un_overview_data.py
git commit -m "UN overview data: display values, pillar trends, member shares, council seats"
```

---

### Task 2: One type per section, and one layout for both hosts

**Files:**
- Modify: `gui/journal_entry_widgets/un_chamber_widget.gui` (replace `te_un_chamber_panel` and the root wrapper)
- Modify: `gui/journal_entry_widgets/un_authority_widget.gui` (replace `te_un_authority_panel` and the root wrapper)
- Create: `gui/journal_entry_widgets/un_layout_widget.gui`
- Modify: `common/journal_entries/je_united_nations.txt` (the two `widget = { … }` blocks, lines ~11–25)
- Modify: `gui/diplomatic_overview.gui` (the UN tab's datacontext flowcontainer)
- Modify: `localization/english/te_journal_entries_l_english.yml`, `localization/english/te_diplomacy_l_english.yml`
- Test: `test_un_layout.py`
- Tool (not committed): `<scratchpad>/restructure_un.py`

**Interfaces:**
- Consumes: `un_session_open_sgui` (Task 1).
- Produces section types:
  - chamber file: `te_un_sec_assembly_core`, `te_un_sec_delegations`, `te_un_sec_standing_help`, `te_un_sec_exposure`, `te_un_sec_missions`, `te_un_sec_obligations`, `te_un_sec_ballot`, `te_un_sec_propose`, `te_un_sec_mandates`, `te_un_sec_archive`;
  - authority file: `te_un_sec_why`, `te_un_sec_auth_help`, `te_un_sec_auth_history`.
- Produces composers (layout file): `te_un_sec_assembly`, `te_un_status_sections`, `te_un_reference_sections`, and the journal roots `widget_je_un_status` and `widget_je_un_reference`.
- Collapse flags after this task:

| Section | Flag | Default |
|---|---|---|
| General Assembly | `un_chamber_assembly_closed` | open |
| Delegations | `un_chamber_delegations_open` | collapsed |
| Recorded ballot | `un_chamber_votes_open` | collapsed |
| Table a resolution | `un_chamber_propose_open` | collapsed |
| Why authority is moving | `un_auth_why_closed` | open (unchanged) |
| Missions | `un_chamber_missions_closed` | open |
| Mandates | `un_chamber_mandates_closed` | open |
| Obligations | `un_chamber_obligations_closed` | open |
| Exposure | `un_chamber_exposure_closed` | open |
| Actions (tab) | `te_un_tab_actions_closed` | open |
| Authority history | `un_auth_hist_closed` | open |
| Archive | `un_chamber_history_open` | collapsed |
| How standing works | `un_chamber_standing_open` | collapsed |
| How authority works | `un_auth_help_open` | collapsed (unchanged) |

- [ ] **Step 1: Write the failing tests** (`test_un_layout.py`)

```python
"""The UN's section order and collapse defaults (spec 2026-09-28-un-gui-pass-design.md §1)."""
import glob
import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
W = os.path.join(REPO, "gui", "journal_entry_widgets")
LAYOUT = os.path.join(W, "un_layout_widget.gui")
UN_GUI = [os.path.join(W, f) for f in ("un_chamber_widget.gui", "un_authority_widget.gui",
                                        "un_layout_widget.gui")]
UN_GUI.append(os.path.join(REPO, "gui", "diplomatic_overview.gui"))

STATUS = ["te_un_sec_assembly", "te_un_sec_why", "te_un_sec_missions", "te_un_sec_mandates",
          "te_un_sec_obligations", "te_un_sec_exposure"]
REFERENCE = ["te_un_sec_auth_history", "te_un_sec_archive", "te_un_sec_standing_help",
             "te_un_sec_auth_help"]
OLD_FLAGS = ["un_chamber_delegations", "un_chamber_standing", "un_chamber_exposure",
             "un_chamber_missions", "un_chamber_obligations", "un_chamber_votes",
             "un_chamber_propose", "un_chamber_mandates", "un_chamber_history", "un_auth_hist_open"]
NOT_SECTIONS = {"un_chamber_veto_armed", "un_chamber_history_details"}


def _read(path):
    with open(path, encoding="utf-8-sig") as f:
        return f.read()


def _type_body(text, name):
    m = re.search(rf"type {name} = \w+ \{{", text)
    assert m, f"no type {name}"
    depth = 0
    for j in range(m.end() - 1, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return text[m.end():j]


class OrderTest(unittest.TestCase):
    def test_status_and_reference_order(self):
        layout = _read(LAYOUT)
        for composer, expected in (("te_un_status_sections", STATUS),
                                   ("te_un_reference_sections", REFERENCE)):
            found = re.findall(r"^\t\t(te_un_sec_\w+) = \{", _type_body(layout, composer), re.M)
            self.assertEqual(found, expected, composer)

    def test_session_subsections_follow_the_session(self):
        body = _type_body(_read(LAYOUT), "te_un_sec_assembly")
        gate = "GetScriptedGui('un_session_open_sgui').IsShown"
        for sec, negated in (("te_un_sec_delegations", False), ("te_un_sec_ballot", False),
                             ("te_un_sec_propose", True)):
            m = re.search(rf"{sec} = \{{\s*visible = \"\[(.*?)\]\"", body, re.S)
            self.assertTrue(m, f"{sec} has no visible gate")
            self.assertIn(gate, m.group(1))
            self.assertEqual(m.group(1).startswith("Not("), negated, sec)


class FlagTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = "\n".join(_read(p) for p in UN_GUI)

    def test_section_flags_say_their_default(self):
        flags = {f for f in re.findall(r"GetVariableSystem\.Toggle\('(\w+)'\)", self.text)
                 if f.startswith(("un_", "te_un_"))} - NOT_SECTIONS
        self.assertTrue(flags)
        for f in flags:
            self.assertRegex(f, r"_(open|closed)$", f"section flag {f} does not say its default")
            negated = len(re.findall(rf"Not\(\s*GetVariableSystem\.Exists\('{f}'\)\s*\)", self.text))
            total = len(re.findall(rf"GetVariableSystem\.Exists\('{f}'\)", self.text))
            bare = total - negated
            if f.endswith("_closed"):   # shown unless closed: one bare (show-more), the rest negated
                self.assertEqual(bare, 1, f)
                self.assertGreaterEqual(negated, 2, f)
            else:                        # shown only when opened: one negated (show-more)
                self.assertEqual(negated, 1, f)
                self.assertGreaterEqual(bare, 2, f)

    def test_no_old_flag_survives(self):
        for f in OLD_FLAGS:
            self.assertNotRegex(self.text, rf"'{f}'", f)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify it fails.** `<dummy env> …python -m unittest test_un_layout -v`. Expected: ERROR (no `un_layout_widget.gui`).

- [ ] **Step 3: Write the restructure tool** (`<scratchpad>/restructure_un.py`). It splits each panel type at its `\t\t# ---- <title> ----` markers, turns each section into a type at the same indentation (depth 2 inside a type body, as it is now), renames or inverts the flags, turns three sections into subsections, and strips the council and standing rows from the top panel.

```python
"""Split te_un_chamber_panel / te_un_authority_panel into one type per section.

Run from the worktree root. Asserts on every assumption; rerunning on already
converted files fails (the panel types are gone).
"""
import re

CHAMBER = "gui/journal_entry_widgets/un_chamber_widget.gui"
AUTHORITY = "gui/journal_entry_widgets/un_authority_widget.gui"

# marker text prefix -> (type key, old flag, new flag, invert)
CHAMBER_SECTIONS = [
    ("Our own standing", "assembly_core", None, None, False),
    ("Delegations", "delegations", "un_chamber_delegations", "un_chamber_delegations_open", False),
    ("How international standing works", "standing_help", "un_chamber_standing", "un_chamber_standing_open", False),
    ("Our exposure", "exposure", "un_chamber_exposure", "un_chamber_exposure_closed", True),
    ("Missions in the field", "missions", "un_chamber_missions", "un_chamber_missions_closed", True),
    ("Our obligations", "obligations", "un_chamber_obligations", "un_chamber_obligations_closed", True),
    ("Recorded ballot", "ballot", "un_chamber_votes", "un_chamber_votes_open", False),
    ("Table a Resolution", "propose", "un_chamber_propose", "un_chamber_propose_open", False),
    ("Authorized military mandates", "mandates", "un_chamber_mandates", "un_chamber_mandates_closed", True),
    ("Archive of closed resolutions", "archive", "un_chamber_history", "un_chamber_history_open", False),
]
AUTHORITY_SECTIONS = [
    ("Why authority is moving", "why", None, None, False),
    ("How UN authority works", "auth_help", None, None, False),
    ("Authority history", "auth_history", "un_auth_hist_open", "un_auth_hist_closed", True),
]
SUBSECTIONS = {"delegations", "ballot", "propose"}


def read(p):
    with open(p, encoding="utf-8-sig", newline="") as f:
        return f.read().split("\n")


def write(p, lines):
    with open(p, "w", encoding="utf-8-sig", newline="") as f:
        f.write("\n".join(lines))


def depth_delta(line):
    code = re.sub(r'"[^"]*"', '""', line.split("#", 1)[0])
    return code.count("{") - code.count("}")


def block_end(lines, start):
    d = 0
    for i in range(start, len(lines)):
        d += depth_delta(lines[i])
        if d == 0:
            return i
    raise AssertionError(f"unbalanced block at {start + 1}")


def rename_flag(text, old, new, invert):
    q_old = f"'{old}'"
    assert q_old in text, old
    if not invert:
        return text.replace(q_old, f"'{new}'")
    neg = re.compile(rf"Not\(\s*GetVariableSystem\.Exists\('{old}'\)\s*\)")
    text = neg.sub("@@SHOWN@@", text)
    text = text.replace(f"GetVariableSystem.Exists('{old}')", f"Not(GetVariableSystem.Exists('{new}'))")
    text = text.replace("@@SHOWN@@", f"GetVariableSystem.Exists('{new}')")
    text = text.replace(f"Toggle('{old}')", f"Toggle('{new}')")
    assert q_old not in text, old
    return text


def to_subsection(sec):
    """Full-width header + panel -> nested subsection header + plain content column."""
    h = next(i for i, l in enumerate(sec) if l == "\t\tun_chamber_section_header = {")
    he = block_end(sec, h)
    header = ["\t" + l if l else l for l in sec[h:he + 1]]
    header[0] = "\t\t\tun_chamber_subsection_header = {"
    wrapped = (["\t\tflowcontainer = {", "\t\t\tdirection = vertical", "\t\t\tignoreinvisible = yes",
                "\t\t\tmargin_left = 20", "\t\t\tmargin_bottom = 6", ""] + header + ["\t\t}"])
    sec = sec[:h] + wrapped + sec[he + 1:]
    p = next(i for i, l in enumerate(sec) if l == "\t\tun_chamber_panel = {")
    sec[p:p + 1] = ["\t\tflowcontainer = {", "\t\t\tdirection = vertical",
                    "\t\t\tignoreinvisible = yes", "\t\t\tparentanchor = hcenter"]
    return sec


def assembly_core(sec):
    """The top panel's children, minus the standing and council rows (now the overview's tooltips)."""
    p = next(i for i, l in enumerate(sec) if l == "\t\tun_chamber_panel = {")
    pe = block_end(sec, p)
    kids = [l[1:] if l.startswith("\t") else l for l in sec[p + 1:pe]]
    start = next(i for i, l in enumerate(kids) if l == "\t\tun_chamber_subheader = {")
    assert any("je_un_chamber_sub_standing" in l for l in kids[start:start + 5])
    council_text = next(i for i, l in enumerate(kids) if "un_chamber_council_sgui" in l)
    end = block_end(kids, next(i for i in range(council_text, -1, -1)
                               if kids[i] == "\t\tun_chamber_text = {"))
    return sec[:p] + kids[:start] + kids[end + 1:]


def split(path, type_name, sections, wrapper_name):
    lines = read(path)
    ts = lines.index(f"\ttype {type_name} = flowcontainer {{")
    te = block_end(lines, ts)
    marks = [i for i in range(ts, te) if lines[i].startswith("\t\t# ---- ")]
    assert len(marks) == len(sections), [lines[i] for i in marks]
    out = []
    for n, (prefix, key, old, new, invert) in enumerate(sections):
        a, b = marks[n], (marks[n + 1] if n + 1 < len(marks) else te)
        sec = lines[a:b]
        assert sec[0][len("\t\t# ---- "):].startswith(prefix), (sec[0], prefix)
        while sec and not sec[-1].strip():
            sec.pop()
        if key == "assembly_core":
            sec = assembly_core(sec)
        if old:
            sec = rename_flag("\n".join(sec), old, new, invert).split("\n")
        if key in SUBSECTIONS:
            sec = to_subsection(sec)
        out += ["", f"\ttype te_un_sec_{key} = flowcontainer {{", "\t\tdirection = vertical",
                "\t\tparentanchor = hcenter", "\t\tignoreinvisible = yes", "\t\tspacing = 4", ""]
        out += sec + ["\t}"]
    # Drop the named root wrapper at the foot of the file (the layout file owns the roots now).
    w = next(i for i, l in enumerate(lines) if l == f'\tname = "{wrapper_name}"') - 1
    assert lines[w] == "flowcontainer = {"
    we = block_end(lines, w)
    banner = w
    while banner > 0 and lines[banner - 1].startswith("###"):
        banner -= 1
    lines = lines[:banner] + lines[we + 1:]
    lines = lines[:ts] + out[1:] + lines[te + 1:]
    write(path, lines)


split(CHAMBER, "te_un_chamber_panel", CHAMBER_SECTIONS, "widget_je_un_chamber")
split(AUTHORITY, "te_un_authority_panel", AUTHORITY_SECTIONS, "widget_je_un_authority")
print("ok")
```

- [ ] **Step 4: Run the tool, then review the result by hand.**

Run: `python3 <scratchpad>/restructure_un.py && python3 <scratchpad>/braces.py gui/journal_entry_widgets/un_chamber_widget.gui gui/journal_entry_widgets/un_authority_widget.gui`
Expected: `ok`, both files at final depth 0, and no top-level `flowcontainer` left in either file.

Then fix what the tool can't know about:
- `git diff -w` both files and read every section's comments. Change "Collapsed by default" to "Open by default" in exposure, missions, obligations, mandates and authority history. Delegations, ballot and proposals now say they are subsections of the General Assembly.
- Rewrite both file headers. Each file is now a type library of UN sections, and `un_layout_widget.gui` sets the order.
- In `te_un_sec_assembly_core`, give the first remaining `un_chamber_subheader` (the session one) `blockoverride "subheader_margin" {}`, the way the old first subheader had it.

- [ ] **Step 5: Create `gui/journal_entry_widgets/un_layout_widget.gui`** (with a BOM):

```
### United Nations — layout. The one place that sets the order of the UN's
### sections, for both hosts: the journal entry (je_united_nations.txt attaches
### the named roots at the foot of this file) and the Diplomacy panel's UN tab
### (gui/diplomatic_overview.gui instances the composers). The sections are
### types in un_chamber_widget.gui and un_authority_widget.gui; the overview is
### un_overview_widget.gui. Spec: docs/superpowers/specs/2026-09-28-un-gui-pass-design.md.
###
### Collapse flags say their default: *_closed sections are open until closed,
### *_open ones collapsed until opened (test_un_layout.py).

types un_layout_widget_types
{
	### The General Assembly: the session core, then either the session's
	### delegations and ballot, or, with nothing in session, the proposals. The
	### two never both apply: every proposal needs the one-vote lock free.
	type te_un_sec_assembly = flowcontainer {
		direction = vertical
		parentanchor = hcenter
		ignoreinvisible = yes
		spacing = 4

		un_chamber_section_header = {
			blockoverride "left_text" {
				text = "je_un_assembly_header"
			}
			blockoverride "onclick" {
				onclick = "[GetVariableSystem.Toggle('un_chamber_assembly_closed')]"
			}
			blockoverride "onclick_showmore" {
				visible = "[GetVariableSystem.Exists('un_chamber_assembly_closed')]"
			}
			blockoverride "onclick_showless" {
				visible = "[Not(GetVariableSystem.Exists('un_chamber_assembly_closed'))]"
			}
		}

		un_chamber_panel = {
			visible = "[Not(GetVariableSystem.Exists('un_chamber_assembly_closed'))]"

			te_un_sec_assembly_core = {}
			te_un_sec_delegations = {
				visible = "[GetScriptedGui('un_session_open_sgui').IsShown( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).End )]"
			}
			te_un_sec_ballot = {
				visible = "[GetScriptedGui('un_session_open_sgui').IsShown( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).End )]"
			}
			te_un_sec_propose = {
				visible = "[Not( GetScriptedGui('un_session_open_sgui').IsShown( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).End ) )]"
			}
		}
	}

	### Everything a returning player checks, open by default.
	type te_un_status_sections = flowcontainer {
		direction = vertical
		parentanchor = hcenter
		ignoreinvisible = yes
		spacing = 4
		visible = "[JournalEntry.IsActive]"

		te_un_sec_assembly = {}
		te_un_sec_why = {}
		te_un_sec_missions = {}
		te_un_sec_mandates = {}
		te_un_sec_obligations = {}
		te_un_sec_exposure = {}
	}

	### The chart, then the record and the explanations, mostly collapsed.
	type te_un_reference_sections = flowcontainer {
		direction = vertical
		parentanchor = hcenter
		ignoreinvisible = yes
		spacing = 4
		visible = "[JournalEntry.IsActive]"

		te_un_sec_auth_history = {}
		te_un_sec_archive = {}
		te_un_sec_standing_help = {}
		te_un_sec_auth_help = {}
	}
}

### ==========================================================================
### JOURNAL ENTRY ROOTS (je_united_nations.txt). Bare wrappers that repeat the
### composers' IsActive gate, so an inactive entry's containers collapse.
### ==========================================================================
flowcontainer = {
	name = "widget_je_un_status"
	visible = "[JournalEntry.IsActive]"
	parentanchor = hcenter
	ignoreinvisible = yes

	te_un_status_sections = {}
}

flowcontainer = {
	name = "widget_je_un_reference"
	visible = "[JournalEntry.IsActive]"
	parentanchor = hcenter
	ignoreinvisible = yes

	te_un_reference_sections = {}
}
```

- [ ] **Step 6: Journal wiring.** In `common/journal_entries/je_united_nations.txt`, replace the two `widget = { … }` blocks and their comments (lines ~6–25) with:

```
	# The UN's panels (docs/superpowers/specs/2026-09-28-un-gui-pass-design.md).
	# The order lives in gui/journal_entry_widgets/un_layout_widget.gui, which the
	# Diplomacy panel's UN tab also instances: the dynamic sections above the
	# button grid, the chart, the record and the explanations below it.
	widget = {
		gui = "gui/journal_entry_widgets/un_layout_widget.gui"
		name = "widget_je_un_status"
		container = "custom_widget_container_2"
	}
	widget = {
		gui = "gui/journal_entry_widgets/un_layout_widget.gui"
		name = "widget_je_un_reference"
		container = "custom_widget_container_3"
	}
```

- [ ] **Step 7: Tab wiring.** In `gui/diplomatic_overview.gui`, inside the UN tab's `datacontext = "[GetPlayerJournalEntry('je_united_nations')]"` flowcontainer, replace

```
							te_un_chamber_panel = {}
							te_je_scripted_buttons = {}
							te_un_authority_panel = {}
```

with the following. `te_je_scripted_bars` and `te_je_status_desc` stay until Task 3.

```
							te_un_status_sections = {}

							# The entry's own buttons (founding, joining, leaving and most
							# requests exist only here), in a section of their own. A
							# wrapper carries the section's gate: te_je_scripted_buttons
							# has a visible of its own (gotcha #17).
							un_chamber_section_header = {
								blockoverride "left_text" {
									text = "te_diplomacy_un_tab_actions_header"
								}
								blockoverride "onclick" {
									onclick = "[GetVariableSystem.Toggle('te_un_tab_actions_closed')]"
								}
								blockoverride "onclick_showmore" {
									visible = "[GetVariableSystem.Exists('te_un_tab_actions_closed')]"
								}
								blockoverride "onclick_showless" {
									visible = "[Not(GetVariableSystem.Exists('te_un_tab_actions_closed'))]"
								}
							}
							flowcontainer = {
								visible = "[Not(GetVariableSystem.Exists('te_un_tab_actions_closed'))]"
								parentanchor = hcenter
								direction = vertical

								te_je_scripted_buttons = {}
							}

							te_un_reference_sections = {}
```

- [ ] **Step 8: Loc.** Add to `te_journal_entries_l_english.yml`: ` je_un_assembly_header:0 "General Assembly"`. Add to `te_diplomacy_l_english.yml`: ` te_diplomacy_un_tab_actions_header:0 "Actions"`. Run `organize_loc.py`.

- [ ] **Step 9: Run the tests.** `<dummy env> …python -m unittest test_un_layout test_un_chamber_propose_ops test_un_convention_registry test_un_chamber_mission_slots test_un_vote_lobbying -v`. Expected: PASS. If a UN test anchors on the old indentation or on `te_un_chamber_panel`, relax the anchor to any depth (as in #567's commit `d42d7164`) and confirm it finds the same rows as before the change. Then run `check_all.sh`.

- [ ] **Step 10: Commit** (the two widgets, the layout file, the journal entry, `diplomatic_overview.gui`, loc, `test_un_layout.py`, and any relaxed test) with the message `UN panels: one type per section, one layout for journal and tab`.

---

### Task 3: The overview

**Files:**
- Create: `gui/journal_entry_widgets/un_overview_widget.gui`
- Modify: `gui/journal_entry_widgets/un_layout_widget.gui` (add the `widget_je_un_overview` root)
- Modify: `common/journal_entries/je_united_nations.txt` (slot 1 and the slot-7 marker)
- Modify: `gui/diplomatic_overview.gui` (replace `te_je_scripted_bars` + `te_je_status_desc` with `te_un_overview_panel`)
- Modify: `localization/english/te_journal_entries_l_english.yml`
- Test: `test_un_overview_data.py` (add `OverviewGuiTest`)

**Interfaces:**
- Consumes Task 1's display values and handlers: `un_chamber_status_sgui`, `un_chamber_standing_sgui`, `un_overview_tier_sgui`, `un_chamber_council_sgui` (existing), `un_authority_crisis_sgui` (existing, `IsShown` and `ExecuteTooltip`), `un_authority_ready_sgui` (existing).
- Produces: `te_un_overview_panel`, and the journal root `widget_je_un_overview`.

- [ ] **Step 1: Add the failing test** to `test_un_overview_data.py`:

```python
OVERVIEW = os.path.join(REPO, "gui", "journal_entry_widgets", "un_overview_widget.gui")


class OverviewGuiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gui = _read(OVERVIEW)

    def _codes(self, value):
        return {int(n) for n in re.findall(
            rf"ScriptValue\('{value}'\), '\(CFixedPoint\)(-?\d+)'", self.gui)}

    def test_every_agency_has_a_slot(self):
        agencies = re.findall(r"un_agency_(\w+)", _block(_read(UN_VALUES), "un_agency_count"))
        for a in agencies:
            self.assertIn(f"ScriptValue('un_disp_agency_{a}')", self.gui, a)

    def test_every_membership_state_and_tier_has_an_icon(self):
        self.assertEqual(self._codes("un_disp_member_code"), set(range(7)))
        self.assertEqual(self._codes("un_disp_tier_code"), set(range(5)))

    def test_five_council_seats_gated_on_the_count(self):
        for n in range(1, 6):
            self.assertIn(f"Var('un_p5_seat_{n}')", self.gui)
        self.assertEqual(
            {int(n) for n in re.findall(
                r"GreaterThanOrEqualTo_CFixedPoint\( JournalEntry\.GetCountry\.MakeScope\.ScriptValue\('un_disp_p5_count'\), '\(CFixedPoint\)(\d)' \)",
                self.gui)},
            set(range(1, 6)))

    def test_rows_below_membership_wait_for_the_first_update(self):
        self.assertIn("GetScriptedGui('un_authority_ready_sgui').IsShown", self.gui)
```

- [ ] **Step 2: Run to verify it fails.** `…python -m unittest test_un_overview_data.OverviewGuiTest`. Expected: ERROR (no file).

- [ ] **Step 3: Create `gui/journal_entry_widgets/un_overview_widget.gui`** (with a BOM). Placeholder textures are vanilla paths (checked 2026-09-28 against the install). The file:

```
### United Nations — the overview, at the top of both hosts (un_layout_widget.gui
### sets the order). A glance for the player who knows the UN: am I in, how
### strong is it, who runs it, what has it built. Every figure is a
### un_disp_* value (common/script_values/un_overview_display_values.txt); every
### tooltip is the text it replaced, from a scripted GUI in un_chamber_sguis.txt.
### Icons are vanilla placeholders; real art changes the paths only.
### Spec: docs/superpowers/specs/2026-09-28-un-gui-pass-design.md §2.

types un_overview_widget_types
{
	### An icon and a short label, for membership and tier.
	type te_un_ov_icon_label = flowcontainer {
		direction = horizontal
		spacing = 6
		ignoreinvisible = yes

		icon = {
			size = { 32 32 }
			parentanchor = vcenter
			block "icon_texture" {}
		}
		textbox = {
			autoresize = yes
			parentanchor = vcenter
			align = left|nobaseline
			using = fontsize_large
			block "label" {}
		}
	}

	### A 0..1 share as a pie over a background disc, its label beneath. The
	### textures are the Cultural Hegemony pie's (frame 1 transparent, frame 2
	### the colour; gui_modding_guide.md "Pie charts of script-held data").
	type te_un_ov_pie = flowcontainer {
		direction = vertical
		spacing = 2
		minimumsize = { 150 -1 }

		widget = {
			size = { 64 64 }
			parentanchor = hcenter

			progresspie = {
				size = { 100% 100% }
				min = 0
				max = 1
				value = 1
				texture = "gfx/interface/journal_entry_widgets/ch_model_pie/ch_pie_other.dds"
				framesize = { 128 128 }
				frame = 2
			}
			progresspie = {
				size = { 100% 100% }
				min = 0
				max = 1
				block "pie_value" {}
				texture = "gfx/interface/journal_entry_widgets/ch_model_pie/ch_pie_liberal.dds"
				framesize = { 128 128 }
				frame = 2
			}
		}
		textbox = {
			parentanchor = hcenter
			autoresize = yes
			align = hcenter|nobaseline
			using = fontsize_medium
			block "label" {}
		}
	}

	### One agency: full colour once founded, dimmed until then. The instance
	### sets the texture on both icons and the value that picks one.
	type te_un_ov_agency = widget {
		size = { 40 40 }

		icon = {
			size = { 36 36 }
			parentanchor = center
			block "lit" {}
			block "agency_texture" {}
		}
		icon = {
			size = { 36 36 }
			parentanchor = center
			alpha = 0.25
			block "unlit" {}
			block "agency_texture" {}
		}
	}

	### A vacant permanent seat.
	type te_un_ov_vacant_seat = widget {
		size = { 52 36 }
		tooltip = "je_un_ov_vacant_tt"

		icon = {
			size = { 48 32 }
			parentanchor = center
			texture = "gfx/interface/progressbar/progressbar_empty.dds"
			spriteType = Corneredtiled
			spriteborder = { 4 4 }
		}
	}

	type te_un_overview_panel = flowcontainer {
		direction = vertical
		parentanchor = hcenter
		ignoreinvisible = yes
		visible = "[JournalEntry.IsActive]"

		un_chamber_panel = {
			spacing = 10

			### Row 1: membership · tier · crisis · standing
			flowcontainer = {
				direction = horizontal
				spacing = 18
				ignoreinvisible = yes

				flowcontainer = {
					ignoreinvisible = yes
					tooltip = "[GetScriptedGui('un_chamber_status_sgui').ExecuteTooltip(GuiScope.SetRoot(JournalEntry.GetCountry.MakeScope).End)]"
					<MEMBERSHIP: seven te_un_ov_icon_label instances, table below>
				}
				flowcontainer = {
					ignoreinvisible = yes
					visible = "[GetScriptedGui('un_authority_ready_sgui').IsShown( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).End )]"
					tooltip = "[GetScriptedGui('un_overview_tier_sgui').ExecuteTooltip(GuiScope.SetRoot(JournalEntry.GetCountry.MakeScope).End)]"
					<TIER: five te_un_ov_icon_label instances, table below>
				}
				icon = {
					size = { 32 32 }
					parentanchor = vcenter
					visible = "[GetScriptedGui('un_authority_crisis_sgui').IsShown( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).End )]"
					texture = "gfx/interface/icons/alert_icons/critical_supply_network.dds"
					tooltip = "[GetScriptedGui('un_authority_crisis_sgui').ExecuteTooltip(GuiScope.SetRoot(JournalEntry.GetCountry.MakeScope).End)]"
				}
				flowcontainer = {
					direction = horizontal
					spacing = 6
					parentanchor = vcenter
					visible = "[NotEqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope.ScriptValue('un_disp_member_code'), '(CFixedPoint)0' )]"
					tooltip = "[GetScriptedGui('un_chamber_standing_sgui').ExecuteTooltip(GuiScope.SetRoot(JournalEntry.GetCountry.MakeScope).End)]"

					textbox = {
						autoresize = yes
						parentanchor = vcenter
						align = left|nobaseline
						text = "je_un_ov_standing_label"
					}
					default_progressbar_horizontal = {
						size = { 80 12 }
						parentanchor = vcenter
						blockoverride "values" {
							value = "[FixedPointToFloat( JournalEntry.GetCountry.MakeScope.ScriptValue('un_disp_standing_frac') )]"
							min = 0
							max = 1
						}
					}
				}
			}

			### Rows 2-5: only once the UN exists and has had its first monthly update.
			flowcontainer = {
				direction = vertical
				spacing = 10
				ignoreinvisible = yes
				visible = "[GetScriptedGui('un_authority_ready_sgui').IsShown( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).End )]"

				### Authority, with a tick at the target (the marker technique of
				### te_je_scripted_bars' double-sided gold bar, which works in game).
				flowcontainer = {
					direction = horizontal
					spacing = 8
					tooltip = "je_un_auth_tbl_headline"

					textbox = {
						minimumsize = { 90 -1 }
						autoresize = yes
						parentanchor = vcenter
						align = left|nobaseline
						text = "je_un_ov_authority_label"
					}
					default_progressbar_horizontal = {
						size = { 240 18 }
						parentanchor = vcenter
						blockoverride "values" {
							value = "[FixedPointToFloat( JournalEntry.GetCountry.MakeScope.ScriptValue('un_disp_authority_frac') )]"
							min = 0
							max = 1
						}
						blockoverride "on_top_of_the_progressbar" {
							progressbar = {
								noprogresstexture = "gfx/interface/icons/generic_icons/transparent.dds"
								progresstexture = "gfx/interface/icons/generic_icons/transparent.dds"
								size = { 100% 100% }
								skip_initial_animation = yes
								direction = horizontal
								value = "[FixedPointToFloat( JournalEntry.GetCountry.MakeScope.ScriptValue('un_disp_target_frac') )]"
								min = 0
								max = 1
								marker = {
									icon = {
										size = { 36 20 }
										parentanchor = vcenter
										widgetanchor = center
										texture = "gfx/interface/progressbar/progressbar_marker.dds"
									}
								}
							}
						}
					}
					textbox = {
						autoresize = yes
						parentanchor = vcenter
						align = left|nobaseline
						text = "je_un_ov_authority_value"
					}
				}

				### Members' share of the world
				flowcontainer = {
					direction = horizontal
					parentanchor = hcenter

					te_un_ov_pie = {
						tooltip = "je_un_ov_pie_countries_tt"
						blockoverride "pie_value" {
							value = "[FixedPointToFloat( JournalEntry.GetCountry.MakeScope.ScriptValue('un_disp_share_countries') )]"
						}
						blockoverride "label" {
							text = "je_un_ov_pie_countries"
						}
					}
					te_un_ov_pie = {
						tooltip = "je_un_ov_pie_gdp_tt"
						blockoverride "pie_value" {
							value = "[FixedPointToFloat( JournalEntry.GetCountry.MakeScope.ScriptValue('un_disp_share_gdp') )]"
						}
						blockoverride "label" {
							text = "je_un_ov_pie_gdp"
						}
					}
					te_un_ov_pie = {
						tooltip = "je_un_ov_pie_pop_tt"
						blockoverride "pie_value" {
							value = "[FixedPointToFloat( JournalEntry.GetCountry.MakeScope.ScriptValue('un_disp_share_pop') )]"
						}
						blockoverride "label" {
							text = "je_un_ov_pie_pop"
						}
					}
				}

				### The Security Council: five seats. A filled seat's datacontext is
				### the stored capital's country (un_p5_display_refresh); the gate on
				### its parent means a seat that is not set is never read.
				flowcontainer = {
					direction = horizontal
					spacing = 4

					textbox = {
						minimumsize = { 130 -1 }
						autoresize = yes
						parentanchor = vcenter
						align = left|nobaseline
						text = "je_un_ov_council_label"
						tooltip = "[GetScriptedGui('un_chamber_council_sgui').ExecuteTooltip(GuiScope.SetRoot(JournalEntry.GetCountry.MakeScope).End)]"
					}
					<SEATS: five blocks, template below>
				}

				### Agencies
				flowcontainer = {
					direction = vertical
					spacing = 2

					textbox = {
						autoresize = yes
						align = left|nobaseline
						text = "je_un_ov_agencies_label"
					}
					flowcontainer = {
						direction = horizontal
						spacing = 4
						<AGENCIES 1-6: who unesco icj unhrc iaea unep>
					}
					flowcontainer = {
						direction = horizontal
						spacing = 4
						<AGENCIES 7-11: unhcr unoosa itlos icc cppnm>
					}
				}
			}
		}
	}
}
```

Replace each `<…>` placeholder above with the generated blocks below; write them out in full in the file. Generate them with a short Python snippet if you like, but the file must contain the expanded markup.

MEMBERSHIP. One instance per code:

```
					te_un_ov_icon_label = {
						visible = "[EqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope.ScriptValue('un_disp_member_code'), '(CFixedPoint)<N>' )]"
						blockoverride "icon_texture" {
							texture = "<TEXTURE>"
						}
						blockoverride "label" {
							text = "je_un_ov_member_<N>"
						}
					}
```

| N | TEXTURE |
|---|---|
| 0 | `gfx/interface/icons/generic_icons/map_list_cross.dds` |
| 1 | `gfx/interface/icons/generic_icons/red_cross.dds` |
| 2 | `gfx/interface/icons/generic_icons/checkbox_simple.dds` |
| 3 | `gfx/interface/icons/generic_icons/green_checkmark.dds` |
| 4 | `gfx/interface/icons/generic_icons/checkbox_greencheck.dds` |
| 5 | `gfx/interface/icons/generic_icons/checkmark.dds` |
| 6 | `gfx/interface/icons/generic_icons/warning.dds` |

TIER. The same shape, with `un_disp_tier_code` and `je_un_ov_tier_<N>`:

| N | TEXTURE |
|---|---|
| 0 | `gfx/interface/icons/alert_icons/revolution.dds` |
| 1 | `gfx/interface/icons/alert_icons/low_legitimacy.dds` |
| 2 | `gfx/interface/icons/generic_icons/checkmark.dds` |
| 3 | `gfx/interface/icons/generic_icons/green_checkmark.dds` |
| 4 | `gfx/interface/icons/alert_icons/formable_possible.dds` |

SEATS. For N = 1..5:

```
					widget = {
						size = { 52 36 }
						visible = "[GreaterThanOrEqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope.ScriptValue('un_disp_p5_count'), '(CFixedPoint)<N>' )]"

						small_flag = {
							parentanchor = center
							datacontext = "[JournalEntry.GetCountry.MakeScope.Var('un_p5_seat_<N>').GetState.GetCountry]"
						}
					}
					te_un_ov_vacant_seat = {
						visible = "[Not( GreaterThanOrEqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope.ScriptValue('un_disp_p5_count'), '(CFixedPoint)<N>' ) )]"
					}
```

AGENCIES. For each agency `<a>` with its placeholder texture:

```
						te_un_ov_agency = {
							tooltip = "[Concatenate( Localize( 'je_un_ov_agency_<a>_tt' ), SelectLocalization( EqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope.ScriptValue('un_disp_agency_<a>'), '(CFixedPoint)1' ), 'je_un_ov_agency_founded', 'je_un_ov_agency_not_founded' ) )]"
							blockoverride "agency_texture" {
								texture = "<TEXTURE>"
							}
							blockoverride "lit" {
								visible = "[EqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope.ScriptValue('un_disp_agency_<a>'), '(CFixedPoint)1' )]"
							}
							blockoverride "unlit" {
								visible = "[Not( EqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope.ScriptValue('un_disp_agency_<a>'), '(CFixedPoint)1' ) )]"
							}
						}
```

| a | TEXTURE |
|---|---|
| who | `gfx/interface/icons/institution_icons/health_service.dds` |
| unesco | `gfx/interface/icons/goods_icons/fine_art.dds` |
| icj | `gfx/interface/icons/institution_icons/home_affairs.dds` |
| unhrc | `gfx/interface/icons/institution_icons/social_security.dds` |
| iaea | `gfx/interface/icons/goods_icons/electricity.dds` |
| unep | `gfx/interface/icons/goods_icons/wood.dds` |
| unhcr | `gfx/interface/icons/institution_icons/colonization.dds` |
| unoosa | `gfx/interface/icons/goods_icons/aeroplanes.dds` |
| itlos | `gfx/interface/icons/goods_icons/merchant_marine.dds` |
| icc | `gfx/interface/icons/institution_icons/police.dds` |
| cppnm | `gfx/interface/icons/goods_icons/explosives.dds` |

Confirm every texture path exists before committing: `for f in <paths>; do [ -f "/mnt/c/Program Files (x86)/Steam/steamapps/common/Victoria 3/game/$f" ] || echo MISSING $f; done`. The CH pie textures are the mod's own; check them in the main checkout's `gfx/`.

- [ ] **Step 4: Loc.** Add to `te_journal_entries_l_english.yml`:

```
 je_un_ov_member_0:0 "No UN"
 je_un_ov_member_1:0 "Cannot join"
 je_un_ov_member_2:0 "Not a member"
 je_un_ov_member_3:0 "Member"
 je_un_ov_member_4:0 "Permanent member"
 je_un_ov_member_5:0 "Suspended, seat carried"
 je_un_ov_member_6:0 "Suspended"
 je_un_ov_tier_0:0 "Moribund"
 je_un_ov_tier_1:0 "Contested"
 je_un_ov_tier_2:0 "Established"
 je_un_ov_tier_3:0 "Strong"
 je_un_ov_tier_4:0 "Supranational"
 je_un_ov_standing_label:0 "Standing #v [JournalEntry.GetCountry.MakeScope.ScriptValue('un_disp_standing')|0]#!"
 je_un_ov_authority_label:0 "[concept_un_authority]"
 je_un_ov_authority_value:0 "#v [JournalEntry.GetCountry.MakeScope.ScriptValue('un_disp_authority')|0]#! → [JournalEntry.GetCountry.MakeScope.ScriptValue('un_disp_target')|0] ([JournalEntry.GetCountry.MakeScope.ScriptValue('un_disp_step')|+1])"
 je_un_ov_pie_countries:0 "Countries #v [JournalEntry.GetCountry.MakeScope.ScriptValue('un_disp_share_countries_pct')|0]%#!"
 je_un_ov_pie_gdp:0 "GDP #v [JournalEntry.GetCountry.MakeScope.ScriptValue('un_disp_share_gdp_pct')|0]%#!"
 je_un_ov_pie_pop:0 "Population #v [JournalEntry.GetCountry.MakeScope.ScriptValue('un_disp_share_pop_pct')|0]%#!"
 je_un_ov_pie_countries_tt:0 "The members' share of the world's countries, as of the last monthly update."
 je_un_ov_pie_gdp_tt:0 "The members' share of the world's GDP, as of the last monthly update."
 je_un_ov_pie_pop_tt:0 "The members' share of the world's population, as of the last monthly update."
 je_un_ov_council_label:0 "Security Council"
 je_un_ov_vacant_tt:0 "A vacant permanent seat. Hover over the Security Council label to see who is in line."
 je_un_ov_agencies_label:0 "Agencies"
 je_un_ov_agency_founded:0 "\n#G Founded.#!"
 je_un_ov_agency_not_founded:0 "\nNot yet founded."
 je_un_ov_agency_who_tt:0 "#b WHO#!: World Health Organization"
 je_un_ov_agency_unesco_tt:0 "#b UNESCO#!: heritage and culture"
 je_un_ov_agency_icj_tt:0 "#b ICJ#!: International Court of Justice"
 je_un_ov_agency_unhrc_tt:0 "#b UNHRC#!: human rights council"
 je_un_ov_agency_iaea_tt:0 "#b IAEA#!: nuclear energy oversight"
 je_un_ov_agency_unep_tt:0 "#b UNEP#!: environment programme"
 je_un_ov_agency_unhcr_tt:0 "#b UNHCR#!: refugee agency"
 je_un_ov_agency_unoosa_tt:0 "#b UNOOSA#!: outer space affairs"
 je_un_ov_agency_itlos_tt:0 "#b ITLOS#!: tribunal for the law of the sea"
 je_un_ov_agency_icc_tt:0 "#b ICC#!: International Criminal Court"
 je_un_ov_agency_cppnm_tt:0 "#b CPPNM#!: physical protection of nuclear material"
```

Confirm `concept_un_authority` exists (`git grep -n "^concept_un_authority = {" common/game_concepts`) and `un_disp_step` exists (`git grep -n "^un_disp_step = {" common/script_values`). Then run `organize_loc.py`.

- [ ] **Step 5: Place the overview.**
  - Add to `un_layout_widget.gui`, above the other roots:

```
flowcontainer = {
	name = "widget_je_un_overview"
	visible = "[JournalEntry.IsActive]"
	parentanchor = hcenter
	ignoreinvisible = yes

	te_un_overview_panel = {}
}
```

  - Add to `je_united_nations.txt`, before the status widget:

```
	widget = {
		gui = "gui/journal_entry_widgets/un_layout_widget.gui"
		name = "widget_je_un_overview"
		container = "custom_widget_container_1"
	}
	# MARKER, not content: the overview draws authority, so the journal panel
	# drops its own bar block at the bottom (gui/journal_entry.gui; see
	# je_banking.txt for the mechanism).
	widget = {
		gui = "gui/journal_entry_widgets/te_je_bars_on_top_marker.gui"
		name = "widget_te_je_bars_on_top_marker"
		container = "custom_widget_container_7"
	}
```

  - In `gui/diplomatic_overview.gui`'s UN tab, replace `te_je_scripted_bars = {}` and `te_je_status_desc = {}` with `te_un_overview_panel = {}`, and update the tab's MOD comment to the new order (overview, status, actions, reference, link).

- [ ] **Step 6: Run the tests.** `…python -m unittest test_un_overview_data -v`, then `check_all.sh`. Expected: PASS and all clean.

- [ ] **Step 7: Commit** (the overview file, the layout file, the journal entry, `diplomatic_overview.gui`, loc, the test) with the message `UN overview: membership, tier, standing, authority, member shares, council flags, agencies`.

---

### Task 4: The session strip in the General Assembly

**Files:**
- Modify: `gui/journal_entry_widgets/un_layout_widget.gui` (`te_un_sec_assembly`, first child of its panel; plus a `te_un_topic_icon` type)
- Modify: `localization/english/te_journal_entries_l_english.yml`
- Test: `test_un_layout.py` (add `SessionStripTest`)

**Interfaces:** consumes `un_disp_res_*` and `un_session_open_sgui` (Task 1).

- [ ] **Step 1: Add the failing test** to `test_un_layout.py`:

```python
class SessionStripTest(unittest.TestCase):
    def test_strip_is_gated_and_the_two_thirds_mark_only_on_supermajority(self):
        body = _type_body(_read(LAYOUT), "te_un_sec_assembly")
        self.assertIn("ScriptValue('un_disp_res_yes_frac')", body)
        self.assertIn("ScriptValue('un_disp_res_not_no_frac')", body)
        self.assertIn("ScriptValue('un_disp_res_months_frac')", body)
        mark = re.search(r"# two-thirds mark.*?visible = \"\[(.*?)\]\"", body, re.S)
        self.assertTrue(mark)
        self.assertIn("un_disp_res_supermajority", mark.group(1))

    def test_every_topic_has_an_icon(self):
        codes = {int(n) for n in re.findall(
            r"ScriptValue\('un_disp_res_topic_code'\), '\(CFixedPoint\)(\d+)'", _read(LAYOUT))}
        self.assertEqual(codes, set(range(18)))
```

- [ ] **Step 2: Run to verify it fails.** Expected: FAIL.

- [ ] **Step 3: Add the strip.** Insert as the first child of `te_un_sec_assembly`'s `un_chamber_panel`, before `te_un_sec_assembly_core = {}`:

```
			### The resolution in session at a glance: topic, tally, time. The tally
			### spans the members with a vote: three stacked bars, red to the end,
			### grey (not yet voted) to 1 - no, green (yes) on top. The upper layers
			### blank their own background and frame so the lower ones show.
			flowcontainer = {
				direction = vertical
				spacing = 4
				ignoreinvisible = yes
				visible = "[GetScriptedGui('un_session_open_sgui').IsShown( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).End )]"

				flowcontainer = {
					direction = horizontal
					spacing = 8

					widget = {
						size = { 40 40 }
						parentanchor = vcenter
						<TOPICS: 18 icons, template below>
					}

					flowcontainer = {
						direction = vertical
						spacing = 4
						parentanchor = vcenter

						### Tally
						flowcontainer = {
							direction = horizontal
							spacing = 6
							tooltip = "je_un_tally_tt"

							widget = {
								size = { 300 18 }
								parentanchor = vcenter

								bad_progressbar_horizontal = {
									size = { 100% 100% }
									blockoverride "values" {
										value = 1
										min = 0
										max = 1
									}
								}
								white_progressbar_horizontal = {
									size = { 100% 100% }
									blockoverride "background" {}
									blockoverride "frame" {}
									blockoverride "values" {
										value = "[FixedPointToFloat( JournalEntry.GetCountry.MakeScope.ScriptValue('un_disp_res_not_no_frac') )]"
										min = 0
										max = 1
									}
								}
								green_progressbar_horizontal = {
									size = { 100% 100% }
									blockoverride "background" {}
									blockoverride "frame" {}
									blockoverride "values" {
										value = "[FixedPointToFloat( JournalEntry.GetCountry.MakeScope.ScriptValue('un_disp_res_yes_frac') )]"
										min = 0
										max = 1
									}
								}
								# two-thirds mark: expulsion and charter reform pass on two
								# thirds of the members with a vote (un_vote_supermajority_passed);
								# 200 is two thirds of the bar's 300.
								icon = {
									visible = "[EqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope.ScriptValue('un_disp_res_supermajority'), '(CFixedPoint)1' )]"
									size = { 3 22 }
									position = { 199 -2 }
									texture = "gfx/interface/progressbar/progressbar_marker.dds"
								}
							}
							textbox = {
								autoresize = yes
								parentanchor = vcenter
								align = left|nobaseline
								text = "je_un_tally_counts"
							}
						}
						textbox = {
							autoresize = yes
							align = left|nobaseline
							using = fontsize_medium
							text = "[SelectLocalization( EqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope.ScriptValue('un_disp_res_supermajority'), '(CFixedPoint)1' ), 'je_un_tally_rule_super', 'je_un_tally_rule_simple' )]"
						}

						### Time in session
						flowcontainer = {
							direction = horizontal
							spacing = 6

							default_progressbar_horizontal = {
								size = { 300 12 }
								parentanchor = vcenter
								blockoverride "values" {
									value = "[FixedPointToFloat( JournalEntry.GetCountry.MakeScope.ScriptValue('un_disp_res_months_frac') )]"
									min = 0
									max = 1
								}
							}
							textbox = {
								autoresize = yes
								parentanchor = vcenter
								align = left|nobaseline
								text = "je_un_session_months"
							}
						}
					}
				}
			}
```

TOPICS. For N = 0..17:

```
						icon = {
							size = { 40 40 }
							visible = "[EqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope.ScriptValue('un_disp_res_topic_code'), '(CFixedPoint)<N>' )]"
							texture = "<TEXTURE>"
						}
```

| N | topic | TEXTURE |
|---|---|---|
| 0 | condemn | `gfx/interface/icons/alert_icons/land_invasion.dds` |
| 1 | sanctions | `gfx/interface/icons/alert_icons/blockaded.dds` |
| 2 | expulsion | `gfx/interface/icons/alert_icons/is_losing_rank.dds` |
| 3 | military_mandate | `gfx/interface/icons/goods_icons/artillery.dds` |
| 4 | peacekeeping_request | `gfx/interface/icons/goods_icons/small_arms.dds` |
| 5 | aid_request | `gfx/interface/icons/goods_icons/groceries.dds` |
| 6 | reform | `gfx/interface/icons/alert_icons/reform_government.dds` |
| 7 | human_rights | `gfx/interface/icons/institution_icons/social_security.dds` |
| 8 | icc | `gfx/interface/icons/institution_icons/police.dds` |
| 9 | npt | `gfx/interface/icons/goods_icons/electricity.dds` |
| 10 | climate | `gfx/interface/icons/goods_icons/wood.dds` |
| 11 | pandemic | `gfx/interface/icons/institution_icons/health_service.dds` |
| 12 | refugee | `gfx/interface/icons/institution_icons/colonization.dds` |
| 13 | heritage | `gfx/interface/icons/goods_icons/fine_art.dds` |
| 14 | decolonization | `gfx/interface/icons/alert_icons/secession.dds` |
| 15 | space | `gfx/interface/icons/goods_icons/aeroplanes.dds` |
| 16 | law_of_sea | `gfx/interface/icons/goods_icons/merchant_marine.dds` |
| 17 | physical_protection | `gfx/interface/icons/goods_icons/explosives.dds` |

- [ ] **Step 4: Loc.** Add to `te_journal_entries_l_english.yml`:

```
 je_un_tally_counts:0 "#G [JournalEntry.GetCountry.MakeScope.ScriptValue('un_disp_res_yes')|0] for#! · #R [JournalEntry.GetCountry.MakeScope.ScriptValue('un_disp_res_no')|0] against#! of [JournalEntry.GetCountry.MakeScope.ScriptValue('un_disp_res_eligible')|0]"
 je_un_tally_tt:0 "The members with a vote: #G green#! have voted for, #R red#! against, grey have not yet voted. Members who lost their vote for arrears, or whose representation is suspended, are not counted."
 je_un_tally_rule_simple:0 "Passes with more votes for than against."
 je_un_tally_rule_super:0 "Passes only with two thirds of the members with a vote (the mark)."
 je_un_session_months:0 "Month #v [JournalEntry.GetCountry.MakeScope.ScriptValue('un_disp_res_months')|0]#! of 12"
```

Run `organize_loc.py`.

- [ ] **Step 5: Run the tests** (`test_un_layout`, then `check_all.sh`). Expected: PASS.
- [ ] **Step 6: Commit** with the message `UN General Assembly: topic icon, tally and time bars for the resolution in session`.

---

### Task 5: Pillar bars

**Files:**
- Modify: `gui/journal_entry_widgets/un_authority_widget.gui` (`te_un_sec_why`: the pillar table)
- Modify: `localization/english/te_journal_entries_l_english.yml`
- Test: `test_un_layout.py` (add `PillarBarTest`)

**Interfaces:** consumes `un_disp_pillar_<p>_{pos,neg,delta,trend}` and `un_disp_pillar_<p>` (Task 1, existing).

- [ ] **Step 1: Add the failing test:**

```python
AUTHORITY = os.path.join(W, "un_authority_widget.gui")
PILLARS = ("participation", "commitment", "credibility", "funding", "order", "delivery")


class PillarBarTest(unittest.TestCase):
    def test_each_pillar_is_a_bar_with_a_trend(self):
        body = _type_body(_read(AUTHORITY), "te_un_sec_why")
        for p in PILLARS:
            for v in ("pos", "neg", "trend"):
                self.assertIn(f"ScriptValue('un_disp_pillar_{p}_{v}')", body, f"{p} {v}")
            self.assertNotRegex(body, rf'blockoverride "pillar_value" \{{ text = "je_un_auth_tbl_{p}_value" \}}',
                                f"{p} still has its old table row")
```

- [ ] **Step 2: Run to verify it fails.**

- [ ] **Step 3: Replace the rows.** In `te_un_sec_why`:
  - **Remove:** the column-headings `un_auth_pillar_row` (`je_un_auth_tbl_h_*`), and the six pillar `un_auth_pillar_row` instances (participation through delivery).
  - **Keep:** the base row, the target row and the weight row as they are.
  - **In the removed rows' place:** insert these six rows, with p running participation, commitment, credibility, funding, order, delivery.

```
				### <p>: the bar spans the pillar's own range, zero at the centre line
				### (un_overview_display_values.txt). Tooltip: what the pillar is,
				### today's reading, and the change since last month.
				flowcontainer = {
					direction = horizontal
					spacing = 8
					margin = { 4 2 }
					tooltip = "je_un_auth_bar_<p>_tt"

					textbox = {
						minimumsize = { 120 -1 }
						maximumsize = { 120 -1 }
						autoresize = yes
						parentanchor = vcenter
						align = left|nobaseline
						using = fontsize_medium
						text = "je_un_auth_tbl_<p>_label"
					}
					double_direction_progressbar = {
						size = { 200 14 }
						parentanchor = vcenter
						blockoverride "value_left" {
							value = "[FixedPointToFloat( JournalEntry.GetCountry.MakeScope.ScriptValue('un_disp_pillar_<p>_neg') )]"
						}
						blockoverride "value_right" {
							value = "[FixedPointToFloat( JournalEntry.GetCountry.MakeScope.ScriptValue('un_disp_pillar_<p>_pos') )]"
						}
					}
					textbox = {
						minimumsize = { 50 -1 }
						autoresize = yes
						parentanchor = vcenter
						align = right|nobaseline
						text = "je_un_auth_tbl_<p>_value"
					}
					widget = {
						size = { 24 24 }
						parentanchor = vcenter

						icon = {
							size = { 24 24 }
							visible = "[EqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope.ScriptValue('un_disp_pillar_<p>_trend'), '(CFixedPoint)1' )]"
							texture = "gfx/interface/icons/generic_icons/trend_up.dds"
						}
						icon = {
							size = { 24 24 }
							visible = "[EqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope.ScriptValue('un_disp_pillar_<p>_trend'), '(CFixedPoint)-1' )]"
							texture = "gfx/interface/icons/generic_icons/trend_down.dds"
						}
						icon = {
							size = { 24 24 }
							visible = "[EqualTo_CFixedPoint( JournalEntry.GetCountry.MakeScope.ScriptValue('un_disp_pillar_<p>_trend'), '(CFixedPoint)0' )]"
							texture = "gfx/interface/icons/generic_icons/trend_nochange.dds"
						}
					}
				}
```

`je_un_auth_tbl_<p>_value` is reused from the old row, so the value keeps its existing formatting. The test tells old from new by the old row's `pillar_value` blockoverride.

- [ ] **Step 4: Loc.** For each pillar add a tooltip that joins the existing tooltip, the reading and the change:

```
 je_un_auth_bar_credibility_tt:0 "$je_un_auth_tbl_credibility_tt$\n\n#b Now:#! $je_un_auth_tbl_credibility_detail$\n#b Since last month:#! [JournalEntry.GetCountry.MakeScope.ScriptValue('un_disp_pillar_credibility_delta')|+1]"
```

Write the same line for the other five pillars. Check that each `je_un_auth_tbl_<p>_tt` and `_detail` key exists (`git grep -n "je_un_auth_tbl_<p>_tt:\|je_un_auth_tbl_<p>_detail:" localization/english`). Run `organize_loc.py`.

- [ ] **Step 5: Run the tests** (`test_un_layout`, then `check_all.sh`). Expected: PASS.
- [ ] **Step 6: Commit** with the message `UN authority: pillar bars with last-month trends`.

---

### Task 6: Probe, docs, verification, deploy

**Files:**
- Modify: `gui/diplomatic_overview.gui` (the probe)
- Modify: `docs/systems/journal_entry_systems.md` (CRLF: edit bytes), `docs/guides/gui_modding_guide.md` (CRLF), `docs/systems/system_panels_feasibility.md`, `docs/superpowers/specs/2026-09-28-un-gui-pass-design.md` (status line)

- [ ] **Step 1: The probe.** In the UN tab, directly under its `default_header`:

```
					# ROUND-2 PROBE (remove in round 2). Can the GUI walk a global list?
					# If this counts the mission registry, round 2 reads the UN's
					# global lists directly; if not, script mirrors them per player.
					textbox = {
						visible = "[InDebugMode]"
						autoresize = yes
						align = left|nobaseline
						raw_text = "Probe: GetGlobalList('un_mission_registry') holds [GetDataModelSize( GetGlobalList('un_mission_registry') )] items"
					}
```

- [ ] **Step 2: Docs.**
  - `journal_entry_systems.md`, UN § Chamber Widget: rewrite the "Second host" paragraph to describe the new layout (overview, status, reference; the layout file; the display values; the seat refresh).
  - `gui_modding_guide.md` JE widget table: add rows for `un_overview_widget.gui` and `un_layout_widget.gui`, and change the chamber and authority rows to "section types".
  - Feasibility doc header: add a line under the UN bullet: "Round 1 of a visual pass (spec 2026-09-28-un-gui-pass-design.md)".
  - Spec status: "Round 1 built, <date>, commits <range>".
  - Confirm CRLF on both CRLF files afterwards (`grep -c $'\r$'` against `wc -l`).

- [ ] **Step 3: Full verification.** Run `check_all.sh` with the tests enabled: the suite OK, every CI step at exit 0, and the three local audits at 0 unreviewed. Then the local ModState run of `loc_render_audit`, `localization_accessor_audit` and `concept_reference_audit` must show 0 flags.

- [ ] **Step 4: Deploy for the owner's look.**
  - Commit anything outstanding.
  - In the main checkout: confirm it's clean and on `main`, then `git switch --detach feat/banking-budget-tab && ./scripts/deploy.sh` (dry run: only expected files) `&& ./scripts/deploy.sh --apply && git switch main`.
  - Push.
  - Update PR #567's body through `gh api -X PATCH … -F body=@file`. Add a UN section and an in-game checklist:
    - each overview element in each state;
    - the flags open their countries;
    - the agencies light up;
    - the pies and trend icons after a month;
    - the tally on a simple and a supermajority topic;
    - the collapse defaults;
    - the journal draws its bar once;
    - the probe's count in debug mode.

- [ ] **Step 5: Commit** the docs with the message `Docs: UN GUI pass round 1`.
