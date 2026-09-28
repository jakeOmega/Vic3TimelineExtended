#!/usr/bin/env python3
"""
generate_icons.py - FLUX-generated UI icons for the mod's placeholder entities.

Reads the registry (icon_prompts.py) and takes each category through:

  render  embed the subjects and render candidates with FLUX: seeds 0..N-1 for
          an unreviewed entry (seed None), only the chosen seed for an accepted
          one. Cached per prompt, so an edited subject re-renders only itself,
          and raising --seeds later renders only the new seeds.
  compose fit each render into the category's vanilla layout (icon_render.py).
  sheet   review sheets, 20 entities each: current icon | 3 vanilla neighbours
          || candidates. Pick a seed per entity and record it in ICONS.
  write   the accepted icons as uncompressed DDS with mips, vanilla's format
          (icon_dds.py), to gfx/interface/icons/<folder>/<key>.dds. A DDS is
          rewritten when its pick (seed or subject) changed since it was
          written (recorded in <work>/written.json); otherwise it is left
          alone, so to force one, delete it. For diplomatic actions it also
          keeps lens_toolbar_icons/<key>.dds a copy of the icon: the lens
          toolbar loads that path by key and ignores `texture`.
  wire    point each accepted entity's icon line at its DDS. Only entities whose
          DDS exists are touched, and an entity already pointing there is left
          byte-for-byte alone.

The two ends, render and write, need .venv-img (torch, diffusers, rembg) and
the game install; see docs/guides/python_tools.md. wire and --validate need
neither.

    FLUX_MODEL_DIR=~/models/FLUX.1-schnell HF_HUB_OFFLINE=1 VIC3_BASE_GAME=<game install> \\
      .venv-img/bin/python scripts/image_pipeline/generate_icons.py --stage render --seeds 2
    ... --stage compose, --stage sheet   (review, set seeds in icon_prompts.py)
    ... --stage write, --stage wire
    python3 scripts/image_pipeline/generate_icons.py --validate

Working files (embeddings, renders, composed candidates, sheets) go to
generated_images/icons/ (gitignored) unless --work says otherwise.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
MOD_ROOT = SCRIPT_DIR.parents[1]
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(MOD_ROOT))
from icon_prompts import CATEGORIES, ICONS, KEEP, icon_path, prompt_for  # noqa: E402

SHEET_ROWS = 20


def name(cat: str, key: str) -> str:
    return f"{cat}__{key}"


def entries(cat: str, only: set[str]) -> dict[str, dict]:
    return {k: e for k, e in ICONS[cat].items() if not only or k in only}


def generated(cat: str, only: set[str]) -> dict[str, dict]:
    """The entries that get a FLUX icon: not "keep", not reusing another icon."""
    return {k: e for k, e in entries(cat, only).items() if "use" not in e and e["seed"] != KEEP}


def accepted(e: dict) -> bool:
    return "use" not in e and isinstance(e["seed"], int) and not isinstance(e["seed"], bool)


# ── reading and rewriting entity files ───────────────────────────────────

# A plain definition or a REPLACE_OR_CREATE: one (mod-added buildings use it),
# captured without the prefix. REPLACE:/INJECT: change a vanilla entity.
_DEF_RE = re.compile(r"^(?:REPLACE_OR_CREATE:)?([A-Za-z0-9_\-]+)\s*=\s*\{")


def _code(line: str) -> str:
    """The line without its comment or quoted strings, for brace counting."""
    return re.sub(r'"[^"]*"', '""', line.split("#", 1)[0])


def hidden_from_lens(cat: str, root: Path = MOD_ROOT) -> set[str]:
    """Keys whose block sets `show_in_lens = no` at depth 1."""
    spec = CATEGORIES[cat]
    hidden: set[str] = set()
    for path in sorted((root / spec["entity_dir"]).rglob("*.txt")):
        key, depth = None, 0
        for line in path.read_text(encoding="utf-8-sig", errors="replace").split("\n"):
            code = _code(line)
            if depth == 0:
                m = _DEF_RE.match(line)
                key = m.group(1) if m else None
            elif depth == 1 and key and re.match(r"\s*show_in_lens\s*=\s*no\b", code):
                hidden.add(key)
            depth += code.count("{") - code.count("}")
    return hidden


def sync_lens_copies(cat: str, only: set[str], root: Path = MOD_ROOT, dry_run: bool = False) -> list[str]:
    """Make lens_toolbar_icons/<key>.dds a copy of each generated action icon.

    Only for categories with a `lens_folder`, only for entities shown in the
    lens, and only where the icon's DDS exists. Returns the keys whose copy was
    (or would be) written.
    """
    spec = CATEGORIES[cat]
    if "lens_folder" not in spec:
        return []
    lens_dir = root / "gfx" / "interface" / "icons" / spec["lens_folder"]
    hidden = hidden_from_lens(cat, root)
    changed = []
    for key, e in generated(cat, only).items():
        src = root / icon_path(cat, key)
        if not accepted(e) or key in hidden or not src.exists():
            continue
        dest = lens_dir / f"{key}.dds"
        data = src.read_bytes()
        if dest.exists() and dest.read_bytes() == data:
            continue
        if not dry_run:
            lens_dir.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
        changed.append(key)
    return changed


def current_icons(cat: str, root: Path = MOD_ROOT) -> dict[str, str]:
    """key -> the path in its top-level `field = "..."` line, for every entity."""
    spec = CATEGORIES[cat]
    field_re = re.compile(r'^\s*' + spec["field"] + r'\s*=\s*"([^"]*)"')
    found: dict[str, str] = {}
    for path in sorted((root / spec["entity_dir"]).rglob("*.txt")):
        key, depth = None, 0
        for line in path.read_text(encoding="utf-8-sig", errors="replace").split("\n"):
            code = _code(line)
            if depth == 0:
                m = _DEF_RE.match(line)
                key = m.group(1) if m else None
            elif depth == 1 and key:
                m = field_re.match(line)
                if m:
                    found.setdefault(key, m.group(1))
            depth += code.count("{") - code.count("}")
    return found


def rewrite_icon_refs(path: Path, field: str, targets: dict[str, str], dry_run: bool = False) -> list[str]:
    """Point each key's depth-1 `field = "..."` line in `path` at targets[key].

    Returns the keys changed. The rest of the file, its BOM and each line's
    indentation and trailing comment are kept, except a comment calling the
    old icon a placeholder, which stops being true. An entity with no such
    line (the covert-operation actions had none, so the game showed no icon)
    gets one as the first line of its block, where vanilla puts it. Mod-added
    entities are plain top-level or REPLACE_OR_CREATE: definitions;
    INJECT:/REPLACE: blocks, which change a vanilla entity, are not matched.
    """
    raw = path.read_bytes()
    bom = raw.startswith(b"\xef\xbb\xbf")
    lines = raw.decode("utf-8-sig").split("\n")
    field_re = re.compile(r'^(\s*' + field + r'\s*=\s*")([^"]*)(".*)$')
    changed: list[str] = []
    opened: dict[str, int] = {}  # target key -> its opening line, while it has no field line
    key, depth = None, 0
    for i, line in enumerate(lines):
        code = _code(line)
        if depth == 0:
            m = _DEF_RE.match(line)
            key = m.group(1) if m else None
            if key in targets and code.count("{") > code.count("}"):
                opened.setdefault(key, i)
        elif depth == 1 and key in targets:
            m = field_re.match(line)
            if m:
                opened.pop(key, None)
                if m.group(2) != targets[key] and key not in changed:
                    rest = m.group(3)
                    if "placeholder" in rest.lower():
                        rest = '"' + rest[1:].split("#", 1)[0].rstrip()
                    lines[i] = m.group(1) + targets[key] + rest
                    changed.append(key)
        depth += code.count("{") - code.count("}")
    for key, i in sorted(opened.items(), key=lambda kv: -kv[1]):
        lines.insert(i + 1, f'\t{field} = "{targets[key]}"')
        changed.append(key)
    if changed and not dry_run:
        text = "\n".join(lines).encode("utf-8")
        path.write_bytes((b"\xef\xbb\xbf" if bom else b"") + text)
    return changed


# ── stages ───────────────────────────────────────────────────────────────

def stage_render(cat: str, only: set[str], work: Path, seeds: int, offload: str) -> None:
    from icon_render import embed, render

    jobs, prompts = [], {}
    for key, e in generated(cat, only).items():
        prompt = prompt_for(cat, e["subject"])
        prompts[name(cat, key)] = prompt
        for seed in ([e["seed"]] if accepted(e) else range(seeds)):
            jobs.append((name(cat, key), prompt, seed))
    embed(prompts, work / "embeds")
    render(jobs, work / "embeds", work / "raw", offload)


def _compose_one(composer, cat: str, raw: Path, final: Path):
    from PIL import Image

    if final.exists() and final.stat().st_mtime >= raw.stat().st_mtime:
        return Image.open(final)
    icon = composer.compose(Image.open(raw), cat, CATEGORIES[cat])
    final.parent.mkdir(parents=True, exist_ok=True)
    icon.save(final)
    return icon


def stage_compose(cat: str, only: set[str], work: Path) -> None:
    from icon_render import Composer

    composer, n = Composer(), 0
    for key in generated(cat, only):
        for raw in sorted((work / "raw").glob(f"{name(cat, key)}__s*.png")):
            _compose_one(composer, cat, raw, work / "final" / raw.name)
            n += 1
    print(f"compose: {n} candidates in {work / 'final'}")


def stage_sheet(cat: str, only: set[str], work: Path, include_reviewed: bool) -> None:
    from icon_render import review_sheet, vanilla_icons_dir

    current = current_icons(cat)
    game = vanilla_icons_dir().parents[2]
    rows = []
    for key, e in generated(cat, only).items():
        if e["seed"] is not None and not include_reviewed:
            continue
        cands = [(f"s{p.stem.rsplit('__s', 1)[1]}", p)
                 for p in sorted((work / "final").glob(f"{name(cat, key)}__s*.png"))]
        now = current.get(key, "")
        now_path = MOD_ROOT / now if (MOD_ROOT / now).exists() else game / now
        subject = e["subject"] if len(e["subject"]) <= 60 else e["subject"][:57] + "..."
        rows.append((f"{key}\n{subject}", now_path, cands))
    out = work / "sheets"
    out.mkdir(parents=True, exist_ok=True)
    for i in range(0, len(rows), SHEET_ROWS):
        review_sheet(rows[i:i + SHEET_ROWS], CATEGORIES[cat]["folder"],
                     out / f"{cat}_{i // SHEET_ROWS + 1:02d}.png")


def needs_write(exists: bool, recorded: list | None, want: list) -> bool:
    """Whether `write` should (re)write an icon.

    A missing DDS is written. An existing one is rewritten only when the
    manifest says it came from another seed or prompt (the pick changed after
    it was written); with no record (another machine, an older run) it is
    trusted and left alone.
    """
    return not exists or (recorded is not None and recorded != want)


def stage_write(cat: str, only: set[str], work: Path) -> None:
    import json

    from icon_dds import write_dds
    from icon_render import Composer, raw_path

    out_dir = MOD_ROOT / "gfx" / "interface" / "icons" / CATEGORIES[cat]["folder"]
    if not out_dir.parent.is_dir():
        raise SystemExit(f"{out_dir.parent} is not checked out (a sparse worktree?)")
    out_dir.mkdir(exist_ok=True)
    # What each DDS was written from, so a changed pick is rewritten instead of
    # silently kept. Machine-local, beside the renders it refers to.
    manifest_path = work / "written.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    composer, wrote = Composer(), 0
    for key, e in generated(cat, only).items():
        if not accepted(e):
            continue
        dest = MOD_ROOT / icon_path(cat, key)
        want = [e["seed"], prompt_for(cat, e["subject"])]
        if not needs_write(dest.exists(), manifest.get(name(cat, key)), want):
            continue
        raw = raw_path(work / "raw", name(cat, key), e["seed"])
        if not raw.exists():
            print(f"  no render for {cat}/{key} seed {e['seed']}: run --stage render")
            continue
        write_dds(_compose_one(composer, cat, raw, work / "final" / raw.name), dest)
        manifest[name(cat, key)] = want
        wrote += 1
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=1, sort_keys=True))
    print(f"write: {wrote} DDS files written in {out_dir}")
    lens = sync_lens_copies(cat, only)
    if lens:
        print(f"write: {len(lens)} lens-toolbar copies updated in {CATEGORIES[cat]['lens_folder']}")


def stage_wire(cat: str, only: set[str], dry_run: bool) -> None:
    spec = CATEGORIES[cat]
    targets = {key: icon_path(cat, key) for key, e in generated(cat, only).items()
               if accepted(e) and (MOD_ROOT / icon_path(cat, key)).exists()}
    targets.update({key: e["use"] for key, e in entries(cat, only).items() if "use" in e})
    total = 0
    for path in sorted((MOD_ROOT / spec["entity_dir"]).rglob("*.txt")):
        changed = rewrite_icon_refs(path, spec["field"], targets, dry_run)
        if changed:
            total += len(changed)
            print(f"  {'WOULD UPDATE' if dry_run else 'UPDATED'}: {path.name} ({len(changed)})")
    print(f"wire: {total} of {len(targets)} icons {'would be ' if dry_run else ''}rewired")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stage", choices=["render", "compose", "sheet", "write", "wire"])
    ap.add_argument("--category", choices=sorted(ICONS), action="append")
    ap.add_argument("--only", nargs="*", default=[], help="entity keys")
    ap.add_argument("--seeds", type=int, default=2, help="candidates per unreviewed entity")
    ap.add_argument("--offload", choices=["model", "sequential"], default="sequential")
    ap.add_argument("--work", type=Path, default=MOD_ROOT / "generated_images" / "icons")
    ap.add_argument("--all", action="store_true", help="sheet: include reviewed entities")
    ap.add_argument("--dry-run", action="store_true", help="wire: report only")
    ap.add_argument("--validate", action="store_true", help="registry vs the mod's files")
    args = ap.parse_args()
    if args.validate:
        from icon_prompts import validate
        sys.exit(0 if validate() else 1)
    if not args.stage:
        ap.error("--stage or --validate is required")
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    only = set(args.only)
    for cat in args.category or sorted(ICONS):
        if args.stage == "render":
            stage_render(cat, only, args.work, args.seeds, args.offload)
        elif args.stage == "compose":
            stage_compose(cat, only, args.work)
        elif args.stage == "sheet":
            stage_sheet(cat, only, args.work, args.all)
        elif args.stage == "write":
            stage_write(cat, only, args.work)
        else:
            stage_wire(cat, only, args.dry_run)


if __name__ == "__main__":
    main()
