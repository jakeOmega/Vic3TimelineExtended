# -*- coding: utf-8 -*-
"""Every reason code the UN ledger books has a line in the journal entry's log.

The UN's "Recent entries" log (``un_authority_log_block`` in
``common/scripted_effects/un_authority_display_effects.txt``) turns the number
each ledger entry was booked with — ``un_ledger_actor_entry = { ... REASON =
1041 }`` — back into words through a hand-kept list of cases. A code booked
somewhere with no case there is engine-silent: the entry prints its headline
and nothing under it. The table at the top of ``un_authority_effects.txt``
asks for the call sites, the cases and the keys to be kept in step; this test
is what keeps them.

It also guards the one way a case can print the WRONG thing. A line that
names the entry's subject reads it from ``scope:un_led_subject_disp``, a
temporary scope that the previous entry may have left set. The log saves it
only for an entry that has a subject and prints it only from
``un_authority_log_reason_on``, which checks for one first — so a subject key
must never be printed by the plain ``un_authority_log_reason_case``, and a
plain key must never name the subject.
"""

import glob
import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
DISPLAY = os.path.join(REPO, "common", "scripted_effects", "un_authority_display_effects.txt")
CHAMBER = os.path.join(REPO, "common", "scripted_effects", "un_chamber_display_effects.txt")

# The booking wrappers of un_authority_effects.txt. Their own bodies pass
# $REASON$ through and are skipped by the \d+ below.
_BOOK = re.compile(
    r"\b(un_ledger_actor_entry(?:_unweighted)?(?:_on)?|un_ledger_entry(?:_on)?"
    r"|un_authority_actor_shock(?:_weighted|_on)?)\s*=\s*\{([^{}]*)\}"
)
_REASON = re.compile(r"\bREASON\s*=\s*(\d+)\b")
_SUBJECT = re.compile(r"\bSUBJECT\s*=")
# un_mission_ledger_outcome (un_mission_effects.txt) books one code per kind of
# mission, always with the mission's state as the subject.
_MISSION = re.compile(r"\bun_mission_ledger_outcome\s*=\s*\{([^{}]*)\}")
_MISSION_CODE = re.compile(r"\b(?:PEACEKEEPING|AID|STABILISATION)\s*=\s*(\d+)\b")

_CASE = re.compile(
    r"\bun_authority_log_reason_(case|on)\s*=\s*\{\s*CODE\s*=\s*(\d+)\s+KEY\s*=\s*(\S+)"
    r"(?:\s+FALLBACK\s*=\s*(\S+))?\s*\}"
)
_TOPIC_CASE = re.compile(r"\bun_authority_log_topic_case\s*=\s*\{\s*TOPIC\s*=\s*(\w+)\s+KEY\s*=\s*(\S+)\s*\}")
_LOC_LINE = re.compile(r'\s*([A-Za-z0-9_.\-]+):\d*\s+"(.*)"\s*$')
_SPLICE = re.compile(r"\$([A-Za-z0-9_.\-]+)\$")

# Booked while scope:un_resolution is set; un_ledger_log_add notes the
# resolution, and the log prints them through un_authority_log_resolution_lines.
RESOLUTION_CODES = {1, 2, 3, 4, 12, 13, 14}


def _read(path):
    with open(path, encoding="utf-8-sig") as f:
        return f.read()


def _strip_comments(text):
    return "\n".join(line.split("#", 1)[0] for line in text.splitlines())


