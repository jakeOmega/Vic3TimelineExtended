# Plan: "Multilateral Institutions" Diplomatic principle group (+ Foreign Service rename)

**Branch:** `claude/diplomatic-principle-groups-4puwcu`
**Status:** **Phase 1 implemented** (statically validated; live reload/audit + in-game smoke test
still owed — the cloud container has no base-game install / mod state server). Phase 2 blocked on
the `un_authority` global-variable fix
(`docs/superpowers/plans/2026-07-06-un-authority-global-variable-fix.md`, in progress in a
separate session).

**Resolved open decisions:** (a) Tier II ships as an inert stub per request (restates Tier I only);
(b) `power_bloc_disallow_war_bool` confirmed = "Cannot start or join wars amongst Power Bloc
members" (member-vs-member — intended); (c) icon = `foreign_investment.dds` (reused).
**Correction applied during build:** collective defense uses the country modifier
`country_join_power_bloc_member_in_defensive_plays_bool` (in `member_modifier`), not the
nonexistent `power_bloc_member_in_defensive_plays_bool` — the latter was a regex-substring
artifact. `power_bloc_disallow_war_bool` stays in `power_bloc_modifier`.

Adds a third primary principle group to `identity_diplomatic` (alongside Foreign Service and
Global Security): the UN-integration / rules-based-order build. Also relocalizes the existing
`principle_group_diplomacy` display name to **"Foreign Service"** (key unchanged).

All modifier names below were validated against `docs/engine/modifiers_summary.txt` and the
existing treaty-article / principle idioms unless marked **NEW** (to be registered) or
**VERIFY**.

---

## Phasing

**Phase 1 (now — no `un_authority` dependency):** Foreign Service rename; the group + identity
wiring; Tiers I, III, IV, V; the new treaty article; the `join_united_nations` gate; modifier
registrations; tech gating; loc. **Tier II ships as an inert stub** (structurally valid, no
gameplay modifiers, `# TODO(un-authority-fix)` marker).

**Phase 2 (after the UN global-var fix merges):** the `country_un_institutional_alignment` scaler,
the `un_authority_drift_institutional` feed, the authority-scaled member benefit, and Tier II's
real body. See "Phase 2" at the end. The other session will provide the branch/PR to build against.

---

## 1. Foreign Service rename (loc only, key unchanged)

`localization/english/te_diplomacy_l_english.yml`:
- `principle_group_diplomacy:0 "Diplomacy"` → `"Foreign Service"`
- Optionally reword `principle_group_diplomacy_desc` to match (foreign-service framing).

Keep the key `principle_group_diplomacy` and all `principle_diplomacy_N` keys — no save break.
The `GetPowerBlocPrincipleGroup('principle_group_diplomacy').GetName` dynamic refs auto-update.
Run `python organize_loc.py` after.

---

## 2. Group definition + identity wiring

`common/power_bloc_principle_groups/extra_power_bloc_principle_groups.txt` — append:

```
principle_group_multilateral_institutions = {
	primary_for_identity = identity_diplomatic
	unlocking_identity = identity_diplomatic

	levels = {
		principle_multilateral_institutions_1
		principle_multilateral_institutions_2
		principle_multilateral_institutions_3
		principle_multilateral_institutions_4
		principle_multilateral_institutions_5
	}
}
```

No change to `extra_power_bloc_identities.txt` — the identity doesn't enumerate its groups; the
group declares `primary_for_identity`. (Precedent: `identity_cultural` already has three primary
groups, so a third diplomatic primary is fine.)

---

## 3. Tier-by-tier design

Follow the **cumulative-restatement convention** (see `principle_diplomacy_*`): each tier's
`*_modifier` block restates all lower tiers' lines plus its own, since the engine applies only the
highest enacted tier. Icons: reuse an existing principles icon (e.g.
`gfx/interface/icons/principles_icons/ideological_truth.dds`, or `dedicated_police.dds` — a custom
icon can come later); backgrounds follow the `principle_tier_1 / _2 / _3 / _3 / _3` pattern used by
`principle_diplomacy_*` for levels 1–5.

Tech gates use the **`_pb_principles_bool` convention** (like `principle_global_security_*` gating
on `country_nuclear_weapons_pb_principles_bool`): a tech grants a country bool, the principle's
`possible` checks `modifier:<bool> = yes`. Three bools (§5) drive: group entry (IGO), Tier IV
(decolonization), Tier V (anti-war movement).

### Tier I — Charter Signatories
```
member_modifier = {
	country_diplomatic_reputation_add = 5
	country_influence_mult = 0.1
}
power_bloc_modifier = {
	power_bloc_can_use_join_united_nations_bool = yes   # NEW bool (§5)
}
possible = { modifier:country_intergovernmental_organizations_pb_principles_bool = yes }  # NEW (§6)
visible = { has_dlc_feature = power_bloc_features }
```
Unlocks the bloc's ability to bind others into the UN (the `join_united_nations` article, now
gated — §4).

