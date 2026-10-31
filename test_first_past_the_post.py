"""First Past the Post: the join-weight generator, the file it wrote, and the
lists the system keeps in step (party types, allowed laws, the voting-law group)."""

import json
import os
import re
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts", "generators"))

import gen_party_join_weights as g  # noqa: E402
import vanilla_parsed  # noqa: E402
from ig_feminism import field_lines  # noqa: E402
from paradox_file_parser import ParadoxFileParser  # noqa: E402

COMMITTED = os.path.join(ROOT, g.OUTPUT_RELPATH)
SNAPSHOT = os.path.join(ROOT, "vanilla_parsed", "common", "parties.json")
MOD_PARTIES = ("green_party", "populist_party", "technocratic_party")


def _read(relpath):
    with open(os.path.join(ROOT, relpath), encoding="utf-8-sig") as file:
        return file.read()


def _block(text, key):
    """The stripped lines inside `key = { ... }`."""
    return field_lines(text, re.escape(key))


def _norm(value):
    return json.dumps(vanilla_parsed.encode(value), sort_keys=True)


def _without_dropped_terms(join_weight):
    """A parsed join_weight without the top-level terms naming a dropped desc.
    The generator refuses a dropped term inside an if/else_if chain, so taking
    entries out of a key's list leaves every chain whole."""
    operator, body = join_weight[0], join_weight[1]
    kept = {}
    for key, value in body.items():
        entries = value if isinstance(value, list) else [value]
        entries = [e for e in entries if not any(d in _norm(e) for d in g.DROPPED_TERM_DESCS)]
        if entries:
            kept[key] = entries if len(entries) > 1 else entries[0]
    return (operator, kept)


# A vanilla-shaped party: the culture term to drop, a size chain that opens with
# another multiplier (as the Liberals' does), a one-line term and a comment.
VANILLA = """example_party = {
	color = { 1 2 3 }
	join_weight = {
		value = { value = -5 desc = "base_value" }
		# a comment that stays
		if = {
			limit = { owner = { is_in_geographic_region = geographic_region_north_america } }
			add = {
				value = -10
				desc = "usa_two_party_system"
			}
		}
		if = { limit = { is_powerful = yes } add = { value = 3 desc = "x" } }
		if = {
			limit = { scope:number <= 1 }
			multiply = { value = 2 desc = "from_influential_supporting_member" }
		}
		else_if = {
			limit = { scope:number = 2 }
			multiply = { value = 0.5 desc = "from_two_prior_members" }
		}
		else_if = {
			limit = { scope:number >= 3 }
			multiply = { value = 0 desc = "from_three_or_more_prior_members" }
		}
	}
}
"""


