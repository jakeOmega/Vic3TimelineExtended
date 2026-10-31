#!/usr/bin/env python3
"""Split ``docs/systems/mod_systems.md`` into one file per system, and port
edits made to the old single file onto the split files.

The single file grew to 1.2 MB and 70 top-level sections. On 2026-10-31 it
became an index (``docs/systems/mod_systems.md``) over one file per system in
``docs/systems/mod_systems/``. ``SYSTEMS`` below is the map: which ``##``
sections each file holds, in what order. Section text moved word for word; each
file adds only a title and a link back to the index. The Banking Cycle section
is the one section cut in two: its Monetary Policy subsections went to
``monetary_policy.md``.

The split ran once::

    python3 scripts/mod_systems_split.py split

The script stays for branches started before the split. Such a branch's edits
to the single file conflict with the index when it merges ``main``; ``port``
carries them into the system files::

    git merge origin/main        # conflict on docs/systems/mod_systems.md
    python3 scripts/mod_systems_split.py port
    git diff --cached            # read what moved; resolve any conflict markers

``port`` reads the conflicted file's merge stages: the single file the branch
started from and the branch's edited copy (in a rebase, git swaps the stages;
``port`` tells them apart by content). It splits both as ``split`` did and
three-way merges each system's change into that system's file
(``git merge-file``), so a section that ``main`` edited after the split keeps
both edits. It then puts back ``main``'s index and stages everything it wrote.
``--base REV --edited REV`` reads the two copies from commits instead, for a
branch that is not mid-merge. A ``##`` section the map doesn't know (one the
branch added or renamed) gets a file named from its heading and a warning:
move its text where it belongs and give it a row in the index.

Delete this script once no open branch predates the split.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DOC_REL = "docs/systems/mod_systems.md"
DOC = REPO_ROOT / DOC_REL
SPLIT_DIR = REPO_ROOT / "docs" / "systems" / "mod_systems"
# The index carries this marker; the old single file never did.
INDEX_MARKER = "<!-- mod_systems index -->"
BACKLINK = "Part of the [mod systems reference](../mod_systems.md), which indexes every system."


@dataclass(frozen=True)
class System:
    file: str
    title: str
    category: str
    covers: str
    sections: tuple[str, ...]  # heading prefixes of the ## sections, in file order


CONVENTIONS = "Conventions and cross-system references"
ECONOMY = "Economy, construction and infrastructure"
POLITICS = "Politics and law"
SOCIETY = "Population, culture and society"
DIPLOMACY = "Diplomacy, war and intelligence"
COLONIES = "Colonies, space and the global commons"
CATEGORIES = (CONVENTIONS, ECONOMY, POLITICS, SOCIETY, DIPLOMACY, COLONIES)

SYSTEMS: tuple[System, ...] = (
    System("dynamic_modifier_pattern.md", "Dynamic Modifier Pattern", CONVENTIONS,
           "Scaling a static modifier with `add_modifier`'s `multiplier`, and which pulse may refresh it",
           ("Dynamic Modifier Pattern",)),
    System("on_actions.md", "On-Actions Reference", CONVENTIONS,
           "Which on-action file wires what; pulse and immediate hooks; the scope-chain limitation",
           ("On-Actions Reference",)),
    System("game_rules.md", "Game Rules", CONVENTIONS,
           "Every game rule, its flag and default, and how a disabled system is gated",
           ("Game Rules",)),
    System("ai.md", "AI Weights and Company AI", CONVENTIONS,
           "AI weight conventions for entries, buttons, actions and articles; how the AI picks companies",
           ("AI Weights Guidelines", "Company AI")),
    System("history_charts.md", "History Store and Charts", CONVENTIONS,
           "The save-persistent store of monthly samples and the reusable column chart",
           ("History Store and Charts",)),
    System("state_and_nation_panels.md", "State Panel and Nation Tab", CONVENTIONS,
           "The state panel's mod tiles and the Timeline Extended window's Nation tab",
           ("State Panel GUI Enhancements", "Nation Tab")),
    System("legacy_narrative_events.md", "Legacy Narrative Events", CONVENTIONS,
           "Older narrative events that now defer to, or feed, the banking, covert and space systems",
           ("Legacy narrative event integration",)),

    System("production_methods.md", "Production Methods", ECONOMY,
           "PM group icons, drugs and pharmaceuticals, barracks training, deep-sea and extraplanetary logistics",
           ("Production Methods (PMs)",)),
    System("construction.md", "Construction", ECONOMY,
           "Construction cost scaling, excess private construction, and construction as a market good",
           ("Construction Cost Scaling", "Excess Private Construction", "Construction as a Market Good")),
    System("transport_goods.md", "Transport Goods", ECONOMY,
           "Transportation inside a state and Merchant Marine between markets",
           ("Transport goods",)),
    System("power_grids.md", "Power Grids", ECONOMY,
           "Grid Transfer Stations and the monthly balancing of Electricity between states",
           ("Power Grids",)),
    System("banking_cycle.md", "Banking Cycle", ECONOMY,
           "The boom-and-bust cycle, the policy dashboard and its tools, the simplified rule, banking laws",
           ("Banking Cycle",)),
    System("monetary_policy.md", "Monetary Policy", ECONOMY,
           "The central bank: rates, mandates, the delegated bank, currencies and pegs (phases 1 to 6)",
           ()),  # the Banking Cycle section's Monetary Policy subsections; see MOVED_SUBSECTIONS
    System("global_warming.md", "Global Warming and Resource Transition", ECONOMY,
           "Emissions, carbon capture, climate policy and the fossil-fuel transition laws",
           ("Global Warming", "Resource Transition")),
    System("wonder_buildings.md", "Wonder Buildings", ECONOMY,
           "The megaprojects' construction-site pattern",
           ("Wonder Buildings",)),

    System("judiciary.md", "Judiciary", POLITICS,
           "The judiciary law group, defying the court, its amendments and landmark cases",
           ("Judiciary",)),
    System("amendments.md", "Amendments", POLITICS,
           "Temporary amendments (sunset clauses), amendment petitions, First Past the Post",
           ("Temporary Amendments", "Amendment Petitions", "First Past the Post")),
    System("tax_code.md", "Legislated Tax Code", POLITICS,
           "The experimental rule that replaces the taxation laws with a legislated code",
           ("Legislated Tax Code",)),
    System("governance_laws.md", "Governance, Bureaucracy and Policing Laws", POLITICS,
           "Collective Governance, the bureaucracy laws, machine administration and rule, policing, penal labor",
           ("Collective Governance", "Bureaucracy Laws", "Machine Administration", "Policing",
            "Penal Labor Camps")),
    System("inheritance.md", "Inheritance", POLITICS,
           "The inheritance laws and what they do through script",
           ("Inheritance",)),
    System("heir_education.md", "Heir Education", POLITICS,
           "Educating the heir: tiers, traits, intelligence and the rebel child",
           ("Heir Education System",)),
    System("social_movements.md", "Social Movements and Religious Revival", POLITICS,
           "The social-movement journal entries, where the retired ones' content went, religious revival events",
           ("Social Movement Journal Entries", "Religious Revival Events")),

    System("demographics.md", "Demographics", SOCIETY,
           "The census by age and sex, Wealth Concentration, births and deaths, the workforce, the late game",
           ("Demographics",)),
    System("pops_and_migration.md", "Pops, Migration and Resettlement", SOCIETY,
           "Migration crowding, unemployment as a workforce share, homelands, resettlement, population transfer",
           ("Migration Crowding", "Unemployment as a Share of the Workforce", "Dynamic Homeland Progress",
            "Internal Resettlement", "Population Transfer")),
    System("sol_expectations.md", "Standard of Living Expectations", SOCIETY,
           "Adaptive standard-of-living expectations and their loyalist and radical effects",
           ("SoL Expectations System",)),
    System("cultural_hegemony.md", "Cultural Hegemony", SOCIETY,
           "Global cultural influence and the ideology drift it drives abroad",
           ("Cultural Hegemony System",)),
    System("grand_monuments.md", "Grand Monuments", SOCIETY,
           "Monuments as political instruments: raising them, their legacy, archaeology, trophies",
           ("Grand Monuments",)),

    System("nuclear.md", "Nuclear Weapons", DIPLOMACY,
           "The nuclear program, deterrence and crisis diplomacy, the Nuclear Program Pause article",
           ("Nuclear Weapons", "Nuclear Deterrence and Crisis Diplomacy", "Nuclear Program Pause")),
    System("covert_warfare.md", "Covert Warfare", DIPLOMACY,
           "Covert operations, networks, tradecraft, backlash, counterintelligence; the intelligence-sharing shield",
           ("Covert Warfare System", "Intelligence Sharing Defense Shield")),
    System("treaties.md", "Treaty Articles", DIPLOMACY,
           "Treaty articles with entity selection, Enforce Emissions Reduction, dynamic treaty names",
           ("Treaty Articles with Entity Selection", "Dynamic Treaty Names")),
    System("war.md", "War", DIPLOMACY,
           "The Rules of War laws, war support feeds, wartime munitions demand",
           ("Rules of War", "War Support Feeds", "Wartime Munitions Demand")),

    System("decolonization.md", "Decolonization", COLONIES,
           "The colonial empire entry, the colony test, wars of independence, nationalization, colonial collapse",
           ("Decolonization System", "Independence Nationalization Event", "Colonial Collapse")),
    System("space_race.md", "Space Race", COLONIES,
           "Milestones, the space program, colonies and their fleets, Space Command, orbital debris",
           ("Space Race",)),
    System("global_commons.md", "Global Commons", COLONIES,
           "Seabed licences and claims, and the UN's Law of the Sea, Antarctica and anti-satellite terms",
           ("Global Commons (", "Global Commons: the UN layer")),
)

# ### subsections filed apart from their ## section: (section prefix, subsection prefix) -> file
MOVED_SUBSECTIONS = {("Banking Cycle", "Monetary Policy (phase"): "monetary_policy.md"}
# The ## heading a file of moved subsections opens with.
MOVED_HEADINGS = {"monetary_policy.md": "## Monetary Policy (part of `je_banking_cycle`)"}

BY_FILE = {s.file: s for s in SYSTEMS}


def split_sections(text: str) -> list[str]:
    """The text of each ``##`` section, heading line included. The preamble before the first is dropped."""
    out: list[list[str]] = []
    fence = False
    for line in text.splitlines(keepends=True):
        if line.startswith("```"):
            fence = not fence
        if not fence and line.startswith("## "):
            out.append([line])
        elif out:
            out[-1].append(line)
    return ["".join(lines) for lines in out]


