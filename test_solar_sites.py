# -*- coding: utf-8 -*-
"""Solar System Colonization's colony record (slices 0 and 1).

Design: docs/superpowers/specs/2026-10-25-solar-colonization-holders-and-cession-design.md.
scripts/generators/gen_solar_sites.py writes every per-world block from one
table. These tests hold:

- the table to the script it describes: the colony events' specializations,
  the launch-window bodies, the discovery seeds and outcomes;
- the generated files: current, one BOM, the header; complete for every world
  and every modifier the founding and discovery events grant; every global
  variable read guarded;
- the shared helpers' contracts (the sync removes only what is there);
- the journal entry's conditions, the rule's four settings and its gate,
  Cede Colony's article and the panel's rows.
"""

import os
import re
import sys
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(REPO, "scripts", "generators"))

import gen_launch_windows as glw  # noqa: E402
import gen_solar_sites as gss  # noqa: E402


def _raw(*parts):
    with open(os.path.join(REPO, *parts), encoding="utf-8-sig") as f:
        return f.read()


def _strip(text):
    return re.sub(r"#[^\n]*", "", text)


def _block(text, name):
    m = re.search(rf"(?m)^\s*{re.escape(name)}\s*=\s*\{{", text)
    if not m:
        raise AssertionError(f"no block {name}")
    depth, i = 1, m.end()
    while depth:
        c = text[i]
        depth += c == "{"
        depth -= c == "}"
        i += 1
    return text[m.end():i - 1]


GENERATED = {
    gss.EFFECTS_OUT: "effects",
    gss.TRIGGERS_OUT: "triggers",
    gss.VALUES_OUT: "values",
    gss.DISPLAY_OUT: "display values",
    gss.BUILDINGS_OUT: "buildings",
    gss.CUSTOM_LOC_OUT: "custom loc",
    gss.GUI_OUT: "panel rows",
}


class TableTest(unittest.TestCase):
    """The table is the script's own."""

    def test_the_specializations_are_the_events_options(self):
        events = _raw("events", "space_race_colony_events.txt")
        for site in gss.SITES:
            with self.subTest(site=site.key):
                start = events.index(f"space_race_colony_events.{site.event} = {{")
                nxt = events.find("\nspace_race_colony_events.", start + 10)
                body = events[start:nxt if nxt > 0 else len(events)]
                granted = re.findall(r"sr_grant_colony_modifier = \{ MODIFIER = (\w+) \}", body)
                self.assertEqual(tuple(granted), gss.spec_modifiers(site))

    def test_every_specialization_modifier_is_a_site_s(self):
        modifiers = _raw("common", "static_modifiers", "space_race_modifiers.txt")
        defined = set(re.findall(r"^(sr_colony_\w+) = \{", modifiers, re.M))
        table = {m for s in gss.SITES for m in gss.spec_modifiers(s)}
        self.assertEqual(table, defined)

    def test_the_bodies_are_the_launch_windows(self):
        site_body = {site: b.key for b in glw.BODIES for site in b.sites}
        for site in gss.SITES:
            with self.subTest(site=site.key):
                if site.body is None:
                    self.assertIn(site.key, glw.UNGATED_SITES)
                    self.assertEqual(glw.UNGATED_SITES[site.key], site.stage)
                else:
                    self.assertEqual(site_body[site.key], site.body)
        stage_of_body = {b.key: b.stage for b in glw.BODIES}
        for site in gss.SITES:
            if site.body:
                self.assertEqual(stage_of_body[site.body], site.stage, site.key)

    def test_the_discoveries_are_the_seeds_and_the_outcomes(self):
        seeded = [d for s in gss.SITES for d in s.discoveries]
        rolls = re.findall(r"sr_roll_colony_discovery = \{ DISCOVERY = (\w+) ",
                           _raw("common", "scripted_effects", "space_race_discovery_effects.txt"))
        self.assertEqual(sorted(seeded), sorted(rolls))
        self.assertEqual(len(seeded), len(set(seeded)))
        outcomes = set(re.findall(r"MODIFIER = (sr_discovery_\w+)", _raw("events", "space_race_discovery_events.txt")))
        table = {m for d in seeded for m in gss.discovery_modifiers(d)}
        self.assertEqual(table, outcomes)

    def test_every_world_has_a_location_and_an_icon(self):
        self.assertEqual(len(gss.SITES), 34)
        self.assertEqual(len({s.key for s in gss.SITES}), 34)
        for site in gss.SITES:
            with self.subTest(site=site.key):
                self.assertIn(site.location, gss.LOCATIONS)
                icon = os.path.join(REPO, "gfx", "interface", "icons", "space_race_icons", f"colony_{site.kind}.dds")
                tracked = os.path.exists(icon) or os.system(
                    f"git -C {REPO} ls-files --error-unmatch gfx/interface/icons/space_race_icons/colony_{site.kind}.dds"
                    " >/dev/null 2>&1") == 0
                self.assertTrue(tracked, icon)


class GeneratedFilesTest(unittest.TestCase):
    def test_generated_files_are_current(self):
        result = gss.regenerate(dry_run=True)
        self.assertEqual(result["changed_files"], [], "run python3 scripts/generators/gen_solar_sites.py")

    def test_one_bom_and_the_auto_generated_header(self):
        for path in GENERATED:
            with self.subTest(path=str(path)):
                data = open(os.path.join(REPO, path), "rb").read()
                self.assertTrue(data.startswith(b"\xef\xbb\xbf"))
                self.assertFalse(data[3:].startswith(b"\xef\xbb\xbf"))
                self.assertTrue(data[3:].decode("utf-8").startswith(gss.HEADER))

    def test_every_global_variable_read_is_guarded(self):
        # A read of a global variable enters it with ?= (or is the right side of
        # one), is an exists test, a value, a scope entered under a limit that
        # tested it, or follows its has_global_variable closely.
        # sr_colonization_stage is set on the draw's first line, and the stage
        # check runs only from the draw.
        initialized = {"sr_colonization_stage"}
        for path in (gss.EFFECTS_OUT, gss.TRIGGERS_OUT, gss.VALUES_OUT, gss.DISPLAY_OUT):
            text = _strip(_raw(str(path)))
            for m in re.finditer(r"global_var:(\w+)", text):
                var = m.group(1)
                if var in initialized:
                    continue
                before = text[max(0, m.start() - 200):m.start()]
                after = text[m.end():m.end() + 4]
                with self.subTest(path=str(path), var=var, at=m.start()):
                    self.assertTrue(
                        after.lstrip().startswith(("?=", "= {"))
                        or before.rstrip().endswith(("?=", "exists =", "value ="))
                        or f"has_global_variable = {var}" in before
                    )


class RecordTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.effects = _raw(str(gss.EFFECTS_OUT))
        cls.shared = _raw("common", "scripted_effects", "sr_site_effects.txt")

    def test_every_world_has_its_blocks(self):
        for site in gss.SITES:
            for kind in ("sync", "mirror_on", "unmirror", "release", "transfer", "monthly"):
                with self.subTest(site=site.key, kind=kind):
                    self.assertRegex(self.effects, rf"(?m)^sr_site_{kind}_{site.key} = \{{")

    def test_every_granted_modifier_has_a_dispatcher(self):
        granted = set(re.findall(r"sr_grant_colony_modifier = \{ MODIFIER = (\w+) \}",
                                 _raw("events", "space_race_colony_events.txt")
                                 + _raw("events", "space_race_discovery_events.txt")))
        self.assertEqual(len(granted), 108)
        dispatched = set(re.findall(r"(?m)^sr_site_choose_(\w+) = \{", self.effects))
        self.assertEqual(granted, dispatched)
        grant = _block(_raw("common", "scripted_effects", "space_race_effects.txt"), "sr_grant_colony_modifier")
        self.assertIn("hidden_effect = { sr_site_choose_$MODIFIER$ = yes }", grant)

    def test_the_draw_names_the_holder_after_the_claim(self):
        draw = _block(self.effects, "sr_establish_colony_effect")
        for site in gss.SITES:
            with self.subTest(site=site.key):
                claim = f"set_global_variable = {{ name = sr_colony_{site.key} value = yes }}"
                holder = f"set_global_variable = {{ name = sr_site_holder_{site.key} value = root }}"
                sync = f"sr_site_sync_{site.key} = yes"
                self.assertIn(claim, draw)
                self.assertLess(draw.index(claim), draw.index(holder))
                self.assertLess(draw.index(holder), draw.index(sync))
        # The sync counts the claim: the draw no longer adds to the count.
        self.assertNotIn("change_variable = { name = sr_colony_count", draw)

    def test_each_stage_draws_its_worlds_and_the_released_worlds_before_it(self):
        draw = _block(self.effects, "sr_establish_colony_effect")
        draw = draw[:draw.index("local_var:sr_colonies_claimed_before < sr_total_global_colonies")]
        stages = re.split(r"global_var:sr_colonization_stage = (\d)", draw)
        for i in range(1, len(stages), 2):
            stage, body = int(stages[i]), stages[i + 1]
            drawn = set(re.findall(r"name = sr_colony_(\w+) value = yes", body))
            with self.subTest(stage=stage):
                self.assertEqual(drawn, {s.key for s in gss.SITES if s.stage <= stage})

    def test_the_mirror_names_exactly_the_world_s_modifiers(self):
        for site in gss.SITES:
            own = set(gss.spec_modifiers(site))
            for d in site.discoveries:
                own |= set(gss.discovery_modifiers(d))
            for kind in ("mirror_on", "unmirror"):
                body = _block(self.effects, f"sr_site_{kind}_{site.key}")
                named = set(re.findall(r"MODIFIER = (\w+)", body))
                with self.subTest(site=site.key, kind=kind):
                    self.assertEqual(named, own)
                    self.assertIn("set_variable = { name = sr_colony_count value = sr_sites_held_count }", body)

    def test_the_sync_takes_the_world_from_the_old_mirror_first(self):
        for site in gss.SITES:
            body = _block(self.effects, f"sr_site_sync_{site.key}")
            with self.subTest(site=site.key):
                self.assertLess(body.index(f"sr_site_unmirror_{site.key} = yes"),
                                body.index(f"sr_site_mirror_on_{site.key} = yes"))
                self.assertIn("is_country_alive = yes", body)

    def test_the_shared_helpers_remove_only_what_is_there(self):
        for name in ("sr_site_hide_modifier", "sr_site_hide_modifier_at", "sr_site_clear_discovery", "sr_site_set_discovery_done"):
            body = _block(self.shared, name)
            for m in re.finditer(r"remove_(variable|modifier) = (\S+)", body):
                with self.subTest(helper=name, target=m.group(2)):
                    before = body[:m.start()]
                    test = "has_modifier" if m.group(1) == "modifier" else "has_variable"
                    self.assertIn(f"{test} = {m.group(2)}", before[-120:])

    def test_the_dead_holder_passes_to_the_capital_region_s_owner(self):
        for site in gss.SITES:
            body = _block(self.effects, f"sr_site_monthly_{site.key}")
            with self.subTest(site=site.key):
                self.assertIn(f"set_global_variable = {{ name = sr_site_region_{site.key} value = capital.state_region }}", body)
                self.assertIn("sr_site_can_hold = yes", body)
                self.assertIn("order_by = state_population", body)
                self.assertIn(f"sr_site_transfer_{site.key} = {{ CAUSE = heir }}", body)
                self.assertIn(f"sr_site_release_{site.key} = yes", body)
        hold = _block(_raw("common", "scripted_triggers", "sr_site_triggers.txt"), "sr_site_can_hold")
        self.assertIn("NOT = { is_country_type = decentralized }", hold)

    def test_every_transfer_cause_has_both_sides(self):
        causes = set(re.findall(r"sr_site_transfer_\w+ = \{ CAUSE = (\w+) \}", self.effects))
        self.assertEqual(causes, {"treaty", "heir", "quiet"})
        for cause in causes:
            for side in ("gained", "lost"):
                with self.subTest(cause=cause, side=side):
                    self.assertRegex(self.shared, rf"(?m)^sr_site_{side}_{cause} = \{{")

    def test_the_migration_reads_every_record(self):
        body = _block(self.effects, "sr_sites_migrate_country")
        held = set(re.findall(r"has_variable = (\w+)_held", body))
        self.assertEqual(held, {m for m, *_ in gss.choices()})

    def test_the_revolution_repoints_every_world(self):
        body = _block(self.effects, "sr_sites_repoint_loser")
        for site in gss.SITES:
            self.assertIn(f"global_var:sr_site_holder_{site.key} ?= scope:te_cw_loser", body)
        repair = _block(_raw("common", "scripted_effects", "space_race_effects.txt"), "sr_repair_after_civil_war")
        self.assertIn("sr_sites_repoint_loser = yes", repair)


class EntryTest(unittest.TestCase):
    def test_a_colony_holder_keeps_the_entry_and_colonizing_needs_the_milestones(self):
        je = _strip(_raw("common", "journal_entries", "je_space_race.txt"))
        entry = _block(je, "je_space_race_solar_colonization")
        for block in ("is_shown_when_inactive", "possible"):
            with self.subTest(block=block):
                body = _block(entry, block)
                self.assertIn("sr_has_space_colony = yes", body)
                self.assertIn("has_variable = sr_completed_moon_base", body)
                self.assertIn("has_variable = sr_completed_mars_landing", body)
        self.assertIn("sr_any_site_unclaimed = yes", _block(entry, "possible"))
        self.assertNotIn("sr_all_colonies_complete", _block(entry, "possible"))
        running = _block(_raw("common", "scripted_triggers", "space_race_triggers.txt"), "sr_solar_colonization_running")
        self.assertIn("sr_solar_colonization_qualified = yes", running)


class RuleTest(unittest.TestCase):
    def test_four_settings_and_the_old_name_kept(self):
        rules = _raw("common", "game_rules", "extra_game_rules.txt")
        body = _block(rules, "space_race_rule")
        settings = re.findall(r"(?m)^\t(\w+) = \{", body)
        self.assertEqual(settings, ["space_race_colonies_full", "space_race_colonies_simple",
                                    "space_race_enabled", "space_race_disabled"])
        self.assertIn("default = space_race_colonies_simple", body)
        for setting in settings:
            self.assertIn(f"flag = {setting}", _block(body, setting))

    def test_no_bare_check_of_races_only(self):
        gate = _block(_raw("common", "scripted_triggers", "sr_site_triggers.txt"), "sr_space_race_on")
        self.assertIn("has_game_rule = space_race_enabled", gate)
        offenders = []
        for top in ("common", "events", "gui"):
            for dirpath, _, files in os.walk(os.path.join(REPO, top)):
                for name in files:
                    if not name.endswith((".txt", ".gui")):
                        continue
                    path = os.path.join(dirpath, name)
                    text = _strip(open(path, encoding="utf-8-sig", errors="replace").read())
                    count = text.count("has_game_rule = space_race_enabled")
                    if name == "sr_site_triggers.txt":
                        count -= 1
                    if count:
                        offenders.append(os.path.relpath(path, REPO))
        self.assertEqual(offenders, [])


class CedeColonyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.article = _block(_raw("common", "treaty_articles", "124_cede_colony.txt"), "te_cede_colony")

    def test_the_article_s_shape(self):
        self.assertIn("kind = directed", self.article)
        self.assertIn("usage_limit = once_per_side_with_same_inputs", self.article)
        flags = _block(self.article, "flags")
        self.assertIn("can_be_enforced", flags)
        self.assertIn("giftable", flags)
        self.assertIn("building_type", _block(self.article, "required_inputs"))
        self.assertIn("sr_cede_site_input_valid = yes", _block(self.article, "building_type_valid_trigger"))
        self.assertIn("sr_colonies_contested_enabled = yes", _block(self.article, "visible"))
        self.assertIn("sr_cede_colony_apply = yes", _block(self.article, "on_entry_into_force"))

    def test_every_world_can_be_named_and_moved(self):
        buildings = _raw(str(gss.BUILDINGS_OUT))
        valid = _block(_raw(str(gss.TRIGGERS_OUT)), "sr_cede_site_input_valid")
        apply = _block(_raw(str(gss.EFFECTS_OUT)), "sr_cede_colony_apply")
        for site in gss.SITES:
            building = gss.site_building(site)
            with self.subTest(site=site.key):
                body = _block(buildings, building)
                self.assertIn("always = no", _block(body, "potential"))
                self.assertIn(f"scope:input = bt:{building} global_var:sr_site_holder_{site.key} ?= root", valid)
                self.assertIn(f"input_building_type ?= bt:{building}", apply)
                self.assertIn(f"sr_site_transfer_{site.key} = {{ CAUSE = treaty }}", apply)


def _gui_type(gui, name):
    m = re.search(rf"type {name} = \w+ \{{", gui)
    if m is None:
        raise AssertionError(f"no type {name}")
    depth, i = 1, m.end()
    while depth:
        depth += {"{": 1, "}": -1}.get(gui[i], 0)
        i += 1
    return gui[m.end():i]


def _instances(section, type_name):
    """The bodies of every `type_name = { ... }` instance in a section."""
    out = []
    for m in re.finditer(rf"\b{type_name} = \{{", section):
        depth, i = 1, m.end()
        while depth:
            depth += {"{": 1, "}": -1}.get(section[i], 0)
            i += 1
        out.append(section[m.end():i])
    return out


class PanelTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.widget = _raw("gui", "journal_entry_widgets", "space_race_widget.gui")
        cls.rows = _raw(str(gss.GUI_OUT))

    def test_the_solar_system_rows_follow_the_table(self):
        self.assertIn("te_sr_solar_system_rows = {}", _gui_type(self.widget, "te_sr_sec_solar_system"))
        section = _gui_type(self.rows, "te_sr_solar_system_rows")
        rows = re.findall(r"text = \"sr_site_name_(\w+)\"", section)
        self.assertEqual(rows, [s.key for s in gss.panel_order()])
        for site, row in zip(gss.panel_order(), _instances(section, "te_sr_site_row")):
            with self.subTest(site=site.key):
                self.assertIn(f"Var('sr_ss_cap_{site.key}').GetState", row)
                self.assertIn(f"ScriptValue('sr_disp_site_{site.key}')", row)
                self.assertIn(f"ScriptValue('sr_disp_site_target_{site.key}')", row)
                self.assertIn(f"ScriptValue('sr_disp_site_inbound_{site.key}')", row)
                # The Target button names this world's index, and only this one.
                self.assertEqual(set(re.findall(r"MakeScopeValue\( '\(CFixedPoint\)(\d+)' \)", row)), {str(site.index)})
                self.assertIn("GetScriptedGui('sr_colony_target_sgui')", row)

    def test_the_settler_and_fleet_rows_follow_the_table(self):
        settlers = _instances(_gui_type(self.rows, "te_sr_settler_rows"), "te_sr_settler_row")
        self.assertEqual(len(settlers), len(gss.SITES))
        for site, row in zip(gss.panel_order(), settlers):
            with self.subTest(site=site.key):
                self.assertIn(f'text = "sr_site_name_{site.key}"', row)
                self.assertIn(f"ScriptValue('sr_disp_site_pop_{site.key}')", row)
                self.assertIn(f"ScriptValue('sr_site_room_{site.key}')", row)
                self.assertIn(f"ScriptValue('sr_disp_site_prio_{site.key}')", row)
                self.assertEqual(set(re.findall(r"MakeScopeValue\( '\(CFixedPoint\)(\d+)' \)", row)), {str(site.index)})
        slots = _instances(_gui_type(self.rows, "te_sr_cf_slot_rows"), "te_sr_cf_slot_row")
        self.assertEqual(len(slots), gss.FLEET_SLOTS)
        for n, row in enumerate(slots, start=1):
            self.assertIn(f"GetCustom('sr_cf_slot_{n}_name')", row)
            self.assertIn(f"je_space_race_widget_cf_slot_{n}_eta", row)
        for section in ("te_sr_sec_colony_fleets", "te_sr_sec_settlers"):
            self.assertIn(f"\t\t{section} = {{}}", _gui_type(self.widget, "te_sr_solar_colonization_status"))


class FleetTest(unittest.TestCase):
    """Colony fleets (slices 2-3 design §§ 3-9)."""

    @classmethod
    def setUpClass(cls):
        cls.effects = _strip(_raw(str(gss.EFFECTS_OUT)))
        cls.triggers = _strip(_raw(str(gss.TRIGGERS_OUT)))
        cls.values = _strip(_raw(str(gss.VALUES_OUT)))
        cls.fleets = _strip(_raw("common", "scripted_effects", "sr_colony_fleet_effects.txt"))
        cls.windows = _strip(_raw("common", "scripted_effects", "sr_launch_window_effects.txt"))

    def test_every_world_has_its_fleet_blocks(self):
        for site in gss.SITES:
            k = site.key
            with self.subTest(site=k):
                for kind in ("found", "dispatch", "found_now", "arrive", "note_inbound"):
                    prefix = "sr_site" if kind == "found" else "sr_cf"
                    self.assertRegex(self.effects, rf"(?m)^{prefix}_{kind}_{k} = \{{")
                for kind in ("targetable", "departs", "eligible", "beaten"):
                    self.assertRegex(self.triggers, rf"(?m)^sr_cf_{kind}_{k} = \{{")
                for kind in ("goal", "cost", "arrival", "score"):
                    self.assertRegex(self.values, rf"(?m)^sr_cf_{kind}_{k} = \{{")

    def test_the_founding_names_this_and_opens_the_entry_before_the_event(self):
        for site in gss.SITES:
            body = _block(self.effects, f"sr_site_found_{site.key}")
            with self.subTest(site=site.key):
                claim = f"set_global_variable = {{ name = sr_colony_{site.key} value = yes }}"
                holder = f"set_global_variable = {{ name = sr_site_holder_{site.key} value = this }}"
                self.assertLess(body.index(claim), body.index(holder))
                self.assertLess(body.index(holder), body.index(f"sr_site_sync_{site.key} = yes"))
                self.assertEqual(re.findall(r"DISCOVERY = (\w+)", body), list(site.discoveries))
                self.assertLess(body.index("sr_cf_open_entry = yes"),
                                body.index(f"trigger_event = {{ id = space_race_colony_events.{site.event} }}"))

    def test_a_landing_takes_its_world_then_its_body_s_others_then_is_lost(self):
        for site in gss.SITES:
            body = _block(self.effects, f"sr_cf_arrive_{site.key}")
            founded = re.findall(r"sr_site_found_(\w+) = yes", body)
            with self.subTest(site=site.key):
                self.assertEqual(founded[0], site.key)
                others = [s.key for s in gss.body_group(site) if s is not site]
                self.assertEqual(founded[1:], others)
                self.assertEqual(len(re.findall(r"sr_cf_note_diverted = \{ TARGET = (\d+) FOUNDED = (\d+) \}", body)),
                                 len(others))
                self.assertIn(f"sr_cf_note_lost = {{ TARGET = {site.index} }}", body)
        # Each launch-window body diverts within itself; the asteroids, Venus and
        # Mercury have no other world.
        for site in gss.SITES:
            self.assertTrue(all(s.body == site.body for s in gss.body_group(site)))

    def test_a_dispatch_spends_its_cost_and_checks_the_window(self):
        for site in gss.SITES:
            body = _block(self.effects, f"sr_cf_dispatch_{site.key}")
            with self.subTest(site=site.key):
                self.assertIn(f"set_local_variable = {{ name = sr_cf_new_site value = {site.index} }}", body)
                self.assertIn(f"value = sr_cf_cost_{site.key}", body)
                self.assertLess(body.index("subtract = var:sr_goal_before_colony"), body.index("sr_cf_store_new = yes"))
                gate = re.findall(r"sr_launch_window_gate_check = \{ BODY = (\w+) \}", body)
                self.assertEqual(gate, [site.body] if site.body else [])
                arrival = _block(self.values, f"sr_cf_arrival_{site.key}")
                self.assertIn(f"add = sr_transit_months_{gss.transit_body(site)}", arrival)

    def test_the_outer_worlds_need_deep_space_or_a_colony_under_simple_and_full(self):
        for site in gss.SITES:
            body = _block(self.triggers, f"sr_cf_targetable_{site.key}")
            with self.subTest(site=site.key):
                self.assertIn(f"sr_current_colonization_stage >= {site.stage}", body)
                needs = "country_sr_deep_space_exploration_program_bool" in body
                self.assertEqual(needs, site.stage >= 3)

    def test_the_score_is_the_design_s(self):
        for site in gss.SITES:
            body = _block(self.values, f"sr_cf_score_{site.key}")
            with self.subTest(site=site.key):
                self.assertIn(f"value = {gss.SCORE_BASE - gss.SCORE_PER_STAGE * site.stage}", body)
                self.assertIn(f"divide = {gss.SCORE_TRANSIT_DIVISOR}", body)
                self.assertIn(f"subtract = {gss.SCORE_BEATEN}", body)
                self.assertIn(f"min = {gss.SCORE_FLOOR}", body)
        self.assertGreater(gss.SCORE_FLOOR, -1000)  # above sr_cf_no_score
        self.assertIn("sr_cf_no_score = { value = -1000 }", self.values)
        self.assertIn(f"sr_cf_horizon_months = {{ value = {gss.HORIZON_MONTHS} }}", self.values)

    def test_the_stage_recompute_lists_each_stage_s_worlds_and_completes(self):
        body = _block(self.effects, "sr_sites_recompute_stage")
        parts = re.split(r"set_global_variable = \{ name = sr_colonization_stage value = (\d) \}", body)
        for i in range(1, 11, 2):
            stage = int(parts[i])
            listed = set(re.findall(r"has_global_variable = sr_colony_(\w+)", parts[i - 1]))
            self.assertEqual(listed, {s.key for s in gss.stage_sites(stage)}, stage)
        self.assertIn("set_global_variable = { name = sr_all_colonies_complete value = yes }", body)

    def test_the_stage_goals_are_the_generator_s(self):
        for stage, goal in gss.STAGE_GOALS.items():
            self.assertIn(f"sr_colonization_goal_stage_{stage} = {{ value = {goal} }}", self.values)
        goal = _block(_strip(_raw("common", "script_values", "space_race_values.txt")), "sr_solar_colonization_goal")
        self.assertEqual(set(re.findall(r"sr_colonization_goal_stage_(\d)", goal)), {"1", "2", "3", "4", "5"})
        self.assertIn("value = sr_cf_target_goal", goal)

    def test_the_launch_month_branches_on_the_rule(self):
        month = _block(self.windows, "sr_launch_month")
        self.assertLess(month.index("NOT = { sr_cf_target_valid = yes }"), month.index("sr_cf_launch_month = yes"))
        self.assertLess(month.index("sr_colonies_contested_enabled = yes"), month.index("sr_cf_launch_month = yes"))
        self.assertLess(month.index("sr_cf_found_target_now = yes"), month.index("sr_launch_fleet_ready = yes"))
        launch = _block(self.fleets, "sr_cf_launch_month")
        self.assertIn("sr_cf_has_free_slot = yes", launch)
        self.assertIn("sr_cf_dispatch_target = yes", launch)
        self.assertIn("sr_cf_pick_auto = yes", launch)

    def test_every_slot_is_listed(self):
        site_triggers = _strip(_raw("common", "scripted_triggers", "sr_site_triggers.txt"))
        free = _block(site_triggers, "sr_cf_has_free_slot")
        self.assertEqual(re.findall(r"has_variable = sr_cf_(\d)_site", free),
                         [str(n) for n in range(1, gss.FLEET_SLOTS + 1)])
        for name, call in (("sr_cf_global_arrivals", "sr_cf_arrive_slot"), ("sr_cf_rebuild_inbound", "sr_cf_note_slot"),
                           ("sr_cf_debug_land_all_now", "sr_cf_debug_land_slot")):
            body = _block(self.fleets, name)
            with self.subTest(effect=name):
                self.assertEqual(re.findall(rf"{call} = \{{ N = (\d) \}}", body),
                                 [str(n) for n in range(1, gss.FLEET_SLOTS + 1)])
        store = _block(self.fleets, "sr_cf_store_new")
        self.assertEqual(re.findall(r"sr_cf_fill_slot = \{ N = (\d) \}", store),
                         [str(n) for n in range(1, gss.FLEET_SLOTS + 1)])

    def test_the_global_step_lands_fleets_before_the_worlds_step(self):
        step = _block(_strip(_raw("common", "scripted_effects", "sr_site_effects.txt")), "sr_sites_global_monthly")
        self.assertLess(step.index("sr_cf_global_arrivals = yes"), step.index("sr_sites_monthly = yes"))
        self.assertLess(step.index("sr_sites_monthly = yes"), step.index("sr_cf_global_after = yes"))
        after = _block(self.fleets, "sr_cf_global_after")
        self.assertLess(after.index("sr_cf_rebuild_inbound = yes"), after.index("sr_sites_recompute_stage = yes"))
        clear = _block(self.effects, "sr_sites_clear_inbound")
        for site in gss.SITES:
            for var in (f"sr_site_inbound_{site.key}", f"sr_site_inbound_first_{site.key}",
                        f"sr_site_inbound_by_{site.key}"):
                self.assertIn(f"remove_global_variable = {var} ", clear)

    def test_the_notice_names_both_worlds(self):
        custom = _raw(str(gss.CUSTOM_LOC_OUT))
        for name in ("sr_cf_target_name", "sr_cf_notice_target_name", "sr_cf_notice_founded_name",
                     *[f"sr_cf_slot_{n}_name" for n in range(1, gss.FLEET_SLOTS + 1)]):
            self.assertRegex(custom, rf"(?m)^{name} = \{{")
        events = _strip(_raw("events", "space_race_events.txt"))
        notice = _block(events, "space_race_events.92")
        self.assertIn("sr_cf_clear_notice = yes", notice)


