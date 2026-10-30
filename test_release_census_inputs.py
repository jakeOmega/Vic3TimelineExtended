"""scripts/release/comment_out_census_inputs.py: a release build with the census off.

The census reads nine script-only modifier types from techs, laws, institutions and a
static modifier; their lines render on those tooltips although the engine never applies
them. A release that ships without the census runs the script on its release branch
(never on main). The test runs it on a copy of common/ and events/ and checks the build
it leaves: no line sets a census type, nothing else is touched, the files still parse,
the gates read always = no and the rule is gone.
"""
import importlib.util
import re
import shutil
import tempfile
import unittest
from pathlib import Path

from paradox_file_parser import ParadoxFileParser

REPO = Path(__file__).resolve().parent
SCRIPT = REPO / "scripts" / "release" / "comment_out_census_inputs.py"
TAG = "# RELEASE: "


def _load():
    spec = importlib.util.spec_from_file_location("comment_out_census_inputs", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _code(line):
    return line.split("#", 1)[0]


class ReleaseCensusInputsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script = _load()
        cls.tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.tmp.name)
        for part in ("common", "events"):
            shutil.copytree(REPO / part, cls.root / part)
        cls.before = {p: p.read_bytes() for p in cls.root.rglob("*.txt")}
        cls.script.run(cls.root, check=False)
        cls.after = {p: p.read_bytes() for p in cls.root.rglob("*.txt")}
        cls.changed = sorted(p for p in cls.before if cls.before[p] != cls.after[p])
        cls.types = re.findall(r"^(\w+) = \{", (REPO / cls.script.TYPES_FILE).read_text(encoding="utf-8-sig"), re.M)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def _text(self, rel):
        return (self.root / rel).read_text(encoding="utf-8-sig")

    def test_no_line_sets_a_census_type(self):
        carrier = re.compile(rf"^\s*({'|'.join(self.types)})\s*=")
        for path in self.root.joinpath("common").rglob("*.txt"):
            if "modifier_type_definitions" in path.parts:
                continue
            for n, line in enumerate(path.read_text(encoding="utf-8-sig").split("\n"), 1):
                self.assertNotRegex(_code(line), carrier, f"{path.relative_to(self.root)}:{n}")

    def test_the_moved_engine_lines_ship(self):
        """Owner, 2026-10-11 (the engine-lines plan, Task 7): a release has no Demographics rule, so the laws',
        technologies' and institutions' birth and mortality lines reach the states through the moved lines' pairs.
        The script leaves their types, the vanilla laws' INJECTs, the pairs, their refresh and its hooks alone, and
        every carrier's moved line stays live."""
        for rel in ("common/modifier_type_definitions/demographics_engine_line_types.txt",
                    "common/laws/te_demog_engine_line_injections.txt",
                    "common/static_modifiers/te_demog_line_modifiers_generated.txt",
                    "common/script_values/te_demog_line_values_generated.txt",
                    "common/scripted_effects/te_demog_line_effects_generated.txt",
                    "common/on_actions/te_demog_on_actions.txt"):
            self.assertNotIn(self.root / rel, self.changed, rel)
        for path in self.changed:
            for line in path.read_text(encoding="utf-8-sig").split("\n"):
                self.assertFalse(line.startswith(TAG) and "state_demog_" in line, f"{path}: {line}")
        mods = self._text("common/static_modifiers/te_inheritance_modifiers.txt")
        self.assertRegex(mods, r"(?m)^\tstate_demog_absorbed_birth_rate_mult = 0\.1$",
                         "a release keeps Primogeniture's farm births: the pair re-applies them")
        self.assertRegex(mods, r"(?m)^\tstate_demog_absorbed_birth_rate_mult = -0\.15$",
                         "a release keeps Forced Heirship's farm births (phase 3): the pair re-applies them")
        # the switch: no rule, so te_demog_effects_run reads always = no and te_demog_lines_apply holds everywhere
        triggers = self._text("common/scripted_triggers/te_demog_triggers.txt")
        self.assertIn("te_demog_lines_apply = {", triggers)
        self.assertNotIn(TAG + "te_demog_lines_apply", triggers)

    def test_wealth_concentrations_law_lines_ship(self):
        """Wealth Concentration runs whatever the Demographics rule, so its law terms (on the laws since 2026-10-17) are
        not census inputs: their types sit outside the census's types file and every line stays live in a release."""
        wc = ("country_wealth_concentration_inheritance_add", "state_wealth_concentration_land_add",
              "country_wealth_concentration_tax_add",
              "country_wealth_concentration_economy_add", "country_wealth_concentration_public_goods_add",
              "country_wealth_concentration_slavery_add")
        self.assertFalse(set(wc) & set(self.types))
        for rel in ("common/modifier_type_definitions/demographics_wealth_concentration_types.txt",
                    "common/laws/te_demog_wealth_law_injections.txt"):
            self.assertNotIn(self.root / rel, self.changed, rel)
        live = re.compile(rf"^\s*({'|'.join(wc)})\s*=")
        lines = [line for folder in ("laws", "amendments") for path in self.root.joinpath("common", folder).glob("*.txt")
                 for line in path.read_text(encoding="utf-8-sig").split("\n") if live.match(line)]
        self.assertEqual(len(lines), 36, "5 inheritance laws and their 4 amendments, 8 land laws, Graduated Taxation, "
                                         "3 economic systems, 4 antitrust laws, 5 health and school laws, 2 IP laws, "
                                         "4 slavery laws")

    def test_it_found_the_carriers(self):
        # the types sat on 39 lines on 2026-10-11; the Causes of Death plan adds the six technologies' and
        # Medical Outreach's spread of medicine; more later, never fewer
        tagged = sum(
            1 for p in self.changed for line in p.read_text(encoding="utf-8-sig").split("\n")
            if line.startswith(TAG) and re.match(rf"\s*({'|'.join(self.types)})\s*=", line[len(TAG):]))
        self.assertGreaterEqual(tagged, 46)

    def test_it_only_comments_lines_out(self):
        # every changed line is the old line behind the tag, except the gates' always = no
        for path in self.changed:
            old = self.before[path].decode("utf-8-sig").split("\n")
            new = self.after[path].decode("utf-8-sig").split("\n")
            rest = [line[len(TAG):] if line.startswith(TAG) else line for line in new]
            rest = [line for line in rest if line.strip() != "always = no"]
            self.assertEqual(rest, old, path.relative_to(self.root))

    def _entry_lines(self, text, name):
        """The line indexes of the top-level `name = { ... }` entry, by brace depth."""
        lines, out, depth = text.split("\n"), set(), 0
        for i, line in enumerate(lines):
            if not out and re.match(rf"{re.escape(name)} = \{{", line):
                out.add(i)
                depth = _code(line).count("{") - _code(line).count("}")
                continue
            if out and depth > 0:
                out.add(i)
                depth += _code(line).count("{") - _code(line).count("}")
        return out

    def test_what_else_it_comments_is_dead_with_the_census(self):
        # outside the census's lines: the entries they leave empty, Family Limitation's application, Medical Outreach
        # (its only effect was a census type), the gates' old bodies and the rule
        census = re.compile(rf"^\s*({'|'.join(self.types)})\s*=")
        # Causes of Death's tags on vanilla's mortality lines (owner, 2026-10-22): INJECTs that carry only a tag
        whole_entries = {"common/laws/te_demog_law_injections.txt",
                         "common/technology/technologies/te_demog_tech_injections.txt",
                         "common/static_modifiers/te_demog_cause_tags_generated.txt",
                         "common/interest_group_traits/te_demog_cause_tags_generated.txt",
                         "common/character_traits/te_demog_cause_tags_generated.txt"}
        decrees = "common/decrees/extra_decrees.txt"
        outreach = self._entry_lines(self.before[self.root / decrees].decode("utf-8-sig"), "decree_medical_outreach")
        self.assertTrue(outreach, "decree_medical_outreach found")
        for path in self.changed:
            rel = path.relative_to(self.root).as_posix()
            for n, line in enumerate(path.read_text(encoding="utf-8-sig").split("\n")):
                if not line.startswith(TAG):
                    continue
                body = line[len(TAG):]
                with self.subTest(rel=rel, line=body.strip()):
                    if census.match(body) or rel in whole_entries:
                        continue
                    if rel == decrees:
                        self.assertIn(n, outreach, "only Medical Outreach goes whole")
                    elif rel == "common/history/extra_history.txt":
                        self.assertIn("add_modifier = { name = te_demog_family_limitation }", body)
                    elif rel == "common/scripted_effects/te_demog_fl_effects.txt":
                        # phase 3: the census's own line, at the share's multiplier, under Full
                        self.assertRegex(body, r"add_modifier = \{ name = te_demog_family_limitation multiplier = \S+ \}")
                    else:
                        self.assertIn(rel, {"common/scripted_triggers/te_demog_triggers.txt",
                                            "common/game_rules/extra_game_rules.txt"})

    def test_the_census_decree_is_commented_whole(self):
        """Medical Outreach's only effect is the census's spread of medicine: a release has no census, so the decree
        goes whole, not as a shell with a texture and a cost (the Causes of Death plan)."""
        entries = self._entries(self._text("common/decrees/extra_decrees.txt"))
        self.assertNotIn("decree_medical_outreach", entries)
        for kept in ("decree_natalism_initiative", "decree_pollution_control", "decree_war_propaganda"):
            self.assertIn(kept, entries)

    def test_the_injection_files_are_inert(self):
        for rel in ("common/laws/te_demog_law_injections.txt",
                    "common/technology/technologies/te_demog_tech_injections.txt"):
            code = [_code(line).strip() for line in self._text(rel).split("\n")]
            self.assertFalse([c for c in code if c], rel)

    def test_the_migrant_profiles_inputs_go_and_their_carriers_stay(self):
        """Stage 3 of the modifier-types design (2026-10-19): families among migrants is a census-only type. A release
        comments its lines out on the mod's own carriers too (the two aviation techs), and keeps every other line those
        carry; the vanilla carriers' INJECTs go whole (test_the_injection_files_are_inert). Stage 3's other type, the
        women's-rights laws' share of women at work, went on 2026-10-25."""
        self.assertIn("state_family_migration_add", self.types)
        self.assertNotIn("state_female_work_share_add", self.types)
        for rel, entry, typ, kept in (
                ("common/technology/technologies/era_6.txt", "commercial_aviation", "state_family_migration_add",
                 "state_building_airport_max_level_add = 1"),
                ("common/technology/technologies/era_7.txt", "jet_engine_technology", "state_family_migration_add",
                 "state_building_airport_max_level_add = 1")):
            with self.subTest(entry=entry):
                lines = self._text(rel).split("\n")
                body = [lines[i] for i in sorted(self._entry_lines(self._text(rel), entry))]
                self.assertTrue(body, entry)
                hits = [line for line in body if typ in line]
                self.assertEqual(len(hits), 1, entry)
                self.assertTrue(hits[0].startswith(TAG), hits[0])
                self.assertTrue([line for line in body if kept in _code(line)], f"{entry} keeps {kept}")

    def test_the_late_chronic_treatment_lines_go_and_their_technologies_stay(self):
        """The safeguards pass (owner, 2026-10-20): chronic treatment on Genetic Engineering, Molecular Assemblers and
        Biological Immortality. A release comments each line out and keeps every other line the technology carries."""
        self.assertIn("state_chronic_treatment_add", self.types)
        for rel, entry, kept in (
                ("common/technology/technologies/era_11.txt", "genetic_engineering", "state_arable_land_mult = 0.50"),
                ("common/technology/technologies/era_12.txt", "molecular_assemblers",
                 "country_max_weekly_construction_progress_add = 200"),
                ("common/technology/technologies/era_12.txt", "biological_immortality", "character_health_add = 100")):
            with self.subTest(entry=entry):
                lines = self._text(rel).split("\n")
                body = [lines[i] for i in sorted(self._entry_lines(self._text(rel), entry))]
                hits = [line for line in body if "state_chronic_treatment_add" in line]
                self.assertEqual(len(hits), 1, entry)
                self.assertTrue(hits[0].startswith(TAG), hits[0])
                self.assertTrue([line for line in body if kept in _code(line)], f"{entry} keeps {kept}")

    def test_family_limitation_is_never_applied(self):
        # its only effect line is a census type, so applied it would show on France doing nothing
        for path in [*self.root.joinpath("common").rglob("*.txt"), *self.root.joinpath("events").rglob("*.txt")]:
            code = "\n".join(_code(line) for line in path.read_text(encoding="utf-8-sig").split("\n"))
            self.assertNotRegex(code, r"name\s*=\s*te_demog_family_limitation\b", path.relative_to(self.root))

    def test_the_gates_read_always_no(self):
        text = self._text("common/scripted_triggers/te_demog_triggers.txt")
        for gate in ("te_demog_cohorts_run", "te_demog_effects_run"):
            body = re.search(rf"^{gate} = \{{(.*?)^\}}", text, re.M | re.S).group(1)
            self.assertEqual([_code(line).strip() for line in body.split("\n") if _code(line).strip()],
                             ["always = no"], gate)

    def _entries(self, text):
        """{name: body} of the top-level `name = { ... }` entries in the code-only text."""
        code = "\n".join(_code(line) for line in text.split("\n"))
        out, depth, start = {}, 0, None
        for m in re.finditer(r"[{}]", code):
            if m.group() == "{":
                if depth == 0:
                    start = m.start()
                depth += 1
            else:
                depth -= 1
                if depth == 0:
                    name = re.search(r"(\S+)\s*=\s*$", code[:start]).group(1)
                    out[name] = code[start:m.end()]
        return out

    def test_it_leaves_every_other_rule_and_trigger_alone(self):
        # only demographics_rule goes from the rules file, and only the two gates change in the
        # triggers file: the walks feeding Wealth Concentration call the others
        for rel, keep_out in (("common/game_rules/extra_game_rules.txt", {"demographics_rule"}),
                              ("common/scripted_triggers/te_demog_triggers.txt", set(self.script.GATES))):
            before = self._entries(self.before[self.root / rel].decode("utf-8-sig"))
            after = self._entries(self._text(rel))
            with self.subTest(rel=rel):
                self.assertTrue(keep_out <= set(before))
                for name, body in before.items():
                    if name not in keep_out:
                        self.assertEqual(after.get(name), body, name)

    def test_the_rule_is_gone(self):
        text = self._text("common/game_rules/extra_game_rules.txt")
        self.assertNotRegex("\n".join(_code(line) for line in text.split("\n")), r"demographics_")

    def test_every_changed_file_still_parses_with_its_bom(self):
        parser = ParadoxFileParser()
        for path in self.changed:
            with self.subTest(path=path.relative_to(self.root)):
                self.assertEqual(self.after[path].startswith(b"\xef\xbb\xbf"),
                                 self.before[path].startswith(b"\xef\xbb\xbf"))
                self.assertFalse(self.after[path].startswith(b"\xef\xbb\xbf\xef\xbb\xbf"))
                text = path.read_text(encoding="utf-8-sig")
                code = "\n".join(_code(line) for line in text.split("\n"))
                self.assertEqual(code.count("{"), code.count("}"))
                parser.parse_object(parser.tokenize("{" + text + "}"))

    def test_a_second_run_changes_nothing(self):
        self.script.run(self.root, check=False)
        again = {p: p.read_bytes() for p in self.root.rglob("*.txt")}
        self.assertEqual([p for p in again if again[p] != self.after[p]], [])


if __name__ == "__main__":
    unittest.main()
