"""The shape of the mod's journal entries under vanilla 1.15.

- No entry keeps a field 1.15 dropped, and every entry declares `activation_description` (the tree checks of the
  one-shot outcome converter, retired with #1404).
- `disable_evaluation` (#1404, design § 1): every entry whose gate requires a game rule prunes on that rule, and a
  prune reads nothing but game rules, so it can't delete an entry a country could still come to qualify for.
- Ends on its rule: a prune touches only inactive records, and a rule can be switched off mid-game, so every
  rule-pruned entry also ends through its invalid outcome when the rule is off, unless it carries
  `# REVIEWED YYYY-MM-DD (rule_outlives): rationale` on its `disable_evaluation = {` line (Culture Merges pause).
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


def gate_conjuncts(entry: Node, triggers: dict[str, Node], field: str = "is_shown_when_inactive") -> list[Node]:
    """The direct children of `is_shown_when_inactive` (or `field`), each followed by the top-level conjuncts of a
    named trigger it calls, recursively (`sr_milestone_followup_is_shown` carries the Space Race rule;
    `te_banking_entry_expected` carries Banking's)."""
    gate = child(entry, field)
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


def is_contextless(entry: Node) -> bool:
    """`context = none`: one entry for the world, so no country holds an inactive record for a prune to remove."""
    context = child(entry, "context")
    return context is not None and context.value == "none"


def prune_problems(entry: Node, triggers: dict[str, Node]) -> list[str]:
    conjuncts = gate_conjuncts(entry, triggers)
    prune = child(entry, "disable_evaluation")
    if is_contextless(entry):
        # 1.15 at load: "JE je_world_climate has a disable_evaluation trigger but is a contextless journal entry,
        # this does nothing" (2026-11-06).
        return [] if prune is None else ["disable_evaluation on a contextless entry does nothing"]
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

    def test_contextless_entry_takes_no_prune(self):
        entry = "je_x = {\n\tcontext = none\n\tis_shown_when_inactive = { has_game_rule = r }\n%s}\n"
        self.assertEqual(prune_problems(_entry(entry % ""), {}), [])
        problems = prune_problems(_entry(entry % "\tdisable_evaluation = { NOT = { has_game_rule = r } }\n"), {})
        self.assertEqual(len(problems), 1)
        self.assertIn("contextless", problems[0])

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


# --- ends on its rule ------------------------------------------------------------------------------------------
#
# A rule can be changed mid-game, from the screen that changes country, and `disable_evaluation` touches only
# inactive records: an active entry runs on, with its modifiers, pulses and events, unless an outcome ends it. A
# Workshop player saw Banking do exactly that (2026-11-08). So a rule-pruned entry also ends when its rule is off,
# through its one invalid outcome (an entry has at most one): the outcome's trigger holds whenever the prune's does,
# alone or folded into an OR. Or it deactivates: `can_deactivate = yes` with the prune's rule a conjunct of
# `possible` takes it off the journal when the rule goes (scripting_best_practices.md, "an entry leaves the journal
# by concluding, or by can_deactivate"), and the prune then removes the record (the Nuclear Program; no effect runs,
# so its teardown is a pulse's). An entry meant to outlive its rule says why with
# `# REVIEWED YYYY-MM-DD (rule_outlives): rationale` on its `disable_evaluation = {` line; the 32 culture merges
# pause where they stand and resume when the rule is switched back on (R19), and so does an interstellar probe's
# transit, which nothing would add back. A tag on an entry that does end on its rule, or that no rule prunes, is stale.

OUTLIVES_TAG = "rule_outlives"
_OUTLIVES_RE = re.compile(r"REVIEWED\s+\d{4}-\d{2}-\d{2}\s*\(" + OUTLIVES_TAG + r"\)\s*:\s*\S")
_FLAGS_RE = re.compile(r"flags\s*=\s*\{([^{}]*)\}")


def prune_rules(entry: Node, triggers: dict[str, Node]) -> set[tuple[str, str | None]]:
    """The rule tests a prune's `NOT = { <rule> }` lines name: empty for an entry no rule prunes."""
    prune = child(entry, "disable_evaluation")
    if prune is None or is_contextless(entry):
        return set()
    return {(t.children[0].key, t.children[0].value) for t in prune.children
            if t.key == "NOT" and len(t.children) == 1 and is_rule_test(t.children[0], triggers)}


def outcome_flags(outcome: Node, lines: list[str]) -> set[str]:
    """An outcome's `flags = { … }` words. The parser skips bare list items, so they are read from the source."""
    flags = child(outcome, "flags")
    if flags is None:
        return set()
    text = "\n".join(line.split("#", 1)[0] for line in lines[flags.line - 1:flags.line + 4])
    match = _FLAGS_RE.search(text)
    return set(match.group(1).split()) if match else set()


def _true_with_rule_off(node: Node, rules: set[tuple[str, str | None]]) -> bool:
    # `T = no` is `NOT = { T = yes }` for a rule-pure trigger (gm_system_enabled = no).
    if node.value == "no" and not node.children and (node.key, "yes") in rules:
        return True
    if node.key == "NOT" and len(node.children) == 1:
        return (node.children[0].key, node.children[0].value) in rules
    if node.key == "OR":
        return any(_true_with_rule_off(c, rules) for c in node.children)
    if node.key == "AND":
        return bool(node.children) and all(_true_with_rule_off(c, rules) for c in node.children)
    return False


def deactivates_on_rule(entry: Node, triggers: dict[str, Node], rules: set[tuple[str, str | None]]) -> bool:
    """`can_deactivate = yes`, and `possible` requires one of the prune's rules."""
    flag = child(entry, "can_deactivate")
    return flag is not None and flag.value == "yes" and any(
        (c.key, c.value) in rules and is_rule_test(c, triggers) for c in gate_conjuncts(entry, triggers, "possible"))


def rule_end_problems(entry: Node, triggers: dict[str, Node], lines: list[str], comments: dict[int, str]) -> list[str]:
    rules = prune_rules(entry, triggers)
    prune = child(entry, "disable_evaluation")
    tagged = prune is not None and bool(_OUTLIVES_RE.search(comments.get(prune.line, "")))
    if not rules:
        return [f"line {prune.line}: ({OUTLIVES_TAG}) tag on an entry no rule prunes"] if tagged else []
    invalid = [o for o in entry.children if o.key == "outcome" and "invalid_outcome" in outcome_flags(o, lines)]
    if len(invalid) > 1:
        return [f"line {o.line}: a second invalid outcome (an entry has at most one)" for o in invalid[1:]]
    trigger = child(invalid[0], "trigger") if invalid else None
    ends = deactivates_on_rule(entry, triggers, rules) or (trigger is not None and bool(trigger.children) and all(
        _true_with_rule_off(c, rules) for c in trigger.children))
    if tagged:
        return [f"line {prune.line}: stale ({OUTLIVES_TAG}) tag, the entry ends on its rule"] if ends else []
    if ends:
        return []
    if not invalid:
        return ["rule-pruned entry has no invalid outcome, so an active one runs on when its rule is switched off"]
    return [f"line {invalid[0].line}: the invalid outcome doesn't hold with the rule off; "
            "fold NOT = { <the prune's rule> } into its trigger with OR"]


def load_entry_sources() -> list[tuple[str, Node, list[str], dict[int, str]]]:
    """(repo-relative path, entry node, source lines, comments by line) for every entry in common/journal_entries/."""
    out = []
    for path in sorted(JE_DIR.glob("*.txt")):
        rel = path.relative_to(ROOT).as_posix()
        text = path.read_text(encoding="utf-8-sig")
        nodes, comments = parse_text(text, rel)
        out.extend((rel, n, text.split("\n"), comments) for n in nodes if n.children)
    return out


class RuleEndFixtureTest(unittest.TestCase):
    PRUNE = "\tdisable_evaluation = {%s\n\t\tNOT = { has_game_rule = r }\n\t}\n"
    GATE = "\tis_shown_when_inactive = { has_game_rule = r has_variable = x }\n"

    def check(self, outcomes: str, tag: str = "", prune: bool = True) -> list[str]:
        text = "je_x = {\n" + (self.PRUNE % tag if prune else "") + self.GATE + outcomes + "}\n"
        nodes, comments = parse_text(text, "j.txt")
        return rule_end_problems(nodes[0], {}, text.split("\n"), comments)

    @staticmethod
    def invalid(trigger: str) -> str:
        return f"\toutcome = {{\n\t\tflags = {{ hidden invalid_outcome }}\n\t\ttrigger = {{ {trigger} }}\n\t}}\n"

    def test_the_rule_alone_ends_it(self):
        self.assertEqual(self.check(self.invalid("NOT = { has_game_rule = r }")), [])

    def test_the_rule_folded_into_an_or_ends_it(self):
        self.assertEqual(self.check(self.invalid("OR = { is_country_type = decentralized "
                                                 "NOT = { has_game_rule = r } }")), [])

    def test_a_rule_trigger_at_no_ends_it(self):
        entry = ("je_x = {\n\tdisable_evaluation = { NOT = { w = yes } }\n\tis_shown_when_inactive = { w = yes }\n"
                 + self.invalid("OR = { w = no has_variable = idle }") + "}\n")
        nodes, comments = parse_text(entry, "j.txt")
        triggers = _triggers("w = { has_game_rule = r }")
        self.assertEqual(rule_end_problems(nodes[0], triggers, entry.split("\n"), comments), [])

    def test_deactivating_on_the_rule_ends_it(self):
        def run(deactivate: str, possible: str) -> list[str]:
            text = ("je_x = {\n" + self.PRUNE % "" + self.GATE + f"\tpossible = {{ {possible} }}\n"
                    f"\tcan_deactivate = {deactivate}\n}}\n")
            nodes, comments = parse_text(text, "j.txt")
            return rule_end_problems(nodes[0], _triggers("w = { has_game_rule = r has_variable = y }"),
                                     text.split("\n"), comments)
        self.assertEqual(run("yes", "has_game_rule = r has_variable = x"), [])
        self.assertEqual(run("yes", "w = yes"), [])  # through a named trigger
        self.assertEqual(len(run("no", "has_game_rule = r")), 1)
        self.assertEqual(len(run("yes", "has_variable = x")), 1)

    def test_no_invalid_outcome_is_flagged(self):
        problems = self.check("\toutcome = {\n\t\ttrigger = { NOT = { has_game_rule = r } }\n\t}\n")
        self.assertEqual(len(problems), 1)
        self.assertIn("no invalid outcome", problems[0])

    def test_an_invalid_outcome_on_something_else_is_flagged(self):
        self.assertEqual(len(self.check(self.invalid("is_country_type = decentralized"))), 1)

    def test_the_rule_and_another_condition_is_flagged(self):
        """Both must hold, so the entry runs on while the other doesn't."""
        self.assertEqual(len(self.check(self.invalid("NOT = { has_game_rule = r } has_variable = y"))), 1)
        self.assertEqual(len(self.check(self.invalid("NOT = { has_game_rule = s }"))), 1)

    def test_a_second_invalid_outcome_is_flagged(self):
        twice = self.invalid("NOT = { has_game_rule = r }") * 2
        self.assertEqual(len(self.check(twice)), 1)

    def test_flags_are_read_from_the_source(self):
        outcome = ("\toutcome = {\n\t\tflags = {\n\t\t\thidden # the panel shows nothing\n\t\t\tinvalid_outcome\n"
                   "\t\t}\n\t\ttrigger = { NOT = { has_game_rule = r } }\n\t}\n")
        self.assertEqual(self.check(outcome), [])

    def test_the_tag_exempts_and_goes_stale(self):
        tag = " # REVIEWED 2026-11-08 (rule_outlives): pauses and resumes"
        self.assertEqual(self.check("", tag), [])
        stale = self.check(self.invalid("NOT = { has_game_rule = r }"), tag)
        self.assertEqual(len(stale), 1)
        self.assertIn("stale", stale[0])
        # Another check's tag is not this one's.
        self.assertEqual(len(self.check("", " # REVIEWED 2026-11-08: something else")), 1)

    def test_an_entry_no_rule_prunes_needs_nothing(self):
        self.assertEqual(self.check("", prune=False), [])


class RuleEndTreeTest(unittest.TestCase):
    def test_every_rule_pruned_entry_ends_on_its_rule(self):
        triggers = load_triggers()
        checked = exempt = 0
        for rel, entry, lines, comments in load_entry_sources():
            if not prune_rules(entry, triggers):
                continue
            checked += 1
            prune = child(entry, "disable_evaluation")
            exempt += bool(_OUTLIVES_RE.search(comments.get(prune.line, "")))
            with self.subTest(file=rel, entry=entry.key):
                self.assertEqual(rule_end_problems(entry, triggers, lines, comments), [])
        self.assertEqual(checked, 57)
        self.assertEqual(exempt, 33, "the 32 culture merges and the interstellar probe's transit outlive their rule")


# --- scaling_modifiers_while_active (design § 3) -----------------------------------------------------------------

# The temporary scaling self-checks (#1404) test for an older save's added copy, which has_modifier sees and a
# declaration never is, so a check can wait for the strip instead of misreading the sum.
SELFCHECK_FILE = "common/scripted_effects/te_scaling_selfcheck_effects.txt"


def _walk(nodes: list[Node]):
    for node in nodes:
        yield node
        yield from _walk(node.children)


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
    """(file, line, kind, modifier) for every `key = <declared modifier>` outside its declaration: a has_modifier,
    add_modifier or remove_modifier of it, and a helper argument that passes it on (`un_state_on = { MODIFIER = x }`,
    whose body adds `$MODIFIER$`). Allowed: the declaration's own `modifier =`, an add inside show_as_tooltip (the
    option's preview, design § 4.0 rule 8), and the self-checks' tests for an old copy. Not a use: a variable or a loc key that shares the modifier's name (a Grand Monuments
    boon's countdown is the variable gm_boon_<source>, read with has_variable and named by its loc)."""
    out: list[tuple[str, int, str, str]] = []
    selfcheck = rel == SELFCHECK_FILE

    def names(value: str, modifier_op: bool) -> bool:
        """The value is a declared modifier, or, in an add, remove or has_modifier, a template whose literal part
        names a family and makes one (`gm_boon_$SRC$`, the shape of the boons' retired adder). A template with one
        literal token (`sr_$MILESTONE$`, the milestone rewards) or none (`$MODIFIER$`) would match any key."""
        if not value:
            return False
        if value in declared:
            return True
        if not modifier_op or "$" not in value:
            return False
        if len([t for t in re.sub(r"\$\w+\$", "", value).split("_") if t]) < 2:
            return False
        pattern = re.compile(re.sub(r"\\\$\w+\\\$", r"\\w+", re.escape(value)))
        return any(pattern.fullmatch(name) for name in declared)

    def walk(items: list[Node], parent: str, declaration: bool, preview: bool):
        for node in items:
            if node.children:
                walk(node.children, node.key, declaration or node.key == "scaling_modifiers_while_active",
                     preview or node.key == "show_as_tooltip")
                continue
            modifier_op = node.key in ("add_modifier", "remove_modifier", "has_modifier") or (
                node.key == "name" and parent in ("add_modifier", "remove_modifier"))
            if declaration or not names(node.value, modifier_op):
                continue
            if node.key in ("has_variable", "remove_variable", "localization_key") or (
                    node.key == "name" and parent in ("set_variable", "change_variable", "clamp_variable")):
                continue
            kind = parent if node.key == "name" and parent in ("add_modifier", "remove_modifier") else node.key
            if kind == "MODIFIER" and parent == "remove_modifier_if_exists_effect":
                kind = parent
            adds = kind not in ("has_modifier", "remove_modifier", "remove_modifier_if_exists_effect")
            if (preview and adds) or (selfcheck and kind == "has_modifier"):
                continue
            out.append((rel, node.line, kind, node.value))

    walk(nodes, "", False, False)
    return out


class ScalingModifierFixtureTest(unittest.TestCase):
    def sites(self, text: str, rel: str = "common/scripted_effects/x.txt") -> list[tuple[str, str]]:
        return [(kind, name) for _, _, kind, name in misuse_sites(parse_text(text, rel)[0], {"m"}, rel)]

    def test_a_template_that_makes_a_declared_name_is_flagged(self):
        sites = lambda text: [(kind, name) for _, _, kind, name in misuse_sites(  # noqa: E731
            parse_text(text, "common/scripted_effects/x.txt")[0], {"gm_boon_reign"}, "common/scripted_effects/x.txt")]
        self.assertEqual(sites("e = { add_modifier = { name = gm_boon_$SRC$ } }"), [("add_modifier", "gm_boon_$SRC$")])
        self.assertEqual(sites("e = { remove_modifier = $MODIFIER$ }"), [])
        self.assertEqual(sites("e = { add_modifier = { name = gm_local_$KEY$ } }"), [])
        self.assertEqual(sites("e = { add_modifier = gm_$X$ }"), [], "one literal token names no family")
        self.assertEqual(sites("e = { has_global_variable = gm_boon_$SRC$ }"), [], "not a modifier operation")

    def test_has_add_and_remove_are_flagged(self):
        self.assertEqual(self.sites("e = { has_modifier = m }"), [("has_modifier", "m")])
        self.assertEqual(self.sites("e = { add_modifier = { name = m multiplier = 2 } }"), [("add_modifier", "m")])
        self.assertEqual(self.sites("e = { add_modifier = m remove_modifier = m }"),
                         [("add_modifier", "m"), ("remove_modifier", "m")])
        self.assertEqual(self.sites("e = { remove_modifier_if_exists_effect = { MODIFIER = m } }"),
                         [("remove_modifier_if_exists_effect", "m")])

    def test_a_preview_is_allowed(self):
        self.assertEqual(self.sites("o = { show_as_tooltip = { if = { add_modifier = { name = m } } } }"), [])

    def test_the_self_checks_may_test_but_not_remove_or_add(self):
        text = "e = { if = { limit = { NOT = { has_modifier = m } } } remove_modifier = m add_modifier = m }"
        self.assertEqual(self.sites(text, SELFCHECK_FILE), [("remove_modifier", "m"), ("add_modifier", "m")])

    def test_a_variable_or_loc_key_of_the_same_name_is_not_flagged(self):
        text = ("e = { if = { limit = { has_variable = m } } set_variable = { name = m value = 1 } "
                "change_variable = { name = m add = -1 } remove_variable = m } t = { localization_key = m }")
        self.assertEqual(self.sites(text), [])
        self.assertEqual(self.sites("e = { set_variable = { name = x value = 1 } add_modifier = { name = m } }"),
                         [("add_modifier", "m")])

    def test_a_helper_argument_is_flagged(self):
        self.assertEqual(self.sites("e = { un_state_on = { MODIFIER = m } }"), [("MODIFIER", "m")])

    def test_the_declaration_itself_is_not_flagged(self):
        self.assertEqual(self.sites("je_x = { scaling_modifiers_while_active = { modifier = m value = 1 } }"), [])

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
