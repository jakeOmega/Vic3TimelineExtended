"""Game rules for a session: what the fresh save was made under, and a rule switched in a copy of it (#1599).

Three facts, read from the harness's own saves on 2026-11-11 with no game running:

- **The fresh save is not made under the default rules.** An unattended new game (`-handsoff`) takes the rules the
  owner last applied in a lobby, `LastAppliedRules` in `player/game_rules/presets.txt` of the user-data folder.
  Both fixtures of that day carried Tax Code light, culture merges on and no fantastical content, none of them a
  default, and the Tax Code's light effects ran in a session made from one.
- **The fresh save is plain text** (`SAV0100…`, not the zipped binary of the owner's own saves), and it names the
  rule settings in force twice: `settings={ "" a b … }` inside `meta_data`'s `game_rules` block, and
  `setting={ "" a b … }` in the game state's own `game_rules` block.
- **The header's last eight hex digits are the byte length of the `meta_data` block**, which follows the header
  line. A change to that block's length has to be written there too.

So a rule can be switched with no click and no write to a file of the owner's: `switched_fixture` writes a copy
of the fixture, under its own fixture name, with one setting of each named rule replaced in both lists.

What that is and is not: the save is from 2 January 1836, so the copy is a game whose rule was switched a day
after it began, the same thing the change-country screen does mid-game. Whatever the game's setup decided
from the old setting has already happened. Rules that must hold from the first day need a fixture made under
them, which only a lobby of the owner's (or a write to their `presets.txt`, which nothing here does) gives.
Whether the mod treats an edited save exactly as it treats a rule changed in game is not verified.

Nothing here writes outside `save games/te_qa_fixture_*`: the copy is staged as `<name>.part` beside its final
name and renamed, and `presets.txt` is only ever read.
"""

from __future__ import annotations

import hashlib
import os
import re
from collections.abc import Mapping, Sequence
from pathlib import Path

from game_qa import fixture

PRESETS_FILE = "player/game_rules/presets.txt"
LAST_APPLIED = "LastAppliedRules"
RULES_FOLDER = "common/game_rules"
STAGED_SUFFIX = ".part"
SWITCHED_AT = "2 January 1836, the day after the game began: its setup ran under the old setting"

_NAME = re.compile(r"[A-Za-z0-9_]{1,80}")
_PRESET = re.compile(r'game_rules_preset\s*=\s*\{\s*name\s*=\s*"([^"]*)"\s*setting\s*=\s*\{([^{}]*)\}')
_META_LIST = re.compile(rb"\tgame_rules=\{\n\t\tsettings=\{([^{}\n]*)\}")
_STATE_LIST = re.compile(rb"\ngame_rules=\{\n\tsetting=\{([^{}\n]*)\}")
_HEADER = re.compile(rb"SAV[0-9a-f]{12}([0-9a-f]{8})")


class RulesError(Exception):
    """A rule, an option or a save this refuses. Nothing has been written."""


# --- the owner's last applied rules (read only) -----------------------------------------------


def last_applied(user_data: Path) -> list[str]:
    """The settings of `LastAppliedRules` in the user-data folder's presets file, in its order: what an
    unattended new game will be made under. An empty list when the file, or that preset, is not there (the game
    then uses each rule's default) or cannot be read; nothing is ever written."""
    try:
        text = (Path(user_data) / PRESETS_FILE).read_text(encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError):
        return []
    for name, settings in _PRESET.findall(text):
        if name == LAST_APPLIED:
            return settings.split()
    return []


# --- the rules the game loads ------------------------------------------------------------------


def rules_in(text: str) -> dict[str, dict]:
    """{rule: {"default": setting or None, "settings": [each setting, in order]}} for one game-rules file. A
    rule is a top-level block; a setting is a block directly inside it; `default = x` names the default."""
    rules: dict[str, dict] = {}
    depth = 0
    rule = None
    for token in _tokens(text):
        if token == "}":
            depth -= 1
            if depth <= 0:
                depth, rule = 0, None
            continue
        key, opens, value = token
        if depth == 0 and opens:
            rule = rules.setdefault(key, {"default": None, "settings": []})
            rule["settings"].clear()        # a rule defined again replaces the earlier one
            rule["default"] = None
        elif depth == 1 and rule is not None:
            if opens:
                rule["settings"].append(key)
            elif key == "default" and value:
                rule["default"] = value
        if opens:
            depth += 1
    return rules


