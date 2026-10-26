"""Covert Warfare's definition of a friend, and the relations block that
became a cost.

covert_is_friend is the one trigger every friend-aware rule asks: the
attacker's backlash, the AI's watch odds, Counterintelligence Support's
launch and upkeep, and the AI's launch checks. A friend is a country with
cordial relations and a tie (alliance, defensive pact, power bloc, or
overlord and subject), or with amicable relations alone. Ties never count on
their own.

Until this change the six hostile operations that had a relations gate
refused a target at amicable relations (destabilization: cordial). The gate is
gone, so a player can spy on a friend and pay for it at home if caught; the
AI is kept off friends with those six operations (will_propose) and calls
the four it can break off once the target turns friend (will_break).

The trigger is checked two ways: by reading its text, and by running its
structure over every combination of relations and ties, so a tie placed
outside the cordial test, or an OR that lost a branch, fails here.

Run: python3 -m unittest test_covert_friend -v
"""

import re
import unittest

from test_covert_launch_preview import _strip_comments
from test_covert_op_registry import (
    ACTIONS,
    HOSTILE_TYPES,
    LOC_DIR,
    TRIGGERS,
    TYPES,
    _loc,
    _text,
    _top_level_block,
)

# The six operations that had a relations gate (spec § "Relations block
# removed"). They keep the AI off friends; the other hostile operations keep
# the AI logic they had.
FORMERLY_GATED = ("election_interference", "financial_subversion", "infrastructure_sabotage",
                  "comms_disruption", "ideological_subversion", "destabilization")
# Of those, the two wartime operations are never called off by the AI choice:
# their war-or-play requirement ends them.
WARTIME = ("infrastructure_sabotage", "comms_disruption")
BREAKABLE = tuple(t for t in FORMERLY_GATED if t not in WARTIME)
# Operations added since, whose AI was written to stay off friends from the
# start (solar colonization slice 5). Unlike the four above, the AI does not
# call them off when the target turns friend: their break reasons are their own.
AI_SPARES_FRIENDS = ("incite_autonomy", "sabotage_colony")

FRIEND_WARNING = "covert_friend_target_warning_tt"
RELATIONS_TOOLTIPS = ("iw_no_good_relations_tt", "iw_no_cordial_relations_tt")

# relations_threshold:* from the vanilla defines (spec § "The definition of a friend").
THRESHOLDS = {"relations_threshold:cordial": 20, "relations_threshold:amicable": 50}


def scripted_trigger(name):
    return _top_level_block(_text(TRIGGERS), name + " = {")


def action(typ):
    return _top_level_block(_text(ACTIONS), "covert_%s_action = {" % typ)


def blocks(text, name):
    """Every `name = { ... }` that opens a line in text, brace-balanced, with
    comments stripped. An action holds several requirement_to_maintain blocks,
    one level down inside `pact`, so no fixed indent is assumed."""
    text = _strip_comments(text)
    found = []
    for m in re.finditer(r"(?m)^[ \t]*%s = \{" % re.escape(name), text):
        depth, i = 0, m.end() - 1
        while True:
            depth += {"{": 1, "}": -1}.get(text[i], 0)
            if depth == 0:
                break
            i += 1
        found.append(text[m.start(): i + 1].strip())
    return found


# ---- a small evaluator for the trigger's structure -----------------------

def _parse(text):
    """Paradox text -> [(key, operator, value)]; value is a string or a nested list."""
    tokens = re.findall(r"\{|\}|[<>]=?|=|[^\s{}=<>]+", _strip_comments(text))
    pos = 0

    def block():
        nonlocal pos
        items = []
        while pos < len(tokens) and tokens[pos] != "}":
            key, op = tokens[pos], tokens[pos + 1]
            pos += 2
            if tokens[pos] == "{":
                pos += 1
                value = block()
                pos += 1
            else:
                value = tokens[pos]
                pos += 1
            items.append((key, op, value))
        return items

    return block()