def heading(section: str) -> str:
    return section.split("\n", 1)[0][3:].strip()


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:50] + ".md"


def file_for(title: str) -> str | None:
    hits = [s.file for s in SYSTEMS for p in s.sections if title.startswith(p)]
    return hits[0] if len(hits) == 1 else None


def pull_subsections(section: str, prefix: str) -> tuple[str, str]:
    """Split a section into (kept, moved): the ``###`` subsections whose heading starts with ``prefix`` move."""
    kept: list[str] = []
    moved: list[str] = []
    dest = kept
    for line in section.splitlines(keepends=True):
        if line.startswith("### "):
            dest = moved if line[4:].startswith(prefix) else kept
        dest.append(line)
    return "".join(kept), "".join(moved)


def render(file: str, blocks: list[str]) -> str:
    system = BY_FILE.get(file)
    title = system.title if system else file[:-3].replace("_", " ").title()
    body = "\n\n".join(b.strip("\n") for b in blocks if b.strip())
    return f"# {title}\n\n{BACKLINK}\n\n{body}\n"


def order(file: str, title: str) -> int:
    """A section's place in its file: the map's order, not the single file's."""
    prefixes = BY_FILE[file].sections if file in BY_FILE else ()
    return next((i for i, p in enumerate(prefixes) if title.startswith(p)), len(prefixes))


