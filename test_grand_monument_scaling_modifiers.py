"""Grand Monuments' national modifiers are scaling modifiers on je_grand_monuments.

Since 1.15 the entry declares each in `scaling_modifiers_while_active` and the
engine re-reads its value from the owning country about every four days
(design: docs/superpowers/specs/2026-11-06-scaling-modifiers-design.md § 4.8).
Until then the national refresh (gm_apply_national_modifiers) removed every one
from the entry and added it again with the country variable as its multiplier:
a step count above 0.001 (above 0.001 or below -0.001 for an interest group's
signed approval), and a boon while its countdown variable existed. These tests
pin that the entry declares exactly those keys, each once, each value an inline
block that reads its variable guarded by has_variable and is 0 wherever the old
refresh added nothing; and that the add-and-remove helpers are gone while the
variables they read are still written. test_journal_entry_shape.py checks the
tree-wide rule that nothing adds, removes or tests a declared key; the launch
gates that count a dig's innovation before its declaration lands are in
test_grand_monument_archaeology.py (PlayerInnovationTests).
"""

import re
import unittest
from pathlib import Path

from je_multiplier_scope_audit import parse_text

ROOT = Path(__file__).resolve().parent
JE = ROOT / "common/journal_entries/je_grand_monuments.txt"
MODIFIERS = ROOT / "common/static_modifiers/gm_modifiers.txt"
ARCH_MODIFIERS = ROOT / "common/static_modifiers/gm_archaeology_modifiers.txt"
EFFECTS = ROOT / "common/scripted_effects/gm_effects.txt"
COM_EFFECTS = ROOT / "common/scripted_effects/gm_commission_effects.txt"
TR_EFFECTS = ROOT / "common/scripted_effects/gm_trophy_effects.txt"
ARCH_EFFECTS = ROOT / "common/scripted_effects/gm_archaeology_effects.txt"
SIG_EFFECTS = ROOT / "common/scripted_effects/gm_signature_effects.txt"

NATIONAL = ("leader", "religious", "war_memorial", "artistic", "scientific", "industrial")
SIGNATURES = ("archive", "archive_spread", "throne", "royal_pantheon", "martial_glory", "liberty", "grande_armee",
              "mandate_of_heaven", "glory_of_athens", "to_victory", "unknown_soldier", "concert_of_nations",
              "conquerors_of_space", "olympic", "heroes")
IGS = ("armed_forces", "devout", "industrialists", "intelligentsia", "landowners", "petty_bourgeoisie",
       "rural_folk", "trade_unions")
BOONS = ("reign", "regime", "great_power", "victory", "defeat", "centenary", "ruler_death", "space", "faith",
         "tech_artistic", "tech_scientific", "tech_industrial", "tech_athletic", "tech_naturalist", "homecoming")

# modifier -> the country variable gm_apply_national_modifiers multiplied it by (gm_add_national).
UNSIGNED = {
    "gm_national_prestige": "gm_s_standing",
    "gm_national_prestige_pct": "gm_s_standing",
    "gm_national_education": "gm_s_education",
    "gm_national_legitimacy": "gm_s_regime",
    **{f"gm_national_{k}": f"gm_s_{k}" for k in NATIONAL},
    "gm_national_teardown": "gm_s_teardown",
    "gm_national_vanity": "gm_vanity_ledger",
    # The Epigraphic Archive's two modifiers ride the same steps.
    **{f"gm_national_sig_{k}": "gm_s_sig_archive" if k == "archive_spread" else f"gm_s_sig_{k}"
       for k in SIGNATURES},
    # gm_arch_add_national: the digs' units, once the pass has listed the country.
    "gm_arch_diversion": "gm_arch_innovation_units",
}
# gm_add_national_signed: an interest group's approval, either sign.
SIGNED = {f"gm_ig_approval_{ig}": f"gm_s_ig_{ig}" for ig in IGS}
# gm_add_boon: flat, while the countdown variable of the same name exists.
FLAT = {f"gm_boon_{b}": f"gm_boon_{b}" for b in BOONS}
KEYS = {**UNSIGNED, **SIGNED, **FLAT}

GONE = ("gm_apply_national_modifiers", "gm_remove_national_modifiers", "gm_add_national", "gm_add_national_signed",
        "gm_add_boons", "gm_add_boon", "gm_remove_boons", "gm_tr_add_national", "gm_tr_remove_national",
        "gm_arch_add_national", "gm_arch_remove_national")


def _text(path):
    return path.read_text(encoding="utf-8-sig")


def _strip_comments(text):
    return re.sub(r"#[^\n]*", "", text)


def _squash(text):
    return " ".join(_strip_comments(text).split())


def _top_level_names(path):
    return re.findall(r"(?m)^(\w+) = \{", _strip_comments(_text(path)))


def _entry():
    nodes, _ = parse_text(_text(JE), "common/journal_entries/je_grand_monuments.txt")
    return next(n for n in nodes if n.key == "je_grand_monuments")


def _declared():
    """modifier -> how many scaling_modifiers_while_active blocks on the entry declare it."""
    out = {}
    for block in (c for c in _entry().children if c.key == "scaling_modifiers_while_active"):
        name = next((c.value for c in block.children if c.key == "modifier"), None)
        out[name] = out.get(name, 0) + 1
    return out


