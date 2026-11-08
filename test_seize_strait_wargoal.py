# -*- coding: utf-8 -*-
"""Seize Strait war goal (te_seize_strait, 2026-11-07).

The goal takes only a state's strait shore. Strait scope has no link to its
shore provinces, so the 24 provinces are written out twice in script: in the
trigger that offers the goal (te_is_seizable_strait_shore) and in the effect
that transfers them (te_seize_strait_shores). The engine says nothing when a
province key names the wrong state region or one list drifts from the other,
so both are pinned here against SHORES, and SHORES against the base game's
strait definitions and state regions when a game install is present
(docs/systems/mod_systems/war.md § Seize Strait War Goal).
"""

import os
import re
import unittest
from pathlib import Path

REPO = os.path.dirname(os.path.abspath(__file__))

# strait -> [(province, state region)], from base 1.15's
# common/strait_definitions/strait_definitions.txt and map_data/state_regions.
SHORES = {
    "canal_panama": [("xD0EF40", "STATE_PANAMA"), ("x910E14", "STATE_PANAMA")],
    "canal_suez": [("xC01060", "STATE_SINAI"), ("x8ED45E", "STATE_SINAI")],
    "canal_kiel": [("x804160", "STATE_SCHLESWIG_HOLSTEIN"), ("xBFCC21", "STATE_SCHLESWIG_HOLSTEIN")],
    "strait_gibraltar": [("xBC6ED3", "STATE_UPPER_ANDALUSIA"), ("xA0B0C0", "STATE_AL_RIF")],
    "strait_bosporus": [("xF0A020", "STATE_EASTERN_THRACE"), ("x30A060", "STATE_HUDAVENDIGAR")],
    "strait_bab_el_mandeb": [("x319060", "STATE_YEMEN"), ("x9E8FDD", "STATE_ERITREA")],
    "strait_oresund": [("xC04161", "STATE_SCANIA"), ("x7F0BF0", "STATE_ZEALAND")],
    "strait_malacca": [("xC00130", "STATE_MALAYA"), ("x48428B", "STATE_NORTH_SUMATRA")],
    "strait_tsugaru": [("xE0D080", "STATE_TOHOKU"), ("xA090C0", "STATE_HOKKAIDO")],
    "strait_sunda": [("xDBE794", "STATE_SOUTH_SUMATRA"), ("x6345B2", "STATE_WEST_JAVA")],
    "strait_lombok": [("x5ABA94", "STATE_SUNDA_ISLANDS"), ("x100090", "STATE_SUNDA_ISLANDS")],
    "strait_hormuz": [("x0170A0", "STATE_LARISTAN"), ("x0DC972", "STATE_ABU_DHABI")],
}

# Canal straits: offered only once the canal is built (owner, 2026-11-07).
CANALS = {
    "canal_panama": ("te_panama_canal_built", "building_panama_canal", "STATE_PANAMA"),
    "canal_suez": ("te_suez_canal_built", "building_suez_canal", "STATE_SINAI"),
    "canal_kiel": ("te_kiel_canal_built", "building_kiel_canal", "STATE_SCHLESWIG_HOLSTEIN"),
}

ALL_PROVINCES = {p for shores in SHORES.values() for p, _ in shores}
REGION_OF = {p: r for shores in SHORES.values() for p, r in shores}


def _raw(*parts):
    with open(os.path.join(REPO, *parts), encoding="utf-8-sig") as f:
        return f.read()


def _strip(text):
    return re.sub(r"#[^\n]*", "", text)


