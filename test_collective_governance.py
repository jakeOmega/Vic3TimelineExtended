# -*- coding: utf-8 -*-
"""Collective Governance (law_direct_democracy): one table, pinned against
every site that lists the Distribution of Power expressions by hand.

The law keeps its engine key and is displayed as Collective Governance. Each
Distribution of Power group it allows gets one script-attached amendment and
at least one government type. Nothing in the engine checks that the
prerequisites, triggers, amendments, refresh effect, preview tooltips and
government types agree, and a mismatch is engine-silent: a country holding the
law with no amendment, or with the wrong government name. EXPRESSIONS is the
single list; each test checks one site against it. To add a Distribution of
Power law, add it to its row (or add a row) and follow the failures.

Spec: docs/superpowers/specs/2026-09-26-collective-governance-design.md

Run: python3 -m unittest test_collective_governance -v
"""

import os
import re
import unittest
from collections import namedtuple

REPO = os.path.dirname(os.path.abspath(__file__))


def _path(*parts):
    return os.path.join(REPO, *parts)


def _raw(path):
    with open(path, encoding="utf-8-sig") as f:
        return f.read()


def _read(path):
    """Script text with comments stripped (not for loc: `#b` is markup there)."""
    return re.sub(r"#[^\n]*", "", _raw(path))


def _close(text, open_brace):
    depth = 0
    for i in range(open_brace, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return i
    raise AssertionError("unclosed block")


def _block(text, name):
    """The body of the top-level ``name = { ... }`` block (an optional
    INJECT:/REPLACE: prefix is allowed)."""
    m = re.search(r"^(?:[A-Z_]+:)?" + re.escape(name) + r"\s*=\s*\{", text, re.M)
    if m is None:
        raise AssertionError(f"{name} not found")
    return text[m.end():_close(text, m.end() - 1)]


def _inner(text, name):
    """The body of the first ``name = { ... }`` block at any depth."""
    m = re.search(r"(?<![\w.:])" + re.escape(name) + r"\s*=\s*\{", text)
    if m is None:
        raise AssertionError(f"{name} not found")
    return text[m.end():_close(text, m.end() - 1)]


def _norm(text):
    return " ".join(text.split())


def _top_level_names(text):
    return re.findall(r"^(\w+)\s*=\s*\{", text, re.M)


def _modifiers(body):
    return dict(re.findall(r"(\w+)\s*=\s*(-?[\w.]+)", body))


_LOC_LINE = re.compile(r'^\s*([\w.]+):\d*\s*"(.*)"\s*$')


def _loc():
    out = {}
    folder = _path("localization", "english")
    for name in os.listdir(folder):
        if name.endswith(".yml"):
            with open(os.path.join(folder, name), encoding="utf-8-sig") as f:
                for line in f:
                    m = _LOC_LINE.match(line)
                    if m:
                        out[m.group(1)] = m.group(2)
    return out


Expression = namedtuple("Expression", "trigger dop_laws amendment tooltip")

EXPRESSIONS = [
    Expression(
        "collective_governance_is_popular",
        {"law_landed_voting", "law_wealth_voting", "law_census_voting", "law_universal_suffrage"},
        "amendment_collective_direct_democracy",
        "COLLECTIVE_GOVERNANCE_TT_POPULAR",
    ),
    Expression(
        "collective_governance_is_party",
        {"law_single_party_state"},
        "amendment_collective_leadership",
        "COLLECTIVE_GOVERNANCE_TT_PARTY",
    ),
    Expression(
        "collective_governance_is_technocratic",
        {"law_technocracy"},
        "amendment_collective_administration",
        "COLLECTIVE_GOVERNANCE_TT_TECHNOCRATIC",
    ),
    Expression(
        "collective_governance_is_anarchic",
        {"law_anarchy"},
        "amendment_collective_free_federation",
        "COLLECTIVE_GOVERNANCE_TT_ANARCHIC",
    ),
    Expression(
        "collective_governance_is_patrician",
        {"law_oligarchy", "law_organic_regulation"},
        "amendment_collective_patrician_council",
        "COLLECTIVE_GOVERNANCE_TT_PATRICIAN",
    ),
]

TRIGGERS = _path("common", "scripted_triggers", "collective_governance_triggers.txt")


class TriggerTests(unittest.TestCase):
    def test_each_trigger_lists_exactly_its_laws(self):
        text = _read(TRIGGERS)
        for e in EXPRESSIONS:
            with self.subTest(trigger=e.trigger):
                laws = set(re.findall(r"has_law\s*=\s*law_type:(\w+)", _block(text, e.trigger)))
                self.assertEqual(laws, e.dop_laws)

    def test_no_stale_trigger(self):
        self.assertEqual(set(_top_level_names(_read(TRIGGERS))), {e.trigger for e in EXPRESSIONS})

    def test_no_law_is_in_two_groups(self):
        laws = [law for e in EXPRESSIONS for law in e.dop_laws]
        self.assertEqual(len(laws), len(set(laws)))

    def test_file_has_bom(self):
        with open(TRIGGERS, "rb") as f:
            self.assertEqual(f.read(3), b"\xef\xbb\xbf")


if __name__ == "__main__":
    unittest.main()
