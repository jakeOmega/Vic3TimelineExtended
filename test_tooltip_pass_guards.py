"""Reads that logged errors while a tooltip was built, and their guards.

From the 2026-10-06 observer run's logs:

- A nuclear strike option's raw `nd_war_law_permits_strategic_strike` (through
  nd_war_law_exception's covered-country checks) read source_country and
  target_country on alliances, defensive pacts and joint exercises while the
  option's tooltip was described: about 2,900 errors a launch, plus 2,160
  "Scope dependent values in localization inside an any trigger" warnings.
  Each strike check in an option's trigger now sits in a custom_tooltip, as in
  nuke_diplo_action's `possible`, so the tooltip shows one line, not a
  description of every child.
- un_dossier_record read var:un_dos_<record> in a limit the tooltip evaluates
  without running the set_variable above it.
- gm_com_track_ruler compared a stored ruler who had since died.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CHECKS = ("nd_doctrine_permits_strike", "nd_pledge_permits_strike", "nd_war_law_permits_strategic_strike")


def _strip(text):
    return re.sub(r"#[^\n]*", "", text)


def option_trigger_lines(path):
    """(line number, text) for every line inside an option's `trigger = { }`."""
    inside = False
    for n, line in enumerate(path.read_text(encoding="utf-8-sig").split("\n"), 1):
        if line == "\t\ttrigger = {":
            inside = True
        elif inside and line == "\t\t}":
            inside = False
        elif inside:
            yield n, _strip(line)


class TestTooltipPassGuards(unittest.TestCase):
    def test_strike_checks_in_option_triggers_are_custom_tooltips(self):
        bad, wrapped = [], 0
        for name in ("events/nuclear_crisis_events.txt", "events/nuclear_incident_events.txt"):
            for n, line in option_trigger_lines(ROOT / name):
                for check in CHECKS:
                    if re.search(r"\b" + check + r"\b", line):
                        if "custom_tooltip = { text = nd_tt_" in line:
                            wrapped += 1
                        else:
                            bad.append(f"{name}:{n} {line.strip()}")
        self.assertEqual(bad, [], "wrap it as nuke_diplo_action's possible does")
        self.assertGreaterEqual(wrapped, 15)

    def test_the_dossier_reads_its_record_only_once_set(self):
        text = _strip((ROOT / "common/scripted_effects/un_dossier_effects.txt").read_text(encoding="utf-8-sig"))
        self.assertRegex(text, r"has_variable = un_dos_\$RECORD\$\s*var:un_dos_\$RECORD\$ > un_dossier_record_cap")

    def test_the_monument_ruler_compare_needs_a_living_ruler(self):
        text = _strip((ROOT / "common/scripted_effects/gm_commission_effects.txt").read_text(encoding="utf-8-sig"))
        self.assertRegex(text, r"has_variable = gm_ruler\s*exists = var:gm_ruler\s*var:gm_ruler = scope:gm_com_tracked_ruler")


if __name__ == "__main__":
    unittest.main()
