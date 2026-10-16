"""Covert Warfare: the domestic backlash of an exposed operation.

An attacker caught spying on a friend pays at home (the lobby that favours the
target loses appeasement, the government loses legitimacy); a foreign operation
exposed at home turns the defender's public against the interest groups
friendly to the attacker. Both ride on the burn that covert_warfare.1 resolves.

What these tests pin is the shape an engine-silent mistake would hide in: the
multipliers are constants (add_modifier re-evaluates a multiplier against ROOT
on later ticks, and iw_burned_type_code is gone by then); the defender's side
reads the operator's variables through ROOT, not its own; the friend flag is
copied in `immediate` and removed in `after`; and the appeasement factor is one
the lobby types accept.

Run: python3 -m unittest test_covert_backlash -v
"""

import re
import unittest

from test_covert_exposure_tiers import (
    EVENTS,
    VALUES,
    _block_span,
    _innermost_enclosing,
    _is_outside,
    _limit_of,
)
from test_covert_op_registry import (
    EFFECTS,
    ROOT,
    TRIGGERS,
    _loc,
    _text,
    _top_level_block,
)

APPEASEMENT = ROOT / "common/political_lobby_appeasement/te_covert_appeasement.txt"
MODIFIERS = ROOT / "common/static_modifiers/extra_modifiers.txt"
ON_ACTIONS = ROOT / "common/on_actions/covert_warfare_on_actions.txt"

FACTOR = "appeasement_covert_spying_exposed"


def event(suffix):
    return _top_level_block(_text(EVENTS), "covert_warfare%s = {" % suffix)


def block(ev, name):
    """The brace-balanced `name = { ... }` block at event level."""
    start, end = _block_span(ev, ev.index("\n\t%s = {" % name))
    return ev[start:end]


def option(ev, name):
    return str(_innermost_enclosing(ev, "name = %s" % name, "option = {"))


def scripted_effect(name):
    return _top_level_block(_text(EFFECTS), name + " = {")


def effect_family(name):
    """The effect plus its internals (`name_full`, `name_half`), which hold the
    literals the dispatcher picks between."""
    text = _text(EFFECTS)
    names = [n for n in (name, name + "_full", name + "_half") if ("\n%s = {" % n) in text]
    return "\n".join(_top_level_block(text, n + " = {") for n in names)


def script_values():
    return _text(VALUES)


def static_modifier(name):
    return _top_level_block(_text(MODIFIERS), name + " = {")


def numbers_after(body, key):
    return re.findall(r"\b%s = (-?\d+(?:\.\d+)?)\b" % key, body)


def strip_comments(text):
    return "\n".join(line.split("#", 1)[0] for line in text.splitlines())


