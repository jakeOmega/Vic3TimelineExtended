"""Old-save repairs expire with the vanilla version they were written for.

A repair for saves made under an older mod version carries a marker line:

    # OLD-SAVE REPAIR (#547): remove after 2026-11-27 or at vanilla 1.15, whichever comes first.

This test fails once the committed vanilla snapshot (`vanilla_parsed/manifest.json`,
rebuilt in every vanilla-patch migration) reaches the marker's vanilla version,
so the migration PR is the one that removes the repair. The date is not checked
here, because a date would fail unrelated PRs on the day it passes; a scheduled
reminder covers it. See `common/on_actions/te_old_save_repairs.txt`.
"""
import json
import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
MANIFEST = os.path.join(REPO, "vanilla_parsed", "manifest.json")
SCAN_ROOTS = ("common", "events")

# A marker names a real issue number; the template in the repairs file's header
# (`#<issue>`) does not, so it is not a marker.
MARKER_START_RE = re.compile(r"OLD-SAVE REPAIR \(#\d")
MARKER_RE = re.compile(
    r"# OLD-SAVE REPAIR \(#(?P<issue>\d+)\): remove after (?P<date>\d{4}-\d{2}-\d{2})"
    r" or at vanilla (?P<version>\d+\.\d+), whichever comes first\."
)


def version_key(version):
    """(major, minor) of a "1.14.4"-style version; () when unparseable."""
    try:
        return tuple(int(p) for p in version.split(".")[:2])
    except (AttributeError, ValueError):
        return ()


def find_markers(root=REPO):
    """Every marker line under common/ and events/: (relpath, line, text)."""
    found = []
    for base in SCAN_ROOTS:
        for dirpath, _dirs, files in os.walk(os.path.join(root, base)):
            for fname in sorted(files):
                if not fname.endswith(".txt"):
                    continue
                path = os.path.join(dirpath, fname)
                with open(path, encoding="utf-8-sig", errors="replace") as fh:
                    for n, line in enumerate(fh, 1):
                        if MARKER_START_RE.search(line):
                            found.append((os.path.relpath(path, root), n, line.strip()))
    return found


def expired(markers, snapshot_version):
    """Markers whose vanilla version the snapshot has reached."""
    snap = version_key(snapshot_version)
    out = []
    for rel, n, text in markers:
        m = MARKER_RE.search(text)
        if m and snap and snap >= version_key(m.group("version")):
            out.append((rel, n, m.group("issue"), m.group("version")))
    return out


class OldSaveRepairTests(unittest.TestCase):
    def test_markers_are_well_formed(self):
        bad = [f"{rel}:{n}: {text}" for rel, n, text in find_markers() if not MARKER_RE.search(text)]
        self.assertEqual(bad, [], "a marker must read `# OLD-SAVE REPAIR (#N): remove after "
                                  "YYYY-MM-DD or at vanilla X.Y, whichever comes first.`")

    def test_no_repair_outlives_its_vanilla_version(self):
        if not os.path.exists(MANIFEST):
            self.skipTest("no vanilla_parsed/manifest.json")
        with open(MANIFEST, encoding="utf-8") as fh:
            snapshot = json.load(fh).get("game_version")
        late = expired(find_markers(), snapshot)
        self.assertEqual(
            late, [],
            f"vanilla_parsed is at {snapshot}: remove these old-save repairs "
            "(file, line, issue, vanilla version)",
        )

    def test_expiry_logic(self):
        marker = [("common/on_actions/x.txt", 3,
                   "# OLD-SAVE REPAIR (#1): remove after 2026-11-27 or at vanilla 1.15, whichever comes first.")]
        self.assertEqual(expired(marker, "1.14.4"), [])
        self.assertEqual(expired(marker, "1.15.0"), [("common/on_actions/x.txt", 3, "1", "1.15")])
        self.assertEqual(expired(marker, "2.0"), [("common/on_actions/x.txt", 3, "1", "1.15")])
        self.assertEqual(expired(marker, None), [])

    def test_the_repairs_file_marks_its_repair(self):
        # While the repairs file exists it holds at least one live repair, and
        # every one is marked, or nothing would ever say when to remove it.
        path = os.path.join(REPO, "common", "on_actions", "te_old_save_repairs.txt")
        if not os.path.exists(path):
            self.skipTest("no old-save repairs")
        with open(path, encoding="utf-8-sig") as fh:
            text = fh.read()
        repairs = re.findall(r"^(te_repair_\w+) = \{", text, re.MULTILINE)
        markers = MARKER_RE.findall(text)
        self.assertTrue(repairs, "an empty te_old_save_repairs.txt should be deleted")
        self.assertEqual(len(markers), len(repairs), f"repairs {repairs} vs {len(markers)} markers")


if __name__ == "__main__":
    unittest.main()
