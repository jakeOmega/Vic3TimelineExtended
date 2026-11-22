"""The light tax code's low dividend tax under a law that levies none (owner, 2026-11-15).

Under the light setting a country on Consumption-Based, Land-Based or Per-Capita Taxation may levy a dividend
tax from nothing up to a low cap (LIGHT_EXTRAS in scripts/generators/gen_tax_code.py), closed under
Traditionalism; Proportional and Graduated keep their own range. The law collects none of it, so je_tax_code
declares te_tax_light_levy_div (test_tax_code_scaling_modifiers.py). Schema: docs/systems/tax_code_schema.md,
"Light code". Each class pins one rule, so a regression of it fails here:

- the cap and the range under each law, against vanilla_parsed's rates;
- the default: a player's starts at nothing and nothing but an AI's sync raises it, so a save in progress
  keeps a player's taxes on load;
- the AI's rate: Proportional's ladder capped, at the AI's native level, never above the player's cap;
- the reactions: the shared dividend tax reaction, once per change, and no relief or band;
- the rule switched off: the levy stops with the code;
- civil wars: the rebels and the winner carry the rate;
- the panel and its text; and the retired self-check (tax_light_div_levy read the declared levy at 0 through
  modifier:, while the Budget collected it: the owner's reading of 2026-11-16), which must not come back.
"""

import importlib.util
import json
import re
import unittest
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent

spec = importlib.util.spec_from_file_location("gen_tax_code", ROOT / "scripts/generators/gen_tax_code.py")
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)

VALUES = "common/script_values/te_tax_light_generated_values.txt"
TRIGGERS = "common/scripted_triggers/te_tax_light_generated_triggers.txt"
GEN_EFFECTS = "common/scripted_effects/te_tax_light_generated_effects.txt"
MODIFIERS = "common/static_modifiers/te_tax_light_generated_modifiers.txt"
CUSTOM_LOC = "common/customizable_localization/te_tax_light_generated_custom_loc.txt"
EFFECTS = "common/scripted_effects/te_tax_light_effects.txt"
TAX_TRIGGERS = "common/scripted_triggers/te_tax_triggers.txt"
MIGRATION_EFFECTS = "common/scripted_effects/te_tax_migration_effects.txt"
JE = "common/journal_entries/je_tax_code.txt"
LIGHT_GUI = "gui/journal_entry_widgets/te_tax_light_widget.gui"
LOC = "localization/english/te_tax_l_english.yml"
GEN_LOC = "localization/english/te_tax_generated_l_english.yml"
RETIRED_SELF_CHECK = "common/on_actions/te_tax_light_div_levy_selfcheck_on_actions.txt"
RETIRED_SELF_CHECK_VALUES = "common/script_values/te_tax_light_div_levy_selfcheck_values.txt"
PLAYTEST = "docs/testing/tax-code-playtest.md"

LEVELS = gen.NATIVE_LEVELS
UNTAXED = ["law_consumption_based_taxation", "law_land_based_taxation", "law_per_capita_based_taxation"]
TAXED = ["law_proportional_taxation", "law_graduated_taxation"]
STEP = Decimal("0.025")


def read(path):
    return (ROOT / path).read_text(encoding="utf-8-sig")


def strip_comments(text):
    return re.sub(r"#[^\n]*", "", text)


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


def flat(text):
    return " ".join(text.split())


def loc(path):
    table = {}
    for line in read(path).splitlines():
        match = re.match(r'^ ([\w.\-]+):\d+ "(.*)"$', line)
        if match:
            table[match.group(1)] = match.group(2)
    return table


def vanilla_div_ladder(law):
    """[index at very_low .. very_high] of the law's dividend rate, from vanilla_parsed."""
    body = json.loads(read("vanilla_parsed/common/laws.json"))[law][1]
    return [int(Decimal(body.get(f"tax_modifier_{level}", ["=", {}])[1].get("tax_dividends_add", ["=", "0"])[1])
                / STEP) for level in LEVELS]


def cap():
    return int(flat(block(read(VALUES), "te_tax_light_extra_cap_div")).split("= ")[1])


