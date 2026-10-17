"""Seabed leases and the subject pact in script (seabed claims spec §§ 4, 5.2).

The model (scripts/analysis/seabed_model.py, test_seabed_allocation.py's
LeaseTest and SubjectTest) carries the arithmetic; these tests hold the script
to it: the five Lease <Basin> Seabed Claims treaty articles, their hook and
the hidden event that starts a lease, the sharing's shift of lease-built
licences, the settle and the consumption order.
"""
import os
import re
import unittest

from test_seabed_script import EFFECTS, TRIGGERS, VALUES, block, english_loc, m, read, strip_comments

ARTICLES = "common/treaty_articles/122_seabed_lease.txt"
EVENTS = "events/te_seabed_events.txt"


def article(b):
    return block(read(ARTICLES), f"te_seabed_lease_{b}")


class LeaseArticleTest(unittest.TestCase):
    def test_five_articles(self):
        for b in m.BASINS:
            body = article(b)
            self.assertIn("kind = directed", body)
            self.assertIn("can_be_enforced", body)
            self.assertIn("can_be_renegotiated", body)
            self.assertIn("giftable", body)
            self.assertIn("usage_limit = once_per_treaty", body)
            self.assertIn("maintenance_paid_by = target_country", body)
            self.assertRegex(body, r"required_inputs = \{\s*quantity\s*\}")
            self.assertIn(f"te_seabed_lease_start = {{ B = {b} }}", body)
            self.assertIn(f"te_seabed_can_lease = {{ B = {b} }}", body)
            self.assertIn(f"te_seabed_lease_maintained = {{ B = {b} }}", body)
            # at most the lessor's own claims there (root is the source)
            self.assertIn(f"te_seabed_own_claims_{b}", block(body, "\tquantity_max_value"))

    def test_articles_are_one_template(self):
        pacific = article("pacific")
        for b in m.BASINS[1:]:
            self.assertEqual(article(b), pacific.replace("pacific", b), b)

    def test_hook_guards_the_call(self):
        """The treaty designer re-walks on_entry_into_force every frame with
        scope:article_options unbound (scripting_best_practices.md): the call
        runs only once both parties are saved."""
        hook = strip_comments(block(article("pacific"), "\ton_entry_into_force"))
        self.assertIn("scope:article_options", hook)
        guard = hook.index("exists = scope:te_sb_lessee")
        self.assertLess(hook.index("exists = scope:te_sb_lessor"), hook.index("te_seabed_lease_start"))
        self.assertLess(guard, hook.index("te_seabed_lease_start"))

    def test_one_lease_per_basin_per_lessee(self):
        self.assertIn("te_seabed_lease_src_$B$", block(read(TRIGGERS), "te_seabed_can_lease"))

    def test_antarctic_bar_on_both_sides(self):
        body = block(read(TRIGGERS), "te_seabed_can_lease")
        self.assertIn("te_seabed_southern_barred", body)
        self.assertIn("scope:other_country", body)
        self.assertIn("te_seabed_southern_barred", block(read(TRIGGERS), "te_seabed_lease_maintained"))

    def test_the_lessee_has_not_relinquished(self):
        self.assertIn("te_seabed_relinq_$B$", block(read(TRIGGERS), "te_seabed_can_lease"))

    def test_loc(self):
        loc = english_loc()
        for b in m.BASINS:
            for suffix in ("", "_desc", "_article_short_desc", "_effects_desc"):
                self.assertRegex(loc, rf"(?m)^ te_seabed_lease_{b}{suffix}:0 \"", (b, suffix))
            self.assertIn(f"custom_tooltip_no_bullet = te_seabed_lease_{b}_effects_desc", article(b))


class LeaseStartTest(unittest.TestCase):
    def test_start_dispatches_a_hidden_event(self):
        """The hook only marks the lessee and dispatches; the event a day later
        walks its treaties for the article and its quantity (a walk in the
        hook may not see the treaty yet)."""
        body = strip_comments(block(read(EFFECTS), "te_seabed_lease_start"))
        self.assertIn("te_seabed_lease_due_$B$", body)
        self.assertRegex(body, r"trigger_event = \{ id = te_seabed\.1 days = 1 \}")
        self.assertIn("hidden_effect", body)
        event = block(read(EVENTS), "te_seabed.1")
        self.assertIn("hidden = yes", event)
        self.assertIn("te_seabed_lease_take_up = yes", event)

    def test_entry_moves_the_lessors_own_claims(self):
        body = strip_comments(block(read(EFFECTS), "te_seabed_lease_enter"))
        self.assertIn("input_quantity", body)
        self.assertIn("te_seabed_own_claims_$B$", body)
        for var in ("te_seabed_lease_src_$B$", "te_seabed_lease_n_$B$", "te_seabed_lease_built_$B$",
                    "te_seabed_lease_unused_$B$"):
            self.assertIn(var, body)


