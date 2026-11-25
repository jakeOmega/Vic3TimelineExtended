"""assimilation_cultures_config: the roster of languages and heritage groups the hybrid cultures are made from.

Run: /home/jakef/src/Vic3TimelineExtended/.venv/bin/python -m pytest test_assimilation_cultures_config.py -q
"""

import dataclasses
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "generators"))

import assimilation_cultures_config as cfg  # noqa: E402
import culture_merges_config as cm_cfg  # noqa: E402
import gen_culture_merges as gen  # noqa: E402

cultures = gen.load_vanilla()
plan = gen.build_plan(cultures)
VANILLA_TRAITS = cultures[cm_cfg.TRAITS_KEY]


def body(culture):
    """A vanilla culture's or a merge result's fields."""
    for entry in plan:
        if entry.merge.result == culture:
            return entry.fields
    return gen.culture_fields(cultures[culture])


def heritage_group(culture):
    """The heritage group key (``european``) of a vanilla culture or a merge result."""
    heritage = body(culture)["heritage"]
    heritage = cm_cfg.unwrap(heritage)
    for entry in plan:
        for trait in entry.traits:
            if trait.key == heritage:
                return trait.group.removeprefix("heritage_group_")
    return cm_cfg.trait_group(heritage, cultures).removeprefix("heritage_group_")


def vanilla_culture_groups():
    """Every heritage group a vanilla culture has, as group keys."""
    return {heritage_group(c) for c in cultures if c != cm_cfg.TRAITS_KEY}


