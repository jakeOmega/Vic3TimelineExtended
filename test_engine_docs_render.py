"""Tests for engine_docs_render — both unit tests for individual renderers
and an integration test for the `render_all` driver that writes every
reference file into a tempdir.
"""
import contextlib
import io
import logging
import os
import tempfile
import unittest
from unittest import mock

import engine_docs_render
import mod_state_server as mss
from engine_docs_render import (
    _compact_desc,
    _is_regional_iterator,
    _primary_scope,
    render_country_triggers,
    render_modifier_patterns,
    render_modifiers_reference,
    render_summary_event_targets,
    render_summary_modifiers,
    render_summary_on_actions,
    render_summary_triggers_effects,
    render_triggers_effects_reference,
    render_triggers_parsed,
    render_all,
)


class CompactDescTests(unittest.TestCase):
    def test_truncates_at_first_sentence(self):
        s = "First sentence. Second sentence still there."
        self.assertEqual(_compact_desc(s), "First sentence.")

    def test_cuts_inline_usage_example(self):
        s = "Some description some_modifier = value here for example"
        result = _compact_desc(s)
        self.assertNotIn("=", result)

    def test_long_text_is_truncated(self):
        s = "x" * 500
        result = _compact_desc(s, max_len=100)
        self.assertLessEqual(len(result), 100)
        self.assertTrue(result.endswith("..."))

    def test_empty_input(self):
        self.assertEqual(_compact_desc(""), "")


class RegionalIteratorTests(unittest.TestCase):
    def test_matches_regional_patterns(self):
        self.assertTrue(_is_regional_iterator("any_country_in_europe"))
        self.assertTrue(_is_regional_iterator("every_state_in_americas"))
        self.assertTrue(_is_regional_iterator("random_strategic_region_in_india"))

    def test_does_not_match_plain_iterators(self):
        self.assertFalse(_is_regional_iterator("any_country"))
        self.assertFalse(_is_regional_iterator("every_state"))
        self.assertFalse(_is_regional_iterator("any_scope_country"))

    # The engine's script_docs dump prints unrelated script (a random scripted
    # trigger's body, sometimes raw memory) as each regional iterator's
    # description, and a fresh dump shuffles it — ~14k lines of diff per dump.
    def test_summary_replaces_regional_description_with_fixed_text(self):
        entries = [
            {"name": "every_country_in_africa", "scopes": ["none"], "targets": ["country"],
             "description": "military_clothes_trigger = {\n\texists = scope:character\n}"},
            {"name": "every_state_region_in_europe", "scopes": ["none"], "targets": ["state_region"],
             "description": "\x00\x9f garbage"},
        ]
        out = render_summary_triggers_effects(entries)
        self.assertIn("none|every_country_in_africa|Iterate through all countries in geographic region africa", out)
        self.assertIn("none|every_state_region_in_europe|Iterate through all state regions in geographic region europe", out)
        self.assertNotIn("military_clothes_trigger", out)
        self.assertNotIn("garbage", out)

    def test_triggers_parsed_replaces_regional_body(self):
        entries = [
            {"name": "any_province_in_india", "scopes": ["none"], "targets": ["province"],
             "description": "ai_can_incorporate_state = {\n\tOR = { }\n}"},
        ]
        out = render_triggers_parsed(entries)
        self.assertIn("## any_province_in_india", out)
        self.assertIn("Targets: province", out)
        self.assertIn("Iterate through all provinces in geographic region india", out)
        self.assertNotIn("ai_can_incorporate_state", out)

    def test_plain_iterator_description_untouched(self):
        entries = [{"name": "every_country", "scopes": ["none"], "description": "Iterate through all countries globally"}]
        self.assertIn("none|every_country|Iterate through all countries globally", render_summary_triggers_effects(entries))


