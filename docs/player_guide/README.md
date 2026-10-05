# Vic3TimelineExtended player guide

A guide to the mod's systems for players who know Victoria 3 but not this mod.

**[Download the PDF](Vic3TimelineExtended_Player_Guide.pdf)**, or read it here
chapter by chapter:

1. [Introduction](01-introduction.md): game rules, installation and load order
2. [The extended timeline](02-timeline.md)
3. [Economy and construction](03-economy.md)
4. [Banking and monetary policy](04-banking.md)
5. [Taxation (experimental)](05-tax-code.md)
6. [Government, laws and characters](06-politics.md)
7. [Social movements](07-social-movements.md)
8. [States and population](08-states.md)
9. [Diplomacy](09-diplomacy.md)
10. [The United Nations](10-united-nations.md)
11. [Cultural hegemony and covert warfare](11-influence.md)
12. [Colonial empires and decolonization](12-decolonization.md)
13. [Military and war](13-military.md)
14. [Nuclear weapons](14-nuclear.md)
15. [Climate and pollution](15-climate.md)
16. [The space race](16-space.md)
17. [Quick reference](17-reference.md)
18. [Appendix: social movement details](18-appendix-social-movements.md)
19. [Appendix: events](19-appendix-events.md)
20. [Appendix: reference lists](20-appendix-reference-lists.md)

## Editing the guide

The numbered Markdown files are the source; the PDF is built from them. Read
[STYLE.md](STYLE.md) before editing a chapter. After an edit:

```sh
python3 scripts/analysis/check_player_guide_style.py      # style and link lint
.venv/bin/pip install -r requirements-docs.txt            # once
.venv/bin/python scripts/build_player_guide.py            # rebuild the PDF
```

and commit the chapter together with the rebuilt PDF. CI runs the lint with
`--strict` and fails if the committed PDF was built from older sources.

The page layout lives in [template.typ](template.typ). Screenshots go in
[images/](images/); see [images/README.md](images/README.md).
