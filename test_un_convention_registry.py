# -*- coding: utf-8 -*-
"""The UN convention registry: every convention in one table, pinned against
every site that lists conventions by hand.

Adding a convention touches about thirty hand-kept places across twenty files:
the propose triggers and effects, the docket, the chamber's switches, widget
row and row renderer, un_vote.1 and un_vote.2, the treaty modifier and its
preview, the joiner's catch-up, the suspended member's snapshot and
restoration event, the regime layer, leaving and dissolution, the ledger log,
the AI's lean and the loc. Nothing in the engine checks that they agree, and a
missed one is engine-silent: a vote with no title, a convention a rejoining
member never regains, an agency a dissolution leaves standing.

CONVENTIONS is the single list. Each test checks one site against it in both
directions (no convention missing, no stale extra), so a half-added convention
fails here, naming the site, instead of in a play test. Add the new row first
and the failures are the checklist (docs/systems/journal_entry_systems.md,
"Adding a convention").

test_un_state_mirror.py (the §0.9 mirrors) and test_un_membership.py (the §0.8
catch-up) take their convention lists from here rather than keeping copies.
test_un_chamber_propose_ops.py checks that the op table agrees with itself;
this file checks that it agrees with CONVENTIONS.

Run: python3 -m unittest test_un_convention_registry -v
"""

import os
import re
import unittest
from collections import namedtuple

REPO = os.path.dirname(os.path.abspath(__file__))


def _path(*parts):
    return os.path.join(REPO, *parts)


PROPOSE_TRIGGERS = _path("common", "scripted_triggers", "un_propose_triggers.txt")
PROPOSE_EFFECTS = _path("common", "scripted_effects", "un_propose_effects.txt")
DOCKET_TRIGGERS = _path("common", "scripted_triggers", "un_docket_triggers.txt")
DOCKET_EFFECTS = _path("common", "scripted_effects", "un_docket_effects.txt")
CHAMBER_SGUIS = _path("common", "scripted_guis", "un_chamber_sguis.txt")
CHAMBER_DISPLAY = _path("common", "scripted_effects", "un_chamber_display_effects.txt")
WIDGET = _path("gui", "journal_entry_widgets", "un_chamber_widget.gui")
VOTE_EVENTS = _path("events", "un_vote_events.txt")
UN_EVENTS = _path("events", "un_events.txt")
VOTE_EFFECTS = _path("common", "scripted_effects", "un_vote_effects.txt")
VOTE_CAST = _path("common", "scripted_effects", "un_vote_cast_effects.txt")
RESOLUTION_TRIGGERS = _path("common", "scripted_triggers", "un_resolution_triggers.txt")
MEMBERSHIP_EFFECTS = _path("common", "scripted_effects", "un_membership_effects.txt")
MEMBERSHIP_TRIGGERS = _path("common", "scripted_triggers", "un_membership_triggers.txt")
REGIME_EFFECTS = _path("common", "scripted_effects", "un_regime_effects.txt")
REGIME_TRIGGERS = _path("common", "scripted_triggers", "un_regime_triggers.txt")
LADDER = _path("common", "scripted_effects", "un_ladder_effects.txt")
LEDGER_DISPLAY = _path("common", "scripted_effects", "un_authority_display_effects.txt")
DOSSIER = _path("common", "script_values", "un_dossier_values.txt")
STATIC_MODIFIERS = _path("common", "static_modifiers")
LOC_DIR = _path("localization", "english")

# ---- The table ----------------------------------------------------------------------

# key               the topic: un_topic_<key>, un_propose_<key>_*, un_docket_*_<key>
# in_force          the global variable passage sets: its agency, or for
#                   decolonization its standing regime
# member_modifier   what a party carries; None for decolonization, which binds
#                   the whole Assembly and has no parties
# scope             where member_modifier sits: "je" (je_united_nations) or
#                   "country"; None with no member modifier
# op                its row in the chamber's Table a Resolution list
# event             its proposer event, un_events.<event>
# refusal_reason    the ledger reason its proposer event's refusal books
# refusal_modifier  what that refusal leaves on the refuser, which bars it
#                   from tabling the convention; None if it leaves nothing
# regime_modifiers  its terms under the regime layer (un_regime_refresh_country)
# rule              None, or (game rule, the chamber's row-visibility sgui)
#                   for a convention that exists only under a game rule
# agenda            whether the docket's Assembly business may raise it with no
#                   situation behind it (un_docket_take_up_agenda)
Convention = namedtuple(
    "Convention",
    "key in_force member_modifier scope op event refusal_reason refusal_modifier"
    " regime_modifiers rule agenda",
)