### Tier II — Standing Delegation  *(Phase 1: INERT STUB)*
Phase 1 body: valid principle, **no gameplay modifiers**, `# TODO(un-authority-fix): institutional
alignment scaler + MoFA delegation land in Phase 2`. Restates Tier I's `member_modifier` per the
cumulative convention (so enacting II doesn't drop I's rep/influence).
> Recommendation: even in Phase 1 it's reasonable to give II the authority-independent half of its
> identity now — `institution = institution_ministry_of_foreign_affairs` + a small
> `institution_modifier` (e.g. `country_lobby_leverage_generation_mult = 0.1`) — so the tier isn't
> literally empty during playtesting. Flagged as an open decision (§10-a).

### Tier III — Development Assistance
```
power_bloc_modifier = {
	power_bloc_can_give_development_aid_bool = yes       # NEW bool (§5)
}
# restates Tier I member_modifier
```
Payload is the new `development_assistance` treaty article (§4). Patronage, not charity: the source
funds the target's poor and gets leverage + a compliant client in return.

### Tier IV — Collective Arbitration
```
possible = { modifier:country_decolonization_pb_principles_bool = yes }   # NEW (§6), era-6 modern tech
power_bloc_modifier = {
	power_bloc_disallow_war_bool = yes            # VERIFY semantics: members can't war fellow members
	power_bloc_member_in_defensive_plays_bool = yes
	power_bloc_can_give_development_aid_bool = yes   # cumulative
}
member_modifier = {
	country_diplomatic_reputation_add = 5           # cumulative
	country_influence_mult = 0.1                     # cumulative
	country_infamy_generation_mult = -0.1            # acting through the international body
}
```
Enforced intra-bloc peace + collective defense. (An active "condemn aggressor" tool is deferred —
it fits better as a Phase 2 authority-linked effect.)

### Tier V — Guarantor of the Order
```
possible = { modifier:country_anti_war_movement_pb_principles_bool = yes }  # NEW (§6), era-7 modern tech
power_bloc_modifier = {
	power_bloc_disallow_war_bool = yes                       # cumulative
	power_bloc_member_in_defensive_plays_bool = yes          # cumulative
	power_bloc_can_give_development_aid_bool = yes            # cumulative
	power_bloc_cohesion_per_member_add = 1                   # cancels identity_diplomatic's built-in -1/member drag
	power_bloc_target_sway_cost_mult = -0.2                  # cheaper to pull members in
	power_bloc_invite_acceptance_minor_power_add = 20
	power_bloc_invite_acceptance_insignificant_power_add = 20
	power_bloc_invite_acceptance_major_power_add = 10
}
# restates cumulative member_modifier (rep, influence, infamy)
```
Big, cohesive, magnetic institutional bloc. Deliberately **not** `country_leverage_resistance_add`
(that grants independence from all blocs incl. its own leader — wrong lever; cohesion is the
membership-retention mechanism).

---

## 4. Treaty articles

`common/treaty_articles/extra_treaty_articles.txt`:

**(a) Gate the existing `join_united_nations`** — add to its `visible` block:
```
power_bloc ?= { modifier:power_bloc_can_use_join_united_nations_bool = yes }
is_power_bloc_leader = yes
```
(Currently visible to any UN member. This is the intended clean gate — only a bloc with Tier I can
force others into the UN by treaty. Confirmed acceptable; non-bloc members lose the tool.)

**(b) New article `development_assistance`** (mirror `healthcare_aid` / `security_aid` structure):
```
kind = directed
maintenance_paid_by = source_country
cost = 150
relations_progress_per_day = 3
relations_improvement_max = 30

source_modifier = {
	country_authority_cost_add = 50            # the expense of running the program
}
target_modifier = {
	state_lower_strata_standard_of_living_add = 2    # the poverty-focused payload
	country_liberty_desire_add = -0.1                # buys a compliant client
	country_colonial_stability_drift_add = 0.1       # firms up the target's hold on its own subjects
	country_treaty_leverage_generation_add = 200     # client dependence → leverage for the source
}
usage_limit = once_per_side
visible = { power_bloc ?= { modifier:power_bloc_can_give_development_aid_bool = yes } }
possible = {
	country_rank > scope:other_country.country_rank
	# target has a poor lower strata — mirror the aid-article possible checks
}
can_ratify = { <DUPLICATE_ARTICLE_SAME_INPUTS guard, per idiom> }
ai = { <mirror healthcare_aid: offer; hostile-attitude / same-bloc / low-SoL scoring> }
```
Self-interest is in `country_treaty_leverage_generation_add` + `country_liberty_desire_add`, so no
altruism is assumed — works for a fascist bloc leader.

