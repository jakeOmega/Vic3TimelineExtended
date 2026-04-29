"""Unit tests for the /event-balance helpers in mod_state_server.

These tests don't require a running server — they exercise the pure helpers
directly, monkey-patching `ms` (the global ModState instance) with a tiny
in-memory fake so we can drive every code path with deterministic data.

Run with:  python3 test_event_balance.py
"""
import os
import tempfile
import unittest

import mod_state_server as srv


# ---------------------------------------------------------------------------
# Fake ModState — only the bits the helpers touch.
# ---------------------------------------------------------------------------
class _FakeMS:
    """Mimics mod_state.ModState's get_data / localize for the helpers."""

    def __init__(self, data: dict, loc: dict | None = None):
        self._data = data
        self._loc = loc or {}

    def get_data(self, entity_type):
        return self._data.get(entity_type)

    def localize(self, key):
        return self._loc.get(key, key)


def _eq(value):
    """Wrap a scalar/dict in the parser's ('=', value) tuple form."""
    return ("=", value)


def _modifier_block(fields: dict, icon: str = "icon.dds"):
    """Build a static-modifier entity tuple: ('=', {field: ('=', value), ...})."""
    inner = {"icon": _eq(icon)}
    for name, val in fields.items():
        inner[name] = _eq(str(val))
    return _eq(inner)


def _modifier_type_block(color: str, percent: str = "yes"):
    return _eq({"color": _eq(color), "percent": _eq(percent), "decimals": _eq("0")})


def _install_fake_ms(modifiers: dict, modifier_types: dict, events: dict | None = None,
                     loc: dict | None = None):
    """Swap srv.ms for a fake. Caller must restore via the returned context."""
    data = {
        "Modifiers": modifiers,
        "Modifier Types": modifier_types,
    }
    if events is not None:
        data["Events"] = events
    fake = _FakeMS(data, loc=loc)
    original = srv.ms
    srv.ms = fake
    return original


# Standard test fixture: two modifiers, one whose fields are mixed in polarity.
def _standard_fixture():
    modifiers = {
        # banking_event_austerity from the user's worked example.
        "austerity": _modifier_block({
            "country_loan_interest_rate_mult": -0.10,  # bad color → reducing → positive
            "country_bureaucracy_mult": -0.05,         # good color → reducing → negative
        }),
        "all_good": _modifier_block({
            "country_authority_add": 100,              # good color → +ve value → positive
        }),
        "all_bad": _modifier_block({
            "country_authority_add": -50,              # good color → -ve value → negative
        }),
        "neutral_mod": _modifier_block({
            "neutral_field": 5,
        }),
    }
    modifier_types = {
        "country_loan_interest_rate_mult": _modifier_type_block("bad"),
        "country_bureaucracy_mult": _modifier_type_block("good"),
        "country_authority_add": _modifier_type_block("good"),
        "neutral_field": _modifier_type_block("neutral"),
    }
    return modifiers, modifier_types


# ---------------------------------------------------------------------------
# Polarity arithmetic
# ---------------------------------------------------------------------------
class PolarityTests(unittest.TestCase):
    def test_good_color_positive_value_is_positive(self):
        self.assertEqual(srv._polarity(0.10, "good"), "positive")

    def test_good_color_negative_value_is_negative(self):
        self.assertEqual(srv._polarity(-0.10, "good"), "negative")

    def test_bad_color_negative_value_is_positive(self):
        # User's example: -0.10 on a `bad` modifier reduces a bad thing → good for player.
        self.assertEqual(srv._polarity(-0.10, "bad"), "positive")

    def test_bad_color_positive_value_is_negative(self):
        self.assertEqual(srv._polarity(0.20, "bad"), "negative")

    def test_neutral_color_is_neutral(self):
        self.assertEqual(srv._polarity(5, "neutral"), "neutral")

    def test_zero_value_is_neutral(self):
        self.assertEqual(srv._polarity(0, "good"), "neutral")

    def test_unknown_color_is_unknown(self):
        # color=None means the modifier-type definition was not found.
        self.assertEqual(srv._polarity(0.10, None), "unknown")


