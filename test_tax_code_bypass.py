"""Native bypasses of the legislated tax code, closed or re-asserted (plan Task 9).

Under the rule no ordinary player, AI or script path may change collections
outside the code without the code being re-asserted, and no vanilla objective
may become impossible. With the rule off nothing changes. Structural checks on
the committed files; the classes that read the installed game skip without it.

* Every native control in the mod's ``gui/`` that changes collections is
  greyed by a production gate ANDed into its ``enabled``: the tax level, the
  consumption-tax menu and every ``Goods.ToggleTaxation`` by
  ``te_tax_native_controls_sgui`` (rule off and no probe lock), the 14
  tariff and subvention buttons by ``te_tax_native_tariff_controls_sgui``
  (customs option off and no probe lock).
* The two new full-file overrides (``goods_panel.gui``,
  ``add_consumption_tax_menu.gui``) are vanilla 1.14.5 plus marked hunks.
* ``on_law_activated`` re-asserts the carrier when another taxation law is
  activated in a migrated country, through a dispatched country event.
* The collection writer counts native drift before it syncs.
* Cultural Hegemony never presses a taxation law under the rule; the
  spectrum auction pays a flat income instead of a dividend tax rate.
* The three vanilla journal entries that need Per-Capita, Proportional or
  Graduated taxation accept the code instead (``REPLACE:``), unchanged with the
  rule off; Traditionalism forbids wage and dividend taxes in a bill.

Run: python3 -m unittest test_tax_code_bypass -v
"""

import difflib
import json
import os
import re
import unittest
from pathlib import Path

from test_tax_code_rule import load, plain
from test_tax_code_state import KEYS, block, catalog, close, gen, schema_tokens

ROOT = Path(__file__).resolve().parent

NATIVE_SGUIS = "common/scripted_guis/te_tax_native_sguis.txt"
DEBUG_SGUIS = "common/scripted_guis/te_debug_tax_sguis.txt"
ON_ACTIONS = "common/on_actions/te_tax_on_actions.txt"
EVENTS = "events/te_tax_internal_events.txt"
MIGRATION = "common/scripted_effects/te_tax_migration_effects.txt"
COLLECTION = "common/scripted_effects/te_tax_collection_effects.txt"
STATE = "common/scripted_effects/te_tax_state_effects.txt"
GEN_EFFECTS = "common/scripted_effects/te_tax_generated_effects.txt"
GEN_TRIGGERS = "common/scripted_triggers/te_tax_generated_triggers.txt"
TRIGGERS = "common/scripted_triggers/te_tax_triggers.txt"
DISPLAY = "common/script_values/te_tax_display_values.txt"
CH_EVENTS = "events/cultural_hegemony_events.txt"
REPEATABLE = "events/repeatable_events.txt"
EVENT_MODIFIERS = "common/static_modifiers/event_modifiers.txt"
JE_OVERRIDES = "common/journal_entries/te_tax_vanilla_je_overrides.txt"
VANILLA_JES = "vanilla_parsed/common/journal_entries.json"
TAX_LOC = "localization/english/te_tax_l_english.yml"
SCHEMA_DOC = "docs/systems/tax_code_schema.md"
LEDGER = "docs/testing/tax-code-capability-ledger.md"
GUI_GUIDE = "docs/guides/gui_modding_guide.md"
CARRIER = "law_te_tax_code"

GATE = "GetScriptedGui('{}').IsValid( GuiScope.SetRoot( GetPlayer.MakeScope ).End )"
DOMESTIC_GATE = GATE.format("te_tax_native_controls_sgui")
TARIFF_GATE = GATE.format("te_tax_native_tariff_controls_sgui")

# Commands that change a collection: the tax level, consumption taxes (the Budget
# panel's add menu opens the menu whose items toggle a good) and, under the
# customs option only, tariffs and subventions.
DOMESTIC = re.compile(r"Execute\(\s*GetPlayer\.SetTaxLevel\w+\s*\)|Execute\(\s*Goods\.ToggleTaxation\("
                      r"|BudgetPanel\.ToggleAddConsumptionTaxMenu\(")
TARIFF = re.compile(r"Execute\(\s*GetPlayer\.Set(?:Import|Export)(?:Tariffs|Subventions)\w+\(")

# Every gated site, by file: Budget's five tax levels and its "+" (add a taxed
# good), the four Tax/Untax items of the goods right-click menus, the goods
# panel's consumption-tax toggle (a type every goods view instantiates) and the
# add-consumption-tax menu's item; the 14 tariff and subvention buttons.
DOMESTIC_SITES = {"budget_panel.gui": 6, "right_click_menu.gui": 4, "goods_panel.gui": 1,
                  "add_consumption_tax_menu.gui": 1}
TARIFF_SITES = {"budget_panel.gui": 14}
# The vanilla condition each gate is ANDed with.
ORIGINAL_CONDITION = {
    "SetTaxLevel": "GetPlayer.HasAnyTaxes",
    "ToggleAddConsumptionTaxMenu": "BudgetPanel.CanTaxGoods",
    "ToggleTaxation": "IsValid( Goods.ToggleTaxation(",
}

# Full-file overrides of vanilla 1.14.5 made for the tax code, each vanilla's
# file plus `### MOD: Tax Code` blocks. Their vanilla copies are in
# test_fixtures/vanilla_gui/ (as topbar.gui's), refreshed on each vanilla patch.
OVERRIDES = ("goods_panel.gui", "add_consumption_tax_menu.gui")
MOD_OPEN = "### MOD: Tax Code"
MOD_CLOSE = "### END MOD ###"
VANILLA_LINE = "# vanilla: "

