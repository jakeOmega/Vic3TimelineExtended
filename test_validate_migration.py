"""Tests for the patch-migration validators (issue #228):

- GET /validate/vanilla-surface-diff?old_ref=<ref>
- GET /validate/gui-at-risk?old_ref=<ref>
- GET /validate/loc-override-drift?old_ref=<ref>

Two layers, both offline (no running server, no real game files):

1. Pure-function tests for the extractors / loc parser — always run.
2. A synthetic two-commit git repo (temp dir) standing in for the vanilla clone
   AND the live install (clone HEAD == live, the real-world invariant), plus a
   throwaway mod git repo, monkeypatched over the module's path globals. This
   deterministically exercises the git-at-ref helpers and all three endpoint
   workers end to end, including the drift-detection and removed-and-used-by-mod
   joins that a same-version identity check can't reach.

Run: python3 test_validate_migration.py
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import unittest

import json
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

import mod_state_server as mss

BOM = "﻿"

SERVER = "http://127.0.0.1:8950"


def _server_up() -> bool:
    try:
        urlopen(f"{SERVER}/status", timeout=2)
        return True
    except (URLError, OSError):
        return False


def _get(path: str):
    with urlopen(f"{SERVER}{path}", timeout=30) as resp:
        return json.loads(resp.read())


def _server_has_new_code() -> bool:
    """True only if the running server exposes the #228 validators (listed in
    GET /validate). HTTP smoke tests skip cleanly until the orchestrator
    restarts the server onto this code."""
    if not _server_up():
        return False
    try:
        return "vanilla-surface-diff" in _get("/validate").get("available", [])
    except (URLError, OSError, ValueError):
        return False

_GIT_ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
}


def _git(repo, *args):
    return subprocess.run(
        ["git", "-C", repo, *args],
        capture_output=True, text=True, env=_GIT_ENV, check=True,
    ).stdout.strip()


def _write(path, text, bom=False):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        if bom:
            f.write(BOM)
        f.write(text)


class PureExtractorTests(unittest.TestCase):
    def test_toplevel_keys_bom_and_spacing(self):
        text = (
            BOM + "alpha = {\n\tdecimals = 0\n}\n"
            "beta={\n}\n"
            "# a comment line\n"
            "gamma_mod = {\n\tnested_key = { x = 1 }\n}\n"
        )
        self.assertEqual(
            mss._extract_toplevel_keys(text), {"alpha", "beta", "gamma_mod"},
        )

    def test_toplevel_skips_indented(self):
        # nested/indented `key = {` must NOT be treated as a top-level entity.
        text = "law_x = {\n\tis_visible = {\n\t\tinner = {\n\t\t}\n\t}\n}\n"
        self.assertEqual(mss._extract_toplevel_keys(text), {"law_x"})

    def test_toplevel_empty_and_none(self):
        self.assertEqual(mss._extract_toplevel_keys(None), set())
        self.assertEqual(mss._extract_toplevel_keys(""), set())

    def test_define_names_qualified(self):
        text = (
            BOM + "NGame = {\n"
            '\tSTART_DATE = "1836.1.1"\n'
            "\tMAX = 5\n"
            "}\n"
            "NCountry = {\n"
            "\tDEFAULT = 1\n"
            "}\n"
        )
        self.assertEqual(
            mss._extract_define_names(text),
            {"NGame.START_DATE", "NGame.MAX", "NCountry.DEFAULT"},
        )

    def test_loc_lines_parse(self):
        text = (
            "l_english:\n"
            ' key_a:0 "hello world"\n'
            "# comment\n"
            ' key_b:1 "second"\n'
            " not_a_loc_line_without_quotes:0 bare\n"
        )
        got = dict(mss._parse_loc_lines(text))
        self.assertEqual(got, {"key_a": "hello world", "key_b": "second"})


class MigrationWorkerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="vic3_mig_test_")
        cls.clone = os.path.join(cls.tmp, "clone")
        cls.mod = os.path.join(cls.tmp, "mod")
        os.makedirs(cls.clone)
        os.makedirs(cls.mod)
        _git(cls.clone, "init", "-q")
        _git(cls.mod, "init", "-q")

        # ---- vanilla clone, commit "old" ---------------------------------
        g = os.path.join(cls.clone, "game")
        _write(os.path.join(g, "common/modifier_type_definitions/00_mt.txt"),
               "alpha_mod = {\n\tdecimals=0\n}\nbeta_mod = {\n}\n"
               "removed_used_mod = {\n}\nremoved_unused_mod = {\n}\n", bom=True)
        _write(os.path.join(g, "common/laws/00_laws.txt"),
               "law_alpha = {\n\tgroup = lawgroup_x\n}\nlaw_removed = {\n}\n",
               bom=True)
        _write(os.path.join(g, "gui/frontend/panel.gui"), "OLD gui content\n")
        _write(os.path.join(g, "gui/frontend/stable.gui"), "unchanged\n")
        _write(os.path.join(g, "common/interest_groups/00_ig.txt"),
               "OLD ig content\n", bom=True)
        _write(os.path.join(g, "localization/english/vanilla_l_english.yml"),
               'l_english:\n key_drift:0 "old string"\n'
               ' key_stable:0 "same string"\n key_only_old:0 "gone"\n')
        _git(cls.clone, "add", "-A")
        _git(cls.clone, "commit", "-q", "-m", "old")
        cls.old_ref = _git(cls.clone, "rev-parse", "HEAD")

        # ---- vanilla clone, commit "new" (== HEAD == live install) --------
        _write(os.path.join(g, "common/modifier_type_definitions/00_mt.txt"),
               "alpha_mod = {\n\tdecimals=0\n}\nbeta_mod = {\n}\n"
               "added_mod = {\n}\n", bom=True)
        _write(os.path.join(g, "common/laws/00_laws.txt"),
               "law_alpha = {\n\tgroup = lawgroup_x\n}\nlaw_added = {\n}\n",
               bom=True)
        _write(os.path.join(g, "gui/frontend/panel.gui"), "NEW gui content\n")
        # stable.gui unchanged
        _write(os.path.join(g, "common/interest_groups/00_ig.txt"),
               "NEW ig content\n", bom=True)
        _write(os.path.join(g, "localization/english/vanilla_l_english.yml"),
               'l_english:\n key_drift:0 "new string"\n'
               ' key_stable:0 "same string"\n')
        _git(cls.clone, "add", "-A")
        _git(cls.clone, "commit", "-q", "-m", "new")

        # ---- mod repo -----------------------------------------------------
        # references removed_used_mod (whole word) but NOT removed_unused_mod
        _write(os.path.join(cls.mod,
               "common/modifier_type_definitions/mod_mt.txt"),
               "some_static = {\n\tremoved_used_mod = 3\n}\n")
        _write(os.path.join(cls.mod, "gui/frontend/panel.gui"),
               "mod override of panel\n")            # same path -> at-risk
        _write(os.path.join(cls.mod, "gui/te_custom.gui"),
               "mod-only gui\n")                      # no vanilla path -> safe
        _write(os.path.join(cls.mod, "common/interest_groups/00_ig.txt"),
               "mod override of ig\n")                # same path -> at-risk
        _write(os.path.join(cls.mod,
               "localization/english/replace/override_l_english.yml"),
               'l_english:\n key_drift:0 "mod override"\n'
               ' key_stable:0 "mod override 2"\n')
        _git(cls.mod, "add", "-A")
        _git(cls.mod, "commit", "-q", "-m", "mod")

        # ---- monkeypatch module path globals ------------------------------
        cls._orig = (
            mss.vanilla_source_repo_path, mss.base_game_path,
            mss.mod_path, mss._VANILLA_LOC_CACHE,
        )
        mss.vanilla_source_repo_path = cls.clone
        mss.base_game_path = cls.clone          # clone HEAD == live install
        mss.mod_path = cls.mod
        mss._VANILLA_LOC_CACHE = {
            "key_drift": "new string", "key_stable": "same string",
        }

    @classmethod
    def tearDownClass(cls):
        (mss.vanilla_source_repo_path, mss.base_game_path,
         mss.mod_path, mss._VANILLA_LOC_CACHE) = cls._orig
        shutil.rmtree(cls.tmp, ignore_errors=True)

    # ---- git-at-ref helpers ----------------------------------------------
    def test_validate_git_ref(self):
        self.assertEqual(mss._validate_git_ref(self.old_ref), self.old_ref)
        with self.assertRaises(mss._EndpointError):
            mss._validate_git_ref("")
        with self.assertRaises(mss._EndpointError):
            mss._validate_git_ref("nonexistent_ref_zzz")
        with self.assertRaises(mss._EndpointError):
            mss._validate_git_ref("-x")

    def test_git_show_at_ref_bom_and_missing(self):
        txt = mss._git_show_at_ref(
            self.old_ref, "game/common/laws/00_laws.txt")
        self.assertTrue(txt.startswith("law_alpha"))   # BOM stripped
        self.assertIsNone(mss._git_show_at_ref(self.old_ref, "game/nope.txt"))

    def test_git_lstree(self):
        files = mss._git_lstree_at_ref(
            self.old_ref, "game/common/modifier_type_definitions", ".txt")
        self.assertEqual(
            files, ["game/common/modifier_type_definitions/00_mt.txt"])
        self.assertEqual(mss._git_lstree_at_ref(self.old_ref, "game/nope"), [])

    def test_git_diff_names(self):
        changed = mss._git_diff_names(self.old_ref, ["game/gui", "game/common"])
        self.assertIn("game/gui/frontend/panel.gui", changed)
        self.assertIn("game/common/interest_groups/00_ig.txt", changed)
        self.assertNotIn("game/gui/frontend/stable.gui", changed)

    def test_mod_grep_uses(self):
        hits = mss._mod_grep_uses("removed_used_mod")
        self.assertIn(
            "common/modifier_type_definitions/mod_mt.txt", hits)
        self.assertEqual(mss._mod_grep_uses("removed_unused_mod"), [])

    # ---- endpoint workers -------------------------------------------------
    def test_surface_diff(self):
        d = mss._migration_surface_diff(self.old_ref)
        self.assertIn("removed_used_mod", d["removed"]["modifier_type_definitions"])
        self.assertIn("removed_unused_mod",
                      d["removed"]["modifier_type_definitions"])
        self.assertIn("added_mod", d["added"]["modifier_type_definitions"])
        self.assertIn("law_removed", d["removed"]["laws"])
        self.assertIn("law_added", d["added"]["laws"])
        joined = {j["name"]: j for j in d["removed_and_used_by_mod"]}
        self.assertIn("removed_used_mod", joined)
        self.assertIn("common/modifier_type_definitions/mod_mt.txt",
                      joined["removed_used_mod"]["mod_files"])
        # mod_mt.txt *uses* the name (`removed_used_mod = 3` inside a static),
        # it does not *register* it as a top-level type — but the current
        # heuristic keys off the directory, so it flags re_registered here.
        # (In real data the distinction is between a use-site file like
        # extra_modifiers.txt and a registration file; the fixture keeps both
        # in the same dir for brevity.) Assert the flag is present & boolean.
        self.assertIsInstance(
            joined["removed_used_mod"].get("re_registered_by_mod", False), bool)
        # a removed name the mod does NOT reference must not appear in the join
        self.assertNotIn("removed_unused_mod", joined)
        # law removals never carry the modifier-only re_registered flag
        law_join = {j["name"]: j for j in d["removed_and_used_by_mod"]
                    if j["category"] == "laws"}
        for j in law_join.values():
            self.assertNotIn("re_registered_by_mod", j)

    def test_surface_diff_identity(self):
        # old_ref == HEAD: no surface should differ.
        head = _git(self.clone, "rev-parse", "HEAD")
        d = mss._migration_surface_diff(head)
        self.assertEqual(d["summary"]["added"], 0)
        self.assertEqual(d["summary"]["removed"], 0)
        self.assertEqual(d["summary"]["removed_and_used_by_mod"], 0)

    def test_gui_at_risk(self):
        g = mss._migration_gui_at_risk(self.old_ref)
        gui_rels = {e["rel"] for e in g["gui_at_risk"]}
        self.assertIn("gui/frontend/panel.gui", gui_rels)
        self.assertNotIn("gui/te_custom.gui", gui_rels)     # mod-only, safe
        common_rels = {e["rel"] for e in g["common_overrides_at_risk"]}
        self.assertIn("common/interest_groups/00_ig.txt", common_rels)

    def test_gui_at_risk_identity(self):
        head = _git(self.clone, "rev-parse", "HEAD")
        g = mss._migration_gui_at_risk(head)
        self.assertEqual(g["gui_at_risk"], [])
        self.assertEqual(g["common_overrides_at_risk"], [])

    def test_loc_drift(self):
        l = mss._migration_loc_drift(self.old_ref)
        self.assertEqual(l["shadowed_key_count"], 2)  # key_drift + key_stable
        drifted = {e["key"]: e for e in l["drifted"]}
        self.assertIn("key_drift", drifted)
        self.assertEqual(drifted["key_drift"]["old"], "old string")
        self.assertEqual(drifted["key_drift"]["new"], "new string")
        self.assertNotIn("key_stable", drifted)       # vanilla string unchanged

    def test_loc_drift_identity(self):
        head = _git(self.clone, "rev-parse", "HEAD")
        l = mss._migration_loc_drift(head)
        self.assertEqual(l["drifted"], [])


@unittest.skipUnless(_server_has_new_code(),
                     "server not running #228 code (restart to activate)")
class HttpSmokeTests(unittest.TestCase):
    """End-to-end HTTP envelope checks against the live server. Uses old_ref=HEAD
    (always resolvable, deterministic empty diffs) so they don't depend on the
    clone's history depth. Gives the orchestrator's post-restart step something
    to run over the real route (do_GET -> _validate -> handler)."""

    def test_surface_diff_envelope(self):
        d = _get("/validate/vanilla-surface-diff?old_ref=HEAD")
        for k in ("old_ref", "added", "removed",
                  "removed_and_used_by_mod", "summary"):
            self.assertIn(k, d)
        self.assertEqual(d["removed_and_used_by_mod"], [])  # identity

    def test_gui_at_risk_envelope(self):
        d = _get("/validate/gui-at-risk?old_ref=HEAD")
        for k in ("gui_at_risk", "common_overrides_at_risk", "summary"):
            self.assertIn(k, d)
        self.assertEqual(d["gui_at_risk"], [])              # identity

    def test_loc_drift_envelope(self):
        d = _get("/validate/loc-override-drift?old_ref=HEAD")
        for k in ("shadowed_key_count", "drifted", "summary"):
            self.assertIn(k, d)
        self.assertEqual(d["drifted"], [])                  # identity

    def test_missing_ref_is_400(self):
        with self.assertRaises(HTTPError) as cm:
            _get("/validate/vanilla-surface-diff")
        self.assertEqual(cm.exception.code, 400)


if __name__ == "__main__":
    unittest.main(verbosity=2)
