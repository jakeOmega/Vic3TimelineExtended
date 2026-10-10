"""Law-consistency generator: carrier laws are never replacement candidates.

The tax-code carrier laws (`law_te_probe_carrier`, the probe harness's debug
carrier, and `law_te_tax_code`, the production carrier) are constraint-free,
tag-free and tech-free laws in `lawgroup_taxation`, so without an exclusion the
generator adopts one as the group's unconditional terminal fallback. Every
Per-Capita/Proportional/Graduated country under a violated constraint would then
be moved onto a zero-rate carrier, even with the game rule off, and the engine
would not say a word.

No game install needed: the tests feed `candidate_order` and `build_output`
hand-built law tables, and the vanilla-input tests read the committed
`vanilla_parsed/` snapshot.
"""

import contextlib
import copy
import io
import os
import tempfile
import types
import unittest
from unittest import mock

import gen_law_consistency as gen
import vanilla_parsed
from paradox_file_parser import ParadoxFileParser

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


def _quiet(fn, *args, **kwargs):
    """Call a generator entry point, swallowing its progress and warning prints."""
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return fn(*args, **kwargs)


def _mod_state(laws, ideologies):
    """A ModState stand-in holding only the vanilla halves the generator reads."""
    def parser(data):
        p = ParadoxFileParser()
        p.data = data
        return p
    return types.SimpleNamespace(
        base_parsers={"Laws": parser(laws), "Ideologies": parser(ideologies)}
    )


class VanillaInputTest(unittest.TestCase):
    """The generator reads parsed vanilla (a ModState's, or the snapshot), not
    raw game files, so a game-less session regenerates its output (#624)."""

    @classmethod
    def setUpClass(cls):
        cls.snapshot = vanilla_parsed.load()

    def test_snapshot_reproduces_committed_output(self):
        # Byte for byte, with no game files on this machine. A failure means
        # the generator, ideology_modifications.py or vanilla_parsed/ changed
        # without the output being regenerated.
        with mock.patch.object(gen, "_vanilla_game_dir", return_value=None):
            output = _quiet(gen.generate)
        with open(GENERATED, encoding="utf-8-sig", newline="") as fh:
            self.assertEqual(output, fh.read())

    def test_mod_state_vanilla_matches_snapshot(self):
        mod_state = _mod_state(
            self.snapshot.data["Laws"], self.snapshot.data["Ideologies"]
        )
        with mock.patch.object(gen, "_vanilla_game_dir", return_value=None):
            output = _quiet(gen.generate, mod_state)
        with open(GENERATED, encoding="utf-8-sig", newline="") as fh:
            self.assertEqual(output, fh.read())

    def test_mod_state_vanilla_is_what_gets_parsed(self):
        tiny = {
            "law_alpha": ("=", {"group": ("=", "lawgroup_taxation"), "progressiveness": ("=", "3")}),
            "law_beta": ("=", {"group": ("=", "lawgroup_taxation"), "progressiveness": ("=", "5")}),
        }
        mod_state = _mod_state(tiny, {})
        vanilla = gen.load_vanilla(mod_state)
        self.assertIs(vanilla["laws"], tiny)
        laws = gen.parse_laws(vanilla["laws"])
        self.assertEqual(laws["law_alpha"]["progressiveness"], 3)
        self.assertEqual(laws["law_beta"]["progressiveness"], 5)
        # Vanilla keeps its key order as the file-order tiebreak, ahead of every mod law.
        self.assertEqual((laws["law_alpha"]["file_order"], laws["law_beta"]["file_order"]), (0, 1))
        self.assertGreater(laws["law_te_tax_code"]["file_order"], 1)
        # Not a stale snapshot's laws.
        self.assertNotIn("law_peasant_levies", laws)

    def test_parsing_never_mutates_vanilla_data(self):
        laws = copy.deepcopy(self.snapshot.data["Laws"])
        ideologies = copy.deepcopy(self.snapshot.data["Ideologies"])
        gen.parse_laws(laws)
        gen.parse_ideologies(ideologies)
        self.assertEqual(laws, self.snapshot.data["Laws"])
        self.assertEqual(ideologies, self.snapshot.data["Ideologies"])

    def test_vanilla_laws_rank_in_file_order(self):
        laws = gen.parse_laws(self.snapshot.data["Laws"])
        vanilla_ids = [k for k in self.snapshot.data["Laws"] if k.startswith("law_")]
        ranks = [laws[k]["file_order"] for k in vanilla_ids if k in laws]
        self.assertEqual(ranks, sorted(ranks))
        self.assertEqual(ranks[0], 0)

    def test_mod_law_files_apply_over_vanilla_data(self):
        # A mod REPLACE of a vanilla law wins, as it does in a ModState load.
        vanilla = {
            "law_alpha": ("=", {"group": ("=", "lawgroup_taxation"), "progressiveness": ("=", "3")}),
        }
        with tempfile.TemporaryDirectory() as mod_dir:
            os.makedirs(os.path.join(mod_dir, "common", "laws"))
            with open(os.path.join(mod_dir, "common", "laws", "mod.txt"), "w", encoding="utf-8") as fh:
                fh.write(
                    "REPLACE:law_alpha = { group = lawgroup_taxation progressiveness = 9 }\n"
                    "law_gamma = { group = lawgroup_taxation progressiveness = 1 }\n"
                )
            with mock.patch.object(gen, "mod_path", mod_dir):
                laws = gen.parse_laws(vanilla)
        self.assertEqual(laws["law_alpha"]["progressiveness"], 9)
        self.assertEqual(laws["law_alpha"]["file_order"], 0)
        self.assertEqual(laws["law_gamma"]["file_order"], 1)

    def test_parsing_without_vanilla_or_game_files_fails_loudly(self):
        # Mod-only output would look complete and be wrong.
        with mock.patch.object(gen, "_vanilla_game_dir", return_value=None):
            with self.assertRaises(FileNotFoundError):
                gen.parse_laws()
            with self.assertRaises(FileNotFoundError):
                gen.parse_ideologies()
        with tempfile.TemporaryDirectory() as empty:
            with mock.patch.object(gen, "_vanilla_game_dir", return_value=empty):
                with self.assertRaises(FileNotFoundError):
                    gen.parse_laws()

    def test_standalone_prefers_game_files_else_snapshot(self):
        with tempfile.TemporaryDirectory() as game:
            os.makedirs(os.path.join(game, "common", "laws"))
            with mock.patch.object(gen, "_vanilla_game_dir", return_value=game):
                self.assertIsNone(gen.load_vanilla())
        with mock.patch.object(gen, "_vanilla_game_dir", return_value=None):
            vanilla = gen.load_vanilla()
        self.assertEqual(set(vanilla["laws"]), set(self.snapshot.data["Laws"]))
        self.assertEqual(set(vanilla["ideologies"]), set(self.snapshot.data["Ideologies"]))

    def test_mod_state_wins_over_game_files(self):
        # The server's own vanilla (it may have chosen the snapshot over older
        # files on disk) is what the generator follows.
        mod_state = _mod_state({}, {})
        with tempfile.TemporaryDirectory() as game:
            os.makedirs(os.path.join(game, "common", "laws"))
            with mock.patch.object(gen, "_vanilla_game_dir", return_value=game):
                self.assertEqual(gen.load_vanilla(mod_state), {"laws": {}, "ideologies": {}})


