"""Covert Warfare: watching a caught operation.

A caught operation no longer goes straight to the attacker's exposure event.
A defender with a covert service decides first (covert_warfare.3 for a player,
a chance at roll time for the AI): expose it now, or let it run, unseen, and
grow its own network inside the attacker while it does. A watched operation is
recorded on the defender (one record container per operation) and can be
exposed later; every exposure still goes through covert_warfare.1, one at a
time per attacker.

What these tests pin is the shape an engine-silent mistake would hide in: the
roll skips what is already known or awaiting a decision; every path that opens
covert_warfare.1 takes the one-exposure-in-flight lock first; no record
outlives its operation (every path that destroys an operation forgets its
record); watched operations count towards the defender's network; and the
watchdogs that undo a lock or a pending decision whose event never ran.

Run: python3 -m unittest test_covert_watch -v
"""

import re
import unittest

from test_covert_exposure_tiers import (
    EVENTS,
    VALUES,
    _block_span,
    _innermost_enclosing,
)
from test_covert_op_registry import (
    CUSTOM_LOC,
    EFFECTS,
    FRIENDLY,
    HOSTILE_TYPES,
    OPS,
    ROOT,
    TRIGGERS,
    _loc,
    _text,
    _top_level_block,
)

JE = ROOT / "common/journal_entries/je_covert_warfare.txt"

# Every type a defender can watch (HOSTILE_TYPES). Counterintelligence Support
# is a friendly operation: never rolled, so never caught and never watched.
HOSTILE_CODES = {t: code for t, code, _, _, _ in OPS if t not in FRIENDLY}


def strip_comments(text):
    return "\n".join(line.split("#", 1)[0] for line in text.splitlines())


def scripted_effect(name):
    return strip_comments(_top_level_block(_text(EFFECTS), name + " = {"))


def scripted_trigger(name):
    return strip_comments(_top_level_block(_text(TRIGGERS), name + " = {"))


def script_value(name):
    return strip_comments(_top_level_block(_text(VALUES), name + " = {"))


def event(suffix):
    return strip_comments(_top_level_block(_text(EVENTS), "covert_warfare%s = {" % suffix))


def event_block(ev, name):
    start, end = _block_span(ev, ev.index("\n\t%s = {" % name))
    return ev[start:end]


def option(ev, name):
    return str(_innermost_enclosing(ev, "name = %s" % name, "option = {"))


def je_pulse():
    body = strip_comments(_text(JE))
    return body[body.index("on_monthly_pulse = {"):]


def _enclosing_top_level(body, at):
    """The top-level `name = { ... }` entry (scripted effect or event) that
    holds position `at`: from the last unindented opener before it to its
    unindented close."""
    start = body.rfind("\n", 0, at)
    while True:
        line_start = body.rfind("\n", 0, start) + 1
        line = body[line_start:body.find("\n", line_start)]
        if re.match(r"^[A-Za-z0-9_.]+ = \{", line):
            break
        start = line_start - 1
        if start < 0:
            raise AssertionError("no top-level entry encloses %d" % at)
    end = body.index("\n}\n", at) + 3
    return body[line_start:end]


def trigger_sites(event_id):
    """(path, enclosing entry) for every place that opens `event_id`, outside
    the console harness. Comments are stripped first, so a commented-out call
    is not a site."""
    pattern = re.compile(
        r"trigger_event = (?:\{\s*id = %s\b|%s\b)" % (re.escape(event_id), re.escape(event_id))
    )
    sites = []
    for path in sorted(list(ROOT.glob("common/**/*.txt")) + list(ROOT.glob("events/*.txt"))):
        if path.name.startswith("te_debug"):
            continue
        body = strip_comments(path.read_text(encoding="utf-8-sig"))
        for m in pattern.finditer(body):
            sites.append((path.name, _enclosing_top_level(body, m.start())))
    return sites


