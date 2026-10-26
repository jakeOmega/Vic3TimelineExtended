# Steam Workshop description

The description as published on the Workshop (1.2.0, 2026-10-26). Paste the contents of the fenced block below into the Steam Workshop description field. Steam Workshop renders BBCode, not Markdown.

- **Length.** Steam caps a description at 8,000 characters. This one is 7,746 characters (7,798 UTF-8 bytes, 7,837 counting each line break as two), so it fits however Steam counts. Measure after an edit: `python3 -c "import sys;t=open(sys.argv[1],encoding='utf-8').read().strip();print(len(t),len(t.encode()),len(t)+t.count(chr(10)))" <file>`.
- **Player guide link.** Point it at the release's tag (`/tree/<version>/docs/player_guide/README.md`), not `main`, so it shows the guide that shipped. See `docs/guides/release_checklist.md`.

## Images to add

When you have screenshots ready, paste `[img]<steam-hosted-url>[/img]` at these locations in the BBCode block below:

1. **Hero image** — between the tagline italic and the `[hr]` above "At a glance". Strongest candidates: Saturn V / lunar landing, a flooded-coastline or wildfire climate scene, or a UN founding scene. Pick whichever best matches the timeline framing.
2. **Banking Cycle JE** — after the Banking Cycle bullet. Mid-cycle screenshot with the phase indicator on a non-stable phase (Boom or Downturn) and the policy buttons + progress bar in frame.
3. **Space Race JE** — after the Space Race bullet. Milestone progress and the contested-site map; mid-game with a couple of milestones already claimed by other countries reads more dramatic than an empty start.
4. **UN panel** — after the United Nations bullet. Authority bar, Security Council seats, and ideally an active vote / resolution. Bonus if a specialized agency tab is visible.
5. **Civil Rights JE** — after the Social Movements bullet. Support progress bar plus the pro/anti/coopt policy button grid. Alternative: an event image from a movement event chain (feminist / LGBTQ+ / environmental).
6. **Laws panel** — under the "Laws and ideologies" header. Filtered to a uniquely-modern lawgroup (cryptocurrency / surveillance / AI governance / post-scarcity) so the visible options are obviously not vanilla. Alternative: a single-law detail view for a flagship law like UBI or Mass Surveillance.

