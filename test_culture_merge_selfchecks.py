"""Tests for the culture merges' console menu, once-a-game self-checks and play-test list (plan Task 8).

Files under test:
* events/te_debug_cm_events.txt: the console menu `event te_debug_cm.1`.
* common/scripted_effects/te_culture_merge_selfcheck_effects.txt and
  common/on_actions/te_culture_merge_selfcheck_on_actions.txt: the TEMPORARY self-checks, and the one-line calls
  that hook them into te_culture_merge_effects.txt and te_culture_merge_on_actions.txt.
* common/scripted_effects/te_debug_cm_effects.txt and the generated `te_cmg_debug_dump`: the menu's variable dump.
* docs/testing/culture-merges-playtest.md: the Self-checks table and everything only the game can show.

The script can't run offline, so most tests read its text: where each verdict is logged, under which once-guard,
and that every hook, every helper and every row of the doc matches the others.

Run: python3 -m unittest test_culture_merge_selfchecks -v
"""

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "generators"))

import culture_merges_config as cfg  # noqa: E402
import gen_culture_merges as gen  # noqa: E402
from test_culture_merge_census import block, slot_cultures, squash, text_of  # noqa: E402
from test_culture_merge_entries import all_english_loc_keys  # noqa: E402

CHECK_EFFECTS = ROOT / "common/scripted_effects/te_culture_merge_selfcheck_effects.txt"
CHECK_ON_ACTIONS = ROOT / "common/on_actions/te_culture_merge_selfcheck_on_actions.txt"
CONSOLE_EFFECTS = ROOT / "common/scripted_effects/te_debug_cm_effects.txt"
MERGE_EFFECTS = ROOT / "common/scripted_effects/te_culture_merge_effects.txt"
MERGE_ON_ACTIONS = ROOT / "common/on_actions/te_culture_merge_on_actions.txt"
GEN_EFFECTS = ROOT / "common/scripted_effects/te_culture_merges_generated_effects.txt"
EVENTS = ROOT / "events/te_debug_cm_events.txt"
PLAYTEST = ROOT / "docs/testing/culture-merges-playtest.md"
BOM = b"\xef\xbb\xbf"

# Every self-check, with the global the check sets once it has spoken (te_cm_chk_<name without cm_>_done).
SELFCHECKS = (
    "cm_conversion_merges_pops",
    "cm_formation_keeps_primary",
    "cm_acceptance_scale",
    "cm_russification_outcome",
    "cm_census_sane",
    "cm_rate_inputs",
    "cm_census_yearly",
    "cm_switch_homeland",
    "cm_fervor_copy",
    "cm_dead_primary_removed",
    "cm_untouched_stripped",
    "cm_tradition_carried",
    "cm_definition_inject",
)
# The checks that read merge state and so wait for the rule (ruling 4). Russification's reads the INJECTed outcome
# of a vanilla entry, which has no rule gate (Task 7), and no merge variable; the fervor copy's rides the copy, which
# has no rule gate either (it serves pops that stay switched with the rule off).
# The four of 2026-11-09 (a switched part leaving the primary cultures) ride the global monthly pulse beside the fervor
# copy: the removal they read is itself behind the rule, the traditions serve parts that already switched, and the
# definitions are injected whatever the rule says.
UNGATED = ("cm_russification_outcome", "cm_fervor_copy", "cm_dead_primary_removed", "cm_untouched_stripped",
           "cm_tradition_carried", "cm_definition_inject")
RULE_GATED = tuple(n for n in SELFCHECKS if n not in UNGATED)


def latch(name):
    return "te_cm_chk_%s_done" % name[len("cm_"):]


# ---------------------------------------------------------------------------------------------------------------
# A small structural reader: the parsed tree keeps neither operators nor a quoted string, and these tests need both.
# ---------------------------------------------------------------------------------------------------------------

_TOKEN = re.compile(r'"(?:[^"\\\n]|\\.)*"|[{}]|\?=|>=|<=|!=|=|<|>|[^\s{}=<>!?"]+')


class Node:
    def __init__(self, key, op=None, value=None, children=None):
        self.key, self.op, self.value, self.children = key, op, value, children

    def child(self, key):
        return next((c for c in self.children or () if c.key == key), None)


def strip_comment(line):
    """The line without a trailing # comment; a # inside a quoted string stays."""
    in_string = False
    for i, ch in enumerate(line):
        if ch == '"' and (i == 0 or line[i - 1] != "\\"):
            in_string = not in_string
        elif ch == "#" and not in_string:
            return line[:i]
    return line


