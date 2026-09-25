"""Parse-time audit: events whose text does not match the context they fire in.

Two families of narrative bug that the engine cannot see (M_NEW2 #2 and #3 in
`docs/audits/open_issues.md`, and the system-bypass class PR #418 fixed by hand):

1. **`system_ungated`** — an event talks about one of the mod's systems (spies,
   bank runs, a space programme, a nuclear standoff, the UN, …) but neither
   reads that system's state nor yields to it. It fires on its own schedule and
   can contradict the system: "our spy was caught" while we run no covert
   operation, a space milestone the space race never recorded.
2. **`unchosen_self_action`** — an event tells country R that *R* did something
   ("our information campaign", "our military expansion") although R reached
   the event from a pulse, a random pool or another country's choice, never its
   own. The canonical case: `international_relations_events.4` fires randomly
   on A, says rival B has launched a disinformation campaign, and if A
   counter-attacks B gets `.106` — "[A] has answered our information campaign"
   plus a backlash modifier. B never chose a campaign.
3. **`imputed_foreign_action`** — the event itself picks another country X
   (`random_country` / `random_rival_country` / … in `immediate`), says X did
   something, and lands consequences on X (relations, a modifier, a follow-up
   event). If X is a player, it is punished for an action it never took.

All three are **ranking heuristics, not verdicts**: they surface candidates
for a human read. Each flag carries the event's dispatch sites (who fires it,
in which scope, under which gate) so the read is quick.

How the dispatch graph is built
-------------------------------
Every `trigger_event` and every event listed in an on-action `events` /
`random_events` / `first_valid` list is a *dispatch site*. Each site records
the entity it sits in (an event, on-action, scripted effect, journal entry,
decision, button, …), whether a scope switch sits between that entity and the
call (`scope:x = { … }`, `random_country = { … }`, `owner = { … }`), and the
conditions guarding it (every enclosing `limit` / `trigger`, plus the if-chain
siblings of an `else`). Scripted effects and custom on-actions are resolved
through their own call sites.

*Gated for system S*: the event's own block reads S's state (its game rule,
journal entry, or a trigger/effect/variable prefix the system owns), or the
event lives in S's own file, or **every** dispatch site is guarded by S's
state, sits in S's own file, or sits in an event / effect / on-action that is
itself gated for S.

*Chosen by the recipient*: every dispatch site is in the recipient's own event
option (no scope switch), a decision, a button, a law hook, a diplomatic
action or a treaty — or in an `immediate` / effect / on-action whose own
dispatch is chosen. A pulse, a journal-entry tick or any scope switch is not.

Suppression
-----------
A `# REVIEWED` comment on the event's opening line is already read by three
other audits (see `docs/guides/scripting_best_practices.md` § "One `# REVIEWED`
Comment Suppresses Every Audit That Reads That Line"), so this audit uses a
**check-tagged** comment on its own line anywhere inside the event block:

    # REVIEWED 2026-09-25 (system_ungated): fires only from the disabled-rule branch

The tag sits between the date and the colon, so the other audits' regex
(which wants the colon straight after the date) never reads it. One comment
suppresses one check; `(all)` suppresses every check on that event.

Report: docs/engine/event_context_report.md. Registered in POST_LOAD_AUDITS.
"""

from __future__ import annotations

import os
import re
from collections import defaultdict
from dataclasses import dataclass, field

CHECKS = ("system_ungated", "unchosen_self_action", "imputed_foreign_action")

# ---------------------------------------------------------------------------
# System registry
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class System:
    key: str
    name: str
    # Anything in an event block or a dispatch guard that reads/writes the
    # system's own state: its game rule, journal entry, owned helpers/vars.
    state_re: re.Pattern
    # Mod files (basename) that belong to the system: events there are gated by
    # construction, and dispatch from there is system dispatch.
    file_re: re.Pattern
    # Player-facing vocabulary that means an event is *about* the system.
    vocab_re: re.Pattern


def _rx(pattern: str, flags: int = 0) -> re.Pattern:
    return re.compile(pattern, flags)


_I = re.IGNORECASE

