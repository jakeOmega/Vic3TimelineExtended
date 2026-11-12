"""Each events file declares exactly one `namespace` (#1403).

`events/te_monetary_arrangement_events.txt` declared two, `te_lolr` and, 240
lines down, `te_union`. The parser reads a file's top level as a map, so it
kept the second and warned `top-level key(s) defined more than once: namespace`
on every server start; and nothing in the mod, its docs or the vanilla
snapshot (which holds no events) shows what the engine does with the second
line. The common currency's events moved to
`events/te_monetary_union_events.txt`.
"""

import glob
import logging
import os
import re
import unittest

from paradox_file_parser import ParadoxFileParser

REPO = os.path.dirname(os.path.abspath(__file__))
EVENT_FILES = sorted(glob.glob(os.path.join(REPO, "events", "*.txt")))

_NAMESPACE = re.compile(r"^namespace\s*=\s*(\S+)", re.MULTILINE)
_EVENT_ID = re.compile(r"^([A-Za-z_]\w*)\.\d+\s*=\s*\{", re.MULTILINE)


def _read(path: str) -> str:
    with open(path, encoding="utf-8-sig") as fh:
        return fh.read()


class OneNamespacePerFile(unittest.TestCase):
    def test_every_events_file_declares_one_namespace(self):
        self.assertTrue(EVENT_FILES)
        wrong = {
            os.path.basename(path): names
            for path in EVENT_FILES
            if len(names := _NAMESPACE.findall(_read(path))) != 1
        }
        self.assertEqual(wrong, {}, "split the file: one namespace each")

    def test_every_event_is_in_its_files_namespace(self):
        wrong = {}
        for path in EVENT_FILES:
            text = _read(path)
            declared = set(_NAMESPACE.findall(text))
            stray = sorted(set(_EVENT_ID.findall(text)) - declared)
            if stray:
                wrong[os.path.basename(path)] = stray
        self.assertEqual(wrong, {})

    def test_the_monetary_arrangement_events_were_split_by_namespace(self):
        homes = {
            "te_monetary_arrangement_events.txt": ("te_lolr", {"te_lolr.1", "te_lolr.2"}),
            "te_monetary_union_events.txt": ("te_union", {"te_union.1", "te_union.2"}),
        }
        for name, (namespace, events) in homes.items():
            with self.subTest(file=name):
                path = os.path.join(REPO, "events", name)
                with open(path, "rb") as fh:
                    raw = fh.read()
                self.assertEqual(raw.count(b"\xef\xbb\xbf"), 1)
                self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))
                parser = ParadoxFileParser()
                # The warning the server logged on every start.
                with self.assertNoLogs("paradox_file_parser", level=logging.WARNING):
                    parser.parse_file(path)
                self.assertEqual(parser.data.get("namespace"), ("=", namespace))
                self.assertEqual(set(parser.data) - {"namespace"}, events)


if __name__ == "__main__":
    unittest.main()
