"""`scripts/analysis/flavor_forms.py`: the classes it reads from a flavor text's shape."""
import unittest

import scripts.analysis.flavor_forms as ff


class ClassifyTests(unittest.TestCase):
    def test_forms(self):
        cases = {
            r'\"One.\"\n\n\"Two.\"\n\n\"Three.\"': "exchange",
            r'\"I signed the counts because the storemen gave me the counts.\"': "one voice",
            r'\"The geysers are how we found the ocean.\"\n\n— A Name, Lead': "quotation",
            r'The guard read the papers.\n\n\"Not valid,\" he said.\n\nShe waited.\n\nThe queue grew.': "scene",
            r"The examiner worked along the bay.\n\nBy evening he had reached the far wall.": "narration",
        }
        for text, form in cases.items():
            self.assertEqual(ff.classify(text), form, text)

    def test_short_last_paragraph(self):
        self.assertTrue(ff.short_last_paragraph(r"A long first paragraph of the text.\n\n\"Very carefully.\""))
        self.assertFalse(ff.short_last_paragraph(r"Only one paragraph, however short."))
        self.assertFalse(ff.short_last_paragraph(
            r"First.\n\nThe second paragraph runs on well past twelve words, so it is no closing line built to land."))


class RepoTests(unittest.TestCase):
    def test_reads_the_mod_s_flavor(self):
        chains = ff.load()
        self.assertGreater(sum(len(v) for v in chains.values()), 1000)
        for entries in chains.values():
            for _, text in entries:
                self.assertIn(ff.classify(text), ff.FORMS)

    def test_row_marks_a_dominant_form(self):
        entries = [("k", r'\"A.\"\n\n\"B.\"')] * 6
        self.assertIn("exchange is 100%", ff.row("chain", entries))


if __name__ == "__main__":
    unittest.main()
