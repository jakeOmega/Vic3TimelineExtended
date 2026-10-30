# First Past the Post: a two-party system from an amendment

Date: 2026-10-25. Owner request: replace vanilla's culture-hardcoded American
two-party system with an amendment that "radically reduces the willingness to
join any but the two largest parties", with big-tent legitimacy effects, and
an event when the voting law changes asking whether to keep it. The owner
handed the open calls to the builder ("I'll leave it up to you"); they are
marked *(builder's call)*.

## What vanilla does (1.14.5)

Vanilla's party `join_weight` blocks carry a `usa_two_party_system` term for
any North American country with a Yankee or Dixie primary culture under
Presidential Republic: −10 to the Agrarian, Free Trade, Military, Radical and
Religious parties, +3 to the Liberals (non-Trade-Union groups whose leader is
not reactionary, conservative or socialist). The Conservatives (Democrats) get
nothing, and the Social Democrat, Communist, Anarchist and Fascist parties are
untouched. An interest group joins a party at affiliation ≥ 1
(`MIN_AFFILIATION_TO_JOIN_PARTY`); every party's base is −5. The North/South
(`from_northern_interests` / `from_southern_interests`) and slaver/abolitionist
(±100) terms are Civil War flavour and stay as they are.

## Engine facts this rests on

- **An `INJECT` into a party's `join_weight` replaces the whole field**, keeping
  the party's other fields (read in game 2026-10-25, the same rule as the
  interest groups' script-value fields, 2026-10-10). So the mod restates each
  vanilla party's whole `join_weight`, as `ig_feminism.py` does, from a
  generator. *(Spike result.)*
- `has_amendment` is law-scoped: `active_law:lawgroup_distribution_of_power ?=
  { has_amendment = amendment_type:X }`.
- `join_weight`'s root is the interest group (`owner` = its country);
  `ordered_active_party` sorts descending (`position = 0` is the largest);
  `every_member` iterates a party's groups; `ig_clout` is a value.
- A law's amendments leave with it when the law is replaced (vanilla re-attaches
  the Tradition of Free Elections from each voting law's `on_activate`).
- The mod's `GLOBAL` history runs last, after vanilla country history.

## Design

### The amendment

`amendment_first_past_the_post`, on the voting laws that hold elections:
Landed, Wealth and Census Voting, Universal Suffrage and Anarchy (the mod
treats Anarchy as electoral). Not on Oligarchy, which grants no voting power.
*(Builder's call: the voting law, not the federal system or Presidential
Republic — the electoral rule is what produces two parties; federal Germany and
presidential Brazil are multi-party.)* No `parent` law: a group's view of it
comes from its party's size, not its ideology, so sponsorship
(`would_sponsor`: a member of one of the two largest parties, once their
groups hold 60% of the clout) and the events'
approval effects carry it. Repealable at vanilla's
`legitimacy_to_repeal_amendment`; the AI never repeals it.

Modifiers *(builder's call, anchored to vanilla)*:

| Modifier | Value | Anchor |
|---|---|---|
| `country_legitimacy_ideological_incoherence_mult` | −0.25 | the strongest reduction a vanilla law gives (Single-Party State, Corporate State) |
| `country_legitimacy_base_add` | −5 | the mod's amendments move legitimacy by ±5 (Whistleblower, Small Donor Matching, Judicial Elections, Habeas Corpus); half the Tradition of Free Elections' +10 |

Big tents cost less (a party of mismatched groups is normal under plurality
voting); voters whose party can't win cost the government a flat 5.

### The two largest parties

Ranked by summed member clout (`te_fptp_party_clout`), refreshed on every
country's monthly pulse, not inside `join_weight`: all groups re-pick their
parties together at a campaign's start, so "largest right now" is undefined
there. The refresh clears and re-sets a country variable per party type
(`te_fptp_major_<type>`), `te_fptp_two_majors` when at least two parties are
active, and `te_fptp_major_member` on each member group of the two. The
revolutionary party is never ranked. Until two parties exist, no terms apply,
so the first two to form become the two.

### Join-weight terms

Added to every party's `join_weight`, for the eleven vanilla parties through
the generated INJECT and for the mod's three in their own files:

- one of the two largest: `te_fptp_major_party_join_weight` = **+5** ("big
  tent"), just ahead of vanilla's party-size chain (×2 with at most one prior
  member for a group that isn't powerful, ×0.5 with two, ×0 with three or
  more). After the chain it would be a flat +5 for every group once a party
  had three members, whatever its fit; ahead of it, a party still fills up at
  three groups and fit still picks the major. So the two majors hold at most
  six groups between them.
- any other party: `te_fptp_minor_party_join_weight` = **−20**, after every
  multiplier, so it is the full size,

only while the amendment is in force and two majors are marked. *(Builder's
call: −20 is twice vanilla's −10 and the largest ordinary term vanilla uses;
fits are mostly +2 to +10 a term, so a third party stays open to a group with
a strong fit — a soft cap, not a ban. One can still overtake a collapsing major.)*
The generated copies drop vanilla's `usa_two_party_system` terms.

### Who has it

- **The USA** from 1836 (history, `GLOBAL`), with the Democrats and Whigs
  marked as its two majors so the parties formed at game start see the terms
  before the first monthly ranking.
- **A once-per-country seed** on the first monthly pulse gives it to any
  country vanilla's term covered (North America, Yankee or Dixie primary
  culture, Presidential Republic or a variant, an allowed voting law): the
  Confederacy when it forms, Texas, and the USA in a save from before this
  change. Once only, so a repeal sticks. Never for a revolution's rebels,
  who start with no mod variables: the winner inherits the nation's seed mark
  instead of being handed back an amendment the nation had repealed. *(Builder's call: no other country
  starts with it; Britain is a candidate for later.)*
- **Enactment debate** (`te_fptp_events.2`, pooled in `on_law_checkpoint_debate`
  as `extra_law_events.87` is): while an allowed voting law is enacted in a
  country whose two largest parties hold 60% of the clout and no first past the
  post, the strongest group in a major party asks for it. The same gate as
  `would_sponsor` and the petition, so the debate doesn't spread it to every
  multi-party AI democracy.
- **Petition** (`amendment_petition_events.28`, 2.5% a year): on an allowed
  voting law in force, when the two largest parties' groups hold 60% of the
  clout, the strongest of them asks.
- **Changing the voting law** (`te_fptp_events.1`, owner request): the
  amendment leaves with the old law, so when an allowed voting law activates in
  a country that held it (`te_fptp_var`), an event asks whether to keep it.
  Keeping attaches it to the new law; declining adopts proportional
  representation (the variable goes). Moving to a law without elections keeps
  the variable, so the question comes back with elections.
- **A civil war's end** (`te_fptp_repair_after_civil_war`, in
  `te_civil_war_on_won`): the rebels hold the law they fought for from the
  outbreak, so no law activates at the end; when the winner inherits
  `te_fptp_var` on an allowed voting law without the amendment, the same
  keep-or-drop event asks.

