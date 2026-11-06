# -*- coding: utf-8 -*-
"""The banking cycle survives a revolution (#465; civil-war audit F6, F7).

`je_banking_cycle` is `can_revolution_inherit`, and the copy a revolution's
winner inherits re-runs `immediate` after the loser's variables have been
merged in, with an empty modifier list. Two things follow, and the engine says
nothing when either breaks:

- an unguarded `set_variable` in `immediate` throws the inherited cycle away
  (a panic at 6.6 became a stable 50 the day the rebels won);
- a stored "which band is applied" tracker inherited without its modifier
  claimed a band that was not there, so the swap never ran and the band stayed
  off (F7). Until 1.15 `immediate` reset the tracker to 0; since then
  (#1404) the entry declares the five bands from te_mon_stance_band itself
  (scaling_modifiers_while_active), so there is no tracker to go stale.
"""

import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
JE = os.path.join(REPO, "common", "journal_entries", "je_banking.txt")
EFFECTS = os.path.join(REPO, "common", "scripted_effects", "banking_cycle_effects.txt")

CYCLE_VARS = ("finance_cycle_value", "finance_cycle_momentum", "bubble_pressure")
BANDS = tuple(f"banking_stance_band_{i}" for i in range(1, 6))


def _read(path):
    with open(path, encoding="utf-8-sig") as f:
        return re.sub(r"#[^\n]*", "", f.read())


def _body_after(text, start):
    """The body of the brace block whose opening brace ends at ``start``."""
    depth = 1
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start:i]
    raise AssertionError("unclosed block")


def _block(text, pattern):
    """The body of the first ``<pattern> = { ... }`` block."""
    m = re.search(pattern + r"\s*=\s*\{", text, re.M)
    if m is None:
        raise AssertionError(f"{pattern} not found")
    return _body_after(text, m.end())


def _immediate():
    je = _block(_read(JE), r"^je_banking_cycle")
    return je, _block(je, r"^\timmediate")


class ImmediateTests(unittest.TestCase):
    def test_entry_is_inherited(self):
        # The premise of the tests below. If this changes, re-read the
        # "What a Civil War's Winner Inherits" section before relaxing them.
        je, _ = _immediate()
        self.assertRegex(je, r"can_revolution_inherit\s*=\s*yes")

    def test_cycle_sets_are_has_variable_guarded(self):
        # Since the banking always-on spec (2026-10-17) the seeds live in
        # banking_cycle_start, which immediate calls only for a country with no
        # cycle that meets the start test; the monthly pulse calls it too.
        _, immediate = _immediate()
        self.assertRegex(
            immediate,
            r"if\s*=\s*\{\s*limit\s*=\s*\{\s*NOT\s*=\s*\{\s*has_variable\s*=\s*finance_cycle_value\s*\}"
            r"\s*te_banking_cycle_unlocked\s*=\s*yes\s*\}\s*banking_cycle_start\s*=\s*yes\s*\}")
        for name in CYCLE_VARS:
            with self.subTest(variable=name, block="immediate"):
                self.assertNotRegex(immediate, r"(set|change)_variable\s*=\s*\{\s*name\s*=\s*%s\b" % name)
        body = _block(_read(EFFECTS), r"^banking_cycle_start")
        for name in CYCLE_VARS:
            with self.subTest(variable=name):
                sets = re.findall(
                    r"set_variable\s*=\s*\{\s*name\s*=\s*%s\b" % name, body)
                guarded = re.findall(
                    r"if\s*=\s*\{\s*limit\s*=\s*\{\s*NOT\s*=\s*\{\s*has_variable\s*=\s*%s\s*\}\s*\}"
                    r"\s*set_variable\s*=\s*\{\s*name\s*=\s*%s\b" % (name, name),
                    body)
                self.assertEqual(len(sets), 1, f"{name} should be seeded once")
                self.assertEqual(len(guarded), len(sets),
                                 f"{name} is set without its own has_variable guard")
                self.assertNotRegex(
                    body, r"change_variable\s*=\s*\{\s*name\s*=\s*%s\b" % name)

    def test_immediate_keeps_no_stance_band_tracker(self):
        _, body = _immediate()
        self.assertNotIn("te_mon_stance_band_applied", body)
        self.assertNotIn("banking_stance_band", body)

    def test_bars_are_drawn_from_the_variables(self):
        _, body = _immediate()
        self.assertIn("banking_cycle_update_progress_bars = yes", body)
        # No bar set to a literal: an inherited cycle would be shown as 50/0/0.
        self.assertNotIn("set_bar_progress", body)


class StanceBandDeclarationTests(unittest.TestCase):
    """The inherited copy re-declares the band from the inherited variable; nothing tracks which band is on."""

    def test_each_band_is_declared_from_the_displayed_band(self):
        je, _ = _immediate()
        for n, band in enumerate(BANDS, 1):
            with self.subTest(band=band):
                m = re.search(r"scaling_modifiers_while_active\s*=\s*\{\s*modifier\s*=\s*%s\s" % band, je)
                self.assertIsNotNone(m, f"{band} is not declared")
                body = _body_after(je, m.end())  # the rest of the declaration
                self.assertRegex(body, r"has_variable\s*=\s*te_mon_stance_band\s+var:te_mon_stance_band\s*=\s*%d\s" % n)

    def test_no_tracker_or_swap_is_left(self):
        for path in (JE, EFFECTS):
            with self.subTest(path=os.path.basename(path)):
                text = _read(path)
                self.assertNotIn("te_mon_stance_band_applied", text)
                self.assertNotIn("banking_cycle_apply_stance_band", text)
                self.assertNotIn("banking_stance_band_healed", text)


if __name__ == "__main__":
    unittest.main()
