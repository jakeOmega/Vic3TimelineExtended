"""A state event triggered with a delay never ran for the Demographics self-checks (log triage 2026-11-06).

Every self-check whose verdict was a state event behind `trigger_event = { id = <state event> days = 7 }` printed its
START line and no verdict, in the 2026-11-06 observer game (1.15) and in the October 1.14.5 games: the variables each
verdict removes were still on their states years later. The country events delayed the same way (.40, .41) read OK. So
each verdict's week now waits on a country event that runs the state's verdict undelayed
(events/te_debug_demog_events.txt, "The verdicts' week waits on the owner").

This test lists every delayed trigger_event whose target is a state event. Each one left is named in KNOWN with why;
anything new fails, so the next self-check or system doesn't build on the path that never ran. te_debug_demog.199 is
the probe that tests the fact once a game (delayed_state_event, docs/testing/demographics-playtest.md). It read BROKEN
in the first new game after it landed (2026-11-08, January 1836), so the three gameplay calls that were left waiting on
it now wait on a country event too: te_demog_events.5 runs .4 in each of the country's states, and monument_events.34
and .35 run .30 and .31 in each state gm_state_tomorrow marked. The probe stays, to say when a patch makes the path
work.
"""
import functools
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent

EVENT_OPEN = re.compile(r"^([A-Za-z_][\w]*\.\d+)\s*=\s*\{", re.M)
EVENT_TYPE = re.compile(r"^\ttype\s*=\s*(\w+)", re.M)
DELAY = re.compile(r"\b(days|weeks|months|years)\s*=")

# target event -> why its delayed call stays
KNOWN = {
    "te_debug_demog.199": "the probe itself: delayed_state_event tests whether this path runs",
}


def _strip_comments(text):
    return re.sub(r"#[^\n]*", "", text)


def _block_at(text, start):
    """The text from the `{` at or after `start` to its matching `}`."""
    i = text.index("{", start)
    depth = 0
    for j in range(i, len(text)):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return text[i:j + 1]
    raise ValueError("unbalanced braces")


def _script_files():
    for sub in ("common", "events"):
        yield from sorted((ROOT / sub).rglob("*.txt"))


@functools.lru_cache(maxsize=None)
def _event_types():
    types = {}
    for path in sorted((ROOT / "events").rglob("*.txt")):
        text = _strip_comments(path.read_text(encoding="utf-8-sig"))
        for m in EVENT_OPEN.finditer(text):
            body = _block_at(text, m.end() - 1)
            t = EVENT_TYPE.search(body)
            types[m.group(1)] = t.group(1) if t else None
    return types


TOP_OPEN = re.compile(r"^(\w+)\s*=\s*\{", re.M)


def _enclosing_top_level(text, pos):
    """The name of the top-level block (a scripted effect, an event) that holds ``pos``."""
    name = None
    for m in TOP_OPEN.finditer(text):
        if m.start() > pos:
            break
        name = m.group(1)
    return name


def _helper_arguments(helper, argument):
    """[(file, value)] for each call of ``helper`` that passes ``argument``."""
    out = []
    for path in _script_files():
        text = _strip_comments(path.read_text(encoding="utf-8-sig"))
        for m in re.finditer(rf"\b{helper}\s*=\s*\{{", text):
            value = re.search(rf"\b{argument}\s*=\s*([\w.]+)", _block_at(text, m.end() - 1))
            if value:
                out.append((path.relative_to(ROOT).as_posix(), value.group(1)))
    return out


@functools.lru_cache(maxsize=None)
def _delayed_calls():
    """(file, target id) for each trigger_event with a delay. An id a scripted effect takes as an argument
    (``id = $EVENT$``) counts at each call of that effect, with the id the call passes."""
    out = []
    for path in _script_files():
        text = _strip_comments(path.read_text(encoding="utf-8-sig"))
        for m in re.finditer(r"\btrigger_event\s*=\s*\{", text):
            body = _block_at(text, m.end() - 1)
            if not DELAY.search(body):
                continue
            ident = re.search(r"\bid\s*=\s*([\w.]+)", body)
            if ident:
                out.append((path.relative_to(ROOT).as_posix(), ident.group(1)))
                continue
            param = re.search(r"\bid\s*=\s*\$(\w+)\$", body)
            helper = _enclosing_top_level(text, m.start()) if param else None
            if helper:
                out.extend(_helper_arguments(helper, param.group(1)))
    return tuple(out)


