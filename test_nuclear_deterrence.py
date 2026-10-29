"""Nuclear deterrence and crisis diplomacy: the hand-kept tables that must agree.

The system (docs/systems/nuclear_crisis_design.md §0) keeps a few lists in
more than one place — the panel's op codes in the .gui, the scripted GUIs and
journal_entry_systems.md; the event ids it fires; the loc keys its script,
events, custom loc and widget name; the managed modifier families. Nothing in
the engine checks any of them: a mistyped op is a dead button, a missing loc
key is a raw key in the player's face, a missing event id is a silent no-op.
Each test pins one of those lists in both directions where both exist.

Run: python3 -m unittest test_nuclear_deterrence -v
"""

import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
GUI = ROOT / "gui/journal_entry_widgets/nuclear_deterrence_widget.gui"
SGUIS = ROOT / "common/scripted_guis/nuclear_deterrence_sguis.txt"
EFFECTS = ROOT / "common/scripted_effects/nuclear_deterrence_effects.txt"
CRISIS_EFFECTS = ROOT / "common/scripted_effects/nuclear_crisis_effects.txt"
TRIGGERS = ROOT / "common/scripted_triggers/nuclear_deterrence_triggers.txt"
VALUES = ROOT / "common/script_values/nuclear_deterrence_values.txt"
MODIFIERS = ROOT / "common/static_modifiers/nuclear_deterrence_modifiers.txt"
CUSTOM_LOC = ROOT / "common/customizable_localization/nuclear_deterrence_custom_loc.txt"
ACTIONS = ROOT / "common/diplomatic_actions/nuclear_crisis_actions.txt"
ARTICLE = ROOT / "common/treaty_articles/115_nuclear_guarantee.txt"
JE = ROOT / "common/journal_entries/je_nuclear_program.txt"
CRISIS_EVENTS = ROOT / "events/nuclear_crisis_events.txt"
INCIDENT_EVENTS = ROOT / "events/nuclear_incident_events.txt"
DEBUG_EVENTS = ROOT / "events/te_debug_deterrence_events.txt"
JE_DOC = ROOT / "docs/systems/journal_entry_systems.md"
LOC_DIR = ROOT / "localization/english"
LENS_ICONS = ROOT / "gfx/interface/icons/lens_toolbar_icons"
NUKE = ROOT / "common/diplomatic_actions/nuke.txt"
WEAPON_EVENTS = ROOT / "events/nuclear_weapon_events.txt"
UMBRELLA_ACTIONS = ROOT / "common/diplomatic_actions/nuclear_umbrella_actions.txt"
CUSTODY_EFFECTS = ROOT / "common/scripted_effects/nuclear_custody_effects.txt"
CUSTODY_TRIGGERS = ROOT / "common/scripted_triggers/nuclear_custody_triggers.txt"
CUSTODY_VALUES = ROOT / "common/script_values/nuclear_custody_values.txt"
CUSTODY_ON_ACTIONS = ROOT / "common/on_actions/nuclear_custody_on_actions.txt"
CUSTODY_EVENTS = ROOT / "events/nuclear_custody_events.txt"
CIVIL_WAR_EFFECTS = ROOT / "common/scripted_effects/te_civil_war_effects.txt"
CIVIL_WAR_ON_ACTIONS = ROOT / "common/on_actions/te_civil_war_on_actions.txt"
LOOSE_EFFECTS = ROOT / "common/scripted_effects/nuclear_loose_effects.txt"
LOOSE_TRIGGERS = ROOT / "common/scripted_triggers/nuclear_loose_triggers.txt"
LOOSE_VALUES = ROOT / "common/script_values/nuclear_loose_values.txt"
LOOSE_EVENTS = ROOT / "events/nuclear_loose_events.txt"
SOCIAL_TENSIONS_ON_ACTIONS = ROOT / "common/on_actions/social_tensions_on_actions.txt"
EXTRA_EFFECTS = ROOT / "common/scripted_effects/extra_effects.txt"
TABOO_EFFECTS = ROOT / "common/scripted_effects/nuclear_taboo_effects.txt"
EXTRA_VALUES = ROOT / "common/script_values/extra_script_values.txt"
EXTRA_BUILDINGS = ROOT / "common/buildings/extra_buildings.txt"
EXTRA_PM_GROUPS = ROOT / "common/production_method_groups/extra_pm_groups.txt"
NUKE_TRIGGERS = ROOT / "common/scripted_triggers/nuke_triggers.txt"
TABOO_TRIGGERS = ROOT / "common/scripted_triggers/nuclear_taboo_triggers.txt"


def tracked(path):
    """Whether git tracks path. CI checks out without gfx/ (sparse), so a
    texture can be committed yet absent from the working tree."""
    rel = path.relative_to(ROOT).as_posix()
    result = subprocess.run(["git", "ls-files", "--error-unmatch", rel],
                            cwd=ROOT, capture_output=True)
    return result.returncode == 0

# `trigger_event = { id = X }`, or nd_crisis_send_event's EVENT parameter.
FIRED = r"\b(?:id|EVENT) = ([a-z_]+\.\d+)"

SCRIPT_FILES = (EFFECTS, CRISIS_EFFECTS, TRIGGERS, ACTIONS, ARTICLE, JE, SGUIS,
                CRISIS_EVENTS, INCIDENT_EVENTS, DEBUG_EVENTS, NUKE,
                CUSTODY_EFFECTS, CUSTODY_TRIGGERS, CUSTODY_ON_ACTIONS, CUSTODY_EVENTS,
                CIVIL_WAR_EFFECTS, CIVIL_WAR_ON_ACTIONS,
                LOOSE_EFFECTS, LOOSE_TRIGGERS, LOOSE_EVENTS, SOCIAL_TENSIONS_ON_ACTIONS,
                ROOT / "common/scripted_effects/nuclear_exchange_effects.txt",
                ROOT / "common/scripted_triggers/nuclear_exchange_triggers.txt",
                ROOT / "common/scripted_effects/nuclear_observer_effects.txt")
EVENT_FILES = (CRISIS_EVENTS, INCIDENT_EVENTS, DEBUG_EVENTS, CUSTODY_EVENTS, LOOSE_EVENTS)


def read(path):
    return path.read_text(encoding="utf-8-sig")


def strip_comments(text):
    return "\n".join(line.split("#", 1)[0] for line in text.splitlines())


def loc_keys():
    keys = set()
    for path in LOC_DIR.glob("*.yml"):
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            m = re.match(r"\s+([A-Za-z0-9_.\-]+):\d*\s", line)
            if m:
                keys.add(m.group(1))
    return keys


def block(text, name):
    """The body of the first `name = { ... }` block that opens a line: a
    top-level definition if there is one, else the first indented one (an
    indented `name = { PARAM = … }` call must not shadow the definition)."""
    m = (re.search(r"^" + re.escape(name) + r"\s*=\s*\{", text, re.M)
         or re.search(r"^[ \t]*" + re.escape(name) + r"\s*=\s*\{", text, re.M))
    if not m:
        raise AssertionError(f"{name} not found")
    depth, i = 1, m.end()
    while depth:
        c = text[i]
        depth += c == "{"
        depth -= c == "}"
        i += 1
    return text[m.end():i - 1]


def gui_ops(gui_text, sgui):
    """Op codes the .gui passes to `sgui` (rows set the datacontext). Only an
    op scope counts (`AddScope( 'op', MakeScopeValue( '(CFixedPoint)N' ) )`),
    so a row's other literals, such as the code that tints the option in
    force, are never read as ops."""
    ops = set()
    for m in re.finditer(r"datacontext = \"\[GetScriptedGui\('(\w+)'\)\]\"", gui_text):
        if m.group(1) != sgui:
            continue
        # The row's buttons follow its datacontext, up to the next row.
        nxt = re.search(r"datacontext = ", gui_text[m.end():])
        seg = gui_text[m.end(): m.end() + (nxt.start() if nxt else len(gui_text))]
        ops |= {int(x) for x in re.findall(r"AddScope\( 'op', MakeScopeValue\( '\(CFixedPoint\)(\d+)' \) \)", seg)}
    return ops


def sgui_ops(sgui_text, name, part):
    body = block(sgui_text, name)
    part_body = block(body, part) if part != "effect" else block(body, "effect")
    return {int(x) for x in re.findall(r"scope:op = (\d+)", part_body)}


class TestPanelOps(unittest.TestCase):
    def setUp(self):
        self.gui = read(GUI)
        self.sguis = strip_comments(read(SGUIS))

    def test_every_gui_op_is_handled_and_every_handled_op_is_drawn(self):
        for sgui in ("nd_posture_sgui", "nd_crisis_action_sgui"):
            drawn = gui_ops(self.gui, sgui)
            valid = sgui_ops(self.sguis, sgui, "is_valid")
            effect = sgui_ops(self.sguis, sgui, "effect")
            self.assertTrue(drawn, f"no buttons found for {sgui}")
            self.assertEqual(drawn, valid, f"{sgui}: .gui ops vs is_valid")
            self.assertEqual(drawn, effect, f"{sgui}: .gui ops vs effect")

    def test_op_table_in_docs_names_every_op(self):
        doc = JE_DOC.read_text(encoding="utf-8")
        section = doc.split("### Nuclear Deterrence Widget", 1)[1].split("\n### ", 1)[0]
        documented = set()
        for lo, hi in re.findall(r"\|\s*(\d+)(?:\s*[–-]\s*(\d+))?\s*\|", section):
            documented |= set(range(int(lo), int(hi or lo) + 1))
        for lo, hi in re.findall(r"\|\s*(\d+) / (\d+)\s*\|", section):
            documented |= {int(lo), int(hi)}
        for sgui in ("nd_posture_sgui", "nd_crisis_action_sgui"):
            missing = gui_ops(self.gui, sgui) - documented
            self.assertFalse(missing, f"{sgui} ops missing from journal_entry_systems.md: {sorted(missing)}")


class TestEventReferences(unittest.TestCase):
    def test_every_fired_event_exists(self):
        defined = set()
        for path in (ROOT / "events").glob("*.txt"):
            defined |= set(re.findall(r"^([a-z_]+\.\d+)\s*=\s*\{", read(path), re.M))
        for path in SCRIPT_FILES:
            text = strip_comments(read(path))
            for ev in re.findall(FIRED, text):
                if ev not in defined:
                    self.fail(f"{path.name} fires {ev}, which no event file defines")

    def test_every_new_event_is_fired_somewhere_or_console_only(self):
        fired = set()
        for path in list((ROOT / "common").rglob("*.txt")) + list((ROOT / "events").glob("*.txt")):
            text = strip_comments(read(path))
            fired |= set(re.findall(FIRED, text))
            # An on_action's weighted random_events entry (`3 = nuclear_loose.1`).
            fired |= set(re.findall(r"(?m)^\s*\d+ = ([a-z_]+\.\d+)\s*$", text))
        for path in (CRISIS_EVENTS, INCIDENT_EVENTS, CUSTODY_EVENTS, LOOSE_EVENTS):
            for ev in re.findall(r"^([a-z_]+\.\d+)\s*=\s*\{", read(path), re.M):
                if ev not in fired:
                    self.fail(f"{ev} is never fired")


class TestLocalization(unittest.TestCase):
    def setUp(self):
        self.keys = loc_keys()

    def assert_keys(self, keys, where):
        missing = sorted(k for k in keys if k not in self.keys)
        self.assertFalse(missing, f"{where}: missing loc keys {missing}")

    def test_event_text_keys(self):
        for path in EVENT_FILES:
            text = strip_comments(read(path))
            keys = set(re.findall(r"\b(?:title|desc|flavor|name) = ([a-z_]+\.\d+\.[a-z_.]+)", text))
            self.assertTrue(keys, path.name)
            self.assert_keys(keys, path.name)

    def test_custom_tooltip_keys(self):
        keys = set()
        for path in SCRIPT_FILES:
            text = strip_comments(read(path))
            keys |= set(re.findall(r"custom_tooltip(?:_no_bullet)? = (nd_[\w$]+)", text))
            keys |= set(re.findall(r"text = (nd_[\w$]+)", text))
        expanded = {k for k in keys if "$" not in k}
        # Parameterised families: every value the wrappers pass.
        expanded |= {f"nd_tt_doctrine_adopted_{d}" for d in range(1, 6)}
        expanded |= {f"nd_tt_readiness_target_{r}" for r in range(0, 4)}
        expanded |= {f"nd_tt_authority_adopted_{a}" for a in range(1, 5)}
        expanded |= {f"nd_tt_{v}_{o}" for v in ("nd_safeguards", "nd_hardening") for o in ("add", "subtract")}
        self.assert_keys(expanded, "custom tooltips")

    def test_custom_loc_targets(self):
        keys = set(re.findall(r"localization_key = (\w+)", strip_comments(read(CUSTOM_LOC))))
        self.assert_keys(keys, CUSTOM_LOC.name)

    def test_widget_keys(self):
        text = read(GUI)
        keys = set(re.findall(r'(?:text|tooltip) = "(nd_\w+)"', text))
        self.assertTrue(keys)
        self.assert_keys(keys, GUI.name)

    def test_static_modifiers_named_and_described(self):
        mods = re.findall(r"^(nd_\w+)\s*=\s*\{", read(MODIFIERS), re.M)
        self.assertTrue(mods)
        self.assert_keys(set(mods) | {m + "_desc" for m in mods}, MODIFIERS.name)

    def test_diplomatic_actions_and_article(self):
        acts = re.findall(r"^(nd_\w+_action)\s*=\s*\{", read(ACTIONS), re.M)
        self.assertEqual(len(acts), 3)
        needed = set()
        for a in acts:
            needed |= {a, a + "_desc", a + "_action_notification_name", a + "_action_notification_desc"}
        for article in ("nuclear_guarantee", "nuclear_security_assistance", "nuclear_basing"):
            needed |= {article, article + "_desc", article + "_article_short_desc",
                       article + "_effects_desc"}
        self.assert_keys(needed, "actions and article")

    def test_diplomatic_actions_have_lens_icons(self):
        """The engine loads lens_toolbar_icons/<action>.dds for every action
        without show_in_lens = no; a missing one is a VFSOpen error per session."""
        text = strip_comments(read(ACTIONS))
        for action in re.findall(r"^(nd_\w+_action)\s*=\s*\{", text, re.M):
            if re.search(r"show_in_lens\s*=\s*no", block(text, action)):
                continue
            icon = LENS_ICONS / f"{action}.dds"
            self.assertTrue(icon.exists() or tracked(icon), f"missing {icon.relative_to(ROOT)}")

    def test_journal_entry_keys(self):
        # Posture and crises share je_nuclear_program since 2026-09-25.
        self.assert_keys({"je_nuclear_program", "je_nuclear_program_desc",
                          "je_nuclear_program_reason",
                          "je_nuclear_program_status_line"}, JE.name)


# Every event option that orders a launch, gated on the command (phase 3) and
# on reach (phase 4a, test_nuclear_reach.py): one list, so the gates can't
# drift apart. The guarantor's hidden answer, nuclear_crisis.22, is the one
# ordered launch that is not an option.
ORDERED_LAUNCH_CRISIS_OPTIONS = ("nuclear_crisis.4.g", "nuclear_crisis.7.a", "nuclear_crisis.20.b",
                                 "nuclear_crisis.24.b")
ORDERED_LAUNCH_INCIDENT_OPTIONS = ("nuclear_incident.1.c", "nuclear_incident.50.c")


def option_body(text, option_name):
    """The body of the `option = { … }` whose `name` is option_name."""
    m = re.search(r"name = " + re.escape(option_name) + r"\s", text)
    if not m:
        raise AssertionError(f"{option_name} not found")
    start = text.rfind("option = {", 0, m.start())
    return block(text[start:], "option")


class TestWarLawGate(unittest.TestCase):
    def test_gate_triggers_exist(self):
        t = read(TRIGGERS)
        for name in ("nd_war_law_permits_strategic_strike",
                     "nd_war_law_permits_tactical_strike",
                     "nd_war_law_exception"):
            self.assertRegex(t, rf"(?m)^{name} = \{{")

    def test_strike_actions_use_the_shared_gate(self):
        text = strip_comments(read(NUKE))
        self.assertNotIn("has_law = law_type:law_limited_war", text)
        self.assertIn("nd_war_law_permits_strategic_strike = yes", block(text, "nuke_diplo_action"))
        self.assertIn("nd_war_law_permits_tactical_strike = yes", block(text, "tactical_nuke_diplo_action"))

    def test_every_crisis_strike_option_checks_the_law(self):
        text = strip_comments(read(CRISIS_EVENTS))
        for opt in ("nuclear_crisis.4.g", "nuclear_crisis.7.a", "nuclear_crisis.20.b", "nuclear_crisis.24.b"):
            self.assertIn("nd_war_law_permits_strategic_strike = yes", option_body(text, opt), opt)

    def test_monopoly_window_first_use_checks_the_law(self):
        text = strip_comments(read(INCIDENT_EVENTS))
        self.assertIn("nd_war_law_permits_strategic_strike = yes",
                      option_body(text, "nuclear_incident.50.c"))

    def test_the_government_launch_order_passes_every_deliberate_gate(self):
        """nuclear_incident.1.c is the government's own order (owner ruling
        2026-09-26): the same gates as nuke_diplo_action, shown greyed, except
        that a launch under attack passes the doctrine in a war or an Acute
        crisis with the suspect unless it is No First Use (owner, 2026-10-28)."""
        body = option_body(strip_comments(read(INCIDENT_EVENTS)), "nuclear_incident.1.c")
        for gate in ("nd_launch_under_attack_context = { SUSPECT = scope:nd_warning_suspect }",
                     "nd_launch_under_attack_doctrine = { SUSPECT = scope:nd_warning_suspect }",
                     "nd_pledge_permits_strike = { ENEMY = scope:nd_warning_suspect }",
                     "nd_war_law_permits_strategic_strike = yes",
                     "nd_forces_assembled = yes",
                     "show_as_unavailable"):
            self.assertIn(gate, body, gate)


class TestIncidentRoll(unittest.TestCase):
    """nd_incident_permille is fractional at low readiness (0.5-0.9 once its
    multipliers apply), and nothing proves `random` rolls a fraction instead
    of truncating it, so the roll's inner chance is always a rounded whole
    number (nd_roll_incident's header)."""

    def test_the_inner_chances_are_rounded(self):
        roll = block(strip_comments(read(EFFECTS)), "nd_roll_incident")
        self.assertEqual(re.findall(r"chance\s*=\s*(\w+)", roll),
                         ["1", "nd_incident_tenth_permille", "10", "nd_incident_permille_whole", "nd_incident_weekly_percent"])
        values = strip_comments(read(VALUES))
        for name in ("nd_incident_tenth_permille", "nd_incident_permille_whole", "nd_incident_weekly_percent"):
            self.assertIn("round = yes", block(values, name), name)


class TestTacticalTargets(unittest.TestCase):
    """nd_state_has_military_target is the tactical strike's one target list:
    the action's state pickers read it, and its AI score covers every
    building on it (a building missing from the score is a target the AI
    never prefers)."""

    def setUp(self):
        self.targets = set(re.findall(r"has_building = (\w+)",
                                      block(strip_comments(read(TRIGGERS)), "nd_state_has_military_target")))
        self.action = block(strip_comments(read(NUKE)), "tactical_nuke_diplo_action")

    def test_military_bases_are_targets(self):
        self.assertIn("building_military_base", self.targets)

    def test_state_pickers_read_the_shared_trigger(self):
        for picker in ("second_state_trigger", "will_select_as_second_state"):
            body = block(self.action, picker)
            self.assertIn("nd_state_has_military_target = yes", body, picker)
            self.assertNotIn("has_building =", body, picker)

    def test_score_covers_exactly_the_targets(self):
        scored = set(re.findall(r"b:(\w+)\.level", block(self.action, "propose_score")))
        self.assertEqual(scored, self.targets)

    def test_score_counts_the_chance_of_getting_through(self):
        per_state = block(block(self.action, "propose_score"), "scope:second_state")
        self.assertIn("multiply = nuclear_strike_success_fraction_here", per_state)


class TestTacticalInstallationDamage(unittest.TestCase):
    """A tactical strike halves naval fortifications and military bases by
    removing and rebuilding them, which resets their production methods; the
    record/restore lists must name every method the building can run."""

    # pmg_base_building_naval_fortification's vanilla methods: CI has no game
    # install to read them from.
    VANILLA_NAVAL_FORTIFICATION_PMS = {"pm_naval_fortification_basic",
                                       "pm_naval_fortification_reinforced",
                                       "pm_naval_fortification_advanced"}

    def setUp(self):
        self.effects = strip_comments(read(EXTRA_EFFECTS))
        self.groups = strip_comments(read(EXTRA_PM_GROUPS))

    def listed_pms(self, name, building):
        body = block(self.effects, name)
        self.assertEqual(set(re.findall(r"BUILDING = (\w+)", body)), {building}, name)
        return set(re.findall(r"PM = (\w+)", body))

    def group_pms(self, group):
        return set(re.findall(r"\b(pm_\w+)", block(block(self.groups, group), "production_methods")))

    def test_military_base_list_is_every_method_of_every_group(self):
        base = block(strip_comments(read(EXTRA_BUILDINGS)), "building_military_base")
        groups = re.findall(r"\b(pmg_\w+)", block(base, "production_method_groups"))
        expected = set().union(*(self.group_pms(g) for g in groups))
        self.assertEqual(self.listed_pms("nuclear_strike_military_base_pms", "building_military_base"), expected)

    def test_naval_fortification_list_is_vanilla_plus_the_injected_tiers(self):
        injected = set(re.findall(r"\b(pm_\w+)", block(self.groups, "INJECT:pmg_base_building_naval_fortification")))
        self.assertEqual(self.listed_pms("nuclear_strike_naval_fortification_pms", "building_naval_fortification"),
                         self.VANILLA_NAVAL_FORTIFICATION_PMS | injected)

    def test_only_sites_without_units_are_damaged(self):
        body = block(self.effects, "nuclear_tactical_strike_damage_installations")
        self.assertEqual(set(re.findall(r"BUILDING = (\w+)", body)),
                         {"building_naval_fortification", "building_military_base"})
        self.assertIn("nuclear_tactical_strike_damage_installations = yes", block(self.effects, "nuclear_tactical_strike"))

    def test_base_rebuild_is_guarded_by_its_unlocking_tech(self):
        base = block(strip_comments(read(EXTRA_BUILDINGS)), "building_military_base")
        tech = re.findall(r"\b(\w+)", block(base, "unlocking_technologies"))
        self.assertEqual(len(tech), 1)
        body = block(self.effects, "nuclear_tactical_strike_damage_installations")
        self.assertIn(f"has_technology_researched = {tech[0]}", body)


class TestFollowThrough(unittest.TestCase):
    def setUp(self):
        self.triggers = strip_comments(read(TRIGGERS))
        self.effects = strip_comments(read(CRISIS_EFFECTS))

    def test_triggers_exist(self):
        for name in ("nd_threat_bluff_nfu", "nd_threat_law_permits", "nd_threat_existential_stake",
                     "nd_threat_backed", "nd_threat_uncertain", "nd_enemy_threatens_existence_in_play"):
            self.assertRegex(self.triggers, rf"(?m)^{name} = \{{")

    def test_classification_writes_every_reason_once(self):
        body = block(self.effects, "nd_crisis_classify_follow_through")
        codes = re.findall(r"name = nd_ft_reason value = (\d)", body)
        self.assertEqual(sorted(codes), [str(c) for c in range(1, 9)])

    def test_ai_never_bluffs_in_public(self):
        self.assertIn("nd_threat_backed = { TARGET = $TARGET$ }",
                      block(self.triggers, "nd_ai_would_issue_ultimatum"))

    def test_ai_bluffs_in_private_only_when_aggressive(self):
        warn = block(self.triggers, "nd_ai_would_warn")
        self.assertRegex(warn, r"OR = \{\s*nd_threat_backed = \{ TARGET = \$TARGET\$ \}\s*ruler_is_aggressive = yes\s*\}")


DANGER_PARTS = ["nd_cd_stage", "nd_cd_issuer_readiness", "nd_cd_target_readiness", "nd_cd_public",
                "nd_cd_counter", "nd_cd_reliability", "nd_cd_weeks", "nd_cd_talks", "nd_cd_backed",
                "nd_cd_exercise", "nd_cd_vulnerability"]
PRESSURE_PARTS = ["nd_yp_base", "nd_yp_answer", "nd_yp_issuer_exposure", "nd_yp_protector", "nd_yp_credibility", "nd_yp_alert",
                  "nd_yp_recessed", "nd_yp_danger", "nd_yp_exercise", "nd_yp_temperament", "nd_yp_war",
                  "nd_yp_stakes", "nd_yp_follow_through", "nd_yp_taboo"]


class TestCrisisFigures(unittest.TestCase):
    def setUp(self):
        self.values = strip_comments(read(VALUES))
        self.effects = strip_comments(read(CRISIS_EFFECTS))

    def summed(self, total):
        body = block(self.values, total)
        return re.findall(r"(?:value|add) = (nd_(?:cd|yp)_\w+)_value\b", body)

    def test_totals_are_exactly_their_parts(self):
        self.assertEqual(self.summed("nd_crisis_danger_value"), DANGER_PARTS)
        self.assertEqual(self.summed("nd_yield_pressure_value"), PRESSURE_PARTS)

    def test_every_part_has_a_value(self):
        for part in DANGER_PARTS + PRESSURE_PARTS:
            self.assertRegex(self.values, rf"(?m)^{part}_value = \{{", part)

    def test_refresh_stores_every_part_under_its_own_value(self):
        body = block(self.effects, "nd_crisis_refresh_figures")
        stored = re.findall(r"nd_crisis_store_(?:cd|yp) = \{ C = (\w+) V = (\w+) \}", body)
        self.assertEqual([c for c, _ in stored], DANGER_PARTS + PRESSURE_PARTS)
        for c, v in stored:
            self.assertEqual(v, c + "_value")

    def test_clear_removes_every_part(self):
        body = block(self.effects, "nd_crisis_clear_figures")
        for var in DANGER_PARTS + PRESSURE_PARTS + ["nd_cd_dampened", "nd_ft_reason"]:
            self.assertIn(f"remove_variable = {var}", body, var)

    def test_losing_war_is_read_from_the_target(self):
        self.assertNotIn("is_losing_war_against", block(self.values, "nd_yp_war_value"))
        self.assertIn("nd_is_losing_war_to = { ENEMY = scope:nd_issuer }", block(self.values, "nd_yp_war_value"))
        self.assertNotIn("ROOT", block(strip_comments(read(TRIGGERS)), "nd_is_losing_war_to"))

    def test_refresh_is_the_only_writer_of_the_totals(self):
        for path in (CRISIS_EFFECTS, EFFECTS, CRISIS_EVENTS, INCIDENT_EVENTS):
            text = strip_comments(read(path))
            if path == CRISIS_EFFECTS:
                text = text.replace(block(text, "nd_crisis_refresh_figures"), "")
            self.assertNotRegex(text, r"name = nd_(?:crisis_danger|yield_pressure) value", path.name)


