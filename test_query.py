"""`scripts/query.py` (#1538): the offline answer to a lookup is the same bytes
the server sends for it, on the same fixtures, for each of the five lookups."""
from __future__ import annotations

import http.client
import io
import json
import os
import tempfile
import types
import unittest
import urllib.error
from unittest import mock

import mod_state_server as mss
import scripts.query as query
from mod_state import ModState

VANILLA_LAWS = """\
law_monarchy = {
\tgroup = lawgroup_governance_principles
\tmodifier = {
\t\tcountry_prestige_mult = 0.1
\t\tcountry_legitimacy_base_add = 10
\t}
}
law_anarchy = {
\tgroup = lawgroup_governance_principles
}
"""

MOD_LAWS = """\
law_te_council = {
\tgroup = lawgroup_governance_principles
\tdisallowing_laws = { law_anarchy }
\tmodifier = {
\t\tcountry_prestige_mult = 0.25
\t\tstate_goods_output_mult = 0.05
\t}
}
"""

EFFECTS = """\
te_some_helper = {
\tadd_modifier = { name = $NAME$ }
}
"""

EVENT = """\
namespace = te_q
te_q.1 = {
\timmediate = {
\t\tte_some_helper = { NAME = x EXTRA = y }
\t}
}
"""


class _WireHandler(mss.ModStateHandler):
    """The real do_GET and _respond_json, writing to a buffer instead of a
    socket: the bytes a client of the server receives."""

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
    handler = _WireHandler(path)
    handler.do_GET()
    body = handler.wfile.getvalue()
    assert handler.sent_headers["Content-Length"] == str(len(body))
    return body, handler.status


def run_cli(argv):
    """(stdout bytes, exit code, stderr text) of `query.main(argv)`."""
    out = io.TextIOWrapper(io.BytesIO(), encoding="utf-8")
    err = io.StringIO()
    with mock.patch("sys.stdout", out), mock.patch("sys.stderr", err):
        code = query.main(argv)
        out.flush()
    return out.buffer.getvalue(), code, err.getvalue()