def _can_hold(law_id, held, laws):
    """Whether `law_id` can be held beside `held` (group -> law), following the
    chain of laws it needs as the consistency walk checks it. Each law needs
    one law from a single list, so the chain has no branches to merge."""
    law = laws[law_id]
    if law["group"] in held:
        return held[law["group"]] == law_id
    if any(d in held.values() for d in law["disallowing_laws"]):
        return False
    if any(law_id in laws[h]["disallowing_laws"] for h in held.values()):
        return False
    held = {**held, law["group"]: law_id}
    needs = [n for n in gen.held_unlocking_laws(law, laws) if n in laws]
    return not needs or any(_can_hold(n, held, laws) for n in needs)


class PrerequisiteHoldableTest(unittest.TestCase):
    """A law's every `unlocking_laws` entry can be held beside it.

    Otherwise the law can be enacted from that prerequisite but never kept
    with it, and the consistency walk takes the prerequisite (and whatever
    needs it) away the moment the law passes, with no preview. Collective
    Governance allowed Anarchy, which needs Cooperative Ownership, which
    vanilla unlocks only with Council Republic or Corporate State: an
    anarchist Council Republic that enacted it lost Cooperative Ownership,
    Anarchy, Collectivized Agriculture and Possession by Use
    (`common/laws/modified.txt` now adds it to Cooperative Ownership's list).
    """

    def test_every_prerequisite_can_be_held(self):
        laws = gen.parse_laws(vanilla_parsed.load().data["Laws"])
        for law_id, law in laws.items():
            if law_id in gen.CARRIER_LAW_DENYLIST:
                continue
            for need in gen.held_unlocking_laws(law, laws):
                if need in laws:
                    with self.subTest(law=law_id, needs=need):
                        self.assertTrue(_can_hold(need, {law["group"]: law_id}, laws))

    def test_chain_is_followed(self):
        laws = {
            "law_head": _law(0, group="lawgroup_a", unlocking_laws=["law_mid"]),
            "law_rival": _law(1, group="lawgroup_a"),
            "law_mid": _law(2, group="lawgroup_b", unlocking_laws=["law_base"]),
            "law_base": _law(3, group="lawgroup_c", unlocking_laws=["law_rival"]),
        }
        self.assertFalse(_can_hold("law_mid", {"lawgroup_a": "law_head"}, laws))
        laws["law_base"]["unlocking_laws"].append("law_head")
        self.assertTrue(_can_hold("law_mid", {"lawgroup_a": "law_head"}, laws))


if __name__ == "__main__":
    unittest.main()