CONVENTIONS = (
    Convention("human_rights", "un_agency_unhrc", "un_human_rights_declaration_modifier", "je",
               7, 3, 1031, "un_human_rights_refusal_modifier",
               ("un_regime_rights_violator_modifier",), None, True),
    Convention("icc", "un_agency_icc", "un_icc_member_modifier", "country",
               8, 22, 1221, "un_icc_refusal_modifier",
               (), None, True),
    Convention("npt", "un_agency_iaea", "un_nonproliferation_modifier", "je",
               9, 14, 1141, "un_nonproliferation_refusal_modifier",
               ("un_regime_npt_inspection_modifier", "un_regime_npt_guarantee_modifier"), None, False),
    Convention("climate", "un_agency_unep", "un_climate_binding_modifier", "je",
               10, 17, 1171, "un_climate_refusal_modifier",
               ("un_regime_climate_emitter_modifier", "un_regime_climate_adaptation_modifier"),
               ("global_warming_enabled", "un_chamber_climate_rule_sgui"), False),
    Convention("pandemic", "un_agency_who", "un_pandemic_cooperation_modifier", "je",
               11, 16, 1161, "un_pandemic_isolationist_modifier",
               (), None, True),
    Convention("refugee", "un_agency_unhcr", "un_refugee_program_modifier", "je",
               12, 18, 1181, "un_refugee_closed_modifier",
               ("un_regime_refugee_host_modifier", "un_regime_refugee_source_modifier"), None, True),
    Convention("heritage", "un_agency_unesco", "un_heritage_program_modifier", "je",
               13, 9, 1091, None,
               ("un_regime_heritage_site_modifier",), None, True),
    Convention("decolonization", "un_regime_decolonization", None, None,
               14, 12, 1121, "un_colonial_defender_modifier",
               ("un_regime_colonial_pressure_modifier",), None, True),
    Convention("space", "un_agency_unoosa", "un_space_partnership_modifier", "je",
               15, 19, 1191, "un_space_independent_modifier",
               ("un_regime_space_leader_modifier", "un_regime_space_laggard_modifier",
                "un_regime_space_weapon_modifier"), None, False),
    Convention("law_of_sea", "un_agency_itlos", "un_law_of_sea_modifier", "country",
               16, 21, 1211, "un_law_of_sea_refusal_modifier",
               ("un_regime_naval_curb_modifier",), None, True),
)

KEYS = tuple(c.key for c in CONVENTIONS)
BY_KEY = {c.key: c for c in CONVENTIONS}
# The conventions a member ratifies and carries.
RATIFIED = tuple(c for c in CONVENTIONS if c.member_modifier)
JE_CONVENTION = [c.member_modifier for c in CONVENTIONS if c.scope == "je"]
COUNTRY_CONVENTION = [c.member_modifier for c in CONVENTIONS if c.scope == "country"]
# AGENCY = <short> in the §0.8 catch-up (un_rep_convention_mark and friends).
AGENCIES = {c.key: c.in_force[len("un_agency_"):] for c in RATIFIED}

# The seven member-initiated topics (ops 0-6), which share many of the same
# lists. Their tag names (un_topic_<tag>) and their propose keys
# (un_propose_<key>_*) differ for three of them.
MEMBER_TOPIC_TAGS = {"condemn", "sanctions", "expulsion", "military_mandate",
                     "peacekeeping_request", "aid_request", "reform"}
MEMBER_PROPOSE_KEYS = {"condemn", "sanctions", "expulsion", "mandate", "peacekeepers", "aid", "reform"}
FIRST_CONVENTION_OP = len(MEMBER_PROPOSE_KEYS)

# Regime-layer modifiers that belong to no one convention's member terms: the
# §7.4 intelligence sharing, and the decolonization regime's reach into a
# member's colonies, which is applied to the colony and shown in the
# non-member's Obligations block rather than a member's.
OTHER_REGIME_MODIFIERS = {"un_regime_shared_intelligence_modifier", "un_regime_colony_liberty_modifier"}

# Agencies founded other than by a convention (dissolution lapses them too).
OTHER_AGENCIES = {"un_agency_icj"}

# Gaps this table found when it was written (2026-09-26), left for the owner to
# rule on rather than changed with the test. Each is asserted still to hold, so
# fixing one fails here until its entry is deleted.
KNOWN_GAPS = {
    ("human_rights", "refusal_bars_tabling"):
        "un_events.3 option C adds un_human_rights_refusal_modifier, but neither the event's "
        "trigger nor un_propose_human_rights_qualifies checks it, so a refuser can be offered "
        "the Declaration again at once. Every other refusal modifier bars both.",
    ("heritage", "qualifies_reads_only_live_modifiers"):
        "un_propose_heritage_qualifies and un_events.9's trigger bar un_heritage_token_modifier, "
        "which nothing adds (since the UN's first commit); un_events.9 option C leaves no "
        "modifier at all.",
}

# Loc every convention needs, as <template>.format(k=key).
LOC_PER_CONVENTION = (
    "je_un_chamber_topic_{k}",
    "je_un_chamber_conseq_{k}",
    "je_un_chamber_propose_topic_{k}",
    "je_un_chamber_propose_need_{k}",
    "je_un_led_topic_{k}",
    "un_vote.1.t_{k}",
    "un_vote.1.d_{k}",
    "un_vote.2.d_{k}_passed",
    "un_vote.2.d_{k}_failed",
    "un_vote_{k}_passed_tt",
)


# ---- Reading the files ------------------------------------------------------------

def _read(path):
    """The file with its comments stripped (they name conventions too)."""
    with open(path, encoding="utf-8-sig") as f:
        return re.sub(r"#[^\n]*", "", f.read())


def _flat(text):
    return re.sub(r"\s+", " ", text)


