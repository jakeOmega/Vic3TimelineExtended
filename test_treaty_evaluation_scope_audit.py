"""Regression coverage for issue #521's silent treaty proposal failures, and
for #1026's party scopes read in a block that does not bind them."""
import contextlib
import io
import json
import re
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from paradox_file_parser import ParadoxFileParser
from treaty_evaluation_scope_audit import UNBOUND, audit, main, scan_text, unreviewed


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


# Extensive Modernization Aid as it shipped from May 2026 until #1025: both
# branches of the requirement name the partner by a scope `can_ratify` never has.
SCIENCE_AID_2 = '''science_aid_2 = {
	kind = directed
	possible = {
		scope:other_country = { NOT = { has_war_with = root } }
	}
	can_ratify = {
		custom_tooltip = {
			text = REQ_BASE_SCIENCE_AID_ARTICLE
			OR = {
				scope:source_country ?= {
					any_scope_treaty = {
						binds = scope:other_country
						any_scope_article = { has_type = science_aid }
					}
				}
				scope:treaty ?= {
					any_scope_article_option = {
						has_type = science_aid
						target_country = scope:other_country
					}
				}
			}
		}
	}
}
'''


def found(text):
    return [(f.article, f.block, f.line, f.scope) for f in unreviewed(scan_text(text, 'test.txt'))]


