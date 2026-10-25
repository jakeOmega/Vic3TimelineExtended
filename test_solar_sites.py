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
- the journal entry's conditions and the panel's rows.
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
    gss.CUSTOM_LOC_OUT: "custom loc",
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


class PanelTest(unittest.TestCase):
    def test_the_solar_system_rows_follow_the_table(self):
        gui = _raw("gui", "journal_entry_widgets", "space_race_widget.gui")
        m = re.search(r"type te_sr_sec_solar_system = \w+ \{", gui)
        self.assertIsNotNone(m)
        depth, i = 1, m.end()
        while depth:
            depth += {"{": 1, "}": -1}.get(gui[i], 0)
            i += 1
        section = gui[m.end():i]
        rows = re.findall(r"text = \"sr_site_name_(\w+)\"", section)
        self.assertEqual(rows, [s.key for s in gss.panel_order()])
        for site in gss.SITES:
            with self.subTest(site=site.key):
                self.assertIn(f"Var('sr_ss_cap_{site.key}').GetState", section)
                self.assertIn(f"ScriptValue('sr_disp_site_{site.key}')", section)


if __name__ == "__main__":
    unittest.main()
