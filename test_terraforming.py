"""Terraforming (era 13 spec § 7.11): the technology and its colony module.

The era 13 society technology Terraforming (after Space Colonization and
Geoengineering) carries a script-only marker, country_sr_terraforming_bool,
that the colony module's queue reads (scripting_best_practices.md § Technology
markers). The module, code 16, is generic and needs crews, but only the sites
on a world in gen_solar_sites.TERRA_WORLDS take it. The work is the world's
(world_of: Mars's five sites are one world, the Moon's six another; the owner,
2026-11-28): each staffed level does a month's work a month into the world's
record (sr_world_terra_done_<world>, global, kept through a cession, a release
and a level coming down), and every colony there gains room by it. A world's
difficulty multiplies its job and its cap alike, so each takes 25 years at the
quickest; up to TERRA_MAX_LEVELS shares are added, and a finished world's
levels stand down. A save from before has its sites' own records moved into
their worlds' once. These tests pin that wiring in the generator's output and
the hand-written parts; docs/testing/era-13-playtest.md § Phase 3:
Terraforming holds the in-game checks.
"""
import glob
import os
import re
import sys
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(REPO, "scripts", "generators"))
import gen_solar_sites as gss  # noqa: E402


def _read(rel):
    with open(os.path.join(REPO, rel), encoding="utf-8-sig") as f:
        return f.read()


def _strip(text):
    return re.sub(r"#[^\n]*", "", text)


def _block(text, name):
    m = re.search(rf"(?m)^\s*{re.escape(name)}\s*=\s*\{{", text)
    if not m:
        raise AssertionError(f"no block {name}")
    depth, i = 1, m.end()
    while depth:
        depth += (text[i] == "{") - (text[i] == "}")
        i += 1
    return text[m.end():i - 1]


def _def(text, name):
    """A definition at the start of a line, not a call of it."""
    m = re.search(rf"(?m)^{re.escape(name)} = \{{", text)
    if not m:
        raise AssertionError(f"no definition {name}")
    depth, i = 1, m.end()
    while depth:
        depth += (text[i] == "{") - (text[i] == "}")
        i += 1
    return text[m.end():i - 1]


def _type_body(text, name):
    m = re.search(rf"(?m)^\ttype {re.escape(name)} = \w+ \{{", text)
    if not m:
        raise AssertionError(f"no type {name}")
    depth, i = 1, m.end()
    while depth:
        depth += (text[i] == "{") - (text[i] == "}")
        i += 1
    return text[m.end():i - 1]


def _squash(text):
    return re.sub(r"\s+", " ", text).strip()


def _loc():
    out = {}
    for path in glob.glob(os.path.join(REPO, "localization", "english", "*.yml")):
        with open(path, encoding="utf-8-sig") as f:
            for line in f:
                m = re.match(r'^ ([\w.\-]+):\d* "(.*)"\s*$', line)
                if m:
                    out[m.group(1)] = m.group(2)
    return out


EFFECTS = _strip(_read(str(gss.EFFECTS_OUT)))
TRIGGERS = _strip(_read(str(gss.TRIGGERS_OUT)))
VALUES = _strip(_read(str(gss.VALUES_OUT)))
DISPLAY = _strip(_read(str(gss.DISPLAY_OUT)))
ROWS = _read(str(gss.GUI_OUT))
WIDGET = _read("gui/journal_entry_widgets/space_race_widget.gui")
SGUIS = _strip(_read("common/scripted_guis/sr_colony_sguis.txt"))
LOC = _loc()
SITE_EFFECTS = _strip(_read("common/scripted_effects/sr_site_effects.txt"))
TERRA = [s for s in gss.SITES if gss.terraformable(s)]
OTHERS = [s for s in gss.SITES if not gss.terraformable(s)]
WORLDS = gss.terra_worlds()
SITE = {s.key: s for s in gss.SITES}
CODE = gss.MODULE_CODES["terra"]


def _w(site):
    return gss.world_of(site)


