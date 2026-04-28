"""Unit tests for the engine-log parsers in mod_state_server.

Each parser turns one of the six Victoria 3 engine-generated `.log` files into
a list of structured entries. The tests use small synthetic fixtures so they
don't depend on the actual logs in the user's Paradox directory.
"""
import os
import tempfile
import unittest

from mod_state_server import (
    _parse_modifiers_log,
    _parse_effects_triggers_log,
    _parse_event_targets_log,
    _parse_on_actions_log,
    _parse_custom_localization_log,
)


def _write(content: str) -> str:
    fd, path = tempfile.mkstemp(suffix=".log")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(content)
    return path


class ModifiersLogTests(unittest.TestCase):
    def test_parses_basic_entries(self):
        path = _write(
            """--- Static modifier types ---
country_authority_add:
  Mask: country
  Name: Authority
  Description: Adds Authority to the Country.
goods_output_grain_mult:
  Mask: goods
  Name: Grain Output
  Description: Multiplier on grain output across the economy.
"""
        )
        try:
            entries = _parse_modifiers_log(path)
        finally:
            os.remove(path)
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]["name"], "country_authority_add")
        self.assertEqual(entries[0]["mask"], "country")
        self.assertEqual(entries[0]["display_name"], "Authority")
        self.assertEqual(entries[0]["description"], "Adds Authority to the Country.")
        self.assertEqual(entries[1]["name"], "goods_output_grain_mult")

    def test_multiline_description_is_captured(self):
        # Regression: vanilla `military_formation_organization_gain_add` has a
        # multi-line description that includes paragraph breaks AND lines like
        # "A Formation with low Organization will suffer penalties..." that end
        # in a colon. Earlier the parser misclassified those as new modifier
        # names and produced spurious entries with empty masks.
        path = _write(
            """alpha_add:
  Mask: country
  Name: Alpha
  Description: Some baseline description.

A continuation paragraph.

A Formation with low Organization will suffer penalties the lower the value is, up to the following effects:
-75% Offense
-50% Defense
beta_mult:
  Mask: country
  Name: Beta
  Description: Beta description.
"""
        )
        try:
            entries = _parse_modifiers_log(path)
        finally:
            os.remove(path)
        self.assertEqual([e["name"] for e in entries], ["alpha_add", "beta_mult"])
        self.assertIn("A Formation with low Organization", entries[0]["description"])
        self.assertIn("A continuation paragraph", entries[0]["description"])
        # The colon-ending prose line must not become a new entry.
        names = {e["name"] for e in entries}
        self.assertNotIn(
            "A Formation with low Organization will suffer penalties the lower the value is, up to the following effects",
            names,
        )

    def test_skips_separator_lines(self):
        path = _write("--- Static modifier types ---\nx_add:\n  Mask: country\n  Name: X\n  Description: X.\n")
        try:
            entries = _parse_modifiers_log(path)
        finally:
            os.remove(path)
        self.assertEqual([e["name"] for e in entries], ["x_add"])

    def test_missing_file_returns_empty_list(self):
        self.assertEqual(_parse_modifiers_log("/nonexistent/path/x.log"), [])


class EffectsTriggersLogTests(unittest.TestCase):
    def test_parses_basic_entries(self):
        path = _write(
            """# Effect Documentation
## abandon_revolution
Removes interest group from revolution
abandon_revolution = yes/no
**Supported Scopes**: interest_group

## activate_law
Activates a law for a country
**Supported Scopes**: country
**Supported Targets**: law_type
"""
        )
        try:
            entries = _parse_effects_triggers_log(path)
        finally:
            os.remove(path)
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]["name"], "abandon_revolution")
        self.assertEqual(entries[0]["scopes"], ["interest_group"])
        self.assertEqual(entries[0]["targets"], [])
        self.assertIn("Removes interest group", entries[0]["description"])
        self.assertEqual(entries[1]["name"], "activate_law")
        self.assertEqual(entries[1]["scopes"], ["country"])
        self.assertEqual(entries[1]["targets"], ["law_type"])

    def test_multiple_scopes(self):
        path = _write(
            """## test_effect
A test effect.
**Supported Scopes**: country, state, building
"""
        )
        try:
            entries = _parse_effects_triggers_log(path)
        finally:
            os.remove(path)
        self.assertEqual(entries[0]["scopes"], ["country", "state", "building"])


class EventTargetsLogTests(unittest.TestCase):
    def test_parses_basic_entries(self):
        path = _write(
            """# Event Target Documentation
### controller
Scope to the controller of the object
Input Scopes: province, state
Output Scopes: country

### initiator
Scope to the initiator of the object
Input Scopes: diplomatic_play
Output Scopes: country
Requires Data: yes
"""
        )
        try:
            entries = _parse_event_targets_log(path)
        finally:
            os.remove(path)
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]["name"], "controller")
        self.assertEqual(entries[0]["input_scopes"], ["province", "state"])
        self.assertEqual(entries[0]["output_scopes"], ["country"])
        self.assertFalse(entries[0]["requires_data"])
        self.assertTrue(entries[1]["requires_data"])
        # "scopes" alias preserved for filter consistency
        self.assertEqual(entries[0]["scopes"], ["province", "state"])


class OnActionsLogTests(unittest.TestCase):
    def test_parses_basic_entries(self):
        path = _write(
            """On Action Documentation
--------------------
on_country_setup:
From Code: Yes
Expected Scope: country
--------------------
on_yearly_pulse_country:
From Code: Yes
Expected Scope: country
--------------------
my_custom_on_action:
From Code: No
Expected Scope: none
--------------------
"""
        )
        try:
            entries = _parse_on_actions_log(path)
        finally:
            os.remove(path)
        self.assertEqual(len(entries), 3)
        self.assertEqual(entries[0]["name"], "on_country_setup")
        self.assertTrue(entries[0]["from_code"])
        self.assertEqual(entries[0]["scopes"], ["country"])
        self.assertEqual(entries[2]["name"], "my_custom_on_action")
        self.assertFalse(entries[2]["from_code"])
        self.assertEqual(entries[2]["scopes"], [])


class CustomLocalizationLogTests(unittest.TestCase):
    def test_parses_basic_entries(self):
        path = _write(
            """Custom Localization Documentation
--------------------
GetCountryName:
Scope: country
Random Valid: no
Entries:
GetName
GetDef
--------------------
GetGoodIcon:
Scope: goods
Random Valid: yes
Entries:
icon
--------------------
"""
        )
        try:
            entries = _parse_custom_localization_log(path)
        finally:
            os.remove(path)
        self.assertEqual(len(entries), 2)
        self.assertEqual(entries[0]["name"], "GetCountryName")
        self.assertEqual(entries[0]["scopes"], ["country"])
        self.assertFalse(entries[0]["random_valid"])
        self.assertEqual(entries[0]["loc_entries"], ["GetName", "GetDef"])
        self.assertTrue(entries[1]["random_valid"])


if __name__ == "__main__":
    unittest.main()
