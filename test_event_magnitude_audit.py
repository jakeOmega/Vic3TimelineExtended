"""Unit tests for event_magnitude_audit.

Run: python3 test_event_magnitude_audit.py
"""
import os
import tempfile
import unittest

from event_magnitude_audit import (
    FAST_SCALING_MODIFIERS,
    DIRECT_EFFECTS,
    ResourceMeta,
)


class RegistryTests(unittest.TestCase):
    def test_registry_has_prestige(self):
        self.assertIn("country_prestige_add", FAST_SCALING_MODIFIERS)
        meta = FAST_SCALING_MODIFIERS["country_prestige_add"]
        self.assertEqual(meta.resource, "prestige")

    def test_registry_has_bureaucracy(self):
        self.assertIn("country_bureaucracy_add", FAST_SCALING_MODIFIERS)

    def test_registry_has_add_treasury_direct(self):
        self.assertIn("add_treasury", DIRECT_EFFECTS)
        meta = DIRECT_EFFECTS["add_treasury"]
        self.assertIn("treasury", meta.resource)


if __name__ == "__main__":
    unittest.main()
