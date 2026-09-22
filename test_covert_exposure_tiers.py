"""Structural tests for covert warfare slice 2 (graduated exposure).

The tier table is the single source of truth for how hostile each operation
type is when it is caught. These tests pin that table, pin that every consumer
reads it rather than re-listing codes, and pin the shape of the blowback the
detection event applies.
"""

import re
import unittest
from pathlib import Path

from paradox_file_parser import ParadoxFileParser

ROOT = Path(__file__).resolve().parent
TRIGGERS = ROOT / "common/scripted_triggers/covert_warfare_triggers.txt"
VALUES = ROOT / "common/script_values/covert_warfare_script_values.txt"
EFFECTS = ROOT / "common/scripted_effects/covert_warfare_effects.txt"
EVENTS = ROOT / "events/covert_warfare_events.txt"
CUSTOM_LOC = ROOT / "common/customizable_localization/covert_warfare_custom_loc.txt"
MESSAGES = ROOT / "common/messages/extra_messages.txt"
ACTIONS = ROOT / "common/diplomatic_actions/covert_operations.txt"
LOC_NOTIFICATIONS = ROOT / "localization/english/te_notifications_l_english.yml"
DEBUG_EFFECTS = ROOT / "common/scripted_effects/te_debug_covert_effects.txt"

# Slice 1's codes, repeated here so this file stands alone.
CODES = {
    "election_interference": 0,
    "financial_subversion": 1,
    "infrastructure_sabotage": 2,
    "comms_disruption": 3,
    "industrial_espionage": 4,
    "military_espionage": 5,
    "influence_campaign": 6,
    "ideological_subversion": 7,
    "destabilization": 8,
}

TIER_CODES = {
    "mild": {4, 5},
    "moderate": {0, 1, 6},
    "severe": {7, 8},
    "war": {2, 3},
}

# Values slice 2 retires. None of them may survive anywhere in the mod.
RETIRED_VALUES = (
    "covert_detection_chance_display",
    "covert_detection_target_ic_display",
    "covert_ops_detected_infamy",
)

MOD_DIRS = ("common", "events", "gui", "localization")
MOD_SUFFIXES = {".txt", ".gui", ".yml"}


def _text(path):
    return path.read_text(encoding="utf-8-sig")


def _top_level_block(body, header):
    """The text of one top-level `header = { ... }` entry, header through the
    first unindented closing brace. Safe because nested closing braces are
    always tab-indented (format_paradox_tabs.py).
    """
    block = body[body.index(header):]
    return block[: block.index("\n}\n") + 3]


def _tier_block(body, tier):
    return _top_level_block(body, "covert_code_tier_%s = {" % tier)


def _block_span(body, from_index):
    """(start, end) of the brace-balanced block whose opening `{` is at or
    after from_index; end is the index just past the matching `}`.

    Counts braces instead of trusting indentation, so it is correct even for
    a block that a future edit re-indents or collapses.
    """
    open_at = body.index("{", from_index)
    depth = 0
    for i in range(open_at, len(body)):
        if body[i] == "{":
            depth += 1
        elif body[i] == "}":
            depth -= 1
            if depth == 0:
                return from_index, i + 1
    raise AssertionError("unbalanced braces from index %d" % from_index)


class _EnclosingBlock(str):
    """The text an `_innermost_enclosing` call found, plus the (start, end)
    span it was found at in the body that was searched.

    Subclassing `str` (rather than a bare `(text, start, end)` tuple) means
    every existing call site that treats the result as plain text --
    `assertIn`, `_limit_of`, passing it back in as the `body` of a nested
    `_innermost_enclosing` call -- keeps working unchanged, since slicing or
    otherwise deriving a new string from it yields a normal `str`. Only
    `_is_outside` needs the span, and reads it off `.start`/`.end` instead of
    re-deriving the block's position by searching `body` for its text again,
    which would silently match the wrong occurrence if that text recurred
    elsewhere in the body (two structurally identical guards, say -- see
    HelperTests.test_is_outside_uses_the_found_span_not_a_text_research for
    a case that pins this down).
    """

    def __new__(cls, text, start, end):
        obj = str.__new__(cls, text)
        obj.start = start
        obj.end = end
        return obj


