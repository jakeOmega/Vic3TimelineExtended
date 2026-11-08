"""Cultural Hegemony's standing modifiers are scaling modifiers on je_cultural_hegemony.

Since 1.15 the entry declares each in `scaling_modifiers_while_active` and the
engine re-reads its value from the owning country about every four days
(design: docs/superpowers/specs/2026-11-06-scaling-modifiers-design.md § 4.6).
These tests pin each declaration and its value's "off" gate, which must read 0
wherever the old code removed the modifier; the four programmes' country
variables, which every enable and disable site writes; the previews the
buttons keep; and that the refresh code the declarations replaced is gone.
test_journal_entry_shape.py checks the tree-wide rule that nothing adds,
removes or tests a declared key.
"""

import re
import unittest
from pathlib import Path

from je_multiplier_scope_audit import parse_text

ROOT = Path(__file__).resolve().parent
JE = ROOT / "common/journal_entries/je_cultural_hegemony.txt"
VALUES = ROOT / "common/script_values/cultural_hegemony_script_values.txt"
EFFECTS = ROOT / "common/scripted_effects/cultural_hegemony_effects.txt"
DEBUG_EFFECTS = ROOT / "common/scripted_effects/te_debug_ch_effects.txt"
TRIGGERS = ROOT / "common/scripted_triggers/cultural_hegemony_triggers.txt"
BUTTONS = ROOT / "common/scripted_buttons/cultural_hegemony_buttons.txt"
SGUIS = ROOT / "common/scripted_guis/cultural_hegemony_sguis.txt"
EVENTS = ROOT / "events/cultural_hegemony_events.txt"
LEGACY = "common/scripted_effects/legacy_modifier_cleanup.txt"
LOC_DIR = ROOT / "localization/english"

# programme -> (its modifier, its country variable, the op its end tooltip is named for)
PROGRAMMES = {
    "world_exposition": ("ch_world_exposition", "ch_world_exposition_on", "outreach"),
    "cultural_institutes": ("ch_cultural_institutes_program", "ch_cultural_institutes_on", "institutes"),
    "global_media_campaign": ("ch_global_media_campaign", "ch_global_media_campaign_on", "media"),
    "cultural_protectionism": ("ch_cultural_protectionism_program", "ch_cultural_protectionism_on", "protectionism"),
}

# modifier -> (the gate in its value's limit, what it adds); None for a block that is one named value.
# Every value is an inline block, as in all of vanilla's uses (08_tsarpoints.txt, 00_communism.txt):
# the bare `value = <name>` form is unproven in the engine.
KEYS = {
    "cultural_hegemony_effect": None,
    "cultural_hegemony_foreign_benchmark": ("ch_trails_hegemon", "var:ch_benchmark_applied"),
    "ch_cultural_program_funding": ("ch_program_funding_in_force", "ch_program_funding_level_value"),
    "ch_cultural_program_funding_cost": ("ch_program_funding_in_force", "ch_program_funding_total_cost_mult"),
    "ch_world_exposition_cost": ("ch_active_world_exposition", "ch_program_funding_cost_mult"),
}
KEYS.update({modifier: (f"ch_active_{prog}", "1") for prog, (modifier, _, _) in PROGRAMMES.items()})

WRAPPERS = ("ch_program_funding_level_value_for_je", "ch_program_funding_cost_mult_for_je",
            "ch_program_funding_total_cost_mult_for_je")


def _text(path):
    return path.read_text(encoding="utf-8-sig")


def _top_level_block(body, header):
    """One top-level `header = { ... }` entry, header through the first
    unindented closing brace (nested braces are always tab-indented)."""
    block = body[body.index("\n" + header) + 1:]
    return block[: block.index("\n}\n") + 3]


def _entry():
    nodes, _ = parse_text(_text(JE), "common/journal_entries/je_cultural_hegemony.txt")
    return next(n for n in nodes if n.key == "je_cultural_hegemony")


def _child(node, key):
    return next((c for c in node.children if c.key == key), None)


def _declarations():
    """modifier -> [the value node] for every scaling_modifiers_while_active block on the entry."""
    out = {}
    for block in (c for c in _entry().children if c.key == "scaling_modifiers_while_active"):
        out.setdefault(_child(block, "modifier").value, []).append(_child(block, "value"))
    return out


def _pulse():
    """The entry's monthly pulse effect, as text."""
    text = _text(JE)
    start = text.index("\ton_monthly_pulse = {")
    return text[start:text.index("\n\t}\n", start) + 4]


