> Survey of branch feat/gm-sites-world-wealth at 823dc25c (2026-10-18), read-only. Line numbers drift as the plan lands; search by name.

# Inventory A: building level reads, rebuilds, freeze/beside, building definition, seeding, .1 (2026-10-18)

Key: GE=gm_effects.txt ME=gm_monument_effects.txt TE=gm_trophy_effects.txt CE=gm_commission_effects.txt AE=gm_archaeology_effects.txt LE=gm_landmark_effects.txt (all common/scripted_effects/); LAD=common/scripted_effects/te_construction_market_build_effects.txt; GV=gm_values.txt MV=gm_monument_values.txt TV=gm_trophy_values.txt CV=gm_commission_values.txt (common/script_values/); MT=monument_triggers.txt GT=gm_monument_triggers.txt CT=gm_commission_triggers.txt TT=gm_trophy_triggers.txt (common/scripted_triggers/); SG=common/scripted_guis/gm_sguis.txt; EV=events/monument_events.txt; B=common/buildings/grand_monuments.txt

## 1. Level reads
- gm_state_level GV:114 (b:building_grand_monument.level or 0) — changes: finished always 1; site needs its own read.
- gm_state_secondary_levels MV:24 — sum of records; rebuild role goes. gm_state_primary_levels MV:39 (building − secondaries, min 1) — point at gm_levels record. gm_mon_levels MV:14 keeps.
- gm_state_primary_grandeur MV:112, gm_mon_grandeur MV:77 — starting grandeur + age. gm_state_grandeur GV:125 keeps.
- gm_state_age_step GV:456 / gm_mon_age_step MV:61 — 2% of starting grandeur.
- gm_evt_grandeur GV:488 / gm_mon_evt_grandeur MV:204 (anniversary adds a tenth of levels, min 1) — base unspecified by spec.
- gm_state_rededicate_cost GV:750 keeps (reads record). gm_state_tr_levels/_age/_value/_whole/_levels_left TV:24-66; gm_mon_tr_levels/_age/_whole MV:151-177 — add starting-grandeur share. gm_tr_infamy TV:99 → grandeur taken.
- gm_com_fit_grandeur CV:15; gm_com_levels_to_go, gm_disp_com_raise_cost, gm_disp_com_accept_cost CV:136/150/156 — grandeur; levels = missing grandeur ÷ rate.
- gm_state_monument_count MV:118 (+1 building, + containers; ai_value + six limit) — must count a site.
- gm_state_shadow_levels MV:229 records only; gm_state_unexplained_levels MV:243 (11 uses), gm_state_levels_short MV:270, gm_state_split_short MV:289, gm_state_disp_split_levels MV:371 — go. gm_disp_rebuild_asked GV:465 go. gm_state_disp_frozen GV:475 ("Finished" line) changes. gm_status_code GV:137 (1 = undedicated → 1 = a site).
- Direct reads: Dedicate button gm_state_level >= 1 SG:126 (moves to site); gm_state_has_new_levels MT:319 (goes); gm_state_short_unexplained GT:844 (goes); gm_state_record_frozen_levels GE:325 (goes); Rededicate arithmetic GE:1560-1563; gm_state_start_ceremony writes gm_ceremony_level GE:1645 (site); gm_state_offer_missed_ceremony GE:1670 (site); gm_state_dedicate writes gm_levels GE:1928 (records the site's levels); .2 immediate EV:185 (site); gm_state_tr_add_levels TE:572 (goes); gm_state_tr_remove_piece TE:292, gm_state_tr_rebuild_from_moving TE:602; gm_state_promote_secondary ME:232; found_beside log ME:313; gm_state_swap_primary ME:750; gm_state_tr_shrink_by ME:1149; split/piece/short ME:1943/2147/2268; rebuild self-check ME:2487.
- Loc reading gm_state_primary_levels: te_miscellaneous_l_english.yml 2851, 3585, 3586, 3592, 3800, 3801, 3961, 3962; te_events_l_english.yml:2986 (monument_trophy_events.1.d). GUI via gm_state_disp_frozen te_state_panel_widgets.gui:727, grand_monuments_widget.gui:1408.

## 2. Rebuilds
- te_construction_market_build_specified_level LAD:80 (cases to :1286; GM added 101-200, comment LAD:78). Non-GM callers extra_effects.txt:92 (wonders), :915 (nuclear), te_construction_market_direct_effects.txt:48/221/230/238, extra_on_actions.txt:3134-3194 — keep shared.
- max = 200 clamps GE:1564, TE:293/574/603, ME:233/1152 — go.
- gm_state_rededicate GE:1536 (Rededicate button SG:60, monument_events.17 EV:2031, AI GE:1810, beside ME:711): guard gm_rededicate_click; remove building, gm_clear_state(KEEP_LANDMARK), rebuild ceil(primary/2)+secondaries, halve age, gm_rebuilding, start ceremony — changes: records, no rebuild; needs a re-dedication path.
- gm_state_tear_down GE:1508 (remove + clear + promote) — keeps remove; promote changes.
- gm_state_promote_secondary ME:209 (from tear-down, whole taking TE:277, gm_monument_pass when building lost ME:113-119; rebuilds via rebuild_from_moving) — records move; building created/kept at 1.
- gm_state_tr_rebuild_from_moving TE:594 (from tr_receive, promote) — create at 1 + records.
- gm_state_tr_receive TE:531 (trophy home TE:489; dig placed in state with no building AE:667) — changes.
- gm_state_tr_add_levels TE:560 (callers TE:534, ME:905/933/1232/1838/2188/2290, AE:734; marks gm_restore_pm, rebuild at level + incoming) — goes.
- gm_state_tr_remove_piece TE:285 (from gm_state_tr_take TE:108) — records only. gm_state_tr_remove_whole TE:263 — keeps.
- gm_state_tr_shrink_by ME:1131 (Pull Down beside ME:690, container taken whole ME:1038 / part ME:1110) — goes.
- gm_state_run_mon_orders ME:654 / .30 EV:1708 — no rebuild, no wait.
- one-rebuild-a-day ME:656, TE:464, ME:1497/1530/1622, AE:485 — go. gm_tr_return_queued / _relations TE:466/469/474-475, pass TE:912-931 — go.
- gm_rebuilding writers GE:1546, TE:287/577/607, ME:1145, LE:83; readers SG:139, GT:292/332/736/863, MT:321/348/361, EV:63/106, ME:1350 — still needed as guard around the one create_building.
- gm_rebuild_level, gm_rebuild_asked GE:1558/1584, TE:289/301/570/583/597-612, ME:230/1147/1160 — go. gm_monument_rebuild_self_check ME:2473 (from GE:429) — go (replace with create-at-1 check).
- gm_restore_pm writers: gm_state_mark_restore_pm CE:865 (from TE:286/566, ME:1143), TE:640, GE:1735 (flag:undedicated); removers GE:401/1701/1921, CE:924; ~25 guards MT:130/320/346/359, GT:313/330/504/622/864, CT:168, TT:50, SG:138, GE:30/321/783/1215/1642, CE:1528, ME:1140/1348/2385/2399, TE:563 — keep, narrowed (swap/promote/raise-orphan + fallback for create at dedication). gm_state_restore_dedication CE:894 (from GE:428/740, ME:1741/1995, EV:54) keeps.
- gm_gift / gm_state_gift_grandeur CE:629 / CE:848 keeps. .26 EV:1604 keeps (stale "rebuilt taller" comments EV:22, .28). .29 EV:1634 mostly goes (orphan adoption stays). .31 EV:1689 changes.
- gm_state_monthly no-building branch GE:491-532 → put back at level 1 when records stand.
- debug te_debug_monuments.1 events/te_debug_monuments_events.txt:31 (create at 20) — changes.

## 3. Freeze / beside
- gm_levels writers GE:325, 1928; TE:305, 538, 650; ME:1985, 2039-2040, 2147, 2167; remover GE:388. Readers MT:318-319, 337; GT:297, 329, 641, 653, 692, 750, 810, 839; MV:232, 247, 276; GV:480; ME:304, 1970. Becomes the size record; migration reads it.
- gm_state_record_frozen_levels GE:315 (refresh GE:792, .1 EV:91) — goes. gm_state_has_new_levels MT:315 (GE:794, EV:88, EV:1668) — goes. gm_state_found_beside ME:303 (EV:89, EV:1669) — goes (replaced by "Dedicate joins beside"). gm_newcomer ME:306/777, GE:389, MT:334, GT:623 — goes. gm_state_newcomer_settled MT:333 — goes. gm_state_settle_newcomer ME:776 — runs at dedication. gm_state_swap_primary ME:749 (ME:710, 795) keeps. gm_state_demote_primary ME:322 keeps + starting grandeur record. gm_state_raise_secondary ME:757 keeps.
- gm_state_can_expand GT:289 (B:46-51; CE:255-318) — becomes the site's gate. gm_state_can_rededicate_beside GT:326 changes.
- gm_ceremony_level writers GE:1645, GE:1753 (0), LE:88, TE:654/657, ME:1986, EV:185; readers GE:1667-1670, MV:253, MT:145/160, GT:620; copied to gm_tr_ceremony_level ME:361/1425. Two roles: 0 = seen awaiting Dedicate; else the asked level.

## 4. Building definition (B)
building_group bg_grand_monuments (extra_building_groups.txt:97: government-funded, urbanization = 10, infrastructure_usage_per_level = 1); city_type/levels_per_mesh 18-19; expandable yes (21); downsizeable no (30); unique no, ai_nationalization_desire 0 (31-32); PMGs pmg_monument_dedication + pmg_maintenance (34-37); required_construction construction_cost_grand_monument=1000 (39); can_build_government/private = gm_state_can_expand (46-51); possible = gm_system_enabled (54-59); ai_value 66-113 (+25 GP/major, +50 tourism industry, +25 legitimacy<40, −100 at war, −25 per monument, −100 hard times). Not set: buildable, has_max_level, unlocking_technologies, potential.
Dedication PMs grand_monument_pms.txt:51-292 (unscaled staff 200/50; self-listing ratchet in unlocking_production_methods; pm_monument_undedicated is_default anchors; industrial needs marketing_research :255; athletic television_broadcasting :277). pmg_maintenance shared REPLACE_OR_CREATE (~74 building types) — don't edit pm_maintenance.

## 5. Seeding
gm_seed_landmarks LE:22 (from monument_events_on_actions.txt:398; 42 rows at LEVEL 5/10/15; Arc 15). gm_seed_landmark LE:71 (gm_rebuilding 1 day, records, gm_ceremony_level = LEVEL, create_building level = LEVEL activate_production_methods = { pm_monument_<ded> } LE:91-95, refresh) → level 1 + records. gm_seed_landmark_beside ME:1203 (container + tr_add_levels; never runs on a normal start). gm_seed_trophies TE:1243 / gm_seed_trophy TE:1269 (10 containers, gm_tr_levels 2-5, gm_tr_grandeur = ceil(L/2)).

## 6. on_building_built → .1
monument_events_on_actions.txt:9-13; EV:39 hidden building_event gated on is_building_group = bg_grand_monuments (group!) + owner. Per level: restore_dedication; vanity (skip under gm_rebuilding); merge adopt; piece-takes-whole / found_beside; record_frozen_levels; reset_copied_dedication; AI ceremony; gm_com_last_state; .20. Not established whether it fires every level (didn't for 5 same-day). Moves to site; must ignore the finished building's creation.

## Trip list
1. create_building with activate_production_methods is in use (LE:91-95, common/decisions/extra_decisions.txt:503): main path; restore_pm fallback + self-check.
2. create_building refuses an owner lacking unlocking_technologies (extra_effects.txt:861-863): finished type must have none; self-check buildable/possible too. Only buildable = no building: building_gm_name_carrier_anchor (never script-created).
3. Level-1 finished building loses per-level group effects (urbanization 10/level, infrastructure usage 1/level).
4. .1 fires on the group: if the site joins bg_grand_monuments, .1 fires for site levels and the finished building's creation (guard).
5. Every "a monument stands here" read checks the finished building (gm_state_monument_count, gm_status_code, gm_state_grandeur, primary levels/age, refresh state loops GE:709/727/738, gm_repair_after_civil_war GE:1418, shadows). Site needs its own presence read.
6. State records belong to the primary: ceremony trigger NOT gm_seen (EV:178) and gm_state_awaits_dedication (MT:159) block a site's Dedicate where a finished primary stands. Site needs its own record names.
7. Rededicate reopens a ceremony with "Not yet" → would leave a finished undedicated monument.
8. Upkeep: level-1 pm_maintenance charges 0.1; N levels ≈ multiplier N−1; mothballed −1. Current code avoided building-scope multiplier (GE:452-453); SR local_var pattern st_res_effects.txt:313-330. Don't edit pm_maintenance.
9. gm_state_record_frozen_levels writes inside gm_country_refresh (walked by tooltips): migration must not copy that.
10. gm_state_merge_pending's cheap read is unexplained_levels > 0 (GT:593), asked by every refresh: needs a replacement.
11. Opportunities/AI build the finished type: start_building_construction = building_grand_monument CE:338, gm_com_monument_under_construction CT:296, gm_com_pick_build_state undedicated branch CE:280-296, under-construction reads SG:130, MT:171, GE:323, GT:298/671/862 → site.
12. Name collision: te_construction_market_site exists with its own on_building_built event (te_construction_market_building_events.2). Distinct key.
13. gm_tr_grandeur is stored; migration recomputes.
14. Engine's-copy machinery exists for undedicated finished buildings (gm_state_has_copied_dedication, reset_copied_dedication, panel pick at first sight, lacks_dedication_tech, flag:undedicated restore): mostly goes for the finished type; keep pm_monument_undedicated key for old saves.
15. Stale comments: EV:22, .28 header, LAD:78-79, GT:272-288.
