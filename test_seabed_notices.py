"""The seabed rush, announced (seabed claims spec § 7). "The Seabed Rush
Begins" is an event (owner, 2026-10-17), once a game, to every player when
the first country can claim, and the research's headline stands down while
the Global Commons rule is on; two notifications follow: "A New Claimant in the <Basin>" when a sharing first gives a country a
share where the receiver already has one; "The <Basin> Is Fully Licensed"
once each time the world's licences reach a basin's pool.
"""
import re
import unittest

from test_seabed_script import EFFECTS, block, read, strip_comments
import seabed_model as m

MESSAGES = "common/messages/te_global_commons_seabed_messages.txt"
NOTIF_LOC = "localization/english/te_notifications_l_english.yml"
EVENTS = "events/te_seabed_events.txt"
HEADLINES = "common/on_actions/headlines.txt"
IMAGES = "scripts/image_pipeline/event_image_prompts.py"


def rush_block():
    """te_seabed_global_monthly from the rush flag's first mention to its
    event."""
    body = strip_comments(block(read(EFFECTS), "te_seabed_global_monthly"))
    start = body.index("te_seabed_rush_announced")
    end = body.index("trigger_event = { id = te_seabed.3")
    return body, body[body.rfind("if = {", 0, start):end]


class SeabedNoticeTest(unittest.TestCase):
    def test_rush_notice_once(self):
        body = strip_comments(block(read(EFFECTS), "te_seabed_global_monthly"))
        self.assertIn("te_seabed_rush_announced", body)
        self.assertIn("trigger_event = { id = te_seabed.3 popup = yes }", body)
        self.assertNotIn("te_seabed_rush_notice", body)
        self.assertIn("set_global_variable = te_seabed_rush_announced", body)

    def test_rush_notice_skips_old_saves(self):
        # an old save with a sharing already done sets the flag without posting
        _, rush = rush_block()
        self.assertIn("NOT = { has_global_variable = te_seabed_pass_year }", rush)

    def test_rush_runs_before_the_first_sharing(self):
        """The first sharing runs the month the first claimant appears and
        sets te_seabed_pass_year: checked after it, the rush would never be
        told."""
        body, _ = rush_block()
        self.assertLess(body.index("te_seabed_rush_announced"), body.index("te_seabed_yearly_pass = yes"))

    def test_rush_waits_for_the_rule_and_a_claimant(self):
        _, rush = rush_block()
        self.assertIn("te_global_commons_enabled = yes", rush)
        self.assertIn("te_seabed_is_claimant = yes", rush)
        self.assertIn("save_scope_as = te_seabed_first_claimant", rush)
        self.assertIn("name = te_seabed_first_claimant value = scope:te_seabed_first_claimant", rush)
        self.assertIn("is_ai = no", rush)

    def test_new_claimant_notice_only_to_sharers(self):
        body = strip_comments(read(EFFECTS))
        self.assertRegex(body, r"te_seabed_ent_\$B\$ > 0[\s\S]{0,400}post_notification = te_seabed_new_claimant_notice")

    def test_new_claimant_receivers_had_a_share_before(self):
        """Told: every other country, not decentralized, with a share there
        now that it had at an earlier sharing (two newcomers of one sharing
        aren't told of each other); the newcomer is the country with a share
        and no mark yet."""
        body = strip_comments(block(read(EFFECTS), "te_seabed_claimant_notice"))
        self.assertIn("NOT = { has_variable = te_seabed_claimed_$B$ }", body)
        self.assertIn("save_scope_as = te_seabed_newcomer", body)
        receivers = body[body.index("save_scope_as = te_seabed_newcomer"):]
        for term in ("NOT = { this = scope:te_seabed_newcomer }", "is_ai = no",
                     "has_variable = te_seabed_claimed_$B$", "var:te_seabed_ent_$B$ > 0",
                     "post_notification = te_seabed_new_claimant_notice_$B$"):
            self.assertIn(term, receivers)

    def test_new_claimant_receivers_have_home_coast_there(self):
        """Review I2: a distant share in every basin made a great power hear of
        every newcomer about four times; only a basin we have coast on counts."""
        body = strip_comments(block(read(EFFECTS), "te_seabed_claimant_notice"))
        receivers = body[body.index("save_scope_as = te_seabed_newcomer"):]
        self.assertRegex(receivers, r"has_variable = te_seabed_coast_\$B\$\s*var:te_seabed_coast_\$B\$ > 0[\s\S]*"
                                    r"post_notification = te_seabed_new_claimant_notice_\$B\$")

    def test_first_sharing_only_marks(self):
        """An old save's first sharing with this code, or a new game's first,
        has every share new: it marks them without a notice."""
        body = strip_comments(block(read(EFFECTS), "te_seabed_claimant_notices"))
        guard = body.index("has_global_variable = te_seabed_claimed_seeded")
        for b in m.BASINS:
            self.assertGreater(body.index(f"te_seabed_claimant_notice = {{ B = {b} }}"), guard)
            self.assertGreater(body.index(f"te_seabed_mark_claimed = {{ B = {b} }}"),
                               body.index(f"te_seabed_claimant_notice = {{ B = {b} }}"))
        self.assertIn("set_global_variable = te_seabed_claimed_seeded", body)
        mark = strip_comments(block(read(EFFECTS), "te_seabed_mark_claimed"))
        self.assertIn("var:te_seabed_ent_$B$ > 0", mark)
        self.assertIn("set_variable = te_seabed_claimed_$B$", mark)

    def test_claimant_notices_follow_the_sharing(self):
        body = strip_comments(block(read(EFFECTS), "te_seabed_yearly_pass"))
        self.assertGreater(body.index("te_seabed_claimant_notices = yes"), body.index("te_seabed_pass_subject_claims = yes"))

    def test_full_notice_rearms_only_after_falling_below(self):
        body = strip_comments(block(read(EFFECTS), "te_seabed_world_totals"))
        self.assertIn("te_seabed_full_$B$", body)
        self.assertIn("remove_global_variable = te_seabed_full_$B$", body)
        full = body[body.index("global_var:te_seabed_records_$B$ >= te_seabed_pool_$B$"):]
        self.assertLess(full.index("NOT = { has_global_variable = te_seabed_full_$B$ }"),
                        full.index("post_notification = te_seabed_basin_full_notice_$B$"))
        self.assertLess(full.index("post_notification = te_seabed_basin_full_notice_$B$"),
                        full.index("remove_global_variable = te_seabed_full_$B$"))

    def test_full_notice_to_claimants_there(self):
        """Review I3: when a basin is full every share equals its holdings, so
        a share alone missed the coastal claimant with no mines there yet,
        the reader the notice is written for."""
        body = strip_comments(block(read(EFFECTS), "te_seabed_world_totals"))
        full = body[body.index("set_global_variable = te_seabed_full_$B$"):body.index("post_notification = te_seabed_basin_full_notice_$B$")]
        self.assertIn("is_ai = no", full)
        self.assertRegex(full, r"OR = \{[\s\S]*var:te_seabed_ent_\$B\$ > 0[\s\S]*var:te_seabed_coast_\$B\$ > 0")

    def test_messages(self):
        text = read(MESSAGES)
        self.assertNotIn("te_seabed_rush_notice", text)
        names = [f"te_seabed_{k}_notice_{b}" for k in ("new_claimant", "basin_full")
                                             for b in m.BASINS]
        for name in names:
            body = block(text, name)
            self.assertIn("type = country", body, name)
            self.assertIn("notification_type = feed", body, name)
            # Review I2: a group lists them in Message Settings, so a player can mute them.
            self.assertIn('group = "te_seabed_notification_group"', body, name)
        self.assertRegex(read("localization/english/te_miscellaneous_l_english.yml") + read(NOTIF_LOC),
                         re.compile(r'^ te_seabed_notification_group:0 "', re.M))

    def test_loc(self):
        loc = read(NOTIF_LOC)
        self.assertNotIn("te_seabed_rush_notice", loc)
        keys = [f"te_seabed_{k}_notice_{b}" for k in ("new_claimant", "basin_full")
                                            for b in m.BASINS]
        for k in keys:
            for part in ("name", "desc", "tooltip"):
                self.assertIn(f"notification_{k}_{part}:", loc)
        for b in m.BASINS:
            for k in ("new_claimant", "basin_full"):
                name = re.search(rf"^ notification_te_seabed_{k}_notice_{b}_name:0 \"(.*)\"$", loc, re.M).group(1)
                self.assertIn(f"$te_seabed_basin_{b}$", name)
            desc = re.search(rf"^ notification_te_seabed_new_claimant_notice_{b}_desc:0 \"(.*)\"$", loc, re.M).group(1)
            self.assertIn("[SCOPE.sCountry('te_seabed_newcomer').GetName]", desc)


