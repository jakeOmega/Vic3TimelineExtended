"""Unit tests for loc_coverage_audit.

Run: python3 test_loc_coverage_audit.py
"""
import os
import tempfile
import unittest

from loc_coverage_audit import (
    audit,
    render_report,
    _event_loc_keys,
    _parse_reviewed,
    _build_entity_locations,
)


class FakeParser:
    def __init__(self, data: dict):
        self.data = data


class FakeMS:
    """Minimal stand-in for ModState. The audit only touches `base_parsers`,
    `mod_parsers`, and `has_localization`."""

    def __init__(
        self,
        mod_data: dict[str, dict],
        base_data: dict[str, dict] | None = None,
        loc_keys: set[str] | None = None,
    ):
        self.base_parsers = {k: FakeParser(v) for k, v in (base_data or {}).items()}
        self.mod_parsers = {k: FakeParser(v) for k, v in mod_data.items()}
        self._loc = loc_keys or set()

    def has_localization(self, key: str) -> bool:
        return key in self._loc


def _write(tmp: str, rel: str, content: str) -> str:
    path = os.path.join(tmp, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
    return path


class ParseReviewedTests(unittest.TestCase):
    def test_match(self):
        result = _parse_reviewed("# REVIEWED 2026-05-08: backwards-compat alias")
        self.assertEqual(result, {"date": "2026-05-08", "rationale": "backwards-compat alias"})

    def test_no_match(self):
        self.assertIsNone(_parse_reviewed("# just a comment"))
        self.assertIsNone(_parse_reviewed(None))
        self.assertIsNone(_parse_reviewed(""))


class EventLocKeysTests(unittest.TestCase):
    def test_full(self):
        ev = {
            "type": "country_event",
            "title": "evt.1.t",
            "desc": "evt.1.d",
            "flavor": "evt.1.f",
            "option": [{"name": "evt.1.a"}, {"name": "evt.1.b"}],
        }
        keys = _event_loc_keys("evt.1", ev)
        ks = {k for k, _, _ in keys}
        self.assertIn("evt.1.t", ks)
        self.assertIn("evt.1.d", ks)
        self.assertIn("evt.1.f", ks)
        self.assertIn("evt.1.a", ks)
        self.assertIn("evt.1.b", ks)

    def test_flavor_optional(self):
        ev = {"type": "country_event", "title": "x.t", "desc": "x.d"}
        keys = dict((k, req) for k, req, _ in _event_loc_keys("x", ev))
        self.assertTrue(keys["x.t"])
        self.assertTrue(keys["x.d"])

    def test_single_option_dict(self):
        # The parser sometimes hands us a dict instead of a list when there's
        # one option block. Audit must handle both.
        ev = {"type": "country_event", "title": "x.t", "desc": "x.d",
              "option": {"name": "x.a"}}
        ks = {k for k, _, _ in _event_loc_keys("x", ev)}
        self.assertIn("x.a", ks)

    def test_skips_non_event_entries(self):
        # Parser surfaces top-level `namespace = X` directives in the same
        # data dict. They lack a `type` field — must be skipped, not flagged.
        keys = _event_loc_keys("namespace", "nuclear_weapon_events")
        self.assertEqual(keys, [])

    def test_unwraps_parser_tuples(self):
        # Real ModState data wraps every assignment as ('=', value).
        ev = ("=", {
            "type": ("=", "country_event"),
            "title": ("=", "evt.t"),
            "desc": ("=", "evt.d"),
            "option": ("=", [("=", {"name": ("=", '"evt.a"')})]),
        })
        ks = {k for k, _, _ in _event_loc_keys("evt", ev)}
        self.assertEqual(ks, {"evt.t", "evt.d", "evt.a"})


class ScriptedButtonTests(unittest.TestCase):
    def test_explicit_name_field_used(self):
        from loc_coverage_audit import _explicit_name_field
        body = {"name": '"CR_GRASSROOTS_ORGANIZING"', "desc": '"CR_GRASSROOTS_ORGANIZING_DESC"'}
        keys = _explicit_name_field("cr_grassroots_organizing", body)
        ks = dict((k, req) for k, req, _ in keys)
        # Must check the loc key from the `name` field, not the entity name
        self.assertIn("CR_GRASSROOTS_ORGANIZING", ks)
        self.assertNotIn("cr_grassroots_organizing", ks)
        self.assertTrue(ks["CR_GRASSROOTS_ORGANIZING"])
        self.assertFalse(ks["CR_GRASSROOTS_ORGANIZING_DESC"])  # desc optional

    def test_handles_missing_name_field(self):
        from loc_coverage_audit import _explicit_name_field
        # Button with no `name` field — should produce no requirements
        # (better than flagging a phantom key).
        self.assertEqual(_explicit_name_field("button_x", {}), [])


class BuildEntityLocationsTests(unittest.TestCase):
    def test_finds_opening_line(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(
                tmp, "common/static_modifiers/foo.txt",
                "prestige_loss_tiny = {\n"
                "    country_prestige_mult = -0.005\n"
                "}\n"
            )
            locs = _build_entity_locations(
                tmp, "common/static_modifiers", {"prestige_loss_tiny"}
            )
            self.assertIn("prestige_loss_tiny", locs)
            rel, line, comment = locs["prestige_loss_tiny"]
            self.assertEqual(line, 1)
            self.assertIsNone(comment)

    def test_captures_trailing_comment(self):
        with tempfile.TemporaryDirectory() as tmp:
            _write(
                tmp, "common/static_modifiers/foo.txt",
                "prestige_loss_tiny = { # REVIEWED 2026-05-08: alias\n"
                "}\n"
            )
            locs = _build_entity_locations(
                tmp, "common/static_modifiers", {"prestige_loss_tiny"}
            )
            _, _, comment = locs["prestige_loss_tiny"]
            self.assertIsNotNone(comment)
            self.assertIn("REVIEWED", comment)


class AuditTests(unittest.TestCase):
    def _scaffold(self, *, mod_modifiers: dict, base_modifiers: dict | None = None,
                  loc_keys: set | None = None, source_lines: dict | None = None):
        """Build (ms, tmp_path) with synthetic mod sources written to tmp."""
        tmp = tempfile.mkdtemp()
        # Write source files for each entity-name to enable file:line resolution
        if source_lines is None:
            source_lines = {
                name: f"{name} = {{\n}}\n" for name in mod_modifiers
            }
        if mod_modifiers:
            blob = "\n".join(source_lines[name] for name in mod_modifiers if name in source_lines)
            _write(tmp, "common/static_modifiers/extra_modifiers.txt", blob)
        ms = FakeMS(
            mod_data={"Modifiers": mod_modifiers},
            base_data={"Modifiers": base_modifiers or {}},
            loc_keys=loc_keys or set(),
        )
        return ms, tmp

    def test_unlocalized_modifier_flagged(self):
        ms, tmp = self._scaffold(
            mod_modifiers={"prestige_loss_tiny": {}},
            loc_keys=set(),
        )
        result = audit(ms, mod_path=tmp)
        self.assertEqual(len(result.flags), 1)
        f = result.flags[0]
        self.assertEqual(f.entity, "prestige_loss_tiny")
        self.assertEqual(f.category, "Modifiers")
        self.assertEqual(f.missing_keys, ["prestige_loss_tiny"])
        self.assertIsNone(f.exemption)

    def test_localized_modifier_not_flagged(self):
        ms, tmp = self._scaffold(
            mod_modifiers={"prestige_loss_tiny": {}},
            loc_keys={"prestige_loss_tiny"},
        )
        result = audit(ms, mod_path=tmp)
        self.assertEqual(result.flags, [])

    def test_reviewed_modifier_exempted(self):
        ms, tmp = self._scaffold(
            mod_modifiers={"prestige_loss_tiny": {}},
            loc_keys=set(),
            source_lines={
                "prestige_loss_tiny": "prestige_loss_tiny = { # REVIEWED 2026-05-08: alias\n}\n",
            },
        )
        result = audit(ms, mod_path=tmp)
        self.assertEqual(len(result.flags), 1)
        f = result.flags[0]
        self.assertIsNotNone(f.exemption)
        self.assertEqual(f.exemption["date"], "2026-05-08")
        self.assertEqual(f.exemption["rationale"], "alias")

    def test_vanilla_override_not_flagged(self):
        # Modifier present in BOTH base and mod parsers — it's a vanilla
        # override, not net-new. Vanilla loc applies; audit must skip.
        ms, tmp = self._scaffold(
            mod_modifiers={"country_prestige_mult": {}},
            base_modifiers={"country_prestige_mult": {}},
            loc_keys=set(),  # even with no mod loc, vanilla loc covers it
        )
        result = audit(ms, mod_path=tmp)
        self.assertEqual(result.flags, [])

    def test_event_missing_title_flagged(self):
        tmp = tempfile.mkdtemp()
        _write(tmp, "events/test_events.txt",
               "test_events.1 = {\n"
               "  type = country_event\n"
               "  title = test_events.1.t\n"
               "  desc = test_events.1.d\n"
               "}\n")
        ms = FakeMS(
            mod_data={"Events": {"test_events.1": {
                "type": "country_event",
                "title": "test_events.1.t",
                "desc": "test_events.1.d",
            }}},
            base_data={"Events": {}},
            loc_keys={"test_events.1.d"},  # title key missing
        )
        result = audit(ms, mod_path=tmp)
        self.assertEqual(len(result.flags), 1)
        f = result.flags[0]
        self.assertEqual(f.category, "Events")
        self.assertIn("test_events.1.t", f.missing_keys)
        self.assertNotIn("test_events.1.d", f.missing_keys)

    def test_event_fully_localized_not_flagged(self):
        tmp = tempfile.mkdtemp()
        _write(tmp, "events/test_events.txt", "test_events.1 = {\n}\n")
        ms = FakeMS(
            mod_data={"Events": {"test_events.1": {
                "type": "country_event",
                "title": "test_events.1.t",
                "desc": "test_events.1.d",
                "option": [{"name": "test_events.1.a"}],
            }}},
            base_data={"Events": {}},
            loc_keys={"test_events.1.t", "test_events.1.d", "test_events.1.a"},
        )
        result = audit(ms, mod_path=tmp)
        self.assertEqual(result.flags, [])

    def test_event_namespace_directive_skipped(self):
        # Parser surfaces `namespace = X` as a top-level entry alongside
        # actual events. Must be filtered out, not flagged.
        tmp = tempfile.mkdtemp()
        _write(tmp, "events/test_events.txt", "namespace = test_events\n")
        ms = FakeMS(
            mod_data={"Events": {"namespace": "test_events"}},
            base_data={"Events": {}},
            loc_keys=set(),
        )
        result = audit(ms, mod_path=tmp)
        self.assertEqual(result.flags, [])

    def test_journal_entry_missing_desc_flagged(self):
        tmp = tempfile.mkdtemp()
        _write(tmp, "common/journal_entries/x.txt", "je_test = {\n}\n")
        ms = FakeMS(
            mod_data={"Journal Entries": {"je_test": {}}},
            base_data={"Journal Entries": {}},
            loc_keys={"je_test"},  # title present, desc missing
        )
        result = audit(ms, mod_path=tmp)
        self.assertEqual(len(result.flags), 1)
        self.assertEqual(result.flags[0].missing_keys, ["je_test_desc"])

    def test_optional_desc_not_required(self):
        # Character traits: name required, desc optional. Missing desc alone
        # must NOT flag.
        tmp = tempfile.mkdtemp()
        _write(tmp, "common/character_traits/x.txt", "trait_brave = {\n}\n")
        ms = FakeMS(
            mod_data={"Character Traits": {"trait_brave": {}}},
            base_data={"Character Traits": {}},
            loc_keys={"trait_brave"},  # only name; desc missing but optional
        )
        result = audit(ms, mod_path=tmp)
        self.assertEqual(result.flags, [])

    def test_government_type_missing_name_flagged(self):
        # Regression for gov_algorithmic_directorate: a mod-new government type
        # with no loc key leaks the raw name into the government panel.
        tmp = tempfile.mkdtemp()
        _write(tmp, "common/government_types/x.txt", "gov_test = {\n}\n")
        ms = FakeMS(
            mod_data={"Government Types": {"gov_test": {}}},
            base_data={"Government Types": {}},
            loc_keys=set(),  # name missing
        )
        result = audit(ms, mod_path=tmp)
        self.assertEqual(len(result.flags), 1)
        self.assertEqual(result.flags[0].missing_keys, ["gov_test"])

    def test_government_type_name_present_not_flagged(self):
        # Name present, desc optional -> no flag (matches the existing mod
        # government types, which carry a name but no _desc).
        tmp = tempfile.mkdtemp()
        _write(tmp, "common/government_types/x.txt", "gov_test = {\n}\n")
        ms = FakeMS(
            mod_data={"Government Types": {"gov_test": {}}},
            base_data={"Government Types": {}},
            loc_keys={"gov_test"},
        )
        result = audit(ms, mod_path=tmp)
        self.assertEqual(result.flags, [])

    def test_pm_group_missing_name_flagged(self):
        # Regression for pmg_automation_building_explosives_factory: a mod-new
        # production method group with no loc key leaks the raw name into the
        # building's PM-selection UI. PMGs are name-only (no _desc convention).
        tmp = tempfile.mkdtemp()
        _write(tmp, "common/production_method_groups/x.txt", "pmg_test = {\n}\n")
        ms = FakeMS(
            mod_data={"PM Groups": {"pmg_test": {}}},
            base_data={"PM Groups": {}},
            loc_keys=set(),  # name missing
        )
        result = audit(ms, mod_path=tmp)
        self.assertEqual(len(result.flags), 1)
        self.assertEqual(result.flags[0].category, "PM Groups")
        self.assertEqual(result.flags[0].missing_keys, ["pmg_test"])

    def test_pm_group_name_present_not_flagged(self):
        # Name present -> no flag. A vanilla-override PMG (present in base too)
        # is also covered by the generic vanilla-override path.
        tmp = tempfile.mkdtemp()
        _write(tmp, "common/production_method_groups/x.txt", "pmg_test = {\n}\n")
        ms = FakeMS(
            mod_data={"PM Groups": {"pmg_test": {}}},
            base_data={"PM Groups": {}},
            loc_keys={"pmg_test"},
        )
        result = audit(ms, mod_path=tmp)
        self.assertEqual(result.flags, [])


class MessageTests(unittest.TestCase):
    """`common/messages` entries are addressed by `post_notification = X` but
    localized through `notification_X_name` / `_desc` / `_tooltip`. A bare
    `X:0 "..."` loc line is never looked up, so the feed renders three raw
    keys with no engine warning — the covert_severe_exposure_notice defect."""

    def test_derivation_shape(self):
        from loc_coverage_audit import _message_keys
        keys = dict((k, req) for k, req, _ in _message_keys("my_notice", {}))
        self.assertTrue(keys["notification_my_notice_name"])
        self.assertTrue(keys["notification_my_notice_desc"])
        # Vanilla omits _tooltip on ~5% of its own messages, so it is checked
        # but not required.
        self.assertFalse(keys["notification_my_notice_tooltip"])
        # The bare message name is NOT a key the engine reads.
        self.assertNotIn("my_notice", keys)

    def _ms(self, loc_keys):
        return FakeMS(
            mod_data={"Messages": {"my_notice": {"type": "country"}}},
            base_data={"Messages": {}},
            loc_keys=loc_keys,
        )

    def _tmp(self):
        tmp = tempfile.mkdtemp()
        _write(tmp, "common/messages/extra_messages.txt",
               "my_notice = {\n\ttype = country\n}\n")
        return tmp

    def test_bare_key_does_not_satisfy_the_requirement(self):
        result = audit(self._ms({"my_notice"}), mod_path=self._tmp())
        self.assertEqual(len(result.flags), 1)
        f = result.flags[0]
        self.assertEqual(f.category, "Messages")
        self.assertEqual(
            f.missing_keys,
            ["notification_my_notice_name", "notification_my_notice_desc"],
        )

    def test_notification_keys_satisfy_the_requirement(self):
        result = audit(
            self._ms({
                "notification_my_notice_name",
                "notification_my_notice_desc",
                "notification_my_notice_tooltip",
            }),
            mod_path=self._tmp(),
        )
        self.assertEqual(result.flags, [])

    def test_missing_tooltip_alone_is_not_flagged(self):
        result = audit(
            self._ms({"notification_my_notice_name", "notification_my_notice_desc"}),
            mod_path=self._tmp(),
        )
        self.assertEqual(result.flags, [])

    def test_vanilla_message_override_not_flagged(self):
        ms = FakeMS(
            mod_data={"Messages": {"vanilla_notice": {"type": "country"}}},
            base_data={"Messages": {"vanilla_notice": {"type": "country"}}},
            loc_keys=set(),
        )
        tmp = tempfile.mkdtemp()
        _write(tmp, "common/messages/extra_messages.txt", "vanilla_notice = {\n}\n")
        self.assertEqual(audit(ms, mod_path=tmp).flags, [])

    def test_registered_in_both_rosters(self):
        from loc_coverage_audit import _REQUIREMENTS, _DIR_MAP
        self.assertIn("Messages", _REQUIREMENTS)
        self.assertEqual(_DIR_MAP["Messages"], "common/messages")


class TreatyArticleTests(unittest.TestCase):
    """Treaty articles resolve four autokeys off the article name. The
    nuclear_disarmament / nuclear_program_pause defect: both shipped with only
    `_effects_desc`, so the treaty picker listed them by raw key."""

    KEYS = {
        "my_article",
        "my_article_desc",
        "my_article_effects_desc",
        "my_article_article_short_desc",
    }

    def _ms(self, loc_keys, *, base=None):
        return FakeMS(
            mod_data={"Treaty Articles": {"my_article": {"kind": "directed"}}},
            base_data={"Treaty Articles": base or {}},
            loc_keys=loc_keys,
        )

    def _tmp(self):
        tmp = tempfile.mkdtemp()
        _write(tmp, "common/treaty_articles/extra_treaty_articles.txt",
               "my_article = {\n\tkind = directed\n}\n")
        return tmp

    def test_fully_localized_not_flagged(self):
        self.assertEqual(audit(self._ms(self.KEYS), mod_path=self._tmp()).flags, [])

    def test_only_effects_desc_flags_the_other_three(self):
        result = audit(self._ms({"my_article_effects_desc"}), mod_path=self._tmp())
        self.assertEqual(len(result.flags), 1)
        f = result.flags[0]
        self.assertEqual(f.category, "Treaty Articles")
        self.assertEqual(
            f.missing_keys,
            ["my_article", "my_article_desc", "my_article_article_short_desc"],
        )
        self.assertEqual(f.file, "common/treaty_articles/extra_treaty_articles.txt")
        self.assertEqual(f.line, 1)

    def test_missing_short_desc_alone_is_flagged(self):
        result = audit(
            self._ms(self.KEYS - {"my_article_article_short_desc"}),
            mod_path=self._tmp(),
        )
        self.assertEqual(
            [f.missing_keys for f in result.flags],
            [["my_article_article_short_desc"]],
        )

    def test_vanilla_article_override_not_flagged(self):
        ms = self._ms(set(), base={"my_article": {"kind": "directed"}})
        self.assertEqual(audit(ms, mod_path=self._tmp()).flags, [])

    def test_registered_in_both_rosters(self):
        from loc_coverage_audit import _REQUIREMENTS, _DIR_MAP
        self.assertIn("Treaty Articles", _REQUIREMENTS)
        self.assertEqual(_DIR_MAP["Treaty Articles"], "common/treaty_articles")


class InstitutionTests(unittest.TestCase):
    """The institution tooltip renders `[InstitutionType.GetDesc]` with no
    guard, so a missing `<name>_desc` prints the raw key. All 17 mod
    institutions shipped without one."""

    def _run(self, loc_keys):
        tmp = tempfile.mkdtemp()
        _write(tmp, "common/institutions/extra_institutions.txt",
               "institution_my_ministry = {\n\tmodifier = { }\n}\n")
        ms = FakeMS(
            mod_data={"Institutions": {"institution_my_ministry": {}}},
            loc_keys=loc_keys,
        )
        return audit(ms, mod_path=tmp).flags

    def test_missing_desc_alone_is_flagged(self):
        flags = self._run({"institution_my_ministry"})
        self.assertEqual([f.missing_keys for f in flags], [["institution_my_ministry_desc"]])

    def test_name_and_desc_satisfy_the_requirement(self):
        self.assertEqual(
            self._run({"institution_my_ministry", "institution_my_ministry_desc"}), [],
        )

    def test_rules_hold_for_every_vanilla_institution(self):
        import vanilla_parsed
        from loc_coverage_audit import _institution_keys
        snap = vanilla_parsed.load()
        institutions = snap.data["Institutions"]
        self.assertGreaterEqual(len(institutions), 7)
        missing = {
            name: [k for k, req, _ in _institution_keys(name, body)
                   if req and k not in snap.localization]
            for name, body in institutions.items()
        }
        self.assertEqual({n: m for n, m in missing.items() if m}, {})

    def test_registered_in_both_rosters(self):
        from loc_coverage_audit import _REQUIREMENTS, _DIR_MAP, _institution_keys
        self.assertIs(_REQUIREMENTS["Institutions"], _institution_keys)
        self.assertEqual(_DIR_MAP["Institutions"], "common/institutions")


class DiplomaticActionTests(unittest.TestCase):
    """Diplomatic actions resolve a notification autokey family chosen by
    `requires_approval`, `pact` and `should_notify_third_parties`. The
    nd_nuclear_ultimatum_action defect: it set `should_notify_third_parties =
    yes` with no `_action_notification_third_party_*` loc, so every observer
    got a notification titled with the raw key."""

    def _keys(self, body):
        from loc_coverage_audit import _diplomatic_action_keys
        return [k for k, req, _label in _diplomatic_action_keys("my_action", body) if req]

    def test_no_approval_notifies_target_only(self):
        self.assertEqual(self._keys({"requires_approval": "no"}), [
            "my_action",
            "my_action_action_notification_name",
            "my_action_action_notification_desc",
        ])

    def test_third_party_flag_adds_observer_keys(self):
        keys = self._keys({"should_notify_third_parties": "yes"})
        self.assertIn("my_action_action_notification_third_party_name", keys)
        self.assertIn("my_action_action_notification_third_party_desc", keys)
        self.assertNotIn("my_action_action_notification_third_party_break_name", keys)

    def test_pact_adds_break_keys(self):
        keys = self._keys({"should_notify_third_parties": "yes", "pact": {}})
        for stem in ("_action_notification_break", "_action_notification_third_party_break"):
            self.assertIn(f"my_action{stem}_name", keys)
            self.assertIn(f"my_action{stem}_desc", keys)

    def test_unset_or_no_flag_requires_no_observer_keys(self):
        for body in ({}, {"should_notify_third_parties": "no"}):
            self.assertFalse(
                [k for k in self._keys(body) if "third_party" in k], body)

    def test_approval_action_uses_proposal_family(self):
        keys = self._keys({"requires_approval": "yes", "should_notify_third_parties": "yes"})
        self.assertIn("my_action_proposal_notification_name", keys)
        self.assertIn("my_action_proposal_accepted_desc", keys)
        self.assertIn("my_action_proposal_declined_name", keys)
        self.assertIn("my_action_proposal_third_party_accepted_name", keys)
        self.assertIn("my_action_proposal_third_party_declined_desc", keys)
        self.assertNotIn("my_action_action_notification_name", keys)
        self.assertNotIn("my_action_action_notification_third_party_name", keys)

    def test_unwraps_parser_tuples(self):
        keys = self._keys({"should_notify_third_parties": ("=", "yes")})
        self.assertIn("my_action_action_notification_third_party_desc", keys)

    def test_non_dict_body_checks_name_only(self):
        self.assertEqual(self._keys(None), ["my_action"])

    def test_missing_third_party_keys_flagged(self):
        tmp = tempfile.mkdtemp()
        _write(tmp, "common/diplomatic_actions/x.txt",
               "my_action = {\n\trequires_approval = no\n"
               "\tshould_notify_third_parties = yes\n}\n")
        body = {"requires_approval": "no", "should_notify_third_parties": "yes"}
        ms = FakeMS(
            mod_data={"Diplomatic Actions": {"my_action": body}},
            base_data={"Diplomatic Actions": {}},
            loc_keys={
                "my_action",
                "my_action_action_notification_name",
                "my_action_action_notification_desc",
            },
        )
        result = audit(ms, mod_path=tmp)
        self.assertEqual([(f.category, f.entity, f.missing_keys, f.line) for f in result.flags], [(
            "Diplomatic Actions", "my_action",
            ["my_action_action_notification_third_party_name",
             "my_action_action_notification_third_party_desc"],
            1,
        )])

    def test_rules_hold_for_every_localized_vanilla_action(self):
        # The rules are read off vanilla, so vanilla must satisfy them. The
        # two exceptions are internal pacts with no loc at all, not even a name.
        # A failure right after a vanilla bump + `vanilla_parsed.py build`
        # means re-derive the rules from the new corpus, not a mod bug.
        import vanilla_parsed
        from loc_coverage_audit import _diplomatic_action_keys, _unwrap
        snap = vanilla_parsed.load()
        actions = snap.data["Diplomatic Actions"]
        self.assertGreater(len(actions), 40)
        failures = {}
        for name, body in actions.items():
            if name not in snap.localization:
                continue
            missing = [k for k, req, _ in _diplomatic_action_keys(name, _unwrap(body))
                       if req and k not in snap.localization]
            if missing:
                failures[name] = missing
        self.assertEqual(failures, {})
        # Guard against a rule that passes because it derives nothing.
        rivalry = self._keys_for(_diplomatic_action_keys, "rivalry", actions)
        self.assertIn("rivalry_action_notification_third_party_break_desc", rivalry)

    @staticmethod
    def _keys_for(fn, name, actions):
        from loc_coverage_audit import _unwrap
        return [k for k, req, _ in fn(name, _unwrap(actions[name])) if req]

    def test_registered_in_both_rosters(self):
        from loc_coverage_audit import _REQUIREMENTS, _DIR_MAP, _diplomatic_action_keys
        self.assertIs(_REQUIREMENTS["Diplomatic Actions"], _diplomatic_action_keys)
        self.assertEqual(_DIR_MAP["Diplomatic Actions"], "common/diplomatic_actions")


class RenderTests(unittest.TestCase):
    def test_empty_report_smoke(self):
        from loc_coverage_audit import AuditResult
        report = render_report(AuditResult(flags=[], coverage={"files_audited": 0, "by_category": {}}))
        self.assertIn("# Localization coverage audit report", report)
        self.assertIn("_None._", report)

    def test_populated_report_smoke(self):
        from loc_coverage_audit import AuditResult, LocFlag
        result = AuditResult(
            flags=[
                LocFlag(category="Modifiers", entity="x", missing_keys=["x"],
                        file="common/static_modifiers/y.txt", line=1, exemption=None),
            ],
            coverage={"files_audited": 1, "by_category": {"Modifiers": 1}},
        )
        report = render_report(result)
        self.assertIn("`common/static_modifiers/y.txt:1` — `x`", report)
        self.assertIn("Modifiers (1)", report)


if __name__ == "__main__":
    unittest.main()
