"""Static-analysis audit for localization accessor chains.

Vic3 silently drops `[X.Y.Z]` accessor chains it can't resolve, replacing
them with the empty string. The bug only surfaces by hovering the in-game
UI. This audit scans every `localization/english/*.yml` value, extracts
each `[…]` chain, and flags any chain whose first step or any intermediate
step is unresolvable in the relevant rendering context.

Strict mode by default. The catalog is bootstrapped from vanilla loc by
running the audit against it and folding every flag back into the
per-context magic-scope tables / accessor tables — the engine reads
vanilla's loc, so any vanilla flag is a catalog gap. An accessor that
returns a name or a number is typed `value`, and the check stops there:
every later step of the chain is accepted unread. So an accessor that
returns an object must carry the type it returns, or the audit is blind
for the rest of each chain through it (#348). `find_blind_pairs` lists
the `value`s some chain continues past; the report and `--blind` show
them for vanilla's loc (from the committed `vanilla_parsed/` snapshot)
and for the loc scanned.

Suppress an intentional flag with a same-line comment in the format:

    unusual_loc_key:0 "Some text [WeirdScope.GetX]"  # REVIEWED 2026-05-08: rationale

Standalone CLI (exits 1 on an unreviewed flag; CI runs it):

    python3 localization_accessor_audit.py [--loc-dir PATH] [--report | --blind]

Default `--loc-dir` is the mod's `localization/english/`. Aim it at the
vanilla install to see what vanilla flags (scripts/generators/
fold_vanilla_loc_accessors.py does this, subfolders included, and sorts
the gaps):

    python3 localization_accessor_audit.py --loc-dir \\
        "/mnt/c/Program Files (x86)/Steam/steamapps/common/Victoria 3/game/localization/english/"
"""
from __future__ import annotations

import argparse
import os
import re
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Regex primitives
# ---------------------------------------------------------------------------

# Same canonical REVIEWED regex used by event_magnitude_audit.py / modifier_visibility_audit.py.
_REVIEWED_RE = re.compile(
    r"#\s*REVIEWED\s+(?P<date>\d{4}-\d{2}-\d{2})\s*:\s*(?P<rationale>.+?)\s*$"
)

# Loc line: ` key:0 "value"`  or  ` key: "value"`. Comments after the value
# come after a `#` outside the quoted body. We don't try to parse YAML strictly;
# the format is fixed enough that a regex on raw lines is robust.
_LOC_LINE_RE = re.compile(
    r"""^\s*
        (?P<key>[\w.\-]+)        # the loc key
        \s*:                     # colon
        \s*\d*\s*                # optional version number
        (?P<value>.*?)           # everything else (value + possible trailing comment)
        \s*$
    """,
    re.VERBOSE,
)

# Match `[…]` non-greedily but allow nested parens inside (for function calls
# like `Concept('foo','$bar$')` and `sCountry('name')`). We stop at the next
# unescaped closing bracket. Brackets don't nest in vanilla loc strings.
_CHAIN_RE = re.compile(r"\[([^\[\]]*)\]")

# Function-call accessor step like `sCountry('name')`, `GetCulture('foo')`,
# `GetTruceDate(TARGET_COUNTRY.Self)`. We split args off when validating.
_FUNC_CALL_RE = re.compile(r"^([A-Za-z_]\w*)\s*\(.*\)$")


# ---------------------------------------------------------------------------
# Engine-grounded catalog
# ---------------------------------------------------------------------------

# Loc-rendering contexts. The classifier returns one of these. The
# magic-scope tables below are keyed by context. "permissive" is the fallback
# for unclassifiable keys — it permits the union of all magic scopes from
# all named contexts, so unclassified mod loc isn't blocked.
CONTEXTS = (
    "events",
    "diplomatic_actions",
    "war_goals",
    "treaty_articles",
    "journal_entries",
    "modifiers",
    "permissive",
)

# Magic scopes that may appear as the *first* step of a chain in each context.
# The value is the engine-resolved type the magic scope evaluates to, used to
# look up subsequent accessors in the catalog.
#
# This table grows during the vanilla knowledge-extraction phase. Initial
# entries are seeded from the explore-agent survey of vanilla loc samples.
_MAGIC_SCOPES_BY_CONTEXT: dict[str, dict[str, str]] = {
    "events": {
        "ROOT": "country",          # most events are country_event
        "SCOPE": "scope_object",    # generic scope-object dispatcher (.sCountry, .sState, etc.)
        "PREV": "country",
        "THIS": "country",
        "FROM": "country",
        "FROMFROM": "country",
        # Uppercase magic scopes used in vanilla event loc
        "COUNTRY": "country",
        "TARGET_COUNTRY": "country",
        "SOURCE_COUNTRY": "country",
        "INITIATOR_COUNTRY": "country",
        "STATE": "state",
        "STATE_REGION": "state_region",
        "STRATEGIC_REGION": "strategic_region",
        "CHARACTER": "character",
        "INTEREST_GROUP": "interest_group",
        "CULTURE": "culture",
        "TARGET_CULTURE": "culture",
        "RELIGION": "religion",
        "TARGET_RELIGION": "religion",
        "POP": "pop",
        "POP_TYPE": "value",
        "BUILDING": "building",
        "BUILDING_TYPE": "value",
        "MARKET": "market",
        "GOODS": "market_goods",
        "TARGET_GOODS": "market_goods",
        "STATE_GOODS": "market_goods",
        "MILITARY_FORMATION": "military_formation",
        "POLITICAL_MOVEMENT": "political_movement",
        "POLITICAL_LOBBY": "political_lobby",
        "DIPLOMATIC_ACTION_TYPE": "value",
        "TARGET_LAW_TYPE": "law",
        "LAW_TYPE": "law",
        "LAW_GROUP": "value",
        "POWER_BLOC": "power_bloc",
        "POWER_BLOC_PRINCIPLE": "value",
        "WAR": "war",
        "FRONT": "value",
        "BATTLE": "value",
        "INVASION": "value",
        "PARTY": "party",
        "COMPANY": "company",
        "JOURNAL_ENTRY": "journal_entry",
        "TREATY": "treaty",
        "TREATY_ARTICLE": "treaty_article",
        "DIPLOMATIC_PLAY": "diplomatic_play",
        "DIPLOMATIC_PACT": "diplomatic_pact",
        "MOBILIZATION_OPTION": "value",
        "INSTITUTION": "value",
        "INSTITUTION_TYPE": "value",
        "DECREE": "value",
        "TECHNOLOGY": "value",
        "ARTICLE_DRAFT": "value",
        "SHIP": "value",
        "LAW": "law",
        "COUNTRY_CREATION": "value",
        "MARKET_GOODS": "market_goods",
        "EMPLOYEE_TRANSFER": "value",
        "TARGET_BUILDING_TYPE": "value",
        "WAR_GOAL_TYPE": "value",
        "TARGET_LAW": "law",
        "ENACTING_LAW": "law",
    },
    "diplomatic_actions": {
        "COUNTRY": "country",
        "TARGET_COUNTRY": "country",
        "STATE": "state",
        "INITIATOR_COUNTRY": "country",
        "MARKET": "market",
        "GOODS": "market_goods",
        "STATE_GOODS": "market_goods",
        "BUILDING": "building",
        "CHARACTER": "character",
        "INTEREST_GROUP": "interest_group",
        "CULTURE": "culture",
        "SCOPE": "scope_object",
        "ROOT": "country",
        "DiplomaticAction": "diplomatic_action",
        "DiplomaticPlay": "diplomatic_play",
        "WAR_GOAL": "war_goal",
        "WAR_GOAL_DRAFT": "war_goal_draft",
    },
    # Notification / proposal-notification / break-notification *descs* of a
    # diplomatic action render in a context where the bare actor scope is NOT
    # bound — `[COUNTRY.…]` resolves to nullptr (every-frame log spam). The
    # actor is `[INITIATOR_COUNTRY.…]`, the target `[TARGET_COUNTRY.…]` (vanilla
    # convention). Same scope table as `diplomatic_actions` but with `COUNTRY`
    # removed, and `COUNTRY` / `GetDiplomaticPact` explicitly denied below.
    "diplomatic_action_notifications": {
        "TARGET_COUNTRY": "country",
        "STATE": "state",
        "INITIATOR_COUNTRY": "country",
        "MARKET": "market",
        "GOODS": "market_goods",
        "STATE_GOODS": "market_goods",
        "BUILDING": "building",
        "CHARACTER": "character",
        "INTEREST_GROUP": "interest_group",
        "CULTURE": "culture",
        "SCOPE": "scope_object",
        "ROOT": "country",
        "DiplomaticAction": "diplomatic_action",
        "DiplomaticPlay": "diplomatic_play",
        "WAR_GOAL": "war_goal",
        "WAR_GOAL_DRAFT": "war_goal_draft",
    },
    "war_goals": {
        "WAR_GOAL_DRAFT": "war_goal_draft",
        "WAR_GOAL": "war_goal",
        "STATE": "state",
        "INITIATOR_COUNTRY": "country",
        "SCOPE": "scope_object",
        "ROOT": "country",
        "COUNTRY": "country",
        "TARGET_COUNTRY": "country",
    },
    "treaty_articles": {
        "FIRST_COUNTRY": "country",
        "SECOND_COUNTRY": "country",
        "STATE": "state",
        "SCOPE": "scope_object",
        "ROOT": "country",
    },
    "journal_entries": {
        "JournalEntry": "journal_entry",
        "STATE": "state",
        "SCOPE": "scope_object",
        "ROOT": "country",
        "COUNTRY": "country",
        "TARGET_COUNTRY": "country",
    },
    "modifiers": {
        "STATE": "state",
        "SCOPE": "scope_object",
        "ROOT": "country",
        "COUNTRY": "country",
        "TARGET_COUNTRY": "country",
    },
    # Permissive context = union of all the above for the first step.
    # Built in _build_permissive_scopes().
    "permissive": {},
}

