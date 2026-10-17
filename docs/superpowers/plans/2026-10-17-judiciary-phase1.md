# Judiciary, Phase 1 (the law group and Judicial Independence) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the Judiciary law group: six court laws whose tooltips state every rule a player plans around, the Judicial Independence score that turns a court's ceiling into legitimacy and credit over decades, entrenchment of constitutional law groups under strong courts, the overhaul shock when courts are cut down, the score's cost on Forceful Legislation and the tax Force Through, 1836 starting laws, ideology stances, and the docs and player guide.

**Architecture:** Laws in a new `common/laws/te_judiciary_laws.txt`, Executive Tribunals first. Every rule is a script-only modifier line on the law that carries it (the ceiling, the paper court, entrenchment, Statutory Courts' two conditional lines, the capture), so the law's tooltip states it; script reads the sums (the banking dials' pattern). One score, `var:te_judicial_independence`, moved yearly toward `te_jud_ceiling` and spent by override. The scaled modifiers are written only by `te_jud_refresh` from the monthly country pulse. Entrenchment is an enactment modifier added at `on_law_enactment_started`. The shock is a hidden country event fired a week after a ceiling law changes, from `on_law_activated`, whose ROOT is the law. Stances come from named lists in `ideology_modifications.py`. A Python test file pins every value against the spec.

**Tech Stack:** Victoria 3 Paradox script (`common/`, `events/`), localization YAML, Python 3.11/3.12 `unittest`.

**Spec:** `docs/superpowers/specs/2026-10-17-judiciary-design.md` (§§ 1–9, 11). Phases 2–4 (§ 10) get their own plans after the phase 1 play-test.

## Global Constraints

- **Values (spec).** Ceilings: Executive 10, Religious 40, Statutory 70, Constitutional 100, Supremacy 100, Algorithmic 60, halved under a paper court (Autocracy and its variants, Single-Party State, Algorithmic Governance). Score: +4 a year below the ceiling, −10 a year above it, clamped to the ceiling either way; starts at half the ceiling unless history sets it. Spending: 5 / 10 / 20 (Forceful Legislation b / c / e), 10 (tax Force Through), floored at 0. Shock at a gap of 20 or more, 5 years decaying, multiplier gap ÷ 100; radicals at 40 or more. Entrenchment: −10% (Constitutional Review), −15% (Judicial Supremacy). Statutory Courts: +10 legitimacy from votes with an elected government, +25 authority without.
- **Owner's rulings (2026-10-17, second round):** no credit floor term; Constitutional Review on `human_rights`; Judicial Supremacy reachable from any court, with legitimacy −5, movement radicalism −10% and pop attraction +10%; Statutory Courts' conditional bonus; every rule on the law's tooltip as a script-only line. The country-modifier tab is a separate spec (spec § 13).
- **A rule is a tooltip line, and script reads the line.** Each lives on the law as a `script_only` modifier type (`judiciary_modifier_types.txt`). Where the engine needs a named modifier (the enactment modifiers), the line picks a tier and `test_judiciary.py` holds every line to a tier.
- **Modifier sums lag a law change.** `te_jud_ceiling` reads them, so the score is first seeded at the monthly pulse (not `on_game_started`), the old-save repair waits a month between assigning courts and seeding scores, and the shock event waits a week.
- **ROOT.** `add_modifier { multiplier = var:X }` resolves against ROOT (`scripting_best_practices.md` § "add_modifier { multiplier = var:X } Resolves Against ROOT"). Only two places apply a multiplier: `te_jud_refresh` (from `on_monthly_pulse_country`, ROOT = the country) and `te_judiciary_events.1` (a country event). `on_law_activated` has ROOT = the law, so it only matches the law type and fires the event on `owner`. `on_game_started` has ROOT = none, so it only sets variables there.
- **One refresh site.** `te_jud_refresh` is the only writer of the four scaled modifiers (`te_judicial_independence`, `te_jud_votes_legitimacy`, `te_jud_unelected_authority`, `te_jud_algorithmic_capture`), and only `te_jud_monthly` calls it. Never `remove_variable` a variable a live modifier's multiplier reads (`te_jud_modifier_mult`, `te_jud_votes_mult`, `te_jud_authority_mult`, `te_jud_capture_mult`, `te_jud_overhaul_mult`).
- **Variables, not modifiers, hold state** (a revolution's winner inherits variables only).
- **Clamp with `if` + `set_variable`**, never `min`/`max` inside `change_variable` (`change_variable_clamp_audit`).
- **Every option that changes the score says so** in `custom_tooltip = { text = … <effect> }` (`silent_variable_audit`).
- **Every `lawgroup_judiciary` block in an ideology names all six laws** (`ideology_lawgroup_audit --strict`).
- **Files.** Brace-based `.txt`: tabs and exactly one UTF-8 BOM; run `python3 scripts/format_paradox_tabs.py <files>` after writing. New loc keys go in the files named per task, then `python3 organize_loc.py`, and commit everything it moves.
- **Python must run on 3.11**: no PEP 701 f-strings (`grep -nE "f\"[^\"]*\{[^}\"]*\"|f'[^']*\{[^}']*'" <files>`).
- **Tests** need the dummy env in a game-less checkout: `VIC3_BASE_GAME=/nonexistent VIC3_MOD_DEPLOY_TARGET=/nonexistent VIC3_VANILLA_REPO=/nonexistent VIC3_VANILLA_DOCS_RUNTIME=/nonexistent VIC3_GAME_LOGS=/nonexistent`. Use the venv Python (`.venv/bin/python`). Read results with `grep -E '^(Ran |OK|FAILED)'`.
- Never `POST /reload` from a worktree. Per task run `test_judiciary.py` and `ruff`; Task 12 runs everything CI runs.
- **Dry run (2026-10-17, after the owner's second review).** Tasks 1–7's code, applied verbatim to a scratch
  worktree, passes `test_judiciary.py` (38 tests), every `--strict` audit CI runs, `effect_trigger_validity_audit` (no
  flags), `modifier_visibility_audit`, `organize_loc --check` after one run, the offline ideology regeneration and its
  `--check`, and the full unit suite (7,628 tests). The runs found three things the steps now cover: the consistency file needs regenerating in Task 1, the
  old-save repair must be named `te_repair_*`, and a modifier name needs `’` rather than a straight apostrophe.

## Review Focus

1. **The shock's multiplier**: applied only inside `te_judiciary_events.1`, from a stored variable, never from `on_law_activated`'s law scope. Test: Task 5 `test_shock_runs_in_a_country_event`.
2. **Seeding never shocks** a new game or an old save, a new country mid-game keeps its law, and no score is seeded before the laws' modifier sums are in place. Test: Task 3 `test_seeding_waits_for_the_monthly_pulse`, `test_old_save_seeding_is_a_marked_repair`, Task 5 `test_shock_needs_seeding`.
3. **Secularizing drops Religious Courts to Statutory Courts** when Rationalism is researched, else Executive Tribunals. Test: Task 7 `test_religious_courts_fall_to_statutory`.
4. **One writer**: no other file adds or removes the four scaled modifiers. Test: Task 3 `test_one_refresh_site`.
5. **The tooltip is the rule**: the ceiling and entrenchment read the laws' lines, never `has_law`. Test: Task 2 `test_ceiling_reads_the_laws_lines`, Task 4 `test_the_laws_lines_pick_the_tier`.
6. **Entrenchment hits the right groups**: each representative law is in the group the spec names. Test: Task 4 `test_protected_groups_match_spec`.
7. **The concept's live value** renders (`loc_render_audit`), and the description of Judicial Supremacy says the courts do not govern (the owner's requirement).

---

### Task 1: The law group, the six laws and their tooltip lines

**Files:**
- Create: `common/modifier_type_definitions/judiciary_modifier_types.txt`
- Modify: `common/law_groups/extra_law_groups.txt`
- Create: `common/laws/te_judiciary_laws.txt`
- Create: `common/laws/te_judiciary_law_injections.txt`
- Modify: `common/laws/extra_laws.txt` (`law_algorithmic_governance`'s `modifier` block)
- Modify: `localization/english/te_laws_l_english.yml`, `localization/english/te_miscellaneous_l_english.yml`
- Create: `test_judiciary.py`

**Interfaces:**
- Produces: `lawgroup_judiciary`; `law_executive_tribunals`, `law_religious_courts`, `law_statutory_courts`, `law_constitutional_review`, `law_judicial_supremacy`, `law_algorithmic_jurisprudence`; the display types `country_judicial_independence_ceiling_add`, `country_judicial_independence_ceiling_mult`, `country_court_challenges_ignored_bool`, `country_constitutional_law_enactment_success_add`, `country_rights_law_enactment_success_add`, `country_legitimacy_from_votes_if_elected_add`, `country_authority_if_unelected_add`, `country_override_with_algorithmic_governance_add` (spec § 2.7).

- [ ] **Step 1: Write the failing tests** (`test_judiciary.py`)

```python
"""Judiciary law group (docs/superpowers/specs/2026-10-17-judiciary-design.md).

What the engine would never report:

- A law whose values drift from the spec, or a law out of order: the first law
  in the file is what an unseeded country and an old save get.
- A rule a player plans around that the law's tooltip doesn't show: every one
  is a display line on the law (a script_only modifier type) that script reads.
- An ideology with a Judiciary block that leaves a law out: the group backs the
  law it omits as if neutral.
- A second writer of a scaled modifier, or a multiplier applied where ROOT is
  not the country (the engine substitutes 1.0 silently).
- A Forceful Legislation option that spends the score without saying so.

No game install needed.
"""

import glob
import json
import os
import re
import unittest

from paradox_file_parser import ParadoxFileParser

REPO = os.path.dirname(os.path.abspath(__file__))
LAWS = os.path.join(REPO, "common", "laws", "te_judiciary_laws.txt")
INJECTIONS = os.path.join(REPO, "common", "laws", "te_judiciary_law_injections.txt")
EXTRA_LAWS = os.path.join(REPO, "common", "laws", "extra_laws.txt")
GROUPS = os.path.join(REPO, "common", "law_groups", "extra_law_groups.txt")
TYPES = os.path.join(REPO, "common", "modifier_type_definitions", "judiciary_modifier_types.txt")

COURT_LAWS = (
    "law_executive_tribunals",
    "law_religious_courts",
    "law_statutory_courts",
    "law_constitutional_review",
    "law_judicial_supremacy",
    "law_algorithmic_jurisprudence",
)
PAPER_COURT_LAWS = (
    "law_autocracy",
    "law_bakufu",
    "law_neo_absolutism",
    "law_single_party_state",
    "law_algorithmic_governance",
)
DISPLAY_TYPES = (
    "country_judicial_independence_ceiling_add",
    "country_judicial_independence_ceiling_mult",
    "country_court_challenges_ignored_bool",
    "country_constitutional_law_enactment_success_add",
    "country_rights_law_enactment_success_add",
    "country_legitimacy_from_votes_if_elected_add",
    "country_authority_if_unelected_add",
    "country_override_with_algorithmic_governance_add",
)

# Spec § 2 and § 2.7. Values as written in the file.
SPEC_LAWS = {
    "law_executive_tribunals": {
        "progressiveness": "-50",
        "tech": [],
        "modifier": {
            "country_judicial_independence_ceiling_add": "10",
            "country_legislative_override_capacity_add": "1",
            "country_authority_add": "50",
            "country_suppression_cost_mult": "-0.1",
            "country_credit_standing_add": "0.01",
        },
    },
    "law_religious_courts": {
        "progressiveness": "-20",
        "tech": [],
        "modifier": {
            "country_judicial_independence_ceiling_add": "40",
            "interest_group_ig_devout_pol_str_mult": "0.15",
            "state_bureaucracy_population_base_cost_factor_mult": "-0.05",
            "country_credit_standing_add": "0.005",
        },
    },
    "law_statutory_courts": {
        "progressiveness": "0",
        "tech": ["rationalism"],
        "modifier": {
            "country_judicial_independence_ceiling_add": "70",
            "country_suppression_cost_mult": "0.1",
            "state_bureaucracy_population_base_cost_factor_mult": "0.05",
            "country_legitimacy_from_votes_if_elected_add": "10",
            "country_authority_if_unelected_add": "25",
        },
    },
    "law_constitutional_review": {
        "progressiveness": "50",
        "tech": ["human_rights"],
        "modifier": {
            "country_judicial_independence_ceiling_add": "100",
            "country_legislative_override_capacity_add": "-2",
            "country_suppression_cost_mult": "0.25",
            "state_bureaucracy_population_base_cost_factor_mult": "0.05",
            "country_constitutional_law_enactment_success_add": "-0.1",
        },
    },
    "law_judicial_supremacy": {
        "progressiveness": "75",
        "tech": ["civil_rights_movement"],
        "modifier": {
            "country_judicial_independence_ceiling_add": "100",
            "country_legislative_override_capacity_add": "-3",
            "country_suppression_cost_mult": "0.4",
            "state_bureaucracy_population_base_cost_factor_mult": "0.05",
            "country_legitimacy_base_add": "-5",
            "country_credit_standing_add": "0.003",
            "country_legitimacy_ideological_incoherence_mult": "-0.25",
            "political_movement_radicalism_add": "-0.1",
            "political_movement_pop_attraction_mult": "0.1",
            "country_constitutional_law_enactment_success_add": "-0.15",
            "country_rights_law_enactment_success_add": "-0.15",
        },
    },
    "law_algorithmic_jurisprudence": {
        "progressiveness": "25",
        "tech": ["generative_ai"],
        "modifier": {
            "country_judicial_independence_ceiling_add": "60",
            "state_bureaucracy_population_base_cost_factor_mult": "-0.1",
            "country_override_with_algorithmic_governance_add": "2",
        },
    },
}


def _parse(path):
    parser = ParadoxFileParser()
    parser.parse_file(path, apply_directives=False)
    return parser.data


def _body(node):
    """The parser stores `key = { ... }` as ('=', body); unwrap it."""
    return node[1] if isinstance(node, tuple) else node


def _read(path):
    with open(path, encoding="utf-8-sig") as fh:
        return fh.read()


def _block(text, name):
    """The text of the top-level `name = {` block, braces balanced."""
    match = re.search(r"^%s = \{" % re.escape(name), text, re.M)
    if match is None:
        raise AssertionError("%s not found" % name)
    depth = 0
    for i in range(text.index("{", match.start()), len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[match.start() : i + 1]
    raise AssertionError("%s is unbalanced" % name)


def _loc_lines():
    """{key: line} over every English loc file (organize_loc may move a key)."""
    lines = {}
    for path in glob.glob(os.path.join(REPO, "localization", "english", "**", "*.yml"), recursive=True):
        for line in _read(path).splitlines():
            match = re.match(r"\s+([A-Za-z0-9_.\-]+):\d*\s", line)
            if match:
                lines[match.group(1)] = line
    return lines


def _loc_keys():
    return set(_loc_lines())


def _modifier(body):
    return {k: _body(v) for k, v in _body(body["modifier"]).items()}


class LawsTest(unittest.TestCase):
    def setUp(self):
        self.laws = _parse(LAWS)

    def test_group_is_power_structure(self):
        group = _body(_parse(GROUPS)["lawgroup_judiciary"])
        self.assertEqual(_body(group["law_group_category"]), "power_structure")
        self.assertEqual(_body(group["ideological_opinion_impact"]), "0.5")
        self.assertEqual(_body(group["affected_by_regime_change"]), "yes")

    def test_six_laws_executive_first(self):
        self.assertEqual(tuple(self.laws), COURT_LAWS)

    def test_values_match_spec(self):
        for law, spec in SPEC_LAWS.items():
            body = _body(self.laws[law])
            with self.subTest(law=law):
                self.assertEqual(_body(body["group"]), "lawgroup_judiciary")
                self.assertEqual(_body(body["progressiveness"]), spec["progressiveness"])
                self.assertEqual(_body(body.get("unlocking_technologies", ("=", []))), spec["tech"])
                self.assertEqual(_modifier(body), spec["modifier"])

    def test_religious_courts_need_a_church(self):
        body = _body(self.laws["law_religious_courts"])
        self.assertEqual(_body(body["disallowing_laws"]), ["law_total_separation", "law_state_atheism"])

    def test_no_law_gates(self):
        # The owner (2026-10-17): Judicial Supremacy is reachable from any court.
        for law in COURT_LAWS:
            self.assertNotIn("unlocking_laws", _body(self.laws[law]), law)

    def test_display_types_are_script_only(self):
        types = {k: _body(v) for k, v in _parse(TYPES).items()}
        self.assertEqual(set(types), set(DISPLAY_TYPES))
        for name, body in types.items():
            if name.endswith("_bool"):
                self.assertEqual(_body(body["boolean"]), "yes", name)
            else:
                self.assertEqual(_body(body["script_only"]), "yes", name)

    def test_paper_courts_carry_both_lines(self):
        injected = _parse(INJECTIONS)
        bodies = {law: _body(injected["INJECT:" + law]) for law in PAPER_COURT_LAWS[:-1]}
        bodies["law_algorithmic_governance"] = _body(_parse(EXTRA_LAWS)["law_algorithmic_governance"])
        for law, body in bodies.items():
            modifier = _modifier(body)
            self.assertEqual(modifier.get("country_judicial_independence_ceiling_mult"), "-0.5", law)
            self.assertEqual(modifier.get("country_court_challenges_ignored_bool"), "yes", law)

    def test_names_and_descriptions(self):
        keys = _loc_keys()
        for key in COURT_LAWS + DISPLAY_TYPES + ("lawgroup_judiciary",):
            self.assertIn(key, keys)
            self.assertIn(key + "_desc", keys)

    def test_supremacy_says_the_courts_do_not_govern(self):
        # The owner's requirement (spec Decisions): otherwise it would be a
        # Distribution of Power law.
        self.assertIn("the government still governs", _loc_lines()["law_judicial_supremacy_desc"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run them and see them fail**

Run: `.venv/bin/python test_judiciary.py 2>&1 | grep -E '^(Ran |OK|FAILED)'`
Expected: FAILED (no `te_judiciary_laws.txt`).

- [ ] **Step 3: The display types**, `common/modifier_type_definitions/judiciary_modifier_types.txt` (UTF-8 with one BOM, tabs):

```
# ======================================================================
#  JUDICIARY — tooltip lines (spec § 2.7)
#  The banking dials' pattern (banking_cycle_modifier_types.txt): the law
#  carries the number, so its tooltip states the rule and the engine renders
#  the breakdown. Script reads the sum (te_judiciary_values.txt,
#  te_judiciary_effects.txt, te_judiciary_on_actions.txt) and applies the
#  effect; the engine applies none of these itself.
# ======================================================================

# The highest Judicial Independence the courts can earn. Each court law.
country_judicial_independence_ceiling_add = {
	color = good
	decimals = 0
	script_only = yes
	game_data = { ai_value = 0 }
}

# A regime whose executive answers to nobody earns its courts less trust:
# Autocracy and its variants, Single-Party State, Algorithmic Governance.
country_judicial_independence_ceiling_mult = {
	color = good
	percent = yes
	decimals = 0
	script_only = yes
	game_data = { ai_value = 0 }
}

# ... and its courts challenge no change to the constitution (§ 3.4). Read by
# te_jud_paper_court.
country_court_challenges_ignored_bool = { color = bad  boolean = yes }

# Enactment success of a law in a protected group (§ 3.4). Read at
# on_law_enactment_started to pick the enactment modifier.
country_constitutional_law_enactment_success_add = {
	color = good
	percent = yes
	decimals = 0
	script_only = yes
	game_data = { ai_value = 0 }
}

country_rights_law_enactment_success_add = {
	color = good
	percent = yes
	decimals = 0
	script_only = yes
	game_data = { ai_value = 0 }
}

# Statutory Courts (§ 2.3): legitimacy from votes under an elected
# government, authority without one. te_jud_refresh applies whichever holds.
country_legitimacy_from_votes_if_elected_add = {
	color = good
	decimals = 0
	script_only = yes
	game_data = { ai_value = 0 }
}

country_authority_if_unelected_add = {
	color = good
	decimals = 0
	script_only = yes
	game_data = { ai_value = 0 }
}

# Algorithmic Jurisprudence's capture (§ 2.6): override capacity while
# Algorithmic Governance is in force. te_jud_refresh applies it.
country_override_with_algorithmic_governance_add = {
	color = neutral
	decimals = 0
	script_only = yes
	game_data = { ai_value = 0 }
}
```

- [ ] **Step 4: Add the group** at the end of the power-structure entries in `common/law_groups/extra_law_groups.txt`, after `lawgroup_state_power`:

```
# Judiciary (docs/superpowers/specs/2026-10-17-judiciary-design.md): who checks
# the government, and how far the courts are trusted to. Courts were imposed
# with regimes (West Germany 1951, Japan 1947), so regime change carries them.
lawgroup_judiciary = {
	law_group_category = power_structure
	ideological_opinion_impact = 0.5
	affected_by_regime_change = yes
}
```

- [ ] **Step 5: Write `common/laws/te_judiciary_laws.txt`** (UTF-8 with one BOM, tabs). Icons are placeholders (Task 8). The display lines go first in each `modifier` block, so the tooltip opens with the ceiling.

```
# ======================================================================
#  JUDICIARY — laws
#  Spec: docs/superpowers/specs/2026-10-17-judiciary-design.md
#  The laws carry what the courts can do. Judicial Independence
#  (te_judiciary_effects.txt) carries how far they are trusted, up to the
#  ceiling each law's tooltip shows. Every rule a player plans around is a
#  line in the law's modifier block (judiciary_modifier_types.txt).
#  Executive Tribunals stays FIRST: the first law in the file is what an
#  unseeded country and an old save get.
#  Placeholder icons: docs/systems/mod_systems.md § Judiciary.
# ======================================================================

law_executive_tribunals = {
	group = lawgroup_judiciary
	icon = "gfx/interface/icons/law_icons/autocracy.dds"

	# No gate: the consistency walk's terminal fallback for the group.
	progressiveness = -50

	modifier = {
		country_judicial_independence_ceiling_add = 10
		country_legislative_override_capacity_add = 1
		country_authority_add = 50
		# Nobody frees a dissident on a writ.
		country_suppression_cost_mult = -0.1
		# Justice the ruler can bend: lenders charge for it (1pp).
		country_credit_standing_add = 0.01
	}

	ai_enact_weight_modifier = {
		value = 10
		if = {
			limit = { ai_has_enact_weight_modifier_journal_entries = yes }
			add = 750
		}
	}
}

law_religious_courts = {
	group = lawgroup_judiciary
	icon = "gfx/interface/icons/law_icons/state_religion.dds"

	# 20 from Statutory Courts and 30 from Executive Tribunals: a country that
	# secularizes falls to Statutory Courts when it has Rationalism.
	progressiveness = -20

	# Courts of the faith need an established faith. The consistency walk moves
	# a country that enacts either law (te_fix_inconsistent_laws).
	disallowing_laws = {
		law_total_separation
		law_state_atheism
	}

	modifier = {
		country_judicial_independence_ceiling_add = 40
		interest_group_ig_devout_pol_str_mult = 0.15
		# Clergy staff the courts, paid from fees and endowments.
		state_bureaucracy_population_base_cost_factor_mult = -0.05
		# Commercial disputes with foreigners: the Ottoman commercial courts
		# (1840) and Egypt's mixed courts (1875) answered this.
		country_credit_standing_add = 0.005
	}

	ai_enact_weight_modifier = {
		value = 10
		if = {
			limit = { ai_has_enact_weight_modifier_journal_entries = yes }
			add = 750
		}
	}
}

law_statutory_courts = {
	group = lawgroup_judiciary
	icon = "gfx/interface/icons/law_icons/appointed_bureaucrats.dds"

	progressiveness = 0

	# Codification: the Prussian General Code (1794), the Code civil (1804).
	unlocking_technologies = {
		rationalism
	}

	modifier = {
		country_judicial_independence_ceiling_add = 70
		country_suppression_cost_mult = 0.1
		state_bureaucracy_population_base_cost_factor_mult = 0.05
		# Whoever makes the law has the last word (spec § 2.3): an elected
		# legislature gains standing (Presidential Republic's +10), a crown
		# gains authority. te_jud_refresh applies whichever holds.
		country_legitimacy_from_votes_if_elected_add = 10
		country_authority_if_unelected_add = 25
	}

	ai_enact_weight_modifier = {
		value = 10
		if = {
			limit = { ai_has_enact_weight_modifier_journal_entries = yes }
			add = 750
		}
	}
}

law_constitutional_review = {
	group = lawgroup_judiciary
	icon = "gfx/interface/icons/law_icons/guaranteed_liberties.dds"

	progressiveness = 50

	# The theory of rights held against the majority. The United States holds
	# the law from history (Marbury v. Madison, 1803), which ignores this, as
	# other laws are held before their technology.
	unlocking_technologies = {
		human_rights
	}

	modifier = {
		country_judicial_independence_ceiling_add = 100
		country_legislative_override_capacity_add = -2
		country_suppression_cost_mult = 0.25
		state_bureaucracy_population_base_cost_factor_mult = 0.05
		# Entrenchment (spec § 3.4), read at on_law_enactment_started.
		country_constitutional_law_enactment_success_add = -0.1
	}

	ai_enact_weight_modifier = {
		value = 10
		if = {
			limit = { ai_has_enact_weight_modifier_journal_entries = yes }
			add = 750
		}
	}
}

law_judicial_supremacy = {
	group = lawgroup_judiciary
	icon = "gfx/interface/icons/law_icons/protected_speech.dds"

	progressiveness = 75

	# The Warren Court (1953-69). Reachable from any court: from Statutory
	# Courts it is a legislature legislating itself out of supremacy.
	unlocking_technologies = {
		civil_rights_movement
	}

	modifier = {
		country_judicial_independence_ceiling_add = 100
		country_legislative_override_capacity_add = -3
		country_suppression_cost_mult = 0.4
		state_bureaucracy_population_base_cost_factor_mult = 0.05
		# A contested court: legitimacy peaks at Constitutional Review (spec § 2.5).
		country_legitimacy_base_add = -5
		# Lenders can't predict policy made by rulings.
		country_credit_standing_add = 0.003
		# Divisive questions go to the court, so coalitions hold (Graber, 1993).
		country_legitimacy_ideological_incoherence_mult = -0.25
		# Movements litigate: they win more and riot less.
		political_movement_radicalism_add = -0.1
		political_movement_pop_attraction_mult = 0.1
		# Entrenchment (spec § 3.4), read at on_law_enactment_started.
		country_constitutional_law_enactment_success_add = -0.15
		country_rights_law_enactment_success_add = -0.15
	}

	ai_enact_weight_modifier = {
		value = 10
		if = {
			limit = { ai_has_enact_weight_modifier_journal_entries = yes }
			add = 750
		}
	}
}

law_algorithmic_jurisprudence = {
	group = lawgroup_judiciary
	icon = "gfx/interface/icons/law_icons/law_algorithmic_governance.dds"

	progressiveness = 25

	unlocking_technologies = {
		generative_ai
	}

	modifier = {
		country_judicial_independence_ceiling_add = 60
		state_bureaucracy_population_base_cost_factor_mult = -0.1
		# The capture (spec § 2.6): te_jud_refresh applies it while
		# Algorithmic Governance is in force.
		country_override_with_algorithmic_governance_add = 2
	}

	ai_enact_weight_modifier = {
		value = 10
		if = {
			limit = { ai_has_enact_weight_modifier_journal_entries = yes }
			add = 750
		}
	}
}
```

- [ ] **Step 6: The paper courts.** `common/laws/te_judiciary_law_injections.txt` (UTF-8 with one BOM). An INJECTed `modifier` block on a law adds to the law's own (`scripting_best_practices.md`; `law_laissez_faire` carries three).

```
# ======================================================================
#  JUDICIARY — paper courts (spec § 3.1, § 3.4)
#  A regime whose executive answers to nobody: its courts earn half the
#  trust and challenge nothing. The lines show on the law's own tooltip.
#  Variants carry their own modifier blocks, so Bakufu and Neo-Absolutism
#  are injected as well as Autocracy. Algorithmic Governance, a mod law,
#  carries the same two lines inline (extra_laws.txt).
# ======================================================================

INJECT:law_autocracy = {
	modifier = {
		country_judicial_independence_ceiling_mult = -0.5
		country_court_challenges_ignored_bool = yes
	}
}

INJECT:law_bakufu = {
	modifier = {
		country_judicial_independence_ceiling_mult = -0.5
		country_court_challenges_ignored_bool = yes
	}
}

INJECT:law_neo_absolutism = {
	modifier = {
		country_judicial_independence_ceiling_mult = -0.5
		country_court_challenges_ignored_bool = yes
	}
}

INJECT:law_single_party_state = {
	modifier = {
		country_judicial_independence_ceiling_mult = -0.5
		country_court_challenges_ignored_bool = yes
	}
}
```

In `law_algorithmic_governance`'s `modifier` block (`common/laws/extra_laws.txt`), after `country_legislative_override_capacity_add = 2`:

```

		# A paper court (Judiciary spec § 3.1): te_judiciary_law_injections.txt
		# gives the other executive-only laws the same two lines.
		country_judicial_independence_ceiling_mult = -0.5
		country_court_challenges_ignored_bool = yes
```

- [ ] **Step 7: Names and descriptions.** Laws and group in `localization/english/te_laws_l_english.yml`, beside `lawgroup_criminal_justice`. Descriptions are flavour with no figures (the enactment popup's box does not scroll); the figures are the tooltip lines.

```yaml
 lawgroup_judiciary:0 "Judiciary"
 lawgroup_judiciary_desc:0 "Who judges disputes and the government's own acts, how independent the judges are, and whether they can overturn the law."
 law_executive_tribunals:0 "Executive Tribunals"
 law_executive_tribunals_desc:0 "The officials who govern also judge. A magistrate collects the taxes, keeps the peace and hears the cases of the district, and a judge who displeases the ruler is replaced."
 law_religious_courts:0 "Religious Courts"
 law_religious_courts_desc:0 "Clerical judges apply religious law to most disputes, beside whatever the ruler decrees. They answer to the faith rather than to the state. Should the state separate itself from religion, state courts replace them."
 law_statutory_courts:0 "Statutory Courts"
 law_statutory_courts_desc:0 "Judges hold office for life or by career and cannot be dismissed for their rulings, but they apply the law as written. Whoever makes the law, a parliament or a king in council, has the last word: no court can strike it down."
 law_constitutional_review:0 "Constitutional Review"
 law_constitutional_review_desc:0 "The courts may strike down any law that breaches the written constitution. Ordinary majorities govern within it, and changing its core is slow."
 law_judicial_supremacy:0 "Judicial Supremacy"
 law_judicial_supremacy_desc:0 "The courts decide only the cases brought before them, and the government still governs. But the courts' reading of the constitution binds the legislature, reaches rights the text does not name, and no ordinary law can overturn it."
 law_algorithmic_jurisprudence:0 "Algorithmic Jurisprudence"
 law_algorithmic_jurisprudence_desc:0 "Models decide routine cases and draft judgments for the rest, and human judges sign them. The rulings are fast and consistent, and as impartial as whoever trains the models."
```

The display types in `localization/english/te_miscellaneous_l_english.yml` (`organize_loc.py` files them). A modifier name takes `’` (U+2019), never a straight apostrophe, which breaks the engine's quoted tooltip argument (`loc_render_audit`):

```yaml
 country_judicial_independence_ceiling_add:0 "[Concept('concept_judicial_independence','Judicial Independence')] Ceiling"
 country_judicial_independence_ceiling_add_desc:0 "The highest [concept_judicial_independence] the courts can earn. The score rises by 4 a year toward it and falls by 10 a year above it."
 country_judicial_independence_ceiling_mult:0 "[Concept('concept_judicial_independence','Judicial Independence')] Ceiling"
 country_judicial_independence_ceiling_mult_desc:0 "The executive can ignore its courts, so they earn less trust."
 country_court_challenges_ignored_bool:0 "Courts Can’t Challenge the Government"
 country_court_challenges_ignored_bool_desc:0 "No court challenges a change to the constitution, whatever the Judiciary law."
 country_constitutional_law_enactment_success_add:0 "Enactment Success of Constitutional Laws"
 country_constitutional_law_enactment_success_add_desc:0 "For laws on Distribution of Power, Governance Principles, Church and State, Citizenship, Free Speech, Internal Security, State Power and the Judiciary: the courts hear challenges to them. Not while the courts can't challenge the government (Autocracy, Single-Party State, Algorithmic Governance)."
 country_rights_law_enactment_success_add:0 "Enactment Success of Rights Laws"
 country_rights_law_enactment_success_add_desc:0 "For laws on Rights of Women, Slavery, Minority Rights, LGBTQ+ Rights and Privacy Rights. Not while the courts can't challenge the government."
 country_legitimacy_from_votes_if_elected_add:0 "[concept_legitimacy] from Votes, with an Elected Government"
 country_legitimacy_from_votes_if_elected_add_desc:0 "Under Landed, Wealth or Census Voting, Universal Suffrage or Anarchy: the legislature's law has the last word, and the government elected to make it gains standing."
 country_authority_if_unelected_add:0 "[concept_authority], without an Elected Government"
 country_authority_if_unelected_add_desc:0 "Under any other Distribution of Power law: the crown's law has the last word."
 country_override_with_algorithmic_governance_add:0 "[Concept('concept_legislative_override_capacity','Legislative Override Capacity')] under Algorithmic Governance"
 country_override_with_algorithmic_governance_add_desc:0 "With Algorithmic Governance, the system that writes the law also judges it."
```

- [ ] **Step 8: Format, run the tests, see them pass**

Run: `python3 scripts/format_paradox_tabs.py common/laws/te_judiciary_laws.txt common/laws/te_judiciary_law_injections.txt common/modifier_type_definitions/judiciary_modifier_types.txt common/law_groups/extra_law_groups.txt common/laws/extra_laws.txt && .venv/bin/python test_judiciary.py 2>&1 | grep -E '^(Ran |OK|FAILED)'`
Expected: OK. (`concept_judicial_independence` arrives in Task 2; `concept_reference_audit` waits for it.)

- [ ] **Step 9: Regenerate the consistency file.** Religious Courts' `disallowing_laws` adds a cascade, so
  `test_gen_law_consistency` fails until `common/scripted_effects/extra_law_consistency_generated.txt` is rewritten:
  `.venv/bin/python gen_law_consistency.py` (it reads parsed vanilla, so it runs without the game). The new
  `te_fix_inconsistent_lawgroup_judiciary` moves Religious Courts to Statutory Courts with Rationalism, else to
  Executive Tribunals (dry run, 2026-10-17). Task 7 rewrites the file again once the stances exist.

- [ ] **Step 10: Commit**

```bash
git add common/modifier_type_definitions/judiciary_modifier_types.txt common/law_groups/extra_law_groups.txt common/laws/te_judiciary_laws.txt common/laws/te_judiciary_law_injections.txt common/laws/extra_laws.txt common/scripted_effects/extra_law_consistency_generated.txt localization/english/ test_judiciary.py
git commit -m "Judiciary: the law group, its six laws and their tooltip lines"
```

---

### Task 2: The ceiling, triggers, modifiers and the concept

**Files:**
- Create: `common/script_values/te_judiciary_values.txt`
- Create: `common/scripted_triggers/te_judiciary_triggers.txt`
- Create: `common/static_modifiers/te_judiciary_modifiers.txt`
- Modify: `common/game_concepts/extra_concepts.txt`
- Modify: `localization/english/te_miscellaneous_l_english.yml` (then `organize_loc.py` files them)
- Test: `test_judiciary.py` (class `ScoreDefinitionsTest`)

**Interfaces:**
- Produces: script values `te_jud_ceiling`, `te_jud_seed_value`, `te_jud_modifier_mult_value`, `te_jud_votes_mult_value`, `te_jud_authority_mult_value`, `te_jud_capture_mult_value`, `te_jud_overhaul_gap`, `te_jud_overhaul_mult_value`, `te_jud_display`; triggers `te_jud_paper_court`, `te_jud_elected_government`, `te_jud_is_islamic_state`; static modifiers `te_judicial_independence`, `te_jud_votes_legitimacy`, `te_jud_unelected_authority`, `te_jud_algorithmic_capture`, `te_jud_court_overhaul`, `te_jud_constitutional_challenge`, `te_jud_supremacy_challenge`; concept `concept_judicial_independence`.

- [ ] **Step 1: Write the failing tests** (add to `test_judiciary.py`)

```python
VALUES = os.path.join(REPO, "common", "script_values", "te_judiciary_values.txt")
TRIGGERS = os.path.join(REPO, "common", "scripted_triggers", "te_judiciary_triggers.txt")
MODIFIERS = os.path.join(REPO, "common", "static_modifiers", "te_judiciary_modifiers.txt")

# Spec § 3.2: the score's modifier at 100.
SCORE_MODIFIER = {
    "country_legitimacy_base_add": "10",
    "country_credit_standing_add": "-0.005",
    "state_capitalists_investment_pool_efficiency_mult": "0.1",
    "political_movement_radicalism_from_enactment_disapproval_mult": "-0.2",
}


class ScoreDefinitionsTest(unittest.TestCase):
    def setUp(self):
        self.mods = {k: _body(v) for k, v in _parse(MODIFIERS).items()}

    def _value(self, modifier, key):
        return _body(self.mods[modifier][key])

    def test_ceiling_reads_the_laws_lines(self):
        block = _block(_read(VALUES), "te_jud_ceiling")
        self.assertIn("value = modifier:country_judicial_independence_ceiling_add", block)
        self.assertIn("add = modifier:country_judicial_independence_ceiling_mult", block)
        self.assertNotIn("has_law", block, "the ceiling is the tooltip's number, not a law check")

    def test_paper_court_reads_its_line(self):
        block = _block(_read(TRIGGERS), "te_jud_paper_court")
        self.assertIn("modifier:country_court_challenges_ignored_bool = yes", block)

    def test_score_modifier_matches_spec(self):
        body = {k: _body(v) for k, v in self.mods["te_judicial_independence"].items() if k != "icon"}
        self.assertEqual(body, SCORE_MODIFIER)

    def test_unit_modifiers(self):
        # Each is applied with multiplier = the law's tooltip line.
        self.assertEqual(self._value("te_jud_votes_legitimacy", "country_legitimacy_govt_total_votes_add"), "1")
        self.assertEqual(self._value("te_jud_unelected_authority", "country_authority_add"), "1")
        self.assertEqual(self._value("te_jud_algorithmic_capture", "country_legislative_override_capacity_add"), "1")
        values = _read(VALUES)
        for name, line in (("te_jud_votes_mult_value", "country_legitimacy_from_votes_if_elected_add"),
                           ("te_jud_authority_mult_value", "country_authority_if_unelected_add"),
                           ("te_jud_capture_mult_value", "country_override_with_algorithmic_governance_add")):
            self.assertIn("value = modifier:" + line, _block(values, name))

    def test_challenge_tiers_match_the_laws(self):
        # The engine needs a named enactment modifier, so the laws' lines pick
        # one of two tiers (te_jud_enactment_started). Every line must be a tier.
        self.assertEqual(self._value("te_jud_constitutional_challenge", "country_law_enactment_success_add"), "-0.1")
        self.assertEqual(self._value("te_jud_supremacy_challenge", "country_law_enactment_success_add"), "-0.15")
        lines = set()
        for body in _parse(LAWS).values():
            modifier = _modifier(_body(body))
            for key in ("country_constitutional_law_enactment_success_add", "country_rights_law_enactment_success_add"):
                if key in modifier:
                    lines.add(modifier[key])
        self.assertLessEqual(lines, {"-0.1", "-0.15"})

    def test_overhaul(self):
        self.assertEqual(self._value("te_jud_court_overhaul", "country_risk_premium_add"), "0.02")
        self.assertEqual(self._value("te_jud_court_overhaul", "country_legitimacy_base_add"), "-10")

    def test_loc(self):
        keys = _loc_keys()
        for key in ("concept_judicial_independence", "te_judicial_independence", "te_jud_votes_legitimacy",
                    "te_jud_unelected_authority", "te_jud_algorithmic_capture", "te_jud_court_overhaul",
                    "te_jud_constitutional_challenge", "te_jud_supremacy_challenge"):
            self.assertIn(key, keys)
            self.assertIn(key + "_desc", keys)
```

- [ ] **Step 2: Run them and see them fail.** Expected: FAILED (files missing).

- [ ] **Step 3: `common/script_values/te_judiciary_values.txt`**

```
# ======================================================================
#  JUDICIARY — script values (country scope)
#  Spec: docs/superpowers/specs/2026-10-17-judiciary-design.md § 3
# ======================================================================

# The ceiling Judicial Independence moves toward (spec § 3.1): the court
# law's tooltip line, times the paper court's (-50%). Read from the modifier
# sums, so a later law or amendment moves it without a script edit. A sum
# can lag a law change by a tick: te_judiciary_events.1 waits a week, and the
# score is first seeded at a monthly pulse.
te_jud_ceiling = {
	value = modifier:country_judicial_independence_ceiling_add
	multiply = {
		value = 1
		add = modifier:country_judicial_independence_ceiling_mult
	}
	min = 0
	max = 100
}

# Where an unset score starts (spec § 5).
te_jud_seed_value = {
	value = te_jud_ceiling
	multiply = 0.5
}

# The scaled modifier's multiplier: score / 100. Stored in
# var:te_jud_modifier_mult by te_jud_refresh, never removed.
te_jud_modifier_mult_value = {
	value = var:te_judicial_independence
	divide = 100
}

# The conditional lines' multipliers (te_jud_refresh): each unit modifier
# times the law's tooltip line.
te_jud_votes_mult_value = {
	value = modifier:country_legitimacy_from_votes_if_elected_add
}

te_jud_authority_mult_value = {
	value = modifier:country_authority_if_unelected_add
}

te_jud_capture_mult_value = {
	value = modifier:country_override_with_algorithmic_governance_add
}

# How far the score stands above the ceiling (spec § 3.5). Read only where
# the score exists (te_judiciary_events.1's trigger).
te_jud_overhaul_gap = {
	value = var:te_judicial_independence
	subtract = te_jud_ceiling
}

te_jud_overhaul_mult_value = {
	value = te_jud_overhaul_gap
	divide = 100
}

# The score for loc, 0 where there is none yet (the concept, the modifier's
# description).
te_jud_display = {
	value = 0
	if = {
		limit = { has_variable = te_judicial_independence }
		value = var:te_judicial_independence
	}
}
```

- [ ] **Step 4: `common/scripted_triggers/te_judiciary_triggers.txt`**

```
# ======================================================================
#  JUDICIARY — scripted triggers (country scope)
#  Spec: docs/superpowers/specs/2026-10-17-judiciary-design.md
# ======================================================================

# A regime whose executive answers to nobody: its courts challenge nothing
# (spec § 3.4). The line sits on Autocracy, its variants, Single-Party State
# and Algorithmic Governance (te_judiciary_law_injections.txt).
te_jud_paper_court = {
	modifier:country_court_challenges_ignored_bool = yes
}

# An elected government (Statutory Courts' two lines, spec § 2.3): a voting
# law, or Anarchy, which the mod counts as electoral
# (te_tradition_of_free_elections.txt).
te_jud_elected_government = {
	OR = {
		has_law = law_type:law_landed_voting
		has_law = law_type:law_wealth_voting
		has_law = law_type:law_census_voting
		has_law = law_type:law_universal_suffrage
		has_law = law_type:law_anarchy
	}
}

# A Sunni, Shia or Ibadi state religion: the three religions with
# heritage_islamic (extra_history.txt tests the same way for Islamic
# inheritance).
te_jud_is_islamic_state = {
	OR = {
		country_has_state_religion = rel:sunni
		country_has_state_religion = rel:shiite
		country_has_state_religion = rel:ibadi
	}
}
```

- [ ] **Step 5: `common/static_modifiers/te_judiciary_modifiers.txt`**

```
# ======================================================================
#  JUDICIARY — static modifiers
#  Spec: docs/superpowers/specs/2026-10-17-judiciary-design.md
# ======================================================================

# Judicial Independence at 100 (spec § 3.2). te_jud_refresh, its only
# writer, applies it with multiplier score / 100.
te_judicial_independence = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_documents_positive.dds
	country_legitimacy_base_add = 10
	country_credit_standing_add = -0.005
	state_capitalists_investment_pool_efficiency_mult = 0.1
	political_movement_radicalism_from_enactment_disapproval_mult = -0.2
}

# Statutory Courts' two conditional lines (spec § 2.3), one unit each;
# te_jud_refresh applies whichever holds, with multiplier = the law's line.
te_jud_votes_legitimacy = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_documents_positive.dds
	country_legitimacy_govt_total_votes_add = 1
}

te_jud_unelected_authority = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_documents_positive.dds
	country_authority_add = 1
}

# Algorithmic Jurisprudence under Algorithmic Governance (spec § 2.6), one
# unit; te_jud_refresh applies it with multiplier = the law's line.
te_jud_algorithmic_capture = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_documents_negative.dds
	country_legislative_override_capacity_add = 1
}

# The overhaul shock at a gap of 100 (spec § 3.5); te_judiciary_events.1
# applies it for 5 years, decaying, with multiplier gap / 100.
te_jud_court_overhaul = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_documents_negative.dds
	country_risk_premium_add = 0.02
	country_legitimacy_base_add = -10
}

