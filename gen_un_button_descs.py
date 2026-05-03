# -*- coding: utf-8 -*-
"""Auto-generate localization for UN scripted button effect descriptions.

For each in-scope UN scripted_button, walk its effect block to collect
add_modifier / remove_modifier calls and change_variable un_authority deltas,
look up modifier values from common/static_modifiers/extra_modifiers.txt,
and emit a `*_EFFECTS` loc key that summarizes the mechanical effects.

The buttons' hand-written `*_DESC` keys reference $..._EFFECTS$ to splice
the auto-generated text into the narrative preamble — see UN_END_PEACEKEEPING_DESC.

Reads:
    common/scripted_buttons/un_buttons.txt
    common/static_modifiers/extra_modifiers.txt

Writes:
    localization/english/te_un_button_effects_l_english.yml

Runs as a post-load generator from mod_state_server.py (after
gen_pb_principle_unlock_descs and before organize_loc).

Usage:
    .venv/bin/python gen_un_button_descs.py             # write
    .venv/bin/python gen_un_button_descs.py --dry-run   # preview
"""

import argparse
import logging
import os
import re

from paradox_file_parser import ParadoxFileParser
from path_constants import mod_path

logger = logging.getLogger(__name__)

BUTTONS_FILE = os.path.join(
    mod_path, "common", "scripted_buttons", "un_buttons.txt"
)
MODIFIERS_FILE = os.path.join(
    mod_path, "common", "static_modifiers", "extra_modifiers.txt"
)
LOC_DIR = os.path.join(mod_path, "localization", "english")
OUTPUT_FILE = os.path.join(LOC_DIR, "te_un_button_effects_l_english.yml")

# Buttons whose effect block is dominated by add/remove_modifier + un_authority
# changes (vs vote-trigger / multi-country / event-firing). These get
# auto-generated effect summaries; other buttons keep fully hand-written descs.
IN_SCOPE_BUTTONS = {
    "un_arms_control_button",
    "un_withdraw_arms_control_button",
    "un_human_rights_resolution_button",
    "un_withdraw_human_rights_button",
    "un_fund_development_button",
    "un_defund_development_button",
    "un_peacekeeping_mission_button",
    "un_end_peacekeeping_button",
    "un_lift_sanctions_button",
    "un_champion_order_button",
    "un_stop_championing_button",
    "un_undermine_order_button",
    "un_stop_undermining_button",
}

# Modifiers we don't want surfaced in the EFFECTS text. Two flavors:
# - Cost modifiers added with a `multiplier = ...` field whose unit value isn't
#   the actual visible cost — the narrative preamble describes the recurring
#   expense scaled by un_program_expense_value.
# - Cooldown / marker modifiers that exist only as gating flags (no effects
#   beyond an icon) and aren't meaningful to surface as button consequences.
SKIP_MODIFIERS = {
    "un_peacekeeping_contributor_cost",
    "un_development_contributor_cost",
    "un_humanitarian_aid_cost",
    "un_peacekeeping_cooldown",
    "un_request_cooldown",
    "un_sanctions_cooldown",
}

MINUS = "−"  # Unicode minus (matches existing tooltip style)


# ---------- parsing ---------------------------------------------------------

def _value_of(node):
    """Unwrap (operator, value) tuples from ParadoxFileParser output."""
    if isinstance(node, tuple) and len(node) >= 2:
        return node[1]
    return node


def _walk_for_effects(node, found):
    """Recursively walk an effect-block subtree and collect:
        added_modifiers   — names of modifiers added without a `multiplier =`
        removed_modifiers — names of modifiers removed
        authority_delta   — net signed change applied to var:un_authority
    Skips contents of `limit` / `trigger` (conditions, not effects)."""
    if isinstance(node, list):
        for item in node:
            inner = _value_of(item)
            if isinstance(inner, (dict, list)):
                _walk_for_effects(inner, found)
        return
    if not isinstance(node, dict):
        return

    for key, raw_val in node.items():
        if key in ("limit", "trigger", "possible", "visible"):
            continue
        val = _value_of(raw_val)

        if isinstance(val, list):
            for v_item in val:
                _dispatch(key, _value_of(v_item), found)
        else:
            _dispatch(key, val, found)


