"""Unit tests for script_loc_reference_audit.

The crux is which `field = value` pairs count as loc references: `desc` on a
breakdown line does, `text` only inside `custom_tooltip`, and parameterized or
block values never do.
"""
from __future__ import annotations

import os
import tempfile
import unittest

from script_loc_reference_audit import (
    LOC_REFERENCE_FIELDS, audit, iter_references, render_report,
)


def _refs(text: str) -> list[tuple[int, str, str]]:
    return [(line, fld, key) for line, fld, key, _ in iter_references(text)]


def _write(root: str, rel: str, text: str) -> None:
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8-sig") as fh:
        fh.write(text)


class ReferenceTests(unittest.TestCase):
    def test_breakdown_desc_is_a_reference(self):
        text = (
            "additional_radicalism_factors = {\n"
            "\tadd = {\n"
            "\t\tvalue = 1\n"
            '\t\tdesc = "INSTITUTION_FUNDING_LEVEL_ministry_of_foreign_affairs"\n'
            "\t}\n"
            "}\n"
        )
        self.assertEqual(
            _refs(text),
            [(4, "desc", "INSTITUTION_FUNDING_LEVEL_ministry_of_foreign_affairs")],
        )

    def test_unquoted_and_dotted_keys(self):
        self.assertEqual(
            _refs("e = { title = te_x.1.t flavor = te_x.1.f }\n"),
            [(1, "title", "te_x.1.t"), (1, "flavor", "te_x.1.f")],
        )

    def test_parameterized_yes_no_and_prose_skipped(self):
        text = (
            "custom_tooltip = je_$NAME$_tt\n"
            "desc = yes\n"
            'desc = "some prose with spaces"\n'
            "custom_tooltip = scope:foo\n"
        )
        self.assertEqual(_refs(text), [])

    def test_text_counts_only_inside_custom_tooltip(self):
        text = (
            "custom_tooltip = {\n"
            "\ttext = my_tooltip_key\n"
            "\tsubject = scope:target\n"
            "}\n"
            "custom_description = {\n"
            "\ttext = my_trigger_localization\n"
            "}\n"
            "text = stray\n"
        )
        self.assertEqual(_refs(text), [(2, "text", "my_tooltip_key")])

    def test_block_desc_checks_the_inner_keys_only(self):
        text = (
            "desc = {\n"
            "\tfirst_valid = {\n"
            "\t\ttriggered_desc = { trigger = { always = yes } desc = inner_a }\n"
            "\t\ttriggered_desc = {\n"
            "\t\t\tdesc = inner_b\n"
            "\t\t}\n"
            "\t}\n"
            "}\n"
        )
        self.assertEqual(_refs(text), [(3, "desc", "inner_a"), (5, "desc", "inner_b")])

    def test_name_and_trigger_localization_fields_not_checked(self):
        self.assertNotIn("name", LOC_REFERENCE_FIELDS)
        self.assertNotIn("first", LOC_REFERENCE_FIELDS)
        self.assertEqual(_refs("name = my_flag\nfirst = SOME_TRIGGER_FIRST\n"), [])

    def test_hash_inside_quotes_is_not_a_comment(self):
        refs = list(iter_references('custom_tooltip = "a#b" desc = real_key # trailing\n'))
        self.assertEqual([(r[1], r[2]) for r in refs], [("desc", "real_key")])
        self.assertEqual(refs[0][3], "# trailing")


class AuditTests(unittest.TestCase):
    def test_flags_unresolved_and_honours_reviewed(self):
        with tempfile.TemporaryDirectory() as root:
            _write(root, "common/political_movements/m.txt", (
                "m = {\n"
                "\tadditional_radicalism_factors = {\n"
                '\t\tadd = { value = 1 desc = "MISSING_KEY" }\n'
                '\t\tadd = { value = 1 desc = "PRESENT_KEY" }\n'
                '\t\tadd = { value = 1 desc = "WAIVED_KEY" } # REVIEWED 2026-09-25: test\n'
                "\t}\n"
                "}\n"
            ))
            _write(root, "events/e.txt", "e.1 = { type = country_event title = e.1.t }\n")
            _write(root, "gui/ignored.txt", 'desc = "NOT_SCANNED"\n')
            result = audit({"PRESENT_KEY"}.__contains__, mod_path=root)

        by_key = {f.key: f for f in result.flags}
        self.assertEqual(set(by_key), {"MISSING_KEY", "WAIVED_KEY", "e.1.t"})
        self.assertEqual(by_key["MISSING_KEY"].file, os.path.join("common", "political_movements", "m.txt"))
        self.assertEqual(by_key["MISSING_KEY"].line, 3)
        self.assertIsNone(by_key["MISSING_KEY"].exemption)
        self.assertEqual(by_key["WAIVED_KEY"].exemption, {"date": "2026-09-25", "rationale": "test"})
        self.assertEqual(result.files_audited, 2)
        self.assertEqual(result.references_checked, 4)

    def test_render_smoke(self):
        with tempfile.TemporaryDirectory() as root:
            _write(root, "common/x/a.txt", "add = { desc = GONE }\n")
            report = render_report(audit(lambda k: False, mod_path=root))
        self.assertIn("`desc = GONE`", report)
        self.assertIn("- unreviewed: 1", report)
        self.assertIn("_None._", render_report(audit(lambda k: True, mod_path=root)))


class RegistrationTests(unittest.TestCase):
    def test_registered_as_post_load_audit(self):
        # Read the roster from source: importing mod_state_server needs the
        # per-machine paths, and this test must run in CI without them.
        here = os.path.dirname(os.path.abspath(__file__))
        with open(os.path.join(here, "mod_state_server.py"), encoding="utf-8") as fh:
            src = fh.read()
        roster = src[src.index("POST_LOAD_AUDITS = ["):]
        roster = roster[:roster.index("]")]
        self.assertIn('"script_loc_reference_audit"', roster)


class VanillaHoldTests(unittest.TestCase):
    """The field catalog is read off vanilla, so vanilla must satisfy it: every
    reference in vanilla `common/` and `events/` resolves to a vanilla key,
    bar one vanilla bug. Needs a game install; skipped without one. A failure
    after a vanilla bump means re-derive the catalog (or add the new vanilla
    bug below), not a mod bug."""

    KNOWN_VANILLA_MISSES = {"POP_SERVICEMEN"}

    def test_every_vanilla_reference_resolves(self):
        try:
            from path_constants import base_game_path
            game = os.path.join(base_game_path, "game")
        except RuntimeError:
            self.skipTest("no Victoria 3 install")
        if not os.path.isdir(os.path.join(game, "common")):
            self.skipTest("no Victoria 3 install")
        import vanilla_parsed
        loc = vanilla_parsed.load().localization
        checked, misses = 0, {}
        for sub in ("common", "events"):
            for root, _dirs, files in os.walk(os.path.join(game, sub)):
                for fname in files:
                    if not fname.endswith(".txt"):
                        continue
                    path = os.path.join(root, fname)
                    with open(path, encoding="utf-8-sig", errors="replace") as fh:
                        for line, _fld, key, _c in iter_references(fh.read()):
                            checked += 1
                            if key not in loc:
                                misses[key] = f"{os.path.relpath(path, game)}:{line}"
        self.assertGreater(checked, 10000)
        self.assertEqual(set(misses) - self.KNOWN_VANILLA_MISSES, set(), misses)


if __name__ == "__main__":
    unittest.main()
