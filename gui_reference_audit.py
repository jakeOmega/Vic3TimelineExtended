"""Offline cross-reference audit for every mod GUI and journal-entry widget mount.

No .gui parser or game install is required. Missing mod-only scripted GUIs,
invalid mounts, BOM/brace errors and duplicate visible properties are errors.
Lookups that could belong to vanilla warn when that category is unavailable.
A configured VIC3_BASE_GAME (install root or game directory) supplies vanilla;
the committed script-values/localization snapshots also supply those categories.
CLI prints only; regenerate() writes docs/engine/gui_reference_report.md.
"""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

BOM = b"\xef\xbb\xbf"
IDENT = r"[A-Za-z_][\w.\-]*"
LEX = re.compile(r'"(?:\\.|[^"\\])*"|#[^\n]*', re.S)
OPEN = re.compile(rf"({IDENT})\s*=\s*\{{")
CALLS = {
    "scripted_guis": "GetScriptedGui",
    "script_values": "ScriptValue",
    "custom_loc": "GetCustom",
    "static_modifiers": "GetStaticModifier",
    "loc_keys": "Localize",
}
# Inherited calls in overridden vanilla panels, absent from the mod. These
# remain UNRESOLVED warnings offline, not assumed resolved or exemptions;
# a live vanilla scripted_guis directory must actually define them.
VANILLA_SCRIPTED_GUIS = {
    "debug_kill_character_sgui",
    "debug_movement_activism_up_sgui",
    "debug_movement_activism_down_sgui",
    "je_meiji_restoration_get_faction_sgui",
}
DIRS = {
    "scripted_guis": "scripted_guis",
    "script_values": "script_values",
    "custom_loc": "customizable_localization",
    "static_modifiers": "static_modifiers",
}
# Engine primitives and compound-valued properties, not user-defined types.
BUILTINS = set("""types widget container flowcontainer hbox vbox button icon textbox
text_single text_multi progressbar scrollarea scrollbar item blockoverride block
tooltipwidget background modify_texture state animation dynamicgridbox fixedgridbox
overlappingitembox expand margin_widget window datamodel axis_label glow scrollwidget
soundparam start_sound attachto editbox checkbutton piechart plotline divider dropdown
list drag_drop_target margin minimumsize maximumsize spriteborder framesize bezier
uv_scale translate_uv portrait_button cursorposition color size position resizeparent
layer alpha blend_mode cliprect layoutpolicy texture uv_offset font fontsize
on_start on_finish sound stop_sound datacontext""".split())


def masks(text: str) -> tuple[str, str]:
    """Comment-free text and syntax-only text; preserve offsets/newlines.

    Quoted hashes/braces (including escaped quotes and multiline strings) are
    never comments or structure. Both masks retain source line numbers.
    """
    def blank(value):
        return re.sub(r"[^\n]", " ", value)
    code = LEX.sub(lambda m: blank(m[0]) if m[0].startswith("#") else m[0], text)
    syntax = LEX.sub(lambda m: blank(m[0]), text)
    return code, syntax


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def blocks(syntax: str):
    """Yield direct assignment blocks (name, opening offset, body start/end).

    Skipping each balanced body avoids treating a nested key as a definition.
    The caller can recurse into a body explicitly (is_shown, saved_scopes).
    """
    pos = 0
    while m := OPEN.search(syntax, pos):
        depth, end = 1, m.end()
        while end < len(syntax) and depth:
            depth += {"{": 1, "}": -1}.get(syntax[end], 0)
            end += 1
        yield m[1].removeprefix("INJECT:").removeprefix("REPLACE:"), m.start(), m.end(), end - 1
        pos = end


