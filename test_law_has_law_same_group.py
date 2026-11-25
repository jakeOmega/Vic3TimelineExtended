"""A trigger block never asks for two laws of one group at once.

A country holds one law of a lawgroup, so ``{ has_law = A  has_law = B }`` with A and B in the same
group is an AND no country can pass. Ancestral Citizenship's ``on_enact`` (#2045) listed Cultural
Assimilation, Protection and Affirmative Action side by side in a ``limit``, so the clean-up it was
written for never ran and a country could hold Ancestral Citizenship with a Minority Rights law
that does not fit it. Multicultural's ``on_enact`` wrapped its three in ``OR``; this one did not.

``OR``, ``NOR`` and ``NAND`` blocks may list several laws of a group, and so may ``NOT`` (several
children read as a NOR). Every other block, ``limit`` and ``AND`` among them, may not.

The scan covers ``common/laws/``. ``country_is_fascist`` (``common/scripted_triggers/world_war_triggers.txt``)
has the same shape, Autocracy with Single-Party State, and is tracked apart: it is a design decision.

Run: python3 -m pytest test_law_has_law_same_group.py
"""

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LAWS_DIR = ROOT / "common/laws"
VANILLA_LAWS = ROOT / "vanilla_parsed/common/laws.json"
CITIZENSHIP = LAWS_DIR / "modified.txt"

# Blocks in which several laws of one group are fine: at least one child is enough, or none may hold.
ANY_OF_BLOCKS = frozenset({"OR", "NOR", "NAND", "NOT"})

TOKEN = re.compile(r'"[^"\n]*"|[{}]|[^\s{}=]+|=')


def code(path):
    return re.sub(r"#[^\n]*", "", Path(path).read_text(encoding="utf-8-sig"))


def block_laws(text):
    """Every ``{ }`` block as (name, [law keys of its direct ``has_law = law_type:X`` children])."""
    tokens = TOKEN.findall(text)
    stack, found = [], []
    for i, token in enumerate(tokens):
        if token == "{":
            name = ""
            if i >= 2 and tokens[i - 1] == "=":
                name = tokens[i - 2]
            stack.append((name, []))
        elif token == "}":
            if stack:
                found.append(stack.pop())
        elif token == "has_law" and i + 2 < len(tokens) and tokens[i + 1] == "=" and stack:
            m = re.fullmatch(r"law_type:(\w+)", tokens[i + 2])
            if m:
                stack[-1][1].append(m.group(1))
    return found


def law_groups():
    """Law key -> lawgroup, vanilla from the committed snapshot and the mod's files over it."""
    groups = {}
    for key, value in json.loads(VANILLA_LAWS.read_text(encoding="utf-8")).items():
        group = value[1].get("group") if isinstance(value, list) and isinstance(value[1], dict) else None
        if group:
            groups[key] = group[1]
    header = re.compile(r"^(?:REPLACE:|INJECT:)?(law_\w+)\s*=\s*\{[^{}]*?\bgroup\s*=\s*(lawgroup_\w+)", re.M)
    for path in sorted(LAWS_DIR.glob("*.txt")):
        for m in header.finditer(code(path)):
            groups[m.group(1)] = m.group(2)
    return groups


def impossible_ands(text, groups):
    """(block name, group, laws) for each block that ANDs two laws of one group."""
    bad = []
    for name, laws in block_laws(text):
        if name in ANY_OF_BLOCKS:
            continue
        by_group = {}
        for law in dict.fromkeys(laws):
            by_group.setdefault(groups.get(law), []).append(law)
        bad += [(name, group, ls) for group, ls in by_group.items() if group and len(ls) > 1]
    return bad


class DetectorTest(unittest.TestCase):
    """The scan has to see the shape it guards against, or a green run proves nothing."""

    GROUPS = {"law_a": "lawgroup_x", "law_b": "lawgroup_x", "law_c": "lawgroup_y"}

    def test_flags_a_limit_that_lists_two_laws_of_a_group(self):
        text = "on_enact = { if = { limit = { has_law = law_type:law_a has_law = law_type:law_b } } }"
        self.assertEqual(impossible_ands(text, self.GROUPS), [("limit", "lawgroup_x", ["law_a", "law_b"])])

    def test_flags_an_and_block(self):
        text = "trigger = { AND = { has_law = law_type:law_a has_law = law_type:law_b } }"
        self.assertEqual(impossible_ands(text, self.GROUPS), [("AND", "lawgroup_x", ["law_a", "law_b"])])

    def test_accepts_the_group_inside_or_nor_nand_and_not(self):
        for wrapper in sorted(ANY_OF_BLOCKS):
            with self.subTest(wrapper=wrapper):
                text = f"limit = {{ {wrapper} = {{ has_law = law_type:law_a has_law = law_type:law_b }} }}"
                self.assertEqual(impossible_ands(text, self.GROUPS), [])

    def test_accepts_laws_of_different_groups_and_a_repeated_law(self):
        text = "limit = { has_law = law_type:law_a has_law = law_type:law_c has_law = law_type:law_a }"
        self.assertEqual(impossible_ands(text, self.GROUPS), [])


class LawFilesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.groups = law_groups()

    def test_group_table_reads_the_laws_these_checks_rest_on(self):
        for law in (
            "law_ethnostate",
            "law_multicultural",
            "law_minority_rights_cultural_assimilation",
            "law_minority_rights_protection",
            "law_minority_rights_affirmative_action",
            "law_minority_rights_indifference",
        ):
            self.assertIn(law, self.groups)
        self.assertEqual(self.groups["law_ethnostate"], "lawgroup_citizenship")
        for law in (
            "law_minority_rights_cultural_assimilation",
            "law_minority_rights_protection",
            "law_minority_rights_affirmative_action",
            "law_minority_rights_indifference",
        ):
            self.assertEqual(self.groups[law], "lawgroup_minority_rights", law)

    def test_no_law_file_ands_two_laws_of_one_group(self):
        problems = []
        for path in sorted(LAWS_DIR.glob("*.txt")):
            for name, group, laws in impossible_ands(code(path), self.groups):
                problems.append(f"{path.name}: a `{name}` block asks for {', '.join(laws)} ({group}) at once")
        self.assertEqual(problems, [], "\n".join(problems))

    def test_ancestral_citizenship_clears_a_minority_rights_law_that_does_not_fit(self):
        text = code(CITIZENSHIP)
        m = re.search(r"^REPLACE:law_ethnostate\s*=\s*\{", text, re.M)
        self.assertTrue(m)
        on_enact = text[text.index("on_enact", m.end()):]
        on_enact = on_enact[: on_enact.index("recalculate_pop_ig_support")]
        names = [name for name, _ in block_laws("x = { " + on_enact)]
        self.assertIn("OR", names, "the three Minority Rights laws belong in one OR")
        or_laws = next(laws for name, laws in block_laws("x = { " + on_enact) if name == "OR")
        self.assertEqual(
            sorted(or_laws),
            [
                "law_minority_rights_affirmative_action",
                "law_minority_rights_cultural_assimilation",
                "law_minority_rights_protection",
            ],
        )
        self.assertIn("activate_law = law_type:law_minority_rights_indifference", on_enact)


if __name__ == "__main__":
    unittest.main()
