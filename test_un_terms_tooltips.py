# -*- coding: utf-8 -*-
"""Every UN topic's terms, stated where the player reads them.

Each convention, member topic and piece of the charter's business has one
terms text, je_un_terms_<topic> in localization/english: every effect it has,
on its parties, its target, its proposer, the members and other systems (the
Grand Monuments' trophy infamy under UNESCO, the nuclear taboo's UN part, war
support under a condemnation, the Strategic Reserve's grain under the World
Food Reserve...). It is shown in four places, and this file pins each:

- the topic's title in Table a Resolution (je_un_chamber_propose_topic_<key>);
- the "Its terms" hover on the resolution card's If it carries line
  (je_un_chamber_conseq_<tag>);
- a convention's line in Our Obligations (je_un_chamber_conv_<key>_tt);
- the "Its terms" hover in the agency icon's tooltip in the overview
  (je_un_ov_agency_<agency>_tt).

Modifier effects render through GetStaticModifier(...).GetDesc, so they
cannot drift. The figures typed by hand (rules that live in script values, not
modifiers) are read back from the script below and fail here when one moves.

Run: python3 -m unittest test_un_terms_tooltips -v
"""

import glob
import os
import re
import unittest

from test_un_convention_registry import CONVENTIONS

REPO = os.path.dirname(os.path.abspath(__file__))
LOC_DIR = os.path.join(REPO, "localization", "english")


def _read(*parts):
    with open(os.path.join(REPO, *parts), encoding="utf-8-sig") as f:
        return f.read()


def _loc_values():
    values = {}
    for path in glob.glob(os.path.join(LOC_DIR, "**", "*.yml"), recursive=True):
        with open(path, encoding="utf-8-sig") as f:
            for line in f:
                m = re.match(r' ([\w.\-]+):\d* "(.*)"\s*$', line)
                if m:
                    values[m.group(1)] = m.group(2)
    return values


LOC = _loc_values()


def _expanded(value, depth=5):
    for _ in range(depth):
        value = re.sub(r"\$(\w+)\$", lambda m: LOC.get(m.group(1), m.group(0)), value)
    return value


def _hover_key(value):
    m = re.search(r"#tooltippable;tooltip:(?:\[GetPlayer\.GetTooltipTag\],)?(\w+) ", value)
    return m and m.group(1)


def _script_value(rel, name):
    m = re.search(rf"(?m)^{re.escape(name)}\s*=\s*(?:\{{\s*value\s*=\s*)?(-?[\d.]+)", _read(*rel.split("/")))
    assert m, f"{name} not found in {rel}"
    return float(m.group(1))


def _fmt(x):
    return f"{x:g}"


# Propose key (je_un_chamber_propose_topic_<key>) -> terms topic. The
# conventions' keys are their own.
OTHER_TOPICS = {
    "condemn": "condemn", "sanctions": "sanctions", "expulsion": "expulsion",
    "mandate": "mandate", "peacekeepers": "peacekeepers", "aid": "aid",
    "court_referral": "court_referral", "arms_embargo": "arms_embargo",
    "credentials": "credentials", "standing_force": "standing_force",
    "observer_request": "observer_request", "food_reserve": "food_reserve",
    "ceasefire": "ceasefire", "development_fund": "development_fund",
    "referendum": "referendum", "reform_1": "reform", "reform_2": "reform",
    "lift_sanctions": "lift_sanctions",
}
PROPOSE = {c.key: c.key for c in CONVENTIONS} | OTHER_TOPICS

# Resolution tag (un_topic_<tag>) -> terms topic, where they differ.
TAG_TOPIC = {"peacekeeping_request": "peacekeepers", "aid_request": "aid",
             "military_mandate": "mandate"}

# Overview agency -> convention (None for the ICJ, which has no terms).
AGENCY = {c.in_force[len("un_agency_"):]: c.key for c in CONVENTIONS if c.in_force.startswith("un_agency_")}
AGENCY["icj"] = None


