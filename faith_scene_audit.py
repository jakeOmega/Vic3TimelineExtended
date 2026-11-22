"""Flag event text that carries one faith's vocabulary and can be shown to a
country of another faith (#1531).

"The Old Rules" (`society_technology_events.4`) once showed Singapore a
priest's sermon: the event had no religion trigger, and its flavor had a pew,
a priest and a sermon in it. The house rule is in `docs/guides/
loc_style_guide.md` ("Do not put one faith's furniture in a scene any country
can get") and `docs/guides/event_creation_guide.md` ("One faith's scene in an
event any country gets"): write the scene without a named faith, or gate the
faith's version. This audit holds the events to it.

What is checked
---------------
Every loc key an event shows, in a file under `events/` (the `te_debug_*`
benches and `hidden = yes` events left out):

- its `title`, `desc` and `flavor`, written as a key or as a block of
  `first_valid` / `random_valid` / `triggered_desc` / `desc`;
- each option's `name`, as a key or as `name = { trigger = { } text = key }`;
- every `custom_tooltip = key` and `text = key` in its `immediate`, `after`
  and options, and in an option's `trigger`;
- the name and description of every modifier it adds (`add_modifier`,
  `add_enactment_modifier`, any `add_*_modifier`);
- the same inside a scripted effect the event calls, arguments substituted;
- and every mod key one of those splices in as `$key$`.

A key is read when the mod's English loc defines it (`te_unused_l_english.yml`
skipped). Its text, without `[...]` data functions and format codes, is
matched against `VOCABULARY` below: words for one faith's clergy, buildings,
books and rites, and the faiths' own names, each with the state religions it
fits.

Gated
-----
For each place a key is named the audit works out which state religions the
country can have when the text shows, and flags the key when one of them is a
religion the word does not fit. The gates it reads, in the country's scope:

- `religion = { has_discrimination_trait = heritage_<x> }`: the religions of
  that heritage, from `vanilla_parsed/common/religions.json` and
  `common/religions/`;
- `country_has_state_religion = rel:<y>` and `religion = rel:<y>`: that one;
- a scripted trigger whose body is made of those (`te_heritage_pali = yes`);
- `AND`, `OR`, `NOT`, `NOR`, `NAND`, `!=` and `always`, over the above.

They count in the event's own `trigger`, an option's `trigger`, the `trigger`
of a `triggered_desc` or of an option's `name` block, and the `limit` of an
`if` / `else_if` around a tooltip or modifier. A later rung of a `first_valid`
also knows that the rungs above it failed, and an `else` that its `if` did,
when those tests are religion tests and nothing else. In a state or building
event the country is `owner = { }`. A religion test under any other scope
change (`scope:x = { }`, `any_scope_state = { }`) is about someone else and
counts for nothing.

A heritage is a family, so `heritage_dharmic` does not gate a guru: the trait
also holds the Buddhist faiths and Sikhism, and the audit flags it. Gate one
faith's scene on that faith.

What it cannot see, and so flags
--------------------------------
- **Culture and country gates.** A Slavic primary culture, a country tag or a
  region does not fix the state religion, which a game can change. Such a text
  is flagged and takes a suppression that says what the gate is.
- **A gate that lives elsewhere**: on the on-action or the event that fires
  this one, or in a variable set earlier (a monument's chosen style). Gate
  the text here too, or suppress with the reason.
- **Real quotations and metaphors.** An attribution line (`— Name`) is signed
  by real and invented speakers alike, so a quotation is not exempt by shape:
  Bryan's "crown of thorns" is flagged and reviewed. So is "Cathedrals of
  Coral".

What it cannot see, and so misses
---------------------------------
- Text outside events: journal entries, decisions, buttons, laws, concepts
  and modifiers nothing in `events/` adds.
- Text reached through `GetCustom` (customizable localization), through a
  loc key built at run time, or through a vanilla key.
- Any word not in `VOCABULARY`, and a scene that is one faith's without using
  one of its words.
- Pops' religion: only the state religion is tested, which is what the mod's
  gates test.

One family is exempt by key, `EXEMPT_KEYS`: the archaeology sites' texts
describe a real place and a real dig, wherever the country stands.
`NAMES` holds proper names that contain a listed word and are not a scene
("Old Church Slavonic", the language).

Suppression is check-tagged and trails the key's loc line (the definition
that wins: the last file in name order), where `check_loc_style.py` and
`long_tooltip_audit` put theirs:

    my_event.3.f:0 "..." # REVIEWED 2026-11-12 (faith_scene): a real quotation, Bryan 1896

Keep the rationale free of `"`. One comment covers the key wherever it is
named. A tag on a line whose key is not flagged is stale and fails `--strict`.

`python3 faith_scene_audit.py --explain <key>` lists where a key is named and
the gate the audit read at each place.

Report: docs/engine/faith_scene_report.md. Registered in POST_LOAD_AUDITS.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

from audit_common import AuditResult as _AuditResult
from audit_common import StaleTag as _StaleTag
from audit_common import cli_main, parse_reviewed, write_text
from mod_state import split_loc_line

CHECK = "faith_scene"
REPORT_PATH = os.path.join("docs", "engine", "faith_scene_report.md")
LOC_DIR = os.path.join("localization", "english")
SKIP_LOC_FILES = frozenset({"te_unused_l_english.yml"})
SKIP_EVENT_PREFIX = "te_debug_"  # console benches
RELIGIONS_SNAPSHOT = os.path.join("vanilla_parsed", "common", "religions.json")
REPO_ROOT = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# The vocabulary
# ---------------------------------------------------------------------------
# Who a word fits: `heritage_<x>` is every religion of that heritage, any other
# name is one religion.
CHRISTIAN = ("heritage_christian",)
ISLAMIC = ("heritage_islamic",)
JEWISH = ("heritage_jewish",)
ABRAHAMIC = CHRISTIAN + ISLAMIC + JEWISH
DHARMIC = ("heritage_dharmic",)
HINDU = ("hindu",)
SIKH = ("sikh",)
# custom_religion_buddhist is the player-made Buddhist faith (common/religions/).
BUDDHIST = ("mahayana", "theravada", "gelugpa", "custom_religion_buddhist")
# Vanilla's Confucian and Shinto state religions stand for China, Korea and
# Japan, where Buddhist monasteries and pagodas are at home.
TAOIC = ("heritage_taoic",)


@dataclass(frozen=True)
class Term:
    faith: str
    """Whose word it is, for the message."""
    fits: tuple[str, ...]
    words: tuple[str, ...]
    """Regex alternatives, matched whole-word and case-insensitively; wrap one
    in `(?-i:...)` where only the capitalized word is the faith's."""


