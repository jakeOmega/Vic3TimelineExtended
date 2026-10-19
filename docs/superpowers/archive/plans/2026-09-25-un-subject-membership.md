# UN Membership for Subjects Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Base UN eligibility on diplomatic autonomy, suspend (not revoke) the representation of members that lose it, have a represented and paying overlord carry a suspended subject's seat, and make the journal entry say who actually takes part.

**Architecture:** Two live scripted triggers answer "may join / is represented" (`un_membership_eligible`) and "member without a voice" (`un_representation_suspended`). The suspension check rides beside every Article 19 (`un_dues_vote_suspended`) check, so the 196 lines that read `un_member_modifier` as "is a member" stay untouched. Membership benefits move off the membership marker onto `un_member_privileges_modifier`, so they can be conditional. A monthly pulse only announces transitions and strips what a suspended member may not hold.

**Tech Stack:** Paradox Clausewitz script (Victoria 3 mod), localization YAML, Python `unittest` static tests over the script files.

**Spec:** `docs/systems/un_redesign_design.md` §0.8 (rulings 1–13, the representative cases, existing saves, the in-game checklist).

## Global Constraints

- Work in the sparse worktree `~/src/vic3te-un-subject-membership` on `feat/un-subject-membership`. Never `POST /reload` from it (it regenerates the main checkout).
- Brace-based `.txt` files use tab indentation, and every changed `.txt`/`.yml` keeps its UTF-8 BOM. New files start with a BOM.
- The eligible subject types are exactly `subject_type_dominion`, `subject_type_protectorate` and `subject_type_tributary` (ruling 1). Do not reuse `te_mon_is_board_subject`.
- Loc strings use `#b X#!` / `#bold X#!` / `#R`/`#G`/`#v` styling, never `[b]`.
- Loc keys keep `un_` / `je_un_` / `notification_un_` / `concept_un_` prefixes; run `python3 organize_loc.py` after adding loc.
- `docs/systems/journal_entry_systems.md` is CRLF: edit with `Edit`, then confirm `grep -c $'\r$'` equals `wc -l`.
- Commits end with the session's `Co-Authored-By` / `Claude-Session` lines. Stage by path, never `git commit -a`.
- Python: run tests with the main checkout's venv, from the worktree: `/home/jakef/src/Vic3TimelineExtended/.venv/bin/python`.

## Review Focus

1. **A suspended member with a live ballot popup already in its notification list.** It must not be able to cast it: `un_vote_can_cast_ballot`, re-asserted by the cast effects, carries the check (Task 2 test).
2. **An overlord that is itself a suspended member (a colony with its own colonial subject).** It must not be billed for its subject: `un_dues_billed_to_overlord` requires the overlord to be represented (Task 1 test pins the trigger body; Task 3 test pins the dues values).
3. **A member joining on an existing save, before its first monthly pulse.** It must get the privileges at once: every `add_modifier = { name = un_member_modifier }` site also adds `un_member_privileges_modifier` (Task 4 test).
4. **A non-member puppet under a strong UN.** It must not carry the pariah modifiers, and it must not be a Supranational "outsider" case (Task 1 test).
5. **"N of M" with an annexed or suspended member.** N must never exceed M: both counts ask `un_membership_eligible` (Task 6 test).

---

### Task 1: Eligibility and representation triggers, and every way in

**Files:**
- Create: `common/scripted_triggers/un_membership_triggers.txt`
- Modify: `common/scripted_buttons/un_buttons.txt` (`un_join_button` `possible`)
- Modify: `common/scripted_effects/un_ladder_effects.txt` (`un_charter_invitations`)
- Modify: `events/un_events.txt` (`un_events.1` trigger, `un_events.10` option e trigger)
- Modify: `common/journal_entries/je_united_nations.txt` (treaty enrolment, pariah blocks)
- Modify: `common/scripted_triggers/un_teeth_triggers.txt` (`un_case_standing_applies`)
- Modify: `localization/english/te_miscellaneous_l_english.yml` (`un_membership_eligible_tt`)
- Test: `test_un_membership.py` (create)

**Interfaces:**
- Produces (scripted triggers, country scope): `un_membership_eligible`, `un_member_represented`, `un_representation_suspended`, `un_dues_billed_to_overlord`, `un_seat_carried`, `un_member_draws_benefits`.

- [ ] **Step 1: Write the failing test** — `test_un_membership.py` with the shared helpers below and the Task 1 test class.

```python
# -*- coding: utf-8 -*-
"""UN membership for subjects (docs/systems/un_redesign_design.md §0.8).

Diplomatic autonomy decides who may join and whose seat is active; a member
that loses it keeps its membership with its representation suspended. The
rule is carried by a few scripted triggers asked at many gates, and nothing in
the engine checks that a gate asks them. These tests do.
"""

import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))


def _path(*parts):
    return os.path.join(REPO, *parts)


def _read(path):
    with open(path, encoding="utf-8-sig") as f:
        return re.sub(r"#[^\n]*", "", f.read())


def _block(text, name):
    """The body of the top-level ``name = { ... }`` block."""
    m = re.search(r"^" + re.escape(name) + r"\s*=\s*\{", text, re.M)
    if m is None:
        raise AssertionError(f"{name} not found")
    depth = 0
    for i in range(m.end() - 1, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[m.end():i]
    raise AssertionError(f"{name} is not closed")


TRIGGERS = _path("common", "scripted_triggers", "un_membership_triggers.txt")


class EligibilityTests(unittest.TestCase):
    def test_eligible_types_are_the_autonomous_ones(self):
        body = _block(_read(TRIGGERS), "un_membership_eligible")
        types = set(re.findall(r"is_subject_type\s*=\s*(\w+)", body))
        self.assertEqual(types, {
            "subject_type_dominion",
            "subject_type_protectorate",
            "subject_type_tributary",
        })
        self.assertIn("is_subject = no", body)
        self.assertIn("is_country_type = decentralized", body)

    def test_billing_needs_a_represented_overlord(self):
        body = _block(_read(TRIGGERS), "un_dues_billed_to_overlord")
        self.assertIn("un_representation_suspended = yes", body)
        self.assertRegex(body, r"overlord\s*\?=\s*\{\s*un_member_represented = yes")

    def test_every_way_in_asks_eligibility(self):
        cases = [
            (("common", "scripted_buttons", "un_buttons.txt"), "un_join_button"),
            (("common", "scripted_effects", "un_ladder_effects.txt"), "un_charter_invitations"),
            (("events", "un_events.txt"), "un_events.1"),
            (("events", "un_events.txt"), "un_events.10"),
            (("common", "scripted_triggers", "un_teeth_triggers.txt"), "un_case_standing_applies"),
        ]
        for parts, name in cases:
            with self.subTest(block=name):
                body = _block(_read(_path(*parts)), name)
                self.assertIn("un_membership_eligible = yes", body)
                self.assertNotIn("is_subject = no", body)

    def test_pariah_and_enrolment_ask_eligibility(self):
        je = _read(_path("common", "journal_entries", "je_united_nations.txt"))
        start = je.index("modifier:country_un_membership_obligation_bool")
        self.assertIn("un_membership_eligible = yes", je[start:start + 400])
        for mod in ("un_nonmember_pariah_modifier", "un_nonmember_pariah_strong_modifier"):
            with self.subTest(modifier=mod):
                add = je.index("add_modifier = { name = " + mod + " }")
                limit = je.rindex("un_tier_at_least", 0, add)
                self.assertIn("un_membership_eligible = yes", je[limit - 200:limit])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it to see it fail**

Run: `/home/jakef/src/Vic3TimelineExtended/.venv/bin/python -m unittest test_un_membership -v`
Expected: FAIL/ERROR (`un_membership_triggers.txt` missing; blocks still use `is_subject = no`).

- [ ] **Step 3: Create the triggers** — `common/scripted_triggers/un_membership_triggers.txt`, with a UTF-8 BOM:

```
# ============================================================================
# UN MEMBERSHIP — ELIGIBILITY AND REPRESENTATION
# docs/systems/un_redesign_design.md §0.8
# ============================================================================
# Who may join, and whose seat is active. A member that stops conducting its
# own foreign policy keeps its membership, but its representation is
# suspended: it is treated as part of its overlord abroad. A represented
# overlord is billed for its seat and, while it pays, the subject keeps the
# benefits of membership (the seat is carried). Everything here is computed
# live: a subjugation takes effect at once, and a release restores the seat at
# once. The monthly pulse only announces the change
# (un_representation_monthly_update, un_membership_effects.txt).
# ============================================================================

