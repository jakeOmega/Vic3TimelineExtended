"""The light tax code's relief and reactions are scaling modifiers on je_tax_code; its low dividend tax is not.

Since 1.15 the entry declares each of the 21 relief and reaction modifiers in `scaling_modifiers_while_active`
and the engine re-reads its value from the owning country about every four days
(design: docs/superpowers/specs/2026-11-06-scaling-modifiers-design.md § 4.9).
Until then the light sync removed and re-added them on the country, the relief
at `multiplier = var:te_tax_light_rl_<key>` and a reaction at
`multiplier = var:te_tax_lr_mag_<ig>`, on the side of its sign. These tests pin
each declaration to the generator's lists (the entry is hand-written, the values
generated), that each value is a guarded read that is 0 wherever the old sync
added nothing, and the monthly net that gives the entry to a country in force the
engine left without one. The low dividend tax a law without one allows (owner, 2026-11-15) was a 22nd from #1855
until TE_SELF_CHECK tax_light_div_levy read the declaration at 0 in 70 of 70 AI countries (2026-11-16); it is now a
flat country modifier the light sync removes and adds again (LevyTest below, test_tax_code_light_extra.py).
test_tax_code_light.py checks that the sync still writes the variables; test_journal_entry_shape.py the tree-wide
rule that nothing adds, removes or tests a declared key.
"""

import importlib.util
import itertools
import math
import re
import unittest
from pathlib import Path

from je_multiplier_scope_audit import parse_text

ROOT = Path(__file__).resolve().parent
JE = "common/journal_entries/je_tax_code.txt"
VALUES = "common/script_values/te_tax_light_generated_values.txt"
GEN_EFFECTS = "common/scripted_effects/te_tax_light_generated_effects.txt"
EFFECTS = "common/scripted_effects/te_tax_light_effects.txt"
ON_ACTIONS = "common/on_actions/te_tax_on_actions.txt"
TRIGGERS = "common/scripted_triggers/te_tax_triggers.txt"

spec = importlib.util.spec_from_file_location("gen_tax_code", ROOT / "scripts/generators/gen_tax_code.py")
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)

KEYS = [instrument.key for instrument in gen.INSTRUMENTS]
RELIEF = {f"te_tax_light_relief_{key}": f"te_tax_light_relief_{key}_value" for key in KEYS}
REACTIONS = {f"te_tax_light_react_{ig}_{sign}": f"te_tax_light_react_{ig}_{sign}_value"
             for ig in gen.IGS for sign in ("pos", "neg")}
LEVIES = {f"te_tax_light_levy_{extra.key}": f"te_tax_light_levy_{extra.key}_value" for extra in gen.LIGHT_EXTRAS}


def read(path):
    return (ROOT / path).read_text(encoding="utf-8-sig")


def strip_comments(text):
    return re.sub(r"#[^\n]*", "", text)


def flat(text):
    return " ".join(text.split())


def block(text, name):
    """The body of the top-level `name = { ... }` in `text`, comments removed."""
    text = strip_comments(text)
    match = re.search(rf"(?m)^{re.escape(name)} = \{{", text)
    if not match:
        raise AssertionError(f"{name} not found")
    depth, start = 0, match.end() - 1
    for i in range(start, len(text)):
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        if depth == 0:
            return text[start + 1:i]
    raise AssertionError(f"{name} is not closed")


def declarations():
    """modifier -> [value] for every scaling_modifiers_while_active block on je_tax_code. Each value is an
    inline block holding one named script value, `value = { value = <name> }`, the form every vanilla use
    takes: a bare `value = <name>`, or a block that holds anything else, comes back as None."""
    nodes, _ = parse_text(read(JE), JE)
    entry = next(n for n in nodes if n.key == "je_tax_code")
    out = {}
    for decl in (c for c in entry.children if c.key == "scaling_modifiers_while_active"):
        modifier = next((c.value for c in decl.children if c.key == "modifier"), None)
        value = next((c for c in decl.children if c.key == "value"), None)
        inner = None
        if value is not None and value.value is None and len(value.children) == 1:
            only = value.children[0]
            if only.key == "value" and not only.children:
                inner = only.value
        out.setdefault(modifier, []).append(inner)
    return out


