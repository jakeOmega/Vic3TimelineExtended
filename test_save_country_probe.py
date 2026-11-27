"""Tests for scripts/analysis/save_country_probe.py (per-country save dump and diff).

The probe decodes a Victoria 3 save's binary `gamestate` from token numbers worked
out by hand on real 1.14 saves. A wrong number does not crash anything: a key
simply stops resolving and the country reads as having no variables, which looks
like an answer. These tests pin the layout by building a synthetic `.v3` byte by
byte and asserting the values come back out, and pin the one piece of judgement
the tool makes — recognising a civil war that has ended, whichever side won, and
reporting what the survivor did with the loser's variables. Laws add a second
failure mode that looks like an answer: a law put in the wrong group, which the
depth-aware law-file reader exists to prevent, hides or invents a conflict.
States (#1061) have a database of their own, read with the countries' readers.

Run: .venv/bin/python test_save_country_probe.py
"""

import io
import json
import struct
import sys
import tempfile
import unittest
import unittest.mock
import zipfile
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / 'scripts' / 'analysis'))
import save_country_probe as scp  # noqa: E402

# Every synthetic save goes in one folder removed when the module's tests end: a NamedTemporaryFile with
# delete=False and no unlink left a file in /tmp per save, 273 of them after an hour of parallel runs (#1803).
_SAVES = tempfile.TemporaryDirectory(prefix='te_test_saves_')


def tearDownModule():
    _SAVES.cleanup()

EQ = b'\x01\x00'
OPEN = b'\x03\x00'
CLOSE = b'\x04\x00'
I32 = b'\x0c\x00'
BOOL = b'\x0e\x00'
STR = b'\x0f\x00'
U32 = b'\x14\x00'
I64 = b'\x9c\x02'


def tok(n):
    return struct.pack('<H', n)


def string(text):
    raw = text.encode('ascii')
    return STR + struct.pack('<H', len(raw)) + raw


def variable(name, value):
    """One entry of a country's variable block.

    value: a number (script value), ('country', id), 'flag', or 0 (saved with no value); and, worked out
    2026-10-19, 'flag:x' (a flag value), True (a bool) and ('container' | 'state' | 'character', id).
    """
    if value == 'flag':
        wrapper = tok(scp.KEY_KIND) + EQ + tok(0x0500)
    elif isinstance(value, str) and value.startswith('flag:'):
        wrapper = tok(scp.KEY_KIND) + EQ + tok(scp.KIND_FLAG) + tok(scp.KIND_FLAG) + EQ + string(value[5:])
    elif value is True:
        wrapper = tok(scp.KEY_KIND) + EQ + tok(scp.KIND_BOOL) + tok(scp.KEY_VAL) + EQ + I64 + struct.pack('<q', 1)
    elif isinstance(value, tuple):
        kind = {v: k for k, v in scp.LIST_KINDS.items()}[value[0]]
        wrapper = tok(scp.KEY_KIND) + EQ + tok(kind) + tok(scp.KEY_VAL) + EQ + I64 + struct.pack('<q', value[1])
    elif value == 0:
        wrapper = tok(scp.KEY_KIND) + EQ + tok(scp.KIND_VALUE)
    else:
        wrapper = (
            tok(scp.KEY_KIND) + EQ + tok(scp.KIND_VALUE)
            + tok(scp.KEY_VAL) + EQ + I64 + struct.pack('<q', round(value * scp.FIXED))
        )
    return (
        OPEN + tok(scp.KEY_NAME) + EQ + string(name)
        + tok(scp.KEY_DATA) + EQ + OPEN + wrapper + CLOSE + CLOSE
    )


def variable_list(name, kind, ids):
    """One entry of a country's variable-list block: `{ 0x001b = "name" (0x0352 = { kind id })... 0x006d = { n } }`.

    kind: 'container', 'state' or 'country' (the item type tokens read off a real 1.14 save).
    """
    token = {v: k for k, v in scp.LIST_KINDS.items()}[kind]
    items = b''.join(
        tok(scp.KEY_LIST_ITEM) + EQ + OPEN + tok(scp.KEY_KIND) + EQ + tok(token)
        + tok(scp.KEY_VAL) + EQ + I64 + struct.pack('<q', i) + CLOSE
        for i in ids
    )
    return OPEN + tok(scp.KEY_LIST_NAME) + EQ + string(name) + items + tok(0x006D) + EQ + OPEN + I32 + struct.pack('<i', 1) + CLOSE + CLOSE


def variable_block(variables=None, lists=None):
    """A country's or a state's 0x0555 block, or nothing when it has neither."""
    if not (variables or lists):
        return b''
    body = tok(scp.KEY_VARS) + EQ + OPEN
    if variables:
        body += tok(scp.KEY_DATA) + EQ + OPEN + b''.join(variable(k, v) for k, v in variables.items()) + CLOSE
    if lists:
        body += tok(scp.KEY_LIST) + EQ + OPEN + b''.join(variable_list(k, *v) for k, v in lists.items()) + CLOSE
    return body + CLOSE


def country(cid, tag, flags=(), variables=None, modifiers=(), lists=None):
    """lists: {name: (kind, [ids])}; they sit in the variable block beside the data, as in real saves."""
    body = b''.join(tok(f) + EQ + BOOL + bytes([1]) for f in flags)
    body += tok(scp.KEY_DEF) + EQ + string(tag)
    body += variable_block(variables, lists)
    if modifiers:
        body += modifier_block(modifiers)
    return U32 + struct.pack('<I', cid) + EQ + OPEN + body + CLOSE


def modifier_block(modifiers):
    entries = b''.join(
        OPEN + tok(0x000B) + EQ + U32 + struct.pack('<I', i)
        + tok(scp.KEY_MODNAME) + EQ + string(m)
        + tok(0x0CF8) + EQ + I32 + struct.pack('<i', 1000) + CLOSE
        for i, m in enumerate(modifiers)
    )
    return tok(scp.KEY_MODS) + EQ + OPEN + tok(scp.KEY_MODLIST) + EQ + OPEN + entries + CLOSE + CLOSE


def state(sid, region, owner, variables=None, modifiers=(), lists=None):
    """One state record, its keys in a 1.14.5 save's order: 0x27f3 first, the owner, variables, region, modifiers."""
    body = tok(scp.KEY_STATE_FIRST) + EQ + I32 + struct.pack('<i', 18924)
    body += tok(scp.KEY_OWNER) + EQ + U32 + struct.pack('<I', owner)
    body += tok(0x52BC) + EQ + I32 + struct.pack('<i', 236)  # undecoded, as in real saves
    body += variable_block(variables, lists)
    body += tok(scp.KEY_REGION) + EQ + string(region)
    if modifiers:
        body += modifier_block(modifiers)
    return U32 + struct.pack('<I', sid) + EQ + OPEN + body + CLOSE


