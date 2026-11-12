# -*- coding: utf-8 -*-
"""A Decolonization Resolution's stance goes to the members that voted for it.

Issue #1373: a great power that voted against a carried Decolonization
Resolution is offered only un_vote.3 option A (un_vote_3_can_refuse is false
for the topic since #1568), and option A runs un_vote_apply_treaty_modifier,
whose stance line used to test un_lobby_has_voted, true for a no voter too, so
an outvoted empire took the anti-colonial stance every time. The line now asks
for a yes vote (the orchestrator's call, 2026-11-12).

These tests drive the real script: a small evaluator reads un_vote.3's option
triggers, option A's call and the stance line's limit, with every scripted
trigger they reach expanded from common/scripted_triggers/. An unknown trigger
raises, so a change that adds one fails loudly instead of passing by accident.

Run: python3 -m pytest test_un_decolonization_stance_vote.py -q
"""

import glob
import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
VOTE_EVENTS = os.path.join(REPO, "events", "un_vote_events.txt")
VOTE_EFFECTS = os.path.join(REPO, "common", "scripted_effects", "un_vote_effects.txt")
TRIGGER_GLOB = os.path.join(REPO, "common", "scripted_triggers", "*.txt")

_TOKEN = re.compile(r'"[^"\n]*"|\?=|>=|<=|!=|[{}=<>]|[^\s{}=<>?!"]+')
OPS = ("?=", ">=", "<=", "!=", "=", ">", "<")
RANKS = {"insignificant_power": 1, "minor_power": 2, "unrecognized_major_power": 3,
         "major_power": 4, "unrecognized_regional_power": 3, "great_power": 5}


def _read(path):
    with open(path, encoding="utf-8-sig") as f:
        return re.sub(r"#[^\n]*", "", f.read())


def _parse(text):
    """`key op value` triples; a block value is itself a list of triples."""
    toks = _TOKEN.findall(text)
    pos = 0

    def block():
        nonlocal pos
        out = []
        while pos < len(toks) and toks[pos] != "}":
            key = toks[pos]
            if pos + 1 < len(toks) and toks[pos + 1] in OPS:
                op = toks[pos + 1]
                pos += 2
                if toks[pos] == "{":
                    pos += 1
                    val = block()
                    pos += 1  # the closing brace
                else:
                    val = toks[pos]
                    pos += 1
                out.append((key, op, val))
            else:  # a bare value in a list
                out.append((key, None, None))
                pos += 1
        return out

    return block()


def _get(entries, key):
    return [v for k, _op, v in entries if k == key]


def _triggers():
    defs = {}
    for path in sorted(glob.glob(TRIGGER_GLOB)):
        text = _read(path)
        for m in re.finditer(r"^(\w+)\s*=\s*\{", text, re.M):
            depth, i = 0, m.end() - 1
            for i in range(m.end() - 1, len(text)):
                if text[i] == "{":
                    depth += 1
                elif text[i] == "}":
                    depth -= 1
                    if depth == 0:
                        break
            defs[m.group(1)] = text[m.end():i]
    return defs


class Scope:
    def __init__(self, tags=(), lists=None, rank="great_power", alive=True, **vars_):
        self.tags = set(tags)
        self.lists = lists or {}
        self.rank = rank
        self.alive = alive
        self.vars = vars_


