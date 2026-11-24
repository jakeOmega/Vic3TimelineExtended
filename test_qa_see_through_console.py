"""`scripts/analysis/qa_see_through_console.py`: the console copy a GUI-evaluation session loads.

The game's own file is not in the repo, so the test uses an invented one with the lines the script edits and the
decoys beside them.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "scripts" / "analysis"))
import qa_see_through_console as q  # noqa: E402

INVENTED = (
    "template editor_text\n{\n\tfontsize = 15\n}\n\n"
    "template ConsoleBackground\n{\n\tusing = clickthrough_blocker\n\n\ttexture = \"bg.dds\"\n"
    "\tmodify_texture = {\n\t\tusing = bg_tiling_pattern\n\t\talpha = 0.065\n\t}\n}\n\n"
    "template console_frame\n{\n\ttexture = \"frame.dds\"\n}\n\n"
    "flowcontainer = {\n\tname = \"console_window\"\n\talwaystransparent = no\n\tscissor = no\n\tlayer = confirmation\n"
    "\tusing = clickthrough_blocker\n\n\tmargin = { 10 10 }\n\n"
    "\tflowcontainer = {\n\t\tdirection = vertical\n\t\tspacing = 4\n\t\tbackground = {\n\t\t\tusing = ConsoleBackground\n"
    "\t\t\tmargin = { 8 8 }\n\t\t}\n\n"
    "\t\tscrollarea = {\n\t\t\tname = \"console_output_scrollarea\"\n\t\t\tsize = { 408 550 }\n\t\t}\n\n"
    "\t\teditbox = {\n\t\t\tbackground = {\n\t\t\t\tusing = ConsoleEditbg\n\t\t\t\tmargin = { 4 0 }\n\t\t\t}\n\n"
    "\t\t\tname = \"console_edit\"\n\t\t\tsize = { 408 40 }\n\t\t}\n\n"
    "\t\tflowcontainer = {\n\t\t\tname = \"toolbars_window\"\n\t\t\tmargin = { 1 10 }\n\t\t}\n\t}\n}\n"
)


class SeeThroughTest(unittest.TestCase):
    def test_every_edit_lands_and_the_edit_line_keeps_its_place(self):
        out = q.see_through(q.BOM + INVENTED.encode()).decode("utf-8-sig")
        self.assertNotIn("clickthrough_blocker", out)
        self.assertIn('name = "console_window"\n\talwaystransparent = yes', out)
        self.assertIn("spacing = 4\n\t\tignoreinvisible = no", out, "hidden children must keep their room, or the "
                      "edit line moves off the point click --console presses")
        self.assertIn('name = "console_output_scrollarea"\n\t\t\tvisible = no', out)
        self.assertIn('name = "toolbars_window"\n\t\t\tvisible = no', out)
        self.assertIn('name = "console_edit"\n\t\t\tsize = { 408 40 }', out, "the edit line itself is untouched")
        self.assertEqual(out.count("{"), out.count("}"))

    def test_bom_and_line_endings_are_kept(self):
        self.assertTrue(q.see_through(q.BOM + INVENTED.encode()).startswith(q.BOM))
        self.assertFalse(q.see_through(INVENTED.encode()).startswith(q.BOM))
        crlf = q.see_through(INVENTED.replace("\n", "\r\n").encode())
        self.assertEqual(crlf.count(b"\r\n"), crlf.count(b"\n"))

    def test_a_patched_file_stops_the_script(self):
        for old, _new, _count in q.EDITS:
            with self.subTest(old=old[:40]):
                with self.assertRaises(q.ConsoleFileChanged):
                    q.see_through(INVENTED.replace(old, "", 1).encode())

    def test_the_variant_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "console.gui"
            source.write_bytes(q.BOM + INVENTED.encode())
            folder = Path(tmp) / "variant"
            written = q.write_variant(folder, source, "1.15.2", "a name")
            self.assertEqual(len(written), 4)
            meta = json.loads((folder / ".metadata" / "metadata.json").read_text())
            self.assertEqual(meta["supported_game_version"], "1.15.2")
            for loc in folder.rglob("*.yml"):
                data = loc.read_bytes()
                self.assertTrue(data.startswith(q.BOM) and not data.startswith(q.BOM + q.BOM))
                self.assertIn(b"l_english:", data)

    def test_a_drive_path_becomes_its_wsl_path(self):
        self.assertEqual(q.wsl_path("D:\\vic3te-data\\v"), Path("/mnt/d/vic3te-data/v"))
        self.assertEqual(q.wsl_path("/mnt/d/x"), Path("/mnt/d/x"))


if __name__ == "__main__":
    unittest.main()
