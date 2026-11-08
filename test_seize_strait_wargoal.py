# -*- coding: utf-8 -*-
"""Seize Strait war goal (te_seize_strait, 2026-11-07).

The goal takes only a state's strait shore. Strait scope has no link to its
shore provinces, so the 24 provinces are written out twice in script: in the
count that offers the goal (te_seize_strait_shore_provinces) and in the effect
that transfers them (te_seize_strait_shores). The engine says nothing when a
province key names the wrong state region or one list drifts from the other,
so both are pinned here against SHORES, and SHORES against the mod's state
regions and, with a game install, the base game's strait definitions
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

HOLDS = r"this\s*=\s*p:(x[0-9A-Fa-f]{6})\.state"
CALL = (r"limit\s*=\s*\{([^{}]*)\}\s*s:(STATE_\w+)\s*=\s*\{\s*set_owner_of_provinces\s*=\s*\{\s*"
        r"country\s*=\s*root\s*provinces\s*=\s*\{([^}]*)\}")


def _ifs(body):
    """The top-level ``if = { ... }`` blocks of a script body, without their braces."""
    out, depth, i = [], 0, 0
    while i < len(body):
        ch = body[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        elif depth == 0:
            m = re.compile(r"if\s*=\s*\{").match(body, i)
            if m and (i == 0 or not (body[i - 1].isalnum() or body[i - 1] == "_")):
                close = _close(body, m.end() - 1)
                out.append(body[m.end():close])
                i = close + 1
                continue
        i += 1
    return out


class ShoreListTests(unittest.TestCase):
    def test_the_count_names_every_shore_once(self):
        named = re.findall(HOLDS, _def(VALUES, "te_seize_strait_shore_provinces"))
        self.assertEqual(len(named), len(set(named)), "a province is listed twice")
        self.assertEqual(set(named), ALL_PROVINCES)

    def test_the_offer_reads_the_count(self):
        self.assertRegex(_def(TRIGGERS, "te_state_has_seizable_strait_shore"),
                         r"^\s*te_seize_strait_shore_provinces\s*>\s*0\s*$")

    def test_canal_shores_wait_for_the_canal(self):
        blocks = _ifs(_def(VALUES, "te_seize_strait_shore_provinces"))
        gated = {}
        bare = set()
        for block in blocks:
            gate = re.match(r"\s*limit\s*=\s*\{\s*(te_\w+_canal_built)\s*=\s*yes\s*\}", block)
            provinces = set(re.findall(HOLDS, block))
            if gate:
                gated[gate.group(1)] = provinces
            else:
                bare |= provinces
        for strait, (trigger, building, region) in CANALS.items():
            self.assertEqual(gated.get(trigger), {p for p, _ in SHORES[strait]}, strait)
            gate = _def(TRIGGERS, trigger)
            self.assertIn(f"s:{region}", gate)
            self.assertIn(f"is_building_type = {building}", gate)
            self.assertRegex(gate, r"level\s*>=\s*1", f"{trigger} counts a canal under construction")
        canal_provinces = {p for strait in CANALS for p, _ in SHORES[strait]}
        self.assertFalse(canal_provinces & bare, "a canal province is counted without its canal")
        self.assertEqual(bare, ALL_PROVINCES - canal_provinces)

    def test_each_transfer_moves_the_provinces_its_guard_tested(self):
        body = _def(EFFECTS, "te_seize_strait_shores")
        transferred = set()
        calls = list(re.finditer(CALL, body))
        self.assertTrue(calls)
        for m in calls:
            limit, region, provinces = m.group(1), m.group(2), set(m.group(3).split())
            # The guard just before the call tests exactly the provinces it hands over...
            self.assertEqual(set(re.findall(HOLDS, limit)), provinces, f"{region}: {provinces}")
            # ...in the region the branch is guarded on, which is the call's own.
            guards = re.findall(r"state_region\s*=\s*s:(STATE_\w+)", body[:m.end()])
            self.assertEqual(guards[-1], region, f"{provinces} handed over under {guards[-1]}'s guard")
            for p in provinces:
                self.assertEqual(REGION_OF.get(p), region, f"{p} is transferred in {region}")
            transferred |= provinces
        self.assertEqual(transferred, ALL_PROVINCES)

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

    def test_no_province_iterator_runs_from_a_state(self):
        # The engine registers the province iterators from a province: from a
        # state they log "Wrong scope" and do nothing (scripting_best_practices.md,
        # 2026-10-16). Only a script value's every_province reads a state's provinces.
        for name, text in (("triggers", TRIGGERS), ("effects", EFFECTS), ("war goal", GOAL)):
            self.assertNotRegex(text, r"\b(any|every|random|ordered)_province\s*=", name)

    def test_regions_match_the_mods_state_regions(self):
        # The mod ships every state_regions file, so the engine reads these.
        region_of = {}
        for path in Path(REPO, "map_data", "state_regions").glob("*.txt"):
            regions = _strip(path.read_text(encoding="utf-8-sig"))
            for name in re.findall(r"(?m)^(STATE_\w+)\s*=\s*\{", regions):
                provinces = re.search(r"provinces\s*=\s*\{([^}]*)\}", _def(regions, name))
                for p in re.findall(r"x[0-9A-Fa-f]{6}", provinces.group(1) if provinces else ""):
                    region_of[p.upper()] = name
        self.assertTrue(region_of, "no state regions read")
        for p, region in REGION_OF.items():
            self.assertEqual(region_of.get(p.upper()), region, p)

    def test_matches_the_game_strait_definitions(self):
        # strait_definitions is not in vanilla_parsed/, so this half needs a game install.
        try:
            from path_constants import base_game_path
            defs = Path(base_game_path) / "game/common/strait_definitions/strait_definitions.txt"
        except Exception:
            defs = None
        if defs is None or not defs.is_file():
            self.skipTest("no Victoria 3 install")
        text = _strip(defs.read_text(encoding="utf-8-sig"))
        vanilla = {}
        for name in re.findall(r"(?m)^(\w+)\s*=\s*\{", text):
            body = _def(text, name)
            vanilla[name] = [re.search(key + r"\s*=\s*(x[0-9A-Fa-f]{6})", body).group(1)
                             for key in ("first_land_endpoint", "second_land_endpoint")]
        self.assertEqual({k: [p for p, _ in v] for k, v in SHORES.items()}, vanilla)


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
        guarded = _block(enforced, "if")
        self.assertRegex(_block(guarded, "limit"), r"scope:target_state\s*\?=\s*\{\s*owner\s*=\s*scope:target_country\s*\}")
        self.assertIn("te_seize_strait_shores = yes",
                      _block(guarded, "scope:target_state", guarded.index("te_seize_strait_selfcheck_before")))
        self.assertLess(guarded.index("te_seize_strait_selfcheck_before"), guarded.index("te_seize_strait_shores"))
        self.assertLess(guarded.index("te_seize_strait_shores"), guarded.index("te_seize_strait_selfcheck_after"))

    def test_self_check_passes_only_on_more_shore(self):
        # Owning land in the region proves nothing: the holder usually does already.
        after = _def(EFFECTS, "te_seize_strait_selfcheck_after")
        self.assertRegex(_block(after, "limit"),
                         r"global_var:te_ss_chk_shores_after\s*>\s*global_var:te_ss_chk_shores_before")
        self.assertIn("value = te_ss_holder_region_shores", _def(EFFECTS, "te_seize_strait_selfcheck_before"))

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