class CapTest(unittest.TestCase):
    """The cap is low: under every levying law's Medium rate, on Proportional's own steps."""

    def test_the_cap_is_five_percent_on_the_named_value(self):
        # The owner's number to settle; the alternative is 1 (2.5%). A change of it changes the PR's tables.
        self.assertEqual([extra.key for extra in gen.LIGHT_EXTRAS], ["div"])
        self.assertEqual(gen.LIGHT_EXTRA_CAP_DIV, 2)
        self.assertEqual(cap(), gen.LIGHT_EXTRA_CAP_DIV)
        self.assertEqual(cap() * STEP, Decimal("0.05"))

    def test_the_cap_is_below_every_levying_laws_medium_rate(self):
        medium = LEVELS.index("medium")
        for law in TAXED:
            with self.subTest(law=law):
                self.assertTrue(1 <= cap() < vanilla_div_ladder(law)[medium])
        for law in UNTAXED:
            self.assertEqual(vanilla_div_ladder(law), [0] * len(LEVELS), law)

    def test_validation_refuses_a_cap_that_is_not_low(self):
        original = gen.LIGHT_EXTRAS
        try:
            for bad in (0, 4, 20):
                gen.LIGHT_EXTRAS = (original[0]._replace(cap=bad),)
                with self.subTest(cap=bad), self.assertRaises(ValueError):
                    gen.validate_light_extras()
            gen.LIGHT_EXTRAS = (original[0]._replace(anchor="law_per_capita_based_taxation"),)
            with self.assertRaises(ValueError):
                gen.validate_light_extras()
            gen.LIGHT_EXTRAS = (original[0]._replace(barred_by=("law_land_based_taxation",)),)
            with self.assertRaises(ValueError):
                gen.validate_light_extras()
        finally:
            gen.LIGHT_EXTRAS = original
        gen.validate_light_extras()

    def test_it_is_open_under_exactly_the_laws_that_levy_none_and_never_under_traditionalism(self):
        body = flat(block(read(TRIGGERS), "te_tax_light_extra_div"))
        self.assertEqual(re.findall(r"OR = \{ (.*?) \}", body)[0].split(" has_law = "),
                         [f"has_law = law_type:{UNTAXED[0]}"] + [f"law_type:{law}" for law in UNTAXED[1:]])
        self.assertIn("NOT = { has_law = law_type:law_traditionalism }", body)
        holds = flat(block(read(TRIGGERS), "te_tax_light_holds_div"))
        self.assertEqual(holds, "OR = { te_tax_light_levies_div = yes te_tax_light_extra_div = yes }")
        # The law-only trigger is unchanged: the relief and the old-law test read it.
        levies = flat(block(read(TRIGGERS), "te_tax_light_levies_div"))
        self.assertEqual(re.findall(r"law_type:(\w+)", levies), TAXED)
        old = flat(block(read(TRIGGERS), "te_tax_light_old_extra_div"))
        self.assertEqual([int(n) for n in re.findall(r"var:te_tax_light_law = (\d+)", old)],
                         [n for n, law in gen.light_laws() if law in UNTAXED])

    def test_the_range_under_each_law(self):
        # What te_tax_light_max_div gives: the cap where the extra is open, the law's very-high rate otherwise.
        body = flat(block(read(VALUES), "te_tax_light_max_div"))
        self.assertEqual(body, "value = te_tax_light_idx_div_4 if = { limit = { te_tax_light_extra_div = yes } "
                               "value = te_tax_light_extra_cap_div }")
        top = {law: (cap() if law in UNTAXED else vanilla_div_ladder(law)[-1]) for law in UNTAXED + TAXED}
        self.assertEqual({law: int(STEP * 100 * n) for law, n in top.items()},
                         {UNTAXED[0]: 5, UNTAXED[1]: 5, UNTAXED[2]: 5, TAXED[0]: 20, TAXED[1]: 30})
        table = loc(GEN_LOC)
        self.assertEqual(table["te_tax_lt_range_div_extra"], "#v 0–5%#!")
        self.assertEqual(table["te_tax_lt_extra_cap_div"], "#v 5%#!")
        custom = flat(block(read(CUSTOM_LOC), "te_tax_lt_range_div"))
        # After the levying laws' own ranges, before the fallback.
        self.assertLess(custom.index("te_tax_lt_range_div_5"), custom.index("te_tax_lt_range_div_extra"))
        self.assertLess(custom.index("te_tax_lt_range_div_extra"), custom.index("te_tax_lt_not_levied"))
        self.assertIn("trigger = { te_tax_view_light_extra_div = 1 } localization_key = te_tax_lt_range_div_extra",
                      custom)

    def test_its_steps_are_proportionals_capped(self):
        ladder = [min(n, cap()) for n in vanilla_div_ladder("law_proportional_taxation")]
        self.assertEqual(ladder, [1, 2, 2, 2, 2])
        values = read(VALUES)
        for n, idx in enumerate(ladder):
            with self.subTest(level=n):
                self.assertEqual(flat(block(values, f"te_tax_light_xidx_div_{n}")),
                                 f"value = 0 if = {{ limit = {{ te_tax_light_extra_div = yes }} value = {idx} }}")
        # Its step: on the extra ladder above nothing, none at nothing (no tax).
        rung = flat(block(values, "te_tax_light_rung_div"))
        branch = rung[rung.index("limit = { te_tax_light_extra_div = yes"):]
        self.assertTrue(branch.startswith("limit = { te_tax_light_extra_div = yes has_variable = te_tax_en_div "
                                          "var:te_tax_en_div > 0 }"))
        thresholds = [(int(t), int(v)) for t, v in re.findall(r"var:te_tax_en_div <= (\d+) \} value = (\d+)", branch)]
        for idx in range(1, cap() + 1):
            value = len(LEVELS) - 1
            for threshold, step in thresholds:
                if idx <= threshold:
                    value = step
            with self.subTest(idx=idx):
                self.assertEqual(value, next(n for n, top in enumerate(ladder) if idx <= top))
        self.assertTrue(rung.startswith("value = -1"))
        # So the cap sits on Low: the most it can do to the tax level is raise it to Low.
        max_raises = flat(block(read(TRIGGERS), "te_tax_light_max_raises_div"))
        self.assertIn("AND = { te_tax_light_extra_div = yes var:te_tax_light_level < 1 }", max_raises)
        up = flat(block(read(TRIGGERS), "te_tax_light_up_raises_div"))
        self.assertIn("AND = { te_tax_light_extra_div = yes var:te_tax_light_level = 0 var:te_tax_en_div >= 1 }", up)

    def test_the_levy_is_one_step_above_zero(self):
        body = flat(block(read(MODIFIERS), "te_tax_light_levy_div"))
        self.assertIn("tax_dividends_add = 0.025", body)
        self.assertIn("modifier_coins_positive.dds", body)
        self.assertEqual(gen.INSTRUMENTS[[i.key for i in gen.INSTRUMENTS].index("div")].step, STEP)