def gui_names(text: str) -> set[str]:
    code, syntax = masks(text)
    names = set(re.findall(rf"\b(?:type|template)\s+({IDENT})", syntax))
    # Only root widget names, not arbitrary name properties inside controls.
    for _, _, start, end in blocks(syntax):
        body = code[start:end]
        inner = masks(body)[1]
        for _, opening, _, stop in blocks(inner):
            body = body[:opening] + re.sub(r"[^\n]", " ", body[opening:stop + 1]) + body[stop + 1:]
        names.update(re.findall(r'\bname\s*=\s*"([^"\n]+)"', body))
    return names


@dataclass
class Flag:
    file: str
    line: int
    kind: str
    name: str
    severity: str
    detail: str


@dataclass
class AuditResult:
    flags: list[Flag] = field(default_factory=list)
    references: dict[str, dict[str, list[dict]]] = field(default_factory=dict)
    files_audited: int = 0

    @property
    def errors(self):
        return sum(f.severity == "error" for f in self.flags)


class Index:
    def __init__(self, root: Path, vanilla: Path | None = None):
        self.root = root
        self.vanilla = vanilla
        if vanilla and (vanilla / "game").is_dir():
            self.vanilla = vanilla / "game"
        self.keys = {kind: set() for kind in (*DIRS, "loc_keys", "gui_types")}
        self.complete = {kind: False for kind in self.keys}
        self.complete["custom_loc"] = True  # mod-only custom localization contract
        self.saved = {}
        self.shown = []
        self.gui_files = {}
        for base in (self.vanilla, root):  # mod definitions override vanilla
            if base is None:
                continue
            for kind, directory in DIRS.items():
                folder = base / "common" / directory
                if base == self.vanilla and folder.is_dir():
                    self.complete[kind] = True
                for path in sorted(folder.rglob("*.txt")):
                    text = read(path)
                    code, syntax = masks(text)
                    # Scalars count too: foo = 1 is a script-value definition.
                    depth = 0
                    for token in re.finditer(rf"[{{}}]|(?:INJECT:|REPLACE:)?({IDENT})\s*=", syntax):
                        if token[0] == "{":
                            depth += 1
                        elif token[0] == "}":
                            depth -= 1
                        elif depth == 0:
                            self.keys[kind].add(token[1])
                    if kind == "scripted_guis":
                        for name, opening, start, end in blocks(syntax):
                            saved, shown = set(), ""
                            for child, _, a, b in blocks(syntax[start:end]):
                                if child == "saved_scopes":
                                    saved.update(re.findall(IDENT, code[start + a:start + b]))
                                elif child == "is_shown":
                                    shown = syntax[start + a:start + b]
                            self.saved[name] = saved
                            reads = [s for s in sorted(saved) if re.search(r"\bscope:" + re.escape(s) + r"\b", shown)]
                            if reads and base == root:
                                self.shown.append((str(path.relative_to(root)), syntax.count("\n", 0, opening) + 1, name, reads))
            loc_dir = base / "localization" / "english"
            if base == self.vanilla and loc_dir.is_dir():
                self.complete["loc_keys"] = True
            for path in sorted(loc_dir.rglob("*.yml")):
                self.keys["loc_keys"].update(re.findall(r'^\s*([\w.\-]+):\d*\s*"', read(path), re.M))
            gui_dir = base / "gui"
            if base == self.vanilla and gui_dir.is_dir():
                self.complete["gui_types"] = True
            for path in sorted(gui_dir.rglob("*.gui")):
                text = read(path)
                self.keys["gui_types"].update(re.findall(rf"\b(?:type|template)\s+({IDENT})", masks(text)[1]))
                self.gui_files[str(path.relative_to(base))] = gui_names(text)
        for kind, rel in (("script_values", "common/script_values.json"),
                          ("static_modifiers", "common/modifiers.json"),
                          ("loc_keys", "localization_english.json")):
            path = root / "vanilla_parsed" / rel
            if path.is_file():
                data = json.loads(path.read_text(encoding="utf-8"))
                self.keys[kind].update(data)
                self.complete[kind] = True


