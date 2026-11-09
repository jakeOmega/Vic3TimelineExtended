"""Tests for starting a culture merge: a journal entry, a start button and a progress bar per merge,
the start, join and release helpers, late joining, and the AI pressing the button.

Files under test:
* common/journal_entries/te_culture_merges_generated.txt (generated)
* common/scripted_buttons/te_culture_merges_generated_buttons.txt (generated)
* common/scripted_progress_bars/te_culture_merges_generated_bars.txt (generated)
* common/script_values/te_culture_merges_generated_values.txt (generated)
* the Task 5 additions to the generated triggers and effects, and the hand-written
  te_cm_start_merge / te_cm_join_part / te_cm_release_starter
  (common/scripted_effects/te_culture_merge_effects.txt)
* common/on_actions/te_culture_merge_on_actions.txt (the release of a lost starter)

The script can't be run offline, so the tests read its text: the shape of each block, the order
of its clauses, and that every name an output uses is defined somewhere.

Run: python3 -m unittest test_culture_merge_entries -v
"""

import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "generators"))

import culture_merges_config as cfg  # noqa: E402
import gen_culture_merges as gen  # noqa: E402
import test_add_journal_entry_guard as guard  # noqa: E402
import test_journal_entry_shape as shape  # noqa: E402
from je_multiplier_scope_audit import parse_text  # noqa: E402
from test_culture_merge_census import block, squash, text_of, tier_of, vanilla  # noqa: E402

JE_FILE = ROOT / "common/journal_entries/te_culture_merges_generated.txt"
BUTTONS = ROOT / "common/scripted_buttons/te_culture_merges_generated_buttons.txt"
BARS = ROOT / "common/scripted_progress_bars/te_culture_merges_generated_bars.txt"
VALUES = ROOT / "common/script_values/te_culture_merges_generated_values.txt"
HAND_VALUES = ROOT / "common/script_values/te_culture_merge_values.txt"
DISPLAY_VALUES = ROOT / "common/script_values/te_culture_merge_display_values.txt"
EFFECTS = ROOT / "common/scripted_effects/te_culture_merge_effects.txt"
GEN_EFFECTS = ROOT / "common/scripted_effects/te_culture_merges_generated_effects.txt"
GEN_TRIGGERS = ROOT / "common/scripted_triggers/te_culture_merges_generated_triggers.txt"
ON_ACTIONS = ROOT / "common/on_actions/te_culture_merge_on_actions.txt"
GEN_LOC = ROOT / "localization/english/te_culture_merges_generated_l_english.yml"
MISC_LOC = ROOT / "localization/english/te_miscellaneous_l_english.yml"
VANILLA_LOC = ROOT / "vanilla_parsed/localization_english.json"
NEW_FILES = (JE_FILE, BUTTONS, BARS, VALUES, DISPLAY_VALUES)
BOM = b"\xef\xbb\xbf"


def merge_index(merge):
    return 1 + [m.key for m in cfg.MERGES].index(merge.key)


def slot_cultures(merge):
    return [c for part in merge.core + merge.optional for c in part.cultures]


def absorb_result(merge, culture):
    return merge.new is None and culture == merge.result


def part_of(merge, culture):
    return next(p for p in merge.core + merge.optional if culture in p.cultures)


def idle(key):
    return "NOR = { global_var:te_cm_state_%s ?= 1 global_var:te_cm_state_%s ?= 2 }" % (key, key)


def loc_of(path):
    out = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        match = re.match(r'^ (\S+):(\d+) "(.*)"(?:\s*#.*)?$', line)
        if match:
            out[match.group(1)] = match.group(3)
    return out


def defined_loc():
    """Every loc key the mod defines in English (the generated file and the miscellaneous one are enough here)."""
    return {**loc_of(GEN_LOC), **loc_of(MISC_LOC)}


_ALL_LOC = None


def all_english_loc_keys():
    """Every English loc key the mod defines (all files, replace/ included), for resolving a splice."""
    global _ALL_LOC
    if _ALL_LOC is None:
        _ALL_LOC = set()
        for path in (ROOT / "localization" / "english").rglob("*.yml"):
            _ALL_LOC.update(re.findall(r"^ (\S+?):\d* ", path.read_text(encoding="utf-8-sig"), re.M))
    return _ALL_LOC


def entry_nodes():
    nodes, _ = parse_text(JE_FILE.read_text(encoding="utf-8-sig"), "te_culture_merges_generated.txt")
    return {n.key: n for n in nodes if n.children}


def je_text(key):
    """The text of one entry (comments and BOM removed), for the checks that need the operators the parser drops."""
    return block(text_of(JE_FILE), "je_te_cm_%s" % key)


def inner(text, header):
    """The body of the first `header = {` in text (any indentation), or None."""
    m = re.search(re.escape(header) + r" = \{", text)
    if not m:
        return None
    depth, i = 1, m.end()
    while depth:
        depth += (text[i] == "{") - (text[i] == "}")
        i += 1
    return text[m.end():i - 1]


def child(node, key):
    return next((c for c in node.children if c.key == key), None)


def children(node, key):
    return [c for c in node.children if c.key == key]


# ---------------------------------------------------------------------------------------------------------------
# A small interpreter for the subset of script the generated triggers, effects and values use, so a test can ask
# what a trigger says about a world instead of what its text looks like. It keeps no operator (the parsed tree
# has none), so it is only used on forms that need none: `global_var:x ?= N`, has_*, exists, this, the logic
# blocks, and the script values' value / divide / max / if / else.
# ---------------------------------------------------------------------------------------------------------------


class World:
    """Global variables, which countries live and carry which variables, the technologies known, who is `this`."""

    def __init__(self, globals=None, alive=None, country_vars=None, techs=(), named=None, primary=()):
        self.globals = dict(globals or {})
        self.alive = dict(alive or {})
        self.vars = {c: set(v) for c, v in (country_vars or {}).items()}
        self.techs = set(techs)
        self.named = dict(named or {})
        self.primary = set(primary)
        self.this = None


_DEFS = {}


def definitions(path):
    if path not in _DEFS:
        nodes, _ = parse_text(path.read_text(encoding="utf-8-sig"), path.name)
        _DEFS[path] = {n.key: n for n in nodes if n.children}
    return _DEFS[path]


def holds(nodes, world):
    return all(_holds_one(n, world) for n in nodes)


def _in_scope(world, country, fn):
    saved = world.this
    world.this = country
    try:
        return fn()
    finally:
        world.this = saved


def _holds_one(n, world):
    k, v = n.key, n.value
    if k == "AND":
        return holds(n.children, world)
    if k == "OR":
        return any(_holds_one(c, world) for c in n.children)
    if k in ("NOR",):
        return not any(_holds_one(c, world) for c in n.children)
    if k == "NOT":
        return not holds(n.children, world)
    if k == "always":
        return v == "yes"
    if k == "custom_tooltip":
        return holds([c for c in n.children if c.key != "text"], world)
    if k == "trigger_if":  # passes when its limit fails
        limit = child(n, "limit")
        return not holds(limit.children, world) or holds([c for c in n.children if c.key != "limit"], world)
    if k.startswith("global_var:"):
        name = k.split(":", 1)[1]
        if n.children:  # global_var:x = { is_country_alive = no }
            if name not in world.globals:
                raise AssertionError("scoped into the unset global %s" % name)
            return _in_scope(world, world.globals[name], lambda: holds(n.children, world))
        return str(world.globals.get(name)) == v
    if k == "has_global_variable":
        return v in world.globals
    if k == "has_variable":
        return v in world.vars.get(world.this, set())
    if k == "exists":
        return v.split(":", 1)[1] in world.globals
    if k == "this":
        return world.this == world.globals.get(v.split(":", 1)[1])
    if k == "is_country_alive":
        return world.alive.get(world.this, True) == (v == "yes")
    if k == "country_has_primary_culture":
        return v.split(":", 1)[1] in world.primary
    if k == "te_cm_tier_tech":
        return int(child(n, "TIER").value) in world.techs
    if k in world.named:
        return world.named[k] == (v == "yes")
    for path in (GEN_TRIGGERS, ROOT / "common/scripted_triggers/te_culture_merge_triggers.txt"):
        if k in definitions(path) and v == "yes":
            return holds(definitions(path)[k].children, world)
    raise KeyError("the test interpreter does not know %s" % k)


def run_effects(nodes, world, this):
    """Run if / every_country / set_global_variable / the release helper over a world."""
    for n in nodes:
        k = n.key
        saved = world.this
        world.this = this
        try:
            if k == "if":
                limit = child(n, "limit")
                if holds(limit.children, world):
                    run_effects([c for c in n.children if c.key != "limit"], world, this)
            elif k == "every_country":
                limit = child(n, "limit")
                body = [c for c in n.children if c.key != "limit"]
                for country in sorted(world.alive):
                    world.this = country
                    if holds(limit.children, world):
                        run_effects(body, world, country)
            elif k == "set_global_variable":
                name = child(n, "name").value
                value = child(n, "value").value
                world.globals[name] = this if value == "this" else int(value) if value.isdigit() else value
            elif k == "remove_global_variable":
                world.globals.pop(n.value, None)
            elif k == "remove_variable":
                world.vars.setdefault(this, set()).discard(n.value)
            elif k in ("te_cm_release_starter", "te_cm_unjoin_part"):
                helper = block(text_of(EFFECTS), k)
                for arg in n.children:
                    helper = helper.replace("$%s$" % arg.key, arg.value)
                body, _ = parse_text(helper, "helper")
                run_effects(body, world, this)
            else:
                raise KeyError("the test interpreter does not know %s" % k)
        finally:
            world.this = saved


def value_of(name, world):
    """A generated script value over a world: value / divide / multiply / max / min / if / else, each statement
    acting on the running total, inside an if too."""
    values = definitions(VALUES)
    constants = dict(re.findall(r"^(te_cm_\w+) = ([\d.]+)$", text_of(HAND_VALUES), re.M))

    def number(token):
        if token.startswith("global_var:"):
            return float(world.globals[token.split(":", 1)[1]])
        if token in values:
            return run(values[token].children, 0.0)
        if token in constants:
            return float(constants[token])
        return float(token)

    def run(nodes, total):
        last_if = None
        for n in nodes:
            k = n.key
            if k == "limit":
                continue
            if k == "value":
                total = number(n.value)
            elif k == "divide":
                total /= number(n.value)
            elif k == "multiply":
                total *= number(n.value)
            elif k == "max":
                total = min(total, number(n.value))
            elif k == "min":
                total = max(total, number(n.value))
            elif k == "if":
                last_if = holds(child(n, "limit").children, world)
                if last_if:
                    total = run(n.children, total)
            elif k == "else":
                if not last_if:
                    total = run(n.children, total)
            else:
                raise KeyError("the test interpreter does not know %s" % k)
        return total

    return run(values[name].children, 0.0)


class FilesTest(unittest.TestCase):
    def test_one_bom_tabs_and_header(self):
        for path in NEW_FILES:
            raw = path.read_bytes()
            self.assertTrue(raw.startswith(BOM), path.name)
            self.assertFalse(raw[3:].startswith(BOM), path.name + " has two BOMs")
            lines = raw.decode("utf-8-sig").splitlines()
            for line in lines:
                self.assertFalse(line.startswith(" "), path.name + ": " + line)
            if path is not DISPLAY_VALUES:
                self.assertEqual(lines[0], gen.HEADER, path.name)

    def test_generated_files_are_current(self):
        self.assertFalse(gen.regenerate(dry_run=True)["changed"], "run python3 scripts/generators/gen_culture_merges.py")

    def test_the_new_outputs_are_planned(self):
        planned = set(gen.plan_outputs())
        for path in (JE_FILE, BUTTONS, BARS, VALUES):
            self.assertIn(path.relative_to(ROOT), planned)


class EntryShapeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.entries = entry_nodes()
        cls.triggers = shape.load_triggers()

    def test_entry_shape(self):
        # test_journal_entry_shape's checks over the generated file: no field 1.15 dropped, an activation
        # description, and a disable_evaluation that prunes on a rule conjunct of the gate only.
        self.assertEqual(len(self.entries), len(cfg.MERGES))
        for name, entry in self.entries.items():
            with self.subTest(entry=name):
                self.assertEqual(shape.dropped_fields(entry), [])
                self.assertIsNotNone(shape.child(entry, "activation_description"))
                self.assertEqual(shape.prune_problems(entry, self.triggers), [])

    def test_every_entry_has_a_button_and_bar(self):
        buttons = text_of(BUTTONS)
        bars = text_of(BARS)
        self.assertEqual(set(self.entries), {"je_te_cm_%s" % m.key for m in cfg.MERGES})
        for merge in cfg.MERGES:
            key = merge.key
            entry = self.entries["je_te_cm_%s" % key]
            self.assertEqual([c.value for c in children(entry, "scripted_button")], ["te_cmg_start_%s_button" % key])
            self.assertEqual([c.value for c in children(entry, "scripted_progress_bar")], ["te_cmg_%s_bar" % key])
            self.assertIsNotNone(block(buttons, "te_cmg_start_%s_button" % key), key)
            self.assertIsNotNone(block(bars, "te_cmg_%s_bar" % key), key)
        self.assertEqual(len(re.findall(r"^te_cmg_start_\w+_button = \{", buttons, re.M)), len(cfg.MERGES))
        self.assertEqual(len(re.findall(r"^te_cmg_\w+_bar = \{", bars, re.M)), len(cfg.MERGES))

    def test_the_gate_is_the_rule_then_the_candidate(self):
        # `te_cm_system_enabled = yes` is its own conjunct (test_journal_entry_shape looks for the rule among
        # them), then the candidate; the prune is the rule's negation.
        for merge in cfg.MERGES:
            entry = self.entries["je_te_cm_%s" % merge.key]
            shown = [(c.key, c.value) for c in child(entry, "is_shown_when_inactive").children]
            self.assertEqual(shown, [("te_cm_system_enabled", "yes"), ("te_cmg_%s_is_candidate" % merge.key, "yes")])
            prune = child(entry, "disable_evaluation")
            self.assertEqual(squash(text_of_node(prune)), "NOT = { te_cm_system_enabled = yes }")

    def test_possible_is_the_real_conditions_or_the_starter(self):
        for merge in cfg.MERGES:
            key = merge.key
            entry = self.entries["je_te_cm_%s" % key]
            (possible,) = children(entry, "possible")
            (alt,) = possible.children
            self.assertEqual(alt.key, "OR")
            can_start, starter = alt.children
            self.assertEqual((can_start.key, can_start.value), ("te_cmg_%s_can_start" % key, "yes"))
            # The starter test in a custom_tooltip: bare, the page printed its script ("They are", "has the variable in
            # question") and logged a nullptr promote for the empty starter on every redraw (2026-11-09).
            self.assertEqual(starter.key, "custom_tooltip")
            self.assertEqual([(c.key, c.value) for c in starter.children],
                             [("text", "te_cm_tt_done_starter"), ("te_cmg_%s_is_starter" % key, "yes")])

    def test_stays_active_and_follows_a_revolution(self):
        for name, entry in self.entries.items():
            self.assertEqual(child(entry, "can_deactivate").value, "no", name)
            self.assertEqual(child(entry, "can_revolution_inherit").value, "yes", name)
            self.assertEqual(child(entry, "group").value, "je_group_internal_affairs", name)
            self.assertEqual(child(entry, "progressbar").value, "no", name)
            self.assertEqual(child(entry, "should_be_pinned_by_default_uninvolved_or_context").value, "yes", name)

    def test_a_complete_outcome_for_the_starter_and_a_silent_one_for_another_country(self):
        for merge in cfg.MERGES:
            key = merge.key
            entry = self.entries["je_te_cm_%s" % key]
            complete, invalid = children(entry, "outcome")
            # Complete first: when two are true on the same update the first declared wins.
            self.assertEqual(
                squash(text_of_node(child(complete, "trigger"))),
                # (the parsed tree keeps no operator: `?= 2` reads `= 2`). R5 in full: state 2 AND no joined part left unswitched,
                # each in a custom_tooltip so the panel's "Will complete if" list reads as text, not as the triggers' variables.
                "custom_tooltip = { text = te_cm_tt_done_starter te_cmg_%s_is_starter = yes } "
                "custom_tooltip = { text = te_cmg_%s_done_core_tt global_var:te_cm_state_%s = 2 } "
                "custom_tooltip = { text = te_cm_tt_done_all te_cmg_%s_all_switched = yes }" % (key, key, key, key),
            )
            self.assertEqual(child(complete, "conclusion_desc").value, "je_te_cm_%s_complete_conclusion_desc" % key)
            self.assertIsNone(child(complete, "flags"))
            raw = je_text(key)
            self.assertIn("flags = { hidden invalid_outcome }", raw)
            # R27: no outcome ends the entry for a rule switched off. Off is a pause.
            switches = gen.result_can_switch(merge, cfg.MERGES)
            core_left = bool(gen.core_left_slots(merge, cfg.MERGES))
            if switches or core_left:
                # R36: also a candidate's stranded entry once the merge's result has switched into a wider culture;
                # R38: or once a higher merge has switched one of its core parts.
                stranded = ""
                if switches:
                    stranded += " AND = { te_cmg_%s_result_switched = yes NOT = { te_cmg_%s_is_starter = yes } }" % (key, key)
                if core_left:
                    stranded += " AND = { NOT = { te_cmg_%s_core_left = yes } NOT = { te_cmg_%s_is_starter = yes } }" % (key, key)
                self.assertEqual(
                    squash(child_text(invalid, "trigger")),
                    "OR = { te_cmg_%s_has_other_starter = yes%s }" % (key, stranded),
                )
            else:
                self.assertEqual(squash(child_text(invalid, "trigger")), "te_cmg_%s_has_other_starter = yes" % key)
            self.assertNotIn("te_cm_system_enabled", text_of_node(invalid))

    def test_the_starter_triggers(self):
        # R30: a civil war's winner inherits te_cm_started_<m> and continues the nation, while the global starter
        # still names the dead tag.
        triggers = text_of(GEN_TRIGGERS)
        for merge in cfg.MERGES:
            key = merge.key
            running = "OR = { global_var:te_cm_state_%s ?= 1 global_var:te_cm_state_%s ?= 2 }" % (key, key)
            guard = "trigger_if = { limit = { exists = global_var:te_cm_starter_%s }" % key
            self.assertEqual(
                squash(block(triggers, "te_cmg_%s_starter_gone" % key)),
                guard + " global_var:te_cm_starter_%s = { is_country_alive = no } }" % key,
            )
            self.assertEqual(
                squash(block(triggers, "te_cmg_%s_is_starter" % key)),
                running + " OR = { AND = { exists = global_var:te_cm_starter_%s %s this = global_var:te_cm_starter_%s } } "
                "AND = { has_variable = te_cm_started_%s te_cmg_%s_starter_gone = yes } }" % (key, guard, key, key, key),
            )
            self.assertEqual(
                squash(block(triggers, "te_cmg_%s_has_other_starter" % key)),
                running + " exists = global_var:te_cm_starter_%s %s global_var:te_cm_starter_%s = { is_country_alive = yes } "
                "NOT = { this = global_var:te_cm_starter_%s } } NOT = { has_variable = te_cm_started_%s }"
                % (key, guard, key, key, key),
            )

    def test_every_read_of_a_starter_waits_behind_a_trigger_if(self):
        # A journal entry's tooltip lists every child of an AND, so `exists` beside a read stops nothing there: the
        # French entry's `possible` logged 2,359 each of three script errors and 9,204 loc errors in about twenty seconds
        # of an observer game (2026-11-08), reading te_cm_starter_french, which an idle merge never sets. Only a
        # trigger_if's contents wait for its limit.
        reads = re.compile(r"global_var:te_cm_starter_(\w+)")
        lines = text_of(GEN_TRIGGERS).splitlines()
        stack, bad = [], []
        for number, line in enumerate(lines, 1):
            body = line.split("#", 1)[0].strip()
            m = reads.search(body)
            if m and not body.startswith(("exists = ", "limit = ")):
                guard = "limit = { exists = global_var:te_cm_starter_%s }" % m.group(1)
                if not any(opener == "trigger_if" and limit == guard for opener, limit in stack):
                    bad.append((number, body))
            if body.startswith("limit = ") and stack and stack[-1][0] == "trigger_if":
                stack[-1] = ("trigger_if", body)
            opened, closed = body.count("{"), body.count("}")
            if opened > closed:
                stack.append((body.split("=", 1)[0].strip(), None))
            elif closed > opened:
                del stack[len(stack) - (closed - opened):]
        self.assertEqual(stack, [])
        self.assertEqual(bad, [])

    def test_the_bar_follows_the_progress_each_month_and_pauses_with_the_rule(self):
        for merge in cfg.MERGES:
            key = merge.key
            entry = self.entries["je_te_cm_%s" % key]
            pulse = squash(text_of_node(child(entry, "on_monthly_pulse")))
            self.assertIn("if = { limit = { te_cm_system_enabled = yes }", pulse)
            self.assertIn("set_variable = { name = te_cm_bar_%s value = te_cmg_%s_bar_pct }" % (key, key), pulse)
            self.assertIn(
                "scope:journal_entry = { set_bar_progress = { name = te_cmg_%s_bar value = root.var:te_cm_bar_%s } }" % (key, key),
                pulse,
            )
            self.assertLess(pulse.index("set_variable"), pulse.index("set_bar_progress"))

    def test_an_entry_never_resets_state_in_immediate(self):
        # Merge state is global variables a revolution's winner keeps; an entry with an `immediate` could reset it.
        for name, entry in self.entries.items():
            self.assertIsNone(child(entry, "immediate"), name)


def child_text(node, key):
    return text_of_node(child(node, key))


def text_of_node(node):
    """A parsed node's children as flat script text (enough to compare shapes)."""
    parts = []

    def walk(n):
        if n.children:
            parts.append("%s = {" % n.key)
            for c in n.children:
                walk(c)
            parts.append("}")
        else:
            parts.append("%s = %s" % (n.key, n.value) if n.value is not None else n.key)

    for c in node.children:
        walk(c)
    return " ".join(parts)


class StatusTextTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.entries = entry_nodes()
        cls.loc = defined_loc()

    def rows(self, key):
        """(the fallback desc lines, [(desc key, squashed trigger)]) of the entry's status text, from the raw text
        (the parsed tree has no operators)."""
        first_valid = inner(je_text(key), "first_valid")
        rows = []
        rest = first_valid
        while True:
            body = inner(rest, "triggered_desc")
            if body is None:
                break
            desc = re.search(r"desc = (\w+)", body).group(1)
            rows.append((desc, squash(inner(body, "trigger"))))
            rest = rest[rest.index(body) + len(body) + 1:]
        return first_valid, rows

    def test_one_row_per_state_then_the_first_failing_condition(self):
        for merge in cfg.MERGES:
            key = merge.key
            first_valid, rows = self.rows(key)
            descs = [d for d, _ in rows]
            # The rule being off comes first: is_candidate needs the rule, so any later row would never show with it
            # off, and a starter's running merge pauses (review B, M1). "Ready" closes the list.
            # A standing gate that fails pauses a running or complete merge whole: its row sits after complete (nothing
            # is left to convert there) and before the late and running rows, which would report a stalled merge as under way.
            head = ["te_cm_status_rule_off", "je_te_cm_%s_status_complete" % key]
            if gen.standing_gate(merge):
                head.append("je_te_cm_%s_status_paused" % key)
            head += ["je_te_cm_%s_status_late" % key, "je_te_cm_%s_status_running" % key, "te_cm_status_elsewhere",
                     "te_cm_status_not_candidate", "te_cm_status_unmeasured"]
            self.assertEqual(descs[:len(head)], head, key)
            self.assertEqual(descs[-1], "te_cm_status_ready")
            self.assertEqual(descs.count("te_cm_status_rule_off"), 1)
            # The unconditional fallback, after the last row (the only `desc` that no triggered_desc holds).
            self.assertEqual(squash(inner(je_text(key), "first_valid")).split(" desc = ")[-1], "te_cm_status_pending")
            self.assertTrue(first_valid)
            self.assertEqual(len(descs), len(set(descs)), key)
            # A component merge that hasn't finished comes before any slot (its result is not a part to hold until it
            # has); the standard-of-living row sits after every slot and before the waits.
            sol = descs.index("te_cm_status_sol")
            for index, part in enumerate(merge.core, start=1):
                busy = descs.index("je_te_cm_%s_status_busy_%d" % (key, index))
                self.assertLess(busy, sol)
                for component in merge.components:
                    self.assertLess(descs.index("je_te_cm_%s_status_component_%s" % (key, component)), busy, key)
            for part in gen.core_waits(merge):
                self.assertGreater(descs.index("je_te_cm_%s_status_wait_%s" % (key, part.cultures[0])), sol)
            # The merge's own gate comes after the components and before every slot: it is the history keeping these
            # peoples apart, which a slot's hold row would otherwise hide.
            if merge.gate:
                gate = descs.index("je_te_cm_%s_status_gate" % key)
                self.assertLess(gate, descs.index("je_te_cm_%s_status_busy_1" % key), key)
                for component in merge.components:
                    self.assertGreater(gate, descs.index("je_te_cm_%s_status_component_%s" % (key, component)), key)
            else:
                self.assertNotIn("je_te_cm_%s_status_gate" % key, descs)
            # The complete row needs every joined part switched; the late row is the core's completion with one left.
            rows = dict(self.rows(key)[1])
            self.assertIn("te_cmg_%s_all_switched = yes" % key, rows["je_te_cm_%s_status_complete" % key])
            self.assertNotIn("all_switched", rows["je_te_cm_%s_status_late" % key])
            self.assertIn("global_var:te_cm_state_%s ?= 2" % key, rows["je_te_cm_%s_status_late" % key])

    def test_the_gap_row_names_both_ends_and_the_gap(self):
        # "Too wide" alone left the player to find which cultures (2026-11-09): the row names the best- and worst-off
        # core cultures from the last census, their standards of living and the gap, and the value it must be under.
        for merge in cfg.MERGES:
            key = merge.key
            var = "[ROOT.GetCountry.MakeScope.Var('te_cm_sol_%s_" + key + "')%s]"
            wide = self.loc["je_te_cm_%s_status_sol_wide" % key]
            for name, accessor in (("best", ".GetCulture.GetName"), ("worst", ".GetCulture.GetName"), ("hi", ".GetValue|1"),
                                   ("lo", ".GetValue|1"), ("gap", ".GetValue|1")):
                self.assertIn(var % (name, accessor), wide, key)
            self.assertIn("ScriptValue('te_cm_sol_gap_open')|0]", wide)
            close = self.loc["je_te_cm_%s_status_sol_close" % key]
            self.assertIn(var % ("gap", ".GetValue|1"), close, key)
            self.assertNotIn("GetCulture", close, key)  # one measured culture would be both ends
            # Wide while the gap is at or over the open value; under it with the gate still shut, a slot was unmet at
            # the last census and the next one counts it; with no figure at all, the shared row.
            rows = dict(self.rows(key)[1])
            shut = "NOT = { var:te_cm_sol_ok_%s ?= 1 }" % key
            figure = "has_variable = te_cm_sol_gap_%s" % key
            self.assertEqual(rows["je_te_cm_%s_status_sol_wide" % key],
                             "%s %s var:te_cm_sol_gap_%s >= te_cm_sol_gap_open" % (shut, figure, key))
            self.assertEqual(rows["je_te_cm_%s_status_sol_close" % key], "%s %s" % (shut, figure))
            self.assertEqual(rows["te_cm_status_sol"], shut)
            descs = [d for d, _ in self.rows(key)[1]]
            sol = descs.index("te_cm_status_sol")
            self.assertEqual(descs[sol - 2:sol], ["je_te_cm_%s_status_sol_wide" % key, "je_te_cm_%s_status_sol_close" % key])

    def test_the_gap_condition_names_both_ends_and_the_gap(self):
        # An inactive entry's page lists the start conditions and no status row (2026-11-09), so the gap condition itself
        # carries the figures, read the way vanilla's own entry and button conditions read a country variable.
        for merge in cfg.MERGES:
            key = merge.key
            var = "[ROOT.GetCountry.MakeScope.Var('te_cm_sol_%s_" + key + "')%s]"
            text = self.loc["te_cmg_%s_sol_tt" % key]
            for name, accessor in (("best", ".GetCulture.GetName"), ("worst", ".GetCulture.GetName"), ("hi", ".GetValue|1"),
                                   ("lo", ".GetValue|1"), ("gap", ".GetValue|1")):
                self.assertIn(var % (name, accessor), text, key)
            self.assertIn("ScriptValue('te_cm_sol_gap_open')|0]", text)
            self.assertIn("ScriptValue('te_cm_sol_gap_close')|0]", text)
            # The figures cover only the cultures measured, so a line with a small gap can still be unmet.
            self.assertIn("once every core culture is held and accepted", text)

    def test_running_shows_the_lowest_share_and_the_starters_speed(self):
        # R28: the starter's Culture Merge Speed total, beside the lowest core dominance.
        for merge in cfg.MERGES:
            text = self.loc["je_te_cm_%s_status_running" % merge.key]
            self.assertIn("ScriptValue('te_cmg_%s_lowest_dom')|%%0]" % merge.key, text)
            self.assertIn("ScriptValue('te_cm_speed_display')", text)
            self.assertIn("ScriptValue('te_cm_switch_share')", text)
            # The modifier's name is spliced, never spelled.
            self.assertIn("$country_culture_merge_speed_mult$", text)
            self.assertNotIn("Culture merge speed", text)
            # Once the merge is complete, the late part's share: the lowest over every part that joined.
            late = self.loc["je_te_cm_%s_status_late" % merge.key]
            self.assertIn("ScriptValue('te_cmg_%s_lowest_dom_all')|%%0]" % merge.key, late)
            self.assertIn("$country_culture_merge_speed_mult$", late)
            # The figure hovers to its breakdown by source, in vanilla's tagged form (it reads data).
            for row in (text, late):
                self.assertIn("#tooltippable;tooltip:[GetPlayer.GetTooltipTag],te_cm_speed_tt $country_culture_merge_speed_mult$: +"
                              "[ROOT.GetCountry.MakeScope.ScriptValue('te_cm_speed_display')|%0]#!", row)
        self.assertIn("GetValueWithBreakdownFor('country_culture_merge_speed_mult')", self.loc["te_cm_speed_tt"])
        for source in ("law_public_schools", "institution_ministry_of_culture", "radio", "film", "mass_propaganda"):
            self.assertIn("$%s$" % source, self.loc["te_cm_speed_tt"])
        values = text_of(DISPLAY_VALUES)
        self.assertEqual(squash(block(values, "te_cm_speed_display")), "value = modifier:country_culture_merge_speed_mult")

    def test_a_failing_core_part_names_its_cause(self):
        # Hold, acceptance and (tiers 1b and 2) years each have a row for each core culture, in that order,
        # reading the variable the census wrote and guarding it with has_variable.
        for merge in cfg.MERGES:
            key = merge.key
            _, rows = self.rows(key)
            by_desc = dict(rows)
            for part in merge.core:
                for culture in part.cultures:
                    held = "te_cm_held_%s_%s" % (key, culture)
                    ok = "te_cm_ok_%s_%s" % (key, culture)
                    hold = by_desc["je_te_cm_%s_status_hold_%s" % (key, culture)]
                    self.assertIn("has_variable = %s var:%s < te_cm_hold_open" % (held, held), hold)
                    accept = by_desc["je_te_cm_%s_status_accept_%s" % (key, culture)]
                    self.assertIn("has_variable = %s var:%s = 0" % (ok, ok), accept)
                    years = "je_te_cm_%s_status_years_%s" % (key, culture)
                    if tier_of(merge, culture) > 1:
                        self.assertIn("NOT = { te_cmg_%s_%s_years_met = yes }" % (key, culture), by_desc[years])
                        # The counter is of years held and accepted together, also for the country's own primary culture.
                        self.assertIn("held and accepted together", self.loc[years])
                    else:
                        self.assertNotIn(years, by_desc)
                    start = max(tier_of(merge, p.cultures[0]) for p in merge.core)
                    tech = "je_te_cm_%s_status_tech_%s" % (key, culture)
                    if tier_of(merge, culture) != start:
                        self.assertIn("NOT = { te_cm_tier_tech = { TIER = %d } }" % tier_of(merge, culture), by_desc[tech])
                        self.assertIn("$%s$" % gen.TIER_TECH[tier_of(merge, culture)], self.loc[tech])
                    else:
                        self.assertNotIn(tech, by_desc)
                    # Each row applies only while the slot is unmet, so an earlier slot's failure shows first.
                    self.assertTrue(hold.startswith("NOT = { "), key)
                    descs = [d for d, _ in rows]
                    self.assertLess(
                        descs.index("je_te_cm_%s_status_hold_%s" % (key, culture)),
                        descs.index("je_te_cm_%s_status_accept_%s" % (key, culture)),
                    )

    def test_the_acceptance_line_names_the_threshold_of_its_tier(self):
        text = self.loc["je_te_cm_american_status_accept_yankee"]
        self.assertIn("ScriptValue('te_cm_accept_open')", text)
        # Afro-American is a tier-1b part of American, but optional: no status row. Latin's Spanish is tier 2
        # of the tier-3 merge, held to the usual mark; a tier-1b core part would name the very high one.
        for merge in cfg.MERGES:
            for part in merge.core:
                for culture in part.cultures:
                    text = self.loc["je_te_cm_%s_status_accept_%s" % (merge.key, culture)]
                    want = "te_cm_accept_high_open" if tier_of(merge, culture) == 2 else "te_cm_accept_open"
                    self.assertIn("ScriptValue('%s')" % want, text, "%s %s" % (merge.key, culture))

    def test_a_vanilla_wait_has_a_row_and_a_tooltip(self):
        # One per distinct entry. German and Yugoslav wait on nothing: the fervor copy took R37's waits' place. Brazil's
        # Sulista waits on the Ragamuffin War, its Farroupilha revolt (owner, 2026-11-09).
        waits = [(m, p) for m in cfg.MERGES for p in gen.core_waits(m)]
        self.assertEqual(
            [(m.key, p.cultures[0]) for m, p in waits],
            [("east_slavic", "ukrainian"), ("east_slavic", "byelorussian"), ("american", "dixie"), ("brazilian", "sulista")],
        )
        for key, culture in (("german", "north_german"), ("german", "south_german"), ("yugoslav", "serb")):
            self.assertNotIn("je_te_cm_%s_status_wait_%s" % (key, culture), self.loc)
            self.assertNotIn("te_cmg_%s_wait_%s_tt" % (key, culture), self.loc)
        for merge, part in waits:
            key, culture = merge.key, part.cultures[0]
            self.assertIn("je_te_cm_%s_status_wait_%s" % (key, culture), self.loc)
            self.assertIn("te_cmg_%s_wait_%s_tt" % (key, culture), self.loc)
            for entry in part.wait_for:
                self.assertIn("$%s$" % entry, self.loc["je_te_cm_%s_status_wait_%s" % (key, culture)])


class ButtonTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = text_of(BUTTONS)

    def test_ai_presses_the_button(self):
        for merge in cfg.MERGES:
            body = squash(block(self.text, "te_cmg_start_%s_button" % merge.key))
            self.assertIn("ai_chance = { value = 100 }", body, merge.key)

    def test_visible_while_idle(self):
        for merge in cfg.MERGES:
            body = squash(block(self.text, "te_cmg_start_%s_button" % merge.key))
            self.assertIn("visible = { %s }" % idle(merge.key), body, merge.key)

    def test_every_entry_point_checks_the_rule(self):
        # R19: off pauses everything. Every on_action and every button's `possible` tests te_cm_system_enabled
        # (a button through its first custom_tooltip, which names the rule), and so do the entry's own gate and
        # the census's net.
        on_actions = text_of(ON_ACTIONS)
        for name in re.findall(r"^(\w+) = \{", on_actions, re.M):
            body = squash(block(on_actions, name))
            if name.startswith("on_"):
                self.assertIn("on_actions = {", body, name)  # a hook: the rule is tested by the action it calls
            elif name == "te_cm_fervor_on_action":
                # R41: the fervor copy serves pops that already switched, which stay switched with the rule off, so it
                # runs either way (as the Russification outcome does); test_culture_merge_fervor pins its body.
                self.assertNotIn("te_cm_system_enabled", body, name)
            else:
                self.assertIn("te_cm_system_enabled = yes", body, name)
        for merge in cfg.MERGES:
            body = squash(block(self.text, "te_cmg_start_%s_button" % merge.key))
            possible = body.split("possible = {", 1)[1]
            self.assertTrue(
                possible.lstrip().startswith("custom_tooltip = { text = te_cm_tt_rule_on te_cm_system_enabled = yes }"),
                merge.key,
            )
        entries = entry_nodes()
        for merge in cfg.MERGES:
            entry = entries["je_te_cm_%s" % merge.key]
            self.assertIn("te_cm_system_enabled", text_of_node(child(entry, "disable_evaluation")))
            self.assertIn("te_cm_system_enabled", text_of_node(child(entry, "is_shown_when_inactive")))
            self.assertIn("te_cm_system_enabled", squash(text_of_node(child(entry, "on_monthly_pulse"))))

    def test_possible_starts_with_the_rule_then_can_start_alone(self):
        for merge in cfg.MERGES:
            body = squash(block(self.text, "te_cmg_start_%s_button" % merge.key))
            self.assertIn(
                "possible = { custom_tooltip = { text = te_cm_tt_rule_on te_cm_system_enabled = yes } "
                "te_cmg_%s_can_start = yes } effect" % merge.key,
                body,
            )

    def test_the_effect_starts_the_merge_under_its_tooltip(self):
        for merge in cfg.MERGES:
            body = squash(block(self.text, "te_cmg_start_%s_button" % merge.key))
            self.assertIn(
                "effect = { custom_tooltip = { text = te_cmg_start_%s_effect_tt te_cmg_start_%s = yes } }" % (merge.key, merge.key),
                body,
            )

    def test_every_condition_has_a_reason_in_its_own_custom_tooltip(self):
        # can_start holds each condition in a custom_tooltip, so no raw script reaches the button's tooltip
        # (button_reason_audit). A bare condition outside one would show as script. The one hidden_trigger, that a new
        # result culture exists, shows nothing, and fails only where is_candidate already hides the button.
        triggers = text_of(GEN_TRIGGERS)
        for merge in cfg.MERGES:
            for name in ("te_cmg_%s_can_start" % merge.key, "te_cmg_%s_start_basics" % merge.key):
                body = block(triggers, name)
                if body is None:
                    continue
                depth = 0
                branch = False  # inside a trigger_if or trigger_else, whose conditions sit one level down
                for line in body.splitlines():
                    stripped = line.strip()
                    if depth == 0 and stripped:
                        branch = stripped.startswith(("trigger_if = {", "trigger_else = {"))
                        if not branch and not stripped.startswith(("custom_tooltip = {", "te_cmg_", "hidden_trigger = {")):
                            self.fail("%s: a bare condition in %s: %s" % (merge.key, name, stripped))
                    elif depth == 1 and branch and stripped != "}" and not stripped.startswith(("limit = {", "custom_tooltip = {")):
                        self.fail("%s: a bare condition in a branch of %s: %s" % (merge.key, name, stripped))
                    depth += line.count("{") - line.count("}")
                self.assertEqual(depth, 0)


class CanStartTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.triggers = text_of(GEN_TRIGGERS)

    def items(self, key):
        """The custom_tooltips of can_start (through start_basics), as (text key, squashed body)."""
        body = block(self.triggers, "te_cmg_%s_can_start" % key)
        basics = block(self.triggers, "te_cmg_%s_start_basics" % key)
        text = (basics or "") + "\n" + body
        out = []
        for match in re.finditer(r"custom_tooltip = \{\n\s*text = (\w+)\n", text):
            depth, i = 1, match.end()
            start = i
            while depth:
                depth += (text[i] == "{") - (text[i] == "}")
                i += 1
            out.append((match.group(1), squash(text[start:i - 1])))
        return out

    def test_the_conditions_are_the_candidates_the_slots_the_gap_and_the_components(self):
        for merge in cfg.MERGES:
            key = merge.key
            items = self.items(key)
            texts = [t for t, _ in items]
            tier = max(tier_of(merge, p.cultures[0]) for p in merge.core)
            # R36: right after the idle test, a merge whose result can switch into a wider culture says that result has
            # not, and the Brazilian merge, which steps aside where vanilla's nation building runs, says that content is off.
            head = ["te_cm_tt_idle"]
            if gen.result_can_switch(merge, cfg.MERGES):
                head.append("te_cm_tt_result_not_merged_on")
            if merge.skip_if_dlc:
                head.append("te_cm_tt_dlc_off_%s" % merge.skip_if_dlc)
            head += ["te_cmg_%s_primary_tt" % key, "te_cm_tt_tech_%d" % tier]
            # The merge's own gate follows the technology (owner, 2026-11-09).
            if merge.gate:
                head.append("te_cmg_%s_gate_tt" % key)
            self.assertEqual(
                texts[:len(head) + len(merge.core)],
                head + ["te_cmg_%s_core_%d_tt" % (key, i) for i in range(1, len(merge.core) + 1)],
                key,
            )
            tail = texts[len(head) + len(merge.core):]
            waits = ["te_cmg_%s_wait_%s_tt" % (key, p.cultures[0]) for p in gen.core_waits(merge)]
            self.assertEqual(
                tail,
                ["te_cmg_%s_sol_tt" % key, "te_cm_tt_sol"] + ["te_cmg_%s_comp_%s_tt" % (key, c) for c in merge.components] + waits,
                key,
            )
            by_text = dict(items)
            self.assertEqual(by_text["te_cm_tt_idle"], idle(key))
            # The gap line names its figures once the census has kept them, and the generic line stands in until then;
            # both test the one gate, and the trigger_else follows its trigger_if (a trigger_if whose limit fails passes).
            gate = "var:te_cm_sol_ok_%s ?= 1" % key
            self.assertEqual(by_text["te_cmg_%s_sol_tt" % key], gate)
            self.assertEqual(by_text["te_cm_tt_sol"], gate)
            self.assertIn(
                "trigger_if = { limit = { has_variable = te_cm_sol_gap_%s } custom_tooltip = { text = te_cmg_%s_sol_tt %s } } "
                "trigger_else = { custom_tooltip = { text = te_cm_tt_sol %s } }" % (key, key, gate, gate),
                squash((block(self.triggers, "te_cmg_%s_start_basics" % key) or "") + "\n" + block(self.triggers, "te_cmg_%s_can_start" % key)),
                key,
            )
            for component in merge.components:
                self.assertEqual(by_text["te_cmg_%s_comp_%s_tt" % (key, component)], "global_var:te_cm_state_%s ?= 2" % component)

    def test_can_start_restates_the_candidates_tests_and_core_oks_slots(self):
        # is_candidate and core_ok are Task 4's, can_start restates them in tooltips; they must not drift.
        for merge in cfg.MERGES:
            key = merge.key
            by_text = dict(self.items(key))
            candidate = squash(block(self.triggers, "te_cmg_%s_is_candidate" % key))
            primary = by_text["te_cmg_%s_primary_tt" % key]
            self.assertIn(primary, candidate, key)
            self.assertIn(by_text["te_cm_tt_tech_%d" % max(tier_of(merge, p.cultures[0]) for p in merge.core)], candidate, key)
            core_ok = squash(block(self.triggers, "te_cmg_%s_core_ok" % key))
            slots = " ".join(by_text["te_cmg_%s_core_%d_tt" % (key, i)] for i in range(1, len(merge.core) + 1))
            self.assertEqual(slots, core_ok, key)

    def test_waits_are_capped(self):
        # Each wait-listed vanilla entry on a core part is in can_start, OR'd with the cap, and read in any
        # country (R37), not only the candidate's.
        for merge in cfg.MERGES:
            key = merge.key
            body = squash(block(self.triggers, "te_cmg_%s_can_start" % key))
            counter = "te_cm_wait_years_%s" % key
            for part in merge.core:
                for entry in part.wait_for:
                    self.assertIn("has_journal_entry = %s" % entry, body, key)
            for part in gen.core_waits(merge):
                self.assertIn(
                    "text = te_cmg_%s_wait_%s_tt OR = { NOT = { any_country = { has_journal_entry = %s } } AND = { has_variable = %s "
                    "trigger_if = { limit = { has_variable = %s } var:%s >= te_cm_wait_cap_years } } }"
                    % (key, part.cultures[0], part.wait_for[0], counter, counter, counter),
                    body,
                    key,
                )
            if not any(p.wait_for for p in merge.core):
                self.assertNotIn("te_cm_wait_cap_years", body, key)
                self.assertIsNone(block(self.triggers, "te_cmg_%s_start_basics" % key), key)
        # An optional part's wait never gates the start (American's Afro-American, Anglophone's two).
        self.assertNotIn("je_acw_equality", block(self.triggers, "te_cmg_american_can_start"))
        self.assertNotIn("je_acw_reincorporate", block(self.triggers, "te_cmg_anglophone_can_start"))

    def test_every_wait_reads_any_country(self):
        # R37: a switch turns the part's pops into the result in every country, and the entry reads their fervor
        # or share there, so a wait holds while ANY country has the entry active. A bare `has_journal_entry` of a
        # wait-listed entry in the generated triggers and effects would be the candidate's alone.
        text = squash(text_of(GEN_TRIGGERS)) + " " + squash(text_of(GEN_EFFECTS))
        entries = {e for m in cfg.MERGES for p in m.core + m.optional for e in p.wait_for}
        self.assertIn("je_ukraine_cultural_renaissance", entries)
        self.assertIn("je_acw_reincorporate", entries)
        unwrapped = re.sub(r"any_country = \{ (?:OR = \{ )?(?:has_journal_entry = \w+ )+\}(?: \})?", "", text)
        for entry in sorted(entries):
            self.assertIn("any_country = { has_journal_entry = %s }" % entry, text, entry)
            self.assertNotIn("has_journal_entry = %s" % entry, unwrapped, "%s is read for one country" % entry)

    def test_two_core_parts_on_one_entry_share_a_wait_but_each_has_a_join_gate(self):
        # No merge in the roster has two core parts on one entry since German's waits gave way to the fervor copy, so a
        # roster of one pins it: the start shows one wait row per distinct entry, and each part keeps its own gate.
        shared = cfg.Merge(
            "shared", "cm_shared", cfg.MERGES[0].new,
            core=(cfg.Part(("north_german",), None, ("je_x",)), cfg.Part(("south_german",), None, ("je_x",))),
        )
        self.assertEqual([p.cultures[0] for p in gen.core_waits(shared)], ["north_german"])
        rendered = gen.render_triggers(gen.load_vanilla(), (shared,))
        triggers = "\n".join(line.split("#", 1)[0].rstrip() for line in rendered.splitlines())
        for culture in ("north_german", "south_german"):
            self.assertIsNotNone(block(triggers, "te_cmg_shared_%s_waiting" % culture), culture)
        # Distinct entries keep a wait each.
        self.assertEqual(
            [p.cultures[0] for p in gen.core_waits(cfg.merge_by_key("east_slavic"))], ["ukrainian", "byelorussian"]
        )

    def test_a_waiting_part_is_waiting_only_until_the_cap(self):
        for merge in cfg.MERGES:
            for culture in slot_cultures(merge):
                waiting = block(self.triggers, "te_cmg_%s_%s_waiting" % (merge.key, culture))
                wait_for = part_of(merge, culture).wait_for
                if not wait_for or absorb_result(merge, culture):
                    self.assertIsNone(waiting, "%s %s" % (merge.key, culture))
                    continue
                flat = squash(waiting)
                counter = "te_cm_wait_years_%s" % merge.key
                self.assertTrue(
                    flat.startswith("any_country = { has_journal_entry = %s } NOT = { AND = { has_variable = %s" % (wait_for[0], counter)), flat
                )
                self.assertIn("var:%s >= te_cm_wait_cap_years" % counter, flat)

    def test_colonial_holders_cannot_start(self):
        # A holder of Javan, Malay, Sumatran or Bornean as colonial subjects has none of them as a primary
        # culture: the Dutch East Indies' owner is not an Indonesian candidate.
        body = squash(block(self.triggers, "te_cmg_indonesian_is_candidate"))
        self.assertIn("country_has_primary_culture = cu:javan", body)
        self.assertIn("OR = { country_has_primary_culture = cu:javan", body)
        self.assertNotIn("culture_percent_country", body)
        primary = dict(self.items("indonesian"))["te_cmg_indonesian_primary_tt"]
        self.assertIn(primary, body)

    def test_a_candidate_start_is_idle(self):
        # A running or complete merge can't be started a second time, from the entry or the button.
        for merge in cfg.MERGES:
            self.assertEqual(self.items(merge.key)[0], ("te_cm_tt_idle", idle(merge.key)))


class HelpersTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = text_of(EFFECTS)

    def test_start_merge(self):
        body = squash(block(self.text, "te_cm_start_merge"))
        self.assertEqual(
            body,
            "set_global_variable = { name = te_cm_state_$MERGE$ value = 1 } "
            "set_global_variable = { name = te_cm_starter_$MERGE$ value = this } "
            "set_variable = { name = te_cm_started_$MERGE$ value = 1 } "
            "if = { limit = { NOT = { country_has_primary_culture = cu:$RESULT$ } } add_primary_culture = cu:$RESULT$ }",
        )

    def test_join_part(self):
        body = squash(block(self.text, "te_cm_join_part"))
        self.assertEqual(
            body,
            "set_global_variable = { name = te_cm_joined_$MERGE$_$CULTURE$ value = 1 } "
            "set_global_variable = { name = te_cm_in_$CULTURE$ value = $INDEX$ }",
        )

    def test_release_goes_back_to_idle_and_keeps_everything_else(self):
        body = squash(block(self.text, "te_cm_release_starter"))
        self.assertEqual(
            body,
            "set_global_variable = { name = te_cm_state_$MERGE$ value = 0 } "
            "if = { limit = { has_global_variable = te_cm_starter_$MERGE$ } remove_global_variable = te_cm_starter_$MERGE$ } "
            "every_country = { limit = { has_variable = te_cm_started_$MERGE$ } remove_variable = te_cm_started_$MERGE$ }",
        )
        # Joined parts, dominance and counters stay: nothing but the starter and its flag is removed or unset.
        self.assertEqual(body.count("remove_global_variable"), 1)
        self.assertEqual(body.count("remove_variable"), 1)
        for kept in ("te_cm_joined_", "te_cm_in_", "te_cm_dom_", "te_cm_years_", "te_cm_wait_years_", "te_cm_home_"):
            self.assertNotIn(kept, body)

    def test_the_helpers_use_the_variables_the_gates_read(self):
        # Every global the helpers write is one the generated triggers read, spelled the same way.
        triggers = text_of(GEN_TRIGGERS)
        self.assertIn("global_var:te_cm_state_german ?= 1", triggers)
        self.assertIn("global_var:te_cm_starter_german", triggers)
        self.assertIn("global_var:te_cm_joined_german_north_german ?= 1", triggers)
        self.assertIn("global_var:te_cm_in_yankee ?= 12", triggers)

    def test_no_helper_takes_an_argument_it_never_names(self):
        for name, args in (
            ("te_cm_start_merge", ("MERGE", "RESULT")),
            ("te_cm_join_part", ("MERGE", "CULTURE", "INDEX")),
            ("te_cm_release_starter", ("MERGE",)),
        ):
            body = block(self.text, name)
            for arg in args:
                self.assertIn("$%s$" % arg, body, name + " " + arg)
        self.assertNotIn("$INDEX$", block(self.text, "te_cm_start_merge"))

    def test_every_call_matches_its_helper(self):
        import script_argument_audit

        result = script_argument_audit.audit(mod_path=str(ROOT), vanilla_game=None)
        mine = {str(p.relative_to(ROOT)) for p in (EFFECTS, GEN_EFFECTS, GEN_TRIGGERS, ON_ACTIONS, BUTTONS, JE_FILE)}
        self.assertEqual([(f.file, f.line, f.callee) for f in result.flags if f.file in mine], [])
        called = {name for name, calls in result.call_sites.items() if any(c.file in mine for c in calls)}
        for helper in ("te_cm_start_merge", "te_cm_join_part", "te_cm_release_starter"):
            self.assertIn(helper, called, helper)


class StarterLossTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.effects = text_of(GEN_EFFECTS)
        cls.on_actions = text_of(ON_ACTIONS)

    def test_starter_loss_returns_merge_to_idle(self):
        # The yearly on_action runs the release of every running merge whose starter no longer exists, first.
        flat = squash(block(self.on_actions, "te_cm_yearly_on_action"))
        self.assertIn("te_cmg_release_lost_starters = yes", flat)
        self.assertLess(flat.index("te_cmg_release_lost_starters = yes"), flat.index("te_cmg_census_all = yes"))
        self.assertEqual(flat.count("te_cmg_release_lost_starters = yes"), 1)
        body = squash(block(self.effects, "te_cmg_release_lost_starters"))
        for merge in cfg.MERGES:
            key = merge.key
            self.assertEqual(body.count("te_cm_release_starter = { MERGE = %s }" % key), 1, key)
            # Only a running merge, and only while the starter is gone (re-evaluated after the re-point above it).
            self.assertIn(
                "if = { limit = { global_var:te_cm_state_%s ?= 1 te_cmg_%s_starter_gone = yes } "
                "te_cm_release_starter = { MERGE = %s } }" % (key, key, key),
                body,
                key,
            )

    def test_a_dead_starter_is_released_as_well_as_a_missing_one(self):
        # The task 4 review: a country that lost every state still resolves, so its absence can't be the only test.
        for merge in cfg.MERGES:
            gone = definitions(GEN_TRIGGERS)["te_cmg_%s_starter_gone" % merge.key].children
            starter = "te_cm_starter_%s" % merge.key
            self.assertTrue(holds(gone, World()), merge.key)
            self.assertTrue(holds(gone, World(globals={starter: "FRA"}, alive={"FRA": False})), merge.key)
            self.assertFalse(holds(gone, World(globals={starter: "FRA"}, alive={"FRA": True})), merge.key)

    def test_a_flag_holder_takes_the_merge_over_before_it_is_released(self):
        # R30: the re-point comes first, in the same pass, and the release only follows if it found nobody.
        body = squash(block(self.effects, "te_cmg_release_lost_starters"))
        for merge in cfg.MERGES:
            key = merge.key
            repoint = (
                "if = { limit = { OR = { global_var:te_cm_state_%s ?= 1 global_var:te_cm_state_%s ?= 2 } "
                "te_cmg_%s_starter_gone = yes } every_country = { limit = { is_country_alive = yes has_variable = te_cm_started_%s } "
                "if = { limit = { te_cmg_%s_starter_gone = yes } set_global_variable = { name = te_cm_starter_%s value = this } } } }"
                % (key, key, key, key, key, key)
            )
            self.assertEqual(body.count(repoint), 1, key)
            self.assertLess(body.index(repoint), body.index("te_cm_release_starter = { MERGE = %s }" % key), key)
            self.assertEqual(body.count("name = te_cm_starter_%s value = this" % key), 1, key)

    def test_only_a_running_merge_is_released(self):
        # A complete merge keeps its state with its starter gone; releasing it would let the merge start twice.
        body = squash(block(self.effects, "te_cmg_release_lost_starters"))
        for merge in cfg.MERGES:
            key = merge.key
            self.assertEqual(body.count("global_var:te_cm_state_%s ?= 1 te_cmg_%s_starter_gone = yes } te_cm_release_starter" % (key, key)), 1)

    def test_losing_the_result_as_primary_is_not_a_release(self):
        body = squash(block(self.effects, "te_cmg_release_lost_starters"))
        self.assertNotIn("country_has_primary_culture", body)

    def test_the_release_runs_behind_the_rule_and_the_year(self):
        flat = squash(block(self.on_actions, "te_cm_yearly_on_action"))
        self.assertLess(flat.index("te_cm_system_enabled = yes"), flat.index("te_cmg_release_lost_starters = yes"))
        self.assertLess(flat.index("name = te_cm_census_year"), flat.index("te_cmg_release_lost_starters = yes"))


class CensusTailTest(unittest.TestCase):
    """What the per-country census does after the gates: wait years, the entry net, late joins."""

    @classmethod
    def setUpClass(cls):
        cls.effects = text_of(GEN_EFFECTS)

    def settle(self, key):
        return squash(block(self.effects, "te_cmg_%s_settle" % key))

    def test_the_census_ends_in_the_settle_of_its_merge(self):
        for merge in cfg.MERGES:
            body = squash(block(self.effects, "te_cmg_census_%s_country" % merge.key))
            self.assertTrue(body.endswith("te_cmg_%s_settle = yes" % merge.key), merge.key)
            self.assertEqual(body.count("_settle = yes"), 1)

    def test_late_joining_runs_for_the_starter_of_a_running_or_complete_merge(self):
        for merge in cfg.MERGES:
            key = merge.key
            self.assertTrue(
                self.settle(key).endswith("if = { limit = { te_cmg_%s_is_starter = yes } te_cmg_%s_join_ready = yes }" % (key, key)), key
            )

    def test_join_ready_joins_each_qualifying_part_that_isnt_waiting_and_never_the_result(self):
        for merge in cfg.MERGES:
            key = merge.key
            body = squash(block(self.effects, "te_cmg_%s_join_ready" % key))
            for culture in slot_cultures(merge):
                call = "te_cm_join_part = { MERGE = %s CULTURE = %s INDEX = %d }" % (key, culture, merge_index(merge))
                if absorb_result(merge, culture):
                    self.assertNotIn("CULTURE = %s " % culture, body, key)
                    continue
                waiting = ""
                if part_of(merge, culture).wait_for:
                    waiting = " NOT = { te_cmg_%s_%s_waiting = yes }" % (key, culture)
                self.assertIn(
                    "if = { limit = { te_cmg_%s_%s_can_join = yes%s } %s }" % (key, culture, waiting, call), body, "%s %s" % (key, culture)
                )
            self.assertEqual(body.count("te_cm_join_part"), len([c for c in slot_cultures(merge) if not absorb_result(merge, c)]))

    def test_the_index_is_the_position_in_the_roster(self):
        # te_cm_in_<c> holds it, and te_cmg_<m>_<c>_available tests the others' (Task 4).
        triggers = text_of(GEN_TRIGGERS)
        index = merge_index(cfg.merge_by_key("american"))
        self.assertEqual(index, 12)
        self.assertIn("te_cm_in_yankee ?= %d" % index, triggers)
        self.assertIn("INDEX = %d" % index, squash(block(self.effects, "te_cmg_american_join_ready")))

    def test_the_button_starts_then_joins_and_only_an_idle_merge(self):
        # A second click on the same day, or the AI's, finds the merge already running.
        for merge in cfg.MERGES:
            key = merge.key
            # R36: a merge whose result can switch into a wider culture is not started once it has.
            guard = idle(key)
            if gen.result_can_switch(merge, cfg.MERGES):
                guard += " NOT = { te_cmg_%s_result_switched = yes }" % key
            # A milestone gate held, since can_start did: the start latches it, as the census would.
            latch = " set_variable = { name = te_cm_gate_met_%s value = 1 }" % key if gen.milestone_gate(merge) else ""
            self.assertEqual(
                squash(block(self.effects, "te_cmg_start_%s" % key)),
                "if = { limit = { %s } te_cm_start_merge = { MERGE = %s RESULT = %s }%s te_cmg_%s_join_ready = yes }"
                % (guard, key, merge.result, latch, key),
            )

    def test_a_wait_year_counts_once_a_census_while_the_merge_could_start_and_an_entry_is_open(self):
        for merge in cfg.MERGES:
            key = merge.key
            body = self.settle(key)
            counter = "te_cm_wait_years_%s" % key
            waits = gen.core_waits(merge)
            if not waits:
                self.assertNotIn(counter, body, key)
                continue
            opened = "OR = { %s }" % " ".join("any_country = { has_journal_entry = %s }" % p.wait_for[0] for p in waits)
            self.assertTrue(all(len(p.wait_for) == 1 for p in waits), "a part with two entries nests an OR; extend the test")
            self.assertTrue(
                body.startswith(
                    "if = { limit = { te_cmg_%s_start_basics = yes %s } "
                    "if = { limit = { NOT = { has_variable = %s } } set_variable = { name = %s value = 0 } } "
                    "if = { limit = { var:%s < te_cm_wait_cap_years } change_variable = { name = %s add = 1 } } }"
                    % (key, opened, counter, counter, counter, counter)
                ),
                body,
            )
        # The counter only rises: the one set is to 0 when it is missing, nothing removes it, and the cap is an
        # explicit test (change_variable's own min and max are a guess, change_variable_clamp_audit).
        for path in (EFFECTS, GEN_EFFECTS):
            text = text_of(path)
            self.assertEqual({v for _, v in re.findall(r"set_variable = \{ name = (te_cm_wait_years_\w+) value = (\S+) \}", text)} - {"0"}, set())
            self.assertNotRegex(text, r"remove_variable = te_cm_wait_years")
            self.assertNotRegex(text, r"change_variable = \{[^}]*te_cm_wait_years[^}]*(min|max) =")

    def test_the_entry_net_skips_an_inactive_copy_and_reads_the_entrys_own_gate(self):
        # R20: an idle merge's candidate that can start, or a running merge's starter, gets the entry back if it
        # holds neither the active nor the inactive record.
        for merge in cfg.MERGES:
            key = merge.key
            entry = "je_te_cm_%s" % key
            body = self.settle(key)
            net = (
                "if = { limit = { te_cm_system_enabled = yes NOT = { has_journal_entry = %s } NOT = { has_inactive_journal_entry = %s } "
                "OR = { te_cmg_%s_can_start = yes AND = { global_var:te_cm_state_%s ?= 1 te_cmg_%s_is_starter = yes } } } "
                "add_journal_entry = { type = %s } }" % (entry, entry, key, key, key, entry)
            )
            self.assertIn(net, body, key)
            self.assertEqual(body.count("add_journal_entry"), 1)

    def test_a_complete_merge_gets_no_entry_back(self):
        # Its finished entry is its end; a new one would conclude at once and fire the outcome every year.
        for merge in cfg.MERGES:
            self.assertNotIn("?= 2", self.settle(merge.key), merge.key)

    def test_the_net_passes_the_inactive_copy_guard_test(self):
        flags, stale = guard.audit_text(GEN_EFFECTS.read_text(encoding="utf-8-sig"), "te_culture_merges_generated_effects.txt",
                                        guard.load_entries(), guard.load_triggers())
        self.assertEqual(flags, [])
        self.assertEqual(stale, [])
        text = GEN_EFFECTS.read_text(encoding="utf-8-sig")
        self.assertEqual(text.count("add_journal_entry"), len(cfg.MERGES))
        # And every added type is an entry that exists.
        types = set(re.findall(r"add_journal_entry = \{ type = (\w+) \}", text))
        self.assertEqual(types, {"je_te_cm_%s" % m.key for m in cfg.MERGES})

    def test_merge_mechanics_never_key_on_the_entry(self):
        # R20: has_journal_entry of the merge's own entry appears only in the net, never in a gate or a join.
        for path in (GEN_TRIGGERS, EFFECTS):
            self.assertNotIn("has_journal_entry = je_te_cm_", text_of(path), path.name)
            self.assertNotIn("has_inactive_journal_entry = je_te_cm_", text_of(path), path.name)
        for merge in cfg.MERGES:
            for name in ("te_cmg_census_%s_country" % merge.key, "te_cmg_%s_join_ready" % merge.key, "te_cmg_start_%s" % merge.key):
                self.assertNotIn("je_te_cm_", block(self.effects, name), name)


class ValuesAndBarsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.values = text_of(VALUES)
        cls.bars = text_of(BARS)

    def test_progress_is_the_lowest_share_over_the_switch_share_capped_at_one(self):
        # While the merge runs the core's lowest share; once it is complete (state 2) the lowest over every part that
        # joined, which are the late ones.
        for merge in cfg.MERGES:
            key = merge.key
            progress = squash(block(self.values, "te_cmg_%s_progress" % key))
            self.assertEqual(
                progress,
                "value = 0 if = { limit = { global_var:te_cm_state_%s ?= 2 } value = te_cmg_%s_lowest_dom_all "
                "divide = te_cm_switch_share max = 1 } else = { value = te_cmg_%s_lowest_dom divide = te_cm_switch_share max = 1 }"
                % (key, key, key),
            )
            self.assertEqual(squash(block(self.values, "te_cmg_%s_bar_pct" % key)), "value = te_cmg_%s_progress multiply = 100" % key)

    def test_lowest_share_skips_switched_parts_and_counts_an_unmeasured_one_as_zero(self):
        for merge in cfg.MERGES:
            key = merge.key
            for name, cultures in (
                ("te_cmg_%s_lowest_dom" % key, [c for p in merge.core for c in p.cultures if not absorb_result(merge, c)]),
                ("te_cmg_%s_lowest_dom_all" % key, [c for c in slot_cultures(merge) if not absorb_result(merge, c)]),
            ):
                body = squash(block(self.values, name))
                joined = " ".join("global_var:te_cm_joined_%s_%s ?= 1" % (key, c) for c in cultures)
                # 0 until a part has joined; 1, from which each unswitched joined part takes its share, once one has.
                self.assertTrue(body.startswith("value = 0 if = { limit = { OR = { %s } } value = 1 " % joined), name)
                for culture in cultures:
                    self.assertIn(
                        "if = { limit = { global_var:te_cm_joined_%s_%s ?= 1 NOT = { has_global_variable = te_cm_switched_%s } } "
                        "if = { limit = { has_global_variable = te_cm_dom_%s_%s } max = global_var:te_cm_dom_%s_%s } else = { max = 0 } }"
                        % (key, culture, culture, key, culture, key, culture),
                        body,
                        "%s %s" % (name, culture),
                    )
            # The core's figure leaves optional parts out; the other one has them.
            for part in merge.optional:
                self.assertNotIn("te_cm_joined_%s_%s " % (key, part.cultures[0]), squash(block(self.values, "te_cmg_%s_lowest_dom" % key)))
                self.assertIn("te_cm_joined_%s_%s " % (key, part.cultures[0]), squash(block(self.values, "te_cmg_%s_lowest_dom_all" % key)))

    def test_one_bar_per_merge_from_zero_to_a_hundred(self):
        for merge in cfg.MERGES:
            body = squash(block(self.bars, "te_cmg_%s_bar" % merge.key))
            self.assertEqual(
                body,
                'name = "te_cm_bar_name" desc = "te_cm_bar_desc" default_green = yes start_value = 0 min_value = 0 max_value = 100',
            )


class LocTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.loc = defined_loc()
        cls.vanilla = json.loads(VANILLA_LOC.read_text(encoding="utf-8"))
        cls.generated = loc_of(GEN_LOC)

    def test_every_key_the_new_files_name_is_defined(self):
        used = set()
        je = JE_FILE.read_text(encoding="utf-8-sig")
        used.update(re.findall(r"\bdesc = (\w+)", je))
        used.update(re.findall(r"conclusion_desc = (\w+)", je))
        used.update(re.findall(r"\b(?:header|effect_header) = (\w+)", je))
        used.update(re.findall(r"\btext = (\w+)", je))
        buttons = BUTTONS.read_text(encoding="utf-8-sig")
        used.update(re.findall(r'(?:name|desc) = "(\w+)"', buttons))
        used.update(re.findall(r"text = (\w+)", buttons))
        used.update(re.findall(r'(?:name|desc) = "(\w+)"', BARS.read_text(encoding="utf-8-sig")))
        used.update(re.findall(r"text = (\w+)", GEN_TRIGGERS.read_text(encoding="utf-8-sig")))
        # The two standard headers are vanilla's.
        vanilla_keys = {"je_standard_completion_header", "je_standard_on_completion_header"}
        self.assertTrue(vanilla_keys <= used)
        missing = sorted(k for k in used - vanilla_keys if k not in self.loc)
        self.assertEqual(missing, [])
        for key in vanilla_keys:
            self.assertIn(key, self.vanilla)

    def test_every_entry_has_a_name_and_a_reason(self):
        for merge in cfg.MERGES:
            self.assertIn("je_te_cm_%s" % merge.key, self.generated)
            self.assertIn("je_te_cm_%s_reason" % merge.key, self.generated)
            self.assertEqual(self.generated["je_te_cm_%s" % merge.key], "Cultural Merge: $%s$" % merge.result)

    def test_every_splice_resolves_and_names_are_spliced_not_spelled(self):
        known = all_english_loc_keys() | set(self.vanilla)
        for key, text in self.generated.items():
            for splice in re.findall(r"\$([\w.\-]+)(?:\|[^$]*)?\$", text):
                self.assertIn(splice, known, "%s splices %s" % (key, splice))
        # A culture's display name never appears in a merge's text: the result and part names are splices.
        names = {merge.new.name for merge in cfg.MERGES if merge.new}
        results = gen.result_loc_keys()
        for key, text in self.generated.items():
            if key in results:
                continue
            plain = re.sub(r"\$[\w.\-]+\$|\[[^\]]*\]", "", text)
            for name in names:
                self.assertNotIn(name, plain, key)

    def test_script_values_in_the_text_exist(self):
        defined = set()
        for path in (VALUES, HAND_VALUES, DISPLAY_VALUES):
            defined.update(re.findall(r"^(\w+) = ", text_of(path), re.M))
        vanilla_values = json.loads((ROOT / "vanilla_parsed/common/script_values.json").read_text(encoding="utf-8"))
        defined.update(vanilla_values)
        for key, text in {**self.generated, **{k: v for k, v in self.loc.items() if k.startswith("te_cm_")}}.items():
            for name in re.findall(r"ScriptValue\('(\w+)'\)", text):
                self.assertIn(name, defined, "%s reads %s" % (key, name))

    def test_variables_in_the_text_are_ones_the_census_writes(self):
        census = text_of(EFFECTS) + text_of(GEN_EFFECTS)
        shown = ("best", "worst", "hi", "lo", "gap")
        for key, text in self.generated.items():
            for name in re.findall(r"Var\('(\w+)'\)", text):
                if name.startswith(("te_cm_held_", "te_cm_years_")):
                    continue
                self.assertRegex(name, r"^te_cm_sol_(%s)_" % "|".join(shown), "%s reads %s" % (key, name))
                self.assertIn("set_variable = { name = %s value = " % name, census, "%s reads %s" % (key, name))
        self.assertIn("te_cm_held_$MERGE$_$CULTURE$", census)
        self.assertIn("te_cm_years_$MERGE$_$CULTURE$", census)

    def test_text_is_american_and_uses_the_house_markup(self):
        for key, text in {**self.generated, **{k: v for k, v in self.loc.items() if k.startswith("te_cm_")}}.items():
            self.assertNotIn("[b]", text, key)
            if key != "te_cm_speed_tt":  # a hover's body, laid out like vanilla's: header, breakdown, divider, prose
                self.assertNotIn("\\n", text, key)
            self.assertNotRegex(text, r"\b(?:colour|favour|organis|recognis|neighbour|centre|defence|labour)", key)

    def test_player_text_says_culture_not_part(self):
        # "Part" is the roster's word for a slot culture; players read "constituent culture", "core culture" or just
        # "culture" (owner, 2026-11-08). "Part of" in its plain sense ("part of another merge") is fine.
        texts = {**self.generated, **{k: v for k, v in self.loc.items() if k.startswith("te_cm_")}}
        rules = loc_of(ROOT / "localization/english/te_game_rules_l_english.yml")
        texts.update({k: v for k, v in rules.items() if k.startswith("setting_culture_merges")})
        self.assertIn("setting_culture_merges_enabled_desc", texts)
        for key, text in texts.items():
            self.assertNotRegex(text, r"(?i)\bparts\b|\bpart's\b|\bpart\b(?! of\b)", key)

    def test_the_number_in_the_bar_text_is_the_switch_share(self):
        self.assertIn("ScriptValue('te_cm_switch_share')|%0]", self.loc["te_cm_bar_desc"])
        values = text_of(HAND_VALUES)
        self.assertIn("te_cm_switch_share = 0.60", values)

    def test_the_tech_lines_name_the_tier_technologies(self):
        for tier, tech in ((1, "pan-nationalism"), (2, "mass_media"), (3, "television")):
            self.assertEqual(self.loc["te_cm_tt_tech_%d" % tier], "$%s$ is researched." % tech)
        triggers = text_of(ROOT / "common/scripted_triggers/te_culture_merge_triggers.txt")
        for tier, tech in ((1, "pan-nationalism"), (2, "mass_media"), (3, "television")):
            self.assertIn("te_cm_tier_tech_%d = {\n\thas_technology_researched = %s\n}" % (tier, tech), triggers)

    def test_hand_written_phrases_file_in_the_miscellaneous_loc(self):
        import organize_loc

        for key in self.loc:
            if key.startswith("te_cm_"):
                self.assertEqual(organize_loc.categorize_key(key, set()), "MISCELLANEOUS", key)
        for key in self.generated:
            self.assertEqual(organize_loc.categorize_key(key, set()), "CULTURE_MERGES_GENERATED", key)


class ThePlanTest(unittest.TestCase):
    def test_entry_keys_do_not_collide_with_result_keys(self):
        self.assertFalse(set(gen.entry_loc(vanilla())) & gen.result_loc_keys())

    def test_each_row_key_is_unique_to_its_merge(self):
        seen = {}
        for merge in cfg.MERGES:
            for row in gen.status_rows(merge, vanilla(), cfg.MERGES):
                if row.text is None:
                    continue
                self.assertNotIn(row.key, seen, row.key)
                seen[row.key] = merge.key

    def test_a_loc_text_cannot_hold_a_quote_mark(self):
        broken = (cfg.Merge("x", "cm_x", cfg.NewCulture('X"', (1, 2, 3)), core=(cfg.Part(("north_german",)), cfg.Part(("south_german",)))),)
        with self.assertRaises(ValueError):
            gen.render_loc(gen.build_plan(vanilla(), broken))


def complete_trigger(key):
    """The conditions of a merge entry's complete outcome, parsed."""
    entry = entry_nodes()["je_te_cm_%s" % key]
    complete, _ = children(entry, "outcome")
    return child(complete, "trigger").children


def joined_world(merge, state, joined, switched, this="A", starter="A", flagged=()):
    """A world where ``this`` is looking at a merge in ``state``, with the named cultures joined and switched."""
    key = merge.key
    globals_ = {"te_cm_state_%s" % key: state, "te_cm_starter_%s" % key: starter}
    globals_.update({"te_cm_joined_%s_%s" % (key, c): 1 for c in joined})
    globals_.update({"te_cm_switched_%s" % c: "cu" for c in switched})
    world = World(globals_, alive={"A": True, "B": True, "C": True}, country_vars={c: {"te_cm_started_%s" % key} for c in flagged})
    world.this = this
    return world


