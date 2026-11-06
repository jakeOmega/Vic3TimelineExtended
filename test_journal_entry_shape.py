"""The shape of the mod's journal entries under vanilla 1.15.

- No entry keeps a field 1.15 dropped, and every entry declares `activation_description` (the tree checks of the
  one-shot outcome converter, retired with #1404).
- `disable_evaluation` (#1404, design § 1): every entry whose gate requires a game rule prunes on that rule, and a
  prune reads nothing but game rules, so it can't delete an entry a country could still come to qualify for.
- `scaling_modifiers_while_active` (design § 3): a declared modifier exists, and nothing adds, removes or tests it
  with `has_modifier`, which can't see one.
"""
from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from je_multiplier_scope_audit import Node, parse_text

ROOT = Path(__file__).resolve().parent
JE_DIR = ROOT / "common" / "journal_entries"

# Fields 1.15 replaced with `outcome = { }` blocks, and the old fields with no 1.15 equivalent.
DROPPED_FIELDS = frozenset({
    "complete", "fail", "invalid", "on_complete", "on_fail", "on_invalid", "on_timeout",
    "custom_completion_header", "custom_on_completion_header",
    "custom_failure_header", "custom_on_failure_header",
    "event_outcome_completed_desc", "event_outcome_failed_desc", "event_outcome_timeout_desc",
    "event_outcome_completed_effect_desc", "event_outcome_failed_effect_desc",
    "event_outcome_timeout_effect_desc",
    "on_complete_all_involved", "on_fail_all_involved", "on_invalid_all_involved", "on_timeout_all_involved",
    "event_outcome_invalidated_desc", "event_outcome_invalidated_effect_desc",
})


def _parse(path: Path) -> list[Node]:
    return parse_text(path.read_text(encoding="utf-8-sig"), path.relative_to(ROOT).as_posix())[0]


def load_entries() -> list[tuple[str, Node]]:
    """(repo-relative path, entry node) for every top-level entry in common/journal_entries/."""
    return [(path.relative_to(ROOT).as_posix(), node)
            for path in sorted(JE_DIR.glob("*.txt"))
            for node in _parse(path) if node.children]


def child(node: Node, key: str) -> Node | None:
    return next((c for c in node.children if c.key == key), None)


def dropped_fields(entry: Node) -> list[str]:
    return sorted({c.key for c in entry.children} & DROPPED_FIELDS)


class DroppedFieldsTest(unittest.TestCase):
    def test_dropped_fields_fixture(self):
        nodes, _ = parse_text("je_x = {\n\ton_complete = { }\n\ttimeout = 5\n\toutcome = { }\n}\n", "j.txt")
        self.assertEqual(dropped_fields(nodes[0]), ["on_complete"])

    def test_no_entry_keeps_a_field_vanilla_dropped(self):
        entries = load_entries()
        self.assertGreater(len(entries), 30)
        for rel, entry in entries:
            with self.subTest(file=rel, entry=entry.key):
                self.assertEqual(dropped_fields(entry), [])

    def test_every_entry_declares_activation_description(self):
        """1.15 logs "missing an activation_description trigger" for an entry without one (29 mod entries on the
        first 1.15 game); vanilla's default is `activation_description = { always = yes }`."""
        for rel, entry in load_entries():
            if entry.key.startswith("INJECT:"):  # takes the field from its target; a REPLACE: needs its own
                continue
            with self.subTest(file=rel, entry=entry.key):
                self.assertIsNotNone(child(entry, "activation_description"))


# --- disable_evaluation (design § 1) ---------------------------------------------------------------------------

LOGIC = ("AND", "OR", "NOT")


def load_triggers() -> dict[str, Node]:
    """Top-level named triggers in common/scripted_triggers/."""
    triggers: dict[str, Node] = {}
    for path in sorted((ROOT / "common" / "scripted_triggers").glob("*.txt")):
        triggers.update((n.key, n) for n in _parse(path) if n.children)
    return triggers