class Triggers(unittest.TestCase):
    def test_exposure_in_flight_reads_both_halves_of_the_lock(self):
        body = scripted_trigger("covert_exposure_in_flight")
        self.assertIn("has_variable = iw_burned_type_code", body)
        self.assertIn("has_variable = iw_expose_inflight", body)
        self.assertIn("OR = {", body)

    def test_can_watch_needs_the_service(self):
        body = scripted_trigger("covert_can_watch")
        self.assertIn("has_game_rule = covert_warfare_enabled", body)
        self.assertIn("has_journal_entry = je_covert_warfare", body)

    def test_hostile_excludes_counterintelligence_support(self):
        self.assertIn(
            "NOT = { has_tag = iw_op_counterintel_support }",
            scripted_trigger("covert_op_is_hostile"),
        )


class Roll(unittest.TestCase):
    def test_roll_skips_known_pending_and_friendly(self):
        body = scripted_effect("covert_ops_roll_detection_all")
        for s in ("has_variable = iw_known", "has_variable = iw_catch_pending", "covert_op_is_hostile = yes"):
            self.assertIn(s, body)
        # ...inside the walk's limit, so they decide what is rolled at all.
        walk = str(_innermost_enclosing(body, "chance = covert_op_roll_chance", "every_in_list = {"))
        start, end = _block_span(walk, walk.index("limit = {"))
        limit = walk[start:end]
        for s in ("NOT = { has_variable = iw_known }", "NOT = { has_variable = iw_catch_pending }",
                  "covert_op_is_hostile = yes"):
            self.assertIn(s, limit)

    def test_roll_waits_while_an_exposure_is_in_flight(self):
        body = scripted_effect("covert_ops_roll_detection_all")
        outer = str(_innermost_enclosing(body, "every_in_list = {", "if = {"))
        start, end = _block_span(outer, outer.index("limit = {"))
        self.assertIn("NOT = { covert_exposure_in_flight = yes }", outer[start:end])

    def test_every_event_1_trigger_checks_lockout(self):
        sites = trigger_sites("covert_warfare.1")
        self.assertTrue(sites)
        for path, ctx in sites:
            self.assertIn("covert_exposure_in_flight", ctx, path)
            # The lock is taken before the event is opened: trigger_event
            # may not run the event's immediate within the calling effect.
            self.assertLess(
                ctx.index("name = iw_expose_inflight value = 1"),
                ctx.index("covert_warfare.1"),
                path,
            )

    def test_one_site_opens_event_1(self):
        # covert_exposure_fire is the only place; everything else calls it.
        sites = trigger_sites("covert_warfare.1")
        self.assertEqual(len(sites), 1, [p for p, _ in sites])
        self.assertTrue(sites[0][1].startswith("covert_exposure_fire = {"))

    def test_defender_branch(self):
        body = scripted_effect("covert_ops_roll_detection_all")
        self.assertIn("covert_can_watch = yes", body)
        self.assertIn("covert_warfare.3", body)
        self.assertIn("is_player = no", body)
        # A defender without a service: today's flow, straight to .1.
        self.assertGreaterEqual(body.count("covert_exposure_fire = yes"), 2)

    def test_attacker_saved_before_either_dispatch(self):
        # The operation carries no operator; .3 and covert_watch_start read
        # the attacker from this scope.
        body = scripted_effect("covert_ops_roll_detection_all")
        saved = body.index("save_scope_as = iw_catcher_attacker")
        self.assertLess(saved, body.index("covert_warfare.3"))
        self.assertLess(saved, body.index("covert_watch_ai_decide = yes"))

    def test_player_decision_marks_the_operation_pending_first(self):
        body = scripted_effect("covert_ops_roll_detection_all")
        self.assertLess(
            body.index("name = iw_catch_pending value = 1"),
            body.index("trigger_event = { id = covert_warfare.3 }"),
        )

    def test_stale_pick_is_cleared(self):
        body = scripted_effect("covert_ops_roll_detection_all")
        self.assertLess(
            body.index("clear_saved_scope = iw_burned_op"),
            body.index("save_scope_as = iw_burned_op"),
        )

    def test_ai_decision_rolls_the_named_chance_in_the_defender(self):
        body = scripted_effect("covert_watch_ai_decide")
        roll = str(_innermost_enclosing(body, "chance = covert_ai_watch_chance", "random = {"))
        self.assertIn("save_scope_as = iw_caught_op", roll)
        self.assertIn("covert_watch_start = yes", roll)
        # Staged before the chance reads them, removed after.
        for var in ("iw_watch_stage_code", "iw_watch_stage_net", "iw_watch_stage_friend"):
            self.assertLess(body.index("name = %s" % var), body.index("chance = covert_ai_watch_chance"))
            self.assertIn("remove_variable = %s" % var, body)
        self.assertIn("covert_is_friend = { TARGET = scope:iw_catcher_attacker }", body)