def _innermost_enclosing(body, needle, opener):
    """The innermost `opener { ... }` block that contains needle, as an
    `_EnclosingBlock` (usable as plain text, and carrying the span it was
    found at).

    This is what lets a test say "the war-tier exclusion is in the limit of
    the `if` that guards THIS effect", rather than "the string appears
    somewhere nearby".
    """
    target = body.index(needle)
    best = None
    pos = 0
    while True:
        at = body.find(opener, pos)
        if at == -1 or at > target:
            break
        start, end = _block_span(body, at)
        if start <= target < end and (best is None or start > best[0]):
            best = (start, end)
        pos = at + 1
    if best is None:
        raise AssertionError("no %r block encloses %r" % (opener, needle))
    return _EnclosingBlock(body[best[0]:best[1]], best[0], best[1])


def _limit_of(block):
    """The `limit = { ... }` sub-block of a block, brace-balanced."""
    start, end = _block_span(block, block.index("limit = {"))
    return block[start:end]


def _is_outside(span, body, needle):
    """True when needle's position in body falls outside `span`'s
    (start, end) -- `span` is normally the `_EnclosingBlock` an
    `_innermost_enclosing` call already found, so this uses the position it
    was actually found at instead of re-deriving it by searching `body` for
    the block's text again (which would silently match the wrong occurrence
    if that text recurred elsewhere in `body`).
    """
    at = body.index(needle)
    return not (span.start <= at < span.end)


class HelperTests(unittest.TestCase):
    SAMPLE = (
        "outer = {\n"
        "\tif = {\n"
        "\t\tlimit = { a = 1 }\n"
        "\t\teffect_one = yes\n"
        "\t}\n"
        "\teffect_two = yes\n"
        "}\n"
    )

    def test_block_span_stops_at_the_matching_brace(self):
        start, end = _block_span(self.SAMPLE, self.SAMPLE.index("if = {"))
        # NOTE: the brief's original assertion here sliced a fixed 20
        # characters off the end and compared it to a 19-character literal,
        # which can never be equal -- a bug in the brief's illustrative test,
        # not in `_block_span` (verified by hand-tracing the brace count).
        # `endswith` checks the same thing without a magic length.
        self.assertTrue(self.SAMPLE[start:end].endswith("effect_one = yes\n\t}"))
        self.assertNotIn("effect_two", self.SAMPLE[start:end])

    def test_innermost_enclosing_picks_the_inner_block(self):
        block = _innermost_enclosing(self.SAMPLE, "effect_one = yes", "if = {")
        self.assertIn("limit = { a = 1 }", block)
        self.assertNotIn("effect_two", block)

    def test_innermost_enclosing_raises_when_nothing_encloses(self):
        with self.assertRaises(AssertionError):
            _innermost_enclosing(self.SAMPLE, "effect_two = yes", "if = {")

    def test_limit_of_returns_only_the_limit(self):
        block = _innermost_enclosing(self.SAMPLE, "effect_one = yes", "if = {")
        self.assertEqual("limit = { a = 1 }", _limit_of(block))

    def test_is_outside_uses_the_found_span_not_a_text_research(self):
        # Two structurally identical `if` guards -- the sort of thing that
        # happens when the same boilerplate condition guards two different
        # effects. `_innermost_enclosing` already pins down which OCCURRENCE
        # it found (the span); if `_is_outside` instead re-derived the
        # guard's position by searching `body` for its TEXT, `str.index`
        # would silently return the FIRST (here, unrelated) occurrence
        # instead of the one that was actually found.
        body = (
            "outer = {\n"
            "\tif = {\n"
            "\t\tlimit = { a = 1 }\n"
            "\t\tremove_variable = stray\n"
            "\t}\n"
            "\tunrelated_effect = yes\n"
            "\tif = {\n"
            "\t\tlimit = { a = 1 }\n"
            "\t\tremove_variable = stray\n"
            "\t}\n"
            "}\n"
        )
        first_start, first_end = _block_span(body, body.index("if = {"))
        second_start, second_end = _block_span(body, body.index("if = {", first_end))
        self.assertEqual(
            body[first_start:first_end],
            body[second_start:second_end],
            "the two guards must be byte-identical for this case to test anything",
        )
        # Simulates what `_innermost_enclosing` would hand back had it been
        # asked for the SECOND guard specifically (its content is identical
        # to the first, so a needle-based search cannot distinguish them --
        # this stands in for "the span a caller already correctly has").
        second_block = _EnclosingBlock(body[second_start:second_end], second_start, second_end)
        needle = "remove_variable = stray"
        # `needle`'s only free-standing occurrence sits inside the FIRST
        # guard, not the second -- so relative to the second guard
        # specifically, it is genuinely outside.
        at = body.index(needle)
        self.assertTrue(first_start <= at < first_end)
        self.assertFalse(second_start <= at < second_end)

        # The current (span-based) `_is_outside` gets this right.
        self.assertTrue(_is_outside(second_block, body, needle))

        # The naive approach the old `_is_outside` used -- re-deriving the
        # guard's position with `body.index(container)` -- gets it wrong: it
        # silently lands on the first (decoy) occurrence, whose span happens
        # to actually contain `needle`, so it wrongly concludes the needle is
        # INSIDE the guard being checked.
        naive_start = body.index(second_block)
        naive_end = naive_start + len(second_block)
        self.assertEqual(first_start, naive_start, "the naive re-search must land on the decoy")
        naive_result = not (naive_start <= at < naive_end)
        self.assertFalse(naive_result, "the naive approach must get this wrong")