def _declaration(modifier):
    """The declaration of `modifier`, squashed: from `scaling_modifiers_while_active = {` through its closing brace
    at the entry's first level of indentation."""
    text = _text(JE)
    match = re.search(r"\n\tscaling_modifiers_while_active = \{\n\t\tmodifier = " + re.escape(modifier) + r"\n", text)
    if match is None:
        return None
    end = text.index("\n\t}\n", match.start() + 1)
    return _squash(text[match.start():end + 3])


def _expected(modifier):
    var = KEYS[modifier]
    if modifier in FLAT:
        limit, add = f"has_variable = {var}", "1"
    elif modifier in SIGNED:
        limit, add = f"has_variable = {var} OR = {{ var:{var} > 0.001 var:{var} < -0.001 }}", f"var:{var}"
    else:
        limit, add = f"has_variable = {var} var:{var} > 0.001", f"var:{var}"
    return (f"scaling_modifiers_while_active = {{ modifier = {modifier} value = {{ value = 0 "
            f"if = {{ limit = {{ {limit} }} add = {add} }} }} }}")


def _block(text, name):
    """A top-level `name = { ... }` block of a script file, or None."""
    match = re.search(rf"(?m)^{re.escape(name)} = \{{", text)
    if match is None:
        return None
    return text[match.start():text.index("\n}\n", match.start()) + 3]


class DeclarationTests(unittest.TestCase):
    def test_the_table_is_every_national_modifier(self):
        """Every gm_national_*, gm_ig_approval_* and gm_boon_* static modifier, and the digs' drain: a new
        signature, boon or dedication's national effect fails here until the entry declares it."""
        names = {n for n in _top_level_names(MODIFIERS) if n.startswith(("gm_national_", "gm_ig_approval_", "gm_boon_"))}
        names.add("gm_arch_diversion")
        self.assertIn("gm_arch_diversion", _top_level_names(ARCH_MODIFIERS))
        self.assertEqual(set(KEYS), names)
        self.assertEqual((len(UNSIGNED), len(SIGNED), len(FLAT)), (28, 8, 15))

    def test_the_entry_declares_each_once(self):
        self.assertEqual(_declared(), {name: 1 for name in KEYS})

    def test_each_value_is_guarded_and_off_where_the_refresh_added_nothing(self):
        """`value = { value = 0 if = { limit = { has_variable = V <cutoff> } add = <V or 1> } }`: an inline block,
        never a bare value, reading the country's variable (the value's root is the owning country)."""
        for modifier in KEYS:
            with self.subTest(modifier=modifier):
                self.assertEqual(_declaration(modifier), _expected(modifier))

    def test_the_declarations_sit_on_the_entry_itself(self):
        # A direct child of the entry, not of an outcome or a pulse.
        text = _strip_comments(_text(JE))
        self.assertEqual(text.count("scaling_modifiers_while_active"), len(KEYS))


class RefreshTests(unittest.TestCase):
    def test_the_add_and_remove_helpers_are_gone(self):
        pattern = re.compile(r"\b(" + "|".join(GONE) + r")\b")
        found = []
        for sub in ("common", "events"):
            for path in sorted((ROOT / sub).rglob("*.txt")):
                found += [(path.relative_to(ROOT).as_posix(), name)
                          for name in pattern.findall(_strip_comments(_text(path)))]
        self.assertEqual(found, [])

    def test_the_refresh_still_writes_the_totals(self):
        """The declarations read what the refresh computes, so every caller of the refresh (the monthly pulse,
        monument_events.20, the panel's buttons) still moves them."""
        refresh = _squash(_block(_text(EFFECTS), "gm_country_refresh"))
        self.assertIn("gm_compute_totals = yes", refresh)

    def test_every_variable_read_is_written(self):
        totals = _squash(_block(_text(EFFECTS), "gm_compute_totals"))
        for var in ("gm_s_standing", "gm_s_education", "gm_s_regime", "gm_s_teardown",
                    *(f"gm_s_{k}" for k in NATIONAL)):
            with self.subTest(var=var):
                self.assertRegex(totals, rf"(OUT|name) = {var}\b")
        self.assertIn("gm_sig_compute_sums = yes", totals)
        self.assertIn("OUT = gm_s_sig_$SIG$", _squash(_text(SIG_EFFECTS)))
        self.assertIn("name = gm_s_ig_$IG$", _squash(_block(_text(EFFECTS), "gm_compute_ig")))
        for ig in IGS:
            self.assertIn(f"gm_compute_ig = {{ IG = {ig} }}", totals)
        self.assertIn("gm_decay = { VAR = gm_vanity_ledger RATE = 0.92 }", _squash(_text(EFFECTS)))
        self.assertIn("change_variable = { name = gm_arch_innovation_units add = gm_arch_innovation_",
                      _squash(_block(_text(ARCH_EFFECTS), "gm_arch_list_one")))
        self.assertIn("set_variable = { name = gm_boon_$SRC$ value = gm_boon_months }",
                      _squash(_block(_text(COM_EFFECTS), "gm_com_grant_boon_one")))
        self.assertIn("set_variable = { name = gm_boon_homecoming value = gm_boon_months }",
                      _squash(_block(_text(TR_EFFECTS), "gm_tr_return_home")))
        tick = _squash(_block(_text(COM_EFFECTS), "gm_tick_boon"))
        self.assertIn("limit = { var:gm_boon_$SRC$ <= 0 } remove_variable = gm_boon_$SRC$", tick,
                      "a boon's countdown is removed when it ends, which takes its declaration to 0")


if __name__ == "__main__":
    unittest.main()