class Records(unittest.TestCase):
    def test_destroy_forgets_record(self):
        self.assertIn("covert_watch_forget", scripted_effect("covert_op_destroy"))
        self.assertIn("covert_watch_forget", scripted_effect("covert_op_sync"))

    def test_forget_runs_before_the_container_goes(self):
        for name in ("covert_op_destroy", "covert_op_sync"):
            body = scripted_effect(name)
            self.assertLess(body.index("covert_watch_forget"), body.rindex("destroy_container = yes"), name)
            self.assertIn("has_variable = iw_known", body, name)

    def test_record_dispatch_covers_every_hostile_type(self):
        body = scripted_effect("covert_watch_start")
        for t in HOSTILE_TYPES:
            self.assertIn(f"iw_op_{t}", body)
            self.assertRegex(
                body,
                r"has_tag = iw_op_%s \} \}\s*covert_watch_record_create = \{ TYPE = %s \}" % (t, t),
            )

    def test_start_marks_the_operation_and_seeds_the_network(self):
        body = scripted_effect("covert_watch_start")
        self.assertIn("set_variable = { name = iw_known value = 1 }", body)
        self.assertIn("remove_variable = iw_catch_pending", body)
        self.assertIn("covert_net_create = { TARGET = scope:iw_catcher_attacker }", body)
        self.assertIn("clear_saved_scope = iw_new_rec", body)

    def test_record_shape(self):
        body = scripted_effect("covert_watch_record_create")
        self.assertIn("tags = { iw_known_rec iw_known_$TYPE$ }", body)
        self.assertIn("parent = scope:iw_watch_defender", body)
        for var in ("iw_attacker", "iw_attacker_capital", "iw_type_code", "iw_watch_months"):
            self.assertIn("name = %s" % var, body)
        self.assertIn("add_to_variable_list = { name = iw_known_ops target = scope:iw_new_rec }", body)
        self.assertIn("exists = scope:iw_new_rec", body)
        # One record per (attacker, type): an older one is forgotten first.
        self.assertLess(body.index("covert_watch_forget"), body.index("create_container"))

    def test_forget_removes_before_destroy(self):
        body = scripted_effect("covert_watch_forget")
        self.assertIn("has_tag = iw_known_$TYPE$", body)
        self.assertIn("var:iw_attacker ?= $ATTACKER$", body)
        self.assertLess(
            body.index("remove_list_variable = { name = iw_known_ops"),
            body.index("destroy_container = yes"),
        )


