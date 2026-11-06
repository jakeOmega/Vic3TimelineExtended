# -*- coding: utf-8 -*-
"""The United Nations' scaling modifiers, declared on je_united_nations.

Since 1.15 the entry declares each modifier that follows a number, or a state a
variable records, in `scaling_modifiers_while_active`, and the engine re-reads
its value from the owning country about every four days (design:
docs/superpowers/specs/2026-11-06-scaling-modifiers-design.md § 4.11). These
tests pin each declaration (once, an inline block, the exact value with its
"off" gate, which must read 0 wherever the old code removed the modifier), the
variables each value reads and every site that writes them, and that the
refresh and re-add code the declarations replaced is gone.
test_journal_entry_shape.py checks the tree-wide rule that nothing adds,
removes or tests a declared key.
"""

import os
import re
import unittest

from je_multiplier_scope_audit import parse_text
from test_un_convention_registry import RATIFIED

REPO = os.path.dirname(os.path.abspath(__file__))


def _path(*parts):
    return os.path.join(REPO, *parts)


JE = _path("common", "journal_entries", "je_united_nations.txt")
UN_VALUES = _path("common", "script_values", "un_script_values.txt")
LADDER = _path("common", "scripted_effects", "un_ladder_effects.txt")
DEBUG = _path("common", "scripted_effects", "te_debug_un_effects.txt")
DUES_EFFECTS = _path("common", "scripted_effects", "un_dues_effects.txt")
DUES_TRIGGERS = _path("common", "scripted_triggers", "un_dues_triggers.txt")
ECONOMY_EFFECTS = _path("common", "scripted_effects", "un_economy_effects.txt")
ECONOMY_TRIGGERS = _path("common", "scripted_triggers", "un_economy_triggers.txt")
ECONOMY_EVENTS = _path("events", "un_economy_events.txt")
MISSION_EFFECTS = _path("common", "scripted_effects", "un_mission_effects.txt")
MISSION_TRIGGERS = _path("common", "scripted_triggers", "un_mission_triggers.txt")
TEETH_EFFECTS = _path("common", "scripted_effects", "un_teeth_effects.txt")
UN_ON_ACTIONS = _path("common", "on_actions", "un_on_actions.txt")
GC_EFFECTS = _path("common", "scripted_effects", "te_global_commons_un_effects.txt")
GC_TRIGGERS = _path("common", "scripted_triggers", "te_global_commons_un_triggers.txt")


def _raw(path):
    with open(path, encoding="utf-8-sig") as f:
        return f.read()


def _read(path):
    """The file without comments."""
    return re.sub(r"#[^\n]*", "", _raw(path))