class DefaultTest(unittest.TestCase):
    """A player's low dividend tax starts at nothing and only the player raises it; nothing a save in progress
    runs on load raises it."""

    def test_the_migration_leaves_a_players_at_nothing(self):
        body = flat(block(read(GEN_EFFECTS), "te_tax_light_gen_uniform"))
        self.assertIn("set_variable = { name = te_tax_en_div value = te_tax_light_idx_div_native }", body)
        # The law's own index is 0 under a law that levies none (test_tax_code_light.BoundsTest), and only an AI's
        # code is raised to the extra's rate.
        self.assertIn("if = { limit = { te_tax_light_ai_uniform = yes te_tax_light_extra_div = yes } "
                      "set_variable = { name = te_tax_en_div value = te_tax_light_xidx_div_native } }", body)
        for n in range(len(LEVELS)):
            idx = flat(block(read(VALUES), f"te_tax_light_idx_div_{n}"))
            for law in UNTAXED:
                self.assertNotIn(law, idx)

    def test_only_an_ais_sync_writes_the_extras_rate(self):
        writes = re.compile(r"value = te_tax_light_(?:xidx_div_native|ai_idx_div)\b")
        for path in (GEN_EFFECTS, EFFECTS):
            text = strip_comments(read(path))
            for match in writes.finditer(text):
                head = text[:match.start()]
                effect = re.findall(r"(?m)^(\w+) = \{", head)[-1]
                with self.subTest(path=path, effect=effect):
                    self.assertIn(effect, {"te_tax_light_gen_uniform", "te_tax_light_gen_uniform_scored"})
        # The scored form runs only in the sync's AI branch.
        sync = flat(block(read(EFFECTS), "te_tax_light_sync"))
        ai_branch = sync.index("te_tax_light_gen_close = yes if = { limit = { te_tax_light_ai_uniform = yes }")
        player_branch = sync.index("te_tax_light_gen_shift = yes")
        for match in re.finditer(r"te_tax_light_gen_uniform_scored = yes", sync):
            self.assertTrue(ai_branch < match.start() < player_branch)
        calls = [path.relative_to(ROOT).as_posix() for directory in ("common", "events")
                 for path in sorted((ROOT / directory).rglob("*.txt"))
                 if "te_tax_light_gen_uniform_scored = yes" in strip_comments(path.read_text("utf-8-sig", "replace"))]
        self.assertEqual(calls, [EFFECTS])

    def test_a_players_choice_carries_between_laws_that_levy_none_and_never_rises(self):
        clamp = flat(block(read(GEN_EFFECTS), "te_tax_light_gen_clamp"))
        self.assertIn("if = { limit = { te_tax_light_extra_div = yes te_tax_light_old_extra_div = yes } "
                      "clamp_variable = { name = te_tax_en_div min = te_tax_light_min_div "
                      "max = te_tax_light_xidx_div_at_level } } else_if = { limit = { NOT = { "
                      "te_tax_light_levies_div = yes } } set_variable = { name = te_tax_en_div value = 0 } }", clamp)

    def test_a_level_moved_outside_the_code_clamps_it_to_the_new_levels_rate(self):
        # The levied taxes move by the law's difference; the low tax only falls, to its rate at the new level, so
        # it never holds the level above where it was moved (review of #1855: an uprising's AI choosing a lower
        # level each month would otherwise shift every levied tax down again each month).
        # test_tax_code_light.StepTest.test_a_shift_never_leaves_a_tax_above_the_new_level models it.
        shift = flat(block(read(GEN_EFFECTS), "te_tax_light_gen_shift"))
        branch = shift[shift.index("else_if = { limit = { te_tax_light_extra_div = yes }"):]
        self.assertIn("clamp_variable = { name = te_tax_en_div min = te_tax_light_min_div "
                      "max = te_tax_light_xidx_div_native }", branch)
        self.assertIn("te_tax_light_gen_react = { KEY = div }", branch)
        self.assertNotIn("change_variable = { name = te_tax_en_div add", branch[:branch.index("te_tax_light_gen_react")])

    def test_nothing_is_levied_at_nothing(self):
        value = flat(block(read(VALUES), "te_tax_light_levy_div_value"))
        self.assertTrue(value.startswith("value = 0 if = { limit = {"))
        self.assertIn("var:te_tax_en_div > 0", value)