def state_db(*states):
    """The state database; a free slot sits among the records and two undecoded keys follow it, as in real saves."""
    free = U32 + struct.pack('<I', 998) + EQ + tok(0x0165)
    body = states[0] + free + b''.join(states[1:]) if states else free
    tail = tok(0x3360) + EQ + OPEN + OPEN + I32 + struct.pack('<i', 133) + CLOSE + CLOSE
    return tok(scp.KEY_STATE_DB) + EQ + OPEN + tok(scp.KEY_DATABASE) + EQ + OPEN + body + CLOSE + tail + CLOSE


def record(rid, type_name, owner, active=None, modifiers=()):
    """A journal-entry-shaped record; other databases (combat units) share this shape."""
    out = U32 + struct.pack('<I', rid) + EQ + OPEN + tok(scp.KEY_KIND) + EQ + string(type_name)
    out += scp.JE_OWNER + struct.pack('<I', owner)
    if active is not None:
        out += scp.JE_ACTIVE + bytes([active])
    if modifiers:
        out += modifier_block(modifiers)
    return out + CLOSE


def law(rid, name, owner, active=False, since=None, replaced=None, enacting=None, mark=False):
    """One country-law record. An inactive law is saved with no active key at all."""
    out = U32 + struct.pack('<I', rid) + EQ + OPEN + tok(scp.KEY_LAW_TYPE) + EQ + string(name)
    out += tok(scp.KEY_OWNER) + EQ + U32 + struct.pack('<I', owner)
    if active:
        out += tok(scp.KEY_ACTIVE) + EQ + BOOL + b'\x01'
    if mark:  # 0x5fac, undecoded; must not upset the walk
        out += tok(0x5FAC) + EQ + BOOL + b'\x01'
    if since is not None:
        out += tok(scp.KEY_LAW_SINCE) + EQ + I32 + struct.pack('<i', since)
    if replaced:
        out += tok(scp.KEY_LAW_REPLACED) + EQ + string(replaced)
    if enacting is not None:
        out += tok(scp.KEY_LAW_ENACTING) + EQ + I32 + struct.pack('<i', enacting)
    return out + CLOSE


def law_db(*records):
    """The law database; a free slot (`<id> = 0x0165`) sits among the records, as in real saves."""
    free = U32 + struct.pack('<I', 999) + EQ + tok(0x0165)
    body = records[0] + free + b''.join(records[1:]) if records else free
    return tok(scp.KEY_LAW_DB) + EQ + OPEN + tok(scp.KEY_DATABASE) + EQ + OPEN + body + CLOSE + CLOSE


def hours(year, month, day):
    days = (year + 5000) * 365 + sum(scp.MONTHS[: month - 1]) + day - 1
    return days * 24


def write_save(countries, records=(), date=(2003, 11, 18), meta=True):
    """meta=False writes an autosave: no meta entry, the date at the head of the gamestate instead."""
    buf = io.BytesIO()
    stamp = b'\x45\x32' + EQ + I32 + struct.pack('<i', hours(*date))
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('gamestate', (b'' if meta else stamp) + b''.join(countries) + b''.join(records))
        if meta:
            archive.writestr('meta', stamp)
    handle = tempfile.NamedTemporaryFile(suffix='.v3', delete=False, dir=_SAVES.name)
    handle.write(b'SAV01030deadbeef00005ba\n' + buf.getvalue())
    handle.close()
    return handle.name


ORIGINAL, REBEL, SPAIN = 5, 0x0100005A, 37
HOLDER, REVOLT = scp.FLAG_TAG_HOLDER, scp.FLAG_REVOLUTIONARY


class DecodingTests(unittest.TestCase):
    """The hand-derived token numbers: wrong by one and nothing resolves."""

    def setUp(self):
        self.path = write_save(
            [
                country(ORIGINAL, 'GER', flags=[HOLDER], modifiers=['nuclear_power', 'un_dues_modifier'], variables={
                    'nuclear_weapon_stockpile': 16,
                    'nuclear_weapons_program_funding': 0,
                    'nd_crisis_last_opponent': ('country', SPAIN),
                    'nd_warning_suspect': ('country', 999),
                    'nuclear_weapon_events.21': 'flag',
                }),
                country(SPAIN, 'SPA', flags=[HOLDER], variables={'nd_doctrine': 3}),
            ],
            records=[
                record(1, 'je_nuclear_program', ORIGINAL, active=1, modifiers=['nd_upkeep_cost']),
                record(2, 'je_strategic_reserve', ORIGINAL, active=0),
                record(3, 'slave_owner_paranoia', ORIGINAL, active=1),
                record(4, 'combat_unit_type_armored_infantry', ORIGINAL),
            ],
        )

    def test_country_block_decodes(self):
        save = scp.Save(self.path, scp.Filters(tags=['GER']))
        recs = save.select()
        self.assertEqual(list(recs), [ORIGINAL])
        rec = recs[ORIGINAL]
        self.assertEqual(rec['tag'], 'GER')
        self.assertEqual(rec['flags'], {HOLDER: 1})
        self.assertIsNone(rec['warning'], 'block must end exactly at the next header')
        self.assertEqual(rec['vars']['nuclear_weapon_stockpile'], 16.0)
        self.assertEqual(rec['vars']['nuclear_weapons_program_funding'], 0.0, 'a zero is saved with no value')
        self.assertEqual(rec['vars']['nd_crisis_last_opponent'], ('country', SPAIN))
        self.assertEqual(rec['vars']['nuclear_weapon_events.21'], 'flag')
        self.assertEqual(rec['modifiers'], ['nuclear_power', 'un_dues_modifier'])

    def test_journal_keeps_entries_and_drops_other_databases(self):
        found = scp.journal_entries(scp.read_gamestate(self.path))[ORIGINAL]
        self.assertEqual(
            sorted((t, a) for t, a, _ in found),
            [('je_nuclear_program', 1), ('je_strategic_reserve', 0), ('slave_owner_paranoia', 1)],
        )

    def test_journal_shows_running_entries_unless_one_is_named(self):
        rec = scp.Save(self.path, scp.Filters(tags=['GER'])).select()[ORIGINAL]
        self.assertEqual(rec['journal'], [('je_nuclear_program', 1), ('slave_owner_paranoia', 1)])
        rec = scp.Save(self.path, scp.Filters(je='je_strategic_reserve')).select()[ORIGINAL]
        self.assertEqual(rec['journal'], [('je_strategic_reserve', 0)])

    def test_journal_entry_modifiers_decode(self):
        rec = scp.Save(self.path, scp.Filters(tags=['GER'])).select()[ORIGINAL]
        self.assertEqual(rec['journal_modifiers']['je_nuclear_program'], ['nd_upkeep_cost'])
        self.assertNotIn('je_strategic_reserve', rec['journal_modifiers'], 'inactive entries are not decoded')

    def test_country_reference_names_its_tag_or_says_gone(self):
        save = scp.Save(self.path, scp.Filters())
        rec = save.record(ORIGINAL)
        self.assertEqual(scp.fmt_value(rec['vars']['nd_crisis_last_opponent'], save.tags), 'country#37(SPA)')
        self.assertEqual(scp.fmt_value(rec['vars']['nd_warning_suspect'], save.tags), 'country#999(gone)')

    def test_save_date(self):
        self.assertEqual(scp.save_date(self.path), '2003.11.18')


