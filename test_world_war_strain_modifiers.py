"""The World War's home front strain is added by its yearly pulse alone (#1617).

"Put the safety of our cities first" (world_war_events.11.a) used to put a
short decaying copy of ww_home_front_strain_modifier on the journal entry. The
pulse adds the standing copy from the war's second year, and only when the
entry holds none, so a copy taken before then kept the standing one away until
it had run out, and one taken after it stacked on it (a same-name add_modifier
stacks). The option now adds ww_air_raid_relief_modifier: the same values,
under its own name, counted once with the strain in war support and removed
wherever the strain is.

Structural tests on the script text; no game or server needed.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STRAIN = "ww_home_front_strain_modifier"
RELIEF = "ww_air_raid_relief_modifier"


def read(rel):
    return re.sub(r"#[^\n]*", "", (ROOT / rel).read_text(encoding="utf-8-sig"))


def block(text, opener):
    """The braced body that starts at the first `opener` (which ends in `{`)."""
    start = text.index(opener) + len(opener)
    depth, i = 1, start
    while depth:
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        i += 1
    return text[start:i - 1]


def fields(text, name):
    """The `key = value` lines of the top-level static modifier `name`."""
    return dict(re.findall(r"^\s*(\w+)\s*=\s*(\S+)\s*$", block(text, f"\n{name} = {{"), re.M))


def loc_keys():
    keys = set()
    for path in (ROOT / "localization/english").glob("*_l_english.yml"):
        keys.update(re.findall(r"^ ([\w.\-]+):", path.read_text(encoding="utf-8-sig"), re.M))
    return keys


class HomeFrontStrainTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.events = read("events/world_war_events.txt")
        cls.entry = read("common/journal_entries/world_war_je.txt")
        cls.modifiers = read("common/static_modifiers/extra_modifiers.txt")
        cls.war_support = read("common/script_values/zz_te_war_support_injections.txt")

    def test_only_the_pulse_adds_the_strain(self):
        adds = re.compile(r"add_modifier\s*=\s*\{[^{}]*\bname\s*=\s*" + STRAIN + r"\b")
        sites = {}
        for folder in ("common", "events"):
            for path in (ROOT / folder).rglob("*.txt"):
                found = len(adds.findall(re.sub(r"#[^\n]*", "", path.read_text(encoding="utf-8-sig"))))
                if found:
                    sites[path.relative_to(ROOT).as_posix()] = found
        self.assertEqual(sites, {"common/journal_entries/world_war_je.txt": 1})
        # And the pulse still asks that the entry holds none before it adds one.
        self.assertRegex(self.entry, r"NOT\s*=\s*\{\s*je:je_world_war\s*=\s*\{\s*has_modifier\s*=\s*" + STRAIN)

    def test_the_option_adds_its_own_decaying_modifier(self):
        option = block(self.events, "option = {\n\t\tname = world_war_events.11.a\n")
        self.assertNotIn(STRAIN, option)
        added = re.search(r"je:je_world_war\s*=\s*\{\s*add_modifier\s*=\s*\{([^{}]*)\}", option)
        self.assertIsNotNone(added, "world_war_events.11.a adds nothing to the journal entry")
        self.assertEqual(dict(re.findall(r"(\w+)\s*=\s*(\S+)", added.group(1))),
                         {"name": RELIEF, "days": "short_modifier_time", "is_decaying": "yes"})

    def test_the_two_modifiers_keep_the_same_values(self):
        self.assertEqual(fields(self.modifiers, RELIEF), fields(self.modifiers, STRAIN))

    def test_war_support_counts_the_two_once(self):
        # An `else_if` straight after the strain's `if`, at the same value:
        # with both on the entry the drain is one line, as it was when the
        # option's modifier was a copy of the strain.
        line = (r"if\s*=\s*\{\s*limit\s*=\s*\{\s*je:je_world_war\s*\?=\s*\{\s*has_modifier\s*=\s*%s\s*\}\s*\}"
                r"\s*add\s*=\s*\{\s*value\s*=\s*(-?[\d.]+)\s*desc\s*=\s*\"(\w+)\"\s*\}\s*\}")
        both = re.search(line % STRAIN + r"\s*else_" + line % RELIEF, self.war_support)
        self.assertIsNotNone(both, "the air-raid line is not an else_if to the strain line")
        self.assertEqual(both.group(1), both.group(3))
        self.assertLessEqual({both.group(2), both.group(4)}, loc_keys())

    def test_whatever_clears_the_strain_clears_the_relief(self):
        removes = r"je:je_world_war\s*=\s*\{\s*remove_modifier\s*=\s*%s\s*\}"
        for rel in ("common/journal_entries/world_war_je.txt",
                    "common/scripted_effects/te_event_agency_ww_effects.txt"):
            text = read(rel)
            with self.subTest(file=rel):
                strain = len(re.findall(removes % STRAIN, text))
                self.assertGreater(strain, 0)
                self.assertEqual(len(re.findall(removes % RELIEF, text)), strain)

    def test_the_new_modifier_has_a_name_and_a_description(self):
        self.assertLessEqual({RELIEF, RELIEF + "_desc"}, loc_keys())


if __name__ == "__main__":
    unittest.main()
