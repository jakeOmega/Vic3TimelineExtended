"""Detects engine-invalid `attitude = <key>` values in mod script.

Background: The `has_attitude` / `any_attitude` triggers (and the standalone
AI `attitude = X` preference lines in diplomatic actions / AI strategies)
accept ONLY the fixed set of attitude keys the engine defines. An unknown key
(e.g. the legacy `friendly` / `hostile` names that predate the current
taxonomy) is *silently ignored* — the trigger simply never matches, so an AI
`evaluation_chance` weight or a refusal gate keyed on it becomes dead code.
The Clausewitz engine emits no parse-time warning, so these rot unnoticed.

This audit scans every mod `.txt` under `common/` and `events/` for
`attitude = <bareword>` and validates the value against the canonical 15-key
catalog below. Block-form `attitude = { ... }` (attitude *definitions*, not
references) is skipped because the character after `=` is `{`, not a bareword.
Content after a `#` comment marker is ignored, so commented-out script and the
`# REVIEWED` suppression tail never produce false positives.

The 15 keys are grouped exactly as the game groups them:
  Positive     — conciliatory, cooperative, genial, protective
  Negative     — wary, antagonistic, belligerent, domineering
  Neutral      — cautious, disinterested, human
  Subject-only — loyal, aloof, defiant, rebellious

Suppress an intentional/known-good deviation with a trailing comment on the
offending line (the engine ignores everything after `#` on a script line):

    ... attitude = somekey   # REVIEWED YYYY-MM-DD: rationale

Usage:
  * Standalone:  `python3 attitude_key_audit.py`  (pure file scan, no ModState;
    exits nonzero if any unreviewed invalid key is found).
  * Post-load:   registered in `mod_state_server.py` POST_LOAD_AUDITS; the
    server calls `regenerate(mod_state)` on every `POST /reload`, which writes
    `docs/engine/attitude_key_report.md` and returns a summary dict whose
    `unreviewed` count drives the reload `warnings` array.
"""
import os
import re
from dataclasses import dataclass, field


# Canonical engine attitude keys. Anything else in an `attitude = <key>`
# position is silently inert in-engine.
ATTITUDE_KEYS = frozenset({
    # Positive
    "conciliatory", "cooperative", "genial", "protective",
    # Negative
    "wary", "antagonistic", "belligerent", "domineering",
    # Neutral
    "cautious", "disinterested", "human",
    # Subject-only
    "loyal", "aloof", "defiant", "rebellious",
})


@dataclass
class AttitudeFlag:
    file: str
    line: int
    key: str
    exemption: dict | None = None


@dataclass
class AuditResult:
    flags: list[AttitudeFlag] = field(default_factory=list)
    files_scanned: int = 0
    refs_checked: int = 0


# `attitude = <bareword>`. The leading word boundary skips the `attitude`
# inside `has_attitude`/`any_attitude` (preceded by `_`, so no boundary),
# matching only the value-position token. Block form `attitude = {` never
# matches because `{` is not in the bareword class.
_ATTITUDE_RE = re.compile(r"\battitude\s*=\s*([A-Za-z_][A-Za-z0-9_]*)")
_REVIEWED_RE = re.compile(
    r"#\s*REVIEWED\s+(?P<date>\d{4}-\d{2}-\d{2})\s*:\s*(?P<rationale>.+?)\s*$"
)

# Mod script roots that carry `attitude = ...` references.
_SCAN_SUBDIRS = ("common", "events")


def _parse_reviewed(comment: str | None) -> dict | None:
    if not comment:
        return None
    m = _REVIEWED_RE.search(comment)
    if not m:
        return None
    return {"date": m.group("date"), "rationale": m.group("rationale").strip()}


def audit(mod_path: str | None = None) -> AuditResult:
    """Scan the mod tree for invalid `attitude = <key>` values.

    Pure file scan — takes no ModState (the catalog is a module constant), so
    it runs in well under a second and is safe to call from `main()` without
    the ~90s server bootstrap.
    """
    if mod_path is None:
        from path_constants import mod_path as _default
        mod_path = _default

    flags: list[AttitudeFlag] = []
    files_scanned = 0
    refs_checked = 0

    for subdir in _SCAN_SUBDIRS:
        base = os.path.join(mod_path, subdir)
        if not os.path.isdir(base):
            continue
        for root, _dirs, files in os.walk(base):
            for fname in sorted(files):
                if not fname.endswith(".txt"):
                    continue
                abs_p = os.path.join(root, fname)
                rel_p = os.path.relpath(abs_p, mod_path)
                files_scanned += 1
                try:
                    with open(abs_p, encoding="utf-8-sig", errors="replace") as fh:
                        for i, raw in enumerate(fh, start=1):
                            line = raw.rstrip("\n")
                            # Split off any comment so commented-out script and
                            # the `# REVIEWED` tail can't produce false hits.
                            code, sep, comment = line.partition("#")
                            for m in _ATTITUDE_RE.finditer(code):
                                key = m.group(1)
                                refs_checked += 1
                                if key in ATTITUDE_KEYS:
                                    continue
                                # `sep` is the stripped `#`; feed it back so
                                # `_REVIEWED_RE`'s `#` anchor matches.
                                exemption = _parse_reviewed(sep + comment) if sep else None
                                flags.append(AttitudeFlag(
                                    file=rel_p,
                                    line=i,
                                    key=key,
                                    exemption=exemption,
                                ))
                except OSError:
                    pass

    return AuditResult(
        flags=flags,
        files_scanned=files_scanned,
        refs_checked=refs_checked,
    )