class TestSurvivorsInCrisis(unittest.TestCase):
    """The answer in kind reads survivors, the issuer's own exposure weighs on
    the threat, and a vulnerable force raises the danger (2026-10-28 rework
    spec §3.3)."""

    def setUp(self):
        self.values = strip_comments(read(VALUES))
        self.effects = strip_comments(read(CRISIS_EFFECTS))
        self.sguis = strip_comments(read(SGUIS))

    def test_new_parts_are_stored_cleared_and_shown(self):
        for part, sgui in (("nd_yp_issuer_exposure", "nd_crisis_pressure_breakdown_sgui"),
                           ("nd_cd_vulnerability", "nd_crisis_danger_breakdown_sgui")):
            self.assertRegex(self.values, rf"(?m)^{part}_value = \{{")
            self.assertIn(f"C = {part} V = {part}_value", block(self.effects, "nd_crisis_refresh_figures"))
            self.assertIn(f"remove_variable = {part}", block(self.effects, "nd_crisis_clear_figures"))
            self.assertIn(f"C = {part} KEY = {part}_line", block(self.sguis, sgui))
            self.assertIsNotNone(loc_value(f"{part}_line"), part)

    def test_answer_has_no_line_at_50(self):
        body = block(self.values, "nd_yp_answer_value")
        self.assertNotIn(">= 50", body)
        self.assertNotIn("nd_authority_automatic", body)
        self.assertIn("nd_yp_answer_survivors_value", body)
        self.assertIn("multiply = -25", body)

    def test_answer_three_quarters_rule(self):
        body = block(self.values, "nd_yp_answer_survivors_value")
        self.assertIn("nd_survivors_vs_issuer", body)
        self.assertIn("nd_authority_central = yes", body)
        self.assertIn("nd_decapitation_margin_value > 0", body)
        self.assertIn("multiply = 0.75", body)
        margin = block(self.values, "nd_decapitation_margin_value")
        self.assertIn("nd_believed_stockpile", margin)
        self.assertIn("subtract = nd_redundancy", margin)

    def test_issuer_exposure_falls_to_minus_15(self):
        body = block(self.values, "nd_yp_issuer_exposure_value")
        self.assertIn("nd_believed_armed = yes", body)
        self.assertIn("nd_survivors_vs_target", body)
        self.assertIn("max = 3", body)
        self.assertIn("multiply = 5", body)

    def test_vulnerability_reads_the_more_vulnerable_armed_party(self):
        body = block(self.values, "nd_cd_vulnerability_value")
        self.assertIn("nd_own_vulnerability_value", body)
        self.assertIn("nd_believed_armed = yes", body)
        own = block(self.values, "nd_own_vulnerability_value")
        for needle in ("value = 50", "subtract = nd_effective_survivability", "divide = 5", "min = 0", "max = 10"):
            self.assertIn(needle, own)

    def test_refresh_stores_each_partys_survivors(self):
        body = block(self.effects, "nd_crisis_refresh_figures")
        self.assertEqual(body.count("name = nd_survivors_crisis"), 2)
        self.assertIn("remove_variable = nd_survivors_crisis", block(self.effects, "nd_crisis_clear_figures"))

    def test_ai_weights_read_survivors(self):
        events = strip_comments(read(CRISIS_EVENTS))
        for name in ("nuclear_crisis.1.c", "nuclear_crisis.20.c"):
            self.assertNotIn("nd_effective_survivability", option_body(events, name))


class TestCrisisSubjects(unittest.TestCase):
    """Stakes weigh on the pressure, an armed co-belligerent covers an unarmed
    one for the war, and an armed rival is not a proliferator (2026-10-28
    rework spec §8.2–§8.4)."""

    def setUp(self):
        self.values = strip_comments(read(VALUES))
        self.triggers = strip_comments(read(TRIGGERS))
        self.crisis = strip_comments(read(CRISIS_EFFECTS))
        self.effects = strip_comments(read(EFFECTS))

    def test_proliferation_needs_unarmed_target(self):
        body = block(self.triggers, "nd_dispute_proliferation_by")
        self.assertRegex(body, r"\$TARGET\$ = \{[^}]*nd_believed_armed = no")

    def test_cobelligerent_branch_in_guarantee_triggers(self):
        for name, branch in (("nd_has_armed_guarantor_against", "nd_cobelligerent_cover_against"),
                             ("nd_has_ready_guarantor_against", "nd_cobelligerent_cover_against"),
                             ("nd_is_guaranteed_by", "nd_cobelligerent_of"),
                             ("nd_covered_country_struck_by", "any_cobelligerent_in_war"),
                             ("nd_covered_country_struck", "any_cobelligerent_in_war")):
            self.assertIn(branch, block(self.triggers, name), name)
        cover = block(self.triggers, "nd_cobelligerent_cover_against")
        for needle in ("nd_believed_armed = no", "has_war_with = $AGAINST$", "any_cobelligerent_in_war",
                       "nd_believed_armed = yes"):
            self.assertIn(needle, cover)

    def test_cobelligerent_branch_skips_treaty_and_umbrella(self):
        for body in (block(self.crisis, "nd_crisis_notify_guarantors"), block(self.effects, "nd_record_nuclear_use")):
            loop = body[body.index("every_cobelligerent_in_war"):]
            limit = block(loop, "limit")
            self.assertRegex(limit, r"NOT = \{[^}]*nd_is_guaranteed_by_treaty")
            self.assertRegex(limit, r"NOT = \{[^}]*nd_under_umbrella_of")
            self.assertIn("name = nd_guarantee_basis value = 3", loop)
            self.assertIn("name = nd_guarantee_basis value = 1", body)
            self.assertIn("name = nd_guarantee_basis value = 2", body)

    def test_cobelligerent_abandon_costs_five(self):
        body = block(self.crisis, "nd_guarantee_act_abandon")
        branch = body[body.index("var:nd_guarantee_basis = 3"):body.index("else = {")]
        branch += block(self.crisis, "nd_cobelligerent_abandon_effects")
        self.assertIn("AMOUNT = -5", branch)
        self.assertNotIn("nd_guarantee_abandoned", branch)
        self.assertNotIn("every_scope_treaty", branch)
        self.assertNotIn("add_liberty_desire", branch)

    def test_stakes_part(self):
        self.assertRegex(self.values, r"(?m)^nd_yp_stakes_value = \{")
        self.assertIn("min = -40", block(self.values, "nd_yp_stakes_value"))
        self.assertIn("C = nd_yp_stakes V = nd_yp_stakes_value", block(self.crisis, "nd_crisis_refresh_figures"))
        self.assertIn("remove_variable = nd_yp_stakes", block(self.crisis, "nd_crisis_clear_figures"))
        self.assertIn("C = nd_yp_stakes KEY = nd_yp_stakes_line",
                      block(strip_comments(read(SGUIS)), "nd_crisis_pressure_breakdown_sgui"))
        self.assertIsNotNone(loc_value("nd_yp_stakes_line"))

    def test_unstaked_total_is_every_other_part(self):
        body = block(self.values, "nd_yield_pressure_unstaked_value")
        parts = re.findall(r"(?:value|add) = (nd_yp_\w+)_value\b", body)
        self.assertEqual(parts, [p for p in PRESSURE_PARTS if p != "nd_yp_stakes"])

    def test_ai_stake_gate(self):
        self.assertIn("nd_ai_stakes_block = { TARGET = $TARGET$ }", block(self.triggers, "nd_ai_would_warn"))
        gate = block(self.triggers, "nd_ai_stakes_block")
        self.assertIn("nd_yield_pressure_unstaked_value >= nd_ai_concession_line", gate)
        self.assertIn("nd_yield_pressure_value < nd_ai_concession_line", gate)
        self.assertRegex(self.values, r"(?m)^nd_ai_concession_line = 40\b")


class TestReviewFixesPhase1(unittest.TestCase):
    """The mid-phase review's fixes (rework phase 1)."""

    def setUp(self):
        self.values = strip_comments(read(VALUES))
        self.triggers = strip_comments(read(TRIGGERS))
        self.effects = strip_comments(read(EFFECTS))
        self.crisis = strip_comments(read(CRISIS_EFFECTS))
        self.cev = strip_comments(read(CRISIS_EVENTS))
        self.iev = strip_comments(read(INCIDENT_EVENTS))

    def test_an_unarmed_country_drops_its_main_rival(self):
        update = block(self.effects, "nd_monthly_update")
        unarmed = update[update.index("else = {"):]
        self.assertIn("nd_refresh_main_rival = yes", unarmed[:unarmed.index("nd_tick_countdown")])
        cleanup = block(self.effects, "nd_country_monthly_cleanup")
        self.assertIn("nd_refresh_main_rival = yes", cleanup)

    def test_ai_weights_read_survivors_stored_by_an_effect(self):
        # A scope a trigger saves as temporary may not reach a script value
        # (unverified), so the AI's weights read figures an effect stored.
        self.assertNotRegex(self.triggers, r"(?m)^nd_vulnerable_to = \{")
        self.assertIn("var:nd_survivors_crisis >= 3", option_body(self.cev, "nuclear_crisis.1.c"))
        self.assertIn("var:nd_survivors_vs_attacker < 3", option_body(self.cev, "nuclear_crisis.20.c"))
        self.assertIn("nd_guarantor_store_survivors = yes", block(self.cev, "nuclear_crisis.20"))
        self.assertIn("name = nd_survivors_vs_attacker value = nd_survivors_vs_saved",
                      block(self.crisis, "nd_guarantor_store_survivors"))
        warning = block(self.effects, "nd_start_unconfirmed_warning")
        self.assertIn("name = nd_survivors_vs_suspect value = nd_survivors_vs_saved", warning)
        self.assertLess(warning.index("nd_survivors_vs_suspect"), warning.index("id = nuclear_incident.1 "))
        body = block(self.iev, "nuclear_incident.1")
        order = body[body.index("name = nuclear_incident.1.c"):]
        self.assertIn("var:nd_survivors_vs_suspect < 3", block(order, "ai_chance"))

    def test_trigger_temp_scope_self_check(self):
        body = block(self.effects, "nd_refresh_main_rival")
        check = body[:body.index("save_scope_as = nd_sv_enemy")]
        self.assertIn("NOT = { exists = scope:nd_sv_enemy }", check)
        self.assertIn("nd_counterforce_reach_visible = { ENEMY = scope:nd_mr_rival }", check)
        self.assertIn("TE_SELF_CHECK OK nd_trigger_temp_scope", check)
        self.assertIn("TE_SELF_CHECK BROKEN nd_trigger_temp_scope", check)
        self.assertIn("save_temporary_scope_as = nd_sv_enemy", block(self.triggers, "nd_counterforce_reach_visible"))

    def test_no_line_at_50_in_the_readiness_hover(self):
        self.assertNotIn("From #v 50#!", loc_value("nd_w_readiness_head_survivability_tt"))

    def test_the_governments_order_is_narrated_as_deliberate(self):
        body = block(self.iev, "nuclear_incident.1")
        order = body[body.index("name = nuclear_incident.1.c"):]
        self.assertLess(order.index("save_scope_as = nd_deliberate_response"), order.index("nd_launch_or_intercept"))

    def test_high_alert_only_over_an_armed_crisis_opponent(self):
        review = block(self.effects, "nd_ai_review_posture")
        i = review.index("var:nd_survivors_main_r2 < 3")
        self.assertIn("var:nd_crisis_opponent ?= { nd_believed_armed = yes }", review[i - 300:i])

    def test_vulnerability_reads_public_belief(self):
        body = block(self.values, "nd_cd_vulnerability_value")
        self.assertIn("nd_believed_armed = yes", body)
        self.assertNotIn("nd_is_armed", body)

    def test_old_saves_settle_to_the_new_ceiling(self):
        step = block(self.values, "nd_survivability_step")
        hardening = step[:step.index("else_if")]
        self.assertNotIn("min = 0", hardening)


class TestProbeFindings20261028(unittest.TestCase):
    """What the 2026-10-28 engine probe changed (scripting_best_practices.md §
    "War Goals, Plays, Adjacency and Claims"): is_target_of_wargoal finds
    nothing in a play, and in a war it also flags the capital under a
    country-level goal."""

    def setUp(self):
        self.values = strip_comments(read(VALUES))
        self.triggers = strip_comments(read(TRIGGERS))

    def test_stakes_count_goal_types_not_states(self):
        territory = block(self.values, "nd_yp_stakes_territory_value")
        self.assertNotIn("is_target_of_wargoal", territory)
        self.assertNotIn("every_scope_state", territory)
        for t in ("conquer_state", "return_state", "take_treaty_port", "liberate_country"):
            self.assertIn(f"TYPE = {t} ", territory)
        self.assertNotRegex(self.values, r"(?m)^nd_stakes_states_counted_value = ")
        self.assertNotIn("nd_stakes_self_check", strip_comments(read(CRISIS_EFFECTS)))

    def test_core_threat_needs_a_state_taking_goal(self):
        body = block(self.triggers, "nd_core_threatened_by")
        self.assertIn("is_target_of_wargoal = $ENEMY$", body)
        for t in ("conquer_state", "return_state", "take_treaty_port"):
            self.assertIn(f"war_side_has_war_goal_of_type_against = {{ type = {t} target = scope:nd_ct_self }}", body)


class TestFinalReviewFixesPhase1(unittest.TestCase):
    """The final review's fixes (rework phase 1)."""

    def setUp(self):
        self.values = strip_comments(read(VALUES))
        self.triggers = strip_comments(read(TRIGGERS))
        self.crisis = strip_comments(read(CRISIS_EFFECTS))

    def test_abandon_tests_the_cobelligerent_case_positively(self):
        body = block(self.crisis, "nd_guarantee_act_abandon")
        self.assertNotRegex(body, r"NOT = \{\s*has_variable = nd_guarantee_basis\s*var:nd_guarantee_basis = 3\s*\}")
        self.assertRegex(body, r"if = \{\s*limit = \{\s*has_variable = nd_guarantee_basis\s*var:nd_guarantee_basis = 3\s*\}")
        self.assertIn("nd_cobelligerent_abandon_effects = yes", body)

    def test_an_ally_that_walks_away_stops_counting_as_a_protector(self):
        body = block(self.crisis, "nd_cobelligerent_abandon_effects")
        self.assertIn("name = nd_crisis_abandoned value = 1", body)
        self.assertIn("var:nd_guarantee_context = 1", body)

    def test_an_armed_ally_lifts_the_nuclear_shadow(self):
        injections = strip_comments(read(ROOT / "common/script_values/zz_te_war_support_injections.txt"))
        i = injections.index("WAR_SUPPORT_TE_NUCLEAR_SHADOW")
        shadow = injections[injections.rindex("if = {", 0, injections.rindex("limit", 0, i)):i]
        self.assertRegex(shadow, r"NOT = \{ this = ROOT \}\s*NOT = \{ has_war_with = ROOT \}\s*nd_believed_armed = yes")

    def test_existence_goals_are_not_counted_twice_in_a_war(self):
        body = block(self.values, "nd_yp_stakes_value")
        self.assertIn("nd_enemy_threatens_existence = { ENEMY = scope:nd_issuer }", body)
        self.assertIn("add = 15", body)

    def test_stake_gate_runs_last_and_not_for_a_guarantee(self):
        warn = block(self.triggers, "nd_ai_would_warn")
        self.assertGreater(warn.index("nd_ai_stakes_block"), warn.index("A cautious ruler") if "A cautious ruler" in warn
                           else warn.index("ruler_is_cautious = no"))
        self.assertRegex(warn, r"OR = \{\s*nd_dispute_guarantee_against = \{ TARGET = \$TARGET\$ \}"
                               r"(?:\s*nd_dispute_peacetime_strike_by = \{ TARGET = \$TARGET\$ \})?\s*NOT = \{ nd_ai_stakes_block")

    def test_acute_record_also_at_close(self):
        self.assertIn("nd_log_crisis_acute_once = yes", block(self.crisis, "nd_crisis_close"))

    def test_more_goal_types_count(self):
        body = block(self.values, "nd_yp_stakes_value") + block(self.values, "nd_yp_stakes_territory_value") + \
            block(self.values, "nd_yp_stakes_minor_value")
        for t in ("unification", "restore_union", "te_colonial_reconquest", "secession", "release_as_subject",
                  "te_colonial_independence", "te_un_mandate_restore_state", "break_enforced_treaties"):
            self.assertIn(f"TYPE = {t} ", body, t)

    def test_main_rival_hover_figures_cleared(self):
        body = block(strip_comments(read(EFFECTS)), "nd_refresh_main_rival")
        for name in ("nd_main_rival_reach", "nd_exposed_main"):
            self.assertIn(f"remove_variable = {name}", body)

    def test_survivors_shown_to_one_decimal(self):
        self.assertIn("Var('nd_survivors_main').GetValue|1", loc_value("nd_w_survivors_value"))


class TestSuezConcession(unittest.TestCase):
    """Yielding in a war drops the target's side's goals against the other
    side and costs 15 war support (2026-10-28 rework spec §8.1)."""

    def setUp(self):
        self.crisis = strip_comments(read(CRISIS_EFFECTS))
        self.triggers = strip_comments(read(TRIGGERS))

    def test_concession_drops_goals_and_15_support(self):
        body = block(self.crisis, "nd_crisis_concede_war")
        self.assertIn("value = -15", body)
        self.assertNotIn("value = -35", body)
        self.assertIn("nd_crisis_drop_goals = { WHO = target }", body)
        self.assertIn("nd_crisis_drop_goals = { WHO = initiator }", body)
        drop = block(self.crisis, "nd_crisis_drop_goals")
        for typ in ("conquer_state", "annex_country", "humiliation", "make_protectorate", "te_reunify_country"):
            self.assertIn(f"remove_war_goal = {{ who = $WHO$ type = {typ} }}", drop, typ)
        self.assertIn("diplomatic_play = {", drop)

    def wars_loop(self):
        return block(block(self.crisis, "nd_crisis_concede_war"), "every_scope_war")

    def test_concession_without_goals_is_war_support_only(self):
        # The war support line is a direct child of the war loop, not inside
        # the goals branch, so a war in which we hold no goals still costs it.
        loop = self.wars_loop()
        support = loop.index("add_war_war_support")
        self.assertEqual(loop[:support].count("{") - loop[:support].count("}"), 0)

    def test_concession_side_from_defending_side(self):
        goals = " ".join(block(self.wars_loop(), "if").split())
        self.assertIn("if = { limit = { is_on_defending_side = scope:nd_target } nd_crisis_drop_goals = { WHO = target } }"
                      " else = { nd_crisis_drop_goals = { WHO = initiator } }", goals)

    def test_suez_self_check_line(self):
        ev = block(strip_comments(read(CRISIS_EVENTS)), "nuclear_crisis.25")
        self.assertIn("TE_SELF_CHECK OK nd_suez_goals", ev)
        self.assertIn("TE_SELF_CHECK BROKEN nd_suez_goals", ev)
        self.assertIn("war_side_has_war_goal_of_type_against = { type = conquer_state target = $TARGET$ }",
                      block(self.triggers, "nd_side_holds_any_goal_against"))
        self.assertNotIn("35", loc_value("nd_tt_yield_war"))
        self.assertIn("15", loc_value("nd_tt_yield_war"))


class TestPeacetimeStrikeDispute(unittest.TestCase):
    """Dispute code 6: the target struck us, or a country we cover, outside a
    war in the last 24 months (2026-10-28 rework spec §8.5)."""

    def setUp(self):
        self.crisis = strip_comments(read(CRISIS_EFFECTS))
        self.triggers = strip_comments(read(TRIGGERS))
        self.effects = strip_comments(read(EFFECTS))
        self.custom = strip_comments(read(CUSTOM_LOC))

    def test_code_6_classified_between_guarantee_and_proliferation(self):
        body = block(self.crisis, "nd_crisis_classify_dispute")
        g = body.index("nd_dispute_guarantee_against")
        six = body.index("nd_dispute_peacetime_strike_by")
        p = body.index("nd_dispute_proliferation_by")
        self.assertLess(g, six)
        self.assertLess(six, p)
        self.assertIn("name = nd_crisis_dispute value = 6", body)

    def test_code_6_at_every_site(self):
        for name in ("nd_crisis_preview", "nd_crisis_revalidate_dispute", "nd_crisis_act_yield", "nd_crisis_yield_lines"):
            body = block(self.crisis, name)
            self.assertTrue("= 6" in body or "D = 6" in body or "nd_dispute_peacetime_strike_by" in body, name)
        for name in ("nd_has_crisis_dispute_with", "nd_crisis_issuer_is_defensive", "nd_ai_would_warn"):
            body = block(self.triggers, name)
            self.assertTrue("nd_dispute_peacetime_strike_by" in body or "var:nd_crisis_dispute = 6" in body, name)
        for name in ("nd_crisis_dispute_phrase", "nd_crisis_dispute_word", "nd_crisis_demand_text",
                     "nd_crisis_concession_past", "nd_crisis_concession_short", "nd_crisis_concession_long"):
            self.assertRegex(block(self.custom, name), r"_6\b", name)
        for key in ("nd_crisis_dispute_phrase_6", "nd_crisis_dispute_6", "nd_crisis_demand_6", "nd_concession_past_they_6",
                    "nd_concession_past_we_6", "nd_concession_short_6", "nd_concession_long_6",
                    "nd_tt_open_over_peacetime_strike", "nd_tt_yield_reparations"):
            self.assertIsNotNone(loc_value(key), key)

    def test_record_written_outside_war(self):
        body = block(self.effects, "nd_record_nuclear_use")
        i = body.index("name = nd_peacetime_struck_by")
        self.assertIn("NOT = { has_war_with = $VICTIM$ }", body[max(0, i - 300):i])
        self.assertIn("days = 730", body[i:i + 120])

    def test_code_6_revalidates_on_the_record(self):
        body = block(self.crisis, "nd_crisis_revalidate_dispute")
        i = body.index("var:nd_crisis_dispute = 6")
        self.assertIn("nd_dispute_peacetime_strike_by", body[i:i + 600])
        self.assertIn("OUTCOME = 10", body[i:i + 900])

    def test_honor_after_peacetime_strike_opens_a_crisis(self):
        self.assertIn("nd_dispute_peacetime_strike_by = { TARGET = $TARGET$ }", block(self.triggers, "nd_has_crisis_dispute_with"))
        trig = block(self.triggers, "nd_dispute_peacetime_strike_by")
        for needle in ("var:nd_peacetime_struck_by ?= $TARGET$", "nd_under_umbrella_of", "has_type = nuclear_guarantee"):
            self.assertIn(needle, trig)

    def test_reparations_concession(self):
        body = block(self.crisis, "nd_crisis_concede_reparations")
        for needle in ("nd_loose_compensation_value", "add_treasury", "name = nd_loose_inspected value = 1 days = 7300",
                       "name = nd_loose_inspections", "remove_variable = nd_peacetime_struck_by"):
            self.assertIn(needle, body)
        self.assertNotIn("nd_loose_answer", body)

    def test_no_35_left_in_war_concession_texts(self):
        for key in ("nd_concession_long_2", "nd_concession_long_3", "nd_concession_past_they_2", "nd_concession_past_they_3",
                    "nd_concession_past_we_2", "nd_concession_past_we_3", "nd_concession_short_2", "nd_tt_open_over_guarantee",
                    "nd_tt_open_over_war"):
            self.assertNotIn("35", loc_value(key), key)


class TestStrikeClaims(unittest.TestCase):
    """A launcher may claim a strike was unauthorized (2026-10-28 rework spec
    §5.4): true after an unordered launch, false under Disavow our strikes or
    an AI's lie."""

    def setUp(self):
        self.effects = strip_comments(read(EFFECTS))
        self.values = strip_comments(read(VALUES))

    def claim(self):
        return block(self.effects, "nd_record_claim")

    def test_each_new_effect_defined_once(self):
        # A patch re-run once defined nd_record_claim twice; the duplicate-key
        # audit only warns on an identical repeat.
        for name in ("nd_record_claim", "nd_claim_schedule_truth", "nd_claim_clear"):
            self.assertLessEqual(len(re.findall(rf"(?m)^{name} = \{{", read(EFFECTS))), 1, name)

    def test_claim_recorded_before_the_victims_event(self):
        strike = block(strip_comments(read(EXTRA_EFFECTS)), "nuclear_first_strike")
        self.assertLess(strike.index("nd_record_claim = yes"), strike.index("id = nuclear_weapon_events.1 "))

    def test_no_claim_on_an_answer(self):
        self.assertIn("NOT = { nd_was_struck_by = { ENEMY = scope:target_country } }", self.claim())

    def test_unordered_launch_claims_true(self):
        body = self.claim()
        i = body.index("nd_strike_from_incident = yes")
        self.assertIn("name = nd_claim_kind value = 1", body[i:i + 200])

    def test_ai_lie_rate(self):
        body = block(self.values, "nd_ai_lies_value")
        for needle in ("value = 15", "ruler_is_aggressive = yes", "multiply = 2", "has_trait = ruthless",
                       "has_trait = grifter", "multiply = 1.5", "has_trait = honorable", "multiply = 0.25",
                       "has_trait = direct", "nd_taboo_value >= 50", "multiply = 0.5"):
            self.assertIn(needle, body)
        claim = self.claim()
        self.assertIn("chance = nd_ai_lies_value", claim)
        self.assertIn("has_variable = nd_disavow_strikes", claim)

    def test_claim_record_once_per_strike(self):
        body = self.claim()
        self.assertIn("name = nd_struck_count", body)
        self.assertIn("days = 30", body)
        self.assertIn("change_global_variable = { name = nd_claim_counter add = 1 }", body)
        for var in ("nd_claim_by", "nd_claim_true", "nd_claim_id"):
            self.assertIn(f"name = {var} value", body)
        # The decision runs only for a strike's first warhead.
        self.assertLess(body.index("var:nd_last_striker ?= scope:attacking_country"), body.index("nd_ai_lies_value"))

    def test_toggle_ops_in_step(self):
        gui = read(GUI)
        for op in (70, 71):
            self.assertIn(f"'(CFixedPoint){op}'", gui)
            self.assertIn(f"scope:op = {op}", strip_comments(read(SGUIS)))
        self.assertIn("70/71", gui)
        self.assertIn("70 / 71", read(SGUIS))
        self.assertIn("70 / 71", read(JE_DOC))
        self.assertIn("has_variable = nd_disavow_strikes", block(strip_comments(read(SGUIS)), "nd_disavowing_sgui"))


class TestVictimWeighsTheClaim(unittest.TestCase):
    """The struck country weighs a claim that the strike was unauthorized
    (2026-10-28 rework spec §5.4)."""

    def setUp(self):
        self.events = strip_comments(read(WEAPON_EVENTS))
        self.values = strip_comments(read(VALUES))
        self.ev1 = block(self.events, "nuclear_weapon_events.1")

    def test_belief_rolled_once_per_claim(self):
        imm = block(self.ev1, "immediate")
        self.assertIn("var:nd_claim_belief_rolled_for = var:nd_claim_id", imm)
        self.assertIn("chance = nd_claim_belief_value", imm)
        self.assertIn("name = nd_claim_belief_rolled_for value = var:nd_claim_id", imm)

    def test_belief_value_terms(self):
        body = block(self.values, "nd_claim_belief_value")
        for needle in ("value = 40", "divide = 4", "add = 20", "subtract = 20", "multiply = 30", "min = 5", "max = 90"):
            self.assertIn(needle, body)

    def test_accept_option_gated_on_a_claim(self):
        accept = option_body(self.events, "nuclear_weapon_events.1.k")
        trig = block(accept, "trigger")
        self.assertIn("nd_strike_carries_claim = { ENEMY = scope:attacking_country }", trig)
        self.assertIn("nd_auto_answers_strike", trig)
        self.assertIn("id = nuclear_weapon_events.27", accept)
        self.assertIn("name = nd_claim_accepted value = var:nd_claim_id", accept)
        self.assertIn("var:nd_claim_believed = 1", block(accept, "ai_chance"))

    def test_reparations_event_pay_or_refuse(self):
        ev = block(self.events, "nuclear_weapon_events.27")
        pay = option_body(self.events, "nuclear_weapon_events.27.a")
        self.assertIn("nd_loose_compensation_value", pay)
        self.assertIn("add_treasury", pay)
        refuse = option_body(self.events, "nuclear_weapon_events.27.b")
        self.assertIn("value = -30", refuse)
        self.assertIn("exists = scope:nd_claim_victim", ev)

    def test_claim_shown_in_the_text(self):
        desc = block(self.ev1, "desc")
        self.assertIn("nuclear_weapon_events.1.d_claim", desc)
        self.assertIsNotNone(loc_value("nuclear_weapon_events.1.d_claim"))


class TestClaimTruth(unittest.TestCase):
    """The truth about a claim comes out 6 to 18 months later, sooner with a
    covert network (2026-10-28 rework spec §5.4)."""

    def setUp(self):
        self.effects = strip_comments(read(EFFECTS))
        self.events = strip_comments(read(WEAPON_EVENTS))

    def test_truth_scheduled_by_the_claim(self):
        self.assertIn("nd_claim_schedule_truth = yes", block(self.effects, "nd_record_claim"))

    def test_truth_delays_are_literal(self):
        body = block(self.effects, "nd_claim_schedule_truth")
        for days in (180, 270, 365, 455, 545, 90):
            self.assertIn(f"days = {days}", body)
        self.assertIn("sr_has_intel_tier = { TARGET = scope:attacking_country TIER = 1 }", body)
        self.assertIn("id = nuclear_weapon_events.28", body)
        self.assertIn("id = nuclear_weapon_events.29", body)
        self.assertNotIn("$", body.replace("$EVENT$", ""))

    def test_truth_revalidates_parties(self):
        for eid in ("nuclear_weapon_events.28", "nuclear_weapon_events.29", "nuclear_weapon_events.30"):
            trig = block(block(self.events, eid), "trigger")
            self.assertIn("exists = scope:nd_truth_launcher", trig, eid)
            self.assertIn("is_country_alive = yes", trig, eid)

    def test_exposed_lie_costs(self):
        body = option_body(self.events, "nuclear_weapon_events.30.a")
        for needle in ("AMOUNT = -20", "change_infamy = nd_taboo_infamy_threat", "value = -50",
                       "change_variable = { name = nd_false_claims add = 1 }"):
            self.assertIn(needle, body)
        self.assertIn("id = nuclear_weapon_events.30", block(self.events, "nuclear_weapon_events.29"))

    def test_rejected_true_claim_offers_reconciliation(self):
        body = option_body(self.events, "nuclear_weapon_events.28.b")
        self.assertIn("nd_claim_accepted", block(body, "trigger"))
        self.assertIn("value = 30", body)


