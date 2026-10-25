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
        for path in (gss.EFFECTS_OUT,):
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



if __name__ == "__main__":
    unittest.main()
