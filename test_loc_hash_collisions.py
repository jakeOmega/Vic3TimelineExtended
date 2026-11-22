"""No mod localization key may share the engine's hash with another key (log triage 2026-11-06).

The engine indexes localization by a 32-bit hash of the key: MurmurHash3 (x86, 32-bit, seed 0) of its UTF-8 bytes,
case-sensitive. Two keys with the same hash log one line at load,

    [pdx_localize.cpp:187]: Localization key hash collision. Key 'Ricchieri' and 'extra_law_events.42.f' have the
    same hash: 36017217.

and the one case seen lost a string: in the 2026-11-06 observer game, vanilla's Argentine general had no surname
(`No such localization key found for Character Ricchieri`, character_templates_utils.cpp:40), and the key sharing
his hash was the mod's event flavor text. The registry had filed both lines as harmless. The two pairs that load logged are
exactly the two this test finds, and the hash reproduces both values.

With about 145,000 keys loaded, a new key has roughly a 1 in 30,000 chance of a collision, so this is rare and
silent. Fix a failure by renaming the mod key (an event's `flavor`, an option's `name`); a key the engine derives
from an entity's name (a modifier's `_desc`) can only be dropped or have its entity renamed.
"""
import json
import os
import struct
import unittest
from collections import defaultdict
from pathlib import Path

from mod_state import iter_loc_files, iter_loc_lines

ROOT = Path(__file__).resolve().parent
VANILLA_LOC = ROOT / "vanilla_parsed" / "localization_english.json"
MOD_LOC = ROOT / "localization" / "english"

# hash -> the keys allowed to share it, with why. Empty: every pair found so far was renamed or dropped.
KNOWN = {}


def murmur3_32(data: bytes, seed: int = 0) -> int:
    c1, c2 = 0xCC9E2D51, 0x1B873593
    h = seed
    blocks = len(data) // 4
    for i in range(blocks):
        k = struct.unpack_from("<I", data, i * 4)[0]
        k = (k * c1) & 0xFFFFFFFF
        k = ((k << 15) | (k >> 17)) & 0xFFFFFFFF
        k = (k * c2) & 0xFFFFFFFF
        h ^= k
        h = ((h << 13) | (h >> 19)) & 0xFFFFFFFF
        h = (h * 5 + 0xE6546B64) & 0xFFFFFFFF
    tail = data[blocks * 4:]
    k = 0
    if len(tail) >= 3:
        k ^= tail[2] << 16
    if len(tail) >= 2:
        k ^= tail[1] << 8
    if tail:
        k ^= tail[0]
        k = (k * c1) & 0xFFFFFFFF
        k = ((k << 15) | (k >> 17)) & 0xFFFFFFFF
        k = (k * c2) & 0xFFFFFFFF
        h ^= k
    h ^= len(data)
    h ^= h >> 16
    h = (h * 0x85EBCA6B) & 0xFFFFFFFF
    h ^= h >> 13
    h = (h * 0xC2B2AE35) & 0xFFFFFFFF
    h ^= h >> 16
    return h


def _mod_keys() -> set:
    paths = list(iter_loc_files(str(MOD_LOC)))
    replace = MOD_LOC / "replace"
    if replace.is_dir():
        paths += sorted(str(p) for p in replace.glob("*.yml"))
    keys = set()
    for path in paths:
        text = Path(path).read_text(encoding="utf-8-sig")
        keys.update(key for key, _ in iter_loc_lines(text))
    return keys


def collisions():
    """{hash: sorted keys} for each hash two or more keys share, where one of them is the mod's."""
    vanilla = set(json.loads(VANILLA_LOC.read_text(encoding="utf-8")))
    mod = _mod_keys()
    by_hash = defaultdict(set)
    for key in vanilla | mod:
        by_hash[murmur3_32(key.encode("utf-8"))].add(key)
    return {h: sorted(keys) for h, keys in by_hash.items() if len(keys) > 1 and keys & mod}


class TestLocHashCollisions(unittest.TestCase):
    def test_the_hash_is_the_engines(self):
        # the two pairs the 2026-11-06 load logged, with the hashes it printed
        logged = {
            36017217: ("Ricchieri", "extra_law_events.42.f"),
            1528721154: ("state_building_thyssen_steelworks_max_level_add_desc", "TRIGGER_GOVERNMENT_LEGITIMACY_NOT"),
        }
        for value, keys in logged.items():
            for key in keys:
                with self.subTest(key=key):
                    self.assertEqual(murmur3_32(key.encode("utf-8")), value)

    def test_no_mod_key_shares_a_hash(self):
        self.assertTrue(VANILLA_LOC.is_file(), "vanilla_parsed/localization_english.json is missing")
        found = collisions()
        new = {h: keys for h, keys in found.items() if h not in KNOWN}
        self.assertEqual(new, {}, "a mod loc key shares the engine's hash with another key, so one of the two "
                                  "strings is lost in game: rename the mod key")
        self.assertEqual(sorted(set(KNOWN) - set(found)), [], "a KNOWN collision is gone: drop its entry")


if __name__ == "__main__":
    os.chdir(ROOT)
    unittest.main()
