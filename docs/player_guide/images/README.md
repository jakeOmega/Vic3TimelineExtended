# Player guide images

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
   text width.
3. Rebuild the PDF (`.venv/bin/python scripts/build_player_guide.py`) and commit
   the image, the chapter and the PDF together.
