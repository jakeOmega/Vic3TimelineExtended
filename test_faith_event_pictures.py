"""A faith-keyed event picture ladder names every faith of each family it shows.

monument_events.4 (the grand shrine's anniversary) and monument_events.11 pick
a faith's video from a ladder of `event_image` blocks, each gated on a list of
`religion = rel:x`. A faith left out of its family's list falls through to
the ladder's last block: an Ibadi country's shrine showed the animism video
(#1621). So a block that names one faith of a heritage and video names them
all, vanilla's and the mod's custom religions
(common/religions/custom_religion.txt).

Run: python3 -m unittest test_faith_event_pictures -v
"""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EVENTS = "events/monument_events.txt"
CUSTOM = "common/religions/custom_religion.txt"
VANILLA = "vanilla_parsed/common/religions.json"

# Videos that stand for one heritage's faiths. Hindu and Sikh share a video of
# their own apart from the Buddhist faiths, which are of the same heritage.
SPLIT = {"asia_hinduism_sikhism": {"hindu", "sikh"},
         "asia_buddhism": {"mahayana", "gelugpa", "theravada", "custom_religion_buddhist"}}


def _text(path):
    return re.sub(r"#[^\n]*", "", (ROOT / path).read_text(encoding="utf-8-sig"))


def _close(text, open_idx):
    depth = 0
    for i in range(open_idx, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return i + 1
    raise AssertionError("unclosed block")


def heritages():
    """Religion -> heritage, vanilla's and the mod's."""
    out = {name: body[1]["heritage"][1]
           for name, body in json.loads((ROOT / VANILLA).read_text(encoding="utf-8")).items()}
    custom = _text(CUSTOM)
    for m in re.finditer(r"(?m)^(\w+) = \{", custom):
        body = custom[m.end():_close(custom, m.end() - 1)]
        out[m.group(1)] = re.search(r"heritage = (\w+)", body).group(1)
    return out


def ladder(event_id):
    """[(video, {faiths})] for each gated event_image block of one event."""
    text = _text(EVENTS)
    m = re.search(rf"(?m)^{re.escape(event_id)} = \{{", text)
    event = text[m.end():_close(text, m.end() - 1)]
    out = []
    for block in re.finditer(r"\n\tevent_image = \{", event):
        body = event[block.end():_close(event, block.end() - 1)]
        faiths = set(re.findall(r"religion = rel:(\w+)", body))
        video = re.search(r'video = "(\w+)"', body)
        if faiths and video:
            out.append((video.group(1), faiths))
    return out


class FaithPictureLadderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.heritage = heritages()

    def test_the_inputs_are_read(self):
        self.assertEqual(self.heritage["ibadi"], "heritage_islamic")
        self.assertEqual(self.heritage["custom_religion_muslim"], "heritage_islamic")
        self.assertGreaterEqual(len(ladder("monument_events.4")), 6)
        self.assertGreaterEqual(len(ladder("monument_events.11")), 6)

    def test_the_shrine_anniversary_names_every_faith_of_a_family(self):
        """monument_events.4's last block is a faith's picture with no trigger, so a faith missing from
        its family's list is shown another faith's ceremony."""
        for video, faiths in ladder("monument_events.4"):
            with self.subTest(video=video):
                for faith in faiths:
                    self.assertIn(faith, self.heritage, f"{faith} is no religion")
                family = {self.heritage[f] for f in faiths}
                self.assertEqual(len(family), 1, f"{video} mixes heritages: {sorted(faiths)}")
                want = {f for f, h in self.heritage.items() if h in family}
                if video in SPLIT:
                    want = SPLIT[video]
                self.assertEqual(faiths, want)

    def test_the_dedication_event_names_every_vanilla_faith_of_a_family(self):
        """monument_events.11 falls back to a picture of no faith, so a custom religion there is only
        unillustrated; vanilla's faiths are all named."""
        for video, faiths in ladder("monument_events.11"):
            with self.subTest(video=video):
                family = {self.heritage[f] for f in faiths}
                self.assertEqual(len(family), 1)
                want = {f for f, h in self.heritage.items() if h in family and not f.startswith("custom_")}
                if video in SPLIT:
                    want = {f for f in SPLIT[video] if not f.startswith("custom_")}
                self.assertEqual({f for f in faiths if not f.startswith("custom_")}, want)


if __name__ == "__main__":
    unittest.main()
