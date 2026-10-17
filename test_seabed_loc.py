"""The seabed's words (seabed claims spec § 1): no seabed string a player
reads says "recorded" (licence and claim instead), the claim concept exists,
and the keys the Seabed panel names are defined."""
import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
LOC = os.path.join(REPO, "localization", "english")
PREFIXES = ("te_seabed_", "TE_STATE_SEABED", "concept_seabed", "je_un_terms_law_of_sea_seabed",
            "je_un_chamber_seabed", "notification_te_seabed")
BASINS = ("pacific", "atlantic", "indian", "arctic", "southern")


def loc_values():
    out = {}
    for f in sorted(os.listdir(LOC)):
        if not f.endswith(".yml"):
            continue
        with open(os.path.join(LOC, f), encoding="utf-8-sig") as fh:
            for line in fh:
                m = re.match(r'\s*([\w.]+):\d*\s*"(.*)"\s*$', line)
                if m:
                    out[m.group(1)] = m.group(2)
    return out


class SeabedWordsTest(unittest.TestCase):
    def test_no_recorded(self):
        bad = sorted(k for k, v in loc_values().items()
                     if k.startswith(PREFIXES) and re.search(r"\brecord", v, re.I))
        self.assertEqual(bad, [])

    def test_claim_concept(self):
        with open(os.path.join(REPO, "common", "game_concepts", "extra_concepts.txt"), encoding="utf-8-sig") as f:
            self.assertRegex(f.read(), r"(?m)^concept_seabed_claim = \{")
        loc = loc_values()
        for key in ("concept_seabed_claim", "concept_seabed_claim_desc"):
            self.assertIn(key, loc)
        self.assertIn("claim", loc["concept_seabed_licence_desc"].lower())

    def test_panel_keys(self):
        loc = loc_values()
        keys = []
        for box in ("room", "licences", "longhaul", "claims", "policy", "regime"):
            keys += [f"te_seabed_ov_{box}_{part}" for part in ("cap", "word", "fig", "tt")]
        keys += [f"te_seabed_policy_short_{i}" for i in (1, 2, 3)]
        for col in ("free", "pool", "weight", "next"):
            keys += [f"te_seabed_col_{col}", f"te_seabed_col_{col}_tt"]
        keys += ["te_seabed_basins_asof", "te_seabed_how_sub_claims", "te_seabed_how_claims"]
        for b in BASINS:
            keys += [f"te_seabed_rival_row_{b}", f"te_seabed_rivals_more_{b}", f"te_seabed_rival_us_{b}"]
        self.assertEqual([k for k in keys if k not in loc], [])

    def test_the_readout_says_enough_not_exact(self):
        """The +1 figure is sufficient, often more than needed (Task 4's ruling)."""
        self.assertIn("enough", loc_values()["te_seabed_col_next_tt"])


if __name__ == "__main__":
    unittest.main()
