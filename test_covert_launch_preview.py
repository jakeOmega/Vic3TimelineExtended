"""The covert actions' launch preview: what the diplomatic action's tooltip
and confirmation box say an operation will do, pinned against what the
monthly pulse (covert_ops_apply_all_phase_effects) actually applies.

Each action's accept_effect renders the operation's static modifiers with
show_as_tooltip, at base strength (established, priority 1): unscaled, no
duration. What the engine cannot list there (script_only fields, modifiers
on political movements or states, conditional parts) is stated by the
action's <type>_extra_tt line instead; STATED below is that table, and its
numbers are checked against extra_modifiers.txt.

Nothing inside show_as_tooltip runs. An add_modifier outside one would put a
permanent, unscaled modifier on the launch click, so every add_modifier in
the actions file must sit inside one.

Run: python3 -m unittest test_covert_launch_preview -v
"""

import json
import re
import unittest

from test_covert_op_registry import (
    ACTIONS,
    EFFECTS,
    ROOT,
    TYPES,
    _loc,
    _text,
    _top_level_block,
)

MODIFIERS = ROOT / "common/static_modifiers/extra_modifiers.txt"
MOD_TYPE_DIR = ROOT / "common/modifier_type_definitions"
VANILLA_TYPES = ROOT / "vanilla_parsed/common/modifier_types.json"

HEADER_TT = "covert_op_preview_header_tt"
PHASE_TT = "covert_op_phase_warning_tt"
SELF_NOTE_TT = "covert_op_self_effect_note_tt"

# (loc key, modifier, field, format): a field the pulse applies that the
# preview's engine lines cannot show, and the line that states it at base
# strength. "pct" renders 0.15 as 15%, "num" renders 0.35 as 0.35.
STATED = (
    ("covert_financial_subversion_extra_tt", "covert_financial_subversion",
     "country_bubble_pressure_monthly_add", "num"),
    ("covert_infrastructure_sabotage_extra_tt", "covert_infrastructure_sabotage",
     "state_infrastructure_mult", "pct"),
    ("covert_infrastructure_sabotage_extra_tt", "covert_infrastructure_sabotage",
     "building_throughput_add", "pct"),
    ("covert_military_espionage_extra_tt", "covert_military_espionage",
     "country_military_tech_spread_mult", "pct"),
    ("covert_ideological_subversion_extra_tt", "covert_ideological_subversion",
     "political_movement_radicalism_add", "pct"),
    ("covert_ideological_subversion_extra_tt", "covert_ideological_subversion",
     "political_movement_pop_attraction_mult", "pct"),
    ("covert_destabilization_extra_tt", "covert_destabilization_resist",
     "country_colonial_stability_drift_add", "num"),
    ("covert_regime_change_extra_tt", "covert_regime_change",
     "country_coup_resistance_add", "num"),
    ("covert_nuclear_sabotage_extra_tt", "covert_nuclear_sabotage",
     "country_nuclear_program_progress_mult", "pct"),
)

BLOCK_OPENER = re.compile(r"([\w:.@$]+)\s*=\s*\{|\}")


def _strip_comments(text):
    out = []
    for line in text.splitlines():
        quoted = False
        for i, c in enumerate(line):
            if c == '"':
                quoted = not quoted
            elif c == "#" and not quoted:
                line = line[:i]
                break
        out.append(line)
    return "\n".join(out)


def _add_modifiers(text):
    """(enclosing block headers, inner text) for every add_modifier block."""
    text = _strip_comments(text)
    stack, found = [], []
    for m in BLOCK_OPENER.finditer(text):
        if m.group(0) == "}":
            stack.pop()
            continue
        if m.group(1) == "add_modifier":
            depth, i = 1, m.end()
            while depth:
                depth += {"{": 1, "}": -1}.get(text[i], 0)
                i += 1
            found.append((tuple(stack), text[m.end(): i - 1].strip()))
        stack.append(m.group(1))
    return found


def _accept_effect(t):
    block = _top_level_block(_text(ACTIONS), "covert_%s_action = {" % t)
    start = block.index("\n\taccept_effect = {\n")
    return block[start: block.index("\n\t}\n", start) + 3]


def _preview(t):
    """(self modifiers, target modifiers) the action's preview renders."""
    own, target = set(), set()
    for stack, inner in _add_modifiers(_accept_effect(t)):
        name = re.fullmatch(r"name = (\w+)", inner)
        if not name:
            continue
        if stack[-2:] == ("accept_effect", "show_as_tooltip"):
            own.add(name.group(1))
        elif stack[-3:] == ("accept_effect", "show_as_tooltip", "scope:target_country"):
            target.add(name.group(1))
    return own, target