class TechnologyTest(unittest.TestCase):
    def test_the_technology(self):
        tech = _block(_strip(_read("common/technology/technologies/era_13.txt")), "terraforming")
        self.assertIn("era = era_13", tech)
        self.assertIn("category = society", tech)
        self.assertEqual(re.findall(r"^\t\t(\w+)$", _block(tech, "unlocking_technologies"), re.M),
                         ["space_colonization", "geoengineering"])
        # The colonies' marker, +50% base room at every colony (test_colony_people.BaseRoomTest),
        # and Local Climate's Winter Sun Relief at home (test_local_climate_comfort.py).
        self.assertEqual(_squash(_block(tech, "modifier")),
                         f"{gss.TERRA_MARKER} = yes {gss.ROOM_MODIFIER} = 0.5 state_climate_sun_relief_add = 0.7")
        self.assertIn("ai_weight = { value = 1 }", _squash(tech))
        # Both prerequisites are society technologies (same-category rule).
        era_12 = _strip(_read("common/technology/technologies/era_12.txt"))
        for prereq in ("space_colonization", "geoengineering"):
            with self.subTest(prereq=prereq):
                self.assertIn("category = society", _block(era_12, prereq))
        # Painted in icon batch 9.
        self.assertRegex(_read("common/technology/technologies/era_13.txt"),
                         r'terraforming = \{[^}]*texture = "gfx/interface/icons/invention_icons/terraforming\.dds"\n')
        self.assertEqual(LOC["terraforming"], "Terraforming")
        # The tooltip names the module through the marker; the description stays in the world.
        self.assertNotIn("Unlocks", LOC["terraforming_desc"])
        prompts = _read("scripts/image_pipeline/icon_prompts.py")
        self.assertRegex(prompts, r'"terraforming": \{"subject": "[^"]+", "seed": \d+\}')

    def test_the_marker(self):
        """A script-only boolean the technology's tooltip names, read by the
        module's queue and the panel, never the technology itself."""
        types = _strip(_read("common/modifier_type_definitions/space_race_modifier_types.txt"))
        body = _squash(_block(types, gss.TERRA_MARKER))
        self.assertIn("boolean = yes", body)
        self.assertIn("script_only = yes", body)
        self.assertTrue(LOC[gss.TERRA_MARKER])
        self.assertTrue(LOC[f"{gss.TERRA_MARKER}_desc"])
        for site in TERRA:
            with self.subTest(site=site.key):
                self.assertIn(f"modifier:{gss.TERRA_MARKER} = yes",
                              _block(TRIGGERS, f"sr_mod_can_queue_terra_{site.key}"))
        self.assertNotIn("has_technology_researched = terraforming", EFFECTS + TRIGGERS + VALUES + SGUIS)


