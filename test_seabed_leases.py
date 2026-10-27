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


class WargoalTest(unittest.TestCase):
    """Review C1: an enforceable article is pressed through vanilla's
    enforce_treaty_article war goal, whose maneuvers and infamy are 0 and leave
    the figures to the article's own wargoal block. Every can_be_enforced
    article in the mod carries one, as every vanilla one does."""

    def test_every_enforceable_article_has_a_wargoal(self):
        folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "common", "treaty_articles")
        missing = []
        for f in sorted(os.listdir(folder)):
            if not f.endswith(".txt"):
                continue
            text = read(os.path.join("common", "treaty_articles", f))
            for name in re.findall(r"^(\w+) = \{", text, re.M):
                body = strip_comments(block(text, name))
                if "can_be_enforced" in body and "wargoal = {" not in body:
                    missing.append(f"{f}: {name}")
        self.assertEqual(missing, [])

    def test_the_lease_war_goal_scales_with_the_claims(self):
        loc = english_loc()
        for b in m.BASINS:
            war = strip_comments(block(article(b), "\twargoal"))
            self.assertIn("contestion_type =", war)
            self.assertIn("execution_priority =", war)
            for part in ("maneuvers", "infamy"):
                self.assertIn("scope:quantity", block(war, f"\t\t{part}"), (b, part))
            for key in re.findall(r'desc = "(\w+)"', war):
                if key.startswith("te_"):
                    self.assertRegex(loc, rf"(?m)^ {key}:0 \"", key)


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

    def test_an_ended_lease_keeps_charging_its_lessor(self):
        """Review C2 (model: lease_charged, settle_leases): the shift charges the
        lessor with built + past while both take part; settle folds an ended
        lease's licences into past and clears a record only when not charged."""
        shift = strip_comments(block(read(EFFECTS), "te_seabed_lease_shift_basin"))
        self.assertIn("te_seabed_lease_past_$B$", shift)
        self.assertIn("set_variable = te_seabed_lease_chg_$B$", shift)
        self.assertIn("scope:te_sb_lessor = { has_variable = te_seabed_part }", shift)
        settle = strip_comments(block(read(EFFECTS), "te_seabed_settle_lease"))
        self.assertIn("te_seabed_lease_chg_$B$", settle)
        self.assertIn("te_seabed_lease_past_$B$", settle)
        self.assertLess(settle.index("te_seabed_lease_chg_$B$"), settle.index("te_seabed_lease_ok_$B$"))

    def test_an_article_never_taken_up_is_adopted(self):
        """Review I1: at the sharing a participant with no record takes up an
        in-force article naming it; one with a record reads its lessor's."""
        shift = strip_comments(block(read(EFFECTS), "te_seabed_lease_shift_basin"))
        self.assertIn("any_scope_treaty", shift)
        self.assertIn("NOT = { exists = scope:te_sb_lessor }", shift)
        self.assertIn("set_variable = { name = te_seabed_lease_src_$B$ value = scope:te_sb_lessor }", shift)
        enter = strip_comments(block(read(EFFECTS), "te_seabed_lease_enter"))
        self.assertIn("source_country = scope:te_sb_lessor", enter)   # a record admits only its own lessor

    def test_the_one_lease_tooltip_names_the_record(self):
        loc = english_loc()
        line = re.search(r"(?m)^ te_seabed_lease_one_tt:0 \"(.*)\"$", loc).group(1)
        self.assertIn("licenses built on", line)

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


class LeaseAiTest(unittest.TestCase):
    """Spec §§ 4, 8: offer claims the source is unlikely to use, request when
    the target's room is near 0 and Tech-Critical Metals sell above base."""

    def test_ai_blocks(self):
        loc = english_loc()
        for b in m.BASINS:
            ai = strip_comments(block(article(b), "\tai"))
            self.assertRegex(ai, r"article_ai_usage = \{\s*offer request\s*\}")
            chance = block(ai, "\t\tevaluation_chance")
            self.assertIn(f"te_seabed_ai_lease_offer_value_{b}", chance)
            self.assertIn(f"te_seabed_ai_lease_request_value_{b}", chance)
            self.assertNotIn("scope:", chance)                 # root only (treaty_evaluation_scope_audit)
            self.assertIn(f"te_seabed_ai_lease_spare_{b}", block(ai, "\t\tquantity_input_value"))
            self.assertIn("proposal_weight", ai)
            self.assertIn("wargoal_score_multiplier", ai)
            descs = re.findall(r'desc = "(\w+)"', block(ai, "\t\tinherent_accept_score"))
            self.assertGreaterEqual(len(descs), 3, b)
            for key in descs:
                self.assertRegex(loc, rf"(?m)^ {key}:0 \"", key)

    def test_the_lessor_weighs_the_quantity(self):
        """Review I3: an AI lessor refuses to lease more than it can spare: the
        claims asked above its spare cost 5 points each, so 10 over outweighs
        the spare's largest pull (+30) and the base reluctance."""
        loc = english_loc()
        for b in m.BASINS:
            score = strip_comments(block(block(article(b), "\tai"), "\t\tinherent_accept_score"))
            giver = score[score.index("scope:source_country ?= this"):score.index("scope:target_country ?= this")]
            self.assertIn("scope:article.input_quantity", giver)
            self.assertIn(f"subtract = te_seabed_ai_lease_spare_{b}", giver)
            self.assertIn('desc = "te_seabed_ai_lease_too_many"', giver)
            self.assertIn("multiply = 5", giver)
        self.assertRegex(loc, r'(?m)^ te_seabed_ai_lease_too_many:0 "')

    def test_offer_follows_the_spec(self):
        """Claims it is unlikely to use: none queued, or claims well above its
        construction pace (spec § 4)."""
        values = read("common/script_values/te_global_commons_seabed_ai_values.txt")
        for b in m.BASINS:
            spare = block(values, f"te_seabed_ai_lease_spare_{b}")
            self.assertIn(f"te_seabed_own_claims_{b}", spare)
            self.assertIn("te_seabed_queued_total_disp", spare)
            self.assertIn("te_seabed_ai_lease_pace_months", spare)
            self.assertIn(f"te_seabed_ai_lease_spare_{b}", block(values, f"te_seabed_ai_lease_offer_value_{b}"))
            request = block(values, f"te_seabed_ai_lease_request_value_{b}")
            self.assertIn("te_seabed_room", request)
            self.assertIn("te_seabed_ai_tech_metals_premium", request)
            self.assertIn(f"te_seabed_home_{b}", request)

    def test_sponsor_pull_counts_protected_claims(self):
        values = read("common/script_values/te_global_commons_seabed_ai_values.txt")
        self.assertIn("te_seabed_protected_claims", block(values, "te_seabed_ai_will_sponsor"))


