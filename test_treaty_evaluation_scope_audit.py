"""Regression coverage for issue #521's silent treaty proposal failures."""
import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from paradox_file_parser import ParadoxFileParser
from treaty_evaluation_scope_audit import audit, main, scan_text


class ScanTests(unittest.TestCase):
    def test_nested_and_scalar_reads_with_exact_lines(self):
        text = ('a = { ai = { evaluation_chance = {\n'
                ' value = 0\n'
                ' if = { limit = { exists = scope:other_country\n'
                ' scope:other_country = { always = yes } } add = 0.1 }\n'
                ' add = scope:source_country.country_rank\n'
                '} } }')
        flags = scan_text(text, 'test.txt')
        self.assertEqual([(f.article, f.line, f.scope) for f in flags],
                         [('a', 3, 'scope:other_country'), ('a', 4, 'scope:other_country'),
                          ('a', 5, 'scope:source_country')])

    def test_comments_strings_and_other_fields(self):
        text = '''a = {
 possible = { scope:other_country = { always = yes } }
 ai = {
  evaluation_chance = { value = 0.1 # scope:other_country = { }
   if = { limit = { country_rank >= rank_value:major_power } add = 0.05 }
  }
  inherent_accept_score = { value = scope:article.source_country.country_rank }
  quantity_input_value = { value = scope:other_country.gdp }
 }
}'''
        self.assertEqual(scan_text(text, 'test.txt'), [])

    def test_quoted_function_argument_is_a_read(self):
        text = ('a = { ai = { evaluation_chance = { '
                'value = "num_shared_rivals(scope:other_country)" } } }')
        self.assertEqual([f.scope for f in scan_text(text, 'test.txt')], ['scope:other_country'])

    def test_multi_article_bom_and_braces_inside_quotes(self):
        text = ('\ufeffa = { icon = "{ }" ai = { evaluation_chance = { value = 0.1 } } }\n'
                'b = { ai = { evaluation_chance = { value = scope:article.cost } } }\n'
                'REPLACE:c = { ai = { evaluation_chance = { scope:first_country = { add = 1 } } } }')
        self.assertEqual([(f.article, f.line) for f in scan_text(text, 'test.txt')],
                         [('b', 2), ('REPLACE:c', 3)])

    def test_strict_cli_and_recursive_walk(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'common/treaty_articles/nested/a.txt'
            path.parent.mkdir(parents=True)
            path.write_text('a = { ai = { evaluation_chance = { value = scope:other_country.gdp } } }',
                            encoding='utf-8-sig')
            self.assertEqual(audit(tmp)[0].file, 'common/treaty_articles/nested/a.txt')
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(['--mod-path', tmp, '--strict']), 1)
                self.assertEqual(main(['--mod-path', tmp]), 0)
                path.write_text('a = { ai = { evaluation_chance = { value = 0.1 } } }')
                self.assertEqual(main(['--mod-path', tmp, '--strict']), 0)


class ModTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parent
        cls.parser = ParadoxFileParser()
        for path in (cls.root / 'common/treaty_articles').glob('*.txt'):
            cls.parser.parse_file(str(path), False)

    def test_all_proposal_checks_are_root_only(self):
        self.assertEqual(audit(self.root), [])

    def test_formerly_fatal_articles_have_positive_base_chances(self):
        for article in ('disband_company', 'seize_company', 'nuclear_disarmament',
                        'nuclear_program_pause'):
            with self.subTest(article=article):
                entity = self.parser.data[article][1]
                chance = entity['ai'][1]['evaluation_chance'][1]
                self.assertGreater(float(chance['value'][1]), 0)

    def test_monetary_frequency_cap_stays_last(self):
        for article in ('currency_peg', 'imposed_currency_peg', 'debt_receivership'):
            with self.subTest(article=article):
                chance = self.parser.data[article][1]['ai'][1]['evaluation_chance'][1]
                self.assertEqual(list(chance)[-1], 'multiply')
                self.assertEqual(chance['multiply'], ('=', '0.25'))


if __name__ == '__main__':
    unittest.main()