class TableTest(unittest.TestCase):
    def test_the_worlds_that_take_it(self):
        """The worlds with the gravity to hold an air and a way to get one, each
        with its difficulty (the owner, 2026-11-28); not Io, nor the small bodies."""
        self.assertEqual(gss.TERRA_WORLDS, {"mars": 1, "callisto": 2, "ganymede": 2, "titan": 3, "europa": 3,
                                            "moon": 3, "venus": 4, "mercury": 5})
        self.assertEqual(set(WORLDS), set(gss.TERRA_WORLDS))
        self.assertEqual({s.key for s in gss.SITES if s.kind in ("mars", "moon")}
                         | {"venus", "mercury", "titan", "europa", "ganymede", "callisto"},
                         gss.TERRAFORMABLE)
        for key in ("io", "ceres", "enceladus", "triton", "pluto"):
            self.assertNotIn(key, gss.TERRAFORMABLE)
        self.assertEqual([len(gss.world_sites(w)) for w in ("mars", "moon")], [5, 6])
        for site in gss.SITES:
            with self.subTest(site=site.key):
                self.assertEqual(gss.terraformable(site), _w(site) in gss.TERRA_WORLDS)
                self.assertEqual("terra" in gss.module_types(site), gss.terraformable(site))
                self.assertEqual("terra" in gss.generic_types(site), gss.terraformable(site))
                self.assertEqual("terra" in gss.crewed_types(site), gss.terraformable(site))

    def test_mars_is_the_easiest(self):
        self.assertEqual(min(gss.TERRA_WORLDS.values()), 1)
        self.assertEqual([w for w, d in gss.TERRA_WORLDS.items() if d == 1], ["mars"])

    def test_its_code_comes_after_every_saved_one(self):
        """Saves keep codes 1 to 15 in their queues and shipments."""
        self.assertEqual(CODE, 16)
        self.assertEqual(max(gss.MODULE_CODES.values()), CODE)
        self.assertEqual(gss.FACILITY["terra"].name, "Terraforming")
        self.assertFalse(gss.FACILITY["terra"].ships)
        self.assertFalse(gss.FACILITY["terra"].modifier)
        self.assertEqual(gss.MODULE_LINES[-1], ("terra",))

    def test_no_other_world_has_any_of_it(self):
        everything = EFFECTS + TRIGGERS + VALUES + DISPLAY + ROWS
        for site in OTHERS:
            with self.subTest(site=site.key):
                self.assertNotRegex(everything, rf"\w*terra\w*_{site.key}\b")

    def test_the_numbers(self):
        """A share is the base room once more; three shares finish a world; a
        world's job and its cap are a site's times its difficulty times its sites,
        so every world takes 25 years at the quickest."""
        self.assertEqual(gss.TERRA_ROOM_SHARE, 1)
        self.assertEqual(gss.TERRA_LEVEL_MONTHS, 300)
        self.assertEqual(gss.TERRA_MAX_LEVELS, 3)
        self.assertEqual(gss.TERRA_FULL_MONTHS, gss.TERRA_MAX_LEVELS * gss.TERRA_LEVEL_MONTHS)
        for name, value in (("sr_terra_level_months", gss.TERRA_LEVEL_MONTHS),
                            ("sr_terra_max_levels", gss.TERRA_MAX_LEVELS),
                            ("sr_terra_full_months", gss.TERRA_FULL_MONTHS),
                            ("sr_mod_ai_terra_fill", gss.TERRA_AI_FILL)):
            with self.subTest(value=name):
                self.assertIn(f"{name} = {{ value = {value} }}", VALUES)
        for w in WORLDS:
            d, n = gss.TERRA_WORLDS[w], len(gss.world_sites(w))
            with self.subTest(world=w):
                self.assertEqual(gss.terra_cap(w), 3 * d * n)
                self.assertEqual(gss.terra_full(w), 900 * d * n)
                self.assertEqual(gss.terra_per_share(w), 300 * d * n)
                self.assertEqual(gss.terra_full(w) / gss.terra_cap(w) / 12, 25)
                self.assertIn(f"sr_terra_difficulty_{w} = {{ value = {d} }}", VALUES)
                times = "" if n == 1 else f" multiply = {n}"
                self.assertEqual(_squash(_def(VALUES, f"sr_world_terra_full_{w}")),
                                 f"value = sr_terra_full_months multiply = sr_terra_difficulty_{w}{times}")
                self.assertEqual(_squash(_def(VALUES, f"sr_world_terra_cap_{w}")),
                                 f"value = sr_terra_max_levels multiply = sr_terra_difficulty_{w}{times}")

    def test_the_loc_states_the_numbers(self):
        """Worked in full, every world gains the same a year (its cap's levels
        times a level's share), so the loc states that pace and the difficulties."""
        for w in WORLDS:
            per_year = gss.terra_cap(w) * 12 * gss.TERRA_ROOM_SHARE / gss.terra_per_share(w)
            self.assertAlmostEqual(per_year, 0.12)
        whole = f"+{gss.TERRA_MAX_LEVELS * gss.TERRA_ROOM_SHARE * 100}%"
        for key in ("je_space_race_widget_mod_terra_tt", "je_space_race_widget_terra_progress_tt",
                    "sr_mod_queue_terra_tt"):
            with self.subTest(key=key):
                self.assertIn("#v 12%#!", LOC[key])
                self.assertIn(f"#v {whole}#!", LOC[key])
                self.assertNotIn("4%", LOC[key])
        tt = LOC["je_space_race_widget_mod_terra_tt"]
        self.assertIn(f"#v {gss.TERRA_MAX_LEVELS}#! levels a site times the world's difficulty", tt)
        self.assertIn("#v 25#! years", tt)
        self.assertIn("from #v 1#! on Mars to #v 5#! on Mercury", tt)
        # The marker's description, on the technology's tooltip, lists every difficulty.
        tt = LOC["country_sr_terraforming_bool_desc"]
        names = {"mars": "Mars", "callisto": "Callisto", "ganymede": "Ganymede", "titan": "Titan",
                 "europa": "Europa", "moon": "the Moon", "venus": "Venus", "mercury": "Mercury"}
        for d in sorted(set(gss.TERRA_WORLDS.values())):
            worlds = [names[w] for w, wd in gss.TERRA_WORLDS.items() if wd == d]
            with self.subTest(difficulty=d):
                at = re.search(rf"#v {d}#! on (.+?)(?:, #v|\.(?: |$))", tt)
                self.assertIsNotNone(at)
                for name in worlds:
                    self.assertIn(name, at.group(1))
        self.assertIn("three for each colony site", LOC["sr_mod_req_terra_room_tt"])
        for name in names.values():
            self.assertIn(name, LOC["country_sr_terraforming_bool_desc"])
        self.assertEqual(LOC["sr_mq_module_terra"], "Terraforming")
        self.assertEqual(LOC["je_space_race_widget_mod_name_terra"], "Terraforming")