def parse(text):
    """Nodes of a script text: `key op value` or `key = { children }`; comments are dropped, strings kept whole."""
    source = "\n".join(strip_comment(line) for line in text.lstrip("\ufeff").splitlines())
    toks = _TOKEN.findall(source)

    def nodes(i):
        out = []
        while i < len(toks) and toks[i] != "}":
            key = toks[i]
            if i + 2 < len(toks) and toks[i + 1] in ("=", "?=", ">=", "<=", "!=", "<", ">"):
                op, value = toks[i + 1], toks[i + 2]
                if value == "{":
                    kids, i = nodes(i + 3)
                    out.append(Node(key, op, None, kids))
                    i += 1  # the closing brace
                else:
                    out.append(Node(key, op, value))
                    i += 3
            else:
                out.append(Node(key))
                i += 1
        return out, i

    return nodes(0)[0]


def walk(nodes, ancestors=()):
    for node in nodes:
        yield node, ancestors
        if node.children:
            yield from walk(node.children, ancestors + (node,))


def file_nodes(path):
    return parse(path.read_text(encoding="utf-8-sig"))


def verdict_logs(path):
    """(verdict, name, node, ancestors) for every TE_SELF_CHECK OK|BROKEN line of a file."""
    for node, ancestors in walk(file_nodes(path)):
        if node.key == "debug_log":
            m = re.match(r'"TE_SELF_CHECK (OK|BROKEN) (\w+)', node.value or "")
            if m:
                yield m.group(1), m.group(2), node, ancestors


def first_clause_guard(ancestor):
    """The latch an `if` ancestor opens with: `limit = { NOT = { has_global_variable = X } ...`, or None."""
    if ancestor.key not in ("if", "else_if"):
        return None
    limit = ancestor.child("limit")
    if limit is None or not limit.children:
        return None
    first = limit.children[0]
    if first.key == "NOT" and first.children and first.children[0].key == "has_global_variable":
        return first.children[0].value
    return None


def limit_text(ancestor):
    """The `limit` of an `if` ancestor as flat text (keys and values only), or ''."""
    limit = ancestor.child("limit") if ancestor.key in ("if", "else_if") else None
    if limit is None:
        return ""
    return " ".join(("%s %s" % (n.key, n.value) if n.value else n.key) for n, _ in walk(limit.children))


class FilesTest(unittest.TestCase):
    def test_one_bom_and_tabs(self):
        for path in (CHECK_EFFECTS, CHECK_ON_ACTIONS, CONSOLE_EFFECTS, EVENTS):
            raw = path.read_bytes()
            self.assertTrue(raw.startswith(BOM), path.name)
            self.assertFalse(raw[3:].startswith(BOM), path.name + " has two BOMs")
            for line in raw.decode("utf-8-sig").splitlines():
                self.assertFalse(line.startswith(" "), path.name + ": " + line)

    def test_the_generated_files_are_current(self):
        self.assertFalse(gen.regenerate(dry_run=True)["changed"], "run python3 scripts/generators/gen_culture_merges.py")


