# City-states and formable flags play-test checklist

What the next play-test should look at in the releasable city-states (`common/country_creation/te_city_states.txt`)
and the new flags (`common/coat_of_arms/coat_of_arms/te_city_states.txt`, `te_formable_countries.txt`, and ZHO in
`common/flag_definitions/te_formable_countries.txt`). In-game checks do not gate a merge (CLAUDE.md, "In-game checks:
self-checks and the play-test list"): a PR lands on the offline gate and adds what only the game can show here. Each
PR adds its own section, newest last, and a fixed item is struck through with the commit that fixed it.

## How to run

- **Deploy** per CLAUDE.md, "Play-testing unmerged work" (or from `main`).
- **Where to look.** The Diplomacy panel's Releasable Countries list; the map and the state panel after a release; the
  flag in the top bar and the Countries list. Console: `tag GBR` to play the holder, then release from the panel.
- **Logs.** Read `debug.log`, not `error.log`. Search it for `te_city_states`, `country_creation`, `coat_of_arms` and
  each new tag (`SGP`, `HKG`, …).

## Releasable city-states (2026-10-31)

The mechanism is vanilla's (Hamburg, Bremen, Danzig, Krakow list `provinces`), so the release itself should work. What
nobody has read in this game is how a split divides pops and buildings, and whether a city that holds a capital state's
hub province can be released cleanly. The offline estimates assume pops divide as resources do (hub provinces count
five times); the guide only claims the resource share.

| Check | Expect | If it fails |
|---|---|---|
| **A start-date release.** As Great Britain, release Singapore; as Portugal, Macau and Goa; as France, Pondicherry. | Each appears in the Releasable Countries list from 1836, releases as a one-province country with its own name, adjective and flag, and Britain keeps its other two Malayan provinces as a smaller Malaya. | Missing from the list: the release needs something the holder lacks (a `possible` block, or every listed province). A blank or random flag: the coat of arms key didn't load (check `debug.log` for the file). |
| **The pop and building split.** In the Singapore release, compare Britain's Malaya pops and buildings before and after. | Roughly 45% of the state's pops and buildings go to Singapore (one hub province of Britain's three, two of them hubs) if pops split by the resource weights. | A very different share is fine for play but means the planning note in the PR is wrong; write down the real rule in `docs/vanilla/vanilla_states_reference.md` § 1.2. |
| **New York takes two provinces.** As the USA, release New York. | New York City and Long Island go; the rest of New York state stays American. | Only one province released: a multi-province `provinces` list needs all of them owned, or takes a subset; note which. |
| **The Hong Kong treaty port.** As Britain, win a treaty port of Eastern Guangdong from China (the Opium War), then open the Releasable Countries list. | Hong Kong is listed: the treaty port is its province. | Not listed: the treaty port takes a different province than the port hub; compare its province with `xB03161`. |
| **A capital state's hub.** As the Ottoman Empire, release Constantinople; as the Argentine Confederation, release Buenos Aires. | The release works and the capital stays in the rest of Eastern Thrace or Buenos Aires state. | The button is greyed (the engine refuses to release a capital province) or the capital jumps elsewhere: add a `possible` guard on the releasing country's capital, or accept it. |
| **The game rule.** Start once with Releasable Nations set to Historically Plausible. | San Francisco is absent from the USA's (or Mexico's) list; every other city-state still shows. | The rule's flag name differs in this version: compare `has_game_rule = plausible_releasable_nations` with vanilla's Jan Mayen entry. |
| **Overlap with a vanilla releasable.** Hold all of Lahej's land, release Aden, then look at Lahej in the list (and the reverse). | Whichever goes first takes Aden's province; the other is still offered with what is left. | Lahej disappears for good after Aden's release: note it; the owner accepted the overlap. |
| **Liberate Country.** As a great power, start a play against the holder of a city-state with a Liberate Country war goal and win it. | The city-state is released with its province and flag. | No Liberate Country goal for it: the goal needs something the city-state lacks; note what. |

## Formable flags (2026-10-31)

| Check | Expect | If it fails |
|---|---|---|
| **The seven new flags.** Form the African Union, East African Federation, European Union, Intermarium, North American Union, United Earth and Dar-Al-Islam, or read them on a start where one exists. | Each flies the flag in the PR's preview sheet, not a random one. | A random flag: the coat of arms named after the tag didn't load. |
| **China follows its government.** Form the mod's China, then change its Governance Principles: a monarchy, a republic, a council republic. | The Qing dragon (a Manchu monarch) or the Han-empire flag, then the republican flag, then the red flag: vanilla China's set. | The same flag throughout: the ZHO `flag_definitions` block isn't read. |
