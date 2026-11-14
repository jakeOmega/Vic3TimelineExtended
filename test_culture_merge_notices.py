"""Tests for the culture merges' notices to the other human countries (2026-11-14).

The owner: "notify the player of cultural merges (start and end), with a notification when they are not part of it
(don't have any of the primary cultures, don't hold any homelands) and with an event when they are."

Who is told what (docs/systems/mod_systems/culture_merges.md § The Notices):

| Moment              | A country the merge reaches          | Any other country            | The starter            |
|---------------------|--------------------------------------|------------------------------|------------------------|
| the merge starts    | te_culture_merge.2 (a card)          | te_cm_merge_started_notice   | nothing new            |
| a culture switches  | te_culture_merge.3 (a popup) where   | nothing                      | te_culture_merge.1     |
|                     | it is tied to that culture           |                              |                        |
| the merge completes | te_culture_merge.4, in place of .3   | te_cm_merge_complete_notice  | nothing new            |

Files under test:
* common/scripted_effects/te_culture_merge_effects.txt (te_cm_switch_part's marks, te_cm_tell_start, te_cm_tell_switch,
  te_cm_tell_complete, te_cm_ev_clear_part, te_cm_ev_note_part)
* common/scripted_triggers/te_culture_merge_triggers.txt (te_cm_tied_to)
* the generated te_cmg_<m>_involves, te_cmg_<m>_tell, te_cmg_dominance_all's marks and te_cmg_start_<m>'s call, the
  custom loc te_cm_core_names and the loc te_cmg_<m>_core_names (scripts/generators/gen_culture_merges.py)
* events/te_culture_merge_events.txt (.2, .3, .4), common/messages/extra_messages.txt (the two notices) and their loc

The script can't run offline. The tell effects are run here through a small interpreter of the forms they use, over
made-up countries, so a test asks who hears what rather than what the text looks like.

Run: python3 -m unittest test_culture_merge_notices -v
"""

import itertools
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "generators"))

import culture_merges_config as cfg  # noqa: E402
import gen_culture_merges as gen  # noqa: E402
from je_multiplier_scope_audit import parse_text  # noqa: E402
from test_culture_merge_census import block, slot_cultures, squash, text_of  # noqa: E402
from test_culture_merge_entries import child, children, definitions  # noqa: E402

EFFECTS = ROOT / "common/scripted_effects/te_culture_merge_effects.txt"
TRIGGERS = ROOT / "common/scripted_triggers/te_culture_merge_triggers.txt"
GEN_EFFECTS = ROOT / gen.EFFECTS_GEN_OUT
GEN_TRIGGERS = ROOT / gen.TRIGGERS_GEN_OUT
CUSTOM_LOC = ROOT / gen.CUSTOM_LOC_OUT
EVENTS = ROOT / "events/te_culture_merge_events.txt"
MESSAGES = ROOT / "common/messages/extra_messages.txt"
NOTICES = ("te_cm_merge_started_notice", "te_cm_merge_complete_notice")
NEW_EVENTS = ("te_culture_merge.2", "te_culture_merge.3", "te_culture_merge.4")
BOM = b"\xef\xbb\xbf"


def loc():
    out = {}
    for path in sorted((ROOT / "localization/english").glob("*_l_english.yml")):
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            m = re.match(r' ([\w.\-]+):\d* "(.*)"\s*(?:#.*)?$', line)
            if m:
                out[m.group(1)] = m.group(2)
    return out


LOC = loc()


def joinable(merge):
    return [c for c in slot_cultures(merge) if not (merge.new is None and c == merge.result)]


def helper(name, **args):
    """A hand-written helper's parsed body, its $X$ arguments filled in."""
    text = block(text_of(EFFECTS), name)
    for key, value in args.items():
        text = text.replace("$%s$" % key, value)
    nodes, _ = parse_text(text, name)
    return nodes