VOCABULARY: tuple[Term, ...] = (
    # --- Christian ------------------------------------------------------------
    Term("Christian", CHRISTIAN, (
        # Clergy and offices.
        r"vicars?", r"pastors?", r"(?:arch)?bishops?", r"deacons?", r"popes?", r"papal", r"reverend",
        r"friars?", r"holy orders",
        # A priest addressed or named. A parent is "my father" or begins a
        # sentence; `, Father.` and `Father Rossi` are the collar.
        r"(?-i:(?<=, )Father(?=[,.!?\\]))", r"(?-i:Father [A-Z][a-z]+)",
        # Places and bodies. Spelled out, so that Churchill is not one.
        r"(?:mega)?church(?:es|man|men|yards?|goers?)?", r"cathedrals?", r"chapels?", r"abbeys?", r"convents?",
        r"parish(?:es|ioners?)?", r"dioces(?:e|es|an)", r"vatican", r"(?:holy )?synods?",
        r"ecumenical", r"encyclicals?", r"pews?",
        # Books and rites. "hymn" alone is left out: most faiths sing them.
        r"bibles?", r"biblical", r"gospels?", r"hymnals?", r"catechisms?", r"baptis(?:m|ms|mal|e|ed)",
        r"christen(?:ed|ing|ings)", r"communion", r"eucharist", r"sunday school", r"crucifix(?:es)?",
        r"crucif(?:y|ied|ixion)", r"crown of thorns", r"rosar(?:y|ies)", r"christmas", r"easter",
        r"god(?:parents?|fathers?|mothers?|sons?|daughters?)",
        # The faith by name.
        r"jesus", r"christ", r"christians?", r"christianity", r"christendom",
    )),
    # Catholic and Protestant only capitalized: "catholic tastes", "a protestant minority view".
    Term("Catholic", ("catholic",), (r"(?-i:Catholics?)", r"(?-i:Catholicism)")),
    Term("Protestant", ("protestant",), (r"(?-i:Protestants?)", r"(?-i:Protestantism)")),
    # "Orthodox" is not listed: orthodox economists are everywhere.
    # --- shared by the faiths of the book --------------------------------------
    # The mod's own Islamic rungs have a Friday sermon (religious_revival_events.2.f_islamic),
    # a mosque has a minbar and a synagogue a bimah, both "pulpit" in English.
    Term("Christian, Islamic and Jewish", ABRAHAMIC, (r"sermons?", r"pulpits?")),
    Term("Christian and Jewish", CHRISTIAN + JEWISH, (r"sabbath", r"tithes?")),
    # A priest serves a Christian altar, a Hindu temple (religious_revival_events.3.f_dharmic),
    # a Shinto shrine and a Chinese temple. Islam, Judaism and Sikhism have none, and the mod
    # calls Buddhist clergy monks.
    Term("Christian, Hindu, Shinto and Chinese", CHRISTIAN + HINDU + TAOIC, (r"priests?", r"priesthoods?")),
    # Monks, nuns and monasteries: Christian, and every dharmic faith but with the taoic
    # countries' Buddhists (see TAOIC).
    Term("Christian, dharmic and East Asian", CHRISTIAN + DHARMIC + TAOIC,
         (r"monks?", r"nuns?", r"monaster(?:y|ies)", r"abbots?", r"abbess(?:es)?")),
    # --- Islamic --------------------------------------------------------------
    Term("Islamic", ISLAMIC, (
        r"imams?", r"mullahs?", r"ayatollahs?", r"muftis?", r"muezzins?", r"ulama", r"ulema",
        r"qadis?", r"caliphs?", r"caliphates?", r"caliphal", r"dervish(?:es)?",
        r"mosques?", r"minarets?", r"madrass?as?", r"waqfs?",
        r"qur'?an(?:ic)?", r"koran(?:ic)?", r"sharia", r"fatwas?", r"zakat", r"hajj", r"ramadan",
        r"(?-i:Eid)", r"halal", r"jihad\w*", r"friday (?:prayers?|sermons?)", r"(?-i:the Prophet)",
        r"islam", r"islamic", r"islamis[mt]s?", r"muslims?", r"(?-i:Sufis?)", r"(?-i:Sufism)",
    )),
    # --- Jewish ---------------------------------------------------------------
    Term("Jewish", JEWISH, (
        r"rabbis?", r"rabbinic(?:al)?", r"synagogues?", r"yeshivas?", r"torah", r"talmud(?:ic)?",
        r"kosher", r"shabbat", r"passover", r"yom kippur", r"menorahs?",
        r"jews?", r"jewish", r"judaism",
    )),
    # --- Hindu ----------------------------------------------------------------
    # "caste" is the guide's own example of a Hindu scene. A text that means an officer caste
    # or a caste of engineers takes the suppression.
    Term("Hindu", HINDU, (
        r"swamis?", r"sadhus?", r"pandits?", r"brahmins?", r"yogis?", r"ashrams?", r"mandirs?",
        r"pujas?", r"(?-i:Vedas?)", r"(?-i:Vedic)", r"castes?", r"diwali",
        r"hindus?", r"hinduism", r"hindutva",
    )),
    Term("Hindu and Sikh", HINDU + SIKH, (r"gurus?",)),
    Term("dharmic", DHARMIC, (r"dharma", r"sutras?")),
    # --- Sikh -----------------------------------------------------------------
    Term("Sikh", SIKH, (r"gurdwaras?", r"granthis?", r"khalsa", r"sikhs?", r"sikhism")),
    # --- Buddhist -------------------------------------------------------------
    Term("Buddhist", BUDDHIST, (
        r"lamas?", r"sangha", r"stupas?", r"bodhisattvas?",
        r"buddhas?", r"buddhists?", r"buddhism",
    )),
    Term("Buddhist and East Asian", BUDDHIST + TAOIC, (r"pagodas?",)),
    # --- East Asian -----------------------------------------------------------
    Term("Shinto", ("shinto",), (r"shinto(?:ists?|ism)?", r"kami", r"torii")),
    Term("Confucian and Taoist", TAOIC, (
        r"confucius", r"confucian(?:s|ism)?", r"taois[mt]s?", r"daois[mt]s?",
    )),
)
# Deliberately in no list, because every faith has them or the mod's neutral rungs use them:
# temple, shrine, house of worship, prayer, the faithful, the devout, clergy, cleric, preacher,
# congregation, scripture, holy day, pilgrim, saint, altar, blessing, sacred, theology, sin.