# Always-valid global functions (top-level, no scope prefix). Functions
# typically take a single string arg and return a typed object.
# Return type is what subsequent chain steps see.
_GLOBAL_FUNCTIONS: dict[str, str] = {
    # Player / scope helpers
    "GetPlayer": "country",
    "GetMetaPlayer": "meta_player",
    # Type-constructor helpers (take an id arg, return that type)
    "Country": "country",
    "State": "state",
    "Character": "character",
    "Pop": "pop",
    "PopType": "value",
    "InterestGroup": "interest_group",
    "Building": "building",
    "BuildingType": "value",
    "Goods": "market_goods",
    "Law": "law",
    "Religion": "religion",
    "Culture": "culture",
    "MilitaryFormation": "military_formation",
    "Battle": "value",
    "Invasion": "value",
    "PowerBloc": "power_bloc",
    "PoliticalMovement": "political_movement",
    "Ship": "value",
    "War": "war",
    "Company": "company",
    "Market": "market",
    "Party": "party",
    "StateRegion": "state_region",
    "PopListItem": "value",
    "GetDataModelSize": "value",
    # Direct getters (no scope; act as global accessors)
    "GetCulture": "culture",
    "GetReligion": "religion",
    "GetState": "state",
    "GetStateRegion": "state_region",
    "GetIdeology": "value",
    "GetLawType": "law",
    "GetBuildingType": "value",
    "GetGeographicRegion": "strategic_region",
    "GetStaticModifier": "value",
    "GetInterestGroupVariant": "value",
    "GetPopType": "value",
    "GetTutorialJournalEntry": "journal_entry",
    "GetGoods": "market_goods",
    "LabelingHelper": "value",
    "GetInstitutionType": "value",
    "GetLawGroup": "value",
    "GetDiplomaticActionType": "value",
    "GetBattleCondition": "value",
    "GetMobilizationOption": "value",
    "GetTechnologyType": "value",
    "GetCharacterTrait": "value",
    "Front": "value",
    "ArticleDraft": "value",
    "Article": "value",
    "WarPanel": "value",
    "Strait": "value",
    # Type-constructor helpers continued (long-tail vanilla)
    "GeographicRegion": "strategic_region",
    "CountryFormation": "value",
    "ShipTemplate": "value",
    "CombatUnitType": "value",
    "StrategicRegion": "strategic_region",
    "CombatUnit": "value",
    "Technology": "value",
    "ShipList": "value",
    "ShipConstruction": "value",
    "WarGoal": "war_goal",
    "PoliticalLobby": "political_lobby",
    "PopsOverviewPanel": "value",
    "Subject": "value",
    "Decree": "value",
    "Institution": "value",
    "Theater": "value",
    "Skirmish": "value",
    "Frontline": "value",
    "Mobilization": "value",
    "Trait": "value",
    "ProductionMethod": "value",
    "BuildingGroup": "value",
    "GoodsType": "value",
    "Pact": "diplomatic_pact",
    "Concept2": "value",
    "Idea": "value",
    "Discrimination": "value",
    "Ideology": "value",
    "BuyPackage": "value",
    "DecreeType": "value",
    "EraTechnology": "value",
    "TraitType": "value",
    "Treaty": "treaty",
    "TreatyArticle": "treaty_article",
    # Pure-helper functions returning value
    "GetDefine": "value",
    "Concept": "value",
    # 1.15: a glossary link (Glossary('glossary_x', 'text')) and a concept
    # looked up by a key held in a parameter.
    "Glossary": "value",
    "ConceptByKey": "value",
    "ObjectsEqual": "value",
    "AddTextIf": "value",
    "AddLocalizationIf": "value",
    "SelectLocalization": "value",
    "ConcatIfNeitherEmpty": "value",
    "GetRawTextTooltipTag": "value",
    "Nbsp": "value",
    "Not": "value",
    "Equal": "value",
    "And": "value",
    "Or": "value",
}