class TestDelayedStateEvents(unittest.TestCase):
    def test_no_new_delayed_state_event(self):
        types = _event_types()
        calls = _delayed_calls()
        self.assertTrue(calls, "found no delayed trigger_event at all: the scan is broken")
        found = {}
        for path, ident in calls:
            if types.get(ident) == "state_event":
                found.setdefault(ident, []).append(path)
        new = {k: v for k, v in found.items() if k not in KNOWN}
        self.assertEqual(new, {}, "a state event triggered with a delay never ran for the self-checks; "
                                  "wait on a country event and trigger the state event from it undelayed")
        self.assertEqual(sorted(set(KNOWN) - set(found)), [],
                         "a KNOWN entry no longer has a delayed call: drop it")

    def test_the_scan_sees_the_known_ones(self):
        # the old form the self-checks used must read as a delayed state-event call
        types = _event_types()
        self.assertEqual(types.get("te_debug_demog.5"), "state_event")
        self.assertEqual(types.get("te_debug_demog.205"), "country_event")
        self.assertIn(("common/scripted_effects/te_debug_demog_effects.txt", "te_debug_demog.199"), _delayed_calls())
        self.assertEqual(types.get("te_debug_demog.199"), "state_event")

    def test_the_scan_follows_an_id_passed_to_a_helper(self):
        # gm_state_tomorrow's trigger_event reads id = $EVENT$: each call counts with the id it passes
        calls = _delayed_calls()
        self.assertIn(("common/scripted_effects/gm_monument_effects.txt", "monument_events.34"), calls)
        self.assertIn(("common/scripted_effects/gm_monument_effects.txt", "monument_events.35"), calls)

    def test_each_relay_runs_its_verdict(self):
        events = _strip_comments((ROOT / "events" / "te_debug_demog_events.txt").read_text(encoding="utf-8-sig"))
        um = _strip_comments((ROOT / "events" / "te_debug_demog_um_events.txt").read_text(encoding="utf-8-sig"))
        relays = {
            "te_debug_demog.202": ("te_debug_demog.2", events),
            "te_debug_demog.205": ("te_debug_demog.5", events),
            "te_debug_demog.206": ("te_debug_demog.6", events),
            "te_debug_demog.207": ("te_debug_demog.7", events),
            "te_debug_demog.208": ("te_debug_demog.8", events),
            "te_debug_demog.210": ("te_debug_demog.10", events),
            "te_debug_demog.230": ("te_debug_demog.30", events),
            "te_debug_demog.281": ("te_debug_demog.81", events),
            "te_debug_demog.290": ("te_debug_demog.90", events),
            "te_debug_demog.330": ("te_debug_demog.130", um),
            "te_debug_demog.331": ("te_debug_demog.131", um),
        }
        calls = _delayed_calls()
        for relay, (verdict, text) in relays.items():
            with self.subTest(relay=relay):
                body = _block_at(text, text.index(f"{relay} = {{") + len(relay))
                self.assertIn("type = country_event", body)
                self.assertIn(f"trigger_event = {{ id = {verdict} }}", body)   # undelayed
                self.assertTrue(any(i == relay for _, i in calls), f"nothing arms {relay} with a delay")
                self.assertFalse(any(i == verdict for _, i in calls), f"{verdict} is still triggered with a delay")

    def test_each_gameplay_relay_runs_its_state_event(self):
        # The three gameplay calls the probe's BROKEN verdict moved (2026-11-08): each relay is a country event that
        # runs the state event undelayed, something arms it with a delay, and the state event has no delayed call.
        demog = _strip_comments((ROOT / "events" / "te_demog_events.txt").read_text(encoding="utf-8-sig"))
        monuments = _strip_comments((ROOT / "events" / "monument_events.txt").read_text(encoding="utf-8-sig"))
        relays = {
            "te_demog_events.5": ("te_demog_events.4", demog, None),
            "monument_events.34": ("monument_events.30", monuments, "gm_mon_orders_tomorrow"),
            "monument_events.35": ("monument_events.31", monuments, "gm_adopt_orphans_tomorrow"),
        }
        calls = _delayed_calls()
        for relay, (event, text, mark) in relays.items():
            with self.subTest(relay=relay):
                body = _block_at(text, text.index(f"{relay} = {{") + len(relay))
                self.assertIn("type = country_event", body)
                self.assertIn(f"trigger_event = {{ id = {event} }}", body)
                self.assertTrue(any(i == relay for _, i in calls), f"nothing arms {relay} with a delay")
                self.assertFalse(any(i == event for _, i in calls), f"{event} is still triggered with a delay")
                if mark:
                    # the mark comes off before the event runs, so a state the event asks again waits a relay
                    self.assertLess(body.index(f"remove_variable = {mark}"), body.index(f"id = {event}"))

    def test_the_probe_has_both_verdicts(self):
        events = _strip_comments((ROOT / "events" / "te_debug_demog_events.txt").read_text(encoding="utf-8-sig"))
        probe = _block_at(events, events.index("te_debug_demog.199 = {") + 18)
        self.assertIn("type = state_event", probe)
        self.assertIn("set_global_variable = { name = te_dbg_delayed_state_ran value = yes }", probe)
        verdict = _block_at(events, events.index("te_debug_demog.198 = {") + 18)
        self.assertIn("type = country_event", verdict)
        for word in ("OK", "BROKEN"):
            self.assertIn(f"TE_SELF_CHECK {word} delayed_state_event", verdict)
        effects = _strip_comments((ROOT / "common" / "scripted_effects" / "te_debug_demog_effects.txt")
                                  .read_text(encoding="utf-8-sig"))
        start = _block_at(effects, effects.index("te_debug_demog_wf_selfchecks = {") + 30)
        self.assertIn("capital = { trigger_event = { id = te_debug_demog.199 days = 7 } }", start)
        self.assertIn("trigger_event = { id = te_debug_demog.198 days = 14 }", start)


if __name__ == "__main__":
    unittest.main()