class CompleteTest(unittest.TestCase):
    """R5 in full: complete when the state is 2 and no joined part is left unswitched."""

    def test_all_switched_is_a_nor_over_every_slot_culture_that_can_join(self):
        triggers = text_of(GEN_TRIGGERS)
        for merge in cfg.MERGES:
            key = merge.key
            cultures = [c for c in slot_cultures(merge) if not absorb_result(merge, c)]
            self.assertEqual(
                squash(block(triggers, "te_cmg_%s_all_switched" % key)),
                "NOR = { %s }" % " ".join(
                    "AND = { global_var:te_cm_joined_%s_%s ?= 1 NOT = { has_global_variable = te_cm_switched_%s } }" % (key, c, c)
                    for c in cultures
                ),
                key,
            )

    def test_a_merge_whose_only_remaining_joined_part_is_optional_is_not_complete(self):
        german = cfg.merge_by_key("german")
        core = ["north_german", "south_german"]
        # Task 6 set the state to 2 when both core parts switched; Alemannic joined and is still converting.
        world = joined_world(german, 2, core + ["alemannic"], core)
        self.assertFalse(holds(definitions(GEN_TRIGGERS)["te_cmg_german_all_switched"].children, world))
        self.assertFalse(holds(complete_trigger("german"), world))
        # It switches, and the entry may conclude.
        world = joined_world(german, 2, core + ["alemannic"], core + ["alemannic"])
        self.assertTrue(holds(complete_trigger("german"), world))
        # A part that never joined doesn't hold it back.
        world = joined_world(german, 2, core, core)
        self.assertTrue(holds(complete_trigger("german"), world))

    def test_every_merge_waits_for_its_last_late_part(self):
        for merge in cfg.MERGES:
            key = merge.key
            joinable = [c for c in slot_cultures(merge) if not absorb_result(merge, c)]
            core = [c for p in merge.core for c in p.cultures if not absorb_result(merge, c)]
            for late in joinable:
                world = joined_world(merge, 2, core + [late], core)
                if late in core:
                    continue
                self.assertFalse(holds(complete_trigger(key), world), "%s: %s still converting" % (key, late))
                world = joined_world(merge, 2, core + [late], core + [late])
                self.assertTrue(holds(complete_trigger(key), world), key)

    def test_complete_needs_the_state_and_the_starter(self):
        german = cfg.merge_by_key("german")
        core = ["north_german", "south_german"]
        self.assertFalse(holds(complete_trigger("german"), joined_world(german, 1, core, core)))
        self.assertFalse(holds(complete_trigger("german"), joined_world(german, 2, core, core, this="C")))
        self.assertTrue(holds(complete_trigger("german"), joined_world(german, 2, core, core)))

    def test_an_absorb_merges_result_is_never_waited_for(self):
        hungarian = cfg.merge_by_key("hungarian")
        world = joined_world(hungarian, 2, ["szekely"], ["szekely"])
        self.assertTrue(holds(complete_trigger("hungarian"), world))
        self.assertNotIn("hungarian_hungarian", block(text_of(GEN_TRIGGERS), "te_cmg_hungarian_all_switched"))

    def test_the_status_text_tells_a_late_part_from_a_finished_merge(self):
        # state 2 with a late part still converting is its own row, ahead of "running", showing the lowest share over
        # every part that joined; a finished merge is the complete row.
        entries = entry_nodes()
        for merge in cfg.MERGES:
            raw = je_text(merge.key)
            body = inner(raw, "first_valid")
            self.assertLess(body.index("_status_complete"), body.index("_status_late"))
            self.assertLess(body.index("_status_late"), body.index("_status_running"))
            self.assertIn("je_te_cm_%s" % merge.key, entries)


class ProgressTest(unittest.TestCase):
    """The bar's figure, evaluated over a world."""

    def test_a_running_merge_with_nothing_joined_shows_no_progress_not_a_full_bar(self):
        for merge in cfg.MERGES:
            world = joined_world(merge, 1, [], [])
            key = merge.key
            self.assertEqual(value_of("te_cmg_%s_lowest_dom" % key, world), 0, key)
            self.assertEqual(value_of("te_cmg_%s_lowest_dom_all" % key, world), 0, key)
            self.assertEqual(value_of("te_cmg_%s_progress" % key, world), 0, key)
            self.assertEqual(value_of("te_cmg_%s_bar_pct" % key, world), 0, key)

    def test_the_core_part_that_lags_sets_the_pace(self):
        german = cfg.merge_by_key("german")
        world = joined_world(german, 1, ["north_german", "south_german"], [])
        world.globals.update({"te_cm_dom_german_north_german": 0.5, "te_cm_dom_german_south_german": 0.2})
        self.assertAlmostEqual(value_of("te_cmg_german_lowest_dom", world), 0.2)
        self.assertAlmostEqual(value_of("te_cmg_german_progress", world), 0.2 / 0.60)
        self.assertAlmostEqual(value_of("te_cmg_german_bar_pct", world), 100 * 0.2 / 0.60)
        # A joined part the census has not measured yet counts as nothing.
        del world.globals["te_cm_dom_german_south_german"]
        self.assertEqual(value_of("te_cmg_german_lowest_dom", world), 0)

    def test_a_switched_part_leaves_the_minimum_and_the_bar_caps_at_one(self):
        german = cfg.merge_by_key("german")
        world = joined_world(german, 1, ["north_german", "south_german"], ["south_german"])
        world.globals["te_cm_dom_german_north_german"] = 0.9
        self.assertEqual(value_of("te_cmg_german_progress", world), 1)
        world = joined_world(german, 2, ["north_german", "south_german"], ["north_german", "south_german"])
        self.assertEqual(value_of("te_cmg_german_progress", world), 1)

    def test_once_complete_the_figure_is_the_late_parts_not_the_cores(self):
        # Core parts all switched: the core's lowest reads 100%, which is not what is left to wait for.
        german = cfg.merge_by_key("german")
        core = ["north_german", "south_german"]
        world = joined_world(german, 2, core + ["alemannic"], core)
        world.globals["te_cm_dom_german_alemannic"] = 0.3
        self.assertEqual(value_of("te_cmg_german_lowest_dom", world), 1)
        self.assertAlmostEqual(value_of("te_cmg_german_lowest_dom_all", world), 0.3)
        self.assertAlmostEqual(value_of("te_cmg_german_progress", world), 0.3 / 0.60)
        # While it still runs (state 1), the core decides.
        world.globals["te_cm_state_german"] = 1
        self.assertEqual(value_of("te_cmg_german_progress", world), 1)


class StarterFlagTest(unittest.TestCase):
    """R30: the winner continues the nation. A civil war's winner inherits the loser's variables, but the global
    te_cm_starter_<m> still names the dead tag."""

    def starter(self, world):
        return holds(definitions(GEN_TRIGGERS)["te_cmg_german_is_starter"].children, world)

    def other(self, world):
        return holds(definitions(GEN_TRIGGERS)["te_cmg_german_has_other_starter"].children, world)

    def world(self, this, state=1, starter="A", a_alive=True, flagged=("A",)):
        world = joined_world(cfg.merge_by_key("german"), state, [], [], this=this, starter=starter, flagged=flagged)
        world.alive["A"] = a_alive
        if starter is None:
            del world.globals["te_cm_starter_german"]
        return world

    def test_the_flag_is_set_at_the_start(self):
        body = squash(block(text_of(EFFECTS), "te_cm_start_merge"))
        self.assertIn("set_variable = { name = te_cm_started_$MERGE$ value = 1 }", body)

    def test_the_global_starter_is_the_starter(self):
        self.assertTrue(self.starter(self.world("A")))
        self.assertFalse(self.other(self.world("A")))

    def test_a_flag_holder_is_the_starter_only_while_the_global_starter_is_dead_or_missing(self):
        # B inherited the flag from A, which is dead: B is the starter.
        self.assertTrue(self.starter(self.world("B", a_alive=False, flagged=("A", "B"))))
        self.assertTrue(self.starter(self.world("B", starter=None, flagged=("B",))))
        # A still lives (the old tag survived): B holds the flag and isn't the starter.
        self.assertFalse(self.starter(self.world("B", flagged=("A", "B"))))
        # No flag, no claim, whatever has happened to the starter.
        self.assertFalse(self.starter(self.world("C", a_alive=False, flagged=("A",))))
        self.assertFalse(self.starter(self.world("C", starter=None, flagged=("A",))))

    def test_nobody_is_the_starter_of_an_idle_merge(self):
        for this in ("A", "B"):
            self.assertFalse(self.starter(self.world(this, state=0, a_alive=False, flagged=("A", "B"))))

    def test_another_country_is_an_other_starter_only_while_the_starter_lives_and_it_has_no_flag(self):
        self.assertTrue(self.other(self.world("C")))
        self.assertFalse(self.other(self.world("A")))
        self.assertFalse(self.other(self.world("B", flagged=("A", "B"))))  # holds the flag
        self.assertFalse(self.other(self.world("C", a_alive=False)))  # the starter is dead: nobody else has it
        self.assertFalse(self.other(self.world("C", starter=None)))
        self.assertFalse(self.other(self.world("C", state=0)))

    def test_the_winners_entry_does_not_end_as_invalid_while_it_is_the_starter(self):
        # The invalid outcome is has_other_starter, which the flag holder is not.
        entry = entry_nodes()["je_te_cm_german"]
        _, invalid = children(entry, "outcome")
        trigger = child(invalid, "trigger").children
        self.assertFalse(holds(trigger, self.world("B", a_alive=False, flagged=("A", "B"))))
        self.assertTrue(holds(trigger, self.world("C")))

    def release_pass(self, world):
        release = definitions(GEN_EFFECTS)["te_cmg_release_lost_starters"]
        for node in release.children:
            if "te_cmg_german_starter_gone" in text_of_node(node):
                run_effects([node], world, None)

    def test_the_yearly_pass_hands_a_running_merge_to_the_flag_holder(self):
        world = self.world("A", a_alive=False, flagged=("A", "B"))
        self.release_pass(world)
        self.assertEqual(world.globals["te_cm_state_german"], 1)
        self.assertEqual(world.globals["te_cm_starter_german"], "B")
        self.assertIn("te_cm_started_german", world.vars["B"])

    def test_the_first_flag_holder_takes_it(self):
        world = self.world("A", a_alive=False, flagged=("A", "B", "C"))
        self.release_pass(world)
        self.assertEqual(world.globals["te_cm_starter_german"], "B")  # sorted: B before C

    def test_a_missing_starter_is_replaced_too(self):
        world = self.world("A", starter=None, flagged=("C",))
        self.release_pass(world)
        self.assertEqual(world.globals["te_cm_starter_german"], "C")
        self.assertEqual(world.globals["te_cm_state_german"], 1)

    def test_a_complete_merge_is_handed_over_and_never_released(self):
        world = self.world("A", state=2, a_alive=False, flagged=("A", "B"))
        self.release_pass(world)
        self.assertEqual(world.globals["te_cm_starter_german"], "B")
        self.assertEqual(world.globals["te_cm_state_german"], 2)
        world = self.world("A", state=2, a_alive=False, flagged=("A",))
        self.release_pass(world)
        self.assertEqual(world.globals["te_cm_state_german"], 2)  # nobody to hand it to, and no release

    def test_the_merge_is_released_only_when_no_living_country_carries_the_flag(self):
        world = self.world("A", a_alive=False, flagged=("A",))
        self.release_pass(world)
        self.assertEqual(world.globals["te_cm_state_german"], 0)
        self.assertNotIn("te_cm_starter_german", world.globals)

    def test_a_living_starter_is_left_alone(self):
        world = self.world("A", flagged=("A", "B"))
        self.release_pass(world)
        self.assertEqual(world.globals["te_cm_starter_german"], "A")
        self.assertEqual(world.globals["te_cm_state_german"], 1)

    # ---- R38 I2: a complete merge nobody can take over lets go of its unswitched parts ----
    def release_merge(self, world, key):
        for node in definitions(GEN_EFFECTS)["te_cmg_release_lost_starters"].children:
            if "te_cmg_%s_starter_gone" % key in text_of_node(node):
                run_effects([node], world, None)

    def lost_french(self, flagged=(), starter_alive=False):
        """French complete under A: Wallonian and Occitan joined and switched, Catalan joined late and still converting."""
        world = joined_world(cfg.merge_by_key("french"), 2, ["wallonian", "occitan", "catalan"], ["wallonian", "occitan"],
                             this=None, flagged=flagged)
        world.globals["te_cm_in_catalan"] = merge_index(cfg.merge_by_key("french"))
        world.alive["A"] = starter_alive
        return world

    def trig(self, world, name):
        return holds(definitions(GEN_TRIGGERS)[name].children, world)

    def test_a_complete_merge_with_no_one_to_take_it_over_lets_go_of_its_late_parts(self):
        world = self.lost_french()
        # Before: Catalan is stranded, so French is never finished and Latin can never take french (R33).
        self.assertFalse(self.trig(world, "te_cmg_french_all_switched"))
        self.assertFalse(self.trig(world, "te_cmg_latin_french_available"))
        self.release_merge(world, "french")
        self.assertNotIn("te_cm_joined_french_catalan", world.globals)
        self.assertNotIn("te_cm_in_catalan", world.globals)
        # The parts that switched keep their record, and the merge stays complete.
        self.assertEqual(world.globals["te_cm_joined_french_wallonian"], 1)
        self.assertEqual(world.globals["te_cm_switched_occitan"], "cu")
        self.assertEqual(world.globals["te_cm_state_french"], 2)
        self.assertTrue(self.trig(world, "te_cmg_french_all_switched"))
        self.assertTrue(self.trig(world, "te_cmg_latin_french_available"))

    def test_a_complete_merge_with_a_country_to_take_it_over_keeps_its_parts(self):
        world = self.lost_french(flagged=("B",))
        self.release_merge(world, "french")
        self.assertEqual(world.globals["te_cm_starter_french"], "B")
        self.assertEqual(world.globals["te_cm_joined_french_catalan"], 1)
        self.assertEqual(world.globals["te_cm_in_catalan"], merge_index(cfg.merge_by_key("french")))
        world = self.lost_french(starter_alive=True)
        self.release_merge(world, "french")
        self.assertEqual(world.globals["te_cm_joined_french_catalan"], 1)

    def test_the_unjoin_leaves_another_merges_index_alone(self):
        world = self.lost_french()
        world.globals["te_cm_in_catalan"] = 99
        self.release_merge(world, "french")
        self.assertNotIn("te_cm_joined_french_catalan", world.globals)
        self.assertEqual(world.globals["te_cm_in_catalan"], 99)

    def test_a_lost_yugoslav_merge_frees_slovene_and_its_result_for_pan_slavic(self):
        yugoslav = cfg.merge_by_key("yugoslav")
        core = ["serb", "croat", "bosniak"]
        world = joined_world(yugoslav, 2, core + ["slovene"], core, this=None)
        world.globals["te_cm_in_slovene"] = merge_index(yugoslav)
        world.alive["A"] = False
        self.assertFalse(self.trig(world, "te_cmg_pan_slavic_slovene_available"))
        self.assertFalse(self.trig(world, "te_cmg_pan_slavic_cm_yugoslav_available"))
        self.release_merge(world, "yugoslav")
        self.assertTrue(self.trig(world, "te_cmg_pan_slavic_slovene_available"))
        self.assertTrue(self.trig(world, "te_cmg_pan_slavic_cm_yugoslav_available"))

    def test_every_merge_lets_go_of_every_part_it_can_join(self):
        for index, merge in enumerate(cfg.MERGES, start=1):
            key = merge.key
            node = next(n for n in definitions(GEN_EFFECTS)["te_cmg_release_lost_starters"].children
                        if n.key == "if" and squash(text_of_node(child(n, "limit"))) ==
                        "global_var:te_cm_state_%s = 2 te_cmg_%s_starter_gone = yes" % (key, key))
            calls = [(c.key, {a.key: a.value for a in c.children}) for c in node.children if c.key != "limit"]
            self.assertEqual(
                calls,
                [("te_cm_unjoin_part", {"MERGE": key, "CULTURE": c, "INDEX": str(index)})
                 for c in slot_cultures(merge) if not absorb_result(merge, c)],
                key,
            )

    def test_a_release_takes_the_flag_from_a_living_holder(self):
        world = self.world("A", flagged=("A", "B"))
        run_effects(definitions_effect_call("german"), world, "A")
        self.assertEqual(world.globals["te_cm_state_german"], 0)
        self.assertEqual(world.vars["A"], set())
        self.assertEqual(world.vars["B"], set())
        self.assertNotIn("te_cm_starter_german", world.globals)


