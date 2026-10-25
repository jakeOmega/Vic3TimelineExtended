"""Every space race event moves progress by whole months of the pace (2026-10-25).

Setbacks used to keep x0.75 (Ambitious) or x0.85 (Safe, Standard) of a
milestone's progress, most options took a flat 3 to 10 points on top, and the
in-progress events gave a flat 2 to 30. The share cost more the longer a
milestone took (the risk is a monthly roll, so a long milestone sees more
setbacks, each taking a share of a larger progress), so a slow programme on
the Mars Landing settled below its goal and never finished; the flat amounts
meant nothing past the first milestones. Now each option moves progress by a
number of months of sr_progress, recorded when the event fires, and its
tooltip says how many. A minor setback costs 1 to 4 months, an Ambitious
failure 4 to 6.
"""
import glob
import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
EVENTS = os.path.join(REPO, "events", "space_race_events.txt")
EFFECTS = os.path.join(REPO, "common", "scripted_effects", "space_race_effects.txt")
VALUES = os.path.join(REPO, "common", "script_values", "space_race_values.txt")
LOC_DIR = os.path.join(REPO, "localization", "english")

MILESTONES = ("suborbital", "orbital", "moon_landing", "probe", "moon_base", "mars_landing",
              "interstellar_probe", "solar_colonization")
HELPERS = r"sr_setback_lose_months|sr_gain_progress_months|sr_lose_progress_months|sr_boost_active_milestones"
# Which tooltip each helper is announced by.
KIND = {"sr_setback_lose_months": "SETBACK_LOSE", "sr_gain_progress_months": "PROGRESS_ADD",
        "sr_boost_active_milestones": "PROGRESS_ADD", "sr_lose_progress_months": "PROGRESS_LOSE"}


def _read(path, comments=False):
    with open(path, encoding="utf-8-sig") as f:
        text = f.read()
    return text if comments else re.sub(r"#[^\n]*", "", text)