def scripted_call_scopes(expr: str):
    """Bind scopes to the literal receiver of each method call in an expression.

    Keep separate receivers separate even inside Concatenate/Select strings.
    Quotes in fixed-point literals do not affect parenthesis matching.
    """
    pattern = re.compile(r"GetScriptedGui\(\s*'([^']+)'\s*\)\s*\.\w+\s*\(")
    for call in pattern.finditer(expr):
        depth, end = 1, call.end()
        quoted = False
        while end < len(expr) and depth:
            char = expr[end]
            if char == "'":
                quoted = not quoted
            elif not quoted:
                depth += {"(": 1, ")": -1}.get(char, 0)
            end += 1
        for scope in re.finditer(r"\bAddScope\(\s*'([^']+)'", expr[call.end():end]):
            yield call[1], scope[1], call.end() + scope.start()


def configured_vanilla() -> Path | None:
    import path_constants
    try:
        path = Path(path_constants.base_game_path)
    except RuntimeError:
        return None
    return path if path.is_dir() else None


def audit(mod_path: str | Path | None = None, vanilla_path: str | Path | None = None) -> AuditResult:
    root = Path(mod_path) if mod_path is not None else Path(__file__).resolve().parent
    index = Index(root, Path(vanilla_path) if vanilla_path is not None else configured_vanilla())
    result = AuditResult()

    def flag(file, line, kind, name, severity, detail):
        result.flags.append(Flag(file, line, kind, name, severity, detail))

    def reference(file, line, kind, name):
        resolved = name in index.keys[kind]
        result.references[file].setdefault(kind, []).append({"name": name, "line": line, "resolved": resolved})
        if not resolved:
            complete = index.complete[kind] or (kind == "scripted_guis" and name not in VANILLA_SCRIPTED_GUIS)
            severity = "error" if complete else "warn"
            flag(file, line, kind, name, severity, "unresolved" if severity == "error" else "unresolved; vanilla category unavailable")

    for path in sorted((root / "gui").rglob("*.gui")):
        file = str(path.relative_to(root))
        result.files_audited += 1
        result.references[file] = {kind: [] for kind in CALLS}
        raw = path.read_bytes()
        if not raw.startswith(BOM):
            flag(file, 1, "bom", "UTF-8 BOM", "error", "missing")
        text = raw.decode("utf-8-sig")
        code, syntax = masks(text)
        def line(offset):
            return text.count("\n", 0, offset) + 1
        # Track properties per actual brace block, including inline blocks.
        stack = [False]
        for m in re.finditer(r"[{}]|\bvisible\s*=", syntax):
            if m[0] == "{":
                stack.append(False)
            elif m[0] == "}":
                if len(stack) == 1:
                    flag(file, line(m.start()), "braces", "}", "error", "closing brace without opener")
                else:
                    stack.pop()
            else:
                if stack[-1]:
                    flag(file, line(m.start()), "duplicate_visible", "visible", "error", "second property in the same block")
                stack[-1] = True
        if len(stack) > 1:
            flag(file, line(len(text)), "braces", "{", "error", f"{len(stack) - 1} unclosed blocks")
        for kind, call in CALLS.items():
            for m in re.finditer(rf"\b{call}\(\s*'([^']+)'\s*\)", code):
                reference(file, line(m.start()), kind, m[1])
        for m in re.finditer(r'\b(?:text|tooltip|default_format|header|desc)\s*=\s*"([A-Za-z_][\w.\-]*)"', code):
            reference(file, line(m.start()), "loc_keys", m[1])
        # Only actual widget instances and inheritance bases, outside strings.
        for m in re.finditer(rf"\b({IDENT})\s*=\s*\{{|\btype\s+{IDENT}\s*=\s*({IDENT})", syntax):
            name = m[1] or m[2]
            if name not in BUILTINS:
                reference(file, line(m.start()), "gui_types", name)
        # Literal GetScriptedGui calls bind scopes exactly. ScriptedGui via a
        # type's overridable datacontext cannot be statically bound: warn only.
        for string in re.finditer(r'"(?:\\.|[^"\\])*"', code, re.S):
            expr = string[0]
            scopes = list(re.finditer(r"\bAddScope\(\s*'([^']+)'", expr))
            if not scopes:
                continue
            bound = set()
            for name, scope, offset in scripted_call_scopes(expr):
                bound.add(offset)
                if name in index.saved and scope not in index.saved[name]:
                    flag(file, line(string.start() + offset), "saved_scopes", scope, "error", f"not declared by {name}")
            if "ScriptedGui." in expr:
                for scope in scopes:
                    if scope.start() not in bound:
                        flag(file, line(string.start() + scope.start()), "saved_scopes", scope[1], "warn", "dynamic ScriptedGui datacontext; binding needs review")
    # Mounts refer to names in this exact file, not the global type registry.
    for path in sorted((root / "common/journal_entries").rglob("*.txt")):
        text = read(path)
        code, syntax = masks(text)
        for m in re.finditer(r"\bwidget\s*=\s*\{", syntax):
            depth, end = 1, m.end()
            while end < len(syntax) and depth:
                depth += {"{": 1, "}": -1}.get(syntax[end], 0)
                end += 1
            body = code[m.end():end - 1]
            fields = dict(re.findall(r'\b(gui|name)\s*=\s*"([^"\n]+)"', body))
            file, ln = str(path.relative_to(root)), text.count("\n", 0, m.start()) + 1
            gui, name = fields.get("gui"), fields.get("name")
            if not gui or not name:
                flag(file, ln, "mount", gui or name or "widget", "error", "mount needs quoted gui and name")
            elif gui not in index.gui_files:
                flag(file, ln, "mount", gui, "error", "GUI file does not exist")
            elif name not in index.gui_files[gui]:
                flag(file, ln, "mount", name, "error", f"no named root widget/type in {gui}")
    for file, ln, name, scopes in index.shown:
        flag(file, ln, "is_shown_scope", name, "warn", f"is_shown reads saved scopes {', '.join(scopes)}; verify visibility context (gotcha #22)")
    return result


