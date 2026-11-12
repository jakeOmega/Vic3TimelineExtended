"""The Structural Anomaly's "Halt construction" stops the space elevator site.

`wonder_events.2.a` used to add a country modifier named "Elevator Construction
Halted" and nothing else: the site kept its tick and its bill (#1621). Now the
option sets a 180-day timer, and while it runs the site stands on its paused
production method, the one a player would otherwise pick by hand to stop
paying for a site that is not building. The site returns to its speed by
itself. These tests pin each link of that chain in the script:

  the option      sets the timer and pauses every site at once, and says so
  the state pulse skips the tick and keeps the site paused while the timer runs
  the helpers     remember each speed the site's method group offers, switch
                  to the paused method, and put the speed back afterwards
  the paused      method makes no progress and costs less than any speed
  method
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EVENTS = ROOT / "events" / "wonder_events.txt"
ON_ACTIONS = ROOT / "common" / "on_actions" / "extra_on_actions.txt"
EFFECTS = ROOT / "common" / "scripted_effects" / "extra_effects.txt"
PM_GROUPS = ROOT / "common" / "production_method_groups" / "extra_pm_groups.txt"
PMS = ROOT / "common" / "production_methods" / "extra_pms.txt"
LOC = ROOT / "localization" / "english" / "te_events_l_english.yml"

SITE = "building_space_elevator_construction_site"
PAUSED = "pm_space_elevator_construction_paused"
HALT_DAYS = 180
# The state pulse is monthly, so the halt can be seen over up to a month late.
PULSE_DAYS = 31


def _read(path):
    return path.read_text(encoding="utf-8-sig")


def _strip_comments(text):
    return re.sub(r"#[^\n]*", "", text)


def _block(text, header):
    """Body of the brace block opened by the first match of `header`."""
    match = re.search(header, text, re.M)
    if match is None:
        return None
    depth, i = 1, match.end()
    while depth:
        depth += (text[i] == "{") - (text[i] == "}")
        i += 1
    return text[match.end():i - 1]


def _effect(name):
    body = _block(_strip_comments(_read(EFFECTS)), rf"^{name}\s*=\s*\{{")
    assert body is not None, f"{name} not found in {EFFECTS.name}"
    return body


def _option_a():
    event = _block(_strip_comments(_read(EVENTS)), r"^wonder_events\.2\s*=\s*\{")
    assert event is not None, "wonder_events.2 not found"
    for match in re.finditer(r"\boption\s*=\s*\{", event):
        body = _block(event[match.start():], r"\boption\s*=\s*\{")
        if re.search(r"\bname\s*=\s*wonder_events\.2\.a\b", body):
            return body
    raise AssertionError("wonder_events.2.a not found")


def _speeds():
    """The site's methods other than the paused one, as the `$SPEED$` tokens."""
    group = _block(
        _strip_comments(_read(PM_GROUPS)),
        r"pmg_base_building_space_elevator_construction_site\s*=\s*\{",
    )
    methods = re.findall(r"\bpm_space_elevator_construction_(\w+)", group)
    assert "paused" in methods, "the site's method group lost its paused method"
    return [m for m in methods if m != "paused"]


def _method(name):
    body = _block(_strip_comments(_read(PMS)), rf"^{name}\s*=\s*\{{")
    assert body is not None, f"{name} not found"
    return body


def _sum(body, pattern):
    return sum(float(v) for v in re.findall(pattern, body))


class TheOptionHalts(unittest.TestCase):
    def test_it_sets_the_timer_inside_a_tooltip_that_says_so(self):
        option = _option_a()
        tooltip = _block(option, r"\bcustom_tooltip\s*=\s*\{")
        self.assertIsNotNone(tooltip, "a set_variable shows nothing by itself")
        self.assertRegex(
            tooltip,
            rf"set_variable\s*=\s*\{{\s*name\s*=\s*space_elevator_halt\s+days\s*=\s*{HALT_DAYS}\s*\}}",
        )
        key = re.search(r"\btext\s*=\s*(\S+)", tooltip).group(1)
        line = re.search(rf'^\s*{re.escape(key)}:\d*\s*"(.*)"\s*$', _read(LOC), re.M)
        self.assertIsNotNone(line, f"{key} has no text")
        self.assertIn(str(HALT_DAYS), line.group(1), "the tooltip gives the halt's length")
        self.assertIn("Paused", line.group(1), "the tooltip names the method the site takes")

    def test_it_pauses_every_site_at_once(self):
        tooltip = _block(_option_a(), r"\bcustom_tooltip\s*=\s*\{")
        states = _block(tooltip, r"\bevery_scope_state\s*=\s*\{")
        self.assertIsNotNone(states)
        self.assertRegex(states, rf"limit\s*=\s*\{{\s*has_building\s*=\s*{SITE}\s*\}}")
        self.assertRegex(states, r"\bspace_elevator_halt_site\s*=\s*yes\b")

    def test_the_modifier_lasts_as_long_as_the_halt(self):
        # "Elevator Construction Halted" must not outlast the halt it names.
        modifier = _block(_option_a(), r"\badd_modifier\s*=\s*\{")
        self.assertRegex(modifier, r"\bname\s*=\s*we_se_structural_halt\b")
        self.assertRegex(modifier, rf"\bdays\s*=\s*{HALT_DAYS}\b")