class LeasePanelTest(unittest.TestCase):
    """The Seabed tab says what is leased, passed and built on leases."""

    def test_overview_hovers(self):
        loc = english_loc()
        claims = re.search(r"(?m)^ te_seabed_ov_claims_tt:0 \"(.*)\"$", loc).group(1)
        self.assertIn("'te_seabed_ov_claims_borrowed'", claims)
        borrowed = re.search(r"(?m)^ te_seabed_ov_claims_borrowed:0 \"(.*)\"$", loc).group(1)
        self.assertIn("te_seabed_leased_claims_disp", borrowed)
        self.assertIn("te_seabed_passed_claims_disp", borrowed)
        licences = re.search(r"(?m)^ te_seabed_ov_licences_tt:0 \"(.*)\"$", loc).group(1)
        self.assertIn("'te_seabed_ov_licences_leased'", licences)
        values = read(VALUES)
        for b in m.BASINS:
            self.assertIn(f"te_seabed_lease_unused_{b}", block(values, "te_seabed_leased_claims_disp"))
            self.assertIn(f"te_seabed_subj_unused_{b}", block(values, "te_seabed_passed_claims_disp"))
            self.assertIn(f"te_seabed_lease_built_{b}", block(values, "te_seabed_lease_built_disp"))

    def test_a_lessor_sees_what_it_lent(self):
        """Review I5: a lessor's (or former subject's) claims shrink at each
        sharing by what its leases take and what others built on its claims;
        the claims hover says so when either is above 0."""
        loc = english_loc()
        claims = re.search(r"(?m)^ te_seabed_ov_claims_tt:0 \"(.*)\"$", loc).group(1)
        self.assertIn("'te_seabed_ov_claims_lent'", claims)
        lent = re.search(r"(?m)^ te_seabed_ov_claims_lent:0 \"(.*)\"$", loc).group(1)
        self.assertIn("te_seabed_leased_out_disp", lent)
        self.assertIn("te_seabed_charged_disp", lent)
        values = read(VALUES)
        for b in m.BASINS:
            self.assertIn(f"te_seabed_leased_out_{b}", block(values, "te_seabed_leased_out_disp"))
            self.assertIn(f"te_seabed_charged_{b}", block(values, "te_seabed_charged_disp"))
        effects = strip_comments(read(EFFECTS))
        self.assertIn("te_seabed_leased_out_pacific", block(effects, "te_seabed_settle_leases"))
        self.assertIn("te_seabed_leased_out_$B$", block(effects, "te_seabed_settle_lease"))
        self.assertIn("te_seabed_leased_out_$B$", block(effects, "te_seabed_lease_enter"))
        self.assertIn("te_seabed_charged_$B$", block(effects, "te_seabed_lease_shift_basin"))
        self.assertIn("te_seabed_charged_$B$", block(effects, "te_seabed_pact_shift_basin"))
        self.assertIn("te_seabed_charged_pacific", block(effects, "te_seabed_lease_shift_held"))

    def test_how_section(self):
        gui = read("gui/te_seabed_widgets.gui")
        self.assertLess(gui.index('"te_seabed_how_claims"'), gui.index('"te_seabed_how_sub_leases"'))
        self.assertLess(gui.index('"te_seabed_how_leases"'), gui.index('"te_seabed_how_sub_policy"'))
        loc = english_loc()
        how = re.search(r"(?m)^ te_seabed_how_leases:0 \"(.*)\"$", loc).group(1)
        for word in ("Lease Seabed Claims", "Administer Seabed Claims", "war"):
            self.assertIn(word, how)


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
        self.assertIn("te_seabed_pact_charge_to = yes", start)
        self.assertIn("te_seabed_pass_basin", start)
        # counters go only when they charge another overlord (review C2)
        charge = strip_comments(block(read(EFFECTS), "te_seabed_pact_charge_to"))
        self.assertIn("var:te_seabed_pass_to ?= { this = scope:te_sb_over }", charge)
        self.assertIn("te_seabed_pass_built_pacific", charge)
        self.assertIn("set_variable = { name = te_seabed_pass_to value = scope:te_sb_over }", charge)

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
        # charged while both take part, pact or no pact (review C2)
        self.assertNotIn("te_seabed_pact_stands", body)
        walk = strip_comments(block(read(EFFECTS), "te_seabed_lease_shift_held"))
        self.assertIn("var:te_seabed_pass_to ?= { save_scope_as = te_sb_over }", walk)
        self.assertIn("set_variable = te_seabed_pass_chg", walk)

    def test_settle_keeps_a_record_while_both_take_part(self):
        body = strip_comments(block(read(EFFECTS), "te_seabed_pass_subject_claims"))
        self.assertIn("te_seabed_pass_chg", body)                  # set by the shift: both take part
        self.assertIn("te_seabed_pact_clear = yes", body)           # cleared only when they don't
        self.assertIn("remove_variable = te_seabed_pass_to", block(read(EFFECTS), "te_seabed_pact_clear"))
        settle = strip_comments(block(read(EFFECTS), "te_seabed_pact_settle"))
        self.assertIn("te_seabed_pact_stands = { B = $B$ }", settle)
        self.assertIn("te_seabed_pact_charge_to = yes", settle)
        self.assertIn("te_seabed_pass_basin = { B = $B$ }", settle)

    def test_consume_drains_subject_claims_before_leased(self):
        body = strip_comments(block(read(EFFECTS), "te_seabed_lease_consume_basin"))
        self.assertIn("te_seabed_subj_unused_$B$", body)
        # booked on the subjects whose counters charge this country (review C2), not
        # its direct subjects: a former subject's passed claims are still here
        self.assertIn("var:te_seabed_pass_to ?= { this = scope:te_sb_cons }", body)
        self.assertNotIn("every_direct_subject", body)
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
        self.assertIn("te_seabed_pass_to", body)

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
        self.assertIn("license", desc.lower())
        self.assertIn("long-haul", desc.lower())