def load_rules(folders: Sequence[Path]) -> dict[str, dict]:
    """The rules of every `.txt` file in `folders` (each a `common/game_rules` folder, vanilla's first), a later
    file of the same name replacing an earlier folder's, as the game loads a mod over vanilla."""
    files: dict[str, Path] = {}
    for folder in folders:
        try:
            names = sorted(os.listdir(folder))
        except OSError:
            continue
        for name in names:
            if name.endswith(".txt"):
                files[name] = Path(folder) / name
    rules: dict[str, dict] = {}
    for name in sorted(files):
        try:
            text = files[name].read_text(encoding="utf-8-sig")
        except (OSError, UnicodeDecodeError) as error:
            raise RulesError(f"{files[name]} could not be read ({error})") from error
        rules.update(rules_in(text))
    return rules


def _tokens(text: str):
    """`}` and (key, whether it opens a block, its value or None), comments and quoted strings set aside."""
    clean = []
    for line in text.splitlines():
        in_string, kept = False, []
        for char in line:
            if char == '"':
                in_string = not in_string
            elif char == "#" and not in_string:
                break
            kept.append(char)
        clean.append("".join(kept))
    pattern = re.compile(r'\}|([A-Za-z0-9_.:]+)\s*=\s*(\{|"[^"]*"|[^\s{}]+)|\{')
    for found in pattern.finditer("\n".join(clean)):
        if found.group(0) == "}":
            yield "}"
        elif found.group(0) == "{":
            yield ("", True, None)          # a block with no key still nests
        else:
            value = found.group(2)
            yield (found.group(1), value == "{", None if value == "{" else value.strip('"'))


# --- a save's rule lists -----------------------------------------------------------------------


def settings_of(data: bytes) -> list[str]:
    """The rule settings a plain-text save is in (the game state's list, which the `meta_data` list must
    repeat), without the empty first entry the game writes. RulesError for a save that is not plain text, or
    whose two lists are not each there exactly once and equal."""
    return _lists(data)[2]


def _lists(data: bytes) -> tuple[re.Match, re.Match, list[str]]:
    header = _header(data)
    meta_end = len(header.group(0)) + 1 + int(header.group(1), 16)
    # From the newline that ends meta_data, so a rule block right after it is found too.
    metas, states = list(_META_LIST.finditer(data, 0, meta_end)), list(_STATE_LIST.finditer(data, meta_end - 1))
    if len(metas) != 1 or len(states) != 1:
        raise RulesError(f"the save names its rule settings {len(metas)} time(s) in meta_data and {len(states)} "
                         "time(s) in the game state, not once in each: it is not a save this can read")
    meta, state = (_settings(m.group(1)) for m in (metas[0], states[0]))
    if meta != state:
        raise RulesError("the save's two rule lists differ, so which one the game reads is not known")
    return metas[0], states[0], state


def _header(data: bytes) -> re.Match:
    header = _HEADER.match(data)
    if header is None or data[header.end():header.end() + 1] != b"\n" or not data.startswith(b"SAV0100"):
        raise RulesError("the save is not a plain-text save (its first line is not `SAV0100…` and a length): "
                         "the harness's fresh save is one, the owner's own saves are zipped")
    return header


def _settings(raw: bytes) -> list[str]:
    return [t for t in raw.decode("utf-8", "replace").split() if t != '""']


