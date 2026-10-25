# First Past the Post: play-test list

`amendment_first_past_the_post` (2026-10-25) replaces vanilla's culture-hardcoded American two-party system with an
amendment on the voting laws. It passed the offline gate (`test_first_past_the_post.py`, the CI audits); what the
join weights do in a running game only the game shows. In-game checks don't gate a merge (CLAUDE.md, "In-game
checks"). Design: `docs/superpowers/specs/2026-10-25-first-past-the-post-design.md`; system notes:
`docs/systems/mod_systems.md` § First Past the Post.

## How to run

- **Deploy** per CLAUDE.md, "Play-testing unmerged work" (or from `main` once merged).
- **Party affiliation**: Politics panel → hover an interest group's party icon, then a party's line for its breakdown.

## Self-checks

| Line in `debug.log` | When | BROKEN means | Fallback |
|---|---|---|---|
| `TE_SELF_CHECK OK\|BROKEN fptp_major_parties` | The first monthly pulse at which some country has three or more active parties (once a game) | The two largest parties weren't marked from `ordered_active_party` by `te_fptp_party_clout`: wrong count, an unmarked party larger than a marked one (compared pairwise), or every clout 0 (the `every_member` sum failed) | Order by the party's `momentum` instead of its members' clout (`te_fptp_refresh_major_parties`, `te_fptp_second_party_clout`) |

## Checks

| # | Check | What to look for | If it fails |
|---|---|---|---|
| 1 | The terms show, and vanilla's are intact | USA, 1836: an interest group's Whig and Democratic breakdowns end with "First Past the Post: one of the two largest parties +5" ahead of the party-size lines, and still carry vanilla's lines (Base Value −5, the North/South and slaver/abolitionist terms). A third party (Know-Nothings, Constitutional Union) shows "not one of the two largest parties −20" as its last line. No "American Two-Party System" line anywhere. | Only the mod lines: the generated INJECT lost vanilla's block; regenerate with `scripts/generators/gen_party_join_weights.py` and check `restate`. No mod lines: `te_fptp_in_force` or the history's major marks didn't apply; check the Census Voting law's amendments. |
| 2 | Two parties in the USA | Through the 1840s–50s the USA keeps two parties, as in vanilla. Each holds at most three groups (vanilla's size chain gives a fourth ×0), so the rest stay out of parties unless one fits a third party strongly. | More parties: raise `te_fptp_minor_party_join_weight`. A major with room (under three groups) that a fitting group won't join: raise `te_fptp_major_party_join_weight`. Too many groups outside parties because the majors are full: the bonus can't help (the chain zeroes it); add a term after the chain that softens the ×0 for majors. |
| 3 | The amendment shows on the law | Census Voting's law tooltip lists First Past the Post with −25% ideological incoherence and −5 legitimacy. | `amendment_first_past_the_post` didn't load; `error.log` for `te_first_past_the_post.txt`. |
| 4 | Keep or drop on a voting-law change | USA: enact Universal Suffrage (console `law` commands or play). On passing, "Counting the Votes" asks whether to keep it. Keeping puts it on Universal Suffrage; declining leaves it off, and enacting another voting law later doesn't ask again. | No event: `on_law_activated` didn't reach `te_fptp_from_law_scope`, or `te_fptp_var` was gone; look for the variable in the country's data. |
| 5 | The Confederacy | When the Civil War starts, the CSA has First Past the Post on its voting law within a month (the seed), and its first two parties are marked. | Not attached: `te_fptp_seed_eligible` failed (its voting law or Presidential Republic); compare with the CSA's laws. |
| 6 | Debate offer and petition | A country with two parties enacting a voting law gets "The Winner Takes All" at a debate checkpoint; a two-party country on a voting law may get "Two Parties Are Enough" (2.5% a year). Accepting either attaches the amendment. | Event never fires in a long observer run: check `te_fptp_two_majors` on such countries. |
| 7 | A third party rises | Over a long game, a USA party can lose a major's place to a growing one (the marks follow members' clout monthly). The new major gains the +5 at the next campaign. | Never moves: the ranking is stuck (self-check above). |
| 8 | How far it spreads | In a long observer run, count the AI countries holding First Past the Post (the voting law's amendments). Negotiation can add it wherever the two largest parties hold 60% of the clout. | Too many: tighten `would_sponsor` (more clout, or powerful groups only). |
| 9 | A revolution | A USA revolution that wins on a new voting law asks "Counting the Votes" at its end (`te_fptp_repair_after_civil_war`); a USA that had repealed it doesn't get it back from the rebels. | No event: the merge didn't hand `te_fptp_var` over, or `te_civil_war_on_won` didn't reach the repair. |