def _body_at(text, open_idx):
    """The body of the brace block whose `{` is at open_idx."""
    depth = 0
    for i in range(open_idx, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[open_idx + 1:i]
    raise AssertionError("unclosed block")


def _block(text, name):
    """The body of the top-level ``name = { ... }`` block."""
    m = re.search(r"^" + re.escape(name) + r"\s*=\s*\{", text, re.M)
    if m is None:
        raise AssertionError(f"{name} not found")
    return _body_at(text, m.end() - 1)


def _sub_block(text, key):
    """The body of the first ``key = { ... }`` inside text."""
    m = re.search(r"(?<![\w.:])" + re.escape(key) + r"\s*\??=\s*\{", text)
    if m is None:
        raise AssertionError(f"{key} not found")
    return _body_at(text, m.end() - 1)


def _top_level_names(text):
    return set(re.findall(r"^([A-Za-z_][\w.]*)\s*=\s*\{", text, re.M))


def _segments(text, pattern):
    """{group(1): the text after each match, up to the next match}, the texts of
    repeated keys joined. For if/else_if chains that switch on one thing."""
    hits = list(re.finditer(pattern, text))
    out = {}
    for i, m in enumerate(hits):
        end = hits[i + 1].start() if i + 1 < len(hits) else len(text)
        out[m.group(1)] = out.get(m.group(1), "") + text[m.end():end]
    return out


_TOPIC = r"has_tag\s*=\s*un_topic_(\w+)"


def _topic_segments(text):
    return _segments(text, _TOPIC)


def _conventions_in(topics, members=MEMBER_TOPIC_TAGS):
    """The topics a site lists, less the member-initiated ones: on a site that
    lists every topic, this is the conventions it knows."""
    return set(topics) - set(members)


def _event(n):
    return _block(_read(UN_EVENTS), f"un_events.{n}")


def _options(event_body):
    return re.split(r"\n\toption\s*=\s*\{", event_body)[1:]


def _event_trigger(event_body):
    m = re.search(r"^\ttrigger\s*=\s*(\{)", event_body, re.M)
    return _body_at(event_body, m.start(1))


def _loc():
    """Every live loc key. te_unused is organize_loc's output for keys nothing
    references, so a key found only there counts as missing."""
    keys = set()
    for name in sorted(os.listdir(LOC_DIR)):
        if not name.endswith(".yml") or name.startswith("te_unused"):
            continue
        with open(os.path.join(LOC_DIR, name), encoding="utf-8-sig") as f:
            for line in f:
                m = re.match(r"^ ([A-Za-z0-9_.\-]+):\d* ", line)
                if m:
                    keys.add(m.group(1))
    return keys


def _script_files():
    for top in ("common", "events"):
        for root, _dirs, files in os.walk(_path(top)):
            for name in files:
                if name.endswith(".txt"):
                    yield os.path.join(root, name)


def _widget_rows():
    """[(set of ops, row body)] for each Table a Resolution row of the widget."""
    widget = _read(WIDGET)
    rows = []
    for m in re.finditer(r"^\t\tun_chamber_propose_row\s*=\s*\{", widget, re.M):
        body = _body_at(widget, m.end() - 1)
        ops = {int(op) for op in re.findall(r"MakeScopeValue\(\s*'\(CFixedPoint\)(\d+)'\s*\)", body)}
        rows.append((ops, body))
    return rows


def _op_branches(text):
    return {int(op): body for op, body in _segments(
        text, r"limit\s*=\s*\{\s*exists\s*=\s*scope:op\s+scope:op\s*=\s*(\d+)\s*\}").items()}


class _GapMixin:
    def assertInvariant(self, key, check, holds, msg):
        """assertTrue(holds), unless (key, check) is a KNOWN_GAP, which must
        still be open."""
        if (key, check) in KNOWN_GAPS:
            self.assertFalse(holds, f"{key}: {check} now holds; delete its KNOWN_GAPS entry")
        else:
            self.assertTrue(holds, msg)


# ---- The table itself ---------------------------------------------------------------

class TableTests(unittest.TestCase):
    def test_keys_ops_and_events_are_unique(self):
        for field in ("key", "in_force", "op", "event", "refusal_reason"):
            values = [getattr(c, field) for c in CONVENTIONS]
            with self.subTest(field=field):
                self.assertEqual(len(set(values)), len(values))

    def test_ops_follow_the_member_topics(self):
        self.assertEqual(sorted(c.op for c in CONVENTIONS),
                         list(range(FIRST_CONVENTION_OP, FIRST_CONVENTION_OP + len(CONVENTIONS))))

    def test_scope_goes_with_the_member_modifier(self):
        for c in CONVENTIONS:
            with self.subTest(key=c.key):
                self.assertEqual(c.scope is None, c.member_modifier is None)
                self.assertIn(c.scope, (None, "je", "country"))
                if c.member_modifier:
                    self.assertTrue(c.in_force.startswith("un_agency_"))

    def test_refusal_reasons_are_the_proposer_events_codes(self):
        # Ledger codes 1NNk are response k to un_events.NN (un_authority_effects.txt).
        for c in CONVENTIONS:
            with self.subTest(key=c.key):
                self.assertEqual(c.refusal_reason // 10, 100 + c.event)

    def test_every_modifier_named_exists(self):
        defined = set()
        for name in os.listdir(STATIC_MODIFIERS):
            if name.endswith(".txt"):
                defined |= _top_level_names(_read(os.path.join(STATIC_MODIFIERS, name)))
        for c in CONVENTIONS:
            for mod in (c.member_modifier, c.refusal_modifier) + c.regime_modifiers:
                if mod:
                    with self.subTest(key=c.key, modifier=mod):
                        self.assertIn(mod, defined)


# ---- Proposing: un_propose_triggers.txt / un_propose_effects.txt ----------------------

class ProposeTests(unittest.TestCase, _GapMixin):
    @classmethod
    def setUpClass(cls):
        cls.triggers = _read(PROPOSE_TRIGGERS)
        cls.effects = _read(PROPOSE_EFFECTS)

    def test_one_trigger_set_per_convention(self):
        names = _top_level_names(self.triggers)
        for part in ("in_force", "qualifies"):
            with self.subTest(part=part):
                found = {n[len("un_propose_"):-len(part) - 1] for n in names
                         if n.startswith("un_propose_") and n.endswith("_" + part)}
                self.assertEqual(found, set(KEYS))
        for part in ("available", "possible"):
            with self.subTest(part=part):
                found = {n[len("un_propose_"):-len(part) - 1] for n in names
                         if n.startswith("un_propose_") and n.endswith("_" + part)}
                # un_propose_own_motion_possible: the gate every convention shares.
                self.assertEqual(found - MEMBER_PROPOSE_KEYS - {"own_motion"}, set(KEYS))

    def test_in_force_reads_the_passage_variable(self):
        for c in CONVENTIONS:
            with self.subTest(key=c.key):
                self.assertEqual(_block(self.triggers, f"un_propose_{c.key}_in_force").split(),
                                 ["has_global_variable", "=", c.in_force])

    def test_available_and_possible_ask_the_shared_gates(self):
        for c in CONVENTIONS:
            with self.subTest(key=c.key):
                available = _flat(_block(self.triggers, f"un_propose_{c.key}_available"))
                self.assertIn("je:je_united_nations ?= { has_modifier = un_member_modifier }", available)
                self.assertIn(f"NOT = {{ un_propose_{c.key}_in_force = yes }}", available)
                possible = _flat(_block(self.triggers, f"un_propose_{c.key}_possible"))
                for call in ("un_propose_own_motion_possible", f"un_docket_topic_open_{c.key}",
                             f"un_propose_{c.key}_qualifies"):
                    self.assertIn(call + " = yes", possible)

    def test_qualifies_bars_parties_and_refusers(self):
        for c in CONVENTIONS:
            body = _flat(_block(self.triggers, f"un_propose_{c.key}_qualifies"))
            with self.subTest(key=c.key, check="party"):
                if c.scope == "je":
                    self.assertIn(f"NOT = {{ je:je_united_nations ?= {{ has_modifier = {c.member_modifier} }} }}",
                                  body)
                elif c.scope == "country":
                    self.assertIn(f"NOT = {{ has_modifier = {c.member_modifier} }}", body)
            if c.refusal_modifier:
                with self.subTest(key=c.key, check="refuser"):
                    self.assertInvariant(
                        c.key, "refusal_bars_tabling",
                        f"NOT = {{ has_modifier = {c.refusal_modifier} }}" in body,
                        f"un_propose_{c.key}_qualifies does not bar {c.refusal_modifier}")

    def test_qualifies_reads_only_live_modifiers(self):
        # A modifier the gate bars that nothing adds is a check that never fails.
        added = set()
        for path in _script_files():
            text = _read(path)
            added |= set(re.findall(r"\bname\s*=\s*(\w+)", text))
            added |= set(re.findall(r"\bMODIFIER\s*=\s*(\w+)", text))
        for c in CONVENTIONS:
            body = _block(self.triggers, f"un_propose_{c.key}_qualifies")
            dead = set(re.findall(r"has_modifier\s*=\s*(\w+)", body)) - added
            with self.subTest(key=c.key):
                self.assertInvariant(c.key, "qualifies_reads_only_live_modifiers", not dead,
                                     f"un_propose_{c.key}_qualifies bars modifiers nothing adds: {sorted(dead)}")

    def test_table_opens_the_vote_and_effect_tables_it(self):
        names = _top_level_names(self.effects)
        found = {n[len("un_propose_"):-len("_table")] for n in names
                 if n.startswith("un_propose_") and n.endswith("_table")}
        self.assertEqual(found, set(KEYS))
        for c in CONVENTIONS:
            with self.subTest(key=c.key):
                table = _flat(_block(self.effects, f"un_propose_{c.key}_table"))
                self.assertIn(f"un_resolution_open = {{ TOPIC = {c.key} }}", table)
                effect = _flat(_block(self.effects, f"un_propose_{c.key}_effect"))
                self.assertIn("un_propose_own_motion_costs = yes", effect)
                self.assertIn(f"un_propose_{c.key}_table = yes", effect)


# ---- The docket: un_docket_triggers.txt / un_docket_effects.txt ------------------------

class DocketTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.triggers = _read(DOCKET_TRIGGERS)
        cls.effects = _read(DOCKET_EFFECTS)

    def test_one_open_and_may_propose_trigger_per_convention(self):
        names = _top_level_names(self.triggers)
        for prefix in ("un_docket_topic_open_", "un_docket_may_propose_"):
            with self.subTest(prefix=prefix):
                found = {n[len(prefix):] for n in names if n.startswith(prefix)}
                self.assertEqual(found - MEMBER_PROPOSE_KEYS, set(KEYS))

    def test_topic_open_is_not_in_force_and_not_on_cooldown(self):
        for c in CONVENTIONS:
            with self.subTest(key=c.key):
                body = _flat(_block(self.triggers, f"un_docket_topic_open_{c.key}"))
                self.assertIn(f"NOT = {{ un_propose_{c.key}_in_force = yes }}", body)
                self.assertIn(f"NOT = {{ un_resolution_topic_on_cooldown = {{ TOPIC = {c.key} }} }}", body)

    def test_may_propose_is_offerable_and_qualifies(self):
        for c in CONVENTIONS:
            with self.subTest(key=c.key):
                body = _block(self.triggers, f"un_docket_may_propose_{c.key}")
                self.assertEqual(set(re.findall(r"(\w+)\s*=\s*yes", body)),
                                 {"un_docket_can_be_offered", f"un_propose_{c.key}_qualifies"})

    def test_every_offer_names_the_conventions_own_event(self):
        offers = re.findall(r"un_docket_offer_topic\s*=\s*\{\s*TOPIC\s*=\s*(\w+)\s+EVENT\s*=\s*un_events\.(\d+)\s*\}",
                            self.effects)
        by_topic = {}
        for topic, event in offers:
            by_topic.setdefault(topic, set()).add(int(event))
        self.assertEqual(set(by_topic) - MEMBER_PROPOSE_KEYS, set(KEYS))
        for c in CONVENTIONS:
            with self.subTest(key=c.key):
                self.assertEqual(by_topic[c.key], {c.event})

    def test_assembly_business_lists_the_agenda_conventions(self):
        expected = {c.key for c in CONVENTIONS if c.agenda}
        take_up = _block(self.effects, "un_docket_take_up_agenda")
        ready = _block(self.triggers, "un_docket_agenda_ready")
        for name, body in (("un_docket_take_up_agenda", take_up), ("un_docket_agenda_ready", ready)):
            with self.subTest(site=name):
                opened = set(re.findall(r"un_docket_topic_open_(\w+)\s*=\s*yes", body))
                asked = set(re.findall(r"any_country\s*=\s*\{\s*un_docket_may_propose_(\w+)\s*=\s*yes", body))
                self.assertEqual(opened, expected)
                self.assertEqual(asked, expected)
        offered = set(re.findall(r"un_docket_offer_topic\s*=\s*\{\s*TOPIC\s*=\s*(\w+)", take_up))
        self.assertEqual(offered, expected)

    def test_a_situation_only_convention_is_raised_by_a_situation(self):
        # Off the agenda, the docket's situation scan is its only way in.
        scan = _block(self.effects, "un_docket_scan")
        for c in CONVENTIONS:
            if not c.agenda:
                with self.subTest(key=c.key):
                    self.assertIn(f"un_docket_topic_open_{c.key} = yes", _flat(scan))


# ---- The proposer events: un_events.txt ---------------------------------------------------

class ProposerEventTests(unittest.TestCase, _GapMixin):
    def test_first_option_tables_it(self):
        for c in CONVENTIONS:
            with self.subTest(key=c.key):
                first = _options(_event(c.event))[0]
                self.assertIn("default_option = yes", first)
                self.assertIn(f"un_propose_{c.key}_table = yes", first)

    def test_declining_passes_it_to_the_next_delegation(self):
        for c in CONVENTIONS:
            options = _options(_event(c.event))
            passing = [o for o in options if "name = un_docket_option_pass" in o]
            refusing = [o for o in options if re.search(rf"REASON\s*=\s*{c.refusal_reason}\b", o)]
            with self.subTest(key=c.key):
                self.assertEqual(len(passing), 1)
                self.assertEqual(len(refusing), 1)
                for opt in passing + refusing:
                    self.assertIn(f"un_docket_offer_topic_next = {{ TOPIC = {c.key} EVENT = un_events.{c.event} }}",
                                  _flat(opt))
                    self.assertIn("un_vote_release = yes", opt)

    def test_refusal_leaves_its_modifier_and_it_bars_the_offer(self):
        for c in CONVENTIONS:
            event = _event(c.event)
            refusing = next(o for o in _options(event) if re.search(rf"REASON\s*=\s*{c.refusal_reason}\b", o))
            added = set(re.findall(r"add_modifier\s*=\s*\{\s*name\s*=\s*(\w+)", refusing))
            with self.subTest(key=c.key, check="adds"):
                self.assertEqual(added, {c.refusal_modifier} if c.refusal_modifier else set())
            if c.refusal_modifier:
                with self.subTest(key=c.key, check="trigger"):
                    self.assertInvariant(
                        c.key, "refusal_bars_tabling",
                        f"NOT = {{ has_modifier = {c.refusal_modifier} }}" in _flat(_event_trigger(event)),
                        f"un_events.{c.event}'s trigger does not bar {c.refusal_modifier}")

    def test_trigger_bars_parties(self):
        for c in RATIFIED:
            with self.subTest(key=c.key):
                trigger = _flat(_event_trigger(_event(c.event)))
                if c.scope == "je":
                    self.assertIn(f"je:je_united_nations ?= {{ has_modifier = {c.member_modifier} }}", trigger)
                else:
                    self.assertIn(f"has_modifier = {c.member_modifier}", trigger)


# ---- The chamber: un_chamber_sguis.txt, the widget, the row renderers ---------------------

class ChamberTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sguis = _read(CHAMBER_SGUIS)
        propose = _block(sguis, "un_chamber_propose_sgui")
        cls.valid = _op_branches(_sub_block(propose, "is_valid"))
        cls.effect = _op_branches(_sub_block(propose, "effect"))
        cls.row = _op_branches(_block(sguis, "un_chamber_propose_row_sgui"))
        cls.display = _read(CHAMBER_DISPLAY)

    def test_each_switch_puts_the_convention_at_its_op(self):
        for name, branches, pattern in (
            ("is_valid", self.valid, r"\bun_propose_(\w+?)_available\b"),
            ("effect", self.effect, r"\bun_propose_(\w+?)_effect\b"),
            ("row", self.row, r"\bun_chamber_propose_(\w+?)_row\b"),
        ):
            with self.subTest(switch=name):
                found = {op: set(re.findall(pattern, body)) for op, body in branches.items()
                         if op >= FIRST_CONVENTION_OP}
                self.assertEqual(found, {c.op: {c.key} for c in CONVENTIONS})

    def test_is_valid_names_what_is_missing(self):
        for c in CONVENTIONS:
            with self.subTest(key=c.key):
                body = _flat(self.valid[c.op])
                self.assertIn(f"custom_tooltip = {{ text = je_un_chamber_propose_need_{c.key} "
                              f"un_propose_{c.key}_available = yes }}", body)
                self.assertIn(f"un_propose_{c.key}_possible = yes", body)

    def test_widget_has_one_row_per_convention(self):
        ops = sorted(op for row_ops, _ in _widget_rows() for op in row_ops if op >= FIRST_CONVENTION_OP)
        self.assertEqual(ops, sorted(c.op for c in CONVENTIONS))

    def test_row_renderer_is_the_conventions_own(self):
        loc = _loc()
        others = set(KEYS)
        for c in CONVENTIONS:
            with self.subTest(key=c.key):
                body = _flat(_block(self.display, f"un_chamber_propose_{c.key}_row"))
                self.assertIn(f"je_un_chamber_propose_topic_{c.key}", body)
                for part in ("in_force", "available", "possible"):
                    self.assertIn(f"un_propose_{c.key}_{part}", body)
                named = set(re.findall(r"\bun_propose_(\w+?)_(?:in_force|available|possible)\b", body))
                self.assertEqual(named & others, {c.key})
                self.assertIn(f"TOPIC = {c.key} ", body + " ")
                raised = re.findall(r"\bje_un_chamber_raised_(\w+)", body)
                self.assertEqual(len(raised), 1, raised)
                self.assertIn(f"je_un_chamber_raised_{raised[0]}", loc)
                if raised[0] == "agenda":
                    self.assertTrue(c.agenda, "says it is raised as Assembly business")

    def test_topic_and_consequence_lines_name_every_convention(self):
        for block, prefix in (("un_chamber_topic_line", "je_un_chamber_topic_"),
                              ("un_chamber_consequences_line", "je_un_chamber_conseq_")):
            segments = _topic_segments(_block(self.display, block))
            with self.subTest(site=block):
                self.assertEqual(_conventions_in(segments), set(KEYS))
            for c in CONVENTIONS:
                with self.subTest(site=block, key=c.key):
                    self.assertIn(prefix + c.key, segments[c.key])


# ---- Game rules --------------------------------------------------------------------

class RuleGateTests(unittest.TestCase):
    """A rule-gated convention is gated at every entrance, and no other one is."""

    @classmethod
    def setUpClass(cls):
        cls.propose = _read(PROPOSE_TRIGGERS)
        cls.docket = _read(DOCKET_TRIGGERS)
        cls.sguis = _read(CHAMBER_SGUIS)
        cls.rows = _widget_rows()

    def _rules(self, body):
        return set(re.findall(r"has_game_rule\s*=\s*(\w+)", body))

    def test_the_gate_is_at_every_entrance(self):
        for c in CONVENTIONS:
            expected = {c.rule[0]} if c.rule else set()
            for site, body in (
                ("topic_open", _block(self.docket, f"un_docket_topic_open_{c.key}")),
                ("available", _block(self.propose, f"un_propose_{c.key}_available")),
                ("proposer event", _event_trigger(_event(c.event))),
            ):
                with self.subTest(key=c.key, site=site):
                    self.assertEqual(self._rules(body), expected)

    def test_the_widget_row_hides_under_the_rule(self):
        for c in CONVENTIONS:
            body = next(b for ops, b in self.rows if c.op in ops)
            gates = set(re.findall(r"GetScriptedGui\('(\w+)'\)", body)) - {"un_chamber_propose_row_sgui"}
            with self.subTest(key=c.key):
                self.assertEqual(gates, {c.rule[1]} if c.rule else set())
                if c.rule:
                    shown = _sub_block(_block(self.sguis, c.rule[1]), "is_shown")
                    self.assertEqual(self._rules(shown), {c.rule[0]})


# ---- Votes: un_vote_events.txt ------------------------------------------------------------

class VoteEventTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        events = _read(VOTE_EVENTS)
        cls.vote1 = _block(events, "un_vote.1")
        cls.vote2 = _block(events, "un_vote.2")
        cls.vote2_option = cls.vote2[cls.vote2.index("\toption = {"):]

    def _described(self, pattern, text):
        found = set(re.findall(pattern, text))
        return {t for t in found if not any(t == m or t.startswith(m + "_") for m in MEMBER_TOPIC_TAGS)}

    def test_vote_1_has_a_title_and_description_per_convention(self):
        for part in ("t", "d"):
            with self.subTest(part=part):
                self.assertEqual(self._described(rf"desc\s*=\s*un_vote\.1\.{part}_(\w+)", self.vote1), set(KEYS))
        flat = _flat(self.vote1)
        for c in CONVENTIONS:
            for part in ("t", "d"):
                with self.subTest(key=c.key, part=part):
                    self.assertIn(f"desc = un_vote.1.{part}_{c.key} trigger = {{ scope:un_resolution ?= "
                                  f"{{ has_tag = un_topic_{c.key} }} }}", flat)

    def test_vote_2_reports_passed_and_failed(self):
        for outcome in ("passed", "failed"):
            with self.subTest(outcome=outcome):
                found = self._described(rf"desc\s*=\s*un_vote\.2\.d_(\w+?)_{outcome}\b", self.vote2)
                self.assertEqual(found, set(KEYS))

    def test_passage_sets_the_conventions_variable(self):
        segments = _topic_segments(self.vote2_option)
        sets = set(re.findall(r"set_global_variable\s*=\s*(un_agency_\w+|un_regime_decolonization)\b",
                              self.vote2_option))
        self.assertEqual(sets, {c.in_force for c in CONVENTIONS})
        for c in CONVENTIONS:
            with self.subTest(key=c.key):
                self.assertIn(f"set_global_variable = {c.in_force}", _flat(segments[c.key]))
                self.assertIn(f"custom_tooltip = un_vote_{c.key}_passed_tt", _flat(segments[c.key]))


# ---- Ratifying: the treaty modifier, its preview, the joiner's catch-up -----------------

class TreatyModifierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        effects = _read(VOTE_EFFECTS)
        cls.apply = _block(effects, "un_vote_apply_treaty_modifier")
        cls.joiner = _block(effects, "un_apply_ratified_conventions")
        cls.preview = _sub_block(_block(_read(VOTE_CAST), "un_vote_cast_yes"), "show_as_tooltip")

    def test_passage_gives_every_member_its_modifier(self):
        segments = _topic_segments(self.apply)
        self.assertEqual(_conventions_in(segments), set(KEYS))
        for c in RATIFIED:
            helper = "un_convention_on" if c.scope == "je" else "un_convention_country_on"
            with self.subTest(key=c.key):
                self.assertIn(f"{helper} = {{ MODIFIER = {c.member_modifier} }}", _flat(segments[c.key]))

    def test_the_yes_vote_previews_it(self):
        segments = _topic_segments(self.preview)
        self.assertEqual(_conventions_in(segments), set(KEYS))
        for c in RATIFIED:
            add = f"add_modifier = {{ name = {c.member_modifier} multiplier = un_convention_multiplier }}"
            body = _flat(segments[c.key])
            with self.subTest(key=c.key):
                if c.scope == "je":
                    self.assertIn("je:je_united_nations ?= { " + add + " }", body)
                else:
                    self.assertIn(add, body)
                    self.assertNotIn("je:je_united_nations", body)

    def test_a_joiner_gets_every_convention_in_force(self):
        segments = _segments(self.joiner, r"has_global_variable\s*=\s*(\w+)")
        self.assertEqual(set(segments), {c.in_force for c in RATIFIED})
        for c in RATIFIED:
            helper = "un_convention_on" if c.scope == "je" else "un_convention_country_on"
            with self.subTest(key=c.key):
                self.assertIn(f"{helper} = {{ MODIFIER = {c.member_modifier} }}", _flat(segments[c.in_force]))

    def test_the_ratified_kind_is_the_conventions_with_parties(self):
        body = _block(_read(RESOLUTION_TRIGGERS), "un_resolution_is_convention")
        self.assertEqual(set(re.findall(_TOPIC, body)), {c.key for c in RATIFIED})


# ---- Suspended representation (§0.8): snapshot, forget, missed, un_events.36 --------------

class RepresentationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.effects = _read(MEMBERSHIP_EFFECTS)
        cls.triggers = _read(MEMBERSHIP_TRIGGERS)

    def test_snapshot_and_forget_cover_every_agency(self):
        for name in ("un_rep_convention_snapshot", "un_rep_convention_forget"):
            with self.subTest(site=name):
                found = set(re.findall(r"AGENCY\s*=\s*(\w+)", _block(self.effects, name)))
                self.assertEqual(found, set(AGENCIES.values()))

    def test_missed_pairs_each_agency_with_its_modifier(self):
        body = _block(self.triggers, "un_rep_any_convention_missed")
        found = set(re.findall(r"AGENCY\s*=\s*(\w+)\s+MODIFIER\s*=\s*(\w+)", body))
        self.assertEqual(found, {(AGENCIES[c.key], c.member_modifier) for c in RATIFIED})

    def test_restoration_ratifies_each_missed_convention(self):
        option_a = _options(_block(_read(UN_EVENTS), "un_events.36"))[0]
        segments = _segments(option_a, r"AGENCY\s*=\s*(\w+)")
        self.assertEqual(set(segments), set(AGENCIES.values()))
        for c in RATIFIED:
            helper = "un_convention_on" if c.scope == "je" else "un_convention_country_on"
            with self.subTest(key=c.key):
                body = _flat(segments[AGENCIES[c.key]])
                self.assertIn(f"MODIFIER = {c.member_modifier} }}", body)
                self.assertIn(f"{helper} = {{ MODIFIER = {c.member_modifier} }}", body)


# ---- The regime layer: un_regime_effects.txt / un_regime_triggers.txt ---------------------

class RegimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.effects = _read(REGIME_EFFECTS)
        cls.triggers = _read(REGIME_TRIGGERS)
        cls.display = _read(CHAMBER_DISPLAY)

    def test_reapply_rescales_every_member_modifier(self):
        body = _block(self.effects, "un_regime_reapply_conventions")
        found = set(re.findall(r"(un_regime_reapply_\w+)\s*=\s*\{\s*MODIFIER\s*=\s*(\w+)", body))
        self.assertEqual(found, {("un_regime_reapply_" + c.scope, c.member_modifier) for c in RATIFIED})

    def test_any_convention_knows_every_one(self):
        body = _block(self.triggers, "un_regime_any_convention")
        self.assertEqual(set(re.findall(r"has_global_variable\s*=\s*(\w+)", body)),
                         {c.in_force for c in CONVENTIONS})

    def test_each_term_is_read_under_its_own_convention(self):
        refresh = _block(self.effects, "un_regime_refresh_country")
        where = {}
        vars_ = "|".join(re.escape(c.in_force) for c in CONVENTIONS)
        for var, seg in _segments(refresh, rf"has_global_variable\s*=\s*({vars_})\b").items():
            for mod in re.findall(r"\bname\s*=\s*(un_regime_\w+_modifier)", seg):
                where.setdefault(mod, set()).add(var)
        for c in CONVENTIONS:
            for mod in c.regime_modifiers:
                with self.subTest(key=c.key, modifier=mod):
                    self.assertEqual(where.get(mod), {c.in_force})

    def test_every_term_is_cleared_listed_and_shown(self):
        expected = {m for c in CONVENTIONS for m in c.regime_modifiers}
        cleared = set(re.findall(r"MODIFIER\s*=\s*(un_regime_\w+_modifier)",
                                 _block(self.effects, "un_regime_clear_country")))
        terms = set(re.findall(r"has_modifier\s*=\s*(un_regime_\w+_modifier)",
                               _block(self.triggers, "un_regime_has_terms")))
        lines = dict(re.findall(r"MODIFIER\s*=\s*(un_regime_\w+_modifier)\s+LINE\s*=\s*(\w+)",
                                _block(self.display, "un_chamber_regime_lines")))
        with self.subTest(site="un_regime_clear_country"):
            self.assertLessEqual(expected, cleared)
            self.assertLessEqual(cleared - expected, OTHER_REGIME_MODIFIERS)
        with self.subTest(site="un_regime_has_terms"):
            self.assertLessEqual(expected, terms)
            self.assertLessEqual(terms - expected, OTHER_REGIME_MODIFIERS)
        with self.subTest(site="un_chamber_regime_lines"):
            self.assertEqual(set(lines), terms)
        loc = _loc()
        for mod, line in lines.items():
            with self.subTest(line=line):
                self.assertIn(line, loc)


# ---- Leaving and dissolution: un_ladder_effects.txt ----------------------------------------

class LeavingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ladder = _read(LADDER)

    def test_leaving_sheds_every_member_modifier(self):
        body = _block(self.ladder, "un_membership_end_effect")
        je_off = set(re.findall(r"un_state_off\s*=\s*\{\s*MODIFIER\s*=\s*(\w+)", body))
        country_off = set(re.findall(r"un_state_country_off\s*=\s*\{\s*MODIFIER\s*=\s*(\w+)", body))
        # un_state_off takes the other journal-entry state too, so only this
        # direction here; test_un_state_mirror.HELPER_NAMES, built from
        # JE_CONVENTION, holds the names it may be called with.
        self.assertLessEqual(set(JE_CONVENTION), je_off)
        self.assertEqual(country_off, set(COUNTRY_CONVENTION))

    def test_dissolution_lapses_every_convention(self):
        found = set(re.findall(r"un_dissolve_remove_global\s*=\s*\{\s*NAME\s*=\s*(\w+)",
                               _block(self.ladder, "un_dissolve")))
        expected = {c.in_force for c in CONVENTIONS}
        self.assertLessEqual(expected, found)
        self.assertLessEqual({n for n in found if n.startswith("un_agency_")} - expected, OTHER_AGENCIES)


# ---- The ledger log and the AI's lean ----------------------------------------------------

class LedgerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.display = _read(LEDGER_DISPLAY)

    def test_every_convention_has_its_topic_case(self):
        cases = dict(re.findall(r"un_authority_log_topic_case\s*=\s*\{\s*TOPIC\s*=\s*(\w+)\s+KEY\s*=\s*(\w+)",
                                _block(self.display, "un_authority_log_resolution_lines")))
        self.assertEqual(_conventions_in(cases), set(KEYS))
        for c in CONVENTIONS:
            with self.subTest(key=c.key):
                self.assertEqual(cases[c.key], f"je_un_led_topic_{c.key}")

    def test_every_refusal_has_its_reason_case(self):
        body = _flat(_block(self.display, "un_authority_log_reason_line"))
        for c in CONVENTIONS:
            with self.subTest(key=c.key):
                self.assertIn(f"CODE = {c.refusal_reason} KEY = je_un_led_reason_{c.refusal_reason}", body)


class LeanTests(unittest.TestCase):
    def test_the_ai_weighs_its_interests_on_every_convention(self):
        body = _block(_read(DOSSIER), "un_lean_interests")
        self.assertEqual(_conventions_in(re.findall(_TOPIC, body)), set(KEYS))


# ---- Loc ---------------------------------------------------------------------------

class LocTests(unittest.TestCase):
    def test_every_convention_has_its_loc(self):
        loc = _loc()
        for c in CONVENTIONS:
            keys = [t.format(k=c.key) for t in LOC_PER_CONVENTION]
            keys.append(f"je_un_led_reason_{c.refusal_reason}")
            for mod in (c.member_modifier, c.refusal_modifier) + c.regime_modifiers:
                if mod:
                    keys += [mod, mod + "_desc"]
            for key in keys:
                with self.subTest(key=key):
                    self.assertIn(key, loc)

    def test_every_key_the_proposer_event_names_exists(self):
        loc = _loc()
        for c in CONVENTIONS:
            names = set(re.findall(rf"\bun_events\.{c.event}\.\w+", _event(c.event)))
            with self.subTest(key=c.key):
                self.assertTrue(names)
            for name in sorted(names):
                with self.subTest(key=c.key, loc=name):
                    self.assertIn(name, loc)


# ---- Counts in comments and docs ------------------------------------------------------

NUMBER_WORDS = ("zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
                "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen")


class CountTests(unittest.TestCase):
    """Comments and docs that count the conventions. Adding one left several
    "ten"s behind in #474, which no check reads."""

    COUNTS = (
        (re.compile(r"\b(\w+) country-scoped conventions\b", re.I), len(COUNTRY_CONVENTION)),
        (re.compile(r"\b(\w+) conventions that sit on the country\b", re.I), len(COUNTRY_CONVENTION)),
        (re.compile(r"\b(\w+) convention modifiers\b", re.I), len(JE_CONVENTION)),
        (re.compile(r"\b(\w+) conventions\b(?! that sit on the country)", re.I), len(CONVENTIONS)),
    )

    def _files(self):
        for top, prefix, suffix in (("common", "un_", ".txt"), ("events", "un_", ".txt"),
                                    ("gui", "un_", ".gui")):
            for root, _dirs, files in os.walk(_path(top)):
                for name in files:
                    if name.startswith(prefix) and name.endswith(suffix):
                        yield os.path.join(root, name)
        yield _path("common", "scripted_effects", "te_debug_un_effects.txt")
        yield _path("docs", "systems", "journal_entry_systems.md")
        yield _path("docs", "systems", "un_redesign_design.md")

    def test_no_count_is_stale(self):
        for path in self._files():
            with open(path, encoding="utf-8-sig") as f:
                lines = f.read().splitlines()
            for n, line in enumerate(lines, 1):
                for pattern, expected in self.COUNTS:
                    for word in pattern.findall(line):
                        if word.lower() in NUMBER_WORDS:
                            with self.subTest(file=os.path.relpath(path, REPO), line=n):
                                self.assertEqual(NUMBER_WORDS.index(word.lower()), expected, line.strip())


if __name__ == "__main__":
    unittest.main()