class Event1Wiring(unittest.TestCase):
    def test_options_call_home_backlash_with_shares(self):
        ev = event(".1")
        self.assertIn("covert_backlash_home = { SHARE = full }", option(ev, "covert_warfare.1.a"))
        self.assertIn("covert_backlash_home = { SHARE = half }", option(ev, "covert_warfare.1.b"))

    def test_the_call_is_last_and_unguarded(self):
        # Last, so the tooltip reads abroad (infamy, relations, vigilance,
        # third parties) then home. Unguarded at option level: every gate lives
        # in the effect, and the exposure-tier tests count the option-level
        # `NOT = { covert_exposure_is_costless = yes }` guards exactly.
        ev = event(".1")
        for name, share in (("covert_warfare.1.a", "full"), ("covert_warfare.1.b", "half")):
            opt = option(ev, name)
            call = "covert_backlash_home = { SHARE = %s }" % share
            self.assertRegex(opt, r"\n\t\t%s\n" % re.escape(call))
            self.assertLess(opt.index("covert_exposure_third_party_blowback = yes"), opt.index(call))
            self.assertLess(opt.index("change_relations"), opt.index(call))
            tail = opt[opt.index(call) + len(call):]
            self.assertEqual("", tail[: tail.index("ai_chance")].strip(), "an effect follows the backlash call")

    def test_friend_flag_copied_and_cleared(self):
        ev = event(".1")
        immediate = block(ev, "immediate")
        self.assertIn("iw_burned_friend", immediate)
        self.assertIn("remove_variable = iw_burned_friend", block(ev, "after"))

    def test_friend_flag_is_evaluated_once_after_the_target_is_saved(self):
        immediate = strip_comments(block(event(".1"), "immediate"))
        saved = immediate.index("save_scope_as = detected_by_country")
        call = immediate.index("covert_is_friend = { TARGET = scope:detected_by_country }")
        self.assertLess(saved, call)
        one = immediate.index("name = iw_burned_friend value = 1")
        zero = immediate.index("name = iw_burned_friend value = 0")
        guard = _innermost_enclosing(immediate, "name = iw_burned_friend value = 1", "if = {")
        self.assertIn("covert_is_friend", _limit_of(guard))
        self.assertIn("exists = scope:detected_by_country", _limit_of(guard))
        self.assertNotIn("name = iw_burned_friend value = 0", guard)
        self.assertGreater(zero, one)
        self.assertEqual(2, immediate.count("name = iw_burned_friend"))

    def test_friend_flag_is_removed_outside_the_target_guard(self):
        # Like the other copied variables: a burn whose target has vanished
        # must not leave it behind.
        ev = event(".1")
        after = block(ev, "after")
        guarded = _innermost_enclosing(after, "trigger_event = { id = covert_warfare.2 }", "if = {")
        needle = "remove_variable = iw_burned_friend"
        self.assertTrue(_is_outside(guarded, after, needle))
        removal = _innermost_enclosing(after, needle, "if = {")
        self.assertIn("has_variable = iw_burned_friend", _limit_of(removal))

    def test_public_backlash_runs_in_after_not_in_event_2(self):
        self.assertIn("covert_backlash_public = yes", block(event(".1"), "after"))
        self.assertNotIn("covert_backlash_public", event(".2"))

    def test_public_backlash_sits_between_the_burn_and_the_defenders_event(self):
        after = strip_comments(block(event(".1"), "after"))
        call = "scope:detected_by_country = { covert_backlash_public = yes }"
        self.assertEqual(1, after.count(call))
        at = after.index(call)
        # After the whole dispatch...
        self.assertGreater(at, after.rindex("covert_op_burn = {"))
        # ...before covert_warfare.2 reads iw_last_exposed_public, and before
        # the type code the effect reads is removed.
        self.assertLess(at, after.index("trigger_event = { id = covert_warfare.2 }"))
        self.assertLess(at, after.index("remove_variable = iw_burned_type_code"))
        # ...inside the same guard as the burn: no target, no defender.
        guard = _innermost_enclosing(after, call, "if = {")
        self.assertIn("exists = scope:detected_by_country", _limit_of(guard))


