"""Static-analysis audit for localization accessor chains.

Vic3 silently drops `[X.Y.Z]` accessor chains it can't resolve, replacing
them with the empty string. The bug only surfaces by hovering the in-game
UI. This audit scans every `localization/english/*.yml` value, extracts
each `[…]` chain, and flags any chain whose first step or any intermediate
step is unresolvable in the relevant rendering context.

Strict mode by default. The catalog is bootstrapped from vanilla loc by
running the audit against the vanilla install and folding every flag back
into the per-context magic-scope tables / accessor tables — vanilla loc
is engine-validated by definition, so any vanilla flag is a catalog gap.

Suppress an intentional flag with a same-line comment in the format:

    unusual_loc_key:0 "Some text [WeirdScope.GetX]"  # REVIEWED 2026-05-08: rationale

Standalone CLI:

    python3 localization_accessor_audit.py [--loc-dir PATH]

Default `--loc-dir` is the mod's `localization/english/`. Aim it at the
vanilla install during the bootstrap phase:

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
    "Battle": "value",
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
        "GetModifier": "value",
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
        # Scope helpers used in chains
        "MakeScope": "scope_object",
        "ScriptValue": "value",
        "Var": "value",
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
        "sInterestGroup": "interest_group",
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
        "sGetEnemy": "country",
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
    },
    "state": {
        "Self": "state",
        "GetName": "value",
        "GetNameNoFormatting": "value",
        "GetCityHubName": "value",
        "GetFarmHubName": "value",
        "GetCountry": "country",
        "GetOwner": "country",
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
    },
    "state_region": {
        "Self": "state_region",
        "GetName": "value",
        "GetNameNoFormatting": "value",
        "GetStrategicRegion": "strategic_region",
        "GetCityHubName": "value",
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
        "MakeScope": "scope_object",
    },
    "culture": {
        "Self": "culture",
        "GetName": "value",
        "GetNameNoFormatting": "value",
        "GetNamePlural": "value",
        "GetCollectiveNoun": "value",
        "GetCustom": "value",
        "MakeScope": "scope_object",
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
        "GetModifier": "value",
        "GetCustom": "value",
        "GetTooltipTag": "value",
    },
    "law": {
        "Self": "law",
        "GetName": "value",
        "GetNameNoFormatting": "value",
        "GetDescription": "value",
        "GetTooltipTag": "value",
        "GetCountry": "country",
        "GetGroup": "value",
    },
    "diplomatic_play": {
        "Self": "diplomatic_play",
        "GetName": "value",
        "GetInitiator": "country",
        "GetTarget": "country",
        "GetWargoal": "war_goal",
    },
    "diplomatic_action": {
        "Self": "diplomatic_action",
        "GetName": "value",
        "GetSecondCountry": "country",
        "GetFirstCountry": "country",
    },
    "war_goal": {
        "Self": "war_goal",
        "GetName": "value",
        "GetTarget": "country",
        "GetTargetState": "state",
        "GetHolder": "country",
    },
    "war_goal_draft": {
        "Self": "war_goal_draft",
        "GetName": "value",
        "GetTarget": "country",
        "GetTargetState": "state",
        "GetHolder": "country",
        "GetCountry": "country",
        "GetWarGoalStakeholder": "country",
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
    },
    "political_movement": {
        "Self": "political_movement",
        "GetName": "value",
        "GetNameNoFormatting": "value",
        "GetType": "value",
        "GetCivilWar": "value",
        "GetTooltipTag": "value",
    },
    "strategic_region": {
        "Self": "strategic_region",
        "GetName": "value",
    },
    "treaty": {
        "Self": "treaty",
        "GetName": "value",
    },
    "war": {
        "Self": "war",
        "GetName": "value",
        "GetDiplomaticPlay": "diplomatic_play",
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
    },
    "party": {
        "Self": "party",
        "GetName": "value",
        "GetNameNoFormatting": "value",
        "GetLeader": "character",
        "GetCountry": "country",
        "GetMembersSummary": "value",
    },
    "company": {
        "Self": "company",
        "GetName": "value",
        "GetNameNoFormatting": "value",
        "GetCountry": "country",
        "GetType": "value",
    },
    "political_lobby": {
        "Self": "political_lobby",
        "GetName": "value",
        "GetNameNoFormatting": "value",
        "GetType": "value",
        "GetCountry": "country",
    },
    "diplomatic_pact": {
        "Self": "diplomatic_pact",
        "GetFirstCountry": "country",
        "GetSecondCountry": "country",
    },
    "treaty_article": {
        "Self": "treaty_article",
        "GetName": "value",
    },
    "market": {
        "Self": "market",
        "GetName": "value",
        "GetCountry": "country",
        "GetGoods": "market_goods",
        "GetOwner": "country",
    },
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


_MAGIC_SCOPES_BY_CONTEXT["permissive"] = _build_permissive_scopes()


# Vanilla-extracted accessors. Generated once from a vanilla loc audit pass.
# Most are terminal `value`-returning UI accessors that don't appear in the
# engine's event-targets log. The type-changing entries (e.g. GetRuler ->
# character) are kept in the manually curated `_BUILTIN_ACCESSORS_BY_TYPE`
# above; this file only adds value-returning long-tail entries on top.
try:
    from localization_accessor_vanilla_extras import VANILLA_EXTRACTED_ACCESSORS
    for _typ, _accessors in VANILLA_EXTRACTED_ACCESSORS.items():
        target = _BUILTIN_ACCESSORS_BY_TYPE.setdefault(_typ, {})
        for _acc, _ret in _accessors.items():
            target.setdefault(_acc, _ret)
except ImportError:
    # vanilla_extras not present (e.g. fresh checkout, or running without
    # the bootstrap). Audit still works; just with the smaller curated catalog.
    pass


# ---------------------------------------------------------------------------
# Catalog from engine docs
# ---------------------------------------------------------------------------

def _load_engine_catalog(engine_docs_dir: str) -> dict[str, dict[str, str]]:
    """Parse `event_targets_summary.txt` into `{scope_type: {accessor: return_type}}`.

    Augmented with `_BUILTIN_ACCESSORS_BY_TYPE`. The result is the spine of
    chain validation: at any point in a walk we look up
    `catalog[current_type][next_step]` to learn the next type.
    """
    catalog: dict[str, dict[str, str]] = {
        typ: dict(accessors) for typ, accessors in _BUILTIN_ACCESSORS_BY_TYPE.items()
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
    # Diplomatic-action-related keys: the action name AND its standard suffixes.
    for suffix in (
        "", "_desc", "_action_name", "_action_propose_name",
        "_action_notification_name", "_action_notification_desc",
        "_action_break_name", "_action_notification_break_name",
        "_action_notification_break_desc",
        "_proposal_accepted_name", "_proposal_accepted_desc",
        "_proposal_declined_name", "_proposal_declined_desc",
        "_proposal_notification_name", "_proposal_notification_desc",
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

    magic = _MAGIC_SCOPES_BY_CONTEXT.get(context, {})
    permissive = _MAGIC_SCOPES_BY_CONTEXT["permissive"]

    if first in magic:
        current = magic[first]
    elif first in _GLOBAL_FUNCTIONS:
        current = _GLOBAL_FUNCTIONS[first]
    elif context != "permissive" and first in permissive:
        # First step is a magic scope from a different context. We don't
        # have full per-context resolution data for vanilla, so accept it
        # as the type the other context resolves it to and walk on. (If
        # this ever produces false negatives, narrow the per-context
        # tables and revisit.)
        current = permissive[first]
    else:
        # Unknown first step: treat as type "unknown" and walk subsequent
        # steps without strict accessor-on-type checking. This matches the
        # engine's actual behavior (silent fallback) and keeps the audit
        # focused on its highest-value catch: known-type + wrong-accessor.
        # Common shapes that land here: capitalized magic scopes specific
        # to a system we haven't catalogued (e.g. PopsOverviewPanel) or
        # builder-style global functions we haven't registered.
        current = "unknown"

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
) -> AuditResult:
    """Run the audit on `loc_dir`. Reads catalog from `engine_docs_dir`
    and diplomatic-action key set from `common_dir` to inform context classification.
    """
    catalog = _load_engine_catalog(engine_docs_dir or "")
    diplo_keys = _collect_diplo_action_keys(common_dir) if common_dir else set()

    files_audited = 0
    chains_scanned = 0
    flags: list[AuditFlag] = []

    if not os.path.isdir(loc_dir):
        return AuditResult(coverage={"files_audited": 0, "chains_scanned": 0})

    for fname in sorted(os.listdir(loc_dir)):
        if not fname.endswith(".yml"):
            continue
        fpath = os.path.join(loc_dir, fname)
        if not os.path.isfile(fpath):
            continue
        files_audited += 1
        for ll in read_loc_file(fpath):
            ctx = classify_context(ll.key, diplo_action_keys=diplo_keys)
            for chain in extract_chains(ll.value):
                chains_scanned += 1
                reason = validate_chain(chain, ctx, catalog)
                if reason is not None:
                    flag = AuditFlag(
                        file=fname,
                        line=ll.line,
                        key=ll.key,
                        chain=chain.raw,
                        context=ctx,
                        reason=reason,
                        exemption=parse_reviewed_comment(ll.comment),
                    )
                    flags.append(flag)

    return AuditResult(
        flags=flags,
        coverage={"files_audited": files_audited, "chains_scanned": chains_scanned},
    )


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
        for f in sorted(exemp, key=lambda x: (x.file, x.line)):
            out.append(
                f"- `{f.file}:{f.line}` — `{f.key}` — `[{f.chain}]` — "
                f"{f.exemption['date']}: {f.exemption['rationale']}"
            )
        out.append("")

    out.append("## Coverage")
    out.append("")
    for k, v in result.coverage.items():
        out.append(f"- {k}: {v}")
    out.append(f"- total flags: {len(result.flags)}")
    out.append(f"- unreviewed: {len(unrev)}")
    out.append(f"- exempted: {len(exemp)}")

    return "\n".join(out) + "\n"


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

    result = audit(loc_dir, common_dir=common_dir, engine_docs_dir=engine_docs_dir)
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
    args = parser.parse_args()

    from path_constants import mod_path

    loc_dir = args.loc_dir or os.path.join(mod_path, "localization", "english")
    common_dir = args.common_dir or os.path.join(mod_path, "common")
    engine_docs_dir = args.engine_docs_dir or os.path.join(mod_path, "docs", "engine")

    if not os.path.isdir(loc_dir):
        print(f"Error: loc-dir does not exist: {loc_dir}")
        return 2

    result = audit(loc_dir, common_dir=common_dir, engine_docs_dir=engine_docs_dir)

    if args.report:
        print(render_report(result))

    unrev = sum(1 for f in result.flags if not f.exemption)
    exemp = sum(1 for f in result.flags if f.exemption)
    print(
        f"\n{loc_dir}: "
        f"files={result.coverage.get('files_audited', 0)} "
        f"chains={result.coverage.get('chains_scanned', 0)} "
        f"flags={len(result.flags)} unreviewed={unrev} exempted={exemp}"
    )
    return 0 if unrev == 0 else 1


if __name__ == "__main__":
    raise SystemExit(_main())
