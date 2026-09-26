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
engine says nothing. The civil-war half hangs off the shared hooks in
te_civil_war_on_actions.txt (agdiff_on_uprising from te_civil_war_on_start,
agdiff_repair_after_civil_war from te_civil_war_on_won). These tests pin every
hook, the rule that the civil-war paths give only what the nation had (the
copy reads ROOT's modifiers and marks the rebels, and the on_civil_war_won
backstop runs only for rebels who won a revolution without the copy, i.e. one
begun before the copy existed, and only if recognized, the broadcast's
filter), and the first-mover restore that runs on the civil war's winner.

Run: python3 -m unittest test_agricultural_diffusion_wiring -v
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ON_ACTIONS = ROOT / "common/on_actions/extra_on_actions.txt"
CW_ON_ACTIONS = ROOT / "common/on_actions/te_civil_war_on_actions.txt"
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
MARKER = "agdiff_cw_copied"

# Hooks whose new country is scope:target and ROOT its parent. Released
# countries get the global backfill (unfiltered, as before #460).
RELEASE_HOOKS = (
    "on_country_released_as_independent",
    "on_country_released_as_own_subject",
    "on_country_released_as_overlord_subject",
    "on_country_released_as_company_subject",
)
# Hooks whose country is ROOT.
ROOT_HOOKS = ("on_country_formed",)
# The civil-war hooks, and the shared on_action each reaches in
# te_civil_war_on_actions.txt.
UPRISING_HOOKS = ("on_revolution_start", "on_secession_start")
CIVIL_WAR_HOOKS = UPRISING_HOOKS + ("on_civil_war_won",)


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

    def test_civil_war_hooks_are_only_the_shared_ones(self):
        # agdiff's own civil-war hook blocks are gone: a second declaration
        # would run the copy or the repair twice.
        for hook in CIVIL_WAR_HOOKS:
            with self.subTest(hook=hook):
                self.assertEqual(
                    [n for n in _hooked_on_actions(self.on_actions, hook)
                     if n.startswith("agdiff_")],
                    [],
                )

    def test_rebels_get_a_copy_of_the_original_not_the_backfill(self):
        # The winner continues the nation: the rebels get what the original
        # holds, never what the global flags say, so an unrecognized nation's
        # rebels gain nothing the broadcast never gave it.
        cw = _read(CW_ON_ACTIONS)
        for hook in UPRISING_HOOKS:
            with self.subTest(hook=hook):
                self.assertIn("te_civil_war_on_start", _hooked_on_actions(cw, hook))
        start = _inner(_block(cw, "te_civil_war_on_start"), "effect")
        self.assertRegex(start, r"\bagdiff_on_uprising\s*=\s*yes\b")
        uprising = _block(self.effects, "agdiff_on_uprising")
        self.assertRegex(uprising, r"scope:target\s*\?=\s*\{",
                         "agdiff_on_uprising must scope into scope:target with ?=")
        target = _inner(uprising, "scope:target")
        self.assertTrue(_calls(target, COPY, self.effects),
                        "agdiff_on_uprising does not copy the original's diffusion")
        self.assertFalse(_calls(uprising, BACKFILL, self.effects),
                         "agdiff_on_uprising must not run the global backfill")
        # ...and marks them, so the on_civil_war_won backstop knows this
        # war's rebels had the copy.
        self.assertRegex(target, r"\bset_variable\s*=\s*" + MARKER + r"\b",
                         f"agdiff_on_uprising must mark the rebels with {MARKER}")
        self.assertNotIn(MARKER, uprising.replace(target, ""),
                         f"agdiff_on_uprising must set {MARKER} on the rebels only")

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
        cw = _read(CW_ON_ACTIONS)
        self.assertIn("te_civil_war_on_won", _hooked_on_actions(cw, "on_civil_war_won"))
        won = _inner(_block(cw, "te_civil_war_on_won"), "effect")
        call = re.search(r"\bagdiff_repair_after_civil_war\s*=\s*yes\b", won)
        self.assertIsNotNone(call, "te_civil_war_on_won must call agdiff_repair_after_civil_war")
        # Bare call: the restore's multiplier resolves against ROOT, which is
        # the winner only outside any scope change...
        depth = won[:call.start()].count("{") - won[:call.start()].count("}")
        self.assertEqual(depth, 0, "the repair must be called on ROOT directly")
        # ...and between resolve (which sets te_cw_rebels_won) and clear
        # (which removes it).
        resolve = won.index("te_civil_war_resolve_sides")
        clear = won.index("te_civil_war_clear")
        self.assertLess(resolve, call.start())
        self.assertLess(call.start(), clear)
        self.assertTrue(_calls(won, "agdiff_restore_first_mover_prestige", self.effects))
        repair = _block(self.effects, "agdiff_repair_after_civil_war")
        self.assertEqual(
            set(re.findall(r"agdiff_repoint_first_country\s*=\s*\{\s*TECH\s*=\s*(\w+)", repair)),
            TECHS,
        )

    def test_civil_war_won_backfill_only_for_uncopied_rebel_winners(self):
        # The backstop is for revolutions begun before the rebels got the
        # copy, and only the rebels' side needs it. It runs only when the
        # shared layer says the revolutionaries won (a loyalist winner keeps
        # its own modifiers, and a secession is never a new regime), when the
        # winner carries no copy marker, and when it is recognized (the
        # broadcast's filter). A recognized type alone is not enough: the
        # decolonization tech makes laggards recognized without the
        # diffusion.
        repair = _block(self.effects, "agdiff_repair_after_civil_war")
        backfill_calls = re.findall(r"\b" + BACKFILL + r"\s*=\s*yes", repair)
        self.assertEqual(len(backfill_calls), 1)
        gated = _inner(repair, "if")
        self.assertIsNotNone(gated)
        limit = _inner(gated, "limit")
        self.assertIn("has_variable = te_cw_rebels_won", limit)
        self.assertRegex(limit, r"var:te_cw_rebels_won\s*=\s*1\b")
        self.assertRegex(limit, r"NOT\s*=\s*\{\s*has_variable\s*=\s*" + MARKER + r"\s*\}")
        self.assertRegex(limit, r"is_country_type\s*=\s*recognized")
        self.assertIn(BACKFILL + " = yes", gated)
        broadcast = _block(self.effects, "agdiff_handle_tech_acquired_effect")
        self.assertRegex(broadcast, r"is_country_type\s*=\s*recognized")

    def test_marker_is_removed_after_the_gate(self):
        # Read once, then dropped (guarded, house style): a winner that later
        # faces a war begun before this build must not be mistaken for one
        # that had the copy.
        repair = _block(self.effects, "agdiff_repair_after_civil_war")
        removal = re.search(
            r"if\s*=\s*\{\s*limit\s*=\s*\{\s*has_variable\s*=\s*" + MARKER
            + r"\s*\}\s*remove_variable\s*=\s*" + MARKER + r"\s*\}",
            repair,
        )
        self.assertIsNotNone(removal, f"agdiff_repair_after_civil_war must remove {MARKER}, guarded")
        gate = re.search(r"NOT\s*=\s*\{\s*has_variable\s*=\s*" + MARKER, repair)
        self.assertIsNotNone(gate, f"agdiff_repair_after_civil_war must test {MARKER}")
        self.assertLess(gate.start(), removal.start())
        # The marker is written only by agdiff_on_uprising and read or
        # removed only in the repair.
        self.assertNotIn(MARKER, self.on_actions)
        self.assertEqual(len(re.findall(r"\b" + MARKER + r"\b",
                                        _block(self.effects, "agdiff_on_uprising"))), 1)
        self.assertEqual(len(re.findall(r"\b" + MARKER + r"\b", self.effects)), 4)


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