def definitions_effect_call(key):
    nodes, _ = parse_text("te_cm_release_starter = { MERGE = %s }" % key, "call")
    return nodes


class MixedTiersTest(unittest.TestCase):
    """R31: a core part of a tier other than the one the merge starts at takes its own technology."""

    def slot_items(self, merge):
        key = merge.key
        defs = definitions(GEN_TRIGGERS)
        nodes = list(defs["te_cmg_%s_can_start" % key].children)
        if "te_cmg_%s_start_basics" % key in defs:
            nodes += defs["te_cmg_%s_start_basics" % key].children
        out = {}
        for node in nodes:
            if node.key == "custom_tooltip":
                text = child(node, "text").value
                m = re.fullmatch(r"te_cmg_%s_core_(\d+)_tt" % key, text)
                if m:
                    out[int(m.group(1))] = node
        return out

    def test_a_slot_holds_exactly_when_an_alternative_passes_its_own_technology(self):
        # With everything else true and the start tier's technology known (can_start asks for it on its own), a
        # slot holds for a set of technologies exactly when one of its alternatives would pass can_join's test.
        import itertools

        for merge in cfg.MERGES:
            start = max(tier_of(merge, p.cultures[0]) for p in merge.core)
            named = {}
            for c in slot_cultures(merge):
                named["te_cmg_%s_%s_measured" % (merge.key, c)] = True
                named["te_cmg_%s_%s_years_met" % (merge.key, c)] = True
                named["te_cmg_%s_%s_switched_in" % (merge.key, c)] = False
            items = self.slot_items(merge)
            self.assertEqual(sorted(items), list(range(1, len(merge.core) + 1)), merge.key)
            for extra in itertools.chain.from_iterable(itertools.combinations({1, 2, 3} - {start}, n) for n in range(3)):
                techs = {start} | set(extra)
                world = World(named=named, techs=techs)
                for index, part in enumerate(merge.core, start=1):
                    want = any(tier_of(merge, c) in techs for c in part.cultures)
                    got = holds([c for c in items[index].children if c.key != "text"], world)
                    self.assertEqual(got, want, "%s slot %d with %s" % (merge.key, index, sorted(techs)))

    def test_pan_turkic_cannot_start_without_kazak_kirgiz_and_tatar_technologies(self):
        merge = cfg.merge_by_key("pan_turkic")
        self.assertEqual({c: tier_of(merge, c) for c in ("kazak", "kirgiz", "tatar", "uzbek")},
                         {"kazak": 1, "kirgiz": 1, "tatar": 2, "uzbek": 3})
        named = {"te_cmg_pan_turkic_%s_%s" % (c, s): s != "switched_in" for c in slot_cultures(merge)
                 for s in ("measured", "years_met", "switched_in")}
        items = self.slot_items(merge)
        by_name = {c.cultures[0]: items[i] for i, c in enumerate(merge.core, start=1)}
        for culture, tier in (("kazak", 1), ("kirgiz", 1), ("tatar", 2)):
            node = by_name[culture]
            body = [c for c in node.children if c.key != "text"]
            self.assertFalse(holds(body, World(named=named, techs={3})), culture)
            self.assertFalse(holds(body, World(named=named, techs={3} | ({1, 2} - {tier}))), culture)
            self.assertTrue(holds(body, World(named=named, techs={3, tier})), culture)

    def test_a_single_tier_merge_adds_nothing(self):
        triggers = text_of(GEN_TRIGGERS)
        for merge in cfg.MERGES:
            if merge.key == "pan_turkic":
                continue
            self.assertNotIn("te_cm_tier_tech", block(triggers, "te_cmg_%s_core_ok" % merge.key), merge.key)

    def test_the_slot_tooltip_names_the_extra_technology(self):
        loc = loc_of(GEN_LOC)
        self.assertIn("$pan-nationalism$", loc["te_cmg_pan_turkic_core_3_tt"])
        self.assertIn("$mass_media$", loc["te_cmg_pan_turkic_core_4_tt"])
        self.assertNotIn("also need", loc["te_cmg_pan_turkic_core_1_tt"])


class WordingTest(unittest.TestCase):
    """R31 wording and splices."""

    @classmethod
    def setUpClass(cls):
        cls.generated = loc_of(GEN_LOC)
        cls.misc = loc_of(MISC_LOC)

    def test_names_of_things_are_spliced_not_spelled(self):
        for merge in cfg.MERGES:
            for suffix in ("running", "late"):
                text = self.generated["je_te_cm_%s_status_%s" % (merge.key, suffix)]
                self.assertIn("$country_culture_merge_speed_mult$", text)
        self.assertIn("$rule_culture_merges_rule$", self.misc["te_cm_tt_rule_on"])
        self.assertIn("$rule_culture_merges_rule$", self.misc["te_cm_status_rule_off"])
        for loc in (self.generated, self.misc):
            for key, text in loc.items():
                if key.startswith(("te_cm", "je_te_cm", "te_cmg")):
                    self.assertNotIn("Culture Merges game rule", text, key)
                    self.assertNotIn("half a century", text, key)
                    self.assertNotIn("for decades", text, key)
        # The years a tier asks for come from the script values.
        self.assertIn("ScriptValue('te_cm_years_tier2')", self.generated["te_cmg_pan_turkic_core_4_tt"])
        self.assertIn("ScriptValue('te_cm_years_tier3')", self.generated["te_cmg_pan_slavic_core_1_tt"])

    def test_the_names_the_text_splices_exist(self):
        known = all_english_loc_keys()
        for needed in ("country_culture_merge_speed_mult", "rule_culture_merges_rule"):
            self.assertIn(needed, known)

    def test_the_button_does_not_promise_that_every_part_joins(self):
        for merge in cfg.MERGES:
            text = self.generated["te_cmg_start_%s_button_desc" % merge.key]
            self.assertNotIn("every constituent culture we hold", text, merge.key)
            self.assertIn("Each constituent culture we hold that qualifies", text, merge.key)
            self.assertIn("A culture that qualifies later joins then", text, merge.key)

    def test_a_rule_row_says_the_system_is_paused(self):
        self.assertIn("paused", self.misc["te_cm_status_rule_off"])
        self.assertIn("Nothing stands in the way", self.misc["te_cm_status_ready"])

    def test_optional_parts_are_named_as_pops(self):
        text = self.generated["je_te_cm_french_reason"]
        self.assertIn("$catalan$ pops can join once they qualify as well.", text)
        for merge in cfg.MERGES:
            if merge.optional:
                text = self.generated["je_te_cm_%s_reason" % merge.key]
                # A lone optional culture with a gate of its own says it in the same sentence.
                gated = [p for p in merge.optional if p.gate]
                tail = ", and only once %s." % gated[0].gate.clause if gated and len(merge.optional) == 1 else "."
                self.assertIn(" pops can join once they qualify as well" + tail, text, merge.key)

    def test_a_slot_shows_its_alternatives_in_the_reason_and_the_button(self):
        # Review B, M7: the status rows already said "$yankee$ or $cm_american$"; the summary texts said "$yankee$".
        for key in ("je_te_cm_anglophone_reason", "te_cmg_start_anglophone_button_desc"):
            self.assertIn("$british$ and $yankee$ (or $cm_american$)", self.generated[key], key)
        self.assertIn("$platinean$ (or $cm_platine$)", self.generated["je_te_cm_latin_reason"])

    def test_a_slot_only_another_merge_fills_is_still_forming_not_busy(self):
        # Review B, M8: Latin's French slot waits for the French merge; its pops are not "part of another merge".
        self.assertIn("$french$ is still forming in its own merge", self.generated["je_te_cm_latin_status_busy_1"])
        self.assertIn("already part of another merge", self.generated["je_te_cm_anglophone_status_busy_2"])

    def test_a_component_row_says_the_other_merge_must_finish_not_that_it_is_busy(self):
        # Before: "$cm_italian$ pops are already part of another merge" for a merge that had not started.
        for merge in cfg.MERGES:
            for component in merge.components:
                self.assertIn("has to finish first", self.generated["je_te_cm_%s_status_component_%s" % (merge.key, component)])


class IconExemptionTest(unittest.TestCase):
    def test_the_icon_pipeline_excepts_exactly_the_merge_entries(self):
        text = (ROOT / "test_icon_pipeline.py").read_text(encoding="utf-8")
        self.assertIn('{"je_te_cm_%s" % m.key for m in cfg.MERGES}', text)


if __name__ == "__main__":
    unittest.main()
