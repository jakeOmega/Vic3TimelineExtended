"""Static checks for the UN overview's script data.

Spec: docs/superpowers/specs/2026-09-28-un-gui-pass-design.md, section 4.
"""
import glob
import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
DISPLAY = os.path.join(REPO, "common", "script_values", "un_overview_display_values.txt")
AUTH_EFFECTS = os.path.join(REPO, "common", "scripted_effects", "un_authority_effects.txt")
UN_VALUES = os.path.join(REPO, "common", "script_values", "un_script_values.txt")
PILLARS = ("participation", "commitment", "credibility", "funding", "order", "delivery")

SEAT_CHANGE = re.compile(
    r"MODIFIER\s*=\s*un_permanent_member_modifier"
    r"|add_modifier\s*=\s*\{\s*name\s*=\s*un_permanent_member_modifier"
    r"|remove_modifier\s*=\s*un_permanent_member_modifier"
)


def _read(path):
    with open(path, encoding="utf-8-sig") as f:
        return f.read()


def _strip_comments(text):
    return "\n".join(line.split("#", 1)[0] for line in text.split("\n"))


def _top_blocks(text):
    """(name, body) for every top-level `name = { ... }`, comments removed."""
    text = _strip_comments(text)
    for m in re.finditer(r"^([\w.]+)\s*=\s*\{", text, re.M):
        depth, i = 0, m.end() - 1
        for j in range(i, len(text)):
            if text[j] == "{":
                depth += 1
            elif text[j] == "}":
                depth -= 1
                if depth == 0:
                    yield m.group(1), text[i + 1:j]
                    break


def _block(text, name):
    for n, body in _top_blocks(text):
        if n == name:
            return body
    raise AssertionError(f"no top-level block {name}")


class SeatRefreshTest(unittest.TestCase):
    def test_every_seat_change_refreshes_the_council_display(self):
        paths = glob.glob(os.path.join(REPO, "common", "scripted_effects", "*.txt"))
        paths += glob.glob(os.path.join(REPO, "events", "*.txt"))
        sites = 0
        for path in paths:
            for name, body in _top_blocks(_read(path)):
                if SEAT_CHANGE.search(body):
                    sites += 1
                    self.assertIn("un_p5_display_refresh = yes", body,
                                  f"{os.path.basename(path)}: {name} changes a permanent seat "
                                  "but does not call un_p5_display_refresh")
        self.assertGreaterEqual(sites, 7)


class DisplayValueTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.display = _read(DISPLAY)

    def test_every_counted_agency_has_a_display_value(self):
        agencies = re.findall(r"un_agency_(\w+)", _block(_read(UN_VALUES), "un_agency_count"))
        self.assertEqual(len(agencies), 11)
        for a in agencies:
            self.assertRegex(self.display, rf"(?m)^un_disp_agency_{a} = \{{")

    def test_every_pillar_has_bar_and_trend_values(self):
        for p in PILLARS:
            for suffix in ("pos", "neg", "delta", "trend"):
                self.assertRegex(self.display, rf"(?m)^un_disp_pillar_{p}_{suffix} = \{{")

    def test_every_global_read_is_guarded(self):
        """A global_var:X read sits in a block that first checks has_global_variable = X."""
        for name, body in _top_blocks(self.display):
            for var in set(re.findall(r"global_var:(\w+)", body)):
                self.assertIn(f"has_global_variable = {var}", body,
                              f"{name} reads global_var:{var} without checking it exists")
            for var in set(re.findall(r"\bvar:(\w+)", body)):
                self.assertIn(f"has_variable = {var}", body,
                              f"{name} reads var:{var} without checking it exists")


class MonthlySnapshotTest(unittest.TestCase):
    def test_each_pillar_keeps_last_months_value_before_the_snapshot(self):
        body = _block(_read(AUTH_EFFECTS), "un_authority_monthly_update")
        for p in PILLARS:
            prev = body.find(f"name = un_pillar_{p}_prev")
            snap = body.find(f"name = un_pillar_{p} value")
            self.assertGreaterEqual(prev, 0, f"no un_pillar_{p}_prev copy")
            self.assertLess(prev, snap, f"un_pillar_{p}_prev must be copied before the snapshot")

    def test_the_shares_and_the_council_are_refreshed_monthly(self):
        body = _block(_read(AUTH_EFFECTS), "un_authority_monthly_update")
        for g in ("un_member_country_share", "un_member_gdp_share", "un_member_pop_share",
                  "un_vote_eligible_count"):
            self.assertIn(f"name = {g} value", body)
        self.assertIn("un_p5_display_refresh = yes", body)


OVERVIEW = os.path.join(REPO, "gui", "journal_entry_widgets", "un_overview_widget.gui")


class OverviewGuiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gui = _read(OVERVIEW)

    def _codes(self, value):
        return {int(n) for n in re.findall(
            rf"ScriptValue\('{value}'\), '\(CFixedPoint\)(-?\d+)'", self.gui)}

    def test_every_agency_has_a_slot(self):
        agencies = re.findall(r"un_agency_(\w+)", _block(_read(UN_VALUES), "un_agency_count"))
        for a in agencies:
            self.assertIn(f"ScriptValue('un_disp_agency_{a}')", self.gui, a)

    def test_every_membership_state_and_tier_has_an_icon(self):
        self.assertEqual(self._codes("un_disp_member_code"), set(range(7)))
        self.assertEqual(self._codes("un_disp_tier_code"), set(range(5)))

    def test_five_council_seats_gated_on_the_count(self):
        for n in range(1, 6):
            self.assertIn(f"Var('un_p5_seat_{n}')", self.gui)
        self.assertEqual(
            {int(n) for n in re.findall(
                r"GreaterThanOrEqualTo_CFixedPoint\( JournalEntry\.GetCountry\.MakeScope\.ScriptValue\('un_disp_p5_count'\), '\(CFixedPoint\)(\d)' \)",
                self.gui)},
            set(range(1, 6)))

    def test_rows_below_membership_wait_for_the_first_update(self):
        self.assertIn("GetScriptedGui('un_authority_ready_sgui').IsShown", self.gui)

if __name__ == "__main__":
    unittest.main()