# The scoped country conducts its own foreign policy, so it may join and, as a
# member, is represented: not decentralized, and independent or a dominion,
# protectorate or tributary. Those are the vanilla subject types that may start
# their own diplomatic plays, less the chartered company, which the
# decolonisation regime already treats as a colony
# (is_qualifying_colonial_subject). The engine has no trigger for
# can_start_own_diplomatic_plays, so the types are listed: keep them in step
# with common/subject_types/ when a patch adds one. Do not swap in
# te_mon_is_board_subject: it groups by autonomy_level, which puts the personal
# union (level 2, but no plays of its own) on the other side.
# Scope: country
un_membership_eligible = {
	NOT = { is_country_type = decentralized }
	OR = {
		is_subject = no
		is_subject_type = subject_type_dominion
		is_subject_type = subject_type_protectorate
		is_subject_type = subject_type_tributary
	}
}

# A member whose seat is active.
# Scope: country
un_member_represented = {
	je:je_united_nations ?= { has_modifier = un_member_modifier }
	un_membership_eligible = yes
}

# A member whose representation is suspended: it no longer conducts its own
# foreign policy. It stays a member, keeps its standing and its ratified
# conventions, and may leave. It casts no ballot, tables nothing, is offered
# nothing by the docket, is not lobbied, is not asked to comply with or ratify
# a passed resolution, is not counted in the two-thirds, holds no permanent
# seat, does not host the headquarters and sends no contingent at will. It sits
# beside every Article 19 check (un_dues_vote_suspended); test_un_membership.py
# keeps the two together.
# Scope: country
un_representation_suspended = {
	je:je_united_nations ?= { has_modifier = un_member_modifier }
	NOT = { un_membership_eligible = yes }
}

# A suspended member whose direct overlord is a represented member: the
# overlord is assessed dues for it (un_dues_assessed_gdp). Only a represented
# overlord carries a subject, so a chain of colonies never bills a country
# that is itself suspended.
# Scope: country
un_dues_billed_to_overlord = {
	un_representation_suspended = yes
	overlord ?= { un_member_represented = yes }
}

# The seat is carried: billed to an overlord that is paying its dues. An
# overlord that withholds withholds its subjects' share too.
# Scope: country
un_seat_carried = {
	un_dues_billed_to_overlord = yes
	overlord ?= { NOT = { un_dues_is_withholding = yes } }
}

# Draws the benefits of membership (un_member_privileges_modifier, and
# un_membership_benefits_modifier from the Contested tier): represented, or
# suspended with its seat carried.
# Scope: country
un_member_draws_benefits = {
	OR = {
		un_member_represented = yes
		un_seat_carried = yes
	}
}
```

- [ ] **Step 4: Route every way in through it**

`common/scripted_buttons/un_buttons.txt`, `un_join_button` `possible`, replace

```
		is_subject = no
		NOT = { is_country_type = decentralized }
```
with
```
		custom_tooltip = {
			text = un_membership_eligible_tt
			un_membership_eligible = yes
		}
```

`common/scripted_effects/un_ladder_effects.txt`, `un_charter_invitations` `limit`, and `events/un_events.txt` `un_events.1` `trigger`: replace the pair `is_subject = no` / `NOT = { is_country_type = decentralized }` with `un_membership_eligible = yes`. Update the comments ("every other recognized independent country" → "every other country that conducts its own foreign policy (un_membership_eligible)").

`events/un_events.txt`, `un_events.10` option e `trigger`: replace `is_subject = no` with `un_membership_eligible = yes`.

`common/scripted_triggers/un_teeth_triggers.txt`, `un_case_standing_applies`: replace `is_subject = no` / `NOT = { is_country_type = decentralized }` with `un_membership_eligible = yes`.

`common/journal_entries/je_united_nations.txt`:
- treaty enrolment `limit`: replace `is_subject = no` / `NOT = { is_country_type = decentralized }` with `un_membership_eligible = yes`; the comment becomes "Only a country that conducts its own foreign policy (un_membership_eligible, §0.8): a treaty obligation is no way round the Join button's gate."
- both pariah `limit`s: add `un_membership_eligible = yes` after the `NOT = { … un_member_modifier … }` line; the comment gains "Only an eligible outsider is a pariah (§0.8 ruling 10): a puppet or colony cannot join, so staying out is not its choice. An expelled country, or one that walked out, is eligible by type and stays one."

`localization/english/te_miscellaneous_l_english.yml`, beside `un_article_19_table_tt`:
```
 un_membership_eligible_tt:0 "We conduct our own foreign policy: we are independent, or a dominion, protectorate or tributary"