# Entrenchment (spec § 3.4): enactment modifiers, the two tiers the laws'
# tooltip lines name, added at on_law_enactment_started.
te_jud_constitutional_challenge = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_documents_negative.dds
	country_law_enactment_success_add = -0.1
}

te_jud_supremacy_challenge = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_documents_negative.dds
	country_law_enactment_success_add = -0.15
}
```

- [ ] **Step 6: The concept.** Add `concept_judicial_independence = {}` to `common/game_concepts/extra_concepts.txt` beside `concept_legislative_override_capacity`.

- [ ] **Step 7: Loc** in `localization/english/te_miscellaneous_l_english.yml` (`organize_loc.py` moves each key to its home):

```yaml
 concept_judicial_independence:0 "Judicial Independence"
 concept_judicial_independence_desc:0 "How far the courts are trusted to rule without fear of the government, from 0 to 100. Each Judiciary law sets a ceiling: Executive Tribunals 10, Religious Courts 40, Algorithmic Jurisprudence 60, Statutory Courts 70, Constitutional Review and Judicial Supremacy 100. Under Autocracy, Single-Party State or Algorithmic Governance the ceiling is halved, since the executive can ignore its courts. The score rises by 4 a year toward the ceiling and falls by 10 a year above it.\n\nIn proportion to the score, the courts add [concept_legitimacy], lower the [concept_banking_credit_standing] premium, make Capitalists invest more and calm movements that lose a law change. Forcing a law through spends the score, and a change that leaves it far above the new ceiling unsettles lenders and costs legitimacy for some years.\n\nNow #v [GetPlayer.MakeScope.ScriptValue('te_jud_display')|0]#!, heading for #v [GetPlayer.MakeScope.ScriptValue('te_jud_ceiling')|0]#!."
 te_judicial_independence:0 "Judicial Independence"
 te_judicial_independence_desc:0 "The courts' standing with the public and with lenders, in proportion to our [concept_judicial_independence] (now #v [GetPlayer.MakeScope.ScriptValue('te_jud_display')|0]#!)."
 te_jud_votes_legitimacy:0 "Supremacy of Statute"
 te_jud_votes_legitimacy_desc:0 "Our courts apply the law our elected legislature makes, and nothing overrides it."
 te_jud_unelected_authority:0 "Supremacy of Statute"
 te_jud_unelected_authority_desc:0 "Our courts apply the law the crown makes, and nothing overrides it."
 te_jud_algorithmic_capture:0 "Captured Court"
 te_jud_algorithmic_capture_desc:0 "The system that drafts our laws also judges them, so no court stands in the way of a law the government wants."
 te_jud_court_overhaul:0 "Court Overhaul"
 te_jud_court_overhaul_desc:0 "We cut the courts down to size. Lenders and the public noticed."
 te_jud_constitutional_challenge:0 "Constitutional Challenge"
 te_jud_constitutional_challenge_desc:0 "The law touches the constitution's core, and the courts will hear challenges to it."
 te_jud_supremacy_challenge:0 "Judicial Review"
 te_jud_supremacy_challenge_desc:0 "The courts have the last word on the constitution and the rights it protects, and this law falls within their reach."