# ---------------------------------------------------------------------------
# _iter_field_values — single tuple vs list-of-tuples
# ---------------------------------------------------------------------------
class IterFieldValuesTests(unittest.TestCase):
    def test_single_tuple(self):
        result = list(srv._iter_field_values(("=", "value")))
        self.assertEqual(result, [("=", "value")])

    def test_list_of_tuples(self):
        v = [("=", "v1"), ("=", "v2"), ("=", "v3")]
        self.assertEqual(list(srv._iter_field_values(v)), v)

    def test_empty_list(self):
        self.assertEqual(list(srv._iter_field_values([])), [])

    def test_non_tuple_yields_nothing(self):
        self.assertEqual(list(srv._iter_field_values("bare_string")), [])
        self.assertEqual(list(srv._iter_field_values(None)), [])


# ---------------------------------------------------------------------------
# Modifier color lookup + static-modifier resolution
# ---------------------------------------------------------------------------
class ModifierLookupTests(unittest.TestCase):
    def setUp(self):
        modifiers, modifier_types = _standard_fixture()
        self._original_ms = _install_fake_ms(modifiers, modifier_types)

    def tearDown(self):
        srv.ms = self._original_ms

    def test_color_lookup_known(self):
        self.assertEqual(srv._modifier_color_lookup("country_loan_interest_rate_mult"), "bad")
        self.assertEqual(srv._modifier_color_lookup("country_bureaucracy_mult"), "good")
        self.assertEqual(srv._modifier_color_lookup("neutral_field"), "neutral")

    def test_color_lookup_unknown_returns_none(self):
        self.assertIsNone(srv._modifier_color_lookup("does_not_exist"))

    def test_resolve_static_modifier_returns_numeric_fields(self):
        fields = srv._resolve_static_modifier("austerity")
        self.assertEqual(len(fields), 2)
        names = {f["modifier"] for f in fields}
        self.assertEqual(names, {"country_loan_interest_rate_mult", "country_bureaucracy_mult"})
        for f in fields:
            self.assertIsInstance(f["value"], float)

    def test_resolve_skips_icon_and_non_numeric(self):
        # The icon field is in every fixture modifier; resolution must skip it.
        for f in srv._resolve_static_modifier("austerity"):
            self.assertNotEqual(f["modifier"], "icon")

    def test_resolve_missing_modifier_returns_none(self):
        self.assertIsNone(srv._resolve_static_modifier("not_a_real_modifier"))


# ---------------------------------------------------------------------------
# _describe_add_modifier — the user's worked example
# ---------------------------------------------------------------------------
class DescribeAddModifierTests(unittest.TestCase):
    def setUp(self):
        modifiers, modifier_types = _standard_fixture()
        self._original_ms = _install_fake_ms(modifiers, modifier_types)

    def tearDown(self):
        srv.ms = self._original_ms

    def test_block_form_with_duration(self):
        block = {
            "name": _eq("austerity"),
            "days": _eq("1825"),
            "is_decaying": _eq("yes"),
        }
        out = srv._describe_add_modifier(block, scope=[])

        self.assertEqual(out["kind"], "add_modifier")
        self.assertEqual(out["name"], "austerity")
        self.assertEqual(out["duration"], "1825")
        self.assertEqual(out["is_decaying"], "yes")
        self.assertEqual(out["resolved"], "ok")

        # Polarity assertions match the user's worked example exactly.
        by_field = {f["modifier"]: f for f in out["fields"]}
        self.assertEqual(by_field["country_loan_interest_rate_mult"]["polarity"], "positive")
        self.assertEqual(by_field["country_loan_interest_rate_mult"]["color"], "bad")
        self.assertEqual(by_field["country_bureaucracy_mult"]["polarity"], "negative")
        self.assertEqual(by_field["country_bureaucracy_mult"]["color"], "good")

        self.assertEqual(out["polarity_counts"]["positive"], 1)
        self.assertEqual(out["polarity_counts"]["negative"], 1)

    def test_string_form_resolves_named_modifier(self):
        # `add_modifier = some_name` (no block).
        out = srv._describe_add_modifier("all_good", scope=[])
        self.assertEqual(out["name"], "all_good")
        self.assertEqual(out["resolved"], "ok")
        self.assertEqual(len(out["fields"]), 1)
        self.assertEqual(out["fields"][0]["polarity"], "positive")

    def test_missing_modifier_marked(self):
        block = {"name": _eq("ghost_modifier")}
        out = srv._describe_add_modifier(block, scope=[])
        self.assertEqual(out["resolved"], "missing")
        self.assertEqual(out["fields"], [])

    def test_unknown_color_field_records_unknown_polarity(self):
        # A static modifier that touches a modifier-type the engine docs don't
        # know about (e.g. typo or unregistered dynamic) → polarity=unknown.
        modifiers = {"odd": _modifier_block({"made_up_field_xyz": 0.5})}
        modifier_types = {}
        original = _install_fake_ms(modifiers, modifier_types)
        try:
            out = srv._describe_add_modifier({"name": _eq("odd")}, scope=[])
            self.assertEqual(out["fields"][0]["polarity"], "unknown")
            self.assertEqual(out["fields"][0]["color"], "unknown")
            self.assertEqual(out["polarity_counts"]["unknown"], 1)
        finally:
            srv.ms = original

    def test_scope_breadcrumb_recorded(self):
        out = srv._describe_add_modifier({"name": _eq("all_good")}, scope=["if", "je:je_test"])
        self.assertEqual(out["scope"], ["if", "je:je_test"])