```

- [ ] **Step 5: Run the test** — same command. Expected: 4 tests PASS.

- [ ] **Step 6: Commit** — `git add common/scripted_triggers/un_membership_triggers.txt common/scripted_buttons/un_buttons.txt common/scripted_effects/un_ladder_effects.txt events/un_events.txt common/journal_entries/je_united_nations.txt common/scripted_triggers/un_teeth_triggers.txt localization/english/te_miscellaneous_l_english.yml test_un_membership.py`, message "UN: eligibility is diplomatic autonomy (§0.8 rulings 1, 2, 10)".

### Task 2: Suspended representation at every gate

**Files:**
- Modify: `common/scripted_triggers/un_resolution_triggers.txt` (`un_vote_can_cast_ballot`, `un_chamber_ballot_open`)
- Modify: `events/un_vote_events.txt` (`un_vote.1` trigger; `un_vote.2` dispatch of `un_vote.3`; `un_vote.3` trigger)
- Modify: `common/scripted_guis/un_chamber_sguis.txt` (`un_chamber_vote_sgui` `is_valid`)
- Modify: `common/script_values/un_script_values.txt` (`un_vote_eligible_member_count`)
- Modify: `common/scripted_triggers/un_propose_triggers.txt` (8 `_possible` triggers)
- Modify: `common/scripted_triggers/un_docket_triggers.txt` (`un_docket_can_be_offered`, `un_docket_loan_candidate`, `un_docket_peacekeeping_power`, `un_docket_aid_power`)
- Modify: `common/diplomatic_actions/un_lobbying.txt` (`selectable`, `potential`)
- Modify: `common/scripted_triggers/un_mission_triggers.txt` (`un_mission_volunteer_eligible`, `un_mission_slot_can_volunteer`)
- Modify: `common/scripted_effects/un_hq_effects.txt` (`un_hq_assign_host`, `un_hq_monthly_update`)
- Modify: `common/scripted_triggers/un_permanent_member_triggers.txt` (`un_permanent_seat_candidate`)
- Modify: `localization/english/te_journal_entries_l_english.yml`, `te_miscellaneous_l_english.yml`
- Test: `test_un_membership.py`

**Interfaces:**
- Consumes: `un_representation_suspended`, `un_member_represented` (Task 1).

- [ ] **Step 1: Write the failing tests** — append to `test_un_membership.py`:

```python
_TOP = re.compile(r"^([A-Za-z_][A-Za-z0-9_.]*)\s*=\s*\{", re.M)

# Blocks that name Article 19 for a reason other than taking a voice away.
_ARTICLE_19_ONLY = {
    "un_dues_vote_suspended",   # the definition
    "un_chamber_dues_lines",    # the dues display
    "un_pay_dues_button",       # an AI weight: settle once the vote is gone
}


def _script_files():
    for root in ("common", "events"):
        for dirpath, _dirs, files in os.walk(_path(root)):
            for f in files:
                if f.endswith(".txt"):
                    yield os.path.join(dirpath, f)


class RepresentationGateTests(unittest.TestCase):
    def test_every_article_19_gate_also_asks_suspension(self):
        missing = []
        for path in _script_files():
            text = _read(path)
            if "un_dues_vote_suspended" not in text:
                continue
            for m in _TOP.finditer(text):
                name = m.group(1)
                body = _block(text, name)
                if ("un_dues_vote_suspended" in body
                        and "un_representation_suspended" not in body
                        and name not in _ARTICLE_19_ONLY):
                    missing.append(f"{os.path.relpath(path, REPO)}: {name}")
        self.assertEqual(missing, [])

    def test_gates_without_article_19(self):
        cases = [
            (("common", "diplomatic_actions", "un_lobbying.txt"), "un_secure_commitment_action"),
            (("common", "scripted_triggers", "un_docket_triggers.txt"), "un_docket_loan_candidate"),
            (("common", "scripted_triggers", "un_docket_triggers.txt"), "un_docket_peacekeeping_power"),
            (("common", "scripted_triggers", "un_docket_triggers.txt"), "un_docket_aid_power"),
            (("common", "scripted_triggers", "un_mission_triggers.txt"), "un_mission_volunteer_eligible"),
            (("common", "scripted_triggers", "un_mission_triggers.txt"), "un_mission_slot_can_volunteer"),
            (("events", "un_vote_events.txt"), "un_vote.2"),
            (("events", "un_vote_events.txt"), "un_vote.3"),
        ]
        for parts, name in cases:
            with self.subTest(block=name):
                self.assertIn("un_representation_suspended", _block(_read(_path(*parts)), name))

    def test_lobbying_target_needs_a_vote(self):
        body = _block(_read(_path("common", "diplomatic_actions", "un_lobbying.txt")),
                      "un_secure_commitment_action")
        potential = body[body.index("potential"):body.index("possible")]
        self.assertIn("un_representation_suspended", potential)
        self.assertIn("un_dues_vote_suspended", potential)

    def test_headquarters_goes_only_to_represented_members(self):
        text = _read(_path("common", "scripted_effects", "un_hq_effects.txt"))
        for name in ("un_hq_assign_host", "un_hq_monthly_update"):
            with self.subTest(block=name):
                body = _block(text, name)
                self.assertIn("un_member_represented = yes", body)
                self.assertNotIn("has_modifier = un_member_modifier", body)
```

- [ ] **Step 2: Run them to see them fail** — `…/python -m unittest test_un_membership -v`. Expected: the new tests FAIL, listing the Article 19 gates.

- [ ] **Step 3: Add the check beside Article 19**

- `un_vote_can_cast_ballot`, `un_chamber_ballot_open` (`un_resolution_triggers.txt`) and `un_vote.1` `trigger` (`un_vote_events.txt`): after `NOT = { un_dues_vote_suspended = yes }` add `NOT = { un_representation_suspended = yes }`. Comment: "§0.8: a member whose representation is suspended has no vote either."
- `un_vote_eligible_member_count` (`un_script_values.txt`): add `NOT = { un_representation_suspended = yes }` after the Article 19 line, with the comment "nor is a member whose representation is suspended (§0.8)".
- `un_permanent_seat_candidate`: add `NOT = { un_representation_suspended = yes }` after the Article 19 line.
- `un_docket_can_be_offered`: add `NOT = { un_representation_suspended = yes }` after the Article 19 line.
- The 8 identical blocks in `un_propose_triggers.txt` (verified by count): after each
  ```
  	custom_tooltip = {
  		text = un_article_19_table_tt
  		NOT = { un_dues_vote_suspended = yes }
  	}
  ```
  insert
  ```
  	custom_tooltip = {
  		text = un_representation_table_tt
  		NOT = { un_representation_suspended = yes }
  	}
  ```
  (a Python `str.replace` on that exact text, asserting the count is 8).
- `un_chamber_vote_sgui` `is_valid`, `trigger_else`: before the Article 19 `custom_tooltip`, insert
  ```
  				custom_tooltip = {
  					text = je_un_chamber_vote_represented_tt
  					NOT = { un_representation_suspended = yes }
  				}
  ```

- [ ] **Step 4: The gates without Article 19**

- `un_docket_loan_candidate`, `un_docket_peacekeeping_power`, `un_docket_aid_power`: add `NOT = { un_representation_suspended = yes }` after the membership line.
- `un_lobbying.txt`: in `selectable` after the membership line add `NOT = { un_representation_suspended = yes }`; in `potential`, inside `scope:target_country`, after the membership line add
  ```
  			# A member without a vote has none to promise: Article 19, or
  			# suspended representation (§0.8).
  			NOT = { un_dues_vote_suspended = yes }
  			NOT = { un_representation_suspended = yes }
  ```
- `un_vote_events.txt`: in `un_vote.2`'s `every_country` limit that fires `un_vote.3`, and in `un_vote.3`'s `trigger`, add `NOT = { un_representation_suspended = yes }`, commented "(§0.8: ratifying is foreign policy, which the overlord conducts)".
- `un_mission_volunteer_eligible`: add `NOT = { un_representation_suspended = yes }`. `un_mission_slot_can_volunteer`: after the member tooltip add
  ```
  	custom_tooltip = {
  		text = un_mission_volunteer_need_represented_tt
  		NOT = { un_representation_suspended = yes }
  	}
  ```
- `un_hq_effects.txt`: in `un_hq_assign_host` replace the four `je:je_united_nations ?= { has_modifier = un_member_modifier }` with `un_member_represented = yes`; in `un_hq_monthly_update` replace `NOT = { je:je_united_nations ?= { has_modifier = un_member_modifier } }` with `NOT = { un_member_represented = yes }`. Header comment: "A suspended member neither keeps nor takes the headquarters (§0.8 ruling 3)."

- [ ] **Step 5: Loc**

`te_journal_entries_l_english.yml`:
```
 je_un_chamber_vote_represented_tt:0 "Our delegation is seated: we conduct our own foreign policy ([concept_un_suspended_representation])"
 je_un_chamber_rule_supermajority:0 "  Passage rule: a two-thirds supermajority of all [THIS.ScriptValue('un_vote_eligible_member_count')|0] members with a vote (a member two years in arrears on its [concept_un_dues] has none, nor does a member whose representation is suspended: [concept_un_suspended_representation])."