```

- [ ] **Step 8: Run `python3 organize_loc.py`, format the new `.txt` files, run the tests.** Expected: OK. Then `loc_render_audit.py --strict` and `concept_reference_audit.py --strict` (with the dummy env) report nothing new.

- [ ] **Step 9: Commit** everything, including what `organize_loc.py` moved: `git commit -m "Judiciary: the ceiling, the score's modifiers and the concept"`.

---

### Task 3: The score: seeding, the yearly step, the refresh and starting laws

**Files:**
- Create: `common/scripted_effects/te_judiciary_effects.txt`
- Create: `common/on_actions/te_judiciary_on_actions.txt`
- Modify: `common/on_actions/te_old_save_repairs.txt`
- Modify: `common/history/extra_history.txt`
- Test: `test_judiciary.py` (class `ScoreScriptTest`)

**Interfaces:**
- Consumes: Task 2's values, triggers and modifiers.
- Produces: effects `te_jud_seed_score`, `te_jud_yearly_update`, `te_jud_refresh`, `te_jud_spend = { AMOUNT }`, `te_jud_assign_court_by_rule`; on-actions `te_jud_on_game_started`, `te_jud_monthly`, `te_jud_yearly`, `te_repair_judiciary_seed`; variables `te_judicial_independence`, `te_jud_modifier_mult`, `te_jud_votes_mult`, `te_jud_authority_mult`, `te_jud_capture_mult`, `te_jud_seeded`; globals `te_jud_world_seeded`, `te_jud_courts_assigned`.

- [ ] **Step 1: Write the failing tests**

```python
EFFECTS = os.path.join(REPO, "common", "scripted_effects", "te_judiciary_effects.txt")
ON_ACTIONS = os.path.join(REPO, "common", "on_actions", "te_judiciary_on_actions.txt")
REPAIRS = os.path.join(REPO, "common", "on_actions", "te_old_save_repairs.txt")
HISTORY = os.path.join(REPO, "common", "history", "extra_history.txt")
SCALED = ("te_judicial_independence", "te_jud_votes_legitimacy", "te_jud_unelected_authority",
          "te_jud_algorithmic_capture")