class TierTableTests(unittest.TestCase):
    def test_tier_triggers_partition_every_operation_code(self):
        # Slice 6 adds three operation types. Each new code must land in
        # exactly one tier, and no code may be forgotten.
        body = _text(TRIGGERS)
        seen = {}
        for tier, expected in TIER_CODES.items():
            codes = {int(m) for m in re.findall(r"var:\$VAR\$ = (\d+)", _tier_block(body, tier))}
            self.assertEqual(codes, expected, "tier %s holds the wrong codes" % tier)
            for code in codes:
                self.assertNotIn(code, seen, "code %d is in two tiers" % code)
                seen[code] = tier
        self.assertEqual(
            set(seen),
            set(CODES.values()),
            "every operation code must belong to exactly one exposure tier",
        )

    def test_tier_triggers_guard_the_variable(self):
        # Reading a variable that does not exist logs an engine error, and
        # these run from custom loc that may render before the code is stamped.
        body = _text(TRIGGERS)
        for tier in TIER_CODES:
            self.assertIn(
                "has_variable = $VAR$",
                _tier_block(body, tier),
                "covert_code_tier_%s must guard $VAR$" % tier,
            )

    def test_triggers_file_parses(self):
        parser = ParadoxFileParser()
        parser.parse_file(str(TRIGGERS), apply_directives=False)
        for tier in TIER_CODES:
            self.assertIn("covert_code_tier_%s" % tier, parser.data)


class BlowbackValueTests(unittest.TestCase):
    def test_blowback_values_read_the_tier_table(self):
        body = _text(VALUES)
        for name in ("covert_exposure_infamy_base", "covert_exposure_relations_base"):
            block = _top_level_block(body, "%s = {" % name)
            self.assertIn("covert_code_tier_", block, "%s must branch on the tier table" % name)
            self.assertIn("VAR = iw_burned_type_code", block)

    def test_phase_multiplier_reads_the_burned_phase(self):
        block = _top_level_block(_text(VALUES), "covert_exposure_phase_mult = {")
        self.assertIn("has_variable = iw_burned_phase", block)
        self.assertIn("var:iw_burned_phase", block)

    def test_option_values_exist_and_split_the_blowback(self):
        body = _text(VALUES)
        ack_infamy = _top_level_block(body, "covert_exposure_infamy_acknowledge = {")
        deny_infamy = _top_level_block(body, "covert_exposure_infamy_deny = {")
        ack_rel = _top_level_block(body, "covert_exposure_relations_acknowledge = {")
        deny_rel = _top_level_block(body, "covert_exposure_relations_deny = {")
        # Acknowledge pays the full infamy; Deny halves it.
        self.assertIn("covert_exposure_phase_mult", ack_infamy)
        self.assertIn("covert_exposure_deny_infamy_mult", deny_infamy)
        # Deny takes the full relations hit; Acknowledge halves it.
        self.assertIn("covert_exposure_phase_mult", deny_rel)
        self.assertIn("covert_exposure_acknowledge_relations_mult", ack_rel)

    def test_infamy_is_capped(self):
        block = _top_level_block(_text(VALUES), "covert_exposure_infamy_acknowledge = {")
        self.assertIn("max = covert_exposure_infamy_max", block)

    def test_retired_values_have_no_references_left(self):
        for name in RETIRED_VALUES:
            for directory in MOD_DIRS:
                for path in sorted((ROOT / directory).rglob("*")):
                    if not path.is_file() or path.suffix not in MOD_SUFFIXES:
                        continue
                    self.assertNotIn(
                        name,
                        path.read_text(encoding="utf-8-sig", errors="ignore"),
                        "%s still appears in %s" % (name, path),
                    )


