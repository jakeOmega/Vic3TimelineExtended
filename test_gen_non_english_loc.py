"""Unit tests for scripts/generators/gen_non_english_loc.py.

The game shows raw keys, not English, for a key the player's language lacks, so
deploy.sh stages one English copy per language. A copy has to be the English
file with only its header and file name changed, or the loader drops it.
"""
from __future__ import annotations

import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "scripts", "generators"))
sys.path.insert(0, os.path.join(_HERE, "scripts", "analysis"))
sys.path.insert(0, os.path.join(_HERE, "scripts", "i18n"))

import gen_non_english_loc as gen  # noqa: E402
from check_localization_files import check_file  # noqa: E402

BOM = "﻿"
EVENTS = BOM + '# comment\nl_english:\n TE_A:0 "Alpha l_english: stays"\n'
OVERRIDE = BOM + 'l_english:\n coal:0 "Energy and Carbon Minerals"\n'


def _write(root: str, rel: str, text: str) -> None:
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)


def _read(root: str, rel: str) -> str:
    with open(os.path.join(root, rel), encoding="utf-8", newline="") as fh:
        return fh.read()


class RenderTests(unittest.TestCase):
    def test_only_the_header_line_changes(self):
        out = gen.render(EVENTS.encode("utf-8"), "german").decode("utf-8")
        self.assertEqual(out, EVENTS.replace("\nl_english:\n", "\nl_german:\n"))
        self.assertTrue(out.startswith(BOM))
        self.assertIn('"Alpha l_english: stays"', out)

    def test_header_on_the_bom_line(self):
        out = gen.render(OVERRIDE.encode("utf-8"), "french").decode("utf-8")
        self.assertTrue(out.startswith(BOM + "l_french:\n"))

    def test_missing_header_is_an_error(self):
        with self.assertRaises(gen.LocSourceError):
            gen.render((BOM + 'l_french:\n A:0 "a"\n').encode("utf-8"), "german")
        with self.assertRaises(gen.LocSourceError):
            gen.render(b"\n# only a comment\n", "german")


class OutputPathTests(unittest.TestCase):
    def test_suffix_and_folder(self):
        self.assertEqual(
            gen.output_relpath("te_events_l_english.yml", "simp_chinese"),
            os.path.join("simp_chinese", "te_events_l_simp_chinese.yml"),
        )

    def test_replace_subfolder_is_kept(self):
        self.assertEqual(
            gen.output_relpath(os.path.join("replace", "x_l_english.yml"), "german"),
            os.path.join("german", "replace", "x_l_german.yml"),
        )

    def test_misnamed_source_is_an_error(self):
        with self.assertRaises(gen.LocSourceError):
            gen.output_relpath("te_events.yml", "german")


class BuildTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.src = os.path.join(self.tmp.name, "english")
        self.out = os.path.join(self.tmp.name, "out")
        _write(self.src, "te_events_l_english.yml", EVENTS)
        _write(self.src, os.path.join("replace", "over_l_english.yml"), OVERRIDE)

    def tearDown(self):
        self.tmp.cleanup()

    def _build(self):
        return gen.build(english_dir=self.src, out_dir=self.out)

    def test_every_language_gets_every_file(self):
        result = self._build()
        self.assertEqual(len(result.written), 2 * len(gen.LANGUAGES))
        for language in gen.LANGUAGES:
            text = _read(self.out, os.path.join(language, f"te_events_l_{language}.yml"))
            self.assertEqual(text, EVENTS.replace("\nl_english:\n", f"\nl_{language}:\n"))
            self.assertTrue(os.path.isfile(os.path.join(
                self.out, language, "replace", f"over_l_{language}.yml")))

    def test_second_run_writes_nothing(self):
        self._build()
        path = os.path.join(self.out, "german", "te_events_l_german.yml")
        os.utime(path, (1_000_000, 1_000_000))
        result = self._build()
        self.assertEqual(result.written, [])
        self.assertEqual(result.unchanged, 2 * len(gen.LANGUAGES))
        self.assertEqual(os.stat(path).st_mtime, 1_000_000)

    def test_changed_source_rewrites_only_its_copies(self):
        self._build()
        _write(self.src, "te_events_l_english.yml", EVENTS.replace("Alpha", "Beta"))
        result = self._build()
        self.assertEqual(len(result.written), len(gen.LANGUAGES))
        self.assertTrue(all("te_events" in rel for rel in result.written))

    def test_deleted_source_prunes_its_copies_and_empty_folders(self):
        self._build()
        os.remove(os.path.join(self.src, "replace", "over_l_english.yml"))
        os.rmdir(os.path.join(self.src, "replace"))
        result = self._build()
        self.assertEqual(len(result.removed), len(gen.LANGUAGES))
        self.assertFalse(os.path.exists(os.path.join(self.out, "german", "replace")))
        self.assertTrue(os.path.isdir(os.path.join(self.out, "german")))

    def test_files_outside_the_language_folders_are_left_alone(self):
        _write(self.out, "english/keep_l_english.yml", EVENTS)
        _write(self.out, "notes.txt", "x")
        self._build()
        self.assertTrue(os.path.isfile(os.path.join(self.out, "english", "keep_l_english.yml")))
        self.assertTrue(os.path.isfile(os.path.join(self.out, "notes.txt")))

    def test_bad_source_writes_nothing(self):
        _write(self.src, "stray.yml", EVENTS)
        with self.assertRaises(gen.LocSourceError):
            self._build()
        self.assertFalse(os.path.exists(self.out))