# ---------------------------------------------------------------------------------------------------------------
# A small interpreter for the forms the tell effects use. A country is made up: human or AI, the starter or not,
# reached by the merge or not, in the starter's sphere or not, and tied to some cultures (te_cm_tied_to), some of them
# primary. The helpers' own bodies are run as written, so a change to them changes what the tests see.
# ---------------------------------------------------------------------------------------------------------------


class Country:
    def __init__(self, name, ai=False, starter=False, involved=False, sphere=False, tied=(), primary=()):
        self.name, self.ai, self.starter, self.involved, self.sphere = name, ai, starter, involved, sphere
        self.tied, self.primary = set(tied), set(primary)


class Run:
    """One call of a tell effect. `sent` collects (country, what, popup, scopes the event or notice carries)."""

    def __init__(self, key, countries, local_vars=None):
        self.key = key
        self.countries = countries
        self.locals = dict(local_vars or {})
        self.scopes = {}
        self.sent = []
        self.this = None

    # ---- triggers ----
    def holds(self, nodes):
        return all(self.holds_one(n) for n in nodes)

    def holds_one(self, n):
        k, v, c = n.key, n.value, self.this
        if k == "is_ai":
            return c.ai == (v == "yes")
        if k == "NOT":
            return not self.holds(n.children)
        if k == "this" and v == "scope:te_cm_ev_starter":
            return c.starter
        if k.startswith("local_var:"):
            return self.locals[k[len("local_var:"):]] == int(v)
        if k == "te_cmg_%s_involves" % self.key:
            return c.involved == (v == "yes")
        if k == "te_cm_in_sphere":
            return c.sphere == (v == "yes")
        if k == "te_cm_tied_to":
            return child(n, "CULTURE").value in c.tied
        if k == "exists" and v.startswith("scope:"):
            return v[len("scope:"):] in self.scopes
        if k == "country_has_primary_culture" and v.startswith("cu:"):
            return v[len("cu:"):] in c.primary
        raise AssertionError("the interpreter doesn't know %s = %s" % (k, v))

    # ---- effects ----
    def run(self, nodes):
        taken = None  # None: no if-chain open; True/False: whether a branch of the open chain ran
        for n in nodes:
            k = n.key
            if k == "if":
                taken = self.branch(n)
            elif k == "else_if":
                assert taken is not None, "else_if with no if"
                if not taken:
                    taken = self.branch(n)
            elif k == "else":
                assert taken is not None, "else with no if"
                if not taken:
                    self.run(n.children)
                taken = None
            else:
                taken = None
                self.effect(n)

    def branch(self, n):
        limit = child(n, "limit")
        if self.holds(limit.children if limit else []):
            self.run([c for c in n.children if c.key != "limit"])
            return True
        return False

    def effect(self, n):
        k, v = n.key, n.value
        if k == "every_country":
            limit = child(n, "limit")
            for country in self.countries:
                self.this = country
                if self.holds(limit.children if limit else []):
                    self.run([c for c in n.children if c.key != "limit"])
            self.this = None
        elif k in ("save_scope_as", "save_temporary_scope_as"):
            self.scopes[v] = self.this.name if self.this else "starter"
        elif k.startswith(("global_var:", "cu:")) and n.children:
            for c in n.children:
                assert c.key == "save_scope_as", c.key
                self.scopes[c.value] = k
        elif k == "clear_saved_scope":
            self.scopes.pop(v)
        elif k == "trigger_event":
            popup = child(n, "popup")
            self.sent.append((self.this.name, child(n, "id").value, popup is not None and popup.value == "yes",
                              dict(self.scopes)))
        elif k == "post_notification":
            self.sent.append((self.this.name, v, False, dict(self.scopes)))
        elif k == "te_cm_ev_clear_part" and v == "yes":
            self.run(helper("te_cm_ev_clear_part"))
        elif k == "te_cm_ev_note_part":
            self.run(helper("te_cm_ev_note_part", CULTURE=child(n, "CULTURE").value))
        elif k == "te_cm_tell_switch":
            self.run(helper("te_cm_tell_switch", CULTURE=child(n, "CULTURE").value))
        elif k == "te_cm_tell_complete" and v == "yes":
            self.run(helper("te_cm_tell_complete"))
        else:
            raise AssertionError("the interpreter doesn't know the effect %s = %s" % (k, v))


