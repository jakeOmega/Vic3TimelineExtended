"""Unit tests for roster_membership_audit.

The audit flags a mod ship type with no `ai_ship_category` (required since
vanilla 1.14.4, #390), one naming an unknown category, one with no fleet
entity, a ship modification no ship type lists (#509) and a production method
no PM group lists.

Each fixture test builds a throwaway mod tree and a vanilla data set parsed
from text, then runs the real `load_state` merge, so a deliberately broken
definition has to be flagged; the last class holds the mod itself clean.
"""
from __future__ import annotations

import contextlib
import io
import os
import tempfile
import textwrap
import unittest

import roster_membership_audit as rma
from paradox_file_parser import ParadoxFileParser

REPO = os.path.dirname(os.path.abspath(__file__))

_VANILLA_CATEGORIES = "ai_ship_category_screens = { }\nai_ship_category_carriers = { }\n"
_VANILLA_SHIP_TYPES = """
ship_type_destroyer = {
    ai_ship_category = ai_ship_category_screens
    modifications = {
        ship_mod_slot_guns = { ship_mod_destroyer_guns }
        ship_mod_slot_utility_1 = { utility_mod_searchlights }
    }
}
"""
_VANILLA_MODS = (
    "ship_mod_destroyer_guns = { type = ship_mod_slot_guns }\n"
    "utility_mod_searchlights = { type = ship_mod_slot_utility_1 }\n"
    "utility_mod_vanilla_orphan = { type = ship_mod_slot_utility_1 }\n"
)
_VANILLA_PM_GROUPS = "pmg_vanilla = { production_methods = { pm_vanilla pm_vanilla_two } }\n"
_VANILLA_PMS = "pm_vanilla = { }\npm_vanilla_two = { }\npm_vanilla_orphan = { }\n"

# A sound mod: one new ship type with a category, a fleet entity row and a
# module of its own, and one production method in a group.
_SHIP_TYPES = """
ship_type_cutter = {
    ship_group = ship_group_torpedo_craft
    ai_ship_category = ai_ship_category_screens
    modifications = {
        ship_mod_slot_guns = { ship_mod_cutter_guns }
    }
}
"""
_MODS = "ship_mod_cutter_guns = {\n    type = ship_mod_slot_guns\n}\n"
_PM_GROUPS = "pmg_mod = { production_methods = { pm_mod } }\n"
_PMS = "pm_mod = {\n    texture = \"x.dds\"\n}\n"
_GENERATOR = 'SHIPS = [\n    ("ship_type_cutter", "ship_type_destroyer"),\n]\n'


def _parse(text: str) -> dict:
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as fh:
        fh.write(textwrap.dedent(text))
        path = fh.name
    try:
        parser = ParadoxFileParser()
        parser.parse_file(path)
        return parser.data
    finally:
        os.unlink(path)


