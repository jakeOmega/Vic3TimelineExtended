"""Political parties in ModState and the server (#1164): the type's
registration, an injected join_weight replacing the field, /raw/Party/<key>,
and GET /parties. No game install needed."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import mod_state_server as mss
import party_catalog
import vanilla_parsed
from mod_state import VANILLA_COMMON_DIRS, ModState
from paradox_file_parser import ParadoxFileParser

REPO = Path(__file__).resolve().parent

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
        self.assertEqual(len(vanilla), 12)
        self.assertIn("social_democrat_party", vanilla)  # in social_democrats_party.txt
        self.assertIn("revolutionary_party", vanilla)

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

    def test_committed_injects_replace_the_snapshots_fields(self):
        state, _ = _committed_state()
        merged = state.get_data("Parties")
        text = (REPO / "common" / "parties" / "zz_te_party_join_weights.txt").read_text(encoding="utf-8-sig")
        injects = {party_catalog.split_directive(k)[1]: v
                   for k, v in party_catalog.raw_entries(text)
                   if party_catalog.split_directive(k)[0] == "INJECT"}
        self.assertEqual(len(injects), 11)
        normalizer = ParadoxFileParser()
        for party, block in injects.items():
            with self.subTest(party=party):
                restated = normalizer._normalize_fully(party_catalog.field(block, "join_weight"))
                self.assertEqual(_norm(merged[party][1]["join_weight"]), _norm(restated))
                self.assertNotIn("usa_two_party_system", _norm(merged[party][1]["join_weight"]))


class PartiesEndpointTests(unittest.TestCase):
    def setUp(self):
        self.tmp, self.root, self.state = _state(VANILLA, INJECT)
        self.addCleanup(self.tmp.cleanup)
        self.patch(ms=self.state, mod_path=str(self.root / "mod"), base_game_path=str(self.root / "game"),
                   mod_paths={"Parties": str(self.root / "mod" / "common" / "parties")},
                   base_game_paths={"Parties": str(self.root / "game" / "common" / "parties")},
                   _vanilla_source={"kind": "game_files"})
        self.handler = object.__new__(mss.ModStateHandler)

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

    def test_raw_party_alias(self):
        status, body = self.request("/raw/Party/example_party")
        self.assertEqual(status, 200)
        self.assertIn("join_weight", json.dumps(body))
        self.assertNotIn("usa_two_party_system", json.dumps(body))

    def test_committed_parties(self):
        state, mod_dirs = _committed_state()
        self.patch(ms=state, mod_path=str(REPO), mod_paths=mod_dirs, _vanilla_source={"kind": "vanilla_parsed"})
        rows = self.rows()
        self.assertEqual(len(rows), 15)
        self.assertEqual({k for k, r in rows.items() if r["source"] == "mod"},
                         {"green_party", "populist_party", "technocratic_party"})
        self.assertEqual({k for k, r in rows.items() if r["source"] == "vanilla"}, {"revolutionary_party"})
        fptp = set(self.rows("?desc=te_fptp_major_party_join"))
        self.assertEqual(fptp, set(rows) - {"revolutionary_party"})
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
