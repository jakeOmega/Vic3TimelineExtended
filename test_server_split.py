"""#1537 moved mod_state_server.py's routes into `server/` modules as moves with
no behaviour change: the engine-docs group first (stage 1), then the entity,
analysis, validation, vocabulary, log and GUI routes and the post-load chain
(stage 2). This file keeps what each stage proved:

* `GoldenResponseTests` sends every request of a moved group through the real
  `do_GET` (routing, error mapping, JSON encoding; no socket) against a fixed
  fixture and compares the bytes and the status with a golden recorded on the
  commit before the move (`test_fixtures/server_split/<group>.json`). Its
  cases include the error paths: 404, 400, 503, and a handler exception (500).
  Stage 1's engine-docs group has one; stage 2 was checked against the real
  mod instead (its PR says how).
* `MovedNamesTests` checks that every name the moves took out of
  mod_state_server stays importable from it, as the same object, that each
  route module's mixin answers its routes, and that the moved code reads the
  server's state through the live module at call time.

`test_server_routes.py` holds the route table to the handlers, `/help` and
the docs. A golden for another group: a `<GROUP>_CASES` list, a fixture, an
entry in `GROUPS`, and a golden recorded with `--record <group>` on a commit
whose code is the one to pin:

    python3 test_server_split.py --record engine_docs
"""
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from unittest import mock

import mod_state_server as mss

ROOT = os.path.dirname(os.path.abspath(__file__))
GOLDEN_DIR = os.path.join(ROOT, "test_fixtures", "server_split")


class _WireHandler(mss.ModStateHandler):
    """The real do_GET and _respond_json, writing to a buffer instead of a
    socket (the bytes a client receives), as test_query.py's handler does."""

    def __init__(self, path):
        self.path = path
        self.headers = {"Host": "127.0.0.1:8950"}
        self.server = types.SimpleNamespace(server_port=8950)
        self.wfile = io.BytesIO()
        self.status = None
        self.sent_headers = {}

    def send_response(self, code, message=None):
        self.status = code

    def send_header(self, key, value):
        self.sent_headers[key] = value

    def end_headers(self):
        pass


def served(path):
    """(body bytes, status) of GET `path`."""
    handler = _WireHandler(path)
    with mock.patch.object(mss.logger, "error"):  # a 500 logs its traceback
        handler.do_GET()
    body = handler.wfile.getvalue()
    assert handler.sent_headers["Content-Length"] == str(len(body))
    return body, handler.status


