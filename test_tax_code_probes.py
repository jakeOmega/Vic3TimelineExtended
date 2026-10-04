"""Offline harness safety checks, not evidence that any engine capability works."""
from pathlib import Path
import itertools
import re
import unittest

from paradox_file_parser import ParadoxFileParser
from test_te_systems_window import _evaluate, _strip_comments, _template, _txt_block

ROOT = Path(__file__).resolve().parent


def read(path):
    return (ROOT / path).read_text(encoding="utf-8-sig")


class TaxProbeSafetyTest(unittest.TestCase):
    def test_every_console_action_except_arm_and_raw_read_requires_opt_in(self):
        text = read("events/te_debug_tax_events.txt")
        ids = re.findall(r"^(te_debug_tax\.\d+) =", text, re.M)
        self.assertGreater(len(ids), 50)
        for event in ids:
            body = _txt_block(text, event)
            self.assertIn("hidden = yes", body, event)
            if event not in {"te_debug_tax.1", "te_debug_tax.91"}:
                trigger = re.search(r"trigger = \{([^}]+)", body, re.S)
                self.assertIsNotNone(trigger, event)
                self.assertIn("has_variable = te_tp_armed", trigger.group(1), event)

    def test_clicks_route_to_existing_country_rooted_guarded_events(self):
        sguis = read("common/scripted_guis/te_debug_tax_sguis.txt")
        events = read("events/te_debug_tax_events.txt")
        widget = read("gui/te_debug_tax_widgets.gui")
        keys = set(re.findall(r"GetScriptedGui\('(te_tp_\w+)'\)\.Execute", widget))
        self.assertGreater(len(keys), 50)
        for key in keys:
            body = _txt_block(sguis, key)
            self.assertIn("scope = country", body)
            self.assertIn("ai_is_valid = { always = no }", body)
            self.assertIn("has_variable = te_tp_armed", body)
            event = re.search(r"id = (te_debug_tax\.\d+)", body).group(1)
            self.assertIn("type = country_event", _txt_block(events, event))
        # Rendering may query values/conditions, but only onclick executes.
        for line in widget.splitlines():
            if ".Execute(" in line:
                self.assertIn("onclick =", line)

    def test_four_tab_selection_is_exclusive_and_stale_debug_choice_falls_back(self):
        gui = read("gui/te_systems_window.gui")
        normal = ["space_race", "colonial_empire", "grand_monuments"]
        names = normal + ["tax_probes"]
        expressions = {n: _template(gui, f"te_systems_window_{n}_selected") for n in names}
        empty = _template(gui, "te_systems_window_none_open")
        for mask in itertools.product((False, True), repeat=4):
            shown = {f"te_window_{n}_tab_sgui" for n, yes in zip(normal, mask[:3]) if yes}
            if mask[3]:
                shown.add("te_tp_tab_sgui")
            for stored in [None, "unknown"] + names:
                selected = [n for n in names if _evaluate(expressions[n], shown, stored)]
                if stored == "tax_probes" and mask[3]:
                    expected = ["tax_probes"]
                elif stored in normal and mask[normal.index(stored)]:
                    expected = [stored]
                else:
                    expected = next(([n] for n, yes in zip(normal, mask[:3]) if yes), [])
                self.assertEqual(selected, expected, (mask, stored))
                self.assertEqual(_evaluate(empty, shown, stored), not expected)

    def test_normal_tabs_remain_clickable_while_debug_tab_is_selected(self):
        gui = read("gui/te_systems_window.gui")
        for tab in ["space_race", "colonial_empire", "grand_monuments"]:
            expr = _template(gui, f"te_systems_window_{tab}_unselected")
            shown = {"te_tp_tab_sgui", f"te_window_{tab}_tab_sgui", f"te_window_{tab}_tab_unlock_sgui"}
            self.assertTrue(_evaluate(expr, shown, "tax_probes"))
            shown.remove(f"te_window_{tab}_tab_unlock_sgui")
            self.assertFalse(_evaluate(expr, shown, "tax_probes"))

    def test_flowcontainers_never_directly_own_box_layouts(self):
        # Engine error pdx_gui_container.cpp:145 on PR 585's initial load.
        # Vanilla tab_buttons is an hbox even though its instance has another name.
        texts = [read(path) for path in (
            "gui/te_systems_window.gui", "gui/te_debug_tax_widgets.gui")]
        bases = {"tab_buttons": "hbox"}
        for text in texts:
            bases.update(re.findall(r"\btype\s+(\w+)\s*=\s*(\w+)", _strip_comments(text)))

        def base_type(name):
            seen = set()
            while name in bases and name not in seen:
                seen.add(name)
                name = bases[name]
            return name

        for text in texts:
            # Ignore braces in comments and strings; anonymous blocks still
            # occupy a stack level, so only direct widget parents are checked.
            clean = re.sub(r'"(?:\\.|[^"\\])*"', '""', _strip_comments(text))
            stack = []
            for token in re.finditer(
                    r"\b(?:type\s+\w+\s*=\s*)?(\w+)\s*(?:=\s*)?\{|[{}]", clean):
                if token.group() == "}":
                    self.assertTrue(stack, "unmatched closing brace")
                    stack.pop()
                    continue
                child = base_type(token.group(1))
                parent = stack[-1] if stack else None
                line = clean.count("\n", 0, token.start()) + 1
                self.assertFalse(
                    parent in {"container", "flowcontainer"} and child in {"hbox", "vbox"},
                    f"line {line}: {parent} cannot directly own {child}")
                stack.append(child)
            self.assertFalse(stack, "unclosed GUI blocks")

    def test_known_native_controls_keep_original_validity_and_add_gate(self):
        # The probe's lock now rides on the tax code's production gates (plan Task 9;
        # every native site is listed in test_tax_code_bypass.py): six tax-level and
        # consumption controls on te_tax_native_controls_sgui, the 14 tariff and
        # subvention buttons on te_tax_native_tariff_controls_sgui.
        gui = read("gui/budget_panel.gui")
        matches = [line for line in gui.splitlines() if 'enabled = "[' in line and any(
            x in line for x in ("GetPlayer.SetExport", "GetPlayer.SetImport", "GetPlayer.HasAnyTaxes", "BudgetPanel.CanTaxGoods"))]
        self.assertEqual(len(matches), 20)
        tariff = [line for line in matches if "GetPlayer.SetExport" in line or "GetPlayer.SetImport" in line]
        self.assertEqual(len(tariff), 14)
        for line in matches:
            gate = "te_tax_native_tariff_controls_sgui" if line in tariff else "te_tax_native_controls_sgui"
            self.assertIn(f"GetScriptedGui('{gate}').IsValid(", line)
        self.assertNotIn("te_tp_native_controls_sgui", gui)
        sguis = read("common/scripted_guis/te_tax_native_sguis.txt")
        for name in ("te_tax_native_controls_sgui", "te_tax_native_tariff_controls_sgui"):
            gate = _txt_block(sguis, name)
            self.assertIn("NOT = { has_variable = te_tp_lock }", gate)
            self.assertNotIn("set_tax_level", gate)

    def test_probe_files_parse_and_domestic_rates_use_tax_namespace(self):
        paths = list((ROOT / "common").rglob("*te_debug_tax*.txt"))
        paths += list((ROOT / "events").glob("te_debug_tax*.txt"))
        for path in paths:
            self.assertTrue(path.read_bytes().startswith(b"\xef\xbb\xbf"), path)
            parser = ParadoxFileParser()
            parser.parse_file(str(path), apply_directives=False)
            self.assertTrue(parser.data, path)
            self.assertNotIn("country_tax_income_add", path.read_text(encoding="utf-8-sig"))
        amendments = read("common/amendments/te_debug_tax_amendments.txt")
        for clause in ("wage", "dividend", "rural", "head", "consumption", "consumption_high"):
            body = _txt_block(amendments, "amendment_te_tp_" + clause)
            rates = re.findall(r"tax_modifier_\w+ = \{ ([^}]+) \}", body)
            self.assertEqual(len(rates), 5)
            self.assertEqual(len(set(rates)), 1, clause)

    def test_carrier_uses_valid_law_gates(self):
        # `possible` is an amendment/decree field, not a law field: debug.log
        # 2026-10-02 14:23:48 "Unexpected token: possible" in this file. A law is
        # gated by can_enact (enactment) and is_visible (law panel).
        path = ROOT / "common/laws/zz_te_debug_tax_carrier.txt"
        parser = ParadoxFileParser()
        parser.parse_file(str(path), apply_directives=False)
        node = parser.data["law_te_probe_carrier"]
        body = node[1] if isinstance(node, tuple) else node
        self.assertNotIn("possible", body)
        self.assertIn("can_enact", body)
        self.assertIn("is_visible", body)
        text = path.read_text(encoding="utf-8-sig")
        self.assertIn("can_enact = { has_variable = te_tp_armed }", text)
        self.assertIn("is_visible = { has_variable = te_tp_armed }", text)
        # The AI must still never pick the carrier by weight.
        self.assertIn("ai_enact_weight_modifier = { value = -100000 }", text)

    def test_arm_event_refuses_under_the_tax_code_rule(self):
        # The harness's carrier and amendments must not run beside the production
        # system. Written inline: the te_tax_code_on trigger is defined later.
        body = _txt_block(read("events/te_debug_tax_events.txt"), "te_debug_tax.1")
        immediate = re.search(r"immediate = \{(.*)\}\s*$", body, re.S).group(1)
        guard = re.search(r"if = \{\s*limit = \{(.*?)\}\s*te_tp_arm = yes\s*\}", immediate, re.S)
        self.assertIsNotNone(guard, "te_tp_arm must sit inside the guarded if")
        self.assertIn("NOT = { has_game_rule = te_tax_code_enabled }", guard.group(1))
        self.assertIn("NOT = { has_game_rule = te_tax_code_enabled_customs }", guard.group(1))
        refusal = re.search(r"else = \{(.*)\}", immediate, re.S)
        self.assertIsNotNone(refusal, "a refused arm must say so")
        self.assertIn("debug_log", refusal.group(1))
        self.assertNotIn("te_tp_arm", refusal.group(1))

    def test_normal_entry_points_never_arm_a_country(self):
        hooks = read("common/on_actions/te_debug_tax_on_actions.txt")
        self.assertNotIn("id = te_debug_tax.1 ", hooks)
        self.assertNotIn("te_tp_arm =", hooks)
        effects = read("common/scripted_effects/te_debug_tax_effects.txt")
        for name in ("te_tp_draft", "te_tp_approve"):
            body = _txt_block(effects, name)
            for mutation in ("add_modifier", "add_amendment", "set_import_tariff_level", "add_taxed_goods", "add_treasury"):
                self.assertNotIn(mutation, body, name)


