"""Political parties in ModState and the server (#1164): the type's
registration, an injected join_weight replacing the field, /raw/Party/<key>,
and GET /parties; the entity-path tables every type comes from, a party's icon
in /placeholder-icons and /duplicate-images, and /gui/render-paths/Parties
(#1183). No game install needed."""
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import mod_state_script
import mod_state_server as mss
import party_catalog
import vanilla_parsed
from mod_state import MOD_ONLY_DIRS, VANILLA_COMMON_DIRS, ModState, entity_paths
from paradox_file_parser import ParadoxFileParser

REPO = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO / "scripts" / "generators"))
import gen_party_join_weights  # noqa: E402

# Vanilla-shaped: a base value, a branch with two descs (one repeated), a
# desc-less step, a culture term, and an if/else_if pair whose else_if the
# merged AST would list after every if.
VANILLA = """
example_party = {
	color = { 1 2 3 }
	name = { desc = party_example }
	join_weight = {
		value = { value = -5 desc = "base_value" }
		if = {
			limit = { is_powerful = yes }
			if = { limit = { has_ideology = ideology:ideology_a } add = { value = 3 desc = "from_a" } }
			if = { limit = { has_ideology = ideology:ideology_b } add = { value = 2 desc = "from_a" } }
			else = { add = { value = 1 desc = "from_b" } }
		}
		if = {
			limit = { owner = { is_in_geographic_region = geographic_region_north_america } }
			add = { value = -10 desc = "usa_two_party_system" }
		}
		if = { limit = { scope:number <= 1 } multiply = { value = 2 desc = "from_one_prior_member" } }
		else_if = { limit = { scope:number = 2 } multiply = { value = 0.5 desc = "from_two_prior_members" } }
		if = { limit = { always = yes } add = 1 }
	}
}
vanilla_only_party = {
	color = { 4 5 6 }
	join_weight = {
		value = 0
		if = { limit = { is_revolutionary = yes } add = { value = 10000 desc = "base_value" } }
	}
}
"""

# Restates vanilla without the culture term and adds a term at the end, as
# gen_party_join_weights.py does.
INJECT = """
INJECT:example_party = {
	join_weight = {
		value = { value = -5 desc = "base_value" }
		if = {
			limit = { is_powerful = yes }
			if = { limit = { has_ideology = ideology:ideology_a } add = { value = 3 desc = "from_a" } }
			if = { limit = { has_ideology = ideology:ideology_b } add = { value = 2 desc = "from_a" } }
			else = { add = { value = 1 desc = "from_b" } }
		}
		if = { limit = { scope:number <= 1 } multiply = { value = 2 desc = "from_one_prior_member" } }
		else_if = { limit = { scope:number = 2 } multiply = { value = 0.5 desc = "from_two_prior_members" } }
		if = { limit = { always = yes } add = 1 }
		if = { limit = { owner = { has_variable = x } } add = { value = -20 desc = "mod_penalty" } }
	}
}
mod_party = {
	color = { 7 8 9 }
	join_weight = {
		value = { value = -5 desc = "base_value" }
		if = { limit = { is_powerful = yes } add = { value = 5 desc = "mod_penalty" } }
	}
}
"""

# No `value` line on either side: the one shape ModState merges instead of
# replacing (ParadoxFileParser._is_script_value_field needs a `value` line on
# one side). No vanilla or mod party is shaped like this.
NO_VALUE_VANILLA = """
plain_party = {
	join_weight = {
		add = { value = 2 desc = "from_x" }
	}
}
"""
NO_VALUE_INJECT = """
INJECT:plain_party = {
	join_weight = {
		add = { value = 1 desc = "from_z" }
	}
}
"""

EXPECTED_EXAMPLE_TERMS = [
    "base_value", "from_a", "from_b", "from_one_prior_member",
    "from_two_prior_members", "if = {...}", "mod_penalty",
]


def _norm(value):
    return json.dumps(vanilla_parsed.encode(value), sort_keys=True)


def _state(vanilla_text, mod_text):
    tmp = tempfile.TemporaryDirectory()
    root = Path(tmp.name)
    for side, text in (("game", vanilla_text), ("mod", mod_text)):
        (root / side / "common" / "parties").mkdir(parents=True)
        (root / side / "common" / "parties" / "00_parties.txt").write_text(text, encoding="utf-8")
    state = ModState({"Parties": str(root / "game" / "common" / "parties")},
                     {"Parties": str(root / "mod" / "common" / "parties")})
    return tmp, root, state