class SelfCheckLogTest(unittest.TestCase):
    """Each check speaks once a game, with the numbers, and only on inputs that mean something."""

    @classmethod
    def setUpClass(cls):
        cls.logs = list(verdict_logs(CHECK_EFFECTS))

    def test_every_selfcheck_has_an_ok_and_a_broken_line(self):
        seen = {}
        for verdict, name, _, _ in self.logs:
            seen.setdefault(name, set()).add(verdict)
        self.assertEqual(sorted(seen), sorted(SELFCHECKS), "a TE_SELF_CHECK name nobody lists, or a listed one that is not logged")
        for name in SELFCHECKS:
            self.assertEqual(seen[name], {"OK", "BROKEN"}, name)

    def test_selfchecks_log_once(self):
        # Every verdict sits under an `if` whose limit opens with NOT = { has_global_variable = <latch> }, and that
        # block (or one between it and the line) sets the latch before the line, so the check speaks once a game.
        for verdict, name, node, ancestors in self.logs:
            guards = [first_clause_guard(a) for a in ancestors]
            self.assertIn(latch(name), guards, "%s %s is not under its once-guard %s" % (verdict, name, latch(name)))
            outer = ancestors[guards.index(latch(name))]
            sets = [n for n, _ in walk(outer.children) if n.key == "set_global_variable"
                    and n.child("name") is not None and n.child("name").value == latch(name)]
            self.assertTrue(sets, "%s %s never sets %s" % (verdict, name, latch(name)))

    def test_one_line_per_verdict_per_block(self):
        # An OK and a BROKEN line for a check live in different branches (an else), never one after the other.
        for name in SELFCHECKS:
            lines = [(verdict, node) for verdict, n, node, _ in self.logs if n == name]
            for verdict, node in lines:
                self.assertEqual(sum(1 for v, other in lines if other is node and v != verdict), 0)

    def test_every_selfcheck_but_russification_waits_for_the_rule(self):
        # Ruling 4: no check that reads merge state fires on a game with no merges. The guard sits in the same limit
        # as the latch, or in one the verdict's block nests in.
        for verdict, name, node, ancestors in self.logs:
            if name not in RULE_GATED:
                continue
            seen = " ".join(limit_text(a) for a in ancestors)
            self.assertIn("te_cm_system_enabled yes", seen, "%s %s is not gated on te_cm_system_enabled" % (verdict, name))

    def test_the_ungated_checks_have_no_rule_gate(self):
        # The INJECTed outcome and the fervor copy carry no rule gate, and their checks read no merge state.
        for verdict, name, node, ancestors in self.logs:
            if name in UNGATED:
                self.assertNotIn("te_cm_system_enabled", " ".join(limit_text(a) for a in ancestors))

    def test_every_number_is_read_from_a_global_set_before_the_line(self):
        # The accessors are GetGlobalVariable('te_cm_chk_...') only (a variable name with a $X$ inside brackets is
        # unproven), and each name is written by a set_global_variable somewhere in the file; a line dropped whole
        # for a bad accessor would lose the verdict (docs/guides/scripting_best_practices.md, debug_log templating).
        text = CHECK_EFFECTS.read_text(encoding="utf-8-sig")
        written = set(re.findall(r"name = (te_cm_chk_\w+)", text)) | {"te_cm_census_year"}
        for node, _ in walk(file_nodes(CHECK_EFFECTS)):
            if node.key != "debug_log" or "TE_SELF_CHECK" not in (node.value or ""):
                continue
            for accessor in re.findall(r"\[([^\]]*)\]", node.value):
                self.assertTrue(
                    accessor == "TimeKeeper.GetCurrentDate.GetString"
                    or accessor == "THIS.GetCountry.GetTagName"
                    or re.fullmatch(r"GetGlobalVariable\('(\w+)'\)\.GetValue\|\d", accessor),
                    node.value[:60] + " -> " + accessor,
                )
                m = re.match(r"GetGlobalVariable\('(\w+)'\)", accessor)
                if m:
                    self.assertIn(m.group(1), written, accessor)

    def test_no_make_scope_on_a_scope_in_a_line(self):
        text = CHECK_EFFECTS.read_text(encoding="utf-8-sig")
        self.assertNotRegex(text, r"\[(?:THIS|SCOPE|ROOT|PREV)\.MakeScope\.")

    def test_no_event_is_delayed(self):
        # A delayed state event never runs (the 2026-11-06 lesson); a verdict that needs settled state waits for the
        # next monthly pulse instead, behind a timed global.
        for path in (CHECK_EFFECTS, CHECK_ON_ACTIONS, CONSOLE_EFFECTS):
            text = text_of(path)
            self.assertNotRegex(text, r"trigger_event")
        self.assertNotRegex(text_of(EVENTS), r"trigger_event")