TOGGLE_TYPE = "consumption_tax_button_toggle"

# The vanilla entries that require Per-Capita, Proportional or Graduated
# taxation, and the counts-as triggers each accepts under the rule.
PATCHED_JES = {
    "je_great_reforms_bureaucratic": ("per_capita", "proportional", "graduated"),
    "je_portugal_regeneration": ("per_capita", "proportional", "graduated"),
    "je_imperialism_of_promise": ("proportional", "graduated"),
}
LAW_OF = {"per_capita": "law_per_capita_based_taxation", "proportional": "law_proportional_taxation",
          "graduated": "law_graduated_taxation"}

DRIFT_TOKENS = {"te_tax_drift_level": 0, "te_tax_drift_goods": 0, "te_tax_drift_amend": 0,
                "te_tax_sync_version": -1}

MONTH = "month=[SCOPE.ScriptValue('te_history_month_index')|0]"
DATE = "date=[TimeKeeper.GetCurrentDate.GetString]"
COUNTRY = "country=[THIS.GetCountry.GetNameNoFormatting]"


def raw(path):
    return (ROOT / path).read_text(encoding="utf-8-sig")


def read(path):
    return re.sub(r"#[^\n]*", "", raw(path))


def uncomment_gui(text):
    """Drop `#` comments outside quoted strings (`"#title"` is a format, not a comment)."""
    out = []
    for line in text.splitlines():
        quoted, cut = False, len(line)
        for i, c in enumerate(line):
            if c == '"':
                quoted = not quoted
            elif c == "#" and not quoted:
                cut = i
                break
        out.append(line[:cut])
    return "\n".join(out)


def enclosing(text, pos):
    """Index of the `{` of the innermost block holding `pos`, or None."""
    depth = 0
    for i in range(pos - 1, -1, -1):
        if text[i] == "}":
            depth += 1
        elif text[i] == "{":
            if depth == 0:
                return i
            depth -= 1
    return None


def own(text, opener):
    """The text of the block opened at `opener` outside its nested blocks."""
    end = close(text, opener)
    out, depth = [], 0
    for c in text[opener + 1:end]:
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        elif depth == 0:
            out.append(c)
    return "".join(out)


def enabled_of(text, opener):
    """The block's own `enabled`, or the one in its `block "enabled"` child."""
    match = re.search(r'\benabled = "([^"]*)"', own(text, opener))
    if match:
        return match.group(1)
    end = close(text, opener)
    child = re.search(r'block "enabled" \{', text[opener + 1:end])
    if child:
        start = opener + 1 + child.end() - 1
        match = re.search(r'\benabled = (?:"([^"]*)"|(\w+))', own(text, start))
        if match:
            return match.group(1) or match.group(2)
    return None


def gate_of(text, pos):
    """The `enabled` that governs the click at `pos`: the nearest enclosing
    block that has one (the goods panel's toggle keeps its click in
    `blockoverride "on_click"` and its gate in the type's `block "enabled"`)."""
    opener = enclosing(text, pos)
    while opener is not None:
        found = enabled_of(text, opener)
        if found is not None:
            return found
        opener = enclosing(text, opener)
    return None


def native_sites(pattern, gui_root=ROOT / "gui"):
    """[(relative path, command, governing enabled)] for every onclick running `pattern`."""
    sites = []
    for path in sorted(gui_root.rglob("*.gui")):
        text = uncomment_gui(path.read_text(encoding="utf-8-sig", errors="replace"))
        for line in re.finditer(r'onclick = "([^"]*)"', text):
            command = pattern.search(line.group(1))
            if command:
                sites.append((path.relative_to(gui_root).as_posix(), command.group(0),
                              gate_of(text, line.start())))
    return sites


def instances(text, name):
    """Bodies of every `name = { ... }` instance (not the `type name = ...` definition)."""
    out = []
    for match in re.finditer(r"(?<![\w.])" + re.escape(name) + r" = \{", text):
        if text[max(0, match.start() - 5):match.start()].endswith("type "):
            continue
        opener = match.end() - 1
        out.append(text[opener:close(text, opener) + 1])
    return out


def installed_game():
    """The installed game's `game/` folder, or None (CI, dummy VIC3_BASE_GAME)."""
    base = os.environ.get("VIC3_BASE_GAME")
    if base is None:
        try:
            import path_constants
            base = path_constants.base_game_path
        except Exception:
            return None
    game = Path(base) / "game"
    return game if (game / "gui").is_dir() else None


def logs(text):
    return re.findall(r'debug_log = "([^"]*)"', text)


# ---------------------------------------------------------------------------
# The gates
# ---------------------------------------------------------------------------

def evaluate(trigger, rule, lock):
    """Truth of a gate's is_valid for a game rule setting and the probe lock."""
    facts = {"te_tax_code_on": rule in ("enabled", "customs"), "te_tax_customs_on": rule == "customs"}
    result = True
    for key, value in trigger.items():
        values = value if isinstance(value, list) else [value]
        for item in values:
            if key == "NOT":
                result &= not evaluate(item, rule, lock)
            elif key in facts:
                result &= facts[key] == (item == "yes")
            elif key == "has_variable":
                if item != "te_tp_lock":
                    raise AssertionError(f"unexpected variable {item}")
                result &= lock
            else:
                raise AssertionError(f"unexpected condition {key}")
    return result


class GateDefinitionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sguis = load(NATIVE_SGUIS)
        cls.text = read(NATIVE_SGUIS)

    def test_file_carries_the_bom(self):
        self.assertTrue((ROOT / NATIVE_SGUIS).read_bytes().startswith(b"\xef\xbb\xbf"))

    def test_two_read_only_gates(self):
        self.assertEqual(set(self.sguis), {"te_tax_native_controls_sgui", "te_tax_native_tariff_controls_sgui"})
        for name, body in self.sguis.items():
            with self.subTest(name=name):
                self.assertEqual(body["scope"], "country")
                self.assertEqual(body["is_shown"], {"always": "yes"})
                self.assertEqual(body["ai_is_valid"], {"always": "no"})
                self.assertIn(body["effect"], ({}, [], ""))
        self.assertNotRegex(self.text, r"\b(set_variable|change_variable|remove_variable|trigger_event|"
                                       r"set_tax_level|add_taxed_goods|remove_taxed_goods|every_\w+)\b")

    def test_domestic_gate_is_valid_only_with_the_rule_off_and_no_probe_lock(self):
        # With the rule off it is the probe gate it replaces (NOT te_tp_lock), so a
        # rule-off game behaves as before; under either rule option it is closed.
        valid = self.sguis["te_tax_native_controls_sgui"]["is_valid"]
        for rule in ("off", "enabled", "customs"):
            for lock in (False, True):
                with self.subTest(rule=rule, lock=lock):
                    self.assertEqual(evaluate(valid, rule, lock), rule == "off" and not lock)

    def test_tariff_gate_closes_only_under_the_customs_option(self):
        # The plain rule option leaves tariffs native and usable.
        valid = self.sguis["te_tax_native_tariff_controls_sgui"]["is_valid"]
        for rule in ("off", "enabled", "customs"):
            for lock in (False, True):
                with self.subTest(rule=rule, lock=lock):
                    self.assertEqual(evaluate(valid, rule, lock), rule != "customs" and not lock)

    def test_the_probe_gate_is_retired(self):
        self.assertNotIn("te_tp_native_controls_sgui", raw(DEBUG_SGUIS))
        for path in (ROOT / "gui").rglob("*.gui"):
            with self.subTest(path=path.name):
                self.assertNotIn("te_tp_native_controls_sgui", path.read_text(encoding="utf-8-sig"))


class NativeSiteTest(unittest.TestCase):
    """Every native control in the mod's gui/ that changes collections keeps its
    vanilla condition and is ANDed with its gate."""

    def check(self, pattern, gate, expected):
        sites = native_sites(pattern)
        counts = {}
        for path, command, enabled in sites:
            counts[os.path.basename(path)] = counts.get(os.path.basename(path), 0) + 1
            with self.subTest(path=path, command=command):
                self.assertIsNotNone(enabled, "no enabled governs the click")
                match = re.fullmatch(r"\[And\( " + re.escape(gate) + r", (.+) \)\]", enabled)
                self.assertIsNotNone(match, enabled)
                rest = match.group(1)
                for key, condition in ORIGINAL_CONDITION.items():
                    if key in command:
                        self.assertIn(condition, rest)
                if pattern is TARIFF:
                    name = re.search(r"Set\w+", command).group(0)
                    self.assertIn(f"IsValid( GetPlayer.{name}(Goods.Self) )", rest)
        self.assertEqual(counts, expected)
        return sites

    def test_tax_level_and_consumption_taxes(self):
        self.check(DOMESTIC, DOMESTIC_GATE, DOMESTIC_SITES)

    def test_tariffs_and_subventions(self):
        self.check(TARIFF, TARIFF_GATE, TARIFF_SITES)

    def test_the_toggle_type_is_gated_in_its_enabled_block(self):
        # Every goods view instantiates this type: goods_panel.gui, and vanilla's
        # goods_state_panel.gui and custom_tooltip.gui, which the mod does not edit.
        text = uncomment_gui(raw("gui/goods_panel.gui"))
        match = re.search(r"type " + TOGGLE_TYPE + r" = \w+ \{", text)
        self.assertIsNotNone(match)
        opener = match.end() - 1
        self.assertEqual(enabled_of(text, opener),
                         f"[And( {DOMESTIC_GATE}, IsValid( Goods.ToggleTaxation(GetMetaPlayer.GetPlayedOrObservedCountry) ) )]")

    def test_no_mod_instance_of_the_toggle_re_enables_it(self):
        for path in sorted((ROOT / "gui").rglob("*.gui")):
            text = uncomment_gui(path.read_text(encoding="utf-8-sig"))
            for body in instances(text, TOGGLE_TYPE):
                override = re.search(r'blockoverride "enabled" \{([^{}]*)\}', body)
                with self.subTest(path=path.name):
                    self.assertTrue(override is None or override.group(1).split() == ["enabled", "=", "no"],
                                    body[:200])