---

## 5. New `power_bloc_*` bool registrations

`common/modifier_type_definitions/power_bloc_extra_modifier_types.txt` — two new bools (copy the
existing `{ color = neutral; boolean = yes; game_data = { ai_value = 100 }; script_only = yes }`
template):
- `power_bloc_can_use_join_united_nations_bool`
- `power_bloc_can_give_development_aid_bool`

---

## 6. Tech-gate bools (`_pb_principles_bool` convention)

Register three country bools (in `common/modifier_type_definitions/tech_gate_modifier_types.txt`,
following the existing `country_*_pb_principles_bool` entries), grant each in the tech's
`modifier = { }` block, and regenerate unlock descriptions:

| Bool | Granted by tech | Era | Gates |
|---|---|---|---|
| `country_intergovernmental_organizations_pb_principles_bool` | `intergovernmental_organizations` | 6 | group entry (all tiers) |
| `country_decolonization_pb_principles_bool` | `decolonization` | 6 | Tier IV |
| `country_anti_war_movement_pb_principles_bool` | `anti_war_movement` | 7 | Tier V |

Unlock-desc loc is produced by `gen_pb_principle_unlock_descs.py` (auto-runs on `POST /reload`);
verify it picks up the new bools, else add loc by hand. (VERIFY the generator's discovery mechanism
during implementation.)

---

## 7. Localization keys to add

`localization/english/te_power_blocs_l_english.yml` (or `te_diplomacy_l_english.yml` — match
whichever holds the sibling group; global_security lives in `te_power_blocs`):
- `principle_group_multilateral_institutions` (name) + `_desc`
- `principle_multilateral_institutions_1_desc` … `_5_desc`
- Bool descs: `power_bloc_can_use_join_united_nations_bool_desc`,
  `power_bloc_can_give_development_aid_bool_desc`
- `development_assistance` article: name + `_desc` + effect tooltips (match the aid-article loc
  file/keys)
- Tech-gate bool `_desc` keys if not auto-generated

Run `python organize_loc.py`. Check `docs/engine/loc_coverage_report.md` after reload for missing
keys.

---

## 8. Phase 2 (deferred — after the `un_authority` global-var fix)

Cross-ref: `docs/superpowers/plans/2026-07-06-un-authority-global-variable-fix.md`.

1. **Register** `country_un_institutional_alignment` (script_only, additive scaler).
2. **Grant** it on the principle, cumulative by tier — Tier II `= 0.25`, III `= 0.3`, IV `= 0.4`,
   V `= 0.5` (tune later).
3. **Feed authority:** add `un_authority_drift_institutional` to `un_script_values.txt` — sum over
   members of `modifier:country_un_institutional_alignment × rank_weight` — and add it to the
   global monthly updater's drift total. Rank-weighting is what stops many small members from
   inflating authority.
4. **Feed off authority:** in the UN JE benefit application, layer the member's benefit magnitude
   × `(1 + modifier:country_un_institutional_alignment)` (0.5 → +50%), scaled by the now-global
   `un_authority` via the existing `add_modifier { multiplier = … }` pattern.
5. **Tier II real body:** replace the inert stub with Standing Delegation (MoFA institution if not
   already added in Phase 1, + the alignment grant).
6. Optional: give Tier IV a "condemn aggressor" active tool that also nudges global authority.

---

## 9. Build + verify

1. Edit files above; `python scripts/format_paradox_tabs.py <brace files>`.
2. `python organize_loc.py`.
3. Restart/reload the mod state server:
   `.venv/bin/python mod_state_server.py` then
   `curl -X POST 'http://localhost:8950/reload'` — **check the `warnings` array** and
   `docs/engine/{loc_coverage,modifier_visibility}_report.md`.
4. Validate the new bools registered: `/modifier-search?q=power_bloc_can_use_join_united_nations`,
   `?q=power_bloc_can_give_development_aid`.
5. In-game smoke test: diplomatic bloc → group appears as a diplomatic primary → Tier I unlocks the
   UN-join article → Tier III unlocks development aid → Tier IV blocks intra-bloc war → Tier V
   cohesion offsets the identity drag.

---

## 10. Open decisions

- **(a) Tier II in Phase 1:** truly inert stub (user's stated preference), or give it the
  authority-independent MoFA institution now so it isn't empty during playtesting? (Recommend the
  latter; low cost, no `un_authority` dependency.)
- **(b) `power_bloc_disallow_war_bool` semantics** — confirm via engine docs it blocks
  member-vs-member war (intended) and not all member wars, before shipping Tier IV.
- **(c) Icon** — reuse an existing principles icon for Phase 1, or commission a custom one.
