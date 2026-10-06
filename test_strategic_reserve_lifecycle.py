# -*- coding: utf-8 -*-
"""Strategic Reserve: the journal entry outlives its hub (#PRNUM).

A journal entry that goes `invalid` is never activated again, even when its
`possible` holds once more. je_strategic_reserve used to end when its hub was
lost, so a country whose hub state fell to the rebels of a civil war kept a
dead entry, and the hub it got back ran with no weekly pulse (13 of 53 hub
holders in the 2026-10-05 observer run). The entry now waits without a hub.
Nothing in the engine checks any of this; these tests pin the pieces.
"""

import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))

HUB = r"any_scope_building\s*=\s*\{\s*is_building_type\s*=\s*building_strategic_reserve_hub\s*\}"


def _read(*parts):
    with open(os.path.join(REPO, *parts), encoding="utf-8-sig") as f:
        return re.sub(r"#[^\n]*", "", f.read())


def _close(text, open_brace):
    depth = 0
    for i in range(open_brace, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return i
    raise AssertionError("unbalanced braces")


def _block(text, name, top_level=True):
    """The body of the first ``name = { ... }`` block (top-level by default)."""
    anchor = r"^" if top_level else r"(?<![\w.:])"
    m = re.search(anchor + re.escape(name) + r"\s*=\s*\{", text, re.M)
    if m is None:
        raise AssertionError(f"{name} not found")
    return text[m.end():_close(text, m.end() - 1)]


def _has_block(text, name):
    return re.search(r"(?<![\w.:])" + re.escape(name) + r"\s*=\s*\{", text) is not None


JE = _block(_read("common", "journal_entries", "je_strategic_reserve.txt"), "je_strategic_reserve")
EFFECTS = _read("common", "scripted_effects", "st_res_effects.txt")
ON_ACTIONS = _read("common", "on_actions", "st_res_on_actions.txt")


class EntryLifecycleTests(unittest.TestCase):
    def test_entry_has_no_invalid(self):
        self.assertFalse(_has_block(JE, "invalid"))
        self.assertFalse(_has_block(JE, "on_invalid"))

    def test_rebels_of_a_revolution_start_no_entry(self):
        self.assertRegex(_block(JE, "is_shown_when_inactive", top_level=False), r"is_revolutionary\s*=\s*no")

    def test_activation_still_needs_a_hub(self):
        self.assertRegex(_block(JE, "possible", top_level=False), HUB)


class StockKeptWithoutHubTests(unittest.TestCase):
    def test_clamp_runs_only_with_a_hub(self):
        clamp = _block(EFFECTS, "st_res_clamp_stockpiles_effect")
        self.assertNotIn("clamp_variable", clamp)
        guard = _block(clamp, "if", top_level=False)
        self.assertRegex(_block(guard, "limit", top_level=False), HUB)
        self.assertIn("st_res_clamp_stockpiles_with_hub_effect = yes", guard)

    def test_every_stock_clamp_sits_behind_the_guard(self):
        """A stored amount is clamped only in the guarded helper or the weekly tick's with-hub branch."""
        allowed = {"st_res_clamp_stockpiles_with_hub_effect", "st_res_apply_weekly_good_effect"}
        for m in re.finditer(r"^(\w+)\s*=\s*\{", EFFECTS, re.M):
            body = EFFECTS[m.end():_close(EFFECTS, m.end() - 1)]
            if re.search(r"clamp_variable\s*=\s*\{\s*name\s*=\s*st_res_\$?\w*stored", body):
                with self.subTest(effect=m.group(1)):
                    self.assertIn(m.group(1), allowed)

    def test_weekly_tick_applies_stock_only_with_a_hub(self):
        weekly = _block(EFFECTS, "st_res_weekly_update_effect")
        branch = _block(weekly, "if", top_level=False)
        self.assertRegex(_block(branch, "limit", top_level=False), HUB)
        self.assertIn("st_res_apply_weekly_good_effect", branch)
        self.assertNotIn("st_res_apply_weekly_good_effect", _block(weekly, "else", top_level=False))

    def test_invalid_effect_is_gone(self):
        self.assertNotIn("st_res_je_invalid_effect", EFFECTS)


class CaptureTests(unittest.TestCase):
    def test_capture_resets_the_holder_without_another_hub(self):
        effect = _block(_block(ON_ACTIONS, "st_res_on_state_owner_change"), "effect", top_level=False)
        capture = _block(effect, "if", top_level=False)
        self.assertIn("remove_building = building_strategic_reserve_hub", capture)
        m = re.search(r"scope:st_res_capture_holder\s*\?=\s*\{", capture)
        self.assertIsNotNone(m, "the capture branch must reach the hub's holder")
        holder = capture[m.end():_close(capture, m.end() - 1)]
        self.assertRegex(holder, r"NOT\s*=\s*\{\s*" + HUB)
        self.assertIn("st_res_reset_vars_effect = yes", holder)

    def test_hand_over_within_the_nation_keeps_the_stock(self):
        effect = _block(_block(ON_ACTIONS, "st_res_on_state_owner_change"), "effect", top_level=False)
        self.assertNotIn("st_res_reset_vars_effect", _block(effect, "else", top_level=False))


if __name__ == "__main__":
    unittest.main()
