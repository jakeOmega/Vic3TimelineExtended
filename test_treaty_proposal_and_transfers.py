"""#1440: partner-article requirements in can_propose, and show_in_lens on every
mod treaty article with no required input. #1457: the cessions and reparations
go through the treaty helpers, whose create_treaty matches the gate they test,
with a check that makes the direct transfer if the treaty does not."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ARTICLES = ROOT / 'common/treaty_articles'


def read(rel):
    return (ROOT / rel).read_text(encoding='utf-8-sig')


def strip_comments(text):
    return re.sub(r'#[^\n]*', '', text)


def block(text, start):
    """The braces' contents from the `{` at or after `start`."""
    i = text.index('{', start) + 1
    depth = 1
    j = i
    while depth:
        depth += {'{': 1, '}': -1}.get(text[j], 0)
        j += 1
    return text[i:j - 1]


def articles():
    """name -> body (comments stripped) for every mod treaty article."""
    out = {}
    for path in sorted(ARTICLES.glob('*.txt')):
        text = strip_comments(path.read_text(encoding='utf-8-sig'))
        for m in re.finditer(r'^([A-Za-z_0-9:]+)\s*=\s*\{', text, re.M):
            out[m.group(1)] = block(text, m.start())
    return out


def field(body, key):
    """A depth-1 field's block, or None."""
    depth = 0
    for m in re.finditer(r'[{}]|\b(%s)\s*=\s*\{' % re.escape(key), body):
        if m.group(0) == '{':
            depth += 1
        elif m.group(0) == '}':
            depth -= 1
        elif depth == 0:
            return block(body, m.start())
    return None


class ProposeAndLensTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.articles = articles()

    def test_partner_requirements_sit_in_can_propose(self):
        for name, tooltip in (('science_aid_2', 'REQ_BASE_SCIENCE_AID_ARTICLE'),
                              ('joint_military_exercises', 'joint_military_exercises_ties_tt'),
                              ('nuclear_guarantee', 'nuclear_guarantee_ties_tt')):
            with self.subTest(article=name):
                body = self.articles[name]
                self.assertIn(tooltip, field(body, 'can_propose') or '')
                self.assertNotIn(tooltip, field(body, 'can_ratify') or '')

    def test_every_article_without_inputs_shows_in_the_lens(self):
        missing = []
        for name, body in self.articles.items():
            if field(body, 'required_inputs') is not None or name == 'te_reparations':
                continue
            if 'show_in_lens' not in (field(body, 'flags') or '').split():
                missing.append(name)
        self.assertEqual(missing, [])
        self.assertGreaterEqual(sum(1 for b in self.articles.values()
                                    if 'show_in_lens' in (field(b, 'flags') or '')), 31)

    def test_a_lens_trigger_comes_with_the_flag(self):
        for name, body in self.articles.items():
            if field(body, 'show_in_lens') is not None:
                with self.subTest(article=name):
                    self.assertIn('show_in_lens', (field(body, 'flags') or '').split())


class TransferTests(unittest.TestCase):
    EFFECTS = 'common/scripted_effects/te_treaty_transfer_effects.txt'

    def test_create_treaty_matches_its_gate(self):
        text = strip_comments(read(self.EFFECTS))
        for helper in ('te_cede_state_by_treaty', 'te_pay_reparations_by_treaty'):
            with self.subTest(helper=helper):
                body = block(text, text.index(helper + ' = {'))
                gate = block(body, body.index('can_create_treaty'))
                made = block(body, body.index('create_treaty = {', body.index('can_create_treaty') + 20))
                self.assertEqual(' '.join(gate.split()), ' '.join(made.split()))

    def test_each_helper_falls_back_to_the_direct_transfer(self):
        text = strip_comments(read(self.EFFECTS))
        cede = block(text, text.index('te_cede_state_by_treaty = {'))
        self.assertIn('trigger_event = { id = te_treaty_transfer.1', cede)
        self.assertIn('else = {\n\t\t\t$STATE$ = { set_state_owner = $TAKER$ }', cede)
        pay = block(text, text.index('te_pay_reparations_by_treaty = {'))
        self.assertIn('trigger_event = { id = te_treaty_transfer.2', pay)
        self.assertIn('te_reparations_settle = yes', pay)
        events = strip_comments(read('events/te_treaty_transfer_events.txt'))
        one = block(events, events.index('te_treaty_transfer.1 = {'))
        self.assertIn('set_state_owner = scope:te_tt_taker', one)
        self.assertNotIn('trigger = {', one)
        two = block(events, events.index('te_treaty_transfer.2 = {'))
        self.assertIn('te_reparations_settle = yes', two)
        self.assertNotIn('trigger = {', two)

    def test_the_call_sites_use_the_helpers(self):
        for rel, needle, helper in (
                ('events/irredentism_events.txt', 'set_state_owner = scope:irr_unifier',
                 'te_cede_state_by_treaty'),
                ('common/scripted_effects/un_justice_effects.txt',
                 'set_state_owner = scope:un_crt_claimant', 'te_cede_state_by_treaty'),
                ('events/decolonization_events.txt',
                 'value = scope:reparations_claimant.var:decol_reparations_claim',
                 'te_pay_reparations_by_treaty'),
                ('common/scripted_effects/nuclear_crisis_effects.txt',
                 'add_treasury = nd_loose_compensation_value', 'te_pay_reparations_by_treaty')):
            with self.subTest(file=rel):
                text = strip_comments(read(rel))
                self.assertNotIn(needle, text)
                self.assertIn(helper, text)

    def test_the_reparations_article_is_one_time_and_script_only(self):
        body = articles()['te_reparations']
        self.assertEqual((field(body, 'flags') or '').split(), ['is_one_time'])
        self.assertIn('te_reparations_due_to', field(body, 'visible'))
        self.assertIn('te_reparations_settle', field(body, 'on_entry_into_force'))


if __name__ == '__main__':
    unittest.main()