```bbcode
[h1]Vic3TimelineExtended[/h1]

[b]Updated for Victoria 3: 1.14.5.[/b]

[i]Extend Victoria 3 past 1936 into the modern era and a speculative future. Banking, climate change, the space race, the UN, and decolonization become playable systems woven into the economy, with game rules to tailor your campaign.[/i]

[b]New to the mod?[/b] The [url=https://github.com/jakeOmega/Vic3TimelineExtended/tree/1.2.0/docs/player_guide/README.md]illustrated player guide[/url] explains the mechanics. Read it online by chapter, or download the PDF from the guide page.

[h1]At a glance[/h1]
[list]
[*]Around 160 technologies across 7 new eras, from interwar industry to a speculative future
[*]New goods, production chains, company buildings, wonders, and megastructures
[*]100+ new laws, plus new combat units, ship classes, treaty articles, decrees, and companies
[*]Hundreds of events, concept tooltips, and mechanical breakdowns
[*]Visual dashboards and dedicated controls, with new tabs in the Budget, Society, Diplomacy, Military, and Market panels
[*]Toggleable game rules for the major systems
[*]English, plus machine-translated German and Spanish; English fallback for other languages
[/list]

[hr][/hr]

[h1]New systems[/h1]

[b]Banking and Monetary Policy[/b] — Navigate booms, bubbles, crashes, and contagion. Set interest rates, manage inflation and gold reserves, intervene in currency flows, or negotiate pegs and monetary unions. Delegate policy or take direct control.

[b]Space Race[/b] — Compete from suborbital flight to solar-system colonies and an interstellar probe. Choose your approach, fund your programme, and estimate rivals' progress. Launch in real orbital windows, manage orbital debris, and earn lasting rewards. An optional rule adds colony fleets, settlers, and modules.

[b]Global Warming[/b] — Track rising temperatures, the largest emitters, and your own emissions. Tax carbon, retire fossil capacity, and build renewables, carbon capture, and adaptation. Treaties can bind rivals to emissions cuts, and penalties grow as the climate degrades.

[b]United Nations[/b] — Pass resolutions, wield Security Council vetoes, and build agencies and conventions. Lobby delegations, impose sanctions, fund peacekeeping and aid, and refer crimes to the court. Its authority sets how much its decisions matter.

[b]Global Commons[/b] — Deep-sea mines need licences from five ocean basins, shared out by coastline and naval power. Protect, lease, or blockade claims, and negotiate the Law of the Sea and an Antarctic Treaty.

[b]Nuclear Weapons[/b] — Build a deterrent, choose doctrine and readiness, and navigate proliferation crises and retaliation. A shifting nuclear taboo shapes the cost of possession, threats, and use. Negotiate arsenal limits or renounce the bomb.

[b]Decolonization[/b] — Colonial stability responds to investment, garrisons, assimilation, and pressure for independence. Arrange a managed handover, or fight a war of independence that is hard to win and buys years, not peace.

[b]Covert Warfare[/b] — Build intelligence networks and run election interference, financial subversion, sabotage, and cyber operations. Weigh funding against detection, and watch the operations you catch.

[b]Cultural Hegemony[/b] — Compete for global cultural influence through prestige, art, technology, and monuments. Promote your political model, attract migrants and tourists, and pressure rivals.

[b]Modern Military[/b] — Mix unit types for combined-arms bonuses. Aviation, missiles, drones, and modern ships extend the vanilla roster, and military installations provide strategic targets.

[b]Social Movements[/b] — Civil rights, feminism, LGBTQ+ rights, environmentalism, secularization, human augmentation, digital rights, and the post-scarcity transition bring event chains and journal entries.

[b]Free Market Construction[/b] — Construction is a traded good bought by governments and private investors; upkeep and retooling compete for the same supply. Based on TOGFan's mod, credited below.

[b]Power Grids[/b] — Grid Transfer Stations share electricity between states, and undersea interconnectors and grid agreements join grids across seas and borders.

[b]Courts and Judiciary[/b] — Six court laws, from Executive Tribunals to Algorithmic Jurisprudence. Independent courts can strike down laws you force through: comply, defy, or pack them.

[b]Grand Monuments and Archaeology[/b] — Raise monuments to your regime, ruler, faith, or nation, as grand as their cost to their age. In 1836, 93 landmarks already stand; carry them off as trophies, bring them home, and dig up 36 buried sites such as Pompeii.

[b]Legislated Tax Code (experimental)[/b] — Pass tax bills, win votes with concessions, and offer relief, while AI governments legislate their own.

[b]Healthcare and Biotechnology[/b] — Healthcare is a need your pops demand, met by pharmaceuticals, biotechnology companies, and new laws.

[b]Internal Resettlement[/b] — Settle sparse regions through Settlement Authorities, by voluntary or coercive programmes, or retreat from environmental damage.

[h2]More ways to shape your country[/h2]

[b]Tourism[/b] — Historic sites, pollution, turmoil, infrastructure, and air travel shape demand.
[b]Strategic Reserves[/b] — Stockpile food, fuel, and military supplies; buy low, release in shortages.
[b]Wealth Concentration[/b] — Inheritance laws decide who inherits; great fortunes strengthen elites and feed bubbles.
[b]Migration and Homelands[/b] — Crowded states attract fewer migrants, and homelands form or dissolve with acceptance and population.
[b]Living-Standard Expectations[/b] — Sustained prosperity raises the bar, so a later downturn is harder to accept.
[b]Power Blocs[/b] — New principles and identities, with names that reflect your bloc's members.
[b]Personal Play Options[/b] — Educate an heir, create a custom religion, enable aptitude traits for all adults, or turn on the World War system.

[hr][/hr]

[h1]Technology, laws, and society[/h1]

Progress from interwar aviation and atomics through computing, biotechnology, AI, fusion, and space colonization. Build space elevators, orbital solar collectors, and antimatter facilities.

Shape inheritance, minority rights, the courts, financial regulation, family policy, internet governance, genetic modification, and universal basic income, or entrench two parties with first past the post. New ministries cover science, the environment, intelligence, and urban planning. New ideologies include environmentalists, anti-colonialists, transhumanists, and business-interest movements, alongside Green, Populist, and Technocratic parties.

[h1]Compatibility[/h1]

The mod changes vanilla ideologies, production methods, state-region data, and several interface panels, so mods editing the same content may conflict. Load this mod [b]last[/b]. Major systems can be switched off at game setup, but the baseline technologies, laws, and buildings remain.

[h1]Feedback and AI-generated content[/h1]

Report bugs here or on the [url=https://github.com/jakeOmega/Vic3TimelineExtended/issues]issue tracker[/url], ideally with steps to reproduce, [i]error.log[/i] or [i]debug.log[/i] snippets, and a save. Feedback on unclear mechanics is welcome.

The mod contains AI-generated event images, icons, and some flavor text. Hand-written text and hand-drawn art are welcome through issues or pull requests.

[h1]Links and credits[/h1]
[list]
[*][url=https://github.com/jakeOmega/Vic3TimelineExtended]Source repository[/url]
[*][url=https://steamcommunity.com/sharedfiles/filedetails/?id=3257202613]Free Market Construction[/url] by [b]TOGFan[/b] — the basis for the construction-market subsystem; recommended on its own if you want just that mechanic.
[/list]
```
