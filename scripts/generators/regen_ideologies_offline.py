"""Regenerate the two ideology-derived files without a Victoria 3 install.

`apply_ideologies.py` (common/ideologies/modified.txt) copies raw vanilla text,
so the server skips it in a game-less cloud session and its output goes stale
after an edit to `ideology_modifications.py`. This runs its own code on
stand-ins. (`gen_law_consistency.py`, which writes
common/scripted_effects/extra_law_consistency_generated.txt from the same
ideology stances, reads only parsed vanilla and runs from `vanilla_parsed/` on
its own, #624; this tool just calls it so one run refreshes both files.)

- modified.txt: vanilla ideologies are serialized from the committed
  `vanilla_parsed/` snapshot (their lawgroup blocks, which is all an INJECT
  entry, one that only adds blocks vanilla lacks, depends on). A REPLACE
  entry (the ideology touches a block vanilla has) needs vanilla's raw text,
  so it starts from its committed REPLACE body with the mod's edits undone:
  mod-added blocks removed, inserted laws dropped, vanilla's values put back
  and the opener's trailing comment moved back (the generator carries it onto
  the first-inserted law). A REPLACE with no committed body, such as the
  first stance on a vanilla ideology the mod hasn't touched, can't be
  produced here; the run stops and says which, and only a machine with the
  game can write it.
- extra_law_consistency_generated.txt: gen_law_consistency runs on the
  snapshot's laws and ideologies, with no stand-in.

Run once on an unchanged tree first: both outputs should come out byte for
byte as committed (`--check` exits 1 otherwise). On a machine with the game,
use the real generators instead.

Usage:
    python3 scripts/generators/regen_ideologies_offline.py           # write both
    python3 scripts/generators/regen_ideologies_offline.py --check   # diff only
"""
import argparse
import json
import os
import re
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)

import vanilla_parsed  # noqa: E402

MODIFIED = os.path.join(REPO, "common", "ideologies", "modified.txt")
CONSISTENCY = os.path.join(REPO, "common", "scripted_effects", "extra_law_consistency_generated.txt")


def _unwrap(v):
    while isinstance(v, tuple) and len(v) >= 2 and v[0] in ("=", "?="):
        v = v[1]
    return v


def _snapshot(entity_type):
    snap = os.path.join(REPO, "vanilla_parsed")
    info = vanilla_parsed.read_manifest(snap)["entity_types"][entity_type]
    with open(os.path.join(snap, info["file"]), encoding="utf-8") as fh:
        return vanilla_parsed.decode(json.load(fh))


def _ideology_text(name, body):
    lines = [f"{name} = {{"] if name else ["{"]
    for key, value in body.items():
        if key.startswith("lawgroup_"):
            lines.append(f"\t{key} = {{")
            lines += [f"\t\t{law} = {_unwrap(st)}" for law, st in _unwrap(value).items()]
            lines.append("\t}")
    lines.append("}")
    return "\n".join(lines) + "\n"


def _committed_replaces(path):
    with open(path, encoding="utf-8-sig") as fh:
        text = fh.read()
    out = {}
    for m in re.finditer(r"(?m)^REPLACE:(\w+) = ", text):
        out[m.group(1)] = text[m.end():text.index("\n}\n", m.end()) + 3]
    return out


def _restore_vanilla(gen, key, body, mods, vanilla):
    """Undo the generator's edits to one committed REPLACE body."""
    for sub_key, lines in mods.get(key, {}).items():
        vblock = vanilla.get(key, {}).get(sub_key)
        if vblock is None:
            block = gen._extract_block(body, sub_key)
            if block:
                body = body.replace(block, "", 1)
            continue
        vblock = {law: _unwrap(st) for law, st in _unwrap(vblock).items()}
        for law, _ in lines:
            if law in vblock:
                body = re.sub(rf"\t\t{re.escape(law)} = .*", f"\t\t{law} = {vblock[law]}", body)
        inserted = {law for law, _ in lines if law not in vblock}
        opener = f"\t{sub_key} = {{\n"
        pos = body.find(opener)
        if pos < 0:
            continue
        cur, last = pos + len(opener), None
        while True:
            eol = body.index("\n", cur)
            m = re.match(r"\t\t(\S+) = (\S+)(\s+#.*)?$", body[cur:eol])
            if not m or m.group(1) not in inserted:
                break
            last = (eol, m)
            cur = eol + 1
        if last:
            comment = last[1].group(3) or ""
            body = body[:pos] + f"\t{sub_key} = {{{comment}\n" + body[last[0] + 1:]
    return body


def regen_modified(out_path):
    import apply_ideologies
    from ideology_modifications import modifications

    vanilla = {k: _unwrap(v) for k, v in _snapshot("Ideologies").items()}
    entries = {name: _ideology_text(None, body) for name, body in vanilla.items()}
    committed = _committed_replaces(MODIFIED)
    for key, body in committed.items():
        entries[key] = _restore_vanilla(apply_ideologies, key, body, modifications, vanilla)
    result, unmatched = apply_ideologies.modify_entries(entries, modifications)
    blind = sorted(k for k, v in result.items() if v[0] == "REPLACE" and k not in committed)
    if blind:
        raise SystemExit(
            "These ideologies now touch a vanilla lawgroup block, so they need a REPLACE built from "
            f"vanilla's raw text, which only a machine with the game has: {', '.join(blind)}"
        )
    result = apply_ideologies.update_law_reqs(result)
    apply_ideologies.write_to_file(out_path, result)
    return unmatched


def regen_consistency(check):
    """Regenerate extra_law_consistency_generated.txt from the snapshot's laws
    and ideologies, whether or not this machine has the game. True if unchanged."""
    import contextlib
    import io

    import gen_law_consistency as gen

    vanilla = vanilla_parsed.parsed_entities(("Laws", "Ideologies"))
    # build_output prints its fallback warnings; this tool's report is its own.
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        content = gen.build_output(
            gen.parse_laws(vanilla["Laws"]), gen.parse_ideologies(vanilla["Ideologies"])
        )
    same = "\ufeff" + content == _read(CONSISTENCY)
    if not same and not check:
        with open(CONSISTENCY, "w", encoding="utf-8-sig", newline="") as fh:
            fh.write(content)
    return same


def _read(path):
    with open(path, encoding="utf-8", newline="") as fh:
        return fh.read()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true", help="write nothing; exit 1 if either output would change")
    args = ap.parse_args()

    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "modified.txt")
        unmatched = regen_modified(out)
        if unmatched:
            print(f"WARNING: modification keys matching no vanilla ideology: {', '.join(sorted(unmatched))}")
        new = _read(out)
    modified_same = new == _read(MODIFIED)
    if not args.check and not modified_same:
        with open(MODIFIED, "w", encoding="utf-8", newline="") as fh:
            fh.write(new)
    consistency_same = regen_consistency(args.check)

    for path, same in ((MODIFIED, modified_same), (CONSISTENCY, consistency_same)):
        rel = os.path.relpath(path, REPO)
        if same:
            print(f"{rel}: unchanged")
        else:
            print(f"{rel}: {'would change' if args.check else 'rewritten'}")
    if args.check and not (modified_same and consistency_same):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