```
`te_miscellaneous_l_english.yml`:
```
 un_representation_table_tt:0 "Our delegation is seated: we conduct our own foreign policy ([concept_un_suspended_representation])"
 un_mission_volunteer_need_represented_tt:0 "Our delegation is seated: we conduct our own foreign policy ([concept_un_suspended_representation])"
```
(`concept_un_suspended_representation` is created in Task 6; `concept_reference_audit` flags it until then, so do not run that audit until Task 6.)

- [ ] **Step 6: Run the tests** — expected: all PASS.

- [ ] **Step 7: Commit** — stage the files listed above plus `test_un_membership.py`; message "UN: suspended representation at every vote, tabling, docket, lobbying and seat gate (§0.8 ruling 3)".

### Task 3: The overlord carries the seat — dues

**Files:**
- Modify: `common/script_values/un_dues_values.txt`
- Modify: `common/journal_entries/je_united_nations.txt` (member block, dues call)
- Modify: `common/scripted_buttons/un_buttons.txt` (withhold and pay buttons)
- Test: `test_un_membership.py`

**Interfaces:**
- Consumes: `un_dues_billed_to_overlord`, `un_member_represented`, `un_representation_suspended` (Task 1).
- Produces: script value `un_dues_assessed_gdp` (country scope).

- [ ] **Step 1: Write the failing test** — append:

```python
DUES = _path("common", "script_values", "un_dues_values.txt")


class DuesTests(unittest.TestCase):
    def test_assessment_reads_the_carried_gdp(self):
        text = _read(DUES)
        self.assertIn("un_dues_billed_to_overlord = yes", _block(text, "un_dues_assessed_gdp"))
        for name in ("un_dues_weekly_value", "un_dues_monthly_value"):
            with self.subTest(value=name):
                self.assertRegex(_block(text, name), r"value\s*=\s*un_dues_assessed_gdp")

    def test_pillar_and_budget_count_represented_members_once(self):
        text = _read(DUES)
        for name in ("un_members_gdp_value", "un_withholders_gdp_value", "un_budget_weekly_value"):
            with self.subTest(value=name):
                body = _block(text, name)
                self.assertIn("un_member_represented = yes", body)
                self.assertNotIn("has_modifier = un_member_modifier", body)

    def test_suspended_member_is_not_assessed(self):
        je = _read(_path("common", "journal_entries", "je_united_nations.txt"))
        call = je.index("un_dues_country_monthly_update = yes")
        self.assertIn("un_representation_suspended = yes", je[call - 500:call])
        buttons = _read(_path("common", "scripted_buttons", "un_buttons.txt"))
        for name in ("un_withhold_dues_button", "un_pay_dues_button"):
            with self.subTest(button=name):
                self.assertIn("un_representation_suspended", _block(buttons, name))
```

- [ ] **Step 2: Run to see it fail.**

- [ ] **Step 3: The values** — in `un_dues_values.txt`, before `un_dues_weekly_value`:

```
# The GDP a member is assessed on: its own, and that of every suspended member
# whose seat it carries as the represented direct overlord (§0.8 ruling 4). A
# suspended member itself is never assessed. Each carried subject is counted
# once, here, so the budget and both GDP terms of the funding pillar read this.
# Scope: country (a represented member)
un_dues_assessed_gdp = {
	value = gdp
	every_direct_subject = {
		limit = { un_dues_billed_to_overlord = yes }
		add = gdp
	}
}
```

In `un_dues_weekly_value` and `un_dues_monthly_value` change `value = gdp` to `value = un_dues_assessed_gdp`. In `un_members_gdp_value` and `un_withholders_gdp_value` replace the membership line with `un_member_represented = yes` and `add = gdp` with `add = un_dues_assessed_gdp`. In `un_budget_weekly_value` replace the membership line with `un_member_represented = yes`. Add to the file header: "A suspended member pays nothing itself; its represented direct overlord is assessed on its GDP (un_dues_assessed_gdp, §0.8)."

- [ ] **Step 4: The member block** — in `je_united_nations.txt` replace `un_dues_country_monthly_update = yes` with:

```
				# A suspended member is never assessed itself: its represented
				# overlord is billed for its seat (un_dues_assessed_gdp, §0.8
				# ruling 4). Its arrears, if any, neither grow nor clear.
				if = {
					limit = { un_representation_suspended = yes }
					if = {
						limit = { has_modifier = un_dues_modifier }
						remove_modifier = un_dues_modifier
					}
				}
				else = {
					un_dues_country_monthly_update = yes
				}
```

- [ ] **Step 5: The buttons** — in `un_withhold_dues_button` and `un_pay_dues_button`, add `NOT = { un_representation_suspended = yes }` to both `visible` and `possible` (comment: "Our dues are our overlord's while our representation is suspended (§0.8).").

- [ ] **Step 6: Run the tests** — all PASS.

- [ ] **Step 7: Commit** — "UN: a represented overlord is assessed dues for the seats it carries (§0.8 ruling 4)".

### Task 4: Membership and its benefits separated

**Files:**
- Modify: `common/static_modifiers/extra_modifiers.txt` (`un_member_modifier`, new `un_member_privileges_modifier`, the comment at the `country_improve_relations_speed_mult` note)
- Modify: `common/scripted_effects/un_ladder_effects.txt` (`un_found_organisation`, `un_join_organisation`, `un_membership_end_effect`)
- Modify: `events/un_events.txt` (`un_events.1` option A)
- Modify: `common/scripted_effects/te_debug_un_effects.txt` (`te_debug_un_seat_member`)
- Modify: `common/journal_entries/je_united_nations.txt` (monthly reconcile, benefits limit, non-member cleanup)
- Modify: `localization/english/te_concepts_l_english.yml`
- Test: `test_un_membership.py`

**Interfaces:**
- Consumes: `un_member_draws_benefits` (Task 1).
- Produces: static modifier `un_member_privileges_modifier`.

- [ ] **Step 1: Write the failing test** — append:

```python
MODIFIERS = _path("common", "static_modifiers", "extra_modifiers.txt")
_FIELDS = {
    "country_improve_relations_speed_mult",
    "country_leverage_generation_add",
    "country_prestige_mult",
    "country_influence_mult",
    "country_defender_diplomatic_play_escalation_weekly_mult",
}