class InstalledVanillaTest(unittest.TestCase):
    """Against the installed game: every vanilla .gui that runs a native command
    is overridden by the mod, and vanilla's own instances of the toggle type
    do not re-enable it. Skipped without the game (CI)."""

    @classmethod
    def setUpClass(cls):
        cls.game = installed_game()
        if cls.game is None:
            raise unittest.SkipTest("installed game not found")

    def test_every_vanilla_file_with_a_native_command_is_overridden(self):
        for pattern in (DOMESTIC, TARIFF):
            for path, command, _ in native_sites(pattern, self.game / "gui"):
                with self.subTest(path=path, command=command):
                    self.assertTrue((ROOT / "gui" / path).is_file())

    def test_vanilla_instances_of_the_toggle_stay_disabled_or_inherit_the_gate(self):
        seen = 0
        for path in sorted((self.game / "gui").rglob("*.gui")):
            if (ROOT / "gui" / path.relative_to(self.game / "gui")).is_file():
                continue
            text = uncomment_gui(path.read_text(encoding="utf-8-sig", errors="replace"))
            for body in instances(text, TOGGLE_TYPE):
                seen += 1
                override = re.search(r'blockoverride "enabled" \{([^{}]*)\}', body)
                with self.subTest(path=path.name):
                    self.assertTrue(override is None or override.group(1).split() == ["enabled", "=", "no"])
        self.assertGreater(seen, 0, "custom_tooltip.gui instantiates the toggle in 1.14.5")

    def test_fixtures_are_the_installed_files(self):
        for name in OVERRIDES:
            with self.subTest(name=name):
                self.assertEqual((ROOT / "test_fixtures" / "vanilla_gui" / name).read_bytes(),
                                 (self.game / "gui" / name).read_bytes(),
                                 "vanilla changed: merge it into gui/ and refresh the fixture")


class OverrideTest(unittest.TestCase):
    """gui/goods_panel.gui and gui/add_consumption_tax_menu.gui are vanilla's
    files, changed only inside `### MOD: Tax Code` blocks, each of which keeps
    the vanilla line it replaces as a `# vanilla:` comment."""

    def test_the_overrides_carry_the_bom(self):
        # Vanilla's copies have none; every mod .gui does (bom_normalizer,
        # check_gui_lint), so the diff below ignores it.
        for name in OVERRIDES:
            with self.subTest(name=name):
                self.assertTrue((ROOT / "gui" / name).read_bytes().startswith(b"\xef\xbb\xbf"))

    def test_every_change_is_marked_and_keeps_the_vanilla_line(self):
        for name in OVERRIDES:
            vanilla = (ROOT / "test_fixtures" / "vanilla_gui" / name).read_text(encoding="utf-8-sig").splitlines()
            mod = raw(f"gui/{name}").splitlines()
            regions, opened = [], None
            for i, line in enumerate(mod):
                if line.strip().startswith(MOD_OPEN):
                    self.assertIsNone(opened, f"{name}:{i + 1} nested MOD block")
                    opened = i
                elif line.strip() == MOD_CLOSE:
                    self.assertIsNotNone(opened, f"{name}:{i + 1} END MOD without MOD")
                    regions.append((opened, i))
                    opened = None
            self.assertIsNone(opened, f"{name}: unclosed MOD block")
            self.assertTrue(regions, f"{name}: no MOD block")
            ops = difflib.SequenceMatcher(None, vanilla, mod, autojunk=False).get_opcodes()
            hunks = [op for op in ops if op[0] != "equal"]
            self.assertTrue(hunks)
            for tag, i1, i2, j1, j2 in hunks:
                with self.subTest(name=name, line=j1 + 1):
                    self.assertIn(tag, ("insert", "replace"), "vanilla lines removed outside a MOD block")
                    region = next(((a, b) for a, b in regions if a <= j1 and j2 - 1 <= b), None)
                    self.assertIsNotNone(region, f"unmarked change: {mod[j1:j2]!r}")
                    kept = {line.strip() for line in mod[region[0]:region[1] + 1]}
                    for old in vanilla[i1:i2]:
                        if old.strip():
                            self.assertIn(VANILLA_LINE + old.strip(), kept)

    def test_the_overrides_are_registered(self):
        guide = raw(GUI_GUIDE)
        section = guide.split("## This Mod's GUI Files", 1)[1]
        # The intro line and the first table, up to the blank line after it.
        table = section[:section.index("\n\n", section.index("| File | Vanilla Panel |"))]
        for name in OVERRIDES:
            with self.subTest(name=name):
                self.assertIn(f"| `{name}` |", table)
        rows = re.findall(r"^\| `([\w.]+\.gui)` \|", table, re.M)
        top = sorted(p.name for p in (ROOT / "gui").glob("*.gui"))
        self.assertEqual(sorted(rows), top)
        additive = sum(1 for row in table.splitlines() if row.startswith("| `") and "(additive" in row)
        self.assertIn(f"Currently {len(top)} GUI files at the top of `gui/`: {len(top) - additive} full-file "
                      f"replacements of vanilla panels plus {additive} additive files", table)


# ---------------------------------------------------------------------------
# Re-assertion of the carrier
# ---------------------------------------------------------------------------

class ReassertHookTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parsed = load(ON_ACTIONS)
        cls.text = read(ON_ACTIONS)

    def test_hooked_on_law_activated(self):
        self.assertEqual(self.parsed["on_law_activated"]["on_actions"], ["te_tax_on_law_activated"])

    def test_gated_on_the_rule_another_taxation_law_and_a_migrated_owner(self):
        effect = self.parsed["te_tax_on_law_activated"]["effect"]
        self.assertEqual(set(effect), {"if"})
        branch = effect["if"]
        self.assertEqual(branch["limit"], {
            "te_tax_code_on": "yes",
            "law_type": {"is_same_law_group_as": f"law_type:{CARRIER}"},
            "NOT": {"law_type": f"law_type:{CARRIER}"},
            "owner": {"has_variable": "te_tax_migrated", "var:te_tax_migrated": "0"},
        })
        self.assertIn("var:te_tax_migrated > 0", block(self.text, "te_tax_on_law_activated"))
        # Dispatched, never run in the law scope.
        self.assertEqual(set(branch), {"limit", "owner"})
        self.assertEqual(branch["owner"], {"trigger_event": {"id": "te_tax.5"}})

    def test_only_the_hook_raises_the_re_assert(self):
        raisers = []
        for directory in ("common", "events"):
            for path in sorted((ROOT / directory).rglob("*.txt")):
                for _ in re.findall(r"trigger_event = \{ id = te_tax\.5\b", read(path.relative_to(ROOT).as_posix())):
                    raisers.append(path.relative_to(ROOT).as_posix())
        self.assertEqual(raisers, [ON_ACTIONS])


class ReassertEventTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = read(MIGRATION)
        cls.body = block(cls.text, "te_tax_reassert_carrier")
        cls.parsed = load(MIGRATION)["te_tax_reassert_carrier"]

    def test_event_is_a_hidden_rule_gated_country_event(self):
        event = load(EVENTS)["te_tax.5"]
        self.assertEqual(event["type"], "country_event")
        self.assertEqual(event["hidden"], "yes")
        self.assertEqual(event["trigger"], {"te_tax_code_on": "yes"})
        self.assertEqual(event["immediate"], {"te_tax_reassert_carrier": "yes"})

    def test_gated_on_a_migrated_country_off_the_carrier(self):
        self.assertEqual(set(self.parsed), {"if"})
        limit = self.parsed["if"]["limit"]
        self.assertEqual(limit["te_tax_code_on"], "yes")
        self.assertEqual(limit["has_variable"], "te_tax_migrated")
        self.assertEqual(limit["NOT"], {"has_law": f"law_type:{CARRIER}"})
        self.assertIn("var:te_tax_migrated >= 1", self.body)

    def test_activates_the_carrier_hands_the_month_back_and_syncs_tomorrow(self):
        order = [f"activate_law = law_type:{CARRIER}",
                 "set_variable = { name = te_tax_last_month value = -1 }",
                 "trigger_event = { id = te_tax.4 days = 1 }"]
        positions = [self.body.find(step) for step in order]
        self.assertTrue(all(p > 0 for p in positions), positions)
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(self.body.count("activate_law"), 1)

    def test_never_syncs_or_processes_in_the_same_execution(self):
        # activate_law is not assumed visible in the same execution: the writer
        # would attach the amendments to the law being replaced.
        for forbidden in ("te_tax_sync_collection", "te_tax_process_month", "te_tax_watchdog_month",
                          "add_amendment", "set_tax_level", "add_taxed_goods", "te_tax.1", "te_tax.2"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, self.body)

    def test_console_event_forces_a_vanilla_law_under_the_rule_only(self):
        # `event te_tax_debug.1`: the play-test of the re-assert. Nothing raises it.
        event = load("events/te_tax_debug_events.txt")["te_tax_debug.1"]
        self.assertEqual(event["hidden"], "yes")
        self.assertEqual(event["trigger"], {"te_tax_code_on": "yes"})
        self.assertEqual(event["immediate"]["activate_law"], "law_type:law_per_capita_based_taxation")
        for directory in ("common", "events"):
            for path in (ROOT / directory).rglob("*.txt"):
                with self.subTest(path=path.name):
                    self.assertNotIn("id = te_tax_debug.", read(path.relative_to(ROOT).as_posix()))

    def test_logs_each_re_assert(self):
        lines = logs(self.body)
        self.assertEqual(len(lines), 1)
        self.assertTrue(lines[0].startswith("TE_TAX reasserted"))
        for stamp in (MONTH, DATE, COUNTRY):
            self.assertIn(stamp, lines[0])
        self.assertNotIn("$", lines[0])


# ---------------------------------------------------------------------------
# Drift detection in the writer
# ---------------------------------------------------------------------------

class DriftTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.collection = read(COLLECTION)
        cls.writer = block(cls.collection, "te_tax_sync_collection")
        cls.detect = block(cls.collection, "te_tax_detect_drift")
        cls.count = block(cls.collection, "te_tax_count_drift")
        cls.effects = read(GEN_EFFECTS)
        cls.triggers = read(GEN_TRIGGERS)

    def test_tokens_are_in_the_schema_and_initialised(self):
        country, _ = schema_tokens()
        init = block(read(STATE), "te_tax_init_country")
        for token, sentinel in DRIFT_TOKENS.items():
            with self.subTest(token=token):
                self.assertEqual(country.get(token), sentinel)
                self.assertIn(f"if = {{ limit = {{ NOT = {{ has_variable = {token} }} }} "
                              f"set_variable = {{ name = {token} value = {sentinel} }} }}", init)

    def test_detected_once_before_any_sync(self):
        self.assertEqual(self.writer.count("te_tax_detect_drift = yes"), 1)
        at = self.writer.find("te_tax_detect_drift = yes")
        self.assertLess(self.writer.find("te_tax_init_country = yes"), at)
        self.assertLess(self.writer.find("save_scope_as = te_tax_country"), at)
        self.assertLess(at, self.writer.find("te_tax_gen_sync_"))
        self.assertLess(at, self.writer.find("set_tax_level"))

    def test_counted_only_against_the_code_last_synced(self):
        # A sunset or commencement changes the code before the processor's sync;
        # the native state then differs by law, not by drift.
        limit = " ".join(self.detect[:close(self.detect, self.detect.find("limit = {") + 8)].split())
        self.assertIn("var:te_tax_sync_version = var:te_tax_code_version", limit)
        guarded = re.search(r"if = \{\s*limit = \{ any_interest_group = \{ always = yes \} \}", self.writer)
        body = self.writer[guarded.end():close(self.writer, guarded.end() - 1)]
        mark = "set_variable = { name = te_tax_sync_version value = var:te_tax_code_version }"
        self.assertEqual(self.writer.count(mark), 1)
        self.assertIn(mark, body)
        self.assertGreater(body.find(mark), body.find("te_tax_gen_sync_cons = yes"))

    def test_counts_each_kind_and_writes_nothing_else(self):
        self.assertIn("NOT = { tax_level = medium }", self.detect)
        self.assertIn("te_tax_gen_goods_drift = yes", self.detect)
        for key in KEYS:
            self.assertIn(f"te_tax_gen_amend_drift_{key} = yes", self.detect)
        # Counted once, whichever branch logs.
        self.assertEqual(self.detect.count("te_tax_count_drift = yes"), 2)
        self.assertIn("change_variable = { name = te_tax_drift_level add = 1 }", self.count)
        self.assertIn("te_tax_gen_count_goods_drift = yes", self.count)
        for key in KEYS:
            with self.subTest(key=key):
                self.assertRegex(self.count, r"if = \{ limit = \{ te_tax_gen_amend_drift_" + key
                                 + r" = yes \} change_variable = \{ name = te_tax_drift_amend add = 1 \} \}")
        self.assertNotRegex(self.detect, r"(?:set|change)_variable")
        writes = re.findall(r"(?:set|change)_variable = \{ name = (\w+)", self.count)
        self.assertEqual(set(writes), {"te_tax_drift_level", "te_tax_drift_amend"})
        counted = block(self.effects, "te_tax_gen_count_goods_drift")
        self.assertEqual(set(re.findall(r"(?:set|change)_variable = \{ name = (\w+)", counted)),
                         {"te_tax_drift_goods"})
        for body in (self.detect, self.count, counted):
            self.assertNotRegex(body, r"\b(add_amendment|remove_amendment|add_taxed_goods|remove_taxed_goods|"
                                      r"set_tax_level|add_modifier|remove_modifier|activate_law)\b")

    def test_logs_the_totals_every_time_for_a_player_and_once_for_the_ai(self):
        squashed = " ".join(self.detect.split())
        self.assertIn("OR = { is_ai = no AND = { var:te_tax_drift_level = 0 var:te_tax_drift_goods = 0 "
                      "var:te_tax_drift_amend = 0 } }", squashed)
        lines = logs(self.detect)
        self.assertEqual(len(lines), 1)
        line = lines[0]
        self.assertTrue(line.startswith("TE_TAX drift"))
        for kind in ("level", "goods", "amend"):
            self.assertIn(f"{kind}=[SCOPE.ScriptValue('te_tax_view_drift_{kind}')|0]", line)
        for stamp in (MONTH, DATE, COUNTRY):
            self.assertIn(stamp, line)

    def test_goods_drift_covers_every_good_both_ways(self):
        any_drift = block(self.triggers, "te_tax_gen_goods_drift")
        counted = block(self.effects, "te_tax_gen_count_goods_drift")
        for good in catalog():
            mismatch = (f"OR = {{ AND = {{ var:te_tax_en_g_{good} = 1 NOT = {{ has_consumption_tax = g:{good} }} }} "
                        f"AND = {{ NOT = {{ var:te_tax_en_g_{good} = 1 }} has_consumption_tax = g:{good} }} }}")
            with self.subTest(good=good):
                self.assertIn(mismatch, any_drift)
                self.assertIn(f"if = {{ limit = {{ {mismatch} }} change_variable = {{ name = te_tax_drift_goods add = 1 }} }}",
                              counted)
        for good in gen.stray_goods():
            with self.subTest(good=good):
                self.assertIn(f"has_consumption_tax = g:{good}", any_drift)
                self.assertIn(f"if = {{ limit = {{ has_consumption_tax = g:{good} }} "
                              f"change_variable = {{ name = te_tax_drift_goods add = 1 }} }}", counted)

    def test_amendment_drift_covers_every_index_both_ways(self):
        for instrument in gen.INSTRUMENTS:
            body = block(self.triggers, f"te_tax_gen_amend_drift_{instrument.key}")
            for idx in range(1, instrument.max_idx + 1):
                name = gen.amendment_key(instrument, idx)
                var = f"var:te_tax_en_{instrument.key}"
                law = f"active_law:lawgroup_taxation = {{ has_amendment = amendment_type:{name} }}"
                with self.subTest(name=name):
                    self.assertIn(f"AND = {{ {var} = {idx} NOT = {{ {law} }} }}", body)
                    self.assertIn(f"AND = {{ NOT = {{ {var} = {idx} }} {law} }}", body)

    def test_display_values(self):
        values = load(DISPLAY)
        for kind in ("level", "goods", "amend"):
            name = f"te_tax_view_drift_{kind}"
            with self.subTest(name=name):
                self.assertEqual(values[name]["value"], "0")
                self.assertIn(f"has_variable = te_tax_drift_{kind}", block(read(DISPLAY), name))

    def test_schema_doc_describes_drift(self):
        doc = raw(SCHEMA_DOC)
        section = doc.split("\n## Native controls and drift\n", 1)[1].split("\n## ", 1)[0]
        for phrase in ("te_tax_native_controls_sgui", "te_tax_native_tariff_controls_sgui", "te_tax.5",
                       "on_law_activated", "te_tax_detect_drift", "te_tax_sync_version", "TE_TAX drift",
                       "TE_TAX reasserted"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, section)


