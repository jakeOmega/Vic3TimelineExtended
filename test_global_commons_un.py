# -*- coding: utf-8 -*-
"""The Global Commons' UN layer (docs/superpowers/archive/specs/2026-10-16-global-commons-design.md
§3, §4 and §6.5): the hooks the seabed allocation and the anti-satellite strike call,
the reads of the variables those systems write, and the figures the player is told.

test_un_convention_registry.py checks the two conventions (the Antarctic Treaty and
the anti-satellite moratorium) at every site a convention has; this file checks what
is particular to them and to the Law of the Sea's seabed terms.

- The hook contract between the branches: the four hook files hold exactly the names
  the contract fixes, at the scopes it fixes.
- Every read of a variable another system writes (te_seabed_policy, _policy_prev,
  _held_<basin>, the state's te_seabed_basin, te_asat_*) is guarded, so the layer
  runs before, or without, that system.
- The regime is written only by te_seabed_un_set_regime, with 1, 2 or 3.
- The figures the loc types by hand (royalty, defection, cooldown, the Scramble's
  return, denunciation, the station's upkeep, the cleaners' Delivery entry) are
  read back from the script values, so a retune fails here until the text follows.
- Each derived modifier has one writer file, and the state it is derived from is a
  variable or a convention's mirror (a revolution's winner keeps it).

Run: python3 -m unittest test_global_commons_un -v
"""

import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))


def _path(*parts):
    return os.path.join(REPO, *parts)


def _read(*parts):
    with open(_path(*parts), encoding="utf-8-sig") as f:
        return f.read()


def _strip(text):
    return re.sub(r"#[^\n]*", "", text)


