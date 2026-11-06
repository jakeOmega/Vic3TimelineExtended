"""Solar System Colonization's modifiers are scaling modifiers on je_space_race_solar_colonization.

Since 1.15 the entry declares each in `scaling_modifiers_while_active` and the
engine re-reads its value from the owning country about every four days
(design: docs/superpowers/specs/2026-11-06-scaling-modifiers-design.md § 4.10).
The 80 specializations, the 40 discovery outcomes and the six facilities are
declared in a generated file (common/journal_entries/sr_sites_generated.txt,
an INJECT into the entry, from scripts/generators/gen_solar_sites.py); the six
population and autonomy modifiers and Interplanetary Trade Networks in the
hand-written entry (je_space_race.txt). These tests pin each declaration and
its value's "off" gate, which must read 0 wherever the old code removed the
modifier, and that the refresh code the declarations replaced is gone.
test_journal_entry_shape.py checks the tree-wide rule that nothing adds,
removes or tests a declared key; test_solar_sites.py that the generated file
is current.
"""

import re
import sys
import unittest
from pathlib import Path

from je_multiplier_scope_audit import parse_text

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts" / "generators"))

import gen_solar_sites as gss  # noqa: E402
import test_journal_entry_shape as shape  # noqa: E402

ENTRY = "je_space_race_solar_colonization"
JE = ROOT / "common/journal_entries/je_space_race.txt"
GENERATED = ROOT / gss.ENTRY_OUT
LEGACY = "common/scripted_effects/legacy_modifier_cleanup.txt"

# The hand-written seven: modifier -> (the conjuncts of its value's limit, what it adds).
CONTESTED = "sr_colonies_contested_enabled = yes"
HAND = {
    "sr_solar_system_trade": (["has_variable = sr_completed_solar_colonization"], "1"),
    "sr_emigration_programme": ([CONTESTED, "sr_emig_level_value >= 1"], "sr_emig_level_value"),
    "sr_offworld_population": ([CONTESTED, "sr_offworld_pop_total >= sr_offworld_bonus_minimum"], "sr_offworld_units"),
    "sr_module_upkeep": ([CONTESTED, "sr_mod_upkeep_levels >= 1"], "sr_mod_upkeep_levels"),
    "sr_free_colony_supply": ([CONTESTED, "sr_free_supply_count >= 1"], "sr_free_supply_count"),
    "sr_free_colony_trade": ([CONTESTED, "sr_free_trade_units > 0"], "sr_free_trade_units"),
    "sr_colonial_garrisons": ([CONTESTED, "sr_garrison_count >= 1"], "sr_garrison_count"),
}

# The old multipliers, read through owner from the entry's scope. Nothing calls them
# now; an older save's added copy may still name one until the strip removes it.
WRAPPERS = {
    "common/script_values/sr_colony_population_values.txt": ("sr_emig_upkeep_units", "sr_offworld_bonus_units"),
    "common/script_values/sr_colony_module_values.txt": ("sr_mod_upkeep_units",),
    "common/script_values/sr_colony_autonomy_values.txt": ("sr_free_supply_units", "sr_free_trade_units_entry",
                                                          "sr_garrison_units"),
    str(gss.VALUES_OUT): tuple(f"sr_mod_units_{f.key}_entry" for f in gss.FACILITIES if f.modifier),
}
PENDING = '# PENDING REMOVAL with the "1.15 scaling modifiers" block of legacy_je_modifier_cleanup_effect (after 2026-12-31)'


def _text(path):
    return Path(path).read_text(encoding="utf-8-sig")


def _blank_comments(text):
    return re.sub(r"#[^\n]*", "", text)


def _declaration_texts(text):
    """modifier -> [the declaration's text] for every scaling_modifiers_while_active block."""
    out = {}
    text = _blank_comments(text)
    for m in re.finditer(r"scaling_modifiers_while_active = \{", text):
        depth, i = 1, m.end()
        while depth:
            depth += {"{": 1, "}": -1}.get(text[i], 0)
            i += 1
        body = text[m.end():i - 1]
        name = re.search(r"modifier = (\w+)", body).group(1)
        out.setdefault(name, []).append(" ".join(body.split()))
    return out


class GeneratedDeclarationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = _text(GENERATED)
        cls.declared = _declaration_texts(cls.text)

    def test_the_file_injects_into_the_entry_and_only_declares(self):
        nodes, _ = parse_text(self.text, gss.ENTRY_OUT.as_posix())
        self.assertEqual([n.key for n in nodes], [f"INJECT:{ENTRY}"])
        self.assertEqual({c.key for c in nodes[0].children}, {"scaling_modifiers_while_active"})
        # mod_structure_audit's style flag on an INJECT into a mod-only entry, reviewed
        self.assertRegex(self.text, rf"(?m)^INJECT:{ENTRY} = \{{ # REVIEWED \d{{4}}-\d\d-\d\d: ")

    def test_every_specialization_is_declared_once_at_its_multiplier_while_held(self):
        for site in gss.SITES:
            for slot, modifier in zip(("a", "b"), gss.spec_modifiers(site)):
                with self.subTest(modifier=modifier):
                    self.assertEqual(self.declared.get(modifier), [
                        f"modifier = {modifier} value = {{ value = 0 if = {{ limit = {{ has_variable = "
                        f"{modifier}_held }} add = sr_site_mult_{slot}_{site.key} }} }}"])

    def test_every_discovery_outcome_is_declared_once_at_one_while_held(self):
        for site in gss.SITES:
            for d in site.discoveries:
                for modifier in gss.discovery_modifiers(d):
                    with self.subTest(modifier=modifier):
                        self.assertEqual(self.declared.get(modifier), [
                            f"modifier = {modifier} value = {{ value = 0 if = {{ limit = {{ has_variable = "
                            f"{modifier}_held }} add = 1 }} }}"])

    def test_every_facility_is_declared_once_at_its_staffed_levels(self):
        for f in gss.FACILITIES:
            if not f.modifier:
                continue
            modifier = f"sr_module_{f.key}"
            with self.subTest(modifier=modifier):
                self.assertEqual(self.declared.get(modifier), [
                    f"modifier = {modifier} value = {{ value = 0 if = {{ limit = {{ {CONTESTED} "
                    f"sr_mod_units_{f.key} > 0 }} add = sr_mod_units_{f.key} }} }}"])

    def test_nothing_else_is_declared(self):
        expected = {m for m, _, _ in gss.entry_declarations()}
        self.assertEqual(len(expected), 80 + 40 + 6)
        self.assertEqual(set(self.declared), expected)

    def test_the_multiplier_reads_the_global_record_only(self):
        # The value's root is the holder; sr_site_mult reads the world's global
        # record (and the holder through it), so it reads alike from any scope.
        values = _blank_comments(_text(ROOT / gss.VALUES_OUT))
        for site in gss.SITES:
            for slot in ("a", "b"):
                body = shape_block(values, f"sr_site_mult_{slot}_{site.key}")
                with self.subTest(site=site.key, slot=slot):
                    self.assertNotIn("owner", body)
                    self.assertNotIn("var:", body.replace("global_var:", ""))


def shape_block(text, name):
    m = re.search(rf"(?m)^{re.escape(name)} = \{{", text)
    depth, i = 1, m.end()
    while depth:
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        i += 1
    return text[m.end():i - 1]


class HandWrittenDeclarationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        text = _blank_comments(_text(JE))
        start = re.search(rf"(?m)^{ENTRY} = \{{", text).start()
        cls.entry_text = text[start:text.index("\n}\n", start)]
        cls.declared = _declaration_texts(cls.entry_text)

    # The milestone half's cost, funding and approach declarations sit on this
    # entry too (test_space_race_scaling_modifiers.py); they are not colony
    # modifiers.
    MILESTONE_KEYS = {"sr_space_program_cost", "sr_funding_progress", "sr_funding_throughput",
                      "sr_safe_approach", "sr_ambitious_approach"}

    def test_the_entry_declares_exactly_the_seven_once_each(self):
        self.assertEqual(set(self.declared) - self.MILESTONE_KEYS, set(HAND))
        for modifier, texts in self.declared.items():
            self.assertEqual(len(texts), 1, modifier)

    def test_each_value_is_zero_outside_its_gate(self):
        for modifier, (limit, add) in HAND.items():
            with self.subTest(modifier=modifier):
                self.assertEqual(self.declared[modifier], [
                    f"modifier = {modifier} value = {{ value = 0 if = {{ limit = {{ {' '.join(limit)} }} "
                    f"add = {add} }} }}"])

    def test_the_values_read_the_country_not_owner(self):
        # The old *_units wrappers read the country through owner from the
        # entry's scope; a declaration's root is the country already.
        for modifier, (_, add) in HAND.items():
            self.assertFalse(add.endswith(("_units_entry", "_upkeep_units", "_bonus_units")), modifier)

    def test_the_trade_reward_is_recorded_and_never_added(self):
        pulse = self.entry_text[self.entry_text.index("on_monthly_pulse = {"):]
        self.assertIn("set_variable = { name = sr_completed_solar_colonization value = yes }", pulse)
        self.assertNotIn("add_modifier", pulse)


class RetiredCodeTests(unittest.TestCase):
    def test_the_refresh_and_repair_code_is_gone(self):
        gone = ("sr_emig_refresh_modifiers", "sr_mod_refresh_facilities", "sr_sync_colony_modifier_base",
                "sr_sync_colony_spec_base", "sr_sync_colony_discovery_modifiers", "sr_sites_sync_entry_specs",
                "sr_mod_seen_self_check", "sr_grant_colony_modifier", "sr_site_show_modifier",
                "sr_site_hide_modifier", "sr_site_show_modifier_at", "sr_site_hide_modifier_at")
        pattern = re.compile(r"\b(" + "|".join(gone) + r")\b")
        for sub in ("common", "events"):
            for path in sorted((ROOT / sub).rglob("*.txt")):
                with self.subTest(file=path.name):
                    self.assertIsNone(pattern.search(_blank_comments(_text(path))))
        for path in sorted((ROOT / "gui").rglob("*.gui")):
            with self.subTest(file=path.name):
                self.assertNotIn("sr_emig_refresh_modifiers", _text(path))

    def test_no_solar_key_is_added_removed_or_tested_outside_the_old_save_strip(self):
        """test_journal_entry_shape's tree rule, outside legacy_modifier_cleanup.txt, whose
        re-adds of the colony keys the controller turns remove-only (rule 7)."""
        declared = set(_declaration_texts(_text(GENERATED))) | set(HAND)
        named = re.compile(r"\b(" + "|".join(sorted(declared)) + r")\b")
        found, scanned = [], 0
        for sub in ("common", "events"):
            for path in sorted((ROOT / sub).rglob("*.txt")):
                rel = path.relative_to(ROOT).as_posix()
                if rel == LEGACY or not named.search(_text(path)):
                    continue  # only a file that names a key can misuse one
                scanned += 1
                found += shape.misuse_sites(shape._parse(path), declared, rel)
        self.assertGreater(scanned, 5)
        self.assertEqual(found, [])

    def test_the_old_multipliers_are_uncalled_and_marked(self):
        names = [name for group in WRAPPERS.values() for name in group]
        pattern = re.compile(r"\b(" + "|".join(names) + r")\b")
        seen = {name: 0 for name in names}
        for sub in ("common", "events", "gui"):
            for path in sorted((ROOT / sub).rglob("*.*")):
                if path.suffix in (".txt", ".gui"):
                    for m in pattern.finditer(_blank_comments(_text(path))):
                        seen[m.group(1)] += 1
        for rel, group in WRAPPERS.items():
            text = _text(ROOT / rel)
            for name in group:
                with self.subTest(value=name):
                    self.assertIn(f"{PENDING}\n{name} = {{", text)
                    self.assertEqual(seen[name], 1)  # its definition, never a call


if __name__ == "__main__":
    unittest.main()