# ---------------------------------------------------------------------------
# Mod content that changed collections outside the code
# ---------------------------------------------------------------------------

class CulturalHegemonyTest(unittest.TestCase):
    def test_taxation_is_never_pressed_under_the_rule(self):
        text = read(CH_EVENTS)
        sites = [m.start() for m in re.finditer(r"is_same_law_group_as = law_type:law_\w+_taxation\b", text)]
        self.assertEqual(len(sites), 3)
        for at in sites:
            opener = enclosing(text, at)
            body = text[opener:close(text, opener) + 1]
            with self.subTest(line=text.count("\n", 0, at) + 1):
                self.assertEqual(" ".join(body.split()),
                                 "{ is_same_law_group_as = law_type:law_consumption_based_taxation "
                                 "NOT = { te_tax_code_on = yes } }")
                self.assertTrue(text[:opener].rstrip().endswith("AND ="))


class SpectrumAuctionTest(unittest.TestCase):
    def test_option_a_pays_income_under_the_rule_and_is_unchanged_without(self):
        body = block(read(REPEATABLE), "repeatable_events.60")
        opener = enclosing(body, body.index("name = repeatable_events.60.a"))
        text = " ".join(body[opener:close(body, opener) + 1].split())
        self.assertIn(
            "if = { limit = { te_tax_code_on = yes } "
            "add_modifier = { name = te_tax_spectrum_auction days = short_modifier_time } "
            "add_modifier = { name = te_tax_spectrum_auction_proceeds days = short_modifier_time "
            "multiplier = sv_money_flow_event_small } } "
            "else = { add_modifier = { name = re_spectrum_auction days = short_modifier_time } }", text)
        self.assertEqual(text.count("add_modifier"), 3)

    def test_the_modifiers_split_the_auction(self):
        modifiers = load(EVENT_MODIFIERS)
        original = modifiers["re_spectrum_auction"]
        self.assertEqual(original.get("tax_dividends_add"), "0.01")    # rule off: unchanged
        politics = modifiers["te_tax_spectrum_auction"]
        self.assertEqual({k: v for k, v in politics.items() if k != "icon"},
                         {k: v for k, v in original.items() if k not in ("icon", "tax_dividends_add")})
        proceeds = modifiers["te_tax_spectrum_auction_proceeds"]
        self.assertEqual({k: v for k, v in proceeds.items() if k != "icon"}, {"country_tax_income_add": "1"})
        for name in ("te_tax_spectrum_auction", "te_tax_spectrum_auction_proceeds"):
            with self.subTest(name=name):
                self.assertNotRegex(json.dumps(modifiers[name]), r'"tax_(income|dividends|land|per_capita|'
                                                                 r'consumption|heathen)_add"')
                self.assertIn(f" {name}:", raw(TAX_LOC))
                self.assertIn(f" {name}_desc:", raw(TAX_LOC))


# ---------------------------------------------------------------------------
# Vanilla objectives
# ---------------------------------------------------------------------------

class CountsAsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.triggers = load(TRIGGERS)
        cls.text = read(TRIGGERS)

    def test_each_counts_as_trigger_needs_the_rule_and_the_carrier(self):
        for kind in LAW_OF:
            body = self.triggers[f"te_tax_code_counts_as_{kind}"]
            with self.subTest(kind=kind):
                self.assertEqual(body["te_tax_code_on"], "yes")
                self.assertEqual(body["has_law"], f"law_type:{CARRIER}")

    def test_thresholds(self):
        per_capita = " ".join(block(self.text, "te_tax_code_counts_as_per_capita").split())
        self.assertIn("te_tax_view_en_head >= 1", per_capita)
        self.assertIn("te_tax_view_en_wage >= 1", per_capita)
        proportional = " ".join(block(self.text, "te_tax_code_counts_as_proportional").split())
        self.assertIn("te_tax_view_en_wage_rate >= 0.1", proportional)
        self.assertIn("te_tax_view_en_div_rate >= 0.025", proportional)
        graduated = " ".join(block(self.text, "te_tax_code_counts_as_graduated").split())
        self.assertIn("te_tax_view_en_wage_rate >= 0.1", graduated)
        self.assertIn("te_tax_view_en_div_rate >= te_tax_view_en_wage_rate", graduated)

    def test_tooltips_have_loc(self):
        loc = raw(TAX_LOC)
        for kind, law in LAW_OF.items():
            with self.subTest(kind=kind):
                line = re.search(rf"^ te_tax_tt_counts_as_{kind}:\d+ \"(.*)\"$", loc, re.M)
                self.assertIsNotNone(line)
                self.assertIn(f"${law}$", line.group(1))