class GeneratorTest(unittest.TestCase):
    def setUp(self):
        self.lines = g.restate(field_lines(VANILLA, "join_weight"), "example_party")
        self.text = "\n".join(self.lines)

    def test_drops_the_culture_term(self):
        self.assertNotIn("usa_two_party_system", self.text)
        self.assertIn("# a comment that stays", self.text)
        self.assertIn('desc = "x"', self.text)

    def test_bonus_goes_ahead_of_the_whole_size_chain(self):
        bonus = self.text.index("te_fptp_major_party_join")
        chain_head = self.text.index("scope:number <= 1")
        self.assertLess(bonus, chain_head)
        self.assertGreater(bonus, self.text.index('desc = "x"'))
        # Nothing between the bonus and the chain's head but the chain's `if`.
        between = self.text[bonus:chain_head]
        self.assertNotIn("else_if", between)

    def test_the_terms_read_no_ruler(self):
        # vanilla_known_bugs.md tags every `Event target link 'ruler' returned an invalid object` in the generated file
        # as vanilla's two council-republic reads, so a ruler read in the mod's terms would log unseen.
        terms = "\n".join(g.major_term_lines("example_party") + g.minor_term_lines("example_party"))
        self.assertNotRegex(terms, r"\bruler\b")
        with open(os.path.join(ROOT, "common", "scripted_triggers", "te_fptp_triggers.txt"), encoding="utf-8-sig") as f:
            self.assertNotRegex(f.read(), r"(?m)^[^#\n]*\bruler\b")

    def test_penalty_comes_last(self):
        self.assertGreater(self.text.index("te_fptp_minor_party_join"), self.text.index("from_three_or_more_prior_members"))
        self.assertIn("te_fptp_major_example_party", self.text)

    def test_dropped_term_in_a_chain_raises(self):
        chained = VANILLA.replace('desc = "x" } }', 'desc = "x" } }\n\t\telse_if = { limit = { always = yes } add = 1 }', 1)
        chained = chained.replace(
            '\t\tif = { limit = { is_powerful = yes }',
            '\t\telse_if = { limit = { is_powerful = yes }',
        )
        with self.assertRaises(ValueError):
            g.restate(field_lines(chained, "join_weight"), "example_party")

    def test_missing_size_chain_raises(self):
        with self.assertRaises(ValueError):
            g.restate(["value = -5"], "example_party")

    def test_build_inject_is_tab_formatted(self):
        sys.path.insert(0, os.path.join(ROOT, "scripts"))
        from format_paradox_tabs import format_text

        block = g.build_inject(VANILLA)
        self.assertTrue(block.startswith("INJECT:example_party = {\n\tjoin_weight = {"))
        self.assertEqual(format_text(block + "\n"), block + "\n")