def render_report(result: AuditResult) -> str:
    unrev = [f for f in result.flags if not f.exemption]
    exemp = [f for f in result.flags if f.exemption]

    out = [
        "# Attitude key audit report",
        "",
        "Auto-generated by `attitude_key_audit.py` on every full",
        "`POST /reload` of the mod state server. Do not hand-edit.",
        "",
        "Flagged: a script line contains `attitude = <key>` whose value is not",
        "one of the 15 engine attitude keys. The `has_attitude` / `any_attitude`",
        "triggers (and standalone AI `attitude = X` preference lines) silently",
        "never match an unknown key, turning the surrounding AI weight or gate",
        "into dead code with no parse-time warning.",
        "",
        "Valid keys — Positive: conciliatory, cooperative, genial, protective;",
        "Negative: wary, antagonistic, belligerent, domineering; Neutral:",
        "cautious, disinterested, human; Subject-only: loyal, aloof, defiant,",
        "rebellious.",
        "",
        "Suppress an intentional deviation with a trailing comment on the line:",
        "`... attitude = somekey   # REVIEWED YYYY-MM-DD: rationale`",
        "",
        "## Unreviewed Flags",
        "",
    ]
    if not unrev:
        out.append("_None._")
        out.append("")
    else:
        # Group by bad key so one legacy name across many sites collapses.
        by_key: dict[str, list[AttitudeFlag]] = {}
        for f in unrev:
            by_key.setdefault(f.key, []).append(f)
        for key in sorted(by_key):
            entries = by_key[key]
            out.append(f"### `attitude = {key}` ({len(entries)})")
            out.append("")
            for f in entries:
                out.append(f"- `{f.file}:{f.line}`")
            out.append("")

    out.append("## Reviewed Exemptions")
    out.append("")
    if not exemp:
        out.append("_None._")
        out.append("")
    else:
        for f in exemp:
            out.append(
                f"- `{f.file}:{f.line}` — `attitude = {f.key}` — "
                f"**{f.exemption['date']}**: {f.exemption['rationale']}"
            )
        out.append("")

    out.append("## Coverage")
    out.append("")
    out.append(f"- script files scanned: {result.files_scanned}")
    out.append(f"- attitude references checked: {result.refs_checked}")
    out.append(f"- valid catalog keys: {len(ATTITUDE_KEYS)}")
    out.append(f"- total flags: {len(result.flags)}")
    out.append(f"- unreviewed: {len(unrev)}")
    out.append(f"- exempted: {len(exemp)}")
    out.append("")

    return "\n".join(out) + "\n"


def regenerate(mod_state) -> dict:
    """POST_LOAD_GENERATORS hook: run the audit and write the report.

    `mod_state` is accepted for signature parity with the other post-load
    audits but is unused — the scan is pure filesystem + module constant.
    """
    from path_constants import mod_path
    result = audit(mod_path=mod_path)
    report = render_report(result)
    out_path = os.path.join(mod_path, "docs", "engine", "attitude_key_report.md")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(report)
    unrev = sum(1 for f in result.flags if not f.exemption)
    exemp = sum(1 for f in result.flags if f.exemption)
    return {
        "files_scanned": result.files_scanned,
        "refs_checked": result.refs_checked,
        "catalog_keys": len(ATTITUDE_KEYS),
        "total_flags": len(result.flags),
        "unreviewed": unrev,
        "exempted": exemp,
    }


def main() -> int:
    """Standalone entry: pure file scan, print the report, exit nonzero if any
    unreviewed invalid key is found. Does NOT build ModState."""
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from path_constants import mod_path
    result = audit(mod_path=mod_path)
    print(render_report(result))
    return 1 if any(not f.exemption for f in result.flags) else 0


if __name__ == "__main__":
    raise SystemExit(main())