# Hand-curated supplement to the catalog parsed from event_targets_summary.txt.
# These are UI-side accessors that don't appear in the engine's event-targets
# log. Keyed by the *current* type; value is the type the accessor resolves to
# (or "value" for terminal atoms like names, numbers, booleans, strings).
#
# Initial seed from vanilla loc samples. Grows during phase 3 vanilla bootstrap.
#
# The entries under a type's "#348" line return an object: vanilla chains
# further through every one. The vanilla fold had typed most of them "value",
# which stopped the check at them (see "Blind pairs" below), and the rest sat
# unseen behind one of those. Their return types are the engine's own, from the
# 1.15.1 data types (`docs/data_types_*.txt` in the Modding-Digests checkout):
# each is a promote to the type named, written in snake case, or to one of the
# engine types this table folds together (a LawType is a `law`; Goods,
# MarketGoods and StateGoods are `market_goods`; an Article is a
# `treaty_article`; a Scope is a `scope_object`).
_BUILTIN_ACCESSORS_BY_TYPE: dict[str, dict[str, str]] = {
    "country": {
        # Names / display
        "GetName": "value",
        "GetNameNoFlag": "value",
        "GetNameNoFormatting": "value",
        "GetAdjective": "value",
        "GetAdjectiveNoFormatting": "value",
        "GetAdjectiveNoFlag": "value",
        "GetFlag": "value",
        "GetFlagTextIcon": "value",
        "GetTag": "value",
        "GetPlayedByDesc": "value",
        "GetTooltipTag": "value",
        "GetCustom": "value",
        # Self / identity
        "Self": "country",
        # Government / characters
        "GetRuler": "character",
        "GetHeir": "character",
        "GetCountry": "country",          # alias-passthrough sometimes seen
        "GetGovernment": "value",
        "GetGovernmentType": "value",
        # Geography / capital
        "GetCapital": "state",
        "GetCapitalState": "state",
        # Religion / culture
        "GetReligion": "religion",
        "GetStateReligion": "religion",
        "GetPrimaryCulture": "culture",
        # Power bloc
        "GetPowerBloc": "power_bloc",
        # 1.14.5: the AI regional objective the country holds in a strategic region
        "GetRegionalObjectiveIn": "regional_objective",
        # Subjects / overlords
        "GetOverlord": "country",
        "GetTopOverlord": "country",
        "GetSubjectType": "value",
        # Buildings / state lookups from country
        "GetBuilding": "building",
        "GetState": "state",
        "GetMarket": "market",
        "GetRank": "value",
        "GetRankName": "value",
        "GetLawBeingEnacted": "value",
        # A modifier, whose accessors the `modifier` type lists. Seeded (and
        # bootstrapped on every other type) as "value", which stopped the
        # check at it: every step after it was accepted unchecked.
        "GetModifier": "modifier",
        # 1.15 (vanilla: `THIS.GetJournalEntry.MakeScope.Var(...)`).
        "GetJournalEntry": "journal_entry",
        # A number (CFixedPoint in the 1.15 data types), which vanilla reads
        # only in its GUI, so the loc fold never meets it.
        "GetInstitutionInvestmentBureaucracyCost": "value",
        "GetActiveLawFromGroup": "law",
        "GetPrimaryCulturesDesc": "value",
        "GetGovernmentLegitimacy": "value",
        "GetCulture": "culture",
        "GetYouOrCountryName": "value",
        # Numerical / ratios
        "GetGDP": "value",
        "GetInfamy": "value",
        "GetPrestige": "value",
        "GetMobilizationRatio": "value",
        "GetBattalions": "value",
        "GetNumShips": "value",
        # Diplomacy
        "GetRelationsWith": "value",       # parametric
        "GetRelationsWithDesc": "value",   # parametric
        "GetRelationsTooltip": "value",    # parametric
        "GetTruceDate": "value",
        "GetAttitudeTowards": "value",
        "GetInvestmentGdpFractionInCountry": "value",
        # Player / observer convenience
        "GetPlayedOrObservedCountry": "country",
        # The player on a country, the type GetMetaPlayer returns (`Player` in
        # the 1.15.1 data types; vanilla: `Country.GetPlayer.GetName`).
        "GetPlayer": "meta_player",
        # Scope helpers used in chains
        "MakeScope": "scope_object",
        "ScriptValue": "value",
        "GetVariable": "scope_object",   # variable holding a scope; GetValue/GetCountry/etc. chain via scope_object
        "Var": "value",
        # #348: object-returning, typed from the 1.15.1 data types.
        "AccessCapital": "state",
        "CalcLibertyDesireLevel": "liberty_desire_level",
        "GetClosestFriendlyPort": "building",
        "GetCurrentInterestTierTypeIn": "interest_tier_type",
        "GetCurrentlyResearchedTechnology": "technology",
        "GetGovernmentLegitimacyLevel": "legitimacy_level",
        "GetInterestGroupOfType": "interest_group",
        "GetNegotiatingInterestGroup": "interest_group",
        "GetPowerBlocWithHighestLeverage": "power_bloc",
        "GetPreviousAttitudeTowards": "ai_attitude",
        "GetRankModifier": "modifier",
        "GetShipList": "ship_list",
        "GetTimedModifier": "timed_modifier",
        # The same, read off a script scope: ROOT, THIS and a journal entry's
        # GetTarget are `Scope`s in the data types, which this table models as
        # `country`, so `Scope.GetInterestGroup` and its kin sit here too.
        "GetCharacter": "character",
        "GetCompany": "company",
        "GetInstitution": "institution",
        "GetInterestGroup": "interest_group",
        "GetLawType": "law",
        "GetMilitaryFormation": "military_formation",
        "GetPoliticalLobby": "political_lobby",
        "GetStateGoods": "market_goods",
        "GetStateRegion": "state_region",
        "GetTechnology": "technology",
    },
    "scope_object": {
        # Saved-scope accessors (events use these). The "s" prefix means
        # "saved scope by name" -- argument is the scope name.
        "sCountry": "country",
        "sC": "country",                  # alias for sCountry seen in vanilla
        "sCharacter": "character",
        "sState": "state",
        "sStateRegion": "state_region",
        "sLaw": "law",
        "sLawType": "law",
        "sCulture": "culture",
        "sReligion": "religion",
        "sPop": "pop",
        "sBuilding": "building",
        # No `sInterestGroup` here: the engine has no such accessor (vanilla loc
        # uses `gsInterestGroup` 947 times and `sInterestGroup` never). A text
        # that used it rendered with everything up to the accessor missing
        # (un_events.34.d), so the audit must flag it, not wave it through.
        "sJournalEntry": "journal_entry",
        "sPoliticalMovement": "political_movement",
        "sPoliticalLobby": "political_lobby",
        "sPowerBloc": "power_bloc",
        "sDiplomaticPlay": "diplomatic_play",
        "sParty": "party",
        "sCommander": "character",
        "sCompany": "company",
        "sGoods": "market_goods",
        "sRegion": "strategic_region",
        "sStrategicRegion": "strategic_region",
        "sInvasion": "value",
        "sBattle": "value",
        # Mod-introduced patterns (used in Vic3TimelineExtended pre-existing loc).
        "sArticleOption": "value",
        "sTreaty": "treaty",
        "sTreatyArticle": "treaty_article",
        "sWar": "war",
        # Global-scope helpers (gs* prefix)
        "gsCountry": "country",
        "gsCharacter": "character",
        "gsState": "state",
        "gsInterestGroup": "interest_group",
        "gsCulture": "culture",
        "gsReligion": "religion",
        # Root passthrough / general getters
        "GetRootScope": "scope_object",
        "GetCountry": "country",
        "GetState": "state",
        "GetCharacter": "character",
        "GetCulture": "culture",
        "GetReligion": "religion",
        "GetInterestGroup": "interest_group",
        "GetMilitaryFormation": "military_formation",
        "GetMarketGoods": "market_goods",
        "GetPowerBloc": "power_bloc",
        "GetDiplomaticPact": "diplomatic_pact",
        "GetDiplomaticAction": "diplomatic_action",
        "GetDiplomaticPlay": "diplomatic_play",
        "GetWar": "war",
        "GetTreaty": "treaty",
        "GetJournalEntry": "journal_entry",
        "GetBuilding": "building",
        "GetParty": "party",
        "GetCompany": "company",
        "GetPoliticalMovement": "political_movement",
        "GetPoliticalLobby": "political_lobby",
        "GetGoods": "market_goods",
        "GetCommander": "character",
        "GetPop": "pop",
        "GetInvasion": "value",
        "GetBattle": "value",
        "GetStrategicRegion": "strategic_region",
        "GetStateGoods": "market_goods",
        "GetValue": "value",
        "sPowerBlocPrinciple": "value",
        "sFront": "value",
        "sInstitution": "value",
        "sDecree": "value",
        "ScriptValue": "value",
        "MakeScope": "scope_object",
        "Var": "value",
        # #348: object-returning, typed from the 1.15.1 data types.
        "GetCivilWar": "civil_war",
        "GetCountryFormation": "country_formation",
        "GetDecisionType": "decision",
        "GetDiplomaticDemand": "diplomatic_demand",
        "GetDiplomaticRelations": "diplomatic_relations",
        "GetFront": "front",
        "GetInstitution": "institution",
        "GetInterest": "interest",
        "GetLaw": "law",
        "GetMarket": "market",
        "GetShip": "ship",
        "GetStateRegion": "state_region",
        "GetTreatyArticle": "treaty_article",
        "sAmendmentType": "amendment_type",
        "sBT": "building_type",
        "sCOT": "commander_order_type",
        "sCR": "character_role",
        "sCha": "character",
        "sCountryFormation": "country_formation",
        "sDiplomaticCatalyst": "diplomatic_catalyst",
        "sG": "market_goods",
        "sHCA": "harvest_condition_area",
        "sHCT": "harvest_condition_type",
        "sHQ": "hq",
        "sIdeology": "ideology",
        "sInterestGroupTrait": "interest_group_trait",
        "sInterestTierType": "interest_tier_type",
        "sJE": "journal_entry",
        "sMilitaryFormation": "military_formation",
        "sPL": "political_lobby",
        "sPowerBlocPrincipleGroup": "power_bloc_principle_group",
        "sProvince": "province",
        "sS": "state",
        "sStrait": "strait",
        "sT": "technology",
        "sW": "war",
        "sWarGoal": "war_goal",
    },
    "character": {
        "Self": "character",
        "GetName": "value",
        "GetNameNoFormatting": "value",
        "GetFullName": "value",
        "GetFullNameNoFormatting": "value",
        "GetFullNameWithTitle": "value",
        "GetFirstName": "value",
        "GetFirstNameNoFormatting": "value",
        "GetLastName": "value",
        "GetLastNameNoFormatting": "value",
        "GetSheHe": "value",
        "GetSheHeCap": "value",
        "GetHerHis": "value",
        "GetHerHisCap": "value",
        "GetHerHim": "value",
        "GetHimHer": "value",
        "GetCountry": "country",
        "GetInterestGroup": "interest_group",
        "GetIdeology": "value",
        "GetCulture": "culture",
        "GetReligion": "religion",
        "GetPrimaryRoleTitle": "value",
        "GetTitle": "value",
        "GetAge": "value",
        "GetPortrait": "value",
        "GetCustom": "value",
        "GetTooltipTag": "value",
        "GetWomanMan": "value",
        "GetHerselfHimself": "value",
        "GetPrimaryRole": "value",
        "GetRankName": "value",
        "GetOrderType": "value",
        "GetMilitaryFormation": "military_formation",
        "GetFullNamePossessive": "value",
        "HasIdeology": "value",
        "MakeScope": "scope_object",
        "Var": "value",
        # #348: object-returning, typed from the 1.15.1 data types.
        "GetBattle": "battle",
        "GetCompany": "company",
        "GetFront": "front",
        "GetHolding": "building",
        "GetHomeCountry": "country",
        "GetHomeCountryDefinition": "country_definition",
        "GetHomeState": "state",
        "GetInvasion": "invasion",
        "GetNextOrderType": "commander_order_type",
        "GetPoliticalMovement": "political_movement",
        "PredictMovementToJoin": "political_movement",
        "PredictMovementTypeToStart": "political_movement_type",
    },
    "state": {
        "Self": "state",
        "GetName": "value",
        "GetNameNoFormatting": "value",
        "GetCityHubName": "value",
        "GetFarmHubName": "value",
        # vanilla uses the next three rarely (Port, Forestry) or never (Mine), but all five hub accessors are in
        # victoria3.exe (2026-11-03); the Demographics tab's Largest Cities names a state's towns with them
        "GetPortHubName": "value",
        "GetMineHubName": "value",
        "GetForestryHubName": "value",
        "GetCountry": "country",
        "GetOwner": "country",
        # State value / state infamy "perspective" accessors both return the
        # COUNTRY the reckoning is from, not a display string. Vanilla:
        #   STATE_STATE_INFAMY_OWNED "[State.GetStateInfamyPerspective
        #       .GetNameNoFormatting] already owns [State.GetName]"
        #   STATE_STATE_VALUE        "How much [State.GetStateValuePerspective
        #       .GetNameNoFormatting] values holding this [concept_state]"
        # Hand-placed here with their real return type rather than folded into
        # the extras as "value": validate_chain treats a `value` step as
        # terminal and accepts every later step unchecked, so mis-folding one
        # of these does not just lose a check, it blinds the rest of the chain.
        # GetStateValuePerspective was mis-folded by the 1.14 bootstrap; see
        # the follow-up issue for the rest of that class.
        "GetStateInfamyPerspective": "country",
        "GetStateValuePerspective": "country",
        # 1.15: the world market hub serving the state, a state itself
        # (vanilla: `STATE.GetWorldMarketHub.GetNameWithCountryFlag`,
        # `.GetWorldMarketHub.GetStateRegion.GetNavalExitStateRegion...`).
        "GetWorldMarketHub": "state",
        "GetModifier": "modifier",
        "GetRegion": "strategic_region",
        "GetStateRegion": "state_region",
        "GetPopulation": "value",
        "GetPopulationSize": "value",
        "GetGDP": "value",
        "GetCustom": "value",
        "GetTooltipTag": "value",
        "GetMarket": "market",
        "GetFoodSecurity": "value",
        "GetBuilding": "building",
        "MakeScope": "scope_object",
        "ScriptValue": "value",
        "Var": "value",
        # #348: object-returning, typed from the 1.15.1 data types.
        "GetColonyCompany": "company",
        "GetController": "country",
        "GetMassMigrationCulture": "culture",
        "GetMassMigrationOriginCountry": "country",
        "GetSubsistenceBuilding": "building",
        "GetTheater": "theater",
    },
    "state_region": {
        "Self": "state_region",
        "GetName": "value",
        "GetNameNoFormatting": "value",
        "GetStrategicRegion": "strategic_region",
        "GetCityHubName": "value",
        # 1.15: the sea region a state region's naval exit opens on, read for
        # its cold (vanilla: `.GetNavalExitStateRegion.GetColdEffect`).
        "GetNavalExitStateRegion": "state_region",
    },
    "interest_group": {
        "Self": "interest_group",
        "GetName": "value",
        "GetNameNoFormatting": "value",
        "GetCountry": "country",
        "GetLeader": "character",
        "GetClout": "value",
        "GetIdeology": "value",
        "GetType": "value",
        "GetCustom": "value",
        "GetTooltipTag": "value",
        "GetPopulation": "value",
        "GetApprovalValue": "value",
        "GetModifier": "modifier",
        "MakeScope": "scope_object",
        # #348: object-returning, typed from the 1.15.1 data types.
        "AccessCountry": "country",
        "GetParty": "party",
        "GetPopWithIG": "pop_with_ig",
    },
    "culture": {
        "Self": "culture",
        "GetName": "value",
        "GetNameNoFormatting": "value",
        "GetNamePlural": "value",
        "GetCollectiveNoun": "value",
        "GetCustom": "value",
        "MakeScope": "scope_object",
        # #348: object-returning, typed from the 1.15.1 data types.
        "GetHeritageTrait": "discrimination_trait",
        "GetLanguageTrait": "discrimination_trait",
        "GetReligion": "religion",
    },
    "religion": {
        "Self": "religion",
        "GetName": "value",
        "GetNameNoFormatting": "value",
        "GetAdjective": "value",
        "GetAdherentNoun": "value",
        "GetCustom": "value",
        "MakeScope": "scope_object",
    },
    "power_bloc": {
        "Self": "power_bloc",
        "GetName": "value",
        "GetNameNoFormatting": "value",
        "GetLeader": "country",
        "GetIdentity": "value",
        "GetParticipantWithHighestInfamy": "country",
        "GetParticipantWithLowestInfamy": "country",
        "GetModifier": "modifier",
        "GetCustom": "value",
        "GetTooltipTag": "value",
        # Every other type's MakeScope is scope_object; power_bloc's was folded
        # in from vanilla as "value", which stopped the audit dead at
        # `PowerBloc.MakeScope.ScriptValue(...)` and accepted whatever followed.
        "MakeScope": "scope_object",
        # #348: object-returning, typed from the 1.15.1 data types.
        "GetCohesionLevel": "cohesion_level",
        "GetParticipantWithHighestLeaderLawProgressivenessDifference": "country",
        "GetParticipantWithHighestLibertyDesire": "country",
        "GetParticipantWithLowestEconomicDependence": "country",
        "GetParticipantWithLowestEconomicDependenceOnLeader": "country",
        "GetParticipantWithLowestLeaderRelations": "country",
        "GetParticipantWithLowestLeaderReligionPercentage": "country",
        "GetPowerStruggleContender": "country",
    },
    "law": {
        # The audit models a law type as `law`, as the global GetLawType('x')
        # does. Law.GetLawType is the promote to it (LawType in the 1.15 data
        # types); vanilla reads it 65 times, mostly in its GUI, so the loc
        # fold never meets it.
        "GetLawType": "law",
        "GetEffectDesc": "value",  # LawType.GetEffectDesc(country): its effects text
        "GetDeltaEffectDesc": "value",  # 1.15: the effects compared to the current law (politics_panel_change_law.gui:969)
        "Self": "law",
        "GetName": "value",
        "GetNameNoFormatting": "value",
        "GetDescription": "value",
        "GetTooltipTag": "value",
        "GetCountry": "country",
        "GetGroup": "value",
        # #348: object-returning, typed from the 1.15.1 data types.
        "GetActiveGroupLaw": "law",
        "GetCheckpointEndDate": "date",
        "GetEnactmentLastCheckpointDate": "date",
        "GetInstitution": "institution",
        "GetInstitutionType": "institution_type",
    },
    "diplomatic_play": {
        "Self": "diplomatic_play",
        "GetName": "value",
        "GetInitiator": "country",
        "GetTarget": "country",
        "GetWargoal": "war_goal",
        # #348: object-returning, typed from the 1.15.1 data types.
        "GetDiplomaticPlayType": "diplomatic_play_type",
        "GetInterestMarker": "interest",
        "GetStrategicRegion": "strategic_region",
    },
    "diplomatic_action": {
        "Self": "diplomatic_action",
        "GetName": "value",
        "GetSecondCountry": "country",
        "GetFirstCountry": "country",
        # #348: object-returning, typed from the 1.15.1 data types.
        "GetType": "diplomatic_action_type",
    },
    "war_goal": {
        "Self": "war_goal",
        "GetName": "value",
        "GetTarget": "country",
        "GetTargetState": "state",
        "GetHolder": "country",
        # #348: object-returning, typed from the 1.15.1 data types.
        "GetCreator": "country",
        "GetDiplomaticPlay": "diplomatic_play",
        "GetType": "war_goal_type",
        "GetWar": "war",
        "GetWarGoalStakeholder": "country",
    },
    "war_goal_draft": {
        "Self": "war_goal_draft",
        "GetName": "value",
        "GetTarget": "country",
        "GetTargetState": "state",
        "GetHolder": "country",
        "GetCountry": "country",
        "GetWarGoalStakeholder": "country",
        # #348: object-returning, typed from the 1.15.1 data types.
        "GetArticleType": "article_type",
        "GetCountryCreation": "country_creation",
        "GetCountryFormation": "country_formation",
        "GetCreator": "country",
    },
    "journal_entry": {
        "Self": "journal_entry",
        "GetName": "value",
        "GetGoalProgressValue": "value",
        "GetGoalAddValue": "value",
        "GetCurrentBarValue": "value",
        "GetCurrentBarProgress": "value",
        "GetTotalGoalValue": "value",
        "CalcCurrentGoalValue": "value",
        "GetCountry": "country",
        "GetTarget": "country",
        # 1.15 (vanilla: `JournalEntry.MakeScope.Var(...)`,
        # `JournalEntry.GetModifier.GetFormattedValueFor(...)`).
        "MakeScope": "scope_object",
        "GetModifier": "modifier",
        # #348: object-returning, typed from the 1.15.1 data types.
        "GetBuildingTarget": "building",
        "GetType": "journal_entry_type",
    },
    "pop": {
        "Self": "pop",
        "GetName": "value",
        "GetNameNoFormatting": "value",
        "GetCulture": "culture",
        "GetReligion": "religion",
        "GetType": "value",
        "GetPopType": "value",
        "GetSize": "value",
        "GetCountry": "country",
        "GetState": "state",
        "GetTooltipTag": "value",
        "GetCurrentWealth": "value",
        # #348: object-returning, typed from the 1.15.1 data types.
        "GetAcceptanceStatus": "acceptance_status",
        "GetAssimilatingCulture": "culture",
        "GetBuilding": "building",
        "GetConvertingReligion": "religion",
        "GetLargestInterestGroup": "interest_group",
        "GetLargestPoliticalMovement": "political_movement",
        "GetSocialClass": "social_class",
    },
    "building": {
        "Self": "building",
        "GetName": "value",
        "GetNameNoFormatting": "value",
        "GetState": "state",
        "GetType": "value",
        "GetBuildingType": "value",
        "GetTooltipTag": "value",
        "GetNoOfEmployed": "value",
        "GetModifier": "modifier",
        # #348: object-returning, typed from the 1.15.1 data types.
        "AccessState": "state",
        "GetDefaultOutputGoods": "market_goods",
        "GetOwner": "country",
    },
    "political_movement": {
        "Self": "political_movement",
        "GetName": "value",
        "GetNameNoFormatting": "value",
        "GetType": "value",
        "GetCivilWar": "value",
        "GetTooltipTag": "value",
        # #348: object-returning, typed from the 1.15.1 data types.
        "GetCountry": "country",
    },
    "strategic_region": {
        "Self": "strategic_region",
        "GetName": "value",
    },
    "treaty": {
        "Self": "treaty",
        "GetName": "value",
        # #348: object-returning, typed from the 1.15.1 data types.
        "GetEnforcedOnCountry": "country",
        "GetFirstCountry": "country",
        "GetOtherCountry": "country",
    },
    "war": {
        "Self": "war",
        "GetName": "value",
        "GetDiplomaticPlay": "diplomatic_play",
        # 1.14.5: the country's war goal that is about to be dropped as uncontested
        "GetWarGoalAtRiskOfBeingDropped": "war_goal",
        # #348: object-returning, typed from the 1.15.1 data types.
        "AccessAttackerLeaderParticipant": "war_participant",
        "AccessDefenderLeaderParticipant": "war_participant",
        "AccessLeftSideLeaderParticipant": "war_participant",
        "AccessRightSideLeaderParticipant": "war_participant",
        "GetAttackerLeader": "country",
        "GetDefenderLeader": "country",
        "GetLeaderOfOppositeSide": "country",
    },
    "regional_objective": {
        "Self": "regional_objective",
        "GetName": "value",
    },
    "market_goods": {
        "Self": "market_goods",
        "GetName": "value",
        "GetNameNoFormatting": "value",
        "GetType": "value",
        "GetGoods": "market_goods",
        "GetMarket": "market",
        "GetState": "state",
        "GetTextIcon": "value",
        "GetTooltipTag": "value",
        "GetPercentageDeltaAgainstBasePrice": "value",
        # #348: object-returning, typed from the 1.15.1 data types.
        "GetBaseGoods": "market_goods",
        "WithMarketContext": "market_goods",
    },
    "military_formation": {
        "Self": "military_formation",
        "GetName": "value",
        "GetNameNoFormatting": "value",
        "GetCountry": "country",
        "GetType": "value",
        "GetShipList": "value",
        "GetUnitIcon": "value",
        "GetUnitLabel": "value",
        "GetTooltipTag": "value",
        "GetNumCombatUnits": "value",
        "GetSelectedUnitTypeForGroup": "value",
        # 1.15, from vanilla's chains: the HQ new ships join
        # (`.GetNewShipsHQ.GetName`), the sea node a fleet sails to
        # (`.GetTargetSeaNode.GetStateRegion`, a Province per the data types),
        # and the interest tier a project-power order would reach
        # (`.GetTargetInterestTierTypeInRegion(...).GetNameNoIcon`).
        "GetNewShipsHQ": "hq",
        # 1.15.1: the state a fleet draws supply from, a State per the data
        # types (vanilla: `MilitaryFormation.GetSupplyHub.GetName`).
        "GetSupplyHub": "state",
        "GetTargetSeaNode": "province",
        "GetTargetInterestTierTypeInRegion": "interest_tier_type",
        "GetTargetInterestTierTypeWithoutFleetInRegion": "interest_tier_type",
        # #348: object-returning, typed from the 1.15.1 data types.
        "FindLeastExperiencedRegularUnit": "combat_unit",
        "GetCommander": "character",
        "GetCurrentHQ": "hq",
        "GetFlagship": "ship",
        "GetInvasion": "invasion",
        "GetNavalMission": "naval_mission",
        "GetStrategicObjective": "state",
        "GetTargetHQ": "hq",
    },
    "party": {
        "Self": "party",
        "GetName": "value",
        "GetNameNoFormatting": "value",
        # A party's leader is its leading interest group (Party.GetLeader is a
        # promote to InterestGroup in the 1.15.1 data types; vanilla:
        # `Party.GetLeader.GetLeader.GetFullName`). Typed `character`, it had
        # the fold add a `character.GetLeader` the engine doesn't have (#348).
        "GetLeader": "interest_group",
        "GetCountry": "country",
        "GetMembersSummary": "value",
        "MakeScope": "scope_object",  # 1.15 vanilla: `.sParty('x').MakeScope.ScriptValue(...)`
    },
    "company": {
        "Self": "company",
        "GetName": "value",
        "GetNameNoFormatting": "value",
        "GetCountry": "country",
        "GetType": "value",
        # #348: object-returning, typed from the 1.15.1 data types.
        "GetBuilding": "building",
        "GetCompanyType": "company_type",
        "GetEstablishmentDate": "date",
        "GetExecutive": "character",
        "GetState": "state",
    },
    "political_lobby": {
        "Self": "political_lobby",
        "GetName": "value",
        "GetNameNoFormatting": "value",
        "GetType": "value",
        "GetCountry": "country",
        # #348: object-returning, typed from the 1.15.1 data types.
        "GetTargetCountry": "country",
    },
    "diplomatic_pact": {
        "Self": "diplomatic_pact",
        "GetFirstCountry": "country",
        "GetSecondCountry": "country",
    },
    "treaty_article": {
        "Self": "treaty_article",
        "GetName": "value",
        # #348: object-returning, typed from the 1.15.1 data types.
        "GetTreaty": "treaty",
    },
    "market": {
        "Self": "market",
        "GetName": "value",
        "GetCountry": "country",
        "GetGoods": "market_goods",
        "GetOwner": "country",
        # #348: object-returning, typed from the 1.15.1 data types.
        "AccessMarketCapital": "state",
        "GetMarketCapital": "state",
    },
    # A modifier (Country/State/Building/InterestGroup/PowerBloc/JournalEntry
    # .GetModifier): every accessor vanilla 1.15's and the mod's loc read off
    # one, all text or numbers.
    "modifier": {
        "GetDesc": "value",
        "GetDescFor": "value",
        "GetFormattedValueFor": "value",
        "GetFullEntryDescFor": "value",
        "GetInvertedValueFor": "value",
        "GetNonFormattedValueWithBreakdownAndNoDecimalsFor": "value",
        "GetTooltipFor": "value",
        "GetValueFor": "value",
        "GetValueWithBreakdownFor": "value",
        "IsEmpty": "value",
    },
    # 1.15's type-changing military formation accessors land on these.
    "hq": {
        "Self": "hq",
        "GetName": "value",
    },
    "province": {
        "Self": "province",
        "GetStateRegion": "state_region",
        # #348: object-returning, typed from the 1.15.1 data types.
        "GetState": "state",
    },
    "interest_tier_type": {
        "Self": "interest_tier_type",
        "GetName": "value",
        "GetNameNoIcon": "value",
        "GetSmallTextIcon": "value",
    },
    # --- #348: the types the object-returning accessors above land on. --------
    # Each holds `Self` and the accessors vanilla chains further through; the
    # names and numbers vanilla reads off it are folded into the extras. So a
    # type here knows only what vanilla's loc calls on it: a flag on another
    # accessor the data types do list is a gap to fill here, not a broken chain.
    "acceptance_status": {"Self": "acceptance_status"},
    "ai_attitude": {"Self": "ai_attitude"},
    "amendment_type": {"Self": "amendment_type"},
    "article_type": {"Self": "article_type"},
    "battle": {
        "Self": "battle",
        "GetFront": "front",
    },
    "building_type": {"Self": "building_type"},
    "character_role": {"Self": "character_role"},
    "civil_war": {
        "Self": "civil_war",
        "GetUprisingCountry": "country",
    },
    "cohesion_level": {"Self": "cohesion_level"},
    "combat_unit": {
        "Self": "combat_unit",
        "GetBuilding": "building",
    },
    "commander_order_type": {"Self": "commander_order_type"},
    "company_type": {
        "Self": "company_type",
        "GetProsperityModifier": "modifier",
    },
    "country_creation": {"Self": "country_creation"},
    "country_definition": {"Self": "country_definition"},
    "country_formation": {"Self": "country_formation"},
    "date": {"Self": "date"},
    "decision": {"Self": "decision"},
    "diplomatic_action_type": {"Self": "diplomatic_action_type"},
    "diplomatic_catalyst": {"Self": "diplomatic_catalyst"},
    "diplomatic_demand": {
        "Self": "diplomatic_demand",
        "GetDemandedWarGoal": "war_goal_draft",
    },
    "diplomatic_play_type": {"Self": "diplomatic_play_type"},
    "diplomatic_relations": {
        "Self": "diplomatic_relations",
        "GetCountryWhichOwesObligation": "country",
        "GetFirstCountry": "country",
        "GetSecondCountry": "country",
    },
    "discrimination_trait": {"Self": "discrimination_trait"},
    "front": {"Self": "front"},
    "harvest_condition_area": {
        "Self": "harvest_condition_area",
        "GetType": "harvest_condition_type",
    },
    "harvest_condition_type": {"Self": "harvest_condition_type"},
    "ideology": {"Self": "ideology"},
    "institution": {"Self": "institution"},
    "institution_type": {"Self": "institution_type"},
    "interest": {
        "Self": "interest",
        "GetStrategicRegion": "strategic_region",
    },
    "interest_group_trait": {"Self": "interest_group_trait"},
    "invasion": {
        "Self": "invasion",
        "GetTargetState": "state",
    },
    "journal_entry_group": {"Self": "journal_entry_group"},
    "journal_entry_type": {
        "Self": "journal_entry_type",
        "GetGroup": "journal_entry_group",
    },
    "legitimacy_level": {"Self": "legitimacy_level"},
    "liberty_desire_level": {"Self": "liberty_desire_level"},
    "naval_mission": {"Self": "naval_mission"},
    "political_movement_type": {"Self": "political_movement_type"},
    "pop_with_ig": {"Self": "pop_with_ig"},
    "power_bloc_principle_group": {"Self": "power_bloc_principle_group"},
    "ship": {
        "Self": "ship",
        "GetType": "ship_type",
    },
    "ship_list": {"Self": "ship_list"},
    "ship_type": {"Self": "ship_type"},
    "social_class": {"Self": "social_class"},
    "strait": {"Self": "strait"},
    "technology": {"Self": "technology"},
    "theater": {"Self": "theater"},
    "timed_modifier": {"Self": "timed_modifier"},
    "war_goal_type": {"Self": "war_goal_type"},
    "war_participant": {"Self": "war_participant"},
    "meta_player": {
        "GetPlayedOrObservedCountry": "country",
        "GetPlayedCountry": "country",
        "GetCountry": "country",
        "Self": "meta_player",
    },
    # Terminal value: no further accessors. Anything chained off `value` is a
    # terminal text/number, but we accept any further step (since some loc
    # uses .GetName-on-value as a no-op) — set this to "value" to keep walking.
    "value": {},
}


