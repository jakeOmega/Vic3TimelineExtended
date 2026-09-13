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


def parse_loc_line(line):
    r"""Return (key, value) for one Paradox localization line, or None.

    Accepts ` key:0 "value"`, ` key: "value"` and unindented forms. Returns
    None for blank lines, comment lines (first non-blank character `#`,
    indented or not), the `l_english:` header and any other line without a
    quoted value, and lines whose key contains whitespace. The value is the
    source text between the opening quote and the first closing quote that
    is not escaped — a backslash escapes the character after it — stripped
    and otherwise verbatim (`\"` and `\n` are kept as written). The old rule
    cut at the second `"` on the line, so `"He said \"go\""` read back as a
    lone backslash. A line whose quoted value never closes is malformed and
    skipped, matching the standalone loc audits' parsers.
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
            return key, rest[start + 1 : i].strip()
        i += 1
    return None


def iter_loc_lines(text):
    """Yield (key, value) for every parseable line of a loc file's text,
    using the same rule as ModState.add_localization (parse_loc_line)."""
    for line in text.splitlines():
        parsed = parse_loc_line(line)
        if parsed is not None:
            yield parsed


class ModState:
    def __init__(self, base_game_dir, mod_dir, diff=False):
        self.base_parsers = {}
        self.mod_parsers = {}
        self.localization = {}
        self._reverse_loc = None
        # Files that failed to parse during the most recent load, as
        # [{"file", "error", "source"}] with source in {"vanilla", "mod"}.
        # Surfaced by mod_state_server in /status and the POST /reload body so
        # a broken file can't hide behind an otherwise-successful reload (#242).
        self.parse_failures = []
        self.load_directory_files(base_game_dir, mod_dir, diff)

    def add_localization(self, loc_path):
        for file_name in os.listdir(loc_path):
            if not file_name.endswith(".yml"):
                continue
            file_path = os.path.join(loc_path, file_name)
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

    def load_directory_files(self, base_game_dir, mod_dir, diff=False):
        for entity_type, dir_path in base_game_dir.items():
            self.base_parsers[entity_type] = ParadoxFileParser()
            self.mod_parsers[entity_type] = ParadoxFileParser()
            if not os.path.isdir(dir_path):
                logger.warning(f"Base game directory not found: {dir_path}")
                continue
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
        for file_name in os.listdir(dir_path):
            if file_name.startswith("_") or (file_name[-3:] == ".md"):
                logger.debug("skipping file: %s", file_name)
                continue
            file_path = os.path.join(dir_path, file_name)
            if os.path.isdir(file_path):
                # Recurse into subdirectories (e.g. events/)
                self.load_files_from_directory(entity_type, file_path, base_game)
            elif os.path.isfile(file_path) and file_name.endswith(".txt"):
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