class VariableListTests(unittest.TestCase):
    """Variable lists sit in the variable block under 0x0351, beside the data (0x00f0): worked out 2026-10-03 on a
    1.14.5 save. An item is `0x0352 = { 0x00e1 = <kind> 0x00db = <id> }`; the kind tokens are the variables' own."""

    def setUp(self):
        lists = {
            'te_tax_en_relief_states': ('state', [5, 456]),
            'te_tp_records': ('container', [2, 3]),
            'nd_pledgers': ('country', [11]),
        }
        self.path = write_save([
            country(ORIGINAL, 'GER', variables={'a_variable': 4}, lists=lists),
            country(SPAIN, 'SPA', variables={'a_variable': 1}),
            country(9, 'ITA', lists={'only_a_list': ('state', [7])}),
        ])
        self.addCleanup(Path(self.path).unlink)

    def test_lists_decode_with_their_item_kinds(self):
        recs = scp.Save(self.path, scp.Filters()).select()
        self.assertEqual(recs[ORIGINAL]['lists'], {
            'te_tax_en_relief_states': ['state#5', 'state#456'],
            'te_tp_records': ['container#2', 'container#3'],
            'nd_pledgers': ['country#11'],
        })
        self.assertEqual(recs[SPAIN]['lists'], {})
        self.assertEqual(recs[ORIGINAL]['vars'], {'a_variable': 4.0}, 'a list is not a variable')

    def test_a_country_with_only_a_list_still_decodes(self):
        self.assertEqual(scp.Save(self.path, scp.Filters(tags=['ITA'])).select()[9]['lists'], {'only_a_list': ['state#7']})

    def test_an_unknown_item_kind_prints_its_token(self):
        items = [(None, [(('tok', scp.KEY_LIST_NAME), ('str', 'x')),
                         (('tok', scp.KEY_LIST_ITEM), [(('tok', scp.KEY_KIND), ('tok', 0x1234)), (('tok', scp.KEY_VAL), ('int', 9))])])]
        block = [(('tok', scp.KEY_VARS), [(('tok', scp.KEY_LIST), items)])]
        self.assertEqual(scp.read_lists(block), {'x': ['0x1234#9']})

    def test_var_filter_trims_lists_by_name(self):
        rec = scp.Save(self.path, scp.Filters(var='^te_tax_')).select()[ORIGINAL]
        self.assertEqual(list(rec['lists']), ['te_tax_en_relief_states'])

    def test_describe_prints_the_lists(self):
        save = scp.Save(self.path, scp.Filters(var='^te_tax_'))
        text = scp.describe(save.select()[ORIGINAL], save.tags, save.filters)
        self.assertIn('te_tax_en_relief_states = state#5 state#456', text)

    def test_diff_reports_a_list_that_changed(self):
        other = write_save([country(ORIGINAL, 'GER', variables={'a_variable': 4},
                                    lists={'te_tax_en_relief_states': ('state', [5])})])
        self.addCleanup(Path(other).unlink)
        out = io.StringIO()
        with redirect_stdout(out):
            scp.diff(self.path, other, scp.Filters(tags=['GER']))
        self.assertIn('te_tax_en_relief_states', out.getvalue())


class StateTests(unittest.TestCase):
    """--states (#1061): the state database, worked out 2026-10-19 on a 1.14.5 save of 758 states."""

    PARIS = state(456, 'STATE_ILE_DE_FRANCE', 4, modifiers=['gm_local_tourism', 'tourism_output'], variables={
        'gm_levels': 3400,
        'gm_form': 'flag:gardens',
        'gm_seen': True,
        'gm_shadow': ('container', 77),
        'gm_name_char': ('character', 5),
        'gm_holder': ('country', 4),
        'te_dg_scale': 1,
    }, lists={'gm_monuments_here': ('container', [1, 2])})

    def setUp(self):
        self.countries = [country(4, 'EUN'), country(9, 'TUR')]
        self.path = self.write([
            self.PARIS,
            state(847, 'STATE_ANKARA', 4, variables={'gm_premigration': True}),
            state(12, 'STATE_ANKARA', 9, variables={'te_dg_scale': 2}),
            state(13, 'STATE_SMYRNA', 9),
        ])

    def write(self, states, extra=(), **kw):
        path = write_save(self.countries, records=[*extra, state_db(*states)] if states is not None else extra, **kw)
        self.addCleanup(Path(path).unlink)
        return path

    def select(self, path=None, **filters):
        return scp.StateSave(path or self.path, scp.StateFilters(**filters)).select()

    def run_main(self, *argv):
        out = io.StringIO()
        with redirect_stdout(out):
            code = scp.main(list(argv))
        return code, out.getvalue()

    def test_records_decode(self):
        save = scp.StateSave(self.path, scp.StateFilters())
        self.assertIsNone(save.warning)
        recs = save.select()
        self.assertEqual(set(recs), {456, 847, 12, 13}, 'the free slot is skipped')
        paris = recs[456]
        self.assertEqual((paris['region'], paris['owner'], paris['tag']), ('STATE_ILE_DE_FRANCE', 4, 'EUN'))
        self.assertIsNone(paris['warning'], 'a record ends where the next begins')
        self.assertEqual(paris['vars'], {
            'gm_levels': 3400.0,
            'gm_form': 'flag:gardens',
            'gm_seen': 'yes',
            'gm_shadow': 'container#77',
            'gm_name_char': 'character#5',
            'gm_holder': ('country', 4),
            'te_dg_scale': 1.0,
        })
        self.assertEqual(paris['lists'], {'gm_monuments_here': ['container#1', 'container#2']})
        self.assertEqual(paris['modifiers'], ['gm_local_tourism', 'tourism_output'])
        self.assertEqual(recs[13]['vars'], {}, 'a state with no variable block')

    def test_owner_state_and_var_filters(self):
        self.assertEqual(set(self.select(owners=['TUR'])), {12, 13})
        self.assertEqual(set(self.select(states=['ankara'])), {847, 12}, 'a region split between owners')
        self.assertEqual(set(self.select(states=['456', 'STATE_SMYRNA'])), {456, 13})
        self.assertEqual(set(self.select(owners=['TUR'], states=['STATE_ANKARA'])), {12}, 'filters combine')
        recs = self.select(var='^gm_(levels|premigration)$')
        self.assertEqual(set(recs), {456, 847})
        self.assertEqual(recs[456]['vars'], {'gm_levels': 3400.0})
        self.assertEqual(set(self.select(modifier='^tourism_')), {456})

    def test_report(self):
        code, text = self.run_main(self.path, '--state', '456', '--var', '^gm_(form|holder)$')
        self.assertEqual(code, 0)
        self.assertIn('[2003.11.18]  4 state records, 1 shown', text)
        self.assertIn('state#456 STATE_ILE_DE_FRANCE, owner country#4(EUN)', text)
        self.assertIn('gm_form = flag:gardens', text)
        self.assertIn('gm_holder = country#4(EUN)', text)
        self.assertNotIn('modifiers', text, '--var prints the variables part only')

    def test_states_refuse_country_filters(self):
        with redirect_stdout(io.StringIO()), self.assertRaises(SystemExit), \
                unittest.mock.patch('sys.stderr', io.StringIO()):
            scp.main([self.path, '--states', '--tag', 'TUR'])

    def test_diff(self):
        after = self.write([
            state(456, 'STATE_ILE_DE_FRANCE', 4, modifiers=['gm_local_tourism'], variables={
                'gm_levels': 3400, 'gm_form': 'flag:temple', 'gm_seen': True, 'gm_migrated': True,
            }, lists={'gm_monuments_here': ('container', [1])}),
            state(847, 'STATE_ANKARA', 9, variables={'gm_premigration': True}),
            state(12, 'STATE_ANKARA', 9, variables={'te_dg_scale': 3}),
            state(14, 'STATE_IZMIR', 9, variables={'gm_seen': True}),
        ], date=(2003, 12, 1))
        code, text = self.run_main('--diff', self.path, after, '--states', '--var', '^gm_')
        self.assertEqual(code, 0)
        self.assertIn('[2003.12.1]', text)
        self.assertIn('gm_migrated: - -> yes', text)
        self.assertIn('gm_form: flag:gardens -> flag:temple', text, 'a flag value that changed is a change')
        self.assertIn('list gm_monuments_here: container#1 container#2 -> container#1', text)
        self.assertIn('owner: country#4(EUN) -> country#9(TUR)', text)
        self.assertIn('== state#14 STATE_IZMIR, owner country#9(TUR)\n   new:', text)
        self.assertNotIn('te_dg_scale', text, 'state 12 holds no gm_ variable in either save')
        self.assertNotIn('modifier', text, '--var compares variables only: Paris lost tourism_output')
        self.assertIn('3 states compared, 3 changed', text)
        code, text = self.run_main('--diff', self.path, after, '--state', '13', '--state', '456')
        self.assertIn('== state#13 STATE_SMYRNA, owner country#9(TUR)\n   gone', text)
        self.assertIn('-modifier tourism_output', text, 'with no --var or --modifier every part is compared')

    def test_no_state_database_is_a_warning(self):
        save = scp.StateSave(self.write(None), scp.StateFilters())
        self.assertEqual(save.extent, {})
        self.assertIn('no state database', save.warning)

    def test_a_state_shaped_record_outside_the_database_is_a_warning(self):
        before = scp.StateSave(self.write([self.PARIS], extra=[state(99, 'STATE_STRAY', 4)]), scp.StateFilters())
        self.assertIn('1 state-shaped records before the database', before.warning)
        self.assertEqual(set(before.extent), {456})
        path = write_save(self.countries, records=[state_db(self.PARIS), state(98, 'STATE_STRAY', 4)])
        self.addCleanup(Path(path).unlink)
        self.assertIn("not followed by the database's closing brace", scp.StateSave(path, scp.StateFilters()).warning)

    def test_an_autosave_takes_its_date_from_the_gamestate(self):
        path = self.write([self.PARIS], meta=False, date=(2055, 2, 1))
        self.assertEqual(scp.save_date(path), '?', 'no meta, no gamestate given')
        self.assertEqual(scp.save_date(path, scp.read_gamestate(path)), '2055.2.1')
        self.assertIn('[2055.2.1]', self.run_main(path, '--state', '456')[1])


