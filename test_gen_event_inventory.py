"""gen_event_inventory reads an event's image from the parsed event, one
`event_image` block or several (#1183). No game install needed."""
import os
import tempfile
import unittest

import gen_event_inventory as inv
from paradox_file_parser import ParadoxFileParser

EVENTS = """namespace = test_inv
test_inv.1 = {
	event_image = { video = "unspecific_naval_battle" }
}
test_inv.2 = {
	event_image = { texture = "gfx/event_pictures/a.dds" }
}
test_inv.3 = {
	event_image = {
		trigger = { has_variable = x }
		video = "europenorthamerica_judaism"
	}
	event_image = {
		texture = "gfx/event_pictures/fallback.dds"
	}
}
test_inv.4 = {
	hidden = yes
}
"""


class EventImageTests(unittest.TestCase):
    def setUp(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "test_inv_events.txt")
            with open(path, "w", encoding="utf-8-sig") as f:
                f.write(EVENTS)
            parser = ParadoxFileParser()
            parser.parse_file(path)
        self.events = parser.data

    def image(self, event_id):
        return inv._event_image(inv._entity_data(self.events[event_id]))

    def test_single_block(self):
        self.assertEqual(self.image("test_inv.1"), "unspecific_naval_battle")
        self.assertEqual(self.image("test_inv.2"), "gfx/event_pictures/a.dds")

    def test_several_blocks_list_each_in_order(self):
        self.assertEqual(self.image("test_inv.3"),
                         "europenorthamerica_judaism | gfx/event_pictures/fallback.dds")

    def test_no_block(self):
        self.assertIsNone(self.image("test_inv.4"))


if __name__ == "__main__":
    unittest.main()
