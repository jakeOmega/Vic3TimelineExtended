"""Delivery legs (2026-11-20 delivery spec §4; phase 1 plan Task 1, D2 and D3).

Two country triggers stand for the hardware: nd_fields_icbms and
nd_fields_missile_submarines. In phase 1 they read the technologies, and the
submarine leg also needs a coastal state to sail from. Phase 2 swaps their
bodies for the fielded variables and touches nothing else. So every read of
the two technologies is a delivery read and goes through the triggers, unless
it is about knowledge rather than hardware, which ALLOWED lists with its
reason."""

import re
import unittest

from test_nuclear_deterrence import ROOT, block, read, squash, strip_comments

TRIGGERS = ROOT / "common/scripted_triggers/nuclear_deterrence_triggers.txt"
VALUES = ROOT / "common/script_values/nuclear_deterrence_values.txt"
EFFECTS = ROOT / "common/scripted_effects/nuclear_deterrence_effects.txt"
INCIDENT_EVENTS = ROOT / "events/nuclear_incident_events.txt"
EXTRA_CUSTOM_LOC = ROOT / "common/customizable_localization/zzz_extra_custom_loc.txt"
CUSTOM_LOC = ROOT / "common/customizable_localization/nuclear_deterrence_custom_loc.txt"
LOC = ROOT / "localization/english"

TECH_READ = re.compile(r"\bhas_technology_researched\s*=\s*(ICBMs|advanced_submarine_technology)\b")
TOP_LEVEL = re.compile(r"^([A-Za-z_][\w:]*)\s*=\s*\{", re.M)

# (file, top-level block) -> why it reads the technology itself. A whole file
# is listed under block None.
ALLOWED = {
    ("common/scripted_triggers/nuclear_deterrence_triggers.txt", "nd_fields_icbms"):
        "the trigger itself",
    ("common/scripted_triggers/nuclear_deterrence_triggers.txt", "nd_fields_missile_submarines"):
        "the trigger itself",
    ("common/scripted_triggers/nuclear_taboo_triggers.txt", "nd_taboo_has_programme_standing"):
        "a Major Power's standing to run a programme comes from the technology: a project can't "
        "stand in for it, since only a country with a programme can run one (spec §4.2)",
    ("common/script_values/extra_script_values.txt", "global_tech_spread_script_value"):
        "the world's technology spread counts research",
    ("common/script_values/te_ai_probe_values.txt", "te_aip_tc_military_7"):
        "the AI probe counts researched technologies",
    ("common/ship_types/extra_ship_types.txt", "INJECT:ship_type_submarine"):
        "the old submarine's obsolescence is about the ship, not the missile",
    ("common/ai_strategies/edited_default_strategy.txt", "INJECT:ai_strategy_default"):
        "the naval AI's supply stance is about the ship, not the missile",
    ("common/scripted_effects/covert_tech_theft_generated.txt", None):
        "generated: covert theft grants the technology (scripts/generators)",
    ("common/scripted_triggers/covert_tech_theft_generated.txt", None):
        "generated: covert theft grants the technology (scripts/generators)",
    ("common/scripted_effects/te_research_commons_sync_generated.txt", None):
        "generated: the research commons shares the technology",
}


def tech_reads():
    """Every read of the two technologies in common/, events/ and gui/, as
    (repo path, line, enclosing top-level block)."""
    for top in ("common", "events", "gui"):
        for path in sorted((ROOT / top).rglob("*")):
            if path.suffix not in (".txt", ".gui"):
                continue
            text = read(path).lstrip("﻿")
            code = strip_comments(text)
            if not TECH_READ.search(code):
                continue
            heads = [(m.start(), m.group(1)) for m in TOP_LEVEL.finditer(code)]
            rel = path.relative_to(ROOT).as_posix()
            for m in TECH_READ.finditer(code):
                owner = None
                for start, name in heads:
                    if start > m.start():
                        break
                    owner = name
                yield rel, code.count("\n", 0, m.start()) + 1, owner


class TestDeliveryTriggers(unittest.TestCase):

    def setUp(self):
        self.triggers = strip_comments(read(TRIGGERS))

    def test_icbm_trigger(self):
        body = squash(block(self.triggers, "nd_fields_icbms"))
        self.assertIn("custom_tooltip = { text = nd_tt_fields_icbms has_technology_researched = ICBMs }", body)

    def test_submarine_trigger_needs_a_coast(self):
        body = squash(block(self.triggers, "nd_fields_missile_submarines"))
        self.assertIn("custom_tooltip = { text = nd_tt_fields_missile_submarines "
                      "has_technology_researched = advanced_submarine_technology "
                      "any_scope_state = { is_coastal = yes } }", body)

    def test_tooltips_have_loc(self):
        loc = "\n".join(read(p) for p in LOC.glob("*.yml"))
        for key in ("nd_tt_fields_icbms", "nd_tt_fields_missile_submarines"):
            self.assertRegex(loc, rf"(?m)^ {key}:0 \"")


