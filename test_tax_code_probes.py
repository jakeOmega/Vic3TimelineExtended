"""Offline harness safety checks, not evidence that any engine capability works."""
from pathlib import Path
import itertools
import re
import unittest

from paradox_file_parser import ParadoxFileParser
from test_te_systems_window import _evaluate, _template, _txt_block

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

    def test_known_native_controls_keep_original_validity_and_add_gate(self):
        gui = read("gui/budget_panel.gui")
        matches = [line for line in gui.splitlines() if 'enabled = "[' in line and any(
            x in line for x in ("GetPlayer.SetExport", "GetPlayer.SetImport", "GetPlayer.HasAnyTaxes", "BudgetPanel.CanTaxGoods"))]
        self.assertEqual(len(matches), 20)
        for line in matches:
            self.assertIn("te_tp_native_controls_sgui", line)
        gate = _txt_block(read("common/scripted_guis/te_debug_tax_sguis.txt"), "te_tp_native_controls_sgui")
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

    def test_normal_entry_points_never_arm_a_country(self):
        hooks = read("common/on_actions/te_debug_tax_on_actions.txt")
        self.assertNotIn("id = te_debug_tax.1 ", hooks)
        self.assertNotIn("te_tp_arm =", hooks)
        effects = read("common/scripted_effects/te_debug_tax_effects.txt")
        for name in ("te_tp_draft", "te_tp_approve"):
            body = _txt_block(effects, name)
            for mutation in ("add_modifier", "add_amendment", "set_import_tariff_level", "add_taxed_goods", "add_treasury"):
                self.assertNotIn(mutation, body, name)


if __name__ == "__main__":
    unittest.main()
