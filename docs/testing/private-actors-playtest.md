# Private Actors: play-test

Every company becomes a firm, behind the default-off rule `te_private_actors_rule`: a record on the company, a yearly
turn in a month of its own, eight goals scored from its markets, the laws and its workers, three currencies, a ledger
and two threshold notices. Spec: `docs/superpowers/specs/2026-11-28-actors-firms-design.md` (#2140); plan:
`docs/superpowers/plans/2026-11-28-private-actors.md`. How it is built: `docs/systems/mod_systems/private_actors.md`.
Nothing in it has been seen in a game. This list starts with the chassis (the plan's Tasks 1 and 2); each later task
adds its lines.

The chassis has no verbs: a firm only assesses, scores and chooses, so what can be judged in phase 1 is whether
its goal and reason are believable. Task 3 adds the Private Actors tab of the Timeline Extended window (items 11 to
18), the posture buttons and the ledger's display. Task 4a adds the first verbs, the trust and the foundation (items 19
to 30, and the `cartel_rents` self-check). Task 4b adds declared moves, the trust's two petitions, the state's actions
and the top-bar alerts (items 31 to 44, and the `charter_monopoly` self-check).

## Self-checks

Each logs once a game in `debug.log` (`TE_SELF_CHECK OK|BROKEN <name>`, with its counts), with the rule on. The four
turn-time checks wait for 20 firms, so the first lines come within a few months of switching the rule on.

| Line | When | OK means | BROKEN means | Fallback |
|---|---|---|---|---|
| `firm_share` | after 20 firms' turns whose sector has two levels or more at home | some read a share above 0 and below 1 (`between`): the `company_owned_levels` ladder and the sector's levels both read | `zero` = all: the ladder matched nothing; `full` = all: `te_pa_g_sector_levels` reads too low | zero: a ladder of `company_employed_levels`; full: sum `b:<type>.level` over the owner's states for the sector |
| `firm_executive` (probe 7) | after the first 20 firms' turns | every firm had an executive (`executive` = `firms`), each held exactly one character ideology, and some held a personality trait | `executive` below `firms`: some company has none; `with_trait` 0: `has_trait` doesn't reach through `company.executive`; `one_ideology` below `executive`: `has_ideology` doesn't | none needed for a missing executive (its temperament is neutral, built); no traits: drop `TRAIT_TEMPERAMENT` and read the ideology alone; no ideology: drop `IDEOLOGY_TEMPERAMENT` |
| `firm_hq` (probe 11) | after 20 seat picks of firms with their buildings at home | `hq_link=none`: no script link reaches a company's headquarters state (the 1.15 event targets; read offline, 2026-11-28), so the seat is the incorporated home state with most levels of the firm's types, and the pick found one (`by_levels` above 0). `seat_hq` counts seats holding some company's headquarters building, for the record | `by_levels=0`: `te_pa_gen_seat_pick` found no state, and every seat is the capital | the capital as every firm's seat (what the pick falls back on already) |
| `firm_revolution` (probe 8) | armed when revolutionaries win with the rule on and firms on either side (a `START` line); read at the winner's next monthly pulse | the winner holds companies and every one kept its record (`with_record` = `companies`; `kept_turns` counts those that had taken a turn before) | `with_record` below `companies`: records were lost; `companies=0`: the loser's companies did not pass to the winner | lost records: the pulse makes new ones for those companies (built); no companies: nothing to keep, firms start over as the winner founds companies |
| `firm_price_read` (Task 1) | after 20 firms' turns whose output is a traded good | some output reads a price off base (`off_base` above 0) | every output reads exactly its base price: `te_pa_gen_firm_price_<good>` fails through the owner | read the country-scope `te_pa_gen_price_<good>` in the owner's scope |
| `law_available` (Task 1) | the first monthly pulse with the rule on, in the first country with a covered law it could move to | `untech=0`: `law_is_available` reads a law's unlocking technology | `untech` above 0: it doesn't | the open-law triggers already carry the technology and `can_enact` lines; drop the `any_law` line and mirror the disallowing laws too |
| `ledger_size` | the first "holds 40% of its sector" line (verb 11) | the entry's size equals the share it was saved from | the size didn't arrive: a saved scope value reads as nothing in `set_variable` | stage the size in a country variable for `te_pa_ledger_add`, as `un_ledger_log_add` stages its amount |
| `cartel_rents` (probe 2) | armed when a cartel's modifier is first applied (a quarter after it forms, strength 5 or more), read at the owner's next monthly pulse | `country` falls by `want` (the cut its strength asks, to 0.002): the modifier's multiplier, `var:te_pa_cm_<type>`, resolved against the owner; and where `seat_has=1`, the seat building's own read falls by it too: a country's `building_<type>_throughput_add` reaches the type's buildings | `country` off: the multiplier didn't resolve (the wrong ROOT) or the type isn't registered, or another cartel of a building type the two share moved the sum in the same quarter (read the numbers); `seat` off with `country` right: the country line doesn't reach the buildings | a restricted production method switched in on the firm's buildings (`activate_production_method`, one per building type, in place of the throughput line; the method's switch back when the cartel ends) |
| `charter_monopoly` | armed at the first monopoly charter granted (on a petition or from Grant a Charter), read at the owner's next monthly pulse | `held=1 any=1`: `add_company_monopoly = bt:<its main building type>` gave the company the engine's monopoly on that type, and both `company_has_building_type_monopoly` and `company_has_monopoly` read it | both 0: the effect gave nothing (or the reads fail); `held=0 any=1`: a monopoly, but not on that type, or the type read fails | the block form, `add_company_monopoly = { building_type = bt:<type> }`, in `gen_private_actors.py`'s `render_charter`; failing that, the charter rests on its lawful, permanent cartel alone (built) |

## In the game

1. **Records and turns.** Start a game with Private Actors Enabled and play six months. With the console, read
   `te_pa_init` and `te_pa_turn_in` on a few companies of several countries: every company has a record, and the
   months to its turn run from 1 to 12, not all the same. After a year every firm has `te_pa_turns` 1.
2. **The owner's phase-1 judgment: are the goals and reasons believable?** For real countries in 1836, 1900 and 1950
   (Britain, France, Prussia or Germany, the United States, Japan, Russia), read each firm's goal and reason after its
   first turn (`te_pa_goal`, `te_pa_reason`, `te_pa_reason_val`, and the eight `te_pa_p_<g>` and `te_pa_s_<g>`; the
   Private Actors tab once Task 3 builds it, its ledger at once). Say which look wrong: a textile firm seeking Cheaper
   Inputs while its cotton sits at base, a firm under Command Economy seeking Dominance, a failing firm not seeking
   Survival, every firm of a country holding one goal, or a goal that never appears. The weights' and pressures'
   numbers are first guesses in `te_pa_goals_values.txt`.
3. **Goals change.** Over ten years a firm's goal should change now and then (a price swing, a law being enacted, a
   slump), and not every year (the +15 for the goal held). A firm whose goal changes at every turn, or none in ten
   years across a whole country, means the scale is off.
4. **Survival.** A firm under prosperity 25 and falling shows Condition Failing and its Survival pressure above 80
   (`te_pa_p_survival`); one that is prosperous shows Survival 0.
5. **Currencies.** After a year, Funds are a small fraction of the investment pool's yearly income summed over the
   country's firms (a tenth of their share of it), none under Command Economy; Connections sit between 20 and 30 for
   a new firm, higher with the executive's group in government; Standing drifts to 50. Nothing leaves the pool.
6. **Notices.** A player's firm that starts failing, or reaches 40% of its sector, posts one notice naming it, and
   not again until it recovers and crosses back. None at the game's start.
7. **The ledger.** `te_pa_ledger` on the player's country holds at most 20 entries, the oldest evicted; after a year
   it holds the firms' first goals with their reasons.
8. **AI posture.** In an AI country, a firm whose executive's interest group is in government reads `te_pa_posture`
   1, one whose group is marginalized -1.
9. **The seat.** `te_pa_seat` is a state with the firm's buildings, kept for years; a firm with no buildings at home
   sits at the capital.
10. **Performance.** With the rule on, a late game's monthly tick should not slow noticeably (a few hundred firms, one
    turn each a year spread over the months).
