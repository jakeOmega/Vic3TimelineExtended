"""Law-consistency generator: carrier laws are never replacement candidates.

The tax-code carrier laws (`law_te_probe_carrier`, the probe harness's debug
carrier, and `law_te_tax_code`, the production carrier) are constraint-free,
tag-free and tech-free laws in `lawgroup_taxation`, so without an exclusion the
generator adopts one as the group's unconditional terminal fallback. Every
Per-Capita/Proportional/Graduated country under a violated constraint would then
be moved onto a zero-rate carrier, even with the game rule off, and the engine
would not say a word.

No game install needed: the tests feed `candidate_order` and `build_output`
hand-built law tables.
"""

import contextlib
import io
import os
import unittest

import gen_law_consistency as gen

REPO = os.path.dirname(os.path.abspath(__file__))
GENERATED = os.path.join(
    REPO, "common", "scripted_effects", "extra_law_consistency_generated.txt"
)
CARRIERS = ("law_te_probe_carrier", "law_te_tax_code")
GROUP = "lawgroup_taxation"


def _law(order, progressiveness=0, **fields):
    law = {
        "group": GROUP,
        "progressiveness": progressiveness,
        "unlocking_laws": [],
        "disallowing_laws": [],
        "unlocking_technologies": [],
        "parent": None,
        "file_order": order,
    }
    law.update(fields)
    return law


def _taxation_table():
    """A trimmed taxation group: two laws with cross-group constraints, one
    unconditional law, and both carriers. The carriers sit at the constrained
    laws' own progressiveness and have nothing gating them, so left in they
    would be the nearest candidate and the cascade's terminal fallback."""
    return {
        "law_land_based_taxation": _law(0, progressiveness=0),
        "law_per_capita_taxation": _law(
            1, progressiveness=1, unlocking_laws=["law_laissez_faire"]
        ),
        "law_graduated_taxation": _law(
            2, progressiveness=2, disallowing_laws=["law_traditionalism"]
        ),
        "law_te_probe_carrier": _law(3, progressiveness=1),
        "law_te_tax_code": _law(4, progressiveness=1),
    }


class CarrierLawDenylistTest(unittest.TestCase):
    def test_denylist_names_both_carriers(self):
        self.assertEqual(
            gen.CARRIER_LAW_DENYLIST, {"law_te_probe_carrier", "law_te_tax_code"}
        )

    def test_carrier_laws_never_candidates(self):
        laws = _taxation_table()
        group_ids = list(laws)
        for active in ("law_per_capita_taxation", "law_graduated_taxation"):
            candidates = gen.candidate_order(active, group_ids, laws, {})
            self.assertTrue(candidates, active)
            for carrier in CARRIERS:
                self.assertNotIn(carrier, candidates, (active, carrier))

    def test_carrier_laws_never_trigger_a_cascade(self):
        laws = _taxation_table()
        # Give each carrier a constraint: its violation must still not be checked.
        laws["law_te_probe_carrier"]["disallowing_laws"] = ["law_traditionalism"]
        laws["law_te_tax_code"]["unlocking_laws"] = ["law_laissez_faire"]
        self.assertEqual(
            gen.constraint_having_groups({
                "law_te_probe_carrier": laws["law_te_probe_carrier"],
                "law_te_tax_code": laws["law_te_tax_code"],
            }),
            [],
        )
        block = gen.emit_lawgroup_helper(GROUP, list(laws), laws, {})
        for carrier in CARRIERS:
            self.assertNotIn(carrier, block)

    def test_carrier_is_not_a_group_fallback(self):
        # A group whose only constraint-free, tech-free law is a carrier has no
        # usable terminal: build_output must warn instead of counting the carrier.
        laws = {
            "law_a": _law(0, unlocking_laws=["law_x"]),
            "law_b": _law(1, disallowing_laws=["law_y"]),
            "law_te_probe_carrier": _law(2),
        }
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            output = gen.build_output(laws, {})
        self.assertIn("no tech-free, constraint-free fallback", err.getvalue())
        self.assertNotIn("law_te_probe_carrier", output)

    def test_build_output_emits_no_carrier(self):
        output = gen.build_output(_taxation_table(), {})
        for carrier in CARRIERS:
            self.assertNotIn(carrier, output)
        # The non-carrier fallback still terminates the cascade.
        self.assertIn("activate_law = law_type:law_land_based_taxation", output)

    def test_committed_output_has_no_carrier(self):
        with open(GENERATED, encoding="utf-8-sig") as fh:
            text = fh.read()
        for carrier in CARRIERS:
            self.assertNotIn(carrier, text)


def _slavery_table():
    """The slavery group's shape: Legacy Slavery is unlocked by Slave Trade, a
    law of its own group, and Slave Trade has a cross-group disallow."""
    def law(order, progressiveness, **fields):
        return _law(order, progressiveness, group="lawgroup_slavery", **fields)
    return {
        "law_slavery_banned": law(0, 100),
        "law_colonial_slavery": law(1, 50),
        "law_debt_slavery": law(2, 0, disallowing_laws=["law_multicultural"]),
        "law_slave_trade": law(3, -50, disallowing_laws=["law_multicultural"]),
        "law_legacy_slavery": law(4, 0, unlocking_laws=["law_slave_trade"]),
    }


class SameGroupUnlockingTest(unittest.TestCase):
    """A same-group unlocking_laws entry gates enactment only.

    Checked as a standing requirement it can never hold (two laws of one group
    can't both be active), so every Legacy Slavery country was moved to
    Colonial Slavery before day one, and the USA lost its slave states.
    """

    def test_held_unlocking_laws_drops_own_group(self):
        laws = _slavery_table()
        self.assertEqual(gen.held_unlocking_laws(laws["law_legacy_slavery"], laws), [])
        self.assertFalse(gen.has_constraints(laws["law_legacy_slavery"], laws))

    def test_other_group_unlocking_still_checked(self):
        laws = _slavery_table()
        laws["law_legacy_slavery"]["unlocking_laws"].append("law_laissez_faire")
        laws["law_laissez_faire"] = _law(5, group="lawgroup_economic_system")
        self.assertEqual(
            gen.held_unlocking_laws(laws["law_legacy_slavery"], laws), ["law_laissez_faire"]
        )
        clause = gen._violation_clause(laws["law_legacy_slavery"], "", "law_legacy_slavery", laws)
        self.assertIn("has_law = law_type:law_laissez_faire", clause)
        self.assertNotIn("law_slave_trade", clause)

    def test_no_cascade_for_held_legacy_slavery(self):
        laws = _slavery_table()
        block = gen.emit_lawgroup_helper("lawgroup_slavery", list(laws), laws, {})
        self.assertNotIn("# Active: law_legacy_slavery", block)
        # As a replacement candidate it stays gated on coming from Slave Trade.
        self.assertIn("# Active: law_slave_trade", block)
        self.assertIn("activate_law = law_type:law_legacy_slavery", block)

    def test_committed_output_keeps_legacy_slavery(self):
        with open(GENERATED, encoding="utf-8-sig") as fh:
            text = fh.read()
        self.assertFalse(
            "# Active: law_legacy_slavery" in text,
            "the generated file still moves held Legacy Slavery to another law; regenerate it",
        )


if __name__ == "__main__":
    unittest.main()
