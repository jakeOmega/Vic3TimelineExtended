"""ig_feminism.py: the INJECT blocks it builds, and the committed file it wrote."""

import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import ig_feminism as g  # noqa: E402
from format_paradox_tabs import format_text  # noqa: E402
from paradox_file_parser import ParadoxFileParser  # noqa: E402

COMMITTED = os.path.join(ROOT, g.OUTPUT_RELPATH)
SNAPSHOT = os.path.join(ROOT, "vanilla_parsed", "common", "interest_groups.json")

# Vanilla's layout varies: a one-line field, stray indentation, blank lines, a
# trailing comment, and the field's name inside a comment ahead of the field.
VANILLA = """ig_example = {
    color = hsv{ 0.1 0.2 0.3 }
    # female_commander_chance = { value = 9 } is a comment, not the field
    female_commander_chance = { value = 0.0 }
  female_politician_chance = {
        value = 0.0   # base
        if = {
            limit = { owner = { has_law_or_variant = law_type:law_womens_suffrage } }

            add = {
                value = 0.1
            }
        }
    }
    female_agitator_chance = {
        value = 0.05
    }
    on_enable = { }
}
"""

PROFILE = {"law_type:law_x": {"type": "has_law", "increase": 0.2}}
BRANCH = """		if = {
			limit = {
				owner = {
					has_law = law_type:law_x
				}
			}
			add = { value = 0.2 }
		}
"""


def _roles(profile):
    return {role: profile for role in ("female_commander_chance", "female_politician_chance", "female_agitator_chance")}


class BuildInjectTest(unittest.TestCase):
    def test_restates_vanilla_then_adds_the_profile(self):
        expected = (
            "INJECT:ig_example = {\n"
            "\tfemale_commander_chance = {\n"
            "\t\tvalue = 0.0\n"
            + BRANCH
            + "\t}\n"
            "\tfemale_politician_chance = {\n"
            "\t\tvalue = 0.0   # base\n"
            "\t\tif = {\n"
            "\t\t\tlimit = { owner = { has_law_or_variant = law_type:law_womens_suffrage } }\n"
            "\t\t\tadd = {\n"
            "\t\t\t\tvalue = 0.1\n"
            "\t\t\t}\n"
            "\t\t}\n"
            + BRANCH
            + "\t}\n"
            "\tfemale_agitator_chance = {\n"
            "\t\tvalue = 0.05\n"
            + BRANCH
            + "\t}\n"
            "}"
        )
        self.assertEqual(g.build_inject(VANILLA, _roles(PROFILE)), expected)

    def test_technology_branch(self):
        lines = g.branch_lines("tech_y", {"type": "technology", "increase": 0.05})
        self.assertIn("has_technology_researched = tech_y", lines)
        self.assertIn("add = { value = 0.05 }", lines)

    def test_output_is_tab_formatted(self):
        text = g.build_inject(VANILLA, _roles(PROFILE)) + "\n"
        self.assertEqual(format_text(text), text)

    def test_missing_field_raises(self):
        with self.assertRaises(ValueError):
            g.field_lines("ig_example = { }", "female_commander_chance")


class CommittedFileTest(unittest.TestCase):
    """The committed file is what the generator writes from the vanilla lines it
    restates, and those lines are vanilla's (per the committed snapshot). The
    generator itself needs the game files, so this is the check CI can run."""

    @classmethod
    def setUpClass(cls):
        with open(COMMITTED, "rb") as file:
            cls.raw = file.read()
        cls.text = cls.raw.decode("utf-8-sig")
        cls.vanilla = {}  # file name -> (ig key, {role: vanilla lines})
        for filename, roles in g.modifications.items():
            ig = "ig_" + filename[len("00_"):-len(".txt")]
            block = "\n".join(g.field_lines(cls.text, f"INJECT:{ig}"))
            fields = {}
            for role, profile in roles.items():
                lines = g.field_lines(block, role)
                fields[role] = lines[: len(lines) - 8 * len(profile)]
            cls.vanilla[filename] = (ig, fields)

    def test_one_bom(self):
        self.assertTrue(self.raw.startswith(b"\xef\xbb\xbf"))
        self.assertFalse(self.raw[3:].startswith(b"\xef\xbb\xbf"))

    def test_matches_a_fresh_generation(self):
        with tempfile.TemporaryDirectory() as tmp:
            for filename, (ig, fields) in self.vanilla.items():
                lines = [f"{ig} = {{"]
                for role, body in fields.items():
                    lines += [f"{role} = {{", *body, "}"]
                lines.append("}")
                with open(os.path.join(tmp, filename), "w", encoding="utf-8-sig") as file:
                    file.write("\n".join(lines) + "\n")
            self.assertEqual(
                g.build_file(tmp, g.modifications),
                self.text,
                "zz_te_ig_female_chance.txt is stale: run ig_feminism.py on a machine with the game.",
            )

    def test_restated_lines_are_vanillas(self):
        with open(SNAPSHOT, encoding="utf-8") as file:
            snapshot = json.load(file)

        def norm(value):
            return json.dumps(json.loads(json.dumps(value)), sort_keys=True)

        for ig, fields in self.vanilla.values():
            text = f"{ig} = {{\n" + "".join(
                f"{role} = {{\n" + "\n".join(body) + "\n}\n" for role, body in fields.items()
            ) + "}\n"
            with tempfile.NamedTemporaryFile("w", suffix=".txt", encoding="utf-8", delete=False) as file:
                file.write(text)
            try:
                parser = ParadoxFileParser()
                parser.parse_file(file.name)
            finally:
                os.unlink(file.name)
            parsed = parser.data[ig][1]
            for role in fields:
                with self.subTest(ig=ig, role=role):
                    self.assertEqual(norm(parsed[role]), norm(snapshot[ig][1][role]))


if __name__ == "__main__":
    unittest.main()
