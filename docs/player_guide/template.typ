// Page layout for the player guide. scripts/build_player_guide.py generates the
// document that imports this file, so edit here to change how the PDF looks and
// edit the numbered .md chapters to change what it says.
//
// Only the fonts compiled into Typst are used (Libertinus Serif, DejaVu Sans
// Mono), and system fonts are ignored, so every machine builds the same PDF.

#let ink = rgb("#1d2b45")
#let accent = rgb("#8c5a1e")
#let tint = rgb("#f3ede1")
#let rule-colour = rgb("#c8b48a")

// Pandoc's Typst writer emits `#horizontalrule` for a Markdown `---`.
#let horizontalrule = align(center, line(length: 40%, stroke: 0.6pt + rule-colour))

#let guide(
  title: "",
  subtitle: "",
  game-version: "",
  edition: "",
  date: none,
  fingerprint: "",
  repo: "",
  cover: "/thumbnail.png",
  body,
) = {
  set document(
    title: title,
    author: "Vic3TimelineExtended contributors",
    keywords: ("source-sha256:" + fingerprint,),
    date: date,
  )
  set text(font: "Libertinus Serif", size: 10.5pt, lang: "en", region: "us", hyphenate: true)
  set par(justify: true, leading: 0.62em, spacing: 1.15em)
  show raw: set text(font: "DejaVu Sans Mono", size: 0.85em)
  show link: set text(fill: accent)

  // ── Cover ───────────────────────────────────────────────────────────────
  let gold = rgb("#d9b46a")
  page(fill: rgb("#10131b"), margin: (x: 2.4cm, y: 2.2cm), numbering: none)[
    #set text(fill: rgb("#e8e2d4"))
    #v(0.6fr)
    #align(center, image(cover, width: 12cm))
    #v(1.4em)
    #align(center, text(size: 26pt, style: "italic", fill: gold)[#subtitle])
    #v(0.8em)
    #align(center, text(size: 11pt)[
      Written for Victoria 3 #game-version #h(0.5em) · #h(0.5em) Guide edition #edition
    ])
    #v(1fr)
    #align(center, text(size: 9pt, fill: rgb("#a39d90"))[
      The Markdown source of this guide lives next to the PDF in the mod's repository, at
      #link(repo + "/tree/main/docs/player_guide")[#text(fill: gold)[docs/player_guide]]. \
      Corrections and screenshots are welcome as issues or pull requests.
    ])
  ]

  // ── Body layout ─────────────────────────────────────────────────────────
  set page(
    paper: "a4",
    margin: (x: 2.3cm, top: 2.5cm, bottom: 2.4cm),
    header: context {
      let here-page = here().page()
      // No running header on a page that opens a chapter.
      let opens = query(heading.where(level: 1)).any(h => h.location().page() == here-page)
      if not opens {
        let before = query(selector(heading.where(level: 1)).before(here()))
        if before.len() > 0 {
          set text(size: 8.5pt, fill: ink.lighten(25%))
          h(1fr)
          smallcaps(before.last().body)
          v(-0.5em)
          line(length: 100%, stroke: 0.4pt + rule-colour)
        }
      }
    },
    footer: context {
      set text(size: 9pt, fill: ink.lighten(25%))
      align(center, counter(page).display("1"))
    },
  )

  set heading(numbering: (..n) => {
    let parts = n.pos()
    if parts.len() <= 2 { numbering("1.1", ..parts) }
  })
  show heading: set text(fill: ink)
  // Each heading is a sticky block, so it never sits alone at the foot of a page.
  // A chapter titled "Appendix: ..." is labelled APPENDIX instead of CHAPTER n.
  // Pandoc hands the title over as a sequence of text and spaces, so flatten it.
  let plain(c) = if type(c) == str { c } else if c.has("text") { c.text } else if c.has("children") {
    c.children.map(plain).sum(default: "")
  } else if c.has("body") { plain(c.body) } else { " " }
  show heading.where(level: 1): it => {
    let appendix = plain(it.body).starts-with("Appendix")
    pagebreak(weak: true)
    v(2.2cm)
    block(sticky: true, below: 1.2em)[
      #if it.numbering != none {
        let label = if appendix [APPENDIX] else [CHAPTER #counter(heading).display("1")]
        text(size: 11pt, fill: accent, tracking: 0.12em, label)
        v(0.1em)
      }
      #text(size: 24pt, weight: "bold")[#it.body]
      #v(0.3em)
      #line(length: 100%, stroke: 0.8pt + accent)
    ]
  }
  show heading.where(level: 2): it => block(sticky: true, above: 1.7em, below: 0.8em)[
    #set text(size: 14.5pt, weight: "bold")
    #if it.numbering != none [#counter(heading).display(it.numbering)#h(0.5em)]#it.body
  ]
  show heading.where(level: 3): it => block(sticky: true, above: 1.4em, below: 0.7em,
    text(size: 12pt, weight: "bold", it.body))
  show heading.where(level: 4): it => block(sticky: true, above: 1.1em, below: 0.6em,
    text(size: 10.5pt, weight: "bold", style: "italic", it.body))

  // Tables: Pandoc wraps each one in a figure, which would otherwise refuse to
  // break across pages.
  show figure.where(kind: table): set block(breakable: true)
  show figure.where(kind: table): set figure.caption(position: top)
  set table(
    inset: (x: 6pt, y: 5pt),
    stroke: (x, y) => if y == 0 { (bottom: 0.8pt + accent) } else { (bottom: 0.3pt + rule-colour) },
    fill: (x, y) => if y == 0 { tint },
  )
  show table: set text(size: 9.5pt)
  show table: set par(justify: false, spacing: 0.7em)
  // Pandoc centres each table; keep the cells themselves left-aligned.
  show table: set align(left)
  show table.cell.where(y: 0): set text(weight: "bold", fill: ink)

  // Screenshots and other images.
  show figure.where(kind: image): set figure.caption(position: bottom)
  show figure.caption: set text(size: 9pt, style: "italic")
  set image(width: 100%)

  // A Markdown block quote is a side note or tip.
  show quote.where(block: true): it => block(
    width: 100%,
    fill: tint,
    inset: (x: 11pt, y: 9pt),
    radius: 2pt,
    stroke: (left: 2.2pt + accent),
    it.body,
  )

  set list(indent: 0.6em, body-indent: 0.5em)
  set enum(indent: 0.6em, body-indent: 0.5em)

  // ── Contents ────────────────────────────────────────────────────────────
  page(header: none, footer: none)[
    #text(size: 22pt, weight: "bold", fill: ink)[Contents]
    #v(0.4em)
    #line(length: 100%, stroke: 0.8pt + accent)
    #v(0.8em)
    #show outline.entry.where(level: 1): it => {
      v(0.55em, weak: true)
      strong(it)
    }
    #outline(title: none, depth: 2, indent: auto)
  ]

  counter(page).update(1)
  body
}
