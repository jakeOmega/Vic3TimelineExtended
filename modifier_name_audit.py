"""Flag a modifier whose name reads as a paragraph, a sentence, or carries a figure (2026-11-15).

A modifier type's name is the label the engine prints beside its value, in
every tooltip that lists modifiers: "+20% Company Throughput Bonus", "-25%
Greenhouse Gas Emissions". The value is the engine's, formatted and colored
from the type's definition; the name says only what the value is of. The
detail goes in the type's `_desc`, which the player reads on hover, and the
rules a player plans around go in a concept the name or the desc links
(`[concept_greenhouse_gas_emissions]`, `[concept_company_charter]`).

The Monetary Union principle broke all three (owner, 2026-11-15, with
screenshots of Companies V and Environmental Sustainability V beside it):
five script-only booleans whose names were the tier's terms written out, up to
389 characters with the figures typed into the text ("adopters get #G +5%#!
export and import advantage and #G +2%#! ..."), and a leader's line named
"Seigniorage at Full Reach, of GDP a Year, before Minting Bonuses". A figure
typed into a name is never formatted, colored or scaled by the engine, and
nothing ties it to the script value it describes. The fix made each figure a
numeric display field and each name a label; this audit keeps it that way.

What is checked
---------------
Every modifier type the mod defines (`common/modifier_type_definitions/`,
`REPLACE:` and `INJECT:` included) and every static modifier
(`common/static_modifiers/`), by the name its loc key gives in the mod's
English loc (`localization/english/`, `replace/` winning,
`te_unused_l_english.yml` skipped). A key with no mod loc is skipped: a
missing name is `loc_coverage_audit`'s. The name is measured as rendered, by
`long_tooltip_audit.rendered_text`: `$key$` splices expanded (mod, then
vanilla from `vanilla_parsed/`), each `[...]` and text icon one character,
format codes none.

- `long`: over `MAX_NAME` (70) rendered characters. Vanilla's longest
  modifier type name is 66 characters (1,486 named types, median 22); the
  mod's were at most 61 before the Monetary Union's, its 99th percentile 54,
  and its static modifiers' longest 56.
- `sentence`: a sentence break (a word of three letters or more, or a closing
  bracket, then `.`, `!` or `?` and more text), a `;`, or a closing `.`. A
  name is a noun phrase; "St." and "U.S." pass.
- `figure`, modifier types only: a signed number (`+5`, `-0.5`, `−25`) or a
  percentage (`15%`). The figure belongs in the value. A static modifier's
  name is the title over its lines, where a step's figure can label the step
  ("Agricultural Tax Relief 25%" beside "50%"), so it is not judged for this.

Suppression is check-tagged and trails the name's loc line (the definition
that wins), as `long_tooltip_audit`'s does:

    my_type:0 "..." # REVIEWED 2026-11-15 (modifier_name): why

Keep the rationale free of `"`. A tag on a line whose key is not flagged is
stale and fails `--strict`.

Report: docs/engine/modifier_name_report.md. Registered in POST_LOAD_AUDITS.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from audit_common import AuditResult as _AuditResult
from audit_common import Flag as _Flag
from audit_common import StaleTag, cli_main, render_report, summary, write_text
from long_tooltip_audit import load_mod_loc, load_vanilla_loc, rendered_text

CHECK = "modifier_name"
MAX_NAME = 70
TYPE_DIR = os.path.join("common", "modifier_type_definitions")
STATIC_DIR = os.path.join("common", "static_modifiers")
REPORT_PATH = os.path.join("docs", "engine", "modifier_name_report.md")
TITLE = "Modifier name audit report"

_DEFINITION = re.compile(r"^(?:REPLACE:|INJECT:)?([A-Za-z_][\w.\-]*)\s*=\s*\{", re.M)
_SENTENCE = re.compile(r"(?:\w{3}|[)\]’'\"])[.!?]\s+\S|;|\.\s*$")
_FIGURE = re.compile(r"(?<![\w.])[+\-−]\s?\d|\d\s?%")
_TOKEN = "\x01"


@dataclass
class Flag(_Flag):
    key: str = ""
    kind: str = ""          # "modifier type" or "static modifier"
    checks: list[str] = field(default_factory=list)
    length: int = 0
    defined_in: str = ""


@dataclass
class AuditResult(_AuditResult):
    max_name: int = MAX_NAME
    names_measured: int = 0


def definitions(root: Path, rel_dir: str) -> dict[str, str]:
    """{name: file} for every top-level block in the directory's `.txt` files."""
    out: dict[str, str] = {}
    folder = root / rel_dir
    for path in sorted(folder.glob("*.txt")):
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        for m in _DEFINITION.finditer(text):
            out.setdefault(m.group(1), path.relative_to(root).as_posix())
    return out


