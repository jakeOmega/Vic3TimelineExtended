"""Heir Education's ideology rolls (heir_education_resolve_effect).

Two engine-silent ways a roll can go wrong, both found in PR #507:

- set_ideology on an ideology without `character_ideology = yes` (an
  interest-group ideology) does nothing, so the heir keeps whatever ideology
  it had. Six rolls named ideology_liberal / _patriarchal / _pious that way.
- set_ideology ignores an ideology's `country_trigger`, so a roll can hand the
  heir an ideology the country cannot otherwise have. Each such roll carries
  `trigger = { owner = { heir_ed_country_allows_<ideology> = yes } }`, whose
  scripted trigger (common/scripted_triggers/heir_education_triggers.txt) is a
  copy of that country_trigger. The copy must match its source, which
  apply_ideologies.py regenerates from vanilla.

No game install needed: the mod's definitions come from the generated
common/ideologies/modified.txt, vanilla's from the committed vanilla_parsed/.
"""

import json
import os
import re
import unittest

import vanilla_parsed
from paradox_file_parser import ParadoxFileParser

REPO = os.path.dirname(os.path.abspath(__file__))
EFFECTS = os.path.join(REPO, "common", "scripted_effects", "heir_education_effects.txt")
TRIGGERS = os.path.join(REPO, "common", "scripted_triggers", "heir_education_triggers.txt")
MOD_IDEOLOGIES = os.path.join(REPO, "common", "ideologies", "modified.txt")
EXTRA_IDEOLOGIES = os.path.join(REPO, "common", "ideologies", "extra_ideologies.txt")
VANILLA_IDEOLOGIES = os.path.join(REPO, "vanilla_parsed", "common", "ideologies.json")

GATE_PREFIX = "heir_ed_country_allows_"
ROLL = re.compile(
    r"^\t+(\d+) = \{ (?:trigger = \{ owner = \{ (\w+) = yes \} \} )?"
    r"set_ideology = ideology:(\w+) \}$",
    re.M,
)


def _parse(path):
    parser = ParadoxFileParser()
    parser.parse_file(path, apply_directives=False)
    return parser.data


def _body(node):
    """The parser stores `key = { ... }` as ('=', body); unwrap it."""
    return node[1] if isinstance(node, tuple) else node


def _resolve_section():
    with open(EFFECTS, encoding="utf-8-sig") as fh:
        text = fh.read()
    start = text.index("# ─── Resolve Ideology ───")
    end = text.index("# ─── Resolve IG Alignment ───")
    return text[start:end]


def _lists(section):
    """Each random_list in the section as [(weight, gate, ideology), ...]."""
    out = []
    for block in section.split("random_list = {")[1:]:
        body = block[: block.index("\n\t\t\t}")]
        out.append([(int(w), g, i) for w, g, i in ROLL.findall(body)])
    return out


class HeirIdeologyRollTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _parse(MOD_IDEOLOGIES)
        cls.extra = _parse(EXTRA_IDEOLOGIES)
        with open(VANILLA_IDEOLOGIES, encoding="utf-8") as fh:
            cls.vanilla = vanilla_parsed.decode(json.load(fh))
        cls.gates = {k: _body(v) for k, v in _parse(TRIGGERS).items()}
        cls.section = _resolve_section()
        cls.lists = _lists(cls.section)

    def _definition(self, ideology):
        """The ideology as the game sees it: a mod REPLACE wins; an INJECT only
        adds law stances (checked below), so vanilla's own fields stand."""
        for key in (f"REPLACE:{ideology}", ideology):
            if key in self.mod:
                return _body(self.mod[key])
            if key in self.extra:
                return _body(self.extra[key])
        inject = self.mod.get(f"INJECT:{ideology}")
        if inject is not None:
            for field in ("character_ideology", "country_trigger"):
                self.assertNotIn(field, _body(inject), f"INJECT:{ideology} changes {field}")
        self.assertIn(ideology, self.vanilla, f"{ideology} is defined nowhere")
        return _body(self.vanilla[ideology])

    def test_every_set_ideology_line_is_a_parsed_roll(self):
        rolls = sum(len(rows) for rows in self.lists)
        self.assertEqual(rolls, self.section.count("set_ideology"))
        self.assertEqual(len(self.lists), 5)

    def test_every_roll_is_a_character_ideology(self):
        for rows in self.lists:
            for _w, _g, ideology in rows:
                with self.subTest(ideology=ideology):
                    self.assertEqual(_body(self._definition(ideology).get("character_ideology")), "yes")

    def test_gated_exactly_where_a_country_trigger_exists(self):
        for rows in self.lists:
            for _w, gate, ideology in rows:
                with self.subTest(ideology=ideology):
                    has_trigger = "country_trigger" in self._definition(ideology)
                    self.assertEqual(gate, GATE_PREFIX + ideology if has_trigger else "")

    def test_gate_bodies_copy_the_country_triggers(self):
        used = {gate for rows in self.lists for _w, gate, _i in rows if gate}
        self.assertEqual(used, set(self.gates), "unused or missing heir_ed_country_allows_* triggers")
        for gate in sorted(used):
            ideology = gate[len(GATE_PREFIX):]
            with self.subTest(ideology=ideology):
                source = _body(self._definition(ideology)["country_trigger"])
                self.assertEqual(self.gates[gate], source)

    def test_every_list_keeps_an_ungated_outcome(self):
        for rows in self.lists:
            with self.subTest(rows=rows):
                self.assertTrue(any(not gate for _w, gate, _i in rows))


if __name__ == "__main__":
    unittest.main()
