# Collective Governance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn `law_direct_democracy` into "Collective Governance" (no supreme individual executive), with one script-attached amendment and a government type for each Distribution of Power group it allows.

**Architecture:** Five scripted triggers name the Distribution of Power groups. They are the single source for the five amendments, the refresh effect that attaches the matching amendment to the governance law, the law's enactment-preview tooltips, the government types and the voting-only call sites. The law keeps its engine key. A static test file with one `EXPRESSIONS` table pins every site.

**Tech Stack:** Paradox Clausewitz script (Victoria 3 mod), localization YAML, Python `unittest` static tests over the script files, the repo's generators (`apply_ideologies.py`, `gen_law_consistency.py`, `organize_loc.py`).

**Spec:** `docs/superpowers/specs/2026-09-26-collective-governance-design.md` (Decisions, engine facts, §1–§8).

## Global Constraints

- Work in the sparse worktree `/home/jakef/src/Vic3TE-collective-governance` on branch `collective-governance`. Never `POST /reload` to port 8950 from it (that regenerates the main checkout). Task 8 runs its own server on port 8951.
- Python: `/home/jakef/src/Vic3TimelineExtended/.venv/bin/python`, written `$PY` below. Every shell step starts with `cd /home/jakef/src/Vic3TE-collective-governance && PY=/home/jakef/src/Vic3TimelineExtended/.venv/bin/python`.
- The engine key stays `law_direct_democracy`. Never rename it, and keep the existing government-type keys `gov_direct_democracy` and `gov_direct_democracy_single_party_state`.
- Brace-based `.txt` files use tab indentation. Every changed `.txt`/`.yml` keeps its UTF-8 BOM, and new `.txt` files start with one. All touched files are LF. `timeline_extended_governments.txt`, `extra_laws.txt` and `extra_ideologies.txt` have no final newline; the edit scripts below preserve that.
- Loc: `#b X#!`, never `[b]`. Describe the mod's own effects; don't explain vanilla mechanics.
- Never hand-edit generated files. `common/ideologies/modified.txt` comes from `apply_ideologies.py`, `common/scripted_effects/extra_law_consistency_generated.txt` from `gen_law_consistency.py`, and loc placement from `organize_loc.py`.
- Exact values from the spec:
  - Tech gate: `political_agitation`.
  - Base modifiers: `country_legitimacy_govt_size_add = 1`, `country_authority_mult = -0.15`, `country_law_enactment_speed_mult = -0.1`, `country_legitimacy_ideological_incoherence_mult = -0.3`.
  - Amendment values: as in Task 2.
- Stage by path, never `git commit -a`. Every commit message ends with:
  ```
  Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01M7W7KgW8hadKoaLqAVNeBf
  ```
- Don't push and don't open a PR. Task 9 writes the PR body to an untracked file; the owner decides when to open it.
- "Append to `test_collective_governance.py`" always means: insert above the final `if __name__ == "__main__":` block.
- Scratch output (reload JSON, cascade summary) goes in the worktree's git dir, `$(git rev-parse --git-dir)`, which is never tracked.

## Review Focus

1. **The law arriving without an enactment.** This covers the consistency cascade's `activate_law`, and a save that already holds the law. The amendment must still be attached. `on_activate` does it hidden, and the monthly pulse backs it up (Task 4 `test_activation_attaches_hidden`, Task 3 `test_hooks_are_wired`).
2. **A Distribution of Power change while the law is held.** The old amendment must go and the new one arrive in the same refresh. The sync removes on `$TRIGGER$ = no` and adds on `$TRIGGER$ = yes` (Task 3 `test_sync_removes_on_mismatch_and_adds_on_match`).
3. **A switch to a Distribution of Power outside the table (Autocracy) while holding the law.** Until the cascade replaces the law, the government must read "Collective Governance", never "Plebiscitary Autocracy", and every amendment must be removed. The catch-all comes last, the autocracy type is gone, and all five triggers are false, so the sync removes each amendment (Task 5 `test_resolution_order`, `test_plebiscitary_autocracy_is_gone`).
4. **Oligarchy under Feudal Contracts versus under any other state-power law.** The first reads Noble Commonwealth, the second Patrician Council, so the more specific type must come first (Task 5 `test_resolution_order`).
5. **Referendum-flavoured events under a council or bureau government.** No enactment event for this law may fire outside the voting laws (Task 6 `test_every_enactment_event_for_the_law_is_gated`).

---

### Task 1: The Distribution of Power triggers and the test table

**Files:**
- Create: `common/scripted_triggers/collective_governance_triggers.txt`
- Create: `test_collective_governance.py`

**Interfaces:**
- Produces (country-scope scripted triggers): `collective_governance_is_popular`, `collective_governance_is_party`, `collective_governance_is_technocratic`, `collective_governance_is_anarchic`, `collective_governance_is_patrician`.
- Produces (test module): `EXPRESSIONS` (namedtuple `Expression(trigger, dop_laws, amendment, tooltip)`), and helpers `_path`, `_read`, `_raw`, `_block`, `_inner`, `_norm`, `_top_level_names`, `_modifiers`, `_loc`. Later tasks append test classes to this file.

- [ ] **Step 0: Worktree setup (once)**

```bash
cd /home/jakef/src/Vic3TE-collective-governance && cp /home/jakef/src/Vic3TimelineExtended/paths.local.json . && git status --short
```
Expected: no output (`paths.local.json` is gitignored).

- [ ] **Step 1: Write the failing test** — create `test_collective_governance.py`:

```python
# -*- coding: utf-8 -*-
"""Collective Governance (law_direct_democracy): one table, pinned against
every site that lists the Distribution of Power expressions by hand.

The law keeps its engine key and is displayed as Collective Governance. Each
Distribution of Power group it allows gets one script-attached amendment and
at least one government type. Nothing in the engine checks that the
prerequisites, triggers, amendments, refresh effect, preview tooltips and
government types agree, and a mismatch is engine-silent: a country holding the
law with no amendment, or with the wrong government name. EXPRESSIONS is the
single list; each test checks one site against it. To add a Distribution of
Power law, add it to its row (or add a row) and follow the failures.

Spec: docs/superpowers/specs/2026-09-26-collective-governance-design.md

Run: python3 -m unittest test_collective_governance -v
"""

import os
import re
import unittest
from collections import namedtuple

REPO = os.path.dirname(os.path.abspath(__file__))


def _path(*parts):
    return os.path.join(REPO, *parts)


def _raw(path):
    with open(path, encoding="utf-8-sig") as f:
        return f.read()


def _read(path):
    """Script text with comments stripped (not for loc: `#b` is markup there)."""
    return re.sub(r"#[^\n]*", "", _raw(path))