class PopulationTest(unittest.TestCase):
    """Colony population (slices 2-3 design § 10)."""

    @classmethod
    def setUpClass(cls):
        cls.effects = _strip(_raw(str(gss.EFFECTS_OUT)))
        cls.values = _strip(_raw(str(gss.VALUES_OUT)))
        cls.population = _strip(_raw("common", "scripted_effects", "sr_colony_population_effects.txt"))
        cls.pop_values = _strip(_raw("common", "script_values", "sr_colony_population_values.txt"))

    def test_every_world_has_room_people_and_weights(self):
        for site in gss.SITES:
            k = site.key
            with self.subTest(site=k):
                self.assertIn(f"sr_site_base_room_{k} = {{ value = {site.room * 1000} }}", self.values)
                # Habitats add half the base room a level (colony modules design § 3).
                room = _block(self.values, f"sr_site_room_{k}")
                self.assertIn(f"value = sr_site_hab_value_{k}", room)
                self.assertIn(f"multiply = {gss.HABITAT_ROOM_SHARE}", room)
                self.assertIn(f"multiply = sr_site_base_room_{k}", room)
                for kind in ("sr_site_pop_value", "sr_site_free_room", "sr_site_crews", "sr_emig_prio_weight",
                             "sr_emig_weight"):
                    self.assertRegex(self.values, rf"(?m)^{kind}_{k} = \{{")
                self.assertIn(f"add = sr_emig_weight_{k}", _block(self.values, "sr_emig_weight_total"))
                self.assertIn(f"add = sr_site_pop_value_{k}", _block(self.values, "sr_offworld_pop_total"))
        self.assertEqual(sum(s.room for s in gss.SITES), 810)

    def test_the_priority_weights_are_the_design_s(self):
        self.assertEqual(gss.PRIORITY_WEIGHTS, (0, 1, 2, 4))
        for site in gss.SITES:
            body = _block(self.values, f"sr_emig_prio_weight_{site.key}")
            self.assertEqual(re.findall(r"var:sr_emig_prio_\w+ = (\d) \} value = (\d)", body),
                             [("0", "0"), ("1", "1"), ("3", "4")])
            self.assertIn("value = 2", body)

    def test_the_people_stay_with_the_world_and_the_priority_with_the_holder(self):
        for site in gss.SITES:
            k = site.key
            with self.subTest(site=k):
                self.assertIn(f"remove_global_variable = sr_site_pop_{k}", _block(self.effects, f"sr_site_release_{k}"))
                self.assertIn(f"remove_variable = sr_emig_prio_{k}", _block(self.effects, f"sr_site_unmirror_{k}"))
                self.assertNotIn("sr_site_pop_", _block(self.effects, f"sr_site_transfer_{k}"))
                monthly = _block(self.effects, f"sr_site_monthly_{k}")
                growth = monthly[monthly.index("# 5.") if "# 5." in monthly else monthly.index("sr_colonies_contested_enabled"):]
                self.assertIn("sr_colonies_contested_enabled = yes", growth)
                self.assertIn(f"multiply = {1 + gss.GROWTH_PER_MONTH}", growth)
                self.assertIn(f"max = sr_site_room_{k}", growth)
                share = _block(self.effects, "sr_emig_distribute")
                self.assertIn(f"max = sr_site_free_room_{k}", share)

    def test_a_batch_is_half_middle_and_half_lower_from_the_space_program_s_state(self):
        month = _block(self.population, "sr_emig_month")
        kills = re.findall(r"kill_population_in_state = \{ value = (\d+) strata = (\w+) \}", month)
        self.assertEqual(kills, [("250", "middle"), ("250", "lower")])
        batch = float(re.search(r"sr_emig_batch_people = \{\s*value = (\d+)", self.pop_values).group(1))
        self.assertEqual(sum(int(v) for v, _ in kills), batch)
        self.assertIn("is_building_type = building_space_program", month)
        self.assertIn("count = local_var:sr_emig_batches", month)
        self.assertIn("sr_colonies_contested_enabled = yes", month)

    def test_the_entry_s_modifiers_are_removed_first_and_read_through_owner(self):
        refresh = _block(self.population, "sr_emig_refresh_modifiers")
        for name in ("sr_emigration_programme", "sr_offworld_population"):
            self.assertLess(refresh.index(f"remove_modifier = {name}"), refresh.index(f"name = {name} multiplier"))
        for value in ("sr_emig_upkeep_units", "sr_offworld_bonus_units"):
            self.assertIn("owner = {", _block(self.pop_values, value))
        je = _strip(_raw("common", "journal_entries", "je_space_race.txt"))
        pulse = _block(_block(je, "je_space_race_solar_colonization"), "on_monthly_pulse")
        for call in ("sr_emig_ai_review = yes", "sr_emig_month = yes", "sr_emig_refresh_modifiers = yes"):
            self.assertIn(call, pulse)

    def test_the_entry_s_modifiers_refresh_once_per_effect(self):
        # Whether has_modifier sees an add_modifier made earlier in the same
        # effect is unverified, so a second refresh in one effect could skip
        # the removal and stack a copy: the AI's review sets the level in the
        # same pulse that refreshes afterwards.
        refresh = "sr_emig_refresh_modifiers = yes"
        self.assertNotIn(refresh, _block(self.population, "sr_emig_set_level"))
        self.assertNotIn(refresh, _block(self.population, "sr_emig_ai_review"))
        step = _block(self.population, "sr_emig_step_level")
        self.assertEqual(step.count(refresh), 1)
        self.assertGreater(step.index(refresh), step.rindex("sr_emig_set_level"))
        je = _strip(_raw("common", "journal_entries", "je_space_race.txt"))
        pulse = _block(_block(je, "je_space_race_solar_colonization"), "on_monthly_pulse")
        self.assertEqual(pulse.count(refresh), 1)
        self.assertGreater(pulse.index(refresh), pulse.index("sr_emig_ai_review = yes"))
        debug = _strip(_raw("events", "te_debug_space_race_events.txt"))
        for option in re.findall(r"(?ms)^\toption = \{\n(.*?)^\t\}", debug):
            if "sr_emig_set_level" in option:
                with self.subTest(option=option.split()[2]):
                    self.assertEqual(option.count(refresh), 1)

    def test_every_settler_sent_lands(self):
        # A colony capped at its free room passes the rest on: passes share
        # what is left among the colonies with room until everyone has landed.
        distribute = _block(self.effects, "sr_emig_distribute")
        self.assertIn("set_local_variable = { name = sr_emig_left value = local_var:sr_emig_sent }", distribute)
        loop = _block(distribute, "while")
        limit = _block(loop, "limit")
        self.assertIn("local_var:sr_emig_left >= 1", limit)
        self.assertIn(f"local_var:sr_emig_passes < {len(gss.SITES)}", limit)
        self.assertIn("sr_emig_weight_total > 0", limit)
        self.assertIn("change_local_variable = { name = sr_emig_passes add = 1 }", loop)
        self.assertIn("set_local_variable = { name = sr_emig_weight_sum value = sr_emig_weight_total }", loop)
        self.assertNotIn("sr_emig_weight_sum", _block(self.population, "sr_emig_month"))
        for site in gss.SITES:
            k = site.key
            with self.subTest(site=k):
                self.assertIn(f"multiply = sr_emig_weight_{k}", loop)
                self.assertIn(f"max = sr_site_free_room_{k}", loop)
                self.assertIn(f"change_global_variable = {{ name = sr_site_pop_{k} add = local_var:sr_emig_share }}", loop)
        self.assertEqual(loop.count("value = local_var:sr_emig_pass\n"), len(gss.SITES))
        self.assertEqual(loop.count("change_local_variable = { name = sr_emig_left subtract = local_var:sr_emig_share }"),
                         len(gss.SITES))


