"""Crisis trades (2026-10-28 rework spec §8.6, phase 4c).

Either side of a crisis over deployment, claims, covert operations or orbital
weapons (disputes 7–10) can offer the matching concession of its own: a base
for a base, a claim for a claim. An accepted trade runs the existing
concession for the target, swaps the parties' saved scopes, runs it again for
the issuer, swaps them back, and closes the crisis as outcome 11, "Trade".
"""

import re
import unittest
from pathlib import Path

from test_nuclear_deterrence import (
    CRISIS_EFFECTS,
    CUSTOM_LOC,
    block,
    loc_value,
    read,
    strip_comments,
)

ROOT = Path(__file__).resolve().parent
CRISIS_EVENTS = ROOT / "events/nuclear_crisis_events.txt"
OBSERVER_EFFECTS = ROOT / "common/scripted_effects/nuclear_observer_effects.txt"

# nd_crisis_close's outcome codes, as the crisis effects' header lists them.
OUTCOMES = {
    1: "the target yielded", 2: "the issuer backed down", 3: "reciprocal stand-down",
    4: "the target backed down natively", 5: "the issuer's side backed down", 6: "the war ended",
    7: "nuclear use", 8: "expired", 9: "invalid", 10: "the dispute ended, no clear winner",
    11: "a trade",
}
TRADE = 11


def first_valid_keys(body):
    """(trigger text, desc key) for each triggered_desc of a first_valid, in order."""
    out = []
    for m in re.finditer(r"triggered_desc = \{", body):
        td = block(body[m.start():], "triggered_desc")
        out.append((block(td, "trigger"), re.search(r"\bdesc = ([\w.]+)", td).group(1)))
    return out


def outcome_branch(body, code):
    """The if/else_if of nd_crisis_apply_outcome_side whose limit tests outcome `code` alone."""
    for m in re.finditer(r"(?:else_if|if) = \{", body):
        branch = block(body[m.start():], "else_if" if body[m.start()] == "e" else "if")
        limit = block(branch, "limit")
        if re.fullmatch(r"\s*var:nd_crisis_pending_outcome = " + str(code) + r"\s*", limit):
            return branch
    raise AssertionError(f"no outcome branch for {code}")


class TestOutcomeEleven(unittest.TestCase):
    def setUp(self):
        self.effects = strip_comments(read(CRISIS_EFFECTS))
        self.events = strip_comments(read(CRISIS_EVENTS))
        self.custom = strip_comments(read(CUSTOM_LOC))

    def test_header_lists_eleven(self):
        header = read(CRISIS_EFFECTS).split("# TOOLTIP PASSES", 1)[0]
        self.assertRegex(header, r"#.*\b11 a trade\b")

    def test_log_names_every_outcome(self):
        body = block(read(OBSERVER_EFFECTS), "nd_log_crisis_end")
        for n in OUTCOMES:
            self.assertIn(f"var:nd_crisis_outcome_now = {n} }} }} debug_log = \"TE_NUCLEAR: type=crisis_end; outcome={n};", body, n)

    def test_trade_pays_five_each(self):
        branch = outcome_branch(block(self.effects, "nd_crisis_apply_outcome_side"), TRADE)
        self.assertRegex(branch, r"text = nd_tt_credibility_up_5\s*nd_change_credibility = \{ AMOUNT = 5 \}")
        self.assertEqual(branch.count("nd_change_credibility"), 1)
        self.assertNotIn("nd_crisis_pending_role", branch)
        self.assertNotIn("nd_crisis_climbdown", branch)
        self.assertNotIn("nd_crisis_bluff_called", branch)

    def test_notice_titles_and_describes_a_trade(self):
        body = block(self.events, "nuclear_crisis.6")
        for part, key in (("title", "nuclear_crisis.6.t_trade"), ("desc", "nuclear_crisis.6.d_trade")):
            pairs = first_valid_keys(block(body, part))
            keys = [k for _, k in pairs]
            self.assertIn(key, keys, part)
            trig = pairs[keys.index(key)][0]
            self.assertIn(f"O = {TRADE}", trig)
            self.assertLess(keys.index(key), len(keys) - 1, f"{part}: the trade must come before the fallback")

    def test_last_word_names_a_trade(self):
        body = block(self.custom, "nd_crisis_last_outcome_word")
        texts = [block(body[m.start():], "text") for m in re.finditer(r"\btext = \{", body)]
        hits = [t for t in texts if f"var:nd_crisis_last_outcome = {TRADE}" in t]
        self.assertEqual(len(hits), 1)
        self.assertIn("localization_key = nd_last_outcome_trade", hits[0])
        self.assertIn("always = yes", texts[-1])

    def test_outcome_loc_exists(self):
        for key in ("nuclear_crisis.6.t_trade", "nuclear_crisis.6.d_trade", "nd_last_outcome_trade"):
            self.assertTrue(loc_value(key), key)


if __name__ == "__main__":
    unittest.main()
