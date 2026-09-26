# -*- coding: utf-8 -*-
"""UN state mirrors (docs/systems/un_redesign_design.md §0.9).

A revolution's winner inherits je_united_nations with the loser's variables
and none of its modifiers, so every UN state modifier has a mirror variable,
``<modifier>_on``, and the entry is rebuilt from the mirrors
(common/scripted_effects/un_state_effects.txt). The rebuild is only as good as
the mirrors: one write site that adds or removes a modifier without its mirror
and the winner of the next revolution silently gains or loses it. Nothing in
the engine checks that, so these tests do.
"""

import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))


def _path(*parts):
    return os.path.join(REPO, *parts)


def _read(path):
    with open(path, encoding="utf-8-sig") as f:
        return re.sub(r"#[^\n]*", "", f.read())


def _block(text, name):
    """The body of the top-level ``name = { ... }`` block."""
    m = re.search(r"^" + re.escape(name) + r"\s*=\s*\{", text, re.M)
    if m is None:
        raise AssertionError(f"{name} not found")
    depth = 0
    for i in range(m.end() - 1, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[m.end():i]
    raise AssertionError(f"{name} is not closed")


# ---- The mirrored modifiers, by how they are written ------------------------------

JE_PLAIN = [
    "un_member_modifier",
    "un_founding_member_modifier",
    "un_headquarters_modifier",
    "un_security_council_modifier",
    "un_permanent_member_modifier",
    "un_peacekeeping_contributor_modifier",
    "un_development_contributor_modifier",
    "un_human_rights_champion_modifier",
    "un_arms_control_participant_modifier",
    "un_champion_order_cost",
    "un_undermine_order_cost",
]
# Added with multiplier = root.var:<expense>, so written at the site itself.
JE_COST = [
    "un_peacekeeping_contributor_cost",
    "un_development_contributor_cost",
]
JE_CONVENTION = [
    "un_human_rights_declaration_modifier",
    "un_nonproliferation_modifier",
    "un_climate_binding_modifier",
    "un_heritage_program_modifier",
    "un_pandemic_cooperation_modifier",
    "un_refugee_program_modifier",
    "un_space_partnership_modifier",
]
COUNTRY_CONVENTION = [
    "un_law_of_sea_modifier",
    "un_icc_member_modifier",
    "un_physical_protection_modifier",
]
MIRRORED = JE_PLAIN + JE_COST + JE_CONVENTION + COUNTRY_CONVENTION

# Which names each helper may be called with.
HELPER_NAMES = {
    "un_state_on": set(JE_PLAIN),
    "un_state_off": set(JE_PLAIN + JE_COST + JE_CONVENTION),
    "un_convention_on": set(JE_CONVENTION),
    "un_convention_country_on": set(COUNTRY_CONVENTION),
    "un_state_country_off": set(COUNTRY_CONVENTION),
    "un_state_record": set(MIRRORED),
    "un_state_forget": set(MIRRORED),
    "un_state_restore": set(JE_PLAIN),
    "un_convention_restore": set(JE_CONVENTION),
    "un_convention_country_restore": set(COUNTRY_CONVENTION),
    "un_state_missing": set(JE_PLAIN + JE_COST + JE_CONVENTION),
    "un_state_country_missing": set(COUNTRY_CONVENTION),
    "un_state_reconcile_one": set(JE_PLAIN + JE_COST + JE_CONVENTION),
    "un_state_reconcile_country": set(COUNTRY_CONVENTION),
}

STATE_EFFECTS = _path("common", "scripted_effects", "un_state_effects.txt")
STATE_TRIGGERS = _path("common", "scripted_triggers", "un_state_triggers.txt")
JE = _path("common", "journal_entries", "je_united_nations.txt")

# Files whose writes are not UN state.
EXEMPT_FILES = {
    # One-shot save migration: the country-scope removes are an old layout,
    # and the journal-entry adds it makes are recorded by the monthly
    # reconcile (un_state_reconcile).
    os.path.join("common", "scripted_effects", "legacy_modifier_cleanup.txt"),
}
# Top-level definitions that write a mirrored modifier without its mirror on
# purpose.
EXEMPT_DEFINITIONS = {
    "un_state_restore_all": "adds only what its mirror already records",
    "te_debug_un_wipe_entry": "does what a revolution does: modifiers go, mirrors stay",
    "te_debug_un_drop": "the wipe's helper",
}
# Blocks whose effects are never run.
DISPLAY_ONLY_BLOCKS = {"show_as_tooltip", "event_outcome_activated_effect_desc"}
# Blocks that wrap a single write and are not the site's own statement list.
WRAPPER_BLOCKS = {"je:je_united_nations", "add_modifier"}

_NAMES = "|".join(MIRRORED)
_WRITE = re.compile(
    r"\b(?P<op>add_modifier|remove_modifier)\s*=\s*"
    r"(?:\{\s*name\s*=\s*(?P<a>" + _NAMES + r")\b|(?P<r>" + _NAMES + r")\b)"
)
_TOKEN = re.compile(
    r"(?P<open>(?P<key>[A-Za-z0-9_:.@$\-]+)\s*\??=\s*\{)|(?P<anon>\{)|(?P<close>\})"
)
_TOP = re.compile(r"^([A-Za-z_][A-Za-z0-9_.]*)\s*=\s*\{", re.M)


def _blocks(text):
    """Every block as (key, body_start, body_end); key is None for a bare {."""
    stack, blocks = [], []
    for m in _TOKEN.finditer(text):
        if m.group("close"):
            key, start = stack.pop()
            blocks.append((key, start, m.start()))
        else:
            stack.append((m.group("key"), m.end()))
    assert not stack, "unbalanced braces"
    return blocks


def _enclosing(blocks, pos):
    """The blocks around pos, innermost first."""
    around = [b for b in blocks if b[1] <= pos < b[2]]
    return sorted(around, key=lambda b: b[1], reverse=True)


def _script_files():
    for root in ("common", "events"):
        for dirpath, _dirs, files in os.walk(_path(root)):
            for f in files:
                if f.endswith(".txt"):
                    yield os.path.join(dirpath, f)


def _body_at(text, open_idx):
    """The body of the block whose `{` is at open_idx, and the index of its `}`."""
    depth = 0
    for i in range(open_idx, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[open_idx + 1:i], i
    raise AssertionError("block is not closed")


def _unpaired_in(text, rel):
    """Each literal add/remove of a mirrored modifier in text whose statement
    list has no matching mirror write."""
    bad = []
    blocks = None
    for m in _WRITE.finditer(text):
        blocks = blocks if blocks is not None else _blocks(text)
        around = _enclosing(blocks, m.start())
        keys = [b[0] for b in around]
        top = keys[-1] if keys else None
        if top in EXEMPT_DEFINITIONS or DISPLAY_ONLY_BLOCKS & set(keys):
            continue
        site = next(b for b in around if b[0] not in WRAPPER_BLOCKS)
        body = text[site[1]:site[2]]
        name = m.group("a") or m.group("r")
        if m.group("op") == "add_modifier":
            pattern = (r"un_state_record\s*=\s*\{\s*MODIFIER\s*=\s*" + name + r"\s*\}"
                       r"|set_variable\s*=\s*" + name + r"_on\b")
        else:
            pattern = (r"un_state_forget\s*=\s*\{\s*MODIFIER\s*=\s*" + name + r"\s*\}"
                       r"|remove_variable\s*=\s*" + name + r"_on\b")
        if not re.search(pattern, body):
            line = text.count("\n", 0, m.start()) + 1
            bad.append(f"{rel}:{line} {m.group('op')} {name} (in {top})")
    return bad


def _unpaired_writes():
    bad = []
    for path in _script_files():
        rel = os.path.relpath(path, REPO)
        if rel in EXEMPT_FILES:
            continue
        text = _read(path)
        if any(name in text for name in MIRRORED):
            bad += _unpaired_in(text, rel)
    return bad


class WriteSiteTests(unittest.TestCase):
    def test_every_write_keeps_its_mirror(self):
        self.assertEqual(_unpaired_writes(), [])

    def test_helpers_are_called_with_the_right_names(self):
        call = re.compile(r"\b(" + "|".join(HELPER_NAMES) + r")\s*=\s*\{\s*MODIFIER\s*=\s*(\w+)\s*\}")
        wrong = []
        for path in _script_files():
            text = _read(path)
            for m in call.finditer(text):
                helper, name = m.groups()
                if name not in HELPER_NAMES[helper]:
                    rel = os.path.relpath(path, REPO)
                    line = text.count("\n", 0, m.start()) + 1
                    wrong.append(f"{rel}:{line} {helper} {name}")
        self.assertEqual(wrong, [])

    def test_the_check_finds_an_unpaired_write(self):
        text = (
            "x = {\n"
            "\tje:je_united_nations ?= { add_modifier = { name = un_member_modifier } }\n"
            "\tun_state_record = { MODIFIER = un_member_modifier }\n"
            "}\n"
            "y = {\n"
            "\tif = {\n"
            "\t\tlimit = { always = yes }\n"
            "\t\tje:je_united_nations ?= { remove_modifier = un_champion_order_cost }\n"
            "\t}\n"
            "\tun_state_forget = { MODIFIER = un_champion_order_cost }\n"
            "}\n"
            "z = {\n"
            "\tshow_as_tooltip = { add_modifier = { name = un_law_of_sea_modifier } }\n"
            "}\n"
        )
        # x pairs its write; y forgets outside the `if` that removes; z only
        # previews.
        self.assertEqual(_unpaired_in(text, "t"),
                         ["t:8 remove_modifier un_champion_order_cost (in y)"])


class RebuildTests(unittest.TestCase):
    def setUp(self):
        self.effects = _read(STATE_EFFECTS)
        self.triggers = _read(STATE_TRIGGERS)

    def test_rebuild_restores_every_mirror(self):
        self.assertIn("un_state_restore_all = yes", _block(self.effects, "un_state_rebuild"))
        body = _block(self.effects, "un_state_restore_all")
        for name in MIRRORED:
            with self.subTest(modifier=name):
                self.assertRegex(
                    body,
                    r"(restore\s*=\s*\{\s*MODIFIER\s*=\s*" + name + r"\s*\}"
                    r"|name\s*=\s*" + name + r"\b)")

    def test_restore_forgets_nothing(self):
        """`immediate` runs mid-transition (the loser may still own a state,
        the headquarters variable may still name it), so what it reaches may
        only add. Forgetting is the pulse heal's (un_state_rebuild)."""
        reached, todo = set(), ["un_state_restore_all"]
        while todo:
            name = todo.pop()
            if name in reached:
                continue
            reached.add(name)
            body = _block(self.effects, name)
            for call in re.findall(r"\b(un_[a-z_]+)\s*=\s*(?:yes|\{)", body):
                if re.search(r"^" + call + r"\s*=\s*\{", self.effects, re.M):
                    todo.append(call)
        self.assertNotIn("un_state_forget", reached)
        self.assertNotIn("un_state_off", reached)
        for name in reached:
            body = _block(self.effects, name)
            with self.subTest(effect=name):
                self.assertNotRegex(body, r"un_state_forget|un_state_off|remove_modifier")
                self.assertEqual(re.findall(r"remove_variable\s*=\s*(\w+)", body),
                                 ["un_regime_stamp"] if name == "un_state_restore_all" else [])

    def test_mirrors_are_recorded_only_where_the_entry_exists(self):
        for name in ("un_state_on", "un_convention_on"):
            with self.subTest(helper=name):
                self.assertRegex(
                    _block(self.effects, name),
                    r"if\s*=\s*\{\s*limit\s*=\s*\{\s*exists = je:je_united_nations\s*\}\s*"
                    r"un_state_record")

    def test_rebuild_forgets_what_it_cannot_honour(self):
        forgotten = (_block(self.effects, "un_state_forget_representation")
                     + _block(self.effects, "un_state_forget_conventions"))
        for name in MIRRORED:
            if name in ("un_member_modifier", "un_founding_member_modifier",
                        "un_headquarters_modifier"):
                continue
            with self.subTest(modifier=name):
                self.assertIn("MODIFIER = " + name + " }", forgotten)

    def test_reconcile_and_heal_cover_every_mirror(self):
        reconcile = _block(self.effects, "un_state_reconcile")
        heal = _block(self.triggers, "un_state_heal_needed")
        for name in MIRRORED:
            with self.subTest(modifier=name):
                self.assertIn("MODIFIER = " + name + " }", reconcile)
                self.assertIn("MODIFIER = " + name + " }", heal)

    def test_debug_wipe_strips_every_mirrored_modifier(self):
        body = _block(_read(_path("common", "scripted_effects", "te_debug_un_effects.txt")),
                      "te_debug_un_wipe_entry")
        for name in MIRRORED:
            with self.subTest(modifier=name):
                self.assertRegex(body, r"(MODIFIER = |remove_modifier = )" + name + r"\b")
        self.assertIn("un_state_rebuild_pending", body)

    def test_mirror_name_is_the_modifier_name(self):
        for helper in ("un_state_record", "un_state_forget"):
            with self.subTest(helper=helper):
                self.assertIn("$MODIFIER$_on", _block(self.effects, helper))
        self.assertIn("$MODIFIER$_on", _block(self.triggers, "un_state_missing"))


class JournalEntryTests(unittest.TestCase):
    def setUp(self):
        self.je = _read(JE)

    def test_immediate_marks_and_rebuilds(self):
        body = _block(self.je, "je_united_nations")
        start = re.search(r"^\timmediate\s*=\s*\{", body, re.M).end()
        immediate = body[start:body.index("\n\t}\n", start)]
        self.assertIn("set_variable = un_state_rebuild_pending", immediate)
        # Restore only: the forgetting rebuild belongs to the pulse.
        self.assertIn("un_state_restore_all = yes", immediate)
        self.assertNotIn("un_state_rebuild = yes", immediate)
        self.assertNotIn("un_state_rebuild = yes",
                         _block(self.je, "je_united_nations").split("on_monthly_pulse")[0])

    def test_pulse_heals_first_and_otherwise_runs_as_usual(self):
        body = _block(self.je, "je_united_nations")
        m = re.search(r"^\ton_monthly_pulse\s*=\s*\{\s*effect\s*=\s*(\{)", body, re.M)
        effect, _ = _body_at(body, m.start(1))
        m_if = re.match(r"\s*if\s*=\s*(\{)", effect)
        self.assertIsNotNone(m_if, "the pulse must open with the heal")
        heal, end_if = _body_at(effect, m_if.start(1))
        self.assertRegex(heal, r"^\s*limit\s*=\s*\{\s*un_state_heal_needed = yes\s*\}\s*"
                               r"un_state_heal = yes\s*$")
        m_else = re.match(r"\s*else\s*=\s*(\{)", effect[end_if + 1:])
        self.assertIsNotNone(m_else, "the heal must have an else")
        rest, end_else = _body_at(effect, end_if + 1 + m_else.start(1))
        self.assertRegex(rest, r"^\s*un_state_reconcile = yes\b")
        self.assertEqual(effect[end_else + 1:].strip(), "", "nothing may follow the else")
        for call in ("un_standing_country_pulse = yes", "un_regime_country_pulse = yes",
                     "un_join_organisation = yes", "un_representation_monthly_update = yes"):
            with self.subTest(call=call):
                self.assertIn(call, rest)


class GlobalPulseTests(unittest.TestCase):
    def test_seat_count_counts_the_mirror(self):
        body = _block(_read(_path("common", "script_values", "un_script_values.txt")),
                      "un_permanent_seat_count")
        self.assertIn("has_variable = un_permanent_member_modifier_on", body)
        self.assertIn("is_country_alive = yes", body)

    def test_headquarters_host_survives_the_window(self):
        host = _block(_read(_path("common", "scripted_triggers", "un_hq_triggers.txt")),
                      "un_hq_is_host")
        self.assertIn("has_variable = un_headquarters_modifier_on", host)
        hq = _read(_path("common", "scripted_effects", "un_hq_effects.txt"))
        self.assertIn("un_member_represented_by_record = yes", _block(hq, "un_hq_monthly_update"))
        enforce = _block(hq, "un_hq_enforce_single_building")
        self.assertEqual(enforce.count("NOT = { un_hq_is_host = yes }"), 2)

    def test_civil_war_repair_hangs_off_the_shared_layer(self):
        """#467's te_civil_war_on_won calls the UN's repair; the UN declares no
        civil-war hook of its own and keeps no which-side-won pointer."""
        shared = _block(_read(_path("common", "on_actions", "te_civil_war_on_actions.txt")),
                        "te_civil_war_on_won")
        self.assertIn("un_repair_after_civil_war = yes", shared)
        self.assertLess(shared.index("te_civil_war_resolve_sides = yes"),
                        shared.index("un_repair_after_civil_war = yes"))
        self.assertLess(shared.index("un_repair_after_civil_war = yes"),
                        shared.index("te_civil_war_clear = yes"))
        un = _read(_path("common", "on_actions", "un_on_actions.txt"))
        for hook in ("on_revolution_start", "on_secession_start", "on_civil_war_won",
                     "on_revolution_end", "on_secession_end"):
            with self.subTest(hook=hook):
                self.assertNotRegex(un, r"^" + hook + r"\s*=", "declared in te_civil_war_on_actions.txt")
        for path in _script_files():
            with self.subTest(path=os.path.relpath(path, REPO)):
                self.assertNotRegex(_read(path), r"\bun_cw_rebel\b")

        repair = _block(_read(STATE_EFFECTS), "un_repair_after_civil_war")
        # The rebels' win marks the entry; the headquarters is handed on.
        self.assertRegex(repair, r"has_variable = te_cw_rebels_won\s*var:te_cw_rebels_won = 1")
        self.assertIn("set_variable = un_state_rebuild_pending", repair)
        self.assertIn("un_hq_adopt_as_successor = yes", repair)
        # Nothing on the journal entry is rebuilt from the hook: its order
        # against the inherited entry's `immediate` is unknown.
        self.assertNotIn("un_state_rebuild = yes", repair)
        self.assertNotIn("un_state_restore_all = yes", repair)
        self.assertNotIn("add_modifier", repair)

    def test_removals_are_guarded(self):
        """remove_modifier on a modifier the scope does not hold logs an error
        (#469); remove_variable is guarded by house style."""
        effects = _read(STATE_EFFECTS)
        self.assertRegex(_block(effects, "un_state_off"),
                         r"if\s*=\s*\{\s*limit\s*=\s*\{\s*has_modifier = \$MODIFIER\$\s*\}\s*"
                         r"remove_modifier = \$MODIFIER\$")
        self.assertIn("remove_modifier_if_exists_effect = { MODIFIER = $MODIFIER$ }",
                      _block(effects, "un_state_country_off"))
        for m in re.finditer(r"^([a-z_]+)\s*=\s*\{", effects, re.M):
            body = _block(effects, m.group(1))
            for v in re.finditer(r"remove_variable\s*=\s*(\S+)", body):
                with self.subTest(effect=m.group(1), variable=v.group(1)):
                    self.assertRegex(body[:v.start()],
                                     r"has_variable = " + re.escape(v.group(1)) + r"\s*\}\s*$")

    def test_the_successor_claims_the_headquarters_every_month(self):
        """The hook alone relies on the loser reading as dead at the win; the
        global pulse asks every mirror holder before it can reassign."""
        hq = _read(_path("common", "scripted_effects", "un_hq_effects.txt"))
        body = _block(hq, "un_hq_monthly_update")
        net = re.search(
            r"every_country\s*=\s*\{\s*limit\s*=\s*\{\s*has_variable = un_headquarters_modifier_on"
            r"\s*\}\s*un_hq_adopt_as_successor = yes\s*\}", body)
        self.assertIsNotNone(net)
        self.assertLess(net.start(), body.index("un_hq_assign_host = yes"))
        adopt = _block(_read(STATE_EFFECTS), "un_hq_adopt_as_successor")
        limit = _body_at(adopt, adopt.index("limit") + adopt[adopt.index("limit"):].index("{"))[0]
        # Never the dead loser; a dead host only of our definition; a vanished
        # host only for a represented member by the record.
        self.assertRegex(limit, r"^\s*is_country_alive = yes")
        self.assertRegex(limit, r"AND\s*=\s*\{\s*global_var:un_hq_country \?= \{ is_country_alive = no \}\s*"
                                r"country_definition = global_var:un_hq_country\.country_definition\s*\}")
        self.assertRegex(limit, r"AND\s*=\s*\{\s*NOT = \{ exists = global_var:un_hq_country \}\s*"
                                r"un_member_represented_by_record = yes\s*\}")

    def test_headquarters_waits_within_the_hosts_civil_war(self):
        text = _read(_path("common", "on_actions", "un_on_actions.txt"))
        body = _block(text, "un_hq_on_state_owner_change")
        self.assertRegex(
            body,
            r"limit\s*=\s*\{\s*NOT\s*=\s*\{\s*owner \?= \{\s*un_hq_shares_host_definition = yes"
            r"\s*\}\s*\}\s*\}\s*un_hq_enforce_single_building = yes")
        trig = _block(_read(_path("common", "scripted_triggers", "un_hq_triggers.txt")),
                      "un_hq_shares_host_definition")
        self.assertIn("NOT = { un_hq_is_host = yes }", trig)
        self.assertIn("country_definition = global_var:un_hq_country.country_definition", trig)

    def test_a_member_by_the_record_cannot_join_again(self):
        """A winner awaiting its rebuild must not rejoin: joining hands it every
        convention in force, the refused ones included."""
        needle = "NOT = { has_variable = un_member_modifier_on }"
        button = _block(_read(_path("common", "scripted_buttons", "un_buttons.txt")), "un_join_button")
        for part in ("visible", "possible"):
            with self.subTest(part=part):
                m = re.search(r"^\t" + part + r"\s*=\s*(\{)", button, re.M)
                self.assertIn(needle, _body_at(button, m.start(1))[0])
        events = _read(_path("events", "un_events.txt"))
        e10 = _block(events, "un_events.10")
        opt = e10[e10.index("name = un_events.10.e"):]
        self.assertIn(needle, opt[:opt.index("ai_chance")])
        e1 = _block(events, "un_events.1")
        m = re.search(r"^\ttrigger\s*=\s*(\{)", e1, re.M)
        self.assertIn(needle, _body_at(e1, m.start(1))[0])


if __name__ == "__main__":
    unittest.main()