def render_report(result: AuditResult) -> str:
    lines = ["# GUI reference audit report", "", "Generated by `gui_reference_audit.py`; do not hand-edit.", "",
             "Missing vanilla categories and dynamic saved-scope bindings are warnings.",
             "`--strict` fails only on errors. The CLI does not write this report.", ""]
    for severity, heading in (("error", "Errors"), ("warn", "Warnings")):
        lines += [f"## {heading}", ""]
        entries = [f for f in result.flags if f.severity == severity]
        if not entries:
            lines += ["_None._", ""]
        else:
            # Group repeats without losing source locations or names.
            groups = {}
            for f in entries:
                groups.setdefault((f.file, f.kind, f.name, f.detail), []).append(f.line)
            for (file, kind, name, detail), locations in groups.items():
                nums = ", ".join(map(str, sorted(set(locations))))
                lines.append(f"- `{file}` lines {nums}: **{kind}** `{name}` — {detail}")
            lines.append("")
    lines += [f"Errors: {result.errors}; warnings: {len(result.flags) - result.errors}.", ""]
    return "\n".join(lines)


def regenerate(mod_state) -> dict:
    # Use the same raw-source scanner as CI; no dependency on parsed .gui data.
    import path_constants
    result = audit(path_constants.mod_path)
    out = Path(path_constants.mod_path) / "docs/engine/gui_reference_report.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_report(result), encoding="utf-8")
    return {"files_audited": result.files_audited, "unreviewed": result.errors,
            "warnings": len(result.flags) - result.errors, "total_flags": len(result.flags)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--mod-path", type=Path)
    parser.add_argument("--vanilla-path", type=Path)
    args = parser.parse_args(argv)
    result = audit(args.mod_path, args.vanilla_path)
    print(render_report(result))
    return int(args.strict and result.errors > 0)


if __name__ == "__main__":
    raise SystemExit(main())