def _build_permissive_scopes() -> dict[str, str]:
    """Permissive context = union of all named-context magic scopes."""
    out: dict[str, str] = {}
    for ctx, scopes in _MAGIC_SCOPES_BY_CONTEXT.items():
        if ctx == "permissive":
            continue
        for name, typ in scopes.items():
            out.setdefault(name, typ)
    return out


# A diplomatic action's own `<action>_desc` is its generic description, and it
# renders with no target bound: `[TARGET_COUNTRY.…]` there promotes to nullptr
# (`voluntary_union_desc` logged 138 per-frame nullptr promotes, 2026-09-14).
# Vanilla never names the target in `<action>_desc`. The table is copied from
# `diplomatic_actions` before `permissive` is built, so the union is unchanged.
_MAGIC_SCOPES_BY_CONTEXT["diplomatic_action_descs"] = {
    name: typ
    for name, typ in _MAGIC_SCOPES_BY_CONTEXT["diplomatic_actions"].items()
    if name != "TARGET_COUNTRY"
}

_MAGIC_SCOPES_BY_CONTEXT["permissive"] = _build_permissive_scopes()


# Scopes that are affirmatively WRONG (unbound) in a given context, even though
# the permissive union would otherwise admit them. Without this, dropping a
# scope from a context's magic table is not enough to flag it — the permissive
# fallback in validate_chain re-admits any scope known to *some* context. These
# entries short-circuit that fallback for the high-value diplomatic-notification
# case (issue #149).
_DENIED_SCOPES_BY_CONTEXT: dict[str, dict[str, str]] = {
    "diplomatic_action_notifications": {
        "COUNTRY": (
            "bare 'COUNTRY' is unbound in diplomatic-action notification descs "
            "(renders nullptr, spams 'Promote COUNTRY returned nullptr' every "
            "frame) — the actor is [INITIATOR_COUNTRY.…], the target "
            "[TARGET_COUNTRY.…]"
        ),
    },
    "diplomatic_action_descs": {
        "TARGET_COUNTRY": (
            "'TARGET_COUNTRY' is unbound in a diplomatic action's own _desc "
            "(renders nullptr every frame) — describe the target generically, "
            "as vanilla does"
        ),
    },
}