def _dispatch(key, val, found):
    if key == "add_modifier":
        if isinstance(val, dict):
            name = _value_of(val.get("name"))
            # multiplier-driven cost modifiers list a unit value that's
            # not the actual visible cost — skip those (handled in narrative).
            if name and "multiplier" not in val:
                found["added_modifiers"].append(name)
        elif isinstance(val, str):
            found["added_modifiers"].append(val)
        return
    if key == "remove_modifier":
        if isinstance(val, str):
            found["removed_modifiers"].append(val)
        elif isinstance(val, dict):
            name = _value_of(val.get("name"))
            if name:
                found["removed_modifiers"].append(name)
        return
    if key == "change_variable":
        if isinstance(val, dict) and _value_of(val.get("name")) == "un_authority":
            delta = 0.0
            for op_key, sign in (("add", 1), ("subtract", -1)):
                op_val = _value_of(val.get(op_key))
                if op_val is None:
                    continue
                try:
                    delta += float(op_val) * sign
                except (TypeError, ValueError):
                    continue
            found["authority_delta"] += delta
        return
    # Recurse into scope hops, if/else, hidden_effect, custom_tooltip, etc.
    if isinstance(val, (dict, list)):
        _walk_for_effects(val, found)


def collect_button_effects():
    """Return {button_id: {desc_key, added_modifiers, removed_modifiers,
    authority_delta}} for every in-scope button."""
    parser = ParadoxFileParser()
    parser.parse_file(BUTTONS_FILE, apply_directives=False)
    out = {}
    for button_id, raw_entry in parser.data.items():
        if button_id not in IN_SCOPE_BUTTONS:
            continue
        entry = _value_of(raw_entry)
        if not isinstance(entry, dict):
            continue
        desc_raw = _value_of(entry.get("desc"))
        desc_key = (desc_raw.strip('"') if isinstance(desc_raw, str) else None)
        effect_block = _value_of(entry.get("effect"))
        if not isinstance(effect_block, dict):
            continue
        found = {
            "desc_key": desc_key,
            "added_modifiers": [],
            "removed_modifiers": [],
            "authority_delta": 0.0,
        }
        _walk_for_effects(effect_block, found)
        out[button_id] = found
    return out


def collect_modifier_effects():
    """Return {modifier_name: [(effect_key, value), ...]} from extra_modifiers."""
    parser = ParadoxFileParser()
    parser.parse_file(MODIFIERS_FILE, apply_directives=False)
    out = {}
    for name, raw_entry in parser.data.items():
        entry = _value_of(raw_entry)
        if not isinstance(entry, dict):
            continue
        effects = []
        for k, v in entry.items():
            if k == "icon":
                continue
            val = _value_of(v)
            try:
                effects.append((k, float(val)))
            except (TypeError, ValueError):
                continue
        if effects:
            out[name] = effects
    return out


# ---------- rendering -------------------------------------------------------

def _format_value(key, value):
    """Render one (modifier_effect_key, numeric_value) as the inline phrase
    matching the existing UN tooltip style: '+5% $key$' or '−25 $key$'."""
    sign = "+" if value > 0 else MINUS
    abs_v = abs(value)
    if 0 < abs_v < 1.0:
        # Heuristic: |v| < 1 → render as percent (covers _mult and _add modifiers
        # whose underlying unit is already a rate, like unit_kill_rate_add).
        pct = abs_v * 100
        num = f"{int(pct)}%" if pct == int(pct) else f"{pct:g}%"
    else:
        num = f"{int(abs_v)}" if abs_v == int(abs_v) else f"{abs_v:g}"
    return f"{sign}{num} ${key}$"


def _render_modifier_phrase(name, modifier_effects):
    """`[Concept('un_X_modifier','$un_X_modifier$')] (+5% $...$, −25 $...$, ...)`."""
    effects = modifier_effects.get(name, [])
    link = f"[Concept('{name}','${name}$')]"
    if not effects:
        return link
    rendered = ", ".join(_format_value(k, v) for k, v in effects)
    return f"{link} ({rendered})"


def render_effects_text(button_data, modifier_effects):
    """Compose the full $X_EFFECTS$ text for a button."""
    parts = []
    for name in button_data["added_modifiers"]:
        if name in SKIP_MODIFIERS:
            continue
        parts.append(f"Applies {_render_modifier_phrase(name, modifier_effects)}")
    for name in button_data["removed_modifiers"]:
        if name in SKIP_MODIFIERS:
            continue
        parts.append(f"Removes {_render_modifier_phrase(name, modifier_effects)}")

    delta = button_data["authority_delta"]
    if delta:
        sign = "+" if delta > 0 else MINUS
        color = "G" if delta > 0 else "R"
        delta_str = (
            f"{int(abs(delta))}" if abs(delta) == int(abs(delta)) else f"{abs(delta):g}"
        )
        parts.append(f"#{color} {sign}{delta_str} UN Authority#!")

    if not parts:
        return ""
    return ". ".join(p.rstrip(".") for p in parts) + "."


