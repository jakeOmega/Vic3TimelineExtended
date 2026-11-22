"""The Human Augmentation Debate's pooled events against the laws that end it.

`augmentation_events.1` to `.5` fire only from `je_human_augmentation`'s monthly
pulse, and the entry ends as soon as a settling law is in force: it completes on
Regulated Augmentation Market, Unrestricted Augmentation or Mandatory
Augmentation and fails on Human Purity. So an option that asks for one of those
laws can never be shown. `augmentation_events.3.c` ("Mandate augmentation for
competitive industries") asked for Unrestricted or Mandatory Augmentation and
was dead from the day it was written (#1616).

Run: python3 test_augmentation_debate_events.py
"""
import os
import re
import unittest

from je_test_helpers import _direct_blocks, entry_text, outcome_part

REPO = os.path.dirname(os.path.abspath(__file__))
JE = os.path.join(REPO, "common", "journal_entries", "je_human_augmentation.txt")
EVENTS = os.path.join(REPO, "events", "augmentation_events.txt")
LAW = re.compile(r"has_law\s*=\s*law_type:(\w+)")


def _read(path):
    with open(path, encoding="utf-8-sig") as f:
        return f.read()


class PooledOptionsAreReachableTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.je = entry_text(_read(JE), "je_human_augmentation")
        cls.events = _read(EVENTS)
        pulse = _direct_blocks(cls.je, "on_monthly_pulse")[0]
        cls.pooled = re.findall(r"=\s*(augmentation_events\.\d+)", pulse)
        cls.ending = (set(LAW.findall(outcome_part(cls.je, "complete", "trigger")))
                      | set(LAW.findall(outcome_part(cls.je, "fail", "trigger"))))

    def test_the_fixture_is_not_empty(self):
        self.assertEqual(len(self.pooled), 5)
        self.assertEqual(self.ending, {
            "law_regulated_augmentation_market", "law_unrestricted_augmentation",
            "law_mandatory_augmentation", "law_human_purity"})

    def test_the_pool_is_the_only_way_in(self):
        # If anything else fires a pooled event, an option gated on a settling
        # law is no longer dead, and this file's premise needs another look.
        for root in ("common", "events"):
            for folder, _, names in os.walk(os.path.join(REPO, root)):
                for name in names:
                    path = os.path.join(folder, name)
                    if not name.endswith(".txt") or path == JE:
                        continue
                    text = "\n".join(line.split("#", 1)[0] for line in _read(path).splitlines())
                    for event in self.pooled:
                        with self.subTest(file=os.path.relpath(path, REPO), event=event):
                            self.assertNotRegex(text, r"id\s*=\s*" + re.escape(event) + r"\b")

    def test_no_option_needs_a_law_that_ends_the_debate(self):
        for event in self.pooled:
            body = entry_text(self.events, event)
            for option in _direct_blocks(body, "option"):
                name = re.search(r"\bname\s*=\s*(\S+)", option).group(1)
                for trigger in _direct_blocks(option, "trigger"):
                    # A NOT / NOR over such a law is merely always true; only a
                    # positive test makes the option unreachable.
                    positive = trigger
                    for negation in ("NOT", "NOR"):
                        for block in _direct_blocks(trigger, negation):
                            positive = positive.replace(block, "")
                    with self.subTest(option=name):
                        self.assertEqual(set(LAW.findall(positive)) & self.ending, set())


if __name__ == "__main__":
    unittest.main()