PROBE_TYPES = "common/modifier_type_definitions/te_tax_probe_modifier_types.txt"
PROBE_GOODS = ("grain", "iron")
PROBE_FAMILIES = ("import_tariffs_rate_add", "export_tariffs_rate_add",
                  "max_import_tariffs_level_add", "min_import_tariffs_level_add",
                  "max_export_tariffs_level_add", "min_export_tariffs_level_add")
# Where a per-good tariff modifier may be named: the registration, the harness
# that applies it, and its loc. Anything else would apply it in a real game.
PROBE_HOMES = {"te_tax_probe_modifier_types.txt", "te_debug_tax_modifiers.txt"}


class CustomsProbeTest(unittest.TestCase):
    """Plan Task 23 (spec 2026-10-03 §2.9): the customs probe registers the
    per-good tariff families for two goods only, and nothing outside the
    harness applies them, so the registration changes no rule-off game."""

    def test_registration_names_exactly_the_probe_families(self):
        names = set(re.findall(r"(?m)^(country_\w+) = \{", read(PROBE_TYPES)))
        expected = {f"country_{g}_{f}" for g in PROBE_GOODS for f in PROBE_FAMILIES}
        self.assertEqual(names, expected)

    def test_no_production_file_uses_the_probe_only_tariff_modifiers(self):
        # Grain/iron remain experimental probe carriers. Production climate
        # rates use separately registered coal/oil types and their own tests.
        names = [f"country_{good}_{family}" for good in PROBE_GOODS for family in PROBE_FAMILIES]
        pattern = re.compile(r"\b(?:" + "|".join(map(re.escape, names)) + r")\b")
        offenders = []
        for folder in ("common", "events", "gui"):
            for path in sorted((ROOT / folder).rglob("*")):
                if path.suffix not in {".txt", ".gui"} or path.name in PROBE_HOMES:
                    continue
                if pattern.search(path.read_text(encoding="utf-8-sig")):
                    offenders.append(str(path.relative_to(ROOT)))
        self.assertEqual(offenders, [])

    def test_lock_and_carrier_modifiers_are_applied_only_by_armed_probe_events(self):
        events = read("events/te_debug_tax_events.txt")
        for name in ("te_tp_lock_grain_low", "te_tp_cancel_max"):
            appliers = [m.start() for m in re.finditer(rf"add_modifier = \{{ name = {name} \}}", events)]
            self.assertTrue(appliers, name)
            for event_id in ("te_debug_tax.80", "te_debug_tax.81", "te_debug_tax.82"):
                body = _txt_block(events, event_id)
                self.assertIn("has_variable = te_tp_armed", body, event_id)
            for folder in ("common", "events"):
                for path in sorted((ROOT / folder).rglob("*.txt")):
                    if path.name in {"te_debug_tax_events.txt", "te_debug_tax_modifiers.txt", "te_debug_tax_effects.txt"}:
                        continue
                    self.assertNotIn(name, path.read_text(encoding="utf-8-sig"), str(path))

    def test_clear_removes_the_new_probe_modifiers(self):
        clear = _txt_block(read("common/scripted_effects/te_debug_tax_effects.txt"), "te_tp_clear")
        for name in ("te_tp_lock_grain_low", "te_tp_cancel_max"):
            self.assertIn(f"remove_modifier = {name}", clear)


if __name__ == "__main__":
    unittest.main()