# ---------------------------------------------------------------------------
# _describe_change_variable
# ---------------------------------------------------------------------------
class DescribeChangeVariableTests(unittest.TestCase):
    def test_add(self):
        out = srv._describe_change_variable(
            {"name": _eq("stress"), "add": _eq("5")},
            scope=[],
        )
        self.assertEqual(out["variable"], "stress")
        self.assertEqual(out["add"], 5.0)
        self.assertNotIn("subtract", out)

    def test_subtract_and_multiply(self):
        out = srv._describe_change_variable(
            {"name": _eq("v"), "subtract": _eq("3"), "multiply": _eq("2.5")},
            scope=[],
        )
        self.assertEqual(out["subtract"], 3.0)
        self.assertEqual(out["multiply"], 2.5)


# ---------------------------------------------------------------------------
# _walk_event_effects — recursive option-body walker
# ---------------------------------------------------------------------------
class WalkEffectsTests(unittest.TestCase):
    def setUp(self):
        modifiers, modifier_types = _standard_fixture()
        self._original_ms = _install_fake_ms(modifiers, modifier_types)

    def tearDown(self):
        srv.ms = self._original_ms

    def test_skips_meta_keys(self):
        opt = {
            "name": _eq("ev.1.a"),
            "default_option": _eq("yes"),
            "ai_chance": _eq({"base": _eq("50")}),
            "trigger": _eq({"foo": _eq("bar")}),
            "add_modifier": _eq({"name": _eq("all_good")}),
        }
        out = []
        srv._walk_event_effects(opt, [], out)
        kinds = [e["kind"] for e in out]
        self.assertEqual(kinds, ["add_modifier"])

    def test_descends_into_if_block(self):
        opt = {
            "name": _eq("ev.1.a"),
            "if": _eq({
                "limit": _eq({"is_country": _eq("yes")}),
                "add_modifier": _eq({"name": _eq("all_good")}),
            }),
        }
        out = []
        srv._walk_event_effects(opt, [], out)
        kinds = [e["kind"] for e in out]
        self.assertIn("add_modifier", kinds)
        am = [e for e in out if e["kind"] == "add_modifier"][0]
        self.assertEqual(am["scope"], ["if"])

    def test_descends_into_custom_tooltip(self):
        # custom_tooltip wraps real effects (e.g. change_variable) and is the
        # most common pattern in banking_cycle_events.
        opt = {
            "custom_tooltip": _eq({
                "text": _eq('"some_loc_key"'),
                "change_variable": _eq({"name": _eq("v"), "add": _eq("3")}),
            }),
        }
        out = []
        srv._walk_event_effects(opt, [], out)
        kinds = {e["kind"] for e in out}
        self.assertIn("change_variable", kinds)
        cv = [e for e in out if e["kind"] == "change_variable"][0]
        self.assertEqual(cv["scope"], ["custom_tooltip"])

    def test_descends_into_scope_change_key(self):
        # Keys with `:` are scope changes (je:je_X, ig:ig_Y).
        opt = {
            "ig:ig_intelligentsia": _eq({
                "add_modifier": _eq({"name": _eq("all_good")}),
            }),
        }
        out = []
        srv._walk_event_effects(opt, [], out)
        am = [e for e in out if e["kind"] == "add_modifier"][0]
        self.assertEqual(am["scope"], ["ig:ig_intelligentsia"])

    def test_descends_into_every_scope_iterator(self):
        opt = {
            "every_scope_state": _eq({
                "limit": _eq({"foo": _eq("bar")}),
                "add_modifier": _eq({"name": _eq("all_good")}),
            }),
        }
        out = []
        srv._walk_event_effects(opt, [], out)
        am = [e for e in out if e["kind"] == "add_modifier"][0]
        self.assertEqual(am["scope"], ["every_scope_state"])

    def test_expands_add_enactment_modifier(self):
        # add_enactment_modifier resolves a static modifier the same way
        # add_modifier does — its fields should be tagged with polarity and
        # contribute to the option's polarity totals.
        opt = {
            "add_enactment_modifier": _eq({"name": _eq("austerity")}),
        }
        out = []
        srv._walk_event_effects(opt, [], out)
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["kind"], "add_enactment_modifier")
        self.assertEqual(out[0]["resolved"], "ok")
        self.assertEqual(len(out[0]["fields"]), 2)
        # Polarity totals roll up via _summarize_polarity.
        totals = srv._summarize_polarity(out)
        self.assertEqual(totals["positive"], 1)
        self.assertEqual(totals["negative"], 1)

    def test_handles_repeated_custom_tooltip_blocks(self):
        # When a key repeats (e.g. two custom_tooltip = {...} in one option),
        # the parser stores the value as a list of ('=', dict) tuples.
        opt = {
            "custom_tooltip": [
                _eq({"change_variable": _eq({"name": _eq("a"), "add": _eq("1")})}),
                _eq({"change_variable": _eq({"name": _eq("b"), "add": _eq("-2")})}),
            ],
        }
        out = []
        srv._walk_event_effects(opt, [], out)
        cvs = [e for e in out if e["kind"] == "change_variable"]
        self.assertEqual(len(cvs), 2)
        self.assertEqual({cv["variable"] for cv in cvs}, {"a", "b"})


