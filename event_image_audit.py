"""Parse-time audit: visible events with no event image (issue #353).

The default Vic3 event window has an image panel and no fallback art. An event
that renders in it without an `event_image` block draws the engine's missing-
texture placeholder — a flat magenta blob — and the engine says nothing: no
`error.log` line, no `debug.log` line, no parse warning. The only way to find
out is to see the event fire in a real game. `monument_events.3`-`.10` shipped
that way for eight days before a player screenshot surfaced it.

Vanilla is unanimous on this. Of its 2185 visible events, 153 carry no
`event_image` — and every one of those supplies art some other way, via a
`gui_window` whose layout has no image panel plus `left_icon` / `right_icon`
portraits (e.g. `acceptance_events.1` -> `event_window_1char_tabloid`). The
single exception across the whole base game is `test.120` in `test_events.txt`.
So "no image and no alternate window" is not a style choice the engine
tolerates; it is always a bug.

Rule: flag a mod-defined event that
  * is not `hidden = yes` (hidden events never render), and
  * has no `event_image` block, and
  * declares none of `gui_window` / `left_icon` / `right_icon`.

Scope / caveats:
- **Mod events only.** The audit walks `events/` under the mod root, so
  vanilla's `test.120` is out of scope by construction.
- **Plain definitions only** (`<id> = {`). A `REPLACE:` / `INJECT:` override of
  a vanilla event inherits whatever art the vanilla block declares, which this
  audit cannot see, so those are skipped.
- **Declaration, not resolution.** This checks that an event *declares* art, not
  that the texture or video file exists. A `texture` path typo still renders the
  same magenta blob. Resolving them needs the vanilla install for `.bk2` videos,
  which CI does not have — tracked separately.

Suppress an intentional flag with an inline `# REVIEWED YYYY-MM-DD: rationale`
comment on the event's opening `<id> = {` line.

Report: docs/engine/event_image_report.md. Registered in POST_LOAD_AUDITS.
"""

import os
import re
from dataclasses import dataclass, field

# A plain top-level event definition line: `<id> = {` (no merge prefix, so
# REPLACE:/INJECT: overrides of vanilla events are skipped).
_DEF_RE = re.compile(r"^[ \t]*([a-z_][a-z0-9_]*\.\d+)[ \t]*=[ \t]*\{", re.M)
_REVIEWED_RE = re.compile(
    r"#\s*REVIEWED\s+(?P<date>\d{4}-\d{2}-\d{2})\s*:\s*(?P<rationale>.+?)\s*$"
)

_HIDDEN_RE = re.compile(r"^[ \t]*hidden[ \t]*=[ \t]*yes\b", re.M)
_IMAGE_RE = re.compile(r"^[ \t]*event_image[ \t]*=", re.M)
# Art supplied some other way. `gui_window` selects a layout with no image
# panel; the icon keys fill the character portraits such layouts use instead.
_ALT_ART_RES = {
    "gui_window": re.compile(r"^[ \t]*gui_window[ \t]*=", re.M),
    "left_icon": re.compile(r"^[ \t]*left_icon[ \t]*=", re.M),
    "right_icon": re.compile(r"^[ \t]*right_icon[ \t]*=", re.M),
}


@dataclass
class ImageFlag:
    event_id: str
    file: str
    line: int
    exemption: dict | None = None


@dataclass
class AuditResult:
    flags: list[ImageFlag] = field(default_factory=list)
    coverage: dict = field(default_factory=dict)


def parse_reviewed_comment(comment: str | None) -> dict | None:
    if not comment:
        return None
    m = _REVIEWED_RE.search(comment)
    if not m:
        return None
    return {"date": m.group("date"), "rationale": m.group("rationale").strip()}


def _trailing_comment(line: str) -> str:
    idx = line.find("#")
    return line[idx:].rstrip("\n") if idx != -1 else ""


def _iter_txt(base: str):
    for dirpath, _dirs, files in os.walk(base):
        for f in sorted(files):
            if f.endswith(".txt"):
                yield os.path.join(dirpath, f)


def _match_block(text: str, brace_pos: int) -> int:
    """Given the index of an opening `{`, return the index just past its
    matching `}` (or len(text) if unbalanced)."""
    depth = 0
    i = brace_pos
    n = len(text)
    while i < n:
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i + 1
        i += 1
    return n