def census(merge, countries, switched=(), done=False):
    """te_cmg_<m>_tell after a pass of te_cmg_dominance_all that switched `switched` and, if `done`, completed."""
    local_vars = {"te_cm_tl_any": 1 if switched else 0, "te_cm_tl_done": int(done)}
    for culture in joinable(merge):
        local_vars["te_cm_tl_%s" % culture] = int(culture in switched)
    run = Run(merge.key, countries, local_vars)
    run.run(definitions(GEN_EFFECTS)["te_cmg_%s_tell" % merge.key].children)
    return run.sent


def start(merge, countries):
    """te_cm_tell_start, as te_cmg_start_<m> calls it, the starter `this`."""
    run = Run(merge.key, countries)
    run.run(helper("te_cm_tell_start", MERGE=merge.key, RESULT=merge.result))
    return run.sent


GERMAN = cfg.merge_by_key("german")


def people():
    """A human and an AI country of every kind the notices tell apart, for the German merge."""
    out = [Country("starter", starter=True, involved=True), Country("ai", ai=True, involved=True, tied={"north_german"})]
    out += [
        Country("far"),                                                       # neither primary nor homeland
        Country("near", involved=True),                                       # reached, no culture switched
        Country("north", involved=True, tied={"north_german"}, primary={"north_german"}),
        Country("north_home", involved=True, tied={"north_german"}),          # holds a homeland only
        Country("both", involved=True, tied={"north_german", "south_german"}, primary={"south_german"}),
        Country("bloc", involved=True, sphere=True, tied={"alemannic"}),
    ]
    return out


