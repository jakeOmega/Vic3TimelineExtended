# Release checklist

How a release is cut, from `main` to the Workshop and GitHub. 1.1.9 (2026-10-18) shipped from `main` without a tag or GitHub release, and was tagged after the fact at the last merge before the upload (`b9cf896e`). Tag on the day you upload.

## 1. Before cutting

- CI green on `main`'s head.
- Translations current: `python3 scripts/i18n/translate_loc.py --language german status` (and `spanish`) shows 0 stale and 0 missing; otherwise run a pass (`i18n/README.md`).
- Work through the play-test lists marked "Before a release play-test" in `docs/README.md` (`docs/testing/`), and read the latest `TE_SELF_CHECK` lines.
- Leave open any PR that removes an old-save repair a player updating from the last release still needs.

## 2. What ships

From 1.2.0 a release ships `main` as it stands, the Demographics census included (owner, 2026-10-26). Set `.metadata/metadata.json`'s version on `main`, write the notes to `docs/releases/<version>.md` (Markdown, one bullet per area; the Workshop's change notes take the same bullets as a BBCode `[list]`, and 1.3.2's 7,000 characters fit), merge, and release the merged commit.

The same PR carries the Workshop description (`docs/audits/steam_workshop_description.md`): its six images, redrawn into `docs/workshop/` (`scripts/image_pipeline/workshop_composites.py --out docs/workshop --preview desc_hero_ages desc_at_a_glance desc_eras desc_systems`; their figures are counted from the mod files when they are drawn, so draw them last and don't commit the `_630` previews), and the version in its seven links, the guide's and the six images'. The links are GitHub raw links at the tag, so the images must be in the commit that is tagged.

Write the notes from what the release changes against the last tag, not from the PR titles: where two PRs moved the same thing, give the end state, and leave out a fault that was introduced and fixed between the two tags (1.3.2: the Space Elevator's sites went to a latitude rule and back, and the United Nations of Earth's great-power test broke and was mended, neither of which a 1.3.1 player ever saw). `git diff <last tag>..origin/main -- docs/player_guide/*.md` gives the figures as the guide states them now. A PR whose guide line reads "no player-facing change" can still be a fix a player sees, so pick the PRs by whether they touch `common/`, `events/`, `gui/`, `localization/` or `gfx/`.

A release that must ship without the census (1.1.8 was one) goes out on a branch that is never merged back:

```bash
git switch -c release/<version> origin/main
python3 scripts/release/comment_out_census_inputs.py
python3 scripts/format_paradox_tabs.py $(git diff --name-only -- common/)
git add common/
git commit -m "Release <version>: the census's inputs commented out"
git push -u origin release/<version>
```

Expected on such a branch, by design: `organize_loc.py --check` wants to move the commented-out rule's loc keys to `te_unused_l_english.yml` (leave them), `empty_effect_audit` flags the `if` in `te_demog_fl_apply` the script empties, and `test_release_census_inputs` and `test_demographics_registry`'s rule tests fail because they describe `main`. Every other CI check passed on the 1.2.0 dry run. The player guide on such a branch still describes the census as shipped.

## 3. Upload, tag, publish

1. From the full checkout (not a sparse worktree: `deploy.sh` would delete `gfx/`): `./scripts/deploy.sh`, read the dry run, then `--apply`, and upload to the Workshop with the change notes.
2. Tag the commit you uploaded and publish the GitHub release (title = tag, as for 1.1.x):
   ```bash
   git tag <version> && git push origin <version>
   gh release create <version> --title <version> --notes-file docs/releases/<version>.md
   ```
3. Workshop description: paste the block from `docs/audits/steam_workshop_description.md` once the tag is pushed. Its guide link and its six image links point at the tag (`.../tree/<version>/docs/player_guide/README.md`, `raw.githubusercontent.com/.../<version>/docs/workshop/<image>.jpg`), so they show the guide and the images that shipped, and show nothing before the tag exists. Keep the text under Steam's 8,000-character limit.