def split(text: str, warn=print) -> dict[str, str]:
    """Map each system file name to its text, from the single file's text."""
    sections: dict[str, list[tuple[int, str]]] = {}
    moved: dict[str, list[str]] = {}
    for section in split_sections(text):
        title = heading(section)
        file = file_for(title)
        if file is None:
            file = slug(title)
            warn(f"warning: no system file for '## {title}'; wrote it to {file}. Move it and give it an index row.")
        for (sec, sub), dest in MOVED_SUBSECTIONS.items():
            if title.startswith(sec):
                section, part = pull_subsections(section, sub)
                if part:
                    moved.setdefault(dest, []).append(part)
        sections.setdefault(file, []).append((order(file, title), section))
    out: dict[str, str] = {}
    for file in sorted(set(sections) | set(moved)):
        blocks = [MOVED_HEADINGS[file] + "\n", *moved[file]] if file in moved else []
        blocks += [s for _, s in sorted(sections.get(file, []), key=lambda pair: pair[0])]
        out[file] = render(file, blocks)
    return out


def section_titles(text: str) -> list[str]:
    return [line[3:].strip() for line in text.splitlines() if line.startswith("## ")]


def render_index(files: dict[str, str]) -> str:
    lines = [
        "# Key Mod Systems",
        "",
        INDEX_MARKER,
        "",
        "Reference for the gameplay systems the mod adds, one file per system in "
        "[`mod_systems/`](mod_systems/). Each covers its system's purpose, file locations and key mechanics. "
        "Before redesigning, rebalancing or extending a system, read its file.",
        "",
        "- **Finding a section an older reference names.** Until 2026-10-31 this was one 1.2 MB file, and "
        "references from then name its sections (\"`mod_systems.md` § Inheritance\"). The tables list every "
        "file's `##` sections. A `###` subsection is a grep away: "
        "`grep -rn '^#.*Fast mode' docs/systems/mod_systems/`.",
        "- **Adding a system or a `##` section.** A new system gets a file here and a row below; a new `##` "
        "section in a file gets named in that file's row. `test_mod_systems_index.py` fails on a file the index "
        "doesn't link or a `##` section it doesn't name.",
        "- **A branch that edited the old single file.** After `git merge origin/main`, run "
        "`python3 scripts/mod_systems_split.py port`: it moves the branch's edits into the system files and "
        "puts this index back (details in the script's docstring).",
    ]
    for category in CATEGORIES:
        lines += ["", f"## {category}", "", "| System | Covers | `##` sections |", "|---|---|---|"]
        for s in SYSTEMS:
            if s.category != category:
                continue
            titles = "<br>".join(section_titles(files[s.file]))
            lines.append(f"| [{s.title}](mod_systems/{s.file}) | {s.covers} | {titles} |")
    return "\n".join(lines) + "\n"


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, check=check)


