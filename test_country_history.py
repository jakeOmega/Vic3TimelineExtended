"""country_history: what each country starts with (#1628), without a game.

The reader runs on text here; the facts about vanilla's real country history
are checked against the committed `vanilla_parsed/history/countries.json`.
"""
import json
import os
import tempfile
import unittest

import country_history as ch
import vanilla_parsed

HISTORY = """
# a comment
COUNTRIES = {
	c:GBR ?= {
		set_next_election_date = 1836.2.1
		ig:ig_intelligentsia ?= {
			add_ruling_interest_group = yes
		}
		ig:ig_devout ?= {
			add_ruling_interest_group = yes
			set_interest_group_name = ig_anglican_church
		}
		set_import_tariff_level = {
			goods = g:grain
			level = high_tariffs
		}
		effect_starting_technology_tier_1_tech = yes
		effect_starting_politics_traditional = yes
		add_technology_researched = labor_movement # a comment
		set_tax_level = medium
		add_taxed_goods = g:liquor
		activate_law = law_type:law_monarchy
		activate_law = law_type:law_wealth_voting
		set_institution_investment_level = {
			institution = institution_schools
			level = 3
		}
		add_journal_entry = { type = je_victoria }
		if = {
			limit = {
				has_dlc_feature = rp1_content
			}
			add_journal_entry = { type = je_aberdeen_act }
		}
		set_immune_to_revolutions = yes
	}
	"c:BIC" ?= {
		set_ruling_interest_groups = { ig_devout ig_landowners }
	}
}
"""


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8-sig") as f:
        f.write(text)