def _close(text, open_idx):
    depth = 0
    for i in range(open_idx, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return i + 1
    raise AssertionError("unclosed block")


def _block(text, name):
    m = re.search(rf"(?m)^{re.escape(name)}\s*=\s*\{{", text)
    assert m, f"{name} not found"
    return text[m.end():_close(text, m.end() - 1) - 1]


def _events():
    text = _read(EVENTS)
    out = {}
    for m in re.finditer(r"(?m)^space_race_events\.(\d+) = \{", text):
        out[int(m.group(1))] = text[m.end():_close(text, m.end() - 1) - 1]
    return out


def _options(event):
    out = {}
    for m in re.finditer(r"\n\toption = \{", event):
        body = event[m.end():_close(event, m.end() - 1) - 1]
        name = re.search(r"name = space_race_events\.(\d+\.\w+)", body)
        if name:
            out[name.group(1)] = body
    return out


def _loc(key):
    for path in glob.glob(os.path.join(LOC_DIR, "*.yml")):
        m = re.search(rf'^ {re.escape(key)}:\d* "(.*)"\s*$', _read(path, comments=True), re.M)
        if m:
            return m.group(1)
    raise AssertionError(f"no loc {key}")


def _pool(dispatcher):
    body = _block(_read(EFFECTS), dispatcher)
    return {int(n) for n in re.findall(r"trigger_event = \{ id = space_race_events\.(\d+) \}", body)}


class ProgressMonthsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.events = _events()

    def test_no_event_moves_progress_by_points(self):
        text = _read(EVENTS)
        self.assertNotRegex(text, r"name = sr_progress_\w+\s+(add|subtract|multiply) =")
        self.assertNotIn("sr_progress_boost", text)
        for retired in ("sr_apply_ambitious_failure_progress_loss", "sr_apply_safe_setback_progress_loss",
                        "sr_boost_setback_milestone", "SR_PROGRESS_LOSE_25_PERCENT_TT", "SR_PROGRESS_SUBTRACT_"):
            self.assertNotIn(retired, text)

    def test_every_amount_has_a_tooltip_with_the_same_months(self):
        checked = 0
        for ev, event in self.events.items():
            for name, body in _options(event).items():
                for call in re.finditer(rf"({HELPERS}) = \{{[^}}]*MONTHS = (\d+)", body):
                    helper, months = call.group(1), call.group(2)
                    tips = re.findall(r"custom_tooltip = SR_(SETBACK_LOSE|PROGRESS_ADD|PROGRESS_LOSE)_(\d)_MONTHS_TT",
                                      body[:call.start()])
                    with self.subTest(option=name, helper=helper):
                        self.assertTrue(tips, "no months tooltip before the change")
                        self.assertEqual(tips[-1], (KIND[helper], months))
                    checked += 1
        self.assertGreater(checked, 150)

    def test_events_that_move_progress_record_the_pace(self):
        for ev, event in self.events.items():
            if not re.search(rf"({HELPERS}) = \{{", event):
                continue
            with self.subTest(event=ev):
                immediate = re.search(r"\n\timmediate = \{", event)
                self.assertIsNotNone(immediate)
                body = event[immediate.end():_close(event, immediate.end() - 1)]
                self.assertIn("sr_record_event_pace = yes", body)

    def test_setback_sizes(self):
        ambitious, safe = _pool("sr_fire_ambitious_failure_event"), _pool("sr_fire_safe_setback_event")
        self.assertTrue(ambitious and safe and not ambitious & safe)
        for ev in ambitious | safe:
            for name, body in _options(self.events[ev]).items():
                months = [int(n) for n in re.findall(r"sr_setback_lose_months = \{ MONTHS = (\d+) \}", body)]
                with self.subTest(option=name):
                    if ev == 74:      # An Unexpected Breakthrough: no loss
                        self.assertEqual(months, [])
                    elif ev in ambitious:
                        self.assertEqual(len(months), 1)
                        self.assertTrue(4 <= months[0] <= 6, months)
                        if "sr_mission_failure_effect = yes" in body and "random_list" not in body:
                            self.assertEqual(months[0], 4, "the review comes with 4 months")
                    else:
                        self.assertTrue(months)
                        self.assertTrue(all(1 <= m <= 4 for m in months), months)

    def test_tooltips_quote_their_months(self):
        values = _read(VALUES)
        used = set(re.findall(r"SR_(?:SETBACK_LOSE|PROGRESS_ADD|PROGRESS_LOSE)_\d_MONTHS_TT", _read(EVENTS)))
        self.assertTrue(used)
        for key in used:
            n = int(re.search(r"_(\d)_MONTHS", key).group(1))
            text = _loc(key)
            with self.subTest(key=key):
                self.assertIn("1 month#!" if n == 1 else f"{n} months#!", text)
                self.assertIn(f"ScriptValue('sr_event_months_{n}')", text)
                body = _block(values, f"sr_event_months_{n}")
                self.assertIn("value = sr_event_pace_value", body)
                if n > 1:
                    self.assertIn(f"multiply = {n}", body)

    def test_the_pace_is_recorded_and_read_back(self):
        effects, values = _read(EFFECTS), _read(VALUES)
        self.assertIn("set_variable = { name = sr_event_pace value = sr_progress }",
                      _block(effects, "sr_record_event_pace"))
        pace = _block(values, "sr_event_pace_value")
        self.assertIn("value = var:sr_event_pace", pace)
        self.assertIn("value = sr_progress", pace)
        for helper in ("sr_gain_progress_months", "sr_lose_progress_months"):
            self.assertIn("value = sr_event_pace_value", _block(effects, helper))

    def test_helpers_walk_every_milestone(self):
        effects = _read(EFFECTS)
        for helper, base in (("sr_setback_lose_months", "sr_setback_lose_months_base"),
                             ("sr_boost_active_milestones", "sr_boost_active_milestone_base")):
            body = _block(effects, helper)
            walked = re.findall(rf"{base} = \{{ MILESTONE = (\w+)\s+MONTHS = \$MONTHS\$ \}}", body)
            self.assertEqual(sorted(walked), sorted(MILESTONES), helper)
        goal_values = _read(VALUES)
        for m in MILESTONES:
            self.assertRegex(goal_values, rf"(?m)^sr_{m}_goal = \{{")


if __name__ == "__main__":
    unittest.main()