# Proper names that contain a listed word and are not a scene.
NAMES: tuple[str, ...] = (
    r"(?:Old )?Church Slavonic",  # the language; extra_law_events.25 and the monuments name it
)

# Key families that describe a real, named place and what was really found there. The country
# that owns the state did not choose the site's faith.
EXEMPT_KEYS = re.compile(r"^gm_arch_site_")

# ---------------------------------------------------------------------------
# Script tree
# ---------------------------------------------------------------------------

# A comment, a line break (counted), a quoted string, a brace, an operator, a word.
_TOKEN_RE = re.compile(r'#[^\n]*|\n|"[^"\n]*"|[{}]|\?=|[<>!=]=|[=<>]|[^\s{}=<>!?"#]+')
_OPERATORS = frozenset({"=", "?=", "==", "!=", "<", ">", "<=", ">="})
_EVENT_ID_RE = re.compile(r"^[A-Za-z_]\w*\.\d+$")
_NUMBER_RE = re.compile(r"^-?[\d.]+$")
_PARAM_RE = re.compile(r"\$(\w+)\$")


@dataclass
class Node:
    key: str
    op: str
    value: str | None
    children: list[Node] | None
    line: int


def parse_script(text: str) -> list[Node]:
    """A Paradox script as a tree of `key op value` and `key = { ... }` nodes,
    each with its line. Duplicate keys and their order are kept, which the
    repository's dict-building parser does not do."""
    tokens: list[tuple[str, int]] = []
    number = 1
    for token in _TOKEN_RE.findall(text):
        if token == "\n":
            number += 1
        elif token[0] != "#":
            tokens.append((token, number))
    pos = 0

    def block() -> list[Node]:
        nonlocal pos
        nodes: list[Node] = []
        while pos < len(tokens):
            token, line = tokens[pos]
            pos += 1
            if token == "}":
                return nodes
            if token == "{":
                nodes.append(Node("", "=", None, block(), line))
            elif pos < len(tokens) and tokens[pos][0] in _OPERATORS:
                op = tokens[pos][0]
                pos += 1
                if pos >= len(tokens):
                    break
                value = tokens[pos][0]
                pos += 1
                if value == "{":
                    nodes.append(Node(token.strip('"'), op, None, block(), line))
                else:
                    nodes.append(Node(token.strip('"'), op, value.strip('"'), None, line))
            else:
                nodes.append(Node(token.strip('"'), "", None, None, line))
        return nodes

    return block()


def _substitute(nodes: list[Node], args: dict[str, str]) -> list[Node]:
    """A scripted effect's or trigger's body with its `$X$` filled in."""
    def fill(text: str | None) -> str | None:
        if text is None or "$" not in text:
            return text
        return _PARAM_RE.sub(lambda m: args.get(m.group(1), m.group(0)), text)

    return [
        Node(fill(n.key), n.op, fill(n.value),
             None if n.children is None else _substitute(n.children, args), n.line)
        for n in nodes
    ]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8-sig", errors="replace")