class ModulesTest(unittest.TestCase):
    """Colony modules and Extraplanetary Base room (slice 4,
    2026-10-25-solar-colonization-modules-and-bases-design.md)."""

    @classmethod
    def setUpClass(cls):
        cls.effects = _strip(_raw(str(gss.EFFECTS_OUT)))
        cls.triggers = _strip(_raw(str(gss.TRIGGERS_OUT)))
        cls.values = _strip(_raw(str(gss.VALUES_OUT)))
        cls.shared = _strip(_raw("common", "scripted_effects", "sr_site_effects.txt"))
        cls.modules = _strip(_raw("common", "scripted_effects", "sr_colony_module_effects.txt"))
        cls.rows = _raw(str(gss.GUI_OUT))

    def test_the_table_s_slots_and_base_room(self):
        for site in gss.SITES:
            with self.subTest(site=site.key):
                self.assertIn(site.slots, range(1, 5))
                self.assertIn(site.ebase_room, range(10, 61))
                self.assertIn(site.ebase_grade, range(-45, 31))
        self.assertEqual(sum(s.ebase_room for s in gss.SITES), 760)
        best = max(gss.SITES, key=lambda s: s.ebase_grade)
        self.assertEqual(best.key, "psyche")
        # The outer worlds are poorer than the inner, stage by stage on average.
        means = [sum(s.ebase_grade for s in gss.stage_sites(n)) / len(gss.stage_sites(n)) for n in range(1, 6)]
        self.assertEqual(means, sorted(means, reverse=True))

    def test_a_specialization_reads_its_founding_level_until_a_module_raises_it(self):
        for site in gss.SITES:
            k = site.key
            for slot, option in (("a", 1), ("b", 2)):
                body = _block(self.values, f"sr_site_lvl_{slot}_value_{k}")
                with self.subTest(site=k, slot=slot):
                    self.assertIn(f"value = global_var:sr_site_lvl_{slot}_{k}", body)
                    self.assertIn(f"global_var:sr_site_spec_{k} = {option} }} value = 1", body)
                    self.assertLess(body.index(f"sr_site_lvl_{slot}_{k}"), body.index(f"sr_site_spec_{k}"))

    def test_staffing_counts_crews_against_the_crewed_levels(self):
        for site in gss.SITES:
            k = site.key
            with self.subTest(site=k):
                levels = _block(self.values, f"sr_site_levels_{k}")
                self.assertEqual(re.findall(r"= (sr_site_\w+_value_\w+)", levels),
                                 [gss.level_value(t, site) for t in gss.CREWED_TYPES])
                self.assertNotIn("hab", levels)
                staffing = _block(self.values, f"sr_site_staffing_{k}")
                self.assertIn("sr_colonies_contested_enabled = yes", staffing)
                self.assertIn(f"sr_site_crews_{k} < sr_site_crew_needed_{k}", staffing)
                self.assertIn("has_technology_researched = artificial_intelligence", staffing)
                self.assertIn(f"value = sr_site_crews_{k}\n\t\tadd = 1\n\t\tdivide = sr_site_levels_{k}", staffing)
                for slot in ("a", "b"):
                    mult = _block(self.values, f"sr_site_mult_{slot}_{k}")
                    self.assertIn(f"value = sr_site_lvl_{slot}_value_{k}", mult)
                    self.assertIn(f"multiply = sr_site_staffing_{k}", mult)

    def test_the_mirror_shows_each_specialization_at_its_multiplier(self):
        for site in gss.SITES:
            k = site.key
            body = _block(self.effects, f"sr_site_mirror_on_{k}")
            for slot, modifier in zip(("a", "b"), gss.spec_modifiers(site)):
                with self.subTest(site=k, slot=slot):
                    self.assertIn(f"sr_site_lvl_{slot}_value_{k} >= 1", body)
                    self.assertIn(f"sr_site_show_modifier_at = {{ MODIFIER = {modifier} MULT = sr_site_mult_{slot}_{k} }}",
                                  body)
                    self.assertIn(f"sr_site_hide_modifier_at = {{ MODIFIER = {modifier} }}", body)

    def test_the_multiplier_is_tested_by_its_record_not_has_modifier(self):
        show = _block(self.shared, "sr_site_show_modifier_at")
        test = _block(show, "limit") if "limit" in show else ""
        self.assertIn("NOT = { var:$MODIFIER$_mult = $MULT$ }", show)
        self.assertNotIn("has_modifier", show[:show.index("je:je_space_race_solar_colonization")])
        inner = show[show.index("je:je_space_race_solar_colonization"):]
        self.assertLess(inner.index("remove_modifier = $MODIFIER$"), inner.index("add_modifier"))
        self.assertIn("add_modifier = { name = $MODIFIER$ multiplier = $MULT$ }", inner)
        self.assertIn("owner = { set_variable = { name = $MODIFIER$_mult value = $MULT$ } }", inner)
        self.assertTrue(test)
        # The founding choice records multiplier 1 for the unscaled modifier the grant just added.
        for modifier, site, kind, _ in gss.choices():
            if kind != "spec":
                continue
            body = _block(self.effects, f"sr_site_choose_{modifier}")
            with self.subTest(modifier=modifier):
                self.assertLess(body.index(f"set_variable = {{ name = {modifier}_mult value = 1 }}"),
                                body.index(f"sr_site_sync_{site.key} = yes"))
        hide_at = _block(self.shared, "sr_site_hide_modifier_at")
        self.assertIn("limit = { has_variable = $MODIFIER$_mult }\n\t\tremove_variable = $MODIFIER$_mult", hide_at)
        # A discovery's modifier has no multiplier record: the plain hide mustn't read one,
        # or the parse-time validator reports every discovery's <modifier>_mult as never set.
        self.assertNotIn("_mult", _block(self.shared, "sr_site_hide_modifier"))
        for site in gss.SITES:
            body = _block(self.effects, f"sr_site_mirror_on_{site.key}") + _block(self.effects, f"sr_site_unmirror_{site.key}")
            for d in site.discoveries:
                for modifier in gss.discovery_modifiers(d):
                    with self.subTest(site=site.key, modifier=modifier):
                        self.assertNotIn(f"sr_site_hide_modifier_at = {{ MODIFIER = {modifier} }}", body)

    def test_release_clears_the_modules_and_the_unmirror_the_queue(self):
        for site in gss.SITES:
            k = site.key
            release = _block(self.effects, f"sr_site_release_{k}")
            unmirror = _block(self.effects, f"sr_site_unmirror_{k}")
            with self.subTest(site=k):
                for var in gss.module_vars(site):
                    self.assertIn(f"remove_global_variable = {var}", release)
                self.assertIn(f"sr_mq_drop_site = {{ INDEX = {site.index} }}", unmirror)

    def test_the_caps_count_queue_and_shipments(self):
        for site in gss.SITES:
            k = site.key
            with self.subTest(site=k):
                for slot in ("a", "b"):
                    can = _block(self.triggers, f"sr_mod_can_queue_{slot}_{k}")
                    self.assertIn(f"global_var:sr_site_holder_{k} ?= this", can)
                    self.assertIn(f"has_global_variable = sr_site_spec_{k}", can)
                    self.assertIn(f"sr_mod_spec_used_{k} < sr_mod_spec_budget", can)
                for t in gss.GENERIC_TYPES:
                    self.assertIn(f"sr_mod_slots_used_{k} < {site.slots}", _block(self.triggers, f"sr_mod_can_queue_{t}_{k}"))
                for name, types in (("spec_used", ("a", "b")), ("slots_used", gss.GENERIC_TYPES)):
                    used = _block(self.values, f"sr_mod_{name}_{k}")
                    for t in types:
                        self.assertIn(f"add = var:sr_mq_{t}_{k}", used)
                        self.assertIn(f"add = global_var:sr_site_ship_{t}_{k}", used)
        self.assertIn(f"sr_mod_spec_budget = {{ value = {gss.SPEC_BUDGET} }}", self.values)

    def test_a_landing_installs_within_its_cap_and_syncs(self):
        for site in gss.SITES:
            k = site.key
            body = _block(self.effects, f"sr_mod_install_{k}")
            with self.subTest(site=k):
                self.assertIn(f"has_global_variable = sr_colony_{k}", body)
                for t in ("a", "b", *gss.GENERIC_TYPES):
                    cap = (f"sr_site_spec_built_{k} < sr_mod_spec_budget" if t in ("a", "b")
                           else f"sr_site_generic_built_{k} < {site.slots}")
                    self.assertIn(f"local_var:sr_ms_type_now = {gss.MODULE_CODES[t]} {cap}", body)
                self.assertIn(f"sr_site_sync_{k} = yes", body)

    def test_fabrication_builds_the_queue_first_in_first_out(self):
        q = gss.QUEUE_SLOTS
        month = _block(self.modules, "sr_mod_month")
        loop = _block(month, "while")
        self.assertIn("has_variable = sr_mq_1_site", _block(loop, "limit"))
        self.assertIn("sr_mod_fab_head = yes", loop)
        self.assertLess(month.index("sr_mq_recount = yes"), month.index("while"))
        head = _block(self.effects, "sr_mod_fab_head")
        # The head leaves the queue before it is built, and is built only for a world THIS holds.
        self.assertLess(head.index("sr_mq_remove_1 = yes"), head.index("sr_mod_fab_build"))
        for site in gss.SITES:
            with self.subTest(site=site.key):
                self.assertIn(f"local_var:sr_mq_head_site = {site.index} global_var:sr_site_holder_{site.key} ?= this",
                              head)
                for t in gss.MODULE_TYPES:
                    self.assertIn(f"local_var:sr_mq_head_type = {gss.MODULE_CODES[t]} }} sr_mod_fab_build = "
                                  f"{{ KEY = {site.key} TYPE = {t} CODE = {gss.MODULE_CODES[t]} INDEX = {site.index} }}",
                                  head)
        # A new entry takes the first free place; a removal moves every later entry up one.
        append = _block(self.effects, "sr_mq_append")
        self.assertEqual(re.findall(r"NOT = \{ has_variable = sr_mq_(\d+)_site \}", append),
                         [str(n) for n in range(1, q + 1)])
        for n in range(1, q + 1):
            remove = _block(self.effects, f"sr_mq_remove_{n}")
            with self.subTest(place=n):
                moves = re.findall(r"name = sr_mq_(\d+)_site value = var:sr_mq_(\d+)_site", remove)
                self.assertEqual(moves, [(str(m), str(m + 1)) for m in range(n, q)])
                self.assertIn(f"remove_variable = sr_mq_{q}_site", remove)
        queue = _block(self.modules, "sr_mod_queue")
        self.assertLess(queue.index("sr_mq_append = yes"), queue.index("sr_mq_count_add"))
        self.assertIn(f"sr_mq_has_room = {{ NOT = {{ has_variable = sr_mq_{q}_site }} }}", self.triggers)
        build = _block(self.modules, "sr_mod_fab_build")
        for line in ("change_variable = { name = sr_fab_stock subtract = sr_module_points }",
                     "sr_ms_count_add = { VAR = sr_site_ship_$TYPE$_$KEY$ }", "sr_ms_store_new = yes"):
            self.assertIn(line, build)
        self.assertNotIn("sr_mq_$TYPE$_$KEY$", build)

    def test_the_counts_follow_the_queue(self):
        recount = _block(self.effects, "sr_mq_recount")
        for site in gss.SITES:
            for t in gss.MODULE_TYPES:
                self.assertIn(f"remove_variable = sr_mq_{t}_{site.key}", recount)
        for n in range(1, gss.QUEUE_SLOTS + 1):
            self.assertIn(f"value = var:sr_mq_{n}_site", recount)
        drop = _block(self.effects[self.effects.index("\nsr_mq_drop_site = {"):], "sr_mq_drop_site")
        self.assertIn("var:sr_mq_1_site = $INDEX$", drop)
        self.assertTrue(drop.rstrip().endswith("sr_mq_recount = yes"))
        for site in gss.SITES:
            with self.subTest(site=site.key):
                self.assertIn(f"sr_mq_drop_site = {{ INDEX = {site.index} }}", _block(self.effects, f"sr_site_unmirror_{site.key}"))
                for t in ("a", "b", *gss.GENERIC_TYPES):
                    self.assertIn("sr_mq_has_room = yes", _block(self.triggers, f"sr_mod_can_queue_{t}_{site.key}"))
        self.assertIn("sr_mq_recount = yes", _block(self.effects, "sr_mq_remove_from_scope"))
        rows = self.rows[self.rows.index("type te_sr_mq_rows = flowcontainer {"):]
        for n in range(1, gss.QUEUE_SLOTS + 1):
            self.assertIn(f"GetCustom('sr_mq_{n}_world_name')", rows)
            self.assertIn(f"GetCustom('sr_mq_{n}_module_name')", rows)

    def test_the_ai_never_queues_a_placeholder(self):
        for site in gss.SITES:
            body = _block(self.effects, f"sr_mod_ai_plan_{site.key}")
            with self.subTest(site=site.key):
                self.assertEqual(set(re.findall(r"sr_mod_queue = \{ KEY = \w+ TYPE = (\w+) ", body)), {"hab", "a", "b"})
        review = _block(self.modules, "sr_mod_ai_review")
        self.assertIn("is_ai = yes", review)
        self.assertIn("days = 360", review)

    def test_shipments_move_before_the_worlds_step_under_simple_and_full(self):
        monthly = _block(self.shared, "sr_sites_global_monthly")
        self.assertLess(monthly.index("sr_ms_global_month = yes"), monthly.index("sr_sites_monthly = yes"))
        guarded = monthly[monthly.index("sr_cf_global_arrivals"):monthly.index("sr_sites_monthly = yes")]
        self.assertIn("sr_ms_global_month = yes", guarded)
        step = _block(self.modules, "sr_ms_global_month")
        self.assertLess(step.index("sr_ms_step_slot"), step.index("sr_ms_clear_counters = yes"))
        self.assertLess(step.index("sr_ms_clear_counters = yes"), step.index("sr_ms_count_slot"))
        for n in range(1, gss.SHIP_SLOTS + 1):
            self.assertIn(f"sr_ms_step_slot = {{ N = {n} }}", step)
            self.assertIn(f"sr_ms_count_slot = {{ N = {n} }}", step)
            self.assertIn(f"NOT = {{ has_variable = sr_ms_{n}_site }}", _block(self.modules, "sr_ms_store_new"))

    def test_the_base_room_fills_best_grade_first(self):
        fill = _block(self.effects, "sr_ebase_fill")
        grades = [int(g) for g in re.findall(r"# [^:]+: \d+ levels at ([+-]\d+)%", _raw(str(gss.EFFECTS_OUT)))]
        self.assertEqual(len(grades), len(gss.SITES) + 1)
        self.assertEqual(grades, sorted(grades, reverse=True))
        self.assertIn(f"value = local_var:sr_eb_left max = {gss.NEAR_EARTH_ROOM}", fill)
        for site in gss.SITES:
            with self.subTest(site=site.key):
                self.assertIn(f"global_var:sr_site_holder_{site.key} ?= this", fill)
        self.assertTrue(fill.rstrip().endswith(
            f"multiply = {gss.OVERFLOW_GRADE} add = local_var:sr_eb_sum }} }}\n\t}}"))
        room = _block(self.values, "sr_ebase_room_total")
        self.assertIn(f"value = {gss.NEAR_EARTH_ROOM}", room)
        # Each world's room counts while it serves its holder (gss.site_serves:
        # held, not blockaded, not occupied; slice 6).
        self.assertEqual(sum(int(n) for n in re.findall(r"sr_site_occupier_\w+ \} \} add = (\d+)", room)), 760)
        for site in gss.SITES:
            with self.subTest(site=site.key):
                self.assertIn(gss.site_serves(site), room)

    def test_the_refresh_averages_over_every_level(self):
        refresh = _block(self.modules, "sr_ebase_refresh")
        self.assertLess(refresh.index("remove_modifier = sr_ebase_room_bonus"), refresh.index("add_modifier"))
        self.assertLess(refresh.index("remove_modifier = sr_ebase_room_penalty"), refresh.index("add_modifier"))
        self.assertIn("value = local_var:sr_eb_sum\n\t\t\t\t\tdivide = local_var:sr_eb_levels", refresh)
        self.assertIn("sr_colonies_contested_enabled = yes", refresh)
        modifiers = _strip(_raw("common", "static_modifiers", "space_race_modifiers.txt"))
        self.assertIn("building_space_mine_throughput_add = 0.01", _block(modifiers, "sr_ebase_room_bonus"))
        self.assertIn("building_space_mine_throughput_add = -0.01", _block(modifiers, "sr_ebase_room_penalty"))
        # The owner's example: room for 10, 20 levels built, -50% past the room, -25% in all.
        self.assertEqual(10 * 0 + 10 * gss.OVERFLOW_GRADE, -25 * 20)

    def test_the_build_gates_hold_the_ai_and_private_investors_to_the_room(self):
        buildings = _strip(_raw("common", "buildings", "extra_buildings.txt"))
        mine = _block(buildings, "REPLACE_OR_CREATE:building_space_mine")
        self.assertIn("owner ?= { sr_ebase_may_build_government = yes }", _block(mine, "can_build_government"))
        self.assertIn("owner ?= { sr_ebase_may_build_private = yes }", _block(mine, "can_build_private"))
        gates = _strip(_raw("common", "scripted_triggers", "sr_colony_module_triggers.txt"))
        self.assertIn("is_ai = no", _block(gates, "sr_ebase_may_build_government"))
        self.assertNotIn("is_ai", _block(gates, "sr_ebase_may_build_private"))
        room = _block(gates, "sr_ebase_has_room")
        self.assertIn("NOT = { sr_colonies_contested_enabled = yes }", room)
        self.assertIn("sr_ebase_queued_levels < sr_ebase_room_total", room)

    def test_the_fabrication_group_is_on_the_space_program(self):
        buildings = _strip(_raw("common", "buildings", "extra_buildings.txt"))
        program = _block(buildings, "REPLACE_OR_CREATE:building_space_program")
        self.assertIn("pmg_space_program_module_fabrication", program)
        group = _strip(_raw("common", "production_method_groups", "sr_colony_module_pmgs.txt"))
        self.assertIn("ai_selection = most_productive", group)
        pms = _strip(_raw("common", "production_methods", "sr_colony_module_pms.txt"))
        points = {}
        for method in re.findall(r"(?m)^(pm_sr_fabrication_\w+) = \{", pms):
            m = re.search(r"country_sr_module_fabrication_add = (\d+)", _block(pms, method))
            if m:
                points[method] = int(m.group(1))
        self.assertEqual(points, {"pm_sr_fabrication_orbital_assembly": 5, "pm_sr_fabrication_lunar_foundries": 12,
                                  "pm_sr_fabrication_fusion_shipyards": 25})
        self.assertNotIn("building_employment_", pms)
        self.assertIn("script_only = yes", _block(_raw("common", "modifier_type_definitions",
                                                       "space_race_modifier_types.txt"),
                                                  "country_sr_module_fabrication_add"))

    def test_the_module_rows_follow_the_table(self):
        rows = self.rows[self.rows.index("type te_sr_module_rows = flowcontainer {"):]
        rows = rows[:rows.index("\ttype ", 1)] if "\ttype " in rows[1:] else rows
        names = re.findall(r'text = "sr_site_name_(\w+)"', rows)
        self.assertEqual(names, [s.key for s in gss.panel_order()])
        for site in gss.SITES:
            with self.subTest(site=site.key):
                for t in ("a", "b", *gss.GENERIC_TYPES):
                    self.assertIn(f"AddScope( 'site', MakeScopeValue( '(CFixedPoint){site.index}' ) )"
                                  f".AddScope( 'op', MakeScopeValue( '(CFixedPoint){gss.MODULE_CODES[t]}' ) )", rows)

    def test_the_cession_value_counts_the_modules(self):
        value = _block(self.values, "sr_cede_ai_input_value")
        for site in gss.SITES:
            with self.subTest(site=site.key):
                self.assertIn(f"add = {{ value = sr_site_extra_levels_{site.key} multiply = {gss.MODULE_AI_VALUE} }}", value)


