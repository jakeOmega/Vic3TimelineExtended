# -*- coding: utf-8 -*-
"""Agricultural-diffusion backfill wiring (issue #460).

The five agdiff_<tech> country modifiers (+130 % arable land between them)
reach a country in one of two ways: the world-first broadcast, which only
reaches countries that exist at that moment, or the stateless
agdiff_backfill_diffusion_for_country, run from a set of on_action hooks. The
rebels in a civil war are a new country object, and a revolution's winner
inherits none of the loser's modifiers, so a hook that stops calling the
backfill is a nation that loses its Green Revolution for the rest of the game.
The engine says nothing. These tests pin every hook, and the first-mover
restore that runs on the civil war's winner.

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

# Hooks whose new country is scope:target (ROOT is the parent).
TARGET_HOOKS = (
    "on_country_released_as_independent",
    "on_country_released_as_own_subject",
    "on_country_released_as_overlord_subject",
    "on_country_released_as_company_subject",
    "on_revolution_start",
    "on_secession_start",
)
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

    def test_every_hook_runs_the_backfill(self):
        for hook in TARGET_HOOKS + ROOT_HOOKS:
            with self.subTest(hook=hook):
                bodies = self._agdiff_effect_bodies(hook)
                self.assertTrue(
                    any(_calls(b, BACKFILL, self.effects) for b in bodies.values()),
                    f"{hook} never reaches {BACKFILL}",
                )

    def test_target_hooks_backfill_the_new_country_guarded(self):
        # The released or uprising country is scope:target; ROOT is its
        # parent, which already has the modifiers.
        for hook in TARGET_HOOKS:
            with self.subTest(hook=hook):
                for name, body in self._agdiff_effect_bodies(hook).items():
                    self.assertRegex(body, r"scope:target\s*\?=\s*\{",
                                     f"{name} must scope into scope:target with ?=")
                    target = _inner(body, "scope:target")
                    self.assertTrue(_calls(target, BACKFILL, self.effects),
                                    f"{name} does not backfill scope:target")

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
        self.assertRegex(limit, r"agdiff_first_mover_months_left\s*>\s*0")
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

        restore = _inner(_block(self.effects, "agdiff_restore_first_mover_prestige"), "add_modifier")
        self.assertIn("name = agdiff_first_mover_prestige", restore)
        self.assertIn("days = very_long_modifier_time", restore)
        self.assertIn("is_decaying = yes", restore)
        self.assertIn("multiplier = agdiff_first_mover_strength_left", restore)

        values = _read(VALUES)
        total = _block(values, "agdiff_first_mover_months_total")
        self.assertIn("value = very_long_modifier_time", total)
        strength = _block(values, "agdiff_first_mover_strength_left")
        self.assertIn("min = 0", strength)
        self.assertIn("max = 1", strength)


if __name__ == "__main__":
    unittest.main()
