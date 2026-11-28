# Private Actors: play-test

Every company becomes a firm, behind the default-off rule `te_private_actors_rule`: a record on the company, a yearly
turn in a month of its own, eight goals scored from its markets, the laws and its workers, three currencies, a ledger
and two threshold notices. Spec: `docs/superpowers/specs/2026-11-28-actors-firms-design.md` (#2140); plan:
`docs/superpowers/plans/2026-11-28-private-actors.md`. How it is built: `docs/systems/mod_systems/private_actors.md`.
Nothing in it has been seen in a game. This list starts with the chassis (the plan's Tasks 1 and 2); each later task
adds its lines.

The chassis has no verbs and no tab of its own yet (Task 3 builds the tab on the rows): a firm only assesses, scores
and chooses, so what can be judged in phase 1 is whether its goal and reason are believable.

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
