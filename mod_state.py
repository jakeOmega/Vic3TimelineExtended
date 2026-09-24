import copy
import logging
import os
from collections import defaultdict

from paradox_file_parser import ParadoxFileParser

# Parse/load diagnostics go through the logger rather than print() so the
# mod_state_server can route them into its console+file handlers (it attaches
# them to the "mod_state" logger at import time). CLI callers that want the
# per-file progress chatter can enable DEBUG on this logger.
logger = logging.getLogger(__name__)


def split_loc_line(line):
    r"""Return (key, value, trailing) for one Paradox localization line, or None.

    Accepts ` key:0 "value"`, ` key: "value"` and unindented forms. Returns
    None for blank lines, comment lines (first non-blank character `#`,
    indented or not), the `l_english:` header and any other line without a
    quoted value, lines whose key contains whitespace, and a quoted value
    that never closes (malformed). `value` is the exact source text between
    the opening quote and the first closing quote that is not escaped — a
    backslash escapes the character after it, so `\"` and `\n` are kept as
    written. `trailing` is everything after that closing quote (where
    `# REVIEWED ...` suppression comments live), without the line break. The
    old rule cut at the second `"` on the line, so `"He said \"go\""` read
    back as a lone backslash.
    """
    stripped = line.lstrip()
    if not stripped or stripped.startswith("#") or ":" not in stripped:
        return None
    key, rest = stripped.split(":", 1)
    key = key.strip()
    if not key or any(c.isspace() for c in key):
        return None
    start = rest.find('"')
    if start == -1:
        return None
    i = start + 1
    n = len(rest)
    while i < n:
        c = rest[i]
        if c == "\\":
            i += 2
            continue
        if c == '"':
            return key, rest[start + 1 : i], rest[i + 1 :].rstrip("\r\n")
        i += 1
    return None


def parse_loc_line(line):
    """Return (key, stripped value) for one localization line, or None — the
    rule ModState.add_localization and the server's loc parsers use. See
    split_loc_line for the line grammar."""
    parsed = split_loc_line(line)
    if parsed is None:
        return None
    key, value, _trailing = parsed
    return key, value.strip()


def iter_loc_lines(text):
    """Yield (key, value) for every parseable line of a loc file's text,
    using the same rule as ModState.add_localization (parse_loc_line)."""
    for line in text.splitlines():
        parsed = parse_loc_line(line)
        if parsed is not None:
            yield parsed


def iter_script_files(dir_path):
    """Yield the path of every `.txt` script file ModState parses under
    `dir_path`, recursing into subdirectories (e.g. events/), in sorted name
    order. Entries whose name starts with `_` (files or directories) and `.md`
    files are skipped. Sorted so the load order — and so the key order of the
    parsed data — is the same on every filesystem (`os.listdir` returns hash
    order on ext4); vanilla_parsed relies on this to build byte-identical
    snapshots on any machine."""
    for file_name in sorted(os.listdir(dir_path)):
        if file_name.startswith("_") or file_name.endswith(".md"):
            logger.debug("skipping file: %s", file_name)
            continue
        file_path = os.path.join(dir_path, file_name)
        if os.path.isdir(file_path):
            yield from iter_script_files(file_path)
        elif os.path.isfile(file_path) and file_name.endswith(".txt"):
            yield file_path


def iter_loc_files(loc_path):
    """Yield the path of every `.yml` file ModState.add_localization reads
    from `loc_path`, in sorted name order, recursing into subdirectories the
    way the engine does — vanilla keeps ~2,400 keys (state names, IG names,
    character names, ...) in english/map/, english/interest_groups/,
    english/character/, english/historical/ and english/frontend/. A `replace/`
    subdirectory is NOT descended into: its keys override every other file's,
    so callers load it separately, last."""
    for file_name in sorted(os.listdir(loc_path)):
        path = os.path.join(loc_path, file_name)
        if os.path.isdir(path):
            if file_name != "replace":
                yield from iter_loc_files(path)
        elif file_name.endswith(".yml"):
            yield path


