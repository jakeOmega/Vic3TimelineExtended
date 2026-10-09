"""The light tax code (te_tax_code_rule = te_tax_code_light).

Design: docs/superpowers/specs/2026-10-09-tax-code-light-design.md; schema:
docs/systems/tax_code_schema.md, "Light code". Structural checks on the
committed script and property checks on the generator's tables (no game install
needed):

- the bounds each law sets are its very-low and very-high rates in vanilla_parsed;
- each rate's step and the tax level the code sets from them reproduce the
  base game for a code with every tax on one step, and never give a tax a
  negative relief;
- the step tooltips' generated triggers say exactly when a step moves the level;
- the reaction and band values follow the support model's tables;
- the sync, the step command, the hooks and the panels are wired in order.
"""

import importlib.util
import itertools
import json
import re
import unittest
from decimal import Decimal
from pathlib import Path

from paradox_file_parser import ParadoxFileParser

ROOT = Path(__file__).resolve().parent

spec = importlib.util.spec_from_file_location("gen_tax_code", ROOT / "scripts/generators/gen_tax_code.py")
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)

VALUES = "common/script_values/te_tax_light_generated_values.txt"
TRIGGERS = "common/scripted_triggers/te_tax_light_generated_triggers.txt"
GEN_EFFECTS = "common/scripted_effects/te_tax_light_generated_effects.txt"
MODIFIERS = "common/static_modifiers/te_tax_light_generated_modifiers.txt"
SGUIS = "common/scripted_guis/te_tax_light_generated_sguis.txt"
CUSTOM_LOC = "common/customizable_localization/te_tax_light_generated_custom_loc.txt"
EFFECTS = "common/scripted_effects/te_tax_light_effects.txt"
TAX_TRIGGERS = "common/scripted_triggers/te_tax_triggers.txt"
EVENTS = "events/te_tax_light_events.txt"
ON_ACTIONS = "common/on_actions/te_tax_on_actions.txt"
LIGHT_GUI = "gui/journal_entry_widgets/te_tax_light_widget.gui"
LIGHT_SGUIS = "common/scripted_guis/te_tax_light_sguis.txt"
PROBE_EVENTS = "events/te_debug_tax_events.txt"
LOC = "localization/english/te_tax_l_english.yml"
GEN_LOC = "localization/english/te_tax_generated_l_english.yml"

KEYS = [instrument.key for instrument in gen.INSTRUMENTS]
BY_KEY = {instrument.key: instrument for instrument in gen.INSTRUMENTS}
LEVELS = gen.NATIVE_LEVELS
LAST = len(LEVELS) - 1
VANILLA_MODIFIER = {instrument.key: instrument.modifier for instrument in gen.INSTRUMENTS}


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


OPERATORS = {"=", "<", ">", "<=", ">=", "!=", "?=", "=="}


def plain(node):
    """Drop the parser's (operator, value) pairs, leaving dicts, lists and strings."""
    if isinstance(node, (tuple, list)) and len(node) == 2 and isinstance(node[0], str) and node[0] in OPERATORS:
        return plain(node[1])
    if isinstance(node, dict):
        return {key: plain(value) for key, value in node.items()}
    if isinstance(node, list):
        return [plain(item) for item in node]
    return node


def loc(path):
    table = {}
    for line in read(path).splitlines():
        match = re.match(r'^ ([\w.\-]+):\d+ "(.*)"$', line)
        if match:
            table[match.group(1)] = match.group(2)
    return table


def ladders():
    return gen.light_ladders()


def rung(ladder, idx):
    """The step a rate sits on: the lowest level whose rate is at least it."""
    return next(n for n, value in enumerate(ladder) if idx <= value) if idx <= ladder[-1] else LAST