class Effects(unittest.TestCase):
    def test_constant_multipliers_only(self):
        for name in ("covert_backlash_home", "covert_backlash_public"):
            body = effect_family(name)
            found = re.findall(r"multiplier = (\S+)", strip_comments(body))
            self.assertTrue(found, "%s applies no scaled modifier" % name)
            for m in found:
                self.assertRegex(m, r"^\d+(\.\d+)?$", f"{name}: {m}")

    def test_appeasement_amounts(self):
        body = effect_family("covert_backlash_home")
        for n in ("-3", "-5", "-8", "-2", "-4"):
            self.assertIn(f"amount = {n}", body)

    def test_each_share_pairs_amount_and_multiplier_by_tier(self):
        # (mild, moderate, severe) magnitudes for the full share and the half;
        # the appeasement amount and the legitimacy multiplier of a branch are
        # the same size. Moderate is the `else`, so an unrecognised code reads
        # as moderate; severe takes the pre-war war tier with it.
        expected = {"full": (3, 5, 8), "half": (2, 3, 4)}
        for share, (mild, moderate, severe) in expected.items():
            body = strip_comments(scripted_effect("covert_backlash_home_" + share))
            for key, sign in (("amount", "-"), ("multiplier", "")):
                with self.subTest(share=share, key=key):
                    mild_if = _innermost_enclosing(body, "%s = %s%d" % (key, sign, mild), "if = {")
                    self.assertIn("covert_code_tier_mild = { VAR = iw_burned_type_code }", _limit_of(mild_if))
                    severe_if = _innermost_enclosing(body, "%s = %s%d" % (key, sign, severe), "if = {")
                    limit = _limit_of(severe_if)
                    self.assertIn("covert_code_tier_severe = { VAR = iw_burned_type_code }", limit)
                    self.assertIn("covert_code_tier_war = { VAR = iw_burned_type_code }", limit)
                    rest = _innermost_enclosing(body, "%s = %s%d" % (key, sign, moderate), "else = {")
                    self.assertNotIn("covert_code_tier", rest)

    def test_legitimacy_uses_the_timed_decaying_modifier(self):
        for share in ("full", "half"):
            body = scripted_effect("covert_backlash_home_" + share)
            for mod in re.findall(r"add_modifier = \{[^{}]*\}", body):
                self.assertIn("name = covert_friend_spying_scandal", mod)
                self.assertIn("days = short_modifier_time", mod)
                self.assertIn("is_decaying = yes", mod)

    def test_home_gate_needs_a_friend_and_a_costed_exposure(self):
        body = scripted_effect("covert_backlash_home")
        gate = _limit_of(_innermost_enclosing(body, "covert_backlash_home_$SHARE$", "if = {"))
        self.assertIn("has_variable = iw_burned_friend", gate)
        self.assertIn("var:iw_burned_friend = 1", gate)
        self.assertIn("NOT = { covert_exposure_is_costless = yes }", gate)
        self.assertIn("exists = scope:detected_by_country", gate)
        self.assertEqual(1, strip_comments(body).count("covert_backlash_home_$SHARE$ = yes"))

    def test_home_appeasement_targets_the_pro_target_lobbies_with_the_mod_factor(self):
        for share in ("full", "half"):
            body = scripted_effect("covert_backlash_home_" + share)
            self.assertEqual(3, body.count("every_political_lobby = {"))
            self.assertEqual(3, body.count("factor = %s" % FACTOR))
            # Each iteration filters with the shared trigger, plus the one
            # `any_political_lobby` that asks whether there is a lobby at all.
            self.assertEqual(1, body.count("any_political_lobby = {"))
            self.assertEqual(
                4, body.count("covert_backlash_pro_lobby_of = { TARGET = scope:detected_by_country }"),
            )
        # With no such lobby the appeasement line is replaced by a note, and
        # the legitimacy hit still lands.
        for share in ("full", "half"):
            body = scripted_effect("covert_backlash_home_" + share)
            self.assertIn("custom_tooltip = covert_backlash_no_lobby_tt", body)
            note = _innermost_enclosing(body, "custom_tooltip = covert_backlash_no_lobby_tt", "else = {")
            self.assertNotIn("add_modifier", note)
            self.assertIn("any_political_lobby", body)

    def test_pro_lobby_trigger_matches_both_kinds_and_the_target(self):
        trig = _top_level_block(_text(TRIGGERS), "covert_backlash_pro_lobby_of = {")
        self.assertIn("is_political_lobby_type = lobby_pro_country", trig)
        self.assertIn("is_political_lobby_type = lobby_pro_overlord", trig)
        self.assertIn("target = $TARGET$", trig)
        self.assertNotIn("lobby_anti", trig)

    def test_public_reads_the_operators_variables_through_root(self):
        body = strip_comments(scripted_effect("covert_backlash_public"))
        # The defender has no iw_burned_* variables of its own: every tier,
        # friend and costless read has to be wrapped in ROOT = { }.
        for read in ("covert_code_tier_", "covert_exposure_is_costless", "var:iw_burned_friend"):
            for m in re.finditer(re.escape(read), body):
                enclosing = _innermost_enclosing_at(body, m.start(), "ROOT = {")
                self.assertIsNotNone(enclosing, "%s read outside ROOT = { } at offset %d" % (read, m.start()))

    def test_public_multipliers_by_tier_and_friend(self):
        body = strip_comments(scripted_effect("covert_backlash_public"))
        self.assertEqual({"1", "1.5", "2", "3", "4.5"}, set(re.findall(r"multiplier = (\S+)", body)))
        # Friend: 1.5 / 3 / 4.5. Not a friend: 1 / 2 / 3. Each branch lists
        # mild, then severe (with the war tier), then the moderate `else`.
        friend = _innermost_enclosing(body, "var:iw_burned_friend = 1", "if = {")
        self.assertEqual(["1.5", "4.5", "3"], numbers_after(friend, "multiplier"))
        plain = _innermost_enclosing(body, "multiplier = 1 }", "else = {")
        self.assertEqual(["1", "3", "2"], numbers_after(plain, "multiplier"))
        for scope in (friend, plain):
            self.assertIn("covert_code_tier_mild", _limit_of(_innermost_enclosing(
                scope, "multiplier = %s" % numbers_after(scope, "multiplier")[0], "if = {")))
            severe = _innermost_enclosing(
                scope, "multiplier = %s" % numbers_after(scope, "multiplier")[1], "if = {")
            self.assertIn("covert_code_tier_severe", _limit_of(severe))
            self.assertIn("covert_code_tier_war", _limit_of(severe))

    def test_public_applies_modifier_to_the_lobbys_members_only(self):
        body = scripted_effect("covert_backlash_public")
        members = _innermost_enclosing(body, "name = covert_foreign_ties_discredited", "every_lobby_member = {")
        lobby = _innermost_enclosing(body, "every_lobby_member = {", "every_political_lobby = {")
        self.assertIn("covert_backlash_pro_lobby_of = { TARGET = ROOT }", _limit_of(lobby))
        self.assertEqual(6, members.count("name = covert_foreign_ties_discredited"))
        for mod in re.findall(r"add_modifier = \{[^{}]*\}", body):
            self.assertIn("days = short_modifier_time", mod)
            self.assertIn("is_decaying = yes", mod)

    def test_public_sets_the_flag_when_hit_and_clears_it_otherwise(self):
        body = strip_comments(scripted_effect("covert_backlash_public"))
        self.assertEqual(1, body.count("set_variable = { name = iw_last_exposed_public value = 1 }"))
        self.assertEqual(1, body.count("remove_variable = iw_last_exposed_public"))
        # Costless exposures take the clearing branch, so a stale flag from an
        # earlier burn cannot print the public-anger line (iw_last_exposed_*
        # is never cleared, only overwritten).
        setter = _innermost_enclosing(body, "name = iw_last_exposed_public value = 1", "if = {")
        self.assertIn("NOT = { covert_exposure_is_costless = yes }", _limit_of(setter))
        self.assertIn("any_political_lobby", _limit_of(setter))
        clear = _innermost_enclosing(body, "remove_variable = iw_last_exposed_public", "else = {")
        self.assertNotIn("add_modifier", clear)
        self.assertIn("has_variable = iw_last_exposed_public", clear)


