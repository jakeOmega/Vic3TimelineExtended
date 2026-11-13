"""The AI tabling buttons ask their `possible`'s cheap gates in `visible`, ahead
of the case scan in un_propose_<key>_available (performance, 2026-11-12: the
scans cost up to 3 ms a call and the gates refused nearly every tabling).

That is safe only while every gate a button's `visible` asks is also a gate of
the same button's `possible`: then `visible` refuses nothing `possible` would
have allowed, and what the AI can table is unchanged. These tests hold that.
"""

import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
BUTTONS = os.path.join(REPO, "common", "scripted_buttons", "un_buttons.txt")
TRIGGERS = os.path.join(REPO, "common", "scripted_triggers", "un_propose_triggers.txt")

PROPOSALS = re.compile(r"^(un_(?:propose|request)_\w+_button) = \{", re.M)

# Helpers a `possible` calls whose gates count as its own.
EXPANDED = (
    "un_propose_own_motion_possible_punitive",
    "un_propose_own_motion_possible",
    "un_propose_own_motion_gates",
)

# What a `visible` may ask besides possible's gates: who sees the button, and
# what the button is for.
NOT_A_GATE = re.compile(r"^(is_ai = yes|un_charter_reform_ii_in_view = yes|un_propose_\w+_available = yes)$")


def _read(path):
    with open(path, encoding="utf-8-sig") as f:
        return re.sub(r"#[^\n]*", "", f.read())


def _flat(text):
    return re.sub(r"\s+", " ", text).strip()


def _inner(text, start):
    """The body of the block whose `{` is the last character before `start`."""
    depth = 1
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start:i]
    raise AssertionError("block is not closed")


def _named(text, name, anywhere=False):
    m = re.search((r"\b" if anywhere else r"^") + re.escape(name) + r"\s*=\s*\{", text, 0 if anywhere else re.M)
    if m is None:
        raise AssertionError(f"{name} not found")
    return _inner(text, m.end())


def _statements(body):
    """The top-level statements of a block body, flattened."""
    out, depth, cur = [], 0, []
    for tok in re.findall(r"\{|\}|[^\s{}]+", body):
        cur.append(tok)
        if tok == "{":
            depth += 1
        elif tok == "}":
            depth -= 1
        if depth == 0 and (tok == "}" or (len(cur) >= 3 and cur[-2] in ("=", ">=", "<=", ">", "<") and tok != "{")):
            out.append(" ".join(cur))
            cur = []
    assert not cur, cur
    return out


class AiGatesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.buttons = _read(BUTTONS)
        cls.triggers = _read(TRIGGERS)
        cls.names = PROPOSALS.findall(cls.buttons)

    def _gates(self, statements):
        """The conditions a list of statements ANDs, through tooltips and the shared helpers."""
        for stmt in statements:
            tooltip = re.fullmatch(r"custom_tooltip = \{ text = \w+ (.*) \}", stmt)
            helper = re.fullmatch(r"(\w+) = yes", stmt)
            reform = re.fullmatch(r"un_charter_has_reform_tt = \{ LEVEL = (\d) TT = \w+ \}", stmt)
            if tooltip:
                yield from self._gates(_statements(tooltip.group(1)))
            elif helper and helper.group(1) in EXPANDED:
                yield from self._gates(_statements(_named(self.triggers, helper.group(1))))
            elif reform:
                yield f"un_charter_has_reform = {{ LEVEL = {reform.group(1)} }}"
            else:
                yield stmt

    def _possible(self, button_body):
        possible = _flat(_named(button_body, "possible", anywhere=True))
        key = re.fullmatch(r"(un_propose_\w+_possible) = yes", possible)
        self.assertIsNotNone(key, possible)
        return set(self._gates(_statements(_named(self.triggers, key.group(1)))))

    def test_there_are_seventeen_tabling_buttons(self):
        self.assertEqual(len(self.names), 17, self.names)

    def test_each_visible_asks_the_floor_first_and_the_case_last(self):
        for name in self.names:
            with self.subTest(button=name):
                visible = _statements(_named(_named(self.buttons, name), "visible", anywhere=True))
                self.assertEqual(visible[0], "is_ai = yes")
                self.assertIn("un_propose_ai_floor_open = yes", visible)
                self.assertRegex(visible[-1], r"^un_propose_\w+_available = yes$")

    def test_every_gate_visible_asks_is_possibles(self):
        floor = _statements(_named(self.triggers, "un_propose_ai_floor_open"))
        for name in self.names:
            body = _named(self.buttons, name)
            possible = self._possible(body)
            gates = [g for g in _statements(_named(body, "visible", anywhere=True)) if not NOT_A_GATE.match(g)]
            gates.remove("un_propose_ai_floor_open = yes")
            for gate in floor + gates:
                with self.subTest(button=name, gate=gate):
                    self.assertIn(gate, possible)


if __name__ == "__main__":
    unittest.main()