def _committed_state():
    """The committed vanilla snapshot's parties under the mod's own files."""
    with open(REPO / "vanilla_parsed" / "common" / "parties.json", encoding="utf-8") as file:
        vanilla = vanilla_parsed.decode(json.load(file))
    mod_dirs = {"Parties": str(REPO / "common" / "parties")}
    return ModState({"Parties": "/nonexistent"}, mod_dirs, vanilla_data={"Parties": vanilla}), mod_dirs


class RegistrationTests(unittest.TestCase):
    def test_parties_in_both_path_tables(self):
        self.assertEqual(VANILLA_COMMON_DIRS["Parties"], "parties")
        self.assertTrue(mss.base_game_paths["Parties"].endswith("parties"))
        self.assertTrue(mss.mod_paths["Parties"].endswith("parties"))

    def test_snapshot_holds_every_vanilla_party(self):
        manifest = vanilla_parsed.read_manifest(str(REPO / "vanilla_parsed"))
        self.assertEqual(manifest["entity_types"]["Parties"]["file"], "common/parties.json")
        state, _ = _committed_state()
        vanilla = state.base_parsers["Parties"].data
        self.assertEqual(len(vanilla), manifest["entity_types"]["Parties"]["entities"])
        self.assertIn("social_democrat_party", vanilla)  # in social_democrats_party.txt
        self.assertIn("revolutionary_party", vanilla)

    def test_path_tables_cover_every_type(self):
        # Both modules build their tables with mod_state.entity_paths (#1183):
        # mod_state_script's once listed 26 of the types by hand, so its
        # standalone users (mod_structure_audit's CLI, gen_event_inventory)
        # read no parties, journal entries or events.
        self.assertFalse(set(VANILLA_COMMON_DIRS) & set(MOD_ONLY_DIRS))
        for module in (mss, mod_state_script):
            with self.subTest(module=module.__name__):
                self.assertEqual(set(module.base_game_paths), set(VANILLA_COMMON_DIRS))
                self.assertEqual(set(module.mod_paths), set(VANILLA_COMMON_DIRS) | set(MOD_ONLY_DIRS))
        self.assertEqual(mod_state_script.base_game_paths, mss.base_game_paths)
        self.assertEqual(mod_state_script.mod_paths, mss.mod_paths)

    def test_entity_paths_roots(self):
        base, mod = entity_paths("/g", "/m")
        self.assertEqual(base["Technologies"], os.path.join("/g", "game", "common", "technology", "technologies"))
        self.assertEqual(mod["Parties"], os.path.join("/m", "common", "parties"))
        self.assertEqual(mod["On Actions"], os.path.join("/m", "common", "on_actions"))
        self.assertEqual(mod["Events"], os.path.join("/m", "events"))
        self.assertNotIn("Events", base)

    def test_raw_type_name_resolves_singular_and_plural(self):
        known = list(VANILLA_COMMON_DIRS)
        for name in ("Parties", "parties", "Party", "party"):
            with self.subTest(name=name):
                self.assertEqual(mss._resolve_entity_type(name, known), "Parties")


