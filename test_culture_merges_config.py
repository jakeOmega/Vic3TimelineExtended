"""Tests for the culture merge roster (scripts/generators/culture_merges_config.py).

Vanilla cultures and discrimination traits come straight from the committed
snapshot, not through ModState with the mod's common/ folders: once the
generator writes the mod's `cm_` cultures, a mod-aware load would find them
"already defined" and fail the validator on its own output.
"""

import colorsys
import math
import os
import re
import sys
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "scripts", "generators"))

import culture_merges_config as cfg  # noqa: E402
import vanilla_parsed  # noqa: E402

_SNAPSHOT = None


def _body(value):
    while isinstance(value, (list, tuple)) and len(value) == 2 and value[0] in ("=", "?="):
        value = value[1]
    return value


def snapshot():
    """Vanilla data, loaded once (it takes seconds)."""
    global _SNAPSHOT
    if _SNAPSHOT is None:
        _SNAPSHOT = vanilla_parsed.load(os.path.join(REPO, "vanilla_parsed")).data
    return _SNAPSHOT


def vanilla_cultures():
    """The `cultures` argument of the config API: id -> body, plus "__traits__"."""
    data = snapshot()
    cultures = dict(data["Cultures"])
    cultures["__traits__"] = dict(data["Discrimination Traits"])
    return cultures


def color_rgb(raw):
    """A vanilla culture color (rgb{}, hsv{}, hsv360{} or a list) as an (r, g, b) tuple."""
    raw = _body(raw)
    if isinstance(raw, (list, tuple)):
        return tuple(int(float(v)) for v in raw)
    kind, nums = re.match(r"(\w+)\s*\{([^}]*)\}", raw).groups()
    a, b, c = (float(v) for v in nums.split())
    if kind == "rgb":
        return (int(a), int(b), int(c))
    if kind == "hsv360":
        a /= 360.0
    r, g, bl = colorsys.hsv_to_rgb(a, b, c)
    return (round(r * 255), round(g * 255), round(bl * 255))


def part_cultures(merge):
    return [c for p in merge.core + merge.optional for c in p.cultures]


class RosterTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cultures = vanilla_cultures()

    def test_validate_is_clean(self):
        self.assertEqual(cfg.validate(self.cultures), [])

    def test_german_parts(self):
        m = cfg.merge_by_key("german")
        self.assertEqual([p.cultures for p in m.core], [("north_german",), ("south_german",)])
        self.assertEqual([p.cultures for p in m.optional], [("alemannic",), ("east_german",)])

    def test_tiers(self):
        french = cfg.merge_by_key("french")
        american = cfg.merge_by_key("american")
        self.assertEqual(cfg.derive_tier(french, "occitan", self.cultures), 1)
        self.assertEqual(cfg.derive_tier(french, "catalan", self.cultures), 3)
        self.assertEqual(cfg.derive_tier(american, "afro_american", self.cultures), 2)
        self.assertEqual(cfg.derive_tier(american, "dixie", self.cultures), 1)

    def test_tier_follows_the_slot_not_the_alternative(self):
        # Yankee and cm_american share traits; both fill one slot, so neither
        # makes the other a tier-1 neighbor. Anglophone's core is tier 1b.
        anglo = cfg.merge_by_key("anglophone")
        self.assertEqual(cfg.derive_tier(anglo, "british", self.cultures), 2)
        self.assertEqual(cfg.derive_tier(anglo, "yankee", self.cultures), 2)
        self.assertEqual(cfg.derive_tier(anglo, "cm_american", self.cultures), 2)
        self.assertEqual(cfg.derive_tier(anglo, "afro_american", self.cultures), 2)
        self.assertEqual(cfg.derive_tier(anglo, "australian", self.cultures), 1)

    def test_hand_set_tiers_are_in_the_roster(self):
        # Where vanilla's traits disagree with history the roster sets the tier.
        d = self.cultures
        chinese = cfg.merge_by_key("chinese")
        for culture in ("han", "yue", "hakka", "min"):
            self.assertEqual(cfg.derive_tier(chinese, culture, d), 1, culture)
        japanese = cfg.merge_by_key("japanese")
        for culture in ("japanese", "ryukyuan"):
            self.assertEqual(cfg.derive_tier(japanese, culture, d), 1, culture)
        french = cfg.merge_by_key("french")
        for culture in ("french", "wallonian", "occitan"):
            self.assertEqual(cfg.derive_tier(french, culture, d), 1, culture)
        self.assertEqual(cfg.derive_tier(cfg.merge_by_key("dravidian"), "kannada", d), 1)
        # Without the overrides the traits alone would say otherwise.
        bare = cfg.Merge("x", "han", None, tuple(cfg.Part(p.cultures) for p in chinese.core))
        self.assertEqual(cfg.derive_tier(bare, "yue", d), 3)
        self.assertEqual(cfg.derive_tier(bare, "han", d), 3)

    def test_a_hand_set_core_part_is_still_a_neighbor(self):
        """Derivation measures against every other core slot, hand-set or not.

        Catalan shares Occitan's language but not French's, so with Occitan in
        the core (tier set by hand) it derives tier 2 from Occitan alone; the
        French merge sets Catalan's tier 3 by hand instead.
        """
        d = self.cultures
        p = cfg.Part
        probe = cfg.Merge("x", "french", None, (p(("french",)), p(("occitan",), tier=1)), (p(("catalan",)),))
        self.assertEqual(cfg.derive_tier(probe, "catalan", d), 2)
        # The same with Occitan dropped: nothing shares Catalan's language.
        alone = cfg.Merge("x", "french", None, (p(("french",)), p(("wallonian",))), (p(("catalan",)),))
        self.assertEqual(cfg.derive_tier(alone, "catalan", d), 3)
        # A non-overridden culture beside an overridden one still derives normally.
        beside = cfg.Merge("x", "british", None, (p(("british",)), p(("scottish",), tier=3)), (p(("australian",)),))
        self.assertEqual(cfg.derive_tier(beside, "australian", d), 1)
        self.assertEqual(cfg.derive_tier(beside, "british", d), 1)
        self.assertEqual(cfg.derive_tier(beside, "scottish", d), 3)
        # The roster's own Catalan is set by hand.
        self.assertEqual(cfg.derive_tier(cfg.merge_by_key("french"), "catalan", d), 3)

    def test_core_tiers_match_appendix_a(self):
        """Appendix A's tier column: 1, except 1b (here 2) and tier 2 (here 3)."""
        expected = {"anglophone": 2, "latin": 3, "pan_slavic": 3, "pan_turkic": 3, "pan_malay": 3, "east_african": 3}
        for m in cfg.MERGES:
            tiers = {
                c: cfg.derive_tier(m, c, self.cultures)
                for p in m.core
                for c in p.cultures
            }
            self.assertEqual(max(tiers.values()), expected.get(m.key, 1), (m.key, tiers))

    def test_derived_tier_edges(self):
        d = self.cultures
        self.assertEqual(cfg.derive_tier(cfg.merge_by_key("dravidian"), "telegu", d), 3)
        self.assertEqual(cfg.derive_tier(cfg.merge_by_key("oghuz_turkic"), "turkmen", d), 2)
        self.assertEqual(cfg.derive_tier(cfg.merge_by_key("hindustani"), "bageli", d), 1)
        with self.assertRaises(ValueError):
            cfg.derive_tier(cfg.merge_by_key("german"), "french", d)

    def test_brazil_skips_with_dlc(self):
        self.assertEqual(cfg.merge_by_key("brazilian").skip_if_dlc, "rp1_content")
        self.assertEqual([m.key for m in cfg.MERGES if m.skip_if_dlc], ["brazilian"])

    def test_waits(self):
        waits = {
            (m.key, c): p.wait_for
            for m in cfg.MERGES
            for p in m.core + m.optional
            for c in p.cultures
            if p.wait_for
        }
        self.assertEqual(waits[("american", "dixie")], ("je_acw_reincorporate",))
        self.assertEqual(waits[("american", "afro_american")], ("je_acw_equality",))
        self.assertEqual(waits[("east_slavic", "ukrainian")], ("je_ukraine_cultural_renaissance",))
        self.assertEqual(waits[("east_slavic", "byelorussian")], ("je_belarus_cultural_renaissance",))

    def test_every_wait_names_a_vanilla_journal_entry(self):
        entries = snapshot()["Journal Entries"]
        for m in cfg.MERGES:
            for p in m.core + m.optional:
                for je in p.wait_for:
                    self.assertIn(je, entries, (m.key, je))

    def test_no_wait_on_russification(self):
        for m in cfg.MERGES:
            for p in m.core + m.optional:
                for je in p.wait_for:
                    self.assertNotIn("je_russification", je)

    def test_cross_family_part_rejected(self):
        bad = cfg.Merge("x", "british", None, (cfg.Part(("british",)), cfg.Part(("welsh",))))
        errors = cfg.validate(self.cultures, cfg.MERGES + (bad,))
        self.assertTrue(any("welsh" in e for e in errors), errors)

    def test_validate_catches_each_kind_of_mistake(self):
        d = self.cultures
        p = cfg.Part
        german = cfg.merge_by_key("german")

        def errors(merge):
            return cfg.validate(d, tuple(m for m in cfg.MERGES if m.key != merge.key) + (merge,))

        def replaced(**changes):
            import dataclasses

            return dataclasses.replace(german, **changes)

        def has(merge, *phrases):
            found = errors(merge)
            self.assertTrue(any(all(ph in e for ph in phrases) for e in found), (phrases, found))

        has(replaced(core=(p(("north_german",)), p(("not_a_culture",)))), "not_a_culture", "not a vanilla culture")
        has(replaced(optional=(p(("cm_nowhere",)),)), "cm_nowhere", "not a vanilla culture or a merge result")
        has(replaced(optional=(p(("south_german",)),)), "south_german", "two slots")
        has(replaced(components=("nowhere",)), "nowhere", "not a merge key")
        has(replaced(core=(p(("cm_german",)), p(("south_german",)))), "cm_german", "own result")
        has(replaced(optional=(p(("french",)),)), "french", "cross-family")
        has(replaced(core=(p(("north_german",), tier=4), p(("south_german",)))), "north_german", "tier 4")
        # A new culture whose id vanilla already defines.
        clash = cfg.NewCulture("Clash", (1, 2, 3))
        has(replaced(result="north_german", new=clash), "vanilla already defines north_german")
        # An absorb merge whose result isn't its first core part.
        has(replaced(new=None), "absorb merge's result")
        # The same key twice.
        twice = cfg.validate(d, cfg.MERGES + (german,))
        self.assertTrue(any("used twice" in e for e in twice), twice)

    def test_skipped_merges_absent(self):
        keys = {m.key for m in cfg.MERGES}
        self.assertFalse(keys & {"pan_germanic", "pan_bantu"})

    def test_roster_is_appendix_a(self):
        self.assertEqual(
            [m.key for m in cfg.MERGES],
            [
                "german", "italian", "scandinavian", "east_slavic", "yugoslav", "czechoslovak", "hungarian",
                "dutch", "finnish", "french", "british", "american", "anglophone", "brazilian", "platine",
                "andean", "gran_colombian", "chinese", "japanese", "arab", "persian", "oghuz_turkic",
                "hindustani", "dravidian", "indonesian", "filipino", "nguni", "latin", "pan_slavic",
                "pan_turkic", "pan_malay", "east_african",
            ],
        )

    def test_overlapping_parts_are_exclusive(self):
        results = {m.result for m in cfg.MERGES if m.new is not None}
        for m in cfg.MERGES:
            cultures = part_cultures(m)
            self.assertEqual(len(cultures), len(set(cultures)), m.key)
            for c in cultures:
                if c.startswith("cm_"):
                    self.assertIn(c, results, (m.key, c))
                    self.assertNotEqual(c, m.result, (m.key, c))

    def test_results(self):
        keys = set()
        for m in cfg.MERGES:
            self.assertNotIn(m.key, keys)
            keys.add(m.key)
            if m.new is None:
                # Absorb: the result is the first core part, an existing culture.
                self.assertEqual(m.result, m.core[0].cultures[0], m.key)
                self.assertIn(m.result, self.cultures, m.key)
            else:
                self.assertEqual(m.result, "cm_" + m.key)
                self.assertNotIn(m.result, self.cultures, m.key)
                self.assertTrue(m.new.name, m.key)
                self.assertEqual(len(m.new.color), 3, m.key)
                self.assertTrue(all(isinstance(v, int) and 0 <= v <= 255 for v in m.new.color), m.key)
        self.assertEqual(cfg.merge_by_key("east_slavic").result, "cm_east_slavic")
        self.assertEqual(cfg.merge_by_key("east_slavic").new.name, "East Slavic")
        self.assertEqual(cfg.merge_by_key("anglophone").new.name, "Anglophone")
        self.assertEqual(cfg.merge_by_key("latin").new.name, "Latin")
        self.assertEqual(cfg.merge_by_key("chinese").result, "han")

    def test_every_part_is_a_vanilla_culture_or_a_result(self):
        results = {m.result for m in cfg.MERGES if m.new is not None}
        for m in cfg.MERGES:
            for c in part_cultures(m):
                self.assertTrue(c in self.cultures or c in results, (m.key, c))

    def test_new_culture_colors_are_distinct(self):
        colors = {m.result: m.new.color for m in cfg.MERGES if m.new is not None}

        def rgb(culture):
            return colors[culture] if culture in colors else color_rgb(self.cultures[culture][1]["color"])

        for m in cfg.MERGES:
            if m.new is None:
                continue
            for c in part_cultures(m):
                self.assertGreaterEqual(math.dist(m.new.color, rgb(c)), 25, (m.key, c))
        names = sorted(colors)
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                self.assertGreaterEqual(math.dist(colors[a], colors[b]), 25, (a, b))

    def test_new_culture_names_do_not_repeat_a_vanilla_name(self):
        """Two cultures called Nguni in one pop list would read as a bug."""
        loc = vanilla_parsed.load(os.path.join(REPO, "vanilla_parsed")).localization
        vanilla_names = {loc[c] for c in self.cultures if c != "__traits__" and isinstance(loc.get(c), str)}
        self.assertIn("Nguni", vanilla_names)  # the check below can fail
        for m in cfg.MERGES:
            if m.new is not None:
                self.assertNotIn(m.new.name, vanilla_names, m.key)

    def test_components(self):
        """A tier-3 merge lists the merges whose results are among its core parts."""
        for m in cfg.MERGES:
            core = {c for p in m.core for c in p.cultures}
            for key in m.components:
                self.assertIn(cfg.merge_by_key(key).result, core, (m.key, key))
            tier3 = max(cfg.derive_tier(m, c, self.cultures) for p in m.core for c in p.cultures) == 3
            # East African has no tier-1 merge to wait for (the owner's ruling).
            self.assertEqual(bool(m.components), tier3 and m.key != "east_african", m.key)
        self.assertEqual(cfg.merge_by_key("latin").components, ("french", "italian"))
        self.assertEqual(cfg.merge_by_key("pan_slavic").components, ("east_slavic", "czechoslovak", "yugoslav"))
        self.assertEqual(cfg.merge_by_key("pan_turkic").components, ("oghuz_turkic",))
        self.assertEqual(cfg.merge_by_key("pan_malay").components, ("indonesian", "filipino"))
        self.assertEqual(cfg.merge_by_key("east_african").components, ())

    def test_brief_roster_lines(self):
        def cultures(parts):
            return [p.cultures for p in parts]

        french = cfg.merge_by_key("french")
        self.assertEqual(cultures(french.core), [("french",), ("wallonian",), ("occitan",)])
        self.assertEqual(cultures(french.optional), [("catalan",)])
        american = cfg.merge_by_key("american")
        self.assertEqual(cultures(american.core), [("yankee",), ("dixie",)])
        self.assertEqual(cultures(american.optional), [("afro_american",)])
        anglo = cfg.merge_by_key("anglophone")
        self.assertEqual(cultures(anglo.core), [("british",), ("yankee", "cm_american")])
        self.assertEqual(
            cultures(anglo.optional),
            [("anglo_canadian",), ("australian",), ("scottish",), ("dixie",), ("afro_american",)],
        )
        latin = cfg.merge_by_key("latin")
        self.assertEqual(cultures(latin.core), [("french",), ("cm_italian",), ("spanish",), ("portuguese",)])
        self.assertEqual(
            cultures(latin.optional),
            [("romanian",), ("platinean",), ("argentine",), ("uruguayan",), ("chilean",)],
        )
        # Filipino drops the cross-family Hispanophone and Mestizo cultures.
        filipino = cfg.merge_by_key("filipino")
        self.assertEqual(filipino.optional, ())
        self.assertNotIn("filipino_mestizo", part_cultures(filipino))
        # Turkmen is optional in Oghuz Turkic.
        oghuz = cfg.merge_by_key("oghuz_turkic")
        self.assertEqual(cultures(oghuz.core), [("turkish",), ("azerbaijani",)])
        self.assertEqual(cultures(oghuz.optional), [("turkmen",)])

    def test_frozen(self):
        import dataclasses

        part = cfg.Part(("north_german",))
        with self.assertRaises(dataclasses.FrozenInstanceError):
            part.tier = 2
        self.assertEqual(part.tier, None)
        self.assertEqual(part.wait_for, ())
        with self.assertRaises(KeyError):
            cfg.merge_by_key("no_such_merge")


if __name__ == "__main__":
    unittest.main()
