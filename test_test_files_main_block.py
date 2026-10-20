"""Every test file runs as a script: `python3 test_<name>.py` (CLAUDE.md) runs its tests only if the file ends with an
`if __name__ == "__main__":` block. Seven files had none, so a direct run passed with no tests run, and
test_grand_monument_registry.py had one mid-file, so a direct run stopped at it with NameErrors (2026-10-20)."""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MAIN = re.compile(r"""^if __name__ == (["'])__main__\1:\s*$""")


class TestMainBlocks(unittest.TestCase):
    def test_every_test_file_ends_with_its_main_block(self):
        files = sorted(ROOT.glob("test_*.py"))
        self.assertGreater(len(files), 100)
        for path in files:
            with self.subTest(file=path.name):
                lines = path.read_text(encoding="utf-8").splitlines()
                at = [i for i, line in enumerate(lines) if MAIN.match(line)]
                self.assertEqual(len(at), 1, "one __main__ block")
                # nothing at the top level after it: a class or test defined below the block never runs as a script
                after = [line for line in lines[at[0] + 1:] if line[:1] not in ("", " ", "\t", "#")]
                self.assertEqual(after, [], "the __main__ block ends the file")


if __name__ == "__main__":
    unittest.main()