class InjectReplacesJoinWeightTests(unittest.TestCase):
    """An injected join_weight replaces the party's field, as the engine does
    (read in game 2026-10-25): ModState treats it as a script-value field
    (ParadoxFileParser._is_script_value_field), never merging or summing it."""

    def test_restated_block_replaces_vanillas(self):
        tmp, _root, state = _state(VANILLA, INJECT)
        self.addCleanup(tmp.cleanup)
        merged = state.get_data("Parties")["example_party"][1]
        block = dict(party_catalog.raw_entries(INJECT))["INJECT:example_party"]
        restated = ParadoxFileParser()._normalize_fully(party_catalog.field(block, "join_weight"))
        self.assertEqual(_norm(merged["join_weight"]), _norm(restated))
        text = _norm(merged["join_weight"])
        self.assertNotIn("usa_two_party_system", text)
        self.assertIn("mod_penalty", text)
        # Merged, the two `value = -5` lines would have summed.
        self.assertEqual(merged["join_weight"][1]["value"][1]["value"], ("=", "-5"))
        self.assertEqual(merged["color"], state.base_parsers["Parties"].data["example_party"][1]["color"])

    def test_the_in_game_shape_drops_vanillas_lines(self):
        # The 2026-10-25 read: an INJECT with one `add` and no `value` line left
        # the breakdown with that line alone, no Base Value; the name and
        # colour stayed vanilla's. The vanilla side's `value` line is what marks
        # the field as a script value here.
        tmp, _root, state = _state(VANILLA, 'INJECT:example_party = {\n'
                                            '\tjoin_weight = { add = { value = 1 desc = "probe" } }\n}\n')
        self.addCleanup(tmp.cleanup)
        merged = state.get_data("Parties")["example_party"][1]
        self.assertEqual(set(merged["join_weight"][1]), {"add"})
        self.assertNotIn("base_value", _norm(merged["join_weight"]))
        self.assertIn("name", merged)
        self.assertIn("color", merged)

    def test_a_value_line_on_the_injected_side_alone_replaces(self):
        tmp, _root, state = _state(NO_VALUE_VANILLA, NO_VALUE_INJECT.replace(
            'add = { value = 1 desc = "from_z" }', 'value = 5\n\t\tadd = { value = 1 desc = "from_z" }'))
        self.addCleanup(tmp.cleanup)
        merged = _norm(state.get_data("Parties")["plain_party"][1]["join_weight"])
        self.assertNotIn("from_x", merged)
        self.assertIn("from_z", merged)

    def test_no_value_line_on_either_side_merges(self):
        # The gap the rule leaves: the two `add` blocks merge like a modifier
        # block, values summed (2 + 1) under the injected desc, where the
        # engine would read the injected block alone (1).
        tmp, _root, state = _state(NO_VALUE_VANILLA, NO_VALUE_INJECT)
        self.addCleanup(tmp.cleanup)
        merged = state.get_data("Parties")["plain_party"][1]["join_weight"][1]
        self.assertEqual(merged["add"][1]["value"], ("=", "3"))
        self.assertEqual(merged["add"][1]["desc"], ("=", '"from_z"'))

    def test_nested_replace_and_inject_of_the_field(self):
        replace = 'INJECT:example_party = {\n\tREPLACE:join_weight = { add = { value = 1 desc = "probe" } }\n}\n'
        tmp, _root, state = _state(VANILLA, replace)
        self.addCleanup(tmp.cleanup)
        self.assertEqual(set(state.get_data("Parties")["example_party"][1]["join_weight"][1]), {"add"})
        inject = 'INJECT:example_party = {\n\tINJECT:join_weight = { add = { value = 1 desc = "probe" } }\n}\n'
        tmp, _root, state = _state(VANILLA, inject)
        self.addCleanup(tmp.cleanup)
        merged = _norm(state.get_data("Parties")["example_party"][1]["join_weight"])
        self.assertIn("probe", merged)
        self.assertIn("base_value", merged)

    def test_committed_injects_replace_the_snapshots_fields(self):
        state, _ = _committed_state()
        merged = state.get_data("Parties")
        text = (REPO / "common" / "parties" / "zz_te_party_join_weights.txt").read_text(encoding="utf-8-sig")
        injects = {party_catalog.split_directive(k)[1]: v
                   for k, v in party_catalog.raw_entries(text)
                   if party_catalog.split_directive(k)[0] == "INJECT"}
        vanilla = state.base_parsers["Parties"].data
        self.assertEqual(set(injects), set(vanilla) - gen_party_join_weights.SKIPPED_PARTIES)
        normalizer = ParadoxFileParser()
        for party, block in injects.items():
            with self.subTest(party=party):
                restated = normalizer._normalize_fully(party_catalog.field(block, "join_weight"))
                self.assertEqual(_norm(merged[party][1]["join_weight"]), _norm(restated))
                self.assertNotIn("usa_two_party_system", _norm(merged[party][1]["join_weight"]))


