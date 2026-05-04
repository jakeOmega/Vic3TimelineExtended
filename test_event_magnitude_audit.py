"""Unit tests for event_magnitude_audit.

Run: python3 test_event_magnitude_audit.py
"""
import os
import tempfile
import unittest

from event_magnitude_audit import (
    FAST_SCALING_MODIFIERS,
    DIRECT_EFFECTS,
    ResourceMeta,
    find_event_id_at_line,
    parse_reviewed_comment,
    scan_direct_effects,
    scan_inline_modifier_types,
    scan_named_modifiers,
    AuditFlag,
    audit,
    AuditResult,
    render_report,
)


def _eq(value):
    """Wrap a scalar/dict in the parser's ('=', value) tuple form."""
    return ("=", value)


class RegistryTests(unittest.TestCase):
    def test_registry_has_prestige(self):
        self.assertIn("country_prestige_add", FAST_SCALING_MODIFIERS)
        meta = FAST_SCALING_MODIFIERS["country_prestige_add"]
        self.assertEqual(meta.resource, "prestige")

    def test_registry_has_bureaucracy(self):
        self.assertIn("country_bureaucracy_add", FAST_SCALING_MODIFIERS)

    def test_registry_has_money_flows(self):
        for key in ("country_expenses_add", "country_tax_income_add", "country_minting_add"):
            self.assertIn(key, FAST_SCALING_MODIFIERS)
            self.assertIn("treasury (weekly flow)", FAST_SCALING_MODIFIERS[key].resource)

    def test_registry_has_add_treasury_direct(self):
        self.assertIn("add_treasury", DIRECT_EFFECTS)
        meta = DIRECT_EFFECTS["add_treasury"]
        self.assertIn("treasury", meta.resource)


class EventIdResolutionTests(unittest.TestCase):
    def test_simple(self):
        text = (
            "namespace = test_events\n"
            "\n"
            "test_events.1 = {\n"
            "  type = country_event\n"
            "  immediate = {\n"
            "    add_treasury = -100\n"
            "  }\n"
            "}\n"
        )
        # add_treasury sits on line 6
        self.assertEqual(find_event_id_at_line(text, line_no=6), "test_events.1")

    def test_multiple_events_in_file(self):
        text = (
            "test_events.1 = {\n"
            "  immediate = { add_treasury = -100 }\n"
            "}\n"
            "test_events.2 = {\n"
            "  immediate = { add_treasury = -200 }\n"
            "}\n"
        )
        # second add_treasury sits on line 5
        self.assertEqual(find_event_id_at_line(text, line_no=5), "test_events.2")

    def test_inject_replace_prefixes(self):
        text = (
            "REPLACE:foo.5 = {\n"
            "  immediate = { add_treasury = -1 }\n"
            "}\n"
            "INJECT:bar.7 = {\n"
            "  immediate = { add_treasury = -2 }\n"
            "}\n"
        )
        self.assertEqual(find_event_id_at_line(text, line_no=2), "foo.5")
        self.assertEqual(find_event_id_at_line(text, line_no=5), "bar.7")

    def test_no_event_returns_none(self):
        text = "namespace = test_events\n# just a comment\n"
        self.assertIsNone(find_event_id_at_line(text, line_no=2))

    def test_out_of_range_returns_none(self):
        text = "test_events.1 = {\n}\n"
        self.assertIsNone(find_event_id_at_line(text, line_no=99))


class SuppressionCommentTests(unittest.TestCase):
    def test_full_form(self):
        line = "    multiplier = 2000  # REVIEWED 2026-05-04: tech-gated; intentionally large"
        result = parse_reviewed_comment(line)
        self.assertIsNotNone(result)
        self.assertEqual(result["date"], "2026-05-04")
        self.assertEqual(result["rationale"], "tech-gated; intentionally large")

    def test_missing_date_rejected(self):
        line = "    multiplier = 2000  # REVIEWED: no date here"
        self.assertIsNone(parse_reviewed_comment(line))

    def test_missing_rationale_rejected(self):
        line = "    multiplier = 2000  # REVIEWED 2026-05-04"
        self.assertIsNone(parse_reviewed_comment(line))

    def test_no_comment_at_all(self):
        line = "    multiplier = 2000"
        self.assertIsNone(parse_reviewed_comment(line))

    def test_unrelated_comment(self):
        line = "    multiplier = 2000  # just a regular comment"
        self.assertIsNone(parse_reviewed_comment(line))