def _holds(key, op, value, world, side):
    """One statement of the trigger in `world`. `side` is whose scope it is
    read in: "self" is the country in scope, "other" the target after
    `$TARGET$ = { ... }`. Anything this does not model fails loudly, so a new
    clause has to be taught here rather than silently read as false."""
    if key in ("OR", "AND"):
        results = [_holds(k, o, v, world, side) for k, o, v in value]
        return any(results) if key == "OR" else all(results)
    if side == "self":
        if key == "T.relations:this" and op == ">=" and value in THRESHOLDS:
            return world["relations"] >= THRESHOLDS[value]
        if key == "has_treaty_alliance_with" and value == [("TARGET", "=", "T")]:
            return world["alliance"]
        if key == "has_treaty_defensive_pact_with" and value == [("TARGET", "=", "T")]:
            return world["defensive_pact"]
        if (key, value) == ("is_in_power_bloc", "yes"):
            return world["in_bloc"]
        if (key, value) == ("is_in_same_power_bloc", "T"):
            return world["same_bloc"]
        if (key, value) == ("is_subject_of", "T"):
            return world["we_are_subject"]
        if key == "T" and isinstance(value, list):
            return all(_holds(k, o, v, world, "other") for k, o, v in value)
    elif (key, value) == ("is_subject_of", "PREV"):
        return world["they_are_subject"]
    raise AssertionError("covert_is_friend uses %s %s %r, which this test does not model" % (key, op, value))


def _is_friend(world):
    body = scripted_trigger("covert_is_friend").replace("$TARGET$", "T")
    (_, _, inner), = _parse(body)
    return all(_holds(k, o, v, world, "self") for k, o, v in inner)


class FriendTrigger(unittest.TestCase):
    def test_trigger_defined_with_both_thresholds(self):
        body = scripted_trigger("covert_is_friend")
        self.assertIn("relations_threshold:cordial", body)
        self.assertIn("relations_threshold:amicable", body)
        for tie in ("has_treaty_alliance_with", "has_treaty_defensive_pact_with",
                    "is_in_same_power_bloc", "is_subject_of", "is_in_power_bloc = yes"):
            self.assertIn(tie, body)

    def test_treaty_ties_take_the_scripted_trigger_argument(self):
        # Both are vanilla scripted triggers (00_diplomacy_triggers.txt) that
        # name their argument; the bare `= scope:x` form fails the per-call
        # compile (script_argument_audit).
        body = scripted_trigger("covert_is_friend")
        for name in ("has_treaty_alliance_with", "has_treaty_defensive_pact_with"):
            self.assertIn("%s = { TARGET = $TARGET$ }" % name, body)

    def test_friend_is_cordial_with_a_tie_or_amicable_alone(self):
        flags = ("alliance", "defensive_pact", "in_bloc", "same_bloc", "we_are_subject", "they_are_subject")
        for relations in (-100, 0, 19, 20, 49, 50, 100):
            for bits in range(1 << len(flags)):
                world = {f: bool(bits >> i & 1) for i, f in enumerate(flags)}
                world["relations"] = relations
                # Two countries in no bloc can read as "the same bloc", so a
                # bloc tie needs the country in scope to be in one.
                tie = (world["alliance"] or world["defensive_pact"]
                       or (world["in_bloc"] and world["same_bloc"])
                       or world["we_are_subject"] or world["they_are_subject"])
                expected = relations >= 50 or (relations >= 20 and tie)
                with self.subTest(**world):
                    self.assertEqual(_is_friend(world), expected)