def switch(data: bytes, switches: Mapping[str, str], rules: Mapping[str, dict]) -> tuple[bytes, dict[str, dict]]:
    """The save's bytes with each rule in `switches` ({rule: setting}) set to that setting in both lists, and
    {rule: {"from": the old setting, "to": the new}}. The header's length is rewritten for the new `meta_data`.

    RulesError, with nothing changed, for a rule the game's files do not define, a setting that is not one of
    that rule's, and a rule whose current setting is not in the save exactly once."""
    meta, state, current = _lists(data)
    changed: dict[str, dict] = {}
    new = list(current)
    for rule, option in sorted(switches.items()):
        known = rules.get(rule)
        if known is None:
            raise RulesError(f"no rule {rule!r} in the game's rule files; the rules are {', '.join(sorted(rules))}")
        if option not in known["settings"]:
            raise RulesError(f"{option!r} is not a setting of {rule}; its settings are "
                             f"{', '.join(known['settings'])}")
        held = [i for i, setting in enumerate(new) if setting in known["settings"]]
        if len(held) != 1:
            raise RulesError(f"the save holds {len(held)} setting(s) of {rule}, not one, so there is nothing "
                             "to switch safely")
        changed[rule] = {"from": new[held[0]], "to": option}
        new[held[0]] = option
    listed = (' "" ' + " ".join(new) + " ").encode("utf-8")
    header = _header(data)
    meta_start = header.end() + 1
    meta_len = int(header.group(1), 16)
    out_meta = data[meta_start:meta.start(1)] + listed + data[meta.end(1):meta_start + meta_len]
    out_rest = data[meta_start + meta_len:state.start(1)] + listed + data[state.end(1):]
    head = data[:header.start(1)] + b"%08x" % len(out_meta)
    return head + b"\n" + out_meta + out_rest, changed


# --- the switched fixture ----------------------------------------------------------------------


def switched_key(base_key: str, switches: Mapping[str, str]) -> str:
    """The fixture key of `base_key`'s fixture with `switches` applied: the base key, `_s` and eight hex digits
    of the switches. `fixture.prune` keeps a base and its switched copies apart by that `_s`."""
    digest = hashlib.sha256()
    for rule, option in sorted(switches.items()):
        digest.update(f"{rule}={option}\n".encode())
    return f"{base_key}{fixture.SWITCHED_MARK}{digest.hexdigest()[:8]}"


def check_switches(switches: Mapping[str, str]) -> None:
    """RulesError for a rule or setting name that could not be one (the names become part of a hash only, but a
    stray character means a mistyped argument)."""
    for rule, option in switches.items():
        for what in (rule, option):
            if not isinstance(what, str) or _NAME.fullmatch(what) is None:
                raise RulesError(f"a rule and its setting are names (letters, digits, _): {what!r}")


def switched_fixture(user_data: Path, base_key: str, switches: Mapping[str, str],
                     rules: Mapping[str, dict]) -> tuple[Path, dict[str, dict], list[str]]:
    """The fixture `base_key` with `switches` applied, as its own fixture file: (its path, what was switched,
    the settings it is now in). Made from the base fixture when it is not there yet; an existing one is read
    back, so the reply is always what the file holds.

    The copy is staged as `<name>.part` and renamed; a `.part` an earlier attempt left is removed first. Only
    files named `te_qa_fixture_*` are touched. RulesError, with nothing written, for whatever `switch` refuses
    and for a base fixture that is not there."""
    check_switches(switches)
    saves = Path(user_data) / fixture.SAVE_FOLDER
    base = saves / f"{fixture.FIXTURE_PREFIX}{base_key}.v3"
    target = saves / f"{fixture.FIXTURE_PREFIX}{switched_key(base_key, switches)}.v3"
    try:
        data = base.read_bytes()
    except OSError as error:
        raise RulesError(f"the fixture {base.name} could not be read ({error})") from error
    new, changed = switch(data, switches, rules)
    if target.is_file():
        try:
            held = settings_of(target.read_bytes())
        except (OSError, RulesError):
            held = None
        if held == settings_of(new):
            return target, changed, held
    staged = target.with_name(target.name + STAGED_SUFFIX)
    try:
        with open(staged, "wb") as handle:
            handle.write(new)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(staged, target)
    except OSError as error:
        raise RulesError(f"{target.name} could not be written ({error})") from error
    finally:
        if staged.exists():
            staged.unlink()
    return target, changed, settings_of(new)