class Exposure(unittest.TestCase):
    def test_fire_takes_the_lock_then_opens_event_1(self):
        body = scripted_effect("covert_exposure_fire")
        self.assertIn("NOT = { covert_exposure_in_flight = yes }", body)
        self.assertLess(
            body.index("set_variable = { name = iw_expose_inflight value = 1 }"),
            body.index("trigger_event = { id = covert_warfare.1 }"),
        )

    def test_expose_record_waits_when_locked_and_fires_inside_the_lookup(self):
        body = scripted_effect("covert_watch_expose_record")
        self.assertIn("covert_exposure_in_flight = yes", body)
        self.assertIn("name = iw_expose_ordered value = 1", body)
        pick = str(_innermost_enclosing(body, "save_scope_as = iw_burned_op", "random_in_list = {"))
        self.assertIn("variable = iw_ops", pick)
        self.assertIn("covert_watch_op_matches = { DEFENDER = scope:iw_expose_defender", pick)
        self.assertIn("covert_exposure_fire = yes", pick)
        self.assertIn("name = iw_expose_sent value = 1", pick)
        # Only when the attacker is free; otherwise the order waits.
        guard = str(_innermost_enclosing(body, "random_in_list = {", "if = {"))
        self.assertIn("NOT = { covert_exposure_in_flight = yes }", guard)

    def test_watched_operation_is_matched_by_target_code_and_flag(self):
        body = scripted_trigger("covert_watch_op_matches")
        self.assertIn("has_variable = iw_known", body)
        self.assertIn("var:iw_target ?= $DEFENDER$", body)
        self.assertIn("var:iw_type_code = $CODE$", body)
        # The code is staged on a country, never compared through the
        # container's own var: or PREV inside a list.
        for name in ("covert_watch_expose_record", "covert_watch_monthly", "covert_nets_sync"):
            for call in re.findall(r"covert_watch_op_matches = \{[^}]*\}", scripted_effect(name)):
                self.assertRegex(call, r"CODE = scope:\w+\.var:\w+_staging", name)

    def test_expose_record_forgets_a_record_with_no_operation(self):
        body = scripted_effect("covert_watch_expose_record")
        self.assertIn("remove_list_variable = { name = iw_known_ops", body)
        self.assertLess(
            body.index("remove_list_variable = { name = iw_known_ops"),
            body.index("destroy_container = yes"),
        )