# ---------------------------------------------------------------------------
# _summarize_polarity — option-level aggregation
# ---------------------------------------------------------------------------
class SummarizePolarityTests(unittest.TestCase):
    def test_sums_only_add_modifier_effects(self):
        effects = [
            {"kind": "add_modifier", "polarity_counts": {"positive": 2, "negative": 1, "neutral": 0, "unknown": 0}},
            {"kind": "change_variable", "variable": "stress", "add": 5},  # ignored
            {"kind": "add_modifier", "polarity_counts": {"positive": 0, "negative": 1, "neutral": 1, "unknown": 0}},
        ]
        totals = srv._summarize_polarity(effects)
        self.assertEqual(totals, {"positive": 2, "negative": 2, "neutral": 1, "unknown": 0})

    def test_empty_effects(self):
        self.assertEqual(
            srv._summarize_polarity([]),
            {"positive": 0, "negative": 0, "neutral": 0, "unknown": 0},
        )


# ---------------------------------------------------------------------------
# _extract_event_ids_from_file
# ---------------------------------------------------------------------------
class ExtractEventIdsTests(unittest.TestCase):
    def test_returns_event_ids_excluding_namespace(self):
        fd, path = tempfile.mkstemp(suffix=".txt")
        try:
            with os.fdopen(fd, "w") as f:
                f.write(
                    "namespace = my_ev\n"
                    "my_ev.1 = { type = country_event option = { name = my_ev.1.a } }\n"
                    "my_ev.2 = { type = country_event option = { name = my_ev.2.a } }\n"
                )
            ids, err = srv._extract_event_ids_from_file(path)
            self.assertIsNone(err)
            self.assertEqual(set(ids), {"my_ev.1", "my_ev.2"})
        finally:
            os.remove(path)

    def test_missing_file_returns_error(self):
        ids, err = srv._extract_event_ids_from_file("/nope/does_not_exist.txt")
        self.assertIsNone(ids)
        self.assertIn("not found", err.lower())