class RoomTest(unittest.TestCase):
    def test_room_adds_the_share_done(self):
        for site in gss.SITES:
            k = site.key
            with self.subTest(site=k):
                for name in (f"sr_site_room_{k}", f"sr_md_room_less_hab_{k}"):
                    body = _squash(_block(VALUES, name))
                    if gss.terraformable(site):
                        self.assertIn(f"add = 1 add = sr_site_terra_share_{k} multiply = sr_site_base_room_{k}", body)
                    else:
                        self.assertIn(f"add = 1 multiply = sr_site_base_room_{k}", body)
        for w in WORLDS:
            n = len(gss.world_sites(w))
            with self.subTest(world=w):
                per_site = "" if n == 1 else f" divide = {n}"
                self.assertEqual(_squash(_def(VALUES, f"sr_world_terra_share_{w}")),
                                 f"value = sr_world_terra_done_value_{w} divide = sr_terra_level_months "
                                 f"divide = sr_terra_difficulty_{w}{per_site}")
                done = _squash(_def(VALUES, f"sr_world_terra_done_value_{w}"))
                self.assertIn(f"has_global_variable = sr_world_terra_done_{w} }} value = global_var:sr_world_terra_done_{w}",
                              done)

    def test_every_colony_on_a_world_gets_its_share(self):
        """The world's share, each colony's of its own base room; a Mars site
        keeps what it had before the work was the world's as a floor."""
        for site in TERRA:
            k = site.key
            with self.subTest(site=k):
                share = _squash(_def(VALUES, f"sr_site_terra_share_{k}"))
                kept = (f" if = {{ limit = {{ has_global_variable = sr_site_terra_kept_{k} }} "
                        f"min = global_var:sr_site_terra_kept_{k} }}")
                self.assertEqual(share, f"value = sr_world_terra_share_{_w(site)}" + kept * gss.terra_kept(site))
                self.assertEqual(gss.terra_kept(site), site.kind == "mars")

    def test_the_pace_is_the_staffed_levels_and_nothing_occupied(self):
        for site in TERRA:
            k = site.key
            with self.subTest(site=k):
                rate = _squash(_block(VALUES, f"sr_site_terra_rate_{k}"))
                # Doubled where a discovery there boosts Terraforming (2026-11-25).
                self.assertIn(f"value = {gss.eff_value(site, 'terra')}", rate)
                self.assertIn(f"has_global_variable = sr_site_occupier_{k} }} value = 0", rate)
                self.assertIn(f"sr_site_terra_staffed_{k} = {{ value = sr_site_terra_value_{k} "
                              f"multiply = sr_site_staffing_{k} }}", VALUES)
                self.assertIn(f"add = sr_site_terra_value_{k}", _squash(_block(VALUES, f"sr_site_levels_{k}")))
        for w in WORLDS:
            sites = gss.world_sites(w)
            with self.subTest(world=w):
                for name, part in (("rate", "sr_site_terra_rate_"), ("levels", "sr_site_terra_value_")):
                    self.assertEqual(_squash(_def(VALUES, f"sr_world_terra_{name}_{w}")),
                                     " ".join([f"value = {part}{sites[0].key}"]
                                              + [f"add = {part}{t.key}" for t in sites[1:]]))

    def test_the_work_is_the_world_s(self):
        """A release clears the levels, not the work done; only the migration
        removes a site's record from before."""
        for site in TERRA:
            k = site.key
            with self.subTest(site=k):
                release = _block(EFFECTS, f"sr_site_release_{k}")
                self.assertIn(f"remove_global_variable = sr_site_terra_{k} ", release + " ")
                self.assertNotIn("terra_done", release)
        self.assertNotIn("remove_global_variable = sr_world_terra_done_", EFFECTS)
        outside = EFFECTS.replace(_def(EFFECTS, "sr_terra_worlds_migrate_once"), "")
        self.assertNotIn("sr_site_terra_done_", outside)
        self.assertNotIn("sr_site_terra_done_", VALUES + TRIGGERS + DISPLAY + ROWS)


