#!/usr/bin/env python3
"""gen_event.py — Event scaffolding tool for Vic3TimelineExtended

Generates Paradox event definitions + localization from compact JSON specs.
Handles ID allocation, boilerplate, UTF-8 BOM encoding, and loc file updates.

Subcommands:
    next-id   Find available event IDs in a namespace
    batch     Generate events from a JSON spec file
    scaffold  Generate a single event from CLI arguments

JSON spec format (batch mode):
{
    "namespace": "my_events",
    "output_file": "events/my_file.txt",   // relative to mod root
    "append": false,                        // true to append to existing file
    "header_comment": "MY EVENTS HEADER",  // optional file/section header
    "auto_id_start": 0,                    // start searching for free IDs after this
    "defaults": {                          // fallback values for all events
        "type": "country_event",
        "placement": "root",
        "icon": "gfx/interface/icons/event_icons/event_default.dds",
        "sound": "event:/SFX/UI/Alerts/event_appear",
        "duration": 3,
        "options": [                       // shared option structure
            {"name": "Acknowledged", "default": true, "ai_weight": 5}
        ]
    },
    "events": [
        {
            "id": 1,                       // optional — auto-assigned if omitted
            "comment": "Short description",
            "section_comment": "SECTION HEADER",  // divider before this event

            // Title: string = new loc key, title_ref = existing key
            "title": "My Event Title",
            // OR: "title_ref": "existing.loc.key",

            // Desc: string = new loc key (simple desc)
            "desc": "The event description.",
            // OR: list = triggered_desc chain (refs + optional new text)
            // "desc": [
            //     "existing.key",                                   // ref, always=yes
            //     {"ref": "existing.key"},                          // same, explicit
            //     {"ref": "key", "trigger": "var:x = 1"},           // ref with trigger
            //     {"text": "New paragraph.", "key": "ns.ID.d.2"}    // new loc entry
            // ],

            // Flavor: string = new loc key, flavor_ref = existing key
            "flavor": "Flavor text.",
            // OR: "flavor_ref": "existing.loc.key",

            // Image: key (short name) or full path or video
            "image": "my_image",
            // OR: "image_path": "gfx/event_pictures/full_path.dds",
            // OR: "video": "event_video_name",

            // Options (falls back to defaults.options)
            "options": [
                {
                    "name": "Do something",        // new loc key
                    // OR: "name_ref": "existing.key",
                    "default": true,               // default_option = yes
                    "ai_weight": 5,                // ai_chance base
                    "effects": "add_prestige = 10" // raw Paradox script, optional
                }
            ],

            // Optional raw Paradox script blocks:
            "trigger": "",         // empty = { }, or raw content
            "immediate": "",
            "cooldown": "{ days = normal_modifier_time }",
            "after": "hidden_effect = { ... }",

            "hidden": false        // hidden event (no UI — just trigger+immediate)
        }
    ]
}
"""

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

MOD_ROOT = Path(__file__).resolve().parent
EVENTS_DIR = MOD_ROOT / "events"
LOC_FILE = MOD_ROOT / "localization" / "english" / "te_events_l_english.yml"
LETTERS = "abcdefghijklmnopqrstuvwxyz"
UTF8_BOM = b"\xef\xbb\xbf"


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

def find_used_ids(namespace: str) -> set:
    """Scan all event files for IDs already used in a namespace."""
    used = set()
    pat = re.compile(rf"^\s*{re.escape(namespace)}\.(\d+)\s*=", re.MULTILINE)
    for p in EVENTS_DIR.glob("*.txt"):
        try:
            for m in pat.finditer(p.read_text(encoding="utf-8-sig")):
                used.add(int(m.group(1)))
        except Exception:
            pass
    return used


def next_free_ids(namespace: str, after: int = 0, count: int = 1) -> list:
    used = find_used_ids(namespace)
    result, c = [], after + 1
    while len(result) < count:
        if c not in used:
            result.append(c)
        c += 1
    return result