class WhoIsToldTest(unittest.TestCase):
    def test_the_start_sends_the_reached_an_event_and_the_rest_a_notice(self):
        sent = start(GERMAN, people())
        by = {name: (what, popup) for name, what, popup, _ in sent}
        self.assertNotIn("starter", by)
        self.assertNotIn("ai", by)
        self.assertEqual(by.pop("far"), ("te_cm_merge_started_notice", False))
        for name, (what, popup) in by.items():
            self.assertEqual((what, popup), ("te_culture_merge.2", False), name)
        self.assertEqual(len(sent), len(people()) - 2)

    def test_the_start_event_knows_the_sphere_from_the_sender(self):
        scopes = {name: s for name, _, _, s in start(GERMAN, people())}
        self.assertIn("te_cm_ev_sphere", scopes["bloc"])
        # Saved for one country, cleared before the next: a later card can't read the bloc member's.
        for name in ("near", "north", "north_home", "both"):
            self.assertNotIn("te_cm_ev_sphere", scopes[name], name)
        for s in scopes.values():
            self.assertIn("te_cm_ev_starter", s)
            self.assertIn("te_cm_ev_result", s)

    def test_a_switch_tells_only_the_countries_tied_to_that_culture(self):
        sent = census(GERMAN, people(), switched={"north_german"})
        self.assertEqual(sorted((n, w, p) for n, w, p, _ in sent),
                         [("both", "te_culture_merge.3", True), ("north", "te_culture_merge.3", True),
                          ("north_home", "te_culture_merge.3", True)])
        scopes = {n: s for n, _, _, s in sent}
        self.assertEqual(scopes["north"]["te_cm_ev_own_part"], "cu:north_german")
        self.assertIn("te_cm_ev_primary", scopes["north"])
        self.assertNotIn("te_cm_ev_primary", scopes["north_home"])   # a homeland, not a primary culture
        self.assertNotIn("te_cm_ev_primary", scopes["both"])         # its primary is South German, which didn't switch

    def test_two_cultures_of_one_country_switching_together_send_one_event_each(self):
        sent = [(n, s["te_cm_ev_own_part"], "te_cm_ev_primary" in s)
                for n, w, _, s in census(GERMAN, people(), switched={"north_german", "south_german"}) if n == "both"]
        self.assertEqual(sent, [("both", "cu:north_german", False), ("both", "cu:south_german", True)])

    def test_a_completion_sends_one_word_to_every_human_country_but_the_starter(self):
        for switched in ({"north_german"}, {"north_german", "south_german"}, {"alemannic"}):
            sent = census(GERMAN, people(), switched=switched, done=True)
            names = [n for n, _, _, _ in sent]
            self.assertEqual(sorted(names), sorted(set(names)), "one word each: %s" % switched)
            self.assertEqual(set(names), {"far", "near", "north", "north_home", "both", "bloc"})
            for name, what, _, _ in sent:
                self.assertEqual(what, "te_cm_merge_complete_notice" if name == "far" else "te_culture_merge.4", name)
            self.assertNotIn("te_culture_merge.3", [w for _, w, _, _ in sent])

    def test_the_completion_event_names_a_culture_of_ours_that_switched_with_it(self):
        sent = {n: (p, s) for n, w, p, s in census(GERMAN, people(), switched={"north_german", "south_german"}, done=True)}
        popup, scopes = sent["both"]
        self.assertTrue(popup)
        self.assertEqual(scopes["te_cm_ev_own_part"], "cu:north_german")   # the first in roster order
        self.assertNotIn("te_cm_ev_primary", scopes)
        popup, scopes = sent["north"]
        self.assertTrue(popup)
        self.assertIn("te_cm_ev_primary", scopes)
        # No culture of its own switched: a card that names none, whatever the country before it was sent.
        for name in ("near", "bloc"):
            popup, scopes = sent[name]
            self.assertFalse(popup, name)
            self.assertNotIn("te_cm_ev_own_part", scopes, name)
            self.assertNotIn("te_cm_ev_primary", scopes, name)

    def test_every_combination_sends_at_most_one_completion_word_and_no_switch_event_with_it(self):
        cultures = joinable(GERMAN)
        for size in range(1, len(cultures) + 1):
            for switched in itertools.combinations(cultures, size):
                for done in (False, True):
                    sent = census(GERMAN, people(), switched=set(switched), done=done)
                    for country in people():
                        mine = [w for n, w, _, _ in sent if n == country.name]
                        if country.ai or country.starter:
                            self.assertEqual(mine, [], country.name)
                        elif done:
                            self.assertEqual(len(mine), 1, (country.name, switched))
                        else:
                            expected = [c for c in cultures if c in switched and c in country.tied]
                            self.assertEqual(mine, ["te_culture_merge.3"] * len(expected), (country.name, switched))

    def test_every_merge_tells_the_same_way(self):
        for merge in cfg.MERGES:
            first = joinable(merge)[0]
            countries = [Country("starter", starter=True, involved=True), Country("far"),
                         Country("tied", involved=True, tied={first}, primary={first})]
            sent = census(merge, countries, switched={first})
            self.assertEqual([(n, w) for n, w, _, _ in sent], [("tied", "te_culture_merge.3")], merge.key)
            sent = census(merge, countries, switched={first}, done=True)
            self.assertEqual(sorted((n, w) for n, w, _, _ in sent),
                             [("far", "te_cm_merge_complete_notice"), ("tied", "te_culture_merge.4")], merge.key)
            sent = start(merge, countries)
            self.assertEqual(sorted((n, w) for n, w, _, _ in sent),
                             [("far", "te_cm_merge_started_notice"), ("tied", "te_culture_merge.2")], merge.key)


class GeneratedTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.triggers = definitions(GEN_TRIGGERS)
        cls.effects_text = text_of(GEN_EFFECTS)

    def test_involves_reads_every_culture_of_the_merge_and_the_homelands_of_its_slots(self):
        for merge in cfg.MERGES:
            body = squash(block(text_of(GEN_TRIGGERS), "te_cmg_%s_involves" % merge.key))
            primary = re.findall(r"country_has_primary_culture = cu:(\w+)", body)
            homeland = re.findall(r"is_homeland = cu:(\w+)", body)
            self.assertEqual(primary, gen.involving_cultures(merge), merge.key)
            self.assertEqual(homeland, slot_cultures(merge), merge.key)
            self.assertEqual(len(primary), len(set(primary)), merge.key)
            self.assertIn(merge.result, primary, merge.key)
            # The homelands are the country's own states, in one walk.
            self.assertEqual(body.count("any_scope_state"), 1, merge.key)
        anglophone = gen.involving_cultures(cfg.merge_by_key("anglophone"))
        self.assertIn("yankee", anglophone)
        self.assertIn("cm_american", anglophone)

    def test_the_dominance_pass_resets_the_marks_then_tells_after_its_last_switch(self):
        body = squash(block(self.effects_text, "te_cmg_dominance_all"))
        for merge in cfg.MERGES:
            key = merge.key
            head = "if = { limit = { OR = { global_var:te_cm_state_%s ?= 1 " % key
            sec = body[body.index(head):]
            resets = ["set_local_variable = { name = te_cm_tl_any value = 0 }",
                      "set_local_variable = { name = te_cm_tl_done value = 0 }"]
            resets += ["set_local_variable = { name = te_cm_tl_%s value = 0 }" % c for c in joinable(merge)]
            tell = "if = { limit = { local_var:te_cm_tl_any = 1 } te_cmg_%s_tell = yes }" % key
            last_switch = "te_cm_switch_part = { MERGE = %s CULTURE = %s RESULT = %s }" % (key, joinable(merge)[-1], merge.result)
            first_switch = "te_cm_census_dominance = { MERGE = %s CULTURE = %s }" % (key, joinable(merge)[0])
            for reset in resets:
                self.assertLess(sec.index(reset), sec.index(first_switch), (key, reset))
            self.assertLess(sec.index(last_switch), sec.index(tell), key)
            self.assertEqual(body.count("te_cmg_%s_tell = yes" % key), 1, key)

    def test_the_switch_marks_what_it_did_for_the_tell(self):
        body = squash(block(text_of(EFFECTS), "te_cm_switch_part"))
        done = ("if = { limit = { global_var:te_cm_state_$MERGE$ ?= 1 te_cmg_$MERGE$_core_switched = yes } "
                "set_global_variable = { name = te_cm_state_$MERGE$ value = 2 } "
                "set_local_variable = { name = te_cm_tl_done value = 1 } }")
        self.assertIn(done, body)
        self.assertEqual(body.count("te_cm_tl_done"), 1)
        marks = ("set_local_variable = { name = te_cm_tl_$CULTURE$ value = 1 } "
                 "set_local_variable = { name = te_cm_tl_any value = 1 }")
        self.assertIn(marks, body)
        # Inside the switch's own guard: a pass that switches nothing marks nothing.
        self.assertTrue(body.startswith("if = { limit = { NOT = { has_global_variable = te_cm_switched_$CULTURE$ } "))
        self.assertTrue(body.endswith("} }"))
        self.assertLess(body.index("set_global_variable = { name = te_cm_switched_$CULTURE$"), body.index(marks))

    def test_every_start_tells_the_others_last(self):
        for merge in cfg.MERGES:
            body = squash(block(self.effects_text, "te_cmg_start_%s" % merge.key))
            call = "te_cm_tell_start = { MERGE = %s RESULT = %s } }" % (merge.key, merge.result)
            self.assertTrue(body.endswith(call + " }") or body.endswith(call), merge.key)
            self.assertLess(body.index("te_cmg_%s_join_ready = yes" % merge.key), body.index("te_cm_tell_start"))
        # Nothing else starts a merge's notices.
        everything = "".join(text_of(p) for d in ("common", "events") for p in (ROOT / d).rglob("*.txt"))
        self.assertEqual(everything.count("te_cm_tell_start = {"), len(cfg.MERGES) + 1)  # the calls and its definition

    def test_only_the_census_sends_the_switch_and_completion_words(self):
        everything = "".join(text_of(p) for d in ("common", "events") for p in (ROOT / d).rglob("*.txt"))
        for merge in cfg.MERGES:
            self.assertEqual(everything.count("te_cmg_%s_tell = yes" % merge.key), 1, merge.key)
        for event in NEW_EVENTS:
            sites = [m.start() for m in re.finditer(r"id = %s\b" % re.escape(event), everything)]
            self.assertTrue(sites, event)
        self.assertEqual(squash(everything).count("id = te_culture_merge.2 }"), 1)
        self.assertEqual(squash(everything).count("id = te_culture_merge.3 popup = yes"), 1)

    def test_the_custom_loc_names_each_merges_core_by_its_result(self):
        self.assertTrue(CUSTOM_LOC.read_bytes().startswith(BOM))
        nodes, _ = parse_text(CUSTOM_LOC.read_text(encoding="utf-8-sig"), CUSTOM_LOC.name)
        names = {n.key: n for n in nodes}
        self.assertEqual(list(names), ["te_cm_core_names"])
        node = names["te_cm_core_names"]
        self.assertEqual(child(node, "type").value, "culture")
        self.assertEqual(child(node, "random_valid").value, "no")
        texts = children(node, "text")
        self.assertEqual(len(texts), len(cfg.MERGES) + 1)
        for merge, text in zip(cfg.MERGES, texts):
            self.assertEqual(child(text, "localization_key").value, "te_cmg_%s_core_names" % merge.key)
            key = "te_cmg_%s_core_names" % merge.key
            self.assertIn(key, LOC)
            # The core cultures but an absorb merge's own result, each spliced, never spelled.
            for part in merge.core:
                if part.cultures[0] == merge.result:
                    self.assertNotIn("$%s$" % merge.result, LOC[key], merge.key)
                else:
                    self.assertIn("$%s$" % part.cultures[0], LOC[key], merge.key)
        self.assertIn("cu:cm_german ?= this", squash(CUSTOM_LOC.read_text(encoding="utf-8-sig")))
        self.assertIsNone(child(texts[-1], "trigger"))
        self.assertIn(child(texts[-1], "localization_key").value, LOC)