class JournalNameTests(unittest.TestCase):
    """Entries are told from other databases by name; a prefix-less entry missing here would read as absent."""

    def test_every_prefixless_vanilla_entry_is_listed(self):
        snapshot = Path(__file__).resolve().parent / 'vanilla_parsed' / 'common' / 'journal_entries.json'
        if not snapshot.exists():
            self.skipTest('no vanilla_parsed snapshot')
        import json
        keys = json.loads(snapshot.read_text(encoding='utf-8'))
        prefixless = {k for k in keys if not k.startswith('je_')}
        self.assertEqual(prefixless, scp.VANILLA_JE_WITHOUT_PREFIX,
                         'update VANILLA_JE_WITHOUT_PREFIX in save_country_probe.py')

    def test_exact_name_bypasses_the_heuristic(self):
        self.assertTrue(scp.is_journal_type('some_modded_entry', wanted='some_modded_entry'))
        self.assertFalse(scp.is_journal_type('combat_unit_type_armored_infantry'))


class FilterTests(unittest.TestCase):
    def setUp(self):
        self.path = write_save([
            country(ORIGINAL, 'GER', flags=[HOLDER], modifiers=['nuclear_power'],
                    variables={'nuclear_weapon_stockpile': 16, 'te_bank_gold': 100}),
            country(SPAIN, 'SPA', flags=[HOLDER], variables={'te_bank_gold': 5}),
        ])

    def test_var_filter_selects_and_trims(self):
        recs = scp.Save(self.path, scp.Filters(var='^nuclear_')).select()
        self.assertEqual(list(recs), [ORIGINAL])
        self.assertEqual(recs[ORIGINAL]['vars'], {'nuclear_weapon_stockpile': 16.0})

    def test_modifier_filter(self):
        self.assertEqual(list(scp.Save(self.path, scp.Filters(modifier='^nuclear_power$')).select()), [ORIGINAL])

    def test_byte_probe_never_hides_a_match(self):
        self.assertIsNotNone(scp.Filters._bytes_probe('^te_bank_(gold|silver)$'))
        self.assertIsNone(scp.Filters._bytes_probe('^a$|^b$'), 'inner anchors cannot be applied to raw bytes')
        both = scp.Save(self.path, scp.Filters(var='^te_bank_gold$')).select()
        self.assertEqual(set(both), {ORIGINAL, SPAIN})


GOV, CRIME = 'lawgroup_governance_principles', 'lawgroup_criminal_justice'
GROUPS = {
    'law_monarchy': GOV,
    'law_presidential_republic': GOV,
    'law_punishment_focused_criminal_justice': CRIME,
    'law_penal_labor_camps': CRIME,
    'law_restorative_justice': CRIME,
}