class AiRateTest(unittest.TestCase):
    """An AI country levies it without being asked, at its native level's rate on the capped ladder, which is
    the player's own range: no AI-only advantage."""

    def test_an_ai_follows_its_level_on_the_capped_ladder(self):
        values = read(VALUES)
        self.assertEqual(flat(block(values, "te_tax_light_ai_idx_div")),
                         "value = te_tax_light_idx_div_native if = { limit = { te_tax_light_extra_div = yes } "
                         "value = te_tax_light_xidx_div_native }")
        native = flat(block(values, "te_tax_light_xidx_div_native"))
        self.assertTrue(native.startswith("value = te_tax_light_xidx_div_2"))
        for n, level in enumerate(LEVELS):
            if level != "medium":
                self.assertIn(f"if = {{ limit = {{ tax_level = {level} }} value = te_tax_light_xidx_div_{n} }}", native)
        scored = flat(block(read(GEN_EFFECTS), "te_tax_light_gen_uniform_scored"))
        self.assertIn("set_variable = { name = te_tax_light_d value = te_tax_light_ai_idx_div } "
                      "change_variable = { name = te_tax_light_d subtract = var:te_tax_en_div } "
                      "if = { limit = { NOT = { var:te_tax_light_d = 0 } } te_tax_light_gen_react = { KEY = div } } "
                      "set_variable = { name = te_tax_en_div value = te_tax_light_ai_idx_div }", scored)

    def test_the_ais_rate_at_each_level_is_within_the_players_range(self):
        rates = [min(n, cap()) * STEP * 100 for n in vanilla_div_ladder("law_proportional_taxation")]
        self.assertEqual(rates, [Decimal("2.5"), 5, 5, 5, 5])
        self.assertLessEqual(max(gen.light_extra_ladder("div")), cap())

    def test_no_branch_reads_is_ai_for_the_extra(self):
        # The AI and the player share the cap, the range, the steps and the reactions; only who moves the rate
        # differs, through te_tax_light_ai_uniform as for every other tax.
        for path in (VALUES, TRIGGERS):
            for name in re.findall(r"(?m)^(te_tax_light_\w*(?:extra|xidx|ai_idx|levy)\w*) = \{", strip_comments(read(path))):
                with self.subTest(name=name):
                    self.assertNotIn("is_ai", block(read(path), name))


