# -*- coding: utf-8 -*-
"""Agricultural-diffusion backfill wiring (issue #460).

The five agdiff_<tech> country modifiers (+130 % arable land between them)
reach a country in one of three ways: the world-first broadcast, which only
reaches recognized countries that exist at that moment; the stateless
agdiff_backfill_diffusion_for_country, run on new countries from the formation
and release hooks; and, for the rebels in a civil war, a copy of what the
original holds (agdiff_copy_diffusion_from_root). A revolution's winner
inherits none of the loser's modifiers, so a hook that stops doing its part is
a nation that loses its Green Revolution for the rest of the game, and the
engine says nothing. These tests pin every hook, the rule that the civil-war
paths give only what the nation had (the copy reads ROOT's modifiers, and the
on_civil_war_won backstop is limited to recognized countries, the broadcast's
filter), and the first-mover restore that runs on the civil war's winner.

Run: python3 -m unittest test_agricultural_diffusion_wiring -v
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ON_ACTIONS = ROOT / "common/on_actions/extra_on_actions.txt"
EFFECTS = ROOT / "common/scripted_effects/agricultural_diffusion_effects.txt"
VALUES = ROOT / "common/script_values/agricultural_diffusion_values.txt"
EVENTS = ROOT / "events/agricultural_diffusion_events.txt"

TECHS = {
    "nitrogen_fixation",
    "modern_chemical_processes",
    "green_revolution",
    "gene_splicing",
    "biotechnology",
}

BACKFILL = "agdiff_backfill_diffusion_for_country"
COPY = "agdiff_copy_diffusion_from_root"

# Hooks whose new country is scope:target and ROOT its parent. Released
# countries get the global backfill (unfiltered, as before #460); the rebels
# get a copy of what the original holds.
RELEASE_HOOKS = (
    "on_country_released_as_independent",
    "on_country_released_as_own_subject",
    "on_country_released_as_overlord_subject",
    "on_country_released_as_company_subject",
)
UPRISING_HOOKS = ("on_revolution_start", "on_secession_start")
# Hooks whose country is ROOT.
ROOT_HOOKS = ("on_country_formed", "on_civil_war_won")


def _read(path):
    with open(path, encoding="utf-8-sig") as f:
        return re.sub(r"#[^\n]*", "", f.read())


def _blocks(text, name):
    """The bodies of every top-level ``name = { ... }`` block."""
    bodies = []
    for m in re.finditer(r"^" + re.escape(name) + r"\s*=\s*\{", text, re.M):
        depth = 0
        for i in range(m.end() - 1, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    bodies.append(text[m.end():i])
                    break
        else:
            raise AssertionError(f"{name} is not closed")
    return bodies


def _block(text, name):
    bodies = _blocks(text, name)
    if len(bodies) != 1:
        raise AssertionError(f"expected one top-level {name}, found {len(bodies)}")
    return bodies[0]


def _inner(body, key):
    """The body of the first ``key = { ... }`` (or ``key ?= { ... }``) in body."""
    m = re.search(r"(?<![\w:.])" + re.escape(key) + r"\s*\??=\s*\{", body)
    if m is None:
        return None
    depth = 0
    for i in range(m.end() - 1, len(body)):
        if body[i] == "{":
            depth += 1
        elif body[i] == "}":
            depth -= 1
            if depth == 0:
                return body[m.end():i]
    raise AssertionError(f"{key} is not closed")


def _hooked_on_actions(on_actions_text, hook):
    names = []
    for body in _blocks(on_actions_text, hook):
        listed = _inner(body, "on_actions")
        if listed:
            names += listed.split()
    return names


def _calls(body, effect, effects_text, depth=0):
    """Does body call ``effect = yes``, directly or through a scripted effect
    defined in the agdiff effects file?"""
    if re.search(r"\b" + re.escape(effect) + r"\s*=\s*yes\b", body):
        return True
    if depth > 4:
        return False
    for called in re.findall(r"\b(agdiff_\w+)\s*=\s*yes\b", body):
        bodies = _blocks(effects_text, called)
        if bodies and _calls(bodies[0], effect, effects_text, depth + 1):
            return True
    return False


class HookWiringTests(unittest.TestCase):
    def setUp(self):
        self.on_actions = _read(ON_ACTIONS)
        self.effects = _read(EFFECTS)

    def _agdiff_effect_bodies(self, hook):
        names = [n for n in _hooked_on_actions(self.on_actions, hook)
                 if n.startswith("agdiff_")]
        self.assertTrue(names, f"{hook} hooks no agdiff on_action")
        return {n: _inner(_block(self.on_actions, n), "effect") for n in names}

    def test_new_countries_get_the_backfill(self):
        for hook in RELEASE_HOOKS + ROOT_HOOKS:
            with self.subTest(hook=hook):
                bodies = self._agdiff_effect_bodies(hook)
                self.assertTrue(
                    any(_calls(b, BACKFILL, self.effects) for b in bodies.values()),
                    f"{hook} never reaches {BACKFILL}",
                )

    def test_release_hooks_backfill_the_new_country_guarded(self):
        # The released country is scope:target; ROOT is its parent, which
        # already has the modifiers.
        for hook in RELEASE_HOOKS:
            with self.subTest(hook=hook):
                for name, body in self._agdiff_effect_bodies(hook).items():
                    self.assertRegex(body, r"scope:target\s*\?=\s*\{",
                                     f"{name} must scope into scope:target with ?=")
                    target = _inner(body, "scope:target")
                    self.assertTrue(_calls(target, BACKFILL, self.effects),
                                    f"{name} does not backfill scope:target")

    def test_rebels_get_a_copy_of_the_original_not_the_backfill(self):
        # The winner continues the nation: the rebels get what the original
        # holds, never what the global flags say, so an unrecognized nation's
        # rebels gain nothing the broadcast never gave it.
        for hook in UPRISING_HOOKS:
            with self.subTest(hook=hook):
                for name, body in self._agdiff_effect_bodies(hook).items():
                    self.assertRegex(body, r"scope:target\s*\?=\s*\{",
                                     f"{name} must scope into scope:target with ?=")
                    target = _inner(body, "scope:target")
                    self.assertTrue(_calls(target, COPY, self.effects),
                                    f"{name} does not copy the original's diffusion")
                    self.assertFalse(_calls(body, BACKFILL, self.effects),
                                     f"{name} must not run the global backfill")

    def test_copy_reads_the_originals_modifiers(self):
        one = _block(self.effects, "agdiff_copy_one_tech_from_root")
        limit = _inner(one, "limit")
        self.assertRegex(limit, r"root\s*=\s*\{\s*has_modifier\s*=\s*agdiff_\$TECH\$\s*\}")
        self.assertRegex(limit, r"NOT\s*=\s*\{\s*has_modifier\s*=\s*agdiff_\$TECH\$\s*\}")
        self.assertNotIn("has_global_variable", one)
        self.assertEqual(
            set(re.findall(r"agdiff_copy_one_tech_from_root\s*=\s*\{\s*TECH\s*=\s*(\w+)",
                           _block(self.effects, COPY))),
            TECHS,
        )

    def test_civil_war_won_repairs_the_winner_as_root(self):
        bodies = self._agdiff_effect_bodies("on_civil_war_won")
        for name, body in bodies.items():
            # Bare call: the restore's multiplier resolves against ROOT, which
            # is the winner only outside any scope change.
            self.assertNotRegex(body, r"scope:|every_|random_|any_",
                                f"{name} must call the repair on ROOT directly")
        joined = "\n".join(bodies.values())
        self.assertTrue(_calls(joined, "agdiff_restore_first_mover_prestige", self.effects))
        repair = _block(self.effects, "agdiff_repair_after_civil_war")
        self.assertEqual(
            set(re.findall(r"agdiff_repoint_first_country\s*=\s*\{\s*TECH\s*=\s*(\w+)", repair)),
            TECHS,
        )

    def test_civil_war_won_backfill_is_recognized_only(self):
        # The backstop is for wars begun before the rebels got the copy. It
        # uses the broadcast's own filter, so a winner of any other type
        # (a loyalist one included) gains nothing its nation never had.
        repair = _block(self.effects, "agdiff_repair_after_civil_war")
        backfill_calls = re.findall(r"\b" + BACKFILL + r"\s*=\s*yes", repair)
        self.assertEqual(len(backfill_calls), 1)
        gated = _inner(repair, "if")
        self.assertIsNotNone(gated)
        self.assertRegex(_inner(gated, "limit"), r"is_country_type\s*=\s*recognized")
        self.assertIn(BACKFILL + " = yes", gated)
        broadcast = _block(self.effects, "agdiff_handle_tech_acquired_effect")
        self.assertRegex(broadcast, r"is_country_type\s*=\s*recognized")


class TechListTests(unittest.TestCase):
    def test_backfill_covers_every_broadcast_tech(self):
        on_actions = _read(ON_ACTIONS)
        effects = _read(EFFECTS)
        dispatched = set(re.findall(
            r"agdiff_dispatch_if_first\s*=\s*\{\s*TECH\s*=\s*(\w+)",
            _block(on_actions, "agricultural_diffusion_on_action"),
        ))
        backfilled = set(re.findall(
            r"agdiff_backfill_one_tech\s*=\s*\{\s*TECH\s*=\s*(\w+)",
            _block(effects, BACKFILL),
        ))
        self.assertEqual(dispatched, TECHS)
        self.assertEqual(backfilled, TECHS)


class FirstMoverTests(unittest.TestCase):
    def setUp(self):
        self.effects = _read(EFFECTS)

    def test_grant_month_is_recorded_with_the_title(self):
        body = _block(self.effects, "agdiff_handle_tech_acquired_effect")
        guarded = _inner(body, "if")
        self.assertIn("name = is_world_first_$TECH$", guarded)
        self.assertRegex(
            guarded,
            r"set_variable\s*=\s*\{\s*name\s*=\s*agdiff_first_mover_month\s+"
            r"value\s*=\s*te_history_month_index\s*\}",
        )

    def test_restore_is_idempotent_and_bounded(self):
        body = _block(self.effects, "agdiff_restore_first_mover_prestige")
        limit = _inner(body, "limit")
        self.assertRegex(limit, r"NOT\s*=\s*\{\s*has_modifier\s*=\s*agdiff_first_mover_prestige\s*\}")
        self.assertIn("has_variable = agdiff_first_mover_month", limit)
        self.assertRegex(limit, r"agdiff_first_mover_months_left\s*>\s*5")
        self.assertRegex(limit, r"root\s*\?=\s*this")

    def test_restore_matches_the_event_grant(self):
        # Same duration and decay as the .a_first options, scaled to what was
        # left of the original 20 years.
        events = _read(EVENTS)
        grants = re.findall(
            r"add_modifier\s*=\s*\{\s*name\s*=\s*agdiff_first_mover_prestige\s+([^}]*)\}",
            events,
        )
        self.assertEqual(len(grants), len(TECHS))
        grant_days = {re.search(r"days\s*=\s*(\w+)", g).group(1) for g in grants}
        self.assertEqual(grant_days, {"very_long_modifier_time"})
        self.assertTrue(all(re.search(r"is_decaying\s*=\s*yes", g) for g in grants))

        # The restore reads whole years left, to the nearest, off a ladder of
        # literal durations: rung k covers 12k-6 .. 12k+5 months left, and its
        # top rung is the grant's own very_long_modifier_time (7300 days).
        restore = _block(self.effects, "agdiff_restore_first_mover_prestige")
        rungs = re.findall(
            r"limit\s*=\s*\{\s*agdiff_first_mover_months_left\s*>\s*(\d+)\s*\}\s*"
            r"add_modifier\s*=\s*\{([^}]*)\}",
            restore,
        )
        self.assertEqual(len(rungs), 20)
        for k, (threshold, modifier) in zip(range(20, 0, -1), rungs):
            with self.subTest(years=k):
                self.assertEqual(int(threshold), 12 * k - 7)
                self.assertIn("name = agdiff_first_mover_prestige", modifier)
                self.assertRegex(modifier, r"days\s*=\s*%d\b" % (365 * k))
                self.assertIn("multiplier = agdiff_first_mover_strength_left", modifier)
                self.assertIn("is_decaying = yes", modifier)
        self.assertEqual(len(re.findall(r"add_modifier", restore)), 20)

        values = _read(VALUES)
        total = _block(values, "agdiff_first_mover_months_total")
        self.assertIn("value = very_long_modifier_time", total)
        strength = _block(values, "agdiff_first_mover_strength_left")
        self.assertIn("min = 0", strength)
        self.assertIn("max = 1", strength)


if __name__ == "__main__":
    unittest.main()