class SelfCheckTest(unittest.TestCase):
    """CLAUDE.md, in-game checks: the engine reads the leases and the pact rest
    on get a once-a-game TE_SELF_CHECK line, listed in the play-test list."""

    def test_lease_entry(self):
        """Review I2: logged by the caller with literal basin names ($B$ in a
        debug_log string is mangled, scripting_best_practices.md), and OK only
        for a quantity of at least 1."""
        body = block(read(EFFECTS), "te_seabed_lease_take_up")
        for b in m.BASINS:
            self.assertIn(f"TE_SELF_CHECK OK seabed_lease_entry basin={b} ", body)
            self.assertIn(f"TE_SELF_CHECK BROKEN seabed_lease_entry basin={b} ", body)
        self.assertIn("te_seabed_selfcheck_lease_done", body)          # OK once a game
        enter = strip_comments(block(read(EFFECTS), "te_seabed_lease_enter"))
        self.assertIn("scope:te_sb_found = { input_quantity > 0 }", enter)

    def test_no_parameter_in_a_log_string(self):
        for rel in (EFFECTS, EVENTS):
            for line in read(rel).split("\n"):
                if "debug_log =" in line:
                    self.assertNotIn("$", line.split("=", 1)[1], line.strip()[:80])

    def test_pact_read(self):
        start = strip_comments(block(read(EFFECTS), "te_seabed_pact_start"))
        self.assertRegex(start, r"trigger_event = \{ id = te_seabed\.2 days = 1 \}")
        event = block(read(EVENTS), "te_seabed.2")
        self.assertIn("hidden = yes", event)
        self.assertIn("TE_SELF_CHECK OK seabed_pact_read", event)
        self.assertIn("TE_SELF_CHECK BROKEN seabed_pact_read", event)
        self.assertIn("has_diplomatic_pact = { who = scope:te_sb_over type = te_seabed_administer_claims }", event)
        self.assertIn("te_seabed_selfcheck_pact_done", event)

    def test_listed(self):
        doc = read("docs/testing/global-commons-playtest.md")
        for name in ("seabed_lease_entry", "seabed_pact_read"):
            self.assertIn(f"TE_SELF_CHECK … {name}", doc)


class EventFileTest(unittest.TestCase):
    def test_bom_and_namespace(self):
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), EVENTS), "rb") as f:
            raw = f.read()
        self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))
        self.assertFalse(raw.startswith(b"\xef\xbb\xbf\xef\xbb\xbf"))
        self.assertTrue(re.match(r"namespace = te_seabed\b", raw[3:].decode()))


if __name__ == "__main__":
    unittest.main()