class BoundsTest(unittest.TestCase):
    """The range of each tax is the law's own very-low to very-high rate."""

    def test_ladders_are_the_vanilla_laws_rates(self):
        vanilla = json.loads(read("vanilla_parsed/common/laws.json"))
        for law, by_key in ladders().items():
            body = vanilla[law][1]
            for key, ladder in by_key.items():
                for n, level in enumerate(LEVELS):
                    block_ = body.get(f"tax_modifier_{level}", ["=", {}])[1]
                    value = Decimal(block_.get(VANILLA_MODIFIER[key], ["=", "0"])[1])
                    with self.subTest(law=law, key=key, level=level):
                        self.assertEqual(BY_KEY[key].step * ladder[n], value)

    def test_every_levied_ladder_rises_strictly(self):
        # So a code with every tax on one step sits on exactly that step.
        for law, by_key in ladders().items():
            for key, ladder in by_key.items():
                if ladder[-1]:
                    with self.subTest(law=law, key=key):
                        self.assertEqual(ladder, sorted(set(ladder)))
                else:
                    self.assertEqual(ladder, [0] * len(LEVELS))

    def test_generated_bounds_and_steps_follow_the_ladders(self):
        text = read(VALUES)
        for key in KEYS:
            for n in range(len(LEVELS)):
                body = flat(block(text, f"te_tax_light_idx_{key}_{n}"))
                for law, by_key in ladders().items():
                    value = by_key[key][n]
                    with self.subTest(key=key, level=n, law=law):
                        if value:
                            self.assertIn(f"limit = {{ has_law = law_type:{law} }} value = {value} }}", body)
                        else:
                            self.assertNotIn(f"law_type:{law}", body)
            self.assertEqual(flat(block(text, f"te_tax_light_min_{key}")), f"value = te_tax_light_idx_{key}_0")
            self.assertEqual(flat(block(text, f"te_tax_light_max_{key}")), f"value = te_tax_light_idx_{key}_{LAST}")

    def test_levies_trigger_names_the_laws_that_levy_the_tax(self):
        text = read(TRIGGERS)
        for key in KEYS:
            laws = re.findall(r"has_law = law_type:(\w+)", block(text, f"te_tax_light_levies_{key}"))
            self.assertEqual(laws, [law for law, by_key in ladders().items() if by_key[key][-1]], key)

    def test_range_text_is_the_ladders_ends(self):
        table = loc(GEN_LOC)
        for n, law in gen.light_laws():
            for key in KEYS:
                ladder = ladders()[law][key]
                name = f"te_tax_lt_range_{key}_{n}"
                with self.subTest(name=name):
                    if not ladder[-1]:
                        self.assertNotIn(name, table)
                        continue
                    low, high = BY_KEY[key].step * ladder[0], BY_KEY[key].step * ladder[-1]
                    if BY_KEY[key].percent:
                        self.assertEqual(table[name], f"#v {gen.fmt(low * 100)}–{gen.fmt(high * 100)}%#!")
                    else:
                        self.assertEqual(table[name], f"@money!#v {gen.fmt(low)}–{gen.fmt(high)}#!")