def merge_file(current: str, base: str, edited: str) -> tuple[str, bool]:
    """Three-way merge text: (result, conflicted)."""
    with tempfile.TemporaryDirectory() as tmp:
        paths = []
        for name, text in (("current", current), ("base", base), ("edited", edited)):
            path = Path(tmp) / name
            path.write_text(text, encoding="utf-8", newline="")
            paths.append(str(path))
        res = subprocess.run(["git", "merge-file", "-p", "-L", "main", "-L", "base", "-L", "branch", *paths],
                             capture_output=True, text=True, encoding="utf-8")
        if res.returncode < 0 or res.returncode > 127:
            raise RuntimeError(res.stderr)
        return res.stdout, res.returncode > 0


def port_texts(base: str, edited: str, current: dict[str, str], warn=print) -> dict[str, tuple[str, bool]]:
    """The system files the branch changed, three-way merged: {file: (text, conflicted)}."""
    old = split(base, warn=lambda _m: None)
    new = split(edited, warn=warn)
    out: dict[str, tuple[str, bool]] = {}
    for file in sorted(set(old) | set(new)):
        if old.get(file, "") == new.get(file, ""):
            continue
        out[file] = merge_file(current.get(file, ""), old.get(file, ""), new.get(file, ""))
    return out


def stage_text(stage: int) -> str | None:
    res = git("show", f":{stage}:{DOC_REL}", check=False)
    return res.stdout if res.returncode == 0 else None


def rev_text(rev: str) -> str:
    return git("show", f"{rev}:{DOC_REL}").stdout


def cmd_split(_args) -> int:
    text = DOC.read_text(encoding="utf-8")
    if INDEX_MARKER in text:
        print(f"{DOC_REL} is already the index; nothing to split.")
        return 1
    files = split(text)
    SPLIT_DIR.mkdir(exist_ok=True)
    for file, body in files.items():
        (SPLIT_DIR / file).write_text(body, encoding="utf-8", newline="")
    DOC.write_text(render_index(files), encoding="utf-8", newline="")
    print(f"wrote {len(files)} system files and the index")
    return 0


def cmd_port(args) -> int:
    if args.base or args.edited:
        if not (args.base and args.edited):
            print("--base and --edited go together")
            return 2
        base, edited, index = rev_text(args.base), rev_text(args.edited), None
    else:
        base, ours, theirs = stage_text(1), stage_text(2), stage_text(3)
        if base is None or ours is None or theirs is None:
            print(f"{DOC_REL} is not in a merge conflict; pass --base REV --edited REV instead.")
            return 2
        if INDEX_MARKER in theirs and INDEX_MARKER not in ours:
            edited, index = ours, theirs  # a merge: ours is the branch
        elif INDEX_MARKER in ours and INDEX_MARKER not in theirs:
            edited, index = theirs, ours  # a rebase: theirs is the commit being replayed
        else:
            print("expected one side of the conflict to be the index and the other the old single file")
            return 2
    current = {p.name: p.read_text(encoding="utf-8") for p in SPLIT_DIR.glob("*.md")}
    merged = port_texts(base, edited, current)
    conflicted = []
    for file, (text, conflict) in merged.items():
        (SPLIT_DIR / file).write_text(text, encoding="utf-8", newline="")
        print(f"{'CONFLICT' if conflict else 'merged  '} docs/systems/mod_systems/{file}")
        if conflict:
            conflicted.append(file)
    if index is not None:
        DOC.write_text(index, encoding="utf-8", newline="")
        git("add", DOC_REL)
    clean = [f"docs/systems/mod_systems/{f}" for f in merged if f not in conflicted]
    if clean:
        git("add", *clean)
    if not merged:
        print("the branch's copy of the single file matches its base: nothing to port")
    if conflicted:
        print("resolve the conflict markers in the files marked CONFLICT, then git add them")
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("split", help="split the single file (done 2026-10-31)").set_defaults(func=cmd_split)
    port = sub.add_parser("port", help="port a branch's edits of the single file onto the system files")
    port.add_argument("--base", help="commit holding the single file the branch started from")
    port.add_argument("--edited", help="commit holding the branch's edited single file")
    port.set_defaults(func=cmd_port)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