class PrivilegesTests(unittest.TestCase):
    def _fields(self, name):
        body = _block(_read(MODIFIERS), name)
        return {k for k in re.findall(r"^\s*(\w+)\s*=", body, re.M) if k != "icon"}

    def test_marker_has_no_effects(self):
        self.assertEqual(self._fields("un_member_modifier"), set())

    def test_privileges_carry_the_old_bonuses(self):
        self.assertEqual(self._fields("un_member_privileges_modifier"), _FIELDS)

    def test_every_join_path_grants_privileges_at_once(self):
        missing = []
        for path in _script_files():
            text = _read(path)
            for m in _TOP.finditer(text):
                body = _block(text, m.group(1))
                if re.search(r"add_modifier\s*=\s*\{\s*name\s*=\s*un_member_modifier\b", body) \
                        and "un_member_privileges_modifier" not in body:
                    missing.append(m.group(1))
        self.assertEqual(missing, [])

    def test_leaving_and_the_pulse(self):
        end = _block(_read(_path("common", "scripted_effects", "un_ladder_effects.txt")),
                      "un_membership_end_effect")
        self.assertIn("remove_modifier = un_member_privileges_modifier", end)
        je = _read(_path("common", "journal_entries", "je_united_nations.txt"))
        benefits = je.index("name = un_membership_benefits_modifier")
        self.assertIn("un_member_draws_benefits = yes", je[benefits - 600:benefits])
        self.assertGreaterEqual(je.count("un_member_privileges_modifier"), 3)
```

- [ ] **Step 2: Run to see it fail.**

- [ ] **Step 3: Split the modifier** — in `extra_modifiers.txt` replace `un_member_modifier`'s body with:

```
# The membership record itself (§0.8 ruling 5): every member carries it,
# represented or not, and 196 lines read it as "is a member". It has no
# effects. What membership brings is un_member_privileges_modifier, drawn only
# by a member that is represented or whose seat is carried
# (un_member_draws_benefits).
un_member_modifier = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_flag_positive.dds
}

# What membership brings (§0.8 ruling 5). The journal entry's monthly member
# pulse reconciles it; every join path adds it at once (un_join_organisation,
# un_found_organisation, un_events.1, te_debug_un_seat_member);
# un_membership_end_effect removes it. UN_JOIN_DESC restates these numbers.
un_member_privileges_modifier = {
	icon = gfx/interface/icons/timed_modifier_icons/modifier_flag_positive.dds
	country_improve_relations_speed_mult = 0.10
	country_leverage_generation_add = 5
	country_prestige_mult = 0.03
	country_influence_mult = 0.03
	country_defender_diplomatic_play_escalation_weekly_mult = -0.05
}
```
and in the comment that says "un_member_modifier already grants", say `un_member_privileges_modifier`.

- [ ] **Step 4: Grant, reconcile, remove**

- `un_found_organisation`, `un_join_organisation` (`un_ladder_effects.txt`), `un_events.1` option A (`un_events.txt`): after the `add_modifier = { name = un_member_modifier }` line add `je:je_united_nations ?= { add_modifier = { name = un_member_privileges_modifier } }`. In `te_debug_un_seat_member`, inside the `if` that adds the marker, add `add_modifier = { name = un_member_privileges_modifier }`.
- `un_membership_end_effect`: after `remove_modifier = un_member_modifier` add `je:je_united_nations ?= { remove_modifier = un_member_privileges_modifier }`.
- `je_united_nations.txt`, pre-member cleanup (beside the Security Council strip): 
  ```
  			# A non-member draws no privileges (§0.8 ruling 5): a safety net
  			# for a path that ended membership without un_membership_end_effect.
  			if = {
  				limit = {
  					je:je_united_nations ?= { has_modifier = un_member_privileges_modifier }
  					NOT = { je:je_united_nations ?= { has_modifier = un_member_modifier } }
  				}
  				je:je_united_nations ?= { remove_modifier = un_member_privileges_modifier }
  			}
  ```
- Member block, before "Apply scaled UN membership modifier":
  ```
  				# ---- Membership privileges (§0.8 ruling 5) ----
  				# Represented, or suspended with the seat carried by a paying
  				# overlord. The join paths add it at once; this reconciles it
  				# every month, which is also how an existing save gains it.
  				if = {
  					limit = { un_member_draws_benefits = yes }
  					if = {
  						limit = { NOT = { je:je_united_nations ?= { has_modifier = un_member_privileges_modifier } } }
  						je:je_united_nations ?= { add_modifier = { name = un_member_privileges_modifier } }
  					}
  				}
  				else_if = {
  					limit = { je:je_united_nations ?= { has_modifier = un_member_privileges_modifier } }
  					je:je_united_nations ?= { remove_modifier = un_member_privileges_modifier }
  				}
  ```
- The benefits block's `limit = { un_tier_at_least_contested = yes }` becomes `limit = { un_tier_at_least_contested = yes un_member_draws_benefits = yes }` (one clause per line), with "…and only to a member that draws the benefits (§0.8)" in its comment.

- [ ] **Step 5: Loc** — `te_concepts_l_english.yml`:
```
 un_member_modifier_desc:0 "This country is a member of the United Nations. What membership brings is listed under UN Membership Privileges: a member whose representation is suspended draws them only while its overlord carries its seat."
 un_member_privileges_modifier:0 "UN Membership Privileges"
 un_member_privileges_modifier_desc:0 "What a seat in the United Nations brings. Drawn by every represented member, and by a member whose [concept_un_suspended_representation] while its overlord sits in the Assembly and pays its [concept_un_dues]."
```

- [ ] **Step 6: Run the tests** — all PASS.

- [ ] **Step 7: Commit** — "UN: membership privileges on their own modifier, drawn by represented and carried members (§0.8 ruling 5)".

### Task 5: Transitions announced once

**Files:**
- Create: `common/scripted_effects/un_membership_effects.txt`
- Modify: `common/journal_entries/je_united_nations.txt` (call before the member block)
- Modify: `common/messages/extra_messages.txt`
- Modify: `localization/english/te_notifications_l_english.yml`
- Test: `test_un_membership.py`

**Interfaces:**
- Consumes: `un_representation_suspended` (Task 1).
- Produces: scripted effect `un_representation_monthly_update`; messages `un_representation_suspended_notice`, `un_representation_restored_notice`; country variable `un_rep_suspended`.

- [ ] **Step 1: Write the failing test** — append:

```python
class TransitionTests(unittest.TestCase):
    def test_pulse_announces_and_strips(self):
        body = _block(_read(_path("common", "scripted_effects", "un_membership_effects.txt")),
                      "un_representation_monthly_update")
        for needle in ("un_representation_suspended_notice", "un_representation_restored_notice",
                       "remove_modifier = un_permanent_member_modifier", "un_rep_suspended"):
            with self.subTest(needle=needle):
                self.assertIn(needle, body)
        je = _read(_path("common", "journal_entries", "je_united_nations.txt"))
        self.assertLess(je.index("un_representation_monthly_update = yes"),
                        je.index("---- Member-only logic ----"))

    def test_messages_exist(self):
        msgs = _read(_path("common", "messages", "extra_messages.txt"))
        for name in ("un_representation_suspended_notice", "un_representation_restored_notice"):
            with self.subTest(message=name):
                _block(msgs, name)