class DeclarationTests(unittest.TestCase):
    def test_the_entry_declares_exactly_the_nine_once_each(self):
        declared = _declarations()
        self.assertEqual(set(declared), set(KEYS))
        for modifier, values in declared.items():
            self.assertEqual(len(values), 1, modifier)

    def test_each_value_is_zero_outside_its_gate(self):
        """`value = { value = 0 if = { limit = { <gate> = yes } add = <x> } }`, or
        `value = { value = <named value> }`: always a block, never bare."""
        for modifier, spec in KEYS.items():
            with self.subTest(modifier=modifier):
                value = _declarations()[modifier][0]
                self.assertIsNone(value.value, "an inline value block")
                if spec is None:
                    self.assertEqual([(c.key, c.value) for c in value.children],
                                     [("value", "cultural_hegemony_modifier_mult")])
                    continue
                gate, add = spec
                self.assertEqual([(c.key, c.value) for c in value.children if c.key != "if"], [("value", "0")])
                branch = _child(value, "if")
                limit = _child(branch, "limit")
                self.assertEqual([(c.key, c.value) for c in limit.children], [(gate, "yes")])
                self.assertEqual(_child(branch, "add").value, add)

    def test_cultural_hegemony_effect(self):
        block = _top_level_block(_text(VALUES), "cultural_hegemony_modifier_mult = {")
        # The old pulse added it from 1% share at the share, clamped 0-100. The
        # value reads the monthly cache, never the live (world-wide) share.
        self.assertRegex(block, r"limit = \{\s*has_variable = ch_total\s*var:ch_total >= 1\s*\}\s*add = var:ch_total")
        self.assertIn("min = 0", block)
        self.assertIn("max = cultural_hegemony_modifier_max_mult", block)
        self.assertNotIn("cultural_pull_total", block)
        self.assertNotIn("owner", block)
        self.assertRegex(_text(VALUES), r"(?m)^cultural_hegemony_modifier_max_mult = 100$")

    def test_the_benchmark_trigger(self):
        block = _top_level_block(_text(TRIGGERS), "ch_trails_hegemon = {")
        body = [line.strip() for line in block.splitlines()[1:-1] if line.strip()]
        self.assertEqual(body, ["has_journal_entry = je_cultural_hegemony", "has_variable = ch_benchmark_applied",
                                "var:ch_benchmark_applied >= 0.1"])

    def test_the_pulse_writes_the_benchmark_every_month(self):
        pulse = _pulse()
        # Unconditional (a direct child of the pulse's effect), then 0 below 0.1:
        # the old code added the modifier exactly when the live value was >= 0.1.
        self.assertRegex(pulse, r"\n\t\t\tset_variable = \{ name = ch_benchmark_applied value = cultural_hegemony_benchmark_mult \}"
                                r"\n\t\t\tif = \{\n\t\t\t\tlimit = \{ var:ch_benchmark_applied < 0\.1 \}"
                                r"\n\t\t\t\tset_variable = \{ name = ch_benchmark_applied value = 0 \}")

    def test_funding_is_in_force_under_the_ministry_from_one_step(self):
        block = _top_level_block(_text(TRIGGERS), "ch_program_funding_in_force = {")
        body = [line.strip() for line in block.splitlines()[1:-1] if line.strip()]
        self.assertEqual(body, ["has_law = law_type:law_ministry_of_culture", "ch_program_funding_level_value >= 1"])

    def test_each_programme_is_on_while_its_variable_is_set(self):
        triggers = _text(TRIGGERS)
        for prog, (_, variable, _) in PROGRAMMES.items():
            with self.subTest(programme=prog):
                block = _top_level_block(triggers, f"ch_active_{prog} = {{")
                body = [line.strip() for line in block.splitlines()[1:-1] if line.strip()]
                self.assertEqual(body, ["has_journal_entry = je_cultural_hegemony", f"has_variable = {variable}"])