class RushEventTest(unittest.TestCase):
    """te_seabed.3, The Seabed Rush Begins: news, so its one option only
    points to the Seabed tab; three descriptions (we are the first, a coastal
    country, a landlocked one); the first claimant read back from a global
    variable in case the saved scope doesn't survive the dispatch."""

    def event(self):
        return strip_comments(block(read(EVENTS), "te_seabed.3"))

    def test_visible_with_art(self):
        ev = self.event()
        self.assertNotIn("hidden = yes", ev)
        self.assertIn('event_image = { texture = "gfx/event_pictures/law_of_sea_maritime.dds" }', ev)
        self.assertIn("title = te_seabed.3.t", ev)
        self.assertIn("flavor = te_seabed.3.f", ev)
        for d in ("te_seabed.3.d_first", "te_seabed.3.d_coastal", "te_seabed.3.d_landlocked"):
            self.assertIn(f"desc = {d}", ev)

    def test_first_claimant_read_back(self):
        ev = self.event()
        imm = ev[ev.index("immediate = {"):]
        self.assertIn("global_var:te_seabed_first_claimant ?= { save_scope_as = te_seabed_first_claimant }", imm)

    def test_one_option_pointing_to_the_tab(self):
        ev = self.event()
        self.assertEqual(ev.count("option = {"), 1)
        self.assertIn("custom_tooltip = te_seabed.3.a.tt", ev)

    def test_loc(self):
        loc = read("localization/english/te_events_l_english.yml")
        for k in ("t", "d_first", "d_coastal", "d_landlocked", "f", "a", "a_first", "a.tt"):
            self.assertRegex(loc, re.compile(rf"^ te_seabed\.3\.{re.escape(k)}:\d+ \"", re.M), k)
        coastal = re.search(r"^ te_seabed\.3\.d_coastal:\d+ \"(.*)\"$", loc, re.M).group(1)
        self.assertIn("[SCOPE.sCountry('te_seabed_first_claimant').GetName]", coastal)

    def test_registered_with_its_picture(self):
        reg = read(IMAGES)
        entry = reg[reg.index('"law_of_sea_maritime": {'):]
        entry = entry[:entry.index("},")]
        self.assertIn('"te_seabed.3"', entry)

    def test_headline_stands_down_under_the_rule(self):
        """headlines_tech_abyssal_plain_mining tells players the same news;
        with the Global Commons rule on the event tells it instead."""
        body = strip_comments(block(read(HEADLINES), "extra_headlines_tech"))
        self.assertRegex(body, r"limit = \{ NOT = \{ te_global_commons_enabled = yes \} \}\s*"
                               r"headlines_tech_announce_effect = \{ TECH = abyssal_plain_mining \}")


if __name__ == "__main__":
    unittest.main()