class LawDecodingTests(unittest.TestCase):
    """Law records: active is the presence of 0x2ab2, groups come from the law files, not the save."""

    def setUp(self):
        self.path = write_save(
            [country(ORIGINAL, 'GER', flags=[HOLDER]), country(SPAIN, 'SPA', flags=[HOLDER])],
            records=[law_db(
                law(1, 'law_presidential_republic', ORIGINAL, active=True, since=hours(1882, 9, 4),
                    replaced='law_monarchy', mark=True),
                law(2, 'law_monarchy', ORIGINAL, since=hours(1836, 1, 1)),
                law(3, 'law_punishment_focused_criminal_justice', ORIGINAL, active=True, since=hours(1836, 1, 1)),
                law(4, 'law_penal_labor_camps', ORIGINAL),
                law(5, 'law_restorative_justice', ORIGINAL, enacting=hours(2003, 10, 1)),
                law(6, 'law_mystery_a', ORIGINAL, active=True),
                law(7, 'law_monarchy', SPAIN, active=True, since=hours(1836, 1, 1)),
                law(8, 'law_punishment_focused_criminal_justice', SPAIN, active=True, since=hours(1836, 1, 1)),
                law(9, 'law_penal_labor_camps', SPAIN, active=True, since=hours(2020, 2, 1)),
                law(10, 'law_mystery_a', SPAIN, active=True),
                law(11, 'law_mystery_b', SPAIN, active=True),
            )],
        )

    def save(self, **filters):
        return scp.Save(self.path, scp.Filters(**filters), GROUPS)

    def test_records_decode_by_key(self):
        recs, warning = scp.law_records(scp.read_gamestate(self.path))
        self.assertIsNone(warning, 'every law-type key in the gamestate is inside the database')
        self.assertEqual(len(recs), 11, 'the free slot is skipped')
        by = {(r['country'], r['law']): r for r in recs}
        self.assertEqual(by[ORIGINAL, 'law_presidential_republic'], {
            'law': 'law_presidential_republic', 'country': ORIGINAL, 'active': True,
            'since': hours(1882, 9, 4), 'replaced': 'law_monarchy', 'enacting': None,
        })
        monarchy = by[ORIGINAL, 'law_monarchy']
        self.assertFalse(monarchy['active'], 'no 0x2ab2 means inactive')
        self.assertEqual(monarchy['since'], hours(1836, 1, 1), 'an inactive law keeps its date')
        self.assertIsNone(by[ORIGINAL, 'law_penal_labor_camps']['since'])
        self.assertEqual(by[ORIGINAL, 'law_restorative_justice']['enacting'], hours(2003, 10, 1))

    def test_record_holds_only_active_laws_sorted_by_group(self):
        rec = self.save(tags=['GER']).select()[ORIGINAL]
        self.assertEqual([(x['group'], x['law']) for x in rec['laws']], [
            (CRIME, 'law_punishment_focused_criminal_justice'),
            (GOV, 'law_presidential_republic'),
            (None, 'law_mystery_a'),
        ])
        self.assertEqual(rec['enacting'], ('law_restorative_justice', hours(2003, 10, 1)))

    def test_law_filter_matches_name_or_group(self):
        recs = self.save(law='^law_penal_labor_camps$').select()
        self.assertEqual(list(recs), [SPAIN], 'GER holds the law only inactive')
        self.assertEqual([x['law'] for x in recs[SPAIN]['laws']], ['law_penal_labor_camps'])
        recs = self.save(law='^lawgroup_criminal_justice$').select()
        self.assertEqual(set(recs), {ORIGINAL, SPAIN})
        self.assertEqual([x['law'] for x in recs[SPAIN]['laws']],
                         ['law_penal_labor_camps', 'law_punishment_focused_criminal_justice'])

    def test_laws_flag_prints_only_laws_and_marks_a_clash(self):
        out = io.StringIO()
        with redirect_stdout(out):
            scp.report(self.path, scp.Filters(tags=['SPA'], laws=True), GROUPS)
        text = out.getvalue()
        self.assertIn('laws, active (5):', text)
        self.assertIn(f'{CRIME}: law_penal_labor_camps (since 2020.2.1); '
                      'law_punishment_focused_criminal_justice (since 1836.1.1)  <- 2 ACTIVE IN ONE GROUP', text)
        self.assertIn('?: law_mystery_a; law_mystery_b\n', text, 'unknown-group laws are listed, never marked')
        self.assertNotIn('variables', text)

    def test_conflicts(self):
        save = self.save()
        found = scp.law_conflicts(save.active_laws, GROUPS)
        self.assertEqual(list(found), [SPAIN], 'two laws with no known group are not a conflict')
        self.assertEqual([r['law'] for r in found[SPAIN][CRIME]],
                         ['law_penal_labor_camps', 'law_punishment_focused_criminal_justice'])

    def test_conflict_report(self):
        out = io.StringIO()
        with redirect_stdout(out):
            count = scp.conflict_report(self.path, scp.Filters(), GROUPS)
        text = out.getvalue()
        self.assertEqual(count, 1)
        self.assertIn('2 countries with active laws (8 laws), 1 with two or more active in one group', text)
        self.assertIn(f'SPA id={SPAIN}: {CRIME}: law_penal_labor_camps (since 2020.2.1); '
                      'law_punishment_focused_criminal_justice (since 1836.1.1)', text)
        self.assertIn(f'by group: {CRIME} 1', text)
        self.assertIn('by law set: law_penal_labor_camps + law_punishment_focused_criminal_justice 1', text)
        self.assertIn('by the date the newer law became active: 2020.2.1 1', text)
        self.assertIn('not checked, no known group (2): law_mystery_a, law_mystery_b', text)
        with redirect_stdout(io.StringIO()):
            self.assertEqual(scp.conflict_report(self.path, scp.Filters(tags=['GER']), GROUPS), 0)

    def test_diff_reports_laws_turning_on_and_off(self):
        after = write_save(
            [country(ORIGINAL, 'GER', flags=[HOLDER]), country(SPAIN, 'SPA', flags=[HOLDER])],
            records=[law_db(
                law(1, 'law_presidential_republic', ORIGINAL, active=True, since=hours(1882, 9, 4),
                    replaced='law_monarchy'),
                law(3, 'law_punishment_focused_criminal_justice', ORIGINAL, active=True, since=hours(1836, 1, 1)),
                law(4, 'law_penal_labor_camps', ORIGINAL, active=True, since=hours(2003, 11, 2)),
                law(6, 'law_mystery_a', ORIGINAL),
            )],
        )
        out = io.StringIO()
        with redirect_stdout(out):
            scp.diff(self.path, after, scp.Filters(tags=['GER']), GROUPS)
        text = out.getvalue()
        self.assertIn(f'+law law_penal_labor_camps (since 2003.11.2) [{CRIME}]', text)
        self.assertIn('-law law_mystery_a [?]', text)
        self.assertNotIn('law_presidential_republic', text, 'an unchanged law is not a change')

    def test_no_law_database_is_a_warning_not_an_empty_answer(self):
        path = write_save([country(ORIGINAL, 'GER')])
        save = scp.Save(path, scp.Filters(), GROUPS)
        self.assertEqual(save.active_laws, {})
        self.assertIn('no law database', save.law_warning)

    def test_a_law_record_outside_the_database_is_a_warning(self):
        stray = tok(scp.KEY_LAW_TYPE) + EQ + string('law_monarchy')
        path = write_save([country(ORIGINAL, 'GER')], records=[law_db(law(1, 'law_monarchy', ORIGINAL)), stray])
        self.assertIn('2 law-type keys in the gamestate but 1 law records decoded',
                      scp.law_records(scp.read_gamestate(path))[1])