`te_fptp_var` is kept by the monthly pulse: set while the amendment is in
force, removed when the country sits on an allowed voting law without it
(a repeal, or a declined event).

## Self-check and play-test

- `TE_SELF_CHECK OK|BROKEN fptp_major_parties`, once a game, the first time a
  country with three or more active parties refreshes: exactly two parties
  marked, no unmarked party larger than either marked one (compared pairwise,
  not through the ordering being checked, with a positive control so a
  comparison that didn't read can't pass), and the second's clout above 0.
  BROKEN means the ranking (`ordered_active_party` by a script value, or the
  `every_member` clout sum) failed; the fallback is ranking by `momentum`.
- Play-test list: `docs/testing/first-past-the-post-playtest.md` (the terms in
  the affiliation tooltip; the keep event on a voting-law change; the
  Confederacy's seed; the debate offer and the petition).

## Tooling

- `scripts/generators/gen_party_join_weights.py` writes
  `common/parties/zz_te_party_join_weights.txt` from the game files;
  `--check` exits 1 when the committed file is stale (needs the game). Added to
  the vanilla patch runbook's regenerate list.
- `test_first_past_the_post.py`: the generator's transforms, the committed
  file against a fresh generation, every party type covered by the dispatch,
  clear and terms, and the amendment's allowed laws against the petition
  trigger. Parties aren't in `vanilla_parsed/` or the mod state server (#1164).

## Not in scope

Brazil's and Iberia's `from_two_party_system` terms; a proportional
representation amendment with its own effects; Britain or other historical
plurality systems at game start.
