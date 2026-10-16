# United Nations tooltips play-test checklist

What the next play-test should look at in the UN panel's tooltips. In-game checks do not gate a merge (CLAUDE.md,
"In-game checks: self-checks and the play-test list"): a PR lands on the offline gate and adds what only the game can
show here. Each PR adds its own section, newest last, and a fixed item is struck through with the commit that fixed it.

## How to run

- **Deploy** per CLAUDE.md, "Play-testing unmerged work" (or from `main`).
- **Where to look.** The United Nations journal entry, or the UN tab of the Diplomacy panel: the overview's agency
  icons, the General Assembly's Table a Resolution rows, the resolution in session, and Our Obligations.
- **Quick setup.** `event te_debug_un.1` founds the UN and seats the great and major powers, and can have another member
  table a condemnation (`events/te_debug_un_events.txt`).
- **Logs.** Read `debug.log`, not `error.log`. Search it for `Failed parsing localized text`, `je_un_terms_` and
  `je_un_ov_agency_`.

## Every topic's terms, on four surfaces (2026-10-16)

Each topic has one terms text, `je_un_terms_<topic>`, shown in four places (docs/systems/journal_entry_systems.md,
"Terms tooltips"). Two of the four rest on patterns that are proven separately but not in this combination: a
`tooltip = "<key>"` whose loc carries a `SelectLocalization` and several `GetStaticModifier(...).GetDesc` lists, and a
tagged hover (`#tooltippable;tooltip:[GetPlayer.GetTooltipTag],<key>`) on a proposal row's title.

| Check | Expect | If it fails |
|---|---|---|
| **Agency icons.** Hover UNESCO, the IAEA and the ICJ in the overview, before and after they are founded. | The agency's name, "Founded." or "Not yet founded.", then its convention's terms with each modifier's effects listed. The ICJ says it has no effects of its own. | A blank or raw tooltip means the direct loc key does not render `SelectLocalization` there: go back to `Concatenate( Localize(...), SelectLocalization(...) )` in `gui/journal_entry_widgets/un_overview_widget.gui` for the name and status, and give the terms a second line. |
| **Proposal titles.** Hover the title of a convention (Cultural Heritage Program), a member topic (Condemnation of Aggression) and a reform in Table a Resolution. | The topic's terms, each modifier's effects, the shared outcomes and, for a convention, when the docket raises it. | Plain text with no effect lists means the tagged form failed on that row; a raw `je_un_chamber_propose_topic_*_tt` means the hover key did not resolve. |
| **The card.** With a resolution in session, hover **Its terms** at the end of the If it carries line, and again after a veto. | The same terms, with the shared outcomes under them. | A word that does not hover: check `je_un_chamber_conseq_<tag>`. |
| **Our Obligations.** As a party to a convention, hover its name. | Its full terms, not only the member modifier. | Only the member modifier means the old `je_un_chamber_conv_<key>_tt` loaded from a stale copy (search `te_unused_l_english.yml`). |
| **Length.** Hover the longest: Decolonization Resolution, Request a Peacekeeping Deployment, Charter Reform II. | The tooltip fits the screen at 1080p. | Too tall: move the shared outcomes (`$je_un_terms_common$`) off the proposal titles and keep them on the card only. |
| **UNESCO in play.** With UNESCO in force, occupy a state with a Grand Monument and carry it off. | The infamy the trophy row shows is twice the figure without UNESCO, matching the agency's tooltip. | A mismatch means `gm_trophy_values.txt` and `je_un_terms_heritage` disagree: `test_un_terms_tooltips.py` should have caught it. |
