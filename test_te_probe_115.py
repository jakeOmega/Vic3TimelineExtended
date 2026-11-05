"""The vanilla 1.15 engine probes (te_probe_115) parse, log only literal lines and are listed in their play-test doc.

The probes answer the open engine questions of docs/audits/vanilla_1_15_prep.md § 2 through which
`TE_PROBE_115 <name> ...` line fires in debug.log. A figure printed through a loc accessor can't be trusted there
(docs/guides/scripting_best_practices.md, "Conditional `debug_log` for Trustworthy Scope Diagnostics"), so every line is
literal: no accessor and no `$ARG$`, except C19's two quoted-argument lines, which are the question. The C7 thresholds
assume the figures of two display-only nuclear modifiers, pinned here.

Delete with the probes once answered (docs/testing/vanilla-1-15-playtest.md).
"""
import os
import re
import unittest

from paradox_file_parser import ParadoxFileParser

REPO = os.path.dirname(os.path.abspath(__file__))
ENTRY = "common/journal_entries/te_probe_115_probes.txt"
EFFECTS = "common/scripted_effects/te_probe_115_effects.txt"
EVENTS = "events/te_probe_115_events.txt"
C5_EFFECTS = "common/scripted_effects/te_probe_115_c5_effects.txt"
C5_BARS = "common/scripted_progress_bars/te_probe_115_bars.txt"
FILES = (ENTRY, EFFECTS, EVENTS, C5_EFFECTS, C5_BARS)
DOC = "docs/testing/vanilla-1-15-playtest.md"
DELETE_LINE = "Delete once answered (see docs/testing/vanilla-1-15-playtest.md)."
BOM = b"\xef\xbb\xbf"

DEBUG_LOG_RE = re.compile(r'\bdebug_log\s*=\s*"([^"]*)"')
C19_LINES = {
    "TE_PROBE_115 c19_quoted_arg_a number=$N$ word=$WORD$ end",
    "TE_PROBE_115 c19_quoted_arg_b (kind $WORD$)",
}


def read(rel):
    with open(os.path.join(REPO, rel), encoding="utf-8-sig") as f:
        return f.read()


def code(rel):
    """The file with its comments removed (a `#` inside a quoted string is kept)."""
    out = []
    for line in read(rel).splitlines():
        kept, quoted = [], False
        for ch in line:
            if ch == '"':
                quoted = not quoted
            if ch == "#" and not quoted:
                break
            kept.append(ch)
        out.append("".join(kept))
    return "\n".join(out)


def parse(rel):
    parser = ParadoxFileParser()
    parser.parse_file(os.path.join(REPO, rel), apply_directives=False)
    return parser.data


def body(value):
    return value[1] if isinstance(value, (tuple, list)) and len(value) == 2 and value[0] in ("=", "?=") else value


def log_lines():
    return [(rel, text) for rel in FILES for text in DEBUG_LOG_RE.findall(code(rel))]


def block(text, name):
    """The top-level `name = { ... }` block of `text` (its definition, not a call), braces balanced."""
    m = re.search(rf"^{re.escape(name)}\s*=\s*\{{", text, re.M)
    if not m:
        return ""
    depth, i = 0, m.end() - 1
    for j in range(i, len(text)):
        depth += {"{": 1, "}": -1}.get(text[j], 0)
        if depth == 0:
            return text[i:j + 1]
    return text[i:]