def _close(text, open_brace):
    depth = 0
    for i in range(open_brace, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return i
    raise AssertionError("unclosed block")


def _block(text, name):
    """The body of the top-level ``name = { ... }`` block (an optional
    INJECT:/REPLACE: prefix is allowed)."""
    m = re.search(r"^(?:[A-Z_]+:)?" + re.escape(name) + r"\s*=\s*\{", text, re.M)
    if m is None:
        raise AssertionError(f"{name} not found")
    return text[m.end():_close(text, m.end() - 1)]


def _inner(text, name):
    """The body of the first ``name = { ... }`` block at any depth."""
    m = re.search(r"(?<![\w.:])" + re.escape(name) + r"\s*=\s*\{", text)
    if m is None:
        raise AssertionError(f"{name} not found")
    return text[m.end():_close(text, m.end() - 1)]


def _norm(text):
    return " ".join(text.split())


def _top_level_names(text):
    return re.findall(r"^(\w+)\s*=\s*\{", text, re.M)


def _modifiers(body):
    return dict(re.findall(r"(\w+)\s*=\s*(-?[\w.]+)", body))


_LOC_LINE = re.compile(r'^\s*([\w.]+):\d*\s*"(.*)"\s*$')


def _loc():
    out = {}
    folder = _path("localization", "english")
    for name in os.listdir(folder):
        if name.endswith(".yml"):
            with open(os.path.join(folder, name), encoding="utf-8-sig") as f:
                for line in f:
                    m = _LOC_LINE.match(line)
                    if m:
                        out[m.group(1)] = m.group(2)
    return out


Expression = namedtuple("Expression", "trigger dop_laws amendment tooltip")

EXPRESSIONS = [
    Expression(
        "collective_governance_is_popular",
        {"law_landed_voting", "law_wealth_voting", "law_census_voting", "law_universal_suffrage"},
        "amendment_collective_direct_democracy",
        "COLLECTIVE_GOVERNANCE_TT_POPULAR",
    ),
    Expression(
        "collective_governance_is_party",
        {"law_single_party_state"},
        "amendment_collective_leadership",
        "COLLECTIVE_GOVERNANCE_TT_PARTY",
    ),
    Expression(
        "collective_governance_is_technocratic",
        {"law_technocracy"},
        "amendment_collective_administration",
        "COLLECTIVE_GOVERNANCE_TT_TECHNOCRATIC",
    ),
    Expression(
        "collective_governance_is_anarchic",
        {"law_anarchy"},
        "amendment_collective_free_federation",
        "COLLECTIVE_GOVERNANCE_TT_ANARCHIC",
    ),
    Expression(
        "collective_governance_is_patrician",
        {"law_oligarchy", "law_organic_regulation"},
        "amendment_collective_patrician_council",
        "COLLECTIVE_GOVERNANCE_TT_PATRICIAN",
    ),
]

TRIGGERS = _path("common", "scripted_triggers", "collective_governance_triggers.txt")


class TriggerTests(unittest.TestCase):
    def test_each_trigger_lists_exactly_its_laws(self):
        text = _read(TRIGGERS)
        for e in EXPRESSIONS:
            with self.subTest(trigger=e.trigger):
                laws = set(re.findall(r"has_law\s*=\s*law_type:(\w+)", _block(text, e.trigger)))
                self.assertEqual(laws, e.dop_laws)

    def test_no_stale_trigger(self):
        self.assertEqual(set(_top_level_names(_read(TRIGGERS))), {e.trigger for e in EXPRESSIONS})

    def test_no_law_is_in_two_groups(self):
        laws = [law for e in EXPRESSIONS for law in e.dop_laws]
        self.assertEqual(len(laws), len(set(laws)))

    def test_file_has_bom(self):
        with open(TRIGGERS, "rb") as f:
            self.assertEqual(f.read(3), b"\xef\xbb\xbf")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `$PY -m unittest test_collective_governance -v`
Expected: 3 ERRORs (`FileNotFoundError` for `collective_governance_triggers.txt`), 1 pass (`test_no_law_is_in_two_groups`).

- [ ] **Step 3: Create the triggers file** — `common/scripted_triggers/collective_governance_triggers.txt`:

```
# Collective Governance (law_direct_democracy, displayed as "Collective
# Governance"): which Distribution of Power group a country is in.
#
# The single source for the five amendments' possible / can_repeal
# (extra_amendments.txt), te_refresh_collective_governance_amendment, the
# law's on_enact preview, the government types and the voting-only call
# sites (cultural hegemony, extra_law_events.24/.60/.84,
# modern_election_events.33). At most one is true. Autocracy and anything
# else outside these five cannot hold the law.
#
# Spec: docs/superpowers/specs/2026-09-26-collective-governance-design.md
# Pinned by test_collective_governance.py (EXPRESSIONS).

collective_governance_is_popular = {
	OR = {
		has_law = law_type:law_landed_voting
		has_law = law_type:law_wealth_voting
		has_law = law_type:law_census_voting
		has_law = law_type:law_universal_suffrage
	}
}

collective_governance_is_party = {
	has_law = law_type:law_single_party_state
}

collective_governance_is_technocratic = {
	has_law = law_type:law_technocracy
}

collective_governance_is_anarchic = {
	has_law = law_type:law_anarchy
}

collective_governance_is_patrician = {
	OR = {
		has_law = law_type:law_oligarchy
		has_law = law_type:law_organic_regulation
	}
}
```

Then give it a BOM:
```bash
sed -i '1s/^\xEF\xBB\xBF//; 1s/^/\xEF\xBB\xBF/' common/scripted_triggers/collective_governance_triggers.txt
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `$PY -m unittest test_collective_governance -v`
Expected: 4 tests, OK.

- [ ] **Step 5: Commit**

```bash
git add common/scripted_triggers/collective_governance_triggers.txt test_collective_governance.py
git commit -F - <<'EOF'
Collective Governance: Distribution of Power triggers and the test table

Five scripted triggers name the groups law_direct_democracy (Collective
Governance) allows. test_collective_governance.py's EXPRESSIONS table pins
them; later sites are checked against the same table.

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01M7W7KgW8hadKoaLqAVNeBf
EOF
```

---

### Task 2: The five amendments, their loc, and the organize_loc rule

**Files:**
- Modify: `common/amendments/extra_amendments.txt` (append a section)
- Modify: `localization/english/te_concepts_l_english.yml` (append keys)
- Modify: `organize_loc.py` (one routing rule, beside the `TE_HOMELAND_` rule near line 428)
- Test: `test_collective_governance.py` (append `AmendmentTests`), `test_organize_loc.py` (one test in `CategorizeKeyTests`)

**Interfaces:**
- Consumes: the five triggers (Task 1).
- Produces: amendment keys `amendment_collective_direct_democracy`, `amendment_collective_leadership`, `amendment_collective_administration`, `amendment_collective_free_federation`, `amendment_collective_patrician_council`, and the loc key `COLLECTIVE_GOVERNANCE_TT_REPEAL`.

- [ ] **Step 1: Write the failing tests** — append to `test_collective_governance.py`, above the `if __name__` line:

```python
AMENDMENTS = _path("common", "amendments", "extra_amendments.txt")

# Today's Direct Democracy law block, moved verbatim onto the amendment (spec §2).
DIRECT_DEMOCRACY_PACKAGE = {
    "country_must_have_movement_to_enact_laws_bool": "yes",
    "political_movement_pop_attraction_mult": "1",
    "political_movement_radicalism_add": "0.5",
    "political_movement_radicalism_from_enactment_approval_mult": "-0.75",
    "political_movement_radicalism_from_enactment_disapproval_mult": "-0.75",
    "country_legitimacy_govt_total_votes_add": "30",
    "state_political_strength_from_wealth_mult": "-0.25",
    "country_law_enactment_success_add": "0.25",
    "country_agitator_slots_add": "1",
}

EXPRESSION_MODIFIERS = {
    "amendment_collective_direct_democracy": DIRECT_DEMOCRACY_PACKAGE,
    "amendment_collective_leadership": {"country_coup_resistance_mult": "0.25"},
    "amendment_collective_administration": {
        "country_institution_size_change_speed_mult": "0.5",
        "state_decree_cost_mult": "0.25",
    },
    "amendment_collective_free_federation": {
        "country_must_have_movement_to_enact_laws_bool": "yes",
        "political_movement_pop_attraction_mult": "0.5",
    },
    "amendment_collective_patrician_council": {
        "country_aristocrats_pol_str_mult": "0.15",
        "country_capitalists_pol_str_mult": "0.15",
    },
}


class AmendmentTests(unittest.TestCase):
    def setUp(self):
        self.text = _read(AMENDMENTS)

    def test_each_amendment_attaches_only_to_the_law(self):
        for e in EXPRESSIONS:
            with self.subTest(amendment=e.amendment):
                body = _block(self.text, e.amendment)
                self.assertEqual(_norm(_inner(body, "allowed_laws")), "law_direct_democracy")

    def test_each_amendment_follows_its_trigger(self):
        for e in EXPRESSIONS:
            with self.subTest(amendment=e.amendment):
                body = _block(self.text, e.amendment)
                self.assertEqual(_norm(_inner(body, "possible")), f"{e.trigger} = yes")
                self.assertEqual(
                    _norm(_inner(body, "can_repeal")),
                    "custom_tooltip = { text = COLLECTIVE_GOVERNANCE_TT_REPEAL "
                    f"NOT = {{ {e.trigger} = yes }} }}",
                )

    def test_each_amendment_is_script_only(self):
        for e in EXPRESSIONS:
            with self.subTest(amendment=e.amendment):
                body = _block(self.text, e.amendment)
                self.assertEqual(_norm(_inner(body, "would_sponsor")), "always = no")
                self.assertEqual(_norm(_inner(body, "ai_will_revoke")), "always = no")
                self.assertRegex(body, r"amendment_activism_multiplier\s*=\s*0\b")
                self.assertNotRegex(body, r"\bparent\s*=")

    def test_modifiers(self):
        for e in EXPRESSIONS:
            with self.subTest(amendment=e.amendment):
                body = _block(self.text, e.amendment)
                self.assertEqual(_modifiers(_inner(body, "modifier")), EXPRESSION_MODIFIERS[e.amendment])

    def test_no_stale_collective_amendment(self):
        defined = {n for n in _top_level_names(self.text) if n.startswith("amendment_collective_")}
        self.assertEqual(defined, {e.amendment for e in EXPRESSIONS})

    def test_loc(self):
        loc = _loc()
        for e in EXPRESSIONS:
            for key in (e.amendment, e.amendment + "_desc"):
                with self.subTest(key=key):
                    self.assertIn(key, loc)
        self.assertIn("COLLECTIVE_GOVERNANCE_TT_REPEAL", loc)
```

And in `test_organize_loc.py`, inside `class CategorizeKeyTests`, after `test_homeland_panel_family_stays_together`:

```python
    def test_collective_governance_families_stay_together(self):
        # A government type or amendment name and its _desc must land in the
        # same file. Four-token bases would otherwise split: the name to
        # MISCELLANEOUS, the _desc to CONCEPTS.
        for key in (
            "gov_collective_noble_commonwealth",
            "gov_collective_noble_commonwealth_desc",
            "gov_collective_governance",
            "gov_collective_governance_desc",
            "gov_direct_democracy_single_party_state",
            "gov_direct_democracy_single_party_state_desc",
            "amendment_collective_direct_democracy",
            "amendment_collective_direct_democracy_desc",
        ):
            with self.subTest(key=key):
                self.assertEqual(categorize_key(key, set()), "CONCEPTS")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `$PY -m unittest test_collective_governance test_organize_loc -v`
Expected: the `AmendmentTests` FAIL with `amendment_collective_… not found`. `test_collective_governance_families_stay_together` FAILs on `gov_collective_noble_commonwealth` (MISCELLANEOUS ≠ CONCEPTS). The Task 1 tests pass.

- [ ] **Step 3: Append the amendments** — add to the end of `common/amendments/extra_amendments.txt` (the file ends with a newline):

```
# ======================================================================
#  COLLECTIVE GOVERNANCE (law_direct_democracy)
#
#  One amendment per Distribution of Power group, attached and removed
#  only by te_refresh_collective_governance_amendment
#  (collective_governance_effects.txt), never by negotiation.
#  possible and can_repeal both ask the group's trigger
#  (collective_governance_triggers.txt), so the swap works whether or
#  not script removal respects can_repeal, and the player cannot repeal
#  the amendment their Distribution of Power calls for.
#  No parent: IG stance would count the law's approval a second time.
#  Spec: docs/superpowers/specs/2026-09-26-collective-governance-design.md
# ======================================================================

amendment_collective_direct_democracy = {
	allowed_laws = { law_direct_democracy }
	modifier = {
		country_must_have_movement_to_enact_laws_bool = yes
		political_movement_pop_attraction_mult = 1
		political_movement_radicalism_add = 0.5
		political_movement_radicalism_from_enactment_approval_mult = -0.75
		political_movement_radicalism_from_enactment_disapproval_mult = -0.75
		country_legitimacy_govt_total_votes_add = 30
		state_political_strength_from_wealth_mult = -0.25
		country_law_enactment_success_add = 0.25
		country_agitator_slots_add = 1
	}
	possible = { collective_governance_is_popular = yes }
	would_sponsor = { always = no }
	ai_will_revoke = { always = no }
	can_repeal = {
		custom_tooltip = {
			text = COLLECTIVE_GOVERNANCE_TT_REPEAL
			NOT = { collective_governance_is_popular = yes }
		}
	}
	amendment_activism_multiplier = 0
}

amendment_collective_leadership = {
	allowed_laws = { law_direct_democracy }
	modifier = {
		country_coup_resistance_mult = 0.25
	}
	possible = { collective_governance_is_party = yes }
	would_sponsor = { always = no }
	ai_will_revoke = { always = no }
	can_repeal = {
		custom_tooltip = {
			text = COLLECTIVE_GOVERNANCE_TT_REPEAL
			NOT = { collective_governance_is_party = yes }
		}
	}
	amendment_activism_multiplier = 0
}

amendment_collective_administration = {
	allowed_laws = { law_direct_democracy }
	modifier = {
		country_institution_size_change_speed_mult = 0.5
		state_decree_cost_mult = 0.25
	}
	possible = { collective_governance_is_technocratic = yes }
	would_sponsor = { always = no }
	ai_will_revoke = { always = no }
	can_repeal = {
		custom_tooltip = {
			text = COLLECTIVE_GOVERNANCE_TT_REPEAL
			NOT = { collective_governance_is_technocratic = yes }
		}
	}
	amendment_activism_multiplier = 0
}

amendment_collective_free_federation = {
	allowed_laws = { law_direct_democracy }
	modifier = {
		country_must_have_movement_to_enact_laws_bool = yes
		political_movement_pop_attraction_mult = 0.5
	}
	possible = { collective_governance_is_anarchic = yes }
	would_sponsor = { always = no }
	ai_will_revoke = { always = no }
	can_repeal = {
		custom_tooltip = {
			text = COLLECTIVE_GOVERNANCE_TT_REPEAL
			NOT = { collective_governance_is_anarchic = yes }
		}
	}
	amendment_activism_multiplier = 0
}

amendment_collective_patrician_council = {
	allowed_laws = { law_direct_democracy }
	modifier = {
		country_aristocrats_pol_str_mult = 0.15
		country_capitalists_pol_str_mult = 0.15
	}
	possible = { collective_governance_is_patrician = yes }
	would_sponsor = { always = no }
	ai_will_revoke = { always = no }
	can_repeal = {
		custom_tooltip = {
			text = COLLECTIVE_GOVERNANCE_TT_REPEAL
			NOT = { collective_governance_is_patrician = yes }
		}
	}
	amendment_activism_multiplier = 0
}
```

- [ ] **Step 4: Append the loc** (`te_concepts_l_english.yml` ends with a newline; `organize_loc.py` re-files keys in Task 8):

```bash
cat >> localization/english/te_concepts_l_english.yml <<'EOF'
 amendment_collective_direct_democracy:0 "Direct Democracy"
 amendment_collective_direct_democracy_desc:0 "The voters decide directly. A law passes only when a political movement carries it."
 amendment_collective_leadership:0 "Collective Leadership"
 amendment_collective_leadership_desc:0 "The party's presidium governs together. There is no single leader for a coup to remove."
 amendment_collective_administration:0 "Collegial Administration"
 amendment_collective_administration_desc:0 "The institutions govern as equal bureaus, each in its own field. They adapt quickly, but decrees cost more with no one executive to issue them."
 amendment_collective_free_federation:0 "Free Federation"
 amendment_collective_free_federation_desc:0 "Delegates act only on mandates from below. A law passes only when a political movement carries it."
 amendment_collective_patrician_council:0 "Patrician Council"
 amendment_collective_patrician_council_desc:0 "The powerful govern as peers, and aristocrats and capitalists hold more of the country's political strength."
 COLLECTIVE_GOVERNANCE_TT_REPEAL:0 "The Distribution of Power no longer calls for this amendment"
EOF
```

- [ ] **Step 5: Add the organize_loc rule** — in `organize_loc.py`, directly after the block

```python
    if key.startswith("TE_HOMELAND_"):
        return "MISCELLANEOUS"
```
insert:
```python
    # Collective Governance government types and amendments (law_direct_democracy):
    # four-token bases (`gov_collective_noble_commonwealth`,
    # `amendment_collective_direct_democracy`) would otherwise split, the name
    # to MISCELLANEOUS and the `_desc` to CONCEPTS. File the whole family with
    # the other government-type and amendment loc.
    if key.startswith(("gov_collective_", "gov_direct_democracy", "amendment_collective_")):
        return "CONCEPTS"
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `$PY -m unittest test_collective_governance test_organize_loc -v`
Expected: all pass.

- [ ] **Step 7: Tab check and commit**

```bash
$PY scripts/format_paradox_tabs.py --check common/amendments/extra_amendments.txt
git add common/amendments/extra_amendments.txt localization/english/te_concepts_l_english.yml organize_loc.py test_organize_loc.py test_collective_governance.py
git commit -F - <<'EOF'
Collective Governance: one amendment per Distribution of Power group

Direct Democracy (today's referendum package, moved verbatim), Collective
Leadership, Collegial Administration, Free Federation and Patrician Council.
Script-only: possible and can_repeal ask the group's trigger, so the player
cannot repeal the one their Distribution of Power calls for. organize_loc
keeps each gov_collective_/amendment_collective_ name with its _desc.

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01M7W7KgW8hadKoaLqAVNeBf
EOF
```
Expected: the tab check prints nothing and exits 0.

---

### Task 3: The refresh effect and its hooks

**Files:**
- Create: `common/scripted_effects/collective_governance_effects.txt`
- Modify: `common/on_actions/extra_on_actions.txt` (`on_monthly_pulse_country` list ~line 347, `on_law_activated` list ~line 508, new wrappers after `te_fix_inconsistent_laws_from_law_scope` ~line 1415)
- Test: `test_collective_governance.py` (append `RefreshTests`)

**Interfaces:**
- Consumes: the triggers (Task 1) and the amendments (Task 2).
- Produces: the country-scope scripted effect `te_refresh_collective_governance_amendment` (no parameters); the law-scope helper `te_cg_sync_amendment = { AMENDMENT = <amendment key> TRIGGER = <trigger> }`; the on-actions `te_collective_governance_from_law_scope` and `te_collective_governance_country_pulse`.

- [ ] **Step 1: Write the failing tests** — append to `test_collective_governance.py`:

```python
EFFECTS = _path("common", "scripted_effects", "collective_governance_effects.txt")
ON_ACTIONS = _path("common", "on_actions", "extra_on_actions.txt")


class RefreshTests(unittest.TestCase):
    def test_refresh_syncs_every_amendment_once(self):
        body = _block(_read(EFFECTS), "te_refresh_collective_governance_amendment")
        calls = re.findall(
            r"te_cg_sync_amendment\s*=\s*\{\s*AMENDMENT\s*=\s*(\w+)\s+TRIGGER\s*=\s*(\w+)\s*\}", body)
        self.assertEqual(sorted(calls), sorted((e.amendment, e.trigger) for e in EXPRESSIONS))

    def test_refresh_only_touches_the_governance_law_of_holders(self):
        body = _norm(_block(_read(EFFECTS), "te_refresh_collective_governance_amendment"))
        self.assertIn("limit = { has_law = law_type:law_direct_democracy }", body)
        self.assertIn("save_scope_as = cg_country", body)
        self.assertIn("ruler ?= { interest_group ?= { save_scope_as = cg_sponsor } }", body)
        self.assertIn("active_law:lawgroup_governance_principles ?= {", body)

    def test_sync_removes_on_mismatch_and_adds_on_match(self):
        body = _norm(_block(_read(EFFECTS), "te_cg_sync_amendment"))
        self.assertIn(
            "limit = { has_amendment = amendment_type:$AMENDMENT$ scope:cg_country = { $TRIGGER$ = no } } "
            "random_scope_amendment = { limit = { amendment_type:$AMENDMENT$ ?= this.type } remove_amendment = yes }",
            body)
        self.assertIn(
            "limit = { NOT = { has_amendment = amendment_type:$AMENDMENT$ } "
            "scope:cg_country = { $TRIGGER$ = yes } exists = scope:cg_sponsor } "
            "add_amendment = { type = $AMENDMENT$ sponsor = scope:cg_sponsor cooldown = 0 }",
            body)

    def test_hooks_are_wired(self):
        text = _read(ON_ACTIONS)
        law_hooks = _inner(_block(text, "on_law_activated"), "on_actions").split()
        self.assertIn("te_collective_governance_from_law_scope", law_hooks)
        self.assertGreater(law_hooks.index("te_collective_governance_from_law_scope"),
                           law_hooks.index("te_fix_inconsistent_laws_from_law_scope"))
        monthly = _inner(_block(text, "on_monthly_pulse_country"), "on_actions").split()
        self.assertIn("te_collective_governance_country_pulse", monthly)
        self.assertEqual(_norm(_block(text, "te_collective_governance_from_law_scope")),
                         "effect = { owner = { te_refresh_collective_governance_amendment = yes } }")
        self.assertEqual(_norm(_block(text, "te_collective_governance_country_pulse")),
                         "effect = { te_refresh_collective_governance_amendment = yes }")

    def test_file_has_bom(self):
        with open(EFFECTS, "rb") as f:
            self.assertEqual(f.read(3), b"\xef\xbb\xbf")
```

- [ ] **Step 2: Run to verify failure**

Run: `$PY -m unittest test_collective_governance.RefreshTests -v`
Expected: ERRORs (`FileNotFoundError`, `te_collective_governance_from_law_scope not found`).

- [ ] **Step 3: Create the effects file** — `common/scripted_effects/collective_governance_effects.txt`:

```
# Collective Governance (law_direct_democracy, displayed as "Collective
# Governance"): keeps on the governance law exactly the one amendment the
# country's Distribution of Power calls for, and none of the other four.
#
# Derived from current laws on every call, so nothing is stored, and a
# revolution's winner gets the amendment its own laws call for. A law's
# amendments leave with it when it is replaced, so a country that drops the
# law needs no cleanup.
#
# One refresh, three callers:
#   law_direct_democracy on_activate (hidden)  - the day the law lands, however it arrives
#   te_collective_governance_from_law_scope     - on_law_activated: a Distribution of Power change
#   te_collective_governance_country_pulse      - monthly backstop, and migration of existing saves
#
# Amendments need a sponsor (vanilla land_ownership_law_events.txt). We use
# the ruler's interest group; with no ruler the add waits for the next call.
#
# Spec: docs/superpowers/specs/2026-09-26-collective-governance-design.md
# Pinned by test_collective_governance.py.

te_refresh_collective_governance_amendment = {
	if = {
		limit = { has_law = law_type:law_direct_democracy }
		save_scope_as = cg_country
		ruler ?= {
			interest_group ?= { save_scope_as = cg_sponsor }
		}
		active_law:lawgroup_governance_principles ?= {
			te_cg_sync_amendment = { AMENDMENT = amendment_collective_direct_democracy TRIGGER = collective_governance_is_popular }
			te_cg_sync_amendment = { AMENDMENT = amendment_collective_leadership TRIGGER = collective_governance_is_party }
			te_cg_sync_amendment = { AMENDMENT = amendment_collective_administration TRIGGER = collective_governance_is_technocratic }
			te_cg_sync_amendment = { AMENDMENT = amendment_collective_free_federation TRIGGER = collective_governance_is_anarchic }
			te_cg_sync_amendment = { AMENDMENT = amendment_collective_patrician_council TRIGGER = collective_governance_is_patrician }
		}
	}
}

# Law scope (the governance law). Needs scope:cg_country, and scope:cg_sponsor
# to add. Removes $AMENDMENT$ when the country no longer meets $TRIGGER$;
# adds it when the country does and it is missing. Vanilla's remove-by-type
# form (ep2_tenpo_events.txt).
te_cg_sync_amendment = {
	if = {
		limit = {
			has_amendment = amendment_type:$AMENDMENT$
			scope:cg_country = { $TRIGGER$ = no }
		}
		random_scope_amendment = {
			limit = { amendment_type:$AMENDMENT$ ?= this.type }
			remove_amendment = yes
		}
	}
	else_if = {
		limit = {
			NOT = { has_amendment = amendment_type:$AMENDMENT$ }
			scope:cg_country = { $TRIGGER$ = yes }
			exists = scope:cg_sponsor
		}
		add_amendment = {
			type = $AMENDMENT$
			sponsor = scope:cg_sponsor
			cooldown = 0
		}
	}
}
```

Then give it a BOM:
```bash
sed -i '1s/^\xEF\xBB\xBF//; 1s/^/\xEF\xBB\xBF/' common/scripted_effects/collective_governance_effects.txt
```

- [ ] **Step 4: Wire the hooks** in `common/on_actions/extra_on_actions.txt` (three Edits; each `old_string` is unique):

(a) The `on_law_activated` list. Replace
```
		te_fix_inconsistent_laws_from_law_scope
		language_reform_law_on_action
```
with
```
		te_fix_inconsistent_laws_from_law_scope
		te_collective_governance_from_law_scope
		language_reform_law_on_action
```

(b) The `on_monthly_pulse_country` list. Replace
```
		te_fix_inconsistent_laws_country_pulse
		operation_polo_on_action
```
with
```
		te_fix_inconsistent_laws_country_pulse
		te_collective_governance_country_pulse
		operation_polo_on_action
```

(c) The wrappers. Replace
```
te_fix_inconsistent_laws_from_law_scope = {
	effect = {
		owner = {
			te_fix_inconsistent_laws = yes
		}
	}
}
```
with the same block followed by:
```

# COLLECTIVE GOVERNANCE - keeps law_direct_democracy's amendment matching the
# Distribution of Power (te_refresh_collective_governance_amendment,
# collective_governance_effects.txt). Listed after
# te_fix_inconsistent_laws_from_law_scope in on_law_activated so it sees the
# laws the consistency cascade leaves. ROOT = law scope; owner = country.
te_collective_governance_from_law_scope = {
	effect = {
		owner = {
			te_refresh_collective_governance_amendment = yes
		}
	}
}

# Monthly backstop for the above: catches a law switched by activate_law
# (whether that fires on_law_activated is unverified) and migrates saves that
# already hold law_direct_democracy.
te_collective_governance_country_pulse = {
	effect = {
		te_refresh_collective_governance_amendment = yes
	}
}
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `$PY -m unittest test_collective_governance -v`
Expected: all pass.

- [ ] **Step 6: Tab check and commit**

```bash
$PY scripts/format_paradox_tabs.py --check common/scripted_effects/collective_governance_effects.txt common/on_actions/extra_on_actions.txt
git add common/scripted_effects/collective_governance_effects.txt common/on_actions/extra_on_actions.txt test_collective_governance.py
git commit -F - <<'EOF'
Collective Governance: refresh the amendment from on_law_activated and monthly

te_refresh_collective_governance_amendment derives the wanted amendment from
current laws, removes any of the other four and adds the missing one, with
the ruler's interest group as sponsor. Runs after the law-consistency
cascade on on_law_activated, and monthly as a backstop and save migration.

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01M7W7KgW8hadKoaLqAVNeBf
EOF
```

---

### Task 4: The law

**Files:**
- Modify: `common/laws/extra_laws.txt` (the whole `law_direct_democracy` block, ~lines 3779–3875)
- Modify: `localization/english/te_laws_l_english.yml:45-46`
- Modify: `localization/english/te_concepts_l_english.yml` (append the six preview tooltips)
- Test: `test_collective_governance.py` (append `LawTests`)

**Interfaces:**
- Consumes: the triggers (Task 1), `te_refresh_collective_governance_amendment` (Task 3).
- Produces: loc keys `COLLECTIVE_GOVERNANCE_TT_POPULAR`, `_PARTY`, `_TECHNOCRATIC`, `_ANARCHIC`, `_PATRICIAN`, `COLLECTIVE_GOVERNANCE_TT_FOLLOWS_DOP`.

- [ ] **Step 1: Write the failing tests** — append to `test_collective_governance.py`:

```python
LAWS = _path("common", "laws", "extra_laws.txt")

BASE_MODIFIERS = {
    "country_legitimacy_govt_size_add": "1",
    "country_authority_mult": "-0.15",
    "country_law_enactment_speed_mult": "-0.1",
    "country_legitimacy_ideological_incoherence_mult": "-0.3",
}


class LawTests(unittest.TestCase):
    def setUp(self):
        self.body = _block(_read(LAWS), "law_direct_democracy")

    def test_prerequisites_are_exactly_the_expressions(self):
        laws = set(_inner(self.body, "unlocking_laws").split())
        self.assertEqual(laws, set().union(*(e.dop_laws for e in EXPRESSIONS)))
        for excluded in ("law_autocracy", "law_bakufu", "law_neo_absolutism",
                         "law_algorithmic_governance", "law_elder_council"):
            self.assertNotIn(excluded, laws)

    def test_tech_gate(self):
        self.assertEqual(_inner(self.body, "unlocking_technologies").split(), ["political_agitation"])

    def test_can_enact(self):
        self.assertEqual(_norm(_inner(self.body, "can_enact")),
                         "NOT = { has_government_type = gov_chartered_company }")

    def test_base_modifiers(self):
        self.assertEqual(_modifiers(_inner(self.body, "modifier")), BASE_MODIFIERS)

    def test_preview_names_each_expression(self):
        body = _norm(_inner(self.body, "on_enact"))
        for e in EXPRESSIONS:
            with self.subTest(trigger=e.trigger):
                self.assertIn(f"limit = {{ {e.trigger} = yes }} custom_tooltip = {e.tooltip}", body)
        self.assertTrue(body.endswith("custom_tooltip = COLLECTIVE_GOVERNANCE_TT_FOLLOWS_DOP"))

    def test_activation_attaches_hidden(self):
        self.assertEqual(_norm(_inner(self.body, "on_activate")),
                         "hidden_effect = { te_refresh_collective_governance_amendment = yes }")

    def test_ai(self):
        will = _norm(_inner(self.body, "ai_will_do"))
        self.assertIn("has_ideology = ideology:ideology_radical", will)
        self.assertIn("has_ideology = ideology:ideology_anarchist", will)
        self.assertNotIn("law_council_republic", _inner(self.body, "ai_impose_chance"))

    def test_loc(self):
        loc = _loc()
        self.assertEqual(loc["law_direct_democracy"], "Collective Governance")
        self.assertNotIn("participate directly", loc["law_direct_democracy_desc"])
        for key in [e.tooltip for e in EXPRESSIONS] + ["COLLECTIVE_GOVERNANCE_TT_FOLLOWS_DOP"]:
            with self.subTest(key=key):
                self.assertIn(key, loc)
```

- [ ] **Step 2: Run to verify failure**

Run: `$PY -m unittest test_collective_governance.LawTests -v`
Expected: every test FAILs or ERRORs (`on_enact not found`, prerequisites mismatch, and so on).

- [ ] **Step 3: Replace the law block.** Run this script. It replaces everything from `law_direct_democracy = {` up to the blank line before `law_neocolonialism = {`, and checks the old block's `can_impose` is carried over unchanged:

```bash
$PY - <<'PYEOF'
import re
P = "common/laws/extra_laws.txt"
with open(P, encoding="utf-8-sig", newline="") as f:
    text = f.read()
start = re.search(r"^law_direct_democracy = \{", text, re.M).start()
end = text.index("\nlaw_neocolonialism = {", start)
old = text[start:end]
assert "can_impose = {" in old and "mass_media" in old, "unexpected old block"
NEW = '''# Displayed as "Collective Governance": no individual holds supreme executive
# power. The key is historical (this law was Direct Democracy) and kept because
# renaming a law breaks saves. What the law means depends on Distribution of
# Power, expressed as one script-attached amendment per group
# (te_refresh_collective_governance_amendment, collective_governance_effects.txt).
# Spec: docs/superpowers/specs/2026-09-26-collective-governance-design.md
law_direct_democracy = {
	group = lawgroup_governance_principles
	icon = "gfx/interface/icons/law_icons/direct_democracy.dds"

	progressiveness = 50

	unlocking_laws = {
		law_landed_voting
		law_wealth_voting
		law_census_voting
		law_universal_suffrage
		law_single_party_state
		law_technocracy
		law_oligarchy
		law_organic_regulation
		law_anarchy
	}

	unlocking_technologies = {
		political_agitation
	}

	can_enact = {
		NOT = { has_government_type = gov_chartered_company }
	}

	can_impose = {
		OR = {
			AND = {
				is_in_same_power_bloc = scope:target_country
				AND = {
					modifier:country_can_impose_same_lawgroup_governance_principles_in_power_bloc_bool = yes
					has_law = scope:law
				}
			}
			can_impose_law_default = yes
		}
	}

	# Preview only: conditions read the laws in force before enactment
	# (vanilla's land-reform laws, law_state_led_language_reform).
	on_enact = {
		if = {
			limit = { collective_governance_is_popular = yes }
			custom_tooltip = COLLECTIVE_GOVERNANCE_TT_POPULAR
		}
		else_if = {
			limit = { collective_governance_is_party = yes }
			custom_tooltip = COLLECTIVE_GOVERNANCE_TT_PARTY
		}
		else_if = {
			limit = { collective_governance_is_technocratic = yes }
			custom_tooltip = COLLECTIVE_GOVERNANCE_TT_TECHNOCRATIC
		}
		else_if = {
			limit = { collective_governance_is_anarchic = yes }
			custom_tooltip = COLLECTIVE_GOVERNANCE_TT_ANARCHIC
		}
		else_if = {
			limit = { collective_governance_is_patrician = yes }
			custom_tooltip = COLLECTIVE_GOVERNANCE_TT_PATRICIAN
		}
		custom_tooltip = COLLECTIVE_GOVERNANCE_TT_FOLLOWS_DOP
	}

	# Fires however the law arrives (enactment or activate_law); hidden so
	# add_amendment adds no line of its own to the preview.
	on_activate = {
		hidden_effect = { te_refresh_collective_governance_amendment = yes }
	}

	# The "no head" identity. The Distribution of Power's own expression is the
	# amendment. No country_legitimacy_headofstate_add: the chair's interest
	# group earns nothing (Monarchy +20, Presidential Republic +10).
	modifier = {
		country_legitimacy_govt_size_add = 1
		country_authority_mult = -0.15
		country_law_enactment_speed_mult = -0.1
		country_legitimacy_ideological_incoherence_mult = -0.3
	}

	ai_will_do = {
		exists = ruler
		ruler = {
			OR = {
				has_ideology = ideology:ideology_radical
				has_ideology = ideology:ideology_anarchist
			}
		}
	}

	ai_enact_weight_modifier = {
		value = 10

		if = {
			limit = { ai_has_enact_weight_modifier_journal_entries = yes }
			add = 750
		}
	}

	# Same weight as before: the old Council Republic multiplier could never
	# fire (it required the imposer to lack the egalitarian agenda its own
	# limit demanded), so the 0.5 branch always ran.
	ai_impose_chance = {
		value = 0

		if = {
			limit = {
				has_law = law_type:law_direct_democracy
				has_strategy = ai_strategy_egalitarian_agenda
			}
			add = base_impose_law_weight
			multiply = 0.5
		}
	}
}
'''
old_can_impose = re.search(r"\tcan_impose = \{.*?\n\t\}\n", old, re.S).group(0)
assert old_can_impose in NEW, "can_impose changed; copy it verbatim"
text = text[:start] + NEW + text[end:]
with open(P, "w", encoding="utf-8-sig", newline="") as f:
    f.write(text)
print("replaced", old.count("\n"), "lines")
PYEOF
```
Expected: `replaced 96 lines` (or close to it). No assertion error.

- [ ] **Step 4: Update the law loc** — in `localization/english/te_laws_l_english.yml`, replace the two lines

```
 law_direct_democracy:0 "Direct Democracy"
 law_direct_democracy_desc:0 "A system of government where eligible citizens participate directly in decision-making processes, rather than through elected representatives."
```
with
```
 law_direct_democracy:0 "Collective Governance"
 law_direct_democracy_desc:0 "No one person holds supreme executive power. Authority rests with a body of equals: an assembly of voters, a party presidium, a college of bureaus, a federation of communes or a council of the powerful, depending on who holds power. Whoever chairs it is first among equals, not a ruler."
```

Then append the preview tooltips:
```bash
cat >> localization/english/te_concepts_l_english.yml <<'EOF'
 COLLECTIVE_GOVERNANCE_TT_POPULAR:0 "With a voting franchise, gains the #b Direct Democracy#! amendment: a law can only be enacted with a political movement behind it, movements draw more support, and enacted laws radicalize their opponents less."
 COLLECTIVE_GOVERNANCE_TT_PARTY:0 "Under Single-Party State, gains the #b Collective Leadership#! amendment: the party's presidium governs together, and there is no single leader for a coup to remove."
 COLLECTIVE_GOVERNANCE_TT_TECHNOCRATIC:0 "Under Technocracy, gains the #b Collegial Administration#! amendment: the institutions govern as equal bureaus and change size faster, but decrees cost more with no one executive to issue them."
 COLLECTIVE_GOVERNANCE_TT_ANARCHIC:0 "Under Anarchy, gains the #b Free Federation#! amendment: delegates act only on mandates from below, so a law can only be enacted with a political movement behind it."
 COLLECTIVE_GOVERNANCE_TT_PATRICIAN:0 "Under an oligarchy, gains the #b Patrician Council#! amendment: the powerful govern as peers, and aristocrats and capitalists gain political strength."
 COLLECTIVE_GOVERNANCE_TT_FOLLOWS_DOP:0 "The amendment changes whenever the Distribution of Power does."
EOF
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `$PY -m unittest test_collective_governance -v`
Expected: all pass.

- [ ] **Step 6: Tab check and commit**

```bash
$PY scripts/format_paradox_tabs.py --check common/laws/extra_laws.txt
git add common/laws/extra_laws.txt localization/english/te_laws_l_english.yml localization/english/te_concepts_l_english.yml test_collective_governance.py
git commit -F - <<'EOF'
Collective Governance: the law (still law_direct_democracy)

Displayed as Collective Governance. Allows the voting laws, Single-Party
State, Technocracy, Oligarchy/Organic Regulation and Anarchy; unlocks with
political_agitation (era 4, was mass_media, era 6). The law carries only the
"no head" base; the referendum package moved to the Direct Democracy
amendment. on_enact names the amendment in the preview; on_activate attaches
it, hidden. AI: anarchist rulers too; ai_impose_chance simplified to the
weight it always produced.

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01M7W7KgW8hadKoaLqAVNeBf
EOF
```

---

### Task 5: Government types

**Files:**
- Modify: `common/government_types/timeline_extended_governments.txt` (the first three blocks, lines 1–60)
- Modify: `localization/english/te_concepts_l_english.yml` (lines ~1182–1185, plus appended keys)
- Modify: `localization/english/te_miscellaneous_l_english.yml` (lines ~2047–2048)
- Test: `test_collective_governance.py` (append `GovernmentTypeTests`)

**Interfaces:**
- Consumes: the triggers (Task 1).
- Produces: government types `gov_collective_noble_commonwealth`, `gov_collective_patrician_council`, `gov_collective_administration`, `gov_collective_free_federation`, `gov_collective_governance`; loc `RULER_TITLE_MARSHAL`, `RULER_TITLE_SYNDIC`, `RULER_TITLE_COORDINATOR`.

- [ ] **Step 1: Write the failing tests** — append to `test_collective_governance.py`:

```python
GOVERNMENTS = _path("common", "government_types", "timeline_extended_governments.txt")

Gov = namedtuple("Gov", "key trigger extra_law name male female transfer")

# Resolution order: the engine takes the first government type whose possible
# holds, so the more specific come first and the catch-all is last (spec §4).
GOV_TYPES = [
    Gov("gov_collective_noble_commonwealth", "collective_governance_is_patrician", "law_feudal_contracts",
        "Noble Commonwealth", "RULER_TITLE_MARSHAL", "RULER_TITLE_MARSHAL", "parliamentary_elective"),
    Gov("gov_collective_patrician_council", "collective_governance_is_patrician", None,
        "Patrician Council", "RULER_TITLE_SYNDIC", "RULER_TITLE_SYNDIC", "parliamentary_elective"),
    Gov("gov_direct_democracy_single_party_state", "collective_governance_is_party", None,
        "Collective Leadership", "RULER_CHAIRMAN", "RULER_CHAIRWOMAN", "presidential_elective"),
    Gov("gov_collective_administration", "collective_governance_is_technocratic", None,
        "Collegial Administration", "RULER_TITLE_COORDINATOR", "RULER_TITLE_COORDINATOR", "parliamentary_elective"),
    Gov("gov_collective_free_federation", "collective_governance_is_anarchic", None,
        "Free Federation", "RULER_REPRESENTATIVE", "RULER_REPRESENTATIVE", "parliamentary_elective"),
    Gov("gov_direct_democracy", "collective_governance_is_popular", None,
        "Direct Democracy", "RULER_TITLE_SPEAKER", "RULER_TITLE_SPEAKER", "parliamentary_elective"),
    Gov("gov_collective_governance", None, None,
        "Collective Governance", "RULER_TITLE_SPEAKER", "RULER_TITLE_SPEAKER", "parliamentary_elective"),
]


class GovernmentTypeTests(unittest.TestCase):
    def setUp(self):
        self.text = _read(GOVERNMENTS)

    def test_resolution_order(self):
        keyed = [n for n in _top_level_names(self.text)
                 if "law_type:law_direct_democracy" in _inner(_block(self.text, n), "possible")]
        self.assertEqual(keyed, [g.key for g in GOV_TYPES])

    def test_possible(self):
        for g in GOV_TYPES:
            with self.subTest(gov=g.key):
                expected = ["has_law = law_type:law_direct_democracy"]
                if g.trigger:
                    expected.append(f"{g.trigger} = yes")
                if g.extra_law:
                    expected.append(f"has_law = law_type:{g.extra_law}")
                self.assertEqual(_norm(_inner(_block(self.text, g.key), "possible")), " ".join(expected))

    def test_every_expression_has_a_government(self):
        self.assertEqual({g.trigger for g in GOV_TYPES if g.trigger}, {e.trigger for e in EXPRESSIONS})

    def test_rulers_and_succession(self):
        for g in GOV_TYPES:
            with self.subTest(gov=g.key):
                body = _block(self.text, g.key)
                self.assertRegex(body, rf'(?<!fe)male_ruler\s*=\s*"{g.male}"')
                self.assertRegex(body, rf'female_ruler\s*=\s*"{g.female}"')
                self.assertRegex(body, rf"transfer_of_power\s*=\s*{g.transfer}\b")
                self.assertIn(f"change_to_{g.transfer} = yes", body)
                self.assertIn(f"post_change_to_{g.transfer} = yes", body)
                self.assertRegex(body, r"new_leader_on_reform_government\s*=\s*yes")

    def test_plebiscitary_autocracy_is_gone(self):
        self.assertNotIn("gov_direct_democracy_autocracy", self.text)
        loc = _loc()
        self.assertNotIn("gov_direct_democracy_autocracy", loc)
        self.assertNotIn("gov_direct_democracy_autocracy_desc", loc)

    def test_loc(self):
        loc = _loc()
        for g in GOV_TYPES:
            with self.subTest(gov=g.key):
                self.assertEqual(loc.get(g.key), g.name)
                self.assertIn(g.key + "_desc", loc)
        for title in ("RULER_TITLE_MARSHAL", "RULER_TITLE_SYNDIC", "RULER_TITLE_COORDINATOR"):
            self.assertIn(title, loc)
```

- [ ] **Step 2: Run to verify failure**

Run: `$PY -m unittest test_collective_governance.GovernmentTypeTests -v`
Expected: FAILs/ERRORs (order mismatch, `gov_collective_noble_commonwealth not found`, the autocracy type still present).

- [ ] **Step 3: Replace the three Direct Democracy government types** with the seven below. The script replaces everything before `gov_corporate_state_democracy = {`:

```bash
$PY - <<'PYEOF'
P = "common/government_types/timeline_extended_governments.txt"
with open(P, encoding="utf-8-sig", newline="") as f:
    text = f.read()
cut = text.index("gov_corporate_state_democracy = {")
assert text[:cut].count("gov_direct_democracy") == 3, "unexpected head of file"
NEW = '''# Collective Governance (law_direct_democracy): one government type per
# Distribution of Power group. The engine takes the first government type whose
# possible holds, so the more specific come first and gov_collective_governance
# is the catch-all (it shows only while a country holds the law under a
# Distribution of Power the law does not allow, until the consistency cascade
# replaces it). The two gov_direct_democracy* keys are kept for saves.
# Spec: docs/superpowers/specs/2026-09-26-collective-governance-design.md

gov_collective_noble_commonwealth = {
	transfer_of_power = parliamentary_elective
	new_leader_on_reform_government = yes

	male_ruler = "RULER_TITLE_MARSHAL"
	female_ruler = "RULER_TITLE_MARSHAL"

	possible = {
		has_law = law_type:law_direct_democracy
		collective_governance_is_patrician = yes
		has_law = law_type:law_feudal_contracts
	}

	on_government_type_change = {
		change_to_parliamentary_elective = yes
	}
	on_post_government_type_change = {
		post_change_to_parliamentary_elective = yes
	}
}

gov_collective_patrician_council = {
	transfer_of_power = parliamentary_elective
	new_leader_on_reform_government = yes

	male_ruler = "RULER_TITLE_SYNDIC"
	female_ruler = "RULER_TITLE_SYNDIC"

	possible = {
		has_law = law_type:law_direct_democracy
		collective_governance_is_patrician = yes
	}

	on_government_type_change = {
		change_to_parliamentary_elective = yes
	}
	on_post_government_type_change = {
		post_change_to_parliamentary_elective = yes
	}
}

gov_direct_democracy_single_party_state = {
	transfer_of_power = presidential_elective
	new_leader_on_reform_government = yes

	male_ruler = "RULER_CHAIRMAN"
	female_ruler = "RULER_CHAIRWOMAN"

	possible = {
		has_law = law_type:law_direct_democracy
		collective_governance_is_party = yes
	}

	on_government_type_change = {
		change_to_presidential_elective = yes
	}
	on_post_government_type_change = {
		post_change_to_presidential_elective = yes
	}
}

gov_collective_administration = {
	transfer_of_power = parliamentary_elective
	new_leader_on_reform_government = yes

	male_ruler = "RULER_TITLE_COORDINATOR"
	female_ruler = "RULER_TITLE_COORDINATOR"

	possible = {
		has_law = law_type:law_direct_democracy
		collective_governance_is_technocratic = yes
	}

	on_government_type_change = {
		change_to_parliamentary_elective = yes
	}
	on_post_government_type_change = {
		post_change_to_parliamentary_elective = yes
	}
}

gov_collective_free_federation = {
	transfer_of_power = parliamentary_elective
	new_leader_on_reform_government = yes

	male_ruler = "RULER_REPRESENTATIVE"
	female_ruler = "RULER_REPRESENTATIVE"

	possible = {
		has_law = law_type:law_direct_democracy
		collective_governance_is_anarchic = yes
	}

	on_government_type_change = {
		change_to_parliamentary_elective = yes
	}
	on_post_government_type_change = {
		post_change_to_parliamentary_elective = yes
	}
}

gov_direct_democracy = {
	transfer_of_power = parliamentary_elective
	new_leader_on_reform_government = yes

	male_ruler = "RULER_TITLE_SPEAKER"
	female_ruler = "RULER_TITLE_SPEAKER"

	possible = {
		has_law = law_type:law_direct_democracy
		collective_governance_is_popular = yes
	}

	on_government_type_change = {
		change_to_parliamentary_elective = yes
	}
	on_post_government_type_change = {
		post_change_to_parliamentary_elective = yes
	}
}

gov_collective_governance = {
	transfer_of_power = parliamentary_elective
	new_leader_on_reform_government = yes

	male_ruler = "RULER_TITLE_SPEAKER"
	female_ruler = "RULER_TITLE_SPEAKER"

	possible = {
		has_law = law_type:law_direct_democracy
	}

	on_government_type_change = {
		change_to_parliamentary_elective = yes
	}
	on_post_government_type_change = {
		post_change_to_parliamentary_elective = yes
	}
}

'''
with open(P, "w", encoding="utf-8-sig", newline="") as f:
    f.write(NEW + text[cut:])
PYEOF
```

- [ ] **Step 4: Update the government-type loc.**

Rewrite the existing keys by name. In `te_concepts_l_english.yml`, delete `gov_direct_democracy_autocracy_desc` and rewrite `gov_direct_democracy_desc` and `gov_direct_democracy_single_party_state_desc`. In `te_miscellaneous_l_english.yml`, delete `gov_direct_democracy_autocracy` and rename `gov_direct_democracy_single_party_state`. `gov_direct_democracy` ("Direct Democracy") stays as it is:

```bash
$PY - <<'PYEOF'
import re
EDITS = {
    "localization/english/te_concepts_l_english.yml": {
        "gov_direct_democracy_autocracy_desc": None,
        "gov_direct_democracy_desc": "Citizens with the vote decide policy themselves, in assemblies and referendums. The Speaker who convenes them holds no power of their own.",
        "gov_direct_democracy_single_party_state_desc": "The party's presidium governs together. Its chair speaks for it, but no single leader decides alone.",
    },
    "localization/english/te_miscellaneous_l_english.yml": {
        "gov_direct_democracy_autocracy": None,
        "gov_direct_democracy_single_party_state": "Collective Leadership",
    },
}
for path, edits in EDITS.items():
    with open(path, encoding="utf-8-sig", newline="") as f:
        lines = f.read().split("\n")
    for key, text in edits.items():
        idx = [i for i, l in enumerate(lines) if re.match(r"\s*%s:\d*\s" % re.escape(key), l)]
        assert len(idx) == 1, (path, key, idx)
        if text is None:
            del lines[idx[0]]
        else:
            lines[idx[0]] = ' %s:0 "%s"' % (key, text)
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        f.write("\n".join(lines))
print("ok")
PYEOF
```
Expected: `ok`.

Then append:
```bash
cat >> localization/english/te_concepts_l_english.yml <<'EOF'
 gov_collective_noble_commonwealth:0 "Noble Commonwealth"
 gov_collective_noble_commonwealth_desc:0 "The great houses govern as peers, each ruling its own lands, and decide the realm's affairs together in a diet whose Marshal only presides."
 gov_collective_patrician_council:0 "Patrician Council"
 gov_collective_patrician_council_desc:0 "A closed council of the powerful governs as equals. Its Syndic presides over its sittings but commands no one."
 gov_collective_administration:0 "Collegial Administration"
 gov_collective_administration_desc:0 "The state's bureaus govern as peers, each in its own field. A Coordinator keeps them in step; none of them answers to a chief executive."
 gov_collective_free_federation:0 "Free Federation"
 gov_collective_free_federation_desc:0 "Communes and associations govern themselves and send delegates, bound by their mandates, to coordinate what they share."
 gov_collective_governance:0 "Collective Governance"
 gov_collective_governance_desc:0 "No single person holds supreme executive power. A body of equals governs, and whoever chairs it is first among equals."
 RULER_TITLE_MARSHAL:0 "Marshal"
 RULER_TITLE_SYNDIC:0 "Syndic"
 RULER_TITLE_COORDINATOR:0 "Coordinator"
EOF
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `$PY -m unittest test_collective_governance -v`
Expected: all pass.

- [ ] **Step 6: Tab check and commit**

```bash
$PY scripts/format_paradox_tabs.py --check common/government_types/timeline_extended_governments.txt
git add common/government_types/timeline_extended_governments.txt localization/english/te_concepts_l_english.yml localization/english/te_miscellaneous_l_english.yml test_collective_governance.py
git commit -F - <<'EOF'
Collective Governance: a government type per Distribution of Power

Noble Commonwealth (Oligarchy + Feudal Contracts), Patrician Council,
Collective Leadership (was Managed Democracy), Collegial Administration,
Free Federation, Direct Democracy, and a Collective Governance catch-all,
most specific first. Removes Plebiscitary Autocracy: it required no voting
franchise, so it could never match before, and would have caught every
Technocracy, Oligarchy and Anarchy combination after.

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01M7W7KgW8hadKoaLqAVNeBf
EOF
```

---

### Task 6: Sites that read the law as "a democracy"

**Files:**
- Modify: `common/scripted_effects/cultural_hegemony_effects.txt:374` (liberal-democratic branch of `ch_set_political_model`)
- Modify: `events/extra_law_events.txt` (triggers of `.24`, `.60`, `.84`)
- Modify: `events/modern_election_events.txt:3137` (`modern_election_events.33` option a AI weight)
- Modify: `localization/english/te_events_l_english.yml:1544` (`extra_law_events.84.d`)
- Test: `test_collective_governance.py` (append `CallSiteTests`)

**Interfaces:**
- Consumes: `collective_governance_is_popular` (Task 1).

- [ ] **Step 1: Write the failing tests** — append to `test_collective_governance.py`:

```python
CH_EFFECTS = _path("common", "scripted_effects", "cultural_hegemony_effects.txt")
LAW_EVENTS = _path("events", "extra_law_events.txt")
ELECTION_EVENTS = _path("events", "modern_election_events.txt")


def _between(text, start_marker, end_marker):
    start = text.index(start_marker)
    return text[start:text.index(end_marker, start)]


class CallSiteTests(unittest.TestCase):
    def test_liberal_democratic_model_needs_a_franchise(self):
        branch = _norm(_between(_raw(CH_EFFECTS), "# Liberal / Progressive democratic", "# Republican:"))
        self.assertIn(
            "AND = { has_law = law_type:law_direct_democracy collective_governance_is_popular = yes }", branch)
        self.assertNotIn("has_law_or_variant = law_type:law_direct_democracy", branch)

    def test_republican_model_is_unchanged(self):
        # An oligarchic council landing in Republican is historically fair (spec §5).
        branch = _norm(_between(_raw(CH_EFFECTS), "# Republican:", "# Mixed / Other"))
        self.assertIn("has_law_or_variant = law_type:law_direct_democracy", branch)

    def test_referendum_events_need_a_franchise(self):
        text = _read(LAW_EVENTS)
        for event in ("extra_law_events.24", "extra_law_events.60", "extra_law_events.84"):
            with self.subTest(event=event):
                trigger = _norm(_inner(_block(text, event), "trigger"))
                self.assertIn("is_enacting_law = law_type:law_direct_democracy "
                              "collective_governance_is_popular = yes", trigger)

    def test_every_enactment_event_for_the_law_is_gated(self):
        text = _read(LAW_EVENTS)
        enacting = re.findall(r"is_enacting_law = law_type:law_direct_democracy", text)
        gated = re.findall(
            r"is_enacting_law = law_type:law_direct_democracy\s+collective_governance_is_popular = yes", text)
        self.assertEqual(len(enacting), len(gated))

    def test_neural_democracy_weight_needs_a_franchise(self):
        body = _norm(_block(_read(ELECTION_EVENTS), "modern_election_events.33"))
        self.assertIn("trigger = { has_law = law_type:law_direct_democracy "
                      "collective_governance_is_popular = yes } add = 5", body)

    def test_instrument_question_does_not_call_the_law_direct_democracy(self):
        self.assertNotIn("direct-democracy bill", _loc()["extra_law_events.84.d"])
```

- [ ] **Step 2: Run to verify failure**

Run: `$PY -m unittest test_collective_governance.CallSiteTests -v`
Expected: every test except `test_republican_model_is_unchanged` FAILs.

- [ ] **Step 3: Cultural hegemony** — in `common/scripted_effects/cultural_hegemony_effects.txt`, replace (unique: the Republican branch lists the republics first)

```
				has_law_or_variant = law_type:law_universal_suffrage
				has_law_or_variant = law_type:law_direct_democracy
```
with
```
				has_law_or_variant = law_type:law_universal_suffrage
				AND = {
					has_law = law_type:law_direct_democracy
					collective_governance_is_popular = yes
				}
```

- [ ] **Step 4: The three enactment events**

```bash
sed -i 's/^\(\t*\)is_enacting_law = law_type:law_direct_democracy$/&\n\1collective_governance_is_popular = yes/' events/extra_law_events.txt
grep -c "collective_governance_is_popular = yes" events/extra_law_events.txt
```
Expected: `3`.

- [ ] **Step 5: The election event** — in `events/modern_election_events.txt`, replace

```
			modifier = { trigger = { has_law = law_type:law_direct_democracy } add = 5 }
```
with
```
			modifier = { trigger = { has_law = law_type:law_direct_democracy collective_governance_is_popular = yes } add = 5 }
```

- [ ] **Step 6: Reword `.84.d`** — in `localization/english/te_events_l_english.yml`, replace

```
 extra_law_events.84.d:0 "The direct-democracy bill [SCOPE.sLaw('current_law_scope').GetName] reaches its instrument question. Populists want direct citizen voting on legislation; reformers want sortition-based deliberative chambers. The design choice defines what 'democracy' will mean here."
```
with
```
 extra_law_events.84.d:0 "The [SCOPE.sLaw('current_law_scope').GetName] bill reaches its instrument question: how will the voters govern? Populists want direct citizen voting on legislation; reformers want sortition-based deliberative chambers. The design choice defines what 'democracy' will mean here."
```

- [ ] **Step 7: Run the tests to verify they pass**

Run: `$PY -m unittest test_collective_governance -v`
Expected: all pass.

- [ ] **Step 8: Tab check and commit**

```bash
$PY scripts/format_paradox_tabs.py --check common/scripted_effects/cultural_hegemony_effects.txt events/extra_law_events.txt events/modern_election_events.txt
git add common/scripted_effects/cultural_hegemony_effects.txt events/extra_law_events.txt events/modern_election_events.txt localization/english/te_events_l_english.yml test_collective_governance.py
git commit -F - <<'EOF'
Collective Governance: keep "democracy" readings to voting countries

The liberal-democratic cultural-hegemony model, the three referendum-
flavoured enactment events (.24/.60/.84) and the neural-democracy AI weight
now also require collective_governance_is_popular, so a patrician council or
a bureau state no longer counts as a democracy. The Republican model is
unchanged. .84.d no longer calls the law "the direct-democracy bill".

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01M7W7KgW8hadKoaLqAVNeBf
EOF
```

---

### Task 7: Ideology stances

**Files:**
- Modify: `ideology_modifications.py` (8 entries)
- Modify: `common/ideologies/extra_ideologies.txt` (2 entries)
- Regenerate: `common/ideologies/modified.txt` (via `apply_ideologies.py`)
- Test: `test_collective_governance.py` (append `IdeologyTests`)

**Interfaces:** none new.

- [ ] **Step 1: Write the failing tests** — append to `test_collective_governance.py`, and add `import ideology_modifications` below the existing imports at the top of the file:

```python
EXTRA_IDEOLOGIES = _path("common", "ideologies", "extra_ideologies.txt")
MODIFIED_IDEOLOGIES = _path("common", "ideologies", "modified.txt")

# Spec §6: stances re-read against "no single head". Changes only.
STANCE_CHANGES = {
    "ideology_anarchist": "strongly_approve",
    "ideology_anarchist_movement": "strongly_approve",
    "ideology_bonapartist": "strongly_disapprove",
    "ideology_bonapartist_movement": "strongly_disapprove",
    "ideology_caudillismo": "strongly_disapprove",
    "ideology_fascist_movement": "strongly_disapprove",
    "ideology_absolutist_movement": "strongly_disapprove",
    "ideology_plutocratic": "neutral",
}
CUSTOM_RELIGION_CHANGES = {
    "ideology_custom_religion_aristocratic_governance": "neutral",
    "ideology_custom_religion_technocratic_governance": "neutral",
}


class IdeologyTests(unittest.TestCase):
    def test_vanilla_ideology_stances(self):
        for ideology, stance in STANCE_CHANGES.items():
            with self.subTest(ideology=ideology):
                pairs = dict(ideology_modifications.modifications[ideology]["lawgroup_governance_principles"])
                self.assertEqual(pairs["law_direct_democracy"], stance)

    def test_generated_file_is_current(self):
        text = _read(MODIFIED_IDEOLOGIES)
        for ideology, stance in STANCE_CHANGES.items():
            with self.subTest(ideology=ideology):
                self.assertRegex(_block(text, ideology), rf"law_direct_democracy\s*=\s*{stance}\b")

    def test_custom_religion_stances(self):
        text = _read(EXTRA_IDEOLOGIES)
        for ideology, stance in CUSTOM_RELIGION_CHANGES.items():
            with self.subTest(ideology=ideology):
                self.assertRegex(_block(text, ideology), rf"law_direct_democracy\s*=\s*{stance}\b")
```

- [ ] **Step 2: Run to verify failure**

Run: `$PY -m unittest test_collective_governance.IdeologyTests -v`
Expected: 3 FAILs (old stances, for example `'approve' != 'strongly_approve'`).

- [ ] **Step 3: Edit the stances.** Each ideology's own entry is changed by locating its block first, because the same line text repeats across ideologies:

```bash
$PY - <<'PYEOF'
import re

PY_FILE = "ideology_modifications.py"
CHANGES = {  # ideology: (old, new)
    "ideology_anarchist": ("approve", "strongly_approve"),
    "ideology_anarchist_movement": ("approve", "strongly_approve"),
    "ideology_bonapartist": ("disapprove", "strongly_disapprove"),
    "ideology_bonapartist_movement": ("disapprove", "strongly_disapprove"),
    "ideology_caudillismo": ("disapprove", "strongly_disapprove"),
    "ideology_fascist_movement": ("disapprove", "strongly_disapprove"),
    "ideology_absolutist_movement": ("disapprove", "strongly_disapprove"),
    "ideology_plutocratic": ("disapprove", "neutral"),
}
with open(PY_FILE, encoding="utf-8") as f:
    lines = f.read().split("\n")
for ideology, (old, new) in CHANGES.items():
    start = next(i for i, l in enumerate(lines) if re.match(r'\s*"%s": \{' % ideology, l))
    for i in range(start + 1, len(lines)):
        if re.match(r'\s*"ideology_\w+": \{', lines[i]):
            raise SystemExit(f"{ideology}: no law_direct_democracy entry")
        if '("law_direct_democracy", ' in lines[i] and not lines[i].lstrip().startswith("#"):
            assert f'("law_direct_democracy", "{old}")' in lines[i], (ideology, lines[i])
            lines[i] = lines[i].replace(f'"{old}"', f'"{new}"')
            break
with open(PY_FILE, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

EX = "common/ideologies/extra_ideologies.txt"
with open(EX, encoding="utf-8-sig", newline="") as f:
    text = f.read()
for ideology in ("ideology_custom_religion_aristocratic_governance",
                 "ideology_custom_religion_technocratic_governance"):
    block = re.search(r"^%s = \{" % ideology, text, re.M)
    hit = re.compile(r"(law_direct_democracy = )disapprove\b").search(text, block.end())
    nxt = re.compile(r"^\w+ = \{", re.M).search(text, block.end())
    assert hit and (nxt is None or hit.start() < nxt.start()), ideology
    text = text[:hit.start()] + hit.group(1) + "neutral" + text[hit.end():]
with open(EX, "w", encoding="utf-8-sig", newline="") as f:
    f.write(text)
print("ok")
PYEOF
git diff --stat ideology_modifications.py common/ideologies/extra_ideologies.txt
```
Expected: `ok`; `ideology_modifications.py | 16 ++++++++--------`, `extra_ideologies.txt | 4 ++--`.

- [ ] **Step 4: Regenerate `modified.txt`**

```bash
$PY apply_ideologies.py && git status --short && git diff --stat common/ideologies/modified.txt
git diff -U0 common/ideologies/modified.txt | grep '^[-+][^-+]' | grep -v law_direct_democracy
```
Expected: `git status` lists only the three ideology files. `modified.txt | 16 ++++++++--------`. The last command prints **nothing**. If it prints anything, the install's vanilla has drifted from the repo's. In that case, restore with `git checkout -- common/ideologies/modified.txt`, stop, and report; don't commit drift.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `$PY -m unittest test_collective_governance -v`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add ideology_modifications.py common/ideologies/extra_ideologies.txt common/ideologies/modified.txt test_collective_governance.py
git commit -F - <<'EOF'
Collective Governance: ideology stances re-read against "no single head"

Anarchists strongly approve; Bonapartist, Caudillismo, fascist and absolutist
movements strongly disapprove (built on one man); plutocratic and the
aristocratic/technocratic custom-religion governance ideologies become
neutral, since a council of the wealthy, nobles or experts now qualifies.
modified.txt regenerated by apply_ideologies.py.

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01M7W7KgW8hadKoaLqAVNeBf
EOF
```

---

### Task 8: Regenerate, reload-check, and read the cascade

**Files:**
- Regenerate: `common/scripted_effects/extra_law_consistency_generated.txt` (`gen_law_consistency.py`)
- Regenerate: `localization/english/*.yml` placement (`organize_loc.py`)
- Create (untracked, never staged): `PR_BODY.md` at the worktree root

**Interfaces:** none new.

- [ ] **Step 1: Regenerate the consistency cascade**

```bash
$PY gen_law_consistency.py && git status --short
```
Expected: only `common/scripted_effects/extra_law_consistency_generated.txt` modified.

- [ ] **Step 2: Summarize which governance cascades changed**

```bash
$PY - <<'PYEOF' | tee "$(git rev-parse --git-dir)/cg_cascade.txt"
import re, subprocess
F = "common/scripted_effects/extra_law_consistency_generated.txt"
def sections(text):
    body = text.split("te_fix_inconsistent_lawgroup_governance_principles = {", 1)[1]
    body = body.split("\nte_fix_inconsistent_", 1)[0]
    out = {}
    for m in re.finditer(r"# Active: (\w+).*?(?=# Active: |\Z)", body, re.S):
        out[m.group(1)] = re.findall(r"activate_law = law_type:(\w+)", m.group(0))
    return out
base = subprocess.run(["git", "merge-base", "HEAD", "origin/main"], capture_output=True, text=True).stdout.strip()
old = sections(subprocess.run(["git", "show", f"{base}:{F}"], capture_output=True, text=True).stdout)
with open(F, encoding="utf-8-sig") as f:
    new = sections(f.read())
for law in sorted(set(old) | set(new)):
    if old.get(law) != new.get(law):
        print(f"{law}\n  before: {old.get(law)}\n  after:  {new.get(law)}")
print("other lawgroups changed:",
      subprocess.run(["git", "diff", "--stat", base, "--", F], capture_output=True, text=True).stdout.strip())
PYEOF
```
Read the output. For each active governance principle, it shows the replacement order before and after. Note every place `law_direct_democracy` now appears earlier than it did, or appears for the first time. That list goes into `PR_BODY.md` for the owner (spec §8), in plain words: "a Monarchy made invalid by Anarchy now falls to Collective Governance when …". If any lawgroup *other than* governance principles changed, stop and investigate: only governance cascades should move.

- [ ] **Step 3: Commit the regenerated cascade**

```bash
git add common/scripted_effects/extra_law_consistency_generated.txt
git commit -F - <<'EOF'
Regenerate the law-consistency cascade for Collective Governance

gen_law_consistency.py output after law_direct_democracy's wider
prerequisites, era-4 tech and stance changes.

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01M7W7KgW8hadKoaLqAVNeBf
EOF
```

- [ ] **Step 4: File the loc**

```bash
$PY organize_loc.py && git diff --stat localization/
grep -n "collective\|COLLECTIVE_GOVERNANCE\|gov_direct_democracy\|RULER_TITLE_\(MARSHAL\|SYNDIC\|COORDINATOR\)" localization/english/te_unused_l_english.yml
```
Expected: the diff moves only this branch's keys: the appended keys land in their category sections, and `gov_direct_democracy_single_party_state` moves from `te_miscellaneous` to `te_concepts`. The `grep` prints **nothing**. A hit means organize_loc thinks a live key is unused; fix the detection, not the file (memory: te_unused is an organize_loc output). Then:
```bash
$PY -m unittest test_collective_governance test_organize_loc -v
git add localization/english/
git commit -F - <<'EOF'
organize_loc: file the Collective Governance loc

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01M7W7KgW8hadKoaLqAVNeBf
EOF
```

- [ ] **Step 5: Reload-check on a second server (port 8951).** Start it with the Bash tool's `run_in_background` (not `&`):

```bash
cd /home/jakef/src/Vic3TE-collective-governance && VIC3_SKIP_DIGESTS_FETCH=1 /home/jakef/src/Vic3TimelineExtended/.venv/bin/python -c "import mod_state_server as m; m.PORT=8951; m.main()"
```
Wait until `curl -s http://127.0.0.1:8951/status` answers. Then:
```bash
export CG_OUT="$(git rev-parse --git-dir)/cg_reload.json"
curl -s -X POST http://127.0.0.1:8951/reload > "$CG_OUT"
$PY - <<'PYEOF'
import json, os, re
d = json.load(open(os.environ["CG_OUT"]))
pat = re.compile(r"collective|direct_democracy|COLLECTIVE_GOVERNANCE|RULER_TITLE_(MARSHAL|SYNDIC|COORDINATOR)|te_cg_", re.I)
hits = [w for w in d.get("warnings", []) if pat.search(json.dumps(w))]
print("parse_failures:", d.get("parse_failures"))
print("generators_wrote_files:", d.get("generators_wrote_files"))
print("reparsed_after_generators:", d.get("reparsed_after_generators"))
print(len(hits), "warnings mention this branch")
for w in hits:
    print(json.dumps(w)[:400])
PYEOF
git status --short
```
Expected: `parse_failures` empty, `0 warnings mention this branch`. `git status` shows only `docs/engine/*` (discard with `git checkout -- docs/engine/`) and no `common/` or `localization/` churn, because Steps 1–4 already ran those generators. Any warning that mentions this branch gets fixed in the task that owns the file, with its test re-run. Stop the server with `kill $(cat mod_state_server.pid)`.

- [ ] **Step 6: Validate the new modifier names.** The engine silently ignores an invalid one. `docs/engine/modifiers_summary.txt` is generated from the engine's own `modifiers.log`:

```bash
for m in country_coup_resistance_mult country_institution_size_change_speed_mult state_decree_cost_mult country_capitalists_pol_str_mult country_aristocrats_pol_str_mult country_legitimacy_govt_size_add country_authority_mult country_law_enactment_speed_mult; do
  printf "%-48s %s\n" $m "$(grep -cw -- "$m" docs/engine/modifiers_summary.txt)"
done
```
Expected: `1` on every line (`0` means the name is invalid).

---

### Task 9: Docs, full verification, PR body

**Files:**
- Modify: `docs/guides/scripting_best_practices.md:2536`
- Modify: `docs/systems/mod_systems.md` (new section after "## Temporary Amendments (Sunset Clauses)", before "## On-Actions Reference")
- Create (untracked, never staged): `PR_BODY.md`

- [ ] **Step 1: scripting_best_practices** — replace

```
Council Republic / mod-added `law_direct_democracy` / `law_neocameralism` / etc.
```
with
```
Council Republic / mod-added `law_direct_democracy` (displayed as Collective Governance) / `law_neocameralism` / etc.
```

- [ ] **Step 2: mod_systems.md** — insert before `## On-Actions Reference`:

```markdown
## Collective Governance (`law_direct_democracy`)

The governance principle `law_direct_democracy` is displayed as **Collective Governance**: no individual holds supreme executive power. The key is historical (the law was Direct Democracy) and kept because renaming a law breaks saves. Spec: `docs/superpowers/specs/2026-09-26-collective-governance-design.md`.

- **What it means depends on Distribution of Power**, expressed as one amendment on the law per group: the voting laws → *Direct Democracy* (the old referendum package: laws need a movement), Single-Party State → *Collective Leadership*, Technocracy → *Collegial Administration*, Anarchy → *Free Federation*, Oligarchy/Organic Regulation → *Patrician Council*. Autocracy can't hold the law. The law itself carries only the "no head" base (legitimacy from broad coalitions, less authority, slower enactment).
- **Script-attached, never negotiated.** `te_refresh_collective_governance_amendment` (`collective_governance_effects.txt`) keeps exactly the matching amendment, derived from current laws on every call: the law's `on_activate` (hidden), `on_law_activated` (after the consistency cascade) and the monthly country pulse. The amendments' `possible` and `can_repeal` ask the same triggers (`collective_governance_triggers.txt`), so the player can't repeal the one their Distribution of Power calls for.
- **Preview:** the law's `on_enact` names the amendment the current Distribution of Power will give (the language-reform pattern).
- **Government types** (`timeline_extended_governments.txt`) run most specific first, because the first match wins: Noble Commonwealth (Oligarchy + Feudal Contracts) before Patrician Council, with `gov_collective_governance` as the catch-all.
- **"Democracy" readings** (the liberal-democratic cultural-hegemony model, the referendum events `extra_law_events.24/.60/.84`) also require `collective_governance_is_popular`.
- **Adding a Distribution of Power law:** add it to its row of `EXPRESSIONS` in `test_collective_governance.py` (or add a row); the failures are the checklist.
```

- [ ] **Step 3: Full verification.** Run each command and confirm its result:

```bash
$PY -m compileall -q . && echo compile-ok
ls test_*.py | grep -v test_reload_post_load | sed 's/\.py$//' | xargs $PY -m unittest 2>&1 | tail -5
$PY -m ruff check .
$PY scripts/format_paradox_tabs.py --check common/scripted_triggers/collective_governance_triggers.txt common/scripted_effects/collective_governance_effects.txt common/amendments/extra_amendments.txt common/laws/extra_laws.txt common/government_types/timeline_extended_governments.txt common/on_actions/extra_on_actions.txt common/scripted_effects/cultural_hegemony_effects.txt events/extra_law_events.txt events/modern_election_events.txt common/ideologies/extra_ideologies.txt
$PY scripts/analysis/check_localization_files.py
$PY scripts/analysis/check_post_load_rosters.py
for a in duplicate_key any_limit loc_render orphaned_event iterator_limit modifier_multiplier_var event_image treaty_leverage_side event_context silent_variable prev_scope container_timed_variable je_immediate_reset; do $PY ${a}_audit.py --strict >/dev/null 2>&1 && echo "$a ok" || echo "$a FAIL"; done
$PY kill_character_audit.py --check >/dev/null && echo kill_character ok
$PY attitude_key_audit.py >/dev/null && echo attitude_key ok
```
Expected: `compile-ok`; the unit tests `OK`; ruff clean; the tab and loc checks exit 0; every audit `ok`. A failing unit test that also fails on `main` (for example `test_localization_accessor_audit.VanillaCleanTests`, a known version-drift failure) is pre-existing: note it in `PR_BODY.md`, don't fix it here. To confirm a failure is pre-existing, run the same test from `/home/jakef/src/Vic3TimelineExtended`.

- [ ] **Step 4: Commit the docs**

```bash
git add docs/guides/scripting_best_practices.md docs/systems/mod_systems.md
git commit -F - <<'EOF'
docs: Collective Governance in mod_systems and the lawgroup note

Co-Authored-By: Claude Opus 5.5 (1M context) <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01M7W7KgW8hadKoaLqAVNeBf
EOF
```

- [ ] **Step 5: Write `PR_BODY.md`** (worktree root, untracked; never `git add` it) with these sections:
  - **Summary**: two or three sentences from the spec's Context.
  - **What changes**: one bullet per Task 1–7 commit.
  - **The cascade** (owner review): the Task 8 Step 2 list in plain words.
  - **Balance**: the spec §1 balance notes (voting countries: small nerf; Single-Party State holders lose the referendum package).
  - **In-game checklist**: the spec §8 list, verbatim, as checkboxes. It includes items 1–8 from "Not verified".
  - **Pre-existing failures**, if Step 3 found any.
  - Footer:
    ```
    🤖 Generated with [Claude Code](https://claude.com/claude-code)

    https://claude.ai/code/session_01M7W7KgW8hadKoaLqAVNeBf
    ```

- [ ] **Step 6: Report.** Give `git log --oneline origin/main..HEAD`, the path of `PR_BODY.md` and the cascade summary. Leave pushing and opening the PR to the owner.