class LeaseSharingTest(unittest.TestCase):
    def test_sharing_order(self):
        body = strip_comments(block(read(EFFECTS), "te_seabed_yearly_pass"))
        at = [body.index(s) for s in ("te_seabed_compute_held", "te_seabed_lease_shift_held",
                                      "te_seabed_set_floors", "te_seabed_share_basin = { B = southern }",
                                      "te_seabed_settle_leases", "te_seabed_world_totals = { B = pacific }")]
        self.assertEqual(at, sorted(at))

    def test_consume_after_recording(self):
        body = strip_comments(block(read(EFFECTS), "te_seabed_record_country"))
        self.assertGreater(body.index("te_seabed_lease_consume"), body.index("te_seabed_state_swap_local"))

    def test_the_sharing_counts_shifted_holdings(self):
        """Model: share_held. The floors, their fit, the participants and the
        claims after the sharing read te_seabed_sh_<basin>, not held."""
        effects = strip_comments(read(EFFECTS))
        for name in ("te_seabed_fit_floors", "te_seabed_set_floor", "te_seabed_share_round"):
            body = block(effects, name)
            self.assertIn("te_seabed_sh_$B$", body, name)
            self.assertNotIn("te_seabed_held_$B$", body, name)
        self.assertIn("te_seabed_sh_$B$", block(effects, "te_seabed_share_basin"))
        self.assertIn("te_seabed_own_claims_$B$", block(effects, "te_seabed_set_floor"))

    def test_shift_reads_the_treaty(self):
        """A lease stands while its article is in force from its recorded lessor
        and both sides claim: the treaty is the record (a hook can be skipped)."""
        body = strip_comments(block(read(EFFECTS), "te_seabed_lease_shift_basin"))
        self.assertIn("every_scope_treaty", body)
        self.assertIn("has_type = te_seabed_lease_$B$", body)
        self.assertIn("source_country = scope:te_sb_lessor", body)
        self.assertIn("te_seabed_lease_stands = { B = $B$ }", body)
        stands = block(read(TRIGGERS), "te_seabed_lease_stands")
        self.assertIn("te_seabed_is_claimant = yes", stands)
        self.assertIn("te_seabed_southern_barred", stands)
        self.assertIn("te_seabed_lease_ok_$B$", body)
        self.assertIn("te_seabed_lease_built_$B$", body)

    def test_settle_tops_up_from_own_claims(self):
        body = strip_comments(block(read(EFFECTS), "te_seabed_settle_lease"))
        for name in ("te_seabed_own_claims_$B$", "te_seabed_lease_n_$B$", "te_seabed_lease_ok_$B$",
                     "te_seabed_relinq_$B$", "te_seabed_held_$B$"):
            self.assertIn(name, body)

    def test_the_sharing_re_divides_leased_claims(self):
        body = strip_comments(block(read(EFFECTS), "te_seabed_share_round"))
        self.assertIn("te_seabed_lease_unused_$B$", body)

    def test_relinquish_drops_leased_claims(self):
        self.assertIn("te_seabed_lease_unused_$B$", block(read(EFFECTS), "te_seabed_relinquish"))

    def test_protected_claims_are_own_claims(self):
        """Sponsor's per-claim cost is for protection, and no floor protects
        leased or passed claims (spec § 2.2)."""
        body = block(read(VALUES), "te_seabed_protected_claims")
        for b in m.BASINS:
            self.assertIn(f"te_seabed_own_claims_{b}", body)

    def test_own_claims_values(self):
        values = read(VALUES)
        for b in m.BASINS:
            body = block(values, f"te_seabed_own_claims_{b}")
            self.assertIn(f"te_seabed_unbuilt_{b}", body)
            self.assertIn(f"te_seabed_lease_unused_{b}", body)
            self.assertIn("min = 0", body)


ACTION = "common/diplomatic_actions/te_seabed_administer_claims.txt"


def action():
    return block(read(ACTION), "te_seabed_administer_claims")


