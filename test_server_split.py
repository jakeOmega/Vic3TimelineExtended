"""#1537 moves mod_state_server.py's routes into `server/` modules, one group per
PR, as moves with no behaviour change. This file is the proof each stage keeps:

* `GoldenResponseTests` sends every request of a moved group through the real
  `do_GET` (routing, error mapping, JSON encoding; no socket) against a fixed
  fixture and compares the bytes and the status with a golden recorded on the
  commit before the move (`test_fixtures/server_split/<group>.json`). Its
  cases include the error paths: 404, 400, 503, and a handler exception (500).
* `MovedNamesTests` checks that every name the move took out of
  mod_state_server stays importable from it, as the same object, and that the
  moved code reads the server's state through the live module at call time.

The next stage adds its group: a `<GROUP>_CASES` list, a fixture, an entry in
`GROUPS`, and a golden recorded with `--record <group>` on the commit BEFORE
its move (record after the move and the test proves nothing):

    python3 test_server_split.py --record engine_docs
"""
import contextlib
import io
import json
import os
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
        "EngineDocsRoutes",
        "_engine_docs_find_usage",
        "_get_loc_function_index",
        "_build_loc_function_index",
        "_is_function_like_ident",
        "_LOC_IDENT_RE",
        "_group_similar_entries",
    ],
}

# Module-level state the moved code reads or rebinds. It stays defined in
# mod_state_server, and the moved code reaches it through server_module().
STATE_LEFT_IN_SERVER = [
    "engine_docs", "engine_docs_source_label", "pattern_index", "base_game_path",
    "_BASE_COMMON", "_LOC_FUNCTION_INDEX", "_USAGE_TARGET_RE_CACHE", "_LOC_EXPR_RE",
]


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

    def test_state_stays_in_the_server_module(self):
        from server import routes_engine_docs
        for name in STATE_LEFT_IN_SERVER:
            with self.subTest(name=name):
                self.assertTrue(hasattr(mss, name))
                self.assertFalse(hasattr(routes_engine_docs, name),
                                 f"{name} copied into the route module: a rebinding in "
                                 "mod_state_server would no longer reach it")

    def test_state_is_read_at_call_time(self):
        # A rebinding after import (what _load_engine_docs and the tests do) is seen.
        with mock.patch.object(mss, "engine_docs", {"only": [{"name": "x"}]}), \
                mock.patch.object(mss, "engine_docs_source_label", "late"):
            body = json.loads(served("/engine-docs")[0])
        self.assertEqual(body, {"available_types": ["only"], "counts": {"only": 1}, "source_label": "late"})
        with mock.patch.object(mss, "_LOC_FUNCTION_INDEX", {"F": {"count": 1}}):
            self.assertEqual(mss._get_loc_function_index(), {"F": {"count": 1}})

    def test_server_module_is_main_when_the_server_runs_as_a_script(self):
        # `python3 mod_state_server.py` runs the module as __main__; an
        # `import mod_state_server` there would load a second copy with empty
        # state, so the route modules must take __main__.
        import server
        self.assertIs(server.server_module(), mss)
        fake_main = types.ModuleType("__main__")
        fake_main._MOD_STATE_SERVER_ENTRY_POINT = True
        with mock.patch.dict(sys.modules, {"__main__": fake_main}):
            self.assertIs(server.server_module(), fake_main)
        other_main = types.ModuleType("__main__")  # pytest, scripts/query.py, an audit's CLI
        with mock.patch.dict(sys.modules, {"__main__": other_main}):
            self.assertIs(server.server_module(), mss)

    def test_routes_serve_main_state_when_run_as_a_script(self):
        # The real thing, in a fresh interpreter: the file's code runs as
        # __main__ (all of it but the last line, which would start the
        # server), and a request through its handler must answer from
        # __main__'s state without importing a second mod_state_server.
        script = (
            "import io, json, sys, types\n"
            "path = sys.argv[1]\n"
            "src = open(path, encoding='utf-8').read()\n"
            "tail = 'if __name__ == \"__main__\":\\n    main()\\n'\n"
            "assert src.endswith(tail), 'the file no longer ends with its main() call'\n"
            "entry = sys.modules['__main__']  # not `main`: the server defines main()\n"
            "entry.__file__ = path\n"
            "exec(compile(src[:-len(tail)], path, 'exec'), entry.__dict__)\n"
            "entry.engine_docs = {'from_main': []}\n"
            "class H(ModStateHandler):\n"
            "    def __init__(self, p):\n"
            "        self.path = p\n"
            "        self.headers = {'Host': '127.0.0.1:8950'}\n"
            "        self.server = types.SimpleNamespace(server_port=8950)\n"
            "        self.wfile = io.BytesIO()\n"
            "    def send_response(self, code, message=None): self.code = code\n"
            "    def send_header(self, k, v): pass\n"
            "    def end_headers(self): pass\n"
            "h = H('/engine-docs')\n"
            "h.do_GET()\n"
            "print(json.dumps({'code': h.code, 'body': json.loads(h.wfile.getvalue()),\n"
            "                  'copy_imported': 'mod_state_server' in sys.modules}))\n"
        )
        import subprocess
        env = dict(os.environ)
        for key, value in {"VIC3_BASE_GAME": "/nonexistent/game", "VIC3_MOD_DEPLOY_TARGET": "/nonexistent/deploy",
                           "VIC3_VANILLA_REPO": "/nonexistent/vic3", "VIC3_VANILLA_DOCS_RUNTIME": "/nonexistent/docs",
                           "VIC3_GAME_LOGS": "/nonexistent/logs"}.items():
            env.setdefault(key, value)
        proc = subprocess.run([sys.executable, "-c", script, os.path.join(ROOT, "mod_state_server.py")],
                              cwd=ROOT, env=env, capture_output=True, text=True, timeout=120)
        self.assertEqual(proc.returncode, 0, proc.stderr[-2000:])
        result = json.loads(proc.stdout.strip().splitlines()[-1])
        self.assertEqual(result["code"], 200)
        self.assertEqual(result["body"]["available_types"], ["from_main"])
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
        import subprocess
        commit = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                                capture_output=True, text=True).stdout.strip()
        data = {"recorded_on": commit, "responses": responses(group)}
        with open(golden_path(group), "w", encoding="utf-8", newline="\n") as fh:
            json.dump(data, fh, indent=1, ensure_ascii=False, sort_keys=True)
            fh.write("\n")
        print(f"wrote {golden_path(group)} ({len(data['responses'])} cases, from {commit})")
    else:
        unittest.main()