class MonthTest(unittest.TestCase):
    def test_the_month_runs_before_the_projection(self):
        for site in TERRA:
            k = site.key
            with self.subTest(site=k):
                month = _block(EFFECTS, f"sr_site_monthly_{k}")
                step = month.index(f"sr_site_terra_step_{k} = {{ MONTHS = 1 }}")
                self.assertLess(step, month.index(f"sr_site_sync_{k} = yes"))
                guard = _squash(month[:step][month[:step].rindex("limit"):])
                self.assertIn("sr_colonies_contested_enabled = yes", guard)
                self.assertIn(f"sr_site_terra_value_{k} > 0", guard)

    def test_the_step_adds_the_colony_s_pace_to_its_world_and_stands_down_when_finished(self):
        for site in TERRA:
            k, w = site.key, _w(site)
            with self.subTest(site=k):
                step = _squash(_def(EFFECTS, f"sr_site_terra_step_{k}"))
                self.assertIn(f"limit = {{ sr_site_terra_rate_{k} > 0 }}", step)
                self.assertIn(f"name = sr_world_terra_done_{w} value = {{ value = sr_site_terra_rate_{k} "
                              f"multiply = $MONTHS$ add = sr_world_terra_done_value_{w} max = sr_world_terra_full_{w} }}",
                              step)
                self.assertLess(step.index("set_global_variable"), step.index("remove_global_variable"))
                self.assertIn(f"NOT = {{ sr_world_terra_open_{w} = yes }} }} remove_global_variable = sr_site_terra_{k} ",
                              step)
        for w in WORLDS:
            with self.subTest(world=w):
                self.assertEqual(TRIGGERS.count(f"sr_world_terra_open_{w} = {{"), 1)
                self.assertIn(f"sr_world_terra_open_{w} = {{ sr_world_terra_done_value_{w} < sr_world_terra_full_{w} }}",
                              TRIGGERS)

    def test_a_simulated_world(self):
        """The step's arithmetic, month by month: a world worked to its cap
        finishes in 25 years and stands down; a lone Mars colony at three levels
        does a fifth of that, and gives every colony there the room it adds."""
        def run(w, levels, staffing, months):
            done, full = 0.0, gss.terra_full(w)
            for _ in range(months):
                if levels:
                    done = min(done + levels * staffing, full)
                    if done >= full:
                        levels = 0
            return done / gss.terra_per_share(w) * gss.TERRA_ROOM_SHARE, levels
        for w in WORLDS:
            with self.subTest(world=w):
                cap = gss.terra_cap(w)
                self.assertEqual(run(w, cap, 1, 300), (3, 0))
                self.assertEqual(run(w, cap, 1, 299)[1], cap)
        self.assertAlmostEqual(run("mars", 3, 1, 300)[0], 0.6)
        self.assertAlmostEqual(run("venus", 3, 1, 300)[0], 0.75)
        self.assertAlmostEqual(run("titan", 2, 0.5, 120)[0], 0.4 / 3)


