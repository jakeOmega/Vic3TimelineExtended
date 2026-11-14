# Steam Workshop description

The description for the Workshop as of 1.3.1 (2026-11-09; the text is 1.3.0's with the guide link moved to the new tag, and 1.2.0's is in git history). Paste the contents of the fenced block below into the Steam Workshop description field. Steam Workshop renders BBCode, not Markdown.

- **Length.** Steam caps a description at 8,000 characters. This one is 7,848 characters (7,902 UTF-8 bytes, 7,941 counting each line break as two), so it fits however Steam counts. Measure after an edit: `python3 -c "import sys;t=open(sys.argv[1],encoding='utf-8').read().strip();print(len(t),len(t.encode()),len(t)+t.count(chr(10)))" <file>`.
- **Player guide link.** Point it at the release's tag (`/tree/<version>/docs/player_guide/README.md`), not `main`, so it shows the guide that shipped. See `docs/guides/release_checklist.md`.

## Images in the description

Steam shows `[img]URL[/img]` in a description, the URL a direct link to the image file, and `[url=...][img]...[/img][/url]` makes one a link. Read 2026-11-13:

- **Width.** Steam's `workshop.css` caps a description image at 630 px (`.workshopItemDescription img { max-width: 630px; }`), so draw them 1260 px wide, sharp on high-DPI screens, and judge each at 630.
- **Length.** The URL counts toward the 8,000 characters: with its tags, a Steam-hosted image (`images.steamusercontent.com/ugc/...`) takes about 114, a GitHub raw link about 115, an imgur one about 43.
- **Hosts.** Of the 60 most-subscribed Victoria 3 mods, 23 embed images: imgur in 14 of them, then postimg, ibb, seeusercontent and Steam's own host; 33 of the images are links. Imgur has blocked visitors from the UK since 2025-09-30, its images embedded elsewhere included, so don't host there. A GitHub raw link (`https://raw.githubusercontent.com/jakeOmega/Vic3TimelineExtended/<tag>/<path>`) keeps the images with the release they describe and is served as an image that other sites may embed; Steam shows one: the owner tried a player-guide image at the 1.3.1 tag in the description on 2026-11-14. The file has to be in the repository at that tag, and `build/workshop_composites/` is gitignored, so the draft below takes the images from `docs/workshop/`, rendered there (`--out docs/workshop`) and committed before the release is tagged. Another mod's raw BBCode, to see how it embeds: `POST https://api.steampowered.com/ISteamRemoteStorage/GetPublishedFileDetails/v1/` with `itemcount=N&publishedfileids[0]=<id>...` (no key; item pages rate-limit).
- **Text in an image** isn't searchable or translated, and vanishes with its host. The draft below keeps the systems' names as text.

`scripts/image_pipeline/workshop_composites.py` draws the description images (a hero, an at-a-glance card, the eras, the systems as cards, a section heading) and the carousel's state-picture image, with their figures counted from the mod files when they are drawn; `workshop_screenshots.py` annotates the carousel's screenshots (2026-11-06). See `docs/guides/python_tools.md`.