class OverlayTests(unittest.TestCase):
    """A language with a translation memory ships its translations in place."""

    SOURCE = BOM + (
        'l_english:\n'
        ' AFU:0 "African Union" # kept comment\n'
        ' law_x:1 "Raises the price of grain by 10% for two years."\n'
        ' law_y:0 "Lowers wages by 5%."\n'
        ' law_z:0 "Brand new text"\n'
    )

    def _overlay(self):
        import translate_loc

        tm = {
            "AFU": {"en": "African Union", "de": "Afrikanische Union"},
            "AFU_NOM": {"en": "African Union", "de": "die Afrikanische Union", "base": "AFU"},
            "AFU_DAT": {"en": "African Union", "de": "der Afrikanischen Union", "base": "AFU"},
            # English since tweaked: old German kept.
            "law_x": {"en": "Raises the price of grain by 10% for the next two years.", "de": "Erhöht …"},
            # English number changed: English ships until retranslated.
            "law_y": {"en": "Lowers wages by 3%.", "de": "Senkt die Löhne um 3 %."},
        }
        return translate_loc.Overlay(tm, "de")

    def test_values_swapped_in_place_and_forms_follow_their_key(self):
        overlay = self._overlay()
        out = gen.render(self.SOURCE.encode("utf-8"), "german", overlay=overlay).decode("utf-8")
        self.assertEqual(out, BOM + (
            'l_german:\n'
            ' AFU:0 "Afrikanische Union" # kept comment\n'
            ' AFU_NOM:0 "die Afrikanische Union"\n'
            ' AFU_DAT:0 "der Afrikanischen Union"\n'
            ' law_x:1 "Erhöht …"\n'
            ' law_y:0 "Lowers wages by 5%."\n'
            ' law_z:0 "Brand new text"\n'
        ))
        self.assertEqual(overlay.counts["translated"], 1)
        self.assertEqual(overlay.counts["stale_kept"], 1)
        self.assertEqual(overlay.counts["stale_english"], 1)
        self.assertEqual(overlay.counts["english"], 1)

    def test_forms_dropped_when_the_base_name_changed(self):
        source = BOM + 'l_english:\n AFU:0 "Pan-African Union"\n'
        out = gen.render(source.encode("utf-8"), "german", overlay=self._overlay()).decode("utf-8")
        self.assertEqual(out, BOM + 'l_german:\n AFU:0 "Pan-African Union"\n')


class CliTests(unittest.TestCase):
    def test_list_languages(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.assertEqual(gen.main(["--list-languages"]), 0)
        names = buf.getvalue().split()
        self.assertEqual(tuple(names), gen.LANGUAGES)
        self.assertNotIn("english", names)


class RepoTreeTests(unittest.TestCase):
    def test_repo_copies_pass_the_ci_loc_check(self):
        """Every staged copy of the real English tree must pass the checks CI
        runs on English: BOM, a header matching the file name, no duplicates."""
        with tempfile.TemporaryDirectory() as out:
            result = gen.build(out_dir=out, overlays=gen.load_overlays())
            english = gen.iter_english_files(gen.ENGLISH_DIR)
            self.assertEqual(len(result.written), len(english) * len(gen.LANGUAGES))
            problems = []
            for rel in result.written:
                problems.extend(check_file(os.path.join(out, rel)))
            self.assertEqual(problems, [], "\n".join(problems[:20]))


if __name__ == "__main__":
    unittest.main()