class StepTest(unittest.TestCase):
    """Each rate's step, and the level and relief that follow from it."""

    def parse_rungs(self, key):
        """{law: [thresholds for steps LAST-1 .. 0]} from te_tax_light_rung_<key>."""
        body = block(read(VALUES), f"te_tax_light_rung_{key}")
        out = {}
        for branch in re.split(r"(?=\b(?:if|else_if) = \{\s*limit = \{ has_law)", body)[1:]:
            law = re.search(r"has_law = law_type:(\w+)", branch).group(1)
            out[law] = [(int(t), int(v)) for t, v in re.findall(
                rf"var:te_tax_en_{key} <= (\d+) \}} value = (\d+)", branch)]
        return out

    def test_generated_step_matches_the_ladder_for_every_index(self):
        for key in KEYS:
            branches = self.parse_rungs(key)
            for law, by_key in ladders().items():
                ladder = by_key[key]
                if not ladder[-1]:
                    self.assertNotIn(law, branches)
                    continue
                for idx in range(ladder[0], ladder[-1] + 1):
                    value = LAST
                    for threshold, step in branches[law]:  # applied in order, the last true one wins
                        if idx <= threshold:
                            value = step
                    with self.subTest(key=key, law=law, idx=idx):
                        self.assertEqual(value, rung(ladder, idx))

    def test_a_uniform_code_sits_on_its_level_and_carries_no_relief(self):
        # What the migration writes and what an AI country's code always is: the
        # base game's rates, the base game's level, no relief modifier.
        for law, by_key in ladders().items():
            for n in range(len(LEVELS)):
                code = {key: ladder[n] for key, ladder in by_key.items()}
                level = max(rung(by_key[key], code[key]) for key in KEYS if by_key[key][-1])
                with self.subTest(law=law, level=LEVELS[n]):
                    self.assertEqual(level, n)
                    for key, ladder in by_key.items():
                        self.assertEqual(ladder[level] - code[key], 0)

    def test_every_code_in_range_collects_its_own_rates_with_no_negative_relief(self):
        for law, by_key in ladders().items():
            levied = [key for key in KEYS if by_key[key][-1]]
            ranges = [range(by_key[key][0], by_key[key][-1] + 1) for key in levied]
            for combo in itertools.product(*ranges):
                code = dict(zip(levied, combo))
                level = max(rung(by_key[key], code[key]) for key in levied)
                for key in levied:
                    relief = by_key[key][level] - code[key]
                    self.assertGreaterEqual(relief, 0, (law, code))
                    # The law's rate at the level, less the relief, is the code's rate.
                    self.assertEqual(by_key[key][level] - relief, code[key])
                # The level is the step of some tax: lowering every other tax never moves it.
                self.assertIn(level, [rung(by_key[key], code[key]) for key in levied])

    def test_the_tooltip_triggers_say_exactly_when_a_step_moves_the_level(self):
        text = read(TRIGGERS)
        for key in KEYS:
            up = block(text, f"te_tax_light_up_raises_{key}")
            down = block(text, f"te_tax_light_down_lowers_{key}")
            for law, by_key in ladders().items():
                ladder = by_key[key]
                if not ladder[-1]:
                    self.assertNotIn(f"law_type:{law}", up)
                    continue
                for level in range(len(LEVELS)):
                    for idx in range(ladder[0], ladder[-1]):
                        raises = rung(ladder, idx + 1) > level
                        # The generated literal: var:en >= ladder[level] under this law and level.
                        literal = level < LAST and idx >= ladder[level]
                        with self.subTest(key=key, law=law, level=level, idx=idx):
                            self.assertEqual(raises, literal)
                    if level < LAST:
                        self.assertIn(f"has_law = law_type:{law} var:te_tax_light_level = {level} "
                                      f"var:te_tax_en_{key} >= {ladder[level]}", flat(up))
                for level in range(1, len(LEVELS)):
                    for idx in range(ladder[0] + 1, ladder[-1] + 1):
                        # This tax alone on the level: one step down leaves it iff its new step is lower.
                        if rung(ladder, idx) != level:
                            continue
                        leaves = rung(ladder, idx - 1) < level
                        literal = idx <= ladder[level - 1] + 1
                        with self.subTest(key=key, law=law, level=level, idx=idx):
                            self.assertEqual(leaves, literal)
                    self.assertIn(f"has_law = law_type:{law} var:te_tax_light_level = {level} "
                                  f"var:te_tax_light_rg_{key} = {level}", flat(down))
                    self.assertIn(f"var:te_tax_en_{key} <= {ladder[level - 1] + 1}", flat(down))
            # Only when no other tax sits on the level or above.
            others = [k for k in KEYS if k != key]
            for other in others:
                self.assertIn(f"has_variable = te_tax_light_rg_{other} var:te_tax_light_rg_{other} >=", flat(down))
            self.assertIn(f"var:te_tax_light_level < {LAST}", flat(block(text, f"te_tax_light_max_raises_{key}")))
            self.assertNotIn("var:te_tax_en_", flat(block(text, f"te_tax_light_min_lowers_{key}")))


class GeneratedEffectsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = read(GEN_EFFECTS)

    def test_relief_is_the_laws_rate_at_the_level_less_the_code(self):
        body = flat(block(self.text, "te_tax_light_gen_relief"))
        for key in KEYS:
            rl = f"te_tax_light_rl_{key}"
            with self.subTest(key=key):
                self.assertIn(f"set_variable = {{ name = {rl} value = te_tax_light_idx_{key}_at_level }} "
                              f"change_variable = {{ name = {rl} subtract = var:te_tax_en_{key} }}", body)
                self.assertIn(f"if = {{ limit = {{ var:{rl} < 0 }} set_variable = {{ name = {rl} value = 0 }} }}", body)
                # Removed and re-added every call; the multiplier is a persistent variable.
                self.assertIn(f"remove_modifier = te_tax_light_relief_{key}", body)
                self.assertIn(f"add_modifier = {{ name = te_tax_light_relief_{key} multiplier = var:{rl} }}", body)

    def test_the_level_is_the_highest_step(self):
        body = flat(block(self.text, "te_tax_light_gen_steps"))
        self.assertTrue(body.startswith("set_variable = { name = te_tax_light_tgt value = 0 }"))
        for key in KEYS:
            self.assertIn(f"set_variable = {{ name = te_tax_light_rg_{key} value = te_tax_light_rung_{key} }} "
                          f"if = {{ limit = {{ var:te_tax_light_rg_{key} > var:te_tax_light_tgt }} "
                          f"set_variable = {{ name = te_tax_light_tgt value = var:te_tax_light_rg_{key} }} }}", body)
        levels = flat(block(self.text, "te_tax_light_gen_set_level"))
        for n, level in enumerate(LEVELS):
            self.assertIn(f"limit = {{ var:te_tax_light_level = {n} NOT = {{ tax_level = {level} }} }} "
                          f"set_tax_level = {level}", levels)

    def test_a_law_change_clamps_and_starts_a_new_tax_at_the_level(self):
        body = flat(block(self.text, "te_tax_light_gen_clamp"))
        for key in KEYS:
            en = f"te_tax_en_{key}"
            self.assertIn(f"if = {{ limit = {{ NOT = {{ te_tax_light_levies_{key} = yes }} }} "
                          f"set_variable = {{ name = {en} value = 0 }} }} else_if = {{ limit = {{ var:{en} = 0 }} "
                          f"set_variable = {{ name = {en} value = te_tax_light_idx_{key}_at_level }} }} else = {{ "
                          f"clamp_variable = {{ name = {en} min = te_tax_light_min_{key} max = te_tax_light_max_{key} }} }}",
                          body)
        # No reaction for a law change: its own approval covers it.
        self.assertNotIn("te_tax_light_gen_react", body)

    def test_the_ai_follows_its_native_level_and_is_scored(self):
        unscored = flat(block(self.text, "te_tax_light_gen_uniform"))
        scored = flat(block(self.text, "te_tax_light_gen_uniform_scored"))
        self.assertNotIn("te_tax_light_gen_react", unscored)
        for key in KEYS:
            self.assertIn(f"set_variable = {{ name = te_tax_en_{key} value = te_tax_light_idx_{key}_native }}", unscored)
            self.assertIn(f"te_tax_light_gen_react = {{ KEY = {key} }}", scored)
        shift = flat(block(self.text, "te_tax_light_gen_shift"))
        for key in KEYS:
            self.assertIn(f"change_variable = {{ name = te_tax_en_{key} add = te_tax_light_idx_{key}_native }} "
                          f"change_variable = {{ name = te_tax_en_{key} subtract = te_tax_light_idx_{key}_at_level }} "
                          f"clamp_variable", shift)

    def test_reaction_scoring(self):
        body = flat(block(self.text, "te_tax_light_gen_react"))
        weight = gen.fmt(gen.LIGHT_PLEASE_WEIGHT)
        for ig in gen.IGS:
            with self.subTest(ig=ig):
                self.assertIn(f"set_local_variable = {{ name = te_tax_lt_s value = te_tax_light_rc_$KEY$_{ig} }} "
                              "change_local_variable = { name = te_tax_lt_s multiply = var:te_tax_light_d } "
                              f"if = {{ limit = {{ local_var:te_tax_lt_s > 0 }} change_local_variable = "
                              f"{{ name = te_tax_lt_s multiply = {weight} }} }}", body)
                self.assertIn(f"change_variable = {{ name = te_tax_lr_{ig} add = {{ value = local_var:te_tax_lt_s "
                              f"divide = {gen.LIGHT_REACTION_DIVISOR} }} }} clamp_variable = {{ name = te_tax_lr_{ig} "
                              f"min = -{gen.LIGHT_REACTION_CAP} max = {gen.LIGHT_REACTION_CAP} }}", body)
        self.assertEqual(gen.LIGHT_PLEASE_WEIGHT, Decimal("0.5"))  # owner ruling 2026-10-09
        decay = flat(block(self.text, "te_tax_light_gen_decay"))
        for ig in gen.IGS:
            self.assertIn(f"change_variable = {{ name = te_tax_lr_{ig} multiply = {gen.fmt(gen.LIGHT_DECAY)} }}", decay)

    def test_a_whole_range_sweep_costs_a_fully_exposed_group_the_radical_law_change(self):
        # Material reason only: four vanilla levels x -10 / divisor = -10 approval,
        # IG_APPROVAL_FROM_RADICAL_LAW_CHANGE in vanilla 1.14.5's defines.
        self.assertEqual(4 * gen.MATERIAL_WEIGHT / gen.LIGHT_REACTION_DIVISOR, -gen.LIGHT_REACTION_CAP)

    def test_apply_reactions_swaps_one_modifier_by_sign(self):
        body = flat(block(self.text, "te_tax_light_gen_apply_reactions"))
        for ig in gen.IGS:
            lr, mag = f"te_tax_lr_{ig}", f"te_tax_lr_mag_{ig}"
            self.assertIn(f"if = {{ limit = {{ var:{lr} >= 0.5 }} set_variable = {{ name = {mag} value = {{ value = "
                          f"var:{lr} round = yes }} }} add_modifier = {{ name = te_tax_light_react_{ig}_pos "
                          f"multiplier = var:{mag} }} }}", body)
            self.assertIn(f"else_if = {{ limit = {{ var:{lr} <= -0.5 }} set_variable = {{ name = {mag} value = {{ "
                          f"value = var:{lr} multiply = -1 round = yes }} }} add_modifier = {{ name = "
                          f"te_tax_light_react_{ig}_neg multiplier = var:{mag} }} }}", body)

    def test_bands_read_the_relief_each_group_gets(self):
        body = flat(block(self.text, "te_tax_light_gen_bands"))
        for ig in gen.IGS:
            self.assertIn(f"set_variable = {{ name = te_tax_light_rlv value = te_tax_light_rlv_{ig} }} "
                          f"if = {{ limit = {{ var:te_tax_light_rlv >= 2 }} set_variable = {{ name = "
                          f"te_tax_light_band_{ig} value = 2 }} }} else_if = {{ limit = {{ var:te_tax_light_rlv >= 1 }} "
                          f"set_variable = {{ name = te_tax_light_band_{ig} value = 1 }} }} else = {{ set_variable = "
                          f"{{ name = te_tax_light_band_{ig} value = 0 }} }}", body)


class ValuesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = read(VALUES)

    def test_reaction_coefficients_follow_the_support_model(self):
        for instrument in gen.INSTRUMENTS:
            levels = instrument.step / gen.LEVEL_STEPS[instrument.key]
            sign = 1 if instrument.key in gen.PROGRESSIVE_KEYS else -1
            for ig in gen.IGS:
                exposure = gen.exposure(ig)[instrument.key]
                material = gen.MATERIAL_WEIGHT * exposure * levels
                ideology = gen.IDEOLOGY_WEIGHT * levels * sign
                body = flat(block(self.text, f"te_tax_light_rc_{instrument.key}_{ig}"))
                with self.subTest(key=instrument.key, ig=ig):
                    self.assertEqual(body, f"value = te_tax_ideo_p_{ig} multiply = {gen._dec(ideology)} "
                                           f"add = {gen._dec(material)}")

    def test_band_weights_are_exposure_times_levels_on_levied_taxes(self):
        for ig in gen.IGS:
            body = block(self.text, f"te_tax_light_rlv_{ig}")
            for law, by_key in ladders().items():
                for key in KEYS:
                    weight = gen.exposure(ig)[key] * BY_KEY[key].step / gen.LEVEL_STEPS[key]
                    levied = by_key[key][-1] > 0
                    with self.subTest(ig=ig, law=law, key=key):
                        branch = re.search(rf"limit = \{{ has_law = law_type:{law} \}}(.*?)\n\t\}}", body, re.S)
                        text = branch.group(1) if branch else ""
                        term = f"var:te_tax_light_rl_{key} multiply = {gen._dec(weight)}"
                        if levied and weight:
                            self.assertIn(term, text)
                        else:
                            self.assertNotIn(f"te_tax_light_rl_{key}", text)

    def test_every_gui_view_is_guarded(self):
        for name in re.findall(r"(?m)^(te_tax_view_light_\w+) = \{", self.text):
            body = block(self.text, name)
            for var in set(re.findall(r"var:(\w+)", body)):
                with self.subTest(name=name, var=var):
                    self.assertIn(f"has_variable = {var}", body)


