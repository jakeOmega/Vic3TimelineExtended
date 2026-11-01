"""Every country tag the mod defines has a name and an adjective in English loc.

The engine reads `TAG` and `TAG_ADJ` for each entry in
common/country_definitions/ without any script naming them, and logs nothing
when either is missing: the country shows its raw tag, or a blank where its
adjective goes (war names, treaties, "the X Army"). The 22 city-states of #1266
shipped with names and no adjectives that way. Dynamic definitions
(`dynamic_country_definition = yes`, the E00-E99 pool) are exempt: a dynamic
country takes its name from the script that creates it.
"""

import glob
import os
import re
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))

_TAG_RE = re.compile(r"^([A-Z][A-Z0-9]{2})\s*=\s*\{(.*)$", re.MULTILINE)
_LOC_KEY_RE = re.compile(r"^\s*([A-Za-z0-9_.\-]+):\d*\s*\"")


def mod_country_tags() -> dict[str, str]:
    """Tag -> file for every non-dynamic tag in common/country_definitions/."""
    tags = {}
    for path in sorted(glob.glob(os.path.join(ROOT, "common", "country_definitions", "*.txt"))):
        with open(path, encoding="utf-8-sig") as f:
            text = f.read()
        for m in _TAG_RE.finditer(text):
            if "dynamic_country_definition" in m.group(2):
                continue
            tags[m.group(1)] = os.path.basename(path)
    return tags


def english_loc_keys() -> set[str]:
    keys = set()
    for path in glob.glob(os.path.join(ROOT, "localization", "english", "**", "*.yml"), recursive=True):
        with open(path, encoding="utf-8-sig") as f:
            for line in f:
                m = _LOC_KEY_RE.match(line)
                if m:
                    keys.add(m.group(1))
    return keys


class CountryDefinitionLocTest(unittest.TestCase):
    def test_every_tag_has_name_and_adjective(self):
        tags = mod_country_tags()
        self.assertGreater(len(tags), 20, "found too few country definitions; the scan is broken")
        keys = english_loc_keys()
        missing = [
            f"{file}: {key}"
            for tag, file in sorted(tags.items())
            for key in (tag, f"{tag}_ADJ")
            if key not in keys
        ]
        self.assertEqual(missing, [], "country tags with no English name or adjective")

    def test_dynamic_pool_is_skipped(self):
        # The E00-E99 pool has no loc and needs none.
        self.assertNotIn("E00", mod_country_tags())


if __name__ == "__main__":
    unittest.main()
