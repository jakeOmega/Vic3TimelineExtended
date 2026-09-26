# -*- coding: utf-8 -*-
"""Civil rights across a revolution (issue #463, civil-war audit F4).

A revolution's winner inherits the loser's variables but no modifiers, and gets
fresh records of the journal entries the loser had finished. je_civil_rights
therefore records its resolution, its outcome modifier and its button policies
in variables, and rebuilds the modifiers at on_civil_war_won
(common/scripted_effects/civil_rights_effects.txt § REVOLUTION CONTINUITY).
None of it is checked by the engine, and every piece is a list that has to stay
in step with another list. These tests pin the pairings.
"""

import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))


def _path(*parts):
    return os.path.join(REPO, *parts)


def _read(*parts):
    with open(_path(*parts), encoding="utf-8-sig") as f:
        return re.sub(r"#[^\n]*", "", f.read())


def _close(text, open_brace):
    depth = 0
    for i in range(open_brace, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return i
    raise AssertionError("unbalanced braces")


def _block(text, name, top_level=True):
    """The body of the first ``name = { ... }`` block (top-level by default)."""
    anchor = r"^" if top_level else r"(?<![\w.:])"
    m = re.search(anchor + re.escape(name) + r"\s*=\s*\{", text, re.M)
    if m is None:
        raise AssertionError(f"{name} not found")
    return text[m.end():_close(text, m.end() - 1)]


JE = ("common", "journal_entries", "je_civil_rights.txt")
EFFECTS = ("common", "scripted_effects", "civil_rights_effects.txt")
BUTTONS = ("common", "scripted_buttons", "civil_rights_buttons.txt")
EVENTS = ("events", "movement_events_te.txt")
ON_ACTIONS = ("common", "on_actions", "civil_rights_on_actions.txt")

# The button policy each mirror stands for.
MIRRORS = {
    "cr_grassroots_modifier": "cr_policy_grassroots",
    "cr_federal_protection_modifier": "cr_policy_federal",
    "cr_gradualist_modifier": "cr_policy_gradualist",
    "cr_cooptation_modifier": "cr_policy_cooptation",
    "cr_suppression_modifier": "cr_policy_suppression",
    "cr_segregationist_modifier": "cr_policy_segregationist",
}


def _je_block(name):
    return _block(_block(_read(*JE), "je_civil_rights"), name, top_level=False)


def _param_calls(text, effect, param="MODIFIER"):
    return re.findall(re.escape(effect) + r"\s*=\s*\{\s*" + param + r"\s*=\s*(\w+)\s*\}", text)


class ResolutionGuardTests(unittest.TestCase):
    def test_complete_and_fail_record_the_resolution(self):
        for hook in ("on_complete", "on_fail"):
            with self.subTest(hook=hook):
                self.assertRegex(_je_block(hook), r"set_variable\s*=\s*civil_rights_resolved\b")

    def test_invalid_does_not(self):
        self.assertNotIn("civil_rights_resolved", _je_block("on_invalid"))

    def test_activation_requires_its_absence(self):
        for gate in ("is_shown_when_inactive", "possible"):
            with self.subTest(gate=gate):
                self.assertRegex(
                    _je_block(gate),
                    r"NOT\s*=\s*\{\s*has_variable\s*=\s*civil_rights_resolved\s*\}",
                )


class RunLifecycleTests(unittest.TestCase):
    RESETS = [
        r"set_variable\s*=\s*\{\s*name\s*=\s*cr_\w+_months\s+value\s*=\s*0\s*\}",
        r"remove_variable\s*=\s*cr_tier_\d+_seen",
        r"set_bar_progress",
    ]

    def test_immediate_resets_only_a_fresh_run(self):
        immediate = _je_block("immediate")
        m = re.search(
            r"if\s*=\s*\{\s*limit\s*=\s*\{\s*NOT\s*=\s*\{\s*has_variable\s*=\s*cr_run_in_progress\s*\}\s*\}",
            immediate,
        )
        self.assertIsNotNone(m, "immediate has no fresh-run guard")
        start = immediate.index("{", m.start())
        end = _close(immediate, start)
        guarded, outside = immediate[start:end], immediate[:m.start()] + immediate[end:]
        self.assertRegex(guarded, r"set_variable\s*=\s*cr_run_in_progress\b")
        self.assertEqual(len(re.findall(self.RESETS[0], guarded)), 6)
        self.assertEqual(len(re.findall(self.RESETS[1], guarded)), 4)
        for pattern in self.RESETS:
            with self.subTest(pattern=pattern):
                self.assertIsNone(re.search(pattern, outside), "reset outside the guard")

    def test_every_end_hook_ends_the_run(self):
        cleanup = _block(_read(*EFFECTS), "cr_je_cleanup_effect")
        self.assertIn("remove_variable = cr_run_in_progress", cleanup)
        for mod, var in MIRRORS.items():
            with self.subTest(policy=mod):
                self.assertIn(f"remove_modifier = {mod}", cleanup)
                self.assertIn(f"remove_variable = {var}", cleanup)
        for hook in ("on_complete", "on_fail", "on_invalid"):
            with self.subTest(hook=hook):
                self.assertIn("cr_je_cleanup_effect = yes", _je_block(hook))


class OutcomeModifierTests(unittest.TestCase):
    def _resolution_events(self):
        ids = set()
        for hook in ("on_complete", "on_fail"):
            ids |= set(re.findall(r"id\s*=\s*(movement_events_te\.\d+)", _je_block(hook)))
        self.assertTrue(ids)
        return ids

    def test_every_outcome_modifier_is_recorded_by_its_option(self):
        events = _read(*EVENTS)
        recorded = set()
        for eid in sorted(self._resolution_events()):
            body = _block(events, eid)
            for om in re.finditer(r"(?<![\w.:])option\s*=\s*\{", body):
                option = body[om.end():_close(body, om.end() - 1)]
                # Only the option's own add_modifier lines: a modifier added to a
                # political movement inside an iterator is not a country modifier.
                adds = re.findall(r"^\t\tadd_modifier\s*=\s*\{\s*name\s*=\s*(\w+)", option, re.M)
                for mod in adds:
                    with self.subTest(event=eid, modifier=mod):
                        pattern = re.compile(
                            r"^\t\tadd_modifier\s*=\s*\{\s*name\s*=\s*" + mod
                            + r"\s+days\s*=\s*long_modifier_time\s+is_decaying\s*=\s*yes\s*\}\s*"
                            r"cr_record_outcome_modifier\s*=\s*\{\s*MODIFIER\s*=\s*" + mod + r"\s*\}",
                            re.M,
                        )
                        self.assertRegex(option, pattern)
                        recorded.add(mod)
        self.assertEqual(recorded, set(_param_calls(events, "cr_record_outcome_modifier")))
        self.assertEqual(len(recorded), 12)

    def test_rebuild_and_forget_lists_match_the_records(self):
        effects = _read(*EFFECTS)
        recorded = set(_param_calls(_read(*EVENTS), "cr_record_outcome_modifier"))
        rebuilt = _param_calls(_block(effects, "cr_rebuild_outcome_modifiers"), "cr_rebuild_outcome_modifier")
        self.assertEqual(sorted(rebuilt), sorted(recorded))
        forgotten = set(re.findall(r"remove_variable\s*=\s*cr_outcome_(\w+)",
                                   _block(effects, "cr_forget_outcome_modifiers")))
        self.assertEqual(forgotten, recorded | {"months"})

    def test_migration_reads_only_resolution_only_modifiers(self):
        effects = _read(*EFFECTS)
        update = _block(effects, "cr_outcome_monthly_update")
        migrated = set(_param_calls(update, "cr_migrate_outcome_modifier"))
        tested = set(re.findall(r"has_modifier\s*=\s*(\w+)", update))
        self.assertEqual(migrated, tested)
        recorded = set(_param_calls(_read(*EVENTS), "cr_record_outcome_modifier"))
        self.assertLessEqual(migrated, recorded)
        # A modifier something else also grants would mark a country resolved
        # that never was. This is the only check that catches a new grant site
        # (say, a later event reusing a triumph modifier), so scan everything.
        sources = []
        for root in ("common", "events"):
            for dirpath, _dirs, files in os.walk(_path(root)):
                for name in files:
                    if name.endswith(".txt"):
                        sources.append(_read(os.path.relpath(os.path.join(dirpath, name), REPO)))
        corpus = "\n".join(sources)
        for mod in recorded:
            grants = len(re.findall(r"name\s*=\s*" + mod + r"\b", corpus))
            with self.subTest(modifier=mod):
                if mod in migrated:
                    self.assertEqual(grants, 1, "migrated modifier has another source")
                else:
                    self.assertGreater(grants, 1, "resolution-only modifier left out of the migration")

    def test_rebuild_ladder_restores_what_was_left(self):
        body = _block(_read(*EFFECTS), "cr_rebuild_outcome_modifier")
        steps = re.findall(
            r"var:cr_outcome_months\s*<\s*(\d+)\s*\}\s*add_modifier\s*=\s*\{\s*name\s*=\s*\$MODIFIER\$\s+"
            r"days\s*=\s*(\d+)\s+multiplier\s*=\s*([\d.]+)\s+is_decaying\s*=\s*yes\s*\}",
            body,
        )
        self.assertEqual(len(steps), 10)
        for i, (below, days, mult) in enumerate(steps):
            with self.subTest(step=i):
                years_left = 10 - i
                self.assertEqual(int(below), 6 + 12 * i)  # nearest whole year
                self.assertEqual(int(days), 365 * years_left)  # long_modifier_time = 3650
                self.assertAlmostEqual(float(mult), years_left / 10)
        self.assertRegex(body, r"NOT\s*=\s*\{\s*has_modifier\s*=\s*\$MODIFIER\$\s*\}")

    def test_counter_runs_ten_years(self):
        update = _block(_read(*EFFECTS), "cr_outcome_monthly_update")
        self.assertRegex(update, r"change_variable\s*=\s*\{\s*name\s*=\s*cr_outcome_months\s+add\s*=\s*1\s*\}")
        self.assertRegex(update, r"var:cr_outcome_months\s*>=\s*120\s*\}\s*cr_forget_outcome_modifiers\s*=\s*yes")

    def test_a_record_without_its_modifier_is_forgotten(self):
        # Round 2 (review I1): the old-save migration guesses the modifier's age.
        # Without this a migrated record could outlive its modifier, and a later
        # revolution would bring back a reward or penalty that had run out.
        effects = _read(*EFFECTS)
        update = _block(effects, "cr_outcome_monthly_update")
        recorded = set(_param_calls(_read(*EVENTS), "cr_record_outcome_modifier"))
        self.assertEqual(sorted(_param_calls(update, "cr_forget_lapsed_outcome")), sorted(recorded))
        helper = _block(effects, "cr_forget_lapsed_outcome")
        self.assertRegex(
            helper,
            r"has_variable\s*=\s*cr_outcome_\$MODIFIER\$\s+NOT\s*=\s*\{\s*has_modifier\s*=\s*\$MODIFIER\$\s*\}"
            r"\s*\}\s*cr_forget_outcome_modifiers\s*=\s*yes",
        )
        # Only from the monthly pulse: the merge and on_civil_war_won share a tick,
        # and anything that ran between them would forget a record the hook is
        # about to rebuild.
        callers = []
        for root in ("common", "events"):
            for dirpath, _dirs, files in os.walk(_path(root)):
                for name in files:
                    if name.endswith(".txt"):
                        rel = os.path.relpath(os.path.join(dirpath, name), REPO)
                        if re.search(r"cr_forget_lapsed_outcome\s*=\s*\{\s*MODIFIER", _read(rel)):
                            callers.append(rel)
        self.assertEqual(callers, [os.path.join(*EFFECTS)])
        stripped = effects.replace(update, "")
        self.assertNotRegex(stripped, r"cr_forget_lapsed_outcome\s*=\s*\{\s*MODIFIER")


class PolicyMirrorTests(unittest.TestCase):
    def test_buttons_keep_modifier_and_mirror_in_step(self):
        buttons = _read(*BUTTONS)
        for name in re.findall(r"^(cr_\w+)\s*=\s*\{", buttons, re.M):
            effect = _block(_block(buttons, name), "effect", top_level=False)
            added = re.findall(r"add_modifier\s*=\s*\{\s*name\s*=\s*(\w+)", effect)
            removed = [m for m in re.findall(r"remove_modifier\s*=\s*(\w+)", effect) if m in MIRRORS]
            with self.subTest(button=name):
                self.assertEqual(len(added) + len(removed), 1)
                if added:
                    self.assertIn(f"set_variable = {MIRRORS[added[0]]}", effect)
                else:
                    self.assertIn(f"remove_variable = {MIRRORS[removed[0]]}", effect)

    def test_sync_covers_every_policy(self):
        sync = _block(_read(*EFFECTS), "cr_sync_policy_mirrors")
        pairs = dict(re.findall(
            r"cr_sync_policy_mirror\s*=\s*\{\s*MODIFIER\s*=\s*(\w+)\s+VAR\s*=\s*(\w+)\s*\}", sync))
        self.assertEqual(pairs, MIRRORS)

    def test_pulse_self_heals_before_counting(self):
        pulse = _je_block("on_monthly_pulse")
        heal = pulse.index("cr_sync_policy_mirrors = yes")
        for mod, var in MIRRORS.items():
            with self.subTest(policy=mod):
                m = re.search(
                    r"OR\s*=\s*\{\s*has_modifier\s*=\s*" + mod + r"\s+has_variable\s*=\s*" + var
                    + r"\s*\}\s*\}\s*change_variable", pulse)
                self.assertIsNotNone(m)
                self.assertLess(heal, m.start())
        # Round 2 (review M3): the expiry marker, like the counters, must not wait
        # a month for a policy the self-heal has just re-added.
        m = re.search(r"OR\s*=\s*\{\s*has_modifier\s*=\s*cr_cooptation_modifier\s+has_variable\s*=\s*"
                      r"cr_policy_cooptation\s*\}\s*var:cr_cooptation_months\s*>=\s*12\s+"
                      r"NOT\s*=\s*\{\s*has_modifier\s*=\s*cr_cooptation_expired\s*\}\s*\}\s*"
                      r"add_modifier\s*=\s*\{\s*name\s*=\s*cr_cooptation_expired\s*\}", pulse)
        self.assertIsNotNone(m)
        self.assertLess(heal, m.start())


    def test_only_buttons_and_the_entry_touch_the_policy_modifiers(self):
        # cr_sync_policy_mirror re-adds a policy whose mirror is set. That is safe
        # only while nothing but the buttons (which move the mirror with it) and
        # the entry's own cleanup adds or removes these modifiers; an event that
        # handed one out as flavour would become a policy the player can't drop.
        allowed = {
            os.path.join(*BUTTONS), os.path.join(*EFFECTS), os.path.join(*JE),
        }
        names = "|".join(list(MIRRORS) + ["cr_cooptation_expired"])
        pattern = re.compile(
            r"(?:add_modifier\s*=\s*\{\s*name\s*=\s*|add_modifier\s*=\s*|remove_modifier\s*=\s*)(?:"
            + names + r")\b")
        for root in ("common", "events"):
            for dirpath, _dirs, files in os.walk(_path(root)):
                for name in files:
                    if not name.endswith(".txt"):
                        continue
                    rel = os.path.relpath(os.path.join(dirpath, name), REPO)
                    if rel in allowed:
                        continue
                    with self.subTest(file=rel):
                        self.assertIsNone(pattern.search(_read(rel)))


class HookTests(unittest.TestCase):
    def test_on_actions_are_wired(self):
        text = _read(*ON_ACTIONS)
        self.assertIn("civil_rights_civil_war_won_on_action",
                      _block(_block(text, "on_civil_war_won"), "on_actions", top_level=False))
        self.assertIn("cr_after_civil_war = yes", _block(text, "civil_rights_civil_war_won_on_action"))
        for hook in ("on_revolution_start", "on_secession_start"):
            with self.subTest(hook=hook):
                self.assertIn("civil_rights_revolution_start_on_action",
                              _block(_block(text, hook), "on_actions", top_level=False))
        self.assertRegex(_block(text, "civil_rights_revolution_start_on_action"),
                         r"set_variable\s*=\s*\{\s*name\s*=\s*cr_revolution_original\s+value\s*=\s*ROOT\s*\}")
        self.assertIn("civil_rights_country_monthly_on_action",
                      _block(_block(text, "on_monthly_pulse_country"), "on_actions", top_level=False))
        self.assertIn("cr_outcome_monthly_update = yes", _block(text, "civil_rights_country_monthly_on_action"))

    def test_the_side_that_won_decides(self):
        body = _block(_read(*EFFECTS), "cr_after_civil_war")
        self.assertRegex(
            body,
            r"var:cr_revolution_original\s*=\s*ROOT\s*\}\s*cr_drop_rebel_run_state\s*=\s*yes\s*\}\s*"
            r"else\s*=\s*\{\s*cr_rebuild_after_civil_war\s*=\s*yes\s*"
            r"set_variable\s*=\s*\{\s*name\s*=\s*cr_revolution_original\s+value\s*=\s*ROOT\s*\}\s*\}",
        )
        # Round 2 (review M2): a secession and a revolution can run at once, and
        # the war that ends second must still find the pointer.
        for parts in (EFFECTS, ON_ACTIONS):
            with self.subTest(file=os.path.join(*parts)):
                self.assertNotIn("remove_variable = cr_revolution_original", _read(*parts))

    def test_rebuild_restores_outcome_and_a_running_struggle(self):
        body = _block(_read(*EFFECTS), "cr_rebuild_after_civil_war")
        self.assertIn("cr_rebuild_outcome_modifiers = yes", body)
        self.assertRegex(
            body,
            r"has_variable\s*=\s*cr_run_in_progress\s+has_journal_entry\s*=\s*je_civil_rights\s*\}\s*"
            r"cr_sync_policy_mirrors\s*=\s*yes",
        )
        self.assertRegex(body, r"NOT\s*=\s*\{\s*has_modifier\s*=\s*cr_cooptation_expired\s*\}")

    def test_loyalists_drop_what_the_rebels_ran(self):
        body = _block(_read(*EFFECTS), "cr_drop_rebel_run_state")
        pairs = dict(re.findall(
            r"cr_drop_rebel_policy_mirror\s*=\s*\{\s*MODIFIER\s*=\s*(\w+)\s+VAR\s*=\s*(\w+)\s*\}", body))
        self.assertEqual(pairs, MIRRORS)
        self.assertRegex(body, r"NOT\s*=\s*\{\s*has_journal_entry\s*=\s*je_civil_rights\s*\}\s*\}\s*"
                               r"cr_je_cleanup_effect\s*=\s*yes")

    def test_orphaned_run_state_is_swept(self):
        update = _block(_read(*EFFECTS), "cr_outcome_monthly_update")
        self.assertRegex(update, r"has_variable\s*=\s*cr_run_in_progress\s+NOT\s*=\s*\{\s*"
                                 r"has_journal_entry\s*=\s*je_civil_rights\s*\}\s*\}\s*cr_je_cleanup_effect\s*=\s*yes")


class OtherDebatesTests(unittest.TestCase):
    """A finished Human Augmentation or Mental Health debate must not replay on a winner."""

    CASES = {
        ("common", "journal_entries", "je_human_augmentation.txt"): ("je_human_augmentation", "human_augmentation_resolved"),
        ("common", "journal_entries", "je_mental_health.txt"): ("je_mental_health_crisis", "mental_health_crisis_resolved"),
    }

    def test_every_end_records_and_activation_checks(self):
        for parts, (je, var) in self.CASES.items():
            body = _block(_read(*parts), je)
            for hook in ("on_complete", "on_fail", "on_timeout"):
                with self.subTest(je=je, hook=hook):
                    self.assertRegex(_block(body, hook, top_level=False), r"set_variable\s*=\s*" + var + r"\b")
            for gate in ("is_shown_when_inactive", "possible"):
                with self.subTest(je=je, gate=gate):
                    self.assertRegex(_block(body, gate, top_level=False),
                                     r"NOT\s*=\s*\{\s*has_variable\s*=\s*" + var + r"\s*\}")

    def test_rebels_do_not_start_these_entries(self):
        # Round 2 (review M1). In is_shown_when_inactive only, as vanilla does
        # (je_the_two_spains, je_risorgimento): it then cannot touch an active
        # record, such as one a revolution's winner inherits.
        cases = dict(self.CASES)
        cases[JE] = ("je_civil_rights", None)
        for parts, (je, _var) in cases.items():
            body = _block(_read(*parts), je)
            with self.subTest(je=je):
                self.assertRegex(_block(body, "is_shown_when_inactive", top_level=False),
                                 r"is_revolutionary\s*=\s*no\b")
                self.assertNotIn("is_revolutionary", _block(body, "possible", top_level=False))
                self.assertNotRegex(body, r"can_deactivate\s*=\s*yes")


if __name__ == "__main__":
    unittest.main()