class MigrationTest(unittest.TestCase):
    """A save from before (1.3.0 to 1.4.0): each site kept its own record."""

    def test_it_runs_once_before_the_worlds_month(self):
        monthly = _def(SITE_EFFECTS, "sr_sites_global_monthly")
        self.assertLess(monthly.index("sr_terra_worlds_migrate_once = yes"), monthly.index("sr_sites_monthly = yes"))
        body = _squash(_def(EFFECTS, "sr_terra_worlds_migrate_once"))
        self.assertTrue(body.startswith("if = { limit = { NOT = { has_global_variable = sr_terra_worlds_migrated } } "
                                        "set_global_variable = { name = sr_terra_worlds_migrated value = yes }"))

    def test_each_old_record_goes_to_its_world(self):
        body = _squash(_def(EFFECTS, "sr_terra_worlds_migrate_once"))
        self.assertLessEqual(set(gss.TERRA_V1_SITES), gss.TERRAFORMABLE)
        for w in WORLDS:
            old = [s.key for s in gss.world_sites(w) if s.key in gss.TERRA_V1_SITES]
            with self.subTest(world=w):
                if not old:
                    self.assertNotIn(f"sr_world_terra_done_{w}", body)
                    continue
                adds = " ".join(f"if = {{ limit = {{ has_global_variable = sr_site_terra_done_{k} }} "
                                f"add = global_var:sr_site_terra_done_{k} }}" for k in old)
                self.assertIn(f"name = sr_world_terra_done_{w} value = {{ value = 0 {adds} "
                              f"multiply = sr_terra_difficulty_{w} max = sr_world_terra_full_{w} }}", body)
        for k in gss.TERRA_V1_SITES:
            with self.subTest(site=k):
                self.assertIn(f"if = {{ limit = {{ has_global_variable = sr_site_terra_done_{k} }} "
                              f"remove_global_variable = sr_site_terra_done_{k} }}", body)
                kept = f"name = sr_site_terra_kept_{k} value = {{ value = global_var:sr_site_terra_done_{k} " \
                       "divide = sr_terra_level_months }"
                self.assertEqual(kept in body, gss.terra_kept(SITE[k]))

    def test_no_colony_loses_room(self):
        """The arithmetic: a one-site world keeps its share exactly; Mars pools
        its five, and each keeps at least the share it had."""
        def migrate(w, old):
            return min(sum(old) * gss.terra_difficulty(w), gss.terra_full(w)) / gss.terra_per_share(w)
        for w in ("venus", "titan", "ganymede", "callisto"):
            for months in (0, 1, 450, 900):
                with self.subTest(world=w, months=months):
                    self.assertAlmostEqual(migrate(w, [months]), months / gss.TERRA_LEVEL_MONTHS)
        old = [900, 0, 300, 0, 0]
        pooled = migrate("mars", old)
        self.assertAlmostEqual(pooled, 0.8)
        for months in old:
            self.assertGreaterEqual(max(pooled, months / gss.TERRA_LEVEL_MONTHS), months / gss.TERRA_LEVEL_MONTHS)
        self.assertAlmostEqual(migrate("mars", [900] * 5), 3)