def _calls(node: Node, triggers: dict[str, Node]) -> Node | None:
    """The named trigger `node` calls (`T = yes`, or `T = { ARG = … }`), if any."""
    if node.key not in triggers:
        return None
    return triggers[node.key] if node.value == "yes" or (node.value is None and node.children) else None


def gate_conjuncts(entry: Node, triggers: dict[str, Node]) -> list[Node]:
    """The direct children of `is_shown_when_inactive`, each followed by the top-level conjuncts of a named trigger
    it calls, recursively (`sr_milestone_followup_is_shown` carries the Space Race rule; `te_banking_entry_expected`
    carries Banking's)."""
    gate = child(entry, "is_shown_when_inactive")
    out: list[Node] = []

    def walk(nodes: list[Node], seen: tuple[str, ...]):
        for node in nodes:
            out.append(node)
            called = _calls(node, triggers)
            if called is not None and node.key not in seen:
                walk(called.children, seen + (node.key,))

    walk(gate.children if gate else [], ())
    return out


def _rule_pure(nodes: list[Node], triggers: dict[str, Node], seen: tuple[str, ...]) -> bool:
    return bool(nodes) and all(
        _is_rule(n, triggers, seen) or (n.key in LOGIC and _rule_pure(n.children, triggers, seen)) for n in nodes)


def _is_rule(node: Node, triggers: dict[str, Node], seen: tuple[str, ...]) -> bool:
    if node.key == "has_game_rule" and node.value and not node.children:
        return True
    if node.key in triggers and node.value == "yes" and node.key not in seen:
        return _rule_pure(triggers[node.key].children, triggers, seen + (node.key,))
    return False


def is_rule_test(node: Node, triggers: dict[str, Node]) -> bool:
    """`has_game_rule = x`, or `T = yes` for a named trigger made of nothing but rule tests under AND/OR/NOT:
    true or false for the whole game, so safe to prune on."""
    return _is_rule(node, triggers, ())


def prune_problems(entry: Node, triggers: dict[str, Node]) -> list[str]:
    conjuncts = gate_conjuncts(entry, triggers)
    prune = child(entry, "disable_evaluation")
    if prune is None:
        if any(is_rule_test(c, triggers) for c in conjuncts):
            return ["rule-gated entry has no disable_evaluation"]
        return []
    tests = prune.children
    if [(t.key, t.value) for t in tests] == [("always", "yes")]:
        gate = child(entry, "is_shown_when_inactive")
        shown = [(c.key, c.value) for c in gate.children] if gate else []
        return [] if shown == [("always", "no")] else [
            "disable_evaluation = { always = yes } on an entry that can show"]
    if not tests:
        return ["empty disable_evaluation"]
    gate_rules = {(c.key, c.value) for c in conjuncts if is_rule_test(c, triggers)}
    problems = []
    for test in tests:
        inner = test.children
        if test.key != "NOT" or len(inner) != 1 or not is_rule_test(inner[0], triggers):
            problems.append(f"line {test.line}: {test.key} is not NOT = {{ <one game-rule test> }}")
        elif (inner[0].key, inner[0].value) not in gate_rules:
            problems.append(f"line {test.line}: {inner[0].key} = {inner[0].value} is not a rule conjunct of the gate")
    return problems


def _entry(text: str) -> Node:
    return next(n for n in parse_text(text, "j.txt")[0] if n.children)


def _triggers(text: str) -> dict[str, Node]:
    return {n.key: n for n in parse_text(text, "t.txt")[0] if n.children}