def _definitions(root: Path, folder: str) -> dict[str, list[Node]]:
    """Top-level `name = { ... }` blocks of every file in `common/<folder>`."""
    found: dict[str, list[Node]] = {}
    directory = root / "common" / folder
    if directory.is_dir():
        for path in sorted(directory.glob("*.txt")):
            for node in parse_script(_read(path)):
                if node.children is not None and node.key:
                    found[node.key] = node.children
    return found


# ---------------------------------------------------------------------------
# Religions and gates
# ---------------------------------------------------------------------------


def load_religions(root: Path) -> dict[str, str]:
    """{religion: heritage} for vanilla (the committed snapshot, the tree's own
    or failing that this checkout's) and the mod's `common/religions/`."""
    religions: dict[str, str] = {}
    for base in (root, Path(REPO_ROOT)):
        snapshot = base / RELIGIONS_SNAPSHOT
        if snapshot.is_file():
            for name, entry in json.loads(snapshot.read_text(encoding="utf-8")).items():
                heritage = entry[1].get("heritage") if isinstance(entry[1], dict) else None
                if heritage:
                    religions[name] = heritage[1]
            break
    for name, body in _definitions(root, "religions").items():
        for child in body:
            if child.key == "heritage" and child.value:
                religions[name] = child.value
    if not religions:
        raise FileNotFoundError(
            f"no religion found: {RELIGIONS_SNAPSHOT} is missing (rebuild it with "
            "`python3 vanilla_parsed.py build` on a machine with the game)"
        )
    return religions


class Faiths:
    """The religions a country can have, and which of them a gate leaves."""

    def __init__(self, religions: dict[str, str], triggers: dict[str, list[Node]] | None = None):
        self.heritage_of = dict(religions)
        self.all = frozenset(religions)
        self.heritages = frozenset(religions.values())
        self.triggers = triggers or {}
        self._expanding: set[str] = set()

    def named(self, names: tuple[str, ...]) -> frozenset[str]:
        """The religions a `fits` tuple names."""
        out: set[str] = set()
        for name in names:
            if name.startswith("heritage_"):
                out |= {r for r, h in self.heritage_of.items() if h == name}
            elif name in self.heritage_of:
                out.add(name)
        return frozenset(out)

    def unknown(self, names: tuple[str, ...]) -> list[str]:
        return [n for n in names if n not in self.heritages and n not in self.heritage_of]

    # A gate reads as (the religions that pass it, whether that is exact). An
    # inexact set is an upper bound: a test the audit can't read passes
    # everyone. Only an exact set may be negated.

    def _all_of(self, nodes, scope, root):
        admitted, exact = self.all, True
        for node in nodes:
            got, sure = self._one(node, scope, root)
            admitted &= got
            exact = exact and sure
        return admitted, exact

    def _any_of(self, nodes, scope, root):
        admitted, exact = frozenset(), True
        for node in nodes:
            got, sure = self._one(node, scope, root)
            admitted |= got
            exact = exact and sure
        return admitted, exact

    def _not(self, pair):
        admitted, exact = pair
        return (self.all - admitted, True) if exact else (self.all, False)

    def _one(self, node: Node, scope: str, root: str):
        key, kids = node.key, node.children
        if kids is not None:
            if key == "AND":
                return self._all_of(kids, scope, root)
            if key == "OR":
                return self._any_of(kids, scope, root)
            if key in ("NOT", "NOR"):
                return self._not(self._any_of(kids, scope, root))
            if key == "NAND":
                return self._not(self._all_of(kids, scope, root))
            if key.lower() == "root":
                return self._all_of(kids, root, root)
            if key == "owner" and scope == "holder":
                return self._all_of(kids, "country", root)
            if key in ("custom_tooltip", "custom_description", "hidden_trigger"):
                return self._all_of([k for k in kids if k.key != "text"], scope, root)
        if key == "always" and node.value in ("yes", "no"):
            return (self.all, True) if node.value == "yes" else (frozenset(), True)
        if scope == "religion":
            if key == "has_discrimination_trait" and node.value in self.heritages:
                admitted = self.named((node.value,))
                return self._not((admitted, True)) if node.op == "!=" else (admitted, True)
            return self.all, False
        if scope != "country":
            return self.all, False
        if key in ("country_has_state_religion", "religion") and node.value and node.value.startswith("rel:"):
            name = node.value[4:]
            if name not in self.heritage_of or node.op not in ("=", "?=", "==", "!="):
                return self.all, False
            admitted = frozenset({name})
            return self._not((admitted, True)) if node.op == "!=" else (admitted, True)
        if key == "religion" and kids is not None:
            return self._all_of(kids, "religion", root)
        if key in self.triggers and key not in self._expanding:
            if node.value in ("yes", "no"):
                body = self.triggers[key]
            elif kids is not None:
                body = _substitute(self.triggers[key], {k.key: k.value for k in kids if k.value is not None})
            else:
                return self.all, False
            self._expanding.add(key)
            try:
                pair = self._all_of(body, scope, root)
            finally:
                self._expanding.discard(key)
            return self._not(pair) if node.value == "no" else pair
        return self.all, False

    def gate(self, nodes: list[Node], scope: str, root: str) -> tuple[frozenset[str], bool]:
        """What a trigger block's lines admit, read together."""
        return self._all_of(nodes, scope, root)


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------