MULT_VARS = ("te_jud_modifier_mult", "te_jud_votes_mult", "te_jud_authority_mult", "te_jud_capture_mult",
             "te_jud_overhaul_mult")


def _script_files():
    for sub in ("common", "events"):
        for path in glob.glob(os.path.join(REPO, sub, "**", "*.txt"), recursive=True):
            yield path


class ScoreScriptTest(unittest.TestCase):
    def test_one_refresh_site(self):
        write = re.compile(r"(?:add_modifier = \{\s*name = |remove_modifier = )(?:%s)\b" % "|".join(SCALED))
        writers, callers = set(), []
        for path in _script_files():
            text = _read(path)
            if write.search(text):
                writers.add(os.path.relpath(path, REPO))
            callers += [os.path.relpath(path, REPO)] * len(re.findall(r"\bte_jud_refresh = yes", text))
        self.assertEqual(writers, {"common/scripted_effects/te_judiciary_effects.txt"})
        self.assertEqual(callers, ["common/on_actions/te_judiciary_on_actions.txt"])
        self.assertIn("te_jud_refresh = yes", _block(_read(ON_ACTIONS), "te_jud_monthly"))

    def test_multiplier_variables_are_never_removed(self):
        for path in _script_files():
            for name in MULT_VARS:
                self.assertNotIn("remove_variable = " + name, _read(path), path)

    def test_refresh_reads_the_conditions(self):
        block = _block(_read(EFFECTS), "te_jud_refresh")
        self.assertIn("te_jud_elected_government = yes", block)
        self.assertIn("NOT = { te_jud_elected_government = yes }", block)
        self.assertIn("has_law = law_type:law_algorithmic_governance", block)

    def test_yearly_step(self):
        block = _block(_read(EFFECTS), "te_jud_yearly_update")
        self.assertIn("add = 4", block)
        self.assertIn("subtract = 10", block)
        self.assertEqual(block.count("value = te_jud_ceiling"), 2, "both directions stop at the ceiling")

    def test_spend_floors_at_zero(self):
        block = _block(_read(EFFECTS), "te_jud_spend")
        self.assertIn("subtract = $AMOUNT$", block)
        self.assertIn("var:te_judicial_independence < 0", block)

    def test_seeding_waits_for_the_monthly_pulse(self):
        # Modifier sums may not be in place at on_game_started.
        start = _block(_read(ON_ACTIONS), "te_jud_on_game_started")
        self.assertNotIn("te_jud_seed_score", start)
        self.assertIn("set_global_variable = te_jud_world_seeded", start)
        monthly = _block(_read(ON_ACTIONS), "te_jud_monthly")
        self.assertIn("has_global_variable = te_jud_world_seeded", monthly)
        self.assertNotIn("te_jud_assign_court_by_rule", monthly, "a new country keeps its law")

    def test_old_save_seeding_is_a_marked_repair(self):
        text = _read(REPAIRS)
        self.assertIn("te_repair_judiciary_seed", _block(text, "on_monthly_pulse"))
        block = _block(text, "te_repair_judiciary_seed")
        self.assertIn("NOT = { has_global_variable = te_jud_world_seeded }", block)
        self.assertIn("te_jud_assign_court_by_rule = yes", block)
        # The score is released a month after the courts change, once their
        # modifiers are in place.
        self.assertIn("has_global_variable = te_jud_courts_assigned", block)
        self.assertRegex(text, r"# OLD-SAVE REPAIR \(#\d+\): remove after \d{4}-\d{2}-\d{2}[^\n]*\n(#[^\n]*\n)*te_repair_judiciary_seed")

    def test_history(self):
        text = _read(HISTORY)
        self.assertIn("te_jud_assign_court_by_rule = yes", _block(text.replace("\n\tevery_country = {", "\nevery_country = {", 1), "every_country"))
        # A country block: `c:TAG = {`, then text and one-level blocks only.
        inside = r"c:%s = \{(?:[^{}]|\{[^{}]*\})*?"
        self.assertRegex(text, inside % "USA" + r"activate_law = law_type:law_constitutional_review")
        for tag, score in (("GBR", 70), ("USA", 60), ("NET", 50), ("SWE", 50), ("BEL", 40), ("PRU", 35), ("FRA", 35)):
            self.assertRegex(text, inside % tag + r"set_variable = \{ name = te_judicial_independence value = %d \}" % score, tag)
