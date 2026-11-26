# Player guide images

Some images here are generated: `pop_spending_by_wealth.png` comes from
`scripts/player_guide_figures.py` (rerun it after changing the pop needs curves,
then rebuild the PDF). Screenshots are added by hand, as below.

Screenshots for the player guide go in this folder. The chapters mark the spots
that would benefit from one with a comment on its own line:

```
<!-- screenshot: the Banking Cycle dashboard during a Boom, policy buttons in view -->
```

`git grep -n "screenshot:" docs/player_guide` lists them. To add one:

1. Save the screenshot here as PNG (or JPEG for large scenes) with a descriptive
   name, e.g. `banking_dashboard_boom.png`. Crop to the panel that matters; at
   1080p a panel crop is usually 600–1200 pixels wide, which prints well at page
   width. Keep files under about 1 MB.
2. Replace the placeholder with an image and a caption:
   `![The Banking Cycle dashboard during a Boom.](images/banking_dashboard_boom.png)`
   The caption becomes the figure caption in the PDF. Images are scaled to the
   text width, but none is drawn taller than 17 cm, so a tall panel comes out
   narrower. Nor is one drawn larger than its pixel density says (72 ppi when
   the file has none), so a small crop, under about 800 pixels wide, would print
   at a larger scale than the panels; save it at 120 ppi (with Pillow,
   `im.save(path, dpi=(120, 120))`) and it prints at their scale, as
   `UN_mission.png` does. Figures float to the top or bottom of a page, so one
   may land a paragraph or two after its place in the text.
3. Rebuild the PDF (`.venv/bin/python scripts/build_player_guide.py`) and commit
   the image, the chapter and the PDF together.

## The shot list, and refreshing the screenshots

Every picture here, and every `<!-- screenshot: -->` spot, has an entry in the
shot manifest, `scripts/image_pipeline/guide_shots.py` (issue #2056): what the
picture shows, the chapters that use it, the files whose change can make it
stale, and, for a panel the harness can open by script, its recipe (a save, a
country, the minimums read before the shot, the view, the crop). A new picture
or a new spot needs an entry; the preflight check `guide-shots` fails until it
has one.

- **What is stale:** `python3 scripts/image_pipeline/guide_shots_stale.py`
  lists the pictures whose files changed since they were taken. Preflight
  prints it as a note and never fails on it.
- **When to refresh:** on a major release, or one known to change what a
  picture shows (owner, 2026-11-25), not in every PR that touches a panel.
- **Taking them:** `python3 -m game_qa capture --permission "<the go-ahead>"`
  takes every entry whose status is `pilot` or `entry`, in the owner's
  3840x2160 window at UI scale 1.5, with nothing of the harness drawn, and
  leaves them in a contact sheet (old, new, difference) under the backup
  root's `captures/`. Look at each new picture against its `shows` and its
  caption; then `--write` copies the changed ones here and records them in
  `guide_shots_taken.json`. Rebuild the PDF and commit the pictures, the
  chapters and the PDF together. The `assisted` and `manual` entries are still
  taken by hand.
- **Captions describe, they don't count.** A capture shows whatever the save
  holds that day, so a caption says what the panel shows ("a country holding
  warheads"), not the figures in it ("12 warheads"). An entry's `needs` are the
  minimums that make the picture true (at least one warhead); a capture whose
  save misses one skips that picture. Rewrite a caption that quotes figures when
  its picture is first replaced.