class LawGroupTests(unittest.TestCase):
    """Law -> group from the law files: only `group` at the law block's own depth counts."""

    TEXT = '''﻿# law_commented = { group = lawgroup_comment    a stray { in a comment
law_a = {
\tgroup = lawgroup_a
\tcan_enact = {
\t\tgroup = lawgroup_nested   # nested: must not win
\t}
\thas_ruling_interest_group = ig_industrialists
}
law_b = {
\tmodifier = { x = 1 }
\tpossible = { OR = { group = lawgroup_deep } }
\tinterest_group = lawgroup_wrong
}
INJECT:law_c = {
\tgroup = lawgroup_c
}
REPLACE:law_d = { group = "lawgroup_d" }
TRY_INJECT:law_e={group=lawgroup_e}
'''

    def test_depth_and_whole_token(self):
        self.assertEqual(scp.law_groups_from_text(self.TEXT), {
            'law_a': 'lawgroup_a',
            'law_c': 'lawgroup_c',
            'law_d': 'lawgroup_d',
            'law_e': 'lawgroup_e',
        })

    def write(self, folder, name, text):
        folder.mkdir(parents=True, exist_ok=True)
        (folder / name).write_text(text, encoding='utf-8-sig')

    def test_mod_layers_over_vanilla(self):
        with tempfile.TemporaryDirectory() as tmp:
            vanilla, mod = Path(tmp) / 'vanilla', Path(tmp) / 'mod'
            self.write(vanilla, '00_a.txt', 'law_x = { group = g_x }\nlaw_y = { group = g_y_old }\n')
            self.write(vanilla, '00_b.txt', 'law_z = { group = g_z }\n')
            self.write(mod, '00_b.txt', 'law_w = { group = g_w }\n')  # replaces vanilla's 00_b.txt
            self.write(mod, 'extra.txt', 'INJECT:law_x = { modifier = { a = 1 } }\nINJECT:law_y = { group = g_y_new }\n')
            self.assertEqual(scp.law_groups(vanilla, None, mod),
                             {'law_x': 'g_x', 'law_y': 'g_y_new', 'law_w': 'g_w'})

    def test_snapshot_stands_in_for_a_missing_install(self):
        import json
        with tempfile.TemporaryDirectory() as tmp:
            snapshot, mod = Path(tmp) / 'laws.json', Path(tmp) / 'mod'
            snapshot.write_text(json.dumps({
                'law_x': ['=', {'group': ['=', 'g_x'], 'icon': ['=', '"x.dds"']}],
                'law_q': ['=', {'icon': ['=', '"q.dds"']}],
            }), encoding='utf-8')
            self.write(mod, 'm.txt', 'law_m = { group = g_m }\n')
            self.assertEqual(scp.law_groups(Path(tmp) / 'no_install', snapshot, mod), {'law_x': 'g_x', 'law_m': 'g_m'})
            self.assertEqual(scp.law_groups(None, None, mod), {'law_m': 'g_m'}, 'nothing but the mod: no error')

    def test_this_checkout(self):
        """A naive scan gave the mod's group-less INJECT:law_elected_bureaucrats the next block's group."""
        repo = Path(__file__).resolve().parent
        snapshot = repo / 'vanilla_parsed' / 'common' / 'laws.json'
        if not snapshot.exists():
            self.skipTest('no vanilla_parsed snapshot')
        groups = scp.law_groups(None, snapshot, repo / 'common' / 'laws')
        self.assertEqual(groups['law_elected_bureaucrats'], 'lawgroup_bureaucracy')
        self.assertEqual(groups['law_penal_labor_camps'], 'lawgroup_criminal_justice')
        self.assertEqual(groups['law_punishment_focused_criminal_justice'], 'lawgroup_criminal_justice')


class CivilWarTests(unittest.TestCase):
    """The MERGE report, and recognising an ended civil war whichever side won."""

    BEFORE = [
        country(ORIGINAL, 'GER', flags=[HOLDER], modifiers=['nuclear_power'],
                variables={'nuclear_weapon_stockpile': 16, 'te_bank_gold': 111}),
        country(REBEL, 'GER', flags=[REVOLT], variables={'te_bank_gold': 3}),
    ]

    def test_revolution_won(self):
        before = write_save(self.BEFORE)
        after = write_save([
            country(ORIGINAL, 'GER', variables={'nuclear_weapon_stockpile': 16, 'te_bank_gold': 111}),
            country(REBEL, 'GER', flags=[HOLDER], variables={'nuclear_weapon_stockpile': 16, 'te_bank_gold': 3}),
        ], date=(2003, 12, 3))
        out = io.StringIO()
        with redirect_stdout(out):
            scp.diff(before, after, scp.Filters(tags=['GER']))
        text = out.getvalue()
        self.assertIn(f'MERGE: loser id {ORIGINAL} -> survivor id {REBEL}', text)
        self.assertIn('inherited (the loser\'s only, now on the survivor): 1', text)
        self.assertIn('survivor kept its own 1, took the loser\'s 0', text)
        self.assertIn('the loser\'s own modifiers: 1, also on the survivor now: 0', text)

    def test_merge_counts_the_losers_laws(self):
        before = write_save(
            [country(ORIGINAL, 'GER', flags=[HOLDER]), country(REBEL, 'GER', flags=[REVOLT])],
            records=[law_db(
                law(1, 'law_monarchy', ORIGINAL, active=True),
                law(2, 'law_penal_labor_camps', ORIGINAL, active=True),
                law(3, 'law_presidential_republic', REBEL, active=True),
            )],
        )
        after = write_save(
            [country(ORIGINAL, 'GER'), country(REBEL, 'GER', flags=[HOLDER])],
            records=[law_db(
                law(3, 'law_presidential_republic', REBEL, active=True),
                law(4, 'law_penal_labor_camps', REBEL, active=True),
            )],
        )
        out = io.StringIO()
        with redirect_stdout(out):
            scp.diff(before, after, scp.Filters(tags=['GER']), GROUPS)
        text = out.getvalue()
        self.assertIn(f'MERGE: loser id {ORIGINAL} -> survivor id {REBEL}', text)
        self.assertIn("the loser's own active laws: 2, also active on the survivor now: 1 ['law_penal_labor_camps']",
                      text)

    def test_loyalists_won(self):
        a = {ORIGINAL: {'flags': {HOLDER: 1}}, REBEL: {'flags': {REVOLT: 1}}}
        z = {ORIGINAL: {'flags': {HOLDER: 1}}}
        self.assertEqual(scp.civil_war_outcome(a, z), (ORIGINAL, REBEL))

    def test_war_still_running_is_not_an_outcome(self):
        a = {ORIGINAL: {'flags': {HOLDER: 1}}, REBEL: {'flags': {REVOLT: 1}}}
        self.assertIsNone(scp.civil_war_outcome(a, a))

    def test_var_filter_keeps_the_pair_together(self):
        """The rebel holds no nuclear variable before the win; it must still be compared."""
        before = write_save(self.BEFORE)
        after = write_save([
            country(REBEL, 'GER', flags=[HOLDER], variables={'nuclear_weapon_stockpile': 16, 'te_bank_gold': 3}),
        ])
        out = io.StringIO()
        with redirect_stdout(out):
            scp.diff(before, after, scp.Filters(var='^nuclear_'))
        self.assertIn(f'MERGE: loser id {ORIGINAL} -> survivor id {REBEL}', out.getvalue())