class ReactionTest(unittest.TestCase):
    """A change of the low dividend tax draws what a dividend tax change draws under a law that levies one:
    the same coefficients, once per change; and no relief or band of its own."""

    def test_one_shared_reaction_per_change(self):
        scored = flat(block(read(GEN_EFFECTS), "te_tax_light_gen_uniform_scored"))
        self.assertEqual(scored.count("te_tax_light_gen_react = { KEY = div }"), 1)
        values = read(VALUES)
        for ig in gen.IGS:
            self.assertEqual(len(re.findall(rf"(?m)^te_tax_light_rc_div_{ig} = \{{", values)), 1)
        self.assertNotRegex(values, r"(?m)^te_tax_light_rc_\w*extra")
        # The step command scores the change whatever the law (test_tax_code_light.SyncTest).
        step = flat(block(read(EFFECTS), "te_tax_light_cmd_step"))
        self.assertEqual(step.count("te_tax_light_gen_react = { KEY = $KEY$ }"), 1)

    def test_what_a_rise_to_the_cap_costs(self):
        # Before ideology, in approval: material x steps / divisor, as for Proportional's 2.5% to 5%... here 0 to 5%.
        costs = {}
        for ig in gen.IGS:
            material, _ideology = gen.light_reaction_terms(ig, next(i for i in gen.INSTRUMENTS if i.key == "div"))
            costs[ig] = material * cap() / gen.LIGHT_REACTION_DIVISOR
        self.assertEqual(costs["industrialists"], -2.5)
        self.assertEqual(costs["landowners"], -2.0)
        self.assertEqual(costs["trade_unions"], 0)

    def test_a_closed_or_carried_extra_draws_none(self):
        # A shift's clamp is scored, as the levied taxes' moves are (DefaultTest).
        for name in ("te_tax_light_gen_close", "te_tax_light_gen_clamp", "te_tax_light_gen_uniform"):
            self.assertNotIn("te_tax_light_gen_react", block(read(GEN_EFFECTS), name), name)
        close = flat(block(read(GEN_EFFECTS), "te_tax_light_gen_close"))
        self.assertEqual(close, "if = { limit = { NOT = { te_tax_light_holds_div = yes } has_variable = te_tax_en_div "
                                "var:te_tax_en_div > 0 } set_variable = { name = te_tax_en_div value = 0 } }")

    def test_no_relief_and_no_band(self):
        relief = flat(block(read(GEN_EFFECTS), "te_tax_light_gen_relief"))
        self.assertIn("if = { limit = { te_tax_light_levies_div = yes } set_variable = { name = te_tax_light_rl_div", relief)
        self.assertNotIn("holds_div", relief)
        self.assertNotIn("extra", relief)
        for law in UNTAXED:
            for ig in gen.IGS:
                self.assertNotIn("div", gen.light_band_weights(ig, law), (law, ig))


