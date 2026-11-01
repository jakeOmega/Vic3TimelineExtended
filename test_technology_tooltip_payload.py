"""Every mod technology shows something in the tech tree besides its description.

The tooltip lists a technology's modifiers and what it unlocks: the buildings,
production methods, laws, units and so on that name it in their
`unlocking_technologies`. A technology whose only payload is script-gated (a
`has_technology_researched` check in a trigger) lists nothing, and reads as one
that does nothing. Geoengineering shipped that way: its Stratospheric Aerosol
Injection climate policy worked, but the tech tree showed no effect
(2026-11-01). Such a technology carries a `country_<thing>_bool` marker in its
`modifier` block, which the tooltip prints (scripting_best_practices.md
§ "Technology markers").
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TECH_DIR = ROOT / "common" / "technology" / "technologies"

_ENTITY = re.compile(r"^(?:[A-Z_]+:)?([a-z0-9_]+) = \{(.*?)^\}", re.M | re.S)
_UNLOCKING = re.compile(r"unlocking_technologies\s*=\s*\{([^}]*)\}")


def _strip_comments(text):
    return re.sub(r"#[^\n]*", "", text)


def _mod_technologies():
    """{name: body} for every technology the mod's technology files define."""
    techs = {}
    for path in sorted(TECH_DIR.glob("*.txt")):
        text = _strip_comments(path.read_text(encoding="utf-8-sig"))
        for m in _ENTITY.finditer(text):
            techs[m.group(1)] = (path.name, m.group(2))
    return techs


def _unlocked_from():
    """Technologies something outside the technology files names as its unlock."""
    names = set()
    for path in (ROOT / "common").rglob("*.txt"):
        if "technology" in path.parts:
            continue
        text = _strip_comments(path.read_text(encoding="utf-8-sig", errors="replace"))
        for m in _UNLOCKING.finditer(text):
            names.update(re.findall(r"[a-z0-9_]+", m.group(1)))
    return names


class TechnologyTooltipPayload(unittest.TestCase):
    def test_the_scan_finds_the_mod_technologies(self):
        techs = _mod_technologies()
        self.assertGreater(len(techs), 100)
        self.assertIn("geoengineering", techs)

    def test_every_technology_has_a_modifier_or_an_unlock(self):
        unlocked = _unlocked_from()
        blank = sorted(
            f"{name} ({file})"
            for name, (file, body) in _mod_technologies().items()
            if not re.search(r"\bmodifier\s*=\s*\{", body) and name not in unlocked
        )
        self.assertEqual(
            blank, [],
            "these technologies show no effect in the tech tree; give each a "
            "country_<thing>_bool marker in its modifier block (declared in "
            "common/modifier_type_definitions/, with loc and _desc) naming what it unlocks",
        )


if __name__ == "__main__":
    unittest.main()