class ThirdPartyBlowbackTests(unittest.TestCase):
    def test_effect_previews_in_a_tooltip(self):
        block = _top_level_block(_text(EFFECTS), "covert_exposure_third_party_blowback = {")
        # Only a custom_tooltip renders an every_country loop in an option
        # tooltip; without it the option previews as doing nothing.
        self.assertIn("custom_tooltip = {", block)
        self.assertIn("covert_exposure_third_party_tt", block)

    def test_effect_excludes_the_operator_and_the_target(self):
        block = _top_level_block(_text(EFFECTS), "covert_exposure_third_party_blowback = {")
        self.assertIn("NOT = { this = root }", block)
        self.assertIn("NOT = { this = scope:detected_by_country }", block)

    def test_bloc_audience_requires_the_target_to_have_a_bloc(self):
        # Without this guard two countries that are both in no power bloc can
        # read as being in the same one, which would spray the whole world.
        # Tightened: `is_in_power_bloc = yes` must be checked ON THE TARGET
        # (nested inside `scope:detected_by_country = { ... }`) -- applying it
        # to the iterated country (`this`) instead would still satisfy a bare
        # substring check but silently defeat the guard.
        block = _top_level_block(_text(EFFECTS), "covert_exposure_third_party_blowback = {")
        scoped_to_target = _innermost_enclosing(
            block, "is_in_power_bloc = yes", "scope:detected_by_country = {"
        )
        self.assertIn("is_in_power_bloc = yes", scoped_to_target)
        self.assertIn("is_in_same_power_bloc = scope:detected_by_country", block)
        self.assertIn("has_treaty_alliance_with = { TARGET = scope:detected_by_country }", block)

    def test_effect_moves_relations_and_posts_the_notice(self):
        # Tightened: both effects must be nested inside the `every_country`
        # loop, not merely present somewhere in the outer effect -- moved to
        # a sibling of the loop, either would fire once globally instead of
        # once per qualifying third party, and a substring check alone would
        # not notice.
        block = _top_level_block(_text(EFFECTS), "covert_exposure_third_party_blowback = {")
        loop = _innermost_enclosing(
            block, "post_notification = covert_severe_exposure_notice", "every_country = {"
        )
        self.assertIn("value = covert_exposure_third_party_relations", loop)
        self.assertIn("post_notification = covert_severe_exposure_notice", loop)

    def test_notice_type_is_defined(self):
        self.assertIn("covert_severe_exposure_notice = {", _text(MESSAGES))

    def test_notice_is_localized_through_the_notification_keys(self):
        # The message DEFINITION existing is not enough, and asserting only
        # that was how this shipped rendering three raw keys. Vic3 resolves a
        # post_notification through notification_<name>_name / _desc /
        # _tooltip; the bare `covert_severe_exposure_notice` key is never
        # looked up, so it must not masquerade as the localization either.
        loc = _text(LOC_NOTIFICATIONS)
        for suffix in ("name", "desc", "tooltip"):
            key = "notification_covert_severe_exposure_notice_%s:0" % suffix
            self.assertIn(key, loc, "%s must be localized" % key)
        # The tooltip composes the other two, the way every notification_iw_*
        # entry in this file does.
        self.assertIn(
            'notification_covert_severe_exposure_notice_tooltip:0 "#header '
            "$notification_covert_severe_exposure_notice_name$#!"
            '\\n$notification_covert_severe_exposure_notice_desc$"',
            loc,
        )
        # No bare key anywhere: organize_loc keeps it alive (the message name
        # is referenced by post_notification), so a leftover reads as a live
        # translation of a key the engine never asks for.
        for directory in MOD_DIRS:
            for path in sorted((ROOT / directory).rglob("*.yml")):
                if not path.is_file():
                    continue
                self.assertNotIn(
                    " covert_severe_exposure_notice:",
                    path.read_text(encoding="utf-8-sig", errors="ignore"),
                    "bare covert_severe_exposure_notice loc key still in %s" % path,
                )


def _event_1(body):
    return body[body.index("covert_warfare.1 = {"): body.index("covert_warfare.2 = {")]