def squash(text):
    return " ".join(text.split())


ACCEPTED_THIS_CLAIM = ("NOT = { AND = { has_variable = nd_claim_accepted"
                       " var:nd_claim_accepted = var:nd_claim_id } }")


class TestFinalReviewFixesPhase2(unittest.TestCase):
    """The phase 2 final review's fixes (PR #1223)."""

    def setUp(self):
        self.effects = strip_comments(read(EFFECTS))
        self.crisis = strip_comments(read(CRISIS_EFFECTS))
        self.triggers = strip_comments(read(TRIGGERS))
        self.events = strip_comments(read(WEAPON_EVENTS))
        self.crisis_events = strip_comments(read(CRISIS_EVENTS))
        self.ev1 = block(self.events, "nuclear_weapon_events.1")

    # A claim belongs to the strike that made it, not to every later warhead
    # or strike while its record stands.
    def test_strike_claim_id_set_at_the_first_warhead(self):
        body = block(self.effects, "nd_record_claim")
        self.assertIn("name = nd_strike_claim_id value = 0 days = 30", body)
        self.assertIn("name = nd_strike_claim_id value = global_var:nd_claim_counter days = 30", body)
        trig = squash(block(self.triggers, "nd_strike_carries_claim"))
        for needle in ("var:nd_claim_by ?= $ENEMY$", "var:nd_strike_claim_id = var:nd_claim_id"):
            self.assertIn(needle, trig)

    def test_victims_event_reads_the_strikes_claim(self):
        call = "nd_strike_carries_claim = { ENEMY = scope:attacking_country }"
        self.assertIn(call, block(self.ev1, "desc"))
        self.assertIn(call, block(self.ev1, "immediate"))
        accept = option_body(self.events, "nuclear_weapon_events.1.k")
        # The guarded form: no vanilla or mod precedent for ?= with a var: on
        # its right, so a variable is compared only once it is known set.
        self.assertIn(ACCEPTED_THIS_CLAIM, squash(block(accept, "trigger")))
        self.assertIn("has_variable = nd_claim_belief_rolled_for var:nd_claim_belief_rolled_for = var:nd_claim_id",
                      squash(block(accept, "ai_chance")))
        self.assertNotIn("?= var:", accept)
        self.assertNotIn("var:nd_claim_by ?= scope:attacking_country", self.ev1)

    def test_reconciliation_reads_this_claims_acceptance(self):
        trig = squash(block(option_body(self.events, "nuclear_weapon_events.28.b"), "trigger"))
        self.assertIn("NOT = { AND = { has_variable = nd_claim_id has_variable = nd_claim_accepted"
                      " var:nd_claim_accepted = var:nd_claim_id } }", trig)

    def test_accept_hidden_where_absorbing_is(self):
        # Recessed under Automatic Retaliation the standing order answers (.h),
        # so neither absorbing (.a) nor accepting the claim (.k) is offered.
        recessed_ar = ("NOT = { scope:target_country = { nd_authority_automatic = yes nd_is_armed = yes"
                       " nd_forces_assembled = no } }")
        self.assertIn(recessed_ar, squash(block(option_body(self.events, "nuclear_weapon_events.1.a"), "trigger")))
        self.assertIn(recessed_ar, squash(block(option_body(self.events, "nuclear_weapon_events.1.k"), "trigger")))

    # A tooltip walk writes nothing, so a variable set and read back in one
    # walked block logs every frame (scripting_best_practices.md).
    def test_reparations_paid_without_a_read_back(self):
        pay = option_body(self.events, "nuclear_weapon_events.27.a")
        concede = block(self.crisis, "nd_crisis_concede_reparations")
        for body in (pay, concede):
            self.assertNotIn("nd_reparations_due", body)
            self.assertEqual(body.count("nd_loose_compensation_value"), 2)
        imm = block(block(self.events, "nuclear_weapon_events.27"), "immediate")
        self.assertIn("save_scope_as = nd_loose_payer", imm)
        self.assertIn("save_scope_as = nd_loose_claimant", imm)

    def test_claim_decided_only_in_the_real_run(self):
        self.assertRegex(block(self.effects, "nd_record_claim"),
                         r"^\s*set_variable = nd_claim_click\s*if = \{\s*limit = \{ has_variable = nd_claim_click \}"
                         r"\s*remove_variable = nd_claim_click")

    # An answer to a first strike is no grievance against the one who struck.
    def test_no_record_against_the_first_striker(self):
        body = block(self.effects, "nd_record_nuclear_use")
        i = body.index("name = nd_peacetime_struck_by")
        self.assertIn("NOT = { nd_was_struck_by = { ENEMY = $VICTIM$ } }", body[max(0, i - 300):i])

    def test_paying_the_demand_settles_the_grievance(self):
        pay = option_body(self.events, "nuclear_weapon_events.27.a")
        self.assertIn("if = { limit = { var:nd_peacetime_struck_by ?= ROOT } remove_variable = nd_peacetime_struck_by }",
                      squash(pay))
        trig = squash(block(block(self.events, "nuclear_weapon_events.27"), "trigger"))
        self.assertIn("scope:nd_claim_victim = { is_country_alive = yes }", trig)

    # The war concession: only wars the two fight against each other, and
    # only a war leader's concession drops its side's goals.
    def test_only_wars_fought_against_each_other(self):
        lim = squash(block(block(block(self.crisis, "nd_crisis_concede_war"), "every_scope_war"), "limit"))
        self.assertIn("AND = { is_on_defending_side = scope:nd_target"
                      " NOT = { is_on_defending_side = scope:nd_crisis_other_side } }", lim)
        self.assertIn("AND = { is_on_defending_side = scope:nd_crisis_other_side"
                      " NOT = { is_on_defending_side = scope:nd_target } }", lim)

    def test_only_the_war_leader_drops_its_sides_goals(self):
        loop = block(block(self.crisis, "nd_crisis_concede_war"), "every_scope_war")
        lim = squash(block(block(loop, "if"), "limit"))
        self.assertIn("is_warleader = scope:nd_target", lim)
        self.assertIn("nd_side_holds_any_goal_against = { TARGET = scope:nd_crisis_other_side }", lim)
        self.assertNotIn("nd_suez_had_goals", self.crisis)

    def test_suez_self_check_a_day_later_naming_the_parties(self):
        concede = block(self.crisis, "nd_crisis_concede_war")
        self.assertNotIn("TE_SELF_CHECK", concede)
        self.assertIn("id = nuclear_crisis.25 days = 1", concede)
        self.assertIn("name = nd_suez_check_other value = scope:nd_crisis_other_side", concede)
        ev = block(self.crisis_events, "nuclear_crisis.25")
        self.assertIn("hidden = yes", ev)
        broken = next(line for line in ev.splitlines() if "TE_SELF_CHECK BROKEN nd_suez_goals" in line)
        self.assertIn("[THIS.GetCountry.GetNameNoFormatting]", broken)
        self.assertIn("[SCOPE.sCountry('nd_suez_check_other').GetNameNoFormatting]", broken)
        self.assertIn("remove_variable = nd_suez_check_other", ev)

    # A crisis their strike ended (outcome 7) leaves a cooldown that must not
    # outlast the grievance it ended over.
    def test_cooldown_waived_after_a_crisis_their_strike_ended(self):
        self.assertIn("AND = { var:nd_crisis_last_outcome ?= 7 var:nd_crisis_last_opponent ?= $TARGET$"
                      " nd_dispute_peacetime_strike_by = { TARGET = $TARGET$ } }",
                      squash(block(self.triggers, "nd_crisis_cooldown_clear")))

    # Texts.
    def test_no_35_war_support_left_in_any_text(self):
        for path in LOC_DIR.glob("*.yml"):
            for line in read(path).splitlines():
                m = re.match(r"\s+(nd_[A-Za-z0-9_.\-]+):\d*\s+\"(.*)\"\s*$", line)
                if m and "war support" in m.group(2):
                    self.assertNotRegex(m.group(2), r"\b35\b", m.group(1))

    def test_dispute_lists_name_the_strike(self):
        self.assertIn("nuclear strike", loc_value("nd_tt_has_dispute"))
        legend = loc_value("nd_w_crisis_actions_legend")
        self.assertIn("nuclear strike", legend)
        self.assertIn("reparations", legend)

    def test_reparations_texts_name_the_inspections_modifier(self):
        for key in ("nd_tt_yield_reparations", "nd_concession_long_6", "nd_tt_open_over_peacetime_strike"):
            self.assertIn("Custody Inspections", loc_value(key), key)

    def test_war_concession_texts_say_only_a_leader_drops_goals(self):
        for key in ("nd_tt_yield_war", "nd_tt_yield_guarantee", "nd_concession_long_2", "nd_concession_long_3",
                    "nd_tt_open_over_war", "nd_tt_open_over_guarantee", "nd_concession_past_they_2",
                    "nd_concession_past_they_3", "nd_concession_past_we_2", "nd_concession_past_we_3"):
            self.assertRegex(loc_value(key), r"\b(leads?|led)\b", key)

    def test_claim_texts_match_the_rules(self):
        self.assertNotIn("a year or two", loc_value("nuclear_weapon_events.1.k.tt"))
        self.assertNotIn("a year or two", loc_value("nd_w_disavow_tt"))
        for key in ("nd_tt_disavow_on", "nd_w_disavow_tt"):
            self.assertNotIn("each country we strike first", loc_value(key), key)
            self.assertIn("city", loc_value(key), key)



class TestSalvo(unittest.TestCase):
    """A salvo by mission (2026-10-28 rework spec §6): one loop of warheads,
    then the use's consequences once."""

    def setUp(self):
        self.effects = strip_comments(read(EFFECTS))
        self.triggers = strip_comments(read(TRIGGERS))
        self.order = block(self.effects, "nd_order_salvo")
        self.after = block(self.effects, "nd_salvo_aftermath")

    def test_salvo_fenced_by_a_click_marker(self):
        self.assertRegex(self.order, r"^\s*set_variable = nd_salvo_click\s*if = \{\s*limit = \{ has_variable = nd_salvo_click \}"
                                     r"\s*remove_variable = nd_salvo_click")
        self.assertIn("nd_can_order_salvo = { ENEMY = scope:nd_salvo_victim }", self.order)

    def test_order_gates(self):
        gates = block(self.triggers, "nd_can_order_salvo")
        for needle in ("nd_is_armed = yes", "nd_forces_assembled = yes", "nd_planner_candidate = { ENEMY = $ENEMY$ }",
                       "nd_doctrine_permits_strike = { ENEMY = $ENEMY$ }", "nd_pledge_permits_strike = { ENEMY = $ENEMY$ }",
                       "nd_war_law_permits_strategic_strike = yes", "nd_command_intact = yes"):
            self.assertIn(needle, gates)
        # The eighth: a Leadership salvo needs the capital in reach (phase 4a).
        self.assertEqual(gates.count("custom_tooltip"), 8)
        cand = squash(block(self.triggers, "nd_planner_candidate"))
        for needle in ("has_war_with = $ENEMY$", "nd_in_peacetime_exchange_with = { ENEMY = $ENEMY$ }",
                       "any_scope_state = { always = yes }"):
            self.assertIn(needle, cand)

    def test_loop_counts_the_size_value(self):
        # The count is fixed before the first warhead: each lowers the
        # stockpile nd_salvo_size_value caps by.
        self.assertIn("set_variable = { name = nd_salvo_count value = nd_salvo_size_value }", squash(self.order))
        self.assertRegex(squash(self.order), r"while = \{ count = nd_salvo_count_value nd_salvo_warhead = yes \}")
        self.assertIn("value = var:nd_salvo_count", block(strip_comments(read(VALUES)), "nd_salvo_count_value"))
        warhead = block(self.effects, "nd_salvo_warhead")
        self.assertIn("var:nuclear_weapon_stockpile > 0", warhead)
        self.assertIn("modifier = nuclear_strike_success_chance", warhead)
        self.assertIn("modifier = nuclear_strike_fail_chance", warhead)
        self.assertIn("action=strategic_miss", warhead)
        self.assertIn("action=strategic_hit", block(self.effects, "nd_salvo_hit"))

    def test_targets_by_mission(self):
        pick = squash(block(self.effects, "nd_salvo_pick_target"))
        for needle in ("capital = { nd_salvo_aim_here = yes }", "nd_state_has_military_target = yes",
                       "region ?= scope:nd_salvo_cap_region", "order_by = nuclear_strike_target_score", "position = 0",
                       "NOT = { has_variable = nd_salvo_target }"):
            self.assertIn(needle, pick)
        self.assertNotRegex(pick, r"position = [^0]")
        aim = squash(block(self.effects, "nd_salvo_aim_here"))
        self.assertIn("save_scope_as = target_state set_variable = nd_salvo_target", aim)

    def test_targets_fall_back_once_all_are_marked(self):
        # Last, once every state in reach is marked: the best state in reach
        # (rework spec §7; test_nuclear_reach.py).
        self.assertIn("ordered_scope_state = { limit = { nd_state_in_reach_of = { COUNTRY = scope:nd_salvo_attacker } }"
                      " order_by = nuclear_strike_target_score position = 0 nd_salvo_aim_here = yes } }",
                      squash(block(self.effects, "nd_salvo_pick_target")))

    def test_marks_cleared(self):
        clear = squash(block(self.effects, "nd_salvo_clear"))
        self.assertIn("every_scope_state = { limit = { has_variable = nd_salvo_target }"
                      " remove_variable = nd_salvo_target }", clear)

    def test_forces_damage_is_a_quarter_and_counted(self):
        damage = block(strip_comments(read(EXTRA_EFFECTS)), "nd_counterforce_strike_damage")
        for needle in ("percent = 0.025", "te_demog_note_kills", "value = nd_counterforce_strike_killed_population",
                       "add_devastation = 25", "name = nuclear_strike_aftermath", "nuclear_strike_attribute = yes"):
            self.assertIn(needle, damage)
        self.assertIn("multiply = 0.025", block(strip_comments(read(EXTRA_VALUES)), "nd_counterforce_strike_killed_population"))
        hit = block(self.effects, "nd_salvo_hit")
        self.assertIn("nd_counterforce_strike_damage = yes", hit)
        self.assertIn("nuclear_industrial_strike = yes", hit)
        self.assertIn("is_capital = yes", hit)

    def test_aftermath_order(self):
        # Ruling (phase 3 Task 2): our record and events come before a Launch
        # on Warning victim fires first, whose hits on us would make our salvo
        # read as an answer (nd_was_struck_by) and whose strike re-saves the
        # scopes the events read.
        order = ["nd_salvo_counterforce = yes", "nd_salvo_decapitation = yes", "nd_record_claim = yes",
                 "nd_salvo_record_use = yes", "id = nuclear_weapon_events.1 ", "id = nuclear_weapon_events.2 ",
                 "nd_record_nuclear_use = { VICTIM = scope:nd_salvo_victim }", "nd_salvo_fire_first = yes"]
        positions = [self.after.index(x) for x in order]
        self.assertEqual(positions, sorted(positions))
        positions = [self.order.index(x) for x in ("name = nd_salvo_victim_r", "while = {", "nd_salvo_aftermath = yes",
                                                   "nd_salvo_clear = yes")]
        self.assertEqual(positions, sorted(positions))
        self.assertLess(self.after.index("te_set_sqrt = { IN = var:nd_salvo_landed OUT = nd_salvo_sqrt }"),
                        self.after.index("nd_salvo_record_use = yes"))

    def test_aftermath_only_when_a_warhead_landed(self):
        landed = block(self.after, "if")
        self.assertIn("limit = { var:nd_salvo_landed > 0 }", landed)
        self.assertIn("nd_salvo_counterforce = yes", landed)
        miss = self.after[self.after.index(landed) + len(landed):]
        miss = block(miss, "else")
        for needle in ("change_infamy = 5", "id = nuclear_weapon_events.3 ", "id = nuclear_weapon_events.4 ",
                       "nd_record_nuclear_use = { VICTIM = scope:nd_salvo_victim }"):
            self.assertIn(needle, miss)
        for needle in ("nd_record_claim", "nd_salvo_record_use", "nd_salvo_counterforce", "nd_salvo_decapitation"):
            self.assertNotIn(needle, miss)

    def test_bookkeeping_scaled_once(self):
        use = squash(block(self.effects, "nd_salvo_record_use"))
        for needle in ("POINTS = nd_salvo_un_order_answer", "POINTS = nd_salvo_dossier_answer",
                       "AMOUNT = nd_salvo_un_shock", "POINTS = nd_salvo_un_order_first", "POINTS = nd_salvo_dossier_first",
                       "change_infamy = nd_salvo_infamy", "value = scope:nd_salvo_attacker.var:nd_salvo_world_rel",
                       "nd_taboo_note_use_scaled = { KIND = strategic RETALIATION = yes SCALE = var:nd_salvo_sqrt }",
                       "nd_taboo_note_use_scaled = { KIND = strategic RETALIATION = no SCALE = var:nd_salvo_sqrt }",
                       "un_docket_note_grievance", "un_regime_icc_note_crime = { CRIME = 1 }"):
            self.assertIn(needle, use)
        self.assertIn("nd_taboo_note_use_scaled = { KIND = $KIND$ RETALIATION = $RETALIATION$ SCALE = 1 }",
                      squash(block(strip_comments(read(TABOO_EFFECTS)), "nd_taboo_note_use")))
        self.assertEqual(block(strip_comments(read(TABOO_EFFECTS)), "nd_taboo_note_use_scaled").count("multiply = $SCALE$"), 2)

    def test_counterforce_rounds_stochastically_within_the_stockpile(self):
        cf = squash(block(self.effects, "nd_salvo_counterforce"))
        for needle in ("save_scope_as = nd_sv_enemy", "value = nd_counterforce_destroyed_raw", "floor = yes",
                       "chance = nd_cf_round_up_chance", "name = nuclear_weapon_stockpile subtract = var:nd_cf_whole",
                       "nd_authority_launch_on_warning = yes", "value = nd_counterforce_saved_raw", "max = 3",
                       "type=counterforce", "set_variable = { name = nd_salvo_destroyed value = scope:nd_salvo_victim.var:nd_cf_whole }"):
            self.assertIn(needle, cf)
        self.assertRegex(cf, r"var:nd_cf_whole > var:nuclear_weapon_stockpile \} set_variable = \{ name = nd_cf_whole"
                             r" value = var:nuclear_weapon_stockpile \}")

    def test_low_fires_first_with_its_gate_and_record(self):
        fire = squash(block(self.effects, "nd_salvo_fire_first"))
        for needle in ("nd_retaliation_permitted = { ENEMY = scope:nd_salvo_attacker }", "nuclear_response_strike = yes",
                       "position = 1", "position = 2", "nd_record_nuclear_use = { VICTIM = scope:nd_salvo_attacker }",
                       "type=fire_first", "remove_variable = nd_cf_fire_first"):
            self.assertIn(needle, fire)

    def test_decapitation_only_central(self):
        self.assertIn("nd_authority_central = yes", block(self.after, "if"))
        dec = squash(block(self.effects, "nd_salvo_decapitation"))
        for needle in ("chance = nd_decapitation_chance_value", "days = 13", "days = 20", "days = 27",
                       "name = nd_pending_retaliation", "name = nd_restored_from_decapitation", "type=decapitation"):
            self.assertIn(needle, dec)

    def test_claim_reads_the_landed_count(self):
        claim = block(self.effects, "nd_record_claim")
        self.assertIn("value = scope:attacking_country.nd_strike_landed_count_value", claim)
        lie = claim[claim.index("is_ai = yes"):claim.index("chance = nd_ai_lies_value")]
        self.assertIn("nd_strike_landed_count_value <= 1", lie)

    def test_salvo_working_variables_cleared(self):
        clear = block(self.effects, "nd_salvo_clear")
        for name in ("nd_salvo_landed", "nd_salvo_forces_landed", "nd_salvo_capital_landed", "nd_salvo_fired",
                     "nd_salvo_victim_r", "nd_salvo_sqrt", "nd_salvo_world_rel", "nd_salvo_destroyed",
                     "nd_salvo_count"):
            self.assertIn(f"remove_variable = {name}", clear, name)
        # The panel's settings stay for the next salvo.
        for name in ("nd_salvo_mission", "nd_salvo_size"):
            self.assertNotIn(f"remove_variable = {name}", clear, name)
        # Every working variable the salvo sets on us is one nd_salvo_clear removes.
        body = strip_comments(read(EFFECTS))
        start = body.index("nd_order_salvo = {")
        section = body[start:body.index("nd_salvo_clear = {")]
        for name in set(re.findall(r"set_variable = \{ name = (nd_salvo_[a-z_]+)", section)):
            if name.startswith("nd_salvo_seen_") or name in ("nd_salvo_mission", "nd_salvo_marked"):
                continue
            self.assertIn(f"remove_variable = {name}", clear, name)

    def test_victim_summary_before_its_event(self):
        summary = squash(self.after)
        for name in ("nd_salvo_seen_by", "nd_salvo_seen_landed", "nd_salvo_seen_destroyed", "nd_salvo_seen_mission"):
            self.assertRegex(summary, rf"set_variable = \{{ name = {name} value = [^}}]+ days = 30 \}}")
            self.assertLess(self.after.index(name), self.after.index("id = nuclear_weapon_events.1 "))

    def test_salvo_targets_self_check(self):
        raw = block(self.effects, "nd_salvo_targets_self_check")
        # Final review: two checks, each once a game. The count, gated on the
        # count ordered (not the warheads fired, so a short loop reports
        # BROKEN), for any mission, so the AI's salvos reach it; the spread,
        # for Cities, with its own flag, so an earlier Forces or Leadership
        # salvo doesn't use it up.
        count = raw[:raw.index("nd_salvo_targets_self_check_done")]
        spread = raw[raw.index("nd_salvo_targets_self_check_done"):]
        for line in ("TE_SELF_CHECK OK nd_salvo_count", "TE_SELF_CHECK BROKEN nd_salvo_count"):
            self.assertIn(line, count)
        for line in ("TE_SELF_CHECK OK nd_salvo_targets", "TE_SELF_CHECK BROKEN nd_salvo_targets"):
            self.assertIn(line, spread)
        gate = squash(block(count, "limit"))
        for needle in ("has_global_variable = nd_salvo_count_self_check_done", "var:nd_salvo_count >= 2"):
            self.assertIn(needle, gate)
        self.assertNotIn("nd_salvo_fired", gate)
        self.assertNotIn("nd_salvo_mission", gate)
        self.assertIn("var:nd_salvo_fired = var:nd_salvo_count", squash(count))
        gate = squash(raw[raw.rindex("limit", 0, raw.index("nd_salvo_targets_self_check_done")):])
        for needle in ("var:nd_salvo_mission = 1", "var:nd_salvo_fired >= 2", "count >= 2"):
            self.assertIn(needle, gate[:gate.index("set_global_variable")])
        self.assertIn("var:nd_salvo_marked >= 2", squash(spread))
        self.assertLess(self.after.index("nd_salvo_targets_self_check = yes"), len(self.after))
        self.assertLess(self.order.index("nd_salvo_aftermath = yes"), self.order.index("nd_salvo_clear = yes"))

    def test_world_hears_of_a_salvo(self):
        # Final review: every third country's .15 says a salvo, not a strike.
        desc = squash(block(block(self.weapon_events(), "nuclear_weapon_events.15"), "desc"))
        self.assertIn("scope:target_country ?= { var:nd_salvo_seen_by ?= scope:attacking_country }", desc)
        self.assertLess(desc.index("desc = nuclear_weapon_events.15.d_salvo }"),
                        desc.index("desc = nuclear_weapon_events.15.d }"))
        self.assertTrue(loc_value("nuclear_weapon_events.15.d_salvo"))

    def weapon_events(self):
        return strip_comments(read(WEAPON_EVENTS))

    def test_fire_first_share_from_the_arsenal_before_destruction(self):
        # Final review: the saved share is min(exposed, K x landed) x credit
        # of the arsenal the salvo met, as the destroyed share is.
        cf = squash(block(self.effects, "nd_salvo_counterforce"))
        self.assertLess(cf.index("value = nd_counterforce_saved_raw"),
                        cf.index("name = nuclear_weapon_stockpile subtract = var:nd_cf_whole"))

    def test_only_an_armed_victim_is_disarmed_or_cut_off(self):
        # Final review: nd_authority_central holds for a country that never
        # set an authority, so the aftermath asks for an arsenal too.
        after = squash(self.after)
        self.assertIn("var:nd_salvo_forces_landed > 0 scope:nd_salvo_victim = { nd_is_armed = yes }", after)
        self.assertIn("scope:nd_salvo_victim = { nd_authority_central = yes nd_is_armed = yes }", after)

    def test_texts_name_a_state_a_warhead_hit(self):
        # Final review: the events, notifications and UN subjects read
        # scope:target_state, which the loop leaves on the last state aimed
        # at; it is put back on one a warhead hit, the capital first.
        hit = squash(block(self.effects, "nd_salvo_hit"))
        self.assertIn("scope:target_state = { save_scope_as = nd_salvo_hit_state }", hit)
        self.assertIn("is_capital = yes } } change_variable = { name = nd_salvo_capital_landed add = 1 }"
                      " scope:target_state = { save_scope_as = nd_salvo_hit_capital }", hit)
        restore = self.after.index("save_scope_as = target_state")
        self.assertLess(self.after.index("scope:nd_salvo_hit_capital"), restore)
        self.assertLess(restore, self.after.index("nd_salvo_record_use = yes"))

    def test_each_salvo_effect_defined_once(self):
        for name in ("nd_order_salvo", "nd_salvo_warhead", "nd_salvo_pick_target", "nd_salvo_hit", "nd_salvo_aftermath",
                     "nd_salvo_record_use", "nd_salvo_counterforce", "nd_salvo_fire_first", "nd_salvo_decapitation",
                     "nd_salvo_clear", "nd_salvo_targets_self_check"):
            self.assertEqual(len(re.findall(rf"(?m)^{name} = \{{", read(EFFECTS))), 1, name)