class DeclarationTest(unittest.TestCase):
    def test_the_entry_declares_every_relief_and_reaction_once_in_block_form(self):
        self.assertEqual(len(RELIEF) + len(REACTIONS), 21)
        self.assertEqual(list(LEVIES), ["te_tax_light_levy_div"])
        found = declarations()
        for family, expected in (("relief", RELIEF), ("reactions", REACTIONS)):
            with self.subTest(family=family):
                self.assertEqual({m: v for m, v in found.items() if m in expected},
                                 {m: [v] for m, v in expected.items()})
        # Nothing else: the view bands and the low dividend tax's levy are flat country modifiers. The levy must
        # never be declared beside the sync's flat copy, which would tax dividends twice.
        self.assertEqual(set(found), set(RELIEF) | set(REACTIONS))
        self.assertEqual(len(found), 21)
        self.assertFalse(set(found) & set(LEVIES))

    def test_the_generator_emits_exactly_the_declared_values_and_the_levys(self):
        generated = {modifier: name for modifier, name, _limit, _read in gen.light_scaling_values()}
        self.assertEqual(generated, {**RELIEF, **REACTIONS})
        levies = {modifier: name for modifier, name, _limit, _read in gen.light_levy_values()}
        self.assertEqual(levies, LEVIES)
        values = read(VALUES)
        for name in {**generated, **levies}.values():
            with self.subTest(value=name):
                self.assertEqual(len(re.findall(rf"(?m)^{name} = \{{", values)), 1)

    def test_relief_is_the_guarded_steps_while_the_law_levies_the_tax(self):
        # The old sync added the relief only for rl > 0, and set rl to 0 for a tax the law does not levy.
        values = read(VALUES)
        for key in KEYS:
            rl = f"te_tax_light_rl_{key}"
            with self.subTest(key=key):
                self.assertEqual(flat(block(values, RELIEF[f"te_tax_light_relief_{key}"])),
                                 f"value = 0 if = {{ limit = {{ te_tax_light_levies_{key} = yes has_variable = {rl} "
                                 f"var:{rl} > 0 }} value = var:{rl} }}")

    def test_the_levy_is_the_guarded_index_while_the_code_is_in_force_and_the_extra_open(self):
        # Unlike the relief it reads the rule and the marker (te_tax_light_in_force): a positive tax stops the
        # day the code does, before the entry's invalid outcome ends it.
        values = read(VALUES)
        for extra in gen.LIGHT_EXTRAS:
            en = f"te_tax_en_{extra.key}"
            with self.subTest(key=extra.key):
                self.assertEqual(flat(block(values, LEVIES[f"te_tax_light_levy_{extra.key}"])),
                                 f"value = 0 if = {{ limit = {{ te_tax_light_in_force = yes "
                                 f"te_tax_light_extra_{extra.key} = yes has_variable = {en} var:{en} > 0 }} "
                                 f"value = var:{en} }}")

    def test_a_reaction_is_the_guarded_rounded_size_on_the_side_of_its_sign(self):
        # The old sync added _pos x round(lr) for round(lr) >= 1 and _neg x -round(lr) for round(lr) <= -1.
        values = read(VALUES)
        for ig in gen.IGS:
            lr, mag = f"te_tax_lr_{ig}", f"te_tax_lr_mag_{ig}"
            for sign, comparison in (("pos", ">"), ("neg", "<")):
                with self.subTest(ig=ig, sign=sign):
                    self.assertEqual(flat(block(values, REACTIONS[f"te_tax_light_react_{ig}_{sign}"])),
                                     f"value = 0 if = {{ limit = {{ has_variable = {lr} var:{lr} {comparison} 0 "
                                     f"has_variable = {mag} var:{mag} >= 1 }} value = var:{mag} }}")

    def test_every_variable_read_is_guarded(self):
        values = read(VALUES)
        for name in itertools.chain(RELIEF.values(), LEVIES.values(), REACTIONS.values()):
            body = block(values, name)
            for var in set(re.findall(r"var:(\w+)", body)):
                with self.subTest(value=name, var=var):
                    self.assertIn(f"has_variable = {var}", body)
            self.assertNotIn("has_modifier", body)

    def test_the_values_give_what_the_old_adds_gave(self):
        """The reaction sizes as te_tax_light_gen_reaction_sizes writes them, then each declaration against the
        old add, over the running reaction's whole range, under either rounding of a half."""
        for round_half in (lambda x: math.copysign(math.floor(abs(x) + 0.5), x),  # away from zero
                           lambda x: math.floor(x + 0.5)):  # up
            for step in range(-400, 401):
                lr = step / 40  # -10 .. 10 by 0.025
                rounded = round_half(lr)
                old = {"pos": rounded if rounded >= 1 else 0, "neg": -rounded if rounded <= -1 else 0}
                mag = -rounded if rounded <= -1 else (rounded if rounded >= 1 else 0)
                new = {"pos": mag if lr > 0 and mag >= 1 else 0, "neg": mag if lr < 0 and mag >= 1 else 0}
                self.assertEqual(new, old, lr)

    def test_the_sync_writes_every_input_and_adds_none(self):
        effects = read(GEN_EFFECTS)
        relief = flat(block(effects, "te_tax_light_gen_relief"))
        sizes = flat(block(effects, "te_tax_light_gen_reaction_sizes"))
        for key in KEYS:
            self.assertIn(f"set_variable = {{ name = te_tax_light_rl_{key}", relief)
        for ig in gen.IGS:
            self.assertIn(f"set_variable = {{ name = te_tax_lr_mag_{ig} value = {{ value = var:te_tax_lr_{ig} "
                          "round = yes } }", sizes)
        sync = flat(block(read(EFFECTS), "te_tax_light_sync"))
        self.assertIn("te_tax_light_gen_relief = yes te_tax_light_gen_levy = yes "
                      "te_tax_light_gen_reaction_sizes = yes", sync)
        names = "|".join(map(re.escape, sorted({**RELIEF, **REACTIONS})))
        for path in (GEN_EFFECTS, EFFECTS):
            self.assertIsNone(re.search(rf"\b({names})\b", strip_comments(read(path))), path)