class PartiesEndpointTests(unittest.TestCase):
    def setUp(self):
        self.use(VANILLA, INJECT)
        self.handler = object.__new__(mss.ModStateHandler)

    def use(self, vanilla_text, mod_text):
        """Serve a ModState of these two party files, read from the game files."""
        tmp, self.root, self.state = _state(vanilla_text, mod_text)
        self.addCleanup(tmp.cleanup)
        self.patch(ms=self.state, mod_path=str(self.root / "mod"), base_game_path=str(self.root / "game"),
                   mod_paths={"Parties": str(self.root / "mod" / "common" / "parties")},
                   base_game_paths={"Parties": str(self.root / "game" / "common" / "parties")},
                   _vanilla_source={"kind": "game_files"}, _party_catalog_cache=None)

    def patch(self, **values):
        patcher = mock.patch.multiple(mss, **values)
        patcher.start()
        self.addCleanup(patcher.stop)

    def request(self, path):
        self.handler.path = path
        self.handler._local_request_ok = mock.Mock(return_value=True)
        self.handler._respond_json = mock.Mock()
        self.handler.do_GET()
        args = self.handler._respond_json.call_args.args
        json.dumps(args[0])
        return (args[1] if len(args) > 1 else 200), args[0]

    def rows(self, query=""):
        status, body = self.request("/parties" + query)
        self.assertEqual(status, 200)
        return {row["key"]: row for row in body}

    def test_sources_and_files(self):
        rows = self.rows()
        self.assertEqual(list(rows), ["example_party", "mod_party", "vanilla_only_party"])
        self.assertEqual({k: r["source"] for k, r in rows.items()},
                         {"example_party": "both", "mod_party": "mod", "vanilla_only_party": "vanilla"})
        inject = {"source": "mod", "file": "common/parties/00_parties.txt", "directive": "INJECT"}
        self.assertEqual(rows["example_party"]["files"],
                         [{"source": "vanilla", "file": "common/parties/00_parties.txt"}, inject])
        self.assertEqual(rows["example_party"]["join_weight_file"], inject)
        self.assertNotIn("terms", rows["example_party"])

    def test_terms_in_source_order(self):
        example = self.rows()["example_party"]
        self.assertEqual(example["terms_order"], "source")
        # The else_if stays beside its if, ahead of the later ifs; a branch's
        # two descs come once each; the desc-less if is marked.
        self.assertEqual(example["join_weight_terms"], EXPECTED_EXAMPLE_TERMS)
        self.assertEqual(self.rows()["vanilla_only_party"]["join_weight_terms"], ["value = 0", "base_value"])

    def test_merged_ast_order_differs(self):
        # Why the order comes from the text: the merged entity groups by key.
        merged = self.state.get_data("Parties")["example_party"]
        by_key = party_catalog.flat_terms(party_catalog.terms(party_catalog.field(merged, "join_weight")))
        self.assertNotEqual(by_key, EXPECTED_EXAMPLE_TERMS)
        self.assertEqual(sorted(by_key), sorted(EXPECTED_EXAMPLE_TERMS))

    def test_desc_filter_and_detail(self):
        self.assertEqual(list(self.rows("?desc=mod_penalty")), ["example_party", "mod_party"])
        self.assertEqual(self.rows("?desc=usa_two_party_system"), {})
        status, detail = self.request("/parties/vanilla_only_party")
        self.assertEqual(status, 200)
        self.assertEqual(detail["terms"], [
            {"key": "value", "descs": [], "value": "0"},
            {"key": "if", "descs": ["base_value"]},
        ])
        self.assertEqual(self.request("/parties/no_such_party")[0], 404)

    def test_snapshot_vanilla(self):
        snapshot = ModState({"Parties": "/nonexistent"}, {"Parties": str(self.root / "mod" / "common" / "parties")},
                            vanilla_data={"Parties": self.state.base_parsers["Parties"].data})
        self.patch(ms=snapshot, _vanilla_source={"kind": "vanilla_parsed"})
        rows = self.rows()
        self.assertEqual(rows["vanilla_only_party"]["files"],
                         [{"source": "vanilla", "file": "vanilla_parsed/common/parties.json"}])
        # No source text for a vanilla-only party: the merged entity's order.
        self.assertEqual(rows["vanilla_only_party"]["terms_order"], "by_key")
        # The mod's INJECT is on disk, so its order holds.
        self.assertEqual(rows["example_party"]["terms_order"], "source")
        self.assertEqual(rows["example_party"]["join_weight_terms"], EXPECTED_EXAMPLE_TERMS)

    def test_nested_replace_of_the_field_carries_it(self):
        self.use(VANILLA, (
            "INJECT:example_party = {\n\tREPLACE:join_weight = {\n"
            '\t\tif = { limit = { always = yes } add = { value = 1 desc = "a" } }\n'
            '\t\telse_if = { limit = { always = no } add = { value = 2 desc = "b" } }\n'
            '\t\tif = { limit = { always = yes } add = { value = 3 desc = "c" } }\n'
            "\t}\n}\n"))
        row = self.rows()["example_party"]
        self.assertEqual(row["join_weight_file"],
                         {"source": "mod", "file": "common/parties/00_parties.txt", "directive": "INJECT"})
        self.assertEqual((row["terms_order"], row["join_weight_terms"]), ("source", ["a", "b", "c"]))

    def test_no_carrier_when_no_file_reproduces_the_field(self):
        # An INJECT:join_weight merges into vanilla's field, and so does an
        # injected block when neither side has a `value` line: no one file
        # holds the merged field, so the row names none and falls back.
        for vanilla_text, mod_text, key in (
            (VANILLA, 'INJECT:example_party = {\n\tINJECT:join_weight = { add = { value = 1 desc = "probe" } }\n}\n',
             "example_party"),
            (NO_VALUE_VANILLA, NO_VALUE_INJECT, "plain_party"),
        ):
            with self.subTest(party=key):
                self.use(vanilla_text, mod_text)
                row = self.rows()[key]
                self.assertIsNone(row["join_weight_file"])
                self.assertEqual(row["terms_order"], "by_key")
                self.assertEqual(len(row["files"]), 2)

    def test_rows_are_cached_until_the_state_changes(self):
        with mock.patch.object(party_catalog, "directory_sites", wraps=party_catalog.directory_sites) as spy:
            self.rows()
            self.request("/parties/example_party")
            self.assertEqual(spy.call_count, 2)  # vanilla's files and the mod's, once
            self.use(VANILLA, INJECT)
            self.rows()
            self.assertEqual(spy.call_count, 4)
        # A detail request hands out a copy, not the cached row.
        self.request("/parties/example_party")[1]["terms"].clear()
        self.assertTrue(self.request("/parties/example_party")[1]["terms"])

    def test_raw_party_alias(self):
        status, body = self.request("/raw/Party/example_party")
        self.assertEqual(status, 200)
        self.assertIn("join_weight", json.dumps(body))
        self.assertNotIn("usa_two_party_system", json.dumps(body))

    def test_committed_parties(self):
        state, mod_dirs = _committed_state()
        self.patch(ms=state, mod_path=str(REPO), mod_paths=mod_dirs, _vanilla_source={"kind": "vanilla_parsed"})
        rows = self.rows()
        vanilla = set(state.base_parsers["Parties"].data)
        defined, named = set(), set()
        for path in sorted((REPO / "common" / "parties").glob("*.txt")):
            for raw_key, _value in party_catalog.raw_entries(path.read_text(encoding="utf-8-sig")):
                directive, key = party_catalog.split_directive(raw_key)
                named.add(key)
                if directive is None:
                    defined.add(key)
        self.assertEqual(set(rows), vanilla | defined)
        self.assertEqual({k for k, r in rows.items() if r["source"] == "mod"}, defined - vanilla)
        self.assertLessEqual({"green_party", "populist_party", "technocratic_party"}, defined - vanilla)
        self.assertEqual({k for k, r in rows.items() if r["source"] == "vanilla"}, vanilla - named)
        fptp = set(self.rows("?desc=te_fptp_major_party_join"))
        self.assertEqual(fptp, set(rows) - gen_party_join_weights.SKIPPED_PARTIES)
        self.assertEqual(self.rows("?desc=usa_two_party_system"), {})
        for key in fptp:
            terms = rows[key]["join_weight_terms"]
            with self.subTest(party=key):
                self.assertEqual(rows[key]["terms_order"], "source")
                self.assertEqual(terms[0], "base_value")
                self.assertEqual(terms[-1], "te_fptp_minor_party_join")
                self.assertEqual(terms[terms.index("te_fptp_major_party_join") + 1],
                                 "from_influential_supporting_member")


if __name__ == "__main__":
    unittest.main()