def _innermost_enclosing_at(body, target, opener):
    """The `opener { }` block enclosing the offset `target`, or None."""
    best = None
    pos = 0
    while True:
        at = body.find(opener, pos)
        if at == -1 or at > target:
            return best
        start, end = _block_span(body, at)
        if start <= target < end:
            best = (start, end)
        pos = at + 1


class ScriptValues(unittest.TestCase):
    def test_friend_relations_factor(self):
        self.assertIn("covert_exposure_friend_relations_mult = 1.5", script_values())

    def test_friend_factor_is_applied_once_in_the_relations_chain(self):
        # Acknowledge is half of deny (`value = covert_exposure_relations_deny`),
        # so the friend factor belongs in deny alone: in both it would be 2.25.
        deny = strip_comments(_top_level_block(script_values(), "covert_exposure_relations_deny = {"))
        ack = strip_comments(_top_level_block(script_values(), "covert_exposure_relations_acknowledge = {"))
        self.assertIn("value = covert_exposure_relations_deny", ack)
        self.assertNotIn("friend", ack)
        step = _innermost_enclosing(deny, "multiply = covert_exposure_friend_relations_mult", "if = {")
        self.assertIn("has_variable = iw_burned_friend", _limit_of(step))
        self.assertIn("var:iw_burned_friend = 1", _limit_of(step))
        # Before the clamp, so a friend's -40 x 1.5 x 1.5 stays inside it.
        self.assertLess(
            deny.index("covert_exposure_friend_relations_mult"), deny.index("min = -100"))

    def test_infamy_is_not_scaled_by_friendship(self):
        infamy = _top_level_block(script_values(), "covert_exposure_infamy_acknowledge = {")
        self.assertNotIn("friend", infamy)