def effects_key_for(desc_key):
    """`UN_END_PEACEKEEPING_DESC` -> `UN_END_PEACEKEEPING_EFFECTS`."""
    if desc_key.endswith("_DESC"):
        return desc_key[: -len("_DESC")] + "_EFFECTS"
    return desc_key + "_EFFECTS"


def build_descriptions():
    button_effects = collect_button_effects()
    modifier_effects = collect_modifier_effects()
    descriptions = {}
    skipped = []
    missing_buttons = sorted(IN_SCOPE_BUTTONS - set(button_effects))
    for button_id, data in sorted(button_effects.items()):
        if not data["desc_key"]:
            skipped.append((button_id, "no desc field"))
            continue
        text = render_effects_text(data, modifier_effects)
        if not text:
            skipped.append((button_id, "no effects collected"))
            continue
        key = effects_key_for(data["desc_key"])
        descriptions[key] = text
    return descriptions, skipped, missing_buttons


# ---------- I/O -------------------------------------------------------------

_LOC_LINE_RE = re.compile(r"^\s*([\w\.\-]+)\s*:(.*)$")


def _read_existing_loc_lines():
    if not os.path.exists(OUTPUT_FILE):
        return {}
    out = {}
    with open(OUTPUT_FILE, "r", encoding="utf-8-sig") as f:
        for line in f:
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or stripped == "l_english:":
                continue
            m = _LOC_LINE_RE.match(line)
            if m:
                out[m.group(1)] = m.group(2).rstrip("\r\n")
    return out


def _format_yml(descriptions, preserved):
    lines = ["﻿l_english:"]
    all_keys = set(preserved) | set(descriptions)
    for key in sorted(all_keys):
        if key in descriptions:
            text = descriptions[key].replace('"', '\\"')
            lines.append(f' {key}:0 "{text}"')
        else:
            lines.append(f" {key}:{preserved[key]}")
    return "\n".join(lines) + "\n"


def _existing_keys_match(descriptions, preserved):
    on_disk = _read_existing_loc_lines()
    for k, text in descriptions.items():
        rendered = f'0 "{text.replace(chr(34), chr(92) + chr(34))}"'
        if on_disk.get(k) != rendered:
            return False
    for k, val in preserved.items():
        if on_disk.get(k) != val:
            return False
    for k in on_disk:
        if k.endswith("_EFFECTS") and k not in descriptions:
            return False
    return True


def write_output(descriptions, dry_run=False):
    existing_lines = _read_existing_loc_lines()
    preserved = {
        k: v for k, v in existing_lines.items() if not k.endswith("_EFFECTS")
    }
    if _existing_keys_match(descriptions, preserved):
        return False
    if dry_run:
        return True
    new_content = _format_yml(descriptions, preserved)
    with open(OUTPUT_FILE, "wb") as f:
        f.write(new_content.encode("utf-8"))
    return True


def regenerate(mod_state=None, dry_run=False):
    """Post-load entry point. mod_state arg unused (we parse source files directly)."""
    descriptions, skipped, missing = build_descriptions()
    for button_id, reason in skipped:
        logger.info("[gen_un_button_descs] skipped %s: %s", button_id, reason)
    for button_id in missing:
        logger.warning(
            "[gen_un_button_descs] in-scope button not found in source: %s",
            button_id,
        )
    wrote = write_output(descriptions, dry_run=dry_run)
    rel_path = os.path.relpath(OUTPUT_FILE, mod_path)
    if wrote:
        verb = "would write" if dry_run else "wrote"
        logger.info(
            "[gen_un_button_descs] %s %d keys to %s", verb, len(descriptions), rel_path
        )
    else:
        logger.info(
            "[gen_un_button_descs] no changes (%d keys, %s)", len(descriptions), rel_path
        )
    return descriptions


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true",
                    help="preview the planned output without writing")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )
    descs = regenerate(dry_run=args.dry_run)
    if args.dry_run:
        print(f"\n--- dry-run preview ({len(descs)} entries) ---")
        for key in sorted(descs):
            print(f' {key}:0 "{descs[key]}"')


if __name__ == "__main__":
    main()