class ExposureEventTests(unittest.TestCase):
    def test_immediate_copies_the_phase_as_well_as_the_code(self):
        # Tightened: both `set_variable` calls (and the phase read) must lie
        # inside the innermost `ROOT = { ... }` block -- a copy that landed on
        # some other scope would still satisfy a bare substring check but
        # write the variable to the wrong entity.
        ev = _event_1(_text(EVENTS))
        immediate = ev[ev.index("immediate = {"): ev.index("option = {")]
        root_block = _innermost_enclosing(immediate, "name = iw_burned_type_code", "ROOT = {")
        self.assertIn("name = iw_burned_type_code", root_block)
        self.assertIn("name = iw_burned_phase", root_block)
        self.assertIn("PREV.var:iw_phase", root_block)

    def test_options_use_the_graduated_values_not_literals(self):
        ev = _event_1(_text(EVENTS))
        options = ev[ev.index("option = {"): ev.index("after = {")]
        self.assertIn("value = covert_exposure_infamy_acknowledge", options)
        self.assertIn("value = covert_exposure_infamy_deny", options)
        self.assertIn("value = covert_exposure_relations_acknowledge", options)
        self.assertIn("value = covert_exposure_relations_deny", options)
        for literal in ("change_infamy = 2", "change_infamy = 1", "value = -15", "value = -30"):
            self.assertNotIn(literal, options, "%s survived the rewiring" % literal)

    def test_relations_are_skipped_in_the_costless_case(self):
        # Superseded by the costless trigger (Task 8): the war tier no longer
        # skips relations unconditionally -- only once the war has actually
        # started. Caught during the run-up, the war tier now takes the
        # relations hit like everyone else. The relations guard's `NOT` is
        # distinguished from the infamy guard's identical clause by the
        # `exists = scope:detected_by_country` line that only the relations
        # limit block carries.
        #
        # Tightened: rather than matching a literal two-line string at a
        # fixed tab depth (fragile under any reformatting), find the `if`
        # that actually guards each option's `change_relations` call and
        # inspect its `limit` directly. Also confirms the guard is NOT the
        # severe-tier one the third-party call uses -- a swap between the two
        # would still leave both literal clauses present in `options`.
        #
        # Placement and duplication are different defect classes, so both
        # are checked: the exact-count assertion catches a duplicated or
        # unguarded third call that `_innermost_enclosing` (which only ever
        # looks at the FIRST occurrence of `needle`) would silently miss;
        # the nesting assertion below catches a guard attached to the wrong
        # `if`, which a bare count cannot tell from a correct one.
        ev = _event_1(_text(EVENTS))
        options = ev[ev.index("option = {"): ev.index("after = {")]
        for value_name in (
            "covert_exposure_relations_acknowledge",
            "covert_exposure_relations_deny",
        ):
            needle = "value = %s" % value_name
            self.assertEqual(
                1,
                options.count(needle),
                "%s must be referenced exactly once" % value_name,
            )
            guard = _innermost_enclosing(options, needle, "if = {")
            limit = _limit_of(guard)
            self.assertIn(
                "exists = scope:detected_by_country",
                limit,
                "%s's guard must check the target still exists" % value_name,
            )
            self.assertIn(
                "NOT = { covert_exposure_is_costless = yes }",
                limit,
                "%s must skip once the war has actually started" % value_name,
            )
            self.assertNotIn(
                "covert_code_tier_severe",
                limit,
                "%s must not be guarded by the third-party severe-tier check" % value_name,
            )

    def test_both_options_call_the_third_party_blowback_on_the_severe_tier(self):
        # Placement and count are different defect classes: a plain count of
        # 2 across both options combined would still pass if both severe-tier
        # guards ended up on the same option and neither on the other, so
        # each occurrence is also checked individually by splitting into the
        # two option halves. But `_innermost_enclosing` only ever looks at
        # the FIRST occurrence of `needle` within whatever body it is given,
        # so a duplicated or unguarded third call inside one option would
        # slip past the per-half check alone -- the exact-count assertions
        # below catch that class instead.
        ev = _event_1(_text(EVENTS))
        options = ev[ev.index("option = {"): ev.index("after = {")]
        self.assertEqual(2, options.count("covert_exposure_third_party_blowback = yes"))
        self.assertEqual(
            2, options.count("covert_code_tier_severe = { VAR = iw_burned_type_code }")
        )
        split_at = options.index("name = covert_warfare.1.b")
        for label, half in (("acknowledge", options[:split_at]), ("deny", options[split_at:])):
            needle = "covert_exposure_third_party_blowback = yes"
            self.assertIn(needle, half, "option %s must call the third-party blowback" % label)
            guard = _innermost_enclosing(half, needle, "if = {")
            limit = _limit_of(guard)
            self.assertIn(
                "covert_code_tier_severe = { VAR = iw_burned_type_code }",
                limit,
                "option %s's third-party call must be gated on the severe tier" % label,
            )
            self.assertNotIn("covert_code_tier_war", limit)

    def test_after_clears_both_copied_variables(self):
        # Tightened: locate the actual guarded block (the innermost `if`
        # enclosing the `trigger_event` call to the target) by brace matching,
        # then assert each removal's position falls outside its span. Slicing
        # on where that anchor string happens to sit textually would still
        # pass if a removal were moved inside the guard but after the anchor.
        ev = _event_1(_text(EVENTS))
        after = ev[ev.index("after = {"):]
        guarded = _innermost_enclosing(
            after, "trigger_event = { id = covert_warfare.2 }", "if = {"
        )
        for name in ("iw_burned_type_code", "iw_burned_phase"):
            needle = "remove_variable = %s" % name
            self.assertIn(needle, after)
            self.assertTrue(
                _is_outside(guarded, after, needle),
                "%s must be removed outside the detected_by_country guard, or a "
                "burn whose target has vanished leaves the variable stuck forever" % needle,
            )