class TestDecapitationGates(unittest.TestCase):
    """A decapitated command orders nothing until it is restored (rework spec
    §6.3, §6.4; plan H11-H13)."""

    def setUp(self):
        self.triggers = strip_comments(read(TRIGGERS))
        self.effects = strip_comments(read(EFFECTS))
        self.weapon = strip_comments(read(WEAPON_EVENTS))

    def test_command_gates_every_ordered_launch(self):
        self.assertIn("nd_command_intact = yes", block(self.triggers, "nd_retaliation_permitted"))
        self.assertIn("nd_command_intact = yes", block(self.triggers, "nd_can_order_salvo"))
        nuke = strip_comments(read(NUKE))
        for action in ("nuke_diplo_action", "tactical_nuke_diplo_action"):
            self.assertIn("nd_command_intact = yes", block(block(nuke, action), "possible"), action)
        for name in ("nd_dispatch_strategic_strike", "nd_dispatch_tactical_strike"):
            body = block(self.effects, name)
            gate = block(body[body.index("remove_variable = nd_dispatch_click"):], "limit")
            self.assertIn("nd_command_intact = yes", gate, name)
        crisis = strip_comments(read(CRISIS_EVENTS))
        for option in ORDERED_LAUNCH_CRISIS_OPTIONS:
            self.assertIn("nd_command_intact = yes", block(option_body(crisis, option), "trigger"), option)
        guarantor = block(crisis, "nuclear_crisis.22")
        self.assertIn("nd_command_intact = yes", guarantor)
        incident = strip_comments(read(INCIDENT_EVENTS))
        for option in ORDERED_LAUNCH_INCIDENT_OPTIONS:
            self.assertIn("nd_command_intact", block(option_body(incident, option), "trigger"), option)
        # The answer that waited is asked only once the command is restored.
        weekly = self.effects[self.effects.index("limit = { has_variable = nd_pending_retaliation }"):]
        weekly = weekly[:weekly.index("nuclear_weapon_events.24")]
        self.assertIn("nd_command_intact = yes", weekly)

    def test_cut_off_command_keeps_its_authority(self):
        # Final review: a change of authority while cut off would leave the
        # new authority's unordered launches narrated but refused by the
        # dispatchers' gate.
        self.assertIn("nd_command_intact = yes", block(self.triggers, "nd_can_set_authority"))
        self.assertIn("limit = { var:nd_authority_months >= nd_authority_tenure_months nd_command_intact = yes }",
                      squash(self.effects))

    def test_unordered_paths_untouched(self):
        # Only a Central Authorization country is ever cut off, and none of
        # these launch under it: a cut-off command, Automatic Retaliation, a
        # loose warhead and the incident dispatch itself.
        self.assertNotIn("nd_command_intact", block(self.effects, "nd_launch_or_intercept"))
        self.assertNotIn("nd_command_intact", strip_comments(read(LOOSE_EFFECTS)))
        self.assertNotIn("nd_command_intact", strip_comments(read(LOOSE_EVENTS)))
        self.assertNotIn("nd_command_intact", option_body(self.weapon, "nuclear_weapon_events.1.e"))
        incident = strip_comments(read(INCIDENT_EVENTS))
        commander = incident[incident.index("KIND = commander") - 3000:incident.index("KIND = commander")]
        self.assertNotIn("nd_command_intact", commander)

    def test_cut_off_option(self):
        one = block(self.weapon, "nuclear_weapon_events.1")
        option = option_body(one, "nuclear_weapon_events.1.cut_off")
        self.assertIn("has_variable = nd_decapitated", block(option, "trigger"))
        self.assertIn("default_option = yes", option)
        raw = read(WEAPON_EVENTS)
        raw_option = raw[raw.index("name = nuclear_weapon_events.1.cut_off"):]
        self.assertRegex(raw_option[:600], r"# REVIEWED \d{4}-\d{2}-\d{2} \(no_effect_option\):")
        # Absorbing and the Recessed mating are hidden while it is the default.
        for name in ("nuclear_weapon_events.1.a", "nuclear_weapon_events.1.g"):
            self.assertIn("NOT = { scope:target_country = { has_variable = nd_decapitated } }",
                          squash(block(option_body(one, name), "trigger")), name)
        for key in ("nuclear_weapon_events.1.cut_off", "nuclear_weapon_events.1.cut_off.tt"):
            self.assertTrue(loc_value(key), key)
        self.assertIn("custom_tooltip = nuclear_weapon_events.1.cut_off.tt", option)

    def test_command_restored_reuses_24(self):
        event = block(self.weapon, "nuclear_weapon_events.24")
        for part, key in (("title", "nuclear_weapon_events.24.t_restored"), ("desc", "nuclear_weapon_events.24.d_restored")):
            body = squash(block(event, part))
            self.assertIn(f"triggered_desc = {{ trigger = {{ has_variable = nd_restored_from_decapitation }} desc = {key} }}",
                          body, part)
            self.assertTrue(loc_value(key), key)
        self.assertIn("remove_variable = nd_restored_from_decapitation", block(event, "after"))

    def test_salvo_claim_keeps_the_salvo_text(self):
        # Final review: a claim on a salvo reads the salvo's text with the
        # hotline sentence, not the single strike's.
        desc = squash(block(block(self.weapon, "nuclear_weapon_events.1"), "desc"))
        for key in ("nuclear_weapon_events.1.d_cut_off_claim", "nuclear_weapon_events.1.d_salvo_forces_claim",
                    "nuclear_weapon_events.1.d_salvo_leadership_claim", "nuclear_weapon_events.1.d_salvo_cities_claim"):
            self.assertLess(desc.index(f"desc = {key} }}"), desc.index("desc = nuclear_weapon_events.1.d_claim }"), key)
            self.assertIn("$nuclear_weapon_events.1.claim_word$", loc_value(key), key)
        self.assertLess(desc.index("desc = nuclear_weapon_events.1.d_salvo_cities }"),
                        desc.index("desc = nuclear_weapon_events.1.d_claim }"))
        self.assertIn("$nuclear_weapon_events.1.claim_word$", loc_value("nuclear_weapon_events.1.d_claim"))

    def test_claim_accepted_while_cut_off_drops_the_answer(self):
        # Final review: accepting the claim holds our answer back, so the
        # answer a decapitation kept for Command Restored goes with it.
        option = squash(option_body(block(self.weapon, "nuclear_weapon_events.1"), "nuclear_weapon_events.1.k"))
        self.assertIn("var:nd_pending_retaliation = scope:attacking_country } remove_variable = nd_pending_retaliation", option)
        self.assertNotIn("hold them back", loc_value("nuclear_weapon_events.1.cut_off.tt"))

    def test_attacker_learns_the_leadership_result(self):
        two = squash(block(block(self.weapon, "nuclear_weapon_events.2"), "desc"))
        cut = two.index("desc = nuclear_weapon_events.2.d_salvo_cut_off }")
        self.assertIn("has_variable = nd_decapitated", two[two.rindex("trigger", 0, cut):cut])
        held = two.index("desc = nuclear_weapon_events.2.d_salvo_leadership }")
        self.assertIn("var:nd_salvo_seen_mission ?= 3", two[two.rindex("trigger", 0, held):held])
        self.assertLess(cut, held)
        self.assertLess(held, two.index("desc = nuclear_weapon_events.2.d_salvo }"))
        for key in ("nuclear_weapon_events.2.d_salvo_cut_off", "nuclear_weapon_events.2.d_salvo_leadership"):
            self.assertTrue(loc_value(key), key)

    def test_launch_order_shows_the_cost(self):
        # Final review: the single strike's confirmation names what it costs;
        # the salvo's does too, with the square root.
        launch = squash(option_body(block(self.weapon, "nuclear_weapon_events.31"), "nuclear_weapon_events.31.a"))
        self.assertIn("nd_was_struck_by = { ENEMY = scope:nd_salvo_victim } } custom_tooltip = nd_taboo_tt_strike_answer", launch)
        self.assertIn("custom_tooltip = nd_taboo_tt_strike_first_use", launch)
        self.assertLess(launch.index("nd_taboo_tt_strike_first_use"), launch.index("nd_order_salvo = yes"))
        self.assertIn("square root", loc_value("nuclear_weapon_events.31.a.tt"))

    def test_salvo_text_and_stale_guard(self):
        one = block(self.weapon, "nuclear_weapon_events.1")
        desc = squash(block(one, "desc"))
        for key in ("nuclear_weapon_events.1.d_salvo_cities", "nuclear_weapon_events.1.d_salvo_forces",
                    "nuclear_weapon_events.1.d_salvo_leadership", "nuclear_weapon_events.1.d_cut_off"):
            self.assertIn(f"desc = {key} }}", desc, key)
            self.assertTrue(loc_value(key), key)
            self.assertLess(desc.index(key), desc.index("desc = nuclear_weapon_events.1.d }"))
        self.assertIn("var:nd_salvo_seen_by ?= scope:attacking_country", desc)
        self.assertIn("nd_salvo_seen_landed", loc_value("nuclear_weapon_events.1.d_salvo_cities"))
        self.assertIn("nd_salvo_seen_destroyed", loc_value("nuclear_weapon_events.1.d_salvo_forces"))
        title = squash(block(one, "title"))
        self.assertIn("desc = nuclear_weapon_events.1.t_salvo }", title)
        self.assertTrue(loc_value("nuclear_weapon_events.1.t_salvo"))
        # A single strike after a salvo must not read as the salvo.
        extra = strip_comments(read(EXTRA_EFFECTS))
        for name in ("nuclear_first_strike", "nuclear_response_response_strike"):
            body = block(extra, name)
            self.assertIn("remove_variable = nd_salvo_seen_by", body, name)
            self.assertLess(body.index("remove_variable = nd_salvo_seen_by"),
                            body.index("id = nuclear_weapon_events.1 "), name)



def strike_section():
    """The Strike section's GUI type body (a type opens `type x = flowcontainer {`)."""
    text = read(GUI)
    return block(text.replace("type te_nuclear_sec_strike = flowcontainer {", "te_nuclear_sec_strike = {"),
                 "te_nuclear_sec_strike")


class TestStrikeSection(unittest.TestCase):
    """The Strike section and the Launch Order (rework spec §6.1, §10; plan
    H1-H3, H15)."""

    OPS = set(range(72, 80))
    EFFECTS_BY_OP = ("nd_plan_step_enemy", "nd_plan_set_mission", "nd_plan_step_size", "nd_plan_order")

    def setUp(self):
        self.effects = strip_comments(read(EFFECTS))
        self.sguis = strip_comments(read(SGUIS))

    def test_ops_in_step(self):
        self.assertLessEqual(self.OPS, gui_ops(read(GUI), "nd_posture_sgui"))
        for part in ("is_valid", "effect"):
            self.assertLessEqual(self.OPS, sgui_ops(self.sguis, "nd_posture_sgui", part), part)
        doc = JE_DOC.read_text(encoding="utf-8")
        for text in (read(GUI), read(SGUIS), doc):
            for needle in ("72 / 73", "74..76", "77 / 78", "79"):
                self.assertIn(needle, text.replace("74–76", "74..76"), needle)

    def test_op_bodies_fenced(self):
        for name in self.EFFECTS_BY_OP:
            body = squash(block(self.effects, name))
            self.assertIn("set_variable = nd_plan_click if = { limit = { has_variable = nd_plan_click }"
                          " remove_variable = nd_plan_click", body, name)
            self.assertIn("custom_tooltip", body[:body.index("set_variable = nd_plan_click")], name)

    def test_refresh_picks_by_index_and_wraps(self):
        refresh = squash(block(self.effects, "nd_plan_refresh"))
        self.assertEqual(refresh.count("every_country = {"), 2)
        self.assertEqual(refresh.count("nd_planner_candidate = { ENEMY = scope:nd_plan_cand }"), 2)
        for needle in ("name = nd_plan_count", "var:nd_plan_index > var:nd_plan_count",
                       "var:nd_plan_index < 1", "set_variable = { name = nd_plan_index value = 1 }",
                       "set_variable = { name = nd_plan_index value = var:nd_plan_count }",
                       "var:nd_plan_seen = var:nd_plan_index", "name = nd_plan_enemy value = scope:nd_plan_pick",
                       "remove_variable = nd_plan_enemy"):
            self.assertIn(needle, refresh, needle)
        weekly = squash(block(self.effects, "nd_weekly_update"))
        self.assertIn("is_ai = no nd_is_armed = yes } nd_plan_refresh = yes", weekly)
        step = squash(block(self.effects, "nd_plan_step_enemy"))
        self.assertIn("change_variable = { name = nd_plan_index $OP$ = 1 } nd_plan_refresh = yes", step)

    def test_section_shown_cheaply(self):
        shown = block(self.sguis, "nd_plan_shown_sgui")
        self.assertIn("has_variable = nd_plan_enemy", block(shown, "is_shown"))
        for loop in ("any_country", "every_country", "ordered_country"):
            self.assertNotIn(loop, shown, loop)
        section = strike_section()
        self.assertIn("GetScriptedGui('nd_plan_shown_sgui').IsShown(", section)

    def test_target_named_through_a_display_sgui(self):
        name = block(self.sguis, "nd_plan_enemy_sgui")
        self.assertIn("var:nd_plan_enemy = { save_temporary_scope_as = nd_plan_enemy_disp }", squash(name))
        self.assertIn("SCOPE.sCountry('nd_plan_enemy_disp')", loc_value("nd_w_strike_target_name"))
        self.assertNotIn("Var('nd_plan_enemy').GetCountry", read(GUI))
        self.assertIn("GetScriptedGui('nd_plan_enemy_sgui').ExecuteTooltip(", strike_section())

    def test_mission_and_size(self):
        mission = squash(block(self.effects, "nd_plan_set_mission"))
        self.assertIn("set_variable = { name = nd_salvo_mission value = $M$ }", mission)
        size = squash(block(self.effects, "nd_plan_step_size"))
        for needle in ("set_variable = { name = nd_salvo_size value = nd_salvo_size_value }",
                       "change_variable = { name = nd_salvo_size $OP$ = 1 }",
                       "set_variable = { name = nd_salvo_size value = nd_salvo_size_value }"):
            self.assertIn(needle, size)
        self.assertEqual(size.count("value = nd_salvo_size_value"), 2)
        values = strip_comments(read(VALUES))
        self.assertIn("value = var:nd_salvo_mission", block(values, "nd_display_plan_mission"))
        section = strike_section()
        for n in (1, 2, 3):
            self.assertIn(f"ScriptValue('nd_display_plan_mission'), '(CFixedPoint){n}' )", section)

    def test_confirmation_rechecks_the_order(self):
        events = strip_comments(read(WEAPON_EVENTS))
        event = block(events, "nuclear_weapon_events.31")
        launch = option_body(event, "nuclear_weapon_events.31.a")
        self.assertIn("nd_can_order_salvo = { ENEMY = scope:nd_salvo_victim }", block(launch, "trigger"))
        self.assertIn("nd_order_salvo = yes", launch)
        stand = option_body(event, "nuclear_weapon_events.31.b")
        self.assertIn("default_option = yes", stand)
        self.assertNotIn("default_option", launch)
        order = squash(block(self.effects, "nd_plan_order"))
        self.assertIn("var:nd_plan_enemy = { save_scope_as = nd_salvo_victim }", order)
        self.assertIn("trigger_event = { id = nuclear_weapon_events.31 popup = yes }", order)
        valid = squash(block(self.triggers_text(), "nd_plan_can_order"))
        self.assertIn("var:nd_plan_enemy ?= { save_temporary_scope_as = nd_plan_victim }", valid)
        self.assertIn("nd_can_order_salvo = { ENEMY = scope:nd_plan_victim }", valid)
        for key in ("nuclear_weapon_events.31.t", "nuclear_weapon_events.31.a", "nuclear_weapon_events.31.b",
                    "nuclear_weapon_events.31.a.tt", "nuclear_weapon_events.31.f"):
            self.assertTrue(loc_value(key), key)

    def triggers_text(self):
        return strip_comments(read(TRIGGERS))


class TestOutcomeNotice(unittest.TestCase):
    def setUp(self):
        self.effects = strip_comments(read(CRISIS_EFFECTS))
        self.events = strip_comments(read(CRISIS_EVENTS))

    def test_close_no_longer_applies_consequences(self):
        self.assertNotRegex(self.effects, r"(?m)^nd_crisis_apply_outcome = \{")
        self.assertNotIn("nd_crisis_apply_outcome = yes", block(self.effects, "nd_crisis_close"))

    def test_close_flushes_before_recording(self):
        body = block(self.effects, "nd_crisis_close")
        flush = body.index("nd_crisis_flush_pending = yes")
        record = body.index("nd_crisis_record_pending = yes")
        self.assertLess(flush, record)
        self.assertEqual(body.count("nd_crisis_flush_pending = yes"), 2)

    def test_outcome_nine_records_nothing(self):
        body = block(self.effects, "nd_crisis_close")
        self.assertRegex(body, r"NOT = \{ var:nd_crisis_outcome_now = 9 \}(\s*\})+\s*nd_crisis_record_pending = yes")

    def test_outcome_option_guards_pending(self):
        body = option_body(self.events, "nuclear_crisis.6.a")
        self.assertIn("has_variable = nd_crisis_pending_outcome", body)
        self.assertIn("var:nd_crisis_pending_opponent ?= scope:nd_outcome_other", body)
        self.assertIn("nd_crisis_apply_outcome_side = yes", body)
        self.assertIn("custom_tooltip = nd_tt_outcome_already_settled", body)

    def test_every_credibility_change_says_its_number(self):
        body = block(self.effects, "nd_crisis_apply_outcome_side") + block(self.effects, "nd_crisis_bluff_called")
        pairs = re.findall(r"text = nd_tt_credibility_(up|down)_(\d+)(?:_bluff)?\s*nd_change_credibility = \{ AMOUNT = (-?\d+) \}", body)
        self.assertTrue(pairs)
        for direction, n, amount in pairs:
            self.assertEqual(int(amount), int(n) if direction == "up" else -int(n))
        self.assertEqual(body.count("nd_change_credibility"), len(pairs), "a credibility change without its number line")


def revalidate_branch(effects, dispute):
    """The else_if of nd_crisis_revalidate_dispute that tests var:nd_crisis_dispute = N."""
    body = block(effects, "nd_crisis_revalidate_dispute")
    for m in re.finditer(r"else_if = \{", body):
        branch = block(body[m.start():], "else_if")
        if re.search(r"var:nd_crisis_dispute = " + str(dispute) + r"\b", block(branch, "limit")):
            return branch
    raise AssertionError(f"no revalidation branch for dispute {dispute}")


class TestNativeCloses(unittest.TestCase):
    """A native close (outcome 4) must observe a state the target can't undo at
    will. Funding stepped to 0 ended a proliferation crisis as the issuer's win
    with no freeze, and the target funded its programme again at once (UNL,
    2026-10-05)."""

    def setUp(self):
        self.effects = strip_comments(read(CRISIS_EFFECTS))

    def test_programme_dispute_closes_only_when_stopped_for_good(self):
        branch = revalidate_branch(self.effects, 4)
        self.assertIn("nuclear_program_has_stopped = yes", branch)
        self.assertNotIn("nuclear_program_is_proliferating", branch)
        self.assertNotIn("nuclear_program_is_standing", branch)

    def test_stopped_reads_neither_funding_nor_our_own_ceiling(self):
        body = strip_comments(block(read(NUKE_TRIGGERS), "nuclear_program_has_stopped"))
        self.assertNotIn("funding", body)
        self.assertNotIn("nuclear_program_is_proliferating", body)
        self.assertIn("nd_taboo_held_by_own_ceiling_only = no", body)

    def test_own_ceiling_test_rules_out_every_other_hold(self):
        body = strip_comments(block(read(TABOO_TRIGGERS), "nd_taboo_held_by_own_ceiling_only"))
        for other_hold in ("nd_taboo_is_dismantling = no", "nd_treaty_ceiling", "nd_tpnw_ceiling",
                           "nd_crisis_programme_freeze", "has_type = nuclear_program_pause"):
            self.assertIn(other_hold, body)

    def test_alert_dispute_ignores_the_targets_own_readiness(self):
        branch = revalidate_branch(self.effects, 5)
        self.assertIn("nd_is_armed = no", branch)
        self.assertNotRegex(branch, r"var:nd_readiness_target\s*[<>=]")


PREVIEW_PINS = {
    # loc key: (script value holding the constant, operation, number)
    "nd_tt_open_f_unarmed": ("nd_yp_answer_value", "add", 20),
    # Armed, the answer is −25 × survivors ÷ 3 (rework spec §3.3): the preview
    # names its ceiling; "armed but disarmable" carries no constant.
    "nd_tt_open_f_survivable": ("nd_yp_answer_value", "multiply", -25),
    "nd_tt_open_f_protector": ("nd_yp_protector_value", "subtract", 20),
    "nd_tt_open_f_aggressive": ("nd_yp_temperament_value", "subtract", 15),
    "nd_tt_open_f_cautious": ("nd_yp_temperament_value", "add", 10),
    "nd_tt_open_f_losing": ("nd_yp_war_value", "add", 15),
    "nd_tt_open_f_existence": ("nd_yp_war_value", "subtract", 15),
    "nd_tt_open_f_alert": ("nd_yp_alert_value", "add", 10),
    "nd_tt_open_backed": ("nd_yp_follow_through_value", "add", 10),
    "nd_tt_open_bluff_existential": ("nd_yp_follow_through_value", "subtract", 25),
    "nd_tt_open_bluff_flexible": ("nd_yp_follow_through_value", "subtract", 25),
    "nd_tt_open_bluff_law": ("nd_yp_follow_through_value", "subtract", 25),
    "nd_tt_open_bluff_nfu": ("nd_yp_follow_through_value", "subtract", 35),
    "nd_tt_open_bluff_reach": ("nd_yp_follow_through_value", "subtract", 25),
}


def loc_value(key):
    for path in LOC_DIR.glob("*.yml"):
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            m = re.match(r"\s+" + re.escape(key) + r":\d*\s+\"(.*)\"\s*$", line)
            if m:
                return m.group(1)
    raise AssertionError(f"loc key {key} not found")


class TestActionPreview(unittest.TestCase):
    def setUp(self):
        self.effects = strip_comments(read(CRISIS_EFFECTS))
        self.values = strip_comments(read(VALUES))

    def test_open_uses_the_preview(self):
        body = block(self.effects, "nd_crisis_open")
        self.assertIn("nd_crisis_preview = { TARGET = $TARGET$ PUBLIC = $PUBLIC$ }", body)
        self.assertNotIn("nd_tt_crisis_opens_", body)
        self.assertNotIn("change_infamy", body)
        self.assertNotIn("change_relations", body)

    def test_preview_reads_no_crisis_scopes(self):
        body = block(self.effects, "nd_crisis_preview")
        self.assertNotRegex(body, r"scope:nd_(?!pv_self\b)")
        self.assertNotRegex(body, r"(?<!temporary_)save_scope_as")
        self.assertNotRegex(body, r"= PREV\b", "PREV passed as a parameter")

    def test_preview_numbers_match_the_formula(self):
        preview = block(self.effects, "nd_crisis_preview")
        for key, (value, op, n) in PREVIEW_PINS.items():
            self.assertIn(key, preview, key)
            self.assertRegex(block(self.values, value), rf"{op} = {n}\b", f"{value} lost {op} {n}")
            self.assertIn(str(n), loc_value(key), key)

    def test_preview_stakes_and_deadlines(self):
        self.assertRegex(self.values, r"nd_crisis_deadline_public_weeks = 8\b")
        self.assertRegex(self.values, r"nd_crisis_deadline_private_weeks = 10\b")
        self.assertRegex(self.values, r"nd_crisis_pressure_interval_weeks = 6\b")
        self.assertIn("8", loc_value("nd_tt_open_next_public"))
        self.assertIn("10", loc_value("nd_tt_open_next_private"))
        for key in ("nd_tt_open_next_public", "nd_tt_open_next_private"):
            self.assertIn("6", loc_value(key))
        for n in ("15", "10"):
            self.assertIn(n, loc_value("nd_tt_open_stakes_public"))
        for n in ("10", "5"):
            self.assertIn(n, loc_value("nd_tt_open_stakes_private"))


READINESS_FACTOR_WORDS = {"recessed": "half", "routine": "four fifths", "heightened": "nine tenths"}


class TestEffectiveSurvivability(unittest.TestCase):
    """A crisis weighs survivability at the target's readiness
    (nd_effective_survivability); the AI's launch authority plans around the
    stored figure, so standing down cannot push it towards Launch on Warning."""

    def setUp(self):
        self.values = strip_comments(read(VALUES))
        self.factors = {name: float(n) for name, n in re.findall(
            r"^nd_survivability_factor_(\w+) = ([\d.]+)", self.values, re.M)}

    def test_factors_rise_with_readiness(self):
        self.assertEqual(set(self.factors), set(READINESS_FACTOR_WORDS))
        self.assertLess(self.factors["recessed"], self.factors["routine"])
        self.assertLess(self.factors["routine"], self.factors["heightened"])
        self.assertLess(self.factors["heightened"], 1)

    def test_values_at_each_readiness_use_the_same_factors(self):
        for readiness, factor in enumerate(("recessed", "routine", "heightened")):
            body = block(self.values, f"nd_effective_survivability_at_readiness_{readiness}")
            self.assertIn(f"multiply = nd_survivability_factor_{factor}", body)
            self.assertIn(f"multiply = nd_survivability_factor_{factor}",
                          block(self.values, "nd_effective_survivability"))
        self.assertNotIn("multiply", block(self.values, "nd_effective_survivability_at_readiness_3"))

    def test_answer_sites_read_survivors_not_a_line(self):
        # The line of 50 is gone (rework spec §3.3): every site that weighs
        # the target's answer reads survivors.
        sites = (block(self.values, "nd_yp_answer_value"),
                 block(strip_comments(read(CRISIS_EFFECTS)), "nd_crisis_preview"))
        for body in sites:
            self.assertNotIn("nd_effective_survivability >= 50", body)
            self.assertNotIn("var:nd_survivability", body)

    def test_ai_alert_reads_survivors_at_heightened(self):
        # Not at the current readiness: reaching High Alert must not undo the
        # reason for it, or the review would swing between the two.
        review = strip_comments(block(read(EFFECTS), "nd_ai_review_posture"))
        self.assertIn("var:nd_survivors_main_r2 < 3", review)
        self.assertNotRegex(review, r"\bnd_effective_survivability(?:_at_readiness_\d)?\s*<")

    def test_tooltips_show_the_figure(self):
        # The readiness table's Survivability column (NUC-5), one cell a level.
        for readiness in range(4):
            self.assertIn(f"ScriptValue('nd_effective_survivability_at_readiness_{readiness}')",
                          loc_value(f"nd_w_readiness_survivability_{readiness}"))
        survivability_tt = loc_value("nd_w_survivability_tt")
        self.assertIn("ScriptValue('nd_effective_survivability')", survivability_tt)
        self.assertIn("50", survivability_tt)
        for factor, words in READINESS_FACTOR_WORDS.items():
            self.assertEqual(self.factors[factor], {"half": 0.5, "four fifths": 0.8, "nine tenths": 0.9}[words])
            self.assertIn(words, survivability_tt)


class TestSurvivorsAgainstRival(unittest.TestCase):
    """Survivability tops out at 80; survivors are measured against the main
    rival (2026-10-28 rework spec §3.1, §3.2)."""

    def test_survivability_cap_is_80(self):
        body = block(strip_comments(read(VALUES)), "nd_survivability_cap")
        self.assertIn("max = 80", body)
        self.assertNotIn("max = 95", body)

    def test_main_rival_cleared_without_attacker(self):
        body = block(strip_comments(read(EFFECTS)), "nd_refresh_main_rival")
        for name in ("nd_main_rival", "nd_survivors_main", "nd_survivors_main_r2", "nd_survivors_main_bare_r2",
                     "nd_survivors_main_ceiling_bare_r2"):
            self.assertIn(f"remove_variable = {name}", body)
            self.assertIn(f"name = {name} value", body)

    def test_main_rival_refreshed_monthly_and_before_the_ai_review(self):
        effects = strip_comments(read(EFFECTS))
        self.assertIn("nd_refresh_main_rival = yes", block(effects, "nd_monthly_update"))
        review = block(effects, "nd_ai_review_posture")
        self.assertLess(review.index("nd_refresh_main_rival = yes"), review.index("nd_set_readiness_target_3"))

    def test_plausible_attacker_shared(self):
        triggers = strip_comments(read(TRIGGERS))
        self.assertIn("nd_plausible_attacker_of", block(triggers, "nd_has_plausible_attacker"))
        self.assertIn("nd_plausible_attacker_of", block(strip_comments(read(EFFECTS)), "nd_refresh_main_rival"))


def ai_review_section(start_marker, end_marker):
    review = read(EFFECTS)
    start = review.index(start_marker, review.index("nd_ai_review_posture = {"))
    return strip_comments(review[start:review.index(end_marker, start)])