def name_checks(text: str, *, figures: bool) -> list[str]:
    """The checks a rendered name fails, in report order."""
    checks = []
    if len(text) > MAX_NAME:
        checks.append("long")
    plain = text.replace(_TOKEN, "X")
    if _SENTENCE.search(plain):
        checks.append("sentence")
    if figures and _FIGURE.search(plain):
        checks.append("figure")
    return checks


def audit(mod_path: str | Path | None = None) -> AuditResult:
    if mod_path is None:
        from path_constants import mod_path as _default
        mod_path = _default
    root = Path(mod_path)
    mod_loc, tagged = load_mod_loc(root, CHECK)
    vanilla = load_vanilla_loc(root)

    def lookup(key: str):
        if key in mod_loc:
            return mod_loc[key].value
        value = vanilla.get(key)
        return value if isinstance(value, str) else None

    types = definitions(root, TYPE_DIR)
    if not types:
        raise FileNotFoundError(f"no modifier type definition under {root / TYPE_DIR}")
    statics = definitions(root, STATIC_DIR)
    result = AuditResult()
    flagged: set[str] = set()
    for kind, defs in (("modifier type", types), ("static modifier", statics)):
        for key, defined_in in sorted(defs.items()):
            entry = mod_loc.get(key)
            if entry is None or key in flagged:
                continue
            result.names_measured += 1
            text = rendered_text(entry.value, lookup)
            checks = name_checks(text, figures=kind == "modifier type")
            if not checks:
                continue
            flagged.add(key)
            excerpt = text.replace(_TOKEN, "[…]").replace("\n", " ")
            if len(excerpt) > 90:
                excerpt = excerpt[:87] + "..."
            message = (f"`{key}` ({kind}, {len(text)} characters): {', '.join(checks)}. "
                       f"Name: \"{excerpt}\"")
            result.flags.append(Flag(entry.file, entry.line, message, exemption=entry.tag, key=key, kind=kind,
                                     checks=checks, length=len(text), defined_in=defined_in))
    for rel, lineno, key in tagged:
        winning = mod_loc.get(key)
        if key not in flagged or (winning.file, winning.line) != (rel, lineno):
            result.stale.append(StaleTag(rel, lineno, CHECK))
    result.flags.sort(key=lambda f: (-f.length, f.key))
    return result


INTRO = f"""
Flagged: a modifier type or static modifier whose English name, as rendered, runs over
{MAX_NAME} characters (`long`), reads as a sentence (`sentence`), or, for a modifier type,
carries a figure (`figure`). A name is the label beside the value the engine prints: the
figure is the value, the conditions go in the `_desc`, and the rules in a concept it links
(`docs/guides/loc_style_guide.md`, "Modifier names").
"""


def render(result: AuditResult) -> str:
    text = render_report(result, TITLE, audit="modifier_name_audit", intro=INTRO)
    return text.rstrip("\n") + f"\n- names measured: {result.names_measured}\n- longest allowed: {result.max_name}\n"


def regenerate(mod_state=None) -> dict:
    """POST_LOAD_AUDITS hook: run the audit and write the report. Reads the
    definition and loc files itself, so `mod_state` is unused."""
    from path_constants import mod_path
    result = audit(mod_path)
    out_path = os.path.join(mod_path, REPORT_PATH)
    write_text(out_path, render(result))
    return summary(result, names_measured=result.names_measured, path=out_path)


def main(argv=None) -> int:
    def add_arguments(parser):
        parser.add_argument("--mod-path", type=Path)

    return cli_main(lambda args: audit(args.mod_path), lambda result, args: render(result),
                    argv=argv, description=__doc__.splitlines()[0], add_arguments=add_arguments)


if __name__ == "__main__":
    raise SystemExit(main())