```bbcode
[h1]Vic3TimelineExtended[/h1]

[b]Updated for Victoria 3: 1.15.0.[/b]

[i]Extend Victoria 3 past 1936 into the modern era and a speculative future. Banking, climate change, the space race, the UN, and decolonization become playable systems woven into the economy, with game rules to tailor your campaign.[/i]

[b]New to the mod?[/b] The [url=https://github.com/jakeOmega/Vic3TimelineExtended/tree/1.3.1/docs/player_guide/README.md]illustrated player guide[/url] explains the mechanics. Read it online by chapter, or download the PDF from the guide page.

[h1]At a glance[/h1]
[list]
[*]Around 190 technologies across 8 new eras, from interwar industry to a speculative future
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

[b]Space Race[/b] — Compete from suborbital flight to solar-system colonies and an interstellar probe. Choose your approach, fund your programme, and estimate rivals' progress. Launch in real orbital windows, manage orbital debris, and earn lasting rewards. Colony fleets carry settlers and modules from the Moon outward, and warships in space blockade, seize, or destroy colonies.

[b]Global Warming[/b] — Track rising temperatures, the largest emitters, and your own emissions. Tax carbon, retire fossil capacity, and build renewables, carbon capture, and adaptation. Treaties can bind rivals to emissions cuts, and penalties grow as the climate degrades.

[b]Demographics[/b] — Every state keeps a census by age and sex that sets its births, deaths, and workforce. Set the pension age and family policy, extend lives, and watch your population age.

[b]United Nations[/b] — Pass resolutions, wield Security Council vetoes, and build agencies and conventions. Lobby delegations, impose sanctions, fund peacekeeping and aid, and refer crimes to the court. Its authority sets how much its decisions matter.

[b]Global Commons[/b] — Deep-sea mines need licences from five ocean basins, shared out by coastline and naval power. Protect, lease, or blockade claims, and negotiate the Law of the Sea and an Antarctic Treaty.

[b]Nuclear Weapons[/b] — Build a deterrent, choose doctrine and readiness, and navigate proliferation crises and retaliation. A shifting nuclear taboo shapes the cost of possession, threats, and use. Negotiate arsenal limits or renounce the bomb.

[b]Decolonization[/b] — Colonial stability responds to investment, garrisons, assimilation, and pressure for independence. Arrange a managed handover, or fight a war of independence that is hard to win and buys years, not peace.

[b]Covert Warfare[/b] — Build intelligence networks and run election interference, financial subversion, sabotage, and cyber operations. Weigh funding against detection, and watch the operations you catch.

[b]Cultural Hegemony[/b] — Compete for global cultural influence through prestige, art, technology, and monuments. Promote your political model, attract migrants and tourists, and pressure rivals.

[b]Modern Military[/b] — Mix unit types for combined-arms bonuses. Aviation, missiles, drones, and modern ships extend the vanilla roster.

[b]Social Movements[/b] — Civil rights, feminism, LGBTQ+ rights, environmentalism, secularization, human augmentation, digital rights, and the post-scarcity transition bring event chains and journal entries.

[b]Free Market Construction[/b] — Construction is a traded good that governments and private investors buy, and upkeep and retooling compete for it. Based on TOGFan's mod.

[b]Power Grids[/b] — Grid Transfer Stations share electricity between states, and undersea interconnectors and grid agreements join grids across seas and borders.

[b]Courts and Judiciary[/b] — Six court laws, from Executive Tribunals to Algorithmic Jurisprudence. Independent courts can strike down laws you force through: comply, defy, or pack them.

[b]Grand Monuments and Archaeology[/b] — Raise monuments to your regime, ruler, faith, or nation, as grand as their cost to their age. In 1836, 93 landmarks already stand; carry them off as trophies, bring them home, and dig up 36 buried sites such as Pompeii.

[b]Legislated Tax Code (experimental)[/b] — Pass tax bills, win votes with concessions, and offer relief, while AI governments legislate their own.

[b]Healthcare and Biotechnology[/b] — Pops demand healthcare, met by pharmaceuticals, biotech companies, and new laws.

[b]Internal Resettlement[/b] — Settle sparse regions through Settlement Authorities, by voluntary or coercive programmes, or retreat from environmental damage.

[h2]More ways to shape your country[/h2]

[b]Tourism[/b] — Historic sites, pollution, turmoil, infrastructure, and air travel shape demand.
[b]Strategic Reserves[/b] — Stockpile food, fuel, and military supplies; buy low, release in shortages.
[b]Dynastic Wealth[/b] — Inheritance laws decide who inherits; great fortunes strengthen elites and feed bubbles.
[b]Migration and Homelands[/b] — Crowded states attract fewer migrants, and homelands form or dissolve with acceptance and population.
[b]Living-Standard Expectations[/b] — A long boom makes a later downturn harder to accept.
[b]Power Blocs[/b] — New principles and identities, with names that reflect your bloc's members.
[b]Personal Play Options[/b] — Heir education, custom religions, aptitude traits for all adults, and a World War system.

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

## Draft for the next release

Not yet published (proposed 2026-11-14). Six images from `workshop_composites.py` stand in for the title, the at-a-glance list, the systems' paragraphs and the technology paragraph, and the text that only repeated them is gone: the megastructures sentence (the eras image and the at-a-glance card have them), the game-rules bullet (the opening line and Compatibility say it) and the counts. What the images can't carry stays as text: everything no image covers, and the systems' names, for search and for a reader whose images don't load. The names are a sentence that leads into the cards, grouped by where each system acts; a bare list under the cards read as a repeat of them (owner, 2026-11-14). Against the player guide, the text gains what the description never named: the Map Room, formable countries and city-states, reunification, culture merges and bloc summits, and the World War gets a line of its own. It gives no end year (owner, 2026-11-14). Other changes from the published text: Victoria 3 1.15.1, a State Pictures line, state pictures in the AI disclosure, American spelling, and the Laws paragraph names law groups the system cards don't already cover.

With a five-character tag it is 5,051 characters counting each line break as two, so about 2,900 are free. Before publishing: render the images into `docs/workshop/`, commit them, tag, and put the tag in place of each `<tag>` (seven: six images and the guide link). `desc_hero_eras` is a hero with no pictures in it, for `desc_hero_ages`. Moving only the hero, the at-a-glance card and the eras into images saved nothing on the 1.3.1 text (8,124, over the limit): the systems' paragraphs are where the characters are.

```bbcode
[b]Updated for Victoria 3: 1.15.1.[/b]

[img]https://raw.githubusercontent.com/jakeOmega/Vic3TimelineExtended/<tag>/docs/workshop/desc_hero_ages.jpg[/img]