def write_bom(path: Path, text: str):
    """Write text with UTF-8 BOM."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(UTF8_BOM + text.encode("utf-8"))


def read_bom(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig")


def _get(ev: dict, key: str, defaults: dict, fallback=None):
    """Get field from event, falling back to defaults, then fallback."""
    return ev.get(key, defaults.get(key, fallback))


def _block(raw: str, indent: str = "\t") -> str:
    """Wrap raw Paradox script content in { } with indentation."""
    raw = (raw or "").strip()
    if not raw:
        return "{ }"
    if raw.startswith("{"):
        return raw
    inner = "\n".join(f"{indent}\t{ln}" for ln in raw.splitlines())
    return "{\n" + inner + f"\n{indent}}}"


# ---------------------------------------------------------------------------
# Event generation
# ---------------------------------------------------------------------------

def generate_event(ns: str, ev: dict, defaults: dict) -> str:
    """Generate Paradox script text for one event definition."""
    eid = ev["id"]
    hidden = ev.get("hidden", False)
    lines = []

    # Section divider
    if "section_comment" in ev:
        lines.append(f"# {'=' * 65}")
        lines.append(f"# {ev['section_comment']}")
        lines.append(f"# {'=' * 65}")
        lines.append("")

    # Per-event comment
    if "comment" in ev:
        lines.append(f"# {ev['comment']}")

    lines.append(f"{ns}.{eid} = {{")
    lines.append(f"\ttype = {_get(ev, 'type', defaults, 'country_event')}")

    # --- Hidden event: minimal structure ---
    if hidden:
        lines.append("\thidden = yes")
        lines.append(f"\ttrigger = {_block(ev.get('trigger', ''))}")
        lines.append(f"\timmediate = {_block(ev.get('immediate', ''))}")
        lines.append("}")
        return "\n".join(lines)

    # --- Visible event ---
    lines.append(f"\tplacement = {_get(ev, 'placement', defaults, 'root')}")

    # Image
    if "video" in ev:
        lines.append(f'\tevent_image = {{ video = "{ev["video"]}" }}')
    elif "image_path" in ev:
        lines.append(f'\tevent_image = {{ texture = "{ev["image_path"]}" }}')
    elif "image" in ev:
        lines.append(f'\tevent_image = {{ texture = "gfx/event_pictures/{ev["image"]}.dds" }}')
    else:
        img = defaults.get("image")
        if img:
            lines.append(f'\tevent_image = {{ texture = "gfx/event_pictures/{img}.dds" }}')

    sound = _get(ev, "sound", defaults, "event:/SFX/UI/Alerts/event_appear")
    lines.append(f'\ton_created_soundeffect = "{sound}"')
    icon = _get(ev, "icon", defaults, "gfx/interface/icons/event_icons/event_default.dds")
    lines.append(f'\ticon = "{icon}"')

    # Title
    if "title_ref" in ev:
        lines.append(f"\ttitle = {ev['title_ref']}")
    else:
        lines.append(f"\ttitle = {ns}.{eid}.t")

    # Desc
    desc = ev.get("desc")
    if desc is None or isinstance(desc, str):
        lines.append(f"\tdesc = {ns}.{eid}.d")
    elif isinstance(desc, list):
        lines.append("\tdesc = {")
        for item in desc:
            if isinstance(item, str):
                lines.append(f"\t\ttriggered_desc = {{ desc = {item} trigger = {{ always = yes }} }}")
            elif isinstance(item, dict):
                ref = item.get("ref", item.get("key", f"{ns}.{eid}.d"))
                trigger = item.get("trigger", "always = yes")
                lines.append(f"\t\ttriggered_desc = {{ desc = {ref} trigger = {{ {trigger} }} }}")
        lines.append("\t}")

    # Flavor
    if "flavor_ref" in ev:
        lines.append(f"\tflavor = {ev['flavor_ref']}")
    elif "flavor" in ev:
        lines.append(f"\tflavor = {ns}.{eid}.f")

    # Duration, cooldown
    lines.append(f"\tduration = {_get(ev, 'duration', defaults, 3)}")
    if "cooldown" in ev:
        lines.append(f"\tcooldown = {ev['cooldown']}")

    # Trigger, immediate
    lines.append(f"\ttrigger = {_block(ev.get('trigger', ''))}")
    lines.append(f"\timmediate = {_block(ev.get('immediate', ''))}")

    # Options
    options = ev.get("options", defaults.get("options",
                     [{"name": "Acknowledged", "default": True, "ai_weight": 5}]))
    for i, opt in enumerate(options):
        letter = LETTERS[i] if i < len(LETTERS) else f"opt{i+1}"
        lines.append("")
        lines.append("\toption = {")
        lines.append(f"\t\tname = {opt.get('name_ref', f'{ns}.{eid}.{letter}')}")
        if opt.get("default", False):
            lines.append("\t\tdefault_option = yes")
        lines.append(f"\t\tai_chance = {{ base = {opt.get('ai_weight', 5)} }}")
        if "effects" in opt and opt["effects"].strip():
            for eline in opt["effects"].strip().splitlines():
                lines.append(f"\t\t{eline}")
        lines.append("\t}")

    # After
    if "after" in ev:
        lines.append(f"\tafter = {_block(ev['after'])}")

    lines.append("}")
    return "\n".join(lines)


def generate_loc(ns: str, ev: dict, defaults: dict) -> list:
    """Return loc entry lines (with leading space) for NEW keys only."""
    eid = ev["id"]
    entries = []

    if ev.get("hidden", False):
        return entries

    # Title
    if "title" in ev and "title_ref" not in ev:
        entries.append(f' {ns}.{eid}.t:0 "{ev["title"]}"')

    # Desc
    desc = ev.get("desc")
    if isinstance(desc, str):
        entries.append(f' {ns}.{eid}.d:0 "{desc}"')
    elif isinstance(desc, list):
        for i, item in enumerate(desc):
            if isinstance(item, dict) and "text" in item:
                key = item.get("key", f"{ns}.{eid}.d.{i + 1}")
                entries.append(f' {key}:0 "{item["text"]}"')

    # Flavor
    if "flavor" in ev and "flavor_ref" not in ev:
        entries.append(f' {ns}.{eid}.f:0 "{ev["flavor"]}"')

    # Options
    options = ev.get("options", defaults.get("options", []))
    for i, opt in enumerate(options):
        letter = LETTERS[i] if i < len(LETTERS) else f"opt{i+1}"
        if "name" in opt and "name_ref" not in opt:
            entries.append(f' {ns}.{eid}.{letter}:0 "{opt["name"]}"')

    return entries


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------

def cmd_next_id(args):
    ids = next_free_ids(args.namespace, after=args.after, count=args.count)
    used = find_used_ids(args.namespace)
    print(f"Namespace: {args.namespace}")
    if used:
        print(f"Used IDs ({len(used)}): {sorted(used)}")
    else:
        print("No existing IDs found.")
    print(f"Next {args.count} available after {args.after}: {ids}")


def cmd_batch(args):
    if args.spec == "-":
        spec = json.load(sys.stdin)
    else:
        with open(args.spec, encoding="utf-8") as f:
            spec = json.load(f)

    ns = spec["namespace"]
    out_rel = spec.get("output_file", f"events/{ns}.txt")
    out_path = MOD_ROOT / out_rel
    append = spec.get("append", False)
    defaults = spec.get("defaults", {})
    header = spec.get("header_comment", "")
    events = spec["events"]

    # Auto-assign IDs where missing
    used = find_used_ids(ns)
    auto_start = spec.get("auto_id_start", 0)
    for ev in events:
        if "id" not in ev:
            c = auto_start + 1
            while c in used:
                c += 1
            ev["id"] = c
            used.add(c)
            auto_start = c

    # Generate script blocks + loc entries
    blocks = [generate_event(ns, ev, defaults) for ev in events]
    all_loc = []
    for ev in events:
        all_loc.extend(generate_loc(ns, ev, defaults))

    # Assemble file content
    if append and out_path.exists():
        body = read_bom(out_path).rstrip() + "\n\n"
        if header:
            body += f"# {'=' * 65}\n# {header}\n# {'=' * 65}\n\n"
        body += "\n\n".join(blocks) + "\n"
    else:
        parts = [f"namespace = {ns}"]
        if header:
            parts.append(f"\n{'#' * 46}\n# {header}\n{'#' * 46}")
        parts.append("")
        parts.append("\n\n".join(blocks))
        body = "\n".join(parts) + "\n"

    ids_list = [ev["id"] for ev in events]
    id_range = f"{ns}.{min(ids_list)}-{ns}.{max(ids_list)}" if ids_list else "none"

    if args.dry_run:
        print(f"{'=' * 70}")
        print(f"EVENT FILE: {out_rel}")
        print(f"{'=' * 70}")
        print(body)
        if all_loc:
            print(f"\n{'=' * 70}")
            print(f"LOCALIZATION ({len(all_loc)} keys)")
            print(f"{'=' * 70}")
            for ln in all_loc:
                print(ln)
        print(f"\nSummary: {len(events)} events, {len(all_loc)} loc keys, IDs {id_range}")
    else:
        write_bom(out_path, body)
        print(f"Wrote {len(events)} events -> {out_rel}")
        if all_loc:
            loc = read_bom(LOC_FILE).rstrip() + "\n" + "\n".join(all_loc) + "\n"
            write_bom(LOC_FILE, loc)
            print(f"Appended {len(all_loc)} loc keys -> {LOC_FILE.name}")
            print("Run `python organize_loc.py` to sort.")
        print(f"IDs: {id_range}")


def cmd_scaffold(args):
    ev = {}
    if args.title:
        ev["title"] = args.title
    else:
        ev["title"] = "TODO: Event Title"
    if args.desc:
        ev["desc"] = args.desc
    else:
        ev["desc"] = "TODO: Event description."
    if args.flavor:
        ev["flavor"] = args.flavor
    else:
        ev["flavor"] = "TODO: Flavor text."
    if args.id:
        ev["id"] = args.id
    if args.image:
        ev["image"] = args.image
    if args.video:
        ev["video"] = args.video
    if args.icon:
        ev["icon"] = args.icon
    if args.hidden:
        ev["hidden"] = True
    if args.cooldown:
        ev["cooldown"] = args.cooldown
    if args.trigger:
        ev["trigger"] = args.trigger
    if args.immediate:
        ev["immediate"] = args.immediate
    if args.options:
        ev["options"] = [
            {"name": n, "default": i == 0, "ai_weight": 5}
            for i, n in enumerate(args.options)
        ]

    spec = {
        "namespace": args.namespace,
        "output_file": args.output or f"events/{args.namespace}.txt",
        "append": args.append,
        "events": [ev],
    }
    if args.type:
        spec["defaults"] = {"type": args.type}

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(spec, f, indent=2)
        tmp = f.name
    try:
        class BatchArgs:
            spec = tmp
            dry_run = args.dry_run
        cmd_batch(BatchArgs())
    finally:
        os.unlink(tmp)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser(
        description="Event scaffolding tool for Vic3TimelineExtended",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    # next-id
    ni = sub.add_parser("next-id", help="Find available event IDs in a namespace")
    ni.add_argument("namespace", help="Event namespace (e.g. space_race_events)")
    ni.add_argument("--after", type=int, default=0,
                    help="Start searching after this ID (default: 0)")
    ni.add_argument("--count", type=int, default=5,
                    help="Number of free IDs to show (default: 5)")

    # batch
    ba = sub.add_parser("batch", help="Generate events from a JSON spec file")
    ba.add_argument("spec", help="Path to JSON spec file, or - for stdin")
    ba.add_argument("--dry-run", action="store_true",
                    help="Print output without writing any files")

    # scaffold
    sc = sub.add_parser("scaffold", help="Generate a single event from CLI args")
    sc.add_argument("--namespace", required=True)
    sc.add_argument("--output", help="Output file (relative to mod root)")
    sc.add_argument("--append", action="store_true",
                    help="Append to existing file instead of overwriting")
    sc.add_argument("--id", type=int, help="Event ID (auto-assigned if omitted)")
    sc.add_argument("--type", help="Event type (default: country_event)")
    sc.add_argument("--title", help="Event title text")
    sc.add_argument("--desc", help="Event description text")
    sc.add_argument("--flavor", help="Flavor text")
    sc.add_argument("--image", help="Image key (without path/extension)")
    sc.add_argument("--video", help="Video name (use instead of --image)")
    sc.add_argument("--icon", help="Icon DDS path")
    sc.add_argument("--options", nargs="+", help="Option button texts")
    sc.add_argument("--cooldown", help="Cooldown block")
    sc.add_argument("--trigger", help="Trigger block content")
    sc.add_argument("--immediate", help="Immediate block content")
    sc.add_argument("--hidden", action="store_true", help="Hidden event")
    sc.add_argument("--dry-run", action="store_true")

    args = p.parse_args()
    {"next-id": cmd_next_id, "batch": cmd_batch, "scaffold": cmd_scaffold}[args.cmd](args)


if __name__ == "__main__":
    main()
