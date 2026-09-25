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
                      vars={'finance_cycle_value': cycle}, trade=100)
        result.update(fields)
        return result

    def test_bailout_requires_distressed_actual_trade_partner(self):
        donor = self.country()
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
            donor = self.country(cycle, in_default=default, countries=[self.country(5)])
            self.assertEqual(self.evaluate(body(self.triggers, 'banking_can_offer_bailout'), donor, donor), expected)
        donor = self.country(countries=[])
        self.assertFalse(self.evaluate(body(self.triggers, 'banking_can_offer_bailout'), donor, donor))

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

    def test_grants_pay_the_recipient_the_donors_amount(self):
        effect = body(self.effects, 'banking_transfer_emergency_aid')
        debit = body(effect, 'add_treasury')
        credit = body(body(effect, 'scope:bailout_country'), 'add_treasury')
        self.assertEqual(body(debit, 'value'), '$AMOUNT$')
        self.assertEqual(body(credit, 'value'), 'root.$AMOUNT$')
        def arithmetic(block, amount, days):
            total = 0
            for key, _, value in entries(block):
                number = amount if value in ('$AMOUNT$', 'root.$AMOUNT$') else days if value == '$DAYS$' else float(value)
                if key == 'value':
                    total = number
                elif key == 'multiply':
                    total *= number
                elif key == 'divide':
                    total /= number
                else:
                    self.fail(key)
            return total
        for amount in (100, 10000):
            for days in (365, 1825):
                self.assertGreater(arithmetic(credit, amount, days), 0)
                self.assertEqual(arithmetic(debit, amount, days) + arithmetic(credit, amount, days), 0)
        options = body(self.banking, 'banking_cycle_events.45')['option']
        self.assertEqual(sum('banking_transfer_emergency_aid' in option for _, option in options), 2)


if __name__ == '__main__':
    unittest.main()