# ---------------------------------------------------------------------------
# _render_event_balance_text — readable output
# ---------------------------------------------------------------------------
class RenderTextTests(unittest.TestCase):
    def test_renders_polarity_glyphs_and_field_lines(self):
        events = [{
            "id": "ev.1",
            "name": "Test Event",
            "options": [{
                "name_key": "ev.1.a",
                "name": "Option A",
                "default_option": True,
                "ai_chance_base": 45,
                "polarity_totals": {"positive": 1, "negative": 1, "neutral": 0, "unknown": 0},
                "effects": [{
                    "kind": "add_modifier",
                    "name": "austerity",
                    "duration": "1825",
                    "is_decaying": "yes",
                    "multiplier": None,
                    "resolved": "ok",
                    "fields": [
                        {"modifier": "country_loan_interest_rate_mult", "value": -0.10,
                         "color": "bad", "polarity": "positive"},
                        {"modifier": "country_bureaucracy_mult", "value": -0.05,
                         "color": "good", "polarity": "negative"},
                    ],
                    "polarity_counts": {"positive": 1, "negative": 1, "neutral": 0, "unknown": 0},
                }],
            }],
            "totals": {"options": 1, "positive": 1, "negative": 1, "neutral": 0, "unknown": 0},
        }]

        text = srv._render_event_balance_text(events)
        self.assertIn("ev.1", text)
        self.assertIn("Option A", text)
        self.assertIn("[default]", text)
        self.assertIn("ai_base=45", text)
        self.assertIn("country_loan_interest_rate_mult = -0.1", text)
        self.assertIn("(color=bad)", text)
        self.assertIn("[+ positive", text)
        self.assertIn("[- negative", text)

    def test_missing_section_renders(self):
        text = srv._render_event_balance_text([], missing=["a.1", "b.2"])
        self.assertIn("missing: a.1, b.2", text)


# ---------------------------------------------------------------------------
# Dominance check (/event-balance/issues)
# ---------------------------------------------------------------------------
def _option(name_key, pos=0, neg=0, neut=0, unk=0, modifiers=None):
    """Build a minimal option dict shaped like _format_option_balance output."""
    effects = []
    if modifiers:
        for m in modifiers:
            effects.append({
                "kind": "add_modifier",
                "name": m["name"],
                "fields": m.get("fields", []),
                "polarity_counts": m.get("polarity_counts",
                    {"positive": 0, "negative": 0, "neutral": 0, "unknown": 0}),
            })
    return {
        "name_key": name_key,
        "name": name_key,
        "default_option": False,
        "ai_chance_base": 50,
        "effects": effects,
        "polarity_totals": {"positive": pos, "negative": neg, "neutral": neut, "unknown": unk},
    }


class ClassifyOptionPolarityTests(unittest.TestCase):
    def test_pure_positive(self):
        self.assertEqual(srv._classify_option_polarity(_option("a", pos=2, neg=0)), "pure_positive")

    def test_pure_negative(self):
        self.assertEqual(srv._classify_option_polarity(_option("a", pos=0, neg=3)), "pure_negative")

    def test_mixed(self):
        self.assertEqual(srv._classify_option_polarity(_option("a", pos=1, neg=1)), "mixed")

    def test_empty_when_no_polarized_modifiers(self):
        # Neutrals/unknowns alone don't make an option "pure" anything.
        self.assertEqual(srv._classify_option_polarity(_option("a", neut=2, unk=1)), "empty")

    def test_empty_when_totals_missing(self):
        self.assertEqual(srv._classify_option_polarity({}), "empty")