# Accessor steps that are affirmatively null in a given context, regardless of
# the first-step scope. `GetDiplomaticPact` resolves to an active pact only in
# `_pact_desc` (pact already formed); in notification / proposal / break descs
# there is no pact yet, so `[SCOPE.GetRootScope.GetDiplomaticPact.…]` is null.
_DENIED_ACCESSORS_BY_CONTEXT: dict[str, dict[str, str]] = {
    "diplomatic_action_notifications": {
        "GetDiplomaticPact": (
            "'GetDiplomaticPact' resolves null in notification/proposal/break "
            "descs (no active pact at this stage) — reference the parties "
            "directly via [INITIATOR_COUNTRY.…] / [TARGET_COUNTRY.…]"
        ),
    },
}


# The hand-typed table as written above, before the vanilla fold's terminals
# join it below. The blind-pair detector tells a hand-typed `value` from a
# folded one by it, and the fold drops an extras entry that a pair here shadows.
HAND_TYPED_ACCESSORS: dict[str, dict[str, str]] = {
    typ: dict(accessors) for typ, accessors in _BUILTIN_ACCESSORS_BY_TYPE.items()
}


def merge_folded(
    hand: dict[str, dict[str, str]], folded: dict[str, dict[str, str]]
) -> dict[str, dict[str, str]]:
    """`hand` plus every `folded` pair it doesn't define: a hand-typed pair
    always wins. Returns a new table."""
    out = {typ: dict(accessors) for typ, accessors in hand.items()}
    for typ, accessors in folded.items():
        target = out.setdefault(typ, {})
        for acc, ret in accessors.items():
            target.setdefault(acc, ret)
    return out


# Vanilla-extracted accessors, written by scripts/generators/
# fold_vanilla_loc_accessors.py from the flags this audit raises on vanilla's
# loc. All are terminal `value`-returning UI accessors that don't appear in the
# engine's event-targets log. An accessor vanilla chains further through
# (GetRuler -> character) is typed by hand in `_BUILTIN_ACCESSORS_BY_TYPE`
# above: the fold reports those and leaves them out (#348).
try:
    from localization_accessor_vanilla_extras import VANILLA_EXTRACTED_ACCESSORS
except ImportError:
    # vanilla_extras not present (e.g. fresh checkout, or running without
    # the bootstrap). Audit still works; just with the smaller curated catalog.
    VANILLA_EXTRACTED_ACCESSORS = {}
_BUILTIN_ACCESSORS_BY_TYPE = merge_folded(HAND_TYPED_ACCESSORS, VANILLA_EXTRACTED_ACCESSORS)


# ---------------------------------------------------------------------------
# Catalog from engine docs
# ---------------------------------------------------------------------------

def _load_engine_catalog(
    engine_docs_dir: str, accessors: dict[str, dict[str, str]] | None = None
) -> dict[str, dict[str, str]]:
    """Parse `event_targets_summary.txt` into `{scope_type: {accessor: return_type}}`.

    Augmented with `_BUILTIN_ACCESSORS_BY_TYPE`, or with `accessors` when given
    (the fold passes the hand-typed table merged with the extras it is about to
    write). The result is the spine of chain validation: at any point in a walk
    we look up `catalog[current_type][next_step]` to learn the next type.
    """
    if accessors is None:
        accessors = _BUILTIN_ACCESSORS_BY_TYPE
    catalog: dict[str, dict[str, str]] = {
        typ: dict(accs) for typ, accs in accessors.items()
    }

    path = os.path.join(engine_docs_dir, "event_targets_summary.txt")
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split("|", 3)
                if len(parts) < 3:
                    continue
                scope_type, accessor, return_type = parts[0], parts[1], parts[2]
                # Some lines list multiple comma-separated scope types
                # (e.g. `country,front,state_region|every_scope_state|...`).
                # Spread the accessor across each.
                for typ in scope_type.split(","):
                    typ = typ.strip()
                    if not typ:
                        continue
                    catalog.setdefault(typ, {}).setdefault(accessor, return_type)

    return catalog


# ---------------------------------------------------------------------------
# Loc reading (preserves comments and line numbers)
# ---------------------------------------------------------------------------

@dataclass
class LocLine:
    file: str       # path (relative or absolute, caller's choice)
    line: int       # 1-indexed
    key: str
    value: str      # the quoted value, with surrounding whitespace stripped
    comment: str | None = None  # everything after the value-ending `"`, or None