11. **The tab and the rule.** With the rule on, the Private Actors tab is the sixth on the window's second strip, after
    Global Warming, and opens; the strip's six names wrap to two lines at most and none ends in "...". With the rule off
    (a new game on the default, or the rule switched off mid-game, after the month's pulse) the tab leaves the strip and
    the other five keep their places. Full screen, the overview, the roster and the ledger take a column each.
12. **The rows show every firm.** The roster lists one row a firm, as many as the country's companies (the Grand
    Monument naming placeholder aside); the overview's Firms box counts the same. Each row's icon is its company's, its
    hover vanilla's company tooltip, a click opens the company; the name wraps at most to two lines. **Not seen in
    game: the GUI's company reads through `ScriptContainer.MakeScope.Var('te_pa_r_firm').GetCompany`** (the icon, the
    name, `FancyTooltip_Company` inside a datamodel row, gotcha #24) **and the ledger's
    `Var('te_pa_l_actor').GetCompany.IsValid`.** If the icon or name is blank, or `debug.log` logs "Failed to fetch"
    or a context error for a row each frame, the fallback is a loc name read through the row
    (`[ScriptContainer.MakeScope.Var('te_pa_r_firm').GetCompany.GetNameNoFormatting]` in a key, as the Grand
    Monuments' naming reads a company) and a plain hover key in place of the company tooltip.
13. **The row's figures.** Executive and Goal match the console's `te_pa_exec` and `te_pa_goal`; Why reads a sentence
    (a good or a law by name, not "a good"); the three bars move with `te_pa_funds` (against its cap), `te_pa_conn` and
    `te_pa_stand` at the next quarter; a holding chip shows only once its strength is above 0 (none can be yet); the
    condition arrow is up, flat or down as the console's `te_pa_cond`.
14. **The posture buttons change the row.** On your own firm, Favor, Tolerate and Restrain: the one in force is grayed
    with "It is not … already" crossed in its hover, and the hover names what the posture does; a click changes the
    row's Posture at once (the row is copied again), adds a ledger line ("… is now Favored by the state"), and
    `te_pa_posture` on the company reads 1, 0 or -1. A posture set stays: an AI's re-derivation never touches a
    player's firms. If a click does nothing, the row's container did not arrive as `scope:te_pa_row` (the button's
    hover then crosses "It is one of our firms"): pass the firm's company type instead, as a number, and find the row
    by it.
15. **Show Details.** Show Details opens one firm's detail, and only that firm's (a key named for the company); Hide
    Details closes it; another firm's stays as it was. The goals table's held goal is ticked and its score the highest
    (with the +15); Law Being Enacted names the law and a stance while the country enacts a law the table covers, and
    None otherwise; Seat names a state. A renamed company's detail closes (the key is its name): expected.
16. **National Info shows another country's firms.** Open an AI country's National Info: its Private Actors tab (the
    last strip, three tabs) shows its overview, firms and ledger, with no posture buttons; each firm's Posture is the AI's
    (Favored for a firm whose executive's group governs). An observer sees no posture buttons and no "?".
17. **The ledger opens collapsed, newest first.** The Ledger section starts collapsed; opened, its lines run newest
    first, each "<firm> <what it did>" and its hover "Recorded N months ago". After the ledger has passed 20 lines (a
    few years of a large country) the order still holds (`te_pa_ledger_view`). A dissolved firm's lines read "A
    dissolved firm …" and log nothing. Secret moves ("Author unknown: a firm …") come with Task 4.
18. **The overview.** Prospering, Steady and Failing add up to Firms; Largest Firm names the firm with the highest
    share and its share, its name shrinking rather than ending in "..." when long; Common Goal names the goal most
    firms hold. They follow the month's pulse, so a turn's change shows on the 1st.
19. **Verbs.** With the rule on for five years in a large 1900 country (Britain, Germany, the United States), the ledger
    shows trust lines (verbs 20 to 29). A firm seeking Dominance below half its sector queues a level of its main
    building type at its seat once a year (`te_pa_expands` counts them; the construction queue shows the private level):
    check the level is queued in the seat and paid by the investment pool, and whose company owns it once built (the
    engine's; unread).
20. **Spending.** A firm's foundation founding and upkeep, and a buyer's payment, take the same sum from the country's
    investment pool as from `te_pa_funds` (read `investment_pool` before and after a quarter with one foundation), and
    never more than the pool holds. Nothing else lowers `te_pa_funds` but the cap.
21. **A cartel forms.** Under Freedom of Contract, a firm at 50% of its sector seeking Dominance or A Protected Market
    forms an open cartel at its turn: a ledger line "<firm> forms a cartel in <good>", a Cartel chip on its row after
    the next quarter, and "<company> Cartel" in the country's modifiers with each of its building types' throughput at
    minus 1% at strength 5. Its strength grows 15 a year (10 under other laws), never past its share × 100. Its output's
    price in the market rises over the following months: say whether it moves enough to notice.
22. **A secret cartel.** Under Antitrust Enforcement, the same firm forms its cartel in secret: the ledger reads
    "Author unknown: a firm forms a cartel in <good>", the firm's row shows no chip and its detail no line, and the
    country's modifiers show "Restricted Supply (author unknown)" with the same throughput lines. Nothing anywhere on the
    tab names the firm until it is exposed.
23. **Regulated Utilities.** A cartel outside infrastructure and power stops at 40 (rising toward 80 with a captured
    regulator); a power or railway firm's cartel is secret.
24. **Exposure.** Over a decade some secret cartels are exposed (more under Protected Speech with police and Home
    Affairs funded, fewer under Outlawed Dissent): the ledger line "<firm> is exposed as the author of a cartel in
    <good>", its earlier secret lines now name it, its Standing falls 15 and its foundation 20, and at the next quarter
    its modifier takes its name. A captured regulator makes exposure rarer in proportion to its strength.
25. **The regulator.** Under a law with one, a cartel firm captures the regulator ("Author unknown: a firm captures the
    regulator"), paying 10 Connections a year; its Connections fall accordingly. Under Contracted Administration or the
    Spoils System it grows half again as fast. With the cartel gone it decays.
26. **Stalling.** While the country enacts Antitrust Enforcement with an open cartel in force, the cartel's firm spends
    20 Connections for one setback ("<firm> stalls Antitrust Enforcement with a setback"), at most once a year; the
    enactment's setbacks rise by one and the law never fails from the stall alone (the guard stops one short).
27. **Buyers.** A firm seeking Cheaper Inputs whose input a secret cartel makes pays to expose it ("<firm> pays to
    expose a cartel in <good>"), and that cartel's exposure comes sooner.
28. **The foundation.** A firm with Standing under 60 (more for a paternal executive) and funds to spare endows a
    foundation at its seat ("<firm> endows a foundation in <state>"); a Favored firm's goes to the home state with the
    lowest literacy. The state shows "<company> Foundation" with education access and lower mortality growing with its
    strength (+10% and −5% at 100), and the firm's Standing climbs toward the foundation's strength. A firm that runs out
    of funds sees it decay; a dissolved firm's foundation decays by itself over the following years. **Not seen in
    game: `literacy_rate` as a state's `order_by` value** (vanilla uses it in script values); if a Favored firm's
    foundation lands in a highly literate state, read it.
29. **The holdings' hovers.** The Cartel chip's hover gives its strength, whether it is legal under the law in force,
    the throughput cut and the faster Funds; the Foundation's names its state and its yield; the Captured Regulator's
    shows only after an exposure.
30. **Rules off with holdings.** As the rules-off list's Private Actors section says: every Cartel and Restricted Supply
    modifier leaves the country and every Foundation modifier its state within a month; switching back on, the cartels'
    return at the next quarter and the foundations' at the next month.
31. **A charter petition from a strong cartel.** Under Guilds and Chartered Monopolies, take a firm of yours whose
    cartel has reached 80 (the console can set `te_pa_cartel` to 85 on one seeking Dominance, with `te_pa_cartel_known`
    1). At its next turn the ledger reads "<firm> petitions the government for a monopoly charter in <good>", a
    notification says so, the firm's row reads "Petition: a monopoly charter, 6 months to the answer", and a yellow alert
    sits on the top bar. Each month the row's months fall by one. A Favored firm with any known cartel petitions under
    any law. A firm with a secret cartel never does.
32. **The alerts' colors.** With the firm still on the posture it started with (Tolerated, never touched), the alert
    turns red at 2 months left ("A Petition Falls Due", naming the posture's answer). Set any posture with the row's
    buttons and it goes back to yellow at once (`te_pa_move_hand` 1), and stays yellow to the end. Both are gone the
    month the event fires. Hover each: the name, the months left and the default read right; a click opens the
    companies panel.
33. **The end event.** At 0 months `te_pa.1` ("A Monopoly by Charter") opens at once, with the boardroom picture, the
    firm named, and four options. Hover each: Grant shows the charter and the Petty Bourgeoisie's −2 approval; Stand
    aside and Refuse the five years' wait; Refuse also Grievance +1; the fourth says the posture answers. Let one event
    lapse instead (wait out its timer): the posture's answer applies (Tolerated: stand aside).
34. **A charter granted.** After Grant: the ledger reads "<firm> is granted a monopoly charter in <good>", the cartel
    chip's hover says it holds a charter, the company's panel shows a monopoly on its main building type (or read the
    `charter_monopoly` line), its Connections are 15 higher, and the cartel no longer ends when its share falls (set
    `te_pa_share` to 0.3 and watch a quarter: it stays, at strength 5 or more). Under Antitrust Enforcement a chartered
    cartel is lawful: Bring Suit is grayed.
35. **The gap.** No second petition is declared while one runs, nor within 12 months of its end (`te_pa_move_last`);
    two firms that would petition in one month declare one move, the higher goal score's, and the other petitions at a
    later turn. A firm refused or left unanswered asks again only after five years.
36. **The buyers' petition.** Under Antitrust Enforcement, with a known (exposed) cartel and a firm of yours seeking
    Cheaper Inputs at score 60 or more with 30 Connections that buys the cartel's good: the buyer petitions ("<buyer>
    petitions the government to sue <firm> over its cartel in <good>"), and `te_pa.2` ends it. Taking it up opens the
    case at once with no approval cost (no "State Action Against Its Firm" on the cartel firm's executive's group).
37. **A suit won and a suit lost.** Bring Suit on a known illegal cartel: the row reads "In court: 12 months to the
    verdict", counting down monthly; the ledger gives the state's chance. Set Judicial Independence high
    (`te_judicial_independence` 90) for one case and low (10) with the firm's Connections at 80 for another: the first is
    usually won ("loses its case, and the court breaks its cartel"; the cartel's modifier leaves at once and no new
    cartel forms for ten years, `te_pa_cartel_barred_until`), the second usually lost ("wins its case", Bring Suit grayed
    for ten years). `te_pa.3` reports each with the courtroom video. Under National Champion Exemption a Favored firm's
    cartel can't be sued.
38. **The other actions.** Inquiry: a year's +30 on the firm's exposure chance (`te_pa_expose_chance_value` reads 30
    higher), the button grayed while it runs. Audit the Regulator on a firm with a captured regulator: usually "found
    and broken" (the regulator gone, the firm's Standing −15); a miss cuts it by 20 silently; on a clean firm "nothing is
    found". Levy on Rents on an open cartel: each quarter the treasury gains what the investment pool loses, half the
    cartel's share of the firm's accrual (read both before and after a quarter), Grievance +1 once; Lift the Levy ends
    it. Grant a Charter as item 34, unasked.
39. **The costs.** On a firm with Standing 80, Bring Suit gives its executive's group about −3 approval for five years
    and radicals in its seat; on one at Standing 20 no approval is lost and its seat gains loyalists. Inquiry and Audit
    cost half. Hover each button: grayed ones list the reason, active ones what it does and costs.
40. **An AI country's answer, with its reason.** In an AI country, find a petition's end in its ledger (National Info,
    the Private Actors tab): the line reads granted, left unanswered or refused, with its reason in parentheses ("its
    posture's default", "the price of the cartel's good", "the government's stance on antitrust", "the Standing of the
    cartel's firm"). Check a few against the country's posture and its governing groups' stances: say whether they read
    as understandable.
41. **AI actions.** Over a decade some AI governments sue, levy, audit or open inquiries into firms holding 40% of their
    sector whose good sells well above its base price, at most one a quarter, never against a Favored firm. Say whether
    they act too often or never.
42. **Too Large to Break.** Under Antitrust Enforcement with a known cartel and the rule on, `amendment_petition_events.4`
    can fire in good times too, and names the firm with the largest known cartel. With the rule off it fires only in
    hard times, as before.
43. **A disbanded petitioner.** Disband a firm with a petition under way: the move lapses, the alert goes, and the next
    petition waits 12 months.
44. **Rules off with a petition.** As the rules-off list's Private Actors section says: the move and the alerts go,
    and every "State Action Against Its Firm" and "Resents a Monopoly Charter" leaves its interest group.