class CommittedFileTest(unittest.TestCase):
    """What CI can check of the committed file: it is what the generator writes
    from the lines it restates, and those lines match the parties in the
    committed snapshot (vanilla_parsed/common/parties.json, #1164) in values,
    descs, lines dropped or added, and order within one key. The snapshot
    keeps no order across keys, so a restated `else_if` moved under another
    `if`, or a step moved past a term of another key, passes CI; only a
    comparison with the game files catches it (test_matches_the_game_files,
    which skips without them, or the generator's --check). The header's game
    version is held to the snapshot's, so a vanilla patch (which rebuilds the
    snapshot) fails here until the generator is rerun."""

    @classmethod
    def setUpClass(cls):
        with open(COMMITTED, "rb") as file:
            cls.raw = file.read()
        cls.text = cls.raw.decode("utf-8-sig")
        cls.parties = re.findall(r"^INJECT:(\w+) = \{", cls.text, flags=re.MULTILINE)

    def test_one_bom(self):
        self.assertTrue(self.raw.startswith(b"\xef\xbb\xbf"))
        self.assertFalse(self.raw[3:].startswith(b"\xef\xbb\xbf"))

    def test_eleven_vanilla_parties_without_the_revolutionary_party(self):
        self.assertEqual(len(self.parties), 11)
        self.assertNotIn("revolutionary_party", self.parties)

    def test_no_culture_term_left(self):
        body = self.text.split("\n", 8)[-1]  # past the header, which names it
        self.assertNotIn("usa_two_party_system", body)

    def test_header_version_matches_the_snapshot(self):
        with open(os.path.join(ROOT, "vanilla_parsed", "manifest.json"), encoding="utf-8") as file:
            snapshot = json.load(file)["game_version"]
        self.assertEqual(
            self._version(),
            snapshot,
            "zz_te_party_join_weights.txt was restated from another game version: "
            "run scripts/generators/gen_party_join_weights.py on a machine with the game.",
        )

    def _version(self):
        match = re.search(r"^# Restated from vanilla (\S+)\.$", self.text, flags=re.MULTILINE)
        self.assertIsNotNone(match, "the header doesn't name the game version")
        return match.group(1)

    def _vanilla_lines(self, party):
        """The committed block's join_weight lines without the mod's two terms."""
        chunks = g.top_level_chunks(_block("\n".join(_block(self.text, f"INJECT:{party}")), "join_weight"))
        return [
            line
            for chunk in chunks
            if not any("te_fptp_" in line for line in chunk)
            and not chunk[0].startswith("# First Past the Post")
            for line in chunk
        ]

    def test_matches_a_fresh_generation(self):
        """Take the mod's two terms out of each committed block, rebuild a file
        from what is left, and regenerate. This catches a hand edit to the mod's
        terms, their placement or the formatting, and a generator change without
        a rerun. A hand edit to a restated vanilla line is carried into the
        rebuilt file too, so it is test_restated_lines_are_vanillas' and
        test_matches_the_game_files' to catch."""
        with tempfile.TemporaryDirectory() as tmp:
            for party in self.parties:
                vanilla = self._vanilla_lines(party)
                with open(os.path.join(tmp, f"{party}.txt"), "w", encoding="utf-8-sig") as file:
                    file.write(f"{party} = {{\njoin_weight = {{\n" + "\n".join(vanilla) + "\n}\n}\n")
            self.assertEqual(
                g.build_file(tmp, self._version()),
                self.text,
                "zz_te_party_join_weights.txt is stale: run scripts/generators/gen_party_join_weights.py",
            )

    def test_restated_lines_are_vanillas(self):
        """Each block's restated lines parse to the snapshot's join_weight for
        that party, less the terms the generator drops (DROPPED_TERM_DESCS).
        Both sides group a repeated key's entries, so this holds values, descs,
        dropped or added lines and the order within one key, not the order
        across keys (see the class docstring)."""
        with open(SNAPSHOT, encoding="utf-8") as file:
            snapshot = vanilla_parsed.decode(json.load(file))
        self.assertEqual(set(self.parties), set(snapshot) - g.SKIPPED_PARTIES)
        for party in self.parties:
            parser = ParadoxFileParser()
            text = f"{party} = {{\njoin_weight = {{\n" + "\n".join(self._vanilla_lines(party)) + "\n}\n}\n"
            parser.merge_data(parser.parse_object(parser.tokenize("{" + text + "}"))[0])
            with self.subTest(party=party):
                self.assertEqual(
                    _norm(parser.data[party][1]["join_weight"]),
                    _norm(_without_dropped_terms(snapshot[party][1]["join_weight"])),
                    "a restated vanilla line differs from vanilla_parsed/: rerun "
                    "scripts/generators/gen_party_join_weights.py, or undo a hand edit",
                )

    def test_matches_the_game_files(self):
        """A generation from the game's own party files reproduces the committed
        file, cross-key order included, when the game is the header's version.
        Skips without the game (CI)."""
        try:
            directory = g.vanilla_parties_dir()
        except RuntimeError:  # no game path configured on this machine
            directory = None
        if not directory or not os.path.isdir(directory):
            self.skipTest("no game files: the generator's --check covers this on a machine with the game")
        live = vanilla_parsed.live_game_version(g.path_constants.base_game_path)
        if live != self._version():
            self.skipTest(f"the game is {live}, the file was restated from {self._version()}")
        self.assertEqual(
            g.build_file(directory, live),
            self.text,
            "zz_te_party_join_weights.txt differs from a generation from the game files: "
            "run scripts/generators/gen_party_join_weights.py, or undo a hand edit",
        )

    def test_each_party_reads_its_own_mark(self):
        for party in self.parties:
            block = "\n".join(_block(self.text, f"INJECT:{party}"))
            with self.subTest(party=party):
                self.assertEqual(len(re.findall(rf"te_fptp_major_{party}\b", block)), 2)