```

- [ ] **Step 2: Run them and see them fail.**

- [ ] **Step 3: `common/scripted_effects/te_judiciary_effects.txt`**

```
# ======================================================================
#  JUDICIARY — scripted effects (country scope)
#  Spec: docs/superpowers/specs/2026-10-17-judiciary-design.md
#  The score lives in var:te_judicial_independence (0-100) and nowhere else,
#  so a revolution's winner inherits it and te_jud_refresh rebuilds the
#  modifiers.
# ======================================================================

# An unset score starts at half the ceiling (spec § 5); history sets some
# first. Called from the monthly pulse only, where the laws' modifier sums
# are in place.
te_jud_seed_score = {
	if = {
		limit = { NOT = { has_variable = te_judicial_independence } }
		set_variable = {
			name = te_judicial_independence
			value = te_jud_seed_value
		}
	}
	set_variable = te_jud_seeded
}

# The yearly step toward the ceiling (spec § 3.1): +4 below it, -10 above it,
# stopping at it either way.
te_jud_yearly_update = {
	if = {
		limit = { has_variable = te_judicial_independence }
		if = {
			limit = { var:te_judicial_independence < te_jud_ceiling }
			change_variable = {
				name = te_judicial_independence
				add = 4
			}
			if = {
				limit = { var:te_judicial_independence > te_jud_ceiling }
				set_variable = {
					name = te_judicial_independence
					value = te_jud_ceiling
				}
			}
		}
		else_if = {
			limit = { var:te_judicial_independence > te_jud_ceiling }
			change_variable = {
				name = te_judicial_independence
				subtract = 10
			}
			if = {
				limit = { var:te_judicial_independence < te_jud_ceiling }
				set_variable = {
					name = te_judicial_independence
					value = te_jud_ceiling
				}
			}
		}
	}
}

# Spends AMOUNT of the score, floored at 0 (spec § 3.3). Callers wrap it in a
# custom_tooltip naming the cost; the modifier follows at the next monthly
# refresh.
te_jud_spend = {
	if = {
		limit = { has_variable = te_judicial_independence }
		change_variable = {
			name = te_judicial_independence
			subtract = $AMOUNT$
		}
		if = {
			limit = { var:te_judicial_independence < 0 }
			set_variable = {
				name = te_judicial_independence
				value = 0
			}
		}
	}
}

# ROOT the country (te_jud_monthly, on_monthly_pulse_country). The ONLY
# writer of the four scaled modifiers. Their multiplier variables are kept,
# never removed: the engine re-reads them.
te_jud_refresh = {
	# The score (spec § 3.2).
	if = {
		limit = { has_variable = te_judicial_independence }
		set_variable = {
			name = te_jud_modifier_mult
			value = te_jud_modifier_mult_value
		}
		if = {
			limit = { has_modifier = te_judicial_independence }
			remove_modifier = te_judicial_independence
		}
		if = {
			limit = { var:te_jud_modifier_mult > 0 }
			add_modifier = {
				name = te_judicial_independence
				multiplier = var:te_jud_modifier_mult
			}
		}
	}
	# Statutory Courts' two lines (spec § 2.3): legitimacy from votes under an
	# elected government, authority without one. Each multiplier is the law's
	# tooltip line, so 0 under any other court.
	set_variable = {
		name = te_jud_votes_mult
		value = te_jud_votes_mult_value
	}
	set_variable = {
		name = te_jud_authority_mult
		value = te_jud_authority_mult_value
	}
	if = {
		limit = { has_modifier = te_jud_votes_legitimacy }
		remove_modifier = te_jud_votes_legitimacy
	}
	if = {
		limit = { has_modifier = te_jud_unelected_authority }
		remove_modifier = te_jud_unelected_authority
	}
	if = {
		limit = {
			te_jud_elected_government = yes
			var:te_jud_votes_mult > 0
		}
		add_modifier = {
			name = te_jud_votes_legitimacy
			multiplier = var:te_jud_votes_mult
		}
	}
	else_if = {
		limit = {
			NOT = { te_jud_elected_government = yes }
			var:te_jud_authority_mult > 0
		}
		add_modifier = {
			name = te_jud_unelected_authority
			multiplier = var:te_jud_authority_mult
		}
	}
	# Algorithmic Jurisprudence's capture (spec § 2.6).
	set_variable = {
		name = te_jud_capture_mult
		value = te_jud_capture_mult_value
	}
	if = {
		limit = { has_modifier = te_jud_algorithmic_capture }
		remove_modifier = te_jud_algorithmic_capture
	}
	if = {
		limit = {
			has_law = law_type:law_algorithmic_governance
			var:te_jud_capture_mult > 0
		}
		add_modifier = {
			name = te_jud_algorithmic_capture
			multiplier = var:te_jud_capture_mult
		}
	}
}

# The starting court by rule (spec § 5): history, and an old save's one-time
# seeding (te_repair_judiciary_seed). activate_law ignores unlock
# technologies, as history does.
te_jud_assign_court_by_rule = {
	if = {
		limit = {
			OR = {
				has_law = law_type:law_theocracy
				AND = {
					te_jud_is_islamic_state = yes
					OR = {
						has_law_or_variant = law_type:law_state_religion
						has_law = law_type:law_freedom_of_conscience
					}
				}
			}
		}
		activate_law = law_type:law_religious_courts
	}
	else_if = {
		limit = {
			OR = {
				has_law = law_type:law_landed_voting
				has_law = law_type:law_wealth_voting
				has_law = law_type:law_census_voting
				has_law = law_type:law_universal_suffrage
			}
		}
		activate_law = law_type:law_statutory_courts
	}
	else = {
		activate_law = law_type:law_executive_tribunals
	}
}
```

- [ ] **Step 4: `common/on_actions/te_judiciary_on_actions.txt`** (Tasks 4 and 5 add to it)

```
# ======================================================================
#  JUDICIARY — on actions
#  Spec: docs/superpowers/specs/2026-10-17-judiciary-design.md
#  Effects: common/scripted_effects/te_judiciary_effects.txt.
# ======================================================================

# A new game: history has set every court. The scores are seeded at the
# first monthly pulse (te_jud_monthly), where the laws' modifier sums are
# certainly in place; this only marks the world as seeded, so the old-save
# repair (te_old_save_repairs.txt) never runs.
on_game_started = {
	on_actions = {
		te_jud_on_game_started
	}
}

te_jud_on_game_started = {
	effect = {
		set_global_variable = te_jud_world_seeded
	}
}

# Root = Country. A country with no score yet (every 1836 country on the
# first pulse, a new country mid-game) gets one from the law it holds; its
# law isn't changed. Then the refresh, the scaled modifiers' only writer.
on_monthly_pulse_country = {
	on_actions = {
		te_jud_monthly
	}
}

te_jud_monthly = {
	effect = {
		if = {
			limit = {
				has_global_variable = te_jud_world_seeded
				NOT = { has_variable = te_jud_seeded }
			}
			te_jud_seed_score = yes
		}
		te_jud_refresh = yes
	}
}

on_yearly_pulse_country = {
	on_actions = {
		te_jud_yearly
	}
}

te_jud_yearly = {
	effect = {
		te_jud_yearly_update = yes
	}
}
```

- [ ] **Step 5: The old-save repair** in `common/on_actions/te_old_save_repairs.txt`: add `te_repair_judiciary_seed` to its `on_monthly_pulse` list and this block. Use the phase 1 PR's number and a date six weeks after its merge, as the file's other repairs do, and schedule the removal reminder the file's header describes.

```
# OLD-SAVE REPAIR (#<PR>): remove after <YYYY-MM-DD> or at vanilla 1.15, whichever comes first.
#
# The Judiciary group (docs/superpowers/specs/2026-10-17-judiciary-design.md
# § 6) is new, so a save from before it gives every country Executive
# Tribunals, the first law in te_judiciary_laws.txt, and no score. First
# month: the starting court by rule. Second month: te_jud_world_seeded, which
# lets te_jud_monthly seed each score from the new law's ceiling, its
# modifier sums by then in place. A new game sets te_jud_world_seeded at
# on_game_started and never runs this. The laws it activates never shock:
# te_judiciary_events.1 needs te_jud_seeded.
te_repair_judiciary_seed = {
	effect = {
		if = {
			limit = { NOT = { has_global_variable = te_jud_world_seeded } }
			if = {
				limit = { has_global_variable = te_jud_courts_assigned }
				set_global_variable = te_jud_world_seeded
			}
			else = {
				every_country = {
					te_jud_assign_court_by_rule = yes
				}
				set_global_variable = te_jud_courts_assigned
			}
		}
	}
}
```

- [ ] **Step 6: History** in `common/history/extra_history.txt`. At the end of the `every_country` block, after the State Power `if`/`else`:

```
		# Judiciary (spec § 5): the starting court by rule. Per-country
		# overrides and starting scores follow in the country blocks.
		te_jud_assign_court_by_rule = yes