class LevyTest(unittest.TestCase):
    """The low dividend tax's levy is a flat country modifier, the dynamic-modifier pattern: the sync, its one
    refresh site, takes it off and puts it back at multiplier = the value, in the country's own scope; a monthly
    net takes it off where the code is not in force, and adds nothing."""

    def test_the_sync_removes_the_old_copy_then_adds_at_the_values_multiplier(self):
        body = flat(block(read(GEN_EFFECTS), "te_tax_light_gen_levy"))
        expected = " ".join(
            f"if = {{ limit = {{ has_modifier = {modifier} }} remove_modifier = {modifier} }} "
            f"if = {{ limit = {{ {name} > 0 }} add_modifier = {{ name = {modifier} multiplier = {name} }} }}"
            for modifier, name in LEVIES.items())
        self.assertEqual(body, expected)
        # The remove comes before the add: a same-name add_modifier stacks.
        self.assertLess(body.index("remove_modifier"), body.index("add_modifier"))

    def test_the_sync_is_its_one_refresh_site(self):
        # Exactly one call of the refresh, from te_tax_light_sync, and no other add of the levy anywhere.
        calls, adds = [], []
        for directory in ("common", "events"):
            for path in sorted((ROOT / directory).rglob("*.txt")):
                text = strip_comments(path.read_text("utf-8-sig", "replace"))
                rel = path.relative_to(ROOT).as_posix()
                calls += [rel] * text.count("te_tax_light_gen_levy = yes")
                for modifier in LEVIES:
                    adds += [rel] * len(re.findall(rf"add_modifier = \{{ name = {modifier}\b", text))
                    self.assertNotRegex(text, rf"add_modifier = {modifier}\b", rel)
        self.assertEqual(calls, [EFFECTS])
        self.assertEqual(adds, [GEN_EFFECTS] * len(LEVIES))
        sync = flat(block(read(EFFECTS), "te_tax_light_sync"))
        self.assertEqual(sync.count("te_tax_light_gen_levy = yes"), 1)
        # Inside the in-force branch, after the law change, Traditionalism's close and the AI's or the player's
        # rates, so the multiplier reads this sync's rate.
        self.assertTrue(sync.startswith("if = { limit = { te_tax_light_in_force = yes }"))
        self.assertLess(sync.index("te_tax_light_gen_close = yes"), sync.index("te_tax_light_gen_levy = yes"))
        self.assertLess(sync.index("te_tax_light_gen_shift = yes"), sync.index("te_tax_light_gen_levy = yes"))

    def test_every_caller_of_the_sync_is_the_countrys_own_scope(self):
        # The multiplier resolves against the calling scope chain (scripting_best_practices.md, "Scope Chain
        # Issues with add_modifier + Script Values"): each caller is a country event, the step's scripted GUI or
        # a light effect those run.
        callers = set()
        for directory in ("common", "events"):
            for path in sorted((ROOT / directory).rglob("*.txt")):
                if "te_tax_light_sync = yes" in strip_comments(path.read_text("utf-8-sig", "replace")):
                    callers.add(path.relative_to(ROOT).as_posix())
        self.assertEqual(callers, {EFFECTS, "events/te_tax_light_events.txt", "events/te_tax_debug_events.txt"})

    def test_the_teardown_net_takes_it_off_where_the_code_is_not_in_force_and_adds_nothing(self):
        text = flat(strip_comments(read(ON_ACTIONS)))
        pulse = re.search(r"on_monthly_pulse_country = \{ on_actions = \{ ([^}]*) \} \}", text)
        self.assertIn("te_tax_light_levy_net", pulse.group(1).split())
        net = flat(block(read(ON_ACTIONS), "te_tax_light_levy_net"))
        self.assertTrue(net.startswith(
            "effect = { if = { limit = { NOT = { te_tax_light_in_force = yes } te_tax_light_has_levy = yes } "
            "te_tax_light_gen_clear_levy = yes debug_log = \"TE_TAX light_levy_off "), net)
        clear = flat(block(read(GEN_EFFECTS), "te_tax_light_gen_clear_levy"))
        self.assertEqual(clear, " ".join(f"if = {{ limit = {{ has_modifier = {m} }} remove_modifier = {m} }}"
                                         for m in LEVIES))
        has = flat(block(read("common/scripted_triggers/te_tax_light_generated_triggers.txt"), "te_tax_light_has_levy"))
        self.assertEqual(has, "OR = { " + " ".join(f"has_modifier = {m}" for m in LEVIES) + " }")
        # Not in force covers the rule switched to Disabled and to the full code: the trigger reads the light
        # setting and the marker.
        self.assertEqual(flat(block(read(TRIGGERS), "te_tax_light_in_force")),
                         "te_tax_code_light_on = yes has_variable = te_tax_light_on var:te_tax_light_on >= 1")

    def test_the_multiplier_never_reads_a_removed_variable(self):
        # The multiplier is te_tax_en_<key>, which nothing removes (modifier_multiplier_var_audit's rule).
        for directory in ("common", "events"):
            for path in sorted((ROOT / directory).rglob("*.txt")):
                text = strip_comments(path.read_text("utf-8-sig", "replace"))
                for extra in gen.LIGHT_EXTRAS:
                    self.assertNotIn(f"remove_variable = te_tax_en_{extra.key}", text, path)