class QueueTest(unittest.TestCase):
    def test_the_queue_gate(self):
        for site in TERRA:
            k, w = site.key, _w(site)
            with self.subTest(site=k):
                can = _squash(_block(TRIGGERS, f"sr_mod_can_queue_terra_{k}"))
                self.assertNotIn("slots", can)
                for cond in (f"global_var:sr_site_holder_{k} ?= this", "sr_mq_has_room = yes",
                             f"modifier:{gss.TERRA_MARKER} = yes",
                             f"sr_world_terra_used_{w} < sr_world_terra_cap_{w}", f"sr_world_terra_open_{w} = yes"):
                    self.assertIn(cond, can)

    def test_the_cap_counts_every_holder_on_the_world(self):
        """Built, in the holder's queue, or on its way, at every site there."""
        for w in WORLDS:
            with self.subTest(world=w):
                used = _squash(_def(VALUES, f"sr_world_terra_used_{w}"))
                self.assertTrue(used.startswith(f"value = sr_world_terra_levels_{w} "))
                for t in gss.world_sites(w):
                    k = t.key
                    self.assertIn(f"if = {{ limit = {{ global_var:sr_site_holder_{k} ?= {{ has_variable = sr_mq_terra_{k} }} }} "
                                  f"global_var:sr_site_holder_{k} = {{ add = var:sr_mq_terra_{k} }} }}", used)
                    self.assertIn(f"if = {{ limit = {{ has_global_variable = sr_site_ship_terra_{k} }} "
                                  f"add = global_var:sr_site_ship_terra_{k} }}", used)
                self.assertNotIn("sr_mod_terra_used_", VALUES + TRIGGERS)

    def test_the_scripted_gui(self):
        sgui = _squash(_block(SGUIS, "sr_colony_module_sgui"))
        terra = sgui[sgui.index(f"limit = {{ scope:op = {CODE} }} custom_tooltip = {{ text = sr_mod_req_terra_tech_tt"):]
        for line in (f"text = sr_mod_req_terra_tech_tt modifier:{gss.TERRA_MARKER} = yes",
                     "text = sr_mod_req_terra_room_tt sr_mod_scope_terra_room = yes",
                     "text = sr_mod_req_terra_open_tt sr_mod_scope_terra_open = yes"):
            self.assertIn(line, terra)
        self.assertIn(f"limit = {{ scope:op = {CODE} }} custom_tooltip = {{ text = sr_mod_queue_terra_tt "
                      "sr_mod_queue_from_scope = yes }", sgui)
        for name in ("sr_mod_scope_terra_room", "sr_mod_scope_terra_open"):
            body = _block(TRIGGERS, name)
            with self.subTest(trigger=name):
                self.assertEqual(re.findall(r"scope:site = (\d+)", body), [str(s.index) for s in TERRA])
        room = _squash(_block(TRIGGERS, "sr_mod_scope_terra_room"))
        is_open = _squash(_block(TRIGGERS, "sr_mod_scope_terra_open"))
        for site in TERRA:
            w = _w(site)
            with self.subTest(site=site.key):
                self.assertIn(f"AND = {{ scope:site = {site.index} sr_world_terra_used_{w} < sr_world_terra_cap_{w} }}", room)
                self.assertIn(f"AND = {{ scope:site = {site.index} sr_world_terra_open_{w} = yes }}", is_open)

    def test_a_landing_and_the_queue_s_head(self):
        for site in TERRA:
            k, w = site.key, _w(site)
            with self.subTest(site=k):
                install = _squash(_block(EFFECTS, f"sr_mod_install_{k}"))
                self.assertIn(f"local_var:sr_ms_type_now = {CODE} "
                              f"sr_world_terra_levels_{w} < sr_world_terra_cap_{w} sr_world_terra_open_{w} = yes", install)
                self.assertIn(f"local_var:sr_mq_head_site = {site.index}", _block(EFFECTS, "sr_mod_fab_head"))
                self.assertIn(f"local_var:sr_mq_head_type = {CODE} sr_world_terra_open_{w} = yes }} sr_mod_fab_build",
                              _squash(_block(EFFECTS, "sr_mod_fab_head")))

    def test_the_ai_terraforms_a_filling_world_within_its_crews(self):
        for site in TERRA:
            k = site.key
            with self.subTest(site=k):
                plan = _squash(_block(EFFECTS, f"sr_mod_ai_plan_{k}"))
                terra = plan[plan.index(f"sr_mod_can_queue_terra_{k} = yes"):]
                terra = terra[:terra.index("}", terra.index("sr_mod_queue = {"))]
                self.assertNotIn("slots", terra)
                for cond in (f"sr_site_fill_{k} >= sr_mod_ai_terra_fill", f"sr_site_crews_{k} >= sr_site_levels_{k}"):
                    self.assertIn(cond, terra)
                order = [plan.index(f"sr_mod_can_queue_{t}_{k}") for t in ("mine", "terra", "bunker")]
                self.assertEqual(order, sorted(order))


