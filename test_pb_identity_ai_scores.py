# -*- coding: utf-8 -*-
"""The mod's power bloc identities in vanilla's AI acceptance scores (#1863).

``common/script_values/modified.txt`` INJECTs a branch per mod identity into two
vanilla script values, and each is read in its own set of scopes:

* ``ai_power_bloc_identity_score``, from the invite action's AI acceptance
  (``28_invite_to_power_bloc.txt``): ``scope:actor`` is the inviting bloc's
  country and ROOT the invited one. ``scope:source_country`` is not set there.
* ``ai_power_bloc_identity_score_treaties``, from the join and embassy treaty
  articles (``09_join_power_bloc.txt``, ``10_host_power_bloc_embassy.txt``):
  ROOT is the country deciding and ``scope:target_country`` the bloc's side.

A branch that tests the wrong scope's bloc is false without a word from the
engine, so its terms never pay: the Diplomatic Framework's read
``scope:source_country`` until #1863. These tests hold every branch to
its value's scope, and each term to an ``add`` block, since a bare ``value =``
in a branch would overwrite what the branches before it added.
"""
import unittest
from pathlib import Path

from paradox_file_parser import ParadoxFileParser

ROOT = Path(__file__).resolve().parent
MODIFIED = ROOT / "common" / "script_values" / "modified.txt"
OPERATORS = {"=", "?=", "<", ">", "<=", ">=", "!="}

# Each value's bloc side, and the relations read that goes with it (ROOT's relations with it).
SCOPES = {
    "INJECT:ai_power_bloc_identity_score": ("scope:actor", '"relations(scope:actor)"'),
    "INJECT:ai_power_bloc_identity_score_treaties": ("scope:target_country", '"relations(scope:target_country)"'),
}


def parse(source):
    """An order-preserving parse: a list of (key, operator, value-or-list). Quotes are kept."""
    tokens = ParadoxFileParser().tokenize(source)
    pos = 0

    def body():
        nonlocal pos
        result = []
        while pos < len(tokens):
            key = tokens[pos]
            pos += 1
            if key == "}":
                return result
            if pos >= len(tokens) or tokens[pos] not in OPERATORS:
                result.append((key, None, None))
                continue
            op, value = tokens[pos], tokens[pos + 1]
            pos += 2
            result.append((key, op, body() if value == "{" else value))
        return result
    return body()


def tokens_of(node):
    """Every key and value under a node, flattened."""
    for key, _, value in node:
        yield key
        if isinstance(value, list):
            yield from tokens_of(value)
        elif value is not None:
            yield value


class IdentityScoreScopesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.top = {key: value for key, _, value in parse(MODIFIED.read_text(encoding="utf-8-sig"))}

    def branches(self, value_name):
        """(identity, branch body) for each top-level `if` that tests a bloc's identity."""
        found = []
        for key, _, body in self.top[value_name]:
            self.assertEqual(key, "if", f"{value_name}: a top-level {key!r}; every branch is an `if`")
            limit = next(v for k, _, v in body if k == "limit")
            self.assertEqual(len(limit), 1, f"{value_name}: a branch's limit tests one bloc")
            scope, op, test = limit[0]
            self.assertEqual(op, "?=", f"{value_name}: {scope} needs `?=`, a country may be in no bloc")
            identity = next(v for k, _, v in test if k == "has_identity")
            found.append((identity, scope, body))
        return found

    def test_each_branch_tests_the_bloc_its_value_is_read_for(self):
        for name, (side, _) in SCOPES.items():
            for identity, scope, _ in self.branches(name):
                with self.subTest(value=name, identity=identity):
                    self.assertEqual(scope, f"{side}.power_bloc")

    def test_the_invitation_never_reads_source_country(self):
        name = "INJECT:ai_power_bloc_identity_score"
        stray = [t for t in tokens_of(self.top[name]) if "scope:source_country" in t]
        self.assertEqual(stray, [], "the invite action sets no scope:source_country")

    def test_every_term_is_an_add_block_with_a_desc(self):
        for name in SCOPES:
            for identity, _, body in self.branches(name):
                for key, _, value in body:
                    if key == "limit":
                        continue
                    with self.subTest(value=name, identity=identity, key=key):
                        self.assertIn(key, ("add", "if"), "a bare value/add in a branch has no line of its own")
                        terms = [value] if key == "add" else [v for k, _, v in value if k == "add"]
                        for term in terms:
                            self.assertIsInstance(term, list)
                            self.assertIn("desc", [k for k, _, _ in term])

    def test_both_forms_carry_the_diplomatic_framework(self):
        for name, (_, relations) in SCOPES.items():
            with self.subTest(value=name):
                body = dict((i, b) for i, _, b in self.branches(name))["identity:identity_diplomatic"]
                term = next(v for k, _, v in body if k == "add")
                self.assertIn(("desc", "=", '"DIPLOMATIC_ACCEPTANCE_DIPLOMATIC_RELATIONS"'), term)
                self.assertIn(("value", "=", "10"), term)
                self.assertIn(("add", "=", relations), term)


if __name__ == "__main__":
    unittest.main()
