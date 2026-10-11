"""The LGBTQ+ Rights laws' effect on births (owner, 2026-10-10).

The laws carried -5% (Legal Limbo) and -10% (each higher law) birth rate. The research
doesn't support anything that size: the careful studies find no fall in opposite-sex
marriage after same-sex marriage (Dillender 2014; Trandafir 2014, both in Demography),
and the plausible mechanism, people who would otherwise have married someone of the
other sex, is a few per cent of adults at most, partly offset by same-sex parents.
Legal Limbo is the 1791 and Napoleonic decriminalisations, under heavy pressure to
marry. So only Full Equality and Protection keeps a token -1%.
"""
import unittest
from pathlib import Path

from paradox_file_parser import ParadoxFileParser

REPO = Path(__file__).resolve().parent
LAWS = REPO / "common" / "laws" / "extra_laws.txt"

EXPECTED_BIRTH_LINE = {
    "law_legal_limbo": None,
    "law_basic_protections": None,
    "law_comprehensive_rights": None,
    "law_full_equality_and_protection": "-0.01",
}


def _entries(node):
    for part in node if isinstance(node, list) else [node]:
        for key, (op, value) in part.items():
            yield key, value


class LgbtqRightsBirthLinesTest(unittest.TestCase):
    def setUp(self):
        parser = ParadoxFileParser()
        text = LAWS.read_text(encoding="utf-8-sig")
        self.laws = dict(_entries(parser.parse_object(parser.tokenize("{" + text + "}"))[0]))

    def test_birth_lines(self):
        for law, expected in EXPECTED_BIRTH_LINE.items():
            with self.subTest(law=law):
                lines = [v for k, block in _entries(self.laws[law]) if k == "modifier"
                         for kk, v in _entries(block) if kk == "state_birth_rate_mult"]
                self.assertEqual(lines, [] if expected is None else [expected])


if __name__ == "__main__":
    unittest.main()