class SubjectActionTest(unittest.TestCase):
    """Administer Seabed Claims (spec § 5.2; model: SubjectTest): an overlord's
    pact, no approval, no DLC gate, Raise Payments' liberty desire."""

    def test_action_shape(self):
        body = action()
        self.assertIn("requires_approval = no", body)
        self.assertIn("country_liberty_desire_add = 0.10", body)
        self.assertNotIn("has_dlc_feature", body)
        self.assertIn("subject_type_protectorate", body)
        self.assertIn("subject_type_personal_union", body)
        self.assertRegex(body, r"groups = \{\s*overlord\s*\}")
        self.assertIn("is_direct_subject_of = root", body)
        self.assertIn("te_seabed_is_claimant = yes", body)
        self.assertIn("relations_progress_per_day = -1", body)
        self.assertIn("DIPLOMATIC_PACT_REQUIREMENT_AT_PEACE", body)

    def test_entry_passes_the_claims_at_once(self):
        body = strip_comments(block(action(), "\taccept_effect"))
        self.assertIn("te_seabed_pact_start = yes", body)
        start = strip_comments(block(read(EFFECTS), "te_seabed_pact_start"))
        self.assertIn("te_seabed_pass_built_", start)          # a former pact's counters go
        self.assertIn("te_seabed_pass_basin", start)

    def test_claims_pass_after_the_leases_settle(self):
        body = strip_comments(block(read(EFFECTS), "te_seabed_yearly_pass"))
        self.assertLess(body.index("te_seabed_settle_leases"), body.index("te_seabed_pass_subject_claims"))
        self.assertLess(body.index("te_seabed_pass_subject_claims"), body.index("te_seabed_world_totals = { B = pacific }"))

    def test_the_pact_is_the_record(self):
        stands = strip_comments(block(read(TRIGGERS), "te_seabed_pact_stands"))
        self.assertIn("has_diplomatic_pact = { who = scope:te_sb_over type = te_seabed_administer_claims }", stands)
        self.assertIn("is_direct_subject_of = scope:te_sb_over", stands)
        self.assertIn("te_seabed_pact_ok = { B = $B$ }", stands)
        ok = strip_comments(block(read(TRIGGERS), "te_seabed_pact_ok"))
        self.assertIn("te_seabed_is_claimant = yes", ok)
        self.assertIn("te_seabed_southern_barred", ok)

    def test_the_pass_takes_own_claims_and_spares_a_relinquished_basin(self):
        body = strip_comments(block(read(EFFECTS), "te_seabed_pass_basin"))
        self.assertIn("te_seabed_own_claims_$B$", body)
        self.assertIn("te_seabed_relinq_$B$", body)
        self.assertIn("te_seabed_subj_unused_$B$", body)
        self.assertIn("te_seabed_pass_unused_$B$", body)

    def test_the_sharing_counts_passed_licences_as_the_subjects(self):
        shift = strip_comments(block(read(EFFECTS), "te_seabed_lease_shift_held"))
        self.assertIn("te_seabed_pact_shift_basin = { B = pacific }", shift)
        self.assertLess(shift.index("te_seabed_lease_shift_basin = { B = southern }"),
                        shift.index("te_seabed_pact_shift_basin = { B = pacific }"))
        body = strip_comments(block(read(EFFECTS), "te_seabed_pact_shift_basin"))
        self.assertIn("te_seabed_pass_built_$B$", body)
        self.assertIn("te_seabed_shleft_$B$", body)
        self.assertIn("te_seabed_pact_stands = { B = $B$ }", body)

    def test_settle_drops_a_former_pacts_licences(self):
        body = strip_comments(block(read(EFFECTS), "te_seabed_pact_settle"))
        self.assertIn("te_seabed_pact_stands = { B = $B$ }", body)
        self.assertIn("te_seabed_pass_built_$B$", body)
        self.assertIn("te_seabed_pass_basin = { B = $B$ }", body)

    def test_consume_drains_subject_claims_before_leased(self):
        body = strip_comments(block(read(EFFECTS), "te_seabed_lease_consume_basin"))
        self.assertIn("te_seabed_subj_unused_$B$", body)
        self.assertIn("every_direct_subject", body)
        self.assertIn("te_seabed_pass_built_$B$", body)
        # the lease keeps its claims longest: its part is settled first
        self.assertLess(body.index("te_seabed_lease_unused_$B$"), body.index("te_seabed_subj_unused_$B$"))

    def test_the_sharing_re_divides_passed_claims(self):
        body = strip_comments(block(read(EFFECTS), "te_seabed_share_round"))
        self.assertIn("te_seabed_subj_unused_$B$", body)
        self.assertIn("te_seabed_pass_unused_$B$", body)

    def test_relinquish_drops_passed_claims(self):
        body = strip_comments(block(read(EFFECTS), "te_seabed_relinquish"))
        self.assertIn("te_seabed_subj_unused_$B$", body)
        self.assertIn("every_direct_subject", body)

    def test_ai(self):
        ai = strip_comments(block(action(), "\tai"))
        propose = block(ai, "\t\twill_propose")
        self.assertIn("liberty_desire < 25", propose)
        self.assertIn("te_seabed_own_claims_total > 0", propose)
        self.assertIn("liberty_desire >= 50", block(ai, "\t\twill_break"))

    def test_loc(self):
        loc = english_loc()
        for suffix in ("", "_desc", "_action_notification_name", "_action_notification_desc",
                       "_action_notification_break_name", "_action_notification_break_desc",
                       "_action_propose_name", "_action_break_name", "_pact_desc"):
            self.assertRegex(loc, rf"(?m)^ te_seabed_administer_claims{suffix}:0 \"", suffix)
        desc = re.search(r"(?m)^ te_seabed_administer_claims_desc:0 \"(.*)\"$", loc).group(1)
        self.assertIn("licence", desc)
        self.assertIn("long-haul", desc.lower())


class EventFileTest(unittest.TestCase):
    def test_bom_and_namespace(self):
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), EVENTS), "rb") as f:
            raw = f.read()
        self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))
        self.assertFalse(raw.startswith(b"\xef\xbb\xbf\xef\xbb\xbf"))
        self.assertTrue(re.match(r"namespace = te_seabed\b", raw[3:].decode()))


if __name__ == "__main__":
    unittest.main()