FX = b'\x67\x01'


def fx(value):
    """A building figure: the f64 token holding an i64 fixed point x 1e5 (BINARY LAYOUT § buildings)."""
    return FX + struct.pack('<q', round(value * scp.FIXED))


def goods_block(key, goods):
    """An inputs (0x2fce) or outputs (0x2fcf) block: {good index: quantity}, laid out as on the 1948 save."""
    entries = b''.join(
        I32 + struct.pack('<i', index) + EQ + OPEN + tok(scp.KEY_QUANTITY) + EQ + fx(qty)
        + tok(0x607C) + EQ + OPEN + fx(0) + fx(0) + fx(0) + CLOSE + CLOSE
        for index, qty in goods.items()
    )
    return tok(key) + EQ + OPEN + tok(0x56EC) + EQ + tok(22255) + tok(scp.KEY_GOODS) + EQ + OPEN + entries + CLOSE + CLOSE


def building(bid, type_name, state_id, levels=1, built=None, inputs=None, outputs=None, staffing=None,
             employees=None, throughput=None, cost=None, sales=None, pms=('pm_base',), modifiers=(), header=U32):
    """One building record, its keys in the 1948 save's order. modifiers: (name, multiplier, start hours, end)."""
    body = tok(scp.KEY_BUILDING_TYPE) + EQ + string(type_name)
    body += tok(scp.KEY_LEVELS) + EQ + I32 + struct.pack('<i', levels)
    body += tok(0x2AB2) + EQ + BOOL + b'\x01'
    body += tok(scp.KEY_BUILDING_STATE) + EQ + U32 + struct.pack('<I', state_id)
    if built is not None:
        body += tok(scp.KEY_BUILT) + EQ + I32 + struct.pack('<i', built)
    body += tok(0x5A15) + EQ + fx(1)
    if inputs is not None:
        body += goods_block(scp.KEY_INPUTS, inputs)
    if outputs is not None:
        body += goods_block(scp.KEY_OUTPUTS, outputs)
    for key, value in ((scp.KEY_STAFFING, staffing), (scp.KEY_THROUGHPUT, throughput), (scp.KEY_GOODS_COST, cost),
                       (scp.KEY_GOODS_SALES, sales)):
        if value is not None:
            body += tok(key) + EQ + fx(value)
    if employees is not None:   # a raw count under the f64 token
        body += tok(scp.KEY_EMPLOYEES) + EQ + FX + struct.pack('<q', employees)
    if pms is not None:
        body += tok(scp.KEY_PMS) + EQ + OPEN + b''.join(string(pm) for pm in pms) + CLOSE
    if modifiers:
        entries = b''
        for i, (name, mult, start, end) in enumerate(modifiers):
            entries += OPEN + tok(0x000B) + EQ + I32 + struct.pack('<i', i) + tok(scp.KEY_MODNAME) + EQ + string(name)
            if mult is not None:
                entries += tok(scp.KEY_MOD_MULT) + EQ + fx(mult)
            entries += tok(scp.KEY_MOD_START) + EQ + I32 + struct.pack('<i', start)
            if end is not None:
                entries += tok(scp.KEY_MOD_END) + EQ + I32 + struct.pack('<i', end)
            entries += CLOSE
        body += tok(scp.KEY_MODS) + EQ + OPEN + tok(scp.KEY_MODLIST) + EQ + OPEN + entries + CLOSE
        body += tok(0x0968) + EQ + I32 + struct.pack('<i', 1) + CLOSE
    body += tok(0x2FD0) + EQ + OPEN + I32 + struct.pack('<i', 285225868) + CLOSE
    return header + struct.pack('<I', bid) + EQ + OPEN + body + CLOSE