class ModifiersTest(unittest.TestCase):
    def test_relief_is_one_step_below_zero_and_reactions_one_point(self):
        parser = ParadoxFileParser()
        parser.parse_file(str(ROOT / MODIFIERS), apply_directives=False)
        mods = plain(parser.data)
        for instrument in gen.INSTRUMENTS:
            body = mods[f"te_tax_light_relief_{instrument.key}"]
            self.assertEqual(Decimal(body[instrument.modifier]), -instrument.step)
            self.assertEqual(set(body), {"icon", instrument.modifier})
        for ig in gen.IGS:
            for sign, value in (("pos", "1"), ("neg", "-1")):
                body = mods[f"te_tax_light_react_{ig}_{sign}"]
                self.assertEqual(body[f"interest_group_ig_{ig}_approval_add"], value)

    def test_names_and_descriptions(self):
        table = loc(GEN_LOC)
        for name in [f"te_tax_light_relief_{k}" for k in KEYS] + [
                f"te_tax_light_react_{ig}_{s}" for ig in gen.IGS for s in ("pos", "neg")]:
            with self.subTest(name=name):
                self.assertTrue(table.get(name))
                self.assertTrue(table.get(f"{name}_desc"))


class SyncTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = read(EFFECTS)

    def test_sync_order(self):
        body = flat(block(self.text, "te_tax_light_sync"))
        self.assertTrue(body.startswith("if = { limit = { te_tax_light_in_force = yes } te_tax_light_gen_init = yes"))

        def in_order(parts, start=0):
            at = start
            for part in parts:
                found = body.find(part, at)
                self.assertNotEqual(found, -1, f"{part!r} not after {at}")
                at = found + len(part)
            return at

        # 1. A law change: an AI's code follows its level, a player's is clamped.
        at = in_order(["var:te_tax_light_law = te_tax_light_law_id", "limit = { is_ai = yes } te_tax_light_gen_uniform = yes",
                       "else = { te_tax_light_gen_clamp = yes }",
                       "set_variable = { name = te_tax_light_law value = te_tax_light_law_id }"])
        # 2. The AI: every tax follows the native level, scored.
        at = in_order(["limit = { is_ai = yes }", "te_tax_light_gen_uniform_scored = yes",
                       "set_variable = { name = te_tax_light_level value = te_tax_light_native_level }",
                       "te_tax_light_gen_steps = yes"], at)
        # The player: an outside level move is adopted, then the level follows the heaviest tax.
        at = in_order(["else = {", "te_tax_light_gen_shift = yes", "te_tax_light_gen_steps = yes",
                       "limit = { var:te_tax_light_law > 0 } set_variable = { name = te_tax_light_level "
                       "value = var:te_tax_light_tgt } te_tax_light_gen_set_level = yes"], at)
        # 3. Relief, reactions and views, for both.
        in_order(["te_tax_light_gen_relief = yes", "te_tax_light_gen_apply_reactions = yes",
                  "te_tax_light_gen_bands = yes", "te_tax_gen_ig_views = yes"], at)

    def test_monthly_fades_then_syncs(self):
        body = flat(block(self.text, "te_tax_light_process_month"))
        self.assertLess(body.index("te_tax_light_gen_decay = yes"), body.index("te_tax_light_sync = yes"))

    def test_migration_writes_the_uniform_code_then_syncs(self):
        body = flat(block(self.text, "te_tax_light_migrate_country"))
        self.assertIn("te_tax_code_light_on = yes", body)
        order = ["te_tax_light_gen_init = yes", "te_tax_light_gen_uniform = yes",
                 "set_variable = { name = te_tax_light_law value = te_tax_light_law_id }",
                 "set_variable = { name = te_tax_light_level value = te_tax_light_native_level }",
                 "set_variable = { name = te_tax_light_on value = 1 }", "te_tax_light_sync = yes"]
        positions = [body.index(part) for part in order]
        self.assertEqual(positions, sorted(positions))
        self.assertNotIn("activate_law", body)

    def test_the_step_command(self):
        body = flat(block(self.text, "te_tax_light_cmd_step"))
        self.assertTrue(body.startswith("if = { limit = { te_tax_light_can_step = { KEY = $KEY$ DIR = $DIR$ } }"))
        hidden = body[body.index("hidden_effect"):]
        # The tooltip lines read the state before the change.
        self.assertLess(body.index("te_tax_light_step_tt_$DIR$"), body.index("hidden_effect"))
        order = ["set_variable = { name = te_tax_light_was value = var:te_tax_en_$KEY$ }",
                 "te_tax_light_step_$DIR$ = { KEY = $KEY$ }",
                 "change_variable = { name = te_tax_light_d subtract = var:te_tax_light_was }",
                 "te_tax_light_gen_react = { KEY = $KEY$ }", "te_tax_light_sync = yes"]
        positions = [hidden.index(part) for part in order]
        self.assertEqual(positions, sorted(positions))
        for direction in (0, 1):
            step = flat(block(self.text, f"te_tax_light_step_{direction}"))
            self.assertIn("clamp_variable = { name = te_tax_en_$KEY$ min = te_tax_light_min_$KEY$ "
                          "max = te_tax_light_max_$KEY$ }", step)
        self.assertIn("value = te_tax_light_min_$KEY$", flat(block(self.text, "te_tax_light_step_2")))
        self.assertIn("value = te_tax_light_max_$KEY$", flat(block(self.text, "te_tax_light_step_3")))
        for direction, trigger in ((0, "down_lowers"), (1, "up_raises"), (2, "min_lowers"), (3, "max_raises")):
            self.assertIn(f"te_tax_light_{trigger}_$KEY$ = yes", flat(block(self.text, f"te_tax_light_step_tt_{direction}")))

    def test_step_triggers_keep_the_variable_on_the_left(self):
        text = read(TAX_TRIGGERS)
        self.assertIn("var:te_tax_en_$KEY$ > te_tax_light_min_$KEY$", flat(block(text, "te_tax_light_can_step_0")))
        self.assertIn("var:te_tax_en_$KEY$ < te_tax_light_max_$KEY$", flat(block(text, "te_tax_light_can_step_1")))
        can = flat(block(text, "te_tax_light_can_step"))
        self.assertIn("te_tax_light_in_force = yes", can)
        self.assertIn("te_tax_light_levies_$KEY$ = yes", can)

    def test_handlers_are_generated_per_tax_and_op(self):
        text = read(SGUIS)
        for key in KEYS:
            body = flat(block(text, f"te_tax_light_step_{key}_sgui"))
            self.assertIn("is_shown = { te_tax_light_in_force = yes }", body)
            for op in gen.LIGHT_OPS:
                self.assertIn(f"te_tax_light_can_step = {{ KEY = {key} DIR = {op} }}", body)
                self.assertIn(f"te_tax_light_cmd_step = {{ KEY = {key} DIR = {op} }}", body)


class HookTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = read(ON_ACTIONS)

    def test_each_handler_raises_its_event_under_the_light_setting(self):
        expected = {
            "te_tax_light_on_game_started": "te_tax_light.2",
            "te_tax_light_on_country_formed": "te_tax_light.2",
            "te_tax_light_on_country_released": "te_tax_light.2",
            "te_tax_light_on_law_activated": "te_tax_light.3",
        }
        for name, event in expected.items():
            body = flat(block(self.text, name))
            with self.subTest(handler=name):
                self.assertIn("te_tax_code_light_on = yes", body)
                self.assertIn(f"trigger_event = {{ id = {event} }}", body)
        dispatch = flat(block(self.text, "te_tax_light_monthly_dispatch"))
        self.assertLess(dispatch.index("trigger_event = { id = te_tax_light.1 }"),
                        dispatch.index("trigger_event = { id = te_tax_light.2 }"))
        released = flat(block(self.text, "te_tax_light_on_country_released"))
        self.assertLess(released.index("set_variable = { name = te_tax_light_on value = 0 }"),
                        released.index("trigger_event = { id = te_tax_light.2 }"))
        law = flat(block(self.text, "te_tax_light_on_law_activated"))
        self.assertIn("law_type = { is_same_law_group_as = law_type:law_proportional_taxation }", law)
        self.assertIn("owner = { te_tax_light_in_force = yes }", law)

    def test_events_are_hidden_country_events_on_the_light_setting(self):
        text = read(EVENTS)
        for n, effect in ((1, "te_tax_light_process_month"), (2, "te_tax_light_migrate_country"),
                          (3, "te_tax_light_sync")):
            body = flat(block(text, f"te_tax_light.{n}"))
            with self.subTest(event=n):
                self.assertIn("type = country_event hidden = yes", body)
                self.assertIn("trigger = { te_tax_code_light_on = yes }", body)
                self.assertIn(f"immediate = {{ {effect} = yes }}", body)

    def test_the_probe_harness_refuses_every_enabled_setting(self):
        body = flat(block(read(PROBE_EVENTS), "te_debug_tax.1"))
        for option in ("te_tax_code_enabled", "te_tax_code_enabled_customs", "te_tax_code_light"):
            self.assertIn(f"NOT = {{ has_game_rule = {option} }}", body)