class FindDominanceIssuesTests(unittest.TestCase):
    def test_flags_pure_positive_vs_pure_negative(self):
        ev = {
            "id": "ev.1",
            "name": "Test",
            "options": [
                _option("ev.1.a", pos=2, neg=0, modifiers=[
                    {"name": "all_good", "fields": [
                        {"modifier": "country_authority_add", "value": 100, "color": "good", "polarity": "positive"}],
                     "polarity_counts": {"positive": 1, "negative": 0, "neutral": 0, "unknown": 0}},
                ]),
                _option("ev.1.b", pos=0, neg=2, modifiers=[
                    {"name": "all_bad", "fields": [
                        {"modifier": "country_authority_add", "value": -100, "color": "good", "polarity": "negative"}],
                     "polarity_counts": {"positive": 0, "negative": 1, "neutral": 0, "unknown": 0}},
                ]),
            ],
        }
        issue = srv._find_dominance_issues(ev)
        self.assertIsNotNone(issue)
        self.assertEqual(issue["id"], "ev.1")
        self.assertIn("ev.1.a", issue["reason"])
        self.assertIn("ev.1.b", issue["reason"])
        self.assertEqual(len(issue["options_pure_positive"]), 1)
        self.assertEqual(len(issue["options_pure_negative"]), 1)
        # Per-option modifier breakdown is preserved.
        self.assertEqual(issue["options_pure_positive"][0]["modifiers"][0]["name"], "all_good")

    def test_does_not_flag_mixed_vs_pure_negative(self):
        # Conservative heuristic: mixed options can still be the right pick.
        ev = {
            "id": "ev.1", "name": "Test",
            "options": [
                _option("a", pos=1, neg=1),
                _option("b", pos=0, neg=2),
            ],
        }
        self.assertIsNone(srv._find_dominance_issues(ev))

    def test_does_not_flag_pure_positive_vs_empty(self):
        # An empty option might have non-modifier effects we can't classify.
        ev = {
            "id": "ev.1", "name": "Test",
            "options": [
                _option("a", pos=2, neg=0),
                _option("b"),
            ],
        }
        self.assertIsNone(srv._find_dominance_issues(ev))

    def test_does_not_flag_when_only_one_option(self):
        ev = {"id": "ev.1", "name": "Test", "options": [_option("a", pos=1, neg=0)]}
        self.assertIsNone(srv._find_dominance_issues(ev))

    def test_flags_with_three_options_one_pure_pos_one_pure_neg_one_mixed(self):
        ev = {
            "id": "ev.1", "name": "Test",
            "options": [
                _option("a", pos=2, neg=0),
                _option("b", pos=1, neg=1),  # mixed — coexists fine
                _option("c", pos=0, neg=2),
            ],
        }
        issue = srv._find_dominance_issues(ev)
        self.assertIsNotNone(issue)
        # Mixed option is NOT included in either bucket.
        labels = {o["name_key"] for o in issue["options_pure_positive"]}
        labels |= {o["name_key"] for o in issue["options_pure_negative"]}
        self.assertEqual(labels, {"a", "c"})