def _split_value_and_comment(payload: str) -> tuple[str, str | None]:
    """From a loc line's RHS (after `key:N `), pull out the quoted value
    and any trailing comment. Quotes inside the value are not escaped in
    Vic3 loc, so we use the *last* `"` as the value boundary.
    """
    payload = payload.lstrip()
    if not payload.startswith('"'):
        # No quoted value; take the whole thing as the value.
        return payload.rstrip(), None
    # Find the closing quote — last `"` on the line.
    closing = payload.rfind('"')
    if closing <= 0:
        return payload.rstrip(), None
    value = payload[1:closing]
    rest = payload[closing + 1:].strip()
    comment = rest if rest else None
    return value, comment


def read_loc_file(path: str) -> list[LocLine]:
    """Parse a single `.yml` loc file. Returns one LocLine per `key: value`.

    Skips the `l_english:` header, blank lines, and pure-comment lines.
    Trailing same-line comments (after the closing `"`) are kept on the
    LocLine for suppression detection.
    """
    out: list[LocLine] = []
    rel = path  # caller passes whatever they want as the displayed path
    with open(path, encoding="utf-8-sig") as f:
        for lineno, raw in enumerate(f, start=1):
            stripped = raw.strip()
            if not stripped or stripped.startswith("#") or stripped == "l_english:":
                continue
            m = _LOC_LINE_RE.match(raw.rstrip("\n").rstrip("\r"))
            if not m:
                continue
            key = m.group("key")
            payload = m.group("value")
            value, comment = _split_value_and_comment(payload)
            out.append(LocLine(file=rel, line=lineno, key=key, value=value, comment=comment))
    return out


def read_all_loc(loc_dir: str) -> list[LocLine]:
    """Read every `.yml` in `loc_dir` (non-recursive), preserving order."""
    out: list[LocLine] = []
    if not os.path.isdir(loc_dir):
        return out
    for fname in sorted(os.listdir(loc_dir)):
        if not fname.endswith(".yml"):
            continue
        fpath = os.path.join(loc_dir, fname)
        if not os.path.isfile(fpath):
            continue
        # Use the basename for display so reports stay portable.
        for ll in read_loc_file(fpath):
            out.append(LocLine(file=fname, line=ll.line, key=ll.key, value=ll.value, comment=ll.comment))
    return out


# ---------------------------------------------------------------------------
# Context classification
# ---------------------------------------------------------------------------

_EVENT_KEY_RE = re.compile(r"^[a-z_]+\.\w+")


def classify_context(
    key: str,
    *,
    diplo_action_keys: set[str] | None = None,
    je_keys: set[str] | None = None,
) -> str:
    """Map a loc key to the rendering context it'll be displayed in.

    Pattern-based; uses sets passed by the caller (or empty fallbacks) to
    recognize entity-id-shaped keys for diplomatic actions and journal
    entries. Defaults to `permissive` for unclassified keys.
    """
    diplo_action_keys = diplo_action_keys or set()
    je_keys = je_keys or set()

    if _EVENT_KEY_RE.match(key):
        return "events"
    if key.startswith("war_goal_"):
        return "war_goals"
    if key.startswith("je_") or key in je_keys:
        return "journal_entries"
    # Diplomatic-action notification *descs*: the bare actor scope is unbound
    # here (see `diplomatic_action_notifications` context). Checked before the
    # general diplomatic suffixes so these route to the stricter context.
    for suffix in (
        "_action_notification_desc",
        "_proposal_notification_desc",
        "_action_notification_break_desc",
    ):
        if key.endswith(suffix) and key[: -len(suffix)] in diplo_action_keys:
            return "diplomatic_action_notifications"
    if key.endswith("_desc") and key[: -len("_desc")] in diplo_action_keys:
        return "diplomatic_action_descs"
    # Diplomatic-action-related keys: the action name AND its standard suffixes.
    for suffix in (
        "", "_desc", "_action_name", "_action_propose_name",
        "_action_notification_name",
        "_action_break_name", "_action_notification_break_name",
        "_proposal_accepted_name", "_proposal_accepted_desc",
        "_proposal_declined_name", "_proposal_declined_desc",
        "_proposal_notification_name",
        "_proposal_notification_effects_desc", "_pact_desc",
    ):
        if suffix and key.endswith(suffix):
            base = key[: -len(suffix)]
            if base in diplo_action_keys:
                return "diplomatic_actions"
        elif suffix == "" and key in diplo_action_keys:
            return "diplomatic_actions"
    if key.startswith("article_"):
        return "treaty_articles"
    return "permissive"


# ---------------------------------------------------------------------------
# Chain extraction and validation
# ---------------------------------------------------------------------------

def _strip_format_modifier(content: str) -> str:
    """Drop the trailing `|fmt` modifier from inside `[...]`. Vanilla forms:
    `|v`, `|0`, `|D`, `|U`, `|0%`, `|+`, `|-0`. The modifier always starts
    with `|` outside any parenthesized expression. Find the *outermost* `|`.
    """
    depth = 0
    in_quote = False
    for i, ch in enumerate(content):
        if ch == "'":
            in_quote = not in_quote
            continue
        if in_quote:
            continue
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch == "|" and depth == 0:
            return content[:i]
    return content


def _split_chain(content: str) -> list[str]:
    """Split on `.` but only at depth 0 (outside parens / quotes). This keeps
    `sCountry('owner.foo')` as a single step."""
    out: list[str] = []
    buf: list[str] = []
    depth = 0
    in_quote = False
    for ch in content:
        if ch == "'":
            in_quote = not in_quote
            buf.append(ch)
            continue
        if in_quote:
            buf.append(ch)
            continue
        if ch == "(":
            depth += 1
            buf.append(ch)
        elif ch == ")":
            depth -= 1
            buf.append(ch)
        elif ch == "." and depth == 0:
            out.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    if buf:
        out.append("".join(buf))
    return out


def _step_name(step: str) -> str:
    """Strip `(...)` from a function-call step, leaving just the function name."""
    m = _FUNC_CALL_RE.match(step)
    if m:
        return m.group(1)
    return step


def _is_concept_or_substitution(content: str) -> bool:
    """`[concept_X]` and `[$X$]` aren't accessor chains."""
    if content.startswith("concept_"):
        return True
    if content.startswith("$") and content.endswith("$"):
        return True
    return False


@dataclass
class Chain:
    raw: str            # the original `[...]` content (without brackets)
    steps: list[str]    # split on `.`, function-call parens kept intact


def extract_chains(text: str) -> list[Chain]:
    """Find every `[...]` reference in text and split into chain steps.

    Skips concept references and `$X$` substitutions. Strips the format
    modifier (e.g. `|v`) before splitting.
    """
    out: list[Chain] = []
    for m in _CHAIN_RE.finditer(text):
        content = m.group(1).strip()
        if not content:
            continue
        if _is_concept_or_substitution(content):
            continue
        body = _strip_format_modifier(content)
        steps = _split_chain(body)
        if not steps:
            continue
        out.append(Chain(raw=content, steps=steps))
    return out


def resolve_first_step(first: str, context: str) -> str:
    """The type a chain's first step resolves to in `context`, or "unknown".

    `first` is the step's name with any `(...)` already stripped. A magic scope
    of the context wins, then a global function, then a magic scope of another
    context.
    """
    magic = _MAGIC_SCOPES_BY_CONTEXT.get(context, {})
    permissive = _MAGIC_SCOPES_BY_CONTEXT["permissive"]
    if first in magic:
        return magic[first]
    if first in _GLOBAL_FUNCTIONS:
        return _GLOBAL_FUNCTIONS[first]
    if context != "permissive" and first in permissive:
        # First step is a magic scope from a different context. We don't
        # have full per-context resolution data for vanilla, so accept it
        # as the type the other context resolves it to and walk on. (If
        # this ever produces false negatives, narrow the per-context
        # tables and revisit.)
        return permissive[first]
    # Unknown first step: treat as type "unknown" and walk subsequent
    # steps without strict accessor-on-type checking. This matches the
    # engine's actual behavior (silent fallback) and keeps the audit
    # focused on its highest-value catch: known-type + wrong-accessor.
    # Common shapes that land here: capitalized magic scopes specific
    # to a system we haven't catalogued (e.g. PopsOverviewPanel) or
    # builder-style global functions we haven't registered.
    return "unknown"


def validate_chain(chain: Chain, context: str, catalog: dict[str, dict[str, str]]) -> str | None:
    """Walk the chain. Return None if every step resolves; else a one-line reason.

    The first step must be:
    - A magic scope valid in the context, OR
    - A global function name (with optional `(...)` args), OR
    - A `value`-typed terminal (rare; covers `[$X$]`-like things slipping past
      the upstream filter).

    Each subsequent step must be a valid accessor on the prior step's resolved
    type per the catalog.
    """
    if not chain.steps:
        return None
    first_full = chain.steps[0]
    first = _step_name(first_full)

    # Context-specific denials take precedence over both the magic table and the
    # permissive fallback: a scope that is bound in some other context but
    # affirmatively unbound here (issue #149).
    denied_scopes = _DENIED_SCOPES_BY_CONTEXT.get(context, {})
    if first in denied_scopes:
        return denied_scopes[first]
    denied_accessors = _DENIED_ACCESSORS_BY_CONTEXT.get(context, {})
    if denied_accessors:
        for step_full in chain.steps:
            if _step_name(step_full) in denied_accessors:
                return denied_accessors[_step_name(step_full)]

    current = resolve_first_step(first, context)

    for step_full in chain.steps[1:]:
        step = _step_name(step_full)
        if current == "unknown":
            # Permissive after an unrecognized first step.
            continue
        accessors = catalog.get(current, {})
        if step in accessors:
            current = accessors[step]
        elif current == "value":
            # Terminals can chain to formatting helpers; accept and continue.
            current = "value"
        else:
            return f"accessor '{step}' is not valid on type '{current}'"

    return None


@dataclass(frozen=True)
class ChainStep:
    """One accessor step of a chain whose receiver's type is known."""
    index: int           # position in `chain.steps`; 1 is the first accessor
    receiver: str        # the type the accessor is called on
    name: str            # the accessor, its `(...)` arguments stripped
    returns: str | None  # the catalog's return type; None when it lists none
    last: bool           # the chain ends here