TEXT_FIELDS = ("title", "desc", "flavor")
# Effect blocks that run in the scope they are written in.
_SAME_SCOPE = frozenset({
    "if", "else_if", "else", "hidden_effect", "show_as_tooltip", "random", "random_list", "while",
    "custom_tooltip", "custom_description", "custom_description_no_bullet", "switch",
})
_NOT_EFFECTS = frozenset({"limit", "trigger", "ai_chance", "modifier", "event_image"})
_ADD_MODIFIER_RE = re.compile(r"^add_(?:\w+_)?modifier$")
_MAX_EFFECT_DEPTH = 6


@dataclass(frozen=True)
class Site:
    """One place an event shows a key."""
    key: str
    event: str
    part: str   # title | desc | flavor | option | tooltip | modifier
    file: str   # mod-relative
    line: int
    admits: frozenset[str]
    via: str = ""  # the scripted effect the reference sits in, if any


def effects_with_text(effects: dict[str, list[Node]]) -> dict[str, list[Node]]:
    """The scripted effects that can show a text or add a modifier, themselves
    or through an effect they call. The rest need no walk."""
    def keys(nodes: list[Node], into: set[str]) -> set[str]:
        for node in nodes:
            into.add(node.key)
            if node.children is not None:
                keys(node.children, into)
        return into

    named = {name: keys(body, set()) for name, body in effects.items()}
    shows = {
        name for name, used in named.items()
        if "custom_tooltip" in used or "text" in used or any(_ADD_MODIFIER_RE.match(k) for k in used)
    }
    grew = True
    while grew:
        more = {name for name, used in named.items() if name not in shows and used & shows}
        grew = bool(more)
        shows |= more
    return {name: effects[name] for name in shows}


class _EventWalk:
    def __init__(self, faiths: Faiths, effects: dict[str, list[Node]], event: Node, rel: str):
        self.faiths = faiths
        self.effects = effects
        self.event = event
        self.rel = rel
        kind = next((c.value for c in event.children if c.key == "type"), "country_event")
        self.root = "country" if kind == "country_event" else "holder"
        self.sites: list[Site] = []
        self._calls: list[str] = []  # scripted effects being walked, outermost first
        self._call_line = 0          # the event's line that made the outermost call

    def _gate(self, nodes: list[Node], scope: str | None = None):
        return self.faiths.gate(nodes, scope or self.root, self.root)

    def _child_gate(self, node: Node, key: str, scope: str | None = None):
        admitted, exact = self.faiths.all, True
        for child in node.children:
            if child.key == key and child.children is not None:
                got, sure = self._gate(child.children, scope)
                admitted &= got
                exact = exact and sure
        return admitted, exact

    def _add(self, key: str | None, part: str, line: int, admits: frozenset[str]) -> None:
        if key:
            self.sites.append(Site(key, self.event.key, part, self.rel,
                                   line if not self._calls else self._call_line, admits,
                                   self._calls[-1] if self._calls else ""))

    def run(self) -> list[Site]:
        base = self._child_gate(self.event, "trigger")[0]
        for child in self.event.children:
            if child.key in TEXT_FIELDS:
                self._text(child, child.key, base)
            elif child.key == "option" and child.children is not None:
                self._option(child, base)
            elif child.key in ("immediate", "after") and child.children is not None:
                self._effects(child.children, base, self.root)
        return self.sites

    def _text(self, node: Node, part: str, admits: frozenset[str]) -> None:
        if node.value is not None:
            self._add(node.value, part, node.line, admits)
        elif node.children is not None:
            self._desc_block(node.children, part, admits, ladder=False)

    def _desc_block(self, nodes: list[Node], part: str, admits: frozenset[str], ladder: bool) -> None:
        """`desc = { ... }`: its parts are all shown, except inside a
        `first_valid`, where a rung shows only if the rungs above it failed."""
        left = self.faiths.all
        for node in nodes:
            here = admits & left if ladder else admits
            if node.key == "desc":
                self._text(node, part, here)
            elif node.children is None:
                continue
            elif node.key == "first_valid":
                self._desc_block(node.children, part, here, ladder=True)
            elif node.key == "random_valid":
                self._desc_block(node.children, part, here, ladder=False)
            elif node.key == "triggered_desc":
                passes, exact = self._child_gate(node, "trigger")
                rest = [c for c in node.children if c.key != "trigger"]
                self._desc_block(rest, part, here & passes, ladder=False)
                if ladder and exact:
                    left -= passes

    def _option(self, option: Node, base: frozenset[str]) -> None:
        admits = base & self._child_gate(option, "trigger")[0]
        for child in option.children:
            if child.key == "name" and child.value is not None:
                self._add(child.value, "option", child.line, admits)
            elif child.key == "name" and child.children is not None:
                passes = self._child_gate(child, "trigger")[0]
                for part in child.children:
                    if part.key == "text" and part.value is not None:
                        self._add(part.value, "option", part.line, admits & passes)
            elif child.key == "trigger" and child.children is not None:
                self._tooltips(child.children, admits)
        self._effects([c for c in option.children if c.key not in ("name", "trigger")], admits, self.root)

    def _tooltips(self, nodes: list[Node], admits: frozenset[str]) -> None:
        """The `custom_tooltip` texts of a trigger block."""
        for node in nodes:
            if node.key in ("custom_tooltip", "text") and node.value is not None:
                self._add(node.value, "tooltip", node.line, admits)
            elif node.children is not None:
                self._tooltips(node.children, admits)

    def _effects(self, nodes: list[Node], admits: frozenset[str], scope: str) -> None:
        left = self.faiths.all  # what the if-chain so far has not taken
        for node in nodes:
            key, kids = node.key, node.children
            if key in ("custom_tooltip", "text") and node.value is not None:
                self._add(node.value, "tooltip", node.line, admits)
            elif _ADD_MODIFIER_RE.match(key):
                name = node.value if kids is None else next(
                    (c.value for c in kids if c.key == "name" and c.value is not None), None)
                if name and "$" not in name and ":" not in name:
                    self._add(name, "modifier", node.line, admits)
                    self._add(name + "_desc", "modifier", node.line, admits)
            elif key in self.effects and (kids is not None or node.value == "yes"):
                self._call(node, admits, scope)
            elif kids is None or key in _NOT_EFFECTS:
                continue
            elif key in ("if", "else_if", "else"):
                if key == "if":
                    left = self.faiths.all
                # Under a scope change the limit tests someone else.
                passes, exact = (self._child_gate(node, "limit", scope) if scope != "other"
                                 else (self.faiths.all, False))
                self._effects([c for c in kids if c.key != "limit"], admits & left & passes, scope)
                if exact:
                    left -= passes
            elif key in _SAME_SCOPE or _NUMBER_RE.match(key):
                self._effects(kids, admits, scope)
            elif key.lower() == "root":
                self._effects(kids, admits, self.root)
            elif key == "owner" and scope == "holder":
                self._effects(kids, admits, "country")
            else:
                # Any other block is a scope change, or an effect's arguments: a
                # religion test inside it is about someone else.
                self._effects(kids, admits, "other")

    def _call(self, node: Node, admits: frozenset[str], scope: str) -> None:
        name = node.key
        if name in self._calls or len(self._calls) >= _MAX_EFFECT_DEPTH:
            return
        body = self.effects[name]
        if node.children is not None:
            body = _substitute(body, {c.key: c.value for c in node.children if c.value is not None})
        if not self._calls:
            self._call_line = node.line
        self._calls.append(name)
        try:
            self._effects(body, admits, scope)
        finally:
            self._calls.pop()