class Events(unittest.TestCase):
    def test_events_exist(self):
        self.assertTrue(event(".3") and event(".4"))
        self.assertIn("hidden = yes", event(".4"))
        self.assertIn("event_image", event(".3"))

    def test_decision_event_shape(self):
        ev = event(".3")
        self.assertIn('texture = "gfx/event_pictures/espionage_dead_drop.dds"', ev)
        self.assertIn("duration = 3", ev)
        self.assertIn("default_option = yes", option(ev, "covert_warfare.3.a"))
        trigger = event_block(ev, "trigger")
        self.assertIn("exists = scope:iw_burned_op", trigger)
        self.assertIn("exists = scope:iw_catcher_attacker", trigger)
        immediate = event_block(ev, "immediate")
        self.assertIn("save_scope_as = iw_caught_op", immediate)
        self.assertIn("name = iw_caught_type_code", immediate)
        self.assertNotIn("covert_warfare.2", ev)  # no 24-month cooldown in the way

    def test_options_guard_the_operation_and_say_what_they_do(self):
        ev = event(".3")
        for name in ("covert_warfare.3.a", "covert_warfare.3.b"):
            opt = option(ev, name)
            self.assertIn("exists = scope:iw_caught_op", opt, name)
            self.assertIn("custom_tooltip = covert_warfare.3.gone_tt", opt, name)
            self.assertIn("hidden_effect = {", opt, name)
        self.assertIn("custom_tooltip = covert_warfare.3.b_tt", option(ev, "covert_warfare.3.b"))
        self.assertIn("covert_watch_start = yes", option(ev, "covert_warfare.3.b"))

    def test_expose_option_takes_the_lock_or_waits(self):
        opt = option(event(".3"), "covert_warfare.3.a")
        self.assertIn("covert_exposure_in_flight = yes", opt)
        self.assertIn("covert_exposure_fire = yes", opt)
        # Locked: watch now, with the exposure ordered, and look again once
        # the open covert_warfare.1 (up to a month) has closed.
        self.assertIn("name = iw_expose_ordered value = 1", opt)
        self.assertIn("trigger_event = { id = covert_warfare.4 days = 4 }", opt)

    def test_after_clears_the_pending_mark(self):
        after = event_block(event(".3"), "after")
        self.assertIn("scope:iw_caught_op", after)
        self.assertIn("remove_variable = iw_catch_pending", after)

    def test_desc_names_attacker_and_operation(self):
        loc = _loc()
        text = loc["covert_warfare.3.d"]
        self.assertIn("[SCOPE.sCountry('iw_catcher_attacker').GetName]", text)
        self.assertIn("GetCustom('covert_caught_type_name')", text)
        for key in ("covert_warfare.3.t", "covert_warfare.3.f", "covert_warfare.3.a", "covert_warfare.3.b",
                    "covert_warfare.3.a_tt", "covert_warfare.3.a_wait_tt", "covert_warfare.3.b_tt",
                    "covert_warfare.3.gone_tt"):
            self.assertIn(key, loc, key)

    def test_let_it_run_tooltip_says_what_watching_does(self):
        text = _loc()["covert_warfare.3.b_tt"].lower()
        for phrase in ("not told", "keeps", "network", "expose"):
            self.assertIn(phrase, text)

    def test_order_event_walks_ordered_records(self):
        immediate = event_block(event(".4"), "immediate")
        self.assertIn("has_variable = iw_expose_ordered", immediate)
        self.assertIn("add_to_temporary_list = iw_expose_queue", immediate)
        self.assertIn("save_scope_as = iw_expose_rec", immediate)
        self.assertIn("covert_watch_expose_record = yes", immediate)

    def test_event_1_releases_the_lock_outside_the_guard(self):
        after = event_block(event(".1"), "after")
        guarded = str(_innermost_enclosing(after, "covert_op_burn = {", "if = {"))
        self.assertNotIn("iw_expose_inflight", guarded)
        self.assertIn(
            "if = {\n\t\t\tlimit = { has_variable = iw_expose_inflight }\n"
            "\t\t\tremove_variable = iw_expose_inflight\n\t\t}",
            after,
        )


class SelfChecks(unittest.TestCase):
    def test_decision_event_logs_ok_once(self):
        immediate = event_block(event(".3"), "immediate")
        self.assertIn("TE_SELF_CHECK OK covert_catch_decision", immediate)
        self.assertIn("has_global_variable = te_selfcheck_covert_catch_done", immediate)
        self.assertIn("set_global_variable = { name = te_selfcheck_covert_catch_done", immediate)

    def test_event_1_logs_ok_for_a_watched_operation_once(self):
        immediate = event_block(event(".1"), "immediate")
        self.assertIn("TE_SELF_CHECK OK covert_watch_expose", immediate)
        self.assertIn("has_variable = iw_known", immediate)
        self.assertIn("set_global_variable = { name = te_selfcheck_covert_watch_done", immediate)

    def test_pending_watchdog_logs_broken_once(self):
        body = scripted_effect("covert_watch_attacker_monthly")
        self.assertIn("TE_SELF_CHECK BROKEN covert_catch_decision", body)
        # Not at the second pass: a player may leave covert_warfare.3 open for
        # its whole duration, which is in months.
        self.assertIn("var:iw_catch_pending >= covert_open_event_stale_passes", body)
        self.assertIn("set_global_variable = { name = te_selfcheck_covert_catch_broken", body)

    def test_monthly_expose_check_needs_a_sent_order(self):
        body = scripted_effect("covert_watch_monthly")
        broken = str(_innermost_enclosing(body, "TE_SELF_CHECK BROKEN covert_watch_expose", "if = {"))
        self.assertIn("has_variable = iw_expose_sent", broken)
        self.assertIn("covert_exposure_in_flight = yes", broken)
        self.assertIn("te_selfcheck_covert_watch_broken", broken)