def _write(root, rel, text):
    path = os.path.join(root, *rel.split("/"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


class OfflineMatchesServerTests(unittest.TestCase):
    """Each lookup through `query.main` and through the server's do_GET, on
    one fixture mod + vanilla tree and one ModState."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls._tmp.cleanup)
        root = cls._tmp.name
        cls.mod = os.path.join(root, "mod")
        cls.base = os.path.join(root, "base")
        _write(cls.base, "game/common/laws/00_laws.txt", VANILLA_LAWS)
        _write(cls.mod, "common/laws/te_laws.txt", MOD_LAWS)
        _write(cls.mod, "common/scripted_effects/te_effects.txt", EFFECTS)
        _write(cls.mod, "events/te_q.txt", EVENT)
        state = ModState({"Laws": os.path.join(cls.base, "game", "common", "laws")},
                         {"Laws": os.path.join(cls.mod, "common", "laws")})
        state.localization = {
            "law_monarchy": "Monarchy",
            "law_monarchy_desc": "Rule by a crowned head — not a café council.",
            "law_anarchy": "Anarchy",
            "law_te_council": "Ratsversammlung (Rätë)",
        }
        cls.state = state

    def setUp(self):
        for name, value in (
            ("ms", self.state),
            ("mod_path", self.mod),
            ("_MOD_COMMON", os.path.join(self.mod, "common")),
            ("base_game_path", self.base),
            ("_BASE_COMMON", os.path.join(self.base, "game", "common")),
            ("_script_args_cache", None),
        ):
            patcher = mock.patch.object(mss, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        # The audit would look for the game's own helpers; the fixture has none.
        patcher = mock.patch.object(mss.script_argument_audit, "vanilla_game_dir",
                                    return_value=None)
        patcher.start()
        self.addCleanup(patcher.stop)
        # Never reach for a real server from a test.
        patcher = mock.patch.object(query, "server_for_this_checkout",
                                    side_effect=AssertionError("--offline must not ask"))
        patcher.start()
        self.addCleanup(patcher.stop)

    CASES = [
        (["localize", "law_monarchy"], "/localize/law_monarchy", 200),
        (["localize", "law_te_council"], "/localize/law_te_council", 200),
        (["references", "law_anarchy"], "/references/law_anarchy", 200),
        (["references", "no_such_thing"], "/references/no_such_thing", 200),
        (["modifier-search", "prestige"], "/modifier-search?q=prestige", 200),
        (["modifier-search", "mult", "limit=1"], "/modifier-search?q=mult&limit=1", 200),
        (["script-args"], "/script-args", 200),
        (["script-args", "te_some_helper"], "/script-args/te_some_helper", 200),
        (["script-args", "te_missing"], "/script-args/te_missing", 404),
        (["modifier-grants", "country_prestige_mult"],
         "/modifier-grants/country_prestige_mult", 200),
        (["modifier-grants", "country_prestige_mult", "scope=mod"],
         "/modifier-grants/country_prestige_mult?scope=mod", 200),
        (["modifier-grants", "Not-Valid"], "/modifier-grants/Not-Valid", 400),
    ]

    def test_every_lookup_prints_the_bytes_the_server_sends(self):
        for argv, path, want_status in self.CASES:
            with self.subTest(argv=argv):
                self.assertEqual(query.build_request(["--offline", *argv]),
                                 (argv[0], path, True))
                body, status = served(path)
                self.assertEqual(status, want_status)
                printed, code, _err = run_cli(["--offline", *argv])
                self.assertEqual(printed, body)
                self.assertEqual(code, 0 if want_status == 200 else 1)

    def test_answers_carry_the_fixture_data(self):
        # The comparison above is only as good as what the fixture reaches.
        def answer(*argv):
            return json.loads(run_cli(["--offline", *argv])[0])

        self.assertEqual(answer("localize", "law_monarchy")["description"],
                         "Rule by a crowned head — not a café council.")
        self.assertEqual([r["id"] for r in answer("references", "law_anarchy")["Laws"]],
                         ["law_te_council"])
        self.assertEqual(answer("modifier-search", "prestige")["entity_count"], 2)
        self.assertEqual(answer("script-args")["flags"][0]["unknown"], ["EXTRA"])
        grants = answer("modifier-grants", "country_prestige_mult")
        self.assertEqual(sorted((g["origin"], g["entity_id"]) for g in grants["grants"]),
                         [("mod", "law_te_council"), ("vanilla", "law_monarchy")])
        # Non-ASCII loc goes out as UTF-8, not \\u escapes, as the server sends it.
        self.assertIn("Rätë".encode("utf-8"),
                      run_cli(["--offline", "localize", "law_te_council"])[0])

    def test_file_scan_lookups_do_not_build_a_mod_state(self):
        with mock.patch.object(mss, "ms", None), \
                mock.patch.object(mss, "cli_mod_state",
                                  side_effect=AssertionError("no ModState needed")):
            for argv in (["script-args"], ["modifier-grants", "country_prestige_mult"]):
                with self.subTest(argv=argv):
                    self.assertEqual(run_cli(["--offline", *argv])[1], 0)

    def test_mod_state_lookups_build_one_when_none_is_loaded(self):
        with mock.patch.object(mss, "ms", None), \
                mock.patch.object(mss, "cli_mod_state", return_value=self.state) as build:
            printed, code, _err = run_cli(["--offline", "localize", "law_anarchy"])
            build.assert_called_once_with()
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(printed), {"key": "law_anarchy", "name": "Anarchy"})


class UsageTests(unittest.TestCase):
    def test_bad_command_lines_exit_2_with_the_lookups_listed(self):
        for argv in ([], ["bogus"], ["localize"], ["localize", "a", "b"],
                     ["modifier-grants"], ["references", "=x"], ["-h"]):
            with self.subTest(argv=argv), \
                    mock.patch.object(query, "answer_offline",
                                      side_effect=AssertionError("must not answer")):
                printed, code, err = run_cli(argv)
                self.assertEqual(code, 2)
                self.assertEqual(printed, b"")
                for lookup in query.LOOKUPS:
                    self.assertIn(lookup, err)

    def test_the_issue_lookups_are_the_supported_ones(self):
        self.assertEqual(set(query.LOOKUPS), {
            "modifier-search", "localize", "references", "script-args", "modifier-grants"})

    def test_request_paths(self):
        self.assertEqual(query.build_request(["modifier-search", "goods_output"])[1],
                         "/modifier-search?q=goods_output")
        self.assertEqual(query.build_request(["script-args"])[1], "/script-args")
        self.assertEqual(
            query.build_request(["script-args", "include_reviewed=true"])[1],
            "/script-args?include_reviewed=true")
        self.assertEqual(
            query.build_request(["localize", "a/b c"])[1], "/localize/a%2Fb%20c")
        self.assertEqual(
            query.build_request(["modifier-grants", "x", "entity_types=Laws,PMs"])[1],
            "/modifier-grants/x?entity_types=Laws%2CPMs")


class LiveServerTests(unittest.TestCase):
    """A server is used only when its /status names this checkout."""

    @staticmethod
    def _status(payload):
        resp = mock.MagicMock()
        resp.__enter__.return_value.read.return_value = json.dumps(payload).encode()
        return resp

    def test_server_for_this_checkout(self):
        import path_constants

        here = path_constants.mod_path
        cases = [
            ({"mod_path": here}, "http://127.0.0.1:8950"),
            ({"mod_path": here + "/"}, "http://127.0.0.1:8950"),
            ({"mod_path": "/some/other/checkout"}, None),
            ({"status": "ok"}, None),
        ]
        for payload, want in cases:
            with self.subTest(payload=payload), \
                    mock.patch("urllib.request.urlopen", return_value=self._status(payload)):
                self.assertEqual(query.server_for_this_checkout(), want)
        for exc in (urllib.error.URLError("refused"), ConnectionResetError(),
                    http.client.BadStatusLine("SSH-2.0-OpenSSH"),
                    http.client.RemoteDisconnected("closed")):
            # Nothing listening, or something on :8950 that is not this server.
            with self.subTest(exc=exc), mock.patch("urllib.request.urlopen", side_effect=exc):
                self.assertIsNone(query.server_for_this_checkout())

    def test_uses_the_server_and_says_so(self):
        body = mss.json_body({"key": "k", "name": "K"})
        with mock.patch.object(query, "server_for_this_checkout",
                               return_value="http://127.0.0.1:8950"), \
                mock.patch.object(query, "fetch", return_value=(body, 200)) as fetch, \
                mock.patch.object(query, "answer_offline",
                                  side_effect=AssertionError("server is up")):
            printed, code, err = run_cli(["localize", "k"])
        fetch.assert_called_once_with("http://127.0.0.1:8950", "/localize/k")
        self.assertEqual((printed, code), (body, 0))
        self.assertIn("mod state server", err)

    def test_falls_back_offline_without_a_server_for_this_checkout(self):
        with mock.patch.object(query, "server_for_this_checkout", return_value=None), \
                mock.patch.object(query, "answer_offline",
                                  return_value=(b"{}", 200)) as offline:
            printed, code, err = run_cli(["references", "law_x"])
        offline.assert_called_once_with("/references/law_x", True)
        self.assertEqual((printed, code, err), (b"{}", 0, ""))

    def test_fetch_passes_endpoint_errors_through(self):
        error = urllib.error.HTTPError("http://x", 404, "Not Found", {},
                                       io.BytesIO(b'{"error": "nope"}'))
        with mock.patch("urllib.request.urlopen", side_effect=error):
            self.assertEqual(query.fetch("http://x", "/localize/k"), (b'{"error": "nope"}', 404))

    def test_a_server_that_goes_away_falls_back_offline(self):
        # Up for /status, gone (or not answering HTTP) for the lookup itself.
        for exc in (urllib.error.URLError("refused"), ConnectionResetError(),
                    http.client.RemoteDisconnected("closed")):
            with self.subTest(exc=exc), \
                    mock.patch.object(query, "server_for_this_checkout",
                                      return_value="http://127.0.0.1:8950"), \
                    mock.patch("urllib.request.urlopen", side_effect=exc), \
                    mock.patch.object(query, "answer_offline",
                                      return_value=(b"{}", 200)) as offline:
                printed, code, err = run_cli(["localize", "k"])
            offline.assert_called_once_with("/localize/k", True)
            self.assertEqual((printed, code), (b"{}", 0))
            self.assertIn("answering offline", err)
            self.assertNotIn("answered by the mod state server", err)


class UnserializableResultTests(unittest.TestCase):
    """A result json cannot encode is the 500 body do_GET gives any other
    failure, from the server and from the CLI alike."""

    def test_a_set_in_a_result_is_a_500_from_both(self):
        with mock.patch.object(mss.ModStateHandler, "route", return_value={"a": {1, 2}}), \
                mock.patch.object(query, "server_for_this_checkout",
                                  side_effect=AssertionError("--offline must not ask")), \
                self.assertLogs(mss.logger, level="ERROR") as logs:
            body, status = served("/script-args")
            printed, code, _err = run_cli(["--offline", "script-args"])
        self.assertEqual(status, 500)
        self.assertEqual(json.loads(body),
                         {"error": "TypeError: Object of type set is not JSON serializable"})
        self.assertEqual((printed, code), (body, 1))
        self.assertTrue(all("/script-args" in line for line in logs.output))


if __name__ == "__main__":
    unittest.main()