class SafetyNetTest(unittest.TestCase):
    """The modifiers apply only while the entry is active, so a country in force without a record of it gets
    one each month (Banking's net, te_banking_entry_on_actions.txt, found the engine leaves some out)."""

    def test_the_net_hangs_off_each_countrys_monthly_pulse(self):
        text = flat(strip_comments(read(ON_ACTIONS)))
        pulse = re.search(r"on_monthly_pulse_country = \{ on_actions = \{ ([^}]*) \} \}", text)
        self.assertIn("te_tax_light_entry_net", pulse.group(1).split())

    def test_the_net_adds_the_entry_only_where_an_add_can_work(self):
        net = flat(block(read(ON_ACTIONS), "te_tax_light_entry_net"))
        # The light setting first, as every light handler (test_tax_code_rule.py's gate sweep); the code
        # in force (which the entry's is_shown_when_inactive and possible both accept), not a
        # decentralized nation (the dispatch never migrates one), and no copy of the entry, active or
        # inactive: add_journal_entry is refused while an inactive copy waits, which the engine
        # activates itself (scripting_best_practices.md, has_journal_entry reads active entries only).
        self.assertTrue(net.startswith(
            "effect = { if = { limit = { te_tax_code_light_on = yes te_tax_light_in_force = yes "
            "NOT = { is_country_type = decentralized } "
            "NOT = { has_journal_entry = je_tax_code } NOT = { has_inactive_journal_entry = je_tax_code } } "
            "add_journal_entry = { type = je_tax_code } debug_log = \"TE_TAX light_entry_net "), net)

    def test_the_full_code_has_the_same_net(self):
        # The full code's entry is display only, but the Tax Code tab, where a tax is changed, opens only while
        # the entry is active. A Workshop player's tab stayed greyed for ten years with the code in force and no
        # record of the entry (2026-11-13): only the light setting had a net.
        text = flat(strip_comments(read(ON_ACTIONS)))
        pulse = re.search(r"on_monthly_pulse_country = \{ on_actions = \{ ([^}]*) \} \}", text)
        self.assertIn("te_tax_full_entry_net", pulse.group(1).split())
        net = flat(block(read(ON_ACTIONS), "te_tax_full_entry_net"))
        self.assertTrue(net.startswith(
            "effect = { if = { limit = { te_tax_code_full = yes te_tax_code_in_force = yes "
            "NOT = { is_country_type = decentralized } "
            "NOT = { has_journal_entry = je_tax_code } NOT = { has_inactive_journal_entry = je_tax_code } } "
            "add_journal_entry = { type = je_tax_code } debug_log = \"TE_TAX full_entry_net "), net)
        # The tab's two gates are what the net restores: the entry active, on a code in force.
        sguis = flat(strip_comments(read("common/scripted_guis/te_system_tab_sguis.txt")))
        self.assertIn("te_budget_tax_tab_sgui = { scope = country is_shown = { te_tax_code_on = yes "
                      "has_journal_entry = je_tax_code }", sguis)
        self.assertIn("te_tax_code_in_force = yes", flat(block(read(TRIGGERS), "te_tax_entry_unlocked")))

    def test_an_inactive_copy_the_engine_never_activates_is_reported(self):
        # The greyed tab's tooltip reads only has_journal_entry, so it cannot tell a country with no record from
        # one holding an inactive copy, and the nets leave the second alone (add_journal_entry is refused over an
        # inactive copy). A handler beside each net, gated on its own setting, counts the months.
        text = flat(strip_comments(read(ON_ACTIONS)))
        pulse = re.search(r"on_monthly_pulse_country = \{ on_actions = \{ ([^}]*) \} \}", text).group(1).split()
        for handler, gate, in_force in (("te_tax_light_entry_stuck", "te_tax_code_light_on", "te_tax_light_in_force"),
                                        ("te_tax_full_entry_stuck", "te_tax_code_full", "te_tax_code_in_force")):
            self.assertIn(handler, pulse)
            self.assertEqual(flat(block(strip_comments(read(ON_ACTIONS)), handler)),
                             "effect = { if = { limit = { %s = yes } te_tax_entry_stuck_check = { IN_FORCE = %s } } }"
                             % (gate, in_force))
        check = flat(block(strip_comments(read("common/scripted_effects/te_tax_migration_effects.txt")),
                           "te_tax_entry_stuck_check"))
        self.assertTrue(check.startswith(
            "if = { limit = { $IN_FORCE$ = yes NOT = { is_country_type = decentralized } "
            "NOT = { has_journal_entry = je_tax_code } has_inactive_journal_entry = je_tax_code } "), check[:200])
        # Three months running, one line, and the counter returns to 0 when the state goes (never removed: a
        # revolution's winner would get a removed token back with the loser's value).
        self.assertIn("limit = { var:te_tax_entry_stuck_months < 3 } "
                      "change_variable = { name = te_tax_entry_stuck_months add = 1 } "
                      "if = { limit = { var:te_tax_entry_stuck_months >= 3 } "
                      "debug_log = \"TE_SELF_CHECK BROKEN tax_entry_inactive_stuck ", check)
        self.assertTrue(check.endswith("else_if = { limit = { has_variable = te_tax_entry_stuck_months "
                                       "var:te_tax_entry_stuck_months > 0 } "
                                       "set_variable = { name = te_tax_entry_stuck_months value = 0 } }"), check[-200:])
        self.assertEqual(check.count("debug_log"), 1)
        self.assertNotIn("remove_variable", check)

    def test_in_force_is_enough_for_the_entrys_own_gates(self):
        triggers = read(TRIGGERS)
        self.assertIn("has_game_rule = te_tax_code_light", flat(block(triggers, "te_tax_code_on")))
        self.assertIn("te_tax_light_in_force = yes", flat(block(triggers, "te_tax_entry_unlocked")))
        entry = flat(block(read(JE), "je_tax_code"))
        self.assertIn("is_shown_when_inactive = { te_tax_code_on = yes }", entry)
        self.assertIn("possible = { te_tax_entry_unlocked = yes }", entry)


if __name__ == "__main__":
    unittest.main()
