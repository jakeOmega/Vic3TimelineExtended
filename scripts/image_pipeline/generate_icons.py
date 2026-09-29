#!/usr/bin/env python3
"""
generate_icons.py - FLUX-generated UI icons for the mod's placeholder entities.

Reads the registry (icon_prompts.py) and takes each category through:

  render  embed the subjects and render candidates with FLUX: seeds 0..N-1 for
          an unreviewed entry (seed None), only the chosen seed for an accepted
          one. Cached per prompt, so an edited subject re-renders only itself,
          and raising --seeds later renders only the new seeds.
  compose fit each render into the category's vanilla layout (icon_render.py).
          A candidate whose final is newer than its raw is kept, so after a
          layout or spec change move the category's finals aside first.
  sheet   review sheets, 20 entities each: current icon | 3 vanilla neighbours
          || candidates. Pick a seed per entity and record it in ICONS.
  write   the accepted icons as uncompressed DDS with mips, vanilla's format
          (icon_dds.py), to gfx/interface/icons/<folder>/<key>.dds, or for a
          category with `dds_format` (the institution strips) block-compressed
          through texconv to <root>/<folder>/<key>.dds. A DDS is
          rewritten when its pick (seed or subject) changed since it was
          written (recorded in <work>/written.json); otherwise it is left
          alone, so to force one, delete it. For diplomatic actions it also
          keeps lens_toolbar_icons/<key>.dds a copy of the icon: the lens
          toolbar loads that path by key and ignores `texture`.
  wire    point each accepted entity's icon line at its DDS. Only entities whose
          DDS exists are touched, and an entity already pointing there is left
          byte-for-byte alone.

A GUI-hosted category (`gui` in its spec; the UN's icons) has no entity
files: each entry names the placeholder it replaces (`now`), `write` puts its
DDS where the .gui file will point, and `wire` is left to whoever edits the
.gui. Its entries may also be derived, with no render of their own: another
entry's icon ("from"), tinted, laid out as a flag, or with marks drawn over
it (see icon_prompts.py). Derived entries are composed on the fly for the
sheet and written once their source and parts are picked. A category marked
`part` (the UN's emblem and scroll badge) is reviewed like any other but only
feeds derived entries; `write` skips it.

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
    """The entries that get a FLUX icon: not "keep", not reusing another icon, not derived."""
    return {k: e for k, e in entries(cat, only).items()
            if "use" not in e and "from" not in e and e["seed"] != KEEP}


def derived(cat: str, only: set[str]) -> dict[str, dict]:
    """The entries built from another entry's icon ("from"), with no render of their own."""
    return {k: e for k, e in entries(cat, only).items() if "from" in e}


def picked(seed) -> bool:
    return isinstance(seed, int) and not isinstance(seed, bool)


def accepted(e: dict) -> bool:
    return "use" not in e and "from" not in e and picked(e.get("seed"))


def hosted(cat: str) -> bool:
    """A GUI-hosted category: no entity files, and each entry names its placeholder."""
    return "gui" in CATEGORIES[cat]


def ref(path: str) -> tuple[str, str]:
    """"<category>/<key>" -> (category, key)."""
    cat, key = path.split("/", 1)
    return cat, key


def depends_on(e: dict) -> list[tuple[str, str]]:
    """The registry entries a derived entry is built from: its source, then any part marks."""
    return [ref(e["from"])] + [ref(m["part"]) for m in e.get("marks", []) if "part" in m]


def derived_ready(e: dict) -> bool:
    """Whether a derived entry can be written: its source and every part it uses are picked."""
    return all(accepted(ICONS[c][k]) for c, k in depends_on(e))


# A category with a shared `backdrop` (the Space Race journal icons) renders it
# under this key, beside its entities. It is no entity: `--only _backdrop`
# renders it alone, which is how it is picked first.
BACKDROP = "_backdrop"


def flux_backdrop(cat: str) -> bool:
    """A backdrop FLUX renders and review picks, not one drawn from colours (`drawn`)."""
    bd = CATEGORIES[cat].get("backdrop")
    return bool(bd) and "drawn" not in bd


def backdrop_prompt(cat: str) -> str:
    return CATEGORIES[cat]["backdrop"]["prompt"] + ", no text, no writing, no letters"


def backdrop_seed(cat: str) -> int:
    """The backdrop candidate icons are composed over: the accepted seed, else s0 while it is under review."""
    seed = CATEGORIES[cat]["backdrop"]["seed"]
    return seed if picked(seed) else 0