class TestTechnologyReads(unittest.TestCase):
    """Every delivery read goes through the triggers (plan D3)."""

    def test_every_read_is_allowed(self):
        stray = [f"{path}:{line} ({owner})" for path, line, owner in tech_reads()
                 if (path, owner) not in ALLOWED and (path, None) not in ALLOWED]
        self.assertEqual(stray, [], "read nd_fields_icbms / nd_fields_missile_submarines instead, "
                                    "or add the site to ALLOWED with its reason")

    def test_allowlist_is_live(self):
        found = {(path, owner) for path, _, owner in tech_reads()} | {(path, None) for path, _, _ in tech_reads()}
        self.assertEqual([key for key in ALLOWED if key not in found], [], "an allowed site no longer reads it")


class TestIcbmReaders(unittest.TestCase):

    def setUp(self):
        self.triggers = strip_comments(read(TRIGGERS))
        self.values = strip_comments(read(VALUES))

    def test_reach(self):
        self.assertIn("$COUNTRY$ = { nd_fields_icbms = yes }", squash(block(self.triggers, "nd_state_in_reach_of")))
        self.assertIn("OR = { nd_fields_icbms = yes", squash(block(self.triggers, "nd_reaches_country")))
        self.assertIn("NOT = { nd_fields_icbms = yes }", squash(block(self.triggers, "nd_reach_limited")))
        refresh = squash(block(strip_comments(read(EFFECTS)), "nd_reach_refresh"))
        self.assertIn("nd_is_armed = yes NOT = { nd_fields_icbms = yes }", refresh)

    def test_launch_authorities(self):
        for name in ("nd_can_adopt_launch_on_warning", "nd_can_adopt_automatic_retaliation"):
            self.assertIn("nd_fields_icbms = yes", squash(block(self.triggers, name)), name)

    def test_values(self):
        self.assertIn("limit = { nd_fields_icbms = yes } value = 0.70", squash(block(self.values, "nd_exposure_factor_icbms")))
        self.assertIn("limit = { nd_fields_icbms = yes } add = 0.5", squash(block(self.values, "nd_k_ratio")))

    def test_incidents_and_the_attack_line(self):
        events = squash(strip_comments(read(INCIDENT_EVENTS)))
        self.assertIn("limit = { nd_fields_icbms = yes } set_variable = { name = nd_ic_unit value = 3 }", events)
        self.assertIn("limit = { nd_fields_icbms = yes } add = 20 } } set_variable = { name = nd_accident_kind value = 2 }",
                      events)
        attack = squash(block(strip_comments(read(EXTRA_CUSTOM_LOC)), "te_nuke_attack_icbms"))
        self.assertIn("trigger = { nd_fields_icbms = yes } localization_key = nuke_attack_line_icbms", attack)


class TestSubmarineReaders(unittest.TestCase):
    """A landlocked country has no submarine reach, factor or incident unit."""

    def setUp(self):
        self.triggers = strip_comments(read(TRIGGERS))

    def test_reach(self):
        state = squash(block(self.triggers, "nd_state_in_reach_of"))
        self.assertIn("AND = { is_coastal = yes $COUNTRY$ = { nd_fields_missile_submarines = yes } }", state)
        country = squash(block(self.triggers, "nd_reaches_country"))
        self.assertIn("AND = { nd_fields_missile_submarines = yes $TARGET$ = { any_scope_state = { is_coastal = yes } } }",
                      country)

    def test_survivability_incident_and_reach_row(self):
        factor = squash(block(strip_comments(read(VALUES)), "nd_exposure_factor_submarines"))
        self.assertIn("limit = { nd_fields_missile_submarines = yes } value = 0.50", factor)
        events = squash(strip_comments(read(INCIDENT_EVENTS)))
        self.assertIn("limit = { nd_fields_missile_submarines = yes } set_variable = { name = nd_ic_unit value = 1 }",
                      events)
        reach = squash(block(strip_comments(read(CUSTOM_LOC)), "nd_reach_value"))
        self.assertIn("trigger = { nd_fields_missile_submarines = yes } localization_key = nd_w_reach_value_subs", reach)


if __name__ == "__main__":
    unittest.main()
