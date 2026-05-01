"""Unit tests for tech_unlocks_lib — block walker + inverted-index builder.

Pure-unit, tempfile-backed. Run:
    .venv/bin/python -m unittest test_tech_unlocks_lib -v
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import tech_unlocks_lib as lib


class IterTopLevelBlocksTests(unittest.TestCase):
    def test_two_top_level_blocks(self) -> None:
        text = (
            "thing_a = {\n"
            "\tinner = 1\n"
            "}\n"
            "thing_b = {\n"
            "\tinner = 2\n"
            "}\n"
        )
        ids = [tid for tid, _ in lib.iter_top_level_blocks(text)]
        self.assertEqual(ids, ["thing_a", "thing_b"])

    def test_handles_nested_braces(self) -> None:
        text = (
            "outer = {\n"
            "\tnested = { a = { b = 1 } c = 2 }\n"
            "\tafter_nested = 3\n"
            "}\n"
        )
        out = list(lib.iter_top_level_blocks(text))
        self.assertEqual(len(out), 1)
        tid, body = out[0]
        self.assertEqual(tid, "outer")
        self.assertIn("after_nested = 3", body)

    def test_preserves_comments(self) -> None:
        text = "x = {\n\t# kept\n\tk = v\n}\n"
        _, body = next(lib.iter_top_level_blocks(text))
        self.assertIn("# kept", body)

    def test_handles_bom(self) -> None:
        # The BOM is stripped at file-read time (utf-8-sig). This test
        # just asserts that an inline `﻿` doesn't crash the regex.
        text = "﻿x = {\n\tk = v\n}\n"
        # Lowering: the leading BOM is part of `text` here. iter_top_level_blocks
        # uses MULTILINE so it'll still find the start at column 0 of line 1
        # if BOM precedes it; but to keep the test lightweight, we just verify
        # no exception.
        list(lib.iter_top_level_blocks(text))

    def test_skips_text_before_first_block(self) -> None:
        text = "# top-of-file comment\nfoo = bar\n\nactual = {\n\tk = v\n}\n"
        ids = [tid for tid, _ in lib.iter_top_level_blocks(text)]
        # `foo = bar` is parsed by the regex too because the regex matches
        # `<id> = {`. Since `foo = bar` has no `{`, it doesn't match, so we
        # only expect `actual`.
        self.assertEqual(ids, ["actual"])

    def test_clausewitz_merge_directive_prefixes(self) -> None:
        # Engine-native prefixes used throughout the mod. Each yielded id
        # should be the underlying entity name, with the directive stripped.
        # Regression: the original implementation's `[A-Za-z_]` char class
        # didn't allow `:` so REPLACE_OR_CREATE entities (e.g.
        # `building_synthetics_plant_rubber`) silently fell out of the index.
        text = (
            "REPLACE_OR_CREATE:building_synthetics_plant_rubber = {\n"
            "\tunlocking_technologies = { isoprene }\n"
            "}\n"
            "INJECT:building_shipyard = {\n"
            "\tx = 1\n"
            "}\n"
            "REPLACE:building_oil_rig = {\n"
            "\ty = 2\n"
            "}\n"
            "plain_id = {\n"
            "\tz = 3\n"
            "}\n"
        )
        ids = [tid for tid, _ in lib.iter_top_level_blocks(text)]
        self.assertEqual(ids, [
            "building_synthetics_plant_rubber",
            "building_shipyard",
            "building_oil_rig",
            "plain_id",
        ])


class ParseUnlockingTechsTests(unittest.TestCase):
    def test_single_tech(self) -> None:
        body = "unlocking_technologies = { tech_alpha }"
        self.assertEqual(lib.parse_unlocking_techs(body), ["tech_alpha"])

    def test_multiple_techs(self) -> None:
        body = "unlocking_technologies = { tech_a tech_b tech_c }"
        self.assertEqual(
            lib.parse_unlocking_techs(body),
            ["tech_a", "tech_b", "tech_c"],
        )

    def test_with_inline_comment(self) -> None:
        body = "unlocking_technologies = { tech_a # commented\n\ttech_b }"
        self.assertEqual(lib.parse_unlocking_techs(body), ["tech_a", "tech_b"])

    def test_empty_block(self) -> None:
        body = "unlocking_technologies = { }"
        self.assertEqual(lib.parse_unlocking_techs(body), [])

    def test_missing_block(self) -> None:
        body = "some_other_field = { value }"
        self.assertEqual(lib.parse_unlocking_techs(body), [])

    def test_block_inside_larger_body(self) -> None:
        body = (
            "name = some_thing\n"
            "unlocking_technologies = {\n\ttech_x\n}\n"
            "modifier = { foo = 1 }"
        )
        self.assertEqual(lib.parse_unlocking_techs(body), ["tech_x"])


class BuildTechUnlockIndexTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.repo_root = Path(self.tmpdir.name)
        self.common = self.repo_root / "common"

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def _write(self, subdir: str, fname: str, content: str) -> None:
        d = self.common / subdir
        d.mkdir(parents=True, exist_ok=True)
        (d / fname).write_text(content, encoding="utf-8")

    def test_groups_by_type_with_multi_tech_entry(self) -> None:
        self._write("production_methods", "pms.txt", (
            "pm_alpha = {\n"
            "\tunlocking_technologies = { tech_a }\n"
            "}\n"
            "pm_beta = {\n"
            "\tunlocking_technologies = { tech_a tech_c }\n"
            "}\n"
        ))
        self._write("combat_unit_types", "units.txt", (
            "combat_unit_type_x = {\n"
            "\tunlocking_technologies = { tech_b }\n"
            "}\n"
        ))
        idx = lib.build_tech_unlock_index(self.repo_root)
        self.assertIn("tech_a", idx)
        self.assertIn("tech_b", idx)
        self.assertIn("tech_c", idx)

        a = idx["tech_a"]["by_type"]["PMs"]
        a_ids = sorted(e["id"] for e in a)
        self.assertEqual(a_ids, ["pm_alpha", "pm_beta"])

        b = idx["tech_b"]["by_type"]["Combat Unit Types"]
        self.assertEqual(b[0]["id"], "combat_unit_type_x")

        c = idx["tech_c"]["by_type"]["PMs"]
        self.assertEqual([e["id"] for e in c], ["pm_beta"])

    def test_entry_carries_type_id_file_source(self) -> None:
        self._write("buildings", "x.txt", (
            "building_thing = {\n"
            "\tunlocking_technologies = { tech_z }\n"
            "}\n"
        ))
        idx = lib.build_tech_unlock_index(self.repo_root)
        entry = idx["tech_z"]["by_type"]["Buildings"][0]
        self.assertEqual(entry["type"], "Buildings")
        self.assertEqual(entry["id"], "building_thing")
        self.assertEqual(entry["file"], "x.txt")
        self.assertEqual(entry["source"], "mod")

    def test_summary_and_n_total_match(self) -> None:
        self._write("production_methods", "pms.txt", (
            "pm_a = { unlocking_technologies = { tech_a } }\n"
            "pm_b = { unlocking_technologies = { tech_a } }\n"
            "pm_c = { unlocking_technologies = { tech_a } }\n"
        ))
        self._write("buildings", "b.txt", (
            "building_x = { unlocking_technologies = { tech_a } }\n"
        ))
        idx = lib.build_tech_unlock_index(self.repo_root)
        rec = idx["tech_a"]
        self.assertEqual(rec["summary"]["PMs"], 3)
        self.assertEqual(rec["summary"]["Buildings"], 1)
        self.assertEqual(rec["n_total"], 4)
        # Double-check by_type lengths line up with summary counts.
        self.assertEqual(len(rec["by_type"]["PMs"]), 3)
        self.assertEqual(len(rec["by_type"]["Buildings"]), 1)

    def test_directive_prefix_resolves_to_underlying_id(self) -> None:
        # End-to-end: the Vic3 isoprene case. The building uses
        # REPLACE_OR_CREATE: but the inverted index should still attribute
        # building_synthetics_plant_rubber to the isoprene tech.
        self._write("buildings", "x.txt", (
            "REPLACE_OR_CREATE:building_synthetics_plant_rubber = {\n"
            "\tunlocking_technologies = { isoprene }\n"
            "}\n"
        ))
        idx = lib.build_tech_unlock_index(self.repo_root)
        self.assertIn("isoprene", idx)
        entry = idx["isoprene"]["by_type"]["Buildings"][0]
        self.assertEqual(entry["id"], "building_synthetics_plant_rubber")

    def test_no_unlocking_block_does_not_index(self) -> None:
        self._write("buildings", "b.txt", (
            "building_no_tech = {\n"
            "\tname = nothing\n"
            "}\n"
        ))
        idx = lib.build_tech_unlock_index(self.repo_root)
        self.assertEqual(idx, {})

    def test_include_vanilla_skipped_when_path_missing(self) -> None:
        # No `common/` populated and no vanilla path — should produce
        # an empty result without raising.
        idx = lib.build_tech_unlock_index(
            self.repo_root,
            include_vanilla=True,
            vanilla_common_root=Path("/does/not/exist"),
        )
        self.assertEqual(idx, {})

    def test_include_vanilla_attributes_source(self) -> None:
        # Set up a mock vanilla tree alongside the mod tree.
        vanilla_root = self.repo_root / "vanilla_common"
        (vanilla_root / "buildings").mkdir(parents=True)
        (vanilla_root / "buildings" / "v.txt").write_text(
            "building_vanilla = {\n"
            "\tunlocking_technologies = { tech_v }\n"
            "}\n",
            encoding="utf-8",
        )
        self._write("buildings", "m.txt", (
            "building_mod = {\n"
            "\tunlocking_technologies = { tech_m }\n"
            "}\n"
        ))
        idx = lib.build_tech_unlock_index(
            self.repo_root,
            include_vanilla=True,
            vanilla_common_root=vanilla_root,
        )
        self.assertEqual(idx["tech_m"]["by_type"]["Buildings"][0]["source"], "mod")
        self.assertEqual(idx["tech_v"]["by_type"]["Buildings"][0]["source"], "vanilla")


if __name__ == "__main__":
    unittest.main()