class ProgrammeVariableTests(unittest.TestCase):
    """Every site that starts a programme sets its variable, every site that ends
    one removes it, and nothing else writes them (but the old-save migration)."""

    SET = re.compile(r"set_variable = \{ name = (ch_\w+_on) value = yes \}")
    REMOVE = re.compile(r"remove_variable = (ch_\w+_on)\b")

    def test_each_enable_sets_and_each_disable_removes(self):
        effects = _text(EFFECTS)
        for prog, (_, variable, _) in PROGRAMMES.items():
            with self.subTest(programme=prog):
                on = _top_level_block(effects, f"ch_effect_{prog} = {{")
                off = _top_level_block(effects, f"ch_effect_disable_{prog} = {{")
                self.assertEqual(self.SET.findall(on), [variable])
                self.assertEqual(self.REMOVE.findall(on), [])
                self.assertEqual(self.REMOVE.findall(off), [variable])
                self.assertEqual(self.SET.findall(off), [])

    def test_losing_the_ministry_ends_all_four(self):
        pulse = _pulse()
        strip = pulse[pulse.index("limit = { NOT = { has_law = law_type:law_ministry_of_culture } }"):]
        strip = strip[: strip.index("\n\t\t\t}\n")]
        # Through ch_shut_down_programmes, which the rule switched off mid-game runs too (the invalid outcome).
        self.assertIn("ch_shut_down_programmes = yes", strip)
        shut = _top_level_block(_text(EFFECTS), "ch_shut_down_programmes = {")
        self.assertIn("set_variable = { name = ch_program_funding_level value = 0 }", shut)
        self.assertEqual(sorted(self.REMOVE.findall(shut)), sorted(v for _, v, _ in PROGRAMMES.values()))
        self.assertEqual(_text(JE).count("ch_shut_down_programmes = yes"), 2, "the pulse and the invalid outcome")

    def test_nothing_else_writes_them(self):
        variables = {v for _, v, _ in PROGRAMMES.values()}
        effects = _text(EFFECTS)
        allowed = {_top_level_block(effects, f"ch_effect_{p} = {{") for p in PROGRAMMES}
        allowed |= {_top_level_block(effects, f"ch_effect_disable_{p} = {{") for p in PROGRAMMES}
        allowed.add(_top_level_block(effects, "ch_shut_down_programmes = {"))
        for sub in ("common", "events"):
            for path in sorted((ROOT / sub).rglob("*.txt")):
                rel = path.relative_to(ROOT).as_posix()
                if rel == LEGACY:
                    continue
                text = _text(path)
                if path == EFFECTS:
                    for block in allowed:
                        text = text.replace(block, "")
                elif path == JE:
                    text = text.replace(_pulse(), "")
                for name in re.findall(r"(?:set_variable|remove_variable|change_variable)\b[^\n]*?\b(ch_\w+_on)\b",
                                       text):
                    with self.subTest(file=rel):
                        self.assertNotIn(name, variables)


class PreviewTests(unittest.TestCase):
    """A control that now only writes a variable keeps its tooltip."""

    @classmethod
    def setUpClass(cls):
        cls.effects = _text(EFFECTS)
        cls.loc = {}
        for path in LOC_DIR.rglob("*.yml"):
            for line in path.read_text(encoding="utf-8-sig").splitlines():
                m = re.match(r'^ ([\w.\-]+):\d* "(.*)"\s*$', line)
                if m:
                    cls.loc[m.group(1)] = m.group(2)

    def test_starting_a_programme_previews_its_modifier(self):
        for prog, (modifier, _, _) in PROGRAMMES.items():
            with self.subTest(programme=prog):
                block = _top_level_block(self.effects, f"ch_effect_{prog} = {{")
                preview = block[block.index("show_as_tooltip = {"):block.index("hidden_effect = {")]
                self.assertIn(f"je:je_cultural_hegemony ?= {{ add_modifier = {{ name = {modifier} }} }}", preview)
        # The outreach's cost too, on the country, where the value can read gdp.
        block = _top_level_block(self.effects, "ch_effect_world_exposition = {")
        self.assertIn("\t\tadd_modifier = { name = ch_world_exposition_cost multiplier = ch_program_funding_cost_mult }",
                      block)

    def test_ending_a_programme_says_so(self):
        for prog, (modifier, variable, op) in PROGRAMMES.items():
            with self.subTest(programme=prog):
                block = _top_level_block(self.effects, f"ch_effect_disable_{prog} = {{")
                self.assertRegex(block, rf"custom_tooltip = \{{\s*text = ch_policy_{op}_end_tt\s*"
                                        rf"hidden_effect = \{{ remove_variable = {variable} \}}")
                self.assertIn(f"${modifier}$", self.loc[f"ch_policy_{op}_end_tt"])

    def test_the_steppers_keep_their_cost_tooltip(self):
        # The old re-add sat in hidden_effect, so a stepper's preview was always
        # its custom_tooltip naming what a step adds and costs; it stays.
        for direction in ("increase", "decrease"):
            block = _top_level_block(self.effects, f"ch_effect_{direction}_program_funding = {{")
            self.assertIn("custom_tooltip = ch_policy_funding_step_tt", block)
        self.assertIn("ch_program_funding_total_cost_display", self.loc["ch_policy_funding_step_tt"])


class ReaderTests(unittest.TestCase):
    """has_modifier cannot see a declared modifier, so the benchmark's readers ask ch_trails_hegemon."""

    READERS = {
        EVENTS: 8,   # cultural_hegemony .2 .4 .6 .7 .14 .15 .16 .18
        BUTTONS: 3,
        SGUIS: 1,
        EFFECTS: 1,  # ch_refresh_baseline_model_pressure
        ROOT / "events/social_tensions_events.txt": 1,
        ROOT / "events/un_events.txt": 2,
        ROOT / "common/script_values/un_dossier_values.txt": 1,
    }

    def test_each_reader_asks_the_trigger(self):
        for path, count in self.READERS.items():
            with self.subTest(file=path.name):
                self.assertEqual(_text(path).count("ch_trails_hegemon = yes"), count)

    def test_the_debug_harness_sets_the_variable(self):
        block = _top_level_block(_text(DEBUG_EFFECTS), "te_debug_ch_stage_follower_events = {")
        self.assertIn("set_variable = { name = ch_benchmark_applied value = 1 }", block)