```

Then add two lines to each of these existing country blocks (all seven already exist in the file), with the comment
on the line above. The `set_variable` must stay on one line (`test_history` reads it that way):

| Block | Court | Score | Comment |
|---|---|---|---|
| `c:USA` | `law_constitutional_review` | 60 | Marbury v. Madison, 1803 |
| `c:GBR` | `law_statutory_courts` | 70 | Judges' tenure from the Act of Settlement, 1701 |
| `c:PRU` | `law_statutory_courts` | 35 | The General Code of 1794 |
| `c:FRA` (the first block) | `law_statutory_courts` | 35 | The Code civil |
| `c:NET` | `law_statutory_courts` | 50 | |
| `c:SWE` | `law_statutory_courts` | 50 | |
| `c:BEL` | `law_statutory_courts` | 40 | |

For example, in `c:USA`:

```
		# Judiciary: Marbury v. Madison, 1803 (spec § 5)
		activate_law = law_type:law_constitutional_review
		set_variable = { name = te_judicial_independence value = 60 }
```

- [ ] **Step 7: Format, run the tests.** Expected: OK. Also `.venv/bin/python script_argument_audit.py --strict` (the `te_jud_spend` signature), `.venv/bin/python change_variable_clamp_audit.py --strict` and `.venv/bin/python modifier_multiplier_var_audit.py --strict`.

- [ ] **Step 8: Commit**: `git commit -m "Judiciary: Judicial Independence, its refresh and the starting courts"`.

---

### Task 4: Entrenchment and its self-check

**Files:**
- Modify: `common/scripted_triggers/te_judiciary_triggers.txt`
- Modify: `common/scripted_effects/te_judiciary_effects.txt`
- Modify: `common/on_actions/te_judiciary_on_actions.txt`
- Test: `test_judiciary.py` (class `EntrenchmentTest`)

**Interfaces:**
- Produces: triggers `te_jud_enacting_core_law`, `te_jud_enacting_rights_law`; effect `te_jud_selfcheck_enacting_scope`; on-action `te_jud_enactment_started`; global `te_jud_selfcheck_enacting_done`.

- [ ] **Step 1: Write the failing tests**

```python
VANILLA_LAWS = os.path.join(REPO, "vanilla_parsed", "common", "laws.json")

# Spec § 3.4.
CORE_GROUPS = {
    "lawgroup_distribution_of_power", "lawgroup_governance_principles", "lawgroup_church_and_state",
    "lawgroup_citizenship", "lawgroup_free_speech", "lawgroup_internal_security",
    "lawgroup_state_power", "lawgroup_judiciary",
}
RIGHTS_GROUPS = {
    "lawgroup_rights_of_women", "lawgroup_slavery", "lawgroup_minority_rights",
    "lawgroup_LGBTQ_rights", "lawgroup_privacy_rights",
}


def _law_groups():
    """{law: group} over vanilla (the snapshot) and every mod law file."""
    with open(VANILLA_LAWS, encoding="utf-8") as fh:
        groups = {k: v[1]["group"][1] for k, v in json.load(fh).items() if "group" in v[1]}
    for path in glob.glob(os.path.join(REPO, "common", "laws", "*.txt")):
        for key, node in _parse(path).items():
            body = _body(node)
            if isinstance(body, dict) and "group" in body:
                groups[key] = _body(body["group"])
    return groups


class EntrenchmentTest(unittest.TestCase):
    def _named_groups(self, trigger):
        laws = re.findall(r"is_same_law_group_as = law_type:(\w+)", _block(_read(TRIGGERS), trigger))
        groups = _law_groups()
        return [groups[law] for law in laws]

    def test_protected_groups_match_spec(self):
        core = self._named_groups("te_jud_enacting_core_law")
        rights = self._named_groups("te_jud_enacting_rights_law")
        self.assertEqual(len(core), len(set(core)), "one law per group")
        self.assertEqual(set(core), CORE_GROUPS)
        self.assertEqual(set(rights), RIGHTS_GROUPS)

    def test_the_laws_lines_pick_the_tier(self):
        block = _block(_read(ON_ACTIONS), "te_jud_enactment_started")
        self.assertEqual(block.count("NOT = { te_jud_paper_court = yes }"), 2)
        self.assertIn("modifier:country_constitutional_law_enactment_success_add <= -0.15", block)
        self.assertIn("modifier:country_rights_law_enactment_success_add <= -0.15", block)
        self.assertIn("modifier:country_constitutional_law_enactment_success_add < 0", block)
        self.assertIn("add_enactment_modifier = { name = te_jud_supremacy_challenge }", block)
        self.assertIn("add_enactment_modifier = { name = te_jud_constitutional_challenge }", block)
        self.assertNotIn("has_law", block, "the tooltip's numbers decide, not a law check")

    def test_self_check_is_once_a_game_and_excludes_no_enactment(self):
        block = _block(_read(EFFECTS), "te_jud_selfcheck_enacting_scope")
        self.assertIn("enacting_any_law = yes", block)
        self.assertIn("set_global_variable = te_jud_selfcheck_enacting_done", block)
        self.assertIn("TE_SELF_CHECK OK judiciary_enacting_law_scope", block)
        self.assertIn("TE_SELF_CHECK BROKEN judiciary_enacting_law_scope", block)
```

- [ ] **Step 2: Run them and see them fail.**

- [ ] **Step 3: Triggers** (append to `te_judiciary_triggers.txt`). One law per group; `is_same_law_group_as` compares groups, so any law of the group works.

```
# The law under enactment belongs to the constitution's core (spec § 3.4):
# Distribution of Power, Governance Principles, Church and State, Citizenship,
# Free Speech, Internal Security, State Power, Judiciary. currently_enacting_law
# is a country -> law link and law_type a law -> law type link. Not `type`:
# the load-time scope check takes it as building -> building type and logs
# "Inconsistent trigger scopes (building_type vs. law_type)" at every line
# below (2026-10-17). Whether currently_enacting_law resolves at
# on_law_enactment_started is unread: te_jud_selfcheck_enacting_scope reports
# it once a game.
te_jud_enacting_core_law = {
	currently_enacting_law ?= {
		law_type = {
			OR = {
				is_same_law_group_as = law_type:law_autocracy
				is_same_law_group_as = law_type:law_monarchy
				is_same_law_group_as = law_type:law_state_religion
				is_same_law_group_as = law_type:law_subjecthood
				is_same_law_group_as = law_type:law_censorship
				is_same_law_group_as = law_type:law_secret_police
				is_same_law_group_as = law_type:law_unitary_state
				is_same_law_group_as = law_type:law_statutory_courts
			}
		}
	}
}

# The rights groups (Judicial Supremacy's wider reach): Rights of Women,
# Slavery, Minority Rights, LGBTQ+ Rights, Privacy Rights.
te_jud_enacting_rights_law = {
	currently_enacting_law ?= {
		law_type = {
			OR = {
				is_same_law_group_as = law_type:law_no_womens_rights
				is_same_law_group_as = law_type:law_slavery_banned
				is_same_law_group_as = law_type:law_minority_rights_protection
				is_same_law_group_as = law_type:law_legal_limbo
				is_same_law_group_as = law_type:law_moderate_data_privacy
			}
		}
	}
}
```

- [ ] **Step 4: The self-check** (append to `te_judiciary_effects.txt`)

```
# Once a game (spec § 9; CLAUDE.md "In-game checks"): does
# currently_enacting_law resolve at on_law_enactment_started? Only a country
# whose court challenges, and only while an enactment runs, so a missing link
# can't read as OK. No line at all after such an enactment means the hook's
# ROOT isn't the country.
te_jud_selfcheck_enacting_scope = {
	if = {
		limit = {
			NOT = { has_global_variable = te_jud_selfcheck_enacting_done }
			enacting_any_law = yes
			modifier:country_constitutional_law_enactment_success_add < 0
			NOT = { te_jud_paper_court = yes }
		}
		set_global_variable = te_jud_selfcheck_enacting_done
		if = {
			limit = { exists = currently_enacting_law }
			debug_log = "TE_SELF_CHECK OK judiciary_enacting_law_scope country=[THIS.GetCountry.GetNameNoFormatting]"
		}
		else = {
			debug_log = "TE_SELF_CHECK BROKEN judiciary_enacting_law_scope country=[THIS.GetCountry.GetNameNoFormatting] currently_enacting_law missing at on_law_enactment_started"
		}
	}
}
```

- [ ] **Step 5: The on-action** (append to `te_judiciary_on_actions.txt`). The Forceful Legislation event fires from the same hook and calls `add_enactment_modifier` the same way.

```
# Root = Country. Entrenchment (spec § 3.4): the laws' tooltip lines say how
# much a court challenges each kind of law; the engine needs a named
# enactment modifier, so the line picks one of two tiers (test_judiciary.py
# holds every line to a tier). A paper court challenges nothing.
on_law_enactment_started = {
	on_actions = {
		te_jud_enactment_started
	}
}

te_jud_enactment_started = {
	effect = {
		if = {
			limit = {
				NOT = { te_jud_paper_court = yes }
				OR = {
					AND = {
						te_jud_enacting_core_law = yes
						modifier:country_constitutional_law_enactment_success_add <= -0.15
					}
					AND = {
						te_jud_enacting_rights_law = yes
						modifier:country_rights_law_enactment_success_add <= -0.15
					}
				}
			}
			add_enactment_modifier = { name = te_jud_supremacy_challenge }
		}
		else_if = {
			limit = {
				NOT = { te_jud_paper_court = yes }
				OR = {
					AND = {
						te_jud_enacting_core_law = yes
						modifier:country_constitutional_law_enactment_success_add < 0
					}
					AND = {
						te_jud_enacting_rights_law = yes
						modifier:country_rights_law_enactment_success_add < 0
					}
				}
			}
			add_enactment_modifier = { name = te_jud_constitutional_challenge }
		}
		te_jud_selfcheck_enacting_scope = yes
	}
}
```

- [ ] **Step 6: Format, run the tests**, plus `.venv/bin/python effect_trigger_validity_audit.py` (it knows `currently_enacting_law`, `is_same_law_group_as`, `add_enactment_modifier`). Expected: OK, no new flags.

- [ ] **Step 7: Commit**: `git commit -m "Judiciary: entrenchment under reviewing courts, with its self-check"`.

---

### Task 5: The overhaul shock

**Files:**
- Create: `events/te_judiciary_events.txt`
- Modify: `common/on_actions/te_judiciary_on_actions.txt`
- Test: `test_judiciary.py` (class `ShockTest`)

**Interfaces:**
- Produces: event `te_judiciary_events.1`; on-action `te_jud_law_activated`; variable `te_jud_overhaul_mult`.

- [ ] **Step 1: Write the failing tests**

```python
EVENTS = os.path.join(REPO, "events", "te_judiciary_events.txt")
CEILING_LAWS = set(COURT_LAWS) | set(PAPER_COURT_LAWS)


class ShockTest(unittest.TestCase):
    def test_every_ceiling_law_fires_the_check(self):
        block = _block(_read(ON_ACTIONS), "te_jud_law_activated")
        self.assertEqual(set(re.findall(r"type = law_type:(\w+)", block)), CEILING_LAWS)
        self.assertIn("owner = {", block)
        # The new law's modifier sums may lag the change.
        self.assertIn("trigger_event = { id = te_judiciary_events.1 days = 7 }", block)
        self.assertNotIn("multiplier", block, "ROOT is the law here")
        self.assertNotIn("var:", block, "has_variable fails on law scopes")

    def test_shock_runs_in_a_country_event(self):
        event = _block(_read(EVENTS), "te_judiciary_events.1")
        self.assertIn("type = country_event", event)
        self.assertIn("hidden = yes", event)
        self.assertIn("multiplier = var:te_jud_overhaul_mult", event)
        self.assertIn("is_decaying = yes", event)
        self.assertIn("years = 5", event)

    def test_shock_needs_seeding(self):
        event = _block(_read(EVENTS), "te_judiciary_events.1")
        trigger = event[event.index("\ttrigger = {"):event.index("\timmediate = {")]
        self.assertIn("has_variable = te_jud_seeded", trigger)
        self.assertIn("te_jud_overhaul_gap >= 20", trigger)
```

- [ ] **Step 2: Run them and see them fail.**

- [ ] **Step 3: `events/te_judiciary_events.txt`** (UTF-8 with BOM)

```
namespace = te_judiciary_events