def walk_chain(chain: Chain, context: str, catalog: dict[str, dict[str, str]]):
    """Yield a `ChainStep` for each step `validate_chain` checks against the
    catalog: every step after the first, until the receiver's type is lost.

    The type is lost after an unrecognized first step, after an accessor the
    catalog types `value`, and after one it doesn't list (the step
    `validate_chain` flags; it is yielded with `returns=None`). The steps after
    a `value` are the ones `validate_chain` accepts unchecked.
    """
    if not chain.steps:
        return
    current = resolve_first_step(_step_name(chain.steps[0]), context)
    last_index = len(chain.steps) - 1
    for index, step_full in enumerate(chain.steps[1:], start=1):
        if current in ("unknown", "value"):
            return
        name = _step_name(step_full)
        returns = catalog.get(current, {}).get(name)
        yield ChainStep(index, current, name, returns, index == last_index)
        if returns is None:
            return
        current = returns


# ---------------------------------------------------------------------------
# Audit orchestration
# ---------------------------------------------------------------------------

@dataclass
class AuditFlag:
    file: str
    line: int
    key: str
    chain: str
    context: str
    reason: str
    exemption: dict | None = None


@dataclass
class AuditResult:
    flags: list[AuditFlag] = field(default_factory=list)
    coverage: dict = field(default_factory=dict)
    blind: "BlindReport | None" = None  # where the check stops; `audit(blind=True)`


def parse_reviewed_comment(comment: str | None) -> dict | None:
    if not comment:
        return None
    m = _REVIEWED_RE.search(comment)
    if not m:
        return None
    return {"date": m.group("date"), "rationale": m.group("rationale").strip()}


def _collect_diplo_action_keys(common_dir: str) -> set[str]:
    """Read `common/diplomatic_actions/*.txt` and collect top-level entity keys."""
    keys: set[str] = set()
    actions_dir = os.path.join(common_dir, "diplomatic_actions")
    if not os.path.isdir(actions_dir):
        return keys
    entity_re = re.compile(r"^\s*(?:REPLACE:|INJECT:|REPLACE_OR_CREATE:)?([A-Za-z_]\w*)\s*=\s*\{")
    for fname in os.listdir(actions_dir):
        if not fname.endswith(".txt"):
            continue
        fpath = os.path.join(actions_dir, fname)
        try:
            with open(fpath, encoding="utf-8-sig") as f:
                for raw in f:
                    m = entity_re.match(raw)
                    if m:
                        keys.add(m.group(1))
        except OSError:
            continue
    return keys


def audit(
    loc_dir: str,
    *,
    common_dir: str | None = None,
    engine_docs_dir: str | None = None,
    blind: bool = False,
) -> AuditResult:
    """Run the audit on `loc_dir`. Reads catalog from `engine_docs_dir`
    and diplomatic-action key set from `common_dir` to inform context classification.

    `blind` also lists where the check stops (`result.blind`): the `value`-typed
    accessors that vanilla's loc, read from the committed snapshot, and
    `loc_dir`'s own chains continue past. It walks vanilla's 48,000 chains, about
    a second.
    """
    catalog = _load_engine_catalog(engine_docs_dir or "")
    diplo_keys = _collect_diplo_action_keys(common_dir) if common_dir else set()

    if not os.path.isdir(loc_dir):
        return AuditResult(coverage={"files_audited": 0, "chains_scanned": 0})

    lines = read_all_loc(loc_dir)
    result = audit_lines(lines, catalog, diplo_keys=diplo_keys)
    result.coverage["files_audited"] = sum(
        1 for fname in os.listdir(loc_dir)
        if fname.endswith(".yml") and os.path.isfile(os.path.join(loc_dir, fname))
    )
    if blind:
        result.blind = blind_report(lines, catalog, diplo_keys=diplo_keys)
    return result


def audit_lines(
    lines: list[LocLine],
    catalog: dict[str, dict[str, str]],
    *,
    diplo_keys: set[str] | None = None,
) -> AuditResult:
    """Validate every chain in `lines` against `catalog`. The core of `audit`,
    for loc that is not a directory of `.yml` files (the vanilla snapshot)."""
    chains_scanned = 0
    flags: list[AuditFlag] = []
    for ll in lines:
        ctx = classify_context(ll.key, diplo_action_keys=diplo_keys)
        for chain in extract_chains(ll.value):
            chains_scanned += 1
            reason = validate_chain(chain, ctx, catalog)
            if reason is not None:
                flags.append(AuditFlag(
                    file=ll.file,
                    line=ll.line,
                    key=ll.key,
                    chain=chain.raw,
                    context=ctx,
                    reason=reason,
                    exemption=parse_reviewed_comment(ll.comment),
                ))
    return AuditResult(flags=flags, coverage={"chains_scanned": chains_scanned})


def lines_from_dict(loc: dict[str, str], source: str = "vanilla_parsed") -> list[LocLine]:
    """`{key: value}` loc (the vanilla snapshot's shape) as `LocLine`s. A
    snapshot keeps no file, line or trailing comment."""
    return [LocLine(file=source, line=0, key=key, value=value) for key, value in loc.items()]


# ---------------------------------------------------------------------------
# Blind pairs: accessors the check stops at (#348)
# ---------------------------------------------------------------------------
#
# `validate_chain` accepts every step after a `value`. That is right after a
# name or a number, and wrong when the `value` typing is itself a mistake: an
# accessor that returns an object, typed `value`, switches the check off for the
# rest of every chain through it. Vanilla's loc shows which those are, since it
# chains further through them.

@dataclass
class BlindPair:
    type: str
    accessor: str
    hand_typed: bool          # typed `value` in the hand table, not by the fold
    chains: int = 0           # chains that continue past it
    example_key: str = ""
    example_chain: str = ""
    # the step names seen right after it, most used first
    continuations: dict[str, int] = field(default_factory=dict)

    @property
    def name(self) -> str:
        return f"{self.type}.{self.accessor}"


def find_blind_pairs(
    lines: list[LocLine],
    catalog: dict[str, dict[str, str]],
    *,
    diplo_keys: set[str] | None = None,
    hand_typed: dict[str, dict[str, str]] | None = None,
) -> list[BlindPair]:
    """Every `(type, accessor)` the catalog types `value` that some chain in
    `lines` continues past, most-chained first.

    Run over vanilla's loc, which the engine reads, a continuation means the
    accessor returns an object: the pair needs its real return type. `hand_typed`
    (default: this module's hand table) says which pairs were typed by hand; the
    rest came from the vanilla fold.
    """
    if hand_typed is None:
        hand_typed = HAND_TYPED_ACCESSORS
    found: dict[tuple[str, str], BlindPair] = {}
    for ll in lines:
        if "[" not in ll.value:
            continue
        ctx = classify_context(ll.key, diplo_action_keys=diplo_keys)
        for chain in extract_chains(ll.value):
            for step in walk_chain(chain, ctx, catalog):
                if step.returns != "value" or step.last:
                    continue
                pair = found.get((step.receiver, step.name))
                if pair is None:
                    pair = found[(step.receiver, step.name)] = BlindPair(
                        type=step.receiver,
                        accessor=step.name,
                        hand_typed=step.name in hand_typed.get(step.receiver, {}),
                        example_key=ll.key,
                        example_chain=chain.raw,
                    )
                pair.chains += 1
                nxt = _step_name(chain.steps[step.index + 1])
                pair.continuations[nxt] = pair.continuations.get(nxt, 0) + 1
    for pair in found.values():
        pair.continuations = dict(
            sorted(pair.continuations.items(), key=lambda kv: (-kv[1], kv[0]))
        )
    return sorted(found.values(), key=lambda p: (-p.chains, p.type, p.accessor))


# Folded pairs vanilla chains further through that are still `value`, because
# nothing says what they return: the 1.15.1 data types list no such accessor on
# the type, so the vanilla text that chains through each is most likely dead.
# {(type, accessor): why}. `test_localization_accessor_audit` holds the
# snapshot's blind folded pairs to exactly this table.
BLIND_UNDETERMINED: dict[tuple[str, str], str] = {
    ("country", "GetGovernmentData"): (
        "no `GetGovernmentData` on any type in the 1.15.1 data types (vanilla: "
        "TIME_REMAINING, CHANGE_GOVERNMENT_BUTTON, test.pre.election_tooltip)"
    ),
    ("military_formation", "GetFormationOrder"): (
        "no `GetFormationOrder` on any type in the 1.15.1 data types (vanilla: "
        "FRONT_FORMATION_ORDER_NAME, FORMATION_PANEL_CURRENT_ORDER)"
    ),
    ("state", "GetOccupier"): (
        "no `GetOccupier` on any type in the 1.15.1 data types; a State has "
        "`GetOccupant` (vanilla: TOOLTIP_STATE_OCCUPATION_MINIMAL / _PARTIAL / _FULL)"
    ),
    ("war_goal", "GetInitiator"): (
        "no `GetInitiator` on WarGoal in the 1.15.1 data types; DiplomaticPlay "
        "has one (vanilla: WAR_GOAL_WORTH)"
    ),
}

# The chains in vanilla's own loc this audit flags, and why each is vanilla's
# mistake and no catalog gap. {(loc key, chain): why}. The fold leaves a flag
# listed here alone; `test_localization_accessor_audit` holds the snapshot's
# flags to exactly this table, so a snapshot rebuild shows what changed.
KNOWN_VANILLA_FLAGS: dict[tuple[str, str], str] = {
    ("warlord_china_events.110.d",
     "SCOPE.sCharacter('prisoner_killing_warlord')GetHerselfHimself"):
        "a typo: no `.` before GetHerselfHimself",
    ("DIPLOMATIC_ACCEPTANCE_PRESTIGE_DIFFERENCE",
     "SCOPE.GetRootScope.GetCountry .GetPrestige|v"):
        "a typo: a space inside the chain",
    ("PLAYER_OBSERVER", "GetPlayer.GetShortUINameNotMeNoTooltip"):
        "no type in the 1.15.1 data types has GetShortUINameNotMeNoTooltip",
    ("OBSERVER_PLAYER_NAME", "GetPlayer.PlayerName"):
        "no type in the 1.15.1 data types has PlayerName",
    # The four below flag since #348 typed the accessor before the flagged one:
    # until then the chain was accepted unread past it.
    ("ADMIRAL_BUSY_NAVAL_INVASION", "Character.GetInvasion.GetGeneral.GetFullName"):
        "Character.GetInvasion returns an Invasion, which has no GetGeneral in "
        "the 1.15.1 data types",
    ("DIPLOMATIC_PLAY_INTEREST_MARKER_TOOLTIP",
     "DiplomaticPlay.GetInterestMarker(DiplomaticPlay.GetTarget).GetInterestStatus"):
        "DiplomaticPlay.GetInterestMarker returns an Interest, which has "
        "GetInterestStatusName and GetInterestStatusIcon and no GetInterestStatus",
    ("notification_formation_travel_deploy_to_sea_node_cancelled_name",
     "SCOPE.sProvince('province').GetName"):
        "a Province has GetSeaNodeName and no GetName in the 1.15.1 data types",
    ("notification_formation_travel_deploy_to_sea_node_cancelled_desc",
     "SCOPE.sProvince('province').GetName"):
        "a Province has GetSeaNodeName and no GetName in the 1.15.1 data types",
}


