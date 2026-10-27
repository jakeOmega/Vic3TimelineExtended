"""The Market panel's All Goods tariff rows (Trade tab).

One import and one export level bar above the goods list; each of its 14
buttons is a scripted GUI that sets its level on every tradeable good. The
script setter skips the checks the engine's per-good buttons make, so the
scripted GUIs restate ownership, the trade policy and treaty bars, and keep a
cooldown of their own. Structural checks on the committed files:

* The effect's goods are the Tax Code's customs catalog (every good neither
  local nor untradeable), so a new good fails here until it is listed.
* 14 scripted GUIs, one per direction and level, each with the right checks.
* Each good's level is set behind the treaty bar its level kind needs.
* The GUI row mirrors the per-good bars' icons and order, gates each button on
  the Tax Code's native tariff gate and its own scripted GUI, and sits in the
  Trade tab of the player's own market.
* Every loc key the script and GUI name exists.

Run: python3 -m unittest test_bulk_tariffs -v
"""

import importlib.util
import json
import re
import unittest
from pathlib import Path

from test_tax_code_rule import load

ROOT = Path(__file__).resolve().parent

SGUIS = "common/scripted_guis/te_bulk_tariff_sguis.txt"
EFFECTS = "common/scripted_effects/te_bulk_tariff_effects.txt"
TRIGGERS = "common/scripted_triggers/te_bulk_tariff_triggers.txt"
WIDGETS = "gui/te_bulk_tariff_widgets.gui"
MARKET = "gui/market_panel.gui"
BUDGET = "gui/budget_panel.gui"
LOC = "localization/english/te_miscellaneous_l_english.yml"  # the effect keys
VANILLA_LOC = "vanilla_parsed/localization_english.json"

_spec = importlib.util.spec_from_file_location("gen_tax_code", ROOT / "scripts" / "generators" / "gen_tax_code.py")
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)

DIRS = ("import", "export")
# The per-good bars' order, left to right, and which treaty article can bar each.
LEVELS = (
    ("max_tariffs", "tariff"),
    ("high_tariffs", "tariff"),
    ("low_tariffs", "tariff"),
    ("no_tariffs_or_subventions", "none"),
    ("low_subventions", "subvention"),
    ("high_subventions", "subvention"),
    ("max_subventions", "subvention"),
)
ARTICLE = {"tariff": "no_tariffs", "subvention": "no_subventions"}

SCOPE = "GuiScope.SetRoot( GetPlayer.MakeScope ).End"
NATIVE_GATE = f"GetScriptedGui('te_tax_native_tariff_controls_sgui').IsValid( {SCOPE} )"


def raw(path):
    return (ROOT / path).read_text(encoding="utf-8-sig")


def block_after(text, opener):
    """The `{ ... }` body that follows the first occurrence of `opener`."""
    start = text.index("{", text.index(opener))
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start + 1:i]
    raise AssertionError(f"unbalanced block after {opener!r}")


def items(body):
    """The bodies of each `set_level_bar_item = { ... }` in a bar type."""
    out, pos = [], 0
    while (pos := body.find("set_level_bar_item = {", pos)) != -1:
        inner = block_after(body[pos:], "set_level_bar_item")
        out.append(inner)
        pos += len(inner)
    return out


def textures(body):
    return [m.group(1) for m in re.finditer(r'texture = "gfx/interface/icons/trade_icons/([\w.]+)"', body)]


def loc_keys():
    keys = set()
    for path in (ROOT / "localization" / "english").glob("*.yml"):
        keys |= set(re.findall(r"^\s*([\w.\-]+):\d*\s", path.read_text(encoding="utf-8-sig"), re.M))
    return keys


class GoodsListTest(unittest.TestCase):
    def test_every_customs_good_is_set_once(self):
        calls = load(EFFECTS)["te_bulk_tariff_all_goods"]["te_bulk_tariff_good_$KIND$"]
        self.assertEqual([c["GOOD"] for c in calls], list(gen.customs_catalog()))
        for call in calls:
            with self.subTest(good=call["GOOD"]):
                self.assertEqual(call, {"GOOD": call["GOOD"], "DIR": "$DIR$", "LEVEL": "$LEVEL$"})

    def test_local_and_untradeable_goods_are_left_out(self):
        goods = gen.goods_definitions()
        listed = {c["GOOD"] for c in load(EFFECTS)["te_bulk_tariff_all_goods"]["te_bulk_tariff_good_$KIND$"]}
        skipped = {g for g, body in goods.items() if body.get("local") == "yes" or body.get("tradeable") == "no"}
        self.assertTrue({"services", "transportation", "electricity", "digital_access", "gold"} <= skipped)
        self.assertFalse(listed & skipped)


