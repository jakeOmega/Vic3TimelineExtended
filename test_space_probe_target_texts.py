"""The Deep-Space Probe's events speak of the target it was sent to (#1620).

space_race_events.81 sends the probe to Venus, Mars or the asteroid belt, or
on the Grand Tour past Jupiter and the planets beyond it, and records the
choice in sr_probe_target_<target>. None of the three single targets is in
the outer solar system, yet .37 reported "the first images of the outer solar
system" and .45 planned a Jupiter flyby whichever was chosen. Now .37's
description is keyed on the target, with a last rung that names none for a
probe with no target set, and .45 names no planet, except in the Grand Tour's
own texts (the `_tour` keys), which are about Jupiter.
"""
import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
EVENTS = os.path.join(REPO, "events", "space_race_events.txt")
LOC_DIR = os.path.join(REPO, "localization", "english")

# The words each target's description must carry, and the ones no text of
# these two events may: places the probe is never sent.
TARGET_WORDS = {"venus": "Venus", "mars": "Mars", "asteroid": "asteroid", "tour": "Jupiter"}
# Where a single-target probe never goes. The Grand Tour does: its texts are
# the keys ending in _tour, each shown only under sr_probe_target_tour.
NEVER = ("Jupiter", "Saturn", "outer system", "outer solar system", "gas giant")
TOUR = "_tour"


def _read(path):
    with open(path, encoding="utf-8-sig") as f:
        return re.sub(r"#[^\n]*", "", f.read())


def _block(text, name):
    m = re.search(r"^[ \t]*" + re.escape(name) + r"\s*=\s*\{", text, re.M)
    assert m, name
    depth, i = 0, m.end() - 1
    while True:
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        if depth == 0:
            return text[m.end():i]
        i += 1


def _loc():
    values = {}
    for name in sorted(os.listdir(LOC_DIR)):
        if not name.endswith(".yml") or name == "te_unused_l_english.yml":
            continue
        with open(os.path.join(LOC_DIR, name), encoding="utf-8-sig") as f:
            for line in f:
                m = re.match(r'\s+([A-Za-z0-9_.\-]+):\d*\s+"(.*)"\s*$', line)
                if m:
                    values[m.group(1)] = m.group(2)
    return values


class ProbeTargetTextsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.events = _read(EVENTS)
        cls.loc = _loc()

    def targets(self):
        """The targets .81 can set, read from its options."""
        found = re.findall(r"set_variable = \{ name = sr_probe_target_(\w+) value = yes \}",
                           _block(self.events, "space_race_events.81"))
        self.assertEqual(sorted(found), sorted(TARGET_WORDS), "a new target needs its texts here")
        return found

    def test_every_target_has_its_own_description_of_the_first_images(self):
        desc = " ".join(_block(_block(self.events, "space_race_events.37"), "desc").split())
        for target in self.targets():
            key = f"space_race_events.37.d_{target}"
            self.assertIn(f"triggered_desc = {{ desc = {key} "
                          f"trigger = {{ has_variable = sr_probe_target_{target} }} }}", desc)
            self.assertIn(TARGET_WORDS[target], self.loc[key], key)
            for other, word in TARGET_WORDS.items():
                if other != target:
                    self.assertNotIn(word, self.loc[key], f"{key} names another target")

    def test_the_last_rung_names_no_target(self):
        desc = " ".join(_block(_block(self.events, "space_race_events.37"), "desc").split())
        self.assertTrue(desc.endswith("desc = space_race_events.37.d }"),
                        "the untriggered description comes last in the first_valid")
        for word in TARGET_WORDS.values():
            self.assertNotIn(word, self.loc["space_race_events.37.d"])

    def test_what_every_target_shares_names_none(self):
        """The title, flavor and options of .37 show under every target and
        under none; .45's plain texts under every target but the Grand Tour."""
        shared = [f"space_race_events.37.{s}" for s in ("t", "f", "a", "b")]
        shared += [f"space_race_events.45.{s}" for s in ("t", "d", "f", "a", "b", "c")]
        for key in shared:
            for word in TARGET_WORDS.values():
                self.assertNotIn(word, self.loc[key], key)

    def test_no_text_sends_the_probe_where_it_cannot_go(self):
        keys = [k for k in self.loc if re.match(r"space_race_events\.(37|45)\.", k)]
        self.assertGreaterEqual(len(keys), 13)
        for key in keys:
            if key.endswith(TOUR):
                continue
            for word in NEVER:
                self.assertNotIn(word.lower(), self.loc[key].lower(), f"{key}: {word}")

    def test_the_grand_tour_s_texts_show_only_on_the_tour(self):
        """Every _tour key of .4, .37 and .45 is named once in its event,
        beside a test of sr_probe_target_tour, and the plain key follows it as
        the fallback."""
        for event, slots in (("4", ("d",)), ("37", ("d",)), ("45", ("d", "f", "a", "b", "c"))):
            body = " ".join(_block(self.events, f"space_race_events.{event}").split())
            for slot in slots:
                key = f"space_race_events.{event}.{slot}{TOUR}"
                self.assertIn(key, self.loc)
                self.assertEqual(body.count(key + " "), 1, key)
                gated = (f"desc = {key} trigger = {{ has_variable = sr_probe_target_tour }}",
                         f"trigger = {{ has_variable = sr_probe_target_tour }} text = {key} ")
                self.assertTrue(any(g in body for g in gated), key)
                plain = key[:-len(TOUR)]
                self.assertGreater(body.index(plain + " ", body.index(key) + len(key)), body.index(key), key)
        for slot in ("d", "f", "a"):
            self.assertIn("Jupiter", self.loc[f"space_race_events.45.{slot}{TOUR}"])

    def test_the_fastest_trajectory_is_the_one_named_fastest(self):
        """.45.a gives the most months, and is the only option that says so."""
        event = _block(self.events, "space_race_events.45")
        months = {}
        for option in re.finditer(r"text = space_race_events\.45\.(\w)\n(.*?)(?=\n\toption = \{|\Z)",
                                  event, re.S):
            months[option.group(1)] = int(re.search(r"MONTHS = (\d+)", option.group(2)).group(1))
        self.assertEqual(sorted(months), ["a", "b", "c"])
        self.assertEqual(max(months, key=months.get), "a")
        self.assertIn("fastest", self.loc["space_race_events.45.a"])
        for letter in ("b", "c"):
            self.assertNotIn("fast", self.loc[f"space_race_events.45.{letter}"])
        # The Grand Tour's names for the same three options: a takes the most
        # speed, and b is the one that says it is slower.
        self.assertIn("speed", self.loc["space_race_events.45.a_tour"])
        self.assertIn("slower", self.loc["space_race_events.45.b_tour"])
        self.assertNotIn("slow", self.loc["space_race_events.45.a_tour"])


if __name__ == "__main__":
    unittest.main()