```

- [ ] **Step 2: Run to see it fail.**

- [ ] **Step 3: The effect** — `common/scripted_effects/un_membership_effects.txt`, with a BOM:

```
# ============================================================================
# UN MEMBERSHIP — THE MONTHLY REPRESENTATION CHECK (§0.8 ruling 9)
# ============================================================================
# The gates read un_representation_suspended live and never wait for this.
# It only announces a suspension or a restoration, once, and strips what a
# suspended member may not hold. There is no country-scoped on-action for a
# change of subject type (colony to dominion), so a monthly check is the
# authoritative one. var:un_rep_suspended exists only to notice the change.
# The headquarters moves by un_hq_monthly_update (un_hq_effects.txt), and the
# vacated permanent seat is refilled by un_seat_monthly_update.
# ============================================================================

# Called from the journal entry's monthly pulse, for every country holding it.
# Scope: country
un_representation_monthly_update = {
	if = {
		limit = { un_representation_suspended = yes }
		if = {
			limit = { NOT = { has_variable = un_rep_suspended } }
			set_variable = un_rep_suspended
			post_notification = un_representation_suspended_notice
		}
		# A permanent seat is a vote; it goes to the next great power by
		# prestige (un_seat_monthly_update).
		if = {
			limit = { is_un_permanent_member = yes }
			je:je_united_nations ?= { remove_modifier = un_permanent_member_modifier }
			je:je_united_nations ?= { remove_modifier = un_security_council_modifier }
			if = {
				limit = { has_variable = un_permanent_subgp_months }
				remove_variable = un_permanent_subgp_months
			}
		}
	}
	else_if = {
		limit = { has_variable = un_rep_suspended }
		remove_variable = un_rep_suspended
		# Restored, not departed: a member that left while suspended is told
		# nothing here.
		if = {
			limit = { je:je_united_nations ?= { has_modifier = un_member_modifier } }
			post_notification = un_representation_restored_notice
		}
	}
}
```

- [ ] **Step 4: Call it** — in `je_united_nations.txt`, just before `# ---- Member-only logic ----`:
```
			# ---- Suspended representation (§0.8 ruling 9) ----
			# Announce a suspension or restoration once, and strip a suspended
			# member's permanent seat. Before the member block, so the dues and
			# privileges below see the same month.
			un_representation_monthly_update = yes
```

- [ ] **Step 5: Messages and loc** — `extra_messages.txt`, after `un_article_19_notice`:
```
# §0.8: our representation in the UN is suspended because we no longer
# conduct our own foreign policy, or restored because we do again
# (un_representation_monthly_update).
un_representation_suspended_notice = {
	type = country
	texture = "gfx/interface/icons/notification_icons/interest_group_bad.dds"
	notification_type = feed
	color = bad
}

un_representation_restored_notice = {
	type = country
	texture = "gfx/interface/icons/notification_icons/unused/interest_group_good.dds"
	notification_type = feed
	color = good
}
```
`te_notifications_l_english.yml`:
```
 notification_un_representation_suspended_notice_name:0 "Our UN Representation Is Suspended"
 notification_un_representation_suspended_notice_desc:0 "We no longer conduct our own foreign policy, so our seat in the United Nations is suspended. We remain a member, but we cast no vote and table no resolution. While our overlord sits in the Assembly and pays its dues, it pays ours and we keep the benefits of membership."
 notification_un_representation_suspended_notice_tooltip:0 "#header $notification_un_representation_suspended_notice_name$#!\n$notification_un_representation_suspended_notice_desc$"
 notification_un_representation_restored_notice_name:0 "Our UN Representation Is Restored"
 notification_un_representation_restored_notice_desc:0 "We conduct our own foreign policy again, so our delegation takes its seat in the General Assembly once more. We vote, table resolutions and pay our own dues."
 notification_un_representation_restored_notice_tooltip:0 "#header $notification_un_representation_restored_notice_name$#!\n$notification_un_representation_restored_notice_desc$"
```

- [ ] **Step 6: Run the tests** — all PASS.

- [ ] **Step 7: Commit** — "UN: announce suspension and restoration, strip a suspended permanent seat (§0.8 ruling 9)".

### Task 6: What the journal entry and chamber say

**Files:**
- Modify: `common/script_values/un_script_values.txt` (`un_member_count`; rename `un_subject_member_count` → `un_suspended_member_count`, `un_independent_country_count` → `un_eligible_country_count`; new `un_carried_seat_count`)
- Modify: `common/journal_entries/je_united_nations.txt` (status_desc §4)
- Modify: `common/game_concepts/extra_concepts.txt` (`concept_un_suspended_representation`)
- Modify: `common/scripted_guis/un_chamber_sguis.txt` (`un_chamber_status_sgui`)
- Modify: `common/scripted_effects/un_chamber_display_effects.txt` (`un_chamber_dues_lines`)
- Modify: `localization/english/te_journal_entries_l_english.yml`, `te_concepts_l_english.yml`
- Test: `test_un_membership.py`

**Interfaces:**
- Consumes: `un_member_represented`, `un_representation_suspended`, `un_membership_eligible`, `un_seat_carried`, `un_dues_billed_to_overlord` (Task 1).
- Produces: script values `un_member_count`, `un_suspended_member_count`, `un_eligible_country_count`, `un_carried_seat_count`; concept `concept_un_suspended_representation`.

- [ ] **Step 1: Write the failing test** — append:

```python
LOC_JE = _path("localization", "english", "te_journal_entries_l_english.yml")


class DisplayTests(unittest.TestCase):
    def test_counts_share_one_rule(self):
        text = _read(_path("common", "script_values", "un_script_values.txt"))
        self.assertIn("un_member_represented = yes", _block(text, "un_member_count"))
        self.assertIn("un_representation_suspended = yes", _block(text, "un_suspended_member_count"))
        self.assertIn("un_membership_eligible = yes", _block(text, "un_eligible_country_count"))
        for gone in ("un_subject_member_count", "un_independent_country_count"):
            with self.subTest(gone=gone):
                self.assertNotRegex(text, re.compile(r"^" + gone + r"\s*=", re.M))

    def test_journal_lines(self):
        je = _read(_path("common", "journal_entries", "je_united_nations.txt"))
        with open(LOC_JE, encoding="utf-8-sig") as f:
            loc = f.read()
        for key in ("je_un_statistics", "je_un_statistics_suspended_one",
                    "je_un_statistics_suspended_many"):
            with self.subTest(key=key):
                self.assertIn("desc = " + key, je)
                self.assertRegex(loc, r"\n " + key + r":0 \".*un_eligible_country_count")
        self.assertNotIn("je_un_statistics_subject_seats", loc + je)

    def test_concept_defined(self):
        concepts = _read(_path("common", "game_concepts", "extra_concepts.txt"))
        self.assertRegex(concepts, re.compile(r"^concept_un_suspended_representation\s*=\s*\{", re.M))
```

- [ ] **Step 2: Run to see it fail.**

- [ ] **Step 3: The counts** — replace the three values and their header comment in `un_script_values.txt`:

