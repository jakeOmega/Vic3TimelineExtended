# Steam Workshop description

The description for the Workshop as of 1.3.2 (2026-11-14), rewritten around six images; what changed from 1.3.1's text is at the end, and that text is in git history at the 1.3.1 tag. Paste the contents of the fenced block below into the Steam Workshop description field. Steam Workshop renders BBCode, not Markdown.

- **Length.** Steam caps a description at 8,000 characters. This one is 4,996 characters (5,020 UTF-8 bytes, 5,051 counting each line break as two), so about 2,900 are free. Measure after an edit: `python3 -c "import sys;t=open(sys.argv[1],encoding='utf-8').read().strip();print(len(t),len(t.encode()),len(t)+t.count(chr(10)))" <file>`.
- **Player guide link and image links.** Point all seven at the release's tag (`/tree/<version>/docs/player_guide/README.md` and `raw.githubusercontent.com/.../<version>/docs/workshop/<image>.jpg`), not `main`, so they show the guide and the images that shipped. They resolve only once the tag is pushed, so tag before pasting. See `docs/guides/release_checklist.md`.

## Images in the description

Steam shows `[img]URL[/img]` in a description, the URL a direct link to the image file, and `[url=...][img]...[/img][/url]` makes one a link. Read 2026-11-13:

- **Width.** Steam's `workshop.css` caps a description image at 630 px (`.workshopItemDescription img { max-width: 630px; }`), so draw them 1260 px wide, sharp on high-DPI screens, and judge each at 630.
- **Length.** The URL counts toward the 8,000 characters: with its tags, a Steam-hosted image (`images.steamusercontent.com/ugc/...`) takes about 114, a GitHub raw link about 115, an imgur one about 43.
- **Hosts.** Of the 60 most-subscribed Victoria 3 mods, 23 embed images: imgur in 14 of them, then postimg, ibb, seeusercontent and Steam's own host; 33 of the images are links. Imgur has blocked visitors from the UK since 2025-09-30, its images embedded elsewhere included, so don't host there. A GitHub raw link (`https://raw.githubusercontent.com/jakeOmega/Vic3TimelineExtended/<tag>/<path>`) keeps the images with the release they describe and is served as an image that other sites may embed; Steam shows one: the owner tried a player-guide image at the 1.3.1 tag in the description on 2026-11-14. The file has to be in the repository at that tag, and `build/workshop_composites/` is gitignored, so the description takes its six images from `docs/workshop/`. Render them there for each release (`workshop_composites.py --out docs/workshop desc_hero_ages desc_at_a_glance desc_eras desc_systems`), look at the `--preview` copies at 630 px, and commit them before the release is tagged: a link at a tag shows that tag's file, so an image changed afterwards needs a new tag or a link at a commit. Another mod's raw BBCode, to see how it embeds: `POST https://api.steampowered.com/ISteamRemoteStorage/GetPublishedFileDetails/v1/` with `itemcount=N&publishedfileids[0]=<id>...` (no key; item pages rate-limit).
- **Text in an image** isn't searchable or translated, and vanishes with its host. The description keeps the systems' names as text.

`scripts/image_pipeline/workshop_composites.py` draws the description images (a hero, an at-a-glance card, the eras, the systems as cards, a section heading) and the carousel's state-picture image, with their figures counted from the mod files when they are drawn; `workshop_screenshots.py` annotates the carousel's screenshots (2026-11-06). See `docs/guides/python_tools.md`.

```bbcode
[b]Updated for Victoria 3: 1.15.1.[/b]

[img]https://raw.githubusercontent.com/jakeOmega/Vic3TimelineExtended/1.3.2/docs/workshop/desc_hero_ages.jpg[/img]

[i]Extend Victoria 3 past 1936 into the modern era and a speculative future. Banking, climate change, the space race, the UN, and decolonization become playable systems woven into the economy, with game rules to tailor your campaign.[/i]

[b]New to the mod?[/b] The [url=https://github.com/jakeOmega/Vic3TimelineExtended/tree/1.3.2/docs/player_guide/README.md]illustrated player guide[/url] explains the mechanics. Read it online by chapter, or download the PDF from the guide page.

[img]https://raw.githubusercontent.com/jakeOmega/Vic3TimelineExtended/1.3.2/docs/workshop/desc_at_a_glance.jpg[/img]
[list]
[*]New goods, production chains, companies, combat units, ship classes, treaty articles, and decrees
[*]A dashboard for each system, a Map Room of more than 40 world maps, and new tabs in the Budget, Society, Diplomacy, Military, and Market panels
[*]English, plus machine-translated German and Spanish; English fallback for other languages
[/list]

Nineteen systems run alongside the base game. In the economy: banking and monetary policy, free market construction, power grids, and a legislated tax code. Between nations: the United Nations, the global commons, decolonization, cultural hegemony, covert warfare, nuclear weapons, a modern military, global warming, and the space race. Within them: demographics, healthcare and biotechnology, courts and judiciary, social movements, internal resettlement, and grand monuments and archaeology.

[img]https://raw.githubusercontent.com/jakeOmega/Vic3TimelineExtended/1.3.2/docs/workshop/desc_systems_1.jpg[/img]
[img]https://raw.githubusercontent.com/jakeOmega/Vic3TimelineExtended/1.3.2/docs/workshop/desc_systems_2.jpg[/img]
[img]https://raw.githubusercontent.com/jakeOmega/Vic3TimelineExtended/1.3.2/docs/workshop/desc_systems_3.jpg[/img]

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

[img]https://raw.githubusercontent.com/jakeOmega/Vic3TimelineExtended/1.3.2/docs/workshop/desc_eras.jpg[/img]

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

## What changed from 1.3.1's text

Six images from `workshop_composites.py` stand in for the title, the at-a-glance list, the systems' paragraphs and the technology paragraph, and the text that only repeated them is gone: the megastructures sentence (the eras image and the at-a-glance card have them), the game-rules bullet (the opening line and Compatibility say it) and the counts. What the images can't carry stays as text: everything no image covers, and the systems' names, for search and for a reader whose images don't load. The names are a sentence that leads into the cards, grouped by where each system acts; a bare list under the cards read as a repeat of them (owner, 2026-11-14). Against the player guide, the text gains what the description never named: the Map Room, formable countries and city-states, reunification, culture merges and bloc summits, and the World War gets a line of its own. It gives no end year (owner, 2026-11-14). Other changes: Victoria 3 1.15.1, a State Pictures line, state pictures in the AI disclosure, American spelling, and the Laws paragraph names law groups the system cards don't already cover.

`desc_hero_eras` is a hero with no pictures in it, for `desc_hero_ages`. Moving only the hero, the at-a-glance card and the eras into images saved nothing on the 1.3.1 text (8,124, over the limit): the systems' paragraphs are where the characters are.