SYSTEMS: tuple[System, ...] = (
    System(
        "banking", "Banking cycle / monetary policy",
        _rx(r"\bbanking_system_(?:enabled|disabled|simplified)\b|\bje_banking_cycle\b"
            r"|\bbanking_\w+|\bte_mon_\w+|\bfinance_cycle_\w+|\bfinreg_\w+|\bte_peg_\w+"),
        _rx(r"^(?:banking_|te_monetary|te_mon_|te_peg|te_inflation|monetary_)"),
        _rx(r"\bbank runs?\b|\brun on the banks?\b|\bbanking (?:crisis|panic|collapse)\b"
            r"|\bcentral bank\b|\bbail-?outs?\b|\bfinancial (?:panic|contagion)\b"
            r"|\bcredit crunch\b|\bhyperinflation\b|\bmonetary policy\b|\bcurrency peg\b", _I),
    ),
    System(
        "covert", "Covert warfare",
        _rx(r"\bcovert_warfare_(?:enabled|disabled)\b|\bje_covert_warfare\b|\bcovert_\w+|\biw_\w+"),
        _rx(r"^covert_"),
        _rx(r"\bspy\b(?! satellites?)|\bspies\b|\bespionage\b|\bspy rings?\b"
            r"|\bintelligence (?:operatives?|agents?|networks?)\b|\bforeign (?:operatives?|agents?)\b"
            r"|\bcovert(?:ly)? (?:operations?|funding|funded|action)\b|\bcampaign of disinformation\b"
            r"|\bforeign disinformation\b|\belection interference\b"
            r"|\bforeign (?:interference|meddling)\b", _I),
    ),
    System(
        "space", "Space race",
        _rx(r"\bspace_race_(?:enabled|disabled)\b|\bje_space_race_\w+|\bspace_race_\w+|\bsr_\w+"
            r"|\bte_space_\w+"),
        _rx(r"^(?:space_race|probe_result|te_space)"),
        # The race's own milestones and colonies. Deliberately not bare
        # "orbital"/"the moon": the space elevator, orbital battlestation and
        # solar collector are wonder buildings, not space-race state.
        _rx(r"\bspace (?:program(?:me)?s?|race|probes?|colon(?:y|ies)|agency)\b|\bastronauts?\b"
            r"|\bcosmonauts?\b|\b(?:moon|lunar|mars|martian) (?:landings?|bases?|colon(?:y|ies)|missions?)\b"
            r"|\boff-world colon(?:y|ies)\b|\binterstellar probes?\b|\b(?:first|artificial) satellites?\b"
            r"|\bmanned (?:space ?)?flights?\b", _I),
    ),
    System(
        "nuclear", "Nuclear weapons / deterrence",
        _rx(r"\bnuclear_weapons_(?:enabled|disabled)\b|\bje_nuclear_(?:program|deterrence)\b"
            r"|\bnuclear_\w+|\bnuke_\w+|\bnd_\w+|\bnuclear_power\b"),
        _rx(r"^(?:nuclear_|nuke_|te_debug_nuclear|te_debug_deterrence)"),
        _rx(r"\bnuclear (?:weapons?|arsenals?|warheads?|tests?|standoff|war|deterrent|deterrence"
            r"|brinkmanship|crisis|strikes?|annihilation|attack)\b|\batomic (?:bombs?|weapons?)\b"
            r"|\bmissile crisis\b|\bICBMs?\b", _I),
    ),
    System(
        "global_warming", "Global warming",
        _rx(r"\bglobal_warming_(?:enabled|disabled)\b|\bje_global_warming\b|\bglobal_warming_\w+"
            r"|\bgw_\w+"),
        _rx(r"^(?:global_warming|gw_|te_debug_gw)"),
        _rx(r"\bclimate (?:change|crisis|catastrophe)\b|\bglobal warming\b|\brising seas?\b"
            r"|\bsea levels? (?:rise|rising)\b|\bcarbon emissions?\b", _I),
    ),
    System(
        "un", "United Nations",
        _rx(r"\bunited_nations_(?:enabled|disabled)\b|\bje_united_nations\b|\bun_\w+|\bte_un_\w+"),
        _rx(r"^(?:un_|te_debug_un)"),
        _rx(r"\bUnited Nations\b|\bSecurity Council\b|\bGeneral Assembly\b"
            r"|\bUN (?:resolutions?|votes?|charter|missions?|peacekeep\w*|sanctions)\b"),
    ),
    System(
        "cultural_hegemony", "Cultural hegemony",
        _rx(r"\bcultural_hegemony_(?:enabled|disabled)\b|\bje_cultural_hegemony\b"
            r"|\bcultural_hegemony_\w+|\bch_\w+"),
        _rx(r"^(?:cultural_hegemony|te_debug_ch)"),
        _rx(r"\bcultural hegemony\b|\bsoft power\b|\bcultural imperialism\b", _I),
    ),
    System(
        "world_war", "World war",
        _rx(r"\bworld_war_(?:enabled|disabled)\b|\bje_world_war\b|\bworld_war_\w+|\bww_\w+"),
        _rx(r"^world_war"),
        _rx(r"\bworld war\b|\bglobal war\b", _I),
    ),
    System(
        "decolonization", "Decolonization",
        _rx(r"\bdecolonization_(?:enabled|disabled)\b|\bje_colonial_empire\b|\bcolonial_\w+"
            r"|\bdecolonization_\w+"),
        _rx(r"^(?:decolonization|colonial_|te_debug_colonial)"),
        _rx(r"\bdecoloni[sz]ation\b|\bindependence movements?\b|\bcolonial (?:administration|uprising)\b", _I),
    ),
    System(
        "heir_education", "Heir education",
        _rx(r"\bheir_education_(?:enabled|disabled)\b|\bje_heir_education\b|\bheir_\w+"),
        _rx(r"^heir_"),
        _rx(r"\bheir'?s? (?:education|tutors?|schooling)\b", _I),
    ),
)

SYSTEM_BY_KEY = {s.key: s for s in SYSTEMS}

# ---------------------------------------------------------------------------
# Agency lexicons
# ---------------------------------------------------------------------------

# First-person claims that the recipient government *did* something. Kept
# deliberately narrow (deliberate state actions), so pops acting, disasters and
# "our economy" never match.
_SELF_ACTION_RE = re.compile(
    r"\bour (?:own )?(?:information campaign|propaganda campaign|disinformation campaign"
    r"|campaign of|military (?:expansion|buildup|build-up)|arms (?:buildup|build-up)"
    r"|intelligence operatives?|operatives?|agents?|spies|spy|covert (?:operations?|funding)"
    r"|veto|ultimatum|embargo|sanctions|blockade|invasion|intervention|strike on"
    r"|nuclear tests?|weapons tests?|crackdown|purge|annexation|bailout"
    r"|decision to|order to|refusal to)\b"
    r"|\bwe (?:have |had )?(?:launched|ordered|vetoed|imposed|declared|deployed|authori[sz]ed"
    r"|detonated|tested|annexed|seized|expelled|blockaded|invaded|sanctioned|embargoed"
    r"|funded|financed|bailed out|nationali[sz]ed|devalued|sabotaged|infiltrated|bombed)\b",
    re.IGNORECASE,
)

