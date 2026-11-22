"""Two events whose text or options did not cover everything their gate lets in.

Issue #1615:

- movement_events_te.100 ("The Movement Broken") shows `desc_faded`, "the
  government never had to move against it", when no suppression was used.
  je_civil_rights.on_fail also sends .100 after 18 months of Segregationist
  Consolidation, which is the government moving against the movement, so the
  faded text must need both trackers at 0. It reads them through the
  cr_months_disp_* script values, which give 0 for a tracker never set.
- cultural_hegemony.4 ("The Old Ways Answer") fires when the Devout, the Armed
  Forces or the Landowners hold 15% clout, and its description names all
  three. Its options moved only the first two, so a country where only the
  Landowners are strong saw options about other groups.

No game install needed.
"""

import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))


def _read(*parts):
    with open(os.path.join(REPO, *parts), encoding="utf-8-sig") as f:
        return re.sub(r"#[^\n]*", "", f.read())


def _block(text, opening):
    """The body of the block that `opening` (ending in `{`) starts."""
    start = text.index(opening) + len(opening)
    depth = 1
    for i in range(start, len(text)):
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        if depth == 0:
            return text[start:i]
    raise AssertionError(f"unclosed block {opening!r}")


def _blocks(text, key):
    """Every `key = { ... }` body in text."""
    out, pos = [], 0
    pattern = re.compile(rf"(?<![\w.:]){re.escape(key)}\s*=\s*\{{")
    while True:
        m = pattern.search(text, pos)
        if m is None:
            return out
        body = _block(text[m.start():], m.group(0))
        out.append(body)
        pos = m.end() + len(body)


class MovementBrokenFadedTextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.event = _block(_read("events", "movement_events_te.txt"), "\nmovement_events_te.100 = {")
        cls.values = _read("common", "script_values", "civil_rights_values.txt")
        cls.entry = _read("common", "journal_entries", "je_civil_rights.txt")

    def _faded_trigger(self):
        for desc in _blocks(_block(self.event, "desc = {"), "triggered_desc"):
            if re.search(r"desc\s*=\s*movement_events_te\.100\.desc_faded\b", desc):
                return _block(desc, "trigger = {")
        raise AssertionError("no triggered_desc shows movement_events_te.100.desc_faded")

    def test_on_fail_sends_it_for_segregation_alone(self):
        # The premise: without this branch the faded text could test
        # suppression only.
        # The outcome that sends it requires cr_fail_ending_now = 1 (#1431), and
        # that value's branch counts segregation alone.
        sent = self.entry.index("id = movement_events_te.100")
        outcome = self.entry[self.entry.rindex("outcome = {", 0, sent):sent]
        self.assertRegex(outcome, r"\bcr_fail_ending_now\s*=\s*1\b")
        chain = _block(self.values, "cr_fail_ending_now = {")
        first = _block(chain, "if = {")
        self.assertRegex(first, r"\bvalue\s*=\s*1\b")
        self.assertRegex(first, r"cr_months_disp_segregationist\s*>\s*18")

    def test_faded_text_needs_both_trackers_at_zero(self):
        trigger = self._faded_trigger()
        self.assertRegex(trigger, r"\bcr_months_disp_suppression\s*=\s*0\b")
        self.assertRegex(trigger, r"\bcr_months_disp_segregationist\s*=\s*0\b")
        self.assertNotRegex(trigger, r"\b(OR|NOT|NOR|NAND)\s*=", "both tests must hold together")

    def test_an_unset_tracker_reads_as_zero(self):
        for tracker in ("suppression", "segregationist"):
            with self.subTest(tracker=tracker):
                value = _block(self.values, f"\ncr_months_disp_{tracker} = {{")
                self.assertRegex(value, r"^\s*value\s*=\s*0\b")
                self.assertRegex(value, rf"has_variable\s*=\s*cr_{tracker}_months")


class CulturalBacklashGroupsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.event = _block(_read("events", "cultural_hegemony_events.txt"), "\ncultural_hegemony.4 = {")

    def test_every_option_acts_on_every_group_in_the_gate(self):
        gate = set(re.findall(r"is_interest_group_type\s*=\s*(ig_\w+)", _block(self.event, "trigger = {")))
        self.assertEqual(gate, {"ig_devout", "ig_armed_forces", "ig_landowners"})
        options = _blocks(self.event, "option")
        self.assertEqual(len(options), 2)
        for option in options:
            name = re.search(r"name\s*=\s*(\S+)", option).group(1)
            effects = option.replace(_block(option, "ai_chance = {"), "")
            for group in sorted(gate):
                with self.subTest(option=name, group=group):
                    self.assertRegex(
                        effects, rf"interest_group\s*=\s*ig:{group}\b",
                        f"{name} moves no pops of {group}, which the trigger lets in")

    def test_the_rally_reaches_each_group_only_where_it_exists(self):
        rally = _blocks(self.event, "option")[0]
        entered = re.findall(r"\big:(ig_\w+)\s*(\??=)\s*\{\s*add_modifier", rally)
        self.assertEqual(
            sorted(entered),
            [("ig_armed_forces", "?="), ("ig_devout", "?="), ("ig_landowners", "?=")])


if __name__ == "__main__":
    unittest.main()