def audit(mod_path: str) -> AuditResult:
    events_dir = os.path.join(mod_path, "events")
    flags: list[ImageFlag] = []
    total = 0
    visible = 0
    alt_art = 0

    if not os.path.isdir(events_dir):
        return AuditResult(flags=[], coverage={})

    for path in _iter_txt(events_dir):
        try:
            with open(path, encoding="utf-8-sig", errors="replace") as fh:
                text = fh.read()
        except OSError:
            continue

        for m in _DEF_RE.finditer(text):
            eid = m.group(1)
            brace = text.index("{", m.start())
            block = text[brace:_match_block(text, brace)]
            total += 1

            if _HIDDEN_RE.search(block):
                continue  # hidden events never render a window
            visible += 1

            if _IMAGE_RE.search(block):
                continue
            if any(rx.search(block) for rx in _ALT_ART_RES.values()):
                alt_art += 1
                continue

            line_end = text.find("\n", m.start())
            def_line = text[m.start():line_end if line_end != -1 else len(text)]
            flags.append(
                ImageFlag(
                    event_id=eid,
                    file=path,
                    line=text.count("\n", 0, m.start()) + 1,
                    exemption=parse_reviewed_comment(_trailing_comment(def_line)),
                )
            )

    flags.sort(key=lambda f: (f.file, f.line))
    return AuditResult(
        flags=flags,
        coverage={
            "events_defined": total,
            "visible": visible,
            "alt_art": alt_art,
            "imageless": len(flags),
        },
    )


def render_report(result: AuditResult, mod_path: str = "") -> str:
    unreviewed = [f for f in result.flags if not f.exemption]
    exempted = [f for f in result.flags if f.exemption]
    cov = result.coverage

    out: list[str] = []
    out.append("# Event Image Report")
    out.append("")
    out.append(
        "Visible mod events that declare no `event_image` and no alternate art "
        "(`gui_window` / `left_icon` / `right_icon`). The default event window "
        "has no fallback art, so these render the engine's magenta missing-"
        "texture placeholder — silently, with no log line of any kind. Vanilla "
        "has exactly one such event across the whole base game (`test.120`)."
    )
    out.append("")
    out.append(f"- Events defined: **{cov.get('events_defined', 0)}**")
    out.append(f"- Visible (not `hidden = yes`): **{cov.get('visible', 0)}**")
    out.append(
        f"- Visible via alternate art (`gui_window` / icons): "
        f"**{cov.get('alt_art', 0)}**"
    )
    out.append(f"- Imageless (unreviewed): **{len(unreviewed)}**")
    out.append(f"- Imageless (REVIEWED-suppressed): **{len(exempted)}**")
    out.append("")

    def _loc(f: ImageFlag) -> str:
        rel = os.path.relpath(f.file, mod_path) if mod_path else f.file
        return f"{rel}:{f.line}"

    if unreviewed:
        out.append("## Unreviewed")
        out.append("")
        for f in unreviewed:
            out.append(f"- `{f.event_id}` — {_loc(f)}")
        out.append("")
        out.append(
            "Add an `event_image = { texture = \"gfx/event_pictures/<name>.dds\" }` "
            "or `{ video = \"<vanilla video>\" }` block (inventory in "
            "`docs/guides/event_creation_guide.md`), switch the event to a "
            "`gui_window` layout that needs no image, or add an inline "
            "`# REVIEWED YYYY-MM-DD: rationale` on its `<id> = {` line."
        )
        out.append("")
    else:
        out.append("No unreviewed imageless events. ✅")
        out.append("")

    if exempted:
        out.append("## REVIEWED-suppressed")
        out.append("")
        for f in exempted:
            ex = f.exemption or {}
            out.append(
                f"- `{f.event_id}` — {_loc(f)} "
                f"(REVIEWED {ex.get('date', '?')}: {ex.get('rationale', '')})"
            )
        out.append("")

    return "\n".join(out)


def regenerate(mod_state=None) -> dict:
    """POST_LOAD_GENERATORS entry point. Writes the event-image report.

    Purely file-based (art declarations are read from each event's own block),
    so `mod_state` is accepted for protocol compatibility but unused.
    """
    from path_constants import mod_path

    result = audit(mod_path)
    report = render_report(result, mod_path)
    out_path = os.path.join(mod_path, "docs", "engine", "event_image_report.md")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(report)

    return {
        "unreviewed": sum(1 for f in result.flags if not f.exemption),
        "exempted": sum(1 for f in result.flags if f.exemption),
        "visible": result.coverage.get("visible", 0),
        "path": out_path,
    }


if __name__ == "__main__":
    import sys

    from path_constants import mod_path as _mp

    res = audit(_mp)
    print(render_report(res, _mp))
    # --strict: CI mode. Exit 1 if any flag lacks a `# REVIEWED ...` exemption.
    if "--strict" in sys.argv:
        raise SystemExit(1 if any(not f.exemption for f in res.flags) else 0)