class DirectEffectScannerTests(unittest.TestCase):
    def test_flags_literal(self):
        text = (
            "test_events.1 = {\n"
            "  immediate = {\n"
            "    add_treasury = -10000\n"
            "  }\n"
            "}\n"
        )
        flags = scan_direct_effects(text, file_path="events/foo.txt")
        self.assertEqual(len(flags), 1)
        f = flags[0]
        self.assertEqual(f.event_id, "test_events.1")
        self.assertEqual(f.effect, "add_treasury")
        self.assertEqual(f.value, "-10000")
        self.assertEqual(f.resource, "treasury (instant)")
        self.assertIsNone(f.exemption)
        self.assertEqual(f.line, 3)
        self.assertEqual(f.kind, "direct_effect")

    def test_skips_script_value(self):
        text = (
            "test_events.1 = {\n"
            "  immediate = { add_treasury = sv_treasury_event_small }\n"
            "}\n"
        )
        self.assertEqual(scan_direct_effects(text, file_path="x.txt"), [])

    def test_reviewed_becomes_exemption(self):
        text = (
            "test_events.1 = {\n"
            "  immediate = {\n"
            "    add_treasury = -10000  # REVIEWED 2026-05-04: vanilla precedent\n"
            "  }\n"
            "}\n"
        )
        flags = scan_direct_effects(text, file_path="x.txt")
        self.assertEqual(len(flags), 1)
        self.assertIsNotNone(flags[0].exemption)
        self.assertEqual(flags[0].exemption["rationale"], "vanilla precedent")

    def test_skips_zero(self):
        # Zero is a literal but not actionable; treat as a no-op.
        text = (
            "test_events.1 = {\n"
            "  immediate = { add_treasury = 0 }\n"
            "}\n"
        )
        flags = scan_direct_effects(text, file_path="x.txt")
        # We still flag zero since it's a literal — it's the user's choice
        # whether to # REVIEWED it. Confirm at least the regex matches.
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0].value, "0")


class InlineModifierScannerTests(unittest.TestCase):
    def test_flags_inline_prestige(self):
        text = (
            "test_events.1 = {\n"
            "  immediate = {\n"
            "    add_modifier = {\n"
            "      country_prestige_add = 100\n"
            "    }\n"
            "  }\n"
            "}\n"
        )
        flags = scan_inline_modifier_types(text, file_path="x.txt")
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0].effect, "country_prestige_add")
        self.assertEqual(flags[0].value, "100")
        self.assertEqual(flags[0].kind, "modifier_inline")

    def test_skips_mult_modifier(self):
        text = (
            "test_events.1 = {\n"
            "  immediate = { add_modifier = { country_prestige_mult = 0.05 } }\n"
            "}\n"
        )
        self.assertEqual(scan_inline_modifier_types(text, file_path="x.txt"), [])

    def test_skips_unrelated_modifier(self):
        text = (
            "test_events.1 = {\n"
            "  immediate = { add_modifier = { country_authority_add = 100 } }\n"
            "}\n"
        )
        self.assertEqual(scan_inline_modifier_types(text, file_path="x.txt"), [])


def _fake_static_modifier_lookup(name):
    return {
        "prestige_loss_X": {"country_prestige_add": "1"},
        "boring_modifier": {"country_authority_add": "10"},
        "mult_modifier": {"country_prestige_mult": "-0.05"},
        "multi_field_modifier": {
            "country_prestige_add": "1",
            "country_authority_add": "10",
        },
    }.get(name)


class NamedModifierScannerTests(unittest.TestCase):
    def test_flags_prestige_via_named_modifier(self):
        text = (
            "test_events.1 = {\n"
            "  immediate = {\n"
            "    add_modifier = {\n"
            "      name = prestige_loss_X\n"
            "      multiplier = -20\n"
            "    }\n"
            "  }\n"
            "}\n"
        )
        flags = scan_named_modifiers(text, file_path="x.txt", lookup=_fake_static_modifier_lookup)
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0].effect, "country_prestige_add")
        self.assertEqual(flags[0].value, "-20")
        # Line should point at the `multiplier` line (the actionable value).
        self.assertEqual(flags[0].line, 5)
        self.assertEqual(flags[0].kind, "modifier_named")
        self.assertEqual(flags[0].event_id, "test_events.1")

    def test_skips_mult_modifier(self):
        text = (
            "test_events.1 = {\n"
            "  immediate = {\n"
            "    add_modifier = { name = mult_modifier multiplier = -0.1 }\n"
            "  }\n"
            "}\n"
        )
        self.assertEqual(
            scan_named_modifiers(text, file_path="x.txt", lookup=_fake_static_modifier_lookup),
            [],
        )

    def test_skips_when_multiplier_is_script_value(self):
        text = (
            "test_events.1 = {\n"
            "  immediate = {\n"
            "    add_modifier = {\n"
            "      name = prestige_loss_X\n"
            "      multiplier = sv_prestige_event_small\n"
            "    }\n"
            "  }\n"
            "}\n"
        )
        self.assertEqual(
            scan_named_modifiers(text, file_path="x.txt", lookup=_fake_static_modifier_lookup),
            [],
        )

    def test_skips_unknown_static_modifier(self):
        # Without a lookup hit we can't know whether the modifier is fast-scaling.
        text = (
            "test_events.1 = {\n"
            "  immediate = {\n"
            "    add_modifier = { name = unknown_modifier multiplier = -20 }\n"
            "  }\n"
            "}\n"
        )
        self.assertEqual(
            scan_named_modifiers(text, file_path="x.txt", lookup=_fake_static_modifier_lookup),
            [],
        )

    def test_no_multiplier_flags_when_static_modifier_has_hardcoded_fast_field(self):
        # `add_modifier { name = X }` with X carrying hardcoded
        # country_prestige_add IS a problem: it applies a flat -N prestige
        # that goes invisible at scale. Flag with the no-mult kind.
        text = (
            "test_events.1 = {\n"
            "  immediate = {\n"
            "    add_modifier = { name = prestige_loss_X }\n"
            "  }\n"
            "}\n"
        )
        flags = scan_named_modifiers(text, file_path="x.txt", lookup=_fake_static_modifier_lookup)
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0].kind, "modifier_named_no_mult")
        self.assertEqual(flags[0].effect, "country_prestige_add")
        # Value reports `field=raw_value (in name)` so the audit reader sees
        # both the underlying magnitude and the static modifier carrying it.
        self.assertIn("country_prestige_add=", flags[0].value)
        self.assertIn("prestige_loss_X", flags[0].value)
        # The fix hint mentions the static modifier name and the alternative.
        self.assertIn("prestige_loss_X", flags[0].fix_hint)

    def test_multi_field_modifier_emits_one_flag_per_fast_field(self):
        text = (
            "test_events.1 = {\n"
            "  immediate = {\n"
            "    add_modifier = { name = multi_field_modifier multiplier = -20 }\n"
            "  }\n"
            "}\n"
        )
        flags = scan_named_modifiers(text, file_path="x.txt", lookup=_fake_static_modifier_lookup)
        # multi_field_modifier has prestige_add (fast) + authority_add (not fast)
        # — only one flag emitted, for the fast field.
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0].effect, "country_prestige_add")