class BlockScopeTests(unittest.TestCase):
    """#1026: the party scopes each trigger block does not bind."""

    def test_science_aid_2_as_it_shipped(self):
        self.assertEqual(found(SCIENCE_AID_2),
                         [('science_aid_2', 'can_ratify', 12, 'scope:other_country'),
                          ('science_aid_2', 'can_ratify', 19, 'scope:other_country')])
        fixed = SCIENCE_AID_2.replace('binds = scope:other_country', 'binds = scope:target_country')
        fixed = fixed.replace('target_country = scope:other_country',
                              'target_country = scope:target_country')
        self.assertEqual(found(fixed), [])

    def test_the_same_read_is_fine_where_the_block_binds_it(self):
        for block, scope, flagged in (
                ('visible', 'other_country', False), ('possible', 'other_country', False),
                ('visible', 'source_country', True), ('possible', 'target_country', True),
                ('possible', 'first_country', True), ('visible', 'second_country', True),
                ('can_ratify', 'source_country', False), ('can_ratify', 'target_country', False),
                ('requirement_to_maintain', 'source_country', False),
                ('can_ratify', 'other_country', True),
                ('requirement_to_maintain', 'other_country', True)):
            with self.subTest(block=block, scope=scope):
                text = f'a = {{\n kind = directed\n {block} = {{ scope:{scope} = {{ is_ai = yes }} }}\n}}'
                self.assertEqual(found(text),
                                 [('a', block, 3, f'scope:{scope}')] if flagged else [])

    def test_a_mutual_article_has_first_and_second_not_source_and_target(self):
        text = '''a = {
 kind = mutual
 can_ratify = {
  scope:first_country = { country_rank >= scope:second_country.country_rank }
  scope:source_country = { is_ai = yes }
 }
 requirement_to_maintain = { NOT = { scope:target_country = { has_war_with = scope:other_country } } }
}'''
        self.assertEqual(found(text), [('a', 'can_ratify', 5, 'scope:source_country'),
                                       ('a', 'requirement_to_maintain', 7, 'scope:target_country'),
                                       ('a', 'requirement_to_maintain', 7, 'scope:other_country')])

    def test_first_and_second_in_a_directed_article_are_not_judged(self):
        # No vanilla article reads them there and no doc says they are unset.
        text = 'a = { kind = directed can_ratify = { scope:first_country = { is_ai = yes } } }'
        self.assertEqual(found(text), [])

    def test_kind_written_after_the_blocks(self):
        text = ('a = {\n can_ratify = { scope:source_country = { is_ai = yes } }\n kind = mutual\n}\n'
                'b = {\n can_ratify = { scope:source_country = { is_ai = yes } }\n kind = directed\n}')
        self.assertEqual(found(text), [('a', 'can_ratify', 2, 'scope:source_country')])

    def test_an_article_with_no_kind_gets_only_what_both_kinds_lack(self):
        text = ('INJECT:alliance = {\n can_ratify = {\n  scope:source_country = { is_ai = yes }\n'
                '  scope:other_country = { is_ai = yes }\n }\n'
                ' possible = { scope:source_country = { is_ai = yes } }\n}')
        self.assertEqual(found(text), [('INJECT:alliance', 'can_ratify', 4, 'scope:other_country'),
                                       ('INJECT:alliance', 'possible', 6, 'scope:source_country')])

    def test_a_scope_the_block_saves_itself_is_bound(self):
        # Vanilla's alliance: possible saves the partner as target_country.
        text = '''alliance = {
 kind = mutual
 possible = {
  scope:other_country = { save_temporary_scope_as = target_country }
  scope:target_country.relations:root >= relations_threshold:amicable
 }
 can_ratify = { scope:target_country = { is_ai = yes } }
}'''
        self.assertEqual(found(text), [('alliance', 'can_ratify', 7, 'scope:target_country')])

    def test_other_scopes_and_other_blocks_are_left_alone(self):
        text = '''a = {
 kind = directed
 possible = { scope:treaty ?= { always = yes } exists = scope:my_saved_thing }
 can_ratify = { scope:article = { has_type = a } scope:is_renegotiation = yes }
 can_withdraw = { scope:other_country = { is_ai = yes } }
 state_valid_trigger = { scope:source_country = { is_ai = yes } }
 on_entry_into_force = { scope:other_country = { add_treasury = 1 } }
 wargoal = { possible = { scope:source_country = { is_ai = yes } } }
 ai = { inherent_accept_score = { value = scope:other_country.gdp }
  can_ratify = { scope:other_country = { is_ai = yes } } }
}
possible = { kind = directed scripted = { scope:source_country = { is_ai = yes } } }'''
        self.assertEqual(found(text), [])

    def test_comments_are_not_reads_and_quoted_arguments_are(self):
        text = ('a = {\n kind = directed\n can_ratify = {\n  always = yes # scope:other_country\n'
                '  "shared_rivals(scope:other_country)" > 0\n }\n}')
        self.assertEqual(found(text), [('a', 'can_ratify', 5, 'scope:other_country')])

    def test_message_names_the_block_and_what_it_binds(self):
        directed, = scan_text('a = { kind = directed can_ratify = { exists = scope:other_country } }', 't')
        self.assertEqual(directed.message, 'scope:other_country in can_ratify of a directed article, '
                                           'which binds scope:source_country and scope:target_country')
        mutual, = scan_text('a = { kind = mutual can_ratify = { exists = scope:source_country } }', 't')
        self.assertIn('of a mutual article, which binds scope:first_country', mutual.message)
        possible, = scan_text('a = { kind = mutual possible = { exists = scope:first_country } }', 't')
        self.assertIn('in possible, which binds only root', possible.message)
        chance, = scan_text('a = { ai = { evaluation_chance = { value = scope:other_country.gdp } } }', 't')
        self.assertEqual(chance.message, 'scope:other_country in root-only evaluation_chance')