[i]Extend Victoria 3 past 1936 into the modern era and a speculative future. Banking, climate change, the space race, the UN, and decolonization become playable systems woven into the economy, with game rules to tailor your campaign.[/i]

[b]New to the mod?[/b] The [url=https://github.com/jakeOmega/Vic3TimelineExtended/tree/<tag>/docs/player_guide/README.md]illustrated player guide[/url] explains the mechanics. Read it online by chapter, or download the PDF from the guide page.

[img]https://raw.githubusercontent.com/jakeOmega/Vic3TimelineExtended/<tag>/docs/workshop/desc_at_a_glance.jpg[/img]
[list]
[*]New goods, production chains, companies, combat units, ship classes, treaty articles, and decrees
[*]A dashboard for each system, a Map Room of more than 40 world maps, and new tabs in the Budget, Society, Diplomacy, Military, and Market panels
[*]English, plus machine-translated German and Spanish; English fallback for other languages
[/list]

Nineteen systems run alongside the base game. In the economy: banking and monetary policy, free market construction, power grids, and a legislated tax code. Between nations: the United Nations, the global commons, decolonization, cultural hegemony, covert warfare, nuclear weapons, a modern military, global warming, and the space race. Within them: demographics, healthcare and biotechnology, courts and judiciary, social movements, internal resettlement, and grand monuments and archaeology.

[img]https://raw.githubusercontent.com/jakeOmega/Vic3TimelineExtended/<tag>/docs/workshop/desc_systems_1.jpg[/img]
[img]https://raw.githubusercontent.com/jakeOmega/Vic3TimelineExtended/<tag>/docs/workshop/desc_systems_2.jpg[/img]
[img]https://raw.githubusercontent.com/jakeOmega/Vic3TimelineExtended/<tag>/docs/workshop/desc_systems_3.jpg[/img]

[h1]More ways to shape your country[/h1]

[b]World War[/b] — Tension between great powers of opposed ideologies builds to a world war and its aftermath.
[b]Formables and Reunification[/b] — Ten new formable countries, 22 releasable city-states, and divided peoples who press for reunion by war or by consent.
[b]Strategic Reserves[/b] — Stockpile food, fuel, and military supplies; buy low, release in shortages.
[b]Tourism[/b] — Historic sites, pollution, turmoil, infrastructure, and air travel shape demand.
[b]Dynastic Wealth[/b] — Inheritance laws decide who inherits; great fortunes strengthen elites and feed bubbles.
[b]Migration and Homelands[/b] — Crowded states attract fewer migrants, and homelands form or dissolve with acceptance and population.
[b]Culture Merges[/b] — Related cultures can grow into one national culture over decades (off by default).
[b]Living-Standard Expectations[/b] — A long boom makes a later downturn harder to accept.
[b]Power Blocs[/b] — New principles and identities, summits, and names that reflect your bloc's members.
[b]State Pictures[/b] — The state banner follows technology, city size, and wealth: 356 new pictures of cities, ports, mines, farms, smog, and ruins.
[b]Rulers and Religion[/b] — Heir education, aptitude traits for all adults, and a custom religion creator.

[img]https://raw.githubusercontent.com/jakeOmega/Vic3TimelineExtended/<tag>/docs/workshop/desc_eras.jpg[/img]

[h1]Laws and politics[/h1]

Legislate minority rights, inheritance, privacy, internet governance, genetic modification, automation, frontier AI, the rules of war, and universal basic income, or entrench two parties with first past the post. Sixteen new ministries run from science and the environment to intelligence and urban planning. New ideologies include environmentalists, anti-colonialists, transhumanists, and corpocrats, alongside Green, Populist, and Technocratic parties.

[h1]Compatibility[/h1]

The mod changes vanilla ideologies, production methods, state-region data, and several interface panels, so mods editing the same content may conflict. Load this mod [b]last[/b]. Major systems can be switched off at game setup, but the baseline technologies, laws, and buildings remain.

[h1]Feedback and AI-generated content[/h1]

Report bugs here or on the [url=https://github.com/jakeOmega/Vic3TimelineExtended/issues]issue tracker[/url], ideally with steps to reproduce, [i]error.log[/i] or [i]debug.log[/i] snippets, and a save. Feedback on unclear mechanics is welcome.

The mod contains AI-generated event images, state pictures, icons, and some flavor text. Hand-written text and hand-drawn art are welcome through issues or pull requests.

[h1]Links and credits[/h1]
[list]
[*][url=https://github.com/jakeOmega/Vic3TimelineExtended]Source repository[/url]
[*][url=https://steamcommunity.com/sharedfiles/filedetails/?id=3257202613]Free Market Construction[/url] by [b]TOGFan[/b] — the basis for the construction-market subsystem; recommended on its own if you want just that mechanic.
[/list]
```