class _StubModState:
    """Minimal ModState fake for audit()."""

    def __init__(self, static_modifiers: dict):
        self._sm = static_modifiers

    def get_data(self, key):
        # ModState's entity-type label is "Modifiers" for static modifiers.
        if key == "Modifiers":
            return self._sm
        return {}


class AuditEntrypointTests(unittest.TestCase):
    def test_end_to_end_on_tempdir(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.makedirs(os.path.join(tmp, "events"))
            with open(os.path.join(tmp, "events", "test_events.txt"), "w") as f:
                f.write(
                    "test_events.1 = {\n"
                    "  immediate = {\n"
                    "    add_modifier = { name = prestige_loss_X multiplier = -20 }\n"
                    "    add_treasury = -10000\n"
                    "    add_treasury = -50000  # REVIEWED 2026-05-04: era-tagged\n"
                    "  }\n"
                    "}\n"
                )
            ms = _StubModState(
                static_modifiers={
                    "prestige_loss_X": _eq({"country_prestige_add": _eq("1")}),
                },
            )
            result = audit(ms, mod_path=tmp)
            self.assertIsInstance(result, AuditResult)
            unrev = [f for f in result.flags if not f.exemption]
            exemp = [f for f in result.flags if f.exemption]
            # 1 named-modifier flag (prestige) + 1 unreviewed direct effect
            self.assertEqual(len(unrev), 2)
            self.assertEqual(len(exemp), 1)
            self.assertEqual(result.coverage["files_audited"], 1)

    def test_no_events_dir_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            ms = _StubModState(static_modifiers={})
            result = audit(ms, mod_path=tmp)
            self.assertEqual(result.flags, [])
            self.assertEqual(result.coverage["files_audited"], 0)


class ReportRenderTests(unittest.TestCase):
    def test_basic_render(self):
        flags = [
            AuditFlag(
                file="events/foo.txt", line=10, event_id="foo.1",
                kind="direct_effect", effect="add_treasury", value="-10000",
                resource="treasury (instant)",
                fix_hint="use add_treasury = sv_treasury_event_<tier>",
            ),
            AuditFlag(
                file="events/bar.txt", line=42, event_id="bar.7",
                kind="modifier_named", effect="country_prestige_add", value="-20",
                resource="prestige", fix_hint="use prestige_loss_<tier>",
                exemption={"date": "2026-05-04", "rationale": "tech-gated"},
            ),
        ]
        result = AuditResult(flags=flags, coverage={"files_audited": 2})
        md = render_report(result)
        self.assertIn("## Unreviewed Flags", md)
        self.assertIn("foo.1", md)
        self.assertIn("treasury (instant)", md)
        self.assertIn("## Reviewed Exemptions", md)
        self.assertIn("bar.7", md)
        self.assertIn("tech-gated", md)
        self.assertIn("## Coverage", md)
        self.assertIn("files_audited", md)

    def test_empty_render(self):
        result = AuditResult(flags=[], coverage={"files_audited": 0})
        md = render_report(result)
        self.assertIn("_None._", md)


if __name__ == "__main__":
    unittest.main()