class HelperTest(unittest.TestCase):
    def test_the_tied_test_is_a_primary_culture_or_a_homeland_held(self):
        body = squash(block(text_of(TRIGGERS), "te_cm_tied_to"))
        self.assertEqual(body, "OR = { country_has_primary_culture = cu:$CULTURE$ "
                               "any_scope_state = { state_region = { is_homeland = cu:$CULTURE$ } } }")

    def test_only_human_countries_but_the_starter_are_told(self):
        limit = "every_country = { limit = { is_ai = no NOT = { this = scope:te_cm_ev_starter } }"
        self.assertIn(limit, squash(block(text_of(EFFECTS), "te_cm_tell_start")))
        for merge in cfg.MERGES:
            self.assertIn(limit, squash(block(text_of(GEN_EFFECTS), "te_cmg_%s_tell" % merge.key)), merge.key)

    def test_the_starter_is_this_scope_at_the_start_never_the_global_just_set(self):
        # The button's tooltip walks te_cmg_start_<m> every frame and writes nothing, so the global starter is unset there.
        body = squash(block(text_of(EFFECTS), "te_cm_tell_start"))
        self.assertTrue(body.startswith("save_scope_as = te_cm_ev_starter save_temporary_scope_as = te_cm_starter "))
        self.assertNotIn("global_var", body)

    def test_the_events_scopes_are_never_saved_as_temporaries(self):
        # A permanent scope refuses a temporary one of the same name, and the census saves te_cm_starter, te_cm_part
        # and te_cm_result as temporaries in the same on_action as the tells.
        everything = squash("".join(text_of(p) for d in ("common", "events") for p in (ROOT / d).rglob("*.txt")))
        for name in ("te_cm_ev_starter", "te_cm_ev_result", "te_cm_ev_own_part", "te_cm_ev_primary", "te_cm_ev_sphere"):
            self.assertNotIn("save_temporary_scope_as = %s " % name, everything + " ", name)
        for name in ("te_cm_starter", "te_cm_part", "te_cm_result"):
            self.assertNotIn("save_scope_as = %s " % name, everything + " ", name)


class EventsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = text_of(EVENTS)

    def test_the_file_has_one_bom(self):
        raw = EVENTS.read_bytes()
        self.assertTrue(raw.startswith(BOM))
        self.assertFalse(raw[3:].startswith(BOM))

    def test_each_event_has_a_picture_one_option_and_changes_nothing(self):
        for event in NEW_EVENTS:
            body = squash(block(self.text, event))
            self.assertIn("type = country_event", body, event)
            self.assertIn('event_image = { texture = "gfx/event_pictures/', body, event)
            self.assertEqual(body.count("option = {"), 1, event)
            self.assertIn("option = { name = %s.a default_option = yes }" % event, body, event)

    def test_each_text_branch_reads_a_scope_its_sender_saves(self):
        branches = {
            "te_culture_merge.2": ["triggered_desc = { trigger = { exists = scope:te_cm_ev_sphere } desc = te_culture_merge.2.d_sphere }"],
            "te_culture_merge.3": ["triggered_desc = { trigger = { exists = scope:te_cm_ev_primary } desc = te_culture_merge.3.d_primary }"],
            "te_culture_merge.4": [
                "triggered_desc = { trigger = { exists = scope:te_cm_ev_own_part exists = scope:te_cm_ev_primary } "
                "desc = te_culture_merge.4.d_primary }",
                "triggered_desc = { trigger = { exists = scope:te_cm_ev_own_part } desc = te_culture_merge.4.d_homeland }",
            ],
        }
        for event, expected in branches.items():
            body = squash(block(self.text, event))
            for branch in expected:
                self.assertIn(branch, body, event)
            self.assertIn("desc = %s.d } }" % event, body, event)   # the fallback, last
            # Nothing the monthly upkeep changes is read when the event is opened.
            self.assertNotIn("country_has_primary_culture", body, event)
            self.assertNotIn("is_homeland", body, event)

    def test_the_text_names_everything_from_the_saved_scopes(self):
        allowed = {"te_cm_ev_starter", "te_cm_ev_result", "te_cm_ev_own_part"}
        keys = [k for k in LOC if k.split(".")[0] == "te_culture_merge" and k.split(".")[1] in "234"]
        keys += ["notification_%s_%s" % (n, s) for n in NOTICES for s in ("name", "desc", "tooltip")]
        self.assertEqual(len(keys), 16 + 6)
        for key in keys:
            text = LOC[key]
            used = set(re.findall(r"SCOPE\.s(?:Culture|Country)\('(\w+)'\)", text))
            self.assertEqual(used - allowed, set(), key)
            self.assertNotIn("GetCustom", text.replace("GetCustom('te_cm_core_names')", ""), key)
            # Only .3 and .4's branches that name it read the culture of ours; only those are sent with it saved.
            if "te_cm_ev_own_part" in text:
                self.assertTrue(key.startswith(("te_culture_merge.3.", "te_culture_merge.4.d_")), key)
            # The player's word is "culture", never the roster's "part" (culture_merges.md, Player-facing words).
            prose = re.sub(r"\[[^\]]*\]", "", text)
            self.assertNotRegex(prose, r"\bparts?\b", key)
            # Every figure is a script value.
            self.assertNotRegex(prose, r"\d", key)

    def test_the_switch_share_is_the_one_value(self):
        for key in ("te_culture_merge.2.d", "te_culture_merge.2.d_sphere", "te_culture_merge.3.d", "te_culture_merge.3.d_primary"):
            self.assertIn("ScriptValue('te_cm_switch_share')|%0]", LOC[key], key)

    def test_the_notices_are_defined_with_their_texts(self):
        messages = text_of(MESSAGES)
        for name in NOTICES:
            body = squash(block(messages, name))
            self.assertEqual(body, 'type = country texture = "gfx/interface/icons/notification_icons/pops.dds" '
                                   'notification_type = feed color = neutral', name)
            for suffix in ("name", "desc", "tooltip"):
                self.assertIn("notification_%s_%s" % (name, suffix), LOC)


if __name__ == "__main__":
    unittest.main()