class RuleOffTest(unittest.TestCase):
    """Only the light setting levies it, and it stops the day the code does."""

    def test_the_levy_reads_the_rule_and_the_marker(self):
        value = flat(block(read(VALUES), "te_tax_light_levy_div_value"))
        self.assertIn("te_tax_light_in_force = yes te_tax_light_extra_div = yes", value)
        in_force = flat(block(read(TAX_TRIGGERS), "te_tax_light_in_force"))
        self.assertEqual(in_force, "te_tax_code_light_on = yes has_variable = te_tax_light_on var:te_tax_light_on >= 1")

    def test_the_rule_off_clears_the_marker_and_ends_the_entry(self):
        leave = flat(block(read(MIGRATION_EFFECTS), "te_tax_leave_code_for_rule"))
        self.assertIn("limit = { has_variable = te_tax_light_on } set_variable = { name = te_tax_light_on value = 0 }",
                      leave)
        je = flat(block(read(JE), "je_tax_code"))
        self.assertIn("flags = { hidden invalid_outcome } conclusion_desc = je_tax_code_invalid_conclusion_desc "
                      "trigger = { NOT = { te_tax_code_on = yes } }", je)
        self.assertIn("modifier = te_tax_light_levy_div value = { value = te_tax_light_levy_div_value }", je)

    def test_nothing_else_applies_the_levy(self):
        for directory in ("common", "events"):
            for path in sorted((ROOT / directory).rglob("*.txt")):
                rel = path.relative_to(ROOT).as_posix()
                if rel in (JE, MODIFIERS):
                    continue
                with self.subTest(path=rel):
                    text = strip_comments(path.read_text("utf-8-sig", "replace"))
                    self.assertNotRegex(text, r"\bte_tax_light_levy_div\b(?!_value)")


class CivilWarTest(unittest.TestCase):
    """The rebels receive the nation's rate and keep it while the war lasts; the winner continues it."""

    def test_the_rate_is_a_copied_token(self):
        self.assertIn(("te_tax_en_div", 0), gen.light_tokens())
        copy = flat(block(read(GEN_EFFECTS), "te_tax_light_gen_copy_code"))
        self.assertIn("te_tax_copy_token = { NAME = te_tax_en_div }", copy)

    def test_the_rebels_keep_it_while_the_war_lasts(self):
        # Only an AI's sync writes the extra's rate (DefaultTest), and rebels holding te_cw_origin are not one;
        # a lower level their AI sets clamps it to that level's rate (the shift, DefaultTest).
        self.assertEqual(flat(block(read(TAX_TRIGGERS), "te_tax_light_ai_uniform")),
                         "is_ai = yes NOT = { has_variable = te_cw_origin }")

    def test_the_winner_reads_it_from_its_own_variables(self):
        # A revolution's winner inherits variables, not modifiers: the levy is the entry's declaration of a
        # variable, and the entry is inherited.
        je = flat(block(read(JE), "je_tax_code"))
        self.assertIn("can_revolution_inherit = yes", je)
        self.assertIn("value = var:te_tax_en_div", flat(block(read(VALUES), "te_tax_light_levy_div_value")))


