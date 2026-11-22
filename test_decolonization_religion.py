"""A released country's religion (#1499).

`create_dynamic_country` inherits the origin's state religion and laws. From
an atheist metropole that left the new country under State Religion with no
religion, and vanilla's `law_state_religion` `on_activate` could not set one.
`form_decolonized_country` saves one religion before the call (the parent's,
or the released culture's when the parent is atheist) and passes it in every
colour branch. The block runs in scope none, so it must be a saved scope.

No game install needed.
"""
import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
EFFECTS = os.path.join(REPO, "common", "scripted_effects", "decolonization.txt")


def _block(text, name):
    match = re.search(r"^%s = \{" % re.escape(name), text, re.M)
    if match is None:
        raise AssertionError("%s not found" % name)
    depth = 0
    for i in range(text.index("{", match.start()), len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[match.start(): i + 1]
    raise AssertionError("%s is unbalanced" % name)


def _calls(body):
    """Each `create_dynamic_country = { ... }` block in body."""
    out = []
    for match in re.finditer(r"create_dynamic_country = \{", body):
        depth = 0
        for i in range(match.end() - 1, len(body)):
            if body[i] == "{":
                depth += 1
            elif body[i] == "}":
                depth -= 1
                if depth == 0:
                    out.append(body[match.start(): i + 1])
                    break
    return out


class ReleaseReligionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(EFFECTS, encoding="utf-8-sig") as fh:
            cls.body = _block(fh.read(), "form_decolonized_country")

    def test_every_branch_passes_the_saved_religion(self):
        calls = _calls(self.body)
        self.assertEqual(len(calls), 12, "one create_dynamic_country per colour")
        for call in calls:
            self.assertIn("religion = scope:new_country_religion", call)

    def test_the_religion_is_saved_before_the_call(self):
        first_call = self.body.index("create_dynamic_country = {")
        parent = self.body.index("scope:decolonizing_parent.religion = { save_scope_as = new_country_religion }")
        atheist = self.body.index("country_has_state_religion = rel:atheist")
        culture = self.body.index("scope:new_country_culture.religion ?= { save_scope_as = new_country_religion }")
        self.assertLess(parent, atheist)
        self.assertLess(atheist, culture)
        self.assertLess(culture, first_call)

    def test_the_self_check_is_once_a_game_each(self):
        after = self.body[self.body.rindex("create_dynamic_country = {"):]
        self.assertIn("TE_SELF_CHECK OK decol_new_country_religion", after)
        self.assertIn("TE_SELF_CHECK BROKEN decol_new_country_religion", after)
        for flag in ("te_selfcheck_decol_religion", "te_selfcheck_decol_religion_atheist"):
            self.assertIn("NOT = { has_global_variable = %s }" % flag, after)
            self.assertIn("set_global_variable = %s\n" % flag, after)


if __name__ == "__main__":
    unittest.main()