def stale_passes():
    m = re.search(r"(?m)^covert_open_event_stale_passes = (\d+)$", _text(VALUES))
    if m is None:
        raise AssertionError("covert_open_event_stale_passes is not a whole-number constant")
    return int(m.group(1))


class Watchdogs(unittest.TestCase):
    def test_stale_passes_outlast_an_unanswered_event(self):
        # An event's `duration` is in months (NEvents.DEFAULT_MONTHS_VALID): a
        # player may leave covert_warfare.1 or .3 open that long. The count
        # starts at 1 on the day the event opens at the earliest, so it reaches
        # N no sooner than N - 1 months later; N >= duration + 2 keeps a
        # month's margin past expiry.
        passes = stale_passes()
        for suffix in (".1", ".3"):
            m = re.search(r"\n\tduration = (\d+)\n", event(suffix))
            self.assertIsNotNone(m, suffix)
            self.assertGreaterEqual(passes, int(m.group(1)) + 2, suffix)

    def test_event_1_lasts_one_month(self):
        # While a covert_warfare.1 is open its attacker is locked: no roll, no
        # Expose against it. A player could stall detection by leaving it
        # unanswered, so it lasts one month (duration is in months): a stall
        # skips at most one monthly roll per catch.
        self.assertRegex(event(".1"), r"\n\tduration = 1\n")

    def test_lock_failsafe_waits_for_a_second_month_without_event_1(self):
        body = scripted_effect("covert_watch_attacker_monthly")
        fail = str(_innermost_enclosing(body, "remove_variable = iw_expose_inflight", "if = {"))
        self.assertIn("var:iw_expose_inflight >= 2", fail)
        outer = str(_innermost_enclosing(body, "change_variable = { name = iw_expose_inflight add = 1 }", "if = {"))
        self.assertIn("NOT = { has_variable = iw_burned_type_code }", outer)

    def test_event_1_copies_left_past_the_stale_passes_are_released(self):
        # A revolution that wins while covert_warfare.1 is open hands its copies
        # to the winner and the event's `after` never runs; covert_exposure_in_flight
        # reads iw_burned_type_code, so the attacker would be locked for good.
        # Each pass that finds the copies counts itself on iw_burned_seen; at
        # covert_open_event_stale_passes they go. Not sooner: a .1 a player
        # hasn't answered is open for months, and its copies must survive.
        body = scripted_effect("covert_watch_attacker_monthly")
        stale = str(_innermost_enclosing(body, "remove_variable = iw_burned_type_code", "if = {"))
        self.assertTrue(
            stale.startswith(
                "if = {\n\t\t\tlimit = { var:iw_burned_seen >= covert_open_event_stale_passes }"),
            stale[:100],
        )
        for var in ("iw_burned_phase", "iw_burned_at_war", "iw_burned_friend",
                    "iw_expose_inflight", "iw_burned_seen"):
            self.assertIn("remove_variable = %s" % var, stale)
        self.assertIn("TE_SELF_CHECK BROKEN covert_exposure_lock", stale)
        self.assertIn("has_global_variable = te_selfcheck_covert_exposure_lock_broken", stale)
        self.assertIn("set_global_variable = { name = te_selfcheck_covert_exposure_lock_broken", stale)
        mark = str(_innermost_enclosing(body, "set_variable = { name = iw_burned_seen value = 1 }", "if = {"))
        self.assertTrue(
            mark.startswith("if = {\n\t\tlimit = { has_variable = iw_burned_type_code }"),
            mark[:80],
        )
        # Counted on every pass (set on the first, raised after), before the
        # test that releases them.
        self.assertIn(stale, mark)
        count = str(_innermost_enclosing(mark, "change_variable = { name = iw_burned_seen add = 1 }", "if = {"))
        self.assertTrue(count.startswith("if = {\n\t\t\tlimit = { has_variable = iw_burned_seen }"), count[:80])
        self.assertLess(mark.index("set_variable = { name = iw_burned_seen value = 1 }"), mark.index(stale))
        self.assertLess(mark.index(count), mark.index(stale))
        # ...and `after` removes the count with the copies, outside the burn's
        # guard, or the next covert_warfare.1 would start part-way there.
        after = event_block(event(".1"), "after")
        guarded = str(_innermost_enclosing(after, "covert_op_burn = {", "if = {"))
        self.assertNotIn("iw_burned_seen", guarded)
        self.assertIn(
            "if = {\n\t\t\tlimit = { has_variable = iw_burned_seen }\n"
            "\t\t\tremove_variable = iw_burned_seen\n\t\t}",
            after,
        )

    def test_orphaned_known_flag_is_dropped(self):
        # A watched operation whose record is gone (a revolution loses the
        # defender's lists) becomes catchable again.
        body = scripted_effect("covert_watch_attacker_monthly")
        self.assertIn("variable = iw_known_ops", body)
        self.assertIn("remove_variable = iw_known", body)

    def test_attacker_side_runs_monthly_before_the_roll(self):
        pulse = je_pulse()
        self.assertLess(
            pulse.index("covert_watch_attacker_monthly = yes"),
            pulse.index("covert_ops_roll_detection_all = yes"),
        )
        self.assertNotIn("covert_watch_attacker_monthly", scripted_effect("covert_ops_sync_all"))