class RosterTest(unittest.TestCase):
    def test_the_roster_is_64_languages_and_584_cultures(self):
        self.assertEqual((len(cfg.COUNTED), len(cfg.HAND), len(cfg.merge_languages(plan))), (39, 20, 5))
        self.assertEqual(len(cfg.pairs(cultures, plan)), 584)

    def test_a_pair_is_left_out_only_for_a_languages_one_group(self):
        made = {(p.language.key, p.group.key) for p in cfg.pairs(cultures, plan)}
        for language in cfg.languages(plan):
            own = cfg.language_groups(language, cultures, plan)
            for group in cfg.GROUPS:
                self.assertEqual((language.key, group.key) in made, not (own == {group.key}), (language.key, group.key))

    def test_the_flagship_pairs_exist(self):
        keys = {p.culture for p in cfg.pairs(cultures, plan)}
        self.assertLessEqual({cfg.SENTINEL, "hc_anglophone_european", "hc_guarani_african", "hc_cm_latin_south_asian"}, keys)
        self.assertNotIn("hc_germanophone_european", keys)
        self.assertNotIn("hc_cm_latin_european", keys)

    def test_the_roster_order_is_counted_then_hand_then_merges(self):
        self.assertEqual(cfg.languages(plan), cfg.COUNTED + cfg.HAND + cfg.merge_languages(plan))
        order = [(p.language.key, p.group.key) for p in cfg.pairs(cultures, plan)]
        expected = [(language.key, group.key) for language in cfg.languages(plan) for group in cfg.GROUPS
                    if (language.key, group.key) in set(order)]
        self.assertEqual(order, expected)

    def test_a_pairs_culture_key_is_its_language_and_group(self):
        for pair in cfg.pairs(cultures, plan):
            self.assertEqual(pair.culture, "hc_%s_%s" % (pair.language.key, pair.group.key))

    def test_every_reference_culture_fits_its_row(self):
        # names_from speaks the language; looks_from is in the group, with one ethnicity to lend.
        for language in cfg.languages(plan):
            self.assertEqual(cm_cfg.unwrap(body(language.names_from)["language"]), "language_" + language.key,
                             language)
        for group in cfg.GROUPS:
            self.assertEqual(heritage_group(group.looks_from), group.key, group)
            self.assertEqual(len(gen.ethnicities(body(group.looks_from))), 1, group)

    def test_a_merge_language_takes_its_names_from_the_merges_result(self):
        minted = {trait.key: entry.merge.result for entry in plan for trait in entry.traits if trait.kind == "language"}
        self.assertEqual({"language_" + lang.key: lang.names_from for lang in cfg.merge_languages(plan)}, minted)
        self.assertTrue(all(lang.word is None for lang in cfg.merge_languages(plan)))

    def test_language_groups_reads_vanilla_and_merge_cultures(self):
        def by_key(key):
            return next(lang for lang in cfg.languages(plan) if lang.key == key)
        self.assertEqual(cfg.language_groups(by_key("germanophone"), cultures, plan), {"european"})
        self.assertEqual(cfg.language_groups(by_key("cm_latin"), cultures, plan), {"european"})
        self.assertLessEqual({"european", "african"}, cfg.language_groups(by_key("anglophone"), cultures, plan))

    def test_no_hybrid_key_is_a_vanilla_or_merge_culture(self):
        results = {entry.merge.result for entry in plan}
        for pair in cfg.pairs(cultures, plan):
            self.assertTrue(pair.culture.startswith("hc_"), pair.culture)
            self.assertNotIn(pair.culture, cultures)
            self.assertNotIn(pair.culture, results)
        self.assertFalse([c for c in cultures if c.startswith("hc_")])

    def test_no_promethean_group_and_ten_groups(self):
        keys = [group.key for group in cfg.GROUPS]
        self.assertEqual(len(keys), 10)
        self.assertNotIn("promethean", keys)
        self.assertEqual(set(keys), vanilla_culture_groups() - {"promethean"})
        for key in keys:
            self.assertTrue(any(cm_cfg.trait_group(t, cultures) == "heritage_group_" + key for t in VANILLA_TRAITS), key)

    def test_only_the_african_group_reuses_a_vanilla_heritage(self):
        for group in cfg.GROUPS:
            if group.key == "african":
                self.assertEqual(group.heritage, "heritage_african_diaspora")
                self.assertEqual(cm_cfg.trait_group(group.heritage, cultures), "heritage_group_african")
            else:
                self.assertEqual(group.heritage, "heritage_hc_" + group.key)
                self.assertNotIn(group.heritage, VANILLA_TRAITS)
        self.assertEqual(cfg.minted_heritages(),
                         tuple((g.heritage, g.key) for g in cfg.GROUPS if g.key != "african"))
        self.assertEqual(len(cfg.minted_heritages()), 9)

    def test_the_committed_roster_validates(self):
        cfg.validate(cultures, plan)

    def test_validate_rejects(self):
        # a language vanilla lacks; names_from of another language; a duplicate key; a word holding a quote mark
        greek = cfg.HAND[0]
        self.assertEqual(greek.key, "greek")
        cases = {
            "vanilla lacks the language trait language_not_a_language": cfg.HAND + (cfg.Language("not_a_language", "greek"),),
            "names_from british speaks language_anglophone": (dataclasses.replace(greek, names_from="british"),) + cfg.HAND[1:],
            "language greek: listed twice": cfg.HAND + (greek,),
            "holds a quote mark": (dataclasses.replace(greek, word='Hel"lenic'),) + cfg.HAND[1:],
        }
        for fragment, hand in cases.items():
            with self.subTest(fragment), mock.patch.object(cfg, "HAND", hand):
                with self.assertRaisesRegex(ValueError, fragment):
                    cfg.validate(cultures, plan)
                with self.assertRaises(ValueError):
                    cfg.pairs(cultures, plan)

    def test_validate_rejects_a_bad_group(self):
        african = cfg.GROUPS[0]
        cases = {
            "is not in the group": (dataclasses.replace(african, looks_from="north_german"),) + cfg.GROUPS[1:],
            "listed twice": cfg.GROUPS + (african,),
            "a minted heritage is": (dataclasses.replace(african, heritage="heritage_hc_african_typo"),) + cfg.GROUPS[1:],
            "no vanilla heritage trait": (dataclasses.replace(african, heritage="heritage_arab"),) + cfg.GROUPS[1:],
        }
        for fragment, groups in cases.items():
            with self.subTest(fragment), mock.patch.object(cfg, "GROUPS", groups):
                with self.assertRaisesRegex(ValueError, fragment):
                    cfg.validate(cultures, plan)


if __name__ == "__main__":
    unittest.main()