class ThePulseKeepsTheSitePaused(unittest.TestCase):
    def setUp(self):
        on_action = _block(_strip_comments(_read(ON_ACTIONS)), r"^space_elevator_on_action\s*=\s*\{")
        self.assertIsNotNone(on_action)
        self.site = _block(on_action, rf"limit\s*=\s*\{{\s*has_building\s*=\s*{SITE}\s*\}}\s*(?=if\b)")
        self.assertIsNotNone(self.site, "the site branch no longer opens with the halt test")

    def test_a_halted_site_is_paused_and_gets_no_tick(self):
        halted = _block(self.site, r"^\s*if\s*=\s*\{")
        self.assertRegex(
            halted, r"limit\s*=\s*\{\s*owner\s*=\s*\{\s*has_variable\s*=\s*space_elevator_halt\s*\}\s*\}"
        )
        self.assertRegex(halted, r"\bspace_elevator_halt_site\s*=\s*yes\b")
        self.assertNotRegex(halted, r"\bspace_elevator_construction\s*=", "a halted site must not tick")

    def test_the_tick_runs_only_when_not_halted_after_the_resume(self):
        running = _block(self.site, r"\belse\s*=\s*\{")
        self.assertIsNotNone(running)
        resume = re.search(r"\bspace_elevator_resume_site\s*=\s*yes\b", running)
        tick = re.search(r"\bspace_elevator_construction\s*=\s*yes\b", running)
        self.assertIsNotNone(resume)
        self.assertIsNotNone(tick)
        self.assertLess(resume.start(), tick.start())
        outside = self.site.replace(running, "")
        self.assertNotRegex(outside, r"\bspace_elevator_construction\s*=\s*yes\b")


class TheHelpersSwitchTheMethod(unittest.TestCase):
    def test_every_speed_is_remembered_and_put_back(self):
        speeds = _speeds()
        self.assertTrue(speeds)
        halt, resume = _effect("space_elevator_halt_site"), _effect("space_elevator_resume_site")
        for speed in speeds:
            with self.subTest(speed=speed):
                self.assertRegex(halt, rf"space_elevator_halt_remember\s*=\s*\{{\s*SPEED\s*=\s*{speed}\s*\}}")
                self.assertRegex(resume, rf"space_elevator_halt_restore\s*=\s*\{{\s*SPEED\s*=\s*{speed}\s*\}}")

    def test_the_halt_switches_to_the_paused_method(self):
        halt = _effect("space_elevator_halt_site")
        switch = _block(halt, r"\bactivate_production_method\s*=\s*\{")
        self.assertRegex(switch, rf"building_type\s*=\s*{SITE}\b")
        self.assertRegex(switch, rf"production_method\s*=\s*{PAUSED}\b")

    def test_the_remembered_speed_outlasts_the_halt_and_then_runs_out(self):
        remember = _effect("space_elevator_halt_remember")
        self.assertRegex(remember, r"has_active_production_method\s*=\s*pm_space_elevator_construction_\$SPEED\$")
        stored = re.search(
            r"set_variable\s*=\s*\{\s*name\s*=\s*space_elevator_halt_resume\s+value\s*=\s*flag:\$SPEED\$\s+days\s*=\s*(\d+)\s*\}",
            remember,
        )
        self.assertIsNotNone(stored, "the speed is stored as a timed flag on the state")
        self.assertGreater(int(stored.group(1)), HALT_DAYS + PULSE_DAYS)

    def test_the_resume_restores_a_paused_site_and_forgets(self):
        resume = _effect("space_elevator_resume_site")
        held = _block(resume, r"limit\s*=\s*\{\s*has_variable\s*=\s*space_elevator_halt_resume\s*\}")
        self.assertIsNotNone(held)
        self.assertRegex(held, r"\bremove_variable\s*=\s*space_elevator_halt_resume\b")
        # A speed the player picked after the last pulse stands: only a site
        # still on the paused method is switched.
        still_paused = _block(held, r"^\s*if\s*=\s*\{")
        self.assertRegex(still_paused, rf"has_active_production_method\s*=\s*{PAUSED}\b")
        self.assertRegex(still_paused, r"space_elevator_halt_restore")
        restore = _effect("space_elevator_halt_restore")
        self.assertRegex(restore, r"var:space_elevator_halt_resume\s*=\s*flag:\$SPEED\$")
        self.assertRegex(restore, r"production_method\s*=\s*pm_space_elevator_construction_\$SPEED\$")


class ThePausedMethodStopsTheCost(unittest.TestCase):
    def test_it_makes_no_progress(self):
        self.assertNotIn("building_annual_space_elevator_progress", _method(PAUSED))
        for speed in _speeds():
            with self.subTest(speed=speed):
                self.assertIn(
                    "building_annual_space_elevator_progress",
                    _method(f"pm_space_elevator_construction_{speed}"),
                )

    def test_it_buys_and_employs_a_small_fraction_of_any_speed(self):
        paused = _method(PAUSED)
        paused_goods = _sum(paused, r"goods_input_\w+_add\s*=\s*([\d.]+)")
        paused_staff = _sum(paused, r"building_employment_\w+_add\s*=\s*([\d.]+)")
        for speed in _speeds():
            with self.subTest(speed=speed):
                body = _method(f"pm_space_elevator_construction_{speed}")
                self.assertLess(paused_goods * 100, _sum(body, r"goods_input_\w+_add\s*=\s*([\d.]+)"))
                self.assertLess(paused_staff * 100, _sum(body, r"building_employment_\w+_add\s*=\s*([\d.]+)"))


if __name__ == "__main__":
    unittest.main()