# Vanilla entity types ModState loads for the mod state server, as
# {entity_type: directory relative to <base_game_path>/game/common, with
# forward slashes}. mod_state_server builds its absolute base_game_paths from
# this, and vanilla_parsed snapshots exactly these types — add a vanilla
# entity type here, not in the server.
VANILLA_COMMON_DIRS = {
    "Building Groups": "building_groups",
    "Buildings": "buildings",
    "Technologies": "technology/technologies",
    "PM Groups": "production_method_groups",
    "PMs": "production_methods",
    "Ideologies": "ideologies",
    "Battle Conditions": "battle_conditions",
    "Buy Packages": "buy_packages",
    "Character Interactions": "character_interactions",
    "Character Traits": "character_traits",
    "Combat Unit Groups": "combat_unit_groups",
    "Combat Unit Types": "combat_unit_types",
    "Company Types": "company_types",
    "Diplomatic Actions": "diplomatic_actions",
    "Diplomatic Plays": "diplomatic_plays",
    "Goods": "goods",
    "Government Types": "government_types",
    "Institutions": "institutions",
    "Interest Groups": "interest_groups",
    "Law Groups": "law_groups",
    "Laws": "laws",
    "Messages": "messages",
    "Mobilization Option Groups": "mobilization_option_groups",
    "Mobilization Options": "mobilization_options",
    "Modifier Types": "modifier_type_definitions",
    "Modifiers": "static_modifiers",
    "Pop Needs": "pop_needs",
    "Subject Types": "subject_types",
    "Script Values": "script_values",
    "Scripted Buttons": "scripted_buttons",
    "Ship Types": "ship_types",
    "Ship Groups": "ship_groups",
    "Ship Modifications": "ship_modifications",
    "Ship Modification Slots": "ship_modification_slots",
    "Ship Name Definitions": "ship_name_definitions",
    "Journal Entries": "journal_entries",
    "Journal Entry Groups": "journal_entry_groups",
    "Decisions": "decisions",
    "Country Formation": "country_formation",
    "Treaty Articles": "treaty_articles",
    "Religions": "religions",
    "Decrees": "decrees",
    "Principles": "power_bloc_principles",
    "Principle Groups": "power_bloc_principle_groups",
    "Amendments": "amendments",
    # Vocabularies the engine needs but the loader didn't include before:
    "Cultures": "cultures",
    "Country Ranks": "country_ranks",
    "Discrimination Traits": "discrimination_traits",
    "Pop Types": "pop_types",
    "Terrains": "terrain",
    "Game Concepts": "game_concepts",
}