class ReaderTests(unittest.TestCase):
    def setUp(self):
        self.countries = ch.parse_text(HISTORY)

    def test_the_effects_a_question_needs_have_fields(self):
        gbr = self.countries["GBR"]
        self.assertEqual(gbr["laws"], ["law_monarchy", "law_wealth_voting"])
        self.assertEqual(gbr["technologies"], ["labor_movement"])
        self.assertEqual(gbr["tech_tier_effects"], ["effect_starting_technology_tier_1_tech"])
        self.assertEqual(gbr["scripted_effects"], ["effect_starting_politics_traditional"])
        self.assertEqual((gbr["tax_level"], gbr["taxed_goods"]), ("medium", ["liquor"]))
        self.assertEqual(gbr["institutions"], {"institution_schools": "3"})
        self.assertEqual(gbr["ruling_interest_groups"], ["ig_intelligentsia", "ig_devout"])
        self.assertEqual(gbr["journal_entries"], ["je_victoria"])
        self.assertEqual(self.countries["BIC"], {"ruling_interest_groups": ["ig_devout", "ig_landowners"]})

    def test_the_rest_is_kept_as_written(self):
        gbr = self.countries["GBR"]
        self.assertEqual(gbr["conditional"], [{
            "kind": "if", "limit": "has_dlc_feature = rp1_content",
            "effects": ["add_journal_entry = { type = je_aberdeen_act }"],
        }])
        self.assertEqual(gbr["other"], [
            "set_next_election_date = 1836.2.1",
            # The ruling flag is taken; the block's other effect keeps it in `other`.
            "ig:ig_devout ?= { add_ruling_interest_group = yes set_interest_group_name = ig_anglican_church }",
            "set_import_tariff_level = { goods = g:grain level = high_tariffs }",
            # `= yes` but not named like a scripted effect: an engine effect.
            "set_immune_to_revolutions = yes",
        ])

    def test_render_keeps_repeated_keys_and_lists(self):
        parsed = ch.parse_text("COUNTRIES = { c:AAA = { every_scope_state = {"
                               " limit = { is_capital = yes } add_modifier = { name = a }"
                               " add_modifier = { name = b } } set_x = { a b } } }")
        self.assertEqual(parsed["AAA"]["other"], [
            "every_scope_state = { limit = { is_capital = yes } add_modifier = { name = a }"
            " add_modifier = { name = b } }",
            "set_x = { a b }",
        ])

    def test_describe_fills_every_field(self):
        out = ch.describe({"file": "x.txt", "laws": ["law_x"]})
        self.assertEqual(out["laws"], ["law_x"])
        self.assertEqual((out["technologies"], out["conditional"], out["tax_level"], out["institutions"]),
                         ([], [], None, {}))
        self.assertEqual(set(out), {"file", "tax_level", "institutions", *ch.LIST_FIELDS})

    def test_a_mod_file_replaces_a_same_named_vanilla_file(self):
        vanilla = {"gbr - great britain.txt": {"GBR": {"laws": ["law_monarchy"]}},
                   "fra - france.txt": {"FRA": {"laws": ["law_monarchy"]}}}
        mod = {"gbr - great britain.txt": {"GBR": {"laws": ["law_parliamentary_republic"]}},
               "zz_extra.txt": {"FRA": {"technologies": ["te_tech"]}}}
        merged = ch.merge(vanilla, mod)
        self.assertEqual(merged["GBR"], [{"file": "gbr - great britain.txt", "laws": ["law_parliamentary_republic"]}])
        self.assertEqual([r["file"] for r in merged["FRA"]], ["fra - france.txt", "zz_extra.txt"])
        self.assertEqual(ch.summary(merged), {"countries": 2, "with_laws": 2, "with_technologies": 1,
                                              "conditional_blocks": 0})

    def test_load_prefers_game_files_and_falls_back_to_the_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(os.path.join(tmp, "game", ch.REL_DIR, "gbr - great britain.txt"), HISTORY)
            countries, source = ch.load(tmp, None)
            self.assertEqual((source, sorted(countries)), ("game_files", ["BIC", "GBR"]))
            _write(os.path.join(tmp, "launcher/launcher-settings.json"), json.dumps({"rawVersion": "1.0.0"}))
            _write(os.path.join(tmp, "game/common/laws/00.txt"), "law_x = { }\n")
            snap = os.path.join(tmp, "snap")
            vanilla_parsed.build(tmp, snap)
            countries2, source2 = ch.load(None, None, snapshot_dir=snap)
            self.assertEqual((source2, countries2), ("vanilla_parsed", countries))
            with self.assertRaises(FileNotFoundError):
                ch.load(None, None, snapshot_dir=os.path.join(tmp, "nowhere"))


class CommittedSnapshotTests(unittest.TestCase):
    """Vanilla's country history as the repo carries it."""

    @classmethod
    def setUpClass(cls):
        by_file = vanilla_parsed.load_country_history()
        if by_file is None:
            raise unittest.SkipTest("vanilla_parsed/ has no country history")
        cls.countries = ch.merge(by_file)

    def test_one_file_per_tag(self):
        self.assertGreater(len(self.countries), 400)
        for tag, records in self.countries.items():
            self.assertRegex(tag, r"^[A-Z0-9]{3}$")
            self.assertEqual(len(records), 1, tag)

    def test_known_starts(self):
        gbr = self.countries["GBR"][0]
        self.assertIn("law_monarchy", gbr["laws"])
        self.assertIn("law_wealth_voting", gbr["laws"])
        self.assertEqual(gbr["tech_tier_effects"], ["effect_starting_technology_tier_1_tech"])
        self.assertIn("ig_intelligentsia", gbr["ruling_interest_groups"])
        # Every tag gets its starting technology through a tier effect.
        self.assertTrue(all(r[0].get("tech_tier_effects") for r in self.countries.values()))

    def test_manifest_counts_match_the_stored_table(self):
        info = vanilla_parsed.read_manifest(vanilla_parsed.DEFAULT_DIR)["country_history"]
        counts = ch.summary(self.countries)
        self.assertEqual({k: info[k] for k in counts}, counts)


if __name__ == "__main__":
    unittest.main()