```
# The General Assembly line (§0.8 rulings 7-8): the represented members of the
# eligible nations, then, apart, the members whose representation is
# suspended. Both sides of "N of M" ask un_membership_eligible, so N never
# exceeds M, and an annexed member leaves both at once.
un_member_count = {
	value = 0
	every_country = {
		limit = { un_member_represented = yes }
		add = 1
	}
}

un_suspended_member_count = {
	value = 0
	every_country = {
		limit = { un_representation_suspended = yes }
		add = 1
	}
}

un_eligible_country_count = {
	value = 0
	every_country = {
		limit = { un_membership_eligible = yes }
		add = 1
	}
}

# Our direct subjects whose seats we carry (§0.8 ruling 4), for our dues line.
# Scope: country
un_carried_seat_count = {
	value = 0
	every_direct_subject = {
		limit = { un_dues_billed_to_overlord = yes }
		add = 1
	}
}
```

- [ ] **Step 4: The journal entry** — replace status_desc §4 (the `first_valid` holding `je_un_statistics_subject_seats` and `je_un_statistics`) with:

```
		# 4. General Assembly statistics (§0.8 ruling 8): the represented
		# members of the eligible nations, then the members whose
		# representation is suspended, in the singular or the plural.
		first_valid = {
			triggered_desc = {
				desc = je_un_statistics_suspended_many
				trigger = {
					any_country = {
						un_representation_suspended = yes
						count >= 2
					}
				}
			}
			triggered_desc = {
				desc = je_un_statistics_suspended_one
				trigger = {
					any_country = { un_representation_suspended = yes }
				}
			}
			triggered_desc = {
				desc = je_un_statistics
				trigger = {
					any_country = {
						je:je_united_nations ?= { has_modifier = un_member_modifier }
						count >= 1
					}
				}
			}
		}
```

- [ ] **Step 5: The concept** — `extra_concepts.txt`, after `concept_un_mission = {}`: `concept_un_suspended_representation = {}`. `te_concepts_l_english.yml`:
```
 concept_un_suspended_representation:0 "Suspended Representation"
 concept_un_suspended_representation_desc:0 "A member of the United Nations that no longer conducts its own foreign policy keeps its membership, but its representation is suspended. Only an independent country, or a dominion, protectorate or tributary, conducts its own. A puppet, vassal, colony, personal union, crown land or chartered company does not, and neither does a decentralized nation. A suspended member casts no vote, tables nothing, holds no permanent seat and does not host the headquarters. It is treated as part of its overlord abroad: while its overlord sits in the [concept_un_general_assembly] and pays its [concept_un_dues], the overlord pays for its seat and it keeps the benefits of membership. Its representation is restored as soon as it conducts its own foreign policy again."
 concept_un_general_assembly_desc:0 "The body of all UN members. Every represented member casts one vote on each proposed resolution; a member that lacks diplomatic autonomy keeps its seat, but its [concept_un_suspended_representation]. Most resolutions pass on a simple majority of the votes cast. Recommendatory resolutions need only the GA. Binding resolutions also require Security Council consent — a [concept_un_veto] from any [concept_un_permanent_member] reduces them to a graduated form."
```

`te_journal_entries_l_english.yml` — replace `je_un_statistics` and `je_un_statistics_subject_seats` with:
```
 je_un_statistics:0 "\n#bold [concept_un_general_assembly]:#! [SCOPE.GetRootScope.ScriptValue('un_member_count')|0] of [SCOPE.GetRootScope.ScriptValue('un_eligible_country_count')|0] eligible nations are represented. Members hold [SCOPE.GetRootScope.ScriptValue('un_member_gdp_share')|0]% of world [Concept('concept_gdp', 'GDP')] and [SCOPE.GetRootScope.ScriptValue('un_member_pop_share')|0]% of its population.\n#bold [Concept('concept_great_power', 'Great Powers')]:#! [SCOPE.GetRootScope.ScriptValue('un_gp_member_count')|0] of [SCOPE.GetRootScope.ScriptValue('un_total_gp_count')|0] are members\n"
 je_un_statistics_suspended_one:0 "\n#bold [concept_un_general_assembly]:#! [SCOPE.GetRootScope.ScriptValue('un_member_count')|0] of [SCOPE.GetRootScope.ScriptValue('un_eligible_country_count')|0] eligible nations are represented. 1 more member state has [Concept('concept_un_suspended_representation', 'suspended representation')] because it lacks diplomatic autonomy. Members hold [SCOPE.GetRootScope.ScriptValue('un_member_gdp_share')|0]% of world [Concept('concept_gdp', 'GDP')] and [SCOPE.GetRootScope.ScriptValue('un_member_pop_share')|0]% of its population.\n#bold [Concept('concept_great_power', 'Great Powers')]:#! [SCOPE.GetRootScope.ScriptValue('un_gp_member_count')|0] of [SCOPE.GetRootScope.ScriptValue('un_total_gp_count')|0] are members\n"
 je_un_statistics_suspended_many:0 "\n#bold [concept_un_general_assembly]:#! [SCOPE.GetRootScope.ScriptValue('un_member_count')|0] of [SCOPE.GetRootScope.ScriptValue('un_eligible_country_count')|0] eligible nations are represented. [SCOPE.GetRootScope.ScriptValue('un_suspended_member_count')|0] more member states have [Concept('concept_un_suspended_representation', 'suspended representation')] because they lack diplomatic autonomy. Members hold [SCOPE.GetRootScope.ScriptValue('un_member_gdp_share')|0]% of world [Concept('concept_gdp', 'GDP')] and [SCOPE.GetRootScope.ScriptValue('un_member_pop_share')|0]% of its population.\n#bold [Concept('concept_great_power', 'Great Powers')]:#! [SCOPE.GetRootScope.ScriptValue('un_gp_member_count')|0] of [SCOPE.GetRootScope.ScriptValue('un_total_gp_count')|0] are members\n"
```

- [ ] **Step 6: The chamber** — `un_chamber_status_sgui` member branch becomes:
```
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
```
`un_chamber_dues_lines`: prepend `if = { limit = { un_representation_suspended = yes } custom_tooltip_no_bullet = je_un_chamber_dues_suspended }` (one clause per line) and turn the existing first `if` into `else_if`; append after the chain:
```
	# Seats we carry for suspended subjects (§0.8 ruling 4).
	if = {
		limit = { un_carried_seat_count > 0 }
		custom_tooltip_no_bullet = je_un_chamber_dues_carried
	}
```
Loc (`te_journal_entries_l_english.yml`):
```
 je_un_chamber_status_suspended:0 "#R Our representation is suspended.#! We do not conduct our own foreign policy, so we cast no vote and table nothing ([concept_un_suspended_representation]). #R Nobody carries our seat:#! membership brings us nothing until our overlord sits in the Assembly and pays its [concept_un_dues], or we conduct our own foreign policy again.\n"
 je_un_chamber_status_suspended_carried:0 "#R Our representation is suspended.#! We do not conduct our own foreign policy, so we cast no vote and table nothing ([concept_un_suspended_representation]). #G [THIS.GetCountry.GetOverlord.GetName] carries our seat:#! it pays our [concept_un_dues], and we keep the benefits of membership.\n"
 je_un_chamber_dues_suspended:0 "#bold [concept_un_dues]:#! none of our own while our representation is suspended. Our overlord is assessed for our seat if it is represented."
 je_un_chamber_dues_carried:0 "  Our assessment includes the seats of #v [THIS.ScriptValue('un_carried_seat_count')|0]#! subject members whose representation is suspended. While we pay, they keep the benefits of membership."
```

