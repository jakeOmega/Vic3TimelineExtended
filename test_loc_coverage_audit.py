"""Unit tests for loc_coverage_audit.

Run: python3 test_loc_coverage_audit.py
"""
import os
import tempfile
import unittest

from loc_coverage_audit import (
    audit,
    render_report,
    _event_loc_keys,
    _parse_reviewed,
    _build_entity_locations,
)


class FakeParser:
    def __init__(self, data: dict):
        self.data = data


class FakeMS:
    """Minimal stand-in for ModState. The audit only touches `base_parsers`,
    `mod_parsers`, and `has_localization`."""

    def __init__(
        self,
        mod_data: dict[str, dict],
        base_data: dict[str, dict] | None = None,
        loc_keys: set[str] | None = None,
    ):
        self.base_parsers = {k: FakeParser(v) for k, v in (base_data or {}).items()}
        self.mod_parsers = {k: FakeParser(v) for k, v in mod_data.items()}
        self._loc = loc_keys or set()

    def has_localization(self, key: str) -> bool:
        return key in self._loc


def _write(tmp: str, rel: str, content: str) -> str:
    path = os.path.join(tmp, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    return path


class ParseReviewedTests(unittest.TestCase):
    def test_match(self):
        result = _parse_reviewed("# REVIEWED 2026-05-08: backwards-compat alias")
        self.assertEqual(result, {"date": "2026-05-08", "rationale": "backwards-compat alias"})

    def test_no_match(self):
        self.assertIsNone(_parse_reviewed("# just a comment"))
        self.assertIsNone(_parse_reviewed(None))
        self.assertIsNone(_parse_reviewed(""))


class EventLocKeysTests(unittest.TestCase):
    def test_full(self):
        ev = {
            "type": "country_event",
            "title": "evt.1.t",
            "desc": "evt.1.d",
            "flavor": "evt.1.f",
            "option": [{"name": "evt.1.a"}, {"name": "evt.1.b"}],
        }
        keys = _event_loc_keys("evt.1", ev)
        ks = {k for k, _, _ in keys}
        self.assertIn("evt.1.t", ks)
        self.assertIn("evt.1.d", ks)
        self.assertIn("evt.1.f", ks)
        self.assertIn("evt.1.a", ks)
        self.assertIn("evt.1.b", ks)

    def test_flavor_optional(self):
        ev = {"type": "country_event", "title": "x.t", "desc": "x.d"}
        keys = dict((k, req) for k, req, _ in _event_loc_keys("x", ev))
        self.assertTrue(keys["x.t"])
        self.assertTrue(keys["x.d"])

    def test_single_option_dict(self):
        # The parser sometimes hands us a dict instead of a list when there's
        # one option block. Audit must handle both.
        ev = {"type": "country_event", "title": "x.t", "desc": "x.d",
              "option": {"name": "x.a"}}
        ks = {k for k, _, _ in _event_loc_keys("x", ev)}
        self.assertIn("x.a", ks)

    def test_skips_non_event_entries(self):
        # Parser surfaces top-level `namespace = X` directives in the same
        # data dict. They lack a `type` field — must be skipped, not flagged.
        keys = _event_loc_keys("namespace", "nuclear_weapon_events")
        self.assertEqual(keys, [])

    def test_unwraps_parser_tuples(self):
        # Real ModState data wraps every assignment as ('=', value).
        ev = ("=", {
            "type": ("=", "country_event"),
            "title": ("=", "evt.t"),
            "desc": ("=", "evt.d"),
            "option": ("=", [("=", {"name": ("=", '"evt.a"')})]),
        })
        ks = {k for k, _, _ in _event_loc_keys("evt", ev)}
        self.assertEqual(ks, {"evt.t", "evt.d", "evt.a"})


class ScriptedButtonTests(unittest.TestCase):
    def test_explicit_name_field_used(self):
        from loc_coverage_audit import _explicit_name_field
        body = {"name": '"CR_GRASSROOTS_ORGANIZING"', "desc": '"CR_GRASSROOTS_ORGANIZING_DESC"'}
        keys = _explicit_name_field("cr_grassroots_organizing", body)
        ks = dict((k, req) for k, req, _ in keys)
        # Must check the loc key from the `name` field, not the entity name
        self.assertIn("CR_GRASSROOTS_ORGANIZING", ks)
        self.assertNotIn("cr_grassroots_organizing", ks)
        self.assertTrue(ks["CR_GRASSROOTS_ORGANIZING"])
        self.assertFalse(ks["CR_GRASSROOTS_ORGANIZING_DESC"])  # desc optional

    def test_handles_missing_name_field(self):
        from loc_coverage_audit import _explicit_name_field
        # Button with no `name` field — should produce no requirements
        # (better than flagging a phantom key).
        self.assertEqual(_explicit_name_field("button_x", {}), [])


class BuildEntityLocationsTests(unittest.TestCase):
    def test_finds_opening_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(
                tmp, "common/static_modifiers/foo.txt",
                "prestige_loss_tiny = {\n"
                "    country_prestige_mult = -0.005\n"
                "}\n"
            )
            locs = _build_entity_locations(
                tmp, "common/static_modifiers", {"prestige_loss_tiny"}
            )
            self.assertIn("prestige_loss_tiny", locs)
            rel, line, comment = locs["prestige_loss_tiny"]
            self.assertEqual(line, 1)
            self.assertIsNone(comment)

    def test_captures_trailing_comment(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(
                tmp, "common/static_modifiers/foo.txt",
                "prestige_loss_tiny = { # REVIEWED 2026-05-08: alias\n"
                "}\n"
            )
            locs = _build_entity_locations(
                tmp, "common/static_modifiers", {"prestige_loss_tiny"}
            )
            _, _, comment = locs["prestige_loss_tiny"]
            self.assertIsNotNone(comment)
            self.assertIn("REVIEWED", comment)


class AuditTests(unittest.TestCase):
    def _scaffold(self, *, mod_modifiers: dict, base_modifiers: dict | None = None,
                  loc_keys: set | None = None, source_lines: dict | None = None):
        """Build (ms, tmp_path) with synthetic mod sources written to tmp."""
        tmp = tempfile.mkdtemp()
        # Write source files for each entity-name to enable file:line resolution
        if source_lines is None:
            source_lines = {
                name: f"{name} = {{\n}}\n" for name in mod_modifiers
            }
        if mod_modifiers:
            blob = "\n".join(source_lines[name] for name in mod_modifiers if name in source_lines)
            _write(tmp, "common/static_modifiers/extra_modifiers.txt", blob)
        ms = FakeMS(
            mod_data={"Modifiers": mod_modifiers},
            base_data={"Modifiers": base_modifiers or {}},
            loc_keys=loc_keys or set(),
        )
        return ms, tmp

    def test_unlocalized_modifier_flagged(self):
        ms, tmp = self._scaffold(
            mod_modifiers={"prestige_loss_tiny": {}},
            loc_keys=set(),
        )
        result = audit(ms, mod_path=tmp)
        self.assertEqual(len(result.flags), 1)
        f = result.flags[0]
        self.assertEqual(f.entity, "prestige_loss_tiny")
        self.assertEqual(f.category, "Modifiers")
        self.assertEqual(f.missing_keys, ["prestige_loss_tiny"])
        self.assertIsNone(f.exemption)

    def test_localized_modifier_not_flagged(self):
        ms, tmp = self._scaffold(
            mod_modifiers={"prestige_loss_tiny": {}},
            loc_keys={"prestige_loss_tiny"},
        )
        result = audit(ms, mod_path=tmp)
        self.assertEqual(result.flags, [])

    def test_reviewed_modifier_exempted(self):
        ms, tmp = self._scaffold(
            mod_modifiers={"prestige_loss_tiny": {}},
            loc_keys=set(),
            source_lines={
                "prestige_loss_tiny": "prestige_loss_tiny = { # REVIEWED 2026-05-08: alias\n}\n",
            },
        )
        result = audit(ms, mod_path=tmp)
        self.assertEqual(len(result.flags), 1)
        f = result.flags[0]
        self.assertIsNotNone(f.exemption)
        self.assertEqual(f.exemption["date"], "2026-05-08")
        self.assertEqual(f.exemption["rationale"], "alias")

    def test_vanilla_override_not_flagged(self):
        # Modifier present in BOTH base and mod parsers — it's a vanilla
        # override, not net-new. Vanilla loc applies; audit must skip.
        ms, tmp = self._scaffold(
            mod_modifiers={"country_prestige_mult": {}},
            base_modifiers={"country_prestige_mult": {}},
            loc_keys=set(),  # even with no mod loc, vanilla loc covers it
        )
        result = audit(ms, mod_path=tmp)
        self.assertEqual(result.flags, [])

    def test_event_missing_title_flagged(self):
        tmp = tempfile.mkdtemp()
        _write(tmp, "events/test_events.txt",
               "test_events.1 = {\n"
               "  type = country_event\n"
               "  title = test_events.1.t\n"
               "  desc = test_events.1.d\n"
               "}\n")
        ms = FakeMS(
            mod_data={"Events": {"test_events.1": {
                "type": "country_event",
                "title": "test_events.1.t",
                "desc": "test_events.1.d",
            }}},
            base_data={"Events": {}},
            loc_keys={"test_events.1.d"},  # title key missing
        )
        result = audit(ms, mod_path=tmp)
        self.assertEqual(len(result.flags), 1)
        f = result.flags[0]
        self.assertEqual(f.category, "Events")
        self.assertIn("test_events.1.t", f.missing_keys)
        self.assertNotIn("test_events.1.d", f.missing_keys)

    def test_event_fully_localized_not_flagged(self):
        tmp = tempfile.mkdtemp()
        _write(tmp, "events/test_events.txt", "test_events.1 = {\n}\n")
        ms = FakeMS(
            mod_data={"Events": {"test_events.1": {
                "type": "country_event",
                "title": "test_events.1.t",
                "desc": "test_events.1.d",
                "option": [{"name": "test_events.1.a"}],
            }}},
            base_data={"Events": {}},
            loc_keys={"test_events.1.t", "test_events.1.d", "test_events.1.a"},
        )
        result = audit(ms, mod_path=tmp)
        self.assertEqual(result.flags, [])

    def test_event_namespace_directive_skipped(self):
        # Parser surfaces `namespace = X` as a top-level entry alongside
        # actual events. Must be filtered out, not flagged.
        tmp = tempfile.mkdtemp()
        _write(tmp, "events/test_events.txt", "namespace = test_events\n")
        ms = FakeMS(
            mod_data={"Events": {"namespace": "test_events"}},
            base_data={"Events": {}},
            loc_keys=set(),
        )
        result = audit(ms, mod_path=tmp)
        self.assertEqual(result.flags, [])

    def test_journal_entry_missing_desc_flagged(self):
        tmp = tempfile.mkdtemp()
        _write(tmp, "common/journal_entries/x.txt", "je_test = {\n}\n")
        ms = FakeMS(
            mod_data={"Journal Entries": {"je_test": {}}},
            base_data={"Journal Entries": {}},
            loc_keys={"je_test"},  # title present, desc missing
        )
        result = audit(ms, mod_path=tmp)
        self.assertEqual(len(result.flags), 1)
        self.assertEqual(result.flags[0].missing_keys, ["je_test_desc"])

    def test_optional_desc_not_required(self):
        # Character traits: name required, desc optional. Missing desc alone
        # must NOT flag.
        tmp = tempfile.mkdtemp()
        _write(tmp, "common/character_traits/x.txt", "trait_brave = {\n}\n")
        ms = FakeMS(
            mod_data={"Character Traits": {"trait_brave": {}}},
            base_data={"Character Traits": {}},
            loc_keys={"trait_brave"},  # only name; desc missing but optional
        )
        result = audit(ms, mod_path=tmp)
        self.assertEqual(result.flags, [])


class RenderTests(unittest.TestCase):
    def test_empty_report_smoke(self):
        from loc_coverage_audit import AuditResult
        report = render_report(AuditResult(flags=[], coverage={"files_audited": 0, "by_category": {}}))
        self.assertIn("# Localization coverage audit report", report)
        self.assertIn("_None._", report)

    def test_populated_report_smoke(self):
        from loc_coverage_audit import AuditResult, LocFlag
        result = AuditResult(
            flags=[
                LocFlag(category="Modifiers", entity="x", missing_keys=["x"],
                        file="common/static_modifiers/y.txt", line=1, exemption=None),
            ],
            coverage={"files_audited": 1, "by_category": {"Modifiers": 1}},
        )
        report = render_report(result)
        self.assertIn("`common/static_modifiers/y.txt:1` — `x`", report)
        self.assertIn("Modifiers (1)", report)


if __name__ == "__main__":
    unittest.main()