def _block(text, name):
    m = re.search(r"^" + re.escape(name) + r"\s*=\s*\{", text, re.M)
    if m is None:
        raise AssertionError(f"{name} not found")
    depth = 0
    for i in range(m.end() - 1, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[m.end():i]
    raise AssertionError(f"{name} is not closed")


def _top_level(text):
    return set(re.findall(r"^([A-Za-z_][\w.]*)\s*=\s*\{", text, re.M))


def _value(name):
    text = _strip(_read("common", "script_values", "te_global_commons_un_values.txt"))
    m = re.search(rf"(?m)^{re.escape(name)}\s*=\s*\{{\s*value\s*=\s*(-?[\d.]+)\s*\}}", text)
    assert m, name
    return float(m.group(1))


def _loc():
    values = {}
    loc_dir = _path("localization", "english")
    for name in os.listdir(loc_dir):
        if name.endswith(".yml"):
            with open(os.path.join(loc_dir, name), encoding="utf-8-sig") as f:
                for line in f:
                    m = re.match(r' ([\w.\-]+):\d* "(.*)"\s*$', line)
                    if m:
                        values[m.group(1)] = m.group(2)
    return values


LOC = _loc()

UN_FILES = (
    ("common", "scripted_triggers", "te_seabed_un_hooks.txt"),
    ("common", "scripted_effects", "te_seabed_un_hooks.txt"),
    ("common", "scripted_triggers", "te_asat_un_hooks.txt"),
    ("common", "scripted_effects", "te_asat_un_hooks.txt"),
    ("common", "scripted_triggers", "te_global_commons_un_triggers.txt"),
    ("common", "scripted_effects", "te_global_commons_un_effects.txt"),
    ("common", "script_values", "te_global_commons_un_values.txt"),
    ("common", "decisions", "te_global_commons_un_decisions.txt"),
)


class HookContractTest(unittest.TestCase):
    """docs/superpowers/archive/specs/2026-10-16-global-commons-design.md and the branches'
    interface contract: same names, same scopes as the stubs."""

    CONTRACT = {
        ("common", "scripted_triggers", "te_seabed_un_hooks.txt"):
            {"te_seabed_reserved_half_eligible", "te_seabed_itlos_party", "te_seabed_southern_barred"},
        ("common", "scripted_effects", "te_seabed_un_hooks.txt"):
            {"te_seabed_un_update_regime", "te_seabed_un_on_policy_change"},
        ("common", "scripted_triggers", "te_asat_un_hooks.txt"): {"te_asat_moratorium_party"},
        ("common", "scripted_effects", "te_asat_un_hooks.txt"): {"te_asat_un_on_strike"},
    }
    # Helpers a hook file may define beside its hooks.
    HELPERS = {"te_seabed_un_set_regime", "te_seabed_un_regime_notices", "te_seabed_un_clear_scramble_clock"}

    def test_each_hook_file_holds_the_contracts_names(self):
        for parts, names in self.CONTRACT.items():
            with self.subTest(file="/".join(parts)):
                found = _top_level(_strip(_read(*parts)))
                self.assertLessEqual(names, found)
                self.assertLessEqual(found - names, self.HELPERS)

    def test_no_hook_is_a_stub(self):
        for parts, names in self.CONTRACT.items():
            text = _strip(_read(*parts))
            for name in names:
                with self.subTest(hook=name):
                    body = _block(text, name)
                    self.assertNotRegex(body, r"^\s*always\s*=\s*no\s*$")
                    self.assertTrue(body.strip())

    def test_the_regime_is_written_once_with_its_three_values(self):
        writes = []
        for parts in UN_FILES:
            for m in re.finditer(r"set_global_variable\s*=\s*\{\s*name\s*=\s*te_seabed_regime\s+value\s*=\s*(\S+)",
                                 _strip(_read(*parts))):
                writes.append(("/".join(parts), m.group(1)))
        self.assertEqual({w for _, w in writes}, {"$REGIME$"})
        effects = _strip(_read("common", "scripted_effects", "te_seabed_un_hooks.txt"))
        regimes = set(re.findall(r"te_seabed_un_set_regime\s*=\s*\{\s*REGIME\s*=\s*(\d)\s*\}", effects))
        self.assertEqual(regimes, {"1", "2", "3"})

    def test_the_strike_hook_raises_the_docket_situation(self):
        body = _block(_strip(_read("common", "scripted_effects", "te_asat_un_hooks.txt")), "te_asat_un_on_strike")
        self.assertIn("un_dkt_asat_pending", body)
        self.assertIn("un_dkt_asat_struck", body)
        scan = _block(_strip(_read("common", "scripted_effects", "un_docket_effects.txt")), "un_docket_scan")
        self.assertIn("has_global_variable = un_dkt_asat_pending", scan)
        self.assertIn("TYPE = 16", scan)


class ForeignReadsAreGuardedTest(unittest.TestCase):
    """Variables the seabed and debris code writes may be absent (an old save, the rule
    off, a system not yet run): every read has its existence check beside it."""

    COUNTRY = ("te_seabed_policy", "te_seabed_policy_prev", "te_seabed_held_southern",
               "te_seabed_held_pacific", "te_seabed_held_atlantic", "te_seabed_held_indian",
               "te_seabed_held_arctic", "te_seabed_basin")
    GLOBAL = ("te_asat_last_strike_month", "te_asat_strikes_total")

    def _files(self):
        for parts in UN_FILES:
            yield "/".join(parts), _strip(_read(*parts))
        for parts in (("common", "script_values", "un_dossier_values.txt"),
                      ("events", "un_events.txt"), ("events", "un_vote_events.txt"),
                      ("common", "scripted_triggers", "un_docket_triggers.txt")):
            yield "/".join(parts), _strip(_read(*parts))

    def test_every_read_is_guarded(self):
        for name, text in self._files():
            for var in self.COUNTRY:
                for m in re.finditer(rf"(?<![\w:])var:{var}\b", text):
                    window = text[max(0, m.start() - 200):m.start()]
                    with self.subTest(file=name, var=var, at=m.start()):
                        self.assertIn(f"has_variable = {var}", window)
            for var in self.GLOBAL:
                for m in re.finditer(rf"global_var:{var}\b", text):
                    window = text[max(0, m.start() - 200):m.start()]
                    with self.subTest(file=name, var=var, at=m.start()):
                        self.assertIn(f"has_global_variable = {var}", window)


class HandTypedFiguresTest(unittest.TestCase):
    """The loc states these figures in words; the script values hold them."""

    def test_the_royalty(self):
        values = _strip(_read("common", "script_values", "te_global_commons_un_values.txt"))
        body = _block(values, "te_seabed_level_output_value")
        output = sum(float(a) * float(b) for a, b in
                     re.findall(r"add\s*=\s*\{\s*value\s*=\s*([\d.]+)\s+multiply\s*=\s*([\d.]+)\s*\}", body))
        self.assertEqual(output, 44700)
        rate = _value("te_seabed_royalty_rate")
        per_level = output * rate
        seabed = LOC["je_un_terms_law_of_sea_seabed"]
        self.assertIn(f"#v {rate * 100:g}%#!", seabed)
        self.assertIn(f"@money!{per_level:,.0f} a level", seabed)
        self.assertIn(f"{rate * 100:g}% of their base output value", LOC["te_seabed_royalty_modifier_desc"])

    def test_the_defection_and_the_return(self):
        infamy, standing, case = (_value(f"te_seabed_defection_{k}") for k in ("infamy", "standing", "case"))
        years = _value("te_seabed_party_cooldown_months") / 12
        seabed = LOC["je_un_terms_law_of_sea_seabed"]
        self.assertIn(f"#R {infamy:g}#! infamy, #R {standing:g}#! standing and #R {case:g}#! to the case", seabed)
        self.assertIn(f"#v {years:g}#! years after it defected", seabed)
        self.assertIn(f"International Standing: −{standing:g}#!", LOC["te_seabed_defection_standing_tt"])
        self.assertIn(f"+{case:g} to the case", LOC["te_seabed_defection_case_tt"])
        for key in ("te_seabed_defection_tt", "te_seabed_party_cooldown_tt"):
            self.assertIn(f"#v {years:g}#! years", LOC[key])
        scramble_years = _value("te_seabed_scramble_return_months") / 12
        self.assertEqual(scramble_years, 2)
        self.assertIn("two years after fewer than two remain", seabed)
        self.assertEqual(_value("te_seabed_scramble_threshold"), 2)

    def test_the_return_counts_from_the_defection(self):
        """Seabed claims spec § 2.4: the defection stores its month, and the
        five years run from it; an old save's flag (below 12) keeps the old
        rule, five years from leaving."""
        hooks = _strip(_read("common", "scripted_effects", "te_seabed_un_hooks.txt"))
        body = _block(hooks, "te_seabed_un_on_policy_change")
        self.assertIn("name = te_seabed_defected value = te_history_month_index", body)
        leave = body[body.index("remove_variable = te_seabed_defected") - 600:]
        self.assertIn("var:te_seabed_defected < 12", leave)
        self.assertIn("te_seabed_party_return_month_value > te_history_month_index", leave)
        values = _strip(_read("common", "script_values", "te_global_commons_un_values.txt"))
        ret = _block(values, "te_seabed_party_return_month_value")
        self.assertIn("var:te_seabed_defected", ret)
        self.assertIn("add = te_seabed_party_cooldown_months", ret)

    def test_the_denunciation(self):
        infamy, standing, case = (_value(f"te_antarctic_denounce_{k}") for k in ("infamy", "standing", "case"))
        terms = LOC["je_un_terms_antarctic"]
        self.assertIn(f"#R {infamy:g}#! infamy, #R {standing:g}#! standing and #R {case:g}#! to the case", terms)
        self.assertIn(f"International Standing: −{standing:g}#!", LOC["te_antarctic_denounce_standing_tt"])
        self.assertIn(f"+{case:g} to the case", LOC["te_antarctic_denounce_case_tt"])
        self.assertEqual(_value("te_antarctic_lapse_threshold"), 2)
        self.assertIn("two or more", terms)

    def test_the_station(self):
        share = _value("te_antarctic_station_upkeep_share")
        floor = _value("te_antarctic_station_upkeep_floor")
        self.assertEqual(share, 0.001)
        for key in ("te_antarctic_station_upkeep_desc", "te_decision_open_antarctic_station_desc",
                    "te_antarctic_station_upkeep_tt"):
            with self.subTest(key=key):
                self.assertIn("a tenth of a percent", LOC[key])
                self.assertRegex(LOC[key], rf"{floor:,.0f} a week")
        mods = _strip(_read("common", "static_modifiers", "te_global_commons_un_modifiers.txt"))
        regime = _block(mods, "un_regime_antarctic_station_modifier")
        research = float(re.search(r"country_tech_research_speed_mult\s*=\s*([\d.]+)", regime).group(1))
        for key in ("te_antarctic_station_treaty_term_tt", "un_antarctic_terms_tt"):
            with self.subTest(key=key):
                self.assertIn(f"#G +{research * 100:g}%#! research speed", LOC[key])
        policy = _block(mods, "un_antarctic_policy_modifier")
        grant = float(re.search(r"country_un_authority_target_add\s*=\s*([\d.]+)", policy).group(1))
        self.assertIn(f"#G {grant:g}#!", LOC["un_antarctic_terms_tt"])
        self.assertEqual(grant, _value("te_gc_chk_policy_expected"))

    def test_the_cleaners_delivery_entry(self):
        points = _value("un_asat_cleaner_delivery_points")
        self.assertIn(f"#G {points:g}#! × its weight", LOC["je_un_terms_asat"])


class DerivedStateTest(unittest.TestCase):
    """A revolution's winner keeps variables and the conventions' mirrors, not
    modifiers: each modifier here is rebuilt from them, in one file."""

    DERIVED = ("te_seabed_royalty_modifier", "te_antarctic_station_modifier",
               "te_antarctic_station_upkeep", "un_antarctic_policy_modifier")

    def test_each_derived_modifier_has_one_writer_file(self):
        writers = {m: set() for m in self.DERIVED}
        for top in ("common", "events"):
            for root, _dirs, files in os.walk(_path(top)):
                for name in files:
                    if not name.endswith(".txt"):
                        continue
                    path = os.path.join(root, name)
                    with open(path, encoding="utf-8-sig") as f:
                        text = _strip(f.read())
                    for mod in self.DERIVED:
                        if re.search(rf"add_modifier\s*=\s*\{{\s*name\s*=\s*{mod}\b", text):
                            writers[mod].add(os.path.relpath(path, REPO))
        for mod, files in writers.items():
            with self.subTest(modifier=mod):
                self.assertEqual(files, {os.path.join("common", "scripted_effects", "te_global_commons_un_effects.txt")})

    def test_the_monthly_pulse_rebuilds_them(self):
        effects = _strip(_read("common", "scripted_effects", "te_global_commons_un_effects.txt"))
        monthly = _block(effects, "te_gc_un_country_monthly")
        for call in ("te_seabed_royalty_refresh", "te_antarctic_station_refresh", "te_antarctic_policy_refresh"):
            self.assertIn(f"{call} = yes", monthly)
        self.assertIn("te_antarctic_has_station = yes", _block(effects, "te_antarctic_station_refresh"))
        self.assertIn("te_antarctic_treaty_party = yes", _block(effects, "te_antarctic_policy_refresh"))
        triggers = _strip(_read("common", "scripted_triggers", "te_global_commons_un_triggers.txt"))
        self.assertIn("has_variable = un_antarctic_treaty_modifier_on", _block(triggers, "te_antarctic_treaty_party"))
        self.assertIn("has_variable = un_law_of_sea_modifier_on", _block(triggers, "te_seabed_itlos_ratified"))
        hooks = _strip(_read("common", "scripted_triggers", "te_asat_un_hooks.txt"))
        self.assertIn("has_variable = un_asat_moratorium_modifier_on", _block(hooks, "te_asat_moratorium_party"))

    def test_the_station_and_denunciation_need_the_global_commons_rule(self):
        decisions = _strip(_read("common", "decisions", "te_global_commons_un_decisions.txt"))
        for name in ("te_decision_open_antarctic_station", "te_decision_denounce_antarctic_treaty"):
            with self.subTest(decision=name):
                self.assertIn("has_game_rule = global_commons_enabled", _block(decisions, name))

    def test_the_un_rule_keeps_the_seabed_open(self):
        triggers = _strip(_read("common", "scripted_triggers", "te_global_commons_un_triggers.txt"))
        governs = _block(triggers, "te_seabed_itlos_governs")
        self.assertIn("has_game_rule = united_nations_enabled", governs)
        self.assertIn("has_global_variable = un_agency_itlos", governs)
        hooks = _strip(_read("common", "scripted_effects", "te_seabed_un_hooks.txt"))
        update = _block(hooks, "te_seabed_un_update_regime")
        first = re.search(r"if\s*=\s*\{\s*limit\s*=\s*\{\s*NOT\s*=\s*\{\s*te_seabed_itlos_governs\s*=\s*yes\s*\}\s*\}"
                          r"\s*te_seabed_un_set_regime\s*=\s*\{\s*REGIME\s*=\s*1\s*\}", update)
        self.assertTrue(first, "the regime is Open first whenever the Law of the Sea does not govern")


if __name__ == "__main__":
    unittest.main()