# `[SCOPE.sCountry('x')…]` — a saved country scope named in loc.
_SCOPE_REF_RE = re.compile(r"\[SCOPE\.s(?:Country|Character)\('(?P<name>\w+)'\)[^\]]*\]")
# A present-perfect / past-perfect finite verb: "has launched", "has been
# apprehended", "have begun". Used within one sentence after an X reference.
_PERFECT_RE = re.compile(
    r"\b(?:has|have|had)\s+(?:been\s+|quietly\s+|now\s+|already\s+|secretly\s+|covertly\s+)?"
    r"(?:\w+ed|begun|sent|made|taken|built|won|struck|thrown|drawn|set|held|led|brought|put"
    r"|given|broken|stolen|spread|shown|begun)\b",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Tokenizer / block walker
# ---------------------------------------------------------------------------

_TOKEN_RE = re.compile(r'"[^"\n]*"|[{}]|\?=|[<>!]=|[=<>]|[^\s{}=<>!?"]+')
_EVENT_ID_RE = re.compile(r"^[a-z_][a-z0-9_]*\.\d+$")
_DEF_RE = re.compile(r"^[ \t]*([a-z_][a-z0-9_]*\.\d+)[ \t]*=[ \t]*\{", re.M)
_TAGGED_REVIEWED_RE = re.compile(
    r"#\s*REVIEWED\s+(?P<date>\d{4}-\d{2}-\d{2})\s*\((?P<checks>[\w ,]+)\)\s*:\s*(?P<rationale>.+?)\s*$",
    re.M,
)

# Block keys that do not change the scope a trigger_event fires in.
_CONTROL_KEYS = {
    "if", "else_if", "else", "limit", "random_list", "random", "option", "immediate", "after",
    "hidden_effect", "while", "custom_tooltip", "custom_description", "trigger", "effect",
    "AND", "OR", "NOT", "NOR", "NAND", "on_actions", "events", "random_events",
    "first_valid", "trigger_event", "show_as_tooltip", "switch", "modifier", "ai_chance",
    "possible", "is_shown", "potential", "on_enact", "immediate_effect", "on_complete",
    "on_fail", "on_timeout", "on_invalid", "on_monthly_pulse", "on_weekly_pulse",
    "on_yearly_pulse", "when_taken", "on_created", "on_entry_into_force", "on_withdrawal",
    "on_break", "on_accept", "on_decline", "accept_effect", "decline_effect", "on_start",
    "on_end", "effect_starting", "effect_on_success", "effect_on_failure", "on_success",
    "on_failure", "complete_effect", "fail_effect", "timeout_effect", "invalid_effect",
    "abandon_effect", "on_weekly_pulse_effect", "manual_break_effect", "on_activate",
    "on_deactivate", "on_ratify", "on_accepted", "on_declined", "on_trigger",
    "on_escalation", "on_war_begins", "on_pay", "on_expire",
}
# Keys whose child `trigger` / `limit` blocks guard the calls that follow.
_COND_KEYS = {"limit", "trigger", "possible", "is_shown", "potential", "is_valid",
              "can_be_enacted", "visible"}
_NUMERIC_RE = re.compile(r"^-?\d+(?:\.\d+)?$")
_PARAM_RE = re.compile(r"^\$\w+\$$")


def _strip_comments(text: str) -> str:
    out = []
    for line in text.split("\n"):
        if "#" in line:
            in_q = False
            for i, c in enumerate(line):
                if c == '"':
                    in_q = not in_q
                elif c == "#" and not in_q:
                    line = line[:i]
                    break
        out.append(line)
    return "\n".join(out)


def _tokens(text: str):
    """Yield (token, line_no) for comment-stripped text."""
    for ln, line in enumerate(_strip_comments(text).split("\n"), 1):
        for m in _TOKEN_RE.finditer(line):
            yield m.group(0), ln


@dataclass
class Site:
    """One place an event is dispatched from."""
    event: str
    file: str            # mod-relative
    line: int
    entity: str          # top-level entity the call sits in
    entity_kind: str     # event | on_action | scripted_effect | journal_entry | decision | ...
    path: list[str]      # block keys from the entity (exclusive) to the call
    switches: list[str]  # scope-changing keys among `path`
    conds: str           # guard text: every enclosing limit / trigger
    via: str = "trigger_event"  # trigger_event | events | random_events | first_valid

    @property
    def in_option(self) -> bool:
        return "option" in self.path

    @property
    def in_immediate(self) -> bool:
        return "immediate" in self.path or "after" in self.path


@dataclass
class _Frame:
    key: str
    line: int
    conds: list[str] = field(default_factory=list)
    chain_conds: list[str] = field(default_factory=list)  # if/else_if siblings
    toks: list[str] | None = None  # collected tokens while inside a cond block


def _is_switch(key: str) -> bool:
    if key in _CONTROL_KEYS or key == "<anon>":
        return False
    if _NUMERIC_RE.match(key) or _PARAM_RE.match(key) or _EVENT_ID_RE.match(key):
        return False
    return True


def _entity_kind(rel: str) -> str:
    parts = rel.replace("\\", "/").split("/")
    if parts[0] == "events":
        return "event"
    if len(parts) > 1 and parts[0] == "common":
        return {
            "on_actions": "on_action",
            "scripted_effects": "scripted_effect",
            "journal_entries": "journal_entry",
            "decisions": "decision",
            "scripted_buttons": "button",
            "scripted_guis": "button",
            "diplomatic_actions": "diplomatic_action",
            "treaty_articles": "treaty",
            "laws": "law",
            "character_interactions": "character_interaction",
            "diplomatic_plays": "diplomatic_play",
            "decrees": "decree",
            "power_bloc_principles": "principle",
            "amendments": "law",
        }.get(parts[1], parts[1])
    return parts[0]


@dataclass
class FileScan:
    sites: list[Site]
    effect_calls: dict[str, list[tuple[str, int, list[str], list[str], str]]]
    on_action_refs: dict[str, list[tuple[str, int, str]]]  # child -> (parent, line, file)


def scan_file(path: str, rel: str, effect_names: set[str]) -> FileScan:
    """Walk one script file, recording dispatch sites, scripted-effect calls and
    on-action chaining, each with its enclosing scope path and guard text."""
    try:
        with open(path, encoding="utf-8-sig", errors="replace") as fh:
            text = fh.read()
    except OSError:
        return FileScan([], {}, {})

    kind = _entity_kind(rel)
    toks = list(_tokens(text))
    stack: list[_Frame] = []
    sites: list[Site] = []
    effect_calls: dict[str, list] = defaultdict(list)
    on_action_refs: dict[str, list] = defaultdict(list)
    n = len(toks)
    i = 0
    pending_key: str | None = None

    def collecting() -> _Frame | None:
        for fr in reversed(stack):
            if fr.toks is not None:
                return fr
        return None

    def context():
        entity = stack[0].key if stack else "<file>"
        path_keys = [fr.key for fr in stack[1:]]
        conds = []
        for fr in stack:
            conds.extend(fr.conds)
        return entity, path_keys, [k for k in path_keys if _is_switch(k)], " ".join(conds)

    while i < n:
        t, ln = toks[i]
        col = collecting()
        if col is not None and t not in ("{", "}"):
            col.toks.append(t)
        if t == "{":
            key = pending_key or "<anon>"
            fr = _Frame(key, ln)
            if key in _COND_KEYS and stack:
                fr.toks = []
            if key in ("else", "else_if") and stack:
                fr.conds.extend(stack[-1].chain_conds)
            stack.append(fr)
            pending_key = None
            i += 1
            continue
        if t == "}":
            if stack:
                fr = stack.pop()
                if fr.toks is not None and stack:
                    joined = " ".join(fr.toks)
                    stack[-1].conds.append(joined)
                    outer = collecting()
                    if outer is not None:
                        outer.toks.append("{ " + joined + " }")
                if fr.key in ("if", "else_if") and stack:
                    stack[-1].chain_conds = fr.conds[:]
                elif fr.key == "else" and stack:
                    stack[-1].chain_conds = []
            pending_key = None
            i += 1
            continue

        nxt = toks[i + 1][0] if i + 1 < n else None
        if nxt in ("=", "?="):
            if t == "trigger_event":
                j = i + 2
                if j < n and toks[j][0] != "{":
                    entity, pk, sw, conds = context()
                    sites.append(Site(toks[j][0], rel, ln, entity, kind, pk, sw, conds))
                else:
                    depth = 0
                    k = j
                    while k < n:
                        tk = toks[k][0]
                        if tk == "{":
                            depth += 1
                        elif tk == "}":
                            depth -= 1
                            if depth == 0:
                                break
                        elif tk == "id" and k + 2 < n and toks[k + 1][0] == "=" and depth == 1:
                            entity, pk, sw, conds = context()
                            sites.append(Site(toks[k + 2][0], rel, ln, entity, kind, pk, sw, conds))
                        k += 1
            elif t in effect_names and stack:
                entity, pk, sw, conds = context()
                # `helper = { WHO = scope:x EVENT = ns.7 }` — keep simple
                # depth-1 arguments for `$PARAM$` substitution.
                params: dict[str, str] = {}
                j = i + 2
                if j < n and toks[j][0] == "{":
                    depth = 0
                    k = j
                    while k < n:
                        tk = toks[k][0]
                        if tk == "{":
                            depth += 1
                        elif tk == "}":
                            depth -= 1
                            if depth == 0:
                                break
                        elif (depth == 1 and k + 2 < n and toks[k + 1][0] == "="
                              and toks[k + 2][0] != "{"):
                            params[tk] = toks[k + 2][0]
                        k += 1
                effect_calls[t].append((rel, ln, pk, sw, conds, entity, kind, params))
            pending_key = t
            i += 2
            continue

        # bare token: an event id in an on-action list, or an on-action name in
        # an `on_actions = { }` list
        if stack:
            parent = stack[-1].key
            if parent in ("events", "random_events", "first_valid") and _EVENT_ID_RE.match(t):
                entity, pk, sw, conds = context()
                sites.append(Site(t, rel, ln, entity, kind, pk, sw, conds, via=parent))
            elif parent == "on_actions" and kind == "on_action" and not _NUMERIC_RE.match(t):
                on_action_refs[t].append((stack[0].key, ln, rel))
        pending_key = None
        i += 1

    return FileScan(sites, dict(effect_calls), dict(on_action_refs))


# ---------------------------------------------------------------------------
# Event definitions + localization
# ---------------------------------------------------------------------------


def _match_block(text: str, brace_pos: int) -> int:
    depth = 0
    i = brace_pos
    n = len(text)
    while i < n:
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i + 1
        elif c == "#":
            nl = text.find("\n", i)
            i = n if nl == -1 else nl
            continue
        i += 1
    return n


_LOC_FIELD_RE = re.compile(r"(?<![\w.])(title|desc|flavor)\s*=\s*\"?([A-Za-z0-9_.]+)\"?")
_HIDDEN_RE = re.compile(r"^[ \t]*hidden[ \t]*=[ \t]*yes\b", re.M)


@dataclass
class EventDef:
    event_id: str
    file: str   # mod-relative
    line: int
    block: str  # raw text (comments kept)
    hidden: bool
    title_keys: list[str]
    desc_keys: list[str]
    flavor_keys: list[str]
    reviewed: dict[str, dict]  # check -> {date, rationale}

    @property
    def code(self) -> str:
        return _strip_comments(self.block)


def _sub_block(code: str, key: str) -> list[str]:
    """Every `key = { … }` sub-block of `code` (comment-free text)."""
    out = []
    for m in re.finditer(r"(?<![\w.:])" + re.escape(key) + r"\s*=\s*\{", code):
        b = code.index("{", m.start())
        out.append(code[b:_match_block(code, b)])
    return out


def load_events(mod_path: str) -> dict[str, EventDef]:
    events: dict[str, EventDef] = {}
    events_dir = os.path.join(mod_path, "events")
    if not os.path.isdir(events_dir):
        return events
    for dirpath, _d, files in os.walk(events_dir):
        for f in sorted(files):
            if not f.endswith(".txt"):
                continue
            path = os.path.join(dirpath, f)
            rel = os.path.relpath(path, mod_path).replace("\\", "/")
            with open(path, encoding="utf-8-sig", errors="replace") as fh:
                text = fh.read()
            for m in _DEF_RE.finditer(text):
                eid = m.group(1)
                b = text.index("{", m.start())
                block = text[b:_match_block(text, b)]
                code = _strip_comments(block)
                title, desc, flavor = [], [], []
                for fm in _LOC_FIELD_RE.finditer(code):
                    {"title": title, "desc": desc, "flavor": flavor}[fm.group(1)].append(fm.group(2))
                reviewed: dict[str, dict] = {}
                for rm in _TAGGED_REVIEWED_RE.finditer(block):
                    for chk in re.split(r"[\s,]+", rm.group("checks").strip()):
                        if chk:
                            reviewed[chk] = {"date": rm.group("date"),
                                             "rationale": rm.group("rationale").strip()}
                events[eid] = EventDef(
                    eid, rel, text.count("\n", 0, m.start()) + 1, block,
                    bool(_HIDDEN_RE.search(code)), title, desc, flavor, reviewed,
                )
    return events


_LOC_LINE_RE = re.compile(r'^\s*([A-Za-z0-9_.\-]+):\d*\s*"(.*)"\s*(?:#.*)?$')


def load_loc(mod_path: str) -> dict[str, str]:
    loc: dict[str, str] = {}
    loc_dir = os.path.join(mod_path, "localization", "english")
    if not os.path.isdir(loc_dir):
        return loc
    for dirpath, _d, files in os.walk(loc_dir):
        for f in sorted(files):
            if not f.endswith(".yml"):
                continue
            with open(os.path.join(dirpath, f), encoding="utf-8-sig", errors="replace") as fh:
                for line in fh:
                    m = _LOC_LINE_RE.match(line)
                    if m:
                        loc[m.group(1)] = m.group(2)
    return loc


def _expand_loc(text: str, loc: dict[str, str], depth: int = 0) -> str:
    if depth > 3:
        return text
    return re.sub(r"\$(\w[\w.]*)\$",
                  lambda m: _expand_loc(loc.get(m.group(1), m.group(0)), loc, depth + 1), text)


# ---------------------------------------------------------------------------
# Graph resolution
# ---------------------------------------------------------------------------

_PULSE_RE = re.compile(r"pulse")
_CHOSEN_HOOK_RE = re.compile(r"^on_law_|^on_amendment_|^on_decree_|^on_company_established"
                             r"|^on_building_built$|^on_character_recruitment$")


@dataclass
class Graph:
    events: dict[str, EventDef]
    sites_by_event: dict[str, list[Site]]
    effect_calls: dict[str, list[tuple]]
    effect_file: dict[str, str]
    on_action_parents: dict[str, list[tuple[str, int, str]]]
    on_action_files: dict[str, list[str]]
    loc: dict[str, str]


def _collect_defs(mod_path: str, sub: str) -> dict[str, str]:
    """Top-level `name = {` definitions in common/<sub> -> mod-relative file."""
    out: dict[str, str] = {}
    base = os.path.join(mod_path, "common", sub)
    if not os.path.isdir(base):
        return out
    def_re = re.compile(r"^(?:REPLACE:|INJECT:|REPLACE_OR_CREATE:)?([A-Za-z_][\w]*)\s*=\s*\{", re.M)
    for dirpath, _d, files in os.walk(base):
        for f in sorted(files):
            if f.endswith(".txt"):
                p = os.path.join(dirpath, f)
                with open(p, encoding="utf-8-sig", errors="replace") as fh:
                    for m in def_re.finditer(fh.read()):
                        out.setdefault(m.group(1), os.path.relpath(p, mod_path).replace("\\", "/"))
    return out


def _collect_def_files(mod_path: str, sub: str) -> dict[str, list[str]]:
    """Like `_collect_defs`, but every file defining each name (engine hooks
    such as `on_monthly_pulse_country` are declared in many files and merged)."""
    out: dict[str, list[str]] = defaultdict(list)
    base = os.path.join(mod_path, "common", sub)
    if not os.path.isdir(base):
        return {}
    def_re = re.compile(r"^(?:REPLACE:|INJECT:|REPLACE_OR_CREATE:)?([A-Za-z_][\w]*)\s*=\s*\{", re.M)
    for dirpath, _d, files in os.walk(base):
        for f in sorted(files):
            if f.endswith(".txt"):
                p = os.path.join(dirpath, f)
                rel = os.path.relpath(p, mod_path).replace("\\", "/")
                with open(p, encoding="utf-8-sig", errors="replace") as fh:
                    for m in def_re.finditer(fh.read()):
                        if rel not in out[m.group(1)]:
                            out[m.group(1)].append(rel)
    return dict(out)


def build_graph(mod_path: str) -> Graph:
    events = load_events(mod_path)
    effect_file = _collect_defs(mod_path, "scripted_effects")
    on_action_files = _collect_def_files(mod_path, "on_actions")
    effect_names = set(effect_file)
    sites_by_event: dict[str, list[Site]] = defaultdict(list)
    effect_calls: dict[str, list] = defaultdict(list)
    on_action_parents: dict[str, list] = defaultdict(list)
    for root in ("events", "common"):
        base = os.path.join(mod_path, root)
        if not os.path.isdir(base):
            continue
        for dirpath, _d, files in os.walk(base):
            for f in sorted(files):
                if not f.endswith(".txt"):
                    continue
                p = os.path.join(dirpath, f)
                rel = os.path.relpath(p, mod_path).replace("\\", "/")
                fs = scan_file(p, rel, effect_names)
                for s in fs.sites:
                    sites_by_event[s.event].append(s)
                for name, calls in fs.effect_calls.items():
                    effect_calls[name].extend(calls)
                for child, parents in fs.on_action_refs.items():
                    on_action_parents[child].extend(parents)
    _substitute_params(sites_by_event, effect_calls)
    return Graph(events, dict(sites_by_event), dict(effect_calls), effect_file,
                 dict(on_action_parents), on_action_files, load_loc(mod_path))


def _substitute_params(sites_by_event: dict[str, list[Site]], effect_calls: dict[str, list]) -> None:
    """Resolve `trigger_event = { id = $EVENT$ }` inside a scripted effect into one
    concrete site per caller that passes `EVENT = <id>`, carrying the caller's
    path, guards and scope switches plus the helper's own (`$WHO$ = { … }`
    becomes the caller's `WHO` value)."""
    for _round in range(4):  # helpers that forward $EVENT$ to other helpers
        pending = [(k, s) for k, lst in sites_by_event.items() if _PARAM_RE.match(k) for s in lst]
        if not pending:
            return
        for k, _lst in list(sites_by_event.items()):
            if _PARAM_RE.match(k):
                del sites_by_event[k]
        added = False
        for key, s in pending:
            pname = key.strip("$")
            if s.entity_kind != "scripted_effect":
                continue
            for (rel, ln, pk, sw, conds, entity, kind, params) in effect_calls.get(s.entity, []):
                if pname not in params:
                    continue

                def sub(x: str, params=params) -> str:
                    return re.sub(r"\$(\w+)\$", lambda m: params.get(m.group(1), m.group(0)), x)

                inner = [sub(p) for p in s.path]
                sites_by_event[params[pname]].append(Site(
                    params[pname], rel, ln, entity, kind, pk + inner,
                    sw + [p for p in inner if _is_switch(p)], conds + " " + sub(s.conds), s.via))
                added = True
        if not added:
            return


# Chooser status of a dispatch source, resolved through immediates, effects and
# on-action chains.
CHOSEN, UNCHOSEN = "chosen", "unchosen"


def _basename(rel: str) -> str:
    return os.path.basename(rel)


class Resolver:
    def __init__(self, g: Graph):
        self.g = g
        self._event_choice: dict[str, tuple[str, str]] = {}
        self._effect_choice: dict[str, tuple[str, str]] = {}
        self._oa_choice: dict[str, tuple[str, str]] = {}
        self._gate_cache: dict[tuple[str, str, str], bool] = {}

    # -- chooser -----------------------------------------------------------
    def site_choice(self, s: Site, seen: frozenset = frozenset()) -> tuple[str, str]:
        """(status, reason) for whether the country receiving the event chose it."""
        if s.switches:
            return UNCHOSEN, f"fired into another scope ({' > '.join(s.switches)}) from {s.entity}"
        k = s.entity_kind
        if k == "event":
            if s.in_option:
                return CHOSEN, f"own option in {s.entity}"
            return self.event_choice(s.entity, seen)
        if k in ("decision", "button", "diplomatic_action", "law", "treaty", "decree",
                 "character_interaction", "principle"):
            return CHOSEN, f"{k} {s.entity}"
        if k == "scripted_effect":
            return self.effect_choice(s.entity, seen)
        if k == "on_action":
            return self.on_action_choice(s.entity, seen)
        if k == "journal_entry":
            return UNCHOSEN, f"journal entry tick ({s.entity})"
        return UNCHOSEN, f"{k} {s.entity}"

    def _combine(self, results: list[tuple[str, str]], none_reason: str) -> tuple[str, str]:
        if not results:
            return UNCHOSEN, none_reason
        for r in results:
            if r[0] == UNCHOSEN:
                return r
        return results[0]

    def event_choice(self, eid: str, seen: frozenset = frozenset()) -> tuple[str, str]:
        if eid in self._event_choice:
            return self._event_choice[eid]
        if ("e", eid) in seen:
            return CHOSEN, "cycle"
        seen = seen | {("e", eid)}
        res = self._combine([self.site_choice(s, seen) for s in self.g.sites_by_event.get(eid, [])],
                            f"{eid} has no mod dispatch site (pulse-fired or vanilla hook)")
        self._event_choice[eid] = res
        return res

    def effect_choice(self, name: str, seen: frozenset = frozenset()) -> tuple[str, str]:
        if name in self._effect_choice:
            return self._effect_choice[name]
        if ("f", name) in seen:
            return CHOSEN, "cycle"
        seen = seen | {("f", name)}
        results = []
        for (rel, ln, pk, sw, conds, entity, kind, _params) in self.g.effect_calls.get(name, []):
            s = Site("", rel, ln, entity, kind, pk, sw, conds)
            results.append(self.site_choice(s, seen))
        res = self._combine(results, f"effect {name} has no callers")
        self._effect_choice[name] = res
        return res

    def on_action_choice(self, name: str, seen: frozenset = frozenset()) -> tuple[str, str]:
        if name in self._oa_choice:
            return self._oa_choice[name]
        if ("o", name) in seen:
            return CHOSEN, "cycle"
        seen = seen | {("o", name)}
        parents = self.g.on_action_parents.get(name, [])
        if not parents:
            if _CHOSEN_HOOK_RE.search(name):
                res = (CHOSEN, f"engine hook {name}")
            elif _PULSE_RE.search(name):
                res = (UNCHOSEN, f"pulse {name}")
            else:
                res = (UNCHOSEN, f"engine hook {name}")
        else:
            res = self._combine([self.on_action_choice(p, seen) for p, _ln, _f in parents], name)
            if res[0] == UNCHOSEN and "pulse" in res[1] and name not in res[1]:
                res = (UNCHOSEN, f"{res[1]} > {name}")
        self._oa_choice[name] = res
        return res

    # -- system gating -------------------------------------------------------
    def owns(self, sysm: System, rel: str) -> bool:
        return bool(sysm.file_re.search(_basename(rel)))

    def site_gated(self, s: Site, sysm: System, seen: frozenset) -> bool:
        if sysm.state_re.search(s.conds):
            return True
        if self.owns(sysm, s.file):
            return True
        k = s.entity_kind
        if k == "event":
            return self.event_gated(s.entity, sysm, seen)
        if k == "scripted_effect":
            return self.effect_gated(s.entity, sysm, seen)
        if k == "on_action":
            return self.on_action_gated(s.entity, sysm, seen)
        if k == "journal_entry":
            return bool(sysm.state_re.search(s.entity))
        return False

    def event_gated(self, eid: str, sysm: System, seen: frozenset = frozenset()) -> bool:
        key = ("e", eid, sysm.key)
        if key in self._gate_cache:
            return self._gate_cache[key]
        if key in seen:
            return False
        seen = seen | {key}
        ev = self.g.events.get(eid)
        if ev is not None and (sysm.state_re.search(ev.code) or self.owns(sysm, ev.file)):
            res = True
        else:
            sites = self.g.sites_by_event.get(eid, [])
            res = bool(sites) and all(self.site_gated(s, sysm, seen) for s in sites)
        self._gate_cache[key] = res
        return res

    def effect_gated(self, name: str, sysm: System, seen: frozenset) -> bool:
        key = ("f", name, sysm.key)
        if key in self._gate_cache:
            return self._gate_cache[key]
        if key in seen:
            return False
        seen = seen | {key}
        if self.owns(sysm, self.g.effect_file.get(name, "")) or sysm.state_re.search(name):
            res = True
        else:
            calls = self.g.effect_calls.get(name, [])
            res = bool(calls) and all(
                self.site_gated(Site("", rel, ln, entity, kind, pk, sw, conds), sysm, seen)
                for (rel, ln, pk, sw, conds, entity, kind, _params) in calls)
        self._gate_cache[key] = res
        return res

    def on_action_gated(self, name: str, sysm: System, seen: frozenset) -> bool:
        key = ("o", name, sysm.key)
        if key in self._gate_cache:
            return self._gate_cache[key]
        if key in seen:
            return False
        seen = seen | {key}
        # Engine hooks (on_monthly_pulse_country, …) are merged from many files,
        # so a hook is owned only if every file defining it is; a chain link is
        # gated when the `on_actions = { name }` reference sits in an owned file
        # or its parent on-action is itself gated.
        files = self.g.on_action_files.get(name, [])
        if (files and all(self.owns(sysm, f) for f in files)) or sysm.state_re.search(name):
            res = True
        else:
            parents = self.g.on_action_parents.get(name, [])
            res = bool(parents) and all(
                self.owns(sysm, f) or self.on_action_gated(p, sysm, seen)
                for p, _ln, f in parents)
        self._gate_cache[key] = res
        return res


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------


@dataclass
class Flag:
    check: str
    event_id: str
    file: str
    line: int
    detail: str
    evidence: str
    dispatch: list[str]
    exemption: dict | None = None


@dataclass
class AuditResult:
    flags: list[Flag] = field(default_factory=list)
    coverage: dict = field(default_factory=dict)


def _first_sentence(text: str, limit: int = 220) -> str:
    text = re.sub(r"\\n", " ", text)
    m = re.search(r"^(.+?[.!?])(\s|$)", text)
    s = m.group(1) if m else text
    return s if len(s) <= limit else s[:limit - 1] + "…"


def _dispatch_summary(g: Graph, r: Resolver, eid: str) -> list[str]:
    out = []
    for s in g.sites_by_event.get(eid, [])[:6]:
        status, reason = r.site_choice(s)
        out.append(f"{s.file}:{s.line} [{s.entity_kind} {s.entity}] {status}: {reason}")
    if not g.sites_by_event.get(eid):
        out.append("no mod dispatch site")
    extra = len(g.sites_by_event.get(eid, [])) - 6
    if extra > 0:
        out.append(f"… and {extra} more")
    return out


def _event_text(ev: EventDef, loc: dict[str, str], fields=("title", "desc", "flavor")) -> str:
    keys = []
    if "title" in fields:
        keys += ev.title_keys
    if "desc" in fields:
        keys += ev.desc_keys
    if "flavor" in fields:
        keys += ev.flavor_keys
    return " \n ".join(_expand_loc(loc.get(k, ""), loc) for k in keys)


_CONSOLE_FILE_RE = re.compile(r"^te_debug_")
_COUNTRY_PICKER_RE = re.compile(r"^(?:random|ordered)_\w*countr(?:y|ies)$")


def _picked_scopes(ev: EventDef) -> set[str]:
    """Scopes the event saves from a country it picks itself in `immediate`."""
    picked: set[str] = set()
    for imm in _sub_block(ev.code, "immediate"):
        stack: list[str] = []
        pending = None
        toks = list(_tokens(imm))
        for idx, (t, _ln) in enumerate(toks):
            if t == "{":
                stack.append(pending or "<anon>")
                pending = None
            elif t == "}":
                if stack:
                    stack.pop()
            elif idx + 1 < len(toks) and toks[idx + 1][0] == "=":
                if t == "save_scope_as" and idx + 2 < len(toks):
                    if any(_COUNTRY_PICKER_RE.match(k) for k in stack):
                        picked.add(toks[idx + 2][0])
                pending = t
    return picked


def _consequences_on(ev: EventDef, scope: str) -> list[str]:
    """What the event's options do to a saved scope."""
    found = []
    for opt in _sub_block(ev.code, "option"):
        for blk in _sub_block(opt, f"scope:{scope}"):
            for what in ("trigger_event", "add_modifier", "change_relations", "add_radicals",
                         "change_infamy", "add_treasury", "set_variable"):
                if re.search(r"\b" + what + r"\b", blk) and what not in found:
                    found.append(what)
        if re.search(r"country\s*=\s*scope:" + re.escape(scope) + r"\b", opt) and \
                "change_relations" not in found:
            found.append("change_relations")
    return found


def audit(mod_path: str, graph: Graph | None = None) -> AuditResult:
    g = graph or build_graph(mod_path)
    r = Resolver(g)
    flags: list[Flag] = []
    visible = 0

    for eid, ev in sorted(g.events.items(), key=lambda kv: (kv[1].file, kv[1].line)):
        if ev.hidden:
            continue
        visible += 1
        if _CONSOLE_FILE_RE.search(os.path.basename(ev.file)):
            continue  # console-only test harnesses: fired by hand, never in play
        # Title + description carry the event's premise; flavor is quoted
        # colour whose passing mentions ("…like nuclear weapons…") are noise.
        head_text = _event_text(ev, g.loc, ("title", "desc"))

        # 1. system_ungated
        for sysm in SYSTEMS:
            m = sysm.vocab_re.search(head_text)
            if not m:
                continue
            if r.event_gated(eid, sysm):
                continue
            ctx = head_text[max(0, m.start() - 60):m.end() + 60].replace("\n", " ").strip()
            flags.append(Flag(
                "system_ungated", eid, ev.file, ev.line,
                f"mentions {sysm.name} (`{m.group(0)}`) but reads none of its state, "
                f"and not every dispatch site is gated on it",
                f"…{ctx}…", _dispatch_summary(g, r, eid)))

        # 2. unchosen_self_action
        m = _SELF_ACTION_RE.search(head_text)
        if m:
            status, reason = r.event_choice(eid)
            if status == UNCHOSEN:
                ctx = head_text[max(0, m.start() - 80):m.end() + 60].replace("\n", " ").strip()
                flags.append(Flag(
                    "unchosen_self_action", eid, ev.file, ev.line,
                    f"text claims the recipient's own action (`{m.group(0)}`) but it can "
                    f"arrive unchosen: {reason}",
                    f"…{ctx}…", _dispatch_summary(g, r, eid)))

        # 3. imputed_foreign_action
        desc_text = _event_text(ev, g.loc, ("title", "desc"))
        for scope in sorted(_picked_scopes(ev)):
            hits = _consequences_on(ev, scope)
            if not hits:
                continue
            attributed = None
            for sm in _SCOPE_REF_RE.finditer(desc_text):
                if sm.group("name") != scope:
                    continue
                tail = desc_text[sm.end():]
                sentence = re.split(r"[.!?]", tail, maxsplit=1)[0]
                pm = _PERFECT_RE.search(sentence)
                if pm:
                    attributed = (desc_text[sm.start():sm.end() + pm.end()]).strip()
                    break
            if not attributed:
                continue
            flags.append(Flag(
                "imputed_foreign_action", eid, ev.file, ev.line,
                f"picks `scope:{scope}` itself, says it acted, and applies "
                f"{', '.join(hits)} to it",
                attributed, _dispatch_summary(g, r, eid)))

    for f in flags:
        ev = g.events[f.event_id]
        f.exemption = ev.reviewed.get(f.check) or ev.reviewed.get("all")

    flags.sort(key=lambda f: (CHECKS.index(f.check), f.file, f.line))
    return AuditResult(flags, {
        "events_defined": len(g.events),
        "visible": visible,
        "dispatch_sites": sum(len(v) for v in g.sites_by_event.values()),
        **{c: sum(1 for f in flags if f.check == c) for c in CHECKS},
    })


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

_CHECK_HELP = {
    "system_ungated": (
        "The event's text is about a mod system, but the event reads none of the "
        "system's state (game rule, journal entry, owned triggers/variables) and at "
        "least one dispatch site is not gated on it either. Gate it on the system "
        "(or make it the system-disabled fallback, as PR #418 did for "
        "`international_relations_events.6`/`.7`), or tie its outcome to the "
        "system's real state."
    ),
    "unchosen_self_action": (
        "The title/description claims the recipient government did something, but "
        "the event can reach it without that country having chosen anything (a "
        "pulse, a journal-entry tick, or another country's option). Give the "
        "recipient the choice, gate the event on the action having happened, or "
        "reword it so it no longer claims an action the country never took."
    ),
    "imputed_foreign_action": (
        "The event picks another country itself, says that country acted, and "
        "applies consequences to it. If that country is a player, it is punished "
        "for something it never chose. Tie the premise to real state (e.g. an "
        "active covert operation), let that country choose first, or drop the "
        "consequence on it."
    ),
}


def render_report(result: AuditResult, mod_path: str = "") -> str:
    cov = result.coverage
    out = ["# Event Context Report", ""]
    out.append(
        "Events whose text does not match the context they fire in: events about a mod "
        "system that ignore it, and events that claim a country acted when it never "
        "chose to. Heuristic ranking for a human read — see `event_context_audit.py` "
        "for the rules. Suppress a reviewed flag with a check-tagged comment on its own "
        "line inside the event block: `# REVIEWED YYYY-MM-DD (<check>): rationale`."
    )
    out.append("")
    out.append(f"- Events defined: **{cov.get('events_defined', 0)}**, visible: "
               f"**{cov.get('visible', 0)}**, dispatch sites traced: "
               f"**{cov.get('dispatch_sites', 0)}**")
    for c in CHECKS:
        un = sum(1 for f in result.flags if f.check == c and not f.exemption)
        ex = sum(1 for f in result.flags if f.check == c and f.exemption)
        out.append(f"- `{c}`: **{un}** unreviewed, {ex} REVIEWED")
    out.append("")

    for c in CHECKS:
        fl = [f for f in result.flags if f.check == c]
        out.append(f"## `{c}`")
        out.append("")
        out.append(_CHECK_HELP[c])
        out.append("")
        un = [f for f in fl if not f.exemption]
        ex = [f for f in fl if f.exemption]
        if not un:
            out.append("No unreviewed flags. ✅")
            out.append("")
        for f in un:
            out.append(f"### `{f.event_id}` — {f.file}:{f.line}")
            out.append("")
            out.append(f"- {f.detail}")
            out.append(f"- Text: {f.evidence}")
            out.append("- Dispatch:")
            for d in f.dispatch:
                out.append(f"  - {d}")
            out.append("")
        if ex:
            out.append("### REVIEWED")
            out.append("")
            for f in ex:
                e = f.exemption or {}
                out.append(f"- `{f.event_id}` — {f.file}:{f.line} (REVIEWED {e.get('date', '?')}: "
                           f"{e.get('rationale', '')})")
            out.append("")
    return "\n".join(out)


def regenerate(mod_state=None) -> dict:
    """POST_LOAD_GENERATORS entry point. Writes the event-context report.

    File-based (events, script and loc are read from disk), so `mod_state` is
    accepted for protocol compatibility but unused.
    """
    from path_constants import mod_path

    result = audit(mod_path)
    out_path = os.path.join(mod_path, "docs", "engine", "event_context_report.md")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(render_report(result, mod_path))
    return {
        "unreviewed": sum(1 for f in result.flags if not f.exemption),
        "exempted": sum(1 for f in result.flags if f.exemption),
        **{c: result.coverage.get(c, 0) for c in CHECKS},
        "path": out_path,
    }


if __name__ == "__main__":
    import sys

    from path_constants import mod_path as _mp

    res = audit(_mp)
    print(render_report(res, _mp))
    # --strict: CI mode. Exit 1 if any flag lacks a check-tagged REVIEWED comment.
    if "--strict" in sys.argv:
        raise SystemExit(1 if any(not f.exemption for f in res.flags) else 0)
