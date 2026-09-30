#!/usr/bin/env python3
"""Offline lint for .gui edits, for GUI work done without the game.

The engine checks a .gui file only when it loads it, and it says little when
something is wrong: a misspelt property is ignored, a missing loc key shows as
a raw key, an unknown texture draws magenta. This lint catches what can be
checked from the repository alone, before a play-test.

    python3 scripts/analysis/check_gui_lint.py [--base origin/main] [files...]

With no files, it lints every gui/**/*.gui that differs from --base, plus
untracked ones. Run it from the checkout (or worktree) being linted.

ERROR (exit 1):
  - no UTF-8 BOM; unbalanced braces, quotes, [ ] or ( )
  - a bare loc key (text/tooltip = "key", or a quoted key argument of Localize,
    SelectLocalization, AddLocalizationIf, AddTextIf) in neither the mod's
    English loc nor vanilla's (vanilla_parsed/localization_english.json)
  - GetScriptedGui('x') with no scripted GUI x; GetPlayerJournalEntry('x') with
    no journal entry x; Concept('x', ..) or [concept_x] with no concept x
WARN:
  - "unproven": a widget type, property, blockoverride name, data function,
    .Method or texture path that no .gui on --base uses and no .gui here
    defines. Not necessarily wrong, but nothing in the mod has shown it works
    in game; prefer a proven equivalent, or check it in game.
  - ScriptValue('x') with no script value x in the mod or vanilla
  - a collapse flag (GetVariableSystem.Toggle) whose name does not say its
    default (_open: collapsed until opened; _closed: open until closed), or
    whose Exists() tests disagree with that default (gui_style_guide.md rule 7)
  - an added loc value that starts or ends with a literal \\n (rule 8), outside
    te_unused_l_english.yml
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys

IDENT_BRACE = re.compile(r"\b([A-Za-z_]\w*)\s*=\s*\{")
IDENT_PROP = re.compile(r"\b([A-Za-z_]\w*)[ \t]*=[ \t]*(?![ \t{])")
BLOCKOVERRIDE = re.compile(r'blockoverride\s+"(\w+)"')
BLOCKDEF = re.compile(r'\bblock\s+"(\w+)"')
TYPEDEF = re.compile(r"\btype\s+(\w+)\s*=\s*\w+")
TEXTURE = re.compile(r'"((?:gfx|fonts)/[^"\]\[]+?\.(?:dds|png|tga))"', re.I)
FUNC = re.compile(r"(?<![.\w])([A-Za-z_]\w*)\s*\(")
METHOD = re.compile(r"\.([A-Za-z_]\w*)")
LOC_LINE = re.compile(r'^\s*([\w.\-]+):\d*\s*"(.*)"\s*$')
LOC_CALL = re.compile(r"\b(Localize|SelectLocalization|AddLocalizationIf|AddTextIf)\(")
BARE_KEY = re.compile(r'\b(?:text|tooltip|raw_text|raw_tooltip)\s*=\s*"([A-Za-z][\w.\-]*)"')
ALWAYS_KNOWN = {"types", "template", "blockoverride", "block", "state", "on_start", "on_finish"}


def strip_comments(text):
    out = []
    for line in text.split("\n"):
        in_q = False
        cut = len(line)
        for i, ch in enumerate(line):
            if ch == '"':
                in_q = not in_q
            elif ch == "#" and not in_q:
                cut = i
                break
        out.append(line[:cut])
    return "\n".join(out)


def bracket_exprs(text):
    """The [..] data expressions in text, allowing one level of nesting."""
    return re.findall(r"\[([^\[\]]*(?:\[[^\[\]]*\][^\[\]]*)*)\]", text)


def loc_args(expr):
    """Loc keys passed as quoted arguments: Localize('k'), and the comma-led
    quoted arguments of SelectLocalization / AddLocalizationIf / AddTextIf
    (a quoted argument opening a call, such as ScriptValue('x'), is not one)."""
    keys = []
    for m in LOC_CALL.finditer(expr):
        depth, end = 1, len(expr)
        for j in range(m.end(), len(expr)):
            if expr[j] == "(":
                depth += 1
            elif expr[j] == ")":
                depth -= 1
                if depth == 0:
                    end = j
                    break
        span = expr[m.end():end]
        lead = r"^\s*" if m.group(1) == "Localize" else r",\s*"
        keys += [k for k in re.findall(lead + r"'([^'(][^']*)'", span) if re.fullmatch(r"[\w.\-]+", k)]
    return keys


def _read(path):
    with open(path, encoding="utf-8-sig", errors="replace") as f:
        return f.read()


class Linter:
    def __init__(self, repo, base):
        self.repo = repo
        self.base = base
        self.findings = []
        self._load()

    def git(self, *args):
        return subprocess.run(["git", "-C", self.repo, *args], capture_output=True, text=True,
                              errors="replace").stdout

    def _path(self, rel):
        return os.path.join(self.repo, rel)

    def _glob(self, pattern):
        return [os.path.relpath(p, self.repo) for p in glob.glob(self._path(pattern), recursive=True)]

    def _top_level_keys(self, pattern):
        keys = set()
        for p in self._glob(pattern):
            text = strip_comments(_read(self._path(p)))
            keys.update(re.findall(r"^(?:INJECT:|REPLACE:)?([\w.\-]+)\s*=", text, re.M))
        return keys

    def _vanilla(self, rel):
        try:
            with open(self._path(rel), encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return {}

    def _load(self):
        base_gui = [p for p in self.git("ls-tree", "-r", "--name-only", self.base, "gui/").split("\n")
                    if p.endswith(".gui")]
        base_gui_text = "\n".join(strip_comments(self.git("show", f"{self.base}:{p}")) for p in base_gui)
        self.base_gui_text = base_gui_text
        self.cur_gui_text = "\n".join(strip_comments(_read(self._path(p))) for p in self._glob("gui/**/*.gui"))
        base_other = "\n".join(
            self.git("show", f"{self.base}:{p}")
            for p in self.git("ls-tree", "-r", "--name-only", self.base, "common/", "localization/english/").split("\n")
            if p.endswith((".txt", ".yml")))
        self.tracked = set(self.git("ls-files").split("\n")) | set(
            self.git("ls-tree", "-r", "--name-only", self.base).split("\n"))

        self.known_brace = (set(IDENT_BRACE.findall(base_gui_text)) | set(TYPEDEF.findall(self.cur_gui_text))
                            | ALWAYS_KNOWN)
        self.known_prop = set(IDENT_PROP.findall(base_gui_text))
        self.known_blocks = set(BLOCKDEF.findall(self.cur_gui_text)) | set(BLOCKOVERRIDE.findall(base_gui_text))
        self.known_texture_text = base_gui_text + base_other
        exprs = " ".join(bracket_exprs(base_gui_text) + bracket_exprs(base_other))
        self.known_funcs = set(FUNC.findall(exprs))
        self.known_methods = set(METHOD.findall(re.sub(r"'[^']*'", "''", exprs)))

        self.mod_loc = {}
        for p in self._glob("localization/english/**/*.yml"):
            for line in _read(self._path(p)).split("\n"):
                m = LOC_LINE.match(line)
                if m:
                    self.mod_loc[m.group(1)] = m.group(2)
        self.vanilla_loc = self._vanilla("vanilla_parsed/localization_english.json")
        self.sguis = self._top_level_keys("common/scripted_guis/**/*.txt")
        self.svals = (self._top_level_keys("common/script_values/**/*.txt")
                      | set(self._vanilla("vanilla_parsed/common/script_values.json")))
        self.jes = (self._top_level_keys("common/journal_entries/**/*.txt")
                    | set(self._vanilla("vanilla_parsed/common/journal_entries.json")))
        self.concepts = (self._top_level_keys("common/game_concepts/**/*.txt")
                         | set(self._vanilla("vanilla_parsed/common/game_concepts.json")))

    def report(self, sev, path, line, msg):
        self.findings.append((sev, path, line, msg))

    def loc_exists(self, key):
        return key in self.mod_loc or key in self.vanilla_loc

    def changed_gui(self):
        diff = self.git("diff", "--name-only", self.base, "--", "gui/").split("\n")
        new = self.git("ls-files", "--others", "--exclude-standard", "gui/").split("\n")
        out = []
        for p in diff + new:
            if p.endswith(".gui") and os.path.exists(self._path(p)) and p not in out:
                out.append(p)
        return out

    def lint_expr(self, path, ln, expr):
        for f in FUNC.findall(expr):
            if f not in self.known_funcs:
                self.report("WARN", path, ln, f"unproven data function {f}(...)")
        for m in METHOD.findall(re.sub(r"'[^']*'", "''", expr)):
            if m not in self.known_methods:
                self.report("WARN", path, ln, f"unproven data method .{m}")
        for k in re.findall(r"GetScriptedGui\(\s*'(\w+)'", expr):
            if k not in self.sguis and f"'{k}'" not in self.base_gui_text:
                self.report("ERROR", path, ln, f"scripted GUI {k} is not defined in common/scripted_guis")
        for k in re.findall(r"ScriptValue\(\s*'(\w+)'", expr):
            if k not in self.svals:
                self.report("WARN", path, ln, f"script value {k} not found (mod or vanilla)")
        for k in re.findall(r"GetPlayerJournalEntry\(\s*'(\w+)'", expr):
            if k not in self.jes:
                self.report("ERROR", path, ln, f"journal entry {k} not found")
        if re.search(r"\.GetJournalEntry\(", expr):
            self.report("ERROR", path, ln, "another country's journal entry (.GetJournalEntry) failed in game: after a "
                        "const Get* promote it fails at load and crashed the panel, and through Access* promotes it "
                        "loads but silently keeps the parent's entry. Read that country's data through a Country datacontext instead, e.g. "
                        "datacontext = \"[MarketPanel.GetMarket.GetOwner]\"; GetPlayerJournalEntry is fine (gotcha #35)")
        for k in re.findall(r"Concept\(\s*'(\w+)'", expr):
            if k not in self.concepts:
                self.report("ERROR", path, ln, f"concept {k} is not defined")
        for k in loc_args(expr):
            if not self.loc_exists(k) and f"'{k}'" not in self.base_gui_text:
                self.report("ERROR", path, ln, f"loc key '{k}' is in neither mod nor vanilla loc")

    def lint_file(self, path):
        with open(self._path(path), "rb") as f:
            raw = f.read()
        if not raw.startswith(b"\xef\xbb\xbf"):
            self.report("ERROR", path, 1, "no UTF-8 BOM")
        text = strip_comments(raw.decode("utf-8-sig", errors="replace"))

        def lineno(i):
            return text.count("\n", 0, i) + 1

        depth = 0
        for i, line in enumerate(text.split("\n"), 1):
            if line.count('"') % 2:
                self.report("WARN", path, i, "odd number of quotes on the line (a string spanning lines?)")
            for s in re.findall(r'"([^"]*)"', line):
                if s.count("[") != s.count("]"):
                    self.report("ERROR", path, i, f"unbalanced [ ] in {s[:80]!r}")
                for e in bracket_exprs(s):
                    if e.count("(") != e.count(")"):
                        self.report("ERROR", path, i, f"unbalanced ( ) in [{e[:80]}]")
            bare = re.sub(r'"[^"]*"', "", line)
            depth += bare.count("{") - bare.count("}")
            if depth < 0:
                self.report("ERROR", path, i, "closing brace with no opener")
                depth = 0
        if text.count('"') % 2:
            self.report("ERROR", path, 1, "odd number of quotes in the file")
        if depth:
            self.report("ERROR", path, lineno(len(text)), f"{depth} unclosed brace(s) at the end of the file")

        nostr = re.sub(r'"[^"]*"', '""', text)
        for m in IDENT_BRACE.finditer(nostr):
            if m.group(1) not in self.known_brace:
                self.report("WARN", path, lineno(m.start()),
                            f"unproven widget or type '{m.group(1)}': no .gui on {self.base} uses it "
                            "and no type here defines it")
        for m in IDENT_PROP.finditer(nostr):
            if m.group(1) not in self.known_prop and m.group(1) not in self.known_brace:
                self.report("WARN", path, lineno(m.start()), f"unproven property '{m.group(1)}'")
        for m in BLOCKOVERRIDE.finditer(text):
            if m.group(1) not in self.known_blocks:
                self.report("WARN", path, lineno(m.start()),
                            f'blockoverride "{m.group(1)}" matches no block in any .gui here and no '
                            f"blockoverride on {self.base}")
        for m in TEXTURE.finditer(text):
            if m.group(1) not in self.tracked and m.group(1) not in self.known_texture_text:
                self.report("WARN", path, lineno(m.start()),
                            f"unproven texture {m.group(1)}: not in the mod, and no mod file on "
                            f"{self.base} names it")
        for m in re.finditer(r'"([^"]*)"', text):
            for e in bracket_exprs(m.group(1)):
                self.lint_expr(path, lineno(m.start()), e)
        for m in BARE_KEY.finditer(text):
            if "_" in m.group(1) and not self.loc_exists(m.group(1)) and f'"{m.group(1)}"' not in self.base_gui_text:
                self.report("ERROR", path, lineno(m.start()),
                            f"loc key '{m.group(1)}' is in neither mod nor vanilla loc")

        for flag in sorted(set(re.findall(r"GetVariableSystem\.Toggle\('(\w+)'\)", text))):
            if not re.search(r"_(open|closed)$", flag):
                self.report("WARN", path, 1, f"collapse flag {flag} should end _open (collapsed until "
                                             "opened) or _closed (open until closed): style rule 7")
                continue
            neg = len(re.findall(rf"Not\(\s*GetVariableSystem\.Exists\('{flag}'\)\s*\)", self.cur_gui_text))
            bare = len(re.findall(rf"GetVariableSystem\.Exists\('{flag}'\)", self.cur_gui_text)) - neg
            if flag.endswith("_closed") and bare != 1:
                self.report("WARN", path, 1, f"{flag} says open by default, but {bare} bare Exists() tests "
                                             "it (expected one: the show-more arrow)")
            if flag.endswith("_open") and neg != 1:
                self.report("WARN", path, 1, f"{flag} says collapsed by default, but {neg} Not(Exists()) "
                                             "test it (expected one: the show-more arrow)")

    def lint_added_loc(self):
        # te_unused holds keys nothing renders; organize_loc moving a key there
        # is not an added value.
        diff = self.git("diff", "-U0", self.base, "--", "localization/english/",
                        ":!localization/english/te_unused_l_english.yml")
        for line in diff.split("\n"):
            if not line.startswith("+") or line.startswith("+++"):
                continue
            m = LOC_LINE.match(line[1:])
            if not m:
                continue
            key, value = m.groups()
            if value.startswith("\\n") or value.endswith("\\n"):
                self.report("WARN", "loc", 0, f"{key}: value starts or ends with \\n (style rule 8)")
            if value.count("[") != value.count("]"):
                self.report("ERROR", "loc", 0, f"{key}: unbalanced [ ]")
            for c in re.findall(r"\[(concept_\w+)\]", value):
                if c not in self.concepts:
                    self.report("ERROR", "loc", 0, f"{key}: concept {c} is not defined")
            for e in bracket_exprs(value):
                if e.count("(") != e.count(")"):
                    self.report("ERROR", "loc", 0, f"{key}: unbalanced ( ) in [{e[:80]}]")
                for k in re.findall(r"GetScriptedGui\(\s*'(\w+)'", e):
                    if k not in self.sguis:
                        self.report("ERROR", "loc", 0, f"{key}: scripted GUI {k} is not defined")
                for k in re.findall(r"Concept\(\s*'(\w+)'", e):
                    if k not in self.concepts:
                        self.report("ERROR", "loc", 0, f"{key}: concept {k} is not defined")
                for k in re.findall(r"ScriptValue\(\s*'(\w+)'", e):
                    if k not in self.svals:
                        self.report("WARN", "loc", 0, f"{key}: script value {k} not found (mod or vanilla)")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--base", default="origin/main", help="the git ref whose .gui files count as proven")
    ap.add_argument("files", nargs="*", help=".gui files, relative to the repository root")
    args = ap.parse_args(argv)
    repo = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip()
    if not repo:
        print("not inside a git checkout", file=sys.stderr)
        return 2
    linter = Linter(repo, args.base)
    files = args.files or linter.changed_gui()
    for f in files:
        linter.lint_file(f)
    linter.lint_added_loc()
    for sev, path, line, msg in linter.findings:
        print(f"{sev} {path}:{line}: {msg}")
    errors = sum(1 for f in linter.findings if f[0] == "ERROR")
    print(f"\n{len(files)} .gui file(s) checked: {errors} error(s), {len(linter.findings) - errors} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