class TestProbeFiles(unittest.TestCase):
    def test_each_file_parses(self):
        for rel in FILES:
            with self.subTest(file=rel):
                self.assertTrue(parse(rel), rel)

    def test_one_bom_each(self):
        for rel in FILES:
            with self.subTest(file=rel):
                with open(os.path.join(REPO, rel), "rb") as f:
                    raw = f.read()
                self.assertTrue(raw.startswith(BOM), "no UTF-8 BOM")
                self.assertFalse(raw[len(BOM):].startswith(BOM), "a doubled BOM")

    def test_each_file_says_what_it_answers_and_when_to_go(self):
        for rel in FILES:
            with self.subTest(file=rel):
                head = read(rel)[:4000]
                self.assertRegex(head, r"What (it|they) answers?")
                self.assertIn(DELETE_LINE, head)

    def test_every_log_line_is_tagged(self):
        lines = log_lines()
        self.assertGreater(len(lines), 50)
        for rel, text in lines:
            with self.subTest(line=text):
                self.assertTrue(text.startswith("TE_PROBE_115 "), f"{rel}: {text}")

    def test_every_log_line_is_literal(self):
        for rel, text in log_lines():
            if text in C19_LINES:
                continue
            with self.subTest(line=text):
                self.assertNotRegex(text, r"[\[\]$]", f"{rel}: a probe line must be literal")

    def test_c19_quotes_its_arguments_once(self):
        texts = [text for _, text in log_lines()]
        for line in C19_LINES:
            self.assertEqual(texts.count(line), 1, line)
        effects = code(EFFECTS)
        self.assertEqual(len(re.findall(r"\bte_probe_115_quoted_arg_effect\s*=\s*\{\s*N = 7 WORD = probe\s*\}",
                                        effects)), 1)
        self.assertIn("local_var:te_probe_115_c19_n = 7", block(effects, "te_probe_115_quoted_arg_effect"))

    def test_every_event_and_effect_called_is_defined(self):
        events = set(parse(EVENTS))
        effects = set(parse(EFFECTS)) | set(parse(C5_EFFECTS))
        text = "\n".join(code(rel) for rel in FILES)
        fired = set(re.findall(r"\bid\s*=\s*(te_probe_115\.\d+)", text))
        self.assertEqual(fired, events - {"namespace"}, "an event fired and not defined, or defined and never fired")
        called = set(re.findall(r"^[ \t]+(te_probe_115_\w+_effect)\s*=\s*(?:yes|\{)", text, re.M))
        self.assertEqual(called - effects, set(), "a probe effect called and not defined")
        self.assertEqual(effects - called, set(), "a probe effect defined and never called")

    def test_the_events_are_hidden_with_no_options(self):
        for key, value in parse(EVENTS).items():
            if key == "namespace":
                continue
            with self.subTest(event=key):
                event = body(value)
                self.assertEqual(body(event.get("hidden")), "yes")
                self.assertNotIn("option", event)

    def test_the_entry_stays_off_players(self):
        entry = body(parse(ENTRY)["te_probe_115"])
        shown = body(entry["is_shown_when_inactive"])
        self.assertEqual(body(shown["is_ai"]), "yes")
        self.assertEqual(body(entry["can_revolution_inherit"]), "no")
        self.assertEqual(body(entry["transferable"]), "no")
        for field in ("scripted_button", "widget", "should_be_pinned_by_default_uninvolved_or_context",
                      "map_color", "modifiers_while_active"):
            self.assertNotIn(field, entry)
        self.assertIn("timeout", entry)

    def test_the_entry_carries_c5s_bar(self):
        entry = body(parse(ENTRY)["te_probe_115"])
        self.assertEqual(body(entry["scripted_progress_bar"]), "te_probe_115_c5_bar")
        bar = code(C5_BARS)
        self.assertIn("te_probe_115_c5_bar", parse(C5_BARS))
        # the three minimums the reads tell apart
        minimum = block(bar, "te_probe_115_c5_bar")
        for value in ("value = 5", "value = 40", "value = 20", "has_variable = te_probe_115_owner",
                      "journal_entry_age >= 0"):
            self.assertIn(value, minimum)


class TestC7Modifiers(unittest.TestCase):
    """C7's thresholds read country_nd_crew_strain_monthly_add as scale x -6 and country_nd_launch_credit_add as
    4 x 0.25: the two display-only modifiers must keep those figures, their types must stay unread script-only ones,
    and the probe must be their only reader."""

    MODIFIERS = "common/static_modifiers/nuclear_deterrence_modifiers.txt"
    TYPES = "common/modifier_type_definitions/nuclear_deterrence_display_types.txt"

    def test_the_figures(self):
        mods = code(self.MODIFIERS)
        terms_1 = block(mods, "nd_readiness_terms_1")
        self.assertEqual(re.findall(r"\b(country_\w+)\s*=\s*(-?[\d.]+)", terms_1),
                         [("country_nd_crew_strain_monthly_add", "-6")])
        terms_2 = block(mods, "nd_authority_terms_2")
        numeric = dict(re.findall(r"\b(country_\w+)\s*=\s*(-?[\d.]+)", terms_2))
        self.assertEqual(numeric.get("country_nd_launch_credit_add"), "0.25")
        self.assertNotIn("country_nd_crew_strain_monthly_add", terms_2)

    def test_the_types_are_unread_script_only(self):
        types = code(self.TYPES)
        for name in ("country_nd_crew_strain_monthly_add", "country_nd_launch_credit_add"):
            with self.subTest(type=name):
                self.assertIn("script_only = yes", block(types, name))
                readers = []
                for sub in ("common", "events", "gui"):
                    for root, _, files in os.walk(os.path.join(REPO, sub)):
                        for f in files:
                            rel = os.path.relpath(os.path.join(root, f), REPO).replace(os.sep, "/")
                            if f.endswith((".txt", ".gui")) and rel != EFFECTS and f"modifier:{name}" in read(rel):
                                readers.append(rel)
                self.assertEqual(readers, [], "another reader would see the probe's modifier")

    def test_the_entry_scales_them(self):
        entry = code(ENTRY)
        self.assertRegex(entry, r"modifier = nd_authority_terms_2\s*value = \{\s*value = 4\s*\}")
        self.assertRegex(entry, r"modifier = nd_readiness_terms_1\s*value = \{\s*value = 0\s*if = \{\s*limit = \{"
                                r"\s*is_ai = yes")


class TestPlaytestDoc(unittest.TestCase):
    def test_the_doc_names_every_probe_line(self):
        doc = read(DOC)
        names = {text.split()[1] for _, text in log_lines()}
        missing = sorted(name for name in names if not re.search(rf"TE_PROBE_115 {re.escape(name)}\b", doc))
        self.assertEqual(missing, [], "probe lines the play-test doc does not explain")


if __name__ == "__main__":
    unittest.main()