def event_sites(root: Path, faiths: Faiths, effects: dict[str, list[Node]]) -> tuple[list[Site], int]:
    """Every (key, place, gate) the mod's events show, and how many events were read."""
    sites: list[Site] = []
    events = 0
    events_dir = root / "events"
    for path in sorted(events_dir.rglob("*.txt")) if events_dir.is_dir() else ():
        if path.name.startswith(SKIP_EVENT_PREFIX):
            continue
        rel = path.relative_to(root).as_posix()
        for node in parse_script(_read(path)):
            if node.children is None or not _EVENT_ID_RE.match(node.key):
                continue
            if any(c.key == "hidden" and c.value == "yes" for c in node.children):
                continue
            events += 1
            sites += _EventWalk(faiths, effects, node, rel).run()
    return sites, events


# ---------------------------------------------------------------------------
# Loc and matching
# ---------------------------------------------------------------------------

_SPLICE_RE = re.compile(r"\$([\w.\-]+)(?:\|[^$]*)?\$")
_MARKUP_RE = re.compile(r"\$[^$\s]*\$|@\w+!|#[A-Za-z_;:,\[\]().']+\s|#!")
_NAMES_RE = re.compile("|".join(NAMES))


@dataclass
class LocEntry:
    value: str
    file: str
    line: int
    tag: dict | None


def load_loc(root: Path) -> tuple[dict[str, LocEntry], list[tuple[str, int, str]]]:
    """The mod's English loc, last file (name order, `replace/` last) winning,
    and every tagged line as (file, line, key), overridden copies included."""
    entries: dict[str, LocEntry] = {}
    tagged: list[tuple[str, int, str]] = []
    loc_dir = root / LOC_DIR
    files = sorted(p for p in loc_dir.rglob("*.yml") if p.name not in SKIP_LOC_FILES) if loc_dir.is_dir() else []
    if not files:
        raise FileNotFoundError(f"no loc file to scan under {loc_dir}")
    for path in sorted(files, key=lambda p: (p.parent.name == "replace", p.name)):
        rel = path.relative_to(root).as_posix()
        for number, raw in enumerate(_read(path).splitlines(), 1):
            parsed = split_loc_line(raw)
            if parsed is None:
                continue
            key, value, trailing = parsed
            tag = parse_reviewed(trailing, (CHECK,))
            if tag:
                tagged.append((rel, number, key))
            entries[key] = LocEntry(value, rel, number, tag)
    return entries, tagged


def prose(value: str) -> str:
    """The value's own words: `[...]` data functions (nested ones too), spliced
    keys, icons and format codes replaced by a space, proper names in `NAMES`
    taken out."""
    out, depth = [], 0
    for ch in value:
        if ch == "[":
            depth += 1
            out.append(" ")
        elif ch == "]" and depth:
            depth -= 1
        elif not depth:
            out.append(ch)
    return _NAMES_RE.sub(" ", _MARKUP_RE.sub(" ", "".join(out)))