def load_vanilla_snapshot_loc(snapshot_dir: str | None = None) -> tuple[dict[str, str], str] | None:
    """`(vanilla's English loc as {key: value}, its game version)` from the
    committed `vanilla_parsed/` snapshot, or None when there is none."""
    import json
    if snapshot_dir is None:
        snapshot_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vanilla_parsed")
    try:
        with open(os.path.join(snapshot_dir, "manifest.json"), encoding="utf-8") as f:
            manifest = json.load(f)
        with open(os.path.join(snapshot_dir, manifest["localization"]["file"]),
                  encoding="utf-8") as f:
            return json.load(f), str(manifest.get("game_version") or "?")
    except (OSError, KeyError, ValueError):
        return None


@dataclass
class BlindReport:
    """Where the check goes blind: in vanilla's loc and in the mod's own."""
    vanilla_version: str | None = None      # None: no snapshot to read
    vanilla: list[BlindPair] = field(default_factory=list)
    mod: list[BlindPair] = field(default_factory=list)

    @property
    def untyped_folded(self) -> list[BlindPair]:
        """Folded pairs vanilla chains through that nobody has looked at yet:
        each needs its return type, or a line in `BLIND_UNDETERMINED`."""
        return [p for p in self.vanilla
                if not p.hand_typed and (p.type, p.accessor) not in BLIND_UNDETERMINED]


def blind_report(
    mod_lines: list[LocLine],
    catalog: dict[str, dict[str, str]],
    *,
    diplo_keys: set[str] | None = None,
    snapshot_dir: str | None = None,
) -> BlindReport:
    out = BlindReport(mod=find_blind_pairs(mod_lines, catalog, diplo_keys=diplo_keys))
    snapshot = load_vanilla_snapshot_loc(snapshot_dir)
    if snapshot is not None:
        loc, out.vanilla_version = snapshot
        out.vanilla = find_blind_pairs(lines_from_dict(loc), catalog)
    return out


# ---------------------------------------------------------------------------
# Report renderer
# ---------------------------------------------------------------------------

def render_report(result: AuditResult) -> str:
    unrev = [f for f in result.flags if not f.exemption]
    exemp = [f for f in result.flags if f.exemption]

    out = [
        "# Localization accessor audit report",
        "",
        "Auto-generated by `localization_accessor_audit.py` on every full",
        "`POST /reload` of the mod state server. Do not hand-edit.",
        "",
        "Vic3 silently drops `[X.Y.Z]` accessor chains it can't resolve,",
        "leaving an empty string in the rendered tooltip. This audit catches",
        "those statically by validating each chain against the engine's",
        "event-targets catalog and a hand-curated UI-accessor supplement.",
        "",
        "Suppress an intentional flag with a same-line comment:",
        "`# REVIEWED YYYY-MM-DD: rationale` after the loc value.",
        "",
        "## Unreviewed Flags",
        "",
    ]
    if not unrev:
        out.append("_None._")
        out.append("")
    else:
        by_file: dict[str, list[AuditFlag]] = {}
        for f in unrev:
            by_file.setdefault(f.file, []).append(f)
        for fname in sorted(by_file):
            out.append(f"### {fname} ({len(by_file[fname])})")
            out.append("")
            for f in sorted(by_file[fname], key=lambda x: x.line):
                out.append(
                    f"- `{f.file}:{f.line}` — `{f.key}` — `[{f.chain}]` — "
                    f"context `{f.context}` — {f.reason}"
                )
            out.append("")

    out.append("## Reviewed Exemptions")
    out.append("")
    if not exemp:
        out.append("_None._")
        out.append("")
    else:
        # No line number on a reviewed entry: the loc key and chain name it,
        # and an edit above it would otherwise churn the report.
        for f in sorted(exemp, key=lambda x: (x.file, x.line)):
            out.append(
                f"- `{f.file}` — `{f.key}` — `[{f.chain}]` — "
                f"{f.exemption['date']}: {f.exemption['rationale']}"
            )
        out.append("")

    if result.blind is not None:
        out += _render_blind(result.blind)

    # Flag counts only: the file / chain counts stay in `result.coverage`
    # (and the regenerate() summary) but move with unrelated loc.
    out.append("## Coverage")
    out.append("")
    out.append(f"- total flags: {len(result.flags)}")
    out.append(f"- unreviewed: {len(unrev)}")
    out.append(f"- exempted: {len(exemp)}")

    return "\n".join(out) + "\n"


def _blind_line(pair: BlindPair, note: str = "") -> str:
    # Names only, no counts: a count moves with unrelated loc.
    then = ", ".join(f"`{name}`" for name in sorted(pair.continuations))
    return f"- `{pair.name}`, then {then}" + (f": {note}" if note else "")


def _render_blind(blind: BlindReport) -> list[str]:
    out = [
        "## Where the check stops",
        "",
        "Every step after an accessor typed `value` is accepted unread. That is",
        "right after a name or a number. An accessor that returns an object and",
        "is typed `value` all the same switches the check off for the rest of",
        "each chain through it. Vanilla's loc shows which those are: the engine",
        "reads it, so an accessor it chains further through returns an object.",
        "",
    ]
    if blind.vanilla_version is None:
        out += ["_No `vanilla_parsed/` snapshot to read vanilla's chains from._", ""]
    else:
        untyped = blind.untyped_folded
        undetermined = [p for p in blind.vanilla
                        if not p.hand_typed and (p.type, p.accessor) in BLIND_UNDETERMINED]
        hand = [p for p in blind.vanilla if p.hand_typed]
        out += [f"### Vanilla {blind.vanilla_version} chains further through", ""]
        if untyped:
            out += [
                f"**Folded as `value`, to be typed ({len(untyped)}).** Give each its return type",
                "in `_BUILTIN_ACCESSORS_BY_TYPE` and rerun",
                "`scripts/generators/fold_vanilla_loc_accessors.py`, or record why it",
                "can't be typed in `BLIND_UNDETERMINED`.",
                "",
            ]
            out += [_blind_line(p) for p in sorted(untyped, key=lambda p: p.name)]
            out.append("")
        out += [
            f"**Folded as `value`, undetermined ({len(undetermined)}).** Nothing says what these",
            "return, so they stay as the fold left them.",
            "",
        ]
        out += [_blind_line(p, BLIND_UNDETERMINED[(p.type, p.accessor)])
                for p in sorted(undetermined, key=lambda p: p.name)] or ["_None._"]
        out += [
            "",
            f"**Typed `value` by hand ({len(hand)}).** The catalog has no type for what",
            "these return, or had none when they were written.",
            "",
        ]
        out += [_blind_line(p) for p in sorted(hand, key=lambda p: p.name)] or ["_None._"]
        out.append("")
    out += ["### The mod's own chains past a `value`", ""]
    out += [_blind_line(p) for p in sorted(blind.mod, key=lambda p: p.name)] or ["_None._"]
    out.append("")
    return out


# ---------------------------------------------------------------------------
# Server post-load hook
# ---------------------------------------------------------------------------

def regenerate(mod_state) -> dict:
    """Run the audit and write `docs/engine/localization_accessor_report.md`.

    Returns a summary dict matching the POST_LOAD_GENERATORS protocol.
    """
    from path_constants import mod_path
    loc_dir = os.path.join(mod_path, "localization", "english")
    common_dir = os.path.join(mod_path, "common")
    engine_docs_dir = os.path.join(mod_path, "docs", "engine")

    result = audit(loc_dir, common_dir=common_dir, engine_docs_dir=engine_docs_dir, blind=True)
    report = render_report(result)
    out_path = os.path.join(mod_path, "docs", "engine", "localization_accessor_report.md")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(report)

    unrev = sum(1 for f in result.flags if not f.exemption)
    exemp = sum(1 for f in result.flags if f.exemption)
    return {
        "files_audited": result.coverage.get("files_audited", 0),
        "chains_scanned": result.coverage.get("chains_scanned", 0),
        "total_flags": len(result.flags),
        "unreviewed": unrev,
        "exempted": exemp,
        # Folded accessors vanilla chains further through that nobody has typed:
        # the catalog is behind the vanilla snapshot. A reload warns on it.
        "catalog_stale": len(result.blind.untyped_folded),
        "blind_pairs_vanilla": len(result.blind.vanilla),
        "blind_pairs_mod": len(result.blind.mod),
    }


# ---------------------------------------------------------------------------
# Standalone CLI
# ---------------------------------------------------------------------------

def _main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--loc-dir",
        default=None,
        help="Localization directory to scan (default: mod's localization/english/).",
    )
    parser.add_argument(
        "--common-dir",
        default=None,
        help="common/ directory for entity-key context hints (default: mod's).",
    )
    parser.add_argument(
        "--engine-docs-dir",
        default=None,
        help="docs/engine/ directory for catalog source (default: mod's).",
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Print the markdown report to stdout (in addition to summary).",
    )
    parser.add_argument(
        "--blind",
        action="store_true",
        help="List the `value`-typed accessors that vanilla's chains (from "
             "vanilla_parsed/) and the scanned loc's own continue past, where "
             "the check stops. Always part of --report.",
    )
    args = parser.parse_args()

    from path_constants import mod_path

    loc_dir = args.loc_dir or os.path.join(mod_path, "localization", "english")
    common_dir = args.common_dir or os.path.join(mod_path, "common")
    engine_docs_dir = args.engine_docs_dir or os.path.join(mod_path, "docs", "engine")

    if not os.path.isdir(loc_dir):
        print(f"Error: loc-dir does not exist: {loc_dir}")
        return 2

    result = audit(loc_dir, common_dir=common_dir, engine_docs_dir=engine_docs_dir,
                   blind=args.report or args.blind)

    if args.report:
        print(render_report(result))
    elif args.blind:
        print("\n".join(_render_blind(result.blind)))

    unrev = sum(1 for f in result.flags if not f.exemption)
    exemp = sum(1 for f in result.flags if f.exemption)
    print(
        f"\n{loc_dir}: "
        f"files={result.coverage.get('files_audited', 0)} "
        f"chains={result.coverage.get('chains_scanned', 0)} "
        f"flags={len(result.flags)} unreviewed={unrev} exempted={exemp}"
    )
    if result.blind is not None and result.blind.untyped_folded:
        print(
            f"{len(result.blind.untyped_folded)} folded accessor(s) that vanilla chains "
            "further through are still typed `value`: see \"Where the check stops\"."
        )
    return 0 if unrev == 0 else 1


if __name__ == "__main__":
    raise SystemExit(_main())
