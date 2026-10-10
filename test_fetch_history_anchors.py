"""scripts/analysis/fetch_history_anchors.py: the stdlib xlsx reader, --from, and a failed download."""

import io
import sys
import tempfile
import unittest
import urllib.error
import zipfile
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))

import fetch_history_anchors as F  # noqa: E402

NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"


def tiny_xlsx(path, country="Testland", v1820="40.5", v1850="42"):
    """A Compact-style sheet: shared strings, a column past Z, an empty cell and an inline string."""
    shared = f'<sst xmlns="{NS}"><si><t>ccode</t></si><si><t>country name</t></si><si><t>{country}</t></si></sst>'
    sheet = (f'<worksheet xmlns="{NS}"><sheetData>'
             '<row r="1"><c r="A1" t="s"><v>0</v></c><c r="B1" t="s"><v>1</v></c>'
             '<c r="C1"><v>1820</v></c><c r="AA1"><v>1850</v></c></row>'
             '<row r="2"><c r="A2"><v>4.0</v></c><c r="B2" t="s"><v>2</v></c>'
             f'<c r="C2"><v>{v1820}</v></c><c r="D2"/><c r="E2" t="inlineStr"><is><t>note</t></is></c>'
             f'<c r="AA2"><v>{v1850}</v></c></row></sheetData></worksheet>')
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("xl/sharedStrings.xml", shared)
        z.writestr("xl/worksheets/sheet1.xml", sheet)


class TestReader(unittest.TestCase):
    def test_shared_strings_columns_past_z_and_empty_cells(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "t.xlsx"
            tiny_xlsx(p)
            rows = F.read_xlsx(p)
        self.assertEqual(rows[0][:3], ["ccode", "country name", "1820"])
        self.assertEqual(rows[0][26], "1850")
        self.assertEqual(rows[1][4], "note", "an inline string")
        self.assertEqual(list(F.long_rows("e0", rows)), [("e0", "Testland", 1820, 40.5), ("e0", "Testland", 1850, 42.0)])

    def test_from_a_directory_writes_the_long_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            for measure, name in F.SOURCES.items():
                tiny_xlsx(Path(tmp) / name.replace("(", "").replace(")", ""), country=measure)
            out = Path(tmp) / "anchors.csv"
            with redirect_stdout(io.StringIO()):
                self.assertEqual(F.main([str(out), "--from", tmp]), 0)
            lines = out.read_text(encoding="utf-8").splitlines()
        self.assertEqual(lines[0], "measure,country,year,value")
        self.assertIn("e0,e0,1820,40.5", lines)
        self.assertEqual(len(lines), 1 + 2 * len(F.SOURCES))

    def test_a_failed_download_exits_1_without_a_traceback(self):
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(F.urllib.request, "urlopen", side_effect=urllib.error.URLError("offline")):
            err = io.StringIO()
            with redirect_stderr(err):
                code = F.main([str(Path(tmp) / "anchors.csv"), "--download-dir", tmp])
        self.assertEqual(code, 1)
        self.assertIn("offline", err.getvalue())


if __name__ == "__main__":
    unittest.main()
