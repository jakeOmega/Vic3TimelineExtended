"""UN Delivery rewards halved (owner ruling 2026-10-06).

With #772's cap alone the 1983 observer save still read 9.6 to 10: at the
four-year half-life about 0.14 points a month holds the ledger at the cap, and
single entries of 1 to 2 refilled it every few months. The owner chose to keep
the memory long and halve every reward ("you need more successes to keep the
pillar strong"). Each figure was halved where it is booked, and so was the loc
that states it.

- Every delivery booking in the mod is pinned at its halved figure. A new one
  belongs in BOOKINGS, at the halved scale.
- Every tooltip that states a delivery figure states the figure of the
  booking it describes.
"""

import re
import unittest
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOC = ROOT / "localization/english"

# (file, POINTS as written, REASON): every delivery booking, halved.
BOOKINGS = Counter([
    ("common/scripted_effects/un_economy_effects.txt", "un_fr_delivery_points_value", "34"),
    ("common/scripted_effects/un_mandate_effects.txt", "1", "5"),
    ("common/scripted_effects/un_mission_effects.txt", "un_mission_success_delivery_value", None),
    ("common/scripted_effects/un_mission_effects.txt", "0.5", "1"),
    ("common/scripted_effects/un_order_effects.txt", "un_cf_delivery_credit", "31"),
    ("events/un_events.txt", "0.75", "1041"),
    ("events/un_events.txt", "0.75", "1044"),
    ("events/un_events.txt", "0.25", "1042"),
    ("events/un_events.txt", "0.75", "1071"),
    ("events/un_events.txt", "0.75", "1075"),
    ("events/un_events.txt", "0.25", "1072"),
    ("events/un_events.txt", "0.5", "18"),
    ("events/un_referendum_events.txt", "un_ref_delivery_credit", "33"),
    ("events/un_vote_events.txt", "0.5", "1"),
    ("events/un_vote_events.txt", "0.25", "2"),
    ("events/un_vote_events.txt", "0.25", "1"),
    ("events/un_vote_events.txt", "0.5", "1"),
])

# Script values the bookings name, at their halved figures.
VALUES = {
    "un_fr_delivery_points": 0.5,  # a full World Food Reserve draw
    "un_mission_success_delivery": 1,
    "un_mission_electoral_success_delivery": 0.5,
    "un_cf_delivery_credit": 0.75,
    "un_ref_delivery_credit": 0.5,
}

# Loc key -> (the figure it states, the booking or value it describes).
STATED = {
    "un_mandate.1.d_complied": (1, "un_mandate_effects.txt reason 5"),
    "je_un_auth_tbl_delivery_tt": (1, "un_mission_success_delivery"),
    "UN_PROPOSE_OBSERVER_REQUEST_DESC": (0.5, "un_mission_effects.txt reason 1"),
    "un_vote_observer_request_passed_tt": (0.5, "un_mission_effects.txt reason 1"),
    "un_ceasefire_kept_tt": (0.75, "un_cf_delivery_credit"),
    "un_order_ledger_tt_referendum_held": (0.5, "un_ref_delivery_credit"),
    "un_ledger_tt_delivery_institutional_0_5": (0.5, "un_events.txt reason 18"),
    "un_ledger_tt_delivery_up_0_75": (0.75, "un_events.txt reasons 1041 1044 1071 1075"),
    "un_ledger_tt_delivery_up_0_25": (0.25, "un_events.txt reasons 1042 1072"),
    "un_vote_peacekeeping_request_passed_tt": (0.5, "un_vote_events.txt reason 1"),
    "un_vote_aid_request_passed_tt": (0.5, "un_vote_events.txt reason 1"),
    "un_vote_peacekeeping_request_passed_vetoed_tt": (0.25, "un_vote_events.txt reason 2"),
    "un_vote_peacekeeping_request_passed_weak_tt": (0.25, "un_vote_events.txt reason 1"),
}

BOOKING_RE = re.compile(r"PILLAR = delivery POINTS = (\S+)(?: REASON = (\d+))?")


def strip_comments(text):
    return "\n".join(line.split("#", 1)[0] for line in text.splitlines())


def loc_values():
    values = {}
    for path in LOC.glob("*_l_english.yml"):
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            m = re.match(r'\s*([^\s:#]+):\d* "(.*)"\s*$', line)
            if m:
                values[m.group(1)] = m.group(2)
    return values


class TestDeliveryRewardsHalved(unittest.TestCase):
    def test_every_delivery_booking_is_at_its_halved_figure(self):
        found = Counter()
        for folder in ("common", "events"):
            for path in sorted((ROOT / folder).rglob("*.txt")):
                text = strip_comments(path.read_text(encoding="utf-8-sig"))
                for points, reason in BOOKING_RE.findall(text):
                    found[(path.relative_to(ROOT).as_posix(), points, reason or None)] += 1
        self.assertEqual(found, BOOKINGS)

    def test_the_named_values_are_halved(self):
        text = "".join(strip_comments(p.read_text(encoding="utf-8-sig"))
                       for p in (ROOT / "common/script_values").glob("*.txt"))
        for name, figure in VALUES.items():
            m = re.search(r"(?m)^" + name + r" = \{ value = ([\d.]+) \}", text)
            self.assertIsNotNone(m, name)
            self.assertEqual(float(m.group(1)), figure, name)

    def test_each_tooltip_states_its_bookings_figure(self):
        values = loc_values()
        for key, (figure, source) in STATED.items():
            self.assertIn(key, values, key)
            stated = re.findall(r"(?:delivery|accomplished#! \() ?\+([\d.]+)", values[key])
            self.assertEqual([float(s) for s in stated], [figure], f"{key} ({source})")

    def test_no_loc_still_states_a_pre_halving_figure(self):
        # The keys named after their points were renamed with them.
        values = loc_values()
        for old in ("un_ledger_tt_delivery_up_1_5", "un_ledger_tt_delivery_up_0_5",
                    "un_ledger_tt_delivery_institutional_1"):
            self.assertNotIn(old, values, old)
        stating = {k for k, v in values.items() if re.search(r"UN delivery \+\d", v)}
        self.assertLessEqual(stating, set(STATED), "a key states a delivery figure the test doesn't check")


if __name__ == "__main__":
    unittest.main()