- [ ] **Step 7: Run the tests** — all PASS.

- [ ] **Step 8: Commit** — "UN: the journal entry and chamber say who is represented (§0.8 ruling 8)".

### Task 7: A debug option for the cases

**Files:**
- Modify: `common/scripted_effects/te_debug_un_effects.txt` (new `te_debug_un_cycle_subject_member`)
- Modify: `events/te_debug_un_events.txt` (option v)
- Modify: `localization/english/te_events_l_english.yml` (`te_debug_un.1.v`)

- [ ] **Step 1: The effect** — append to `te_debug_un_effects.txt`:
```
# §0.8's cases in one button. If one of our direct subjects is a member, move
# it along: puppet → protectorate (still a member, now represented) →
# independent. Otherwise make the weakest other independent member below
# major-power rank our puppet (suspended at once). A protectorate, not a
# dominion: the dominion needs a colonial country type.
# Scope: the player's country
te_debug_un_cycle_subject_member = {
	if = {
		limit = {
			any_direct_subject = { je:je_united_nations ?= { has_modifier = un_member_modifier } }
		}
		random_direct_subject = {
			limit = { je:je_united_nations ?= { has_modifier = un_member_modifier } }
			if = {
				limit = { is_subject_type = subject_type_puppet }
				change_subject_type = subject_type_protectorate
			}
			else = {
				make_independent = yes
			}
		}
	}
	else = {
		ordered_country = {
			limit = {
				NOT = { this = ROOT }
				is_subject = no
				je:je_united_nations ?= { has_modifier = un_member_modifier }
				country_rank < rank_value:major_power
			}
			order_by = {
				value = 0
				subtract = gdp
			}
			save_scope_as = te_debug_un_new_subject
		}
		if = {
			limit = { exists = scope:te_debug_un_new_subject }
			create_diplomatic_pact = {
				country = scope:te_debug_un_new_subject
				type = puppet
			}
		}
	}
}
```

- [ ] **Step 2: The option** — in `te_debug_un.1`, before option z:
```
	# ---- §0.8: subjects and suspended representation ----
	# Puppet the weakest minor member, or move our subject member along
	# puppet → protectorate → independent.
	option = {
		name = te_debug_un.1.v
		trigger = { has_global_variable = un_founded }
		te_debug_un_cycle_subject_member = yes
	}
```
Loc: ` te_debug_un.1.v:0 "Puppet the weakest minor member, or move our subject member along: puppet, protectorate, independent"`.

- [ ] **Step 3: Commit** — "UN debug: option v cycles a member through the §0.8 subject cases".

### Task 8: Docs, stale comments, and verification

**Files:**
- Modify: `docs/systems/un_redesign_design.md` (status banner; §0.8 "Designed" → "Built … not yet seen in-game" plus a Files list; §0.7 ruling 9 closing pointer; §0.7 ruling 5's misattribution of the +15 terms to the vote lean)
- Modify: `docs/systems/journal_entry_systems.md` (CRLF: Founding Process sentence; a "Membership and representation" bullet)
- Modify: comments in `common/scripted_triggers/un_regime_triggers.txt` (`un_regime_member_colony`), `common/scripted_effects/un_regime_effects.txt` (header and the colony-liberty block), `common/journal_entries/je_united_nations.txt` (the "a colony is not a member" note), `common/scripted_triggers/un_permanent_member_triggers.txt` (seat loss by suspension), `common/scripted_effects/un_ladder_effects.txt` (`un_leave_organisation`'s "Only this effect ends a membership" → "ends a membership by choice; suspension keeps it")

- [ ] **Step 1: Docs and comments** — as listed. In `journal_entry_systems.md`, "After founding, any recognized non-subject country can join (no tech requirement)." becomes "After founding, any country that conducts its own foreign policy can join: independent, or a dominion, protectorate or tributary (`un_membership_eligible`; no tech requirement). A member that loses that keeps its membership with its representation suspended; see `un_redesign_design.md` §0.8." Confirm `grep -c $'\r$'` equals `wc -l` afterwards.

- [ ] **Step 2: Loc housekeeping** — `python3 organize_loc.py`; check `git diff --stat localization/` touches only the new keys' files.

- [ ] **Step 3: Game-independent checks** (dummy env from CLAUDE.md):
```
export VIC3_BASE_GAME=/nonexistent VIC3_MOD_DEPLOY_TARGET=/nonexistent VIC3_VANILLA_REPO=/nonexistent VIC3_VANILLA_DOCS_RUNTIME=/nonexistent VIC3_GAME_LOGS=/nonexistent
PY=/home/jakef/src/Vic3TimelineExtended/.venv/bin/python
ls test_*.py | grep -v test_reload_post_load | sed 's/\.py$//' | xargs $PY -m unittest
$PY -m ruff check .   # or the pinned ruff CI uses
$PY scripts/format_paradox_tabs.py --check $(git diff --name-only origin/main -- '*.txt')
$PY scripts/analysis/check_localization_files.py
$PY scripts/analysis/check_post_load_rosters.py
for a in duplicate_key any_limit loc_render orphaned_event iterator_limit modifier_multiplier_var event_image treaty_leverage_side event_context silent_variable prev_scope; do $PY ${a}_audit.py --strict || echo "FAIL $a"; done
$PY kill_character_audit.py --check; $PY attitude_key_audit.py
```
Expected: all green.

- [ ] **Step 4: Reload-check the worktree on a second server** (`docs/guides/python_tools.md` § "Reload-checking a worktree branch"), as a background task:
```
cd ~/src/vic3te-un-subject-membership
VIC3_SKIP_DIGESTS_FETCH=1 /home/jakef/src/Vic3TimelineExtended/.venv/bin/python -c "import mod_state_server as m; m.PORT=8951; m.main()"
```
then `curl -s -X POST http://127.0.0.1:8951/reload` and read `warnings` for the new names (`un_member_privileges_modifier`, `concept_un_suspended_representation`, the new loc keys and triggers); `git status --short`; keep regeneration churn this branch caused (organize_loc placement, BOM), discard `docs/engine/*` and vanilla-drift churn; `kill $(cat mod_state_server.pid)`.

- [ ] **Step 5: BOM check** on every changed `.txt`/`.yml`: `for f in $(git diff --name-only origin/main -- '*.txt' '*.yml'); do head -c3 "$f" | xxd -p | grep -q efbbbf || echo "NO BOM $f"; done`.

- [ ] **Step 6: Commit** — "UN §0.8: docs, stale comments" and push; open the PR (`--base main`) with the in-game checklist from §0.8, and a note that `te_monetary_on_actions.txt`'s "NO ceased-to-be-a-subject on-action" comment is wrong (`on_become_independent` exists).