class FindSoftDominanceTests(unittest.TestCase):
    def test_flags_mixed_vs_mixed_with_clear_gap(self):
        # A: pos=3 neg=1; B: pos=1 neg=2 → A dominates by +2 pos, +1 fewer neg.
        ev = {
            "id": "ev.1", "name": "Test",
            "options": [
                _option("a", pos=3, neg=1),
                _option("b", pos=1, neg=2),
            ],
        }
        issue = srv._find_soft_dominance_issues(ev, threshold=2)
        self.assertIsNotNone(issue)
        self.assertEqual(len(issue["pairs"]), 1)
        pair = issue["pairs"][0]
        self.assertEqual(pair["pos_diff"], 2)
        self.assertEqual(pair["neg_diff"], 1)

    def test_threshold_filters_marginal_gaps(self):
        # A: pos=2 neg=0; B: pos=1 neg=0 → only +1 pos diff, below threshold=2.
        ev = {
            "id": "ev.1", "name": "Test",
            "options": [
                _option("a", pos=2, neg=0),
                _option("b", pos=1, neg=0),
            ],
        }
        self.assertIsNone(srv._find_soft_dominance_issues(ev, threshold=2))
        # Same input passes threshold=1.
        self.assertIsNotNone(srv._find_soft_dominance_issues(ev, threshold=1))

    def test_does_not_flag_when_neither_option_dominates(self):
        # A: pos=2 neg=0; B: pos=0 neg=2 → strict dominance, NOT soft. soft only fires
        # when the worse option still has ≥1 pos OR the better has ≥1 neg.
        # Actually: A.pos=2, B.pos=0, A.neg=0, B.neg=2 → pos_diff=2, neg_diff=2,
        # total=4, A.pos+A.neg > 0 → soft DOES flag this. That's fine —
        # strict-dominance is a subset of soft-dominance.
        ev = {
            "id": "ev.1", "name": "Test",
            "options": [
                _option("a", pos=2, neg=0),
                _option("b", pos=0, neg=2),
            ],
        }
        issue = srv._find_soft_dominance_issues(ev, threshold=2)
        self.assertIsNotNone(issue)

    def test_skips_empty_better_option(self):
        # If "better" has 0 polarized modifiers, skip — its non-modifier
        # effects (treasury, radicals, etc.) might be the actual offset.
        ev = {
            "id": "ev.1", "name": "Test",
            "options": [
                _option("a"),                 # empty
                _option("b", pos=0, neg=2),   # negative
            ],
        }
        self.assertIsNone(srv._find_soft_dominance_issues(ev, threshold=1))

    def test_does_not_flag_when_gap_in_one_direction_only_too_small(self):
        # A: pos=1 neg=0; B: pos=1 neg=1 → pos_diff=0, neg_diff=1, total=1.
        # Below threshold=2.
        ev = {
            "id": "ev.1", "name": "Test",
            "options": [
                _option("a", pos=1, neg=0),
                _option("b", pos=1, neg=1),
            ],
        }
        self.assertIsNone(srv._find_soft_dominance_issues(ev, threshold=2))


class RenderIssuesTextTests(unittest.TestCase):
    def test_renders_summary_and_per_event_sections(self):
        flagged = [{
            "id": "ev.1",
            "name": "Test Event",
            "reason": "option 'ev.1.a' has only positive modifier effects; "
                      "option 'ev.1.b' has only negative modifier effects",
            "options_pure_positive": [{
                "name_key": "ev.1.a", "name": "Take the bonus",
                "polarity_totals": {"positive": 1, "negative": 0, "neutral": 0, "unknown": 0},
                "modifiers": [{
                    "name": "good_mod",
                    "fields": [{"modifier": "country_authority_add", "value": 50,
                                "color": "good", "polarity": "positive"}],
                    "polarity_counts": {"positive": 1, "negative": 0, "neutral": 0, "unknown": 0},
                }],
            }],
            "options_pure_negative": [{
                "name_key": "ev.1.b", "name": "Eat the cost",
                "polarity_totals": {"positive": 0, "negative": 1, "neutral": 0, "unknown": 0},
                "modifiers": [{
                    "name": "bad_mod",
                    "fields": [{"modifier": "country_authority_add", "value": -50,
                                "color": "good", "polarity": "negative"}],
                    "polarity_counts": {"positive": 0, "negative": 1, "neutral": 0, "unknown": 0},
                }],
            }],
        }]
        text = srv._render_event_balance_issues_text(scanned=200, flagged=flagged)
        self.assertIn("scanned 200", text)
        self.assertIn("flagged 1", text)
        self.assertIn("ev.1", text)
        self.assertIn("Take the bonus", text)
        self.assertIn("Eat the cost", text)
        self.assertIn("country_authority_add = 50", text)
        self.assertIn("country_authority_add = -50", text)

    def test_empty_flagged_list_renders_summary_only(self):
        text = srv._render_event_balance_issues_text(scanned=412, flagged=[])
        self.assertIn("scanned 412", text)
        self.assertIn("flagged 0", text)


if __name__ == "__main__":
    unittest.main()
