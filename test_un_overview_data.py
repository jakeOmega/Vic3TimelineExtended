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

# A change the council display can see: the seat's mirror variable
# (un_permanent_member_modifier_on) set or cleared. un_state_restore and
# te_debug_un_drop move only the modifier, and un_p5_display_seat reads the
# mirror (a modifier added in an effect block is invisible to the rest of it).
SEAT_CHANGE = re.compile(
    r"un_state_(?:on|off|forget|record)\s*=\s*\{\s*MODIFIER\s*=\s*un_permanent_member_modifier\s*\}"
    r"|(?:set|remove)_variable\s*=\s*un_permanent_member_modifier_on"
)
REFRESH = "un_p5_display_refresh = yes"
# Blocks that change a seat without refreshing, and why that is right.
SEAT_CHANGE_EXEMPT = {
    "un_state_forget_representation": "called only by un_state_rebuild, which refreshes after it",
}
ON_ACTIONS = os.path.join(REPO, "common", "on_actions", "un_on_actions.txt")
DISPLAY_EFFECTS = os.path.join(REPO, "common", "scripted_effects", "un_overview_display_effects.txt")


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


def _enclosing(text, pos):
    """Spans (start, end) of the blocks enclosing pos, innermost first."""
    spans, depth_stack = [], []
    for i, ch in enumerate(text):
        if ch == "{":
            depth_stack.append(i)
        elif ch == "}":
            start = depth_stack.pop()
            if start < pos < i:
                spans.append((start, i))
    return sorted(spans, key=lambda sp: sp[1] - sp[0])


def _seat_files():
    for sub in (("common", "scripted_effects"), ("events",), ("common", "journal_entries")):
        for path in glob.glob(os.path.join(REPO, *sub, "*.txt")):
            yield path, sub[-1] == "scripted_effects"


class SeatRefreshTest(unittest.TestCase):
    def test_every_seat_change_refreshes_the_council_display(self):
        """A refresh follows each seat change inside a block around it. A scripted
        effect may refresh at its own end; an event or a journal entry must do it
        inside the option or branch, not anywhere later in the file."""
        sites = 0
        for path, top_level_ok in _seat_files():
            text = _strip_comments(_read(path))
            tops = [(m.group(1), m.start()) for m in re.finditer(r"^([\w.]+)\s*=\s*\{", text, re.M)]
            for m in SEAT_CHANGE.finditer(text):
                sites += 1
                top = max((t for t in tops if t[1] <= m.start()), key=lambda t: t[1])[0]
                if top in SEAT_CHANGE_EXEMPT:
                    continue
                spans = _enclosing(text, m.start())
                if not top_level_ok:
                    spans = spans[:-1]
                self.assertTrue(any(REFRESH in text[m.end():end] for _, end in spans),
                                f"{os.path.basename(path)}:{text.count(chr(10), 0, m.start()) + 1} "
                                f"({top}) changes a permanent seat without refreshing after it")
        self.assertGreaterEqual(sites, 8)

    def test_refresh_only_where_a_seat_changes(self):
        """Mirror bookkeeping and modifier-only restores change nothing the council
        display reads; a refresh there is a wasted sweep (every holder, monthly)."""
        for path, _ in _seat_files():
            for name, body in _top_blocks(_read(path)):
                if REFRESH in body and name != "un_p5_display_refresh":
                    self.assertRegex(body, SEAT_CHANGE, f"{os.path.basename(path)}: {name} refreshes "
                                     "the council display but changes no seat")

    def test_the_council_is_read_from_the_mirror(self):
        body = _strip_comments(_read(DISPLAY_EFFECTS))
        self.assertNotIn("is_un_permanent_member", body)
        self.assertNotIn("has_modifier", body)
        self.assertEqual(body.count("has_variable = un_permanent_member_modifier_on"), 2)


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

    def test_the_shares_are_snapshotted_monthly(self):
        body = _block(_read(AUTH_EFFECTS), "un_authority_monthly_update")
        for g in ("un_member_country_share", "un_member_gdp_share", "un_member_pop_share",
                  "un_vote_eligible_count"):
            self.assertIn(f"name = {g} value", body)

    def test_the_council_is_refreshed_after_the_monthly_seat_fill(self):
        self.assertNotIn(REFRESH, _block(_read(AUTH_EFFECTS), "un_authority_monthly_update"))
        body = _block(_read(ON_ACTIONS), "un_global_authority_on_action")
        self.assertIn(REFRESH, body)
        self.assertGreater(body.index(REFRESH), body.index("un_seat_monthly_update = yes"))

    def test_the_tally_never_divides_by_one_before_the_first_snapshot(self):
        body = _block(_read(DISPLAY), "un_disp_res_eligible")
        self.assertIn("un_disp_res_yes", body)
        self.assertIn("un_disp_res_no", body)

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

JE = os.path.join(REPO, "common", "journal_entries", "je_united_nations.txt")
SGUIS = os.path.join(REPO, "common", "scripted_guis", "un_chamber_sguis.txt")


class StatusDescTest(unittest.TestCase):
    """The entry's status text says only what the overview does not (owner, 2026-09-28)."""

    def _status(self):
        text = _strip_comments(_read(JE))
        m = re.search(r"\tstatus_desc = \{", text)
        depth = 0
        for j in range(m.end() - 1, len(text)):
            depth += {"{": 1, "}": -1}.get(text[j], 0)
            if depth == 0:
                return text[m.end():j]

    def test_nothing_the_overview_shows(self):
        status = self._status()
        for gone in ("je_un_status_member", "je_un_status_not_member", "je_un_status_suspended",
                     "je_un_status_not_eligible", "je_un_tier_line_", "je_un_crisis_line_",
                     "je_un_authority_heading", "je_un_security_council_", "je_un_agenc"):
            self.assertNotIn(gone, status, gone)

    def test_what_only_it_says_stays(self):
        status = self._status()
        for kept in ("je_un_hq_host", "je_un_hq_established", "je_un_statistics",
                     "je_un_active_programs", "je_un_status_conference", "je_un_status_dissolved"):
            self.assertIn(kept, status, kept)

    def test_a_non_member_learns_what_joining_brings(self):
        self.assertIn("je_un_status_not_member", _block(_read(SGUIS), "un_chamber_status_sgui"))

if __name__ == "__main__":
    unittest.main()