class TierNameLocTests(unittest.TestCase):
    def test_both_tier_names_read_the_tier_table(self):
        # Tightened: each tier's `trigger` and `localization_key` must live in
        # the SAME `text = { ... }` sub-block. Checking both strings appear
        # somewhere in the entry would still pass if a tier's trigger were
        # paired with a different tier's localization_key, since every tier
        # name is present somewhere in the entry regardless of pairing.
        body = _text(CUSTOM_LOC)
        for entry, var in (
            ("covert_burned_tier_name", "iw_burned_type_code"),
            ("covert_last_exposed_tier_name", "iw_last_exposed_type"),
        ):
            block = _top_level_block(body, "%s = {" % entry)
            for tier in TIER_CODES:
                trigger_call = "covert_code_tier_%s = { VAR = %s }" % (tier, var)
                self.assertIn(
                    trigger_call,
                    block,
                    "%s must name the %s tier through the tier table" % (entry, tier),
                )
                text_block = _innermost_enclosing(block, trigger_call, "text = {")
                self.assertIn(
                    "localization_key = iw_exposure_tier_%s" % tier,
                    text_block,
                    "%s's %s tier must pair the trigger with its OWN localization_key, "
                    "not one borrowed from a sibling text block" % (entry, tier),
                )
            # No custom loc may re-list codes; that is the tier table's job.
            self.assertNotIn("var:%s = " % var, block)

    def test_tier_name_keys_exist(self):
        loc = (ROOT / "localization/english").rglob("*.yml")
        body = "".join(p.read_text(encoding="utf-8-sig") for p in loc)
        for tier in TIER_CODES:
            self.assertIn("iw_exposure_tier_%s:" % tier, body)


ACTION_TIER = {
    "election_interference": "moderate",
    "financial_subversion": "moderate",
    "infrastructure_sabotage": "war",
    "comms_disruption": "war",
    "industrial_espionage": "mild",
    "military_espionage": "mild",
    "influence_campaign": "moderate",
    "ideological_subversion": "severe",
    "destabilization": "severe",
}


class PreLaunchTierNoteTests(unittest.TestCase):
    def test_the_hand_written_mapping_matches_the_tier_table(self):
        body = _text(TRIGGERS)
        for op_type, tier in ACTION_TIER.items():
            codes = {int(m) for m in re.findall(r"var:\$VAR\$ = (\d+)", _tier_block(body, tier))}
            self.assertIn(
                CODES[op_type],
                codes,
                "%s is documented as %s but the tier table disagrees" % (op_type, tier),
            )

    def test_every_action_description_shows_its_tier(self):
        loc = "".join(
            p.read_text(encoding="utf-8-sig")
            for p in sorted((ROOT / "localization/english").rglob("*.yml"))
        )
        for op_type, tier in ACTION_TIER.items():
            line = next(
                l for l in loc.splitlines()
                if l.strip().startswith("covert_%s_action_desc:" % op_type)
            )
            self.assertIn(
                "$iw_exposure_tier_%s_note$" % tier,
                line,
                "covert_%s_action_desc must show the %s tier" % (op_type, tier),
            )

    def test_every_covert_action_is_hostile(self):
        body = _text(ACTIONS)
        self.assertEqual(
            len(CODES),
            body.count("is_hostile = yes"),
            "every covert operation must be marked hostile",
        )


class DebugHarnessTests(unittest.TestCase):
    def test_the_seed_plants_a_severe_operation(self):
        block = _top_level_block(_text(DEBUG_EFFECTS), "te_debug_covert_seed_phases = {")
        planted = {int(m) for m in re.findall(r"CODE = (\d+)", block)}
        self.assertTrue(
            planted & TIER_CODES["severe"],
            "the seed must plant a severe operation so the third-party "
            "blowback branch is reachable in game",
        )