class TermsReachEveryPlaceTest(unittest.TestCase):

    def test_every_convention_states_its_modifiers(self):
        for c in CONVENTIONS:
            with self.subTest(convention=c.key):
                terms = _expanded(LOC[f"je_un_terms_{c.key}"])
                for mod in ((c.member_modifier,) if c.member_modifier else ()) + tuple(c.regime_modifiers):
                    self.assertIn(f"GetStaticModifier('{mod}').GetDesc", terms)

    def test_every_title_hovers_its_terms(self):
        for key, topic in PROPOSE.items():
            with self.subTest(topic=key):
                hover = _hover_key(LOC[f"je_un_chamber_propose_topic_{key}"])
                self.assertTrue(hover, key)
                self.assertIn(f"$je_un_terms_{topic}_tt$", LOC[hover])

    def test_every_card_line_hovers_its_terms(self):
        tags = set(re.findall(r"custom_tooltip_no_bullet = je_un_chamber_conseq_(\w+)", _read(
            "common", "scripted_effects", "un_chamber_display_effects.txt")))
        self.assertGreater(len(tags), 40)
        for tag in sorted(tags):
            if tag.startswith("fail"):
                continue
            base = re.sub(r"_(vetoed|weak|1|2)$", "", tag)
            topic = TAG_TOPIC.get(base, base)
            with self.subTest(line=tag):
                line = LOC[f"je_un_chamber_conseq_{tag}"]
                self.assertIn(f"tooltip:[GetPlayer.GetTooltipTag],je_un_terms_{topic}_tt ", line)

    def test_every_obligation_hovers_its_terms(self):
        for c in CONVENTIONS:
            if not c.member_modifier:
                continue
            with self.subTest(convention=c.key):
                self.assertIn(f"$je_un_terms_{c.key}$", LOC[f"je_un_chamber_conv_{c.key}_tt"])

    def test_every_agency_hovers_its_terms(self):
        # The icon's own hover stays short (its name and whether it stands);
        # the convention's terms are one hover away, on "Its terms", as on the
        # resolution card (long_tooltip_audit; style rules 2 and 3).
        gui = _read("gui", "journal_entry_widgets", "un_overview_widget.gui")
        for agency, key in AGENCY.items():
            with self.subTest(agency=agency):
                self.assertIn(f'tooltip = "je_un_ov_agency_{agency}_tt"', gui)
                tip = LOC[f"je_un_ov_agency_{agency}_tt"]
                self.assertIn(f"ScriptValue('un_disp_agency_{agency}')", tip)
                if key:
                    self.assertIn(f"#tooltippable;tooltip:[GetPlayer.GetTooltipTag],je_un_terms_{key} ", tip)
                    self.assertNotIn(f"$je_un_terms_{key}$", tip)
                else:
                    self.assertIn("$je_un_ov_agency_icj_terms$", tip)

    def test_terms_read_no_scope(self):
        # They render on a proposal row (a country), a resolution card (a
        # resolution container) and an overview icon (a widget): only global
        # reads are safe in all three.
        for key, value in LOC.items():
            if key.startswith("je_un_terms_"):
                with self.subTest(key=key):
                    for token in ("THIS.", "SCOPE.", "ROOT", "JournalEntry.", "GetGlobalVariable"):
                        self.assertNotIn(token, value)