@dataclass(frozen=True)
class Hit:
    word: str
    term: Term


class Matcher:
    def __init__(self, vocabulary: tuple[Term, ...] = VOCABULARY):
        self._terms = [
            (term, re.compile(r"\b(?:" + "|".join(term.words) + r")\b", re.IGNORECASE))
            for term in vocabulary
        ]

    def hits(self, value: str) -> list[Hit]:
        """One Hit per (term, word as written), in the order found."""
        text = prose(value)
        found: dict[tuple[str, str], Hit] = {}
        for term, pattern in self._terms:
            for m in pattern.finditer(text):
                found.setdefault((term.faith, m.group(0).lower()), Hit(m.group(0), term))
        return list(found.values())


def spliced_keys(key: str, loc: dict[str, LocEntry]) -> list[str]:
    """`key` and every mod key its text splices in, recursively."""
    seen: list[str] = []
    stack = [key]
    while stack:
        current = stack.pop()
        if current in seen or current not in loc:
            continue
        seen.append(current)
        stack += [m.group(1) for m in _SPLICE_RE.finditer(loc[current].value)]
    return seen


# ---------------------------------------------------------------------------
# The audit
# ---------------------------------------------------------------------------


@dataclass
class Flag:
    key: str
    loc_file: str
    loc_line: int
    words: list[tuple[str, str]] = field(default_factory=list)  # (word as written, whose it is)
    sites: list[tuple[Site, tuple[str, ...]]] = field(default_factory=list)  # (place, wrong faiths)
    exemption: dict | None = None


@dataclass
class StaleTag(_StaleTag):
    """A `(faith_scene)` tag that suppresses nothing, on `key`'s loc line."""

    key: str = ""


@dataclass
class AuditResult(_AuditResult):
    """`stale` holds the tags that suppress nothing."""

    flags: list[Flag] = field(default_factory=list)
    events_read: int = 0
    keys_read: int = 0
    gated_uses: int = 0  # (key, place) pairs with a listed word that a gate makes safe
    sites: list[Site] = field(default_factory=list)
    religions: int = 0


def audit(mod_path: str | Path | None = None, vocabulary: tuple[Term, ...] = VOCABULARY) -> AuditResult:
    if mod_path is None:
        from path_constants import mod_path as _default
        mod_path = _default
    root = Path(mod_path)
    faiths = Faiths(load_religions(root), _definitions(root, "scripted_triggers"))
    loc, tagged = load_loc(root)
    sites, events = event_sites(root, faiths, effects_with_text(_definitions(root, "scripted_effects")))
    matcher = Matcher(vocabulary)

    result = AuditResult(events_read=events, sites=sites, religions=len(faiths.all))
    hits_of: dict[str, list[Hit]] = {}
    fits: dict[str, frozenset[str]] = {}
    flags: dict[str, Flag] = {}
    read: set[str] = set()
    for site in sites:
        for key in spliced_keys(site.key, loc):
            read.add(key)
            if EXEMPT_KEYS.match(key):
                continue
            if key not in hits_of:
                hits_of[key] = matcher.hits(loc[key].value)
            if not hits_of[key]:
                continue
            wrong: set[str] = set()
            words: list[tuple[str, str]] = []
            for hit in hits_of[key]:
                if hit.term.faith not in fits:
                    fits[hit.term.faith] = faiths.named(hit.term.fits)
                outside = site.admits - fits[hit.term.faith]
                if outside:
                    wrong |= outside
                    words.append((hit.word, hit.term.faith))
            if not wrong:
                result.gated_uses += 1
                continue
            entry = loc[key]
            flag = flags.setdefault(key, Flag(key, entry.file, entry.line, exemption=entry.tag))
            flag.words += [w for w in words if w not in flag.words]
            shown = tuple(sorted(wrong)) if site.admits != faiths.all else ()
            if (site, shown) not in flag.sites:
                flag.sites.append((site, shown))
    result.keys_read = len(read)
    result.flags = sorted(flags.values(), key=lambda f: (f.loc_file, f.loc_line))
    for rel, number, key in tagged:
        winning = loc.get(key)
        if key not in flags or (winning.file, winning.line) != (rel, number):
            result.stale.append(StaleTag(rel, number, CHECK, key=key))
    return result


def _gate_text(wrong: tuple[str, ...]) -> str:
    if not wrong:
        return "no religion gate"
    shown = ", ".join(wrong[:4]) + (f" and {len(wrong) - 4} more" if len(wrong) > 4 else "")
    return f"its gate also admits {shown}"


def _site_text(site: Site, wrong: tuple[str, ...]) -> str:
    via = f" through `{site.via}`" if site.via else ""
    return f"`{site.event}` {site.part}{via} (`{site.file}:{site.line}`): {_gate_text(wrong)}"


def _words_text(flag: Flag) -> str:
    return ", ".join(f"\"{word}\" ({whose})" for word, whose in flag.words)