class PruneFixtureTest(unittest.TestCase):
    def check(self, gate: str, prune: str | None, triggers: str = "") -> list[str]:
        body = f"\tis_shown_when_inactive = {{ {gate} }}\n"
        if prune is not None:
            body = f"\tdisable_evaluation = {{ {prune} }}\n" + body
        return prune_problems(_entry("je_x = {\n" + body + "}\n"), _triggers(triggers))

    def test_prune_of_a_gate_rule_is_sound(self):
        self.assertEqual(self.check("has_game_rule = r has_variable = x", "NOT = { has_game_rule = r }"), [])

    def test_rule_gated_entry_without_prune_is_flagged(self):
        problems = self.check("has_game_rule = r", None)
        self.assertEqual(len(problems), 1)
        self.assertIn("no disable_evaluation", problems[0])

    def test_ungated_entry_needs_no_prune(self):
        self.assertEqual(self.check("has_variable = x OR = { has_game_rule = r has_law = law_type:l }", None), [])

    def test_prune_rule_missing_from_gate_is_flagged(self):
        self.assertEqual(len(self.check("has_game_rule = r", "NOT = { has_game_rule = s }")), 1)

    def test_prune_on_a_variable_is_flagged(self):
        self.assertEqual(len(self.check("has_variable = x", "NOT = { has_variable = x }")), 1)
        self.assertEqual(len(self.check("w = yes", "NOT = { w = yes }", "w = { has_variable = x }")), 1)

    def test_rule_pure_wrapper_is_a_rule_test(self):
        triggers = "w = { OR = { has_game_rule = a has_game_rule = b } }"
        self.assertEqual(self.check("w = yes", "NOT = { w = yes }", triggers), [])
        self.assertEqual(len(self.check("w = yes", None, triggers)), 1)

    def test_gate_read_through_a_parameterised_trigger(self):
        triggers = "w = { has_game_rule = a }\nf = { w = yes has_variable = done_$P$ }"
        self.assertEqual(self.check("f = { P = x }", "NOT = { w = yes }", triggers), [])
        self.assertEqual(len(self.check("f = { P = x }", None, triggers)), 1)

    def test_always_yes_only_for_a_never_shown_entry(self):
        self.assertEqual(self.check("always = no", "always = yes"), [])
        self.assertEqual(len(self.check("has_variable = x", "always = yes")), 1)

    def test_not_with_two_children_is_flagged(self):
        self.assertEqual(len(self.check("has_game_rule = r has_game_rule = s",
                                        "NOT = { has_game_rule = r has_game_rule = s }")), 1)


class PruneTreeTest(unittest.TestCase):
    def test_every_entry_prune_is_sound(self):
        triggers = load_triggers()
        self.assertIn("sr_space_race_on", triggers)
        for rel, entry in load_entries():
            with self.subTest(file=rel, entry=entry.key):
                self.assertEqual(prune_problems(entry, triggers), [])


# --- scaling_modifiers_while_active (design § 3) -----------------------------------------------------------------

# legacy_je_modifier_cleanup_effect strips the copies an old save added by hand (design § 4.0, rule 7): it may test
# and remove a declared key, never add one.
LEGACY_STRIP_FILE = "common/scripted_effects/legacy_modifier_cleanup.txt"


def scaling_declarations(entries: list[tuple[str, Node]]) -> dict[str, list[tuple[str, int, str]]]:
    """modifier → [(file, line, entry)] for every scaling_modifiers_while_active block."""
    out: dict[str, list[tuple[str, int, str]]] = {}
    for rel, entry in entries:
        for block in (c for c in entry.children if c.key == "scaling_modifiers_while_active"):
            name = child(block, "modifier")
            out.setdefault(name.value if name else "?", []).append((rel, block.line, entry.key))
    return out


def static_modifier_names() -> set[str]:
    names = {n.key.split(":", 1)[-1]
             for path in sorted((ROOT / "common" / "static_modifiers").glob("*.txt")) for n in _parse(path)}
    vanilla = json.loads((ROOT / "vanilla_parsed" / "common" / "modifiers.json").read_text(encoding="utf-8"))
    return names | set(vanilla)