class PrimaryScopeTests(unittest.TestCase):
    def test_known_scope_mapped_to_label(self):
        self.assertEqual(_primary_scope("country"), "Country")
        self.assertEqual(_primary_scope("interest_group"), "Interest Group")
        self.assertEqual(_primary_scope("political_movement"), "Political Movement")

    def test_unknown_scope_falls_back_to_titlecase(self):
        self.assertEqual(_primary_scope("some_new_scope"), "Some New Scope")

    def test_none_or_empty_is_global(self):
        self.assertEqual(_primary_scope(None), "Global / Logic")
        self.assertEqual(_primary_scope(""), "Global / Logic")
        self.assertEqual(_primary_scope("none"), "Global / Logic")
        self.assertEqual(_primary_scope([]), "Global / Logic")

    def test_list_input_uses_first_element(self):
        self.assertEqual(_primary_scope(["country", "state"]), "Country")


class TriggersEffectsRenderTests(unittest.TestCase):
    def test_renders_with_iterator_family_and_scope_sections(self):
        triggers = [
            {"name": "any_scope_state", "description": "Iterate states.",
             "scopes": ["country"], "targets": ["state"]},
            {"name": "is_at_war", "description": "Country is at war.",
             "scopes": ["country"], "targets": []},
        ]
        effects = [
            {"name": "every_scope_state", "description": "Iterate states.",
             "scopes": ["country"], "targets": ["state"]},
            {"name": "add_modifier", "description": "Add a modifier.",
             "scopes": ["country", "state"], "targets": []},
        ]
        out = render_triggers_effects_reference(triggers, effects)
        self.assertIn("# Victoria 3", out)
        # Iterator family should appear once with both prefixes.
        self.assertIn("`any/every_scope_state`", out)
        # Plain triggers and effects should appear under per-scope sections.
        self.assertIn("`is_at_war`", out)
        self.assertIn("`add_modifier`", out)
        # Header should mention the source files.
        self.assertIn("Auto-generated from", out.splitlines()[0])

    def test_filters_regional_iterators(self):
        triggers = [
            {"name": "any_country_in_europe", "description": "Regional iter.",
             "scopes": ["none"], "targets": ["country"]},
            {"name": "any_country", "description": "Plain iter.",
             "scopes": ["none"], "targets": ["country"]},
        ]
        out = render_triggers_effects_reference(triggers, [])
        self.assertNotIn("`any/every_country_in_europe`", out)
        self.assertNotIn("any_country_in_europe", out)


class ModifiersRenderTests(unittest.TestCase):
    def test_groups_pattern_members_when_index_provided(self):
        modifiers = [
            {"name": "goods_output_grain_add", "mask": "goods", "display_name": "Grain", "description": "Grain out."},
            {"name": "goods_output_iron_add", "mask": "goods", "display_name": "Iron", "description": "Iron out."},
            {"name": "country_authority_add", "mask": "country", "display_name": "Auth", "description": "Auth."},
        ]
        pattern_index = {
            "goods_output_{good}_add": {
                "grain": modifiers[0],
                "iron": modifiers[1],
            }
        }
        out = render_modifiers_reference(modifiers, pattern_index)
        self.assertIn("## Dynamic Patterns", out)
        self.assertIn("`goods_output_{good}_add`", out)
        # Members listed compactly:
        self.assertIn("`goods_output_grain_add`", out)
        self.assertIn("`goods_output_iron_add`", out)
        # Modifiers covered by pattern do NOT also appear in the per-mask list:
        # only the un-grouped country_authority_add should appear there.
        by_mask_section = out.split("## By Mask", 1)[1]
        self.assertIn("`country_authority_add`", by_mask_section)
        self.assertNotIn("`goods_output_grain_add`", by_mask_section)

    def test_no_pattern_index_lists_everything_under_mask(self):
        modifiers = [
            {"name": "country_authority_add", "mask": "country", "display_name": "", "description": "Auth."},
        ]
        out = render_modifiers_reference(modifiers, None)
        self.assertNotIn("## Dynamic Patterns", out)
        self.assertIn("country_authority_add", out)