class ModState:
    def __init__(self, base_game_dir, mod_dir, diff=False, vanilla_data=None):
        """Parse vanilla (`base_game_dir`, {entity_type: dir}) and layer the
        mod (`mod_dir`, same shape) on top.

        `vanilla_data` ({entity_type: parsed data}, e.g. from
        vanilla_parsed.load) replaces the vanilla parse: `base_game_dir` then
        only names the entity types to set up, and no vanilla file is read. A
        type missing from `vanilla_data` loads with empty vanilla data."""
        self.base_parsers = {}
        self.mod_parsers = {}
        self.localization = {}
        self._reverse_loc = None
        # Files that failed to parse during the most recent load, as
        # [{"file", "error", "source"}] with source in {"vanilla", "mod"}.
        # Surfaced by mod_state_server in /status and the POST /reload body so
        # a broken file can't hide behind an otherwise-successful reload (#242).
        self.parse_failures = []
        self.load_directory_files(base_game_dir, mod_dir, diff, vanilla_data)

    def add_localization(self, loc_path):
        for file_path in iter_loc_files(loc_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    for line in f:
                        parsed = parse_loc_line(line)
                        if parsed is None:
                            continue
                        key, value = parsed
                        self.localization[key] = value
            except Exception as e:
                logger.warning(f"Failed to read localization file {file_path}: {e}")
        # Invalidate reverse localization cache when new loc is added
        self._reverse_loc = None

    def load_directory_files(self, base_game_dir, mod_dir, diff=False, vanilla_data=None):
        for entity_type, dir_path in base_game_dir.items():
            self.base_parsers[entity_type] = ParadoxFileParser()
            self.mod_parsers[entity_type] = ParadoxFileParser()
            if vanilla_data is not None:
                data = vanilla_data.get(entity_type) or {}
                self.base_parsers[entity_type].data = data
                self.mod_parsers[entity_type].data = copy.deepcopy(data)
            elif not os.path.isdir(dir_path):
                logger.warning(f"Base game directory not found: {dir_path}")
                continue
            else:
                self.load_files_from_directory(entity_type, dir_path, base_game=True)

            if diff:
                self.mod_parsers[entity_type].set_data_from_changes_json(
                    self.base_parsers[entity_type],
                    mod_dir + os.sep + entity_type + ".json",
                )
            else:
                if entity_type in mod_dir:
                    mod_dir_path = mod_dir[entity_type]
                    if os.path.isdir(mod_dir_path):
                        self.load_files_from_directory(
                            entity_type, mod_dir_path, base_game=False
                        )
                    # else: mod has no override for this entity type — expected
                    # whenever a vanilla type is registered in mod_paths for
                    # forward-compat without an actual override on disk.
                    # Vanilla data is already loaded above, so this is benign.

        # Load mod-only entity types (not in base game)
        if not diff and isinstance(mod_dir, dict):
            for entity_type, dir_path in mod_dir.items():
                if entity_type not in base_game_dir:
                    self.base_parsers[entity_type] = ParadoxFileParser()
                    self.mod_parsers[entity_type] = ParadoxFileParser()
                    if os.path.isdir(dir_path):
                        self.load_files_from_directory(
                            entity_type, dir_path, base_game=False
                        )
                    else:
                        logger.warning(f"Mod-only directory not found: {dir_path}")

    def reload_mod(self, mod_dir):
        # Re-parse mod files in place, reusing the cached vanilla parse in
        # self.base_parsers. Caller is responsible for resetting/repopulating
        # self.localization (vanilla loc is cached at the server layer).
        # Drop the previous run's mod-side parse failures; every mod file is
        # about to be re-read. Vanilla entries stay — reload_mod reuses the
        # cached vanilla parse and never revisits those files.
        self.parse_failures = [
            f for f in self.parse_failures if f.get("source") != "mod"
        ]
        for entity_type, parser in self.base_parsers.items():
            fresh = ParadoxFileParser()
            fresh.data = copy.deepcopy(parser.data)
            self.mod_parsers[entity_type] = fresh
        if not isinstance(mod_dir, dict):
            return
        for entity_type, dir_path in mod_dir.items():
            if not os.path.isdir(dir_path):
                continue
            if entity_type not in self.mod_parsers:
                # Mod-only entity type with no vanilla side.
                self.mod_parsers[entity_type] = ParadoxFileParser()
                if entity_type not in self.base_parsers:
                    self.base_parsers[entity_type] = ParadoxFileParser()
            self.load_files_from_directory(entity_type, dir_path, base_game=False)

    def load_files_from_directory(self, entity_type, dir_path, base_game=True):
        for file_path in iter_script_files(dir_path):
            logger.debug("reading file: %s", file_path)
            try:
                if base_game:
                    self.base_parsers[entity_type].parse_file(file_path)
                    self.mod_parsers[entity_type].parse_file(file_path)
                else:
                    mod_data = self.parse_mod_file(file_path)
                    self.mod_parsers[entity_type].merge_data(mod_data)
            except Exception as e:
                logger.warning(
                    f"skipping file due to parse error: {file_path}: "
                    f"{type(e).__name__}: {e}"
                )
                self.parse_failures.append({
                    "file": file_path,
                    "error": f"{type(e).__name__}: {e}",
                    "source": "vanilla" if base_game else "mod",
                })

    def parse_mod_file(self, file_path):
        parser = ParadoxFileParser()
        parser.parse_file(file_path, apply_directives=False)
        return parser.data

    def get_data(self, entity_type):
        return (
            self.mod_parsers[entity_type].data
            if entity_type in self.mod_parsers
            else None
        )

    def get_string_form(self, entity_type):
        return (
            str(self.mod_parsers[entity_type])
            if entity_type in self.mod_parsers
            else None
        )

    def update_and_write_file(self, entity_type, file_path):
        if entity_type in self.mod_parsers:
            self.mod_parsers[entity_type].write_file(
                file_path, self.base_parsers[entity_type]
            )
        else:
            raise Exception(f"entity_type {entity_type} not found")

    def save_changes_to_json(self, file_path, entity_type=None):
        if entity_type is None:
            for entity_type in self.mod_parsers:
                self.mod_parsers[entity_type].save_changes_to_json(
                    self.base_parsers[entity_type],
                    file_path + os.sep + entity_type + ".json",
                )
        else:
            if entity_type in self.mod_parsers:
                self.mod_parsers[entity_type].save_changes_to_json(
                    self.base_parsers[entity_type], file_path
                )
            else:
                raise Exception(f"entity_type {entity_type} not found")

    def has_localization(self, text):
        return text in self.localization

    def localize(self, text):
        if text in self.localization:
            return self.localization[text]
        return text

    def get_description(self, text):
        desc_key = text + "_desc"
        if desc_key in self.localization:
            return self.localization[desc_key]
        return None

    def build_reverse_localization(self):
        """Build reverse mapping from display text (lowercase) to list of keys."""
        self._reverse_loc = defaultdict(list)
        for key, value in self.localization.items():
            self._reverse_loc[value.lower()].append(key)

    def unlocalize(self, text):
        """Find all localization keys that map to the given display text (case-insensitive)."""
        if self._reverse_loc is None:
            self.build_reverse_localization()
        return list(self._reverse_loc.get(text.lower(), []))

    def search_localization(self, query, limit=50):
        """Search localization keys and values for a substring (case-insensitive).

        Returns a list of {"key": ..., "value": ...} dicts.
        """
        query_lower = query.lower()
        results = []
        for key, value in self.localization.items():
            if query_lower in key.lower() or query_lower in value.lower():
                results.append({"key": key, "value": value})
                if len(results) >= limit:
                    break
        return results