class TestAuthorityPayoffs(unittest.TestCase):
    """Delegation and Launch on Warning pay; safeguards trim the payoff; the
    AI's safeguards are no longer automatic and its authority reads survivors
    (2026-10-28 rework spec §4.1, §4.2, §4.4)."""

    def test_authority_reads_bare_heightened_survivors(self):
        authority = ai_review_section("# ---- launch authority", "# ---- investment")
        self.assertIn("nd_ai_vulnerable_to_main_rival = yes", authority)
        self.assertIn("nd_ai_hardening_cannot_close = yes", authority)
        self.assertNotIn("nd_effective_survivability", authority)
        self.assertNotIn("var:nd_survivability", authority)
        triggers = strip_comments(read(TRIGGERS))
        self.assertIn("var:nd_survivors_main_bare_r2 < 3", block(triggers, "nd_ai_vulnerable_to_main_rival"))
        self.assertIn("var:nd_survivors_main_ceiling_bare_r2 < 3", block(triggers, "nd_ai_hardening_cannot_close"))

    def test_safeguards_not_automatic(self):
        investment = ai_review_section("# ---- investment", "# ---- arsenal size")
        for needle in ("ruler_is_cautious = yes", "nd_regime_is_restraint = yes", "nd_regime_is_militarist = yes",
                       "nd_doctrine_warfighting = yes", "nd_in_budget_deficit = yes",
                       "nd_authority_delegated_or_warning = yes",
                       "clamp_variable = { name = nd_ai_want_safeguards min = 0 max = 3 }"):
            self.assertIn(needle, investment)
        self.assertNotIn("var:nd_readiness_target = 3", investment)

    def test_back_to_central_without_threat(self):
        authority = ai_review_section("# ---- launch authority", "# ---- investment")
        branches = re.findall(r"else_if = \{\s*limit = \{(.*?)\}\s*(?:random = \{[^}]*)?nd_set_authority_1 = yes",
                              authority, re.S)
        self.assertTrue(any("ruler_is_cautious" not in b and "nd_ai_vulnerable_to_main_rival = no" in b
                            for b in branches), branches)

    def test_hardening_closes_a_closable_gap(self):
        investment = ai_review_section("# ---- investment", "# ---- arsenal size")
        self.assertIn("nd_ai_hardening_cannot_close = no", investment)
        self.assertIn("clamp_variable = { name = nd_ai_want_hardening min = 0 max = 3 }", investment)

    def test_authority_modifiers_show_payoff(self):
        modifiers = strip_comments(read(MODIFIERS))
        self.assertIn("country_nd_launch_credit_add = 0.25", block(modifiers, "nd_authority_terms_2"))
        self.assertIn("country_nd_launch_credit_add = 0.6", block(modifiers, "nd_authority_terms_3"))
        for level in (2, 3, 4):
            self.assertIn("country_nd_decapitation_immune_bool = yes", block(modifiers, f"nd_authority_terms_{level}"))
        self.assertIn("country_nd_launch_credit_add = -0.05", block(modifiers, "nd_safeguards_slow_launch"))


ACT_LINES = {
    "nd_crisis_act_yield": ["nd_crisis_yield_lines = yes", "custom_tooltip = nd_tt_then_yield"],
    "nd_crisis_yield_lines": ["nd_tt_yield_war", "nd_tt_yield_play", "nd_tt_yield_guarantee",
                              "nd_tt_yield_freeze", "nd_tt_yield_alert"],
    "nd_crisis_act_reject": ["nd_tt_stage_to_confrontation", "nd_tt_reject_defiance"],
    "nd_crisis_act_counter_threat": ["nd_tt_stage_to_confrontation", "nd_tt_counter_danger"],
    "nd_crisis_act_propose_talks": ["nd_tt_talks_terms", "nd_crisis_talks_credibility_lines = yes",
                                    "nd_tt_talks_meanwhile"],
    "nd_crisis_act_accept_standdown": ["nd_tt_standdown_terms", "nd_crisis_talks_credibility_lines = yes"],
    "nd_crisis_act_hold": ["nd_tt_hold_deadline", "nd_tt_hold_alert_4w", "nd_tt_hold_alert_2w"],
    "nd_crisis_act_extend": ["text = nd_tt_credibility_down_3"],
    "nd_crisis_act_back_down": ["nd_tt_then_back_down_public", "nd_tt_then_back_down_private",
                                "nd_tt_then_bluff_called"],
    "nd_crisis_act_go_public": ["change_infamy = nd_taboo_infamy_threat", "change_relations", "nd_tt_go_public_terms"],
    "nd_crisis_act_exercise": ["text = nd_tt_strain_up_5", "text = nd_tt_credibility_up_3",
                               "nd_tt_exercise_effect"],
}


class TestActLines(unittest.TestCase):
    def setUp(self):
        self.effects = strip_comments(read(CRISIS_EFFECTS))

    def test_every_act_names_its_numbers(self):
        for act, needles in ACT_LINES.items():
            body = block(self.effects, act)
            for needle in needles:
                self.assertIn(needle, body, f"{act} lacks {needle}")

    def test_visible_act_lines_read_no_saved_scopes(self):
        """The panel renders these acts with no saved scopes."""
        for act in ACT_LINES:
            body = block(self.effects, act)
            hidden = re.findall(r"hidden_effect = \{", body)
            visible = body
            for _ in hidden:
                visible = visible.replace("hidden_effect = {" + block(visible, "hidden_effect") + "}", "")
            self.assertNotRegex(visible, r"scope:nd_(issuer|target)", act)

    def test_act_numbers_match_their_constants(self):
        values = strip_comments(read(VALUES))
        self.assertRegex(values, r"nd_crisis_deadline_extension_weeks = 6\b")
        self.assertIn("6", loc_value("nd_tt_hold_deadline"))
        self.assertIn("6", loc_value("nd_tt_act_extend"))
        self.assertRegex(block(values, "nd_cd_counter_value"), r"add = 10\b")
        self.assertIn("10", loc_value("nd_tt_counter_danger"))
        self.assertRegex(block(values, "nd_cd_talks_value"), r"subtract = 15\b")
        self.assertIn("15", loc_value("nd_tt_talks_meanwhile"))
        self.assertRegex(block(values, "nd_yp_alert_value"), r"add = 10\b")
        self.assertIn("10", loc_value("nd_tt_hold_alert_2w"))
        self.assertIn("name = nd_crisis_exercise_weeks value = 6", block(self.effects, "nd_crisis_act_exercise"))
        self.assertIn("6", loc_value("nd_tt_exercise_effect"))


BREAKDOWN_KEYS = {p: p + "_line" for p in DANGER_PARTS + PRESSURE_PARTS}


class TestCrisisPanel(unittest.TestCase):
    def setUp(self):
        self.sguis = strip_comments(read(SGUIS))
        self.gui = read(GUI)
        self.custom = strip_comments(read(CUSTOM_LOC))
        self.effects = strip_comments(read(CRISIS_EFFECTS))

    def test_display_handlers_exist_and_are_display_only(self):
        for name in ("nd_crisis_we_issued_sgui", "nd_crisis_we_are_target_sgui", "nd_crisis_private_sgui",
                     "nd_crisis_pressure_breakdown_sgui", "nd_crisis_danger_breakdown_sgui",
                     "nd_crisis_next_pressure_sgui"):
            body = block(self.sguis, name)
            self.assertIn("is_valid = { always = no }", body, name)
            self.assertIn("ai_is_valid = { always = no }", body, name)
            self.assertIn(name, self.gui, f"{name} is never drawn")

    def test_breakdowns_print_every_stored_part(self):
        pressure = block(self.sguis, "nd_crisis_pressure_breakdown_sgui")
        danger = block(self.sguis, "nd_crisis_danger_breakdown_sgui")
        for part in PRESSURE_PARTS:
            self.assertIn(f"nd_crisis_breakdown_line = {{ C = {part} KEY = {BREAKDOWN_KEYS[part]} }}", pressure)
        for part in DANGER_PARTS:
            self.assertIn(f"nd_crisis_breakdown_line = {{ C = {part} KEY = {BREAKDOWN_KEYS[part]} }}", danger)

    def test_breakdown_lines_guard_their_variable(self):
        body = block(self.effects, "nd_crisis_breakdown_line")
        self.assertIn("has_variable = $C$", body)
        for part, key in BREAKDOWN_KEYS.items():
            self.assertIn(f"THIS.Var('{part}').GetValue", loc_value(key), key)

    def test_role_rows_are_gated(self):
        for key, sgui in (("nd_w_crisis_act_public", "nd_crisis_private_sgui"),
                          ("nd_w_crisis_act_yield", "nd_crisis_we_are_target_sgui"),
                          ("nd_w_crisis_act_back_down", "nd_crisis_we_issued_sgui"),
                          ("nd_w_crisis_act_exercise", "nd_armed_sgui")):
            i = self.gui.index(f'text = "{key}"')
            row = self.gui.rfind("nd_choice_row = {", 0, i)
            self.assertIn(f"GetScriptedGui('{sgui}')", self.gui[row:i], key)

    def test_new_custom_loc_blocks_have_fallbacks(self):
        for name in ("nd_crisis_pressure_label", "nd_crisis_concede_label", "nd_crisis_concession_short",
                     "nd_crisis_concession_long", "nd_crisis_ft_label", "nd_crisis_ft_word",
                     "nd_crisis_ft_reason", "nd_crisis_stakes_long",
                     "nd_crisis_concession_past", "nd_crisis_stage_next",
                     # the compact crisis (NUC-7): the headline's words, the readings, the outcomes
                     "nd_crisis_role_phrase", "nd_crisis_dispute_phrase", "nd_crisis_public_phrase",
                     "nd_crisis_deadline_who", "nd_crisis_pressure_band", "nd_crisis_backdown_label",
                     "nd_crisis_cred_if_concede", "nd_crisis_cred_if_backdown", "nd_crisis_cred_if_standdown"):
            body = block(self.custom, name)
            self.assertRegex(body, r"text = \{\s*trigger = \{ always = yes \}\s*localization_key = \w+\s*\}\s*$", name)

    def test_localize_keys_in_gui_exist(self):
        keys = set(re.findall(r"Localize\( '(\w+)' \)", self.gui))
        self.assertTrue(keys)
        missing = sorted(k for k in keys if k not in loc_keys())
        self.assertFalse(missing, missing)

    def test_pressure_thresholds_match_the_events(self):
        events = strip_comments(read(CRISIS_EVENTS))
        concede = option_body(events, "nuclear_crisis.5.a")
        for n in ("50", "70", "85"):
            self.assertIn(f"var:nd_yield_pressure >= {n}", concede)
            self.assertIn(n, loc_value("nd_w_crisis_pressure_tt"))


class TestWorldCrises(unittest.TestCase):
    """The World Crises section (NUC-14): the list the refresh keeps, the
    datamodel that draws it, and every place a crisis starts, ends or changes
    its danger."""

    def setUp(self):
        self.sguis = strip_comments(read(SGUIS))
        self.gui = read(GUI)
        self.effects = strip_comments(read(CRISIS_EFFECTS))

    def test_the_refresh_rebuilds_the_list_most_dangerous_first(self):
        body = block(self.effects, "nd_world_crises_refresh")
        self.assertTrue(body.strip().startswith("hidden_effect"), "the refresh must stay out of tooltips")
        self.assertIn("nd_lists_store_ensure = yes", body)
        self.assertLess(body.index("clear_variable_list = nd_crises"), body.index("ordered_country"))
        self.assertIn("order_by = nd_display_crisis_danger", body)
        self.assertIn("add_to_variable_list = { name = nd_crises target = scope:nd_wc_issuer_cap }", body)
        self.assertIn("set_variable = { name = nd_wc_target_cap value = scope:nd_wc_target_cap_new }", body)
        self.assertIn("set_global_variable = { name = nd_wc_count value = 0 }", body)
        store = block(self.effects, "nd_lists_store_ensure")
        self.assertIn("set_global_variable = { name = nd_lists_store value = scope:nd_lists_store_new }", store)

    def test_the_section_draws_the_list(self):
        sec = self.gui[self.gui.index("type te_nuclear_sec_world_crises"):self.gui.index("type te_nuclear_sec_posture")]
        self.assertIn('datamodel = "[GetGlobalVariable(\'nd_lists_store\').GetList(\'nd_crises\')]"', sec)
        self.assertIn('datacontext = "[Scope.GetState]"', sec)
        row = self.gui[self.gui.index("type nd_world_crisis_row = widget"):self.gui.index("type nd_world_crisis_head")]
        self.assertEqual(row.count("tiny_flag = {"), 2)
        self.assertIn('datacontext = "[State.GetOwner]"', row)
        self.assertIn("State.GetOwner.MakeScope.Var('nd_wc_target_cap').GetState.GetOwner", row)
        self.assertIn("GetScriptedGui('nd_world_crisis_item_detail_sgui').ExecuteTooltip( GuiScope.SetRoot( State.GetOwner.MakeScope ).End )", row)

    def test_the_gate_reads_the_count(self):
        gate = block(self.sguis, "nd_world_crises_sgui")
        self.assertIn("global_var:nd_wc_count > 0", gate)

    def test_every_change_refreshes_the_list(self):
        for name in ("nd_crisis_open", "nd_crisis_close", "nd_crisis_weekly_tick"):
            self.assertIn("nd_world_crises_refresh = yes", block(self.effects, name), name)
        taboo = strip_comments(read(ROOT / "common/scripted_effects/nuclear_taboo_effects.txt"))
        self.assertIn("nd_world_crises_refresh = yes", block(taboo, "nd_taboo_monthly_update"))

    def test_handlers_are_display_only_and_drawn(self):
        for name in ("nd_world_crises_sgui", "nd_world_crisis_item_detail_sgui"):
            body = block(self.sguis, name)
            self.assertIn("is_valid = { always = no }", body, name)
            self.assertIn("ai_is_valid = { always = no }", body, name)
            self.assertIn(name, self.gui, f"{name} is never drawn")
        self.assertIn("nd_world_crisis_detail_lines = yes", block(self.sguis, "nd_world_crisis_item_detail_sgui"))

    def test_the_slots_are_gone(self):
        for old in ("nd_world_crisis_row_sgui", "nd_world_crisis_detail_sgui", "nd_world_crisis_slot_live",
                    "nd_world_crisis_row_at", "nd_world_crisis_detail_at", "global_var:nd_wc_1"):
            for text in (self.sguis, self.effects, self.gui, strip_comments(read(TRIGGERS))):
                self.assertNotIn(old, text, old)

    def test_printed_lines_have_loc(self):
        text = self.effects + self.sguis
        printed = set(re.findall(r"custom_tooltip_no_bullet = (nd_wc_\w+)", text))
        self.assertTrue(printed)
        missing = sorted(printed - loc_keys())
        self.assertFalse(missing, missing)


class TestInterestGroupClasses(unittest.TestCase):
    OLD = ("nd_ig_leader_is_hawk", "nd_ig_leader_is_dove", "nd_ig_class_warfighting", "nd_ig_class_dove")
    NEW = ("nd_stance_militarist_full", "nd_stance_militarist_mild", "nd_stance_restraint_full",
           "nd_stance_restraint_mild", "nd_stance_militarist", "nd_stance_restraint",
           "nd_stance_full", "nd_ig_is_fixed_class", "nd_ig_class_professional", "nd_ig_class_business",
           "nd_ig_class_militarist", "nd_ig_class_restraint", "nd_ig_lean_militarist", "nd_ig_lean_restraint",
           "nd_ig_is_militarist", "nd_ig_is_restraint", "nd_ig_is_hawk", "nd_ig_view_full")

    def test_new_triggers_exist(self):
        t = read(TRIGGERS)
        for name in self.NEW:
            self.assertRegex(t, rf"(?m)^{name} = \{{", name)

    def test_old_triggers_are_gone_everywhere(self):
        for path in list((ROOT / "common").rglob("*.txt")) + list((ROOT / "events").glob("*.txt")):
            text = strip_comments(read(path))
            for name in self.OLD:
                self.assertNotIn(name, text, f"{path.name} still uses {name}")

    def test_stances_read_the_rules_of_war_laws(self):
        t = strip_comments(read(TRIGGERS))
        for name in ("nd_stance_militarist_full", "nd_stance_restraint_full"):
            body = block(t, name)
            self.assertIn("law_type:law_total_war", body)
            self.assertIn("law_type:law_limited_war", body)

    def test_rewards_pay_hawks_and_doves(self):
        effects = strip_comments(read(CRISIS_EFFECTS))
        self.assertIn("nd_ig_is_hawk = yes", block(effects, "nd_reward_hawks"))
        self.assertIn("nd_ig_is_restraint = yes", block(effects, "nd_reward_doves"))


IG_VARS = ["nd_ig_class", "nd_ig_lean", "nd_ig_strength", "nd_ig_term_doctrine", "nd_ig_term_readiness",
           "nd_ig_term_authority", "nd_ig_term_strain", "nd_ig_term_business", "nd_ig_term_possession",
           "nd_ig_stance"]


class TestInterestGroupOpinion(unittest.TestCase):
    def setUp(self):
        self.values = strip_comments(read(VALUES))
        self.effects = strip_comments(read(EFFECTS))

    def test_country_level_stance_values_are_gone(self):
        for old in ("nd_stance_warfighting_value", "nd_stance_professional_value",
                    "nd_stance_dove_value", "nd_stance_business_value"):
            self.assertNotRegex(self.values, rf"(?m)^{old} = \{{")

    def test_ig_values_exist(self):
        for name in ("nd_ig_doctrine_militarist_value", "nd_ig_doctrine_restraint_value",
                     "nd_ig_doctrine_professional_value", "nd_ig_term_doctrine_value",
                     "nd_ig_term_readiness_value", "nd_ig_term_authority_value", "nd_ig_term_strain_value",
                     "nd_ig_term_business_value", "nd_ig_stance_value", "nd_display_stance_months_left"):
            self.assertRegex(self.values, rf"(?m)^{name} = \{{", name)

    def test_store_writes_and_clear_removes_every_variable(self):
        store = block(self.effects, "nd_ig_store_opinion")
        clear = block(self.effects, "nd_ig_clear_opinion")
        for var in IG_VARS:
            self.assertIn(f"name = {var} value", store, var)
            self.assertIn(f"remove_variable = {var}", clear, var)

    def test_band_reads_the_stored_stance(self):
        band = block(self.effects, "nd_ig_set_band")
        self.assertIn("var:nd_ig_stance >= 2", band)
        self.assertNotIn("owner", band)

    def test_business_terms_do_not_wait_for_tenure(self):
        body = block(self.values, "nd_ig_term_business_value")
        self.assertNotIn("nd_ig_posture_judged", body)
        for name in ("nd_ig_term_doctrine_value", "nd_ig_term_readiness_value",
                     "nd_ig_term_authority_value", "nd_ig_term_strain_value"):
            self.assertIn("nd_ig_posture_judged = yes", block(self.values, name), name)


# The At Home table (play-test round 3, 2026-09-30): one small table per
# interest group with a view, in place of the two script-built lines per group
# that nd_home_line printed. Each class shows the terms its line used to print.
HOME_TERMS = ("doctrine", "readiness", "authority", "strain", "possession", "business")
HOME_VIEWS = range(1, 11)   # the ten lines: class x lean / strength


class TestAtHome(unittest.TestCase):
    def setUp(self):
        self.gui = read(GUI)
        start = self.gui.index("type nd_home_ig_table = flowcontainer {")
        depth, i = 0, self.gui.index("{", start)
        for i in range(i, len(self.gui)):
            depth += (self.gui[i] == "{") - (self.gui[i] == "}")
            if depth == 0:
                break
        self.table = self.gui[start:i]
        self.values = strip_comments(read(VALUES))

    def test_every_group_view_and_term_is_a_row(self):
        sv = "InterestGroup.MakeScope.ScriptValue"
        for n in HOME_VIEWS:
            self.assertIn(f"{sv}('nd_disp_ig_view'), '(CFixedPoint){n}' )", self.table, n)
            self.assertIn(f'text = "nd_home_view_{n}"', self.table, n)
            self.assertTrue(loc_value(f"nd_home_view_{n}"), n)
        self.assertIn('text = "nd_home_row_approval_value"', self.table)
        self.assertIn(f"{sv}('nd_disp_ig_stance')", loc_value("nd_home_row_approval_value"))
        for term in HOME_TERMS:
            self.assertIn(f"{sv}('nd_disp_ig_shows_{term}'), '(CFixedPoint)1' )", self.table, term)
            self.assertIn(f"{sv}('nd_disp_ig_term_{term}')", loc_value(f"nd_home_row_{term}_value"), term)
            self.assertTrue(loc_value(f"nd_home_row_{term}_tt"), term)
        self.assertIn("[InterestGroup.GetName]", loc_value("nd_home_ig_name"))

    def test_cap_row_shows_what_the_cap_cut(self):
        """A group whose terms total past the cap (doctrine 2 + readiness 1 -> 2)
        gets a closing row with the difference, so the rows visibly add up."""
        sv = "InterestGroup.MakeScope.ScriptValue"
        self.assertIn(f"{sv}('nd_disp_ig_cap_cut'), '(CFixedPoint)0' )", self.table)
        self.assertIn('text = "nd_home_row_cap_value"', self.table)
        self.assertIn(f"{sv}('nd_disp_ig_cap_cut')", loc_value("nd_home_row_cap_value"))
        self.assertTrue(loc_value("nd_home_row_cap_tt"))
        body = block(self.values, "nd_disp_ig_cap_cut")
        self.assertIn("value = nd_disp_ig_stance", body)
        for term in HOME_TERMS:
            self.assertIn(f"subtract = nd_disp_ig_term_{term}", body, term)

    def test_each_class_shows_the_terms_its_line_printed(self):
        """militarist: doctrine, readiness; restraint: + authority, the arsenal;
        officers: doctrine, readiness, crew strain; business: alerts and crises,
        and doctrine when its leader leans."""
        shows = {term: block(self.values, f"nd_disp_ig_shows_{term}") for term in HOME_TERMS}
        for term in ("doctrine", "readiness"):
            self.assertIn("nd_disp_ig_class >= 1", shows[term], term)
            self.assertIn("nd_disp_ig_class <= 3", shows[term], term)
        self.assertRegex(shows["doctrine"], r"nd_disp_ig_class = 4\s+nd_disp_ig_lean > 0")
        self.assertNotIn("nd_disp_ig_class = 4", shows["readiness"])
        for term, cls in (("authority", 2), ("possession", 2), ("strain", 3), ("business", 4)):
            self.assertIn(f"nd_disp_ig_class = {cls}", shows[term], term)

    def test_display_values_read_guarded(self):
        for var in ("class", "lean", "strength", "stance") + tuple(f"term_{t}" for t in HOME_TERMS):
            name = f"nd_disp_ig_{var}"
            body = block(self.values, name)
            self.assertIn(f"has_variable = nd_ig_{var}", body, name)

    def test_item_tooltips_need_no_journal_entry(self):
        """gui_modding_guide.md gotcha #24: a datamodel item's tooltip sees only the item."""
        for key in re.findall(r'tooltip = "(\w+)"', self.table):
            self.assertNotIn("JournalEntry", loc_value(key), key)
        self.assertIn('datamodel = "[AccessPlayer.AccessAllInterestGroups]"', self.gui)

    def test_list_is_drawn_and_old_rows_are_gone(self):
        gui = read(GUI)
        self.assertIn("nd_home_list_sgui", gui)
        for old in ("nd_w_home_warfighting_value", "nd_w_home_professional_value",
                    "nd_w_home_dove_value", "nd_w_home_business_value"):
            self.assertNotIn(old, gui)
        custom = strip_comments(read(CUSTOM_LOC))
        self.assertNotIn("nd_stance_warfighting_word", custom)
        self.assertNotIn("nd_home_line = {", strip_comments(read(EFFECTS)))

    def test_list_handler_is_display_only(self):
        """Only the empty states now: before the first review, and no group with a view."""
        body = block(strip_comments(read(SGUIS)), "nd_home_list_sgui")
        self.assertIn("is_valid = { always = no }", body)
        self.assertIn("any_interest_group", body)
        self.assertNotIn("every_interest_group", body)
        self.assertIn("custom_tooltip_no_bullet = nd_home_list_none", body)

class TestReviewFixes(unittest.TestCase):
    """Fixes from the PR 1 whole-branch review."""

    def setUp(self):
        self.effects = strip_comments(read(CRISIS_EFFECTS))
        self.events = strip_comments(read(CRISIS_EVENTS))
        self.triggers = strip_comments(read(TRIGGERS))
        self.values = strip_comments(read(VALUES))

    def test_outcome_option_applies_when_the_opponent_is_gone(self):
        body = option_body(self.events, "nuclear_crisis.6.a")
        self.assertIn("NOT = { exists = scope:nd_outcome_other }", body)
        self.assertIn("NOT = { exists = var:nd_crisis_pending_opponent }", body)

    def test_opponent_reactions_need_the_live_pending_opponent(self):
        self.assertRegex(self.triggers, r"(?m)^nd_outcome_other_is_live = \{")
        body = block(self.effects, "nd_crisis_apply_outcome_side")
        self.assertNotIn("limit = { exists = scope:nd_outcome_other }", body)
        self.assertIn("nd_outcome_other_is_live = yes", body)

    def test_outcome_notices_pop_up(self):
        body = block(self.effects, "nd_crisis_close")
        self.assertEqual(body.count("trigger_event = { id = nuclear_crisis.6 popup = yes }"), 2)

    def test_every_act_credibility_change_says_its_number(self):
        for m in re.finditer(r"(?m)^((?:nd_crisis_act|nd_guarantee_act)_\w+) = \{", self.effects):
            body = block(self.effects, m.group(1))
            pairs = re.findall(r"text = nd_tt_credibility_(up|down)_(\d+)(?:_bluff)?\s*nd_change_credibility = \{ AMOUNT = (-?\d+) \}", body)
            for direction, n, amount in pairs:
                self.assertEqual(int(amount), int(n) if direction == "up" else -int(n), m.group(1))
            self.assertEqual(body.count("nd_change_credibility"), len(pairs),
                             f"{m.group(1)} changes credibility without its number line")

    def test_guarantee_honour_previews_its_ultimatum(self):
        body = block(self.effects, "nd_guarantee_act_honour")
        hidden = block(body, "hidden_effect")
        self.assertNotIn("nd_crisis_open", hidden)
        self.assertIn("nd_crisis_open = { TARGET = scope:nd_guarantee_attacker PUBLIC = yes }", body)

    def test_exercise_pressure_counts_only_the_issuers(self):
        self.assertIn("var:nd_crisis_exercise_by_issuer = 1", block(self.values, "nd_yp_exercise_value"))
        act = block(self.effects, "nd_crisis_act_exercise")
        self.assertIn("name = nd_crisis_exercise_by_issuer value = 1", act)
        self.assertIn("name = nd_crisis_exercise_by_issuer value = 0", act)
        self.assertIn("remove_variable = nd_crisis_exercise_by_issuer", block(self.effects, "nd_crisis_weekly_tick"))
        self.assertIn("remove_variable = nd_crisis_exercise_by_issuer", block(self.effects, "nd_crisis_clear_vars"))
        incidents = strip_comments(read(INCIDENT_EVENTS))
        self.assertIn("nd_crisis_exercise_by_issuer", option_body(incidents, "nuclear_incident.10.c"))
        self.assertIn("name = nd_crisis_exercise_by_issuer value = 1", option_body(incidents, "nuclear_incident.10.e"))

    def test_preview_charges_only_when_the_crisis_opens(self):
        body = block(self.effects, "nd_crisis_preview")
        gate = body.index("nd_crisis_parties_free = { TARGET = $TARGET$ }")
        self.assertLess(gate, body.index("change_infamy"))
        self.assertLess(gate, body.index("change_relations"))

    def test_refuse_talks_promises_pressure_only_from_confrontation(self):
        body = block(self.effects, "nd_crisis_act_refuse_talks")
        self.assertIn("custom_tooltip = nd_tt_refuse_talks_resume", body)
        self.assertIn("custom_tooltip = nd_tt_refuse_talks_no_pressure_yet", body)
        self.assertIn("6", loc_value("nd_tt_refuse_talks_resume"))

    def test_war_law_tooltips_match_the_exception(self):
        for key in ("nd_tt_war_law_permits_strike", "nd_tt_war_law_permits_tactical_strike"):
            self.assertIn("a war we are fighting", loc_value(key), key)

    def test_ft_reason_2_names_both_doctrines(self):
        self.assertIn("Warfighting", loc_value("nd_ft_reason_2"))

    def test_preview_header_is_pinned_and_points_to_the_tab(self):
        self.assertRegex(block(self.values, "nd_yp_base_value"), r"value = 30\b")
        header = loc_value("nd_tt_open_factors_header")
        self.assertIn("30", header)
        self.assertIn("#v Nuclear#! tab of the Military panel", header)


STANCES = ["strongly_disapprove", "disapprove", "neutral", "approve", "strongly_approve", "count"]


def stance_clauses(trigger_body):
    """(negated, law, threshold) for each `law_stance = { law = … value > … }`
    in a trigger body, top-level or under one NOT."""
    out = []
    for m in re.finditer(r"(NOT = \{\s*)?law_stance = \{\s*law = law_type:(\w+)\s*value > (\w+)\s*\}", trigger_body):
        out.append((bool(m.group(1)), m.group(2), m.group(3)))
    return out