# The court overhaul (spec § 3.5). Fired a week after a ceiling law changes
# (te_jud_law_activated), on the country, so ROOT is the country and the
# multiplier resolves here, and the new law's modifier sums are in place. The
# gap is stored once: a script value would drift as the score decays. A
# second shock replaces the first.
te_judiciary_events.1 = {
	type = country_event
	hidden = yes

	trigger = {
		has_variable = te_jud_seeded
		has_variable = te_judicial_independence
		te_jud_overhaul_gap >= 20
	}

	immediate = {
		set_variable = {
			name = te_jud_overhaul_mult
			value = te_jud_overhaul_mult_value
		}
		add_modifier = {
			name = te_jud_court_overhaul
			years = 5
			is_decaying = yes
			multiplier = var:te_jud_overhaul_mult
		}
		if = {
			limit = { te_jud_overhaul_gap >= 40 }
			add_radicals = {
				value = small_radicals
				strata = middle
			}
		}
	}
}
```

- [ ] **Step 4: The on-action** (append to `te_judiciary_on_actions.txt`)

```
# ROOT = the law (scripting_best_practices.md § "Checking the Type of the Law
# in on_law_activated"). Script values that read country variables fail on a
# law scope, so this only matches the type of every law that moves the
# ceiling and leaves the arithmetic to te_judiciary_events.1 on the owner,
# a week later, once the new law's modifier sums are in place.
on_law_activated = {
	on_actions = {
		te_jud_law_activated
	}
}

te_jud_law_activated = {
	effect = {
		if = {
			limit = {
				OR = {
					type = law_type:law_executive_tribunals
					type = law_type:law_religious_courts
					type = law_type:law_statutory_courts
					type = law_type:law_constitutional_review
					type = law_type:law_judicial_supremacy
					type = law_type:law_algorithmic_jurisprudence
					type = law_type:law_autocracy
					type = law_type:law_bakufu
					type = law_type:law_neo_absolutism
					type = law_type:law_single_party_state
					type = law_type:law_algorithmic_governance
				}
			}
			owner = {
				trigger_event = { id = te_judiciary_events.1 days = 7 }
			}
		}
	}
}
```

- [ ] **Step 5: Format, run the tests**, plus `orphaned_event_audit.py --strict` and `event_context_audit.py --strict`. Expected: OK.

- [ ] **Step 6: Commit**: `git commit -m "Judiciary: the overhaul shock"`.

---

### Task 6: Spending the score

**Files:**
- Modify: `events/minor_events.txt` (`minor_events_timelineextended.2`, options b, c, e)
- Modify: `common/scripted_effects/te_tax_offer_effects.txt` (`te_tax_force_into`)
- Modify: `localization/english/te_miscellaneous_l_english.yml`, `localization/english/te_tax_l_english.yml`
- Test: `test_judiciary.py` (class `SpendTest`)

- [ ] **Step 1: Write the failing tests**

```python
MINOR_EVENTS = os.path.join(REPO, "events", "minor_events.txt")
TAX_OFFER = os.path.join(REPO, "common", "scripted_effects", "te_tax_offer_effects.txt")


class SpendTest(unittest.TestCase):
    def test_forceful_legislation_spends_and_says_so(self):
        event = _block(_read(MINOR_EVENTS), "minor_events_timelineextended.2")
        options = re.split(r"\n\toption = \{", event)[1:]
        by_name = {re.search(r"name = (\S+)", o).group(1): o for o in options}
        for name, amount, key in (("minor_events_timelineextended.2.b", 5, "te_jud_spend_small_tt"),
                                  ("minor_events_timelineextended.2.c", 10, "te_jud_spend_medium_tt"),
                                  ("minor_events_timelineextended.2.e", 20, "te_jud_spend_large_tt")):
            self.assertRegex(by_name[name],
                             r"custom_tooltip = \{\s*text = %s\s*te_jud_spend = \{ AMOUNT = %d \}" % (key, amount), name)
        self.assertNotIn("te_jud_spend", by_name["minor_events_timelineextended.2.a"])

    def test_tax_force_through_spends(self):
        block = _block(_read(TAX_OFFER), "te_tax_force_into")
        self.assertIn("te_jud_spend = { AMOUNT = 10 }", block)

    def test_loc(self):
        keys = _loc_keys()
        for key in ("te_jud_spend_small_tt", "te_jud_spend_medium_tt", "te_jud_spend_large_tt"):
            self.assertIn(key, keys)
```

- [ ] **Step 2: Run them and see them fail.**

- [ ] **Step 3: The event.** In each of options b, c and e of `minor_events_timelineextended.2`, after the `add_enactment_modifier`, add (5 / `small`, 10 / `medium`, 20 / `large`):

```
		custom_tooltip = {
			text = te_jud_spend_medium_tt
			te_jud_spend = { AMOUNT = 10 }
		}
```

- [ ] **Step 4: The tax code.** In `te_tax_force_into`, after the two `add_modifier` blocks:

```
		# Judicial Independence, as the Forceful Legislation option whose
		# modifiers this applies (judiciary spec § 3.3).
		te_jud_spend = { AMOUNT = 10 }
```

- [ ] **Step 5: Loc.** In `te_miscellaneous_l_english.yml`:

```yaml
 te_jud_spend_small_tt:0 "[concept_judicial_independence] #N -5#!"
 te_jud_spend_medium_tt:0 "[concept_judicial_independence] #N -10#!"
 te_jud_spend_large_tt:0 "[concept_judicial_independence] #N -20#!"
```

In `te_tax_l_english.yml`, end `te_tax_tt_cmd_force_through` with " It also lowers [concept_judicial_independence] by 10." and `te_tax_how_passage_force` with ", and lowers [concept_judicial_independence] by 10" before its final full stop.

- [ ] **Step 6: Run `organize_loc.py`, the tests, `silent_variable_audit.py --strict` and `script_argument_audit.py --strict`.** Expected: OK. Add `docs/systems/tax_code_schema.md` § 7.4's mention of the cost in the same commit.

- [ ] **Step 7: Commit**: `git commit -m "Judiciary: forcing a law through spends Judicial Independence"`.

---

### Task 7: Ideology stances and the consistency walk

**Files:**
- Modify: `ideology_modifications.py`
- Modify: `common/ideologies/extra_ideologies.txt`
- Regenerate: `common/ideologies/modified.txt`, `common/scripted_effects/extra_law_consistency_generated.txt`
- Test: `test_judiciary.py` (class `StancesTest`)

**Interfaces:**
- Produces: `ideology_modifications.JUDICIARY_LISTS` (name → six (law, stance) pairs), `ideology_modifications.JUDICIARY_STANCES` (vanilla ideology → list name), and the generated `te_fix_inconsistent_lawgroup_judiciary`.

- [ ] **Step 1: Write the failing tests**

```python
IDEOLOGY_FILES = sorted(glob.glob(os.path.join(REPO, "common", "ideologies", "*.txt")))
CONSISTENCY = os.path.join(REPO, "common", "scripted_effects", "extra_law_consistency_generated.txt")
VANILLA_IDEOLOGIES = os.path.join(REPO, "vanilla_parsed", "common", "ideologies.json")

# Spec § 7, mod ideologies written by hand in extra_ideologies.txt.
MOD_STANCES = {
    "ideology_islamic_inheritance": "religious",
    "ideology_corporate": "market",
    "ideology_multicultural": "rights",
    "ideology_optimist_transhumanist": "technocratic",
    "ideology_custom_religion_theocratic_governance": "religious",
    "ideology_custom_religion_theocratic_society": "religious",
    "ideology_custom_religion_technocratic_governance": "technocratic",
    "ideology_custom_religion_republican_governance": "liberal",
    "ideology_custom_religion_aristocratic_governance": "traditional",
    "ideology_custom_religion_corporate_governance": "market",
    "ideology_custom_religion_imperial_cult_governance": "absolutist",
}


class StancesTest(unittest.TestCase):
    def test_lists_name_all_six_laws(self):
        import ideology_modifications as im
        for name, stances in im.JUDICIARY_LISTS.items():
            self.assertEqual(tuple(law for law, _ in stances), COURT_LAWS, name)

    def test_vanilla_keys_exist(self):
        import ideology_modifications as im
        with open(VANILLA_IDEOLOGIES, encoding="utf-8") as fh:
            vanilla = set(json.load(fh))
        self.assertLessEqual(set(im.JUDICIARY_STANCES), vanilla)
        for ideology, name in im.JUDICIARY_STANCES.items():
            self.assertEqual(im.modifications[ideology]["lawgroup_judiciary"], im.JUDICIARY_LISTS[name], ideology)

    def test_every_block_in_script_names_all_six(self):
        seen = set()
        for path in IDEOLOGY_FILES:
            for key, node in _parse(path).items():
                body = _body(node)
                if isinstance(body, dict) and "lawgroup_judiciary" in body:
                    block = _body(body["lawgroup_judiciary"])
                    self.assertEqual(set(block), set(COURT_LAWS), key)
                    seen.add(key.split(":")[-1])
        import ideology_modifications as im
        self.assertLessEqual(set(im.JUDICIARY_STANCES) | set(MOD_STANCES), seen)

    def test_mod_ideologies_use_their_lists(self):
        import ideology_modifications as im
        data = _parse(os.path.join(REPO, "common", "ideologies", "extra_ideologies.txt"))
        for ideology, name in MOD_STANCES.items():
            block = {k: _body(v) for k, v in _body(_body(data[ideology])["lawgroup_judiciary"]).items()}
            self.assertEqual(block, dict(im.JUDICIARY_LISTS[name]), ideology)

    def test_religious_courts_fall_to_statutory(self):
        block = _block(_read(CONSISTENCY), "te_fix_inconsistent_lawgroup_judiciary")
        religious = block[block.index("law_type:law_religious_courts"):]
        self.assertLess(religious.index("law_type:law_statutory_courts"),
                        religious.index("law_type:law_executive_tribunals"))
```

(`test_religious_courts_fall_to_statutory` reads the generator's shape as of the 2026-10-17 dry run: the held law's `has_law` line, then its candidates in order, Statutory Courts behind a `rationalism` check and Executive Tribunals as the `always = yes` fallback.)

- [ ] **Step 2: Run them and see them fail.**

- [ ] **Step 3: The lists** in `ideology_modifications.py`, before `modifications = {`:

```python
# --- lawgroup_judiciary (docs/superpowers/specs/2026-10-17-judiciary-design.md § 7) ---
# Every list names all six laws, in file order (the ideology_lawgroup audit;
# test_judiciary.py). Applied to the vanilla ideologies in JUDICIARY_STANCES by
# the loop after `modifications`; the mod's own ideologies carry the same
# lists by hand in extra_ideologies.txt.
_JUDICIARY_LAWS = (
    "law_executive_tribunals",
    "law_religious_courts",
    "law_statutory_courts",
    "law_constitutional_review",
    "law_judicial_supremacy",
    "law_algorithmic_jurisprudence",
)
_STANCE_CODES = {
    "++": "strongly_approve",
    "+": "approve",
    "0": "neutral",
    "-": "disapprove",
    "--": "strongly_disapprove",
}


def judiciary_constructor(*codes):
    """Six stance codes, in _JUDICIARY_LAWS order, as (law, stance) pairs."""
    assert len(codes) == len(_JUDICIARY_LAWS)
    return [(law, _STANCE_CODES[code]) for law, code in zip(_JUDICIARY_LAWS, codes)]


JUDICIARY_LISTS = {
    #                                    Exec  Rel   Stat  Const Supr  Algo
    "absolutist": judiciary_constructor("++", "0", "-", "--", "--", "0"),
    "traditional": judiciary_constructor("+", "0", "+", "-", "--", "-"),
    "religious": judiciary_constructor("0", "++", "-", "-", "--", "--"),
    "liberal": judiciary_constructor("--", "-", "+", "++", "0", "-"),
    "anticlerical": judiciary_constructor("--", "--", "+", "++", "0", "-"),
    "market": judiciary_constructor("-", "-", "+", "++", "-", "+"),
    "rights": judiciary_constructor("--", "--", "0", "+", "++", "-"),
    # Taff Vale, Lochner and the labour injunctions: wary of strong courts.
    "labour": judiciary_constructor("-", "-", "++", "0", "-", "0"),
    # The people's representatives have the last word (Jackson and
    # Worcester v. Georgia, 1832).
    "populist": judiciary_constructor("0", "0", "++", "-", "--", "-"),
    "vanguard": judiciary_constructor("++", "--", "-", "--", "--", "+"),
    "technocratic": judiciary_constructor("-", "--", "+", "+", "-", "++"),
}

JUDICIARY_STANCES = {
    **{k: "absolutist" for k in (
        "ideology_loyalist", "ideology_authoritarian", "ideology_military_absolutist",
        "ideology_reactionary", "ideology_reactionary_movement", "ideology_royalist_movement",
        "ideology_absolutist_movement",
    )},
    **{k: "traditional" for k in (
        "ideology_paternalistic", "ideology_hierarchic", "ideology_patriarchal", "ideology_patriotic",
        "ideology_jingoist", "ideology_royalist", "ideology_legitimist", "ideology_bonapartist",
    )},
    **{k: "religious" for k in (
        "ideology_pious", "ideology_moralist", "ideology_theocrat", "ideology_papal_paternalistic",
        "ideology_buddhist_moralist", "ideology_hindu_moralist", "ideology_hindu_moralist_british_india",
        "ideology_sikh_moralist", "ideology_shinto_moralist", "ideology_papal_moralist",
        "ideology_montenegrin_moralist", "ideology_orthodox_patriarch",
        "ideology_oriental_orthodox_patriarch", "ideology_russian_patriarch",
    )},
    **{k: "liberal" for k in (
        "ideology_liberal", "ideology_liberal_leader", "ideology_republican", "ideology_republican_leader",
        "ideology_individualist", "ideology_constitutionalist", "ideology_liberal_movement",
    )},
    "ideology_anti_clerical": "anticlerical",
    **{k: "market" for k in ("ideology_laissez_faire", "ideology_plutocratic", "ideology_market_liberal")},
    **{k: "rights" for k in (
        "ideology_liberal_modern", "ideology_egalitarian_modern", "ideology_humanitarian", "ideology_feminist",
    )},
    **{k: "labour" for k in (
        "ideology_proletarian", "ideology_egalitarian", "ideology_socialist", "ideology_social_democrat",
        "ideology_socialist_movement",
    )},
    **{k: "populist" for k in ("ideology_populist", "ideology_agrarian", "ideology_jacksonian_democrat")},
    **{k: "vanguard" for k in (
        "ideology_communist", "ideology_communist_movement", "ideology_vanguardist",
        "ideology_vanguardist_movement", "ideology_fascist", "ideology_fascist_movement",
    )},
    **{k: "technocratic" for k in ("ideology_technocratic", "ideology_positivist", "ideology_meritocratic")},
}
```

And after the closing `}` of `modifications`:

```python
for _ideology, _list in JUDICIARY_STANCES.items():
    modifications.setdefault(_ideology, {})["lawgroup_judiciary"] = JUDICIARY_LISTS[_list]