class RelationsBlockRemoved(unittest.TestCase):
    def test_no_relations_threshold_in_possible_or_maintain(self):
        for typ in TYPES:
            for block in ("possible", "requirement_to_maintain"):
                for b in blocks(action(typ), block):
                    self.assertNotIn("relations_threshold", b, f"{typ} {block}")

    def test_the_relations_tooltips_are_gone(self):
        # Nothing names them, and a key nothing references only ends up in
        # te_unused as dead text.
        for key in RELATIONS_TOOLTIPS:
            self.assertNotIn(key, _text(ACTIONS))
            for path in LOC_DIR.rglob("*.yml"):
                self.assertNotIn(key, path.read_text(encoding="utf-8-sig"), path.name)

    def test_concepts_no_longer_state_the_old_gate(self):
        loc = _loc()
        for key in ("concept_covert_operations_desc", "concept_covert_warfare_system_desc"):
            with self.subTest(key):
                self.assertNotRegex(loc[key], r"(?i)\b(amicable|cordial)\b[^.;]*\bor better\b")
                self.assertIn("friend", loc[key])

    def test_the_intelligence_sharing_gate_stays(self):
        # A treaty obligation, not the relations block (spec: Kept). Only on
        # the hostile operations: a partner may be protected (spec § C).
        for typ in HOSTILE_TYPES:
            self.assertIn("text = iw_no_intel_sharing_tt", blocks(action(typ), "possible")[0], typ)

    def test_formerly_gated_ai_avoids_friends(self):
        for typ in FORMERLY_GATED + AI_SPARES_FRIENDS:
            wp = blocks(action(typ), "will_propose")[0]
            self.assertRegex(wp, r"NOT = \{\s*covert_is_friend = \{ TARGET = scope:target_country \}")

    def test_other_hostile_operations_keep_their_ai(self):
        # Owner's choice (spec § B, option c): the AI goes on spying on
        # friends with the rest and pays the backlash when caught.
        # Counterintelligence Support is for friends only, so its AI asks.
        for typ in HOSTILE_TYPES:
            if typ not in FORMERLY_GATED + AI_SPARES_FRIENDS:
                with self.subTest(typ):
                    self.assertNotIn("covert_is_friend", "\n".join(blocks(action(typ), "ai")))

    def test_ai_calls_off_breakable_operations_against_friends(self):
        friend = ("covert_is_friend", "=", [("TARGET", "=", "scope:target_country")])
        for typ in BREAKABLE:
            with self.subTest(typ):
                (_, _, inner), = _parse(blocks(action(typ), "will_break")[0])
                # Behind the settled wait, as the other break reasons are, and
                # one reason among several.
                self.assertEqual(inner[0][0], "covert_ai_op_settled")
                reasons = [v for k, _, v in inner if k == "OR"]
                self.assertEqual(len(reasons), 1)
                self.assertIn(friend, reasons[0])
                self.assertGreater(len(reasons[0]), 1)

    def test_wartime_operations_are_never_called_off_by_choice(self):
        for typ in WARTIME:
            with self.subTest(typ):
                self.assertEqual(blocks(action(typ), "will_break"), ["will_break = { always = no }"])


class LaunchPreview(unittest.TestCase):
    def test_launch_preview_warns_on_friend(self):
        # Every hostile operation; Counterintelligence Support is only ever
        # run on a friend, and its preview shows the boost instead.
        for typ in HOSTILE_TYPES:
            accept = blocks(action(typ), "accept_effect")[0]
            with self.subTest(typ):
                self.assertIn(FRIEND_WARNING, accept)
                self.assertRegex(
                    accept,
                    r"if = \{\s*limit = \{ covert_is_friend = \{ TARGET = scope:target_country \} \}\s*"
                    r"custom_tooltip = \{\s*text = %s\s*\}\s*\}" % FRIEND_WARNING,
                )
                # Before the effect that starts the operation, beside the
                # detection warning it qualifies.
                self.assertLess(accept.index(FRIEND_WARNING), accept.index("covert_op_start"))

    def test_warning_names_the_target_through_the_saved_scope(self):
        # TARGET_COUNTRY is unbound in a preview tooltip's text (scripting_best_practices.md).
        text = _loc()[FRIEND_WARNING]
        self.assertIn("[SCOPE.sCountry('target_country').GetName]", text)
        self.assertNotIn("TARGET_COUNTRY", text)


if __name__ == "__main__":
    unittest.main()