class PanelTest(unittest.TestCase):
    def test_the_row_shows_while_the_code_holds_the_tax(self):
        view = flat(block(read(VALUES), "te_tax_view_light_levied_div"))
        self.assertIn("te_tax_light_holds_div = yes", view)
        extra = flat(block(read(VALUES), "te_tax_view_light_extra_div"))
        self.assertIn("te_tax_light_extra_div = yes", extra)
        self.assertIn("ScriptValue('te_tax_view_light_levied_div')", read(LIGHT_GUI))
        self.assertIn('tooltip = "te_tax_lt_row_div_tt"', read(LIGHT_GUI))

    def test_the_tooltip_says_why_the_cap_is_low_and_names_the_laws_that_tax_dividends_in_full(self):
        table = loc(LOC)
        self.assertIn("SelectLocalization( EqualTo_CFixedPoint( Country.MakeScope.ScriptValue("
                      "'te_tax_view_light_extra_div'), '(CFixedPoint)1' ), 'te_tax_lt_extra_note_div', 'te_tax_empty' )",
                      table["te_tax_lt_row_div_tt"])
        note = loc(GEN_LOC)["te_tax_lt_extra_note_div"]
        self.assertIn("The taxation law levies no dividend tax", note)
        self.assertIn("#v 5%#!", note)
        self.assertIn("The laws that tax dividends in full are $law_proportional_taxation$, up to #v 20%#!, and", note)
        self.assertIn("$law_graduated_taxation$, up to #v 30%#!.", note)
        self.assertNotIn("Proportional Taxation", note)

    def test_the_levy_and_the_how_text(self):
        generated = loc(GEN_LOC)
        self.assertEqual(generated["te_tax_light_levy_div"], "Low $te_tax_inst_div$")
        self.assertTrue(generated["te_tax_light_levy_div_desc"])
        rates = loc(LOC)["te_tax_lt_how_rates"]
        for law in UNTAXED + ["law_traditionalism", "law_proportional_taxation"]:
            self.assertIn(f"${law}$", rates)
        self.assertIn("$te_tax_lt_extra_cap_div$", rates)
        self.assertIn("$te_tax_lt_extra_cap_div$", loc(LOC)["te_tax_lt_how_ai"])


class RetiredSelfCheckTest(unittest.TestCase):
    """TE_SELF_CHECK tax_light_div_levy is retired (2026-11-16). It read modifier:tax_dividends_add and logged BROKEN in
    every game (0 of 70 levy countries in July 1881, 0 of 92 in April 1925) while the Budget collected the levy (the
    owner's reading of PT-47): the read is blind to a tax rate a journal entry declares
    (scripting_best_practices.md, "A Tax Rate a Journal Entry Declares Is Collected but Invisible to modifier:").
    The declaration stays, and nothing may name the check, its latch or its values again."""

    def test_the_declaration_stays_on_the_entry(self):
        je = flat(block(read(JE), "je_tax_code"))
        self.assertIn("scaling_modifiers_while_active = { modifier = te_tax_light_levy_div "
                      "value = { value = te_tax_light_levy_div_value } }", je)
        self.assertEqual(je.count("modifier = te_tax_light_levy_div "), 1)

    def test_its_files_are_gone_and_nothing_names_it(self):
        self.assertFalse((ROOT / RETIRED_SELF_CHECK).exists())
        self.assertFalse((ROOT / RETIRED_SELF_CHECK_VALUES).exists())
        names = re.compile(r"te_tldv_|te_tax_light_div_levy_selfcheck|TE_SELF_CHECK \w+ tax_light_div_levy")
        for directory in ("common", "events", "gui", "localization"):
            for path in sorted((ROOT / directory).rglob("*")):
                if path.suffix not in (".txt", ".gui", ".yml"):
                    continue
                with self.subTest(path=path.relative_to(ROOT).as_posix()):
                    self.assertIsNone(names.search(path.read_text("utf-8-sig", "replace")))

    def test_the_play_test_list_records_the_outcome(self):
        text = flat(read(PLAYTEST))
        self.assertIn("The light code's low dividend tax", text)
        # Script can't see collection: the Budget line decided, in the owner's words.
        self.assertIn("Script can't measure collection", text)
        self.assertIn("dividend taxes with the light code (and per capita taxes) appear to be working", text)
        self.assertIn("tax_light_div_levy` (retired 2026-11-16)", text)
        for line in ("levy=0/70 matched, 70 at 0; control=5/5 matched; date=July 1, 1881",
                     "levy=0/92 matched, 92 at 0; control=31/32 matched; date=April 1, 1925"):
            self.assertIn(line, text)
        for build in ("81b947368", "2d26c6b5a"):
            self.assertIn(build, text)


if __name__ == "__main__":
    unittest.main()