def _pulse():
    """type -> {"self": set, "target": set, "all": set} of the modifiers the
    pulse applies for it. Helper calls name their type; a direct apply site
    belongs to the nearest has_tag = iw_op_<type> above it."""
    block = _strip_comments(_top_level_block(_text(EFFECTS), "covert_ops_apply_all_phase_effects = {"))
    out = {t: {"self": set(), "target": set(), "all": set()} for t in TYPES}
    for side, t, mod in re.findall(
        r"covert_op_apply_(self|target)_effect = \{ TYPE = (\w+) MODIFIER = (\w+) \}", block
    ):
        out[t][side].add(mod)
        out[t]["all"].add(mod)
    for m in re.finditer(r"(?:covert_op_add_scaled_modifier|ch_apply_hegemon_movement_pressure) = \{ MODIFIER = (\w+)", block):
        owner = re.findall(r"has_tag = iw_op_(\w+)", block[: m.start()])
        out[owner[-1]]["all"].add(m.group(1))
    return out


def _fields(modifier):
    block = _top_level_block(_text(MODIFIERS), "%s = {" % modifier)
    return {k: float(v) for k, v in re.findall(r"(?m)^\t(\w+) = (-?[\d.]+)\s*$", block)}


def _script_only_types():
    names = set()
    for path in sorted(MOD_TYPE_DIR.glob("*.txt")):
        body = _strip_comments(path.read_text(encoding="utf-8-sig"))
        for m in re.finditer(r"(?m)^(\w+)\s*=\s*\{(.*?)^\}", body, re.S):
            if re.search(r"script_only\s*=\s*yes", m.group(2)):
                names.add(m.group(1))
    vanilla = json.loads(VANILLA_TYPES.read_text(encoding="utf-8"))
    for name, (_, spec) in vanilla.items():
        if isinstance(spec, dict) and spec.get("script_only") == ["=", "yes"]:
            names.add(name)
    return names


def _fmt(value, kind):
    v = abs(value) * (100 if kind == "pct" else 1)
    return ("%g" % v) + ("%" if kind == "pct" else "")


class LaunchPreviewTests(unittest.TestCase):
    def test_no_modifier_is_applied_at_launch(self):
        for stack, inner in _add_modifiers(_text(ACTIONS)):
            with self.subTest(block=stack, add_modifier=inner):
                self.assertIn("show_as_tooltip", stack)

    def test_preview_is_base_strength(self):
        # No multiplier (base strength) and no duration: the pulse refreshes a
        # three-month modifier every month, so "for 3 months" would be false.
        for t in TYPES:
            for stack, inner in _add_modifiers(_accept_effect(t)):
                with self.subTest(type=t, add_modifier=inner):
                    self.assertRegex(inner, r"^name = \w+$")

    def test_each_type_previews_what_its_helpers_apply(self):
        pulse = _pulse()
        for t in TYPES:
            own, target = _preview(t)
            with self.subTest(type=t):
                self.assertLessEqual(pulse[t]["self"], own)
                self.assertLessEqual(pulse[t]["target"], target)
                self.assertLessEqual(own | target, pulse[t]["all"])

    def test_every_applied_field_is_shown_or_stated(self):
        pulse, script_only = _pulse(), _script_only_types()
        stated = {(mod, field): key for key, mod, field, _ in STATED}
        for t in TYPES:
            own, target = _preview(t)
            accept = _accept_effect(t)
            for mod in sorted(pulse[t]["all"]):
                for field in _fields(mod):
                    with self.subTest(type=t, modifier=mod, field=field):
                        if mod in own | target and field not in script_only:
                            self.assertNotIn((mod, field), stated, "rendered by the engine and stated too")
                            continue
                        self.assertIn((mod, field), stated, "neither rendered nor stated")
                        self.assertIn("text = %s\n" % stated[(mod, field)], accept)

    def test_stated_numbers_match_the_modifiers(self):
        loc = _loc()
        for key, mod, field, kind in STATED:
            number = _fmt(_fields(mod)[field], kind)
            with self.subTest(key=key, field=field, number=number):
                self.assertRegex(loc[key], r"(?<![\d.])%s(?![\d])" % re.escape(number))

    def test_preview_frames_and_self_note(self):
        pulse = _pulse()
        for t in TYPES:
            accept = _accept_effect(t)
            with self.subTest(type=t):
                has_effects = bool(pulse[t]["all"])
                self.assertEqual("text = %s\n" % HEADER_TT in accept, has_effects)
                self.assertEqual("text = %s\n" % PHASE_TT in accept, has_effects)
                # A self effect comes from the type's strongest operation only
                # (covert_op_apply_self_effect): a second one adds nothing to us.
                self.assertEqual("text = %s\n" % SELF_NOTE_TT in accept, bool(pulse[t]["self"]))
                if has_effects:
                    self.assertLess(accept.index(HEADER_TT), accept.index("show_as_tooltip"))
                    self.assertLess(accept.index("show_as_tooltip"), accept.index(PHASE_TT))

    def test_preview_keys_exist(self):
        loc = _loc()
        for key in {HEADER_TT, PHASE_TT, SELF_NOTE_TT} | {row[0] for row in STATED}:
            with self.subTest(key=key):
                self.assertIn(key, loc)


if __name__ == "__main__":
    unittest.main()