class BuildingTests(unittest.TestCase):
    """--buildings (#1788): building records, laid out as on a 1.15.1 save of 1948 (16,959 buildings)."""

    GOODS = ['coal', 'iron', 'steel', 'construction']
    SAVE_DATE = (1948, 9, 20)

    def setUp(self):
        self.countries = [country(4, 'USA'), country(9, 'GER')]
        self.states = state_db(state(31, 'STATE_PENNSYLVANIA', 4), state(1039, 'STATE_RUHR', 9))
        site_built = hours(1948, 9, 20) - 10 * 7 * 24        # ten weeks before the save
        self.SITE = building(16777264, 'te_construction_market_site', 31, built=site_built, inputs={3: 3.05438},
                             staffing=2.0, employees=2, throughput=2.93914, cost=6105.70562, pms=(
                                 'pm_te_construction_market_base', 'pm_no_construction_automation'),
                             modifiers=[('te_construction_market_capacity_modifier', 1.98216, hours(1948, 9, 17), None)])
        self.MILL = building(805306473, 'building_steel_mill', 1039, levels=86, built=hours(1916, 3, 14),
                             inputs={0: 1.00138, 1: 5.00691}, outputs={2: 3.12932}, staffing=0.85, employees=214998,
                             throughput=2.32966, cost=211633.16, sales=338561.31, header=I32)
        self.records = [
            self.SITE, self.MILL,
            building(300, 'building_steel_mill', 31, levels=12, built=hours(1930, 1, 1), outputs={2: 1.5}),
            building(301, 'building_steel_mill', 0xFFFFFFFF, levels=0),               # gone: in no state
            building(302, 'te_construction_market_site', 31, pms=None),               # names the type; no building
            building(303, 'building_coal_mine', 31, outputs={0: 7.0}),
        ]
        self.path = self.write(self.records)

    def write(self, records, **kw):
        kw.setdefault('date', self.SAVE_DATE)
        path = write_save(self.countries, records=[self.states, *records], **kw)
        self.addCleanup(Path(path).unlink)
        return path

    def select(self, path=None, types=('te_construction_market_site', 'steel_mill'), **filters):
        return scp.BuildingSave(path or self.path, scp.BuildingFilters(types, **filters), self.GOODS).select()

    def run_main(self, *argv):
        out = io.StringIO()
        with unittest.mock.patch.object(scp, 'known_goods', lambda: self.GOODS), redirect_stdout(out):
            code = scp.main(list(argv))
        return code, out.getvalue()

    def test_a_record_decodes(self):
        rows = self.select()
        self.assertEqual(set(rows), {16777264, 805306473, 300, 301}, 'no coal mine, no record without methods')
        site = rows[16777264]
        self.assertEqual(site, {
            'id': 16777264, 'type': 'te_construction_market_site', 'state': 31, 'region': 'STATE_PENNSYLVANIA',
            'tag': 'USA', 'levels': 1, 'staffing': 2.0, 'employees': 2, 'throughput': 2.93914,
            'started': '1948.7.12', 'age_weeks': 10.0,
            'pms': ['pm_te_construction_market_base', 'pm_no_construction_automation'],
            'inputs': {'construction': 3.05438}, 'outputs': None, 'goods_cost': 6105.70562, 'goods_sales': None,
            'modifiers': [{'name': 'te_construction_market_capacity_modifier', 'multiplier': 1.98216,
                           'start': '1948.9.17', 'end': None}]})
        mill = rows[805306473]
        self.assertEqual((mill['tag'], mill['region'], mill['levels'], mill['employees']), ('GER', 'STATE_RUHR', 86, 214998))
        self.assertEqual((mill['inputs'], mill['outputs']), ({'coal': 1.00138, 'iron': 5.00691}, {'steel': 3.12932}))
        self.assertEqual((rows[301]['state'], rows[301]['tag'], rows[301]['region']), (None, 'none', None))

    def test_a_good_past_the_list_prints_its_index(self):
        save = scp.BuildingSave(self.path, scp.BuildingFilters(['steel_mill']), ['coal'])
        self.assertEqual(save.select()[805306473]['outputs'], {'good#2': 3.12932})

    def test_owner_and_state_filters(self):
        self.assertEqual(set(self.select(owners=['GER'])), {805306473})
        self.assertEqual(set(self.select(states=['pennsylvania'])), {16777264, 300})
        self.assertEqual(set(self.select(states=['1039'], types=['building_steel_mill'])), {805306473})

    def test_report_names_the_traps(self):
        code, text = self.run_main(self.path, '--buildings', 'te_construction_market_site')
        self.assertEqual(code, 0)
        self.assertIn('[1948.9.20]  te_construction_market_site: 1 buildings, 1 shown', text)
        self.assertIn('id 16777264  USA  STATE_PENNSYLVANIA (state 31)  te_construction_market_site', text)
        self.assertIn('level 1  staffing 2  employees 2  throughput 2.93914  started 1948.7.12 (10 weeks)', text)
        self.assertIn('inputs: construction 3.05438   outputs: -', text)
        self.assertIn('modifiers: te_construction_market_capacity_modifier x1.98216 from 1948.9.17', text)
        self.assertIn('two employees on one job', text)
        self.assertIn('no state', self.run_main(self.path, '--buildings', 'steel_mill')[1])

    def test_json(self):
        code, text = self.run_main(self.path, '--buildings', 'steel_mill', '--owner', 'USA', '--json')
        self.assertEqual(code, 0)
        data = json.loads(text)
        self.assertEqual((data['date'], data['types'], data['warnings']), ('1948.9.20', ['steel_mill'], []))
        self.assertEqual([b['id'] for b in data['buildings']], [300])
        self.assertIn('different moments', data['traps'])

    def test_help_names_the_traps(self):
        out = io.StringIO()
        with redirect_stdout(out), self.assertRaises(SystemExit):
            scp.main(['--help'])
        text = ' '.join(out.getvalue().split())
        self.assertIn('different moments', text)
        self.assertIn('two employees on one job', text)

    def test_diff_follows_the_ids(self):
        after = self.write([
            building(16777264, 'te_construction_market_site', 31, built=hours(1948, 7, 12), inputs={3: 4.0},
                     staffing=1.0, employees=1, throughput=2.93914, cost=6105.70562,
                     pms=('pm_te_construction_market_base', 'pm_construction_no_effect'),
                     modifiers=[('te_construction_market_capacity_modifier', 2.5, hours(1948, 10, 1), None)]),
            self.MILL,
            building(304, 'building_steel_mill', 31, levels=1, built=hours(1948, 10, 1)),
        ], date=(1948, 10, 4))
        code, text = self.run_main('--diff', self.path, after, '--buildings', 'te_construction_market_site',
                                   '--buildings', 'steel_mill', '--owner', 'USA')
        self.assertEqual(code, 0)
        self.assertIn('[1948.10.4]', text)
        self.assertIn('staffing: 2 -> 1', text)
        self.assertIn('employees: 2 -> 1', text)
        self.assertIn('input construction: 3.05438 -> 4', text)
        self.assertIn('+pm pm_construction_no_effect', text)
        self.assertIn('-pm pm_no_construction_automation', text)
        self.assertIn('modifier te_construction_market_capacity_modifier x1.98216 from 1948.9.17 -> '
                      'te_construction_market_capacity_modifier x2.5 from 1948.10.1', text)
        self.assertIn('== id 300  USA  STATE_PENNSYLVANIA (state 31)  building_steel_mill\n   gone', text)
        self.assertIn('== id 304  USA  STATE_PENNSYLVANIA (state 31)  building_steel_mill\n   new:', text)
        self.assertNotIn('805306473', text, "the Ruhr's mill is Germany's in both saves")
        self.assertIn('3 buildings compared: 1 changed, 1 gone, 1 new', text)

    def test_buildings_refuse_country_filters_and_json_without_them(self):
        for argv in (('--tag', 'USA'), ('--var', 'x'), ('--states',), ('--laws',)):
            with self.subTest(argv=argv), redirect_stdout(io.StringIO()), unittest.mock.patch('sys.stderr', io.StringIO()):
                with self.assertRaises(SystemExit):
                    scp.main([self.path, '--buildings', 'steel_mill', *argv])
        with redirect_stdout(io.StringIO()), unittest.mock.patch('sys.stderr', io.StringIO()):
            with self.assertRaises(SystemExit):
                scp.main([self.path, '--json'])
            with self.assertRaises(SystemExit):
                scp.main(['--diff', self.path, self.path, '--buildings', 'steel_mill', '--json'])


class GoodsOrderTests(unittest.TestCase):
    """A building's goods are saved by index: the goods in load order (verified on the 1948 save: index 61 was
    construction, every coal mine made coal, every steel mill steel)."""

    def test_files_by_name_a_mod_file_replacing_vanillas_and_an_inject_keeping_its_place(self):
        with tempfile.TemporaryDirectory() as tmp:
            vanilla, mod = Path(tmp) / 'vanilla', Path(tmp) / 'mod'
            vanilla.mkdir(), mod.mkdir()
            (vanilla / '00_goods.txt').write_text('ammunition = {\n\tcost = 50 # { a brace\n}\ncoal = { cost = 30 }\n')
            (vanilla / '10_more.txt').write_text('iron = { x = { y = 1 } }\n')
            (mod / '10_more.txt').write_text('steel = {}\n')            # replaces vanilla's file of that name
            (mod / 'te_goods.txt').write_text('﻿construction = {}\nINJECT:coal = { cost = 31 }\n')
            self.assertEqual(scp.goods_order(vanilla, None, mod), ['ammunition', 'coal', 'steel', 'construction'])
            snapshot = Path(tmp) / 'goods.json'
            snapshot.write_text(json.dumps({'ammunition': [], 'coal': [], 'iron': []}))
            self.assertEqual(scp.goods_order(Path(tmp) / 'none', snapshot, mod),
                             ['ammunition', 'coal', 'iron', 'steel', 'construction'])

    def test_this_checkout_puts_the_mods_goods_after_vanillas(self):
        order = scp.known_goods()
        vanilla = json.loads((Path(__file__).resolve().parent / 'vanilla_parsed' / 'common' / 'goods.json').read_text())
        self.assertEqual(order[:len(vanilla)], list(vanilla))
        self.assertIn('construction', order[len(vanilla):])
        self.assertEqual(len(order), len(set(order)))


if __name__ == '__main__':
    unittest.main()