def _close(text, open_brace):
    depth = 0
    for i in range(open_brace, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return i
    raise AssertionError("unclosed block")


def _block(text, name, start=0):
    """The first ``name = { ... }`` block at any depth, without its braces."""
    m = re.compile(r"(?<![\w.:$])" + re.escape(name) + r"\s*=\s*\{").search(text, start)
    if m is None:
        raise AssertionError(f"{name} not found")
    return text[m.end():_close(text, m.end() - 1)]


def _def(text, name):
    m = re.compile(r"(?m)^" + re.escape(name) + r"\s*=\s*\{").search(text)
    if m is None:
        raise AssertionError(f"{name} is not defined")
    return text[m.end():_close(text, m.end() - 1)]


GOAL = _strip(_raw("common", "war_goal_types", "te_seize_strait.txt"))
PLAY = _strip(_raw("common", "diplomatic_plays", "te_seize_strait_play.txt"))
TRIGGERS = _strip(_raw("common", "scripted_triggers", "te_seize_strait_triggers.txt"))
EFFECTS = _strip(_raw("common", "scripted_effects", "te_seize_strait_effects.txt"))
VALUES = _strip(_raw("common", "script_values", "te_seize_strait_values.txt"))


class ShoreListTests(unittest.TestCase):
    def test_trigger_names_every_shore_once(self):
        body = _def(TRIGGERS, "te_is_seizable_strait_shore")
        named = re.findall(r"this\s*=\s*p:(x[0-9A-Fa-f]{6})", body)
        self.assertEqual(len(named), len(set(named)), "a province is listed twice")
        self.assertEqual(set(named), ALL_PROVINCES)

    def test_canal_shores_wait_for_the_canal(self):
        body = _def(TRIGGERS, "te_is_seizable_strait_shore")
        canal_provinces = set()
        for strait, (trigger, building, region) in CANALS.items():
            ands = [m.end() for m in re.finditer(r"\bAND\s*=\s*\{", body)]
            found = False
            for start in ands:
                inner = body[start:_close(body, start - 1)]
                if trigger in inner:
                    provinces = set(re.findall(r"p:(x[0-9A-Fa-f]{6})", inner))
                    self.assertEqual(provinces, {p for p, _ in SHORES[strait]}, strait)
                    found = True
            self.assertTrue(found, f"{strait}'s shores aren't gated on {trigger}")
            canal_provinces |= {p for p, _ in SHORES[strait]}
            gate = _def(TRIGGERS, trigger)
            self.assertIn(f"s:{region}", gate)
            self.assertIn(f"is_building_type = {building}", gate)
            self.assertRegex(gate, r"level\s*>=\s*1", f"{trigger} counts a canal under construction")
        # Outside the AND blocks, only natural straits are listed bare.
        bare = re.sub(r"\bAND\s*=\s*\{.*?\n\t\t\}", "", body, flags=re.S)
        self.assertFalse(canal_provinces & set(re.findall(r"p:(x[0-9A-Fa-f]{6})", bare)),
                         "a canal province is offered without its canal")

    def test_effect_transfers_each_shore_in_its_own_region(self):
        body = _def(EFFECTS, "te_seize_strait_shores")
        calls = re.findall(
            r"s:(STATE_\w+)\s*=\s*\{\s*set_owner_of_provinces\s*=\s*\{\s*country\s*=\s*root\s*"
            r"provinces\s*=\s*\{([^}]*)\}",
            body,
        )
        transferred = set()
        for region, provinces in calls:
            for p in provinces.split():
                self.assertEqual(REGION_OF.get(p), region, f"{p} is transferred in {region}")
                transferred.add(p)
        self.assertEqual(transferred, ALL_PROVINCES)
        # Each region branch is guarded by that region, so a province is never
        # handed over from a state in another region.
        for region in {r for r in REGION_OF.values()}:
            self.assertRegex(body, r"state_region\s*=\s*s:" + region + r"\b", region)

    def test_paired_regions_hand_both_shores_over_in_one_call(self):
        body = _def(EFFECTS, "te_seize_strait_shores")
        for strait in ("canal_panama", "canal_suez", "canal_kiel", "strait_lombok"):
            (a, region), (b, _) = SHORES[strait]
            self.assertRegex(body, rf"s:{region}\s*=\s*\{{\s*set_owner_of_provinces\s*=\s*\{{"
                                   rf"\s*country\s*=\s*root\s*provinces\s*=\s*\{{\s*{a}\s+{b}\s*\}}", strait)

    def test_no_region_holds_two_straits(self):
        # te_seize_strait_shores's else_if ladder relies on it.
        regions = {}
        for strait, shores in SHORES.items():
            for _, region in shores:
                regions.setdefault(region, set()).add(strait)
        self.assertFalse({r: s for r, s in regions.items() if len(s) > 1})

    def test_matches_the_game_files(self):
        try:
            from path_constants import base_game_path
            game = Path(base_game_path) / "game"
        except Exception:
            game = None
        defs = game / "common/strait_definitions/strait_definitions.txt" if game else None
        if defs is None or not defs.is_file():
            self.skipTest("no Victoria 3 install")
        text = _strip(defs.read_text(encoding="utf-8-sig"))
        vanilla = {}
        for name in re.findall(r"(?m)^(\w+)\s*=\s*\{", text):
            body = _def(text, name)
            vanilla[name] = [re.search(key + r"\s*=\s*(x[0-9A-Fa-f]{6})", body).group(1)
                             for key in ("first_land_endpoint", "second_land_endpoint")]
        self.assertEqual({k: [p for p, _ in v] for k, v in SHORES.items()}, vanilla)
        region_of = {}
        for path in (game / "map_data/state_regions").glob("*.txt"):
            regions = _strip(path.read_text(encoding="utf-8-sig"))
            for name in re.findall(r"(?m)^(STATE_\w+)\s*=\s*\{", regions):
                provinces = re.search(r"provinces\s*=\s*\{([^}]*)\}", _def(regions, name))
                for p in re.findall(r"x[0-9A-Fa-f]{6}", provinces.group(1) if provinces else ""):
                    region_of[p.upper()] = name
        for p, region in REGION_OF.items():
            self.assertEqual(region_of.get(p.upper()), region, p)


class GoalShapeTests(unittest.TestCase):
    def test_custom_state_goal(self):
        goal = _def(GOAL, "te_seize_strait")
        self.assertRegex(goal, r"\bkind\s*=\s*custom\b")
        self.assertRegex(goal, r"\btarget_type\s*=\s*state\b")
        self.assertRegex(goal, r"\bcontestion_type\s*=\s*control_target_state\b")

    def test_conflicts_with_conquest_but_annexes_no_whole_state(self):
        settings = _block(_def(GOAL, "te_seize_strait"), "settings")
        for setting in ("require_target_be_part_of_war", "validate_conflicts_conquer_state",
                        "conflicts_with_annex_state", "validate_target_not_treaty_port"):
            self.assertIn(setting, settings)
        self.assertNotIn("annexes_entire_state", settings)
        self.assertNotIn("skip_build_list", settings, "the goal must be addable to a play")

    def test_enforced_only_by_peace(self):
        # A territorial mirror needs an annexation the custom kind doesn't declare.
        self.assertNotIn("mirrored_wargoal", _def(GOAL, "te_seize_strait"))

    def test_valid_and_enforcement(self):
        goal = _def(GOAL, "te_seize_strait")
        self.assertIn("te_state_has_seizable_strait_shore = yes", _block(goal, "valid"))
        enforced = _block(goal, "on_enforced")
        self.assertIn("te_seize_strait_shores = yes", _block(enforced, "scope:target_state",
                                                              enforced.index("te_seize_strait_selfcheck_before")))
        self.assertLess(enforced.index("te_seize_strait_selfcheck_before"),
                        enforced.index("te_seize_strait_shores"))
        self.assertLess(enforced.index("te_seize_strait_shores"),
                        enforced.index("te_seize_strait_selfcheck_after"))

    def test_infamy_share_is_floored_at_a_quarter(self):
        share = _def(VALUES, "te_seize_strait_infamy_share")
        self.assertRegex(share, r"(?m)^\tmin\s*=\s*0\.25\b")
        self.assertRegex(share, r"(?m)^\tmax\s*=\s*1\b")
        self.assertIn("multiply = te_seize_strait_infamy_share", _block(_def(GOAL, "te_seize_strait"), "infamy"))

    def test_play_opens_with_the_goal(self):
        self.assertRegex(_def(PLAY, "dp_te_seize_strait"), r"\bwar_goal\s*=\s*te_seize_strait\b")

    def test_localized(self):
        loc = "\n".join(
            p.read_text(encoding="utf-8-sig") for p in Path(REPO, "localization", "english").glob("*.yml"))
        for key in ("war_goal_te_seize_strait", "war_goal_te_seize_strait_desc",
                    "war_goal_te_seize_strait_sway_desc", "war_goal_te_seize_strait_type_name",
                    "war_goal_te_seize_strait_type_desc", "dp_te_seize_strait", "dp_te_seize_strait_desc",
                    "dp_te_seize_strait_tooltip", "TE_INFAMY_STRAIT_SHORE_SHARE"):
            self.assertRegex(loc, rf"(?m)^ {key}:0 \"", key)


if __name__ == "__main__":
    unittest.main()