class ScriptedGuiTest(unittest.TestCase):
    def setUp(self):
        self.sguis = load(SGUIS)

    def test_one_per_direction_and_level(self):
        expected = [f"te_bulk_tariff_{d}_{level}_sgui" for d in DIRS for level, _ in LEVELS]
        self.assertEqual(list(self.sguis), expected)

    def test_each_checks_and_sets_its_own_level(self):
        for d in DIRS:
            for level, kind in LEVELS:
                with self.subTest(dir=d, level=level):
                    sgui = self.sguis[f"te_bulk_tariff_{d}_{level}_sgui"]
                    self.assertEqual(sgui["scope"], "country")
                    self.assertEqual(sgui["ai_is_valid"], {"always": "no"})
                    valid = sgui["is_valid"]
                    self.assertEqual(valid["te_bulk_tariff_can_set"], {"DIR": d})
                    if kind == "none":
                        self.assertNotIn("te_bulk_tariff_policy_allows", valid)
                    else:
                        self.assertEqual(valid["te_bulk_tariff_policy_allows"], {"DIR": d, "KIND": kind})
                    self.assertEqual(sgui["effect"], {"te_bulk_tariff_apply": {"DIR": d, "KIND": kind, "LEVEL": level}})


class EffectTest(unittest.TestCase):
    def setUp(self):
        self.effects = load(EFFECTS)
        self.triggers = load(TRIGGERS)

    def test_each_kind_checks_its_treaty_article(self):
        for kind, article in ARTICLE.items():
            with self.subTest(kind=kind):
                body = self.effects[f"te_bulk_tariff_good_{kind}"]["if"]
                self.assertEqual(body["limit"], {"NOT": {"te_bulk_tariff_barred": {"GOOD": "$GOOD$", "ARTICLE": article}}})
                self.assertEqual(body["set_$DIR$_tariff_level"], {"goods": "g:$GOOD$", "level": "$LEVEL$"})
        self.assertEqual(self.effects["te_bulk_tariff_good_none"],
                         {"set_$DIR$_tariff_level": {"goods": "g:$GOOD$", "level": "$LEVEL$"}})

    def test_the_treaty_bar_binds_the_articles_source(self):
        article = self.triggers["te_bulk_tariff_barred"]["any_scope_treaty"]["any_scope_article"]
        self.assertEqual(article, {"has_type": "$ARTICLE$", "source_country": "scope:te_bt_country",
                                   "input_goods": "g:$GOOD$"})

    def test_cooldown_starts_only_outside_the_grace_week(self):
        hidden = self.effects["te_bulk_tariff_apply"]["hidden_effect"]
        self.assertEqual(hidden["if"]["limit"], {"NOT": {"has_variable": "te_bulk_tariff_grace_$DIR$"}})
        self.assertEqual(hidden["if"]["set_variable"], [{"name": "te_bulk_tariff_cd_$DIR$", "months": "3"},
                                                        {"name": "te_bulk_tariff_grace_$DIR$", "days": "7"},
                                                        {"name": "te_bulk_tariff_cd_day_$DIR$", "value": "game_date"}])

    def test_the_wait_says_when_it_ends(self):
        """MKT-5: while the wait runs the tooltip gives the days left, from the
        day it began; the grace week and a free row keep their own lines."""
        apply = self.effects["te_bulk_tariff_apply"]
        self.assertEqual(apply["if"], {"limit": {"has_variable": "te_bulk_tariff_grace_$DIR$"},
                                       "custom_tooltip": "te_bulk_tariff_effect_grace_$DIR$"})
        self.assertEqual(apply["else_if"], {"limit": {"has_variable": "te_bulk_tariff_cd_$DIR$"},
                                            "custom_tooltip": "te_bulk_tariff_effect_wait_$DIR$"})
        self.assertEqual(apply["else"], {"custom_tooltip": "te_bulk_tariff_effect_cd_$DIR$"})
        values = load("common/script_values/te_bulk_tariff_values.txt")
        for d in DIRS:
            body = values[f"te_bulk_tariff_cd_days_left_{d}"]["if"]
            self.assertEqual(body["limit"], {"has_variable": [f"te_bulk_tariff_cd_{d}", f"te_bulk_tariff_cd_day_{d}"]})
            self.assertEqual(body["add"], f"var:te_bulk_tariff_cd_day_{d}")
            self.assertEqual(body["subtract"], "game_date")
            line = re.search(rf"^ te_bulk_tariff_effect_wait_{d}:0 \"(.*)\"$", raw(LOC), re.M).group(1)
            self.assertIn(f"te_bulk_tariff_cd_days_left_{d}", line)
        ready = self.triggers["te_bulk_tariff_can_set"]["custom_tooltip"][2]
        self.assertEqual(ready["OR"], {"NOT": {"has_variable": "te_bulk_tariff_cd_$DIR$"},
                                       "has_variable": "te_bulk_tariff_grace_$DIR$"})

    def test_owner_and_customs_checks(self):
        owner, customs = (self.triggers["te_bulk_tariff_can_set"]["custom_tooltip"][i] for i in (1, 0))
        self.assertEqual(owner["te_tax_owns_market"], "yes")
        self.assertEqual(customs["NOT"], {"te_tax_customs_on": "yes"})

    def test_policy_reads_the_law_rate_for_its_kind(self):
        policy = self.triggers["te_bulk_tariff_policy_allows"]["custom_tooltip"]
        self.assertIn("modifier:state_$KIND$_$DIR$_add > 0", raw(TRIGGERS))
        self.assertEqual(policy["text"], "te_bulk_tariff_req_policy_$KIND$_$DIR$")
        # The four modifiers it expands to are vanilla's trade-policy rates.
        laws = json.dumps(load_vanilla_laws())
        for kind in ("tariff", "subvention"):
            for d in DIRS:
                self.assertIn(f'"state_{kind}_{d}_add"', laws)


