# -*- coding: utf-8 -*-
"""The proposal list's "Nearest" line names who the topic's own test admits.

The 2026-10-27 GUI audit's UN-23: a targeted topic with no case shows, on its
row, the candidate with the strongest case and the threshold it falls short
of (``un_chamber_propose_nearest_line``,
``common/scripted_effects/un_chamber_display_effects.txt``). Who counts as a
candidate is a copy of the topic's own test without its case line
(``un_<topic>_relation``, ``common/scripted_triggers/un_propose_triggers.txt``).
Nothing in the engine checks that the copy matches: a relation that drifts
names a country the topic could never target. These tests hold each copy to
its topic's test, line for line.

Run: python3 -m unittest test_un_propose_nearest -v
"""

import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
TRIGGERS = os.path.join(REPO, "common", "scripted_triggers")
DISPLAY = os.path.join(REPO, "common", "scripted_effects", "un_chamber_display_effects.txt")
LOC = os.path.join(REPO, "localization", "english")

# topic -> (file, trigger, the block inside it that is the candidate's test)
CANDIDATE = {
    "condemn": ("un_propose_triggers.txt", "un_propose_condemn_available", "any_country"),
    "sanctions": ("un_propose_triggers.txt", "un_propose_sanctions_available", "any_country"),
    "arms_embargo": ("un_justice_triggers.txt", "un_arms_embargo_candidate", None),
    "credentials": ("un_justice_triggers.txt", "un_credentials_candidate", None),
    "ceasefire": ("un_order_triggers.txt", "un_ceasefire_target_eligible", None),
}


def _read(path):
    with open(path, encoding="utf-8-sig") as f:
        return "\n".join(line.split("#", 1)[0] for line in f.read().split("\n"))


def _body(text, start):
    j = text.index("{", start)
    depth = 0
    for k in range(j, len(text)):
        if text[k] == "{":
            depth += 1
        elif text[k] == "}":
            depth -= 1
            if depth == 0:
                return text[j + 1:k]
    raise AssertionError("unbalanced block")


def _top(text, name):
    m = re.search(rf"(?m)^{re.escape(name)} = \{{", text)
    assert m, f"no {name}"
    return _body(text, m.end() - 1)


def _clauses(body):
    """The block's top-level clauses (`key op value`, the value a token or a
    whole block), each flattened to one line."""
    tokens = re.findall(r"\{|\}|>=|<=|\?=|[=<>]|[^\s{}=<>?]+", body)
    out, i = [], 0
    while i < len(tokens):
        key, op = tokens[i], tokens[i + 1]
        i += 2
        if tokens[i] == "{":
            depth, j = 0, i
            while True:
                depth += {"{": 1, "}": -1}.get(tokens[j], 0)
                j += 1
                if depth == 0:
                    break
            value = " ".join(tokens[i:j])
            i = j
        else:
            value = tokens[i]
            i += 1
        out.append(f"{key} {op} {value}")
    return out


class NearestTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.relations = _read(os.path.join(TRIGGERS, "un_propose_triggers.txt"))
        cls.display = _read(DISPLAY)

    def test_each_relation_is_its_topics_test_without_the_case(self):
        for topic, (fname, name, inner) in CANDIDATE.items():
            body = _top(_read(os.path.join(TRIGGERS, fname)), name)
            if inner:
                body = _body(body, body.index(inner + " = {") + len(inner))
            want = [c for c in _clauses(body) if not c.startswith("un_case_supports")]
            if topic == "ceasefire":
                want = [c.replace("this = scope:un_order_proposer", "this = ROOT") for c in want]
            got = _clauses(_top(self.relations, f"un_{topic}_relation"))
            with self.subTest(topic=topic):
                self.assertEqual(sorted(got), sorted(want))
                self.assertTrue(any(c.startswith("un_case_supports") for c in _clauses(body)), body)

    def test_each_row_asks_for_its_own_topic(self):
        for topic in CANDIDATE:
            row = " ".join(_top(self.display, f"un_chamber_propose_{topic}_row").split())
            with self.subTest(topic=topic):
                self.assertIn(f"NOT = {{ un_propose_{topic}_available = yes }}", row)
                self.assertIn(f"un_chamber_propose_nearest_line = {{ RELATION = un_{topic}_relation "
                              f"KEY = je_un_chamber_propose_nearest_{topic} }}", row)

    def test_each_line_names_its_topics_threshold(self):
        values = {}
        for fname in os.listdir(LOC):
            if not fname.endswith(".yml"):
                continue
            with open(os.path.join(LOC, fname), encoding="utf-8-sig") as f:
                for line in f:
                    m = re.match(r'^ ([\w.\-]+):\d* "(.*)"\s*$', line)
                    if m:
                        values[m.group(1)] = m.group(2)
        for topic in CANDIDATE:
            with self.subTest(topic=topic):
                line = values[f"je_un_chamber_propose_nearest_{topic}"]
                self.assertIn(f"ScriptValue('un_case_threshold_{topic}')", line)
                self.assertIn("SCOPE.sCountry('un_chamber_nearest')", line)


if __name__ == "__main__":
    unittest.main()
