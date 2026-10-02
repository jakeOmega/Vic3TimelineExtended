"""Execute the annual store's actual script in a small offline test harness.

This checks calendar guards and swap-removal/sorting without Victoria 3.
It does not prove engine scope behavior or the GUI binding/layout; those
remain explicit in-game checks in the PR and system documentation.
"""
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
import re
import unittest

from paradox_file_parser import ParadoxFileParser
from test_cultural_hegemony_layout import _type_body
from test_history_chart_tooltip_context import _closure, _data_roots, _load_loc

ROOT = Path(__file__).parent


def read(path):
    return (ROOT / path).read_text(encoding="utf-8-sig")


def entries(node):
    for part in node if isinstance(node, list) else [node]:
        for key, (op, value) in part.items():
            yield key, op, value


def config(node):
    return {key: value for key, _, value in entries(node)}


@dataclass(eq=False)
class Container:
    variables: dict = field(default_factory=dict)
    lists: dict = field(default_factory=dict)
    tags: set = field(default_factory=set)


class StoreHarness:
    """Only the documented effect/trigger subset used by this store.

    Unknown syntax fails instead of being silently ignored. List removal
    intentionally swaps in the last element, matching the observed engine
    behavior that requires the post-eviction sort.
    """
    def __init__(self):
        parser = ParadoxFileParser()
        source = read("common/scripted_effects/te_history_cultural_hegemony_effects.txt")
        self.effects = config(parser.parse_object(parser.tokenize("{" + source + "}"))[0])
        self.globals = {}
        self.scopes = {}
        self.live = []
        self.year, self.month, self.enabled = 1900, 1, True

    def value(self, text, scope):
        if text.startswith("global_var:"):
            return self.globals.get(text[11:], Decimal(0))
        if text.startswith("scope:"):
            target, _, variable = text[6:].partition(".var:")
            obj = self.scopes.get(target)
            return obj.variables[variable] if variable else obj
        if text.startswith("var:"):
            return scope.variables[text[4:]]
        if text == "te_history_current_year":
            return Decimal(self.year)
        if text == "te_history_current_month":
            return Decimal(self.month)
        if text == "ch_model_hist_total_share":
            return sum(self.globals.get(f"ch_ideology_{m}_share", Decimal(0)) for m in MODELS)
        return Decimal(text)

    def condition(self, node, scope):
        outcomes = []
        for key, op, item in entries(node):
            if key in ("OR", "NOT"):
                checks = [self.condition({k: (o, v)}, scope) for k, o, v in entries(item)]
                result = any(checks) if key == "OR" else not all(checks)
            elif key == "has_game_rule":
                result = self.enabled
            elif key == "has_global_variable":
                result = item in self.globals
            elif key == "has_variable_list":
                result = item in scope.lists
            elif key == "exists":
                result = self.value(item, scope) is not None
            elif key == "any_in_list":
                cfg = config(item)
                count = sum(cfg["has_tag"] in obj.tags for obj in scope.lists.get(cfg["variable"], []))
                result = count >= int(cfg["count"])
            else:
                left, right = self.value(key, scope), self.value(item, scope)
                result = {"<": left < right, ">": left > right, "=": left == right}[op]
            outcomes.append(result)
        return all(outcomes)

    def run(self, name, scope=None, params=None):
        node = self.effects[name]
        if params:
            source = repr(node)
            for key, value in params.items():
                source = source.replace(f"${key}$", value)
            import ast
            node = ast.literal_eval(source)
        self.execute(node, scope)

    def execute(self, node, scope):
        for key, _, item in entries(node):
            if key == "hidden_effect":
                self.execute(item, scope)
            elif key == "if":
                body = [(k, o, v) for k, o, v in entries(item)]
                if self.condition(next(v for k, _, v in body if k == "limit"), scope):
                    self.execute([{k: (o, v)} for k, o, v in body if k != "limit"], scope)
            elif key == "create_container":
                cfg = config(item)
                obj = Container(tags=set(cfg["tags"]))
                self.live.append(obj)
                self.scopes[cfg["save_scope_as"]] = obj
            elif key in ("set_variable", "set_global_variable"):
                cfg = config(item)
                target = self.globals if key == "set_global_variable" else scope.variables
                target[cfg["name"]] = self.value(cfg["value"], scope)
            elif key == "change_variable":
                cfg = config(item)
                name = cfg.pop("name")
                operation, operand = next(iter(cfg.items()))
                value = self.value(operand, scope)
                if operation == "add":
                    scope.variables[name] += value
                elif operation == "divide":
                    scope.variables[name] /= value
                elif operation == "multiply":
                    scope.variables[name] *= value
                else:
                    raise AssertionError(operation)
            elif key == "clamp_variable":
                cfg = config(item)
                scope.variables[cfg["name"]] = max(Decimal(cfg["min"]), min(Decimal(cfg["max"]), scope.variables[cfg["name"]]))
            elif key == "remove_variable":
                scope.variables.pop(item)
            elif key.startswith(("global_var:", "scope:")):
                self.execute(item, self.value(key, scope))
            elif key == "save_scope_as":
                self.scopes[item] = scope
            elif key == "add_to_variable_list":
                cfg = config(item)
                scope.lists.setdefault(cfg["name"], []).append(self.value(cfg["target"], scope))
            elif key == "remove_list_variable":
                cfg = config(item)
                items = scope.lists[cfg["name"]]
                idx = items.index(self.value(cfg["target"], scope))
                items[idx] = items[-1]
                items.pop()
            elif key == "clear_variable_list":
                scope.lists.pop(item, None)
            elif key == "destroy_container":
                self.live.remove(scope)
            elif key == "ordered_in_list":
                cfg = config(item)
                assert cfg["order_by"] == "te_history_sample_order"
                items = sorted(scope.lists[cfg["variable"]], key=lambda c: -c.variables["te_hist_i"], reverse=True)
                if "position" in cfg:
                    items = items[int(cfg["position"]):int(cfg["position"]) + 1]
                else:
                    items = items[int(cfg["min"]):int(cfg["max"])]
                body = [{k: (o, v)} for k, o, v in entries(item) if k not in {"variable", "order_by", "position", "min", "max", "check_range_bounds"}]
                for obj in items:
                    self.execute(body, obj)
            elif key in self.effects:
                self.run(key, scope, None if item == "yes" else config(item))
            else:
                raise AssertionError(f"unsupported effect: {key}")

    def sample(self):
        self.scopes = {}  # saved scopes belong to one invocation, not the save
        self.run("te_history_record_cultural_hegemony_models")

    @property
    def samples(self):
        store = self.globals.get("ch_model_hist_store")
        return store.lists.get("ch_model_hist", []) if store else []