def _block(text, name):
    """The body of the top-level `name = { ... }` definition."""
    m = re.search(r"^" + re.escape(name) + r"\s*=\s*\{", text, re.M)
    if not m:
        raise AssertionError(f"{name} not found")
    depth, i = 0, m.end() - 1
    for j in range(i, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return text[m.end():j]
    raise AssertionError(f"{name} is not closed")


def _booked():
    """{code: set of 'subject'/'plain'} over every booking in common/ and events/."""
    codes = {}
    files = glob.glob(os.path.join(REPO, "common", "**", "*.txt"), recursive=True)
    files += glob.glob(os.path.join(REPO, "events", "**", "*.txt"), recursive=True)
    for path in files:
        text = _strip_comments(_read(path))
        for m in _BOOK.finditer(text):
            reason = _REASON.search(m.group(2))
            if not reason:
                continue
            kind = "subject" if _SUBJECT.search(m.group(2)) else "plain"
            codes.setdefault(int(reason.group(1)), set()).add(kind)
        for m in _MISSION.finditer(text):
            for code in _MISSION_CODE.findall(m.group(1)):
                codes.setdefault(int(code), set()).add("subject")
    return codes


def _loc():
    keys = {}
    for path in glob.glob(os.path.join(REPO, "localization", "english", "*.yml")):
        for line in _read(path).splitlines():
            m = _LOC_LINE.match(line)
            if m:
                keys[m.group(1)] = m.group(2)
    return keys


def _expanded(key, loc, seen=None):
    """A loc value with its $splices$ followed, transitively."""
    seen = seen or set()
    if key in seen or key not in loc:
        return ""
    seen.add(key)
    value = loc[key]
    return value + "".join(_expanded(ref, loc, seen) for ref in _SPLICE.findall(value))


class UnLedgerReasonCodes(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        display = _strip_comments(_read(DISPLAY))
        cls.reason_line = _block(display, "un_authority_log_reason_line")
        cls.resolution_lines = _block(display, "un_authority_log_resolution_lines")
        cls.cases = {}
        for m in _CASE.finditer(cls.reason_line):
            cls.cases[int(m.group(2))] = (m.group(1), m.group(3), m.group(4), m.start())
        cls.resolution_cases = [
            (m.group(1), int(m.group(2)), m.group(3)) for m in _CASE.finditer(cls.resolution_lines)
        ]
        cls.booked = _booked()
        cls.loc = _loc()

    def test_bookings_were_found(self):
        # A regex that silently stops matching would pass every test below.
        self.assertGreater(len(self.booked), 40)
        self.assertIn(1041, self.booked)
        self.assertIn(21, self.booked)

    def test_every_booked_code_has_a_line(self):
        missing = sorted(set(self.booked) - set(self.cases))
        self.assertEqual(missing, [], "reason codes booked with no case in un_authority_log_reason_line")

    def test_resolution_codes_have_resolution_lines(self):
        covered = {code for _, code, _ in self.resolution_cases}
        missing = sorted((set(self.booked) & RESOLUTION_CODES) - covered)
        self.assertEqual(missing, [], "resolution codes with no case in un_authority_log_resolution_lines")

    def test_each_case_sits_in_its_band(self):
        # The chain checks >= 1000, then >= 100, then the rest; a case in the
        # wrong band is never reached.
        mid = self.reason_line.index("var:un_led_reason >= 100 ")
        low = self.reason_line.index("else = {", mid)
        wrong = []
        for code, (_, _, _, pos) in self.cases.items():
            if pos < mid:
                in_band = code >= 1000
            elif pos < low:
                in_band = 100 <= code < 1000
            else:
                in_band = code < 100
            if not in_band:
                wrong.append(code)
        self.assertEqual(sorted(wrong), [])

    def test_subject_codes_print_the_subject_and_plain_codes_do_not(self):
        problems = []
        for code, kinds in self.booked.items():
            if code in RESOLUTION_CODES or code not in self.cases:
                continue
            form, key, fallback, _ = self.cases[code]
            names_subject = "un_led_subject_disp" in _expanded(key, self.loc)
            if "subject" in kinds and form != "on":
                problems.append(f"{code}: booked with a SUBJECT but printed by un_authority_log_reason_case")
            if form == "on" and not names_subject:
                problems.append(f"{code}: {key} is printed only with a subject but does not name it")
            if form == "case" and names_subject:
                problems.append(f"{code}: {key} names the subject but is printed without checking for one")
            if fallback and "un_led_subject_disp" in _expanded(fallback, self.loc):
                problems.append(f"{code}: fallback {fallback} names the subject it is the fallback for")
        self.assertEqual(problems, [])

    def test_resolution_lines_name_the_target_only_when_checked(self):
        at_block = self.resolution_lines.index("exists = var:un_led_subject")
        plain_block = self.resolution_lines.index("else = {", at_block)
        problems = []
        for m in _CASE.finditer(self.resolution_lines):
            key = m.group(3)
            names_subject = "un_led_subject_disp" in _expanded(key, self.loc)
            checked = at_block < m.start() < plain_block
            if names_subject and not checked:
                problems.append(key)
        self.assertEqual(problems, [])

    def test_every_key_exists(self):
        keys = set()
        for form, key, fallback, _ in self.cases.values():
            keys.add(key)
            if fallback:
                keys.add(fallback)
        keys.update(key for _, _, key in self.resolution_cases)
        keys.update(m.group(2) for m in _TOPIC_CASE.finditer(self.resolution_lines))
        keys.update(re.findall(r"custom_tooltip_no_bullet\s*=\s*(\S+)", self.resolution_lines))
        missing = sorted(k for k in keys if k not in self.loc and not k.startswith("$"))
        self.assertEqual(missing, [])

    def test_every_resolution_topic_is_named_in_the_log(self):
        chamber = _strip_comments(_read(CHAMBER))
        topics = set(re.findall(r"has_tag\s*=\s*un_topic_(\w+)", _block(chamber, "un_chamber_topic_line")))
        self.assertGreater(len(topics), 10)
        logged = {m.group(1) for m in _TOPIC_CASE.finditer(self.resolution_lines)}
        logged.update(re.findall(r"has_tag\s*=\s*un_topic_(\w+)", self.resolution_lines))
        self.assertEqual(sorted(topics - logged), [])


if __name__ == "__main__":
    unittest.main()
