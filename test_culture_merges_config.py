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
        # The German and Yugoslav parts don't wait: their fervor follows the merged culture's (test_culture_merge_fervor).
        self.assertEqual(sorted(k for k in waits if k[0] in ("german", "yugoslav")), [])

    def test_the_german_and_yugoslav_parts_wait_on_nothing(self):
        # R37's waits on je_german_unification_idea and je_the_balkan_league gave way to the fervor copy (owner,
        # 2026-11-07): those entries read the parts' fervor, and a switched part's follows the merged culture's.
        for key in ("german", "yugoslav"):
            merge = cfg.merge_by_key(key)
            self.assertEqual([c for p in merge.core + merge.optional for c in p.cultures if p.wait_for], [], key)

    def test_the_guides_appendix_lists_exactly_the_configs_waits(self):
        # docs/player_guide/20-appendix-reference-lists.md, the culture merge table, in roster order: a row names a wait
        # exactly when one of the merge's parts has one (R41 dropped German's and Yugoslav's and left the rows stale).
        text = open(os.path.join(REPO, "docs/player_guide/20-appendix-reference-lists.md"), encoding="utf-8").read()
        table = text[text.index("| Merge | Core cultures | Optional cultures | Tier | Waits and requirements |"):]
        rows = [line for line in table.split("\n")[2:] if line.startswith("|")][: len(cfg.MERGES)]
        self.assertEqual(len(rows), len(cfg.MERGES))
        for row, merge in zip(rows, cfg.MERGES):
            waits = sorted({e for p in merge.core + merge.optional for e in p.wait_for})
            last = row.strip("|").split("|")[-1]
            self.assertEqual("wait" in last.lower(), bool(waits), (merge.key, last.strip()))

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
        # R38 M3: cm_platine stands for the three Platine parts once that merge has switched them.
        self.assertEqual(
            cultures(latin.optional),
            [("romanian",), ("platinean", "cm_platine"), ("argentine",), ("uruguayan",), ("chilean",)],
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


class RepresentationTest(unittest.TestCase):
    """R38 M3, spec section 3: a merged part is represented by its result. Once a lower merge has switched the parts
    it shares with a higher merge, those pops are its result's, so the higher merge must list that result: as an
    alternative in the same slot for a core part (or the higher merge's core can never be met again), anywhere in the
    merge for an optional one (an optional slot need not be met, and one culture fills one slot)."""

    def shared(self, merges=None):
        """(higher, lower) -> the slot cultures the two share, for every pair of merges that shares any."""
        merges = cfg.MERGES if merges is None else merges
        cases = {}
        for i, a in enumerate(merges):
            for b in merges[i + 1:]:
                common = set(part_cultures(a)) & set(part_cultures(b))
                if not common:
                    continue
                a_in_b, b_in_a = a.result in part_cultures(b), b.result in part_cultures(a)
                # One of the two lists the other's result: never neither (a part would be lost), never both (a cycle).
                self.assertNotEqual(a_in_b, b_in_a, (a.key, b.key, sorted(common)))
                higher, lower = (b, a) if a_in_b else (a, b)
                cases[(higher.key, lower.key)] = sorted(common)
        return cases

    def test_every_pair_of_merges_that_shares_a_part_is_a_higher_and_a_lower_one(self):
        self.assertEqual(self.shared(), {
            ("anglophone", "british"): ["british", "scottish"],
            ("latin", "french"): ["french"],
            ("anglophone", "american"): ["afro_american", "dixie", "yankee"],
            ("pan_slavic", "yugoslav"): ["bulgarian", "slovene"],
            ("latin", "platine"): ["argentine", "platinean", "uruguayan"],
            ("pan_malay", "filipino"): ["filipino"],
        })

    def test_a_shared_core_part_takes_the_lower_result_in_its_own_slot(self):
        checked = []
        for (higher_key, lower_key), common in self.shared().items():
            higher, lower = cfg.merge_by_key(higher_key), cfg.merge_by_key(lower_key)
            for culture in common:
                if culture == lower.result:
                    continue  # the lower merge's result itself (french in Latin): it is the representative
                for part in higher.core:
                    if culture in part.cultures:
                        self.assertIn(lower.result, part.cultures, (higher_key, culture))
                        checked.append((higher_key, part.cultures))
        self.assertEqual(checked, [("anglophone", ("yankee", "cm_american"))])

    def test_the_slots_that_take_a_result_for_shared_optional_parts(self):
        # Latin's Platinean slot takes cm_platine for Platinean, Argentine and Uruguayan alike; Pan-Slavic and
        # Anglophone already list cm_yugoslav and cm_american as core parts, which cover Slovene, Bulgarian, Dixie
        # and Afro-American.
        latin = cfg.merge_by_key("latin")
        self.assertIn(("platinean", "cm_platine"), [p.cultures for p in latin.optional])
        for higher, result in (("pan_slavic", "cm_yugoslav"), ("anglophone", "cm_american")):
            self.assertIn(result, [c for p in cfg.merge_by_key(higher).core for c in p.cultures], higher)

    def test_the_rule_would_notice_a_missing_result(self):
        latin = cfg.merge_by_key("latin")
        stripped = tuple(cfg.Part(tuple(c for c in p.cultures if c != "cm_platine"), p.tier, p.wait_for) for p in latin.optional)
        broken = tuple(m if m.key != "latin" else cfg.Merge(m.key, m.result, m.new, m.core, stripped, m.components)
                       for m in cfg.MERGES)
        with self.assertRaises(AssertionError):
            self.shared(broken)


class PartsAndSuccessorsTest(unittest.TestCase):
    """parts_of and successors_of, which test_culture_merge_mod_refs reads."""

    def test_parts_of_a_new_result(self):
        self.assertEqual(
            cfg.parts_of("cm_german"), {"north_german", "south_german", "alemannic", "east_german"}
        )

    def test_parts_of_an_absorb_result_leaves_the_result_out(self):
        self.assertEqual(cfg.parts_of("french"), {"wallonian", "occitan", "catalan"})
        self.assertEqual(cfg.parts_of("han"), {"yue", "min", "hakka"})

    def test_parts_of_a_slot_with_alternatives_gives_both(self):
        parts = cfg.parts_of("cm_anglophone")
        self.assertIn("yankee", parts)
        self.assertIn("cm_american", parts)

    def test_parts_of_a_culture_nothing_merges_into_is_empty(self):
        self.assertEqual(cfg.parts_of("german"), set())
        self.assertEqual(cfg.parts_of("north_german"), set())

    def test_parts_of_every_result_are_slot_cultures(self):
        for m in cfg.MERGES:
            slot = {c for p in m.core + m.optional for c in p.cultures}
            self.assertTrue(cfg.parts_of(m.result) <= slot, m.key)
            self.assertNotIn(m.result, cfg.parts_of(m.result), m.key)

    def test_successors_follow_the_chain(self):
        self.assertEqual(cfg.successors_of("north_german"), {"cm_german"})
        self.assertEqual(cfg.successors_of("corsican"), {"cm_italian", "cm_latin"})
        self.assertEqual(cfg.successors_of("scottish"), {"british", "cm_anglophone"})
        self.assertEqual(cfg.successors_of("yankee"), {"cm_american", "cm_anglophone"})
        self.assertEqual(cfg.successors_of("russian"), {"cm_east_slavic", "cm_pan_slavic"})

    def test_a_culture_is_not_its_own_successor(self):
        # French is the absorb result of its own merge, and a Latin part.
        self.assertEqual(cfg.successors_of("french"), {"cm_latin"})
        self.assertEqual(cfg.successors_of("catalan"), {"french", "cm_latin"})
        for m in cfg.MERGES:
            for p in m.core + m.optional:
                for c in p.cultures:
                    self.assertNotIn(c, cfg.successors_of(c), "%s in %s" % (c, m.key))

    def test_a_culture_no_merge_folds_away_has_none(self):
        self.assertEqual(cfg.successors_of("hungarian"), set())
        self.assertEqual(cfg.successors_of("han"), set())
        self.assertEqual(cfg.successors_of("cm_latin"), set())
        self.assertEqual(cfg.successors_of("german"), set())

    def test_a_culture_in_two_merges_gets_both_chains(self):
        # Dixie is an American core part and an Anglophone optional one.
        self.assertEqual(cfg.successors_of("dixie"), {"cm_american", "cm_anglophone"})
        # Platinean joins Platine and, as an optional part, Latin.
        self.assertEqual(cfg.successors_of("platinean"), {"cm_platine", "cm_latin"})

    def test_successors_agree_with_parts_of(self):
        # Every direct result of a part lists that part in parts_of.
        for m in cfg.MERGES:
            for part in cfg.parts_of(m.result):
                self.assertIn(m.result, cfg.successors_of(part), "%s -> %s" % (part, m.result))


if __name__ == "__main__":
    unittest.main()