def holds(clauses, total, limited):
    for negated, law, threshold in clauses:
        value = total if law == "law_total_war" else limited
        result = STANCES.index(value) > STANCES.index(threshold)
        if result == negated:
            return False
    return True


class TestAtHomeReviewFixes(unittest.TestCase):
    """Fixes from the PR 2 whole-branch review."""

    def setUp(self):
        self.triggers = strip_comments(read(TRIGGERS))
        self.sguis = strip_comments(read(SGUIS))

    def test_stance_truth_table(self):
        """Spec §4.1 over every pair of stances: the stronger approval of Total
        War or Limited War wins, a tie is no view, and `count` is never
        approval."""
        names = ("nd_stance_militarist_full", "nd_stance_militarist_mild",
                 "nd_stance_restraint_full", "nd_stance_restraint_mild")
        clauses = {n: stance_clauses(block(self.triggers, n)) for n in names}
        for n in names:
            self.assertTrue(clauses[n], n)
        real = STANCES[:5]
        for total in STANCES:
            for limited in STANCES:
                got = [n for n in names if holds(clauses[n], total, limited)]
                self.assertLessEqual(len(got), 1, (total, limited, got))
                if "count" in (total, limited):
                    expected = []
                else:
                    t, l = real.index(total), real.index(limited)
                    expected = []
                    if t > l and t >= 3:
                        expected = ["nd_stance_militarist_full" if t == 4 else "nd_stance_militarist_mild"]
                    elif l > t and l >= 3:
                        expected = ["nd_stance_restraint_full" if l == 4 else "nd_stance_restraint_mild"]
                self.assertEqual(got, expected, (total, limited))

    def test_fixed_class_leans_read_the_leader(self):
        self.assertIn("leader ?= { nd_stance_militarist = yes }", block(self.triggers, "nd_ig_lean_militarist"))
        self.assertIn("leader ?= { nd_stance_restraint = yes }", block(self.triggers, "nd_ig_lean_restraint"))
        self.assertIn("leader ?= { nd_stance_full = yes }", block(self.triggers, "nd_ig_view_full"))

    def test_incident_sites_pay_militarists_including_leans(self):
        text = strip_comments(read(INCIDENT_EVENTS))
        self.assertIn("limit = { nd_ig_is_militarist = yes }", text)
        for path in list((ROOT / "common").rglob("*.txt")) + list((ROOT / "events").glob("*.txt")):
            self.assertNotRegex(strip_comments(read(path)), r"nd_ig_stance_(militarist|restraint|full)", path.name)

    def test_footer_follows_the_list_and_always_says_reviewed(self):
        gui = read(GUI)
        self.assertLess(gui.index("nd_home_list_sgui"), gui.index("nd_home_footer_sgui"))
        footer = block(self.sguis, "nd_home_footer_sgui")
        self.assertRegex(footer, r"custom_tooltip_no_bullet = nd_home_list_reviewed\s")
        self.assertIn("custom_tooltip_no_bullet = nd_home_list_waiting", footer)
        self.assertNotIn("nd_home_list_waiting", block(self.sguis, "nd_home_list_sgui"))

    def test_list_before_the_first_review_says_so(self):
        body = block(self.sguis, "nd_home_list_sgui")
        self.assertIn("has_variable = nd_stance_applied", body)
        self.assertIn("custom_tooltip_no_bullet = nd_home_list_not_reviewed", body)


class TestManagedFamilies(unittest.TestCase):
    def test_doctrine_and_readiness_families_exist(self):
        mods = set(re.findall(r"^(nd_\w+)\s*=\s*\{", read(MODIFIERS), re.M))
        for d in range(1, 6):
            self.assertIn(f"nd_doctrine_mod_{d}", mods)
        for r in (2, 3):
            self.assertIn(f"nd_readiness_mod_{r}", mods)
        self.assertIn("nd_upkeep_cost", mods)

    def test_every_family_member_is_removed_by_the_tracker_helpers(self):
        effects = read(EFFECTS)
        remove_doc = block(effects, "nd_remove_doctrine_modifier")
        for d in range(1, 6):
            self.assertIn(f"remove_modifier = nd_doctrine_mod_{d}", remove_doc)
        remove_rd = block(effects, "nd_remove_readiness_modifier")
        for r in (2, 3):
            self.assertIn(f"remove_modifier = nd_readiness_mod_{r}", remove_rd)

    def test_posture_wrappers_exist_for_every_value(self):
        effects = read(EFFECTS)
        for d in range(1, 6):
            self.assertRegex(effects, rf"(?m)^nd_set_doctrine_{d} = \{{")
        for r in range(0, 4):
            self.assertRegex(effects, rf"(?m)^nd_set_readiness_target_{r} = \{{")
        for a in range(1, 5):
            self.assertRegex(effects, rf"(?m)^nd_set_authority_{a} = \{{")

    def test_no_bare_parameterised_calls_remain(self):
        """Callers go through the wrappers, which pass the literal flags the
        core effects branch on (see nd_set_doctrine's header)."""
        for path in SCRIPT_FILES:
            text = strip_comments(read(path))
            for m in re.finditer(r"nd_set_(doctrine|readiness_target|authority) = \{ [DRA] = \d \}", text):
                self.fail(f"{path.name}: {m.group(0)} bypasses the wrapper")


class TestRecessed(unittest.TestCase):
    """Recessed readiness, level 0 (spec 2026-09-25 umbrella/recessed/dead-hand §2)."""

    def setUp(self):
        self.triggers = strip_comments(read(TRIGGERS))
        self.effects = strip_comments(read(EFFECTS))
        self.crisis = strip_comments(read(CRISIS_EFFECTS))
        self.values = strip_comments(read(VALUES))

    def test_triggers_exist(self):
        for name in ("nd_readiness_recessed", "nd_forces_assembled"):
            self.assertRegex(self.triggers, rf"(?m)^{name} = \{{")

    def test_standdowns_never_raise_a_recessed_country(self):
        # A stand-down sets the target to Routine only when it is above Routine.
        self.assertIn("var:nd_readiness_target > 1", block(self.crisis, "nd_standdown_one_side"))
        concession = self.crisis[self.crisis.index("nd_crisis_programme_freeze"):]
        concession = concession[:concession.index("nd_readiness_lock_months_value")]
        self.assertIn("var:nd_readiness_target > 1", concession)

    def test_stood_down_alert_includes_recessed(self):
        # No crisis test may treat Routine alone as stood down. The alert
        # dispute's native close reads no readiness at all now
        # (TestNativeCloses); the concession's lock is what binds.
        self.assertNotRegex(self.crisis, r"var:nd_readiness_target = 1\b")

    def test_recessed_has_no_readiness_modifier(self):
        # nd_readiness_mod_on uses 0 for "none": a level-0 member could never be tracked.
        self.assertNotIn("nd_readiness_mod_0", read(MODIFIERS))
        self.assertNotIn("nd_readiness_mod_0", self.effects)

    def test_every_readiness_level_has_upkeep_and_a_row(self):
        for r in range(0, 4):
            self.assertRegex(self.values, rf"(?m)^nd_upkeep_weekly_at_readiness_{r} = \{{")
        self.assertIn(20, gui_ops(read(GUI), "nd_posture_sgui"))

    def test_lock_lets_routine_through(self):
        sg = strip_comments(read(SGUIS))
        for op, ok in ((20, "yes"), (21, "yes"), (22, "no"), (23, "no")):
            self.assertIn(f"nd_can_set_readiness = {{ R = {op - 20} LOCK_OK = {ok} }}", sg)
        self.assertIn("always = $LOCK_OK$", block(self.triggers, "nd_can_set_readiness"))

    def test_recessed_is_named_everywhere_a_level_is(self):
        custom = strip_comments(read(CUSTOM_LOC))
        self.assertIn("localization_key = nd_readiness_0", block(custom, "nd_readiness_name"))
        self.assertIn("localization_key = nd_readiness_moving_0", block(custom, "nd_readiness_moving"))
        self.assertIn("nd_readiness_recessed = yes", block(self.values, "nd_incident_base_monthly_permille"))


DISPLAY_TYPES = ROOT / "common/modifier_type_definitions/nuclear_deterrence_display_types.txt"


class TestPostureTerms(unittest.TestCase):
    """NUC-6 (2026-10-27): what readiness and launch authority do through script
    prints as modifier lines, from display-only modifiers nothing adds, whose
    figures are the ones the script uses."""

    def setUp(self):
        self.mods = strip_comments(read(MODIFIERS))
        self.values = strip_comments(read(VALUES))
        self.types = strip_comments(read(DISPLAY_TYPES))

    def field(self, mod, name):
        m = re.search(rf"\b{name} = (-?[\d.]+|yes)", block(self.mods, mod))
        return None if m is None else (m.group(1) if m.group(1) == "yes" else float(m.group(1)))

    def test_every_display_type_is_script_only_and_named(self):
        names = re.findall(r"^(country_nd_\w+) = \{", self.types, re.M)
        self.assertGreaterEqual(len(names), 10)
        keys = loc_keys()
        for name in names:
            self.assertIn("script_only = yes", block(self.types, name), name)
            self.assertIn(name, keys, name)
            self.assertIn(name + "_desc", keys, name)

    def test_nothing_adds_the_display_modifiers(self):
        for path in SCRIPT_FILES + (ROOT / "common/journal_entries/je_nuclear_program.txt",):
            text = strip_comments(read(path))
            self.assertNotRegex(text, r"(add|remove)_modifier\s*=\s*\{?\s*(name\s*=\s*)?nd_(readiness|authority)_terms_",
                                path.name)

    def test_readiness_figures_match_the_script(self):
        base = block(self.values, "nd_incident_base_monthly_permille")
        rates = {0: float(re.search(r"nd_readiness_recessed = yes \} value = ([\d.]+)", base).group(1)), 1: 1.0,
                 2: float(re.search(r"nd_readiness_heightened_or_higher = yes \} value = ([\d.]+)", base).group(1)),
                 3: float(re.search(r"nd_readiness_high_alert = yes \} value = ([\d.]+)", base).group(1))}
        self.assertRegex(base, r"^\s*value = 1\s*$" if False else r"value = 1\b")
        strain = block(self.values, "nd_strain_step")
        steps = {0: -6.0, 1: -6.0, 2: 1.5, 3: 5.0}
        self.assertIn("value = -6", strain)
        self.assertIn("value = 5", strain)
        self.assertIn("value = 1.5", strain)
        self.assertIn("multiply = 8", block(self.values, "nd_cd_issuer_readiness_value"))
        for r in range(4):
            mod = f"nd_readiness_terms_{r}"
            rate = self.field(mod, "country_nd_incident_rate_mult") or 0.0
            self.assertAlmostEqual(rate, rates[r] - 1, msg=mod)
            self.assertEqual(self.field(mod, "country_nd_crew_strain_monthly_add"), steps[r], mod)
            self.assertEqual(self.field(mod, "country_nd_crisis_danger_add") or 0.0, (r - 1) * 8.0, mod)
        self.assertIn("multiply = 0.5", block(self.values, "nd_upkeep_units_custody_recessed"))
        self.assertEqual(self.field("nd_readiness_terms_0", "country_nd_custody_cost_mult"), -0.5)
        self.assertEqual(self.field("nd_readiness_terms_0", "country_nd_launch_blocked_bool"), "yes")
        self.assertIn("add = -10", block(self.values, "nd_yp_recessed_value"))
        self.assertIn("add = 10", block(self.values, "nd_yp_alert_value"))
        self.assertEqual(self.field("nd_readiness_terms_0", "country_nd_threat_pressure_add"), -10.0)
        self.assertEqual(self.field("nd_readiness_terms_3", "country_nd_threat_pressure_add"), 10.0)

    def test_authority_figures_match_the_script(self):
        hold = block(self.values, "nd_hold_chance")
        self.assertRegex(hold, r"nd_authority_launch_on_warning = yes \}\s*subtract = 10")
        self.assertEqual(self.field("nd_authority_terms_3", "country_nd_halt_chance_add"), -0.1)
        custody = block(strip_comments(read(CUSTODY_VALUES)), "nd_custody_loss_rate")
        self.assertRegex(custody, r"nd_authority_delegated_or_warning = yes \}\s*add = 0.03")
        for a in (2, 3):
            self.assertEqual(self.field(f"nd_authority_terms_{a}", "country_nd_custody_loss_add"), 0.03, a)
            self.assertEqual(self.field(f"nd_authority_terms_{a}", "country_nd_unapproved_launch_bool"), "yes", a)
        self.assertEqual(self.field("nd_authority_terms_1", "country_nd_order_required_bool"), "yes")
        self.assertEqual(self.field("nd_authority_terms_4", "country_nd_automatic_answer_bool"), "yes")

    def test_the_choices_print_the_lines(self):
        for r in range(4):
            self.assertIn(f"GetStaticModifier('nd_readiness_terms_{r}').GetDesc", loc_value(f"nd_w_readiness_choice_{r}_tt"))
        for r in (2, 3):
            self.assertIn(f"GetStaticModifier('nd_readiness_mod_{r}').GetDesc", loc_value(f"nd_w_readiness_choice_{r}_tt"))
        for a in range(1, 5):
            self.assertIn(f"GetStaticModifier('nd_authority_terms_{a}').GetDesc", loc_value(f"nd_w_authority_choice_{a}_tt"))
        # NUC-6c: no option names the interest groups' reactions (At Home and the
        # posture concepts list them all).
        for key in ([f"nd_w_doctrine_choice_{d}_tt" for d in range(1, 6)] + [f"nd_w_readiness_choice_{r}_tt" for r in range(4)]
                    + [f"nd_w_authority_choice_{a}_tt" for a in range(1, 5)]):
            for word in ("groups approve", "groups disapprove", "popular with", "officers do not"):
                self.assertNotIn(word, loc_value(key), key)


class TestLaunchGate(unittest.TestCase):
    """Nothing launches from Recessed; a struck recessed country can answer
    once assembled (umbrella/recessed/dead-hand spec §2.3–§2.4)."""

    def test_every_launch_path_needs_assembled_forces(self):
        nuke = strip_comments(read(NUKE))
        for action in ("nuke_diplo_action", "tactical_nuke_diplo_action"):
            self.assertIn("nd_forces_assembled = yes", block(block(nuke, action), "possible"), action)
        t = strip_comments(read(TRIGGERS))
        for name in ("nd_retaliation_permitted", "nd_incident_eligible_commander", "nd_monopoly_window_conditions"):
            self.assertIn("nd_forces_assembled = yes", block(t, name), name)
        e = strip_comments(read(EFFECTS))
        for name in ("nd_dispatch_strategic_strike", "nd_dispatch_tactical_strike"):
            self.assertIn("nd_forces_assembled = yes", block(e, name), name)
        ev = strip_comments(read(CRISIS_EVENTS))
        for opt in ("nuclear_crisis.4.g", "nuclear_crisis.7.a"):
            self.assertIn("nd_forces_assembled = yes", option_body(ev, opt), opt)
        inc = strip_comments(read(INCIDENT_EVENTS))
        ev20 = block(inc, "nuclear_incident.20")
        event_trigger = ev20[re.search(r"(?m)^\ttrigger = \{", ev20).start():]
        self.assertIn("nd_forces_assembled = yes", block(event_trigger, "trigger"))

    def test_struck_while_recessed_can_wait_and_answer(self):
        ev = strip_comments(read(WEAPON_EVENTS))
        self.assertIn("nd_assemble_for_retaliation = { ENEMY = scope:attacking_country }",
                      option_body(ev, "nuclear_weapon_events.1.g"))
        self.assertRegex(ev, r"(?m)^nuclear_weapon_events\.24 = \{")
        weekly = block(strip_comments(read(EFFECTS)), "nd_weekly_update")
        self.assertIn("nd_pending_retaliation", weekly)
        self.assertIn("id = nuclear_weapon_events.24", weekly)
        body = block(ev, "nuclear_weapon_events.24")
        # The event's own trigger, not a triggered text's (its title reads
        # "Command Restored" after a decapitation).
        event_trigger = block(body[re.search(r"(?m)^\ttrigger = \{", body).start():], "trigger")
        self.assertIn("has_war_with = scope:nd_ready_enemy", event_trigger)

    def test_assembling_bypasses_the_lock_but_only_raises(self):
        body = block(strip_comments(read(EFFECTS)), "nd_assemble_for_retaliation")
        self.assertIn("var:nd_readiness_target < 1", body)
        self.assertIn("nd_set_readiness_target_1 = yes", body)
        self.assertNotIn("nd_can_set_readiness", body)


class TestProliferationSpur(unittest.TestCase):
    """"The Bomb Has Been Used" (nd_proliferation_spur) follows a warhead that
    went off, not a launch: a miss detonated nothing. Every strike effect's
    hit branch marks the launcher; nd_record_nuclear_use spurs only on the
    mark and clears it, so a salvo spurs once."""

    STRIKES = ((EXTRA_EFFECTS, "nuclear_first_strike"),
               (EXTRA_EFFECTS, "nuclear_response_strike"),
               (EXTRA_EFFECTS, "nuclear_response_response_strike"),
               (EFFECTS, "nd_tactical_strike_resolve"))

    @staticmethod
    def branches(body):
        """The strike's random_list branches, keyed by their weight."""
        rl = block(body, "random_list")
        out = {}
        for m in re.finditer(r"(?m)^[ \t]*0 = \{", rl):
            branch = block(rl[m.start():], "0")
            out[re.search(r"modifier = (nuclear_strike_\w+_chance)", branch).group(1)] = branch
        return out

    def test_only_a_hit_marks_the_launcher(self):
        mark = "set_variable = { name = nd_strike_landed value = 1 }"
        for path, name in self.STRIKES:
            branches = self.branches(block(strip_comments(read(path)), name))
            self.assertEqual(set(branches), {"nuclear_strike_success_chance",
                                             "nuclear_strike_fail_chance"}, name)
            self.assertIn(mark, branches["nuclear_strike_success_chance"], name)
            self.assertNotIn("nd_strike_landed", branches["nuclear_strike_fail_chance"], name)

    def test_the_record_spurs_only_after_a_hit(self):
        record = block(strip_comments(read(EFFECTS)), "nd_record_nuclear_use")
        self.assertEqual(record.count("name = nd_proliferation_spur"), 1)
        gate = record[record.index("has_variable = nd_strike_landed"):]
        self.assertLess(gate.index("name = nd_proliferation_spur"),
                        gate.index("remove_variable = nd_strike_landed"))
        # Nothing reads the mark anywhere else, so none can outlive a launch.
        for path in (ROOT / "common").rglob("*.txt"):
            text = strip_comments(read(path))
            if path == EFFECTS:
                text = text.replace(record, "")
            self.assertNotRegex(text, r"(?:has_variable = |var:)nd_strike_landed",
                                path.relative_to(ROOT))

class TestAutomaticRetaliation(unittest.TestCase):
    """Authority 4 (umbrella/recessed/dead-hand spec §3)."""

    def setUp(self):
        self.t = strip_comments(read(TRIGGERS))
        self.ev = strip_comments(read(WEAPON_EVENTS))

    def test_authority_triggers(self):
        for name in ("nd_authority_automatic", "nd_can_adopt_automatic_retaliation", "nd_auto_answers_strike"):
            self.assertRegex(self.t, rf"(?m)^{name} = \{{")
        deleg = block(self.t, "nd_authority_delegated_or_warning")
        self.assertNotIn(">= 2", deleg)
        self.assertIn("var:nd_authority = 2", deleg)
        self.assertIn("var:nd_authority = 3", deleg)
        self.assertIn("mainframe_computers", block(self.t, "nd_can_adopt_automatic_retaliation"))
        self.assertIn(34, gui_ops(read(GUI), "nd_posture_sgui"))
        self.assertIn("localization_key = nd_authority_4", block(strip_comments(read(CUSTOM_LOC)), "nd_authority_name"))

    def test_first_strike_is_answered_automatically_and_only_there(self):
        auto = option_body(self.ev, "nuclear_weapon_events.1.e")
        self.assertIn("nd_auto_answers_strike = { ENEMY = scope:attacking_country }", auto)
        for opt in ("nuclear_weapon_events.1.a", "nuclear_weapon_events.1.b", "nuclear_weapon_events.1.c"):
            self.assertIn("nd_auto_answers_strike = { ENEMY = scope:attacking_country }", option_body(self.ev, opt), opt)
        # .11 (being answered) never fires by itself: no loop between two systems.
        self.assertNotIn("nd_auto_answers_strike", block(self.ev, "nuclear_weapon_events.11"))
        self.assertIn("nd_auto_answered_months", block(self.t, "nd_auto_answers_strike"))
        self.assertIn("nd_auto_answer_record", auto)

    def test_salvo_is_sized_before_anything_flies(self):
        auto = option_body(self.ev, "nuclear_weapon_events.1.e")
        # The stock-sized extra warheads come first, so the preview and the
        # run read the same stock; the first warhead flies last.
        self.assertLess(auto.index("var:nuclear_weapon_stockpile >= 3"), auto.index("position = 0"))

    def test_ready_event_answers_automatically_too(self):
        body = block(self.ev, "nuclear_weapon_events.24")
        # Gated on the answer being permitted, not the bare authority: a system
        # barred by a pledge must leave the ordinary options, not none.
        self.assertIn("nd_auto_answers_strike = { ENEMY = scope:attacking_country }",
                      option_body(body, "nuclear_weapon_events.24.e"))
        for opt in ("nuclear_weapon_events.24.a", "nuclear_weapon_events.24.b", "nuclear_weapon_events.24.c"):
            self.assertIn("NOT = { nd_auto_answers_strike = { ENEMY = scope:attacking_country } }",
                          option_body(body, opt), opt)

    def test_accident_branch_goes_through_the_launch_path(self):
        inc = strip_comments(read(INCIDENT_EVENTS))
        self.assertIn("nd_system_reads_attack = yes", block(inc, "nuclear_incident.30"))
        e = block(strip_comments(read(EFFECTS)), "nd_system_reads_attack")
        self.assertIn("KIND = system", e)
        self.assertIn("nd_authority_automatic = yes", e)
        self.assertIn("nd_roll_launch_hold = yes", e)
        self.assertIn("nd_strike_from_incident_of = { KIND = system }", block(self.t, "nd_strike_from_incident"))

    def test_warnings_route_to_the_government(self):
        warn = block(strip_comments(read(EFFECTS)), "nd_start_unconfirmed_warning")
        self.assertIn("nd_authority_launch_on_warning = yes", warn)
        self.assertNotIn("nd_authority_automatic", warn)


class TestUmbrellaCoverage(unittest.TestCase):
    """An armed overlord's direct subjects are covered as if guaranteed
    (umbrella/recessed/dead-hand spec §1.1–§1.2)."""

    GUARANTEE_READERS = {"nd_has_armed_guarantor_against", "nd_has_ready_guarantor_against", "nd_protects_anyone",
                         "nd_allies_alarmed", "nd_is_guaranteed", "nd_is_guaranteed_by_treaty",
                         "nd_dispute_guarantee_against", "nd_crisis_classify_dispute", "nd_crisis_notify_guarantors",
                         "nd_record_nuclear_use", "nd_guarantee_act_abandon", "nd_covered_country_struck_by",
                         "nd_covered_country_struck", "nd_dispute_peacetime_strike_by",
                         # Dispute 7 reads a guarantee over a neighbor and leaves
                         # umbrellas out on purpose: every armed overlord's
                         # subjects are under one by default (phase 4b, R2).
                         "nd_dispute_deployment_by", "nd_crisis_concede_deployment", "nd_concession_costs_an_alliance"}

    def test_umbrella_triggers(self):
        t = strip_comments(read(TRIGGERS))
        for name in ("nd_umbrella_withdrawn", "nd_under_an_umbrella", "nd_under_umbrella_of",
                     "nd_is_guaranteed_by_treaty", "nd_beneficiary_threatened_by"):
            self.assertRegex(t, rf"(?m)^{name} = \{{")
        self.assertIn("nd_withdraw_umbrella_action", block(t, "nd_umbrella_withdrawn"))
        for name in ("nd_has_armed_guarantor_against", "nd_is_guaranteed", "nd_is_guaranteed_by",
                     "nd_dispute_guarantee_against"):
            self.assertIn("umbrella", block(t, name), name)

    def test_every_guarantee_read_is_a_known_site(self):
        """A new `has_type = nuclear_guarantee` read outside the known sites
        would see treaties but not umbrellas."""
        for path in (TRIGGERS, EFFECTS, CRISIS_EFFECTS):
            text = strip_comments(read(path))
            for m in re.finditer(r"has_type = nuclear_guarantee", text):
                owner = re.findall(r"(?m)^(\w+) = \{", text[:m.start()])[-1]
                self.assertIn(owner, self.GUARANTEE_READERS, f"{path.name}: {owner}")

    def test_umbrella_loops_exist_beside_treaty_loops(self):
        c = strip_comments(read(CRISIS_EFFECTS))
        e = strip_comments(read(EFFECTS))
        for body in (block(c, "nd_crisis_notify_guarantors"), block(e, "nd_record_nuclear_use")):
            self.assertIn("nd_under_an_umbrella = yes", body)
            self.assertIn("nd_is_guaranteed_by_treaty", body)   # asked once, not twice
        self.assertIn("every_direct_subject", block(c, "nd_guarantee_act_abandon"))
        self.assertIn("random_direct_subject", block(c, "nd_crisis_classify_dispute"))

    def test_abandoning_a_subject_costs_liberty_desire(self):
        body = block(strip_comments(read(CRISIS_EFFECTS)), "nd_guarantee_act_abandon")
        visible = body.split("hidden_effect")[0]
        self.assertIn("add_liberty_desire = 10", visible)

    def test_article_refuses_own_subject(self):
        self.assertIn("nd_tt_already_under_umbrella", block(strip_comments(read(ARTICLE)), "possible"))


class TestUmbrellaWithdrawal(unittest.TestCase):
    """Withdrawing a subject's umbrella: a pact with a one-off and a lasting
    liberty-desire cost (umbrella/recessed/dead-hand spec §1.3, §1.6)."""

    def test_action_is_a_liberty_desire_pact(self):
        text = strip_comments(read(UMBRELLA_ACTIONS))
        body = block(text, "nd_withdraw_umbrella_action")
        self.assertIn("overlord", block(body, "groups"))
        self.assertIn("add_liberty_desire = 10", block(body, "accept_effect"))
        self.assertIn("value = -20", block(body, "accept_effect"))
        pact = block(body, "pact")
        self.assertIn("country_liberty_desire_add = 0.10", block(pact, "second_modifier"))
        self.assertIn("is_direct_subject_of = root", block(pact, "requirement_to_maintain"))
        self.assertIn("always = no", block(block(body, "ai"), "will_propose"))
        self.assertTrue(read(UMBRELLA_ACTIONS).startswith("\ufeff") or
                        UMBRELLA_ACTIONS.read_bytes().startswith(b"\xef\xbb\xbf"))

    def test_action_loc(self):
        a = "nd_withdraw_umbrella_action"
        needed = {a, a + "_desc", a + "_action_propose_name", a + "_action_break_name", a + "_pact_desc",
                  a + "_action_notification_name", a + "_action_notification_desc",
                  a + "_action_notification_break_name", a + "_action_notification_break_desc"}
        self.assertFalse(sorted(needed - loc_keys()))

    def test_own_desc_names_no_unbound_country(self):
        # A diplomatic action's own _desc has no TARGET_COUNTRY bound: it
        # renders nullptr every frame (localization_accessor_audit).
        self.assertNotIn("TARGET_COUNTRY", loc_value("nd_withdraw_umbrella_action_desc"))

    def test_pact_leaves_breaking_to_the_engine_default(self):
        # actor_can_break defaults to true; spelled out, the effect/trigger
        # validity audit reads it as an unresolved helper call.
        self.assertNotIn("actor_can_break", strip_comments(read(UMBRELLA_ACTIONS)))

    def test_panel_line(self):
        self.assertIn("nd_umbrella_sgui", read(GUI))
        self.assertIn("is_valid = { always = no }", block(strip_comments(read(SGUIS)), "nd_umbrella_sgui"))
        self.assertRegex(strip_comments(read(VALUES)), r"(?m)^nd_display_umbrella_count = \{")