class _Tree:
    """A temp mod tree over a small vanilla data set."""

    def __init__(self, ship_types=_SHIP_TYPES, mods=_MODS, pm_groups=_PM_GROUPS, pms=_PMS,
                 generator: str | None = _GENERATOR, fleet_entities: str | None = None):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = self._tmp.name
        files = {
            "common/ship_types/test.txt": ship_types,
            "common/ship_modifications/test.txt": mods,
            "common/ai_ship_categories/test.txt": "",
            "common/production_method_groups/test.txt": pm_groups,
            "common/production_methods/test.txt": pms,
            rma.FLEET_ENTITY_GENERATOR: generator,
            os.path.join(rma.FLEET_ENTITIES_DIR, "02_extra_fleet_entities.txt"): fleet_entities,
        }
        for rel, text in files.items():
            if text is None:
                continue
            path = os.path.join(self.root, rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            if text:
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(textwrap.dedent(text))
        self.vanilla = {
            "AI Ship Categories": _parse(_VANILLA_CATEGORIES),
            "Ship Types": _parse(_VANILLA_SHIP_TYPES),
            "Ship Modifications": _parse(_VANILLA_MODS),
            "PM Groups": _parse(_VANILLA_PM_GROUPS),
            "PMs": _parse(_VANILLA_PMS),
        }

    def audit(self) -> rma.AuditResult:
        state = rma.load_state(self.root, vanilla_data=self.vanilla)
        return rma.audit(state, mod_path=self.root)

    def flags(self) -> list[tuple[str, str]]:
        """Each flag, then each stale tag, as (kind, name)."""
        result = self.audit()
        return [(f.kind, f.name) for f in result.flags] + [("stale_review", t.name) for t in result.stale]

    def close(self):
        self._tmp.cleanup()


class _Case(unittest.TestCase):
    def tree(self, **kwargs) -> _Tree:
        tree = _Tree(**kwargs)
        self.addCleanup(tree.close)
        return tree


class SoundTreeTests(_Case):
    def test_a_sound_mod_has_no_flags_and_is_counted(self):
        result = self.tree().audit()
        self.assertEqual(result.flags, [])
        self.assertEqual(
            (result.ship_types_checked, result.modifications_checked, result.pms_checked), (1, 1, 1))
        self.assertTrue(result.fleet_entities_checked)


class AiShipCategoryTests(_Case):
    def test_a_ship_type_with_no_category_is_flagged(self):
        tree = self.tree(ship_types=_SHIP_TYPES.replace(
            "    ai_ship_category = ai_ship_category_screens\n", ""))
        (flag,) = tree.audit().flags
        self.assertEqual((flag.kind, flag.name), ("missing_ai_category", "ship_type_cutter"))
        self.assertEqual((flag.file, flag.line), ("common/ship_types/test.txt", 2))
        self.assertIsNone(flag.exemption)

    def test_an_unknown_category_is_flagged_on_its_line(self):
        tree = self.tree(ship_types=_SHIP_TYPES.replace(
            "ai_ship_category_screens", "ai_ship_category_skirmishers"))
        (flag,) = tree.audit().flags
        self.assertEqual((flag.kind, flag.name), ("unknown_ai_category", "ship_type_cutter"))
        self.assertEqual(flag.line, 4)
        self.assertIn("ai_ship_category_skirmishers", flag.detail)

    def test_a_category_the_mod_adds_is_known(self):
        tree = self.tree(ship_types=_SHIP_TYPES.replace(
            "ai_ship_category_screens", "ai_ship_category_drones"))
        with open(os.path.join(tree.root, "common/ai_ship_categories/test.txt"), "w", encoding="utf-8") as fh:
            fh.write("ai_ship_category_drones = { }\n")
        self.assertEqual(tree.flags(), [])

    def test_a_commented_out_or_nested_category_does_not_count(self):
        tree = self.tree(ship_types="""
            ship_type_cutter = {
                # ai_ship_category = ai_ship_category_screens
                modifier = { ai_ship_category = ai_ship_category_screens }
                modifications = { ship_mod_slot_guns = { ship_mod_cutter_guns } }
            }
        """)
        self.assertEqual(tree.flags(), [("missing_ai_category", "ship_type_cutter")])

    def test_an_inject_onto_a_vanilla_type_needs_no_category(self):
        tree = self.tree(ship_types=_SHIP_TYPES + """
            INJECT:ship_type_destroyer = {
                is_obsolete = { always = yes }
            }
        """)
        result = tree.audit()
        self.assertEqual(result.flags, [])
        self.assertEqual(result.ship_types_checked, 1)

    def test_an_inject_that_writes_an_unknown_category_is_flagged(self):
        tree = self.tree(ship_types=_SHIP_TYPES + """
            INJECT:ship_type_destroyer = {
                ai_ship_category = ai_ship_category_nope
            }
        """)
        self.assertEqual(tree.flags(), [("unknown_ai_category", "ship_type_destroyer")])

    def test_a_replaced_vanilla_type_must_restate_its_category(self):
        tree = self.tree(ship_types=_SHIP_TYPES + """
            REPLACE:ship_type_destroyer = {
                modifications = {
                    ship_mod_slot_guns = { ship_mod_destroyer_guns }
                    ship_mod_slot_utility_1 = { utility_mod_searchlights }
                }
            }
        """)
        # Vanilla's own fleet entity still serves it: no `no_fleet_entity`.
        self.assertEqual(tree.flags(), [("missing_ai_category", "ship_type_destroyer")])

    def test_a_quoted_category_is_read_as_its_value(self):
        tree = self.tree(ship_types=_SHIP_TYPES.replace(
            "ai_ship_category = ai_ship_category_screens", 'ai_ship_category = "ai_ship_category_screens"'))
        self.assertEqual(tree.flags(), [])

    def test_a_quoted_unknown_category_is_named_in_full(self):
        tree = self.tree(ship_types=_SHIP_TYPES.replace(
            "ai_ship_category = ai_ship_category_screens", 'ai_ship_category = "ai_ship_category_nope"'))
        (flag,) = tree.audit().flags
        self.assertEqual((flag.kind, flag.line), ("unknown_ai_category", 4))
        self.assertIn("`ai_ship_category = ai_ship_category_nope`", flag.detail)

    _NO_CATEGORY = _SHIP_TYPES.replace("    ai_ship_category = ai_ship_category_screens\n", "")

    def test_an_inject_can_supply_a_mod_types_category(self):
        """The merged ship type is what the engine reads: a later `INJECT:`
        onto the mod's own type applies (scripting_best_practices.md, Load
        Order)."""
        tree = self.tree(ship_types=self._NO_CATEGORY + """
            INJECT:ship_type_cutter = {
                ai_ship_category = ai_ship_category_screens
            }
        """)
        result = tree.audit()
        self.assertEqual(result.flags, [])
        self.assertEqual(result.ship_types_checked, 1)

    def test_an_inject_ahead_of_the_definition_supplies_nothing(self):
        """The definition that follows replaces what the `INJECT:` made."""
        tree = self.tree(ship_types="""
            INJECT:ship_type_cutter = {
                ai_ship_category = ai_ship_category_screens
            }
        """ + self._NO_CATEGORY)
        (flag,) = tree.audit().flags
        self.assertEqual((flag.kind, flag.name, flag.line), ("missing_ai_category", "ship_type_cutter", 6))

    def test_a_category_written_twice_is_judged_at_each_value(self):
        tree = self.tree(ship_types=_SHIP_TYPES.replace(
            "    ai_ship_category = ai_ship_category_screens\n",
            "    ai_ship_category = ai_ship_category_screens\n    ai_ship_category = ai_ship_category_nope\n"))
        (flag,) = tree.audit().flags
        self.assertEqual((flag.kind, flag.line), ("unknown_ai_category", 5))

    def test_an_inject_or_create_onto_a_mod_type_is_not_a_second_definition(self):
        tree = self.tree(ship_types=_SHIP_TYPES + """
            INJECT_OR_CREATE:ship_type_cutter = {
                is_obsolete = { always = yes }
            }
        """)
        result = tree.audit()
        self.assertEqual(result.flags, [])
        self.assertEqual(result.ship_types_checked, 1)

    def test_an_inject_or_create_that_creates_the_type_is_its_definition(self):
        tree = self.tree(
            ship_types="INJECT_OR_CREATE:ship_type_cutter = {\n"
                       "    modifications = { ship_mod_slot_guns = { ship_mod_cutter_guns } }\n}\n")
        self.assertEqual(tree.flags(), [("missing_ai_category", "ship_type_cutter")])

    def test_a_field_level_directive_on_the_category_is_checked(self):
        """`REPLACE:ai_ship_category = x` inside an `INJECT:` is the parser's
        convention, which neither vanilla nor the mod uses; the value is
        judged all the same, on its line."""
        tree = self.tree(ship_types=_SHIP_TYPES + """
            INJECT:ship_type_destroyer = {
                REPLACE:ai_ship_category = ai_ship_category_nope
            }
        """)
        (flag,) = tree.audit().flags
        self.assertEqual((flag.kind, flag.name), ("unknown_ai_category", "ship_type_destroyer"))
        self.assertEqual(flag.line, 11)  # the field's own line, not the block's

    def test_the_ship_type_flags_take_no_comment(self):
        tree = self.tree(ship_types="""
            ship_type_cutter = { # REVIEWED 2026-11-12 (roster_membership): later
                modifications = { ship_mod_slot_guns = { ship_mod_cutter_guns } }
            }
        """)
        result = tree.audit()
        self.assertEqual([(f.kind, f.name) for f in result.flags], [("missing_ai_category", "ship_type_cutter")])
        self.assertTrue(all(f.exemption is None for f in result.flags))
        self.assertEqual([(t.name, t.why) for t in result.stale],
                         [("ship_type_cutter", "a ship type flag takes no comment")])


class FleetEntityTests(_Case):
    def test_a_new_ship_type_missing_from_the_table_is_flagged(self):
        tree = self.tree(generator='SHIPS = [\n    ("ship_type_other", "ship_type_destroyer"),\n]\n')
        (flag,) = tree.audit().flags
        self.assertEqual((flag.kind, flag.name), ("no_fleet_entity", "ship_type_cutter"))
        self.assertIn("SHIPS", flag.detail)

    def test_a_row_without_its_generated_block_is_flagged_where_gfx_is_on_disk(self):
        tree = self.tree(fleet_entities="ship_type_other = {\n    ship_type = ship_type_other\n}\n")
        (flag,) = tree.audit().flags
        self.assertEqual((flag.kind, flag.name), ("no_fleet_entity", "ship_type_cutter"))
        self.assertIn("re-run", flag.detail)

    def test_a_generated_block_satisfies_it(self):
        tree = self.tree(fleet_entities="ship_type_cutter = {\n    ship_type = ship_type_cutter\n}\n")
        self.assertEqual(tree.flags(), [])

    def test_without_the_generator_the_check_is_reported_as_not_run(self):
        result = self.tree(generator=None).audit()
        self.assertEqual(result.flags, [])
        self.assertFalse(result.fleet_entities_checked)
        self.assertIn("## Not checked", rma.render_report(result))

    def test_a_table_of_another_shape_is_reported_as_not_checked(self):
        """A reshaped `SHIPS` must not raise: on a reload that would turn the
        whole audit into a `[post-load] FAILED` warning."""
        for generator in (
            'SHIPS = [{"ship": "ship_type_cutter", "template": "ship_type_destroyer"}]\n',
            "SHIPS = [1, 2, 3]\n",
            'SHIPS = {"ship_type_cutter": "ship_type_destroyer"}\n',
            "SHIPS = [()]\n",
            "SHIPS = build_table()\n",
            "SHIPS = [\n",
            "OTHER = []\n",
        ):
            with self.subTest(generator=generator):
                tree = self.tree(generator=generator)
                self.assertIsNone(rma.fleet_entity_table(tree.root))
                result = tree.audit()
                self.assertEqual(result.flags, [])
                self.assertFalse(result.fleet_entities_checked)

    def test_the_real_table_is_read_without_importing_the_generator(self):
        table = rma.fleet_entity_table(REPO)
        self.assertTrue(table)
        self.assertTrue(all(isinstance(name, str) and name.startswith("ship_type_") for name in table))
        new_types = {o.name for o in rma.scan_dir(REPO, rma.SHIP_TYPES_DIR) if o.directive is None}
        self.assertTrue(new_types)
        self.assertLessEqual(new_types, table)


class UnlistedModificationTests(_Case):
    _ORPHAN = (
        "utility_mod_helicopter_pad = {{{comment}\n"
        "    type = ship_mod_slot_utility_1\n"
        "    unlocking_technologies = {{ rapid_deployment_forces }}\n"
        "}}\n"
    )

    def test_a_modification_no_ship_type_lists_is_flagged(self):
        tree = self.tree(mods=_MODS + self._ORPHAN.format(comment=""))
        (flag,) = tree.audit().flags
        self.assertEqual((flag.kind, flag.name), ("unlisted_modification", "utility_mod_helicopter_pad"))
        self.assertEqual((flag.file, flag.line), ("common/ship_modifications/test.txt", 4))
        self.assertIn("ship_mod_slot_utility_1", flag.detail)
        self.assertIn("rapid_deployment_forces", flag.detail)

    def test_a_vanilla_ship_type_listing_it_is_enough(self):
        tree = self.tree(mods=_MODS + "REPLACE:utility_mod_searchlights = {\n    type = ship_mod_slot_utility_1\n}\n")
        self.assertEqual(tree.flags(), [])

    def test_a_repeated_modifications_key_keeps_every_slot_list(self):
        tree = self.tree(
            ship_types=_SHIP_TYPES.rstrip()[:-1]
            + "    modifications = {\n        ship_mod_slot_utility_1 = { utility_mod_radar }\n    }\n}\n",
            mods=_MODS + "utility_mod_radar = {\n    type = ship_mod_slot_utility_1\n}\n")
        result = tree.audit()
        self.assertEqual(result.flags, [])
        self.assertEqual(result.modifications_checked, 2)

    def test_a_repeated_slot_key_keeps_every_entry(self):
        tree = self.tree(
            ship_types=_SHIP_TYPES.replace(
                "        ship_mod_slot_guns = { ship_mod_cutter_guns }\n",
                "        ship_mod_slot_guns = { ship_mod_cutter_guns }\n"
                "        ship_mod_slot_guns = { ship_mod_cutter_guns_heavy }\n"),
            mods=_MODS + "ship_mod_cutter_guns_heavy = {\n    type = ship_mod_slot_guns\n}\n")
        self.assertEqual(tree.flags(), [])

    def test_a_slot_entry_an_inject_adds_to_a_ship_type_counts(self):
        mods = _MODS + "utility_mod_radar = {\n    type = ship_mod_slot_utility_1\n}\n"
        self.assertEqual(self.tree(mods=mods).flags(), [("unlisted_modification", "utility_mod_radar")])
        for target in ("ship_type_destroyer", "ship_type_cutter"):
            with self.subTest(target=target):
                tree = self.tree(mods=mods, ship_types=_SHIP_TYPES + f"""
                    INJECT:{target} = {{
                        modifications = {{
                            ship_mod_slot_utility_1 = {{ utility_mod_radar }}
                        }}
                    }}
                """)
                self.assertEqual(tree.flags(), [])

    def test_a_vanilla_modification_is_not_judged(self):
        # `utility_mod_vanilla_orphan` is in no slot list, and is vanilla's.
        result = self.tree().audit()
        self.assertEqual(result.flags, [])
        self.assertEqual(result.modifications_checked, 1)

    def test_a_tagged_comment_on_the_opening_line_exempts_it(self):
        tree = self.tree(mods=_MODS + self._ORPHAN.format(
            comment=" # REVIEWED 2026-11-12 (roster_membership): parked for the carrier rework"))
        (flag,) = tree.audit().flags
        self.assertEqual(flag.kind, "unlisted_modification")
        self.assertEqual(flag.exemption, {"date": "2026-11-12", "tag": "roster_membership",
                                          "rationale": "parked for the carrier rework"})

    def test_an_untagged_comment_does_not(self):
        tree = self.tree(mods=_MODS + self._ORPHAN.format(comment=" # REVIEWED 2026-11-12: parked"))
        (flag,) = tree.audit().flags
        self.assertIsNone(flag.exemption)

    def test_a_tag_on_a_listed_modification_is_stale(self):
        tree = self.tree(mods=_MODS.replace(
            "ship_mod_cutter_guns = {", "ship_mod_cutter_guns = { # REVIEWED 2026-11-12 (roster_membership): old"))
        result = tree.audit()
        self.assertEqual(result.flags, [])
        (stale,) = result.stale
        self.assertEqual((stale.name, stale.tag, stale.why), ("ship_mod_cutter_guns", "roster_membership", "remove it"))


class UnlistedPmTests(_Case):
    def test_a_production_method_no_group_lists_is_flagged(self):
        tree = self.tree(pms=_PMS + "pm_stray = {\n    texture = \"x.dds\"\n}\n")
        (flag,) = tree.audit().flags
        self.assertEqual((flag.kind, flag.name), ("unlisted_pm", "pm_stray"))
        self.assertEqual((flag.file, flag.line), ("common/production_methods/test.txt", 4))

    def test_a_vanilla_group_listing_it_is_enough(self):
        tree = self.tree(pms=_PMS + "REPLACE:pm_vanilla = {\n}\n")
        self.assertEqual(tree.flags(), [])

    def test_an_inject_onto_a_vanilla_method_is_not_judged(self):
        tree = self.tree(pms=_PMS + "INJECT:pm_vanilla_orphan = {\n    texture = \"y.dds\"\n}\n")
        result = tree.audit()
        self.assertEqual(result.flags, [])
        self.assertEqual(result.pms_checked, 1)

    def test_a_tagged_comment_exempts_it(self):
        tree = self.tree(pms=_PMS + "pm_stray = { # REVIEWED 2026-11-12 (roster_membership): next release\n}\n")
        (flag,) = tree.audit().flags
        self.assertEqual(flag.exemption["rationale"], "next release")


class ReportAndExitTests(_Case):
    def _main(self, tree: _Tree, *argv: str) -> tuple[int, str]:
        # `main` builds its own state from the tree's vanilla_parsed/, which a
        # fixture has none of: every vanilla name is then unknown, so the
        # fixtures here stand on mod data alone.
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = rma.main(list(argv), mod_path=tree.root)
        return code, out.getvalue()

    def _mod_only_tree(self, **kwargs) -> _Tree:
        tree = self.tree(**kwargs)
        with open(os.path.join(tree.root, "common/ai_ship_categories/test.txt"), "w", encoding="utf-8") as fh:
            fh.write(_VANILLA_CATEGORIES)
        return tree

    def test_strict_passes_on_a_sound_tree(self):
        code, text = self._main(self._mod_only_tree(), "--strict")
        self.assertEqual(code, 0)
        self.assertIn("## Unreviewed Flags\n\n_None._", text)

    def test_strict_fails_on_each_broken_definition(self):
        broken = {
            "missing_ai_category": {"ship_types": _SHIP_TYPES.replace(
                "    ai_ship_category = ai_ship_category_screens\n", "")},
            "unknown_ai_category": {"ship_types": _SHIP_TYPES.replace("_screens", "_nope")},
            "no_fleet_entity": {"generator": "SHIPS = []\n"},
            "unlisted_modification": {"mods": _MODS + "utility_mod_stray = {\n}\n"},
            "unlisted_pm": {"pms": _PMS + "pm_stray = {\n}\n"},
            "stale_review": {"pms": _PMS.replace(
                "pm_mod = {", "pm_mod = { # REVIEWED 2026-11-12 (roster_membership): old")},
        }
        self.assertEqual(set(broken), set(rma.KIND_ORDER))
        for kind, kwargs in broken.items():
            with self.subTest(kind=kind):
                tree = self._mod_only_tree(**kwargs)
                code, text = self._main(tree, "--strict")
                self.assertEqual(code, 1)
                self.assertIn(f"### {kind}", text)
                # Without --strict the report prints and the exit is clean.
                self.assertEqual(self._main(tree)[0], 0)

    def test_a_reviewed_flag_passes_strict_and_is_listed_without_a_line(self):
        tree = self._mod_only_tree(
            mods=_MODS + "utility_mod_stray = { # REVIEWED 2026-11-12 (roster_membership): parked\n}\n")
        code, text = self._main(tree, "--strict")
        self.assertEqual(code, 0)
        self.assertIn(
            "- unlisted_modification: `utility_mod_stray` (common/ship_modifications/test.txt) — "
            "**2026-11-12**: parked", text)

    def test_the_report_counts_no_coverage(self):
        """A committed report changes only when its findings do (#494)."""
        bigger = self.tree(
            pm_groups="pmg_mod = { production_methods = { pm_mod pm_more } }\n",
            pms=_PMS + "pm_more = {\n}\n",
        ).audit()
        self.assertEqual(bigger.pms_checked, 2)
        self.assertEqual(rma.render_report(bigger), rma.render_report(self.tree().audit()))


class LiveModTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.state = rma.load_state(REPO)
        cls.result = rma.audit(cls.state, mod_path=REPO)

    def test_the_mod_is_clean(self):
        unreviewed = [f for f in self.result.flags if not f.exemption]
        self.assertEqual(unreviewed, [], rma.render_report(self.result))
        self.assertEqual(self.result.stale, [], rma.render_report(self.result))

    def test_the_pass_is_not_vacuous(self):
        self.assertGreaterEqual(self.result.ship_types_checked, 19)
        self.assertGreater(self.result.modifications_checked, 200)
        self.assertGreater(self.result.pms_checked, 1500)
        self.assertTrue(self.result.fleet_entities_checked)
        categories = self.state.get_data("AI Ship Categories")
        self.assertIn("ai_ship_category_submarines", categories)
        self.assertGreater(len(rma.listed_modifications(self.state.get_data("Ship Types"))), 400)
        self.assertGreater(len(rma.listed_pms(self.state.get_data("PM Groups"))), 2000)


if __name__ == "__main__":
    unittest.main()