class HookTest(unittest.TestCase):
    """The checks are TEMPORARY: each hook is one call line, listed in the on_actions file's header, so deleting the
    two self-check files and those lines removes them all."""

    HOOKS = (
        # (file, enclosing top-level block, call)
        (MERGE_EFFECTS, "te_cm_census_part", "te_cm_chk_census = { MERGE = $MERGE$ CULTURE = $CULTURE$ }"),
        (MERGE_EFFECTS, "te_cm_convert_part", "te_cm_chk_conversion = { CULTURE = $CULTURE$ RESULT = $RESULT$ }"),
        (MERGE_EFFECTS, "te_cm_switch_part", "te_cm_chk_switch = { CULTURE = $CULTURE$ }"),
        (MERGE_EFFECTS, "te_cm_copy_fervor", "te_cm_chk_fervor = { CULTURE = $CULTURE$ }"),
        (MERGE_EFFECTS, "te_cm_monthly_switched_culture", "te_cm_chk_dead_primary = { CULTURE = $CULTURE$ }"),
        (MERGE_ON_ACTIONS, "te_cm_fervor_on_action", "te_cm_chk_fervor_monthly = yes"),
        (MERGE_ON_ACTIONS, "te_cm_fervor_on_action", "te_cm_chk_dead_primary_monthly = yes"),
        (MERGE_ON_ACTIONS, "te_cm_fervor_on_action", "te_cm_chk_strip_monthly = yes"),
        (MERGE_ON_ACTIONS, "te_cm_fervor_on_action", "te_cm_chk_definition_inject = yes"),
        (GEN_EFFECTS, "te_cmg_carry_traditions", "te_cm_chk_traditions = yes"),
        (MERGE_ON_ACTIONS, "te_cm_yearly_on_action", "te_cm_chk_census_year = yes"),
        (MERGE_ON_ACTIONS, "te_cm_formed_on_action", "te_cm_chk_formation = yes"),
    )

    def test_each_hook_is_one_call_line_in_its_helper(self):
        for path, name, call in self.HOOKS:
            body = squash(block(text_of(path), name))
            self.assertEqual(body.count(call), 1, "%s: %s" % (name, call))
        # And nowhere else in the merge files.
        for path in (MERGE_EFFECTS, MERGE_ON_ACTIONS):
            text = text_of(path)
            for helper in re.findall(r"\bte_cm_chk_\w+(?= = )", text):
                self.assertIn(helper, [c.split(" =")[0] for _, _, c in self.HOOKS], helper)

    def test_the_formation_check_runs_before_the_refresh(self):
        body = squash(block(text_of(MERGE_ON_ACTIONS), "te_cm_formed_on_action"))
        self.assertLess(body.index("te_cm_chk_formation = yes"), body.index("te_cmg_formed_country = yes"))
        # Behind the rule, like the refresh.
        self.assertLess(body.index("te_cm_system_enabled = yes"), body.index("te_cm_chk_formation = yes"))

    def test_the_census_year_check_runs_after_the_year_is_stored(self):
        body = squash(block(text_of(MERGE_ON_ACTIONS), "te_cm_yearly_on_action"))
        self.assertLess(body.index("name = te_cm_census_year"), body.index("te_cm_chk_census_year = yes"))
        self.assertLess(body.index("te_cm_chk_census_year = yes"), body.index("te_cmg_census_all = yes"))

    def test_the_census_hook_sits_after_the_hold_and_before_the_acceptance_scan(self):
        # Where te_cm_cp_pops, te_cm_cp_max_cnt and the hold are all set; the acceptance scan removes te_cm_tmp_cnt.
        body = squash(block(text_of(MERGE_EFFECTS), "te_cm_census_part"))
        hook = body.index("te_cm_chk_census = ")
        self.assertLess(body.index("set_variable = { name = te_cm_held_$MERGE$_$CULTURE$ value = 0 }"), hook)
        self.assertLess(body.index("name = te_cm_sol_$MERGE$_$CULTURE$"), hook)
        self.assertLess(hook, body.index("te_cm_cp_fail_open value = 0"))

    def test_the_conversion_hook_runs_for_a_converting_country_before_its_pops_convert(self):
        body = squash(block(text_of(MERGE_EFFECTS), "te_cm_convert_part"))
        hook = body.index("te_cm_chk_conversion = ")
        self.assertLess(body.index("add_primary_culture = cu:$RESULT$"), hook)  # the primary flag reads the primary
        self.assertLess(hook, body.index("change_pop_culture"))
        self.assertLess(body.index("te_cm_converted_$MERGE$"), hook)
        # Inside the branch that converts: after the pause test cleared it.
        self.assertLess(body.index("limit = { local_var:te_cm_cv_fail = 0 }"), hook)

    def test_the_switch_hook_runs_before_anything_is_converted_or_added(self):
        body = squash(block(text_of(MERGE_EFFECTS), "te_cm_switch_part"))
        hook = body.index("te_cm_chk_switch = ")
        self.assertLess(body.index("save_temporary_scope_as = te_cm_result"), hook)  # the result is saved first
        self.assertLess(hook, body.index("change_pop_culture"))
        self.assertLess(hook, body.index("add_homeland"))

    def test_the_header_lists_every_hook_and_row(self):
        header = CHECK_ON_ACTIONS.read_text(encoding="utf-8-sig").split("\n\n", 1)[0]
        self.assertIn("TEMPORARY", header)
        self.assertIn("delete after the 1.3.x play-test", header)
        self.assertIn("docs/testing/culture-merges-playtest.md", header)
        for name in SELFCHECKS:
            self.assertIn(name, header, name)
        for _, helper_block, call in self.HOOKS:
            self.assertIn(call.split(" ")[0], header, call)

    def test_the_monthly_hook_calls_the_four_monthly_passes(self):
        text = text_of(CHECK_ON_ACTIONS)
        self.assertEqual(squash(block(text, "on_monthly_pulse_country")), "on_actions = { te_cm_chk_monthly_on_action }")
        body = squash(block(text, "te_cm_chk_monthly_on_action"))
        for call in ("te_cm_chk_conversion_monthly", "te_cm_chk_switch_monthly", "te_cm_chk_formation_monthly",
                     "te_cm_chk_russification_monthly"):
            self.assertEqual(body.count(call + " = yes"), 1, call)
        # Each pass defined once in the effects file, and first-guarded by its own latch.
        effects = text_of(CHECK_EFFECTS)
        for call in ("te_cm_chk_conversion_monthly", "te_cm_chk_switch_monthly", "te_cm_chk_formation_monthly",
                     "te_cm_chk_russification_monthly"):
            self.assertIsNotNone(block(effects, call), call)