class TestExtendedDeterrence(unittest.TestCase):
    """A strike on a country we cover licenses our answer under any doctrine,
    and answering pulls us into the war (umbrella/recessed/dead-hand spec §1.5)."""

    def setUp(self):
        self.t = strip_comments(read(TRIGGERS))
        self.c = strip_comments(read(CRISIS_EFFECTS))
        self.ev = strip_comments(read(CRISIS_EVENTS))

    def test_strike_on_covered_country_licenses(self):
        self.assertIn("nd_covered_country_struck_by = { ENEMY = $ENEMY$ }", block(self.t, "nd_was_struck_by"))
        body = block(self.t, "nd_covered_country_struck_by")
        self.assertIn("nd_under_an_umbrella = yes", body)
        self.assertIn("has_type = nuclear_guarantee", body)
        self.assertIn("nd_covered_country_struck = yes", block(self.t, "nd_war_law_exception"))

    def test_retaliate_no_longer_needs_our_doctrine_or_a_prior_war(self):
        trig = block(option_body(self.ev, "nuclear_crisis.20.b"), "trigger")
        self.assertNotIn("nd_doctrine_permits_strike", trig)
        self.assertNotRegex(trig, r"(?m)^\s*has_war_with = scope:nd_guarantee_attacker")
        self.assertIn("scope:nd_guarantee_beneficiary = { has_war_with = scope:nd_guarantee_attacker }", trig)
        self.assertIn("nd_forces_assembled = yes", trig)

    def test_answering_joins_the_war_then_strikes_only_at_war(self):
        self.assertIn("join_war", block(self.c, "nd_guarantor_join_war"))
        for act in ("nd_guarantee_act_honour", "nd_guarantee_act_retaliate"):
            self.assertIn("nd_guarantor_join_war = yes", block(self.c, act), act)
        self.assertIn("id = nuclear_crisis.22", block(self.c, "nd_guarantor_schedule_answer"))
        self.assertNotIn("nd_dispatch_strategic_strike", block(self.c, "nd_guarantee_act_retaliate"))
        hidden = block(self.ev, "nuclear_crisis.22")
        self.assertIn("hidden = yes", hidden)
        self.assertIn("has_war_with = scope:attacking_country", hidden)
        self.assertIn("nuclear_response_strike = yes", hidden)
        self.assertIn("remove_variable = nd_answer_strike_target", hidden)


class TestStruckByNamesTheStriker(unittest.TestCase):
    """A strike's aftermath on one of our states licenses an answer only to
    the country that struck it, or one fighting us beside it (#526). The
    aftermath alone used to count, so a terror detonation, a third country's
    strike or one from an earlier war licensed a cheap "answer" to anyone we
    were at war with."""

    AFTERMATH = re.compile(r"name = (nuclear_strike_aftermath|tactical_nuke_aftermath)\b")

    def setUp(self):
        self.t = strip_comments(read(TRIGGERS))
        self.extra = strip_comments(read(EXTRA_EFFECTS))

    def test_no_bare_aftermath_check(self):
        body = block(self.t, "nd_was_struck_by")
        self.assertIn("save_temporary_scope_as = nd_wsb_self", body)
        states = [block(body[m.start():], "any_scope_state")
                  for m in re.finditer(r"(?m)^[ \t]*any_scope_state = \{", body)]
        self.assertTrue(states)
        for state in states:
            self.assertIn("var:nd_struck_by ?= {", state)
            striker = block(state, "var:nd_struck_by ?")
            self.assertIn("has_war_with = scope:nd_wsb_self", striker)
            war = block(striker, "any_scope_war")
            self.assertIn("is_war_participant = scope:nd_wsb_self", war)
            self.assertIn("is_war_participant = $ENEMY$", war)

    def test_every_detonation_site_names_its_striker(self):
        sites = []
        for folder in ("common", "events"):
            for path in sorted((ROOT / folder).rglob("*.txt")):
                text = strip_comments(read(path))
                sites += [(path, m.group(1)) for m in self.AFTERMATH.finditer(text)]
        # The city strike and the counterforce strike (rework spec §6.2) share
        # the strategic attribution.
        self.assertEqual(sorted(kind for _, kind in sites),
                         ["nuclear_strike_aftermath", "nuclear_strike_aftermath", "tactical_nuke_aftermath"])
        self.assertTrue(all(path == EXTRA_EFFECTS for path, _ in sites))
        for name in ("nuclear_industrial_strike", "nd_counterforce_strike_damage"):
            self.assertIn("name = nuclear_strike_aftermath", block(self.extra, name))
            self.assertIn("nuclear_strike_attribute = yes", block(self.extra, name))
        strategic = block(self.extra, "nuclear_strike_attribute")
        self.assertIn("set_variable = { name = nd_struck_by value = scope:nd_current_strike_launcher "
                      "days = short_modifier_time }", strategic)
        self.assertIn("set_variable = { name = nd_struck_by value = scope:attacking_country "
                      "days = short_modifier_time }", strategic)
        tactical = block(self.extra, "nuclear_tactical_strike")
        self.assertIn("name = tactical_nuke_aftermath", tactical)
        self.assertIn("set_variable = { name = nd_struck_by value = scope:attacking_country "
                      "days = short_modifier_time }", tactical)
        # On the state, not its owner.
        for body in (strategic, tactical):
            self.assertNotIn("nd_struck_by", block(body, "owner"))

    def test_terror_detonation_names_nobody(self):
        loose = strip_comments(read(LOOSE_EFFECTS))
        self.assertIn("nuclear_industrial_strike = yes", loose)
        self.assertNotIn("save_scope_as = attacking_country", loose)
        self.assertNotIn("nd_current_strike_launcher", loose)
        self.assertNotIn("nd_struck_by", loose)

    def test_record_is_the_wars(self):
        cleanup = block(strip_comments(read(EFFECTS)), "nd_country_monthly_cleanup")
        states = block(cleanup, "every_scope_state")
        self.assertIn("has_variable = nd_struck_by", states)
        self.assertIn("NOT = { has_war_with = ROOT }", states)
        self.assertIn("NOT = { nd_in_peacetime_exchange_with = { ENEMY = ROOT } }", states)
        self.assertIn("remove_variable = nd_struck_by", states)


class TestReviewFixesUmbrellaRecessed(unittest.TestCase):
    """Fix pass after the whole-branch review of #455."""

    def setUp(self):
        self.t = strip_comments(read(TRIGGERS))
        self.e = strip_comments(read(EFFECTS))
        self.c = strip_comments(read(CRISIS_EFFECTS))
        self.wev = strip_comments(read(WEAPON_EVENTS))
        self.cev = strip_comments(read(CRISIS_EVENTS))

    def test_honour_keeps_the_ultimatum_for_a_guarantor_already_at_war(self):
        body = block(self.c, "nd_guarantee_act_honour")
        join = body[:body.index("nd_guarantor_join_war = yes")]
        self.assertIn("NOT = { has_war_with = scope:nd_guarantee_attacker }", join)
        self.assertIn("nd_crisis_open", body)

    def test_umbrella_lapses_while_the_subject_faces_its_overlord(self):
        body = block(self.t, "nd_under_an_umbrella")
        self.assertIn("NOT = { has_war_with = scope:", body)
        self.assertIn("NOT = { is_diplomatic_play_enemy_of = scope:", body)

    def test_withdrawal_read_only_from_the_subject_side(self):
        self.assertIn("second_country = { this = scope:", block(self.t, "nd_umbrella_withdrawn"))

    def test_subject_cannot_break_the_withdrawal(self):
        body = block(strip_comments(read(UMBRELLA_ACTIONS)), "nd_withdraw_umbrella_action")
        pact = block(body, "pact")
        self.assertIn("always = no", block(pact, "target_can_break"))
        self.assertIn("is_two_sided_pact = no", pact)
        self.assertIn("is_direct_subject_of = root", block(block(body, "ai"), "will_break"))
        self.assertIn("nd_believed_armed = yes", block(body, "potential"))

    def test_system_launch_is_narrated_by_the_accident_not_a_warning(self):
        body = block(self.e, "nd_system_reads_attack")
        self.assertIn("NARRATE = no", body)
        custom = block(strip_comments(read(CUSTOM_LOC)), "nd_system_outcome")
        for key in ("nd_system_outcome_held", "nd_system_outcome_struck", "nd_system_outcome_recalled"):
            self.assertIn(f"localization_key = {key}", custom)
        self.assertIn("nd_last_launch_kind", custom)

    def test_licence_ends_with_the_war(self):
        body = block(self.e, "nd_country_monthly_cleanup")
        self.assertIn("remove_variable = nuked_by_country", body)
        self.assertIn("has_war_with = ROOT", body)

    def test_one_visible_default_in_every_state(self):
        for opt in ("nuclear_weapon_events.1.a", "nuclear_weapon_events.1.e", "nuclear_weapon_events.1.h",
                    "nuclear_weapon_events.24.a", "nuclear_weapon_events.24.e"):
            self.assertIn("default_option = yes", option_body(self.wev, opt), opt)
        g = option_body(self.wev, "nuclear_weapon_events.1.g")
        self.assertNotIn("default_option", g)
        self.assertIn("nd_authority_automatic = no", g)
        h = option_body(self.wev, "nuclear_weapon_events.1.h")
        self.assertIn("nd_authority_automatic = yes", h)
        self.assertIn("nd_assemble_for_retaliation = { ENEMY = scope:attacking_country }", h)

    def test_war_checks_read_a_saved_scope(self):
        weekly = block(self.e, "nd_weekly_update")
        self.assertNotIn("has_war_with = var:", weekly)
        self.assertIn("has_war_with = scope:nd_ready_enemy", weekly)
        hidden = block(self.cev, "nuclear_crisis.22")
        self.assertNotIn("has_war_with = var:", hidden)
        self.assertIn("has_war_with = scope:attacking_country", hidden)

    def test_a_pending_answer_ends_with_its_war(self):
        weekly = block(self.e, "nd_weekly_update")
        pending = weekly[weekly.index("nd_pending_retaliation"):]
        self.assertRegex(pending, r"NOT = \{ has_war_with = scope:nd_ready_enemy \}\s*NOT = \{ nd_in_peacetime_exchange_with = \{ ENEMY = scope:nd_ready_enemy \} \}\s*\}\s*remove_variable = nd_pending_retaliation")

    def test_assembling_is_not_called_a_stand_down(self):
        custom = block(strip_comments(read(CUSTOM_LOC)), "nd_readiness_moving")
        self.assertIn("localization_key = nd_readiness_moving_1_up", custom)


class TestProtectorsAndProteges(unittest.TestCase):
    """Owner follow-ups on #455: shelving the bomb while protecting others,
    and a protected country that struck first."""

    def setUp(self):
        self.t = strip_comments(read(TRIGGERS))
        self.e = strip_comments(read(EFFECTS))
        self.c = strip_comments(read(CRISIS_EFFECTS))
        self.v = strip_comments(read(VALUES))
        self.cev = strip_comments(read(CRISIS_EVENTS))

    def test_no_concealing_a_launch_the_world_saw(self):
        opt = option_body(strip_comments(read(INCIDENT_EVENTS)), "nuclear_incident.30.e")
        self.assertIn("var:nd_system_reacted = 2", block(opt, "trigger"))

    def test_ai_keeps_its_warheads_mated_while_it_protects_anyone(self):
        self.assertRegex(self.t, r"(?m)^nd_protects_anyone = \{")
        review = block(self.e, "nd_ai_review_posture")
        recessed = review[:review.index("nd_set_readiness_target_0 = yes")]
        self.assertIn("nd_protects_anyone = no", recessed[recessed.rindex("else_if"):])
        monthly = block(self.e, "nd_monthly_update")
        stepout = monthly[monthly.index("var:nd_readiness_target = 0"):]
        self.assertIn("nd_protects_anyone = yes", stepout[:stepout.index("nd_set_readiness_target_1 = yes")])

    def test_allies_are_alarmed_when_readiness_reaches_recessed(self):
        weekly = block(self.e, "nd_weekly_update")
        self.assertIn("id = nuclear_crisis.23", weekly)
        self.assertIn("nd_allies_alarmed = yes", option_body(self.cev, "nuclear_crisis.23.a"))
        costs = block(self.c, "nd_allies_alarmed")
        for bit in ("AMOUNT = -5", "value = -10", "add_liberty_desire = 5"):
            self.assertIn(bit, costs)
        self.assertIn("nd_tt_recessed_alarms_allies", block(self.e, "nd_set_readiness_target_0"))

    def test_a_recessed_protector_protects_half_as_credibly(self):
        body = block(self.v, "nd_yp_protector_value")
        self.assertIn("nd_has_ready_guarantor_against = { AGAINST = scope:nd_issuer }", body)
        self.assertIn("subtract = 10", body)
        self.assertIn("nd_forces_assembled = yes", block(self.t, "nd_has_ready_guarantor_against"))

    def test_a_protege_that_struck_first_gets_its_own_event(self):
        hears = block(self.c, "nd_guarantor_hears_of_strike")
        self.assertIn("nd_was_struck_by = { ENEMY = scope:nd_guarantee_beneficiary }", hears)
        self.assertIn("id = nuclear_crisis.24", hears)
        self.assertIn("id = nuclear_crisis.20", hears)
        record = block(self.e, "nd_record_nuclear_use")
        # Treaty, umbrella and co-belligerent (rework spec §8.3) branches.
        self.assertEqual(record.count("nd_guarantor_hears_of_strike = yes"), 3)
        self.assertNotIn("id = nuclear_crisis.20", record)
        self.assertIn("nd_guarantee_act_honour = yes", option_body(self.cev, "nuclear_crisis.24.a"))
        self.assertIn("nd_guarantee_act_retaliate = yes", option_body(self.cev, "nuclear_crisis.24.b"))
        self.assertIn("nd_guarantee_act_decline = yes", option_body(self.cev, "nuclear_crisis.24.c"))
        for opt in ("nuclear_crisis.24.a", "nuclear_crisis.24.b"):
            self.assertIn("change_infamy = 5", option_body(self.cev, opt), opt)

    def test_declining_a_first_striker_is_not_abandonment(self):
        decline = block(self.c, "nd_guarantee_act_decline")
        self.assertNotIn("nd_guarantee_abandoned", decline)
        self.assertNotIn("nd_change_credibility", decline)
        self.assertIn("value = -10", decline)
        self.assertIn("add_liberty_desire = 5", decline)
        self.assertIn("var:nd_guarantee_answer = 2", block(self.cev, "nuclear_crisis.21"))


class TestCustody(unittest.TestCase):
    """Nuclear custody (nuclear_crisis_design.md §0.10, spec
    docs/superpowers/archive/specs/2026-09-26-nuclear-custody-design.md): the
    settlement is one idempotent helper, so every hook where an arsenal's
    owner can end must call it, and the invariants that keep the civil-war
    merge from counting a transfer twice live in a few specific blocks."""

    def setUp(self):
        self.e = strip_comments(read(EFFECTS))
        self.ce = strip_comments(read(CUSTODY_EFFECTS))
        self.t = strip_comments(read(TRIGGERS))
        self.ct = strip_comments(read(CUSTODY_TRIGGERS))
        self.cw = strip_comments(read(CIVIL_WAR_ON_ACTIONS))
        self.coa = strip_comments(read(CUSTODY_ON_ACTIONS))
        self.ev = strip_comments(read(CUSTODY_EVENTS))
        self.je = strip_comments(read(JE))

    def test_every_hook_settles(self):
        self.assertIn("nd_custody_reconcile = yes", block(self.coa, "nd_custody_monthly_on_action"))
        self.assertIn("nd_custody_reconcile_soon = yes", block(self.coa, "nd_custody_on_wargoal_enforced"))
        self.assertIn("nd_custody_reconcile_soon = yes", block(self.coa, "nd_custody_on_country_formed"))
        self.assertIn("nd_custody_reconcile = yes", block(self.cw, "te_civil_war_on_secession_end"))
        self.assertIn("nd_custody_on_civil_war_won = yes", block(self.cw, "te_civil_war_on_won"))
        self.assertIn("nd_custody_reconcile = yes", block(self.ce, "nd_custody_on_civil_war_won"))
        self.assertIn("nd_custody_reconcile = yes", block(self.ev, "nuclear_custody.9"))
        self.assertIn("id = nuclear_custody.9", block(self.ce, "nd_custody_reconcile_soon"))
        # Every hook the on_actions file declares is actually declared.
        for hook, handler in (("on_monthly_pulse", "nd_custody_monthly_on_action"),
                              ("on_wargoal_enforced", "nd_custody_on_wargoal_enforced"),
                              ("on_country_formed", "nd_custody_on_country_formed")):
            self.assertIn(handler, block(self.coa, hook))
        for hook, handler in (("on_revolution_start", "te_civil_war_on_start"),
                              ("on_secession_start", "te_civil_war_on_start"),
                              ("on_revolution_end", "te_civil_war_on_revolution_end"),
                              ("on_secession_end", "te_civil_war_on_secession_end"),
                              ("on_civil_war_won", "te_civil_war_on_won")):
            self.assertIn(handler, block(self.cw, hook))

    def test_every_mod_annex_schedules_the_settlement(self):
        """An `annex` the mod scripts itself must settle an armed victim's
        arsenal a day later (the monthly pass would, up to a month late)."""
        for path in list((ROOT / "common").rglob("*.txt")) + list((ROOT / "events").glob("*.txt")):
            lines = strip_comments(read(path)).splitlines()
            for i, line in enumerate(lines):
                if re.match(r"\s*annex\s*=\s*\S", line):
                    after = "\n".join(lines[i + 1:i + 4])
                    self.assertIn("nd_custody_reconcile_soon = yes", after,
                                  f"{path.relative_to(ROOT)}:{i + 1} annexes without scheduling the settlement")

    def test_the_price_of_striking_our_own_side_is_shown(self):
        record = block(self.e, "nd_record_nuclear_use")
        hidden = block(record, "hidden_effect")
        self.assertIn("nd_custody_struck_own_people = yes", record)
        self.assertNotIn("nd_custody_struck_own_people", hidden)
        self.assertIn("nd_is_civil_war_counterpart = { ENEMY = $VICTIM$ }", record)
        cost = block(self.ce, "nd_custody_struck_own_people")
        self.assertIn("name = nd_struck_own_people", cost)
        self.assertIn("is_decaying = yes", cost)
        self.assertIn("value = nd_own_strike_radicals", cost)
        self.assertIn("country_legitimacy_base_add = -50",
                      block(strip_comments(read(MODIFIERS)), "nd_struck_own_people"))

    def test_the_ai_spares_its_own_side(self):
        gate = block(self.t, "nd_ai_nuclear_use_justified")
        self.assertIn("nd_is_civil_war_counterpart = { ENEMY = $ENEMY$ }", gate)
        self.assertIn("nd_ai_would_strike_own_people = yes", gate)
        # The gate sits before the retaliation clause, so it binds it too.
        self.assertLess(gate.index("nd_is_civil_war_counterpart"), gate.index("nd_was_struck_by"))

    def test_the_withdrawn_lock_is_read_everywhere_readiness_rises(self):
        for name in ("nd_weekly_update", "nd_monthly_update", "nd_ai_review_posture",
                     "nd_assemble_for_retaliation"):
            self.assertIn("nd_readiness_withdrawn", block(self.e, name), name)
        self.assertIn("nd_readiness_withdrawn", block(self.t, "nd_can_set_readiness"))
        self.assertIn("remove_variable = nd_cw_withdrawn", block(self.e, "nd_country_monthly_cleanup"))

    def test_a_civil_war_is_read_from_the_rebel_country(self):
        """any_civil_war iterates the civil wars still brewing (a movement's
        progress), not one that has broken out: the lock read it and lifted
        the month after the outbreak. Every "is our civil war still on" test
        goes through nd_in_civil_war instead."""
        live = block(self.ct, "nd_in_civil_war")
        self.assertIn("civil_war_origin_country ?= scope:nd_icw_self", live)
        self.assertIn("is_revolutionary = yes", live)
        self.assertIn("is_secessionist = yes", live)
        cleanup = block(self.e, "nd_country_monthly_cleanup")
        self.assertIn("nd_in_civil_war = no", cleanup)
        for path in (EFFECTS, CUSTODY_EFFECTS, CUSTODY_TRIGGERS, TRIGGERS, CUSTODY_EVENTS):
            self.assertNotIn("any_civil_war", strip_comments(read(path)), path.name)

    def test_both_sides_of_a_civil_war_hold_their_own_arsenal(self):
        start = block(self.ce, "nd_custody_on_civil_war_start")
        rebel = block(start, "scope:target")
        self.assertIn("name = nuclear_weapon_stockpile value = 0", rebel)
        self.assertIn("nd_ledger_refresh = yes", rebel)
        self.assertIn("name = nd_cw_origin_record", rebel)
        self.assertIn("nd_ledger_refresh = yes", start.replace(rebel, ""))
        self.assertIn("id = nuclear_custody.1", start)
        # An origin that gets its first record mid-war seeds its rebels then.
        ensure = block(self.ce, "nd_ledger_ensure")
        seed = block(ensure, "every_country")
        self.assertIn("civil_war_origin_country ?= scope:nd_ledger_parent", seed)
        self.assertIn("name = nuclear_weapon_stockpile value = 0", seed)
        self.assertIn("nd_ledger_create = yes", seed)

    def test_the_new_regime_reads_the_record_before_the_settlement(self):
        won = block(self.ce, "nd_custody_on_civil_war_won")
        self.assertLess(won.index("nd_custody_new_regime = yes"), won.index("nd_custody_reconcile = yes"))
        regime = block(self.ce, "nd_custody_new_regime")
        self.assertIn("var:nd_cw_origin_record", regime)
        self.assertNotIn("te_cw_loser", regime)  # never the dead loser itself
        self.assertIn("name = nd_credibility value = 50", regime)
        self.assertIn("nd_custody_restore_progress = yes", self.je)

    def test_split_tooltips_are_literal_and_localized(self):
        keys = set(re.findall(r"TT = (nd_\w+)", self.ce + self.ev))
        self.assertEqual(keys, {"nd_tt_cw_split_hold", "nd_tt_cw_split_pull",
                                "nd_tt_cw_dismantle", "nd_tt_cw_deny_rest",
                                "nd_tt_cw_deny_supervised",
                                "nd_tt_cwr_back_gov", "nd_tt_cwr_back_rebels"})
        missing = keys - loc_keys()
        self.assertFalse(missing, missing)
        # Every figure the roll writes is cleared again, for both modes.
        roll = block(self.ce, "nd_cw_roll_one")
        clear = block(self.ce, "nd_cw_clear_roll")
        for part in ("seized", "lost", "taken", "kept"):
            self.assertIn(f"name = nd_cw_$MODE$_{part}", roll, part)
            for mode in ("hold", "pull"):
                self.assertIn(f"remove_variable = nd_cw_{mode}_{part}", clear, (mode, part))

    def test_outbreak_options(self):
        self.assertIn("nd_cw_apply_split = { MODE = hold TT = nd_tt_cw_split_hold }",
                      option_body(self.ev, "nuclear_custody.1.a"))
        self.assertIn("nd_cw_pull_back = yes", option_body(self.ev, "nuclear_custody.1.b"))
        self.assertIn("nd_cw_dismantle = yes", option_body(self.ev, "nuclear_custody.1.c"))
        self.assertIn("default_option = yes", option_body(self.ev, "nuclear_custody.1.a"))
        self.assertIn("nd_cw_roll_split = yes", block(self.ev, "nuclear_custody.1"))


class TestCustodyLosingAndWatching(unittest.TestCase):
    """Step 3's rest (spec docs/superpowers/archive/specs/2026-09-26-nuclear-loose-
    warheads-design.md §1): "Deny Them the Bomb" for a government losing a
    revolution, the watching powers' event, and secured custody, which halves
    what goes missing whenever warheads change hands."""

    def setUp(self):
        self.e = strip_comments(read(EFFECTS))
        self.ce = strip_comments(read(CUSTODY_EFFECTS))
        self.ct = strip_comments(read(CUSTODY_TRIGGERS))
        self.cv = strip_comments(read(CUSTODY_VALUES))
        self.ev = strip_comments(read(CUSTODY_EVENTS))

    def test_deny_is_asked_of_a_losing_revolution_only(self):
        self.assertIn("nd_cw_monthly_check = yes", block(self.e, "nd_country_monthly_cleanup"))
        check = block(self.ce, "nd_cw_monthly_check")
        ask = block(check, "random_country")
        self.assertIn("is_revolutionary = yes", ask)
        self.assertNotIn("is_secessionist", ask)
        self.assertIn("nd_is_losing_war_to = { ENEMY = scope:nd_cw_rebel }", check)
        self.assertIn("id = nuclear_custody.5", check)
        # Forgotten, with the custodian, once no civil war is left.
        self.assertIn("nd_in_civil_war = no", check)
        self.assertIn("remove_variable = nd_cw_deny_asked", check)
        self.assertIn("remove_variable = nd_cw_custodian", check)

    def test_deny_options(self):
        self.assertIn("nd_cw_deny_roll = yes", block(self.ev, "nuclear_custody.5"))
        self.assertIn("nd_cw_deny_dismantle = yes", option_body(self.ev, "nuclear_custody.5.a"))
        supervised = option_body(self.ev, "nuclear_custody.5.b")
        self.assertIn("nd_cw_custodian_can_supervise = yes", supervised)
        self.assertIn("nd_cw_deny_supervised = yes", supervised)
        keep = option_body(self.ev, "nuclear_custody.5.c")
        self.assertIn("default_option = yes", keep)
        self.assertIn("nd_tt_cw_deny_keep", keep)
        # The hasty dismantling loses what the roll said, into the pool.
        hurried = block(self.ce, "nd_cw_deny_dismantle")
        self.assertIn("nd_custody_lose_warheads = { AMOUNT = var:nd_cw_deny_lost }", hurried)
        self.assertIn("nd_cw_dismantle_as = { TT = nd_tt_cw_deny_rest }", hurried)
        self.assertNotIn("nd_custody_lose_warheads", block(self.ce, "nd_cw_deny_supervised"))
        self.assertIn("multiply = nd_cw_outbreak_loss_rate", block(self.ce, "nd_cw_deny_roll"))

    def test_the_world_hears_of_an_armed_civil_war(self):
        start = block(self.ce, "nd_custody_on_civil_war_start")
        self.assertIn("nd_cw_notify_world = yes", start)
        notify = block(self.ce, "nd_cw_notify_world")
        self.assertIn("nd_cw_would_watch = {", notify)
        self.assertIn("id = nuclear_custody.6 days = 7", notify)
        # Stored on the observer for the delayed event, not passed as scopes.
        self.assertIn("name = nd_cwr_origin", notify)
        self.assertIn("name = nd_cwr_rebel", notify)
        self.assertIn("nd_cwr_pair_at_war = yes", block(self.ev, "nuclear_custody.6"))
        self.assertIn("SIDE = gov OTHER = reb", option_body(self.ev, "nuclear_custody.6.a"))
        self.assertIn("SIDE = reb OTHER = gov", option_body(self.ev, "nuclear_custody.6.b"))
        self.assertIn("nd_cwr_offer_custody = yes", option_body(self.ev, "nuclear_custody.6.c"))
        self.assertIn("default_option = yes", option_body(self.ev, "nuclear_custody.6.e"))
        self.assertIn("id = nuclear_custody.7", block(self.ce, "nd_cwr_offer_custody"))
        self.assertIn("nd_cw_accept_custodian = yes", option_body(self.ev, "nuclear_custody.7.a"))
        self.assertIn("id = nuclear_custody.8", block(self.ce, "nd_cw_answer_offer"))

    def test_secured_custody_halves_both_loss_rates_after_the_clamp(self):
        for name, test in (("nd_custody_loss_rate", "nd_custody_is_secured = yes"),
                           ("nd_ar_loss_rate", "var:nd_ar_secured = 1")):
            body = block(self.cv, name)
            self.assertIn(test, body, name)
            self.assertLess(body.index("max = 0.1"), body.index(test), name)
        self.assertIn("nd_custody_is_secured = yes", block(self.ce, "nd_ledger_refresh"))
        self.assertIn("name = nd_ar_secured value = 1", block(self.ce, "nd_ledger_refresh"))
        self.assertIn("var:nd_cw_custodian", block(self.ct, "nd_custody_is_secured"))


