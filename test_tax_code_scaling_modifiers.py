"""The light tax code's relief and reactions are scaling modifiers on je_tax_code.

Since 1.15 the entry declares each of the 21 in `scaling_modifiers_while_active`
and the engine re-reads its value from the owning country about every four days
(design: docs/superpowers/specs/2026-11-06-scaling-modifiers-design.md § 4.9).
Until then the light sync removed and re-added them on the country, the relief
at `multiplier = var:te_tax_light_rl_<key>` and a reaction at
`multiplier = var:te_tax_lr_mag_<ig>`, on the side of its sign. These tests pin
each declaration to the generator's lists (the entry is hand-written, the values
generated), that each value is a guarded read that is 0 wherever the old sync
added nothing, and the monthly net that gives the entry to a country in force the
engine left without one. test_tax_code_light.py checks that the sync still writes
the variables and adds neither; test_journal_entry_shape.py the tree-wide rule
that nothing adds, removes or tests a declared key.
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
        found = declarations()
        for family, expected in (("relief", RELIEF), ("reactions", REACTIONS)):
            with self.subTest(family=family):
                self.assertEqual({m: v for m, v in found.items() if m in expected},
                                 {m: [v] for m, v in expected.items()})
        # Nothing else: the view bands stay flat country modifiers (the full code adds them too).
        self.assertEqual(set(found), set(RELIEF) | set(REACTIONS))

    def test_the_generator_emits_exactly_the_declared_values(self):
        generated = {modifier: name for modifier, name, _limit, _read in gen.light_scaling_values()}
        self.assertEqual(generated, {**RELIEF, **REACTIONS})
        values = read(VALUES)
        for name in generated.values():
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
        for name in itertools.chain(RELIEF.values(), REACTIONS.values()):
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
        self.assertIn("te_tax_light_gen_relief = yes te_tax_light_gen_reaction_sizes = yes", sync)
        names = "|".join(map(re.escape, sorted({**RELIEF, **REACTIONS})))
        for path in (GEN_EFFECTS, EFFECTS):
            self.assertIsNone(re.search(rf"\b({names})\b", strip_comments(read(path))), path)


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

    def test_in_force_is_enough_for_the_entrys_own_gates(self):
        triggers = read(TRIGGERS)
        self.assertIn("has_game_rule = te_tax_code_light", flat(block(triggers, "te_tax_code_on")))
        self.assertIn("te_tax_light_in_force = yes", flat(block(triggers, "te_tax_entry_unlocked")))
        entry = flat(block(read(JE), "je_tax_code"))
        self.assertIn("is_shown_when_inactive = { te_tax_code_on = yes }", entry)
        self.assertIn("possible = { te_tax_entry_unlocked = yes }", entry)


if __name__ == "__main__":
    unittest.main()