class LatchTest(unittest.TestCase):
    def test_a_check_that_has_spoken_does_not_wake_again(self):
        # Every pass's first limit clause is the cheap once-guard, so a check that has spoken costs one read.
        for name, start in (
            ("te_cm_chk_conversion_monthly", "NOT = { has_global_variable = te_cm_chk_conversion_merges_pops_done }"),
            ("te_cm_chk_switch_monthly", "NOT = { has_global_variable = te_cm_chk_switch_homeland_done }"),
            ("te_cm_chk_formation_monthly", "NOT = { has_global_variable = te_cm_chk_formation_keeps_primary_done }"),
        ):
            body = squash(block(text_of(CHECK_EFFECTS), name))
            self.assertTrue(body.startswith("if = { limit = { " + start), name)

    def test_degenerate_inputs_are_left_out(self):
        text = text_of(CHECK_EFFECTS)
        census = squash(block(text, "te_cm_chk_census"))
        # census_sane: the sphere must hold some of the part in its homeland states, or 0 would read as OK and BROKEN, and the part
        # must have an owned homeland state: the world fallback notes its holders in country scope, which proves nothing about
        # the write from inside owner = { }.
        self.assertIn("local_var:te_cm_cp_pops > 0", census)
        self.assertIn("local_var:te_cm_cp_states > 0", census)
        # acceptance_scale: a primary culture with a real share of the country's pops, not a handful.
        self.assertIn("country_has_primary_culture = cu:$CULTURE$", census)
        self.assertRegex(census, r"culture_percent_country = \{ target = cu:\$CULTURE\$ value >= 0\.1 \}")
        # census_yearly: only the second census reaches a verdict; the first logs START.
        year = squash(block(text, "te_cm_chk_census_year"))
        self.assertIn("TE_SELF_CHECK START cm_census_yearly", year)
        # rate_inputs: the starter's own accepted homeland pop, the base case the pace was tuned on.
        conversion = squash(block(text, "te_cm_chk_conversion"))
        self.assertIn("this = scope:te_cm_starter", conversion)
        self.assertIn("pop_acceptance >= acceptance_status_4", conversion)
        self.assertIn("is_homeland = scope:te_cm_part", conversion)
        # switch_homeland: a part with homeland states to check.
        switch = squash(block(text, "te_cm_chk_switch"))
        self.assertIn("local_var:te_cm_chk_n > 0", switch)
        # fervor_copy: a source with fervor to copy, and the culture zeroed before the ladder copies, so a copy that did
        # nothing reads 0, not the target.
        fervor = squash(block(text, "te_cm_chk_fervor"))
        self.assertIn("scope:te_cm_fervor_source = { culture_current_fervor >= 5 }", fervor)
        self.assertLess(fervor.index("set_fervor = 0"), fervor.index("te_cmg_set_fervor_from_source = yes"))
        # conversion_merges_pops: the first pass must have made a result pop to compare the second against.
        monthly = squash(block(text, "te_cm_chk_conversion_monthly"))
        self.assertIn("global_var:te_cm_chk_conv_inc1 >= 1", monthly)
        # The sample's cultures are saved inside the block that picks the state, not from a global read back after it.
        self.assertNotIn("limit = { has_global_variable = te_cm_chk_conv_stage } cu:", conversion)
        self.assertLess(conversion.index("random_scope_state"), conversion.index("name = te_cm_chk_conv_part"))
        self.assertLess(conversion.index("name = te_cm_chk_conv_part"), conversion.index("name = te_cm_chk_conv_stage value = 1"))

    def test_the_verdict_logic(self):
        text = text_of(CHECK_EFFECTS)
        census = squash(block(text, "te_cm_chk_census"))
        for needle in ("global_var:te_cm_chk_home > 0", "global_var:te_cm_chk_held > 0", "global_var:te_cm_chk_held <= 1",
                       "global_var:te_cm_chk_holder > 0", "NOT = { global_var:te_cm_chk_pops > global_var:te_cm_chk_home }"):
            self.assertIn(needle, census)
        self.assertIn("value >= te_cm_accept_open", census)  # the very value the census gates on
        year = squash(block(text, "te_cm_chk_census_year"))
        self.assertIn("global_var:te_cm_chk_census_gap = 1", year)
        conversion = squash(block(text, "te_cm_chk_conversion"))
        self.assertIn("global_var:te_cm_chk_rate > 0", conversion)
        self.assertIn("global_var:te_cm_chk_rate <= 0.5", conversion)
        monthly = squash(block(text, "te_cm_chk_conversion_monthly"))
        self.assertIn("global_var:te_cm_chk_conv_inc2 < global_var:te_cm_chk_conv_half", monthly)
        switch = squash(block(text, "te_cm_chk_switch_monthly"))
        for needle in ("global_var:te_cm_chk_sw_after = global_var:te_cm_chk_sw_before",
                       "global_var:te_cm_chk_sw_by_scope = global_var:te_cm_chk_sw_after",
                       "global_var:te_cm_chk_sw_by_global = global_var:te_cm_chk_sw_after",
                       "is_homeland = scope:te_cm_chk_sw_res", "is_homeland = global_var:te_cm_chk_sw_result"):
            self.assertIn(needle, switch)
        fervor = squash(block(text, "te_cm_chk_fervor_monthly"))
        for needle in ("global_var:te_cm_chk_fv_target >= 5",
                       "global_var:te_cm_chk_fv_later >= global_var:te_cm_chk_fv_low",
                       "global_var:te_cm_chk_fv_later <= global_var:te_cm_chk_fv_high",
                       "change_global_variable = { name = te_cm_chk_fv_low add = -2.5 }",
                       "change_global_variable = { name = te_cm_chk_fv_high add = 2 }"):
            self.assertIn(needle, fervor)
        russia = squash(block(text, "te_cm_chk_russification_monthly"))
        self.assertIn("has_global_variable = te_cm_russification_injected_fired", russia)
        self.assertIn("te_cm_russification_complete = yes", russia)
        self.assertIn("has_journal_entry = je_russification", russia)
        self.assertIn("var:te_cm_chk_rus_n >= 2", russia)


class ConsoleMenuTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = EVENTS.read_text(encoding="utf-8-sig")
        cls.nodes = {n.key: n for n in parse(cls.text) if n.children}

    def event(self):
        return self.nodes["te_debug_cm.1"]

    def test_the_menu_is_console_only_and_documented_as_such(self):
        self.assertRegex(self.text, r"^namespace = te_debug_cm$".replace("^", "(?m)^"))
        self.assertIn(
            "te_debug_cm.1 = { # REVIEWED 2026-11-07: console-only test event (event te_debug_cm.1); never fired by script on purpose",
            self.text,
        )
        self.assertNotRegex(text_of(ROOT / "events/te_debug_cm_events.txt"), r"trigger_event")
        # Nothing but the console fires it.
        for path in list((ROOT / "common").rglob("*.txt")) + list((ROOT / "events").glob("*.txt")):
            self.assertNotRegex(path.read_text(encoding="utf-8-sig", errors="replace"), r"id = te_debug_cm\.", path.name)

    def test_the_menu_has_an_image_another_debug_event_already_uses(self):
        event = self.event()
        image = event.child("event_image")
        self.assertIsNotNone(image)
        texture = image.child("texture").value.strip('"')
        used = [p.name for p in (ROOT / "events").glob("te_debug_*_events.txt")
                if p.name != "te_debug_cm_events.txt" and texture in p.read_text(encoding="utf-8-sig")]
        self.assertTrue(used, "%s is used by no other te_debug_* event" % texture)

    def test_options_a_to_d_call_the_named_helpers_behind_the_rule(self):
        options = [c for c in self.event().children if c.key == "option"]
        calls = []
        for option in options:
            names = {n.key for n, _ in walk(option.children)}
            calls.append(names)
        by_helper = {
            "te_cmg_census_all": "A",
            "te_cmg_yearly_country": "B",
            "te_cmg_dominance_all": "C",
            "te_cmg_debug_dump": "D",
        }
        found = {}
        for option, names in zip(options, calls):
            for helper, letter in by_helper.items():
                if helper in names:
                    found[letter] = option
        self.assertEqual(sorted(found), ["A", "B", "C", "D"])
        for letter, option in found.items():
            trig = option.child("trigger")
            self.assertIsNotNone(trig, letter)
            self.assertTrue(any(n.key == "te_cm_system_enabled" for n, _ in walk(trig.children)), letter)
        # A runs the census with no lock and no year guard; it neither sets nor reads them.
        a = found["A"]
        a_names = {n.key for n, _ in walk(a.children)}
        self.assertNotIn("te_cm_census_lock", " ".join(n.value or "" for n, _ in walk(a.children)))
        self.assertNotIn("has_global_variable", a_names)

    def test_a_close_option_and_a_loc_key_for_every_text(self):
        keys = all_english_loc_keys()
        event = self.event()
        for field in ("title", "desc", "flavor"):
            self.assertIn(event.child(field).value, keys, field)
        options = [c for c in event.children if c.key == "option"]
        self.assertGreaterEqual(len(options), 5)
        for option in options:
            self.assertIn(option.child("name").value, keys)
        # The last option closes the menu: no effect of its own.
        self.assertEqual([c.key for c in options[-1].children], ["name", "default_option"])
        # No option key collides with the description key.
        names = [o.child("name").value for o in options]
        self.assertNotIn("te_debug_cm.1.d", names)

    def test_the_dump_is_generated_for_every_merge_and_slot(self):
        body = block(text_of(GEN_EFFECTS), "te_cmg_debug_dump")
        self.assertIsNotNone(body)
        flat = squash(body)
        for merge in cfg.MERGES:
            # Only a merge with a core wait has the wait counter, so only it names te_cm_wait_years_<m>: a read of a
            # name nothing sets logs "is used but is never set" at every load (2026-11-08).
            waiting = bool(gen.core_waits(merge))
            self.assertEqual(flat.count("te_cm_debug_dump_merge_waiting = { MERGE = %s }" % merge.key), int(waiting), merge.key)
            self.assertEqual(flat.count("te_cm_debug_dump_merge = { MERGE = %s }" % merge.key), int(not waiting), merge.key)
            optional = {c for part in merge.optional for c in part.cultures}
            for culture in gen._joinable_slot_cultures(merge):
                # An optional part answers to its own standard-of-living gate, a core part to the merge's.
                gate = "te_cm_sol_ok_%s_%s" % (merge.key, culture) if culture in optional else "te_cm_sol_ok_%s" % merge.key
                self.assertEqual(
                    flat.count("te_cm_debug_dump_part = { MERGE = %s CULTURE = %s SOL_OK = %s }" % (merge.key, culture, gate)),
                    1, "%s/%s" % (merge.key, culture))
            for culture in slot_cultures(merge):
                if gen._is_absorb_result(merge, culture):
                    self.assertNotIn("te_cm_debug_dump_part = { MERGE = %s CULTURE = %s " % (merge.key, culture), flat)
            # Only the merges ROOT is a candidate for or that are not idle.
            self.assertIn(
                "limit = { OR = { global_var:te_cm_state_%s ?= 1 global_var:te_cm_state_%s ?= 2 te_cmg_%s_is_candidate = yes } }"
                % (merge.key, merge.key, merge.key), flat, merge.key)

    def test_the_dump_helpers_read_each_variable_behind_a_guard(self):
        text = text_of(CONSOLE_EFFECTS)
        for helper in ("te_cm_debug_dump_merge", "te_cm_debug_dump_merge_waiting", "te_cm_debug_dump_merge_slots",
                       "te_cm_debug_dump_merge_line", "te_cm_debug_dump_part", "te_cm_dbg_global", "te_cm_dbg_var"):
            self.assertIsNotNone(block(text, helper), helper)
        part = squash(block(text, "te_cm_debug_dump_part"))
        for name in ("te_cm_home_$CULTURE$", "te_cm_home_r_$CULTURE$", "te_cm_joined_$MERGE$_$CULTURE$",
                     "te_cm_dom_$MERGE$_$CULTURE$", "te_cm_in_$CULTURE$", "te_cm_held_$MERGE$_$CULTURE$",
                     "te_cm_ok_$MERGE$_$CULTURE$", "te_cm_sol_$MERGE$_$CULTURE$", "$SOL_OK$",
                     "te_cm_years_$MERGE$_$CULTURE$", "te_cm_paused_$MERGE$_$CULTURE$"):
            self.assertIn("NAME = " + name, part)
        slots = squash(block(text, "te_cm_debug_dump_merge_slots"))
        for name in ("te_cm_state_$MERGE$", "te_cm_sol_ok_$MERGE$", "te_cm_started_$MERGE$",
                     "te_cm_bar_$MERGE$", "te_cm_converted_$MERGE$"):
            self.assertIn("NAME = " + name, slots)
        # The wait counter only in the waiting form; the other prints -1 in its slot.
        self.assertIn("NAME = te_cm_wait_years_$MERGE$", squash(block(text, "te_cm_debug_dump_merge_waiting")))
        self.assertNotIn("te_cm_wait_years_", squash(block(text, "te_cm_debug_dump_merge")))
        self.assertIn("name = te_cm_dbg_j value = -1", squash(block(text, "te_cm_debug_dump_merge")))
        merge = slots
        # The starter is a country, so it is logged as a yes/no, and where this country stands in the merge.
        for needle in ("exists = global_var:te_cm_starter_$MERGE$", "te_cmg_$MERGE$_is_starter = yes",
                       "te_cmg_$MERGE$_is_candidate = yes", "te_cmg_$MERGE$_core_ok = yes", "te_cmg_$MERGE$_can_start = yes"):
            self.assertIn(needle, merge)
        # A variable name never goes inside a [..] accessor with a $X$ in it.
        for node, _ in walk(file_nodes(CONSOLE_EFFECTS)):
            if node.key == "debug_log":
                for accessor in re.findall(r"\[([^\]]*)\]", node.value):
                    self.assertNotIn("$", accessor)
        # Unset reads as -1, written by the guarded helper.
        self.assertIn("value = -1", squash(block(text, "te_cm_dbg_global")))
        self.assertIn("has_global_variable = $NAME$", squash(block(text, "te_cm_dbg_global")))
        self.assertIn("has_variable = $NAME$", squash(block(text, "te_cm_dbg_var")))


class PlaytestDocTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = PLAYTEST.read_text(encoding="utf-8")

    def table(self):
        m = re.search(r"^## Self-checks\n(.*?)(?=^## )", self.text, re.M | re.S)
        self.assertIsNotNone(m, "no '## Self-checks' section")
        return m.group(1)

    def test_playtest_doc_lists_every_selfcheck(self):
        table = self.table()
        self.assertIn("| Line | Means | Fallback if BROKEN |", table)
        rows = [line for line in table.splitlines() if line.startswith("| `TE_SELF_CHECK")]
        for name in SELFCHECKS:
            hits = [r for r in rows if re.search(r"TE_SELF_CHECK[^`]*\b%s\b" % name, r)]
            self.assertEqual(len(hits), 1, name)
            cells = [c.strip() for c in hits[0].strip("|").split("|")]
            self.assertEqual(len(cells), 3, name)
            self.assertTrue(all(cells), name)

    def test_every_row_names_what_no_line_at_all_means(self):
        # A check may never fire in a short game; the table says so beside each row.
        for line in self.table().splitlines():
            if line.startswith("| `TE_SELF_CHECK"):
                self.assertRegex(line, r"No line|no line|No verdict|no verdict", line[:60])

    def test_the_list_collects_every_unverified_item(self):
        topics = {
            "the rule off and on": r"switch(?:ed)? the rule off",
            "a candidate's entry comes back": r"entr(?:y|ies) (?:come|comes|return|returns)|comes? back",
            "nested custom_tooltip reasons": r"custom_tooltip",
            "set_bar_progress through scope:journal_entry": r"set_bar_progress",
            "the AI presses the button": r"AI presses|the AI",
            "dead-starter release": r"dead[- ]starter|starter dies|starter is gone",
            "civil war winner takes over": r"civil war",
            "te_cm_started_ inherited": r"te_cm_started_",
            "the old tag survives": r"old tag",
            "re-adding a concluded entry": r"re-add",
            "Russification two success rows": r"two success",
            "Russification map highlight": r"map highlight|highlight",
            "merged traits load": r"discrimination_traits",
            "cm_ cultures in the culture lists": r"culture lists?",
            "21 empty cultures": r"21 ",
            "change_pop_culture with a named script value": r"change_pop_culture",
            "global_var ?= cu": r"\?= cu:",
            "on_country_formed for a released country": r"released",
            "census cost, rule on vs off": r"rule on vs off|on versus off|on against off",
            "R26 result-SoL walk cost": r"R26|result_sol|result-SoL",
            "the entry's layout": r"layout",
            "a full German merge in an observer game": r"German",
            "a switch reaching a foreign-held homeland": r"foreign-held",
            "Bavaria released after the switch": r"Bavaria",
            "a kept part homeland with no pops": r"no pops",
            "the numeric global ?=": r"global_var:[a-z_<>]+ \?= (?:N|a number|1)",
            "te_cm_in_sphere from state scope": r"te_cm_in_sphere",
            "is_homeland = global_var": r"is_homeland = global_var",
        }
        for topic, pattern in topics.items():
            self.assertIsNotNone(re.search(pattern, self.text, re.I), "the play-test list says nothing about: " + topic)

    def test_each_area_has_a_heading(self):
        headings = re.findall(r"^## (.+)$", self.text, re.M)
        self.assertIn("Self-checks", headings)
        self.assertGreaterEqual(len(headings), 8, headings)

    def test_the_doc_is_american_and_uses_hash_b_bold(self):
        self.assertNotIn("[b]", self.text)
        for word in ("colour", "behaviour", "neighbour ", "licence"):
            self.assertNotIn(word, self.text)


if __name__ == "__main__":
    unittest.main()