class Growth(unittest.TestCase):
    def test_nets_sync_counts_watched_ops(self):
        body = scripted_effect("covert_nets_sync")
        self.assertIn("iw_known_ops", body)
        self.assertIn("iw_net_watch_gain", body)

    def test_monthly_called_from_journal_pulse_after_nets_sync(self):
        pulse = je_pulse()
        self.assertLess(pulse.index("covert_nets_sync = yes"), pulse.index("covert_watch_monthly = yes"))

    def test_watched_network_grows_does_not_decay_and_is_not_reaped(self):
        body = _top_level_block(_text(EFFECTS), "covert_nets_sync = {")
        tick = body[body.index("# ---- 3. Tick ----"): body.index("# ---- 4. Reap ----")]
        self.assertIn("covert_net_gain = { AMOUNT = covert_net_watch_tick_gain }", tick)
        # Grow (not decay) when either feeds it: the decay is this if's else.
        self.assertRegex(tick, r"OR = \{\s*var:iw_net_ops >= 1\s*var:iw_net_watch_gain > 0\s*\}")
        reap = body[body.index("# ---- 4. Reap ----"):]
        self.assertIn("var:iw_net_watch_gain <= 0", reap)

    def test_watch_gain_is_zeroed_then_summed_per_record(self):
        raw = _top_level_block(_text(EFFECTS), "covert_nets_sync = {")
        count = raw[raw.index("# ---- 2. Count ----"): raw.index("# ---- 3. Tick ----")]
        body = strip_comments(count)
        self.assertLess(
            body.index("set_variable = { name = iw_net_watch_gain value = 0 }"),
            body.index("variable = iw_known_ops"),
        )
        # Each record's gain lands in the network inside its attacker, inside
        # that network's own lookup.
        pick = str(_innermost_enclosing(body, "name = iw_net_watch_gain\n", "random_in_list = {"))
        self.assertIn("limit = { var:iw_target ?= scope:iw_net_watch_tgt }", pick)
        # Zeroed per record before the lookup, so a dead operation adds 0.
        self.assertLess(
            body.index("name = iw_watch_gain_staging value = 0"),
            body.index("covert_watch_op_matches"),
        )
        for p in (1, 2, 3):
            self.assertIn("covert_net_watch_gain_p%d" % p, body)
        # An exposure already ordered stops the gain.
        self.assertIn("NOT = { has_variable = iw_expose_ordered }", body)

    def test_watch_tick_gain_applies_tradecraft_and_un_but_not_cultivation(self):
        body = script_value("covert_net_watch_tick_gain")
        self.assertIn("var:iw_net_watch_gain", body)
        self.assertIn("multiply = var:iw_net_tc_mult", body)
        self.assertIn("multiply = var:iw_net_un_mult", body)
        self.assertNotIn("cultivat", body)

    def test_watch_gain_constants(self):
        values = _text(VALUES)
        self.assertRegex(values, r"(?m)^covert_net_watch_gain_p1 = 4$")
        # The busier levels are the base gain x the priority effect
        # multipliers, derived so a retune of priority carries them along.
        for p in (2, 3):
            block = script_value("covert_net_watch_gain_p%d" % p)
            self.assertIn("value = covert_net_watch_gain_p1", block)
            self.assertIn("multiply = covert_op_priority_%d_effect_mult" % p, block)