class DetectionFloorTests(unittest.TestCase):
    def test_the_floor_is_a_named_constant_at_a_tenth_of_a_percent(self):
        body = _text(VALUES)
        self.assertIn("covert_ops_detection_floor = 0.1", body)
        block = _top_level_block(body, "covert_operation_detection_chance = {")
        self.assertIn("min = covert_ops_detection_floor", block)
        self.assertNotIn("\n\tmin = 1\n", block)

    def test_the_operation_row_shows_a_decimal(self):
        # At the floor the risk is 0.1%/month. Rendered with |0 that reads as
        # "0%", which tells the player they are safe when they are not.
        loc = _text(ROOT / "localization/english/te_journal_entries_l_english.yml")
        line = next(
            l for l in loc.splitlines()
            if l.strip().startswith("je_iw_op_row_detection:")
        )
        self.assertIn("GetVariableValue('iw_detect')|1", line)


WAR_ACTIONS = ("covert_infrastructure_sabotage_action", "covert_comms_disruption_action")


def _header_block(body, header, start=0):
    """The brace-balanced text of one `header { ... }` occurrence, searching
    from `start`. Returns (text, end_index) so a caller can find a second
    occurrence of the same header after this one.
    """
    idx = body.index(header, start)
    span_start, span_end = _block_span(body, idx)
    return body[span_start:span_end], span_end


class DiplomaticPlayGateTests(unittest.TestCase):
    def test_both_wartime_actions_accept_a_play_in_all_three_gates(self):
        # Tightened: a bare count of 3 across the whole action block passes
        # even if the clauses landed in the wrong THREE places (e.g. doubled
        # in `possible` and missing from the pact's `requirement_to_maintain`,
        # which is the gate that decides whether an in-progress operation
        # survives a play resolving into war). Check each named gate by name
        # instead. `requirement_to_maintain` appears twice (this gate and the
        # funding gate), so the play-or-war clause only has to land in one of
        # the two -- checked as their concatenation.
        body = _text(ACTIONS)
        for action in WAR_ACTIONS:
            block = _top_level_block(body, "%s = {" % action)
            possible_block, _ = _header_block(block, "possible = {")
            rtm_1, rtm_1_end = _header_block(block, "requirement_to_maintain = {")
            rtm_2, _ = _header_block(block, "requirement_to_maintain = {", rtm_1_end)
            requirement_blocks = rtm_1 + rtm_2
            will_propose_block, _ = _header_block(block, "will_propose = {")
            for gate_name, gate_block in (
                ("possible", possible_block),
                ("requirement_to_maintain", requirement_blocks),
                ("will_propose", will_propose_block),
            ):
                self.assertIn(
                    "is_diplomatic_play_enemy_of = scope:target_country",
                    gate_block,
                    "%s's %s must accept a diplomatic play" % (action, gate_name),
                )
                self.assertIn(
                    "has_war_with = scope:target_country",
                    gate_block,
                    "%s's %s must still accept an actual war" % (action, gate_name),
                )
            # The old blanket "are you at war with anyone" clause is gone.
            self.assertNotIn("is_at_war = yes", block)

    def test_the_gate_tooltip_was_renamed_to_match_what_it_now_says(self):
        body = _text(ACTIONS)
        self.assertNotIn("iw_at_war_tt", body)
        self.assertEqual(4, body.count("iw_at_war_or_play_tt"))
        loc = _text(ROOT / "localization/english/te_miscellaneous_l_english.yml")
        self.assertIn("iw_at_war_or_play_tt:", loc)
        self.assertNotIn("iw_at_war_tt:", loc)


