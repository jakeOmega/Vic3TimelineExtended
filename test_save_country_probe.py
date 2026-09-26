"""Tests for scripts/analysis/save_country_probe.py (per-country save dump and diff).

The probe decodes a Victoria 3 save's binary `gamestate` from token numbers worked
out by hand on real 1.14 saves. A wrong number does not crash anything: a key
simply stops resolving and the country reads as having no variables, which looks
like an answer. These tests pin the layout by building a synthetic `.v3` byte by
byte and asserting the values come back out, and pin the one piece of judgement
the tool makes — recognising a civil war that has ended, whichever side won, and
reporting what the survivor did with the loser's variables.

Run: .venv/bin/python test_save_country_probe.py
"""

import io
import struct
import sys
import tempfile
import unittest
import zipfile
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / 'scripts' / 'analysis'))
import save_country_probe as scp  # noqa: E402

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

    value: a number (script value), ('country', id), 'flag', or 0 (saved with no value).
    """
    if value == 'flag':
        wrapper = tok(scp.KEY_KIND) + EQ + tok(0x0500)
    elif isinstance(value, tuple):
        wrapper = tok(scp.KEY_KIND) + EQ + tok(scp.KIND_COUNTRY) + tok(scp.KEY_VAL) + EQ + I64 + struct.pack('<q', value[1])
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


def country(cid, tag, flags=(), variables=None, modifiers=()):
    body = b''.join(tok(f) + EQ + BOOL + bytes([1]) for f in flags)
    body += tok(scp.KEY_DEF) + EQ + string(tag)
    if variables:
        body += (
            tok(scp.KEY_VARS) + EQ + OPEN + tok(scp.KEY_DATA) + EQ + OPEN
            + b''.join(variable(k, v) for k, v in variables.items())
            + CLOSE + CLOSE
        )
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


def record(rid, type_name, owner, active=None, modifiers=()):
    """A journal-entry-shaped record; other databases (combat units) share this shape."""
    out = U32 + struct.pack('<I', rid) + EQ + OPEN + tok(scp.KEY_KIND) + EQ + string(type_name)
    out += scp.JE_OWNER + struct.pack('<I', owner)
    if active is not None:
        out += scp.JE_ACTIVE + bytes([active])
    if modifiers:
        out += modifier_block(modifiers)
    return out + CLOSE


def hours(year, month, day):
    days = (year + 5000) * 365 + sum(scp.MONTHS[: month - 1]) + day - 1
    return days * 24


def write_save(countries, records=(), date=(2003, 11, 18)):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('gamestate', b''.join(countries) + b''.join(records))
        archive.writestr('meta', b'\x45\x32' + EQ + I32 + struct.pack('<i', hours(*date)))
    handle = tempfile.NamedTemporaryFile(suffix='.v3', delete=False)
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


if __name__ == '__main__':
    unittest.main()