def _block(text, name):
    """The body of the top-level ``name = { ... }`` block."""
    m = re.search(r"^" + re.escape(name) + r"\s*=\s*\{", text, re.M)
    if m is None:
        raise AssertionError(f"{name} not found")
    depth = 0
    for i in range(m.end() - 1, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[m.end():i]
    raise AssertionError(f"{name} is not closed")


def _flat(text):
    """Comments dropped, whitespace collapsed to single spaces."""
    return " ".join(re.sub(r"#[^\n]*", "", text).split())


def _value_texts():
    """modifier -> [its declaration's ``value = ...`` text, flattened] (operators kept, which the parser drops)."""
    body = _block(_read(JE), "je_united_nations")
    out = {}
    for m in re.finditer(r"^\tscaling_modifiers_while_active\s*=\s*\{", body, re.M):
        depth, i = 0, m.end() - 1
        while True:
            depth += {"{": 1, "}": -1}.get(body[i], 0)
            if depth == 0:
                break
            i += 1
        flat = _flat(body[m.end():i])
        name = re.match(r"modifier = (\w+) ", flat).group(1)
        out.setdefault(name, []).append(flat[len(f"modifier = {name} "):])
    return out


def _entry():
    nodes, _ = parse_text(_raw(JE), "common/journal_entries/je_united_nations.txt")
    return next(n for n in nodes if n.key == "je_united_nations")


def _child(node, key):
    return next((c for c in node.children if c.key == key), None)


def _declarations():
    """modifier -> [the value node] for every scaling_modifiers_while_active block on the entry."""
    out = {}
    for block in (c for c in _entry().children if c.key == "scaling_modifiers_while_active"):
        out.setdefault(_child(block, "modifier").value, []).append(_child(block, "value"))
    return out


def _gated(limit, add):
    """``value = { value = 0 if = { limit = { <limit> } add = <add> } }``, flattened (_flat)."""
    return f"value = {{ value = 0 if = {{ limit = {{ {limit} }} add = {add} }} }}"


# modifier -> its value block, flattened (_flat). Every value is an inline
# block, as in all of vanilla's uses (08_tsarpoints.txt, 00_communism.txt).
EXPECTED = {
    # Membership benefits: from the Contested tier, to a member that draws them.
    "un_membership_benefits_modifier": _gated(
        "un_tier_at_least_contested = yes un_member_draws_benefits = yes", "un_membership_benefits_multiplier"),
    # Dues: this month's cache while the member pays its own.
    "un_dues_modifier": _gated("un_dues_in_force = yes", "var:un_dues_cached"),
    # The World Development Fund: the recipients' memory, and this month's grant.
    "un_development_patron_modifier": _gated(
        "has_variable = un_dev_fund_patron var:un_dev_fund_patron > 0", "var:un_dev_fund_patron"),
    "un_dev_fund_pool_grant_modifier": _gated("un_dev_fund_grant_into_pool = yes", "var:un_dev_fund_grant"),
    "un_dev_fund_treasury_grant_modifier": _gated("un_dev_fund_grant_into_treasury = yes", "var:un_dev_fund_grant"),
    # Missions: the cost of those we serve in at will, and an electoral mission's observers.
    "un_mission_service_cost": _gated("un_mission_service_paying = yes", "var:un_msn_service_cached"),
    "un_electoral_observers_modifier": _gated("un_mission_observers_present = yes", "var:un_msn_electoral_power"),
    # A bound mandate's war support, and the seabed royalty.
    "un_mandate_war_support_modifier": _gated(
        "has_global_variable = un_founded un_teeth_mandate_support_applies = yes", "un_enforcement"),
    "te_seabed_royalty_modifier": _gated("te_seabed_royalty_paying = yes", "var:te_seabed_royalty_cached"),
    # The programmes and stances, while their mirrors are set: the flat ones at
    # 1, the costs at the weekly expense their start caches, the development
    # benefits at the contribution's size factor.
    "un_peacekeeping_contributor_modifier": _gated("has_variable = un_peacekeeping_contributor_modifier_on", "1"),
    "un_peacekeeping_contributor_cost": _gated(
        "has_variable = un_peacekeeping_contributor_cost_on has_variable = un_peacekeeping_expense_cached",
        "var:un_peacekeeping_expense_cached"),
    "un_development_contributor_modifier": _gated(
        "has_variable = un_development_contributor_modifier_on has_variable = un_dev_fund_benefit",
        "var:un_dev_fund_benefit"),
    "un_development_contributor_cost": _gated(
        "has_variable = un_development_contributor_cost_on has_variable = un_development_expense_cached",
        "var:un_development_expense_cached"),
    "un_human_rights_champion_modifier": _gated("has_variable = un_human_rights_champion_modifier_on", "1"),
    "un_arms_control_participant_modifier": _gated("has_variable = un_arms_control_participant_modifier_on", "1"),
    "un_champion_order_cost": _gated("has_variable = un_champion_order_cost_on", "1"),
    # Championing the order cancels undermining it, as the old two-modifier
    # merge did (un_policy_counts_in_full).
    "un_undermine_order_cost": _gated("un_undermines_the_order = yes", "1"),
}

# The conventions we are party to, at the enforcement, while the mirror (the
# ratification) is set: a Moribund UN's x0 takes them off and keeps the
# ratification, so un_convention_multiplier no longer floors at x0.01.
CONVENTION_MODIFIERS = tuple(c.member_modifier for c in RATIFIED)
for _mod in CONVENTION_MODIFIERS:
    EXPECTED[_mod] = _gated(f"has_variable = {_mod}_on", "un_convention_multiplier")

# The regime terms: un_regime_refresh_country decides them once an epoch and
# sets their presence variables; the entry declares each at its multiplier,
# read live.
REGIME_MULTIPLIERS = {
    "climate_emitter": "un_enforcement", "climate_adaptation": "un_regime_adaptation_multiplier",
    "npt_inspection": "un_enforcement", "npt_guarantee": "un_enforcement", "naval_curb": "un_enforcement",
    "rights_violator": "un_enforcement", "colonial_pressure": "un_enforcement",
    "colony_liberty": "un_enforcement", "refugee_host": "un_enforcement", "refugee_source": "un_enforcement",
    "space_leader": "un_enforcement", "space_laggard": "un_enforcement", "space_weapon": "un_enforcement",
    "heritage_site": "un_enforcement", "cultural_hegemon": "un_enforcement",
    "antarctic_station": "un_enforcement", "shared_intelligence": "un_regime_strong_steps",
}
for _term, _mult in REGIME_MULTIPLIERS.items():
    EXPECTED[f"un_regime_{_term}_modifier"] = _gated(f"has_variable = un_regime_{_term}_modifier_on", _mult)

# What the Assembly imposed on us: an arms embargo while its months run, full
# or voluntary by its form, and a sanctions regime while its variable is set.
EXPECTED["un_arms_embargo_target_modifier"] = _gated("un_arms_embargo_full_in_force = yes", "un_enforcement")
EXPECTED["un_arms_embargo_voluntary_modifier"] = _gated("un_arms_embargo_voluntary_in_force = yes", "un_enforcement")
EXPECTED["un_sanctions_target_modifier"] = _gated("has_variable = un_sanctions_target_on", "un_enforcement")

PROGRAMMES = (
    "un_peacekeeping_contributor_modifier", "un_peacekeeping_contributor_cost",
    "un_development_contributor_modifier", "un_development_contributor_cost",
    "un_human_rights_champion_modifier", "un_arms_control_participant_modifier",
    "un_champion_order_cost", "un_undermine_order_cost",
)


def _script_files():
    for root in ("common", "events"):
        for dirpath, _dirs, files in os.walk(_path(root)):
            for f in sorted(files):
                if f.endswith(".txt"):
                    yield os.path.join(dirpath, f)


# The old-save strip (legacy_scaling_strip_united_nations) sets a mirror from an older save's
# added copy before removing it, as the deleted monthly reconcile did. It goes after 2026-12-31.
LEGACY_STRIP = os.path.join("common", "scripted_effects", "legacy_modifier_cleanup.txt")


def _writes(variable, ops=("set_variable", "remove_variable", "change_variable")):
    """(file, top-level definition) of every write of ``variable`` in common/ and events/, by op, the old-save
    strip's migration left out."""
    out = {op: [] for op in ops}
    pattern = re.compile(r"\b(" + "|".join(ops) + r")\s*=\s*(?:\{\s*name\s*=\s*)?" + re.escape(variable) + r"\b")
    top = re.compile(r"^([A-Za-z_][A-Za-z0-9_.]*)\s*=\s*\{", re.M)
    for path in _script_files():
        if os.path.relpath(path, REPO) == LEGACY_STRIP:
            continue
        text = _read(path)
        if variable not in text:
            continue
        tops = [(m.start(), m.group(1)) for m in top.finditer(text)]
        for m in pattern.finditer(text):
            owner = max((t for t in tops if t[0] <= m.start()), default=(0, "?"))[1]
            out[m.group(1)].append((os.path.relpath(path, REPO), owner))
    return out


class OldSaveStripTests(unittest.TestCase):
    def test_the_strip_sets_mirrors_and_never_clears_one(self):
        text = _read(_path(*LEGACY_STRIP.split(os.sep)))
        body = text.split("legacy_scaling_strip_united_nations = {", 1)[1].split("\n}\n", 1)[0]
        self.assertNotIn("remove_variable", body)
        for key in (*PROGRAMMES, "un_human_rights_declaration_modifier", "un_law_of_sea_modifier",
                    "un_regime_climate_emitter_modifier"):
            with self.subTest(key=key):
                self.assertIn(f"set_variable = {key}_on", body)
                self.assertLess(body.index(f"set_variable = {key}_on"), body.index(f"remove_modifier = {key} "))
        self.assertIn("set_variable = un_sanctions_target_on", body)

    def test_every_clear_strips_first(self):
        # Until a country's first strip, an older save's copy stands beside a
        # mirror the new code clears, and the strip would set it again from the
        # copy (review of PR 8): each helper that clears a mirror runs it first.
        sites = {
            STATE_EFFECTS: ("un_mirror_clear",),
            REGIME_EFFECTS: ("un_regime_term_off",),
            JUSTICE_EFFECTS: ("un_sanctions_lift_regime", "un_sanctions_lift_ours"),
            LADDER: ("un_dissolve_strip_country",),
        }
        for path, names in sites.items():
            text = _read(path)
            for name in names:
                with self.subTest(effect=name):
                    body = _flat(_block(text, name))
                    self.assertIn("legacy_scaling_strip_united_nations = yes", body)
                    self.assertLess(body.index("legacy_scaling_strip_united_nations = yes"),
                                    body.index("remove_variable"))

    def test_a_stale_dues_figure_goes(self):
        text = _read(_path(*LEGACY_STRIP.split(os.sep)))
        body = _flat(text.split("legacy_scaling_strip_united_nations = {", 1)[1].split("\n}\n", 1)[0])
        self.assertIn("if = { limit = { has_variable = un_dues_cached NOT = { un_dues_in_force = yes } } "
                      "un_dues_stop_paying = yes }", body)


class UprisingTests(unittest.TestCase):
    """A revolution's winner inherits the loser's variables, and nothing
    reconciles a declared modifier's mirror, so a government that beat rebels
    who had joined would keep their conventions and programmes: an uprising
    may not join (review of PR 8)."""

    def test_every_way_in_turns_an_uprising_away(self):
        for path, name in ((BUTTONS, "un_join_button"), (SGUIS, "un_act_join_sgui")):
            with self.subTest(control=name):
                gate = _block(_read(path), name)
                self.assertIn("text = un_join_not_revolutionary_tt\n\t\t\tis_revolutionary = no", gate)
        self.assertIn("un_membership_eligible = yes\n\t\t\t\t\t\tis_revolutionary = no",
                      _read(JE))
        events = _read(_path("events", "un_events.txt"))
        self.assertEqual(events.count("un_membership_eligible = yes\n\t\tis_revolutionary = no"), 1)
        self.assertEqual(events.count("un_membership_eligible = yes\n\t\t\tis_revolutionary = no"), 1)


class InfluenceGateTooltipTests(unittest.TestCase):
    def test_the_booking_has_its_own_line(self):
        # The cost line keeps the cost (test_international_influence_costs reads
        # its figure); the booking prints only while there is one.
        for path in (BUTTONS, SGUIS):
            text = _read(path)
            for kind in ("programme", "stance"):
                with self.subTest(path=path, kind=kind):
                    cost = (f"text = un_{kind}_influence_tt\n\t\t\tinfluence >= un_{kind}_influence_cost")
                    booked = ("trigger_if = {\n\t\t\tlimit = { has_variable = un_influence_pending }\n"
                              "\t\t\tcustom_tooltip = {\n\t\t\t\ttext = un_influence_pending_tt\n"
                              f"\t\t\t\tinfluence >= un_{kind}_influence_gate")
                    self.assertEqual(text.count(cost), text.count(booked))
                    self.assertGreater(text.count(cost), 0)
                    self.assertNotIn(f"text = un_{kind}_influence_tt\n\t\t\tinfluence >= un_{kind}_influence_gate",
                                     text)


class DeclarationTests(unittest.TestCase):
    def test_the_entry_declares_exactly_these_once_each(self):
        declared = _declarations()
        self.assertEqual(set(declared), set(EXPECTED))
        for modifier, values in declared.items():
            with self.subTest(modifier=modifier):
                self.assertEqual(len(values), 1)

    def test_each_value_is_its_block(self):
        declared, texts = _declarations(), _value_texts()
        for modifier, expected in EXPECTED.items():
            with self.subTest(modifier=modifier):
                self.assertIsNone(declared[modifier][0].value, "an inline value block, never a bare name")
                self.assertEqual(texts[modifier], [expected])


class MembershipBenefitsTests(unittest.TestCase):
    def test_the_strength_reads_the_country_without_a_wrapper(self):
        body = _block(_read(UN_VALUES), "un_membership_benefits_multiplier")
        self.assertIn("has_global_variable = un_authority", body)
        self.assertIn("add = modifier:country_un_institutional_alignment", body)
        self.assertNotIn("owner", body)

    def test_the_old_wrapper_is_left_uncalled_for_old_saves(self):
        raw = _raw(UN_VALUES)
        at = raw.index("\nun_membership_benefits_multiplier_for_je = {")
        self.assertIn("PENDING REMOVAL", raw[raw.rindex("\n\n", 0, at):at])
        for root in ("common", "events"):
            for dirpath, _dirs, files in os.walk(_path(root)):
                for f in files:
                    if f.endswith(".txt") and f != "un_script_values.txt":
                        with self.subTest(file=f):
                            self.assertNotIn("un_membership_benefits_multiplier_for_je",
                                             _read(os.path.join(dirpath, f)))


class DuesTests(unittest.TestCase):
    def test_in_force_is_the_old_gate(self):
        body = [line.strip() for line in _block(_read(DUES_TRIGGERS), "un_dues_in_force").splitlines()
                if line.strip()]
        self.assertEqual(body, ["has_variable = un_dues_cached", "un_dues_self_assessed = yes",
                                "NOT = { un_dues_is_withholding = yes }", "un_dues_assessed = yes"])

    def test_the_cache_is_set_by_the_refresh_and_the_resume_and_removed_by_one_helper(self):
        writes = _writes("un_dues_cached")
        self.assertEqual(sorted(set(owner for _, owner in writes["set_variable"])),
                         ["un_dues_country_monthly_update", "un_dues_resume"])
        self.assertEqual(writes["remove_variable"],
                         [("common/scripted_effects/un_dues_effects.txt", "un_dues_stop_paying")])
        self.assertEqual(writes["change_variable"], [])

    def test_every_way_out_stops_paying(self):
        effects = _read(DUES_EFFECTS)
        monthly = _block(effects, "un_dues_country_monthly_update")
        self.assertEqual(monthly.count("un_dues_stop_paying = yes"), 2, "withholding, and not assessed")
        for name in ("un_dues_withhold", "un_dues_clear"):
            with self.subTest(effect=name):
                self.assertIn("un_dues_stop_paying = yes", _block(effects, name))
        self.assertIn("un_dues_stop_paying = yes", _block(_read(LADDER), "un_membership_end_effect"))
        je = _read(JE)
        self.assertRegex(je, r"limit = \{ NOT = \{ un_dues_self_assessed = yes \} \}\s*un_dues_stop_paying = yes")


def _lines(body):
    return [line.strip() for line in body.splitlines() if line.strip()]


class DevelopmentFundTests(unittest.TestCase):
    def test_the_grant_goes_one_way_or_the_other(self):
        triggers = _read(ECONOMY_TRIGGERS)
        self.assertEqual(_lines(_block(triggers, "un_dev_fund_grant_paid")),
                         ["has_global_variable = un_inst_development_fund", "has_variable = un_dev_fund_grant",
                          "var:un_dev_fund_grant > 0"])
        self.assertEqual(_lines(_block(triggers, "un_dev_fund_grant_into_pool")),
                         ["un_dev_fund_grant_paid = yes", "un_dev_fund_pays_into_pool = yes"])
        self.assertEqual(_lines(_block(triggers, "un_dev_fund_grant_into_treasury")),
                         ["un_dev_fund_grant_paid = yes", "NOT = { un_dev_fund_pays_into_pool = yes }"])

    def test_the_monthly_update_writes_the_grant_and_fires_nothing(self):
        body = _block(_read(ECONOMY_EFFECTS), "un_dev_fund_monthly_update")
        self.assertIn("set_variable = { name = un_dev_fund_grant value = un_dev_fund_grant_value }", body)
        self.assertIn("set_variable = { name = un_dev_fund_grant value = 0 }", body)
        self.assertNotIn("trigger_event", body)

    def test_the_root_hop_and_the_refresh_are_gone(self):
        self.assertNotRegex(_read(ECONOMY_EVENTS), r"(?m)^un_economy\.1\s*=")
        for path in _script_files():
            with self.subTest(path=os.path.relpath(path, REPO)):
                text = _read(path)
                self.assertNotIn("un_dev_fund_country_refresh", text)
                self.assertNotRegex(text, r"\bun_economy\.1\b")

    def test_the_patron_pulse_writes_only_the_variable(self):
        body = _block(_read(ECONOMY_EFFECTS), "un_dev_fund_patron_pulse")
        self.assertIn("set_variable = { name = un_dev_fund_patron value = un_dev_fund_patron_next_value }", body)
        self.assertNotIn("modifier", body)


class MissionMandateSeabedTests(unittest.TestCase):
    def test_the_mission_gates(self):
        triggers = _read(MISSION_TRIGGERS)
        member = "je:je_united_nations ?= { has_modifier = un_member_modifier }"
        self.assertEqual(_lines(_block(triggers, "un_mission_service_paying")),
                         ["has_variable = un_msn_service_cached", member])
        self.assertEqual(_lines(_block(triggers, "un_mission_observers_present")),
                         ["has_variable = un_msn_electoral_power", member])

    def test_each_cache_has_its_one_writer(self):
        for variable, owner in (("un_msn_service_cached", "un_mission_service_refresh"),
                                ("un_msn_electoral_power", "un_mission_electoral_host_refresh"),
                                ("te_seabed_royalty_cached", "te_seabed_royalty_refresh")):
            with self.subTest(variable=variable):
                writes = _writes(variable)
                self.assertEqual({o for _, o in writes["set_variable"] + writes["remove_variable"]}, {owner})

    def test_a_country_that_stops_paying_the_royalty_reads_zero(self):
        refresh = _flat(_block(_read(GC_EFFECTS), "te_seabed_royalty_refresh"))
        self.assertIn("else_if = { limit = { has_variable = te_seabed_royalty_cached var:te_seabed_royalty_cached > 0 } "
                      "set_variable = { name = te_seabed_royalty_cached value = 0 } }", refresh)
        self.assertEqual(_lines(_block(_read(GC_TRIGGERS), "te_seabed_royalty_paying")),
                         ["has_variable = te_seabed_royalty_cached", "var:te_seabed_royalty_cached > 0",
                          "te_seabed_regime_is_regulated = yes", "te_seabed_itlos_party = yes"])

    def test_the_mandate_refresh_is_gone(self):
        for path in _script_files():
            with self.subTest(path=os.path.relpath(path, REPO)):
                self.assertNotIn("un_teeth_mandate_support_refresh", _read(path))


BUTTONS = _path("common", "scripted_buttons", "un_buttons.txt")
SGUIS = _path("common", "scripted_guis", "un_action_sguis.txt")
STATE_EFFECTS = _path("common", "scripted_effects", "un_state_effects.txt")
MEMBERSHIP_TRIGGERS = _path("common", "scripted_triggers", "un_membership_triggers.txt")
VOTE_EFFECTS = _path("common", "scripted_effects", "un_vote_effects.txt")

# start button -> (the mirrors it sets, the influence its start commits or None,
# the modifiers its show_as_tooltip previews); each has an un_act_*_sgui twin.
STARTS = {
    "un_peacekeeping_mission_button": (
        ("un_peacekeeping_contributor_modifier", "un_peacekeeping_contributor_cost"), "un_programme_influence_cost",
        ("un_peacekeeping_contributor_modifier", "un_peacekeeping_contributor_cost")),
    "un_fund_development_button": (
        ("un_development_contributor_modifier", "un_development_contributor_cost"), None, ()),
    "un_human_rights_resolution_button": (
        ("un_human_rights_champion_modifier",), "un_programme_influence_cost", ("un_human_rights_champion_modifier",)),
    "un_arms_control_button": (
        ("un_arms_control_participant_modifier",), "un_programme_influence_cost",
        ("un_arms_control_participant_modifier",)),
    "un_champion_order_button": (("un_champion_order_cost",), "un_stance_influence_cost", ("un_champion_order_cost",)),
    "un_undermine_order_button": (("un_undermine_order_cost",), "un_stance_influence_cost", ("un_undermine_order_cost",)),
}
STOPS = {
    "un_end_peacekeeping_button": ("un_peacekeeping_contributor_modifier", "un_peacekeeping_contributor_cost"),
    "un_defund_development_button": ("un_development_contributor_modifier", "un_development_contributor_cost"),
    "un_withdraw_human_rights_button": ("un_human_rights_champion_modifier",),
    "un_withdraw_arms_control_button": ("un_arms_control_participant_modifier",),
    "un_stop_championing_button": ("un_champion_order_cost",),
    "un_stop_undermining_button": ("un_undermine_order_cost",),
}


def _twin(button):
    return "un_act_" + button[len("un_"):-len("_button")] + "_sgui"


def _effect(body):
    """The flattened ``effect = { ... }`` of a button or scripted GUI."""
    flat = _flat(body)
    i = flat.index("effect = {")
    depth = 0
    for j in range(i + len("effect = "), len(flat)):
        depth += {"{": 1, "}": -1}.get(flat[j], 0)
        if depth == 0:
            return flat[i:j + 1]
    raise AssertionError("effect is not closed")


class ProgrammeTests(unittest.TestCase):
    def test_the_mirrors_are_written_only_through_the_helpers(self):
        state = _read(STATE_EFFECTS)
        self.assertEqual(_lines(_block(state, "un_mirror_set")), ["set_variable = $MIRROR$"])
        self.assertEqual(_flat(_block(state, "un_mirror_clear")),
                         "legacy_scaling_strip_united_nations = yes "
                         "if = { limit = { has_variable = $MIRROR$ } remove_variable = $MIRROR$ }")
        for modifier in PROGRAMMES:
            with self.subTest(modifier=modifier):
                writes = _writes(modifier + "_on")
                self.assertEqual(writes, {"set_variable": [], "remove_variable": [], "change_variable": []})

    def test_each_start_sets_its_mirrors_previews_and_commits_its_influence(self):
        files = {BUTTONS: _read(BUTTONS), SGUIS: _read(SGUIS)}
        for button, (mirrors, influence, previews) in STARTS.items():
            for path, name in ((BUTTONS, button), (SGUIS, _twin(button))):
                with self.subTest(start=name):
                    effect = _effect(_block(files[path], name))
                    for modifier in mirrors:
                        self.assertIn(f"un_mirror_set = {{ MIRROR = {modifier}_on }}", effect)
                    if influence:
                        self.assertIn(f"un_influence_pending_add = {{ AMOUNT = {influence} }}", effect)
                    else:
                        self.assertNotIn("un_influence_pending_add", effect)
                    if previews:
                        preview = effect[effect.index("show_as_tooltip = {"):]
                        for modifier in previews:
                            self.assertIn(f"add_modifier = {{ name = {modifier}", preview)

    def test_each_stop_clears_its_mirrors(self):
        files = {BUTTONS: _read(BUTTONS), SGUIS: _read(SGUIS)}
        for button, mirrors in STOPS.items():
            for path, name in ((BUTTONS, button), (SGUIS, _twin(button))):
                with self.subTest(stop=name):
                    effect = _effect(_block(files[path], name))
                    for modifier in mirrors:
                        self.assertIn(f"un_mirror_clear = {{ MIRROR = {modifier}_on }}", effect)

    def test_the_pending_influence_lasts_a_week(self):
        body = _flat(_block(_read(STATE_EFFECTS), "un_influence_pending_add"))
        self.assertEqual(body.count("days = 7"), 2)
        self.assertIn("add = $AMOUNT$", body)

    def test_a_pledge_signs_up_once(self):
        effects = _flat(_read(VOTE_EFFECTS))
        for modifier in ("un_peacekeeping_contributor_modifier", "un_peacekeeping_contributor_cost"):
            with self.subTest(modifier=modifier):
                self.assertIn(f"if = {{ limit = {{ NOT = {{ has_variable = {modifier}_on }} }} show_as_tooltip = {{",
                              effects)
                self.assertIn(f"un_mirror_set = {{ MIRROR = {modifier}_on }}", effects)

    def test_undermining_is_cancelled_by_championing(self):
        triggers = _read(MEMBERSHIP_TRIGGERS)
        self.assertEqual(_lines(_block(triggers, "un_undermines_the_order")),
                         ["has_variable = un_undermine_order_cost_on",
                          "NOT = { has_variable = un_champion_order_cost_on }"])
        self.assertIn("NOT = { un_undermines_the_order = yes }", _flat(_block(triggers, "un_policy_counts_in_full")))

    def test_every_way_out_ends_the_programmes(self):
        state = _read(STATE_EFFECTS)
        ends = _block(state, "un_programmes_end")
        for modifier in PROGRAMMES:
            with self.subTest(modifier=modifier):
                self.assertIn(f"un_mirror_clear = {{ MIRROR = {modifier}_on }}", ends)
        self.assertIn("un_programmes_end = yes", _block(_read(LADDER), "un_membership_end_effect"))
        self.assertIn("un_programmes_end = yes", _block(state, "un_state_forget_representation"))


class ConventionTests(unittest.TestCase):
    def test_the_mirrors_are_written_only_by_ratifying_and_ending(self):
        # un_convention_on sets one (its stem), un_conventions_end clears them
        # all; the Antarctic Treaty's denunciation and lapse clear its own.
        for modifier in CONVENTION_MODIFIERS:
            with self.subTest(modifier=modifier):
                self.assertEqual(_writes(modifier + "_on"),
                                 {"set_variable": [], "remove_variable": [], "change_variable": []})
        clears = {}
        call = re.compile(r"un_mirror_clear = \{ MIRROR = (un_\w+_modifier)_on \}")
        for path in _script_files():
            text = _read(path)
            tops = [(m.start(), m.group(1)) for m in re.finditer(r"^([A-Za-z_][A-Za-z0-9_.]*)\s*=\s*\{", text, re.M)]
            for m in call.finditer(text):
                if m.group(1) in CONVENTION_MODIFIERS:
                    owner = max(t for t in tops if t[0] <= m.start())[1]
                    clears.setdefault(m.group(1), set()).add(owner)
        for modifier in CONVENTION_MODIFIERS:
            with self.subTest(modifier=modifier):
                expected = {"un_conventions_end"}
                if modifier == "un_antarctic_treaty_modifier":
                    expected |= {"te_antarctic_treaty_denounce", "te_antarctic_treaty_lapse"}
                self.assertEqual(clears.get(modifier), expected)

    def test_the_regime_layer_no_longer_rescales_them(self):
        for path in _script_files():
            with self.subTest(path=os.path.relpath(path, REPO)):
                self.assertNotIn("un_regime_reapply", _read(path))


REGIME_EFFECTS = _path("common", "scripted_effects", "un_regime_effects.txt")


class RegimeTermTests(unittest.TestCase):
    def test_the_refresh_starts_each_term_once_at_its_multiplier(self):
        refresh = _block(_read(REGIME_EFFECTS), "un_regime_refresh_country")
        found = re.findall(r"un_regime_term_on = \{ TERM = (\w+) MULT = (\w+) \}", refresh)
        self.assertEqual(sorted(found), sorted(REGIME_MULTIPLIERS.items()))
        self.assertNotIn("add_modifier = {\n\t\t\t\tname = un_regime_", refresh)
        # The sovereignty reaction stays on the interest groups: no entry can
        # declare an interest group's modifier.
        self.assertIn("name = un_sovereignty_resentment_ig_modifier", refresh)
        self.assertIn("name = un_sovereignty_welcome_ig_modifier", refresh)

    def test_the_helpers_preview_and_write_the_presence_variable(self):
        effects = _read(REGIME_EFFECTS)
        self.assertEqual(_flat(_block(effects, "un_regime_term_on")),
                         "show_as_tooltip = { je:je_united_nations ?= { add_modifier = { "
                         "name = un_regime_$TERM$_modifier multiplier = $MULT$ } } } "
                         "set_variable = un_regime_$TERM$_modifier_on")
        self.assertEqual(_flat(_block(effects, "un_regime_term_off")),
                         "legacy_scaling_strip_united_nations = yes "
                         "if = { limit = { has_variable = un_regime_$TERM$_modifier_on } "
                         "remove_variable = un_regime_$TERM$_modifier_on }")
        clear = _block(effects, "un_regime_clear_country")
        self.assertEqual(sorted(re.findall(r"un_regime_term_off = \{ TERM = (\w+) \}", clear)),
                         sorted(REGIME_MULTIPLIERS))

    def test_the_presence_variables_have_no_other_writers(self):
        for term in REGIME_MULTIPLIERS:
            with self.subTest(term=term):
                self.assertEqual(_writes(f"un_regime_{term}_modifier_on"),
                                 {"set_variable": [], "remove_variable": [], "change_variable": []})
        # Leaving takes the liberty term off our colonies, through the helper.
        ladder = _flat(_block(_read(LADDER), "un_membership_end_effect"))
        self.assertIn("every_direct_subject = { limit = { has_variable = un_regime_colony_liberty_modifier_on } "
                      "un_regime_term_off = { TERM = colony_liberty } }", ladder)

    def test_the_cadence_is_kept(self):
        # The epoch decides the terms (emitter shares and ranks would flicker);
        # only the multiplier is live.
        pulse = _flat(_block(_read(REGIME_EFFECTS), "un_regime_country_pulse"))
        self.assertIn("NOT = { var:un_regime_stamp = global_var:un_regime_epoch }", pulse)
        self.assertIn("un_regime_refresh_country = yes", pulse)


JUSTICE_EFFECTS = _path("common", "scripted_effects", "un_justice_effects.txt")
JUSTICE_TRIGGERS = _path("common", "scripted_triggers", "un_justice_triggers.txt")


class EmbargoSanctionsTests(unittest.TestCase):
    def test_the_two_forms_split_the_record(self):
        triggers = _read(JUSTICE_TRIGGERS)
        self.assertEqual(_lines(_block(triggers, "un_arms_embargo_voluntary_in_force")),
                         ["has_variable = un_arms_embargo_months", "has_variable = un_arms_embargo_form",
                          "var:un_arms_embargo_form = 2"])
        self.assertEqual(_lines(_block(triggers, "un_arms_embargo_full_in_force")),
                         ["has_variable = un_arms_embargo_months",
                          "NOT = { un_arms_embargo_voluntary_in_force = yes }"])

    def test_an_embargo_previews_and_records_and_nothing_restores_it(self):
        effects = _read(JUSTICE_EFFECTS)
        for name, modifier, form in (("un_arms_embargo_impose_full", "un_arms_embargo_target_modifier", 1),
                                     ("un_arms_embargo_impose_voluntary", "un_arms_embargo_voluntary_modifier", 2)):
            with self.subTest(effect=name):
                body = _flat(_block(effects, name))
                self.assertIn(f"show_as_tooltip = {{ je:je_united_nations ?= {{ add_modifier = {{ name = {modifier} "
                              f"multiplier = un_enforcement }} }} }}", body)
                self.assertIn(f"set_variable = {{ name = un_arms_embargo_form value = {form} }}", body)
        clear = _flat(_block(effects, "un_arms_embargo_clear"))
        self.assertNotIn("modifier", clear)
        self.assertIn("remove_variable = un_arms_embargo_months", clear)
        for path in _script_files():
            with self.subTest(path=os.path.relpath(path, REPO)):
                self.assertNotIn("un_arms_embargo_restore", _read(path))

    def test_the_sanctions_variable_is_set_by_the_vote_and_cleared_by_the_lifts(self):
        writes = _writes("un_sanctions_target_on")
        self.assertEqual({o for _, o in writes["set_variable"]}, {"un_vote.2"})
        self.assertEqual({o for _, o in writes["remove_variable"]},
                         {"un_sanctions_lift_regime", "un_sanctions_lift_ours", "un_dissolve_strip_country"})
        self.assertEqual(writes["change_variable"], [])


if __name__ == "__main__":
    unittest.main()
