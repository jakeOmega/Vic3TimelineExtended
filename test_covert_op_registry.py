"""The covert operation registry: every operation type in one table, pinned
against every site that lists operation types by hand.

Adding an operation type touches about fourteen hand-kept places — see
docs/systems/mod_systems.md § Covert Warfare System, "Adding an operation
type". OPS is the single list. Each test checks one site against it in both
directions (no type missing, no stale extra), so a half-added type fails here,
naming the site, instead of in a play test. The widget's stand-down buttons
are pinned by test_covert_stand_down.py, which reads TYPES from here.

The other covert test files import CODES / TIERS / TIER_CODES / TYPES from
this module rather than keeping their own copies.

Run: python3 -m unittest test_covert_op_registry -v
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ACTIONS = ROOT / "common/diplomatic_actions/covert_operations.txt"
EFFECTS = ROOT / "common/scripted_effects/covert_warfare_effects.txt"
TRIGGERS = ROOT / "common/scripted_triggers/covert_warfare_triggers.txt"
EVENTS = ROOT / "events/covert_warfare_events.txt"
CUSTOM_LOC = ROOT / "common/customizable_localization/covert_warfare_custom_loc.txt"
SGUIS = ROOT / "common/scripted_guis/covert_warfare_sguis.txt"
WIDGET = ROOT / "gui/journal_entry_widgets/covert_operations_widget.gui"
LOC_DIR = ROOT / "localization/english"
LENS_ICONS = ROOT / "gfx/interface/icons/lens_toolbar_icons"

# (short type, code, covert-defence axis, exposure tier, target marker)
#
# The code is what iw_type_code / iw_burned_type_code / iw_last_exposed_type
# carry. The marker is the country-scope modifier the operation leaves on its
# target; None for an operation that leaves nothing on its target. (Until #430
# covert_warfare.2 keyed on the markers; it now reads covert_op_burn's
# exposure record, which every type writes.)
OPS = (
    ("election_interference", 0, "ideological", "moderate", "covert_election_interference"),
    ("financial_subversion", 1, "economic", "moderate", "covert_financial_subversion"),
    ("infrastructure_sabotage", 2, "military", "war", "covert_infra_sabotage_morale"),
    ("comms_disruption", 3, "military", "war", "covert_comms_disruption"),
    ("industrial_espionage", 4, "economic", "mild", "covert_industrial_espionage_detected"),
    ("military_espionage", 5, "military", "mild", "covert_military_espionage_detected"),
    ("influence_campaign", 6, "ideological", "moderate", "covert_influence_campaign"),
    ("ideological_subversion", 7, "ideological", "severe", "covert_ideological_subversion_resist"),
    ("destabilization", 8, "ideological", "severe", "covert_destabilization_resist"),
    ("regime_change", 9, "ideological", "severe", "covert_regime_change"),
    ("nuclear_sabotage", 10, "military", "severe", "covert_nuclear_sabotage"),
    ("space_espionage", 11, "economic", "mild", "covert_space_espionage_detected"),
    ("cultivate_assets", 12, "ideological", "mild", None),
)

TIER_NAMES = ("mild", "moderate", "severe", "war")
NUMBER_WORDS = ("Zero", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight",
                "Nine", "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen",
                "Sixteen", "Seventeen", "Eighteen", "Nineteen", "Twenty")
TYPES = tuple(op[0] for op in OPS)
CODES = {op[0]: op[1] for op in OPS}
TIERS = {op[0]: op[3] for op in OPS}
TIER_CODES = {tier: {op[1] for op in OPS if op[3] == tier} for tier in TIER_NAMES}

# Keys every covert action needs, as covert_<type><suffix>. The engine derives
# the _action_* ones from the diplomatic action key.
ACTION_LOC_SUFFIXES = (
    "_action",
    "_action_desc",
    "_action_action_propose_name",
    "_action_action_break_name",
    "_action_action_notification_name",
    "_action_action_notification_break_name",
    "_action_action_notification_desc",
    "_action_action_notification_break_desc",
    "_action_pact_desc",
)


def _text(path):
    return path.read_text(encoding="utf-8-sig")


def _top_level_block(body, header):
    """One top-level `header = { ... }` entry, header through the first
    unindented closing brace. Safe because nested closing braces are always
    tab-indented (format_paradox_tabs.py)."""
    block = body[body.index("\n" + header) + 1:]
    return block[: block.index("\n}\n") + 3]


def _event(n):
    body = _text(EVENTS)
    start = body.index("\ncovert_warfare.%d = {" % n)
    end = body.find("\ncovert_warfare.", start + 1)
    return body[start: end if end != -1 else len(body)]


def _loc():
    """Every live loc key -> its text. te_unused is organize_loc's output for
    keys nothing references, so a key found only there counts as missing."""
    out = {}
    for path in sorted(LOC_DIR.rglob("*.yml")):
        if path.name.startswith("te_unused"):
            continue
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            m = re.match(r"^ ([A-Za-z0-9_.]+):\d* (.*)$", line)
            if m:
                out[m.group(1)] = m.group(2)
    return out


class TableTests(unittest.TestCase):
    def test_codes_are_contiguous_from_zero(self):
        self.assertEqual(sorted(CODES.values()), list(range(len(OPS))))

    def test_types_are_unique(self):
        self.assertEqual(len(set(TYPES)), len(OPS))


class SyncRowTests(unittest.TestCase):
    def test_sync_all_has_exactly_one_row_per_type(self):
        block = _top_level_block(_text(EFFECTS), "covert_ops_sync_all = {")
        rows = set(re.findall(
            r"covert_op_sync = \{ TYPE = (\w+) ACTION = (\w+) DEFENSE_MOD = (\w+) CODE = (\d+) \}",
            block,
        ))
        expected = {
            (t, "covert_%s_action" % t, "country_covert_defense_%s_add" % axis, str(code))
            for t, code, axis, _, _ in OPS
        }
        self.assertEqual(rows, expected)


class DiplomaticActionTests(unittest.TestCase):
    def test_one_action_per_type_and_no_other(self):
        found = set(re.findall(r"(?m)^(covert_\w+_action) = \{", _text(ACTIONS)))
        self.assertEqual(found, {"covert_%s_action" % t for t in TYPES})

    def test_each_action_is_wired_to_its_own_type(self):
        body = _text(ACTIONS)
        for t, code, axis, _, _ in OPS:
            with self.subTest(type=t):
                block = _top_level_block(body, "covert_%s_action = {" % t)
                self.assertIn(
                    "covert_op_start = { TYPE = %s DEFENSE_MOD = country_covert_defense_%s_add CODE = %d }"
                    % (t, axis, code),
                    block,
                )
                self.assertIn("is_hostile = yes", block)
                self.assertIn("manual_break_effect = { covert_op_end = { TYPE = %s } }" % t, block)
                self.assertIn("auto_break_effect = { covert_op_end = { TYPE = %s } }" % t, block)
                self.assertIn("covert_ops_type_below_cap = { TYPE = covert_%s_action }" % t, block)
                self.assertIn(
                    "NOT = { has_diplomatic_pact = { who = scope:target_country type = covert_%s_action } }" % t,
                    block,
                )
                self.assertIn("var:iw_funding_level >= 1", block)

    def test_every_tooltip_the_actions_name_exists(self):
        loc = _loc()
        for key in sorted(set(re.findall(r"text = (\w+)", _text(ACTIONS)))):
            with self.subTest(key=key):
                self.assertIn(key, loc)


class PactIdentityTests(unittest.TestCase):
    def test_is_covert_operation_pact_lists_every_action(self):
        block = _top_level_block(_text(TRIGGERS), "is_covert_operation_pact = {")
        found = set(re.findall(r"is_diplomatic_action_type = (\w+)", block))
        self.assertEqual(found, {"covert_%s_action" % t for t in TYPES})


class TierTableTests(unittest.TestCase):
    def test_tier_triggers_partition_the_codes(self):
        body = _text(TRIGGERS)
        seen = []
        for tier in TIER_NAMES:
            block = _top_level_block(body, "covert_code_tier_%s = {" % tier)
            codes = {int(c) for c in re.findall(r"var:\$VAR\$ = (\d+)", block)}
            self.assertEqual(codes, TIER_CODES[tier], "covert_code_tier_%s" % tier)
            seen.extend(codes)
        self.assertEqual(sorted(seen), sorted(CODES.values()))


class DetectionEventTests(unittest.TestCase):
    def test_after_burns_every_code_as_its_own_type(self):
        ev = _event(1)
        after = ev[ev.index("after = {"):]
        self.assertEqual(
            sorted(int(c) for c in re.findall(r"var:iw_burned_type_code = (\d+)", after)),
            sorted(CODES.values()),
        )
        for t, code, _, _, _ in OPS:
            with self.subTest(type=t):
                self.assertRegex(
                    after,
                    r"limit = \{ var:iw_burned_type_code = %d \}\s*"
                    r"covert_op_burn = \{ TYPE = %s ACTION = covert_%s_action "
                    r"TARGET = scope:detected_by_country CODE = %d \}" % (code, t, t, code),
                )

    def test_defender_event_hears_every_type(self):
        # covert_warfare.2 keys on the exposure record covert_op_burn writes
        # for every code (test_after_burns_every_code_as_its_own_type), not on
        # the per-type markers: those are applied only once an operation is
        # established, so a burn during preparation never reached the defender
        # (#430). No per-type line may creep back into the trigger.
        ev = _event(2)
        # The event's own trigger, not the text variants' (tab-indented once).
        trigger = ev[ev.index("\n\ttrigger = {"): ev.index("\n\timmediate = {")]
        self.assertIn("has_variable = iw_last_exposed_type", trigger)
        self.assertNotRegex(trigger, r"has_modifier = covert_")
        self.assertNotRegex(trigger, r"var:iw_last_exposed_type = \d")
        burn = _top_level_block(_text(EFFECTS), "covert_op_burn = {")
        self.assertIn("set_variable = { name = iw_last_exposed_type value = $CODE$ }", burn)
        # ...and records the phase, which the event's text reads.
        self.assertIn("name = iw_last_exposed_phase", burn)
        self.assertIn("var:iw_last_exposed_phase = 1", ev)

    def test_markers_are_what_the_operation_leaves_on_its_target(self):
        block = _top_level_block(_text(EFFECTS), "covert_ops_apply_all_phase_effects = {")
        for t, _, _, _, marker in OPS:
            with self.subTest(type=t):
                if marker is None:
                    # No effect at all: not on the target, not on the operator.
                    self.assertNotIn("iw_op_%s" % t, block)
                    self.assertNotIn("TYPE = %s " % t, block)
                else:
                    self.assertIn(
                        "covert_op_apply_target_effect = { TYPE = %s MODIFIER = %s }" % (t, marker),
                        block,
                    )


class CustomLocTests(unittest.TestCase):
    def test_both_type_name_blocks_name_every_code(self):
        body = _text(CUSTOM_LOC)
        for entry, var in (
            ("covert_last_exposed_type_name", "iw_last_exposed_type"),
            ("covert_burned_type_name", "iw_burned_type_code"),
        ):
            with self.subTest(entry=entry):
                block = _top_level_block(body, "%s = {" % entry)
                pairs = re.findall(
                    r"trigger = \{ var:%s = (\d+) \}\s*localization_key = iw_op_name_(\w+)" % var,
                    block,
                )
                self.assertEqual(
                    {(int(c), t) for c, t in pairs},
                    {(code, t) for t, code, _, _, _ in OPS},
                )
                self.assertIn("localization_key = iw_op_name_unknown", block)


class StandDownHandlerTests(unittest.TestCase):
    def test_one_handler_per_type(self):
        body = _text(SGUIS)
        self.assertEqual(
            set(re.findall(r"(?m)^covert_stand_down_(\w+)_sgui = \{", body)),
            set(TYPES),
        )
        for t in TYPES:
            with self.subTest(type=t):
                block = _top_level_block(body, "covert_stand_down_%s_sgui = {" % t)
                self.assertIn("covert_possible_stand_down = { TYPE = %s }" % t, block)
                self.assertIn(
                    "covert_effect_stand_down = { TYPE = %s ACTION = covert_%s_action }" % (t, t),
                    block,
                )


class WidgetTests(unittest.TestCase):
    def test_each_type_has_its_row_line(self):
        rows = re.findall(
            r"visible = \"\[ScriptContainer\.HasTag\('iw_op_(\w+)'\)\]\"\s*"
            r"text = \"je_iw_op_row_\1\"",
            _text(WIDGET),
        )
        self.assertEqual(sorted(rows), sorted(TYPES))


class LocTests(unittest.TestCase):
    def test_every_type_has_its_loc(self):
        loc = _loc()
        for t in TYPES:
            keys = ["iw_op_name_%s" % t, "je_iw_op_row_%s" % t]
            keys += ["covert_%s%s" % (t, s) for s in ACTION_LOC_SUFFIXES]
            for key in keys:
                with self.subTest(key=key):
                    self.assertIn(key, loc)

    def test_every_action_description_shows_its_own_tier(self):
        loc = _loc()
        for t, _, _, tier, _ in OPS:
            with self.subTest(type=t):
                self.assertIn("$iw_exposure_tier_%s_note$" % tier, loc["covert_%s_action_desc" % t])


class ConceptTests(unittest.TestCase):
    def test_concept_description_counts_and_lists_every_type(self):
        # The covert-operations concept tooltip is the player's list of what
        # exists: one bullet per type, and the right count in words.
        desc = _loc()["concept_covert_operations_desc"]
        self.assertIn("%s types are available" % NUMBER_WORDS[len(OPS)], desc)
        self.assertEqual(desc.count("\\n• #bold"), len(OPS))


class DocCountTests(unittest.TestCase):
    """Docs and comments that count or describe the operation types. Slice 6
    found five stale "nine"s and a false war-check claim after adding four."""

    STALE = re.compile(r"\bnine\b|\b9 (?:covert|diplomatic)\b", re.IGNORECASE)

    def test_no_covert_line_still_says_nine(self):
        for rel in ("docs/systems/mod_systems.md", "docs/systems/journal_entry_systems.md",
                    "common/diplomatic_actions/un_lobbying.txt", "README.md"):
            lines = (ROOT / rel).read_text(encoding="utf-8-sig").splitlines()
            for n, line in enumerate(lines, 1):
                if "covert" in line.lower():
                    with self.subTest(file=rel, line=n):
                        self.assertNotRegex(line, self.STALE)

    def test_covert_doc_claims_match_the_actions(self):
        doc = (ROOT / "docs/systems/mod_systems.md").read_text(encoding="utf-8")
        # The per-type list now has an executable form.
        self.assertNotIn("there is no single shared list", doc)
        self.assertIn("test_covert_op_registry.py", doc)
        # No covert action has a has_war guard ("Allowed during war").
        self.assertNotIn("have war and truce checks", doc)


class LensIconTests(unittest.TestCase):
    @unittest.skipUnless(LENS_ICONS.is_dir(), "gfx/ not checked out (sparse worktree)")
    def test_every_action_has_a_lens_icon(self):
        for t in TYPES:
            with self.subTest(type=t):
                self.assertTrue((LENS_ICONS / ("covert_%s_action.dds" % t)).is_file())


if __name__ == "__main__":
    unittest.main()