PALETTE = re.findall(r'\("(\w+)", "(#[0-9a-f]+)"\)', read("scripts/image_pipeline/gen_ch_model_pie_textures.py").split("UN_PIES:")[0])
MODELS = [m for m, _ in PALETTE]


class CulturalHegemonyHistoryTests(unittest.TestCase):
    def setUp(self):
        self.h = StoreHarness()
        for index, model in enumerate(MODELS):
            self.h.globals[f"ch_ideology_{model}_share"] = Decimal(index + 1)

    def test_rebuilds_in_one_year_are_immutable_across_country_switches(self):
        self.h.sample()
        first = self.h.samples[0]
        original = first.variables.copy()
        for country in (Container(), Container(), Container()):
            self.h.month = 7
            self.h.globals["ch_ideology_republican_share"] = Decimal(90)
            self.h.scopes = {}
            self.h.run("te_history_record_cultural_hegemony_models", country)
            self.assertFalse(country.variables or country.lists)
        self.assertEqual(self.h.samples, [first])
        self.assertEqual(first.variables, original)
        self.h.year += 1
        self.h.sample()
        self.assertEqual(len(self.h.samples), 2)

    def test_existing_save_starts_now_and_does_not_backfill(self):
        self.h.year = 2020
        self.h.sample()
        self.h.year = 2023
        self.h.sample()
        self.assertEqual([c.variables["te_hist_y"] for c in self.h.samples], [2020, 2023])

    def test_eviction_destroys_oldest_and_repairs_swap_order(self):
        for year in range(1836, 1986):
            self.h.year = year
            self.h.sample()
        self.assertEqual([c.variables["te_hist_y"] for c in self.h.samples], list(range(1886, 1986)))
        self.assertEqual(len(self.h.live), 101)  # one store plus 100 samples
        self.assertEqual(self.h.globals["ch_model_hist_since_y"], 1886)
        self.assertNotIn("ch_model_hist_tmp", self.h.globals["ch_model_hist_store"].lists)

    def test_distribution_is_normalized_and_zero_models_stay_zero(self):
        self.h.globals["ch_ideology_republican_share"] = Decimal(0)
        self.h.sample()
        values = self.h.samples[0].variables
        self.assertEqual(values["ch_model_hist_republican"], 0)
        self.assertAlmostEqual(sum(values[f"ch_model_hist_{m}"] for m in MODELS), Decimal(100))
        cumulative = [values[f"ch_model_hist_cum_{m}"] for m in MODELS]
        self.assertEqual(cumulative, sorted(cumulative))
        self.assertEqual(cumulative[-1], 100)
        self.assertFalse(any(k in values for k in ("ch_model_hist_total", "ch_model_hist_cumulative")))

    def test_player_view_lists_the_store_oldest_first_and_follows_eviction(self):
        player = Container()
        self.h.run("te_history_mirror_ch_models", player)
        self.assertNotIn("ch_model_hist_view", player.lists)  # no store yet
        for year in range(1836, 1936):
            self.h.year = year
            self.h.sample()
        self.h.run("te_history_mirror_ch_models", player)
        view = player.lists["ch_model_hist_view"]
        self.assertEqual(view, self.h.samples)  # the same containers, not copies
        self.assertEqual([c.variables["te_hist_y"] for c in view], list(range(1836, 1936)))
        self.h.year = 1936
        self.h.sample()  # evicts 1836
        self.h.run("te_history_mirror_ch_models", player)
        view = player.lists["ch_model_hist_view"]
        self.assertEqual([c.variables["te_hist_y"] for c in view], list(range(1837, 1937)))
        self.assertTrue(all(c in self.h.live for c in view))
        self.assertNotIn("ch_model_hist_view", self.h.globals["ch_model_hist_store"].lists)

    def test_player_view_is_rebuilt_by_the_census_and_monthly(self):
        effects = read("common/scripted_effects/cultural_hegemony_effects.txt")
        record = effects.index("te_history_record_cultural_hegemony_models = yes")
        census = re.search(r"every_country = \{\s*limit = \{ is_player = yes \}\s*te_history_mirror_ch_models = yes", effects[record:])
        self.assertIsNotNone(census)
        monthly = effects[effects.index("ch_monthly_country_update = {"):record]
        self.assertRegex(monthly, r"limit = \{ is_player = yes \}\s*ch_leaders_display_write = yes\s*te_history_mirror_ch_models = yes")
        self.assertRegex(monthly, r"else_if = \{\s*limit = \{ has_variable_list = ch_model_hist_view \}\s*clear_variable_list = ch_model_hist_view")

    def test_no_history_when_disabled_or_world_pull_is_zero(self):
        self.h.enabled = False
        self.h.sample()
        self.assertFalse(self.h.live)
        self.h.enabled = True
        self.h.globals = {}
        self.h.sample()
        self.assertFalse(self.h.live)

    def test_gui_palette_order_shared_binding_and_historical_tooltips(self):
        gui = read("gui/journal_entry_widgets/cultural_hegemony_widget.gui")
        plot = _type_body(gui, "ch_model_history_plot")
        history = _type_body(gui, "te_ch_sec_history")
        # GetGlobalVariable(..).GetList(..) loaded cleanly but drew no bars in
        # game; the player's mirror is read like the te_hist charts.
        self.assertIn("JournalEntry.GetCountry.MakeScope.GetList('ch_model_hist_view')", plot)
        self.assertNotIn("GetGlobalVariable", plot)
        self.assertEqual(re.findall(r"GetVariableValue\('ch_model_hist_cum_(\w+)'\)", plot), list(reversed(MODELS)))
        colors = re.findall(r"color = \{ ([\d.]+) ([\d.]+) ([\d.]+) 1.0 \}", plot)
        expected = [tuple(int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)) for _, color in reversed(PALETTE)]
        for rgb, want in zip(colors, expected):
            for actual, target in zip(rgb, want):
                self.assertAlmostEqual(float(actual), target, places=6)
        self.assertEqual(re.findall(r'text = "ch_model_((?!hist_)\w+)"', history), MODELS)
        self.assertNotIn("te_hist_mk", plot + history)
        self.assertNotIn("'te_hist_range'", plot + history)
        loc = _load_loc()
        for key in _closure("ch_model_hist_tt", loc):
            self.assertLessEqual(_data_roots(loc[key]), {"ScriptContainer"})
        self.assertEqual(re.findall(r"GetVariableValue\('ch_model_hist_(\w+)'\)", loc["ch_model_hist_tt"]), MODELS)

    def test_only_sampler_is_wired_after_global_aggregates(self):
        effects = read("common/scripted_effects/cultural_hegemony_effects.txt")
        call = "te_history_record_cultural_hegemony_models = yes"
        self.assertEqual(effects.count(call), 1)
        self.assertLess(effects.index("ch_finish_all_model_buckets = yes"), effects.index(call))
        self.assertNotIn("te_history_record_cultural_hegemony_marker", effects)
        self.assertNotIn("te_history_record_cultural_hegemony_samples", read("common/journal_entries/je_cultural_hegemony.txt"))


if __name__ == "__main__":
    unittest.main()
