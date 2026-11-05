"""No event option is named after its own event's title, desc or flavor key.

One loc key can't be both: an option named `<event>.d` shows the description
as its button text, or the event's description shows the button's. Options
are lettered a, b, c, e, g… and skip d, f and t
(docs/guides/event_creation_guide.md § Localization for Events).
`decolonization_events.9` and `arch_events.2` shipped such collisions (their
options are now `.9.e` and `.2.g`/`.2.h`).

Run: python3 -m unittest test_event_option_keys -v
"""
import glob
import os
import unittest

from paradox_file_parser import ParadoxFileParser

REPO = os.path.dirname(os.path.abspath(__file__))
EVENTS = os.path.join(REPO, "events")

# Blocks inside title/desc/flavor that hold the alternatives' keys.
_DESC_WRAPPERS = {"first_valid", "random_valid", "triggered_desc"}


def _pairs(obj):
    """(key, value) pairs of a parsed block: a dict when its keys are unique,
    a list of single-key dicts when a key repeats."""
    if isinstance(obj, dict):
        yield from obj.items()
    elif isinstance(obj, list):
        for item in obj:
            if isinstance(item, dict):
                yield from item.items()


def _val(v):
    return v[1] if isinstance(v, tuple) else v


def _keys(value, leaf_keys):
    """Every loc key a title/desc/flavor or option name can print: the value
    itself, or each `leaf_keys` entry under its first_valid/triggered_desc
    alternatives. Triggers are skipped."""
    value = _val(value)
    if isinstance(value, str):
        yield value
        return
    for k, sub in _pairs(value):
        if k in leaf_keys or k in _DESC_WRAPPERS:
            yield from _keys(sub, leaf_keys)


def collisions(text, parser=None):
    """(event id, key) for each option name that is also one of its event's
    title, desc or flavor keys, and the number of events read."""
    parser = parser or ParadoxFileParser()
    top = parser.parse_object(parser.tokenize("{" + text + "}"))[0]
    found = []
    events = 0
    for event_id, body in _pairs(top):
        body = _val(body)
        if not isinstance(body, (dict, list)):
            continue
        events += 1
        text_keys = set()
        names = []
        for k, v in _pairs(body):
            if k in ("title", "desc", "flavor"):
                text_keys.update(_keys(v, {"desc"}))
            elif k == "option":
                for kk, vv in _pairs(_val(v)):
                    if kk == "name":
                        names.extend(_keys(vv, {"text", "desc"}))
        found.extend((event_id, name) for name in names if name in text_keys)
    return found, events


class EventOptionKeyTests(unittest.TestCase):
    def test_the_scan_catches_a_collision(self):
        text = """
namespace = probe
probe.1 = {
	title = probe.1.t
	desc = { first_valid = { triggered_desc = { trigger = { always = no } desc = probe.1.d_x } triggered_desc = { desc = probe.1.d } } }
	flavor = probe.1.f
	option = { name = probe.1.a }
	option = { name = probe.1.d }
	option = { name = { trigger = { always = yes } text = probe.1.f } }
}
probe.2 = {
	title = probe.2.t
	desc = probe.2.d
	option = { name = probe.2.e }
}
"""
        self.assertEqual(collisions(text), ([("probe.1", "probe.1.d"), ("probe.1", "probe.1.f")], 2))

    def test_no_option_is_named_after_its_events_text(self):
        parser = ParadoxFileParser()
        found = []
        events = 0
        paths = sorted(glob.glob(os.path.join(EVENTS, "**", "*.txt"), recursive=True))
        self.assertTrue(paths)
        for path in paths:
            with open(path, encoding="utf-8-sig") as fh:
                hits, n = collisions(fh.read(), parser)
            events += n
            rel = os.path.relpath(path, REPO)
            found.extend(f"{rel}: {event_id} has an option named {key}" for event_id, key in hits)
        self.assertGreater(events, 1000, "the scan read the events")
        self.assertEqual(found, [], "rename the option (a, b, c, e, g…; never d, f or t)")


if __name__ == "__main__":
    unittest.main()