def misuse_sites(nodes: list[Node], declared: set[str], rel: str) -> list[tuple[str, int, str, str]]:
    """(file, line, kind, modifier) for each has_modifier, add_modifier or remove_modifier of a declared key. An
    add inside show_as_tooltip is the option's preview (design § 4.0, rule 8); the legacy strip may test and
    remove."""
    out: list[tuple[str, int, str, str]] = []
    legacy = rel == LEGACY_STRIP_FILE

    def walk(items: list[Node], preview: bool):
        for node in items:
            name = None
            if node.key in ("has_modifier", "add_modifier", "remove_modifier"):
                name = node.value if not node.children else getattr(child(node, "name"), "value", None)
            elif node.key == "remove_modifier_if_exists_effect":
                name = getattr(child(node, "MODIFIER"), "value", None)
            if name in declared:
                skip = (node.key == "add_modifier" and preview) or (legacy and node.key != "add_modifier")
                if not skip:
                    out.append((rel, node.line, node.key, name))
            walk(node.children, preview or node.key == "show_as_tooltip")

    walk(nodes, False)
    return out


class ScalingModifierFixtureTest(unittest.TestCase):
    def sites(self, text: str, rel: str = "common/scripted_effects/x.txt") -> list[tuple[str, str]]:
        return [(kind, name) for _, _, kind, name in misuse_sites(parse_text(text, rel)[0], {"m"}, rel)]

    def test_has_add_and_remove_are_flagged(self):
        self.assertEqual(self.sites("e = { has_modifier = m }"), [("has_modifier", "m")])
        self.assertEqual(self.sites("e = { add_modifier = { name = m multiplier = 2 } }"), [("add_modifier", "m")])
        self.assertEqual(self.sites("e = { add_modifier = m remove_modifier = m }"),
                         [("add_modifier", "m"), ("remove_modifier", "m")])
        self.assertEqual(self.sites("e = { remove_modifier_if_exists_effect = { MODIFIER = m } }"),
                         [("remove_modifier_if_exists_effect", "m")])

    def test_a_preview_is_allowed(self):
        self.assertEqual(self.sites("o = { show_as_tooltip = { if = { add_modifier = { name = m } } } }"), [])

    def test_the_legacy_strip_may_test_and_remove_but_not_add(self):
        text = "e = { if = { limit = { has_modifier = m } remove_modifier = m } add_modifier = { name = m } }"
        self.assertEqual(self.sites(text, LEGACY_STRIP_FILE), [("add_modifier", "m")])

    def test_an_undeclared_key_is_not_flagged(self):
        self.assertEqual(self.sites("e = { has_modifier = other add_modifier = { name = other } }"), [])

    def test_declarations_are_listed(self):
        nodes, _ = parse_text("je_x = {\n\tscaling_modifiers_while_active = { modifier = a value = 1 }\n"
                              "\tscaling_modifiers_while_active = { modifier = b value = 2 }\n}\n", "j.txt")
        self.assertEqual(scaling_declarations([("j.txt", nodes[0])]),
                         {"a": [("j.txt", 2, "je_x")], "b": [("j.txt", 3, "je_x")]})


class ScalingModifierTreeTest(unittest.TestCase):
    def test_every_scaling_modifier_exists(self):
        names = static_modifier_names()
        self.assertTrue({"base_values", "nuclear_weapon_program_funding"} <= names)
        for name, sites in scaling_declarations(load_entries()).items():
            with self.subTest(modifier=name, at=sites[0]):
                self.assertIn(name, names)

    def test_no_scaling_modifier_is_added_or_tested(self):
        """has_modifier can't see a scaling modifier, on the entry or the country (probed 2026-11-05), and an
        add or remove beside the declaration doubles it or does nothing."""
        declared = set(scaling_declarations(load_entries()))
        found = []
        if declared:
            for sub in ("common", "events"):
                for path in sorted((ROOT / sub).rglob("*.txt")):
                    rel = path.relative_to(ROOT).as_posix()
                    found += misuse_sites(_parse(path), declared, rel)
            gui = re.compile(r"HasModifier.*\b(" + "|".join(map(re.escape, sorted(declared))) + r")\b")
            for path in sorted((ROOT / "gui").rglob("*.gui")):
                for number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
                    match = gui.search(line)
                    if match:
                        found.append((path.relative_to(ROOT).as_posix(), number, "HasModifier", match.group(1)))
        self.assertEqual(found, [])


if __name__ == "__main__":
    unittest.main()