class WartimeExposureTests(unittest.TestCase):
    def test_the_costless_case_is_one_trigger(self):
        block = _top_level_block(_text(TRIGGERS), "covert_exposure_is_costless = {")
        self.assertIn("covert_code_tier_war = { VAR = iw_burned_type_code }", block)
        self.assertIn("has_variable = iw_burned_at_war", block)
        self.assertIn("var:iw_burned_at_war = 1", block)

    def test_immediate_copies_the_war_state(self):
        # Tightened: both the `if` writing 1 and the `else` writing 0 must lie
        # inside the innermost `ROOT = { ... }` block, and each write must
        # sit under its own branch -- the `if`'s `limit` must be the war
        # check, and the `else` (not just "somewhere in immediate") must
        # write 0. Without asserting the `else` branch specifically, a stray
        # unconditional `set_variable = { name = iw_burned_at_war value = 0 }`
        # placed right after the `if` (silently overwriting the war case back
        # to 0 every time) would still pass a bare substring check.
        ev = _event_1(_text(EVENTS))
        immediate = ev[ev.index("immediate = {"): ev.index("option = {")]
        root_block = _innermost_enclosing(
            immediate, "name = iw_burned_at_war value = 1", "ROOT = {"
        )
        war_if = _innermost_enclosing(
            root_block, "name = iw_burned_at_war value = 1", "if = {"
        )
        self.assertIn("has_war_with = scope:detected_by_country", _limit_of(war_if))
        war_else = _innermost_enclosing(
            root_block, "name = iw_burned_at_war value = 0", "else = {"
        )
        self.assertIn("name = iw_burned_at_war value = 0", war_else)

    def test_after_clears_the_war_state(self):
        # Tightened: same brace-matching approach as
        # `test_after_clears_both_copied_variables` -- find the actual guard
        # by locating the `if` that encloses the `trigger_event` call, then
        # confirm the removal's position falls outside its span.
        ev = _event_1(_text(EVENTS))
        after = ev[ev.index("after = {"):]
        guarded = _innermost_enclosing(
            after, "trigger_event = { id = covert_warfare.2 }", "if = {"
        )
        needle = "remove_variable = iw_burned_at_war"
        self.assertIn(needle, after)
        self.assertTrue(_is_outside(guarded, after, needle))

    def test_wartime_sabotage_during_the_war_costs_nothing(self):
        # Tightened: `covert_exposure_is_costless = yes` must be the LIMIT of
        # the branch that actually adds the zero/war magnitude, not merely
        # present somewhere in the value's if/else_if chain -- the chain has
        # another branch (the pre-war case, below) that also references a
        # `covert_exposure_*_war*` constant, so a bare substring check cannot
        # tell the two branches apart. `_innermost_enclosing`'s `opener`
        # "if = {" also matches inside "else_if = {" (that keyword contains
        # "if = {" as a substring, starting 5 characters in), which is
        # exactly what lets this walk the if/else_if chain uniformly.
        body = _text(VALUES)
        self.assertIn("covert_exposure_infamy_war = 0", body)
        infamy_block = _top_level_block(body, "covert_exposure_infamy_base = {")
        infamy_branch = _innermost_enclosing(
            infamy_block, "add = covert_exposure_infamy_war\n", "if = {"
        )
        self.assertIn("covert_exposure_is_costless = yes", _limit_of(infamy_branch))
        relations_block = _top_level_block(body, "covert_exposure_relations_base = {")
        relations_branch = _innermost_enclosing(relations_block, "add = 0\n", "if = {")
        self.assertIn("covert_exposure_is_costless = yes", _limit_of(relations_branch))

    def test_wartime_sabotage_before_the_war_is_charged_as_severe(self):
        # Severe-tier infamy, moderate relations -- stated as their own named
        # constants so the pre-war case can be retuned without touching either
        # tier it borrows its magnitude from.
        #
        # Tightened: assert `covert_code_tier_war` (not `covert_exposure_is_
        # costless`) is specifically the limit of the branch that adds each
        # *_war_prewar constant -- a bare substring check cannot distinguish
        # this branch from the costless branch above, since both blocks
        # contain both constant names somewhere.
        body = _text(VALUES)
        self.assertIn("covert_exposure_infamy_war_prewar = 4", body)
        self.assertIn("covert_exposure_relations_war_prewar = -20", body)
        infamy_block = _top_level_block(body, "covert_exposure_infamy_base = {")
        infamy_branch = _innermost_enclosing(
            infamy_block, "add = covert_exposure_infamy_war_prewar", "if = {"
        )
        infamy_limit = _limit_of(infamy_branch)
        self.assertIn("covert_code_tier_war = { VAR = iw_burned_type_code }", infamy_limit)
        self.assertNotIn("covert_exposure_is_costless", infamy_limit)
        relations_block = _top_level_block(body, "covert_exposure_relations_base = {")
        relations_branch = _innermost_enclosing(
            relations_block, "add = covert_exposure_relations_war_prewar", "if = {"
        )
        relations_limit = _limit_of(relations_branch)
        self.assertIn("covert_code_tier_war = { VAR = iw_burned_type_code }", relations_limit)
        self.assertNotIn("covert_exposure_is_costless", relations_limit)

    def test_both_options_skip_infamy_and_relations_in_the_costless_case(self):
        ev = _event_1(_text(EVENTS))
        options = ev[ev.index("option = {"): ev.index("after = {")]
        # Once per option for infamy, once per option for relations: a zero
        # would otherwise render as "+0" / "-0" in the option tooltip.
        self.assertEqual(4, options.count("NOT = { covert_exposure_is_costless = yes }"))


if __name__ == "__main__":
    unittest.main()
