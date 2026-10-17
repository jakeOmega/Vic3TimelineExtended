"""The seabed rush, announced (seabed claims spec § 7): three notifications,
no events. "The Seabed Rush Begins" once a game, when the first country can
claim; "A New Claimant in the <Basin>" when a sharing first gives a country a
share where the receiver already has one; "The <Basin> Is Fully Licensed"
once each time the world's licences reach a basin's pool.
"""
import re
import unittest

from test_seabed_script import EFFECTS, block, read, strip_comments
import seabed_model as m

MESSAGES = "common/messages/te_global_commons_seabed_messages.txt"
NOTIF_LOC = "localization/english/te_notifications_l_english.yml"


def rush_block():
    """te_seabed_global_monthly from the rush flag's first mention to its
    notice."""
    body = strip_comments(block(read(EFFECTS), "te_seabed_global_monthly"))
    start = body.index("te_seabed_rush_announced")
    end = body.index("post_notification = te_seabed_rush_notice")
    return body, body[body.rfind("if = {", 0, start):end]


class SeabedNoticeTest(unittest.TestCase):
    def test_rush_notice_once(self):
        body = strip_comments(block(read(EFFECTS), "te_seabed_global_monthly"))
        self.assertIn("te_seabed_rush_announced", body)
        self.assertIn("post_notification = te_seabed_rush_notice", body)
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
        self.assertIn("NOT = { is_country_type = decentralized }", rush)

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
        for term in ("NOT = { this = scope:te_seabed_newcomer }", "NOT = { is_country_type = decentralized }",
                     "has_variable = te_seabed_claimed_$B$", "var:te_seabed_ent_$B$ > 0",
                     "post_notification = te_seabed_new_claimant_notice_$B$"):
            self.assertIn(term, receivers)

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
        body = strip_comments(block(read(EFFECTS), "te_seabed_world_totals"))
        self.assertRegex(body, r"var:te_seabed_ent_\$B\$ > 0\s*\}\s*post_notification = te_seabed_basin_full_notice_\$B\$")

    def test_messages(self):
        text = read(MESSAGES)
        names = ["te_seabed_rush_notice"] + [f"te_seabed_{k}_notice_{b}" for k in ("new_claimant", "basin_full")
                                             for b in m.BASINS]
        for name in names:
            body = block(text, name)
            self.assertIn("type = country", body, name)
            self.assertIn("notification_type = feed", body, name)

    def test_loc(self):
        loc = read(NOTIF_LOC)
        keys = ["te_seabed_rush_notice"] + [f"te_seabed_{k}_notice_{b}" for k in ("new_claimant", "basin_full")
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
        rush = re.search(r"^ notification_te_seabed_rush_notice_desc:0 \"(.*)\"$", loc, re.M).group(1)
        self.assertIn("[SCOPE.sCountry('te_seabed_first_claimant').GetName]", rush)


if __name__ == "__main__":
    unittest.main()