class ReviewedTests(unittest.TestCase):
    TEXT = ('a = {{\n kind = directed\n can_ratify = {{\n'
            '  scope:other_country = {{ is_ai = yes }} {comment}\n }}\n}}')

    def test_a_tagged_comment_on_the_line_suppresses_it(self):
        flags = scan_text(self.TEXT.format(comment='# REVIEWED 2026-11-12 (treaty_scope): bound here in 1.16'),
                          'test.txt')
        self.assertEqual([(f.line, f.reviewed) for f in flags], [(4, True)])
        self.assertEqual(unreviewed(flags), [])

    def test_other_comments_do_not(self):
        for comment in ('', '# the partner', '# REVIEWED 2026-11-12: untagged',
                        '# REVIEWED 2026-11-12 (involvement): another audit\'s tag',
                        '# REVIEWED (treaty_scope): no date', '# REVIEWED 2026-11-12 (treaty_scope):'):
            with self.subTest(comment=comment):
                self.assertEqual(len(found(self.TEXT.format(comment=comment))), 1)

    def test_a_comment_covers_its_own_line_only(self):
        text = ('a = {\n kind = directed\n can_ratify = { # REVIEWED 2026-11-12 (treaty_scope): no\n'
                '  scope:other_country = { is_ai = yes }\n }\n}')
        self.assertEqual(len(found(text)), 1)

    def test_evaluation_chance_takes_no_suppression(self):
        text = ('a = { ai = { evaluation_chance = {\n'
                ' value = scope:other_country.gdp # REVIEWED 2026-11-12 (treaty_scope): no\n} } }')
        self.assertEqual(len(found(text)), 1)

    def test_strict_passes_once_every_flag_is_reviewed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'common/treaty_articles/a.txt'
            path.parent.mkdir(parents=True)
            path.write_text(SCIENCE_AID_2, encoding='utf-8-sig')
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(main(['--mod-path', tmp, '--strict']), 1)
            self.assertIn('common/treaty_articles/a.txt:12: science_aid_2: scope:other_country in can_ratify',
                          out.getvalue())
            self.assertIn('2 invalid named-scope reads (0 reviewed)', out.getvalue())
            path.write_text(SCIENCE_AID_2.replace(
                'scope:other_country\n', 'scope:other_country # REVIEWED 2026-11-12 (treaty_scope): test\n'),
                encoding='utf-8-sig')
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(main(['--mod-path', tmp, '--strict']), 0)
            self.assertIn('0 invalid named-scope reads (2 reviewed)', out.getvalue())
            self.assertEqual(len(audit(tmp)), 2)


class VanillaEvidenceTests(unittest.TestCase):
    """The table is an engine fact nobody can read off the engine, so hold it
    to vanilla's own script: a party scope vanilla reads in a block is one
    that block binds. Fails when a patch makes the table wrong."""

    SCOPE = re.compile(r'scope:([A-Za-z_][A-Za-z0-9_]*)')

    def walk(self, node, reads, saved):
        if isinstance(node, str):
            reads.update(self.SCOPE.findall(node))
        elif isinstance(node, dict):
            for key, value in node.items():
                reads.update(self.SCOPE.findall(key))
                if key in ('save_scope_as', 'save_temporary_scope_as'):
                    saved.update(v for v in value if isinstance(v, str))
                self.walk(value, reads, saved)
        elif isinstance(node, (list, tuple)):
            for value in node:
                self.walk(value, reads, saved)

    def test_vanilla_reads_no_scope_the_table_calls_unbound(self):
        path = Path(__file__).resolve().parent / 'vanilla_parsed/common/treaty_articles.json'
        articles = json.loads(path.read_text(encoding='utf-8'))
        self.assertIn('alliance', articles)
        blocks = 0
        for name, (_, body) in articles.items():
            kind = body['kind'][1]
            for block, by_kind in UNBOUND.items():
                if block not in body:
                    continue
                blocks += 1
                reads, saved = set(), set()
                self.walk(body[block], reads, saved)
                self.assertEqual((reads - saved) & by_kind[kind], set(), f'{name}.{block} ({kind})')
        self.assertGreater(blocks, 60)


class ModTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parent
        cls.parser = ParadoxFileParser()
        for path in (cls.root / 'common/treaty_articles').glob('*.txt'):
            cls.parser.parse_file(str(path), False)

    def test_all_proposal_checks_are_root_only(self):
        self.assertEqual(unreviewed(audit(self.root)), [])

    def test_the_scan_reaches_the_mods_trigger_blocks(self):
        """A clean run means something only if the blocks are being read: with
        every party scope called unbound, the mod's own reads must show up."""
        every = frozenset({'other_country', 'source_country', 'target_country',
                           'first_country', 'second_country'})
        with mock.patch.dict(UNBOUND, {block: {'directed': every, 'mutual': every} for block in UNBOUND}):
            seen = {(f.block, f.scope) for f in audit(self.root)}
        self.assertLessEqual({('possible', 'scope:other_country'), ('visible', 'scope:other_country'),
                              ('can_ratify', 'scope:source_country'),
                              ('can_ratify', 'scope:first_country'),
                              ('requirement_to_maintain', 'scope:target_country')}, seen)

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
