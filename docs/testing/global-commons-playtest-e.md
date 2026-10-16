# Global Commons play-test checklist: the UN layer

The UN's part of the Global Commons (`docs/superpowers/specs/2026-10-16-global-commons-design.md`
§3, §4, §6.5; `docs/systems/mod_systems.md` § Global Commons: the UN layer). In-game checks
don't gate the merge (CLAUDE.md, "In-game checks"); the play-test before a release works through
this list. The integrator merges it with the other four Global Commons lists.

## How to run

- A late-game save with the UN founded (`event te_debug_un.1`, first option, founds it and seats
  the powers), Space Exploration researched, and, for §3, Abyssal Plain Mining somewhere.
- The seabed allocation (the seabed branch) calls `te_seabed_un_update_regime` once a year. To see
  a regime change without waiting, research Abyssal Plain Mining and wait for the yearly pass, or
  pass the Convention on the Law of the Sea from the chamber.
- The anti-satellite strike (the debris branch) calls `te_asat_un_on_strike`. Without a war, the
  docket item can be seen by striking in a test war.

## Self-checks

| Line in `debug.log` | When | OK means | BROKEN means | Fallback |
|---|---|---|---|---|
| `TE_SELF_CHECK … antarctic_policy_grant` | once a game: `START` the first month a country becomes an Antarctic Treaty party (its monthly pulse adds `un_antarctic_policy_modifier`), the verdict a week later (`te_global_commons_un.1`) | the country's `country_un_authority_target_add` rose by the treaty's 0.25 (`added` ≈ `expected`): a script-only type added by `add_modifier` reaches the modifier read the Policy pillar sums (un_redesign_design.md §0.10's checklist, never yet seen in game) | `added` 0: the Policy pillar sees no modifier grant added by script, the treaty's and the nuclear doctrines' alike. A whole-step gap is a law change in the week (the line prints both figures) | grant the 0.25 through a script value the pillar adds directly (`un_policy_contribution` + a party term), and check the doctrine grants the same way |

No `antarctic_policy_grant` line means nobody ratified an Antarctic Treaty: open a station (the
decision), wait for the docket's item, and vote the treaty through. A `START` with no verdict means
the country left the treaty within the week; the check re-arms for the next party.

Nothing else here rests on an unverified engine fact: the royalty is billed as dues are
(`multiplier = var:` from the country pulse), the station's and the treaty's modifiers are vanilla
types, and every trigger, docket item and vote follows a pattern already seen in game.

## The Law of the Sea and the seabed

- [ ] With the Law of the Sea in force and nobody holding Abyssal Plain Mining, the Seabed section
      reads the regime as Open, and Our Obligations shows no seabed lines under the convention.
- [ ] The first country researches Abyssal Plain Mining; at the next yearly pass the regime is
      Regulated and every country with the technology gets "The Law of the Sea Regulates the Seabed".
- [ ] The convention's hover (Table a Resolution, Our Obligations, the ITLOS icon) lists the seabed
      terms.
- [ ] A party with Deep-Sea Mines pays royalties: Our Obligations shows "Royalties: N a week",
      N ≈ 1,788 × its levels, and the Budget panel's Breakdown counts them under United Nations.
- [ ] With the World Development Fund standing, its pot (the chamber's Fund row) grows by the
      royalties; without it, the UN budget does.
- [ ] A poorer party sees "Reserved half" in Our Obligations; a richer one does not.
- [ ] A party switches to Unilateral Licensing: +10 infamy, −5 standing (Our Record: "we licensed
      seabed mining on our own terms"), +10 case strength, and "Defected" in Our Obligations; no
      royalties from the next month.
- [ ] It switches back to Sponsor Contractors: "Returning: a party again in 60 months", counting down;
      switching to Scientific Survey in between does not restart it.
- [ ] A member that refused the convention switches to Unilateral Licensing: no infamy, standing or
      case cost.
- [ ] Two great powers on Unilateral Licensing: at the next yearly pass the regime is a Scramble
      ("A Scramble for the Seabed"), and royalties stop. One leaves: two yearly passes later the
      regime is Regulated again.
- [ ] Under the disabled United Nations rule the regime stays Open.
- [ ] A revolution's winner that was a party pays royalties again the month after the war, and
      keeps a defection's cooldown.

## The Antarctic research station and the Antarctic Treaty

- [ ] With Space Exploration, the decision Open an Antarctic Research Station is offered (under the
      Global Commons rule only); taking it shows +2% research speed and +25 innovation cap, and an
      upkeep of 0.1% of GDP a year, at least 1,000 a week, under Space Race in the Breakdown.
- [ ] The AI opens stations: great and major powers with the surplus, smaller powers only with a
      Southern coastline or as treaty parties, none in default. About thirty countries is the
      target (the real number); far more means the weights in `te_decision_open_antarctic_station`
      need lowering.
- [ ] The first station puts the Antarctic Treaty on the docket (the chamber's last item: "the first
      Antarctic research station of X, and the Antarctic Treaty"); a human member with Space
      Exploration is offered it first.
- [ ] The treaty carries: the ATS icon lights, parties gain +2% prestige (×E), a party with a station
      gains "Station science shared" (+3% research speed) at its next monthly UN review, and the
      Policy row of Why Authority Is Moving rises by about 0.25 × each party's weight.
- [ ] A party holds no new Southern seabed licences in the seabed section; its built Southern levels
      keep theirs.
- [ ] A party denounces it by decision: +10 infamy, −5 standing ("we denounced the Antarctic Treaty"),
      +10 case; the treaty's line leaves Our Obligations; leaving and rejoining the UN does not
      re-ratify it.
- [ ] Two great powers outside the treaty hold Southern licences: within a month the treaty lapses,
      every member gets "The Antarctic Treaty Lapses", the ATS icon goes dark, and the docket does not
      raise it again while the condition holds.
- [ ] Closing the station removes its modifiers and the treaty's station term at the next review.
- [ ] A revolution's winner keeps its station (research and upkeep back the month after the war).

## The Moratorium on Destructive Anti-Satellite Tests

- [ ] Before any strike the moratorium's chamber row says a strike must have been made.
- [ ] After a strike the docket takes it up (score 55; "a destructive anti-satellite strike by X, and
      the Moratorium on Destructive Anti-Satellite Tests"); the striker is never offered it and cannot
      table it for two years.
- [ ] It carries: the UNODA icon lights, parties gain +5% prestige (×E).
- [ ] A party's own strike costs twice the infamy and twice the case strength (the strike's tooltip).
- [ ] Once a year a party with a debris-removal method books "a party to the anti-satellite
      moratorium kept orbit clean" in Recent Entries, and the Delivery pillar rises by about
      0.25 × its weight.
- [ ] Under the disabled Space Race rule the row is hidden and the docket never raises it.