class PartyCoverageTest(unittest.TestCase):
    """Every party type is marked, cleared and read by the same names."""

    @classmethod
    def setUpClass(cls):
        committed = _read(g.OUTPUT_RELPATH)
        cls.types = set(re.findall(r"^INJECT:(\w+) = \{", committed, flags=re.MULTILINE)) | set(MOD_PARTIES)
        cls.effects = _read("common/scripted_effects/te_fptp_effects.txt")
        cls.triggers = _read("common/scripted_triggers/te_fptp_triggers.txt")

    def _names(self, text, block, pattern):
        return set(re.findall(pattern, "\n".join(_block(text, block))))

    def test_the_mod_parties_exist(self):
        for party in MOD_PARTIES:
            self.assertRegex(_read(f"common/parties/{party}.txt"), rf"(?m)^{party} = \{{")

    def test_mark_dispatch(self):
        self.assertEqual(self._names(self.effects, "te_fptp_mark_major_party", r"is_party_type = (\w+)"), self.types)
        self.assertEqual(
            self._names(self.effects, "te_fptp_mark_major_party", r"set_variable = te_fptp_major_(\w+_party)\b"),
            self.types,
        )

    def test_clear(self):
        self.assertEqual(
            self._names(self.effects, "te_fptp_clear_major_marks", r"remove_variable = te_fptp_major_(\w+_party)\b"),
            self.types,
        )

    def test_is_major_trigger(self):
        lines = _block(self.triggers, "te_fptp_party_is_major")
        pairs = {
            (m.group(1), m.group(2))
            for m in (re.search(r"is_party_type = (\w+) .*has_variable = te_fptp_major_(\w+)", line) for line in lines)
            if m
        }
        self.assertEqual(pairs, {(t, t) for t in self.types})

    def test_history_marks_name_party_types(self):
        history = _read("common/history/extra_history.txt")
        marks = set(re.findall(r"set_variable = te_fptp_major_(\w+_party)\b", history))
        self.assertEqual(marks, {"conservative_party", "liberal_party"})
        self.assertLessEqual(marks, self.types)

    def test_mod_parties_carry_both_terms(self):
        for party in MOD_PARTIES:
            text = "\n".join(_block(_read(f"common/parties/{party}.txt"), "join_weight"))
            with self.subTest(party=party):
                self.assertIn("\n".join(g.major_term_lines(party)[2:]), text)
                self.assertTrue(text.endswith("\n".join(g.minor_term_lines(party)[1:])))
                bonus = text.index("te_fptp_major_party_join")
                self.assertLess(bonus, text.index("from_influential_supporting_member"))


class LawListsTest(unittest.TestCase):
    """The amendment's allowed laws, restated in three triggers, and the
    petition's list of every law in the voting-law group."""

    @staticmethod
    def _laws(text, block, prefix):
        return set(re.findall(rf"{prefix}(law_\w+)", "\n".join(_block(text, block))))

    def test_allowed_laws_restated(self):
        amendment = _read("common/amendments/te_first_past_the_post.txt")
        allowed = set(re.findall(r"law_\w+", "\n".join(_block(amendment, "allowed_laws"))))
        self.assertEqual(len(allowed), 5)
        triggers = _read("common/scripted_triggers/te_fptp_triggers.txt")
        self.assertEqual(self._laws(triggers, "te_fptp_allowed_voting_law", "law_type:"), allowed)
        self.assertEqual(self._laws(triggers, "te_fptp_enacting_allowed_voting_law", "law_type:"), allowed)

    def test_petition_names_every_voting_law(self):
        with open(os.path.join(ROOT, "vanilla_parsed", "common", "laws.json"), encoding="utf-8") as file:
            vanilla = json.load(file)
        group = {name for name, entry in vanilla.items() if "lawgroup_distribution_of_power" in json.dumps(entry)[:400]}
        for name in os.listdir(os.path.join(ROOT, "common", "laws")):
            if name.endswith(".txt"):
                text = _read(os.path.join("common", "laws", name))
                for match in re.finditer(r"(?m)^(law_\w+) = \{\n(?:.*\n){0,3}?\tgroup = lawgroup_distribution_of_power", text):
                    group.add(match.group(1))
        triggers = _read("common/scripted_triggers/amendment_petition_triggers.txt")
        self.assertEqual(self._laws(triggers, "te_ap_enacting_in_distribution_of_power", "law_type:"), group)


if __name__ == "__main__":
    unittest.main()