class HandTypedFiguresTest(unittest.TestCase):
    """The figures the terms type by hand, read back from the script."""

    def test_unesco_trophy_rules(self):
        values = _read("common", "script_values", "gm_trophy_values.txt")
        unesco = re.findall(r"has_global_variable = un_agency_unesco \}\s*multiply = ([\d.]+)", values)
        self.assertEqual(sorted(set(unesco)), ["0.25", "2"])
        terms = LOC["je_un_terms_heritage"]
        self.assertIn("#R twice#!", terms)
        self.assertIn("4 to 16 instead of 2 to 8", terms)
        self.assertIn("a quarter as often", terms)
        self.assertIn("add = 2\n\tmax = 8", values)

    def test_condemnation_war_support(self):
        inj = _read("common", "script_values", "zz_te_war_support_injections.txt")
        for value, desc in (("-0.5", "CONDEMNED"), ("-0.25", "REBUKED"), ("0.25", "ENEMY_CONDEMNED")):
            self.assertRegex(inj, rf"value = {re.escape(value)}\s*desc = \"WAR_SUPPORT_TE_UN_{desc}\"")
        terms = LOC["je_un_terms_condemn"]
        for shown in ("#R 0.5#!", "#G 0.25#!", "#R 0.25#!"):
            self.assertIn(shown, terms)

    def test_nuclear_taboo_weights(self):
        for name, key in (("nd_taboo_un_npt_weight", "npt"), ("nd_taboo_un_cppnm_weight", "physical_protection"),
                          ("nd_taboo_un_tpnw_weight", "nuclear_ban")):
            weight = _fmt(_script_value("common/script_values/nuclear_taboo_values.txt", name))
            with self.subTest(convention=key):
                self.assertIn(f"rises by up to #G {weight}#!", LOC[f"je_un_terms_{key}"])

    def test_custody_recovery_chance(self):
        chance = _fmt(_script_value("common/script_values/nuclear_loose_values.txt", "nd_loose_convention_chance"))
        self.assertIn(f"#v {chance}%#!", LOC["je_un_terms_physical_protection"])

    def test_regime_lines(self):
        regime = "common/script_values/un_regime_values.txt"
        climate = LOC["je_un_terms_climate"]
        self.assertIn(f"{_fmt(_script_value(regime, 'un_regime_emitter_share_pct'))}% or more", climate)
        self.assertIn(f"under {_fmt(_script_value(regime, 'un_regime_low_emitter_share_pct'))}%", climate)
        refugee = LOC["je_un_terms_refugee"]
        self.assertIn(f"the {_fmt(_script_value(regime, 'un_regime_refugee_host_rank'))} richest", refugee)
        self.assertIn(f"below {_fmt(_script_value(regime, 'un_regime_refugee_source_rank'))}th", refugee)
        self.assertEqual(_script_value(regime, "un_regime_space_lead_min"), 3)
        self.assertEqual(_script_value(regime, "un_regime_space_laggard_gap"), 3)
        self.assertIn("three or more milestones behind", LOC["je_un_terms_space"])

    def test_standing_figures(self):
        standing = "common/script_values/un_standing_values.txt"
        self.assertIn(f"loses {_fmt(_script_value(standing, 'un_standing_condemned_loss'))} standing",
                      LOC["je_un_terms_condemn"])
        self.assertIn(f"loses {_fmt(_script_value(standing, 'un_standing_rebuked_loss'))} standing",
                      LOC["je_un_terms_condemn"])
        self.assertIn(f"loses {_fmt(_script_value(standing, 'un_standing_sanctioned_loss'))} standing",
                      LOC["je_un_terms_sanctions"])
        self.assertIn(f"loses {_fmt(_script_value(standing, 'un_standing_mandate_violated_loss'))}",
                      LOC["je_un_terms_mandate"])
        self.assertIn(f"#G +{_fmt(_script_value(standing, 'un_standing_mandate_complied_gain'))}#!",
                      LOC["je_un_terms_mandate"])

    def test_ceasefire_figures(self):
        order = "common/script_values/un_order_values.txt"
        terms = LOC["je_un_terms_ceasefire"]
        self.assertIn(f"a {_fmt(_script_value(order, 'un_cf_order_length'))}-month order", terms)
        self.assertIn(f"falls by {_fmt(_script_value(order, 'un_cf_drain_base'))} (scaled)", terms)
        self.assertIn(f"loses {_fmt(_script_value(order, 'un_cf_fight_on_loss'))} standing, "
                      f"or {_fmt(_script_value(order, 'un_cf_fight_on_accepted_loss'))}", terms)
        self.assertIn(f"falls once by {_fmt(_script_value(order, 'un_cf_call_hit_base'))} (scaled)", terms)

    def test_lift_sanctions_figures(self):
        dossier = "common/script_values/un_dossier_values.txt"
        justice = "common/script_values/un_justice_values.txt"
        case = _fmt(_script_value(dossier, "un_case_threshold_sanctions"))
        self.assertEqual(_script_value(justice, "un_lift_fresh_months"), 60)
        terms = LOC["je_un_terms_lift_sanctions"]
        self.assertIn(f"below the {case} that supports sanctions", terms)
        self.assertIn("stood less than five years", terms)
        desc = LOC["UN_PROPOSE_LIFT_SANCTIONS_DESC"]
        self.assertIn(f"a case strength of {case}", desc)
        self.assertIn("stood less than five years", desc)

    def test_failure_costs_influence_not_prestige(self):
        mods = _read("common", "static_modifiers", "extra_modifiers.txt")
        body = mods[mods.index("un_vote_failure_penalty = {"):]
        body = body[:body.index("}")]
        self.assertIn("country_influence_mult", body)
        self.assertNotIn("prestige", body)
        self.assertIn("[concept_influence]", LOC["un_vote_failed_tt"])
        self.assertNotIn("prestige", LOC["un_vote_failed_tt"])


if __name__ == "__main__":
    unittest.main()