class RefreshGoneTests(unittest.TestCase):
    MODIFIER_OP = re.compile(r"\b(add_modifier|remove_modifier|has_modifier)\b[^\n]*\b(%s)\b" % "|".join(KEYS))

    def test_no_add_remove_or_test_outside_a_preview(self):
        for path in (JE, TRIGGERS, BUTTONS, SGUIS, DEBUG_EFFECTS, EVENTS):
            with self.subTest(path=path.name):
                self.assertEqual(self.MODIFIER_OP.findall(_text(path)), [])
        # The effects file only previews (show_as_tooltip) the programmes it starts.
        effects = _text(EFFECTS)
        for prog in PROGRAMMES:
            block = _top_level_block(effects, f"ch_effect_{prog} = {{")
            effects = effects.replace(block[block.index("show_as_tooltip = {"):block.index("hidden_effect = {")], "")
        self.assertEqual(self.MODIFIER_OP.findall(effects), [])

    def test_the_refresh_and_its_wrappers_are_gone(self):
        for sub in ("common", "events"):
            for path in sorted((ROOT / sub).rglob("*.txt")):
                text = _text(path)
                with self.subTest(file=path.relative_to(ROOT).as_posix()):
                    self.assertNotIn("ch_refresh_funding_modifiers", text)
                    self.assertNotIn("ch_effect_mult_cached", text)
                    for wrapper in WRAPPERS:
                        # Kept, uncalled, until the old-save strip's removal date: an old
                        # save's entry copies still name them in their multipliers.
                        allowed = 1 if path == VALUES else 0
                        self.assertEqual(text.count(wrapper), allowed, wrapper)

    def test_the_pulse_only_ends_programmes_writes_the_benchmark_and_fires_milestones(self):
        pulse = _pulse()
        self.assertNotIn("je:je_cultural_hegemony", pulse)
        self.assertNotIn("_modifier", pulse)
        self.assertIn("trigger_event = { id = cultural_hegemony.8 }", pulse)
        self.assertIn("trigger_event = { id = cultural_hegemony.9 }", pulse)


class LateCostTests(unittest.TestCase):
    """A programme's influence use reaches the country a few days after it starts (the entry declares it), so
    the influence gates count what was started in the last week (review of PR 3, #1404)."""

    def test_both_influence_programmes_book_their_cost(self):
        effects = _text(EFFECTS)
        for prog, cost in (("cultural_institutes", "ch_cultural_institutes_influence_cost"),
                           ("global_media_campaign", "ch_global_media_influence_cost")):
            with self.subTest(programme=prog):
                block = _top_level_block(effects, f"ch_effect_{prog} = {{")
                self.assertIn(f"value = {{ value = var:ch_influence_pending add = {cost} }}", block)
                self.assertIn(f"set_variable = {{ name = ch_influence_pending value = {cost} days = 7 }}", block)


class OldSaveMigrationTests(unittest.TestCase):
    """The strip sets a programme's variable from an older save's copy only under the Ministry of Culture, and
    not when the programme it excludes was started since the load (the copy is invisible to the exclusion)."""

    def test_the_migration_keeps_the_law_and_the_exclusion(self):
        text = _text(ROOT / LEGACY)
        for modifier, var in (("ch_world_exposition", "ch_world_exposition_on"),
                              ("ch_cultural_institutes_program", "ch_cultural_institutes_on"),
                              ("ch_global_media_campaign", "ch_global_media_campaign_on"),
                              ("ch_cultural_protectionism_program", "ch_cultural_protectionism_on")):
            with self.subTest(programme=modifier):
                head = f"limit = {{ je:je_cultural_hegemony ?= {{ has_modifier = {modifier} }} }}"
                block = text[text.index(head):]
                block = block[:block.index(f"je:je_cultural_hegemony = {{ remove_modifier = {modifier} }}")]
                self.assertIn("has_law = law_type:law_ministry_of_culture", block)
                self.assertIn(f"set_variable = {{ name = {var} value = yes }}", block)
                partner = {"ch_global_media_campaign_on": "ch_cultural_protectionism_on",
                           "ch_cultural_protectionism_on": "ch_global_media_campaign_on"}.get(var)
                if partner:
                    self.assertIn(f"NOT = {{ has_variable = {partner} }}", block)


if __name__ == "__main__":
    unittest.main()
