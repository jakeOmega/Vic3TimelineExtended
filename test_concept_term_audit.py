"""Unit tests for scripts/analysis/concept_term_audit.py's glossary scan (#1438).

The audit finds plain-text mentions of 1.15 glossary names (vanilla's from
the `vanilla_parsed/` snapshot when no game is installed, the mod's from
`common/glossary/`) as well as concept names, and leaves a mention already
linked as `[glossary_x]`, `[glossary_x|l]` or `[Glossary(...)]` alone.
"""
import os
import tempfile
import unittest
from unittest import mock

import scripts.analysis.concept_term_audit as cta


def _write(path: str, text: str, bom: bool = True) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8-sig" if bom else "utf-8") as fh:
        fh.write(text)


class GlossaryScanTests(unittest.TestCase):
    def setUp(self):
        self._td = tempfile.TemporaryDirectory()
        self.root = self._td.name
        _write(os.path.join(self.root, "common", "glossary", "te_glossary.txt"),
               "glossary_te_dirigisme = {}\n")
        _write(os.path.join(self.root, "localization", "english", "te_misc_l_english.yml"),
               'l_english:\n'
               ' glossary_te_dirigisme:0 "Dirigisme"\n'
               ' glossary_te_dirigisme_desc:0 "State direction of investment."\n')
        _write(os.path.join(self.root, "localization", "english", "te_buildings_l_english.yml"),
               'l_english:\n'
               ' plain:0 "The industrial cradle of the Sumitomo zaibatsu."\n'
               ' linked:0 "The Mitsui [glossary_zaibatsu]\'s trading house."\n'
               ' linked_lower:0 "The cradle of the Sumitomo [glossary_zaibatsu|l]."\n'
               ' linked_fn:0 "The [Glossary(\'glossary_zaibatsu\',\'zaibatsu\')] houses."\n'
               ' mod_plain:0 "A turn toward dirigisme in the ministries."\n'
               ' ri_plain:0 "Ri Sung-gyu signs."\n')
        patches = [
            mock.patch.object(cta, "mod_path", self.root),
            mock.patch.object(cta, "base_game_path", os.path.join(self.root, "no_game")),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(self._td.cleanup)

    def _candidates(self):
        ids = cta.load_registered_glossary()
        display = cta.load_glossary_display_names(ids)
        tiers = [cta.classify(gid, names) for gid, names in display.items()]
        return ids, display, cta.scan(tiers)

    def test_vanilla_entries_come_from_the_snapshot_without_a_game(self):
        ids, display, _ = self._candidates()
        self.assertIn("glossary_zaibatsu", ids)
        self.assertEqual(display["glossary_zaibatsu"], ["Zaibatsu"])

    def test_mod_entries_come_from_common_glossary_and_mod_loc(self):
        ids, display, _ = self._candidates()
        self.assertIn("glossary_te_dirigisme", ids)
        self.assertEqual(display["glossary_te_dirigisme"], ["Dirigisme"])

    def test_plain_mentions_flag_and_linked_ones_do_not(self):
        _, _, cands = self._candidates()
        flagged = {(c.loc_key, c.cid) for c in cands}
        self.assertIn(("plain", "glossary_zaibatsu"), flagged)
        self.assertIn(("mod_plain", "glossary_te_dirigisme"), flagged)
        for key in ("linked", "linked_lower", "linked_fn"):
            self.assertNotIn((key, "glossary_zaibatsu"), flagged, key)

    def test_an_entry_does_not_flag_its_own_name_line(self):
        _, _, cands = self._candidates()
        self.assertFalse([c for c in cands if c.loc_key.startswith("glossary_te_dirigisme")])

    def test_excluded_entry_never_flags(self):
        _, display, cands = self._candidates()
        self.assertIn("glossary_ri", display)
        self.assertFalse([c for c in cands if c.cid == "glossary_ri"])

    def test_single_word_glossary_names_scan_in_event_files(self):
        tier, _ = cta._surface_tier("glossary_zaibatsu", "Zaibatsu")
        self.assertEqual(tier, 1)


if __name__ == "__main__":
    unittest.main()