class PanelTest(unittest.TestCase):
    def test_rows_use_the_light_handlers_and_hide_an_unlevied_tax(self):
        text = read(LIGHT_GUI)
        for key in KEYS:
            with self.subTest(key=key):
                self.assertIn(f"datacontext = \"[GetScriptedGui('te_tax_light_step_{key}_sgui')]\"", text)
                self.assertIn(f"ScriptValue('te_tax_view_light_levied_{key}')", text)
                self.assertIn(f"GetPlayer.GetCustom('te_tax_lt_range_{key}')", text)
                self.assertIn(f"GetPlayer.GetCustom('te_tax_lt_rung_{key}')", text)
        self.assertEqual(text.count('blockoverride "row_arrow" {}'), len(KEYS))

    def test_display_gate(self):
        body = flat(block(read(LIGHT_SGUIS), "te_tax_show_light_sgui"))
        self.assertIn("is_shown = { te_tax_light_in_force = yes }", body)
        self.assertIn("is_valid = { always = no }", body)

    def test_custom_loc_names_come_from_vanilla_keys(self):
        text = read(CUSTOM_LOC)
        for n, level in enumerate(LEVELS):
            self.assertIn(f"trigger = {{ te_tax_view_light_level = {n} }}\n\t\tlocalization_key = tax_level_{level}", text)
        for n, law in gen.light_laws():
            self.assertIn(f"trigger = {{ te_tax_view_light_law = {n} }}\n\t\tlocalization_key = {law}", text)

    def test_hand_written_loc_exists(self):
        table = loc(LOC)
        names = set(re.findall(r'"(te_tax_lt_\w+)"', read(LIGHT_GUI)))
        names |= set(re.findall(r"\b(te_tax_lt_(?:tt|level|not|law)_\w+)\b", read(EFFECTS) + read(TAX_TRIGGERS)))
        names -= {f"te_tax_lt_tt_react_{k}" for k in KEYS}  # generated
        self.assertTrue(names)
        for name in sorted(names):
            if name.endswith("_"):  # a $KEY$ family: te_tax_lt_tt_react_$KEY$ is generated
                continue
            with self.subTest(name=name):
                self.assertTrue(table.get(name), "no loc")


if __name__ == "__main__":
    unittest.main()