class ModifierPatternsRenderTests(unittest.TestCase):
    def test_lists_catalog_and_discovered_with_missing(self):
        catalog = [
            {
                "pattern": "goods_output_{good}_add",
                "placeholder": "good",
                "vocab": "good",
                "notes": "Per-good output additive.",
            }
        ]
        pattern_index = {
            "goods_output_{good}_add": {
                "grain": {"name": "goods_output_grain_add", "mask": "goods"},
            }
        }
        discovered = [
            {
                "pattern": "country_{poptype}_strength_mult",
                "placeholder": "poptype",
                "vocab": "poptype",
                "members": ["clergy", "aristo"],
            }
        ]
        vocabularies = {"good": ["grain", "iron", "wheat"], "poptype": ["clergy", "aristo"]}
        out = render_modifier_patterns(catalog, pattern_index, discovered, vocabularies)
        self.assertIn("## Catalog (1 patterns)", out)
        self.assertIn("Per-good output additive.", out)
        # Missing values list (vocab minus present members):
        self.assertIn("Missing values:", out)
        self.assertIn("`iron`", out)
        self.assertIn("`wheat`", out)
        # Discovered section appears with member preview:
        self.assertIn("## Discovered (not yet in catalog)", out)
        self.assertIn("country_{poptype}_strength_mult", out)


class SummaryRenderTests(unittest.TestCase):
    def test_triggers_effects_summary_pipe_format(self):
        entries = [
            {"name": "is_at_war", "scopes": ["country"], "description": "True if at war."},
        ]
        out = render_summary_triggers_effects(entries)
        self.assertIn("country|is_at_war|True if at war.", out)

    def test_modifiers_summary_pipe_format(self):
        entries = [
            {"name": "country_authority_add", "mask": "country", "description": "Adds authority."},
        ]
        out = render_summary_modifiers(entries)
        self.assertIn("country|country_authority_add|Adds authority.", out)

    def test_event_targets_summary(self):
        entries = [
            {"name": "controller", "input_scopes": ["state"], "output_scopes": ["country"], "description": "scope to controller"},
        ]
        out = render_summary_event_targets(entries)
        self.assertIn("state|controller|country|scope to controller", out)

    def test_on_actions_summary(self):
        entries = [
            {"name": "on_yearly_pulse_country", "scopes": ["country"], "from_code": True},
        ]
        out = render_summary_on_actions(entries)
        self.assertIn("on_yearly_pulse_country|country|from_code=yes", out)

    def test_country_triggers_filter(self):
        entries = [
            {"name": "country_thing", "scopes": ["country"], "description": "Country trigger."},
            {"name": "state_thing", "scopes": ["state"], "description": "State trigger."},
        ]
        out = render_country_triggers(entries)
        self.assertIn("country_thing", out)
        self.assertNotIn("state_thing", out)

    def test_triggers_parsed_full_form(self):
        entries = [
            {"name": "test_trigger", "scopes": ["country"], "targets": ["state"],
             "description": "Detailed description here."},
        ]
        out = render_triggers_parsed(entries)
        self.assertIn("## test_trigger", out)
        self.assertIn("Scopes: country", out)
        self.assertIn("Targets: state", out)
        self.assertIn("Detailed description here.", out)


