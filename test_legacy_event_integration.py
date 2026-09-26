"""Offline regressions for legacy events interacting with their successor systems."""
import operator
import unittest
from pathlib import Path

from paradox_file_parser import ParadoxFileParser

ROOT = Path(__file__).resolve().parent


def parse(path):
    parser = ParadoxFileParser()
    parser.parse_file(str(ROOT / path), False)
    return parser.data


def entries(block):
    for key, items in block.items():
        for op, value in items if isinstance(items, list) else [items]:
            yield key, op, value


def body(data, key):
    return data[key][1]


def entries_op(block, key):
    return block[key][0]


def find_dispatch(block, event):
    """The `trigger` of the random-list entry that fires `event`, or None."""
    if any(key == 'trigger_event' and isinstance(value, dict) and body(value, 'id') == event
           for key, _, value in entries(block)):
        return body(block, 'trigger')
    for _, _, value in entries(block):
        if isinstance(value, dict):
            found = find_dispatch(value, event)
            if found is not None:
                return found
    return None


class LegacyIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.triggers = parse('common/scripted_triggers/legacy_event_integration_triggers.txt')
        cls.effects = parse('common/scripted_effects/legacy_event_integration_effects.txt')
        cls.values = parse('common/script_values/legacy_event_integration_values.txt')
        cls.agency = parse('common/scripted_effects/te_event_agency_misc_effects.txt')
        cls.ir = parse('events/international_relations_events.txt')
        cls.society = parse('events/society_technology_events.txt')
        cls.laws = parse('events/extra_law_events.txt')
        cls.banking = parse('events/banking_cycle_events.txt')
        cls.market = parse('common/scripted_triggers/market_triggers.txt')

    def evaluate(self, block, current, donor, mode='AND'):
        answers = []
        for key, op, value in entries(block):
            if key in ('AND', 'OR', 'NOT', 'NOR'):
                answer = self.evaluate(value, current, donor, key)
            elif key in self.triggers or key.startswith('banking_cycle_is_'):
                source = self.triggers if key in self.triggers else self.market
                answer = self.evaluate(body(source, key), current, donor)
                if value == 'no':
                    answer = not answer
            elif key == 'any_country':
                answer = any(self.evaluate(value, other, donor) for other in donor['countries'])
            elif key == 'this':
                answer = current is donor
            elif key in ('has_journal_entry', 'has_technology_researched', 'has_game_rule', 'has_modifier', 'has_variable'):
                field = {'has_journal_entry': 'journals', 'has_technology_researched': 'techs',
                         'has_game_rule': 'rules', 'has_modifier': 'modifiers', 'has_variable': 'vars'}[key]
                answer = value in current.get(field, {})
            elif key in ('has_diplomatic_relevance', 'has_war_with', 'in_default'):
                answer = current.get(key, key == 'has_diplomatic_relevance')
            elif key.startswith('var:') or key == 'banking_bilateral_bailout_trade':
                number = current.get('trade', 0) if key == 'banking_bilateral_bailout_trade' else current.get('vars', {}).get(key[4:], 0)
                answer = {'=': operator.eq, '>': operator.gt, '>=': operator.ge, '<': operator.lt}[op](number, float(value))
            elif key == 'gdp':
                # `gdp < root.gdp`: the candidate recipient against the donor.
                self.assertEqual(value, 'root.gdp')
                answer = {'<': operator.lt, '>': operator.gt}[op](current['gdp'], donor['gdp'])
            elif key in ('market', 'root.market'):
                # A dotted chain is one scope change: `prev` inside is the
                # country it was entered from (vanilla trade_route_events.txt).
                owner = current if key == 'market' else donor
                answer = self.evaluate(value, dict(market_owner=owner, prev=current), donor)
            elif key == 'market_trade_reliance':
                target = {'root.market': donor, 'prev.market': current.get('prev')}[body(value, 'target')]
                threshold = float(body(body(self.values, body(value, 'value')), 'value'))
                reliance = current['market_owner']['reliance']
                share = reliance.get(target['name'], 0) if isinstance(reliance, dict) else reliance
                self.assertEqual(entries_op(value, 'value'), '>=')
                answer = share >= threshold
            elif key == 'any_scope_building':
                answer = current.get('building', False)
            elif key in ('any_rival_country', 'country_rank', 'exists'):
                # These scenarios hold the unrelated eligibility gates satisfied
                # (`exists` is a follow-up event's check for the saved actor).
                answer = True
            else:
                self.fail(f'Unhandled trigger: {key}')
            answers.append(answer)
        if mode == 'OR':
            return any(answers)
        if mode in ('NOT', 'NOR'):
            return not any(answers)
        return all(answers)

    def country(self, cycle=50, **fields):
        result = dict(journals={'je_banking_cycle'}, techs={'keynesian_economics'},
                      vars={'finance_cycle_value': cycle}, trade=100, gdp=100,
                      name='country', reliance=0.1)
        result.update(fields)
        return result

    def test_bailout_requires_distressed_actual_trade_partner(self):
        donor = self.country(gdp=1000)
        for cycle, trade, journal, war, expected in [
            (5, 100, True, False, True), (20, 100, True, False, True),
            (50, 100, True, False, False), (20, 0, True, False, False),
            (20, 100, False, False, False), (20, 100, True, True, False),
        ]:
            with self.subTest(cycle=cycle, trade=trade, journal=journal, war=war):
                candidate = self.country(cycle, trade=trade, journals={'je_banking_cycle'} if journal else set(), has_war_with=war)
                self.assertEqual(self.evaluate(body(self.triggers, 'banking_is_bailout_recipient'), candidate, donor), expected)
        self.assertFalse(self.evaluate(body(self.triggers, 'banking_is_bailout_recipient'), donor, donor))

    def test_bailout_uses_recipient_distress_not_donor_distress(self):
        for cycle, default, expected in [(50, False, True), (20, False, False), (50, True, False)]:
            donor = self.country(cycle, in_default=default, gdp=1000, countries=[self.country(5)])
            self.assertEqual(self.evaluate(body(self.triggers, 'banking_can_offer_bailout'), donor, donor), expected)
        donor = self.country(countries=[])
        self.assertFalse(self.evaluate(body(self.triggers, 'banking_can_offer_bailout'), donor, donor))

    def test_bailout_donor_must_out_gdp_the_recipient(self):
        # A rescuer smaller than the economy it would rescue cannot steady it:
        # a ~5M-GDP puppet was offered as the rescuer of a ~20B-GDP country.
        donor = self.country(gdp=1000)
        for gdp, expected in [(999, True), (1000, False), (4_000_000, False)]:
            with self.subTest(gdp=gdp):
                candidate = self.country(5, gdp=gdp)
                self.assertEqual(self.evaluate(body(self.triggers, 'banking_is_bailout_recipient'), candidate, donor), expected)

    def test_bailout_needs_trade_reliance_on_either_side(self):
        # Either market relying on the other for 5% of its trade is enough
        # (the banking contagion's first tier); any trade at all is not.
        for donor_on_recipient, recipient_on_donor, expected in [
            (0.06, 0.0, True), (0.0, 0.06, True), (0.05, 0.0, True),
            (0.04, 0.04, False), (0.0, 0.0, False),
        ]:
            with self.subTest(donor_on_recipient=donor_on_recipient, recipient_on_donor=recipient_on_donor):
                donor = self.country(gdp=1000, name='donor', reliance={'recipient': donor_on_recipient})
                candidate = self.country(5, name='recipient', reliance={'donor': recipient_on_donor})
                self.assertEqual(self.evaluate(body(self.triggers, 'banking_is_bailout_recipient'), candidate, donor), expected)

    def test_protected_recipient_cannot_collect_repeat_bailouts(self):
        candidate = self.country(5, modifiers={'finreg_banking_stability'})
        self.assertFalse(self.evaluate(body(self.triggers, 'banking_is_bailout_recipient'), candidate, self.country()))

    def test_random_spy_and_achievement_events_are_disabled_system_fallbacks(self):
        for number, system in [(6, 'covert_warfare'), (7, 'space_race')]:
            gate = body(body(self.ir, f'international_relations_events.{number}'), 'trigger')
            for enabled in (True, False):
                country = self.country(rules={system + ('_enabled' if enabled else '_disabled')},
                                       techs={'cryptography', 'space_exploration'}, building=True)
                self.assertEqual(self.evaluate(gate, country, country), not enabled)

    def test_covert_shaped_chains_are_disabled_system_fallbacks(self):
        # Propaganda, proxy funding, espionage, election meddling and funding a
        # rival's militants are covert operations when the system is on, so both
        # the actor's precursor (.202/.203/.32/.17) and the victim's event exist
        # only with it off.
        social = parse('events/social_tensions_events.txt')
        for events, namespace, numbers in [(self.ir, 'international_relations_events', (2, 4, 6, 202, 203)),
                                           (self.society, 'society_technology_events', (14, 32)),
                                           (social, 'social_tensions_events', (2, 17))]:
            for number in numbers:
                name = f'{namespace}.{number}'
                gate = body(body(events, name), 'trigger')
                rules = [value for key, _, value in entries(gate) if key == 'has_game_rule']
                with self.subTest(event=name):
                    self.assertEqual(rules, ['covert_warfare_disabled'])

    def test_covert_shaped_pool_entries_are_gated(self):
        # The monthly pools offer the precursors only with covert warfare off,
        # and the victims' events no longer have pool entries of their own.
        actions = parse('common/on_actions/extra_on_actions.txt')
        for event in ('international_relations_events.2', 'international_relations_events.202',
                      'international_relations_events.203', 'society_technology_events.32'):
            gate = find_dispatch(actions, event)
            with self.subTest(event=event):
                self.assertIsNotNone(gate)
                rules = [value for key, _, value in entries(gate) if key == 'has_game_rule']
                self.assertEqual(rules, ['covert_warfare_disabled'])
        for event in ('international_relations_events.1', 'international_relations_events.4',
                      'international_relations_events.6', 'society_technology_events.14'):
            with self.subTest(event=event):
                self.assertIsNone(find_dispatch(actions, event))
        # The yearly pool is a bare `weight = id` list, so .17 carries its own
        # gate (checked above); .2 must not be in it.
        yearly = parse('common/on_actions/social_tensions_on_actions.txt')
        pool = [value for _, _, value in entries(body(body(yearly, 'on_yearly_events'), 'random_events'))]
        self.assertIn('social_tensions_events.17', pool)
        self.assertNotIn('social_tensions_events.2', pool)

    def test_colony_stories_require_real_settlements_when_enabled(self):
        for number in (18, 19):
            gate = body(body(self.society, f'society_technology_events.{number}'), 'trigger')
            for count, charter, expected in [(0, False, False), (1, True, True)]:
                country = self.country(rules={'space_race_enabled'}, techs=set(),
                                       vars={'sr_colony_count': count, **({'ste_event_18_fired': 1} if number == 19 and charter else {})})
                self.assertEqual(self.evaluate(gate, country, country), expected)
            # Buildings alone are sufficient only with the system off.
            for enabled in (True, False):
                country = self.country(rules={'space_race_enabled' if enabled else 'space_race_disabled'},
                                       techs={'space_colonization'}, building=True)
                self.assertEqual(self.evaluate(gate, country, country), not enabled)

    def test_colony_dispatch_backfills_saves_without_racing_establishment(self):
        actions = parse('common/on_actions/extra_on_actions.txt')
        first = find_dispatch(actions, 'society_technology_events.18')
        governance = find_dispatch(actions, 'society_technology_events.19')
        self.assertIsNotNone(first)
        self.assertIsNotNone(governance)
        for count, pending, charter, expected_first, expected_governance in [
            (0, False, False, False, False), (1, False, False, True, False),
            (1, True, False, False, False), (1, False, True, False, True),
        ]:
            country = self.country(rules={'space_race_enabled'}, techs=set(), vars={
                'sr_colony_count': count,
                **({'sr_colony_charter_pending': 1} if pending else {}),
                **({'ste_event_18_fired': 1} if charter else {}),
            })
            self.assertEqual(self.evaluate(first, country, country), expected_first)
            self.assertEqual(self.evaluate(governance, country, country), expected_governance)

    def test_bank_runs_never_initialize_a_disabled_banking_system(self):
        effect = body(self.effects, 'banking_enactment_run_shock')
        conditional = body(effect, 'if')
        gate = body(conditional, 'limit')
        for active in (True, False):
            country = self.country(journals={'je_banking_cycle'} if active else set())
            self.assertEqual(self.evaluate(gate, country, country), active)
        for number in (2, 38):
            immediate = body(body(self.laws, f'extra_law_events.{number}'), 'immediate')
            self.assertEqual(body(immediate, 'banking_enactment_run_shock'), 'yes')
        self.assertEqual(body(conditional, 'banking_cycle_post_event_refresh'), 'yes')

    def test_grants_pay_the_recipient_the_donors_amount_up_to_a_cap(self):
        # Donor-GDP sized, capped at a share of the recipient's GDP: the donor
        # pays, the recipient receives and .69 names the same sum.
        effect = body(self.effects, 'banking_transfer_emergency_aid')
        debit = body(effect, 'add_treasury')
        credit = body(body(effect, 'scope:bailout_country'), 'add_treasury')
        sets = body(body(self.agency, 'te_ea_bailout_answer_aid'), 'scope:bailout_country')['set_variable']
        reported = [v for _, v in sets if body(v, 'name') == 'te_ea_bailout_amount'][0]
        def arithmetic(block, amount, days, cap):
            total = 0
            for key, _, value in entries(block):
                if isinstance(value, dict):
                    number = None
                else:
                    number = {'$AMOUNT$': amount, 'root.$AMOUNT$': amount, '$DAYS$': days,
                              '$CAP$': cap, 'scope:bailout_country.$CAP$': cap}.get(value)
                    number = float(value) if number is None else number
                if key == 'value':
                    total = number
                elif key == 'multiply':
                    total *= number
                elif key == 'divide':
                    total /= number
                elif key == 'max':
                    total = min(total, number)
                elif key == 'subtract':
                    total -= arithmetic(value, amount, days, cap)
                else:
                    self.fail(key)
            return total
        for amount, days, cap, expected in [(100, 1400, 1e9, 10000), (100, 1400, 2500, 2500)]:
            with self.subTest(amount=amount, cap=cap):
                self.assertEqual(arithmetic(credit, amount, days, cap), expected)
                self.assertEqual(arithmetic(debit, amount, days, cap), -expected)
                self.assertEqual(arithmetic(body(reported, 'value'), amount, days, cap), expected)
        # Each paying option hands the transfer and the report the same terms.
        options = [option for _, option in body(self.banking, 'banking_cycle_events.45')['option']
                   if 'banking_transfer_emergency_aid' in option]
        self.assertEqual(len(options), 2)
        def find(block, key):
            for k, _, v in entries(block):
                if k == key:
                    return v
                if isinstance(v, dict) and (found := find(v, key)) is not None:
                    return found
            return None
        caps = []
        for option in options:
            transfer = body(option, 'banking_transfer_emergency_aid')
            answer = find(option, 'te_ea_bailout_answer_aid')
            for param in ('AMOUNT', 'DAYS', 'CAP'):
                self.assertEqual(body(transfer, param), body(answer, param), param)
            caps.append(body(transfer, 'CAP'))
        self.assertEqual(caps, ['banking_bailout_rescue_cap', 'banking_bailout_grant_cap'])
        for cap in caps:
            self.assertIn(cap, self.values)

    def test_bailout_is_asked_for_before_it_is_answered(self):
        # The donor's pulse puts the question to the distressed partner (.68);
        # .45 reaches the donor only from .68's appeal option, and never picks
        # a partner of its own. Every .45 answer is reported back (.69).
        text = (ROOT / 'common/scripted_effects/banking_cycle_effects.txt').read_text(encoding='utf-8-sig')
        self.assertIn('trigger_event = { id = banking_cycle_events.68 }', text)
        self.assertNotIn('trigger_event = { id = banking_cycle_events.45 }', text)
        request = body(self.banking, 'banking_cycle_events.45')
        self.assertNotIn('immediate', request)
        appeal, alone = [option for _, option in body(self.banking, 'banking_cycle_events.68')['option']]
        self.assertIn('banking_cycle_events.45', str(appeal))
        self.assertNotIn('banking_cycle_events.45', str(alone))
        answers = [str(option) for _, option in request['option']]
        self.assertEqual(sum('te_ea_bailout_answer_aid' in answer for answer in answers), 2)
        self.assertEqual(sum('te_ea_bailout_answer_refusal' in answer for answer in answers), 1)


if __name__ == '__main__':
    unittest.main()