def _write(root, rel, text):
    path = os.path.join(root, *rel.split("/"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


# ---------------------------------------------------------------------------
# engine_docs: /engine-docs and its sub-routes (stage 1, server/routes_engine_docs.py)
# ---------------------------------------------------------------------------

ENGINE_DOCS = {
    "effects": [
        {"name": "add_modifier", "origin": "vanilla", "description": "Adds a modifier",
         "example": "add_modifier = { name = x }", "traits": "", "scopes": ["country", "state"],
         "targets": []},
        {"name": "te_effect", "origin": "mod", "description": "A mod effect", "scopes": ["state"]},
        {"name": "set_variable", "origin": "vanilla", "description": "Sets a variable",
         "scopes": ["none"], "reads": "Reads nothing."},
    ],
    "triggers": [
        {"name": "has_modifier", "origin": "vanilla", "description": "Has the modifier",
         "scopes": ["country"]},
        {"name": "add_modifier", "origin": "unknown", "scopes": ["state"]},
    ],
    "modifiers": [
        {"name": "country_prestige_mult", "origin": "vanilla", "mask": "country",
         "display_name": "Prestige", "description": "", "decimals": 0},
        {"name": "building_steel_mill_throughput_add", "origin": "vanilla", "mask": "building",
         "display_name": "Steel Mill Throughput", "description": "Throughput"},
        {"name": "building_iron_mine_throughput_add", "origin": "vanilla", "mask": "building"},
        {"name": "state_te_bonus_add", "origin": "mod", "mask": "state", "mod_redeclares": True,
         "mod_redeclared_in": ["common/modifier_type_definitions/te.txt"], "is_boolean": False},
    ],
    "event-targets": [
        {"name": "capital", "input_scopes": ["country"], "output_scopes": ["state"]},
        {"name": "capital", "input_scopes": ["state"], "output_scopes": ["state"]},
    ],
    "on-actions": [],
    "broken": [{"name": "bad_entry", "scopes": None}],
}

# One pattern over two of the modifiers above, as _refresh_pattern_state builds it.
PATTERN_INDEX = {
    "building_{building}_throughput_add": {
        "steel_mill": ENGINE_DOCS["modifiers"][1],
        "iron_mine": ENGINE_DOCS["modifiers"][2],
    },
}

# One file of call sites (a single file keeps the scan's order independent of
# the filesystem's directory order), and a trigger-localization label.
ENGINE_DOCS_COMMON = {
    "scripted_effects/te_calls.txt": (
        "te_target = {\n"
        "\tlimit = { always = yes }\n"
        "}\n"
        "te_caller = {\n"
        "\tte_target = { X = 1 }\n"
        "\tif = {\n"
        "\t\tte_target = yes\n"
        "\t}\n"
        "\tnot_te_target_suffix = yes\n"
        "\tte_target >= 3\n"
        "}\n"
    ),
    "trigger_localization/te_labels.txt": "te_target = {\n\tglobal = TE_TARGET\n}\n",
}

ENGINE_DOCS_LOC = (
    "﻿l_english:\n"
    " te_a: \"[GetStaticModifier('te_x').GetDesc] and [ROOT.GetCountry.GetName]\"\n"
    " te_b: \"[Concept('concept_pop', '$concept_pops$')] [concept_homeland]\"\n"
    " te_c: \"[sCharacter('ruler').GetFullName] [GetStaticModifier('te_y').GetName]\"\n"
)
ENGINE_DOCS_GUI = (
    "types te {\n"
    "\ttext = \"[AddTextIf(Not(StringIsEmpty(Article.GetEffectsDesc)), 'x')]\"\n"
    "\ttooltip = \"[Country.GetName]\"\n"
    "}\n"
)

GREP = shutil.which("grep")

# Fixed, so the 503 body (which names the directory) is the same everywhere.
MISSING_COMMON = "/nonexistent/te_server_split/game/common"

# (label, path, overrides of mod_state_server globals for that one request)
ENGINE_DOCS_CASES = [
    ("index", "/engine-docs", {}),
    ("listing", "/engine-docs/effects", {}),
    ("listing q", "/engine-docs/effects?q=MODIFIER", {}),
    ("listing q display_name", "/engine-docs/modifiers?q=steel", {}),
    ("listing scope", "/engine-docs/effects?scope=State", {}),
    ("listing scope input/output", "/engine-docs/event-targets?scope=country", {}),
    ("listing mask", "/engine-docs/modifiers?mask=building", {}),
    ("listing origin", "/engine-docs/effects?origin=MOD", {}),
    ("listing origin unknown", "/engine-docs/triggers?origin=unknown", {}),
    ("listing truncated", "/engine-docs/effects?limit=1", {}),
    ("listing empty type", "/engine-docs/on-actions", {}),
    ("group", "/engine-docs/modifiers?group=true", {}),
    ("group limit", "/engine-docs/modifiers?group=yes&limit=0", {}),
    ("group without patterns", "/engine-docs/modifiers?group=1", {"pattern_index": {}}),
    ("one entry", "/engine-docs/effects/add_modifier", {}),
    ("one entry, repeated name", "/engine-docs/event-targets/capital", {}),
    ("404 did_you_mean", "/engine-docs/effects/add_modifer", {}),
    ("404 defined_in_types", "/engine-docs/effects/has_modifier", {}),
    ("400 two name segments", "/engine-docs/effects/a/b", {}),
    ("404 unknown type", "/engine-docs/bogus", {}),
    ("400 origin without name", "/engine-docs/origin", {}),
    ("origin", "/engine-docs/origin/add_modifier", {}),
    ("origin modifier fields", "/engine-docs/origin/state_te_bonus_add", {}),
    ("origin not found", "/engine-docs/origin/no_such_name", {}),
    ("400 usage without name", "/engine-docs/usage", {}),
    ("400 usage invalid name", "/engine-docs/usage/Not-Valid", {}),
    ("usage", "/engine-docs/usage/te_target", {}),
    ("usage limit and context", "/engine-docs/usage/te_target?limit=1&before=0&after=0", {}),
    ("usage include_defs", "/engine-docs/usage/te_target?include_defs=true", {}),
    ("usage no hits", "/engine-docs/usage/te_absent", {}),
    ("usage python walk", "/engine-docs/usage/te_target", {"_no_grep": True}),
    ("503 usage no vanilla common", "/engine-docs/usage/te_target", {"_BASE_COMMON": MISSING_COMMON}),
    ("500 usage bad limit", "/engine-docs/usage/te_target?limit=x", {}),
    ("loc-functions", "/engine-docs/loc-functions", {}),
    ("loc-functions filtered",
     "/engine-docs/loc-functions?q=get&kind=Function&min_count=1&limit=2&include_examples=true", {}),
    ("loc-functions kind scope", "/engine-docs/loc-functions?kind=scope&include_examples=1", {}),
    ("loc-function", "/engine-docs/loc-functions/GetStaticModifier", {}),
    ("loc-function limit", "/engine-docs/loc-functions/GetStaticModifier?limit=1", {}),
    ("loc-function not found", "/engine-docs/loc-functions/NoSuchFunction", {}),
    ("500 listing bad limit", "/engine-docs/effects?limit=abc", {}),
    ("500 loc-functions bad min_count", "/engine-docs/loc-functions?min_count=lots", {}),
    ("500 entry with null scopes", "/engine-docs/broken?scope=x", {}),
]


@contextlib.contextmanager
def engine_docs_fixture():
    with tempfile.TemporaryDirectory() as tmp, contextlib.ExitStack() as stack:
        base = os.path.join(tmp, "base")
        for rel, text in ENGINE_DOCS_COMMON.items():
            _write(base, "game/common/" + rel, text)
        _write(base, "game/localization/english/te_l_english.yml", ENGINE_DOCS_LOC)
        _write(base, "game/gui/te.gui", ENGINE_DOCS_GUI)
        for name, value in (
            ("engine_docs", json.loads(json.dumps(ENGINE_DOCS))),
            ("engine_docs_source_label", "vanilla_snapshot"),
            ("pattern_index", PATTERN_INDEX),
            ("base_game_path", base),
            ("_BASE_COMMON", os.path.join(base, "game", "common")),
            ("_LOC_FUNCTION_INDEX", None),
        ):
            stack.enter_context(mock.patch.object(mss, name, value))
        # The usage scan takes grep, else ripgrep, else a Python walk, by what
        # is on PATH: pin grep so `backend` is the same on every machine.
        stack.enter_context(mock.patch("shutil.which", side_effect=lambda name: GREP if name == "grep" else None))
        yield


def _with_overrides(overrides):
    stack = contextlib.ExitStack()
    for name, value in overrides.items():
        if name == "_no_grep":
            stack.enter_context(mock.patch("shutil.which", return_value=None))
        else:
            stack.enter_context(mock.patch.object(mss, name, value))
    return stack


GROUPS = {
    "engine_docs": (ENGINE_DOCS_CASES, engine_docs_fixture),
}


def responses(group):
    """{label: {"path", "status", "body"}} for every case of `group`."""
    cases, fixture = GROUPS[group]
    out = {}
    with fixture():
        for label, path, overrides in cases:
            with _with_overrides(overrides):
                body, status = served(path)
            out[label] = {"path": path, "status": status, "body": body.decode("utf-8")}
    return out


def golden_path(group):
    return os.path.join(GOLDEN_DIR, f"{group}.json")


class GoldenResponseTests(unittest.TestCase):
    """Each moved route answers byte for byte as it did before the move."""

    def check_group(self, group):
        with open(golden_path(group), encoding="utf-8") as fh:
            golden = json.load(fh)["responses"]
        got = responses(group)
        self.assertEqual(sorted(got), sorted(golden), "the case list changed: re-record on the pre-move commit")
        for label, want in golden.items():
            with self.subTest(case=label, path=want["path"]):
                if GREP is None and '"backend": "grep"' in want["body"]:
                    self.skipTest("no grep on PATH")
                self.assertEqual(got[label]["path"], want["path"])
                self.assertEqual(got[label]["status"], want["status"])
                self.assertEqual(got[label]["body"], want["body"])

    def test_engine_docs(self):
        self.check_group("engine_docs")

    def test_cases_cover_every_status(self):
        with open(golden_path("engine_docs"), encoding="utf-8") as fh:
            statuses = {r["status"] for r in json.load(fh)["responses"].values()}
        self.assertEqual(statuses, {200, 400, 404, 500, 503})


# Every name a stage moved out of mod_state_server, by module. Each must stay
# importable from mod_state_server (tests and tools import them from there).
MOVED = {
    "server.routes_engine_docs": [
        "EngineDocsRoutes", "_LOC_IDENT_RE", "_build_loc_function_index", "_engine_docs_find_usage",
        "_get_loc_function_index", "_group_similar_entries", "_is_function_like_ident",
    ],
    "server.routes_logs": [
        "LogRoutes",
    ],
    "server.routes_gui": [
        "GuiRoutes", "_build_gui_render_index", "_get_gui_render_index", "_GUI_DATAREF_RE",
        "_GUI_LOC_ATTRS", "_GUI_TEXT_ATTR_RE", "ENTITY_TYPE_TO_DATATYPE", "FIELD_TO_METHODS",
    ],
    "server.routes_vocabulary": [
        "VocabularyRoutes",
    ],
    "server.routes_validation": [
        "ValidationRoutes", "_ALLOWLIST_TYPE_SLUGS", "_code_part", "_collect_image_uses",
        "_entity_image", "_extract_define_names", "_extract_surface_keys", "_extract_toplevel_keys",
        "_find_duplicate_images", "_find_placeholder_icons", "_flagships_on_company_logo",
        "_git_diff_names", "_git_log_touched", "_git_lstree_at_ref", "_git_show_at_ref",
        "_icon_definition_sites", "_image_content_hash", "_image_entity_uses",
        "_IMAGE_FIELDS_BY_TYPE", "_image_origin", "_iter_loc_at_ref", "_live_vanilla_loc_map",
        "_load_image_allowlist", "_load_standin_patterns", "_migration_gui_at_risk",
        "_migration_loc_drift", "_MIGRATION_SURFACE_CATEGORIES", "_migration_surface_diff",
        "_MOD_GREP_DIRS", "_mod_grep_mentions", "_mod_loc_keys", "_overlap_state",
        "_OVERLAP_STATE_CACHE_SIZE", "_overlap_vanilla_index", "_parse_loc_lines",
        "_PLACEHOLDER_STATUSES", "_principle_group_of", "_read_live_file",
        "_render_duplicate_images_text", "_render_placeholder_icons_text", "_resolve_image_path",
        "_SHARED_BY_DESIGN_ICON_FIELDS", "_SHARED_WITH_LIMIT", "_TOP_LEVEL_OPENER_RE",
        "_TOPLEVEL_KEY_RE", "_validate_git_ref",
    ],
    "server.routes_analysis": [
        "AnalysisRoutes", "_BAG_CONTAINERS", "_classify_option_polarity", "_data_contains_string",
        "_describe_add_modifier", "_describe_change_variable", "_emit_event_effect",
        "_EVENT_HEADER_RE", "_event_ids_from_mod_file", "_extract_event_ids_from_file",
        "_extract_modifier_fields", "_find_dominance_issues", "_find_modifier_grants",
        "_find_soft_dominance_issues", "_format_value", "_get_loc_accessor_index",
        "_get_script_args_result", "_get_variable_usage_index", "_grant_block_label",
        "_grant_entity_dirs", "_grant_entity_type_name", "_GRANT_LINE_RE", "_GRANT_NESTED_PARENTS",
        "_GRANT_OPENER_RE", "_GRANT_REPLACE_RE", "_grant_scan_plan", "_GRANT_SKIP_DIRS",
        "_grant_type_key", "_iter_field_values", "_mod_replaced_entity_ids",
        "_modifier_color_lookup", "_polarity", "_POLARITY_GLYPHS", "_render_effect_text",
        "_render_event_balance_issues_text", "_render_event_balance_text",
        "_resolve_mod_relative_path", "_resolve_static_modifier", "_SCALING_WRAPPERS",
        "_scan_events_for_reviewed_dominance", "_scan_file_for_grants", "_summarize_balance_option",
        "_summarize_polarity", "_try_float", "_walk_event_effects", "EVENT_BALANCE_CONTAINER_KEYS",
        "EVENT_BALANCE_OPTION_META_KEYS", "MODIFIER_GRANT_SOURCES",
    ],
    "server.routes_entities": [
        "EntityRoutes", "_company_catalog", "_diff_entity_fields", "_extract_parameters",
        "_loc_keys_for", "_normalize_entity_type", "_paradox_text", "_PARAM_RE", "_party_catalog",
        "_resolve_entity_type", "_singularize_word", "_state_history_tables", "_unwrap_modifiers",
        "_unwrap_val", "LOC_KEY_FAMILIES",
    ],
    "server.post_load": [
        "_changed_files", "_failure_warning", "_POST_LOAD_TRACEBACK_TAIL_LINES",
        "_POST_LOAD_WARN_KEYS", "_reparse_mod_after_writes", "_run_generator_chain",
        "_run_post_load_generators", "_snapshot_mod_text_files", "_WRITER_WATCH_DIRS",
        "_WRITER_WATCH_SUFFIXES", "PARTIAL_VANILLA_FILE_REGENERATORS", "POST_LOAD_AUDITS",
        "POST_LOAD_GENERATORS", "POST_LOAD_REGENERATORS", "VANILLA_FILE_REGENERATORS",
    ],
}

# Module-level state the moved code reads or rebinds. It stays defined in
# mod_state_server, and the moved code reaches it through server_state().
STATE_LEFT_IN_SERVER = [
    "engine_docs", "engine_docs_source_label", "pattern_index", "base_game_path",
    "_BASE_COMMON", "_LOC_FUNCTION_INDEX", "_USAGE_TARGET_RE_CACHE", "_LOC_EXPR_RE",
    # stage 2
    "ms", "mod_path", "dev_reference_docs", "_GUI_RENDER_INDEX", "_VANILLA_LOC_CACHE",
    "_last_validation_report", "_overlap_state_cache", "_overlap_vanilla_cache",
    "_tech_unlocks_index_cache", "_company_catalog_cache", "_party_catalog_cache",
    "_state_history_cache", "_script_args_cache", "_variable_usage_cache", "_loc_accessor_cache",
    "_post_load_warnings", "_post_load_wrote_files", "_post_load_reparsed",
]

# The handler mixin each route module adds to ModStateHandler.
MIXINS = {
    "server.routes_engine_docs": "EngineDocsRoutes",
    "server.routes_entities": "EntityRoutes",
    "server.routes_analysis": "AnalysisRoutes",
    "server.routes_validation": "ValidationRoutes",
    "server.routes_vocabulary": "VocabularyRoutes",
    "server.routes_logs": "LogRoutes",
    "server.routes_gui": "GuiRoutes",
}


class MovedNamesTests(unittest.TestCase):

    def test_moved_names_stay_importable_as_the_same_object(self):
        import importlib
        for module_name, names in MOVED.items():
            module = importlib.import_module(module_name)
            for name in names:
                with self.subTest(name=name):
                    self.assertIs(getattr(mss, name), getattr(module, name))

    def test_handler_methods_come_from_the_route_module(self):
        from server import routes_engine_docs
        self.assertIs(mss.ModStateHandler._engine_docs, routes_engine_docs.EngineDocsRoutes._engine_docs)
        self.assertNotIn("_engine_docs", vars(mss.ModStateHandler))
        import importlib
        for module_name, mixin_name in MIXINS.items():
            mixin = getattr(importlib.import_module(module_name), mixin_name)
            self.assertIn(mixin, mss.ModStateHandler.__mro__)
            methods = [n for n, v in vars(mixin).items() if callable(v) or isinstance(v, staticmethod)]
            self.assertTrue(methods, mixin_name)
            for name in methods:
                with self.subTest(mixin=mixin_name, method=name):
                    self.assertNotIn(name, vars(mss.ModStateHandler))
                    self.assertIs(getattr(mss.ModStateHandler, name), getattr(mixin, name))

    def test_no_two_mixins_define_one_method(self):
        import importlib
        seen = {}
        for module_name, mixin_name in MIXINS.items():
            mixin = getattr(importlib.import_module(module_name), mixin_name)
            for name in vars(mixin):
                if name.startswith("__"):
                    continue
                with self.subTest(method=name):
                    self.assertNotIn(name, seen, f"{name} in both {seen.get(name)} and {mixin_name}")
                seen[name] = mixin_name

    def test_state_stays_in_the_server_module(self):
        import importlib
        for name in STATE_LEFT_IN_SERVER:
            self.assertTrue(hasattr(mss, name), name)
            for module_name in MOVED:
                module = importlib.import_module(module_name)
                with self.subTest(name=name, module=module_name):
                    self.assertFalse(hasattr(module, name),
                                     f"{name} copied into {module_name}: a rebinding in "
                                     "mod_state_server would no longer reach it")

    def test_state_is_read_at_call_time(self):
        # A rebinding after import (what _load_engine_docs and the tests do) is seen.
        with mock.patch.object(mss, "engine_docs", {"only": [{"name": "x"}]}), \
                mock.patch.object(mss, "engine_docs_source_label", "late"):
            body = json.loads(served("/engine-docs")[0])
        self.assertEqual(body, {"available_types": ["only"], "counts": {"only": 1}, "source_label": "late"})
        with mock.patch.object(mss, "_LOC_FUNCTION_INDEX", {"F": {"count": 1}}):
            self.assertEqual(mss._get_loc_function_index(), {"F": {"count": 1}})

    def test_state_comes_from_the_registered_globals(self):
        import server
        self.assertIs(server.server_globals(), vars(mss))  # imported: pytest, query.py, an audit's CLI
        state = server.server_state()
        with mock.patch.object(mss, "engine_docs", {"late": []}):
            self.assertEqual(state.engine_docs, {"late": []})
        with mock.patch.object(mss, "_LOC_FUNCTION_INDEX", None):
            state._LOC_FUNCTION_INDEX = {"F": {}}
            self.assertEqual(mss._LOC_FUNCTION_INDEX, {"F": {}})
        with self.assertRaises(AttributeError):
            state.no_such_name_anywhere
        # The script's own globals, wherever they live, win over an imported copy.
        script_globals = {"__name__": "__main__"}
        with mock.patch.object(server, "_registered", [script_globals, vars(mss)]):
            self.assertIs(server.server_globals(), script_globals)
        with mock.patch.object(server, "_registered", []):
            with self.assertRaises(RuntimeError):
                server.server_globals()

    # How each way of running the file executes its code: into the __main__
    # module (`python3 mod_state_server.py`, `-m`), or into a plain dict
    # (`python3 -m cProfile|profile|trace mod_state_server.py`, built the way
    # cProfile.main and trace.main build it). The last line, main(), is left
    # out: it would start a server.
    _PROBE = """\
import importlib.machinery, io, json, sys, types
mode, path = sys.argv[1], sys.argv[2]
src = open(path, encoding='utf-8').read()
tail = 'if __name__ == "__main__":\\n    main()\\n'
assert src.endswith(tail), 'the file no longer ends with its main() call'
code = compile(src[:-len(tail)], path, 'exec')
if mode == 'script':
    globs = sys.modules['__main__'].__dict__
    globs['__file__'] = path
    exec(code, globs)
else:
    globs = {'__spec__': importlib.machinery.ModuleSpec(name='__main__', loader=None, origin=path),
             '__file__': path, '__name__': '__main__', '__package__': None, '__cached__': None}
    if mode == 'cProfile':
        import cProfile
        cProfile.Profile().runctx(code, globs, None)
    else:
        import trace
        trace.Trace(count=0, trace=0).runctx(code, globs, globs)
globs['engine_docs'] = {'from_main': []}
class H(globs['ModStateHandler']):
    def __init__(self, p):
        self.path = p
        self.headers = {'Host': '127.0.0.1:8950'}
        self.server = types.SimpleNamespace(server_port=8950)
        self.wfile = io.BytesIO()
    def send_response(self, code, message=None): self.code = code
    def send_header(self, k, v): pass
    def end_headers(self): pass
out = {}
for p in ('/engine-docs', '/engine-docs/bogus'):
    h = H(p)
    h.do_GET()
    out[p] = [h.code, json.loads(h.wfile.getvalue())]
out['copy_imported'] = 'mod_state_server' in sys.modules
print(json.dumps(out))
"""

    def test_routes_serve_the_running_file_state_however_it_was_run(self):
        # The real thing, in a fresh interpreter per mode: a request through
        # the running file's handler answers from that file's globals, raises
        # its own NotFound (a copy's class would miss do_GET's except: 500),
        # and loads no second mod_state_server.
        env = dict(os.environ)
        for key, value in {"VIC3_BASE_GAME": "/nonexistent/game", "VIC3_MOD_DEPLOY_TARGET": "/nonexistent/deploy",
                           "VIC3_VANILLA_REPO": "/nonexistent/vic3", "VIC3_VANILLA_DOCS_RUNTIME": "/nonexistent/docs",
                           "VIC3_GAME_LOGS": "/nonexistent/logs"}.items():
            env.setdefault(key, value)
        for mode in ("script", "cProfile", "trace"):
            with self.subTest(mode=mode):
                proc = subprocess.run(
                    [sys.executable, "-c", self._PROBE, mode, os.path.join(ROOT, "mod_state_server.py")],
                    cwd=ROOT, env=env, capture_output=True, text=True, timeout=120)
                self.assertEqual(proc.returncode, 0, proc.stderr[-2000:])
                result = json.loads(proc.stdout.strip().splitlines()[-1])
                self.assertEqual(result["/engine-docs"][0], 200)
                self.assertEqual(result["/engine-docs"][1]["available_types"], ["from_main"])
                self.assertEqual(result["/engine-docs/bogus"][0], 404)
                self.assertFalse(result["copy_imported"])

    def test_route_modules_do_not_import_the_server_at_import_time(self):
        # A module-level `import mod_state_server` would, under __main__, load
        # the second copy described above.
        import ast
        for module_name in MOVED:
            path = os.path.join(ROOT, *module_name.split(".")) + ".py"
            with open(path, encoding="utf-8") as fh:
                tree = ast.parse(fh.read())
            for node in tree.body:
                names = []
                if isinstance(node, ast.Import):
                    names = [a.name for a in node.names]
                elif isinstance(node, ast.ImportFrom):
                    names = [node.module or ""]
                with self.subTest(module=module_name, line=getattr(node, "lineno", 0)):
                    self.assertNotIn("mod_state_server", names)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--record":
        group = sys.argv[2]
        os.makedirs(GOLDEN_DIR, exist_ok=True)
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                                capture_output=True, text=True).stdout.strip()
        data = {"recorded_on": commit, "responses": responses(group)}
        with open(golden_path(group), "w", encoding="utf-8", newline="\n") as fh:
            json.dump(data, fh, indent=1, ensure_ascii=False, sort_keys=True)
            fh.write("\n")
        print(f"wrote {golden_path(group)} ({len(data['responses'])} cases, from {commit})")
    else:
        unittest.main()
