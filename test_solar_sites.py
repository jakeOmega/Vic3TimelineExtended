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
        for name in ("sr_site_hide_modifier", "sr_site_clear_discovery", "sr_site_set_discovery_done"):
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
        self.assertIn("default = space_race_enabled", body)
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
                self.assertIn(f"sr_site_room_{k} = {{ value = {site.room * 1000} }}", self.values)
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


if __name__ == "__main__":
    unittest.main()
