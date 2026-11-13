"""server/routes_entities.py: request handling the endpoint tests don't reach
without a live server."""
import unittest

import mod_state_server as mss


class _FakeMS:
    def __init__(self, techs):
        self.techs = techs

    def get_data(self, entity_type):
        return self.techs if entity_type == "Technologies" else None

    def localize(self, key):
        return key

    def get_description(self, key):
        return None


def _tech(era):
    return ("=", {"era": ("=", era)})


class TechnologiesEraTests(unittest.TestCase):
    def setUp(self):
        self.original = mss.ms
        mss.ms = _FakeMS({"tech_a": _tech("era_1"), "tech_b": _tech("era_2"), "tech_c": _tech("era_2")})
        self.handler = object.__new__(mss.ModStateHandler)

    def tearDown(self):
        mss.ms = self.original

    def get(self, path):
        return self.handler.get_result(path)

    def test_an_era_number_or_the_listing_key_picks_one_era(self):
        for path in ("/technologies?era=2", "/technologies?era=era_2", "/technologies?era=era_02"):
            with self.subTest(path=path):
                body, status = self.get(path)
                self.assertEqual(status, 200)
                self.assertEqual(list(body), ["era_2"])
                self.assertEqual(body["era_2"]["count"], 2)

    def test_no_era_lists_them_all(self):
        body, status = self.get("/technologies")
        self.assertEqual((status, sorted(body)), (200, ["era_1", "era_2"]))

    def test_a_bad_era_is_a_400_not_a_500(self):
        # Non-ASCII digits pass str.isdigit(); `²` then fails int() (a 500).
        for value in ("era_x", "first", "-1", "era_", "\u00b2", "era_\u00b2", "\u0663"):
            with self.subTest(era=value):
                body, status = self.get(f"/technologies?era={value}")
                self.assertEqual(status, 400)
                self.assertIn("era number", body["error"])


if __name__ == "__main__":
    unittest.main()