def final_dir(cat: str, work: Path) -> Path:
    """Where composed candidates go. A backed category keeps one folder per
    backdrop seed, so a new pick never reuses finals composed over the old one."""
    if flux_backdrop(cat):
        return work / "final" / f"{cat}_bd{backdrop_seed(cat)}"
    return work / "final"


def load_backdrop(cat: str, work: Path, seed: int | None = None):
    """The composed backdrop disc and the raw render it came from (None for a drawn one)."""
    from PIL import Image

    from icon_render import compose_backdrop, draw_disc, raw_path

    spec = CATEGORIES[cat]
    if "drawn" in spec["backdrop"]:
        return draw_disc(spec["size"], spec["backdrop"]["drawn"]), None

    raw = raw_path(work / "raw", name(cat, BACKDROP), backdrop_seed(cat) if seed is None else seed)
    if not raw.exists():
        raise SystemExit(f"no backdrop render for {cat}: run --stage render --only {BACKDROP}")
    return compose_backdrop(Image.open(raw), CATEGORIES[cat]), raw


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
    """key -> the path in its top-level `field = "..."` line, for every entity
    (for a GUI-hosted category, the placeholder each entry names)."""
    if hosted(cat):
        return {k: e.get("now", "") for k, e in ICONS[cat].items()}
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
    bd = CATEGORIES[cat].get("backdrop")
    if flux_backdrop(cat) and (not only or BACKDROP in only):
        prompts[name(cat, BACKDROP)] = backdrop_prompt(cat)
        for seed in ([bd["seed"]] if picked(bd["seed"]) else range(bd["seeds"])):
            jobs.append((name(cat, BACKDROP), backdrop_prompt(cat), seed))
    embed(prompts, work / "embeds")
    kw = {"size": CATEGORIES[cat]["gen_size"]} if "gen_size" in CATEGORIES[cat] else {}
    render(jobs, work / "embeds", work / "raw", offload, **kw)


# Per-entry settings that change how an entry's render is composed.
ENTRY_SPEC_KEYS = ("solid",)


def entry_spec(cat: str, e: dict) -> dict:
    """The category's spec with the entry's own compose settings (`solid`) over it."""
    own = {k: e[k] for k in ENTRY_SPEC_KEYS if k in e}
    return dict(CATEGORIES[cat], **own) if own else CATEGORIES[cat]


def _compose_one(composer, cat: str, raw: Path, final: Path, backdrop=None, backdrop_raw: Path | None = None,
                 spec: dict | None = None):
    from PIL import Image

    newest = max(raw.stat().st_mtime, backdrop_raw.stat().st_mtime if backdrop_raw else 0)
    if final.exists() and final.stat().st_mtime >= newest:
        return Image.open(final)
    icon = composer.compose(Image.open(raw), cat, spec or CATEGORIES[cat], backdrop=backdrop)
    final.parent.mkdir(parents=True, exist_ok=True)
    icon.save(final)
    return icon


class Finals:
    """Composed candidates with their marks, composed on demand.

    Derived entries and marks reach across categories (a UN topic is an
    agency icon under a scroll part), so whatever they build on is composed
    here when its final is missing, not only by that category's compose stage.
    """

    def __init__(self, work: Path) -> None:
        from icon_render import Composer, vanilla_icons_dir

        self.work, self.composer, self._backdrops = work, Composer(), {}
        self.game = vanilla_icons_dir().parents[2]

    def backdrop(self, cat: str):
        if cat not in self._backdrops:
            self._backdrops[cat] = load_backdrop(cat, self.work) if "backdrop" in CATEGORIES[cat] else (None, None)
        return self._backdrops[cat]

    def seeds(self, cat: str, key: str) -> list[int]:
        """The entry's pick, or every candidate rendered for it while it is under review."""
        e = ICONS[cat][key]
        if accepted(e):
            return [e["seed"]]
        return sorted(int(p.stem.rsplit("__s", 1)[1])
                      for p in (self.work / "raw").glob(f"{name(cat, key)}__s*.png"))

    def get(self, cat: str, key: str, seed: int):
        """The candidate composed in its category's layout, marks and all; None with no render."""
        from icon_render import raw_path

        raw = raw_path(self.work / "raw", name(cat, key), seed)
        if not raw.exists():
            return None
        icon = _compose_one(self.composer, cat, raw, final_dir(cat, self.work) / raw.name, *self.backdrop(cat),
                            spec=entry_spec(cat, ICONS[cat][key]))
        return self.finish(ICONS[cat][key], icon)

    def finish(self, e: dict, icon):
        from icon_render import apply_marks

        return apply_marks(icon, e["marks"], self.load_mark) if e.get("marks") else icon

    def load_mark(self, mark: dict):
        from icon_render import load_rgba

        if "icon" in mark:
            return load_rgba(self.game / mark["icon"])
        cat, key = ref(mark["part"])
        seeds = self.seeds(cat, key)
        im = self.get(cat, key, seeds[0]) if seeds else None
        if im is None:
            raise SystemExit(f"no render for the part {mark['part']}: run --stage render --category {cat}")
        return im

    def derived(self, e: dict, seed: int):
        """A derived entry built on its source's candidate `seed`; None with no render."""
        from icon_render import flag_layout, tint

        base = self.get(*ref(e["from"]), seed)
        if base is None:
            return None
        im = tint(base, e.get("tint"))
        if e.get("layout") == "flag":
            im = flag_layout(im, tuple(e["size"]))
        return self.finish(e, im)