def render_report(result: AuditResult) -> str:
    unreviewed = result.unreviewed
    reviewed = result.exemptions
    out = [
        "# Faith scene audit report",
        "",
        "Auto-generated by `faith_scene_audit.py` on every `POST /reload` of the",
        "mod state server. Do not hand-edit.",
        "",
        "Flagged: a loc key an event shows (title, description, flavor, option, tooltip,",
        "or a modifier it adds) whose text has a word of one faith, named in a place",
        "where the country's state religion can be one the word does not fit (#1531).",
        "Write the scene without a named faith, or gate that version on the faith:",
        "`religion = { has_discrimination_trait = heritage_<x> }` for a family,",
        "`country_has_state_religion = rel:<y>` for one faith",
        "(`docs/guides/event_creation_guide.md`, \"One faith's scene in an event any",
        "country gets\"). The words and the faiths each fits are `VOCABULARY` in the audit.",
        "",
        "Suppress a deliberate case trailing on the key's loc line (no `\"` in the",
        "rationale): `# REVIEWED YYYY-MM-DD (faith_scene): why`",
        "",
        "## Unreviewed flags",
        "",
    ]
    if not unreviewed:
        out += ["_None._", ""]
    for flag in unreviewed:
        out.append(f"- `{flag.key}` (`{flag.loc_file}:{flag.loc_line}`): {_words_text(flag)}")
        out += [f"  - {_site_text(site, wrong)}" for site, wrong in flag.sites]
    if unreviewed:
        out.append("")

    if result.stale:
        out += ["## Stale tags", "", "Tags that suppress nothing; remove them.", ""]
        out += [f"- `{t.file}:{t.line}` `{t.key}` ({CHECK})" for t in result.stale]
        out.append("")

    out += ["## Reviewed exemptions", ""]
    if not reviewed:
        out += ["_None._", ""]
    else:
        out += [
            f"- `{f.key}`: {_words_text(f)} — **{f.exemption['date']}**: {f.exemption['rationale']}"
            for f in reviewed
        ]
        out.append("")
    out += [
        "## Coverage",
        "",
        f"- events read: {result.events_read}",
        f"- loc keys read: {result.keys_read}",
        f"- uses of a listed word that a gate makes safe: {result.gated_uses}",
        f"- total flags: {len(result.flags)}",
        f"- unreviewed: {len(unreviewed)}",
        f"- exempted: {len(reviewed)}",
        f"- stale tags: {len(result.stale)}",
        "",
    ]
    return "\n".join(out) + "\n"


def explain(result: AuditResult, mod_path: str | Path, key: str) -> str:
    """Where `key` is named, directly or through a splice, and the gate read at
    each place."""
    root = Path(mod_path)
    faiths = Faiths(load_religions(root))
    loc, _ = load_loc(root)
    if key not in loc:
        return f"{key}: not a key of the mod's English loc."
    lines = [f"{key}: " + (", ".join(f"\"{h.word}\" ({h.term.faith})" for h in Matcher().hits(loc[key].value))
                           or "no listed word")]
    shown = [s for s in result.sites if key in spliced_keys(s.key, loc)]
    if not shown:
        lines.append("  no event shows it: the audit does not read it")
    for site in shown:
        if site.admits == faiths.all:
            gate = "any state religion"
        else:
            gate = "state religion one of: " + (", ".join(sorted(site.admits)) or "none (never shown)")
        lines.append(f"  {site.event} {site.part}" + (f" through {site.via}" if site.via else "")
                     + (f" as part of {site.key}" if site.key != key else "")
                     + f" ({site.file}:{site.line}): {gate}")
    return "\n".join(lines)


def regenerate(mod_state=None) -> dict:
    """POST_LOAD_AUDITS hook: run the audit and write the report. Reads the
    event and loc files itself, so `mod_state` is unused."""
    from path_constants import mod_path
    result = audit(mod_path)
    out_path = os.path.join(mod_path, REPORT_PATH)
    write_text(out_path, render_report(result))
    return {
        # Flags without a tag, plus tags that suppress nothing.
        "unreviewed": len(result.failing),
        "total_flags": len(result.flags),
        "exempted": len(result.exemptions),
        "stale_tags": len(result.stale),
        "events_read": result.events_read,
        "keys_read": result.keys_read,
        "path": out_path,
    }


def main(argv=None) -> int:
    """Print the report, or with `--explain` where one key is named; `--strict`
    (CI) exits 1 on any untagged flag or stale tag and names each."""
    def add_arguments(parser) -> None:
        parser.add_argument("--explain", metavar="KEY",
                            help="list where a loc key is named and the gate read at each place")
        parser.add_argument("--mod-path", type=Path)

    def run(args) -> AuditResult:
        if args.mod_path is None:
            from path_constants import mod_path
            args.mod_path = Path(mod_path)
        if args.explain:
            args.strict = False  # `--explain` only lists: it exits 0
        return audit(args.mod_path)

    def render(result: AuditResult, args) -> str:
        if args.explain:
            return explain(result, args.mod_path, args.explain)
        out = [render_report(result)]
        if args.strict and result.failed:
            # The runner shows a failing audit's last lines: say what failed there.
            out += [f"FLAG  {flag.loc_file}:{flag.loc_line}: {flag.key}: {_words_text(flag)}"
                    for flag in result.unreviewed]
            out += [f"STALE {tag.file}:{tag.line}: {tag.key}: the ({CHECK}) comment suppresses nothing"
                    for tag in result.stale]
        return "\n".join(out)

    return cli_main(run, render, argv=argv, description=__doc__.splitlines()[0],
                    add_arguments=add_arguments,
                    strict_help="exit 1 on any untagged flag or stale tag (CI mode)")


if __name__ == "__main__":
    raise SystemExit(main())