class Evaluator:
    def __init__(self, root, saved):
        self.root = root
        self.saved = saved
        self.defs = _triggers()

    def scope_ref(self, ref, this):
        if ref in ("root", "ROOT"):
            return self.root
        if ref in ("this", "THIS"):
            return this
        if ref.startswith("scope:"):
            return self.saved.get(ref[6:])
        if ref.startswith("var:"):
            return this.vars.get(ref[4:])
        raise AssertionError("unknown scope reference " + ref)

    def all(self, entries, this):
        return all(self.one(k, op, v, this) for k, op, v in entries)

    def one(self, key, op, val, this):
        if key == "AND":
            return self.all(val, this)
        if key == "OR":
            return any(self.one(k, o, v, this) for k, o, v in val)
        if key == "NOT":
            return not self.all(val, this)
        if key == "NOR":
            return not any(self.one(k, o, v, this) for k, o, v in val)
        if key.startswith(("scope:", "var:")) and isinstance(val, list):
            target = self.scope_ref(key, this)
            if target is None:
                if op == "?=":
                    return False
                raise AssertionError(key + " is not set")
            return self.all(val, target)
        if key == "has_tag":
            return val in this.tags
        if key == "has_variable_list":
            return val in this.lists
        if key == "is_target_in_variable_list":
            name = _get(val, "name")[0]
            target = self.scope_ref(_get(val, "target")[0], this)
            return target in this.lists.get(name, ())
        if key == "country_rank":
            want = RANKS[val.split(":")[1]]
            have = RANKS[this.rank]
            return {">=": have >= want, ">": have > want, "<": have < want,
                    "<=": have <= want, "=": have == want}[op]
        if key == "is_country_alive":
            return this.alive == (val == "yes")
        if key == "this" and op == "=":
            return this is self.scope_ref(val, this)
        if key == "always":
            return val == "yes"
        if key in self.defs:
            body = self.defs[key]
            if isinstance(val, list):
                for k, _o, v in val:
                    body = body.replace("$" + k + "$", v)
                wanted = True
            else:
                wanted = val == "yes"
            assert "$" not in body, key + " left an argument unfilled"
            return self.all(_parse(body), this) == wanted
        raise AssertionError("the evaluator does not know " + key)


def _top(text, name):
    for key, _op, val in _parse(text):
        if key == name:
            return val
    raise AssertionError(name + " not found")


def _find_ifs(entries, needle):
    """Every if-block (at any depth) whose own body calls `needle`."""
    found = []
    for key, _op, val in entries:
        if isinstance(val, list):
            if key == "if" and any(k == needle for k, _o, _v in val):
                found.append(val)
            found += _find_ifs(val, needle)
    return found


class DecolonizationStanceVoteTests(unittest.TestCase):

    def setUp(self):
        self.vote3 = _top(_read(VOTE_EVENTS), "un_vote.3")
        self.options = _get(self.vote3, "option")
        self.treaty = _top(_read(VOTE_EFFECTS), "un_vote_apply_treaty_modifier")
        stance = _find_ifs(self.treaty, "custom_tooltip")
        stance = [b for b in stance
                  if any(k == "custom_tooltip" and isinstance(v, list)
                         and ("decol_stance_core_anti", "=", "yes") in v
                         for k, _o, v in b)]
        self.assertEqual(len(stance), 1)
        self.stance_limit = _get(stance[0], "limit")[0]

    def _world(self, voted):
        country = Scope(rank="great_power")
        proposer = Scope(rank="great_power")
        lists = {"un_res_yes": [proposer], "un_res_no": []}
        lists[voted].append(country)
        resolution = Scope(tags={"un_resolution", "un_topic_decolonization", "un_res_passed"},
                           lists=lists, un_res_proposer=proposer)
        ev = Evaluator(country, {"un_resolution": resolution, "un_vote_proposer": proposer})
        return ev, country

    def _offered(self, ev, country):
        offered = []
        for opt in self.options:
            triggers = _get(opt, "trigger")
            offered.append(all(ev.all(t, country) for t in triggers))
        return offered

    def _option_a_takes_stance(self, ev, country):
        option_a = self.options[0]
        calls = _find_ifs(option_a, "un_vote_apply_treaty_modifier")
        self.assertEqual(len(calls), 1)
        if not ev.all(_get(calls[0], "limit")[0], country):
            return False
        return ev.all(self.stance_limit, country)

    def test_a_no_voter_gets_option_a_alone_and_no_stance(self):
        ev, country = self._world("un_res_no")
        self.assertEqual(self._offered(ev, country), [True, False, False])
        self.assertFalse(self._option_a_takes_stance(ev, country))

    def test_a_yes_voter_still_takes_the_stance(self):
        ev, country = self._world("un_res_yes")
        self.assertEqual(self._offered(ev, country), [True, False, False])
        self.assertTrue(self._option_a_takes_stance(ev, country))

    def test_the_proposer_takes_it_as_a_yes_voter(self):
        ev, _country = self._world("un_res_no")
        proposer = ev.saved["un_vote_proposer"]
        ev.root = proposer
        self.assertTrue(ev.all(self.stance_limit, proposer))

    def test_below_great_power_rank_no_stance(self):
        ev, country = self._world("un_res_yes")
        country.rank = "major_power"
        self.assertFalse(ev.all(self.stance_limit, country))


if __name__ == "__main__":
    unittest.main()