class RenderAllIntegrationTests(unittest.TestCase):
    """Drives the full pipeline end-to-end with synthetic engine_docs."""

    def setUp(self):
        self.engine_docs = {
            "triggers": [
                {"name": "is_at_war", "scopes": ["country"], "targets": [], "description": "At war."},
                {"name": "any_scope_state", "scopes": ["country"], "targets": ["state"],
                 "description": "Iter states."},
            ],
            "effects": [
                {"name": "add_modifier", "scopes": ["country"], "targets": [], "description": "Add."},
                {"name": "every_scope_state", "scopes": ["country"], "targets": ["state"],
                 "description": "Iter."},
            ],
            "modifiers": [
                {"name": "country_authority_add", "mask": "country", "display_name": "Auth", "description": "Auth."},
                {"name": "goods_output_grain_add", "mask": "goods", "display_name": "Grain", "description": "Grain."},
            ],
            "event-targets": [
                {"name": "controller", "input_scopes": ["state"], "output_scopes": ["country"],
                 "scopes": ["state"], "description": "Controller."},
            ],
            "on-actions": [
                {"name": "on_yearly_pulse_country", "from_code": True, "scopes": ["country"]},
            ],
            "custom-localization": [
                {"name": "GetCountryName", "scopes": ["country"], "random_valid": False, "loc_entries": ["x"]},
            ],
        }
        self.pattern_catalog = [
            {"pattern": "goods_output_{good}_add", "placeholder": "good", "vocab": "good",
             "notes": "Per-good output additive."},
        ]
        self.pattern_index = {
            "goods_output_{good}_add": {"grain": self.engine_docs["modifiers"][1]}
        }
        self.vocabularies = {"good": ["grain", "iron"]}

    def test_writes_all_expected_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            written = render_all(
                self.engine_docs,
                tmp,
                pattern_catalog=self.pattern_catalog,
                pattern_index=self.pattern_index,
                discovered_patterns=[],
                vocabularies=self.vocabularies,
            )
            files = sorted(os.listdir(tmp))
        expected = {
            "vic3_triggers_effects_reference.md",
            "vic3_modifier_type_definitions_reference.md",
            "triggers_summary.txt",
            "effects_summary.txt",
            "modifiers_summary.txt",
            "event_targets_summary.txt",
            "on_actions_summary.txt",
            "custom_localization_summary.txt",
            "country_triggers.txt",
            "triggers_parsed.txt",
            "modifier_patterns.md",
        }
        self.assertEqual(set(files), expected)
        # All written sizes positive
        for size in written.values():
            self.assertGreater(size, 0)

    def test_files_carry_auto_generated_header(self):
        with tempfile.TemporaryDirectory() as tmp:
            render_all(
                self.engine_docs,
                tmp,
                pattern_catalog=self.pattern_catalog,
                pattern_index=self.pattern_index,
                vocabularies=self.vocabularies,
            )
            for fname in os.listdir(tmp):
                with open(os.path.join(tmp, fname), "r", encoding="utf-8") as f:
                    head = f.read(400)
                self.assertTrue(
                    "Auto-generated" in head,
                    f"{fname} missing auto-generated header",
                )

    def test_headers_name_the_snapshot_version_not_a_timestamp(self):
        """A re-copied or re-dumped snapshot with identical content must not
        re-diff every header, so headers carry the version, never an mtime."""
        with tempfile.TemporaryDirectory() as tmp:
            src_dir = os.path.join(tmp, "vic3-engine-docs", "1.14.4", "docs")
            os.makedirs(src_dir)
            sources = {}
            for key, fname in [("triggers", "triggers.log"), ("effects", "effects.log"),
                               ("modifiers", "modifiers.log"), ("event-targets", "event_targets.log"),
                               ("on-actions", "on_actions.log"),
                               ("custom-localization", "custom_localization.log")]:
                sources[key] = os.path.join(src_dir, fname)
                with open(sources[key], "w", encoding="utf-8") as f:
                    f.write("")
            out_dir = os.path.join(tmp, "out")
            render_all(self.engine_docs, out_dir, pattern_catalog=self.pattern_catalog,
                       pattern_index=self.pattern_index, vocabularies=self.vocabularies,
                       source_paths=sources)
            for fname in os.listdir(out_dir):
                with open(os.path.join(out_dir, fname), "r", encoding="utf-8") as f:
                    head = f.readline()
                self.assertIn("1.14.4", head, fname)
                self.assertNotRegex(head, r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", fname)

    def test_headers_without_a_versioned_source_carry_no_timestamp(self):
        with tempfile.TemporaryDirectory() as tmp:
            render_all(self.engine_docs, tmp)
            for fname in os.listdir(tmp):
                with open(os.path.join(tmp, fname), "r", encoding="utf-8") as f:
                    head = f.readline()
                self.assertNotRegex(head, r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", fname)

    def test_modifier_patterns_omitted_when_no_catalog(self):
        with tempfile.TemporaryDirectory() as tmp:
            render_all(self.engine_docs, tmp)  # no catalog → no patterns MD
            self.assertNotIn("modifier_patterns.md", os.listdir(tmp))


# ---------------------------------------------------------------------------
# #1592 — `python3 engine_docs_render.py` renders through the server's loader
# ---------------------------------------------------------------------------
_FIXTURE_LOGS = {
    "triggers.log": (
        "# Trigger Documentation\n"
        "## is_at_war\n"
        "Checks whether the country is at war\n"
        "is_at_war = yes\n"
        "Reads gamestate for all scopes.\n"
        "**Supported Scopes**: country\n"
        "\n"
        "## any_scope_state\n"
        "Iterate through all states of a country\n"
        "any_scope_state = { <count=num/all> / <percent=fixed_point> <triggers> }\n"
        "Reads gamestate for all scopes.\n"
        "**Supported Scopes**: country\n"
        "**Supported Targets**: state\n"
    ),
    "effects.log": (
        "# Effect Documentation\n"
        "## add_modifier\n"
        "Adds a timed modifier\n"
        "add_modifier = { name = x }\n"
        "**Supported Scopes**: country, state\n"
    ),
    "modifiers.log": (
        "--- Static modifier types ---\n"
        "country_prestige_add:\n"
        "  Mask: country\n"
        "  Name: Prestige\n"
        "  Description: Adds prestige.\n"
        "goods_output_fish_add:\n"
        "  Mask: goods\n"
        "  Name: Fish output\n"
        "  Description: Adds fish output.\n"
        "goods_output_grain_add:\n"
        "  Mask: goods\n"
        "  Name: Grain output\n"
        "  Description: Adds grain output.\n"
    ),
    "event_targets.log": (
        "### controller\n"
        "The country controlling a state\n"
        "Input Scopes: state\n"
        "Output Scopes: country\n"
    ),
    "on_actions.log": (
        "On Action Documentation:\n"
        "--------------------\n"
        "on_yearly_pulse_country:\n"
        "From Code: Yes\n"
        "Expected Scope: country\n"
        "--------------------\n"
    ),
    "custom_localization.log": (
        "Custom Localization Documentation:\n"
        "--------------------\n"
        "GetCountryName:\n"
        "Scope: country\n"
        "Random Valid: no\n"
        "Entries:\n"
        "country_name_default\n"
        "--------------------\n"
    ),
}

# What a dump taken with the mod loaded adds to modifiers.log.
_MOD_LOADED_ONLY_MODIFIER = "country_te_only_in_the_mod_loaded_dump_bool"


def _write_logs(docs_dir: str, *, extra_modifier: str | None = None, absent=()) -> str:
    os.makedirs(docs_dir)
    for name, text in _FIXTURE_LOGS.items():
        if name in absent:
            continue
        if name == "modifiers.log" and extra_modifier:
            text += f"{extra_modifier}:\n  Mask: country\n  Name: Mod\n  Description: Mod.\n"
        with open(os.path.join(docs_dir, name), "w", encoding="utf-8") as f:
            f.write(text)
    return docs_dir


def _read_dir(path: str) -> dict:
    out = {}
    for name in sorted(os.listdir(path)) if os.path.isdir(path) else ():
        with open(os.path.join(path, name), "rb") as f:
            out[name] = f.read()
    return out


class _Parser:
    def __init__(self, data):
        self.data = data


class _StubModState:
    """The ModState surface `_load_engine_docs` reads: vocabularies for the
    pattern grouping and the modifier types for the mod-source union."""

    def __init__(self):
        self.base_parsers = {"Modifier Types": _Parser({"country_prestige_add": {"decimals": "1"}})}
        self.mod_parsers = {"Modifier Types": _Parser({
            "country_prestige_add": {"decimals": "1"},
            "country_te_script_only_bool": {"script_only": "yes", "boolean": "yes"},
        })}

    def get_data(self, etype):
        return {"grain": {}, "fish": {}, "iron": {}} if etype == "Goods" else {"placeholder": {}}

    def localize(self, key):
        return key


class StandaloneCliTests(unittest.TestCase):
    """The command line must write what a server start writes. It was a second
    code path: it read `vanilla_docs_path`, the dump the game last wrote with
    whatever mods were on, and rendered with no pattern data, so it dropped the
    version from every header, the pattern grouping from the modifier reference
    and `modifier_patterns.md` (#1592)."""

    ELEVEN = {
        "vic3_triggers_effects_reference.md", "vic3_modifier_type_definitions_reference.md",
        "triggers_summary.txt", "effects_summary.txt", "modifiers_summary.txt",
        "event_targets_summary.txt", "on_actions_summary.txt",
        "custom_localization_summary.txt", "country_triggers.txt",
        "triggers_parsed.txt", "modifier_patterns.md",
    }
    # The loader's two other files (gitignored; stubbed empty in setUp).
    ALSO_WRITTEN = {"engine_coverage_report.md", "error_log_digest.md"}

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = tmp.name
        self.snapshot = _write_logs(os.path.join(self.root, "vic3-engine-docs", "1.15.1", "docs"))
        self.mod_loaded = _write_logs(os.path.join(self.root, "game", "docs"),
                                      extra_modifier=_MOD_LOADED_ONLY_MODIFIER)
        self.stub = _StubModState()
        self.digests_steps = []
        patches = [
            # The three places `_engine_docs_source` looks, in its order.
            mock.patch.object(mss, "vanilla_snapshot_docs_path", self.snapshot),
            mock.patch.object(mss, "vanilla_snapshot_docs_path_default", None),
            mock.patch.object(mss, "mod_loaded_docs_path", self.mod_loaded),
            # What a cold start does before the load; no network, no parse.
            mock.patch.object(mss, "_ensure_modding_digests_fresh",
                              lambda: self.digests_steps.append("fetch")),
            mock.patch.object(mss, "_refresh_digest_snapshot_path",
                              lambda: self.digests_steps.append("refresh")),
            mock.patch.object(mss, "cli_mod_state", lambda: self.stub),
            mock.patch.object(mss, "ms", None),
            mock.patch.object(mss, "_vanilla_reference_versions", lambda: (None, None)),
            mock.patch.object(mss, "_version_mismatch_warnings", lambda: []),
            # The loader's other outputs, which need a real ModState and logs.
            mock.patch.object(mss, "_validate_engine_coverage", return_value={}),
            mock.patch.object(mss, "_annotate_validation_with_error_log"),
            mock.patch.object(mss, "_render_engine_coverage_md", return_value=""),
            mock.patch("game_log_reader.render_error_log_digest", return_value=""),
        ]
        # Module state the loader rebinds; restored afterwards.
        for name, value in (("engine_docs", {}), ("engine_docs_sources", {}),
                            ("engine_docs_source_label", ""), ("_engine_docs_warnings", []),
                            ("_last_validation_report", None), ("pattern_catalog", []),
                            ("pattern_index", {}), ("discovered_patterns", []),
                            ("modifier_to_pattern", {}),
                            ("_vanilla_snapshot_contamination", [])):
            patches.append(mock.patch.object(mss, name, value))
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        for logger in (mss.logger, logging.getLogger("mod_state")):
            self.addCleanup(logger.setLevel, logger.level)
            logger.setLevel(logging.CRITICAL + 1)

    def _out(self, name: str) -> str:
        """Point the server's `doc_path` at a fresh folder; returns its engine dir."""
        docs = os.path.join(self.root, name)
        p = mock.patch.object(mss, "doc_path", docs)
        p.start()
        self.addCleanup(p.stop)
        return os.path.join(docs, "engine")

    def _cli(self) -> tuple:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            status = engine_docs_render._cli([])
        return status, out.getvalue(), err.getvalue()

    def test_cli_output_equals_the_server_loaders(self):
        server_dir = self._out("server")
        with mock.patch.object(mss, "ms", self.stub):
            mss._load_engine_docs()
        server_files = _read_dir(server_dir)

        cli_dir = self._out("cli")
        status, out, err = self._cli()
        self.assertEqual((status, err), (0, ""))
        cli_files = _read_dir(cli_dir)

        self.assertEqual(set(server_files), self.ELEVEN | self.ALSO_WRITTEN)
        self.assertEqual(set(cli_files), set(server_files))
        for name in sorted(server_files):
            with self.subTest(file=name):
                self.assertEqual(cli_files[name], server_files[name])
        self.assertIn(f"vanilla_snapshot ({self.snapshot})", out)
        self.assertIn("wrote 11 files", out)

    def test_cli_names_the_version_and_groups_the_patterns(self):
        cli_dir = self._out("cli")
        self.assertEqual(self._cli()[0], 0)
        files = {name: data.decode("utf-8") for name, data in _read_dir(cli_dir).items()}
        for name, text in files.items():
            if name in self.ALSO_WRITTEN:
                continue
            with self.subTest(file=name):
                self.assertIn("1.15.1", text.splitlines()[0])
        reference = files["vic3_modifier_type_definitions_reference.md"]
        self.assertIn("goods_output_{good}_add", reference)
        self.assertIn("goods_output_{good}_add", files["modifier_patterns.md"])

    def test_cli_reads_the_snapshot_not_the_dump_the_game_last_wrote(self):
        cli_dir = self._out("cli")
        self.assertEqual(self._cli()[0], 0)
        summary = _read_dir(cli_dir)["modifiers_summary.txt"].decode("utf-8")
        self.assertIn("country_prestige_add", summary)
        self.assertNotIn(_MOD_LOADED_ONLY_MODIFIER, summary)
        # Nor the mod's own modifier types, which the server unions in.
        self.assertNotIn("country_te_script_only_bool", summary)

    def test_cli_takes_the_cold_start_steps_in_order(self):
        self._out("cli")
        loaded_with = []
        with mock.patch.object(mss, "_load_engine_docs",
                               lambda: loaded_with.append((list(self.digests_steps), mss.ms))):
            self._cli()
        self.assertEqual(loaded_with, [(["fetch", "refresh"], self.stub)])

    def test_cli_exits_1_and_says_why_when_the_files_are_left_alone(self):
        # No snapshot, and a dump with a log missing: the server skips the
        # render, so the command must not report success.
        cli_dir = self._out("cli")
        incomplete = _write_logs(os.path.join(self.root, "incomplete"),
                                 absent=("on_actions.log",))
        with mock.patch.object(mss, "vanilla_snapshot_docs_path", None), \
                mock.patch.object(mss, "mod_loaded_docs_path", incomplete):
            status, out, err = self._cli()
        self.assertEqual(status, 1)
        self.assertIn("on_actions.log", err)
        self.assertIn("not re-rendered", err)
        self.assertNotIn("Done", out)
        self.assertEqual(_read_dir(cli_dir), {})

    def test_cli_warns_when_it_renders_the_mod_loaded_dump(self):
        # The fallback a server start also takes, so the files match it; what
        # the command adds is saying so.
        cli_dir = self._out("cli")
        with mock.patch.object(mss, "vanilla_snapshot_docs_path", None):
            status, out, err = self._cli()
        self.assertEqual(status, 0)
        self.assertIn(f"mod_loaded ({self.mod_loaded})", out)
        self.assertIn("WARNING", err)
        self.assertIn("vanilla_snapshot_docs_path", err)
        self.assertEqual(set(_read_dir(cli_dir)), self.ELEVEN | self.ALSO_WRITTEN)

    def test_cli_reports_a_version_mismatch(self):
        self._out("cli")
        mismatch = [{"label": "version_mismatch", "detail": "vanilla versions disagree: x"}]
        with mock.patch.object(mss, "_version_mismatch_warnings", lambda: mismatch):
            status, _out, err = self._cli()
        self.assertEqual(status, 0)
        self.assertIn("WARNING: vanilla versions disagree: x", err)

    def test_cli_exits_1_when_the_render_crashes(self):
        self._out("cli")
        with mock.patch("engine_docs_render.render_all", side_effect=OSError("disk full")):
            status, out, err = self._cli()
        self.assertEqual(status, 1)
        self.assertIn("render failed", err)
        self.assertNotIn("Done", out)


if __name__ == "__main__":
    unittest.main()