def load_vanilla_laws():
    data = json.loads((ROOT / "vanilla_parsed" / "common" / "laws.json").read_text(encoding="utf-8"))
    return data.get("data", data)["law_protectionism"]


class GuiTest(unittest.TestCase):
    def setUp(self):
        self.widgets = raw(WIDGETS)
        self.budget = raw(BUDGET)

    def test_bom(self):
        for path in (WIDGETS, SGUIS, EFFECTS, TRIGGERS):
            with self.subTest(path=path):
                data = (ROOT / path).read_bytes()
                self.assertTrue(data.startswith(b"\xef\xbb\xbf"))
                self.assertFalse(data.startswith(b"\xef\xbb\xbf\xef\xbb\xbf"))

    def test_bars_mirror_the_per_good_bars(self):
        for d in DIRS:
            with self.subTest(dir=d):
                ours = block_after(self.widgets, f"type te_bulk_tariff_bar_{d} = flowcontainer")
                vanilla = block_after(self.budget, f"type set_level_bar_{d}_tariffs = flowcontainer")
                self.assertEqual(textures(ours), textures(vanilla))
                self.assertEqual(len(items(ours)), len(LEVELS))

    def test_each_button_runs_its_own_scripted_gui_behind_the_native_gate(self):
        for d in DIRS:
            bar = items(block_after(self.widgets, f"type te_bulk_tariff_bar_{d} = flowcontainer"))
            for (level, _), item in zip(LEVELS, bar):
                with self.subTest(dir=d, level=level):
                    sg = f"GetScriptedGui('te_bulk_tariff_{d}_{level}_sgui')"
                    self.assertIn(f'enabled = "[And( {NATIVE_GATE}, {sg}.IsValid( {SCOPE} ) )]"', item)
                    self.assertIn(f'onclick = "[{sg}.Execute( {SCOPE} )]"', item)
                    self.assertIn(f"{sg}.IsValidTooltip( {SCOPE} )", item)
                    self.assertIn(f"{sg}.ExecuteTooltip( {SCOPE} )", item)
                    self.assertIn('visible = no', item)
                    self.assertEqual(item.count("GetScriptedGui('te_bulk_tariff_"), 5, "one scripted GUI per button")

    def test_the_panel_sits_in_the_trade_tab_of_the_players_market(self):
        market = raw(MARKET)
        # The Trade tab's content, from its visibility test to the next tab's block.
        start = market.index("visible = \"[InformationPanel.IsTabSelected('world_market_trade')]\"\n"
                             "\t\t\t\t\tusing = default_fade_in_out")
        tab = market[start:market.index("market_panel_food_security_content = {", start)]
        self.assertEqual(market.count("te_bulk_tariff_panel"), 1)
        self.assertLess(tab.index("te_bulk_tariff_panel = {"), tab.index("market_world_market_goods_list_item = {}"))
        panel = block_after(tab, "te_bulk_tariff_panel")
        self.assertIn('visible = "[MarketPanel.GetMarket.IsSame( GetPlayer.GetCapital.GetMarket )]"', panel)


class LocTest(unittest.TestCase):
    def test_every_named_key_exists(self):
        keys = loc_keys()
        names = set()
        for path in (EFFECTS, TRIGGERS, WIDGETS):
            names |= set(re.findall(r"\bte_bulk_tariff_(?:effect|req|label)_[\w$]+", raw(path)))
        names.add("te_tt_break")
        subs = {"$DIR$": DIRS, "$LEVEL$": [level for level, _ in LEVELS], "$KIND$": ("tariff", "subvention")}
        expanded = set()
        for name in names:
            todo = [name]
            while todo:
                n = todo.pop()
                param = next((p for p in subs if p in n), None)
                if param is None:
                    expanded.add(n)
                else:
                    todo += [n.replace(param, v, 1) for v in subs[param]]
        self.assertEqual(len([k for k in expanded if k.startswith("te_bulk_tariff_effect_") and "_cd_" not in k
                              and "_grace_" not in k and "_wait_" not in k]), 14)
        self.assertEqual(sorted(expanded - keys), [])

    def test_level_names_are_the_games(self):
        vanilla = json.loads((ROOT / VANILLA_LOC).read_text(encoding="utf-8"))
        text = raw(LOC)
        for d in DIRS:
            for level, _ in LEVELS:
                with self.subTest(dir=d, level=level):
                    self.assertIn(level, vanilla)
                    line = re.search(rf"^ te_bulk_tariff_effect_{d}_{level}:0 \"(.*)\"$", text, re.M).group(1)
                    self.assertIn(f"${level}$", line)


if __name__ == "__main__":
    unittest.main()