class DataFiles(unittest.TestCase):
    def test_appeasement_factor_is_always_usable(self):
        raw = APPEASEMENT.read_bytes()
        self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))
        self.assertFalse(raw.startswith(b"\xef\xbb\xbf\xef\xbb\xbf"))
        entry = _top_level_block(_text(APPEASEMENT), FACTOR + " = {")
        # Not listed in any lobby type: the mod cannot edit vanilla's lists, so
        # an always-usable factor is the one the lobby types accept.
        self.assertIn("is_always_usable = yes", entry)
        self.assertIn("duration_to_show = { months = 60 }", entry)

    def test_every_appeasement_call_names_the_defined_factor(self):
        for name in ("covert_backlash_home_full", "covert_backlash_home_half"):
            for factor in re.findall(r"factor = (\S+)", scripted_effect(name)):
                self.assertEqual(FACTOR, factor)

    def test_static_modifiers(self):
        scandal = static_modifier("covert_friend_spying_scandal")
        self.assertIn("country_legitimacy_base_add = -1", scandal)
        self.assertIn("timed_modifier_icons/modifier_documents_negative.dds", scandal)
        ties = static_modifier("covert_foreign_ties_discredited")
        self.assertIn("interest_group_pol_str_mult = -0.05", ties)
        self.assertIn("timed_modifier_icons/modifier_flag_negative.dds", ties)
        # One modifier field each: the multiplier scales everything in a block.
        for entry in (scandal, ties):
            fields = [ln for ln in entry.splitlines()[1:-1] if ln.strip() and "icon" not in ln]
            self.assertEqual(1, len(fields), entry)

    def test_localization(self):
        loc = _loc()
        for key in (
            "covert_friend_spying_scandal",
            "covert_friend_spying_scandal_desc",
            "covert_foreign_ties_discredited",
            "covert_foreign_ties_discredited_desc",
            FACTOR,
            FACTOR + "_desc",
            "covert_backlash_no_lobby_tt",
            "covert_warfare.2.d_public",
            "covert_warfare.2.d_public_unnamed",
        ):
            with self.subTest(key=key):
                self.assertIn(key, loc)
                self.assertTrue(loc[key].strip())
        # Vanilla's factor texts are plain: no country scope to resolve.
        self.assertNotIn("SCOPE", loc[FACTOR])
        self.assertNotIn("SCOPE", loc[FACTOR + "_desc"])
        # Appended to the defender event's text as another paragraph.
        self.assertTrue(loc["covert_warfare.2.d_public"].startswith('"\\n\\n'))
        self.assertTrue(loc["covert_warfare.2.d_public_unnamed"].startswith('"\\n\\n'))
        self.assertIn("sCountry('iw_exposed_by')", loc["covert_warfare.2.d_public"])


class Event2Text(unittest.TestCase):
    def test_desc_appends_the_public_line_as_a_second_child(self):
        ev = event(".2")
        desc = block(ev, "desc")
        # Existing first_valid stays the first child; the public line follows
        # it as a sibling, so the paragraphs concatenate (the shape
        # probe_result_events.txt already ships).
        first = desc.index("first_valid = {")
        public = desc.index("covert_warfare.2.d_public")
        self.assertLess(first, public)
        named = _innermost_enclosing(desc, "desc = covert_warfare.2.d_public\n", "triggered_desc = {")
        self.assertIn("has_variable = iw_last_exposed_public", named)
        self.assertIn("exists = scope:iw_exposed_by", named)
        plain = _innermost_enclosing(desc, "desc = covert_warfare.2.d_public_unnamed", "triggered_desc = {")
        self.assertIn("has_variable = iw_last_exposed_public", plain)
        self.assertNotIn("exists = scope:iw_exposed_by", plain)

    def test_defender_flag_is_documented_with_the_rest_of_the_record(self):
        self.assertIn("iw_last_exposed_public", _text(ON_ACTIONS))


if __name__ == "__main__":
    unittest.main()
