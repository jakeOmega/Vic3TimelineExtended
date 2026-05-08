"""Generate `docs/engine/event_image_inventory.md` — every mod event's title,
description, flavor, and current image. Used to drive custom event-image
generation.

Auto-runs after every full `mod_state_server` reload via
`POST_LOAD_GENERATORS`. Standalone usage:
    .venv/bin/python gen_event_inventory.py
"""
import os
import re
from collections import defaultdict


def _entity_data(entity):
    """Unwrap a ('=', {...}) entity tuple to the inner data dict.

    Mirrors mod_state_server.get_entity_data; duplicated here so this
    module has no dependency on the server.
    """
    if isinstance(entity, tuple) and len(entity) >= 2:
        data = entity[1]
    else:
        data = entity
    if isinstance(data, list):
        flat = {}
        for item in data:
            if isinstance(item, dict):
                flat.update(item)
        return flat
    return data


def _field(data, key, default=None):
    val = data.get(key) if isinstance(data, dict) else None
    if val is None:
        return default
    if isinstance(val, tuple) and len(val) >= 2:
        return val[1]
    return val


def _event_image(ed):
    """Return the texture/video string for an event's `event_image` block, or None."""
    event_image = _field(ed, "event_image")
    if isinstance(event_image, dict):
        video = _field(event_image, "video")
        if video:
            return video.strip('"')
        texture = _field(event_image, "texture")
        if texture:
            return texture.strip('"')
    return None


def _load_localization(mod_path):
    loc = {}
    loc_dir = os.path.join(mod_path, "localization", "english")
    for root, _dirs, files in os.walk(loc_dir):
        for fn in files:
            if not fn.endswith(".yml"):
                continue
            fp = os.path.join(root, fn)
            try:
                with open(fp, "r", encoding="utf-8-sig") as f:
                    for line in f:
                        m = re.match(r'^\s+(\S+?):\d+\s+"(.*)"', line)
                        if m:
                            loc[m.group(1)] = m.group(2)
            except Exception:
                pass
    return loc


def _event_files_in_order(events_dir):
    """Map event-file basename → ordered list of event IDs declared in it."""
    event_files = defaultdict(list)
    for fn in sorted(os.listdir(events_dir)):
        if not fn.endswith(".txt"):
            continue
        fp = os.path.join(events_dir, fn)
        with open(fp, "r", encoding="utf-8-sig") as f:
            content = f.read()
        for m in re.finditer(r"^(\S+\.\d+)\s*=\s*\{", content, re.MULTILINE):
            event_files[fn].append(m.group(1))
    return event_files


def regenerate(mod_state=None):
    if mod_state is None:
        from mod_state import ModState
        from mod_state_script import base_game_paths, mod_paths
        mod_state = ModState(base_game_paths, mod_paths)

    from path_constants import mod_path

    events_raw = mod_state.get_data("Events") or {}
    images_by_id = {}
    for eid, raw in events_raw.items():
        if eid == "namespace":
            continue
        ed = _entity_data(raw)
        img = _event_image(ed)
        if img:
            images_by_id[eid] = img

    loc = _load_localization(mod_path)
    event_files = _event_files_in_order(os.path.join(mod_path, "events"))

    output = []
    output.append("# Event Image Generation Inventory")
    output.append("")
    output.append("This document inventories all mod events for the purpose of generating custom event images.")
    output.append("Each event is listed with its title, description, and flavor text (where available).")
    output.append("")
    total = sum(len(v) for v in event_files.values())
    output.append(f"**Total events:** {total}")
    output.append(f"**Event files:** {len(event_files)}")
    output.append("")

    for fn in sorted(event_files.keys()):
        output.append(f"## {fn}")
        output.append("")
        for eid in event_files[fn]:
            title = loc.get(eid + ".t", "(no localization)")
            desc = loc.get(eid + ".d", "(no localization)")
            flavor = loc.get(eid + ".f", "(none)")
            img = images_by_id.get(eid, "(unknown)")
            output.append(f"### {eid}")
            output.append(f"- **Title:** {title}")
            output.append(f"- **Description:** {desc}")
            output.append(f"- **Flavor:** {flavor}")
            output.append(f"- **Current image:** {img}")
            output.append("")

    out_path = os.path.join(mod_path, "docs", "engine", "event_image_inventory.md")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(output))

    return {"events": total, "files": len(event_files), "path": out_path}


def main():
    result = regenerate()
    print(f"Wrote {result['events']} events across {result['files']} files → {result['path']}")


if __name__ == "__main__":
    main()