class Monthly(unittest.TestCase):
    def test_reaps_dead_records_remove_before_destroy(self):
        body = scripted_effect("covert_watch_monthly")
        reap = body[body.index("add_to_temporary_list = iw_watch_dead_recs"):]
        self.assertLess(
            reap.index("remove_list_variable = { name = iw_known_ops"),
            reap.index("destroy_container = yes"),
        )
        self.assertIn("is_country_alive = yes", body)

    def test_ages_retries_and_rolls_for_the_ai(self):
        body = scripted_effect("covert_watch_monthly")
        self.assertIn("change_variable = { name = iw_watch_months add = 1 }", body)
        self.assertIn("covert_watch_expose_record = yes", body)
        ai = str(_innermost_enclosing(body, "chance = covert_ai_watch_expose_chance", "if = {"))
        self.assertIn("is_player = no", ai)

    def test_old_saves_guard_the_list(self):
        self.assertIn("has_variable_list = iw_known_ops", scripted_effect("covert_watch_monthly"))


class Values(unittest.TestCase):
    def test_ai_watch_chance(self):
        body = script_value("covert_ai_watch_chance")
        self.assertIn("covert_code_tier_severe = { VAR = iw_watch_stage_code }", body)
        self.assertIn("var:iw_watch_stage_net >= covert_ai_watch_net_done", body)
        self.assertIn("var:iw_watch_stage_friend = 1", body)
        values = _text(VALUES)
        for name, number in (("covert_ai_watch_chance_base", "60"), ("covert_ai_watch_chance_severe", "15"),
                             ("covert_ai_watch_friend_add", "20"), ("covert_ai_watch_chance_net_done", "10"),
                             ("covert_ai_watch_net_done", "75")):
            self.assertRegex(values, r"(?m)^%s = %s$" % (name, number))

    def test_ai_expose_chance(self):
        body = script_value("covert_ai_watch_expose_chance")
        self.assertIn("covert_code_tier_severe = { VAR = iw_type_code }", body)
        self.assertIn("var:iw_watch_net", body)
        values = _text(VALUES)
        for name, number in (("covert_ai_watch_expose_base", "2"), ("covert_ai_watch_expose_per_point", "0.1"),
                             ("covert_ai_watch_expose_net_done", "25"), ("covert_ai_watch_expose_severe_add", "5")):
            self.assertRegex(values, r"(?m)^%s = %s$" % (name, re.escape(number)))


class CustomLoc(unittest.TestCase):
    def test_caught_type_name_maps_every_hostile_code(self):
        block = _top_level_block(_text(CUSTOM_LOC), "covert_caught_type_name = {")
        pairs = re.findall(
            r"trigger = \{ var:iw_caught_type_code = (\d+) \}\s*localization_key = iw_op_name_(\w+)", block
        )
        # Every watchable code (the registry test holds it to the full table).
        self.assertLessEqual({(c, t) for t, c in HOSTILE_CODES.items()}, {(int(c), t) for c, t in pairs})
        self.assertIn("localization_key = iw_op_name_unknown", block)


if __name__ == "__main__":
    unittest.main()