class VanillaJournalEntryTest(unittest.TestCase):
    """Each patched entry is vanilla's (vanilla_parsed, 1.14.5) except its
    `complete`, where the taxation OR becomes a trigger_if on the rule: with the
    rule on, the original laws or the code counting as one of them; with it off
    (trigger_else), vanilla's OR unchanged."""

    @classmethod
    def setUpClass(cls):
        cls.mod = load(JE_OVERRIDES)
        with open(ROOT / VANILLA_JES, encoding="utf-8") as f:
            cls.vanilla = plain(json.load(f))

    def test_three_entries_replaced(self):
        self.assertEqual(set(self.mod), {f"REPLACE:{name}" for name in PATCHED_JES})
        self.assertTrue((ROOT / JE_OVERRIDES).read_bytes().startswith(b"\xef\xbb\xbf"))

    def taxation_or(self, complete):
        """Vanilla's OR over the taxation laws in a `complete` block."""
        ors = complete["OR"] if isinstance(complete["OR"], list) else [complete["OR"]]
        found = [o for o in ors if all(
            item in {f"law_type:{law}" for law in LAW_OF.values()}
            for values in o.values() for item in (values if isinstance(values, list) else [values]))]
        self.assertEqual(len(found), 1)
        return found[0]

    def test_everything_but_complete_is_vanilla(self):
        for name in PATCHED_JES:
            mine = dict(self.mod[f"REPLACE:{name}"])
            theirs = dict(self.vanilla[name])
            with self.subTest(name=name):
                mine.pop("complete")
                theirs.pop("complete")
                self.assertEqual(mine, theirs)

    def test_complete_branches_on_the_rule(self):
        for name, kinds in PATCHED_JES.items():
            mine = dict(self.mod[f"REPLACE:{name}"]["complete"])
            theirs = dict(self.vanilla[name]["complete"])
            original = self.taxation_or(theirs)
            with self.subTest(name=name):
                for law in original.values():
                    for item in (law if isinstance(law, list) else [law]):
                        self.assertIn(item, [f"law_type:{LAW_OF[kind]}" for kind in kinds])
                ifs = mine.pop("trigger_if")
                ifs = ifs if isinstance(ifs, list) else [ifs]
                rule_on = [branch for branch in ifs if branch.get("limit") == {"te_tax_code_on": "yes"}]
                self.assertEqual(len(rule_on), 1)
                rest_ifs = [branch for branch in ifs if branch is not rule_on[0]]
                if rest_ifs:
                    mine["trigger_if"] = rest_ifs if len(rest_ifs) > 1 else rest_ifs[0]
                # trigger_else binds to the trigger_if just before it: the rule's.
                self.assertEqual(mine.pop("trigger_else"), {"OR": original})
                expected = dict(original)
                tips = [{"text": f"te_tax_tt_counts_as_{kind}", f"te_tax_code_counts_as_{kind}": "yes"}
                        for kind in kinds]
                expected["custom_tooltip"] = tips if len(tips) > 1 else tips[0]
                self.assertEqual(rule_on[0]["OR"], expected)
                self.assertEqual(set(rule_on[0]), {"limit", "OR"})
                # The rest of vanilla's complete, untouched.
                if isinstance(theirs["OR"], list):
                    left = [o for o in theirs["OR"] if o is not original]
                    theirs["OR"] = left if len(left) > 1 else left[0]
                else:
                    theirs.pop("OR")
                self.assertEqual(mine, theirs)

    def test_rule_branch_follows_the_original_position(self):
        # trigger_else must come straight after the rule's trigger_if.
        text = read(JE_OVERRIDES)
        for name in PATCHED_JES:
            body = " ".join(block(text, f"REPLACE:{name}").split())
            with self.subTest(name=name):
                at = body.find("trigger_if = { limit = { te_tax_code_on = yes }")
                self.assertGreater(at, 0)
                opener = body.find("{", at)
                after = body[close(body, opener) + 1:].lstrip()
                self.assertTrue(after.startswith("trigger_else = {"), after[:60])


class TraditionalismTest(unittest.TestCase):
    def test_a_bill_under_traditionalism_taxes_no_wages_or_dividends(self):
        text = read(TRIGGERS)
        ready = block(text, "te_tax_draft_ready")
        # Read only while a draft is open: inside the draft-active branch.
        draft_branch = ready[:ready.find("trigger_else")]
        squashed = " ".join(draft_branch.split())
        self.assertIn("trigger_if = { limit = { has_law = law_type:law_traditionalism } custom_tooltip = { "
                      "text = te_tax_tt_draft_traditionalism te_tax_dr_eff_wage < 1 te_tax_dr_eff_div < 1 } }",
                      squashed)
        for name in ("introduce", "revise"):
            self.assertIn("te_tax_draft_ready = yes", block(text, f"te_tax_can_{name}"))
        self.assertRegex(raw(TAX_LOC), r"(?m)^ te_tax_tt_draft_traditionalism:\d+ \".*\$law_traditionalism\$.*\"$")


class LedgerTest(unittest.TestCase):
    def test_limitations_and_closures_are_recorded(self):
        ledger = raw(LEDGER).lower()
        for phrase in ("te_tax_native_controls_sgui", "te_tax.5", "te_tax_drift_level", "je_negotiate_taxes",
                       "negotiation option 7", "REPLACE:je_great_reforms_bureaucratic", "re_spectrum_auction",
                       "law_traditionalism", "party membership weights", "je_urbanization", "te_tax_debug.1"):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase.lower(), ledger)


if __name__ == "__main__":
    unittest.main()