class TestBudapestPath(unittest.TestCase):
    """Step 4 (spec §2): a secession that won holding warheads is pressed by
    the great powers to trade them for guarantees, with the existing
    nuclear_disarmament and nuclear_guarantee articles."""

    def setUp(self):
        self.ce = strip_comments(read(CUSTODY_EFFECTS))
        self.ct = strip_comments(read(CUSTODY_TRIGGERS))
        self.ev = strip_comments(read(CUSTODY_EVENTS))
        self.cw = strip_comments(read(CIVIL_WAR_ON_ACTIONS))

    def test_a_won_secession_opens_the_path(self):
        self.assertIn("nd_bp_open = yes", block(self.cw, "te_civil_war_on_secession_end"))
        opened = block(self.ce, "nd_bp_open")
        self.assertIn("is_country_alive = yes", opened)
        self.assertIn("nd_is_armed = yes", opened)
        self.assertIn("id = nuclear_custody.10 days = 7", opened)
        self.assertIn("country_rank >= rank_value:great_power", block(self.ct, "nd_bp_would_hear"))

    def test_the_first_to_press_schedules_one_offer(self):
        press = block(self.ce, "nd_bp_press")
        self.assertIn("id = nuclear_custody.11 days = 30", press)
        self.assertIn("add_to_variable_list = { name = nd_bp_guarantors target = ROOT }", press)
        self.assertIn("nd_bp_press = yes", option_body(self.ev, "nuclear_custody.10.a"))

    def test_treaty_effects_match_their_triggers(self):
        """can_create_treaty must describe the very treaty create_treaty makes."""
        for name in ("lead", "guarantee"):
            trig = block(self.ct, f"nd_bp_can_treaty_{name}")
            eff = block(self.ce, f"nd_bp_treaty_{name}")
            norm = lambda t: re.sub(r"\s+", " ", t).strip()
            self.assertEqual(norm(block(trig, "can_create_treaty")), norm(block(eff, "create_treaty")), name)
        lead = block(self.ce, "nd_bp_treaty_lead")
        self.assertIn("article = nuclear_disarmament", lead)
        self.assertIn("article = nuclear_guarantee", lead)
        self.assertIn("is_draft = no", lead)

    def test_accept_creates_the_treaties_before_disarming(self):
        accept = block(self.ce, "nd_bp_accept")
        self.assertLess(accept.index("nd_bp_treaty_lead ="), accept.index("name = nuclear_weapon_stockpile value = 0"))
        self.assertIn("nd_bp_can_treaty_guarantee = { GUARANTOR = scope:nd_bp_lead", accept)
        self.assertIn("nd_bp_answer = { ANSWER = 1 }", accept)
        refuse = block(self.ce, "nd_bp_refuse")
        self.assertIn("name = nd_bp_refused", refuse)
        self.assertIn("nd_bp_answer = { ANSWER = 2 }", refuse)
        self.assertIn("nd_bp_accept = yes", option_body(self.ev, "nuclear_custody.11.a"))
        self.assertIn("nd_bp_refuse = yes", option_body(self.ev, "nuclear_custody.11.b"))
        articles = strip_comments(read(ROOT / "common/treaty_articles/extra_treaty_articles.txt"))
        self.assertIn("has_variable = nd_bp_refused", block(articles, "nuclear_disarmament"))


def enclosing_block(text, needle):
    """The `{ ... }` body of the innermost block around `needle`'s line: for a
    `limit = { … }` line, the `if` it gates."""
    start = text.rfind("\n", 0, text.index(needle)) + 1
    depth, i = 1, start
    while depth:
        i -= 1
        depth += text[i] == "}"
        depth -= text[i] == "{"
    depth, j = 1, i + 1
    while depth:
        depth += text[j] == "{"
        depth -= text[j] == "}"
        j += 1
    return text[i + 1:j - 1]


class TestNuclearArticleAIDemands(unittest.TestCase):
    """The AI demands a freeze or a disarmament only of a country the article
    would stop. An AI India pressed a freeze as a war goal on insignificant
    Mekong, which had the nuclear_weapons tech and no standing to build
    (2026-10-16)."""

    ARTICLES = {
        "nuclear_program_pause": ("nuclear_program_freeze_matters", "nuclear_program_pause_ai_demand_weight"),
        "nuclear_disarmament": ("nuclear_disarmament_matters", "nuclear_disarmament_ai_demand_weight"),
    }

    def setUp(self):
        self.articles = strip_comments(read(ROOT / "common/treaty_articles/extra_treaty_articles.txt"))
        self.values = strip_comments(read(ROOT / "common/script_values/extra_script_values.txt"))
        self.triggers = strip_comments(read(NUKE_TRIGGERS))

    def test_a_freeze_matters_only_with_a_programme_or_major_rank(self):
        freeze = block(self.triggers, "nuclear_program_freeze_matters")
        self.assertIn("nuclear_program_has_programme = yes", freeze)
        self.assertIn("country_rank >= rank_value:major_power", freeze)
        self.assertNotIn("minor_power", freeze)
        disarm = block(self.triggers, "nuclear_disarmament_matters")
        self.assertIn("nd_believed_armed = yes", disarm)
        self.assertIn("nuclear_program_freeze_matters = yes", disarm)

    def test_both_demand_fields_read_the_weight(self):
        for article, (_, weight) in self.ARTICLES.items():
            ai = block(block(self.articles, article), "ai")
            for field in ("proposal_weight", "wargoal_score_multiplier"):
                self.assertIn(f"{field} = {{ value = {weight} }}", ai, f"{article} {field}")

    def test_the_weight_is_zero_unless_the_article_matters(self):
        for article, (matters, weight) in self.ARTICLES.items():
            body = block(self.values, weight)
            self.assertTrue(body.strip().startswith("value = 0"), weight)
            # The last branch, the weakest positive one, is the matters gate,
            # and there is no bare `else`: anything that fails it keeps the 0.
            last = body[body.rindex("else_if = {"):]
            self.assertIn(f"limit = {{ scope:source_country = {{ {matters} = yes }} }}", last, weight)
            self.assertNotIn("else =", body, weight)

    def test_requester_interest_counts_only_when_the_article_matters(self):
        for article, (matters, _) in self.ARTICLES.items():
            accept = block(block(self.articles, article), "inherent_accept_score")
            # The requester's branch. (nuclear_disarmament's bonus against a
            # Budapest refuser sits after it, and the refuser keeps its warheads,
            # so the world believes it armed: disarming it matters.)
            requester = enclosing_block(accept, "limit = { scope:target_country = this }")
            gated = enclosing_block(requester, f"scope:source_country = {{ {matters} = yes }}")
            for desc in ("AI_IS_RIVAL", "AI_HOSTILE_ATTITUDE", "AI_BELLIGERENT_ATTITUDE",
                         "AI_ANTAGONISTIC_ATTITUDE", "AI_WARY_ATTITUDE"):
                self.assertEqual(requester.count(f'"{desc}"'), 1, f"{article} {desc}")
                self.assertEqual(gated.count(f'"{desc}"'), 1, f"{article} {desc}")
            self.assertNotIn('"AI_IS_ALLY"', gated, article)
            self.assertIn('"AI_IS_ALLY"', requester, article)

    def test_aid_is_offered_only_to_a_country_with_the_tech(self):
        ai = block(block(self.articles, "nuclear_program_aid"), "ai")
        self.assertIn("proposal_weight = { value = nuclear_program_aid_ai_offer_weight }", ai)
        self.assertIn("scope:target_country = { has_technology_researched = nuclear_weapons }",
                      block(self.values, "nuclear_program_aid_ai_offer_weight"))


class TestLooseWarheads(unittest.TestCase):
    """Step 5 (spec §3): the pool's plots, the attribution roll that keeps the
    truth apart from what the victim learns, and the reckoning."""

    def setUp(self):
        self.le = strip_comments(read(LOOSE_EFFECTS))
        self.lt = strip_comments(read(LOOSE_TRIGGERS))
        self.lv = strip_comments(read(LOOSE_VALUES))
        self.lev = strip_comments(read(LOOSE_EVENTS))
        self.ct = strip_comments(read(CUSTODY_TRIGGERS))

    def test_the_plot_draws_from_the_terror_pool(self):
        pool = block(strip_comments(read(SOCIAL_TENSIONS_ON_ACTIONS)), "random_events")
        self.assertRegex(pool, r"(?m)^\s*\d+ = nuclear_loose\.1\s*$")
        self.assertIn("nd_loose_plot_possible = yes", block(self.lev, "nuclear_loose.1"))
        possible = block(self.lt, "nd_loose_plot_possible")
        for gate in ("has_technology_researched = terrorism_and_anti_terrorism",
                     "global_var:nd_loose_warheads > 0",
                     "NOT = { has_global_variable = nd_loose_plot_cooldown }"):
            self.assertIn(gate, possible)

    def test_cooldown_only_once_a_device_exists(self):
        self.assertNotIn("nd_loose_plot_cooldown", block(self.le, "nd_loose_plot"))
        self.assertIn("name = nd_loose_plot_cooldown", block(self.le, "nd_loose_surface"))

    def test_a_line_must_have_a_live_owner_and_not_be_the_victims(self):
        live = block(self.lt, "nd_loose_line_live")
        self.assertIn("is_country_alive = yes", live)
        self.assertIn("NOT = { var:nd_ar_owner ?= $VICTIM$ }", block(self.lt, "nd_loose_line_usable"))
        self.assertIn("nd_loose_line_usable = { VICTIM = scope:nd_loose_victim }", block(self.le, "nd_loose_plot"))

    def test_the_warhead_leaves_the_pool_whatever_happens(self):
        surface = block(self.le, "nd_loose_surface")
        seized_branch = surface.index("var:nd_loose_seized = 1 }")
        self.assertLess(surface.index("nd_loose_pool_take = { AMOUNT = 1 }"), seized_branch)
        self.assertLess(surface.index("name = nd_ar_loose subtract = 1"), seized_branch)
        # The candidates are counted before this line's count falls.
        self.assertLess(surface.index("name = nd_loose_candidates add = 1"),
                        surface.index("name = nd_ar_loose subtract = 1"))
        # A terror device has no attacker to answer.
        self.assertNotIn("attacking_country", surface)
        self.assertIn("nuclear_industrial_strike = yes", surface)
        self.assertIn("id = nuclear_loose.4 days = 30", surface)

    def test_attribution_has_three_results_and_the_victims_options_follow_them(self):
        attribute = block(self.le, "nd_loose_attribute")
        for n in (1, 2, 3):
            self.assertIn(f"name = nd_loose_attribution value = {n}", attribute)
        self.assertIn("chance = nd_loose_confirm_chance", attribute)
        self.assertIn("chance = nd_loose_shortlist_share", attribute)
        for part in ("nd_loose_expertise", "nd_loose_network_part", "has_modifier = nuclear_power",
                     "var:nd_loose_candidates", "var:nd_loose_seized"):
            self.assertIn(part, block(self.lv, "nd_loose_confirm_chance"), part)
        self.assertIn("max = 90", block(self.lv, "nd_loose_confirm_chance"))
        self.assertIn("nd_loose_origin_answerable = yes", option_body(self.lev, "nuclear_loose.4.a"))
        for opt in ("nuclear_loose.4.b", "nuclear_loose.4.c"):
            self.assertIn("nd_loose_attributed = { RESULT = 2 }", option_body(self.lev, opt), opt)
        self.assertIn("nd_loose_attributed = { RESULT = 3 }", option_body(self.lev, "nuclear_loose.4.e"))
        self.assertIn("default_option = yes", option_body(self.lev, "nuclear_loose.4.g"))
        # An AI names suspects in public only under an aggressive ruler.
        name_all = option_body(self.lev, "nuclear_loose.4.b")
        self.assertIn("base = 0", name_all)
        self.assertIn("ruler_is_aggressive = yes", name_all)

    def test_the_reckoning(self):
        send = block(self.le, "nd_loose_send_demand")
        self.assertIn("value = nd_loose_compensation_value", send)
        self.assertIn("id = nuclear_loose.6", send)
        self.assertIn("nd_loose_demand_is_full = yes", option_body(self.lev, "nuclear_loose.6.a"))
        self.assertIn("nd_loose_pay = yes", option_body(self.lev, "nuclear_loose.6.a"))
        self.assertIn("nd_loose_open_to_inspection = yes", option_body(self.lev, "nuclear_loose.6.b"))
        self.assertIn("nd_loose_deny = yes", option_body(self.lev, "nuclear_loose.6.c"))
        # Inspection secures custody; a search can find a warhead.
        self.assertIn("has_variable = nd_loose_inspected", block(self.ct, "nd_custody_is_secured"))
        inspect = block(self.le, "nd_loose_open_to_inspection")
        self.assertIn("name = nd_loose_inspected", inspect)
        self.assertIn("nd_loose_recover_from_line = { HOW = 1 }", inspect)
        self.assertIn("country_legitimacy_base_add = -5",
                      block(strip_comments(read(MODIFIERS)), "nd_loose_inspections"))

    def test_recovery_destroys_the_warhead(self):
        recover = block(self.le, "nd_loose_recover_from_line")
        self.assertIn("name = nd_ar_loose subtract = 1", recover)
        self.assertIn("nd_loose_pool_take = { AMOUNT = 1 }", recover)
        self.assertNotIn("nuclear_weapon_stockpile", recover)

    def test_panel_row(self):
        gui = read(GUI)
        self.assertIn("GetScriptedGui('nd_loose_sgui')", gui)
        self.assertIn('text = "nd_w_loose_value"', gui)
        self.assertIn("nd_loose_has_line = yes", block(strip_comments(read(SGUIS)), "nd_loose_sgui"))


class TestLooseRecovery(unittest.TestCase):
    """Step 5's recovery (spec §3.5): a covert operation, a treaty article and
    inspection each find warheads unaccounted for and take them out of the
    pool; the article and inspection also secure custody."""

    def setUp(self):
        self.le = strip_comments(read(LOOSE_EFFECTS))
        self.lt = strip_comments(read(LOOSE_TRIGGERS))
        self.ct = strip_comments(read(CUSTODY_TRIGGERS))

    def test_covert_operation_finds_warheads_once_established(self):
        effects = strip_comments(read(ROOT / "common/scripted_effects/covert_warfare_effects.txt"))
        phase = block(effects, "covert_ops_apply_all_phase_effects")
        i = phase.index("has_tag = iw_op_secure_material")
        search = phase[i: phase.index("covert_refresh_priority_cost", i)]
        self.assertIn("covert_op_is_established = yes", search)
        self.assertIn("chance = covert_secure_material_chance", search)
        self.assertIn("nd_loose_recover_from_line = { HOW = 2 }", search)
        # The operator hears; the target is never told.
        self.assertIn("nd_loose_tell_recovery = { WHO = ROOT HOW = 2 }", search)
        action = block(strip_comments(read(ROOT / "common/diplomatic_actions/covert_operations.txt")),
                       "covert_secure_material_action")
        self.assertIn("has_game_rule = nuclear_weapons_enabled", action)
        # Ends by itself when nothing is left to find.
        self.assertIn("nd_loose_has_line = yes", block(action, "pact"))

    def test_article_secures_custody_and_searches(self):
        article = strip_comments(read(ROOT / "common/treaty_articles/116_nuclear_security_assistance.txt"))
        self.assertIn("maintenance_paid_by = source_country", article)
        self.assertIn("country_treaty_leverage_generation_add", block(article, "target_modifier"))
        self.assertIn("has_type = nuclear_security_assistance", block(self.lt, "nd_has_security_assistance"))
        self.assertIn("nd_has_security_assistance = yes", block(self.ct, "nd_custody_is_secured"))
        monthly = block(self.le, "nd_loose_monthly")
        self.assertIn("nd_has_security_assistance = yes", monthly)
        self.assertIn("nd_loose_recover_from_line = { HOW = 3 }", monthly)
        self.assertIn("nd_loose_monthly = yes", block(strip_comments(read(EFFECTS)), "nd_country_monthly_cleanup"))

    def test_un_convention_secures_custody_and_searches(self):
        self.assertIn("has_modifier = un_physical_protection_modifier", block(self.ct, "nd_custody_is_secured"))
        monthly = block(self.le, "nd_loose_monthly")
        self.assertIn("chance = nd_loose_convention_chance", monthly)
        self.assertIn("nd_loose_recover_from_line = { HOW = 4 }", monthly)
        # Raised only once warheads have gone loose, and kept on the table
        # after the pool drains (a permanent world flag).
        docket = strip_comments(read(ROOT / "common/scripted_triggers/un_docket_triggers.txt"))
        opened = block(docket, "un_docket_topic_open_physical_protection")
        self.assertIn("has_game_rule = nuclear_weapons_enabled", opened)
        self.assertIn("has_global_variable = nd_loose_device_surfaced", opened)
        self.assertIn("name = nd_loose_device_surfaced", block(self.le, "nd_loose_surface"))
        self.assertIn("set_global_variable = un_agency_cppnm", strip_comments(read(ROOT / "events/un_vote_events.txt")))


class TestReviewFixes474(unittest.TestCase):
    """Findings of the independent review of #474."""

    def setUp(self):
        self.ce = strip_comments(read(CUSTODY_EFFECTS))
        self.ev = strip_comments(read(CUSTODY_EVENTS))
        self.le = strip_comments(read(LOOSE_EFFECTS))

    def test_lost_warheads_reach_the_origins_line(self):
        """A caller passes AMOUNT = var:<its own variable>; read inside the
        ledger record that named the record's (absent) variable, so the line
        gained nothing while the world count gained the lot."""
        lose = block(self.ce, "nd_custody_lose_warheads")
        record = lose[lose.index("var:nd_arsenal_record ?="):]
        self.assertNotIn("$AMOUNT$", record)
        self.assertIn("scope:nd_clw_holder.var:nd_clw_amount", record)
        self.assertIn("name = nd_clw_amount value = $AMOUNT$", lose)
        # No other effect adds a parameter to a record's count from inside it.
        for name in ("nd_custody_lose_warheads", "nd_loose_recover_from_line"):
            body = block(self.ce if name.startswith("nd_custody") else self.le, name)
            self.assertNotRegex(body, r"nd_ar_loose (?:add|subtract) = \$")

    def test_budapest_lead_can_sign_and_signs_last(self):
        prepare = block(self.ce, "nd_bp_prepare_offer")
        self.assertIn("nd_bp_can_treaty_guarantee = { GUARANTOR = this STATE = ROOT }",
                      block(prepare, "ordered_in_list"))
        accept = block(self.ce, "nd_bp_accept")
        self.assertLess(accept.index("save_scope_as = nd_bp_other"),
                        accept.index("nd_bp_treaty_lead = { GUARANTOR = scope:nd_bp_lead"))
        offer = block(self.ev, "nuclear_custody.11")
        gate = offer[offer.index("\n\ttrigger = {"): offer.index("\n\timmediate = {")]
        self.assertIn("nd_bp_can_treaty_guarantee = { GUARANTOR = this STATE = ROOT }", gate)
        self.assertIn("exists = scope:nd_bp_lead", option_body(self.ev, "nuclear_custody.11.a"))
        answer = block(self.ce, "nd_bp_answer")
        self.assertIn("name = nd_bp_answer value = 3", answer)
        self.assertIn("name = nd_bp_answered", answer)
        self.assertIn("has_variable = nd_bp_answered", block(self.ce, "nd_bp_press"))

    def test_a_blamed_rival_is_told(self):
        blame = block(self.le, "nd_loose_blame_rival")
        self.assertIn("name = nd_loose_accused_by", blame)
        self.assertIn("id = nuclear_loose.7", blame)


class TestPledgeAfterUnorderedLaunch(unittest.TestCase):
    """#803: after a launch nobody ordered broke No First Use (#448 left the
    doctrine and the amendment standing), the government answers in
    nuclear_incident.6: reaffirm, repudiate at half price, or say nothing."""

    def setUp(self):
        self.e = strip_comments(read(EFFECTS))
        self.inc = strip_comments(read(INCIDENT_EVENTS))

    def test_only_an_incident_launch_under_nfu_marks_the_breach(self):
        record = block(self.e, "nd_record_nuclear_use")
        nfu = record[record.index("nd_doctrine_nfu = yes"):]
        nfu = nfu[:nfu.index("set_variable = { name = nd_has_used")]
        self.assertIn("nd_break_pledge_effects = { CREDIBILITY = 30 INFAMY = 10 }", nfu)
        self.assertIn("set_variable = nd_nfu_unordered_breach", nfu)
        for kind in ("warning", "commander", "system"):
            self.assertIn(f"scope:nd_incident_launch_{kind} ?= scope:nd_rec_attacker", nfu)
        # The ruling stands: the record itself moves no doctrine.
        self.assertNotIn("nd_set_doctrine", record)
        self.assertNotIn("nd_repudiate_nfu", record)

    def test_every_incident_that_can_launch_asks_afterwards(self):
        for event in ("nuclear_incident.3", "nuclear_incident.20", "nuclear_incident.30"):
            self.assertIn("nd_nfu_breach_follow_up = yes", block(block(self.inc, event), "after"), event)
        follow = block(self.e, "nd_nfu_breach_follow_up")
        self.assertIn("remove_variable = nd_nfu_unordered_breach", follow)
        self.assertIn("id = nuclear_incident.6", follow)

    def test_the_three_answers(self):
        ev = block(self.inc, "nuclear_incident.6")
        self.assertIn("nd_doctrine_nfu = yes", block(ev, "trigger"))
        self.assertIn("nd_reaffirm_nfu = yes", option_body(self.inc, "nuclear_incident.6.a"))
        self.assertIn("nd_set_doctrine_2_after_breach = yes", option_body(self.inc, "nuclear_incident.6.b"))
        silent = option_body(self.inc, "nuclear_incident.6.c")
        self.assertIn("default_option = yes", silent)
        for effect in ("nd_reaffirm_nfu", "nd_repudiate_nfu", "nd_set_doctrine"):
            self.assertNotIn(effect, silent)

    def test_reaffirming_costs_standing_and_restores_credibility(self):
        reaffirm = block(self.e, "nd_reaffirm_nfu")
        self.assertIn("name = nd_nfu_reaffirmed", reaffirm)
        self.assertIn("is_decaying = yes", reaffirm)
        self.assertIn("change_variable = { name = nd_credibility add = 15 }", reaffirm)
        self.assertIn("text = nd_tt_credibility_up_15", reaffirm)
        self.assertNotIn("nd_set_doctrine", reaffirm)
        self.assertIn("country_legitimacy_base_add = -10",
                      block(strip_comments(read(MODIFIERS)), "nd_nfu_reaffirmed"))

    def test_repudiating_after_the_breach_is_half_price_and_strikes_the_amendment(self):
        after = block(self.e, "nd_set_doctrine_2_after_breach")
        self.assertIn("nd_repudiate_nfu = { CREDIBILITY = 10 INFAMY = 5 }", after)
        # The core must not charge the full repudiation on top.
        self.assertIn("nd_set_doctrine = { D = 2 OFFENSIVE = no LEAVES_NFU = no }", after)
        self.assertIn("nd_repudiate_nfu = { CREDIBILITY = 20 INFAMY = 10 }", block(self.e, "nd_set_doctrine"))
        repudiate = block(self.e, "nd_repudiate_nfu")
        self.assertIn("nd_break_pledge_effects = { CREDIBILITY = $CREDIBILITY$ INFAMY = $INFAMY$ }", repudiate)
        self.assertIn("nd_strike_nfu_amendment = yes", repudiate)


class TestProliferationAlertAnswers(unittest.TestCase):
    """The proliferation alert's accommodation and reassurance answers, and the
    NPT standing case (#804)."""

    def setUp(self):
        self.ev = strip_comments(read(WEAPON_EVENTS))
        self.t = strip_comments(read(TRIGGERS))
        self.nt = strip_comments(read(NUKE_TRIGGERS))

    def test_accommodation_pays_with_the_opponents(self):
        e = option_body(self.ev, "nuclear_weapon_events.18.opt_e")
        self.assertIn("value = 25", e)
        self.assertIn("catalyst_event_positive", e)
        opponents = block(e, "every_country")
        self.assertIn("nuclear_program_opposes = { PROLIFERATOR = scope:proliferating_country }", opponents)
        self.assertIn("NOT = { THIS = ROOT }", opponents)
        self.assertIn("value = -15", opponents)
        # The AI never accommodates a programme it opposes.
        ai = block(e, "ai_chance")
        self.assertRegex(ai, r"nuclear_program_opposes = \{ PROLIFERATOR = scope:proliferating_country \}"
                             r"\s*\}\s*factor = 0")
        self.assertIn("rivalry", block(self.nt, "nuclear_program_opposes"))
        self.assertIn("nd_crisis_opponent", block(self.nt, "nuclear_program_opposes"))

    def test_guarantee_offer_reaches_only_candidates(self):
        g = option_body(self.ev, "nuclear_weapon_events.18.opt_g")
        trig = block(g, "trigger")
        self.assertIn("nd_is_armed = yes", trig)
        call = "nd_proliferation_guarantee_candidate = { GUARANTOR = ROOT PROLIFERATOR = scope:proliferating_country }"
        self.assertIn(call, trig)
        self.assertIn(call, block(g, "every_country"))
        self.assertIn("id = nuclear_weapon_events.25", g)
        self.assertIn("save_scope_as = nuclear_pg_guarantor", g)

    def test_candidate_reads_the_articles_gates(self):
        body = block(self.t, "nd_proliferation_guarantee_candidate")
        for line in ("any_neighbouring_state = { owner = $PROLIFERATOR$ }",
                     "nd_believed_armed = no",
                     "nd_is_guaranteed = no",
                     "NOT = { is_direct_subject_of = scope:nd_pg_guarantor }",
                     "NOT = { has_war_with = scope:nd_pg_guarantor }",
                     "relations_threshold:poor",
                     "has_type = alliance",
                     "has_type = defensive_pact",
                     "has_type = guarantee_independence",
                     "is_in_same_power_bloc = scope:nd_pg_beneficiary",
                     "nd_bp_can_treaty_guarantee = { GUARANTOR = scope:nd_pg_guarantor STATE = scope:nd_pg_beneficiary }"):
            self.assertIn(line, body)
        # The article's own ties: a Guarantee Independence counts only from
        # the guarantor to the beneficiary, and a bloc only if there is one.
        gi = body[body.index("has_type = guarantee_independence"):]
        self.assertIn("source_country = scope:nd_pg_guarantor", gi)
        self.assertIn("target_country = scope:nd_pg_beneficiary", gi)
        self.assertIn("is_in_power_bloc = yes", body)

    def test_answer_rechecks_and_signs_the_budapest_guarantee(self):
        ev = block(self.ev, "nuclear_weapon_events.25")
        accept = option_body(ev, "nuclear_weapon_events.25.a")
        recheck = ("nd_proliferation_guarantee_candidate = { GUARANTOR = scope:nuclear_pg_guarantor "
                   "PROLIFERATOR = scope:proliferating_country }")
        self.assertIn(recheck, block(accept, "trigger"))
        self.assertIn("nd_bp_treaty_guarantee = { GUARANTOR = scope:nuclear_pg_guarantor STATE = ROOT }", accept)
        self.assertIn("name = nuclear_pg_accepted", accept)
        self.assertIn("id = nuclear_weapon_events.26", accept)
        self.assertIn("NOT = { " + recheck + " }", block(option_body(ev, "nuclear_weapon_events.25.c"), "trigger"))
        decline = option_body(ev, "nuclear_weapon_events.25.b")
        self.assertIn(recheck, block(decline, "trigger"))
        self.assertIn("id = nuclear_weapon_events.26", decline)
        self.assertIn("exists = scope:nuclear_pg_accepted", block(self.ev, "nuclear_weapon_events.26"))

    def test_npt_standing_case(self):
        teeth = strip_comments(read(ROOT / "common/scripted_triggers/un_teeth_triggers.txt"))
        body = block(teeth, "un_case_npt_standing_applies")
        for line in ("un_tier_is_supranational = yes",
                     "has_modifier = un_member_modifier",
                     "un_propose_npt_in_force = yes",
                     "NOT = { je:je_united_nations ?= { has_modifier = un_nonproliferation_modifier } }",
                     "un_regime_npt_threshold = yes",
                     "has_variable = un_npt_built_outside"):
            self.assertIn(line, body)
        term = block(strip_comments(read(ROOT / "common/script_values/un_teeth_values.txt")),
                     "un_case_standing_term")
        self.assertIn("un_case_npt_standing_applies = yes", term)
        self.assertEqual(term.count("add = un_case_standing_value"), 1)
        first = strip_comments(read(ROOT / "common/scripted_effects/nuclear_weapon_effects.txt"))
        first = first[first.index("name = nuclear_weapons_program_first_nuke_done"):]
        first = first[:first.index("world_first_nuclear_weapon")]
        self.assertIn("set_variable = un_npt_built_outside", first)


if __name__ == "__main__":
    unittest.main()