```

- [ ] **Step 4: The mod's own ideologies.** In `common/ideologies/extra_ideologies.txt`, give each `MOD_STANCES` ideology a `lawgroup_judiciary` block written from its list, all six laws, in `_JUDICIARY_LAWS` order. For example, `religious`:

```
	lawgroup_judiciary = {
		law_executive_tribunals = neutral
		law_religious_courts = strongly_approve
		law_statutory_courts = disapprove
		law_constitutional_review = disapprove
		law_judicial_supremacy = strongly_disapprove
		law_algorithmic_jurisprudence = strongly_disapprove
	}
```

- [ ] **Step 5: Regenerate.** On a machine with the game: `.venv/bin/python apply_ideologies.py && .venv/bin/python gen_law_consistency.py`. Without it: `.venv/bin/python scripts/generators/regen_ideologies_offline.py`. Every new block is append-only on its vanilla ideology (vanilla has no Judiciary block), so the offline tool writes INJECT entries; it stops and names any ideology it can't produce. Then `python3 scripts/format_paradox_tabs.py common/ideologies/extra_ideologies.txt`. (`modified.txt` and the consistency file are excluded from the tab check as generator-owned.)

- [ ] **Step 6: Run the tests**, plus `.venv/bin/python ideology_lawgroup_audit.py --strict`, `.venv/bin/python test_apply_ideologies.py` and `regen_ideologies_offline.py --check`. Expected: OK. The consistency generator must print no WARNING for `lawgroup_judiciary` (Executive Tribunals is its constraint-free fallback).

- [ ] **Step 7: Commit** the input, the hand-written blocks and both generated files: `git commit -m "Judiciary: ideology stances and the consistency walk"`.

---

### Task 8: Icons

**Files:**
- Modify: `scripts/image_pipeline/icon_prompts.py`
- Modify: `docs/systems/mod_systems.md` (the placeholder list, written in Task 9's section)

Laws ship on placeholder icons (Task 1: Autocracy, State Religion, Appointed Bureaucrats, Guaranteed Liberties, Protected Speech, Algorithmic Governance). The final art goes through the FLUX pipeline (`docs/auto_generated_files.md`: every mod law icon is `generate_icons.py`'s `law_<key>.dds`), which renders on a machine with the GPU. Placeholder art is fine (`gui_style_guide.md` rule 10).

- [ ] **Step 1: Add the six entries** beside the other law entries in `icon_prompts.ICONS`, `seed: None` (unreviewed), one object per law, siblings differing in silhouette:

```python
        # Judiciary (docs/superpowers/specs/2026-10-17-judiciary-design.md)
        "law_executive_tribunals": {"subject": "a royal crown resting on top of a closed leather-bound law book", "seed": None},
        "law_religious_courts": {"subject": "a thick holy book lying open on a carved wooden lectern, a string of prayer beads draped across its pages", "seed": None},
        "law_statutory_courts": {"subject": "a stack of three thick bound law codes with a judge's curled white wig resting on top", "seed": None},
        "law_constitutional_review": {"subject": "a long parchment charter unrolled and pinned flat by two brass weights, a large red wax seal at its foot", "seed": None},
        "law_judicial_supremacy": {"subject": "a pair of large brass balance scales on a marble pedestal, one pan holding a small rolled scroll and sitting lower than the other", "seed": None},
        "law_algorithmic_jurisprudence": {"subject": "a pair of brass balance scales whose central pillar is a computer chip with glowing circuit traces running out along the beam", "seed": None},
```

- [ ] **Step 2: On the owner's machine** (not in this PR if no GPU is available): `generate_icons.py` render, sheet, pick seeds, write, wire. `wire` points each law's `icon =` at `law_icons/<key>.dds`. Record the placeholder list as done in `mod_systems.md`.

- [ ] **Step 3: Commit** the registry entries: `git commit -m "Judiciary: icon prompts for the six laws"`.

---

### Task 9: Existing content and the systems doc

**Files:**
- Modify: `localization/english/te_laws_l_english.yml` (`lawgroup_criminal_justice_desc`)
- Modify: `localization/english/te_concepts_l_english.yml` (`concept_legislative_override_capacity_desc`)
- Modify: `docs/guides/scripting_best_practices.md` (the override sources bullet)
- Modify: `docs/systems/mod_systems.md` (new § Judiciary)

- [ ] **Step 1: Criminal Justice** no longer claims the courts: `lawgroup_criminal_justice_desc:0 "The form and function of the criminal justice system: what follows a conviction, and how offenders are punished or rehabilitated."`

- [ ] **Step 2: Override capacity's concept**: in "democratic suffrage, decentralization, feudal arrangements, and protected liberties lower it", add "and courts that can overturn the law" before "lower it", and "executive tribunals" to the raising list.

- [ ] **Step 3: `scripting_best_practices.md`**: the `country_legislative_override_capacity_add` bullet names "Judiciary" among its law groups.

- [ ] **Step 4: `docs/systems/mod_systems.md` § Judiciary** (after § Resource Transition), at that section's density: laws and file; the score (variable, ceilings, paper court, yearly step, the one refresh site, seeding and the old-save repair); entrenchment and its self-check; the shock (law-scope hop to the event); spending; stances (`JUDICIARY_LISTS`, hand-written mod blocks); the placeholder icon list (law, current icon, final subject); tests.

- [ ] **Step 5: Run `organize_loc.py --check` and `check_localization_files.py`**, then commit: `git commit -m "Judiciary: systems doc and the texts it touches"`.

---

### Task 10: The player guide

**Files:**
- Modify: `docs/player_guide/06-politics.md`, `docs/player_guide/04-banking.md`
- Regenerate: `docs/player_guide/Vic3TimelineExtended_Player_Guide.pdf`

Match the depth of the peers (`CLAUDE.md` § "Keep the player guide current"): a table row, the sources that changed, one short paragraph. No subsection for one law.

- [ ] **Step 1: `06-politics.md`, § "Laws on state power and information"**: a row:

```markdown
| Judiciary | Executive Tribunals, Religious Courts, Statutory Courts, Constitutional Review, Judicial Supremacy, Algorithmic Jurisprudence | Who checks the government: authority and override capacity against legitimacy and credit. Stronger courts earn their benefits through Judicial Independence, which grows over decades. |
```

Then a paragraph after the State Power paragraph: each court law sets a ceiling for **Judicial Independence** (0–100), which rises 4 a year toward it and falls 10 a year above it, halved under Autocracy, Single-Party State and Algorithmic Governance. At 100 it gives +10 legitimacy, −0.5pp credit standing, 10% more Capitalist investment and calmer losers of law changes. Statutory Courts give an elected government legitimacy from votes and an unelected one authority. Constitutional Review and Judicial Supremacy slow changes to the constitutional law groups, by 10% and 15% enactment success, and Judicial Supremacy the rights laws too; each law's tooltip lists what it does. Cutting the courts far below the score shakes lenders and costs legitimacy for five years. Religious Courts need an established religion.

- [ ] **Step 2: `06-politics.md`, § "Forceful Legislation"**: add the court laws to the sources sentence (Executive Tribunals +1; Constitutional Review −2, Judicial Supremacy −3; Algorithmic Jurisprudence +2 under Algorithmic Governance), and to the table's "Lasting cost" column, "Judicial Independence −5 / −10 / −20".

- [ ] **Step 3: `04-banking.md`**: where the guide names what moves credit standing, add the Judicial Independence and court-law terms in one clause.

- [ ] **Step 4: Rebuild and lint**: `.venv/bin/python scripts/build_player_guide.py && python3 scripts/analysis/check_player_guide_style.py --strict && .venv/bin/python scripts/build_player_guide.py --check`.

- [ ] **Step 5: Commit** chapters and PDF together: `git commit -m "Player guide: the Judiciary laws and Judicial Independence"`.

---

### Task 11: The play-test list

**Files:**
- Create: `docs/testing/judiciary-playtest.md`

- [ ] **Step 1: Write it**, in the shape of `docs/testing/demographics-playtest.md`: a Self-checks table (name, what OK and BROKEN mean, the fallback) and a checklist:
  - **Self-check** `judiciary_enacting_law_scope`: OK means entrenchment can see the law. BROKEN, or no line at all after a reviewing court's enactment, means move the work into a hidden event fired from `on_law_enactment_started` (Forceful Legislation's route).
  - **Lobby (1836):** the United States shows Constitutional Review, Persia and the Ottoman Empire Religious Courts, Britain, France and Prussia Statutory Courts, Russia and Qing Executive Tribunals (the scripted effect ran from history).
  - **February 1836:** the Judicial Independence modifier shows in Britain's modifiers with the scaled values; the concept reads "Now 70, heading for 70". Britain (an elected government) shows Supremacy of Statute as legitimacy from votes; Prussia, if it has no voting law, as +25 authority.
  - **Tooltips:** each court law's tooltip lists its ceiling and its other lines; Autocracy's lists "Judicial Independence Ceiling −50%" and "Courts Can’t Challenge the Government"; the country panel's Modifiers tab shows the ceiling's breakdown.
  - **Entrenchment:** as the United States, start Universal Suffrage; the enactment shows "Constitutional Challenge".
  - **Spending:** Forceful Legislation's options show the score's cost; next month the modifier is smaller.
  - **Shock:** as the United States, enact Executive Tribunals (console); a week later a hidden event applies Court Overhaul, decaying over 5 years, with middle-strata radicals.
  - **Secularizing:** as the Ottoman Empire with Rationalism, enact Total Separation; the courts become Statutory Courts.
  - **Old save:** load a save from before the group; within a month each country holds its rule-based court, and within two a score at half its ceiling.
  - **AI:** over 50 years, count court-law changes per country: flip-flopping is a red flag.

- [ ] **Step 2: Commit**: `git commit -m "Judiciary: play-test list"`.

---

### Task 12: Validation

- [ ] **Step 1: Everything CI runs**, with the dummy env:
  - `.venv/bin/python -m compileall -q .`
  - `.venv/bin/python -m unittest discover -s . -p 'test_*.py' > /tmp/jud.txt 2>&1; grep -E '^(Ran |OK|FAILED)' /tmp/jud.txt`
  - `.venv/bin/ruff check .`
  - `python3 scripts/format_paradox_tabs.py --check` over the changed `.txt` (CI's pathspec)
  - `python3 scripts/analysis/check_localization_files.py`, `python3 organize_loc.py --check`
  - `python3 scripts/analysis/check_post_load_rosters.py`
  - every `--strict` audit CI lists in `CLAUDE.md` (in particular `ideology_lawgroup`, `loc_coverage`, `loc_render`, `silent_variable`, `script_argument`, `change_variable_clamp`, `event_context`, `orphaned_event`, `modifier_multiplier_var`, `effect_trigger_validity`'s report), `kill_character_audit --check`, `attitude_key_audit` bare.
- [ ] **Step 2: BOMs**: every new or changed `.txt` and `.yml` starts with exactly one BOM (`head -c 6 <f> | xxd`).
- [ ] **Step 3: The f-string scan** on changed Python files.
- [ ] **Step 4: Re-read the diff against the Global Constraints and Review Focus**; fix what fails before pushing.
- [ ] **Step 5: The PR body** names the chapters updated (Player guide line), links the spec, lists the self-check and the play-test file, and says which § 12 questions were ruled on.