def stage_compose(cat: str, only: set[str], work: Path) -> None:
    from icon_render import Composer

    composer, n = Composer(), 0
    backdrop, backdrop_raw = load_backdrop(cat, work) if "backdrop" in CATEGORIES[cat] else (None, None)
    final = final_dir(cat, work)
    for key, e in generated(cat, only).items():
        for raw in sorted((work / "raw").glob(f"{name(cat, key)}__s*.png")):
            _compose_one(composer, cat, raw, final / raw.name, backdrop, backdrop_raw, spec=entry_spec(cat, e))
            n += 1
    print(f"compose: {n} candidates in {final}")


def stage_sheet(cat: str, only: set[str], work: Path, include_reviewed: bool) -> None:
    from icon_render import (Composer, backdrop_sheet, panel_preview, review_sheet, strip_sheet, vanilla_folder,
                             vanilla_icons_dir)
    from PIL import Image

    current = current_icons(cat)
    game = vanilla_icons_dir().parents[2]
    spec = CATEGORIES[cat]
    finals = Finals(work)
    rows, panel_rows = [], []
    for key, e in {**generated(cat, only), **derived(cat, only)}.items():
        if "from" in e:
            # Shown while anything it is built from is under review, one
            # candidate per candidate of its source.
            if derived_ready(e) and not include_reviewed:
                continue
            cands = [(f"{ref(e['from'])[1]} s{seed}", finals.derived(e, seed))
                     for seed in finals.seeds(*ref(e["from"]))]
            subject = "from " + e["from"]
        else:
            if e["seed"] is not None and not include_reviewed:
                continue
            cands = [(f"s{seed}", finals.get(cat, key, seed)) for seed in finals.seeds(cat, key)]
            subject = e["subject"] if len(e["subject"]) <= 60 else e["subject"][:57] + "..."
        cands = [(c, im) for c, im in cands if im is not None]
        now = current.get(key, "")
        now_path = MOD_ROOT / now if (MOD_ROOT / now).exists() else game / now
        rows.append((f"{key}\n{subject}", now_path, cands))
        if spec.get("panel_preview"):
            tiles = [("now", Image.open(now_path))] if now_path.is_file() else []
            panel_rows.append((key, tiles + cands))
    out = work / "sheets"
    out.mkdir(parents=True, exist_ok=True)
    for i in range(0, len(rows), SHEET_ROWS):
        dest = out / f"{cat}_{i // SHEET_ROWS + 1:02d}.png"
        if spec["mode"] == "strip":
            strip_sheet(rows[i:i + SHEET_ROWS], vanilla_folder(spec) / "institution_image_mask.dds", dest)
        else:
            # A folder new to the mod (un_icons) has no vanilla files to show beside it.
            review_sheet(rows[i:i + SHEET_ROWS], spec.get("neighbours", spec["folder"]), dest)
        if panel_rows:
            panel_preview(panel_rows[i:i + SHEET_ROWS], out / f"{cat}_panel_{i // SHEET_ROWS + 1:02d}.png")
    if flux_backdrop(cat) and not picked(spec["backdrop"]["seed"]):
        # Each backdrop candidate bare, then under the first raw of a few subjects.
        composer, samples = Composer(), list(generated(cat, only))[::2][:4]
        bd_rows = []
        for raw in sorted((work / "raw").glob(f"{name(cat, BACKDROP)}__s*.png")):
            seed = int(raw.stem.rsplit("__s", 1)[1])
            backdrop, _ = load_backdrop(cat, work, seed)
            images = [(f"backdrop s{seed}", backdrop)]
            for key in samples:
                sample = work / "raw" / f"{name(cat, key)}__s0.png"
                if sample.exists():
                    images.append(("", composer.compose(Image.open(sample), cat, spec, backdrop=backdrop)))
            bd_rows.append((f"s{seed}", images))
        if bd_rows:
            backdrop_sheet(bd_rows, out / f"{cat}_backdrops.png")


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

    spec = CATEGORIES[cat]
    if spec.get("part"):
        print(f"write: {cat} holds parts of other icons; nothing to write")
        return
    bd = spec.get("backdrop") if flux_backdrop(cat) else None
    # Before the image imports: refusing needs neither Pillow nor the game.
    if bd and not picked(bd["seed"]) and any(accepted(e) for e in entries(cat, only).values()):
        raise SystemExit(f"{cat}: pick the backdrop first (set its seed in icon_prompts.py)")

    from icon_dds import write_dds
    from icon_render import raw_path

    out_dir = (MOD_ROOT / icon_path(cat, "_")).parent
    if not (MOD_ROOT / "gfx" / "interface").is_dir():
        raise SystemExit(f"{MOD_ROOT / 'gfx' / 'interface'} is not checked out (a sparse worktree?)")
    out_dir.mkdir(parents=True, exist_ok=True)
    # What each DDS was written from, so a changed pick is rewritten instead of
    # silently kept. Machine-local, beside the renders it refers to.
    manifest_path = work / "written.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    finals, wrote = Finals(work), 0

    def part_seeds(e: dict) -> list:
        return [ICONS[c][k].get("seed") for c, k in (ref(m["part"]) for m in e.get("marks", []) if "part" in m)]

    def want_for(c: str, e: dict) -> list:
        """What an icon is made from, as the manifest stores it; a change rewrites the icon."""
        if "from" in e:
            want = (["from", want_for(*_src(e))] + [e.get(k) for k in ("tint", "layout", "size", "marks")]
                    + part_seeds(e))
        else:
            want = [e["seed"], prompt_for(c, e["subject"])]
            if flux_backdrop(c):
                # A new backdrop pick or prompt rewrites every icon over it.
                want += [CATEGORIES[c]["backdrop"]["seed"], backdrop_prompt(c)]
            elif "backdrop" in CATEGORIES[c]:
                # So do new colours for a drawn one.
                want += [CATEGORIES[c]["backdrop"]["drawn"]]
            if e.get("marks"):
                want += [e["marks"]] + part_seeds(e)
            if any(k in e for k in ENTRY_SPEC_KEYS):
                want += [{k: e[k] for k in ENTRY_SPEC_KEYS if k in e}]
        return json.loads(json.dumps(want))  # tuples as lists, as read back

    def _src(e: dict) -> tuple[str, dict]:
        c, k = ref(e["from"])
        return c, ICONS[c][k]

    for key, e in derived(cat, only).items():
        if not derived_ready(e):
            continue
        dest = MOD_ROOT / icon_path(cat, key)
        want = want_for(cat, e)
        if not needs_write(dest.exists(), manifest.get(name(cat, key)), want):
            continue
        icon = finals.derived(e, _src(e)[1]["seed"])
        if icon is None:
            print(f"  no render for {e['from']}, which {cat}/{key} is built on: run --stage render")
            continue
        write_dds(icon, dest)
        manifest[name(cat, key)] = want
        wrote += 1
    for key, e in generated(cat, only).items():
        if not accepted(e) or not all(map(picked, part_seeds(e))):
            continue
        dest = MOD_ROOT / icon_path(cat, key)
        want = want_for(cat, e)
        if not needs_write(dest.exists(), manifest.get(name(cat, key)), want):
            continue
        raw = raw_path(work / "raw", name(cat, key), e["seed"])
        if not raw.exists():
            print(f"  no render for {cat}/{key} seed {e['seed']}: run --stage render")
            continue
        final = final_dir(cat, work) / raw.name
        icon = finals.get(cat, key, e["seed"])
        if "dds_format" in spec:
            # Block-compressed through texconv, as event pictures are; the
            # composed PNG is already at its final size.
            from convert_event_image import convert_image, ensure_texconv
            convert_image(final, dest, ensure_texconv(), spec["dds_format"], do_resize=False)
        else:
            write_dds(icon, dest)
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
    if hosted(cat):
        print(f"wire: {cat} is GUI-hosted: point the .gui's textures at {spec['folder']}/<key>.dds by hand")
        return
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