class PanelTest(unittest.TestCase):
    def test_the_widget_hides_it_by_default(self):
        # the list's row (its Modules line) and the colony's page (its tile and its module row)
        row = _type_body(WIDGET, "te_sr_colony_row") + _type_body(WIDGET, "te_sr_colony_page")
        self.assertEqual(_squash(row).count('block "terra_visible" { visible = no }'), 3)
        for block in ("mod_terra_level", "mod_terra_pending", "mod_terra_button", "mod_terra_dismantle_button",
                      "terra_pct", "terra_years", "terra_idle_visible", "terra_under_way_visible",
                      "terra_finished_visible"):
            with self.subTest(block=block):
                self.assertIn(f'block "{block}" {{}}', row)
        self.assertIn('text = "je_space_race_widget_mod_name_terra"', row)
        self.assertIn('text = "je_space_race_widget_page_terraformed"', row)

    def test_each_world_that_takes_it_shows_it(self):
        for site in gss.SITES:
            k = site.key
            with self.subTest(site=k):
                shown = f"ScriptValue('sr_disp_terra_shown_{k}')"
                self.assertEqual(shown in ROWS, gss.terraformable(site))
                op = (f"AddScope( 'site', MakeScopeValue( '(CFixedPoint){site.index}' ) )"
                      f".AddScope( 'op', MakeScopeValue( '(CFixedPoint){CODE}' ) )")
                self.assertEqual(op in ROWS, gss.terraformable(site))
        for site in TERRA:
            k, w = site.key, _w(site)
            with self.subTest(site=k):
                shown = _squash(_block(DISPLAY, f"sr_disp_terra_shown_{k}"))
                for cond in (f"modifier:{gss.TERRA_MARKER} = yes", f"sr_site_terra_value_{k} > 0",
                             f"sr_world_terra_done_value_{w} > 0", f"sr_disp_mod_pending_terra_{k} > 0"):
                    self.assertIn(cond, shown)
                self.assertEqual(_squash(_def(DISPLAY, f"sr_disp_terra_pct_{k}")),
                                 f"value = sr_site_terra_share_{k} multiply = 100 floor = yes")
                for name in ("years", "state"):
                    self.assertIn(f"ScriptValue('sr_disp_terra_{name}_{w}')", ROWS)
        for w in WORLDS:
            with self.subTest(world=w):
                state = _squash(_def(DISPLAY, f"sr_disp_terra_state_{w}"))
                self.assertIn(f"NOT = {{ sr_world_terra_open_{w} = yes }} }} value = 2", state)
                self.assertIn(f"sr_world_terra_rate_{w} > 0 }} value = 1", state)
                years = _squash(_def(DISPLAY, f"sr_disp_terra_years_{w}"))
                self.assertIn(f"value = sr_world_terra_full_{w} subtract = sr_world_terra_done_value_{w} "
                              f"divide = sr_world_terra_rate_{w} divide = 12 ceiling = yes max = 999", years)

    def test_the_icon_is_kept_art(self):
        """The page's row and tile show the Mars colony's icon, art the panel
        already has (space_race_gui_icons.md, Kept)."""
        row = _type_body(WIDGET, "te_sr_colony_page")
        page = row[row.index('block "terra_visible" {', row.index("te_sr_page_tile")):]
        self.assertIn('texture = "gfx/interface/icons/space_race_icons/colony_mars.dds"', page)
        self.assertIn("Terraforming", _read("docs/systems/space_race_gui_icons.md"))


class ConsoleTest(unittest.TestCase):
    def test_ten_years_from_the_console(self):
        event = _squash(_block(_strip(_read("events/te_debug_space_race_events.txt")), "te_debug_space_race.4"))
        self.assertIn("name = te_debug_space_race.4.i trigger = { sr_colonies_contested_enabled = yes } "
                      "sr_terra_debug_advance = yes }", event)
        self.assertTrue(LOC["te_debug_space_race.4.i"])
        advance = _squash(_block(EFFECTS, "sr_terra_debug_advance"))
        # Every step first, then every colony's sync, so each sees its world's ten years.
        last_step = max(advance.index(f"sr_site_terra_step_{s.key} = {{ MONTHS = 120 }}") for s in TERRA)
        for site in TERRA:
            k = site.key
            with self.subTest(site=k):
                self.assertIn(f"if = {{ limit = {{ global_var:sr_site_holder_{k} ?= this }} "
                              f"sr_site_terra_step_{k} = {{ MONTHS = 120 }} }}", advance)
                sync = f"if = {{ limit = {{ has_global_variable = sr_colony_{k} }} sr_site_sync_{k} = yes }}"
                self.assertIn(sync, advance)
                self.assertGreater(advance.index(sync), last_step)


if __name__ == "__main__":
    unittest.main()
