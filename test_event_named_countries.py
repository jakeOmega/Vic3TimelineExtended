"""The country an event names or acts on is the one its text says (#1617).

Four events picked or addressed a country by a looser test than the one their
text rests on, and one option's effects fell on the wrong side of its name:

- The Partition Question (decolonization_events.16) found a neighbor of shared
  heritage in its trigger, then saved any neighbor of that state.
- The Nationalization Question (decolonization_events.15) saved a random
  foreign owner as "the biggest".
- A Sister Asks to Be Absorbed (irredentism.8) could ask a bloc leader to
  bless its own proposal of union.
- A demand for a state (irredentism.2) arrived five days after Event 1 tested
  that a play could be opened, and tested nothing itself.
- The Frozen Program (treaty_article_events.8): the promise to the hawks
  angered the hawks, and "the price of peace" did not.

Structural tests on the script text; no game or server needed.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8-sig")


def strip_comments(text):
    return re.sub(r"#[^\n]*", "", text)


def block(text, name):
    """The body of the top-level `name = { ... }` block."""
    m = re.search(r"^" + re.escape(name) + r"\s*=\s*\{", text, re.M)
    if m is None:
        raise AssertionError(f"no block {name}")
    depth, i = 1, m.end()
    while depth:
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        i += 1
    return text[m.end():i - 1]


def inner(text, opener):
    """The body of the first `opener` block inside text (`opener` ends in `{`)."""
    start = text.index(opener) + len(opener)
    depth, i = 1, start
    while depth:
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        i += 1
    return text[start:i - 1]


def option(body, name):
    """The body of the event option whose name is `name`."""
    for m in re.finditer(r"\n\toption = \{", body):
        opt = inner(body[m.start():], "\n\toption = {")
        if re.search(r"\bname = " + re.escape(name) + r"\s", opt):
            return opt
    raise AssertionError(f"no option {name}")


def squeeze(text):
    return re.sub(r"\s+", " ", text).strip()


DECOL = strip_comments(read("events/decolonization_events.txt"))
DECOL_EFFECTS = strip_comments(read("common/scripted_effects/decolonization.txt"))
IRR = strip_comments(read("events/irredentism_events.txt"))
ON_ACTIONS = strip_comments(read("common/on_actions/extra_on_actions.txt"))
TREATY = strip_comments(read("events/treaty_article_events.txt"))


class PartitionNeighborIsTheOneTheTriggerFound(unittest.TestCase):
    def setUp(self):
        self.event = block(DECOL, "decolonization_events.16")

    def owner_test(self, text):
        """The first `owner = { ... }` test inside text, whitespace squeezed."""
        return squeeze(inner(text, "owner = {"))

    def test_saved_neighbor_passes_the_triggers_owner_test(self):
        trigger = inner(self.event, "\n\ttrigger = {")
        immediate = inner(self.event, "\n\timmediate = {")
        picked = inner(immediate, "random_neighbouring_state = {")
        self.assertIn("save_scope_as = partition_neighbor", picked)
        wanted = self.owner_test(inner(trigger, "any_neighbouring_state = {"))
        self.assertIn("shares_heritage_trait_group_with_any_primary_culture = root", wanted)
        self.assertEqual(wanted, self.owner_test(inner(picked, "limit = {")))

    def test_state_is_picked_by_the_same_owner_test(self):
        trigger = inner(self.event, "\n\ttrigger = {")
        immediate = inner(self.event, "\n\timmediate = {")
        state_limit = inner(inner(immediate, "random_scope_state = {"), "limit = {")
        self.assertEqual(
            self.owner_test(inner(trigger, "any_neighbouring_state = {")),
            self.owner_test(state_limit),
        )


class NationalizationNamesTheLargestOwner(unittest.TestCase):
    def setUp(self):
        self.event = block(DECOL, "decolonization_events.15")
        self.helper = block(DECOL_EFFECTS, "decol_save_biggest_foreign_owner")
        self.band = block(DECOL_EFFECTS, "decol_save_foreign_owner_above")

    def test_event_saves_through_the_helper(self):
        immediate = inner(self.event, "\n\timmediate = {")
        self.assertIn("decol_save_biggest_foreign_owner = yes", immediate)
        self.assertNotIn("random_country", immediate)

    def test_bands_run_down_to_the_triggers_threshold(self):
        shares = [float(s) for s in re.findall(
            r"decol_save_foreign_owner_above = \{ SHARE = ([\d.]+) \}", self.helper)]
        self.assertGreaterEqual(len(shares), 3)
        self.assertEqual(shares, sorted(shares, reverse=True))
        self.assertEqual(len(shares), len(set(shares)))
        trigger = inner(self.event, "\n\ttrigger = {")
        floor = float(re.search(r"value > ([\d.]+)", trigger).group(1))
        # The last band is the trigger's own test, so an event that fires
        # always has an owner to name.
        self.assertEqual(shares[-1], floor)

    def test_scope_is_cleared_before_the_first_band(self):
        first = self.helper.strip().splitlines()[0].strip()
        self.assertEqual(first, "clear_saved_scope = biggest_foreign_owner")

    def test_a_band_saves_only_when_no_higher_band_did(self):
        band = squeeze(self.band)
        self.assertIn("limit = { NOT = { exists = scope:biggest_foreign_owner } }", band)
        self.assertIn("value > $SHARE$", band)
        self.assertIn("save_scope_as = biggest_foreign_owner", band)
        # The same owners the trigger counts.
        self.assertIn("country_rank >= rank_value:minor_power", band)
        self.assertIn("NOT = { this = root }", band)


class BlocLeaderIsNotAskedToBlessItsOwnProposal(unittest.TestCase):
    def test_dispatch_skips_a_proposer_that_leads_our_bloc(self):
        dispatch = block(ON_ACTIONS, "irredentism_bloc_approval_on_action")
        branch = dispatch[dispatch.index("has_modifier = irr_open_to_union_modifier"):]
        proposer = squeeze(inner(branch, "var:irr_union_proposer ?= {"))
        self.assertIn(
            "NOT = { AND = { is_power_bloc_leader = yes is_in_same_power_bloc = ROOT } }",
            proposer,
        )

    def test_event_does_not_reach_a_leader_who_proposed(self):
        trigger = squeeze(inner(block(IRR, "irredentism.8"), "\n\ttrigger = {"))
        self.assertIn("NOT = { scope:irr_unifier = { this = root } }", trigger)

    def test_such_a_union_needs_no_blessing(self):
        # Why skipping is enough: the peace check's target side passes a
        # target whose bloc the unifier leads.
        check = squeeze(block(
            strip_comments(read("common/scripted_triggers/irredentism_triggers.txt")),
            "irredentist_bloc_check_peace"))
        self.assertIn(
            "AND = { is_in_same_power_bloc = ROOT ROOT = { is_power_bloc_leader = yes } }",
            check,
        )


class DemandArrivesOnlyWhileAPlayCanOpen(unittest.TestCase):
    def setUp(self):
        self.event = block(IRR, "irredentism.2")
        self.trigger = squeeze(inner(self.event, "\n\ttrigger = {"))

    def test_trigger_repeats_the_senders_tests(self):
        # The option's own trigger (two tabs), not an ai_chance modifier's.
        sender = squeeze(inner(option(block(IRR, "irredentism.1"), "irredentism.1.c"),
                               "\n\t\ttrigger = {"))
        self.assertIn("exists = scope:irr_demanded_state", sender)
        self.assertIn("exists = scope:irr_demanded_state", self.trigger)
        # Both countries, as in Event 1 option C.
        self.assertEqual(sender.count("is_diplomatic_play_committed_participant = no"), 2)
        self.assertEqual(self.trigger.count("is_diplomatic_play_committed_participant = no"), 2)
        self.assertIn("scope:irr_unifier = {", self.trigger)

    def test_the_state_is_still_ours_to_cede(self):
        self.assertIn("scope:irr_demanded_state = { owner = { this = root } }", self.trigger)

    def test_refusal_still_opens_the_play(self):
        refuse = option(self.event, "irredentism.2.a")
        self.assertIn("create_diplomatic_play", refuse)
        self.assertIn("type = dp_return_state", refuse)


class FrozenProgramPromiseDoesNotAngerTheHawks(unittest.TestCase):
    HAWKS = ("ig_armed_forces", "ig_industrialists")

    def setUp(self):
        event = block(TREATY, "treaty_article_events.8")
        self.accept = option(event, "treaty_article_events.8.a")
        self.promise = option(event, "treaty_article_events.8.b")

    def test_promise_carries_no_disapproval(self):
        self.assertNotIn("ig_approval_negative_modifier", self.promise)

    def test_refusing_them_is_what_angers_them(self):
        for ig in self.HAWKS:
            self.assertRegex(
                squeeze(self.accept),
                r"IG = " + ig + r" MODIFIER = ig_approval_negative_modifier",
            )

    def test_each_option_keeps_a_cost(self):
        # The promise leaves the question open, so its tension lasts longer.
        def days(opt):
            body = squeeze(inner(opt, "add_modifier = {"))
            self.assertIn("name = nuclear_freeze_tension_modifier", body)
            return re.search(r"days = (\w+)", body).group(1)

        self.assertEqual(days(self.accept), "short_modifier_time")
        self.assertEqual(days(self.promise), "normal_modifier_time")


if __name__ == "__main__":
    unittest.main()