class FreeColoniesTest(unittest.TestCase):
    """Autonomy, free colonies, abandonment, the covert hooks and colony life
    (slice 5, 2026-10-26-solar-colonization-free-colonies-design.md)."""

    @classmethod
    def setUpClass(cls):
        cls.effects = _strip(_raw(str(gss.EFFECTS_OUT)))
        cls.triggers = _strip(_raw(str(gss.TRIGGERS_OUT)))
        cls.values = _strip(_raw(str(gss.VALUES_OUT)))
        cls.display = _strip(_raw(str(gss.DISPLAY_OUT)))
        cls.shared = _strip(_raw("common", "scripted_effects", "sr_colony_autonomy_effects.txt"))
        cls.numbers = _strip(_raw("common", "script_values", "sr_colony_autonomy_values.txt"))
        cls.events = _strip(_raw("events", "space_race_events.txt"))
        cls.rows = _raw(str(gss.GUI_OUT))
        cls.custom_loc = _raw(str(gss.CUSTOM_LOC_OUT))

    def _number(self, name):
        return float(re.search(rf"(?m)^{name} = \{{ value = (-?[\d.]+) \}}", self.numbers).group(1))

    def test_every_world_has_its_slice_5_blocks(self):
        for site in gss.SITES:
            k = site.key
            with self.subTest(site=k):
                for name in (f"sr_site_free_or_release_{k}", f"sr_site_set_free_{k}", f"sr_site_rejoin_{k}",
                             f"sr_site_clear_ties_{k}", f"sr_site_free_step_{k}", f"sr_site_aut_step_{k}"):
                    self.assertRegex(self.effects, rf"(?m)^{name} = \{{")
                for name in (f"sr_site_autonomy_value_{k}", f"sr_site_months_since_contact_{k}",
                             f"sr_site_aut_drift_{k}", f"sr_site_charter_factor_{k}", f"sr_site_suppliers_value_{k}",
                             f"sr_free_ties_value_{k}", f"sr_free_trade_share_{k}"):
                    self.assertRegex(self.values, rf"(?m)^{name} = \{{")
                self.assertRegex(self.triggers, rf"(?m)^sr_free_may_petition_{k} = \{{")
                for name in (f"sr_disp_site_aut_{k}", f"sr_disp_site_aut_drift_{k}", f"sr_disp_site_aut_status_{k}",
                             f"sr_disp_free_{k}", f"sr_disp_free_ties_{k}", f"sr_disp_free_supplied_{k}"):
                    self.assertRegex(self.display, rf"(?m)^{name} = \{{")

    def test_a_release_clears_the_whole_slice_5_record(self):
        for site in gss.SITES:
            release = _block(self.effects, f"sr_site_release_{site.key}")
            with self.subTest(site=site.key):
                for var in gss.slice5_vars(site):
                    self.assertIn(f"remove_global_variable = {var}", release)
                self.assertIn(f"sr_site_clear_ties_{site.key} = yes", release)

    def test_a_free_colony_keeps_its_people_and_modules(self):
        for site in gss.SITES:
            k = site.key
            free = _block(self.effects, f"sr_site_set_free_{k}")
            with self.subTest(site=k):
                self.assertIn(f"set_global_variable = {{ name = sr_site_free_{k} value = yes }}", free)
                self.assertIn(f"remove_global_variable = sr_site_holder_{k}", free)
                self.assertIn(f"sr_site_sync_{k} = yes", free)
                for kept in [f"sr_site_pop_{k}", f"sr_colony_{k}", f"sr_site_spec_{k}", *gss.module_vars(site)]:
                    self.assertNotIn(f"remove_global_variable = {kept} ", free + " ")
                for gone in (f"sr_site_autonomy_{k}", f"sr_site_charter_{k}", f"sr_site_garrison_{k}"):
                    self.assertIn(f"remove_global_variable = {gone}", free)

    def test_the_monthly_step_spares_a_free_colony_and_grows_it_only_supplied(self):
        for site in gss.SITES:
            k = site.key
            monthly = _block(self.effects, f"sr_site_monthly_{k}")
            with self.subTest(site=k):
                # The adopt-or-release branch skips a free colony, which would be released after the grace.
                adopt = monthly[monthly.index("random_country"):]
                limit = monthly[:monthly.index("random_country")]
                self.assertIn(f"NOT = {{ has_global_variable = sr_site_free_{k} }}", limit[limit.rindex("else_if"):])
                self.assertIn(f"sr_site_release_{k} = yes", adopt)
                # No heir: free or released, never straight to a release.
                self.assertIn(f"sr_site_free_or_release_{k} = yes", monthly)
                # Growth needs a supplier at a free colony.
                growth = monthly[monthly.index(f"multiply = {1 + gss.GROWTH_PER_MONTH}") - 600:]
                self.assertIn(f"sr_site_suppliers_value_{k} >= 1", growth)
                self.assertIn(f"sr_site_free_step_{k} = yes", monthly)
                self.assertIn(f"sr_site_aut_step_{k} = yes", monthly)
                self.assertLess(monthly.index(f"sr_site_free_step_{k} = yes"), monthly.index(f"sr_site_suppliers_value_{k} >= 1"))
                choice = _block(self.effects, f"sr_site_free_or_release_{k}")
                self.assertIn("sr_colonies_contested_enabled = yes", choice)
                self.assertIn(f"sr_site_pop_value_{k} >= sr_free_colony_minimum", choice)

    def test_autonomy_breaks_at_100_and_asks_at_75_once_in_five_years(self):
        self.assertEqual(self._number("sr_aut_ask_level"), 75)
        self.assertEqual(self._number("sr_aut_break_level"), 100)
        for site in gss.SITES:
            k = site.key
            step = _block(self.effects, f"sr_site_aut_step_{k}")
            with self.subTest(site=k):
                self.assertIn(f"add = sr_site_aut_drift_{k}", step)
                self.assertIn("min = 0", step)
                self.assertIn("max = sr_aut_break_level", step)
                self.assertLess(step.index("sr_aut_break_away"), step.index("sr_aut_ask ="))
                self.assertIn(f"name = sr_site_aut_asked_{k} value = yes days = 1825", step)
                drift = _block(self.values, f"sr_site_aut_drift_{k}")
                for term in ("sr_aut_home_pull", "sr_aut_per_10k_people", "sr_aut_per_transit_month",
                             "sr_aut_distance_cap", "sr_aut_no_contact", "sr_aut_at_war", "sr_aut_garrisoned",
                             "sr_aut_chartered"):
                    self.assertIn(term, drift)
                self.assertIn(f"sr_transit_months_{gss.transit_body(site)}", drift)

    def test_the_charter_scales_the_specializations(self):
        self.assertEqual(self._number("sr_aut_charter_share"), 0.8)
        for site in gss.SITES:
            for slot in ("a", "b"):
                with self.subTest(site=site.key, slot=slot):
                    self.assertIn(f"multiply = sr_site_charter_factor_{site.key}",
                                  _block(self.values, f"sr_site_mult_{slot}_{site.key}"))

    def test_the_garrison_goes_home_with_a_cession(self):
        for site in gss.SITES:
            with self.subTest(site=site.key):
                self.assertIn(f"remove_global_variable = sr_site_garrison_{site.key}",
                              _block(self.effects, f"sr_site_transfer_{site.key}"))

    def test_every_dispatched_helper_exists_and_names_its_key(self):
        # The fleets' console actions (slice 6) live with the fleets.
        fleets = _strip(_raw("common", "scripted_effects", "sr_fleet_effects.txt"))
        for action in gss.SITE_ACTIONS:
            with self.subTest(action=action):
                home = fleets if action in ("debug_integrity", "debug_occupy") else self.shared
                body = _block(home, f"sr_site_{action}_at")
                self.assertIn("$KEY$", body)
        for dispatcher in ("sr_site_by_index", "sr_site_by_scope"):
            body = _block(self.effects, dispatcher)
            self.assertEqual(body.count("sr_site_$DO$_at = { KEY = "), len(gss.SITES))
        # Every DO a caller passes is one of them.
        used = set()
        for text in (self.events, self.shared, self.effects,
                     _strip(_raw("common", "scripted_guis", "sr_colony_sguis.txt")),
                     _strip(_raw("events", "te_debug_space_race_events.txt"))):
            used |= set(re.findall(r"sr_site_by_(?:index|scope) = \{ DO = (\w+) \}", text))
        self.assertTrue(used)
        self.assertLessEqual(used, set(gss.SITE_ACTIONS))

    def test_the_covert_hooks_reach_every_world(self):
        incite = _block(self.effects, "sr_cov_incite_autonomy")
        sabotage = _block(self.effects, "sr_cov_sabotage_colony")
        for site in gss.SITES:
            with self.subTest(site=site.key):
                self.assertIn(f"global_var:sr_site_holder_{site.key} ?= this", incite)
                self.assertIn(f"sr_site_pop_value_{site.key} > local_var:sr_cov_best", sabotage)
        self.assertIn("local_var:sr_cov_mult", incite)
        self.assertIn("local_var:sr_cov_mult", sabotage)
        self.assertIn("sr_site_by_index = { DO = sabotage }", sabotage)

    def test_each_event_names_its_world_and_clears_it(self):
        names = {"sr_abandon_site": 93, "sr_aut_site": 94, "sr_life_site": (95, 96, 97), "sr_freed_site": 98,
                 "sr_petition_site": 99}
        for var, ids in names.items():
            self.assertIn(f"{var}_name = {{", self.custom_loc)
            for n in (ids if isinstance(ids, tuple) else (ids,)):
                with self.subTest(event=n):
                    event = _block(self.events, f"space_race_events.{n}")
                    self.assertIn(f"trigger = {{ has_variable = {var} }}", event)
                    self.assertIn(f"sr_site_clear_event_var = {{ VAR = {var} }}", _block(event, "after"))

    def test_colony_life_stays_rare(self):
        # Owner, 2026-10-26: a few two-option events seen too often break
        # immersion. The first child once per nation; a strike or a breach
        # starts ten quiet years for both; chances in whole percents.
        month = _block(self.shared, "sr_life_month")
        first = month[:month.index("space_race_events.95")]
        self.assertIn("NOT = { has_variable = sr_life_first_child_done }", first)
        self.assertIn("set_variable = { name = sr_life_first_child_done value = yes }", first)
        for before, event in (("space_race_events.95", "space_race_events.96"),
                              ("space_race_events.96", "space_race_events.97")):
            roll = month[month.index(before):month.index(event)]
            with self.subTest(event=event):
                self.assertIn("NOT = { has_variable = sr_life_cooldown }", roll)
                self.assertIn("sr_life_start_cooldown = yes", roll)
        self.assertIn("name = sr_life_cooldown value = yes days = 3650",
                      _block(self.shared, "sr_life_start_cooldown"))
        self.assertEqual(self._number("sr_life_strike_chance"), 1)
        self.assertEqual(self._number("sr_life_breach_chance"), 1)
        self.assertIn("chance = 50", month[month.index("chance = sr_life_breach_chance"):])
        self.assertNotRegex(month, r"chance = \d+\.\d")

    def test_the_autonomy_and_free_rows_follow_the_table(self):
        for row_type in ("te_sr_autonomy_rows", "te_sr_free_rows"):
            rows = self.rows[self.rows.index(f"type {row_type} = flowcontainer {{"):]
            rows = rows[:rows.index("\ttype ", 1)] if "\ttype " in rows[1:] else rows
            with self.subTest(rows=row_type):
                self.assertEqual(re.findall(r'text = "sr_site_name_(\w+)"', rows), [s.key for s in gss.panel_order()])
        solar = self.rows[self.rows.index("type te_sr_solar_system_rows"):]
        for site in gss.SITES:
            with self.subTest(site=site.key):
                self.assertIn(f"has_global_variable = sr_site_free_{site.key} }} value = 4", self.display)
        self.assertEqual(solar.count('blockoverride "site_free_visible"'), len(gss.SITES))


if __name__ == "__main__":
    unittest.main()
