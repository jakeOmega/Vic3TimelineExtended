"""Mod content that tests a part culture also names the culture it merges into.

A culture merge (docs/superpowers/specs/2026-11-07-culture-merges-design.md)
converts every pop of a part to the result when the part switches: North and
South German become ``cm_german``. A test that names only the part then stops
matching those pops and, for a country that holds only the result, stops
matching at all. Section 7 keeps the parts as primary cultures of every country
that had them, so ``country_has_primary_culture = cu:north_german`` does not go
dark for Germany itself; the result is added for a country formed or released
later that lists only the result, and for pop and character reads, which do
follow the pops.

**The rule.** Every culture test in ``common/`` and ``events/`` that names a
part (``cu:<c>``, ``has_pop_culture = <c>`` and any other ``*culture* = <c>``, or
an entry in a bare culture list) sits in an ``OR`` / ``NOR`` / ``NOT`` block or
a bare list that also names every culture in ``successors_of(c)``: the result of
each merge the part is in, and those results' own results. Alone, or in an
``AND`` or an ``any_*`` block, the result would have to be wrapped in an ``OR``
with it, so such a test fails too.

**Declining a successor.** The whole chain is the safe default for a pop read,
but flavor is a judgment: the ladders of party names are ``first_valid``, so
adding ``cm_latin`` to the French entry would hand a Latin Spain the French
party name. A line declines with ``# REVIEWED YYYY-MM-DD (culture_merge_ref):
reason`` on the test's line or on its block's opening line. One comment covers
every successor missing on the lines it covers. A comment that no longer
excuses anything fails (a stale one hides a regression).

**Not scanned.**

* ``common/country_definitions/`` and ``common/history/``: kept homelands and
  primaries cover them (spec section 7).
* The culture-merge system's own files (``te_culture_merge*``,
  ``te_culture_merges_generated*``, ``te_cm*``, ``te_debug_cm*``,
  ``te_vanilla_russification_merge.txt``).
* A file with an ``AUTO-GENERATED`` header is fixed at its generator. Three
  generated files restate **vanilla's** text (``GENERATED_RESTATEMENTS``): the
  generator copies vanilla's condition, and widening the copy would make it
  disagree with the vanilla entry it mirrors. The test pins that set, so a new
  generated file that tests a part fails here and gets a decision.
"""

import os
import re
import sys
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "scripts", "generators"))

import culture_merges_config as cfg  # noqa: E402

SCAN_ROOTS = ("common", "events")
EXEMPT_DIRS = ("common/country_definitions/", "common/history/")
EXEMPT_NAMES = re.compile(
    r"^(te_culture_merge|te_culture_merges_generated|te_cm|te_debug_cm|te_vanilla_russification_merge)"
)
GENERATED_MARK = "AUTO-GENERATED"

# Generated files whose part tests are vanilla's own text, copied. Path -> why.
GENERATED_RESTATEMENTS = {
    "common/ideologies/modified.txt": (
        "apply_ideologies copies vanilla's ideologies whole and edits only their law stances; the "
        "Carlist and Miguelist country_trigger blocks that test Spanish, Catalan and Portuguese are "
        "vanilla's"
    ),
    "common/parties/zz_te_party_join_weights.txt": (
        "gen_party_join_weights restates every vanilla party's join_weight line for line (an injected "
        "join_weight replaces vanilla's whole field), and test_first_past_the_post holds the copy to "
        "vanilla's; the Spain and Portugal two-party term, French legitimism and the antebellum "
        "Northern and Southern interests are vanilla's"
    ),
    "common/scripted_triggers/00_a_te_culture_merge_vanilla_triggers.txt": (
        "gen_culture_merges restates vanilla's has_indian_primary_culture, a plain list of cultures, with every "
        "culture a listed part can become added to it (test_culture_merge_primary_reads holds the copy to vanilla's "
        "list and to successors_of)"
    ),
    "common/government_types/zz_te_culture_merge_government_types.txt": (
        "gen_culture_merges restates eleven vanilla government types (the Kaiser family, the American forms) with the "
        "merged culture added beside the cultures vanilla names, so the ruler keeps the title; "
        "test_culture_merge_primary_reads holds each copy to vanilla's text plus that one line"
    ),
    "common/scripted_effects/extra_law_consistency_generated.txt": (
        "gen_law_consistency restates the conditions vanilla's own laws carry (Manorialism and "
        "Organic Regulation test Romanian); widening the copy would make its walk disagree with the "
        "law the game enforces"
    ),
}

REVIEWED_RE = re.compile(r"#\s*REVIEWED\s+\d{4}-\d{2}-\d{2}\s*\(culture_merge_ref\)\s*:\s*\S")
TOKEN_RE = re.compile(r'"(?:[^"\\]|\\.)*"|[=<>!?]+|[{}]|[^\s{}=<>!?"]+')
OPERATORS = frozenset({"=", "?=", "!=", "==", "<", ">", "<=", ">="})
# A block whose members are alternatives: a hit in one needs the result beside it.
ALTERNATIVE_BLOCKS = frozenset({"OR", "NOR", "NOT"})


def part_cultures():
    """Every culture some merge folds away or into a further merge: the ones whose pops move."""
    return {
        c
        for m in cfg.MERGES
        for p in m.core + m.optional
        for c in p.cultures
        if cfg.successors_of(c)
    }


def split_comment(line):
    """(code, comment) with the comment starting at the first `#` outside a string."""
    quoted = False
    for i, ch in enumerate(line):
        if ch == '"':
            quoted = not quoted
        elif ch == "#" and not quoted:
            return line[:i], line[i:]
    return line, ""


class Token:
    __slots__ = ("text", "line")

    def __init__(self, text, line):
        self.text = text
        self.line = line


class Block:
    __slots__ = ("key", "open_line", "start", "end")

    def __init__(self, key, open_line, start):
        self.key = key
        self.open_line = open_line
        self.start = start
        self.end = None


def tokenize(text):
    """(tokens, comments, lines): tokens with their 1-based lines, and the comment of each line."""
    tokens = []
    comments = {}
    lines = text.split("\n")
    for n, raw in enumerate(lines, 1):
        code, comment = split_comment(raw)
        if comment:
            comments[n] = comment
        for m in TOKEN_RE.finditer(code):
            tokens.append(Token(m.group(0), n))
    return tokens, comments, lines


def blocks_of(tokens):
    """Every `{ }` block, keyed by the word before its `=` (or before a bare `{`)."""
    blocks = []
    stack = []
    for i, tok in enumerate(tokens):
        if tok.text == "{":
            key = ""
            if i >= 2 and tokens[i - 1].text in OPERATORS:
                key = tokens[i - 2].text
            elif i >= 1 and tokens[i - 1].text not in OPERATORS:
                key = tokens[i - 1].text
            block = Block(key, tok.line, i)
            blocks.append(block)
            stack.append(block)
        elif tok.text == "}" and stack:
            stack.pop().end = i
    for block in stack:  # unbalanced: run to the end
        block.end = len(tokens)
    return blocks


def innermost(blocks, index):
    best = None
    for block in blocks:
        if block.start < index < block.end and (best is None or block.start > best.start):
            best = block
    return best


def find_hits(tokens, parts):
    """(token index, culture, form) for every culture test that names a part.

    form is "cu" (`cu:<c>`), "key" (`<key with culture in it> = <c>`) or "list"
    (a bare entry of a block that is a list of cultures).
    """
    hits = []
    blocks = blocks_of(tokens)
    for i, tok in enumerate(tokens):
        text = tok.text
        if text.startswith("cu:") and text[3:] in parts:
            hits.append((i, text[3:], "cu"))
        elif text in parts:
            before = tokens[i - 1].text if i else ""
            after = tokens[i + 1].text if i + 1 < len(tokens) else ""
            if before in OPERATORS and i >= 2 and "culture" in tokens[i - 2].text:
                hits.append((i, text, "key"))
            elif before not in OPERATORS and after not in OPERATORS and before != "":
                block = innermost(blocks, i)
                # A list of cultures: every member is a bare token.
                if block is not None and "culture" in block.key and not any(
                    t.text in OPERATORS for t in tokens[block.start + 1 : block.end]
                ):
                    hits.append((i, text, "list"))
    return hits, blocks


def names(tokens, block, culture):
    for t in tokens[block.start + 1 : block.end]:
        if t.text == "cu:" + culture or t.text == culture:
            return True
    return False


def scan_text(path, text, parts=None):
    """(problems, used): what is wrong with one file, and the lines of the REVIEWED comments it relied on."""
    parts = part_cultures() if parts is None else parts
    tokens, comments, _lines = tokenize(text)
    hits, blocks = find_hits(tokens, parts)
    problems = []
    used = set()
    for index, culture, form in hits:
        tok = tokens[index]
        block = innermost(blocks, index)
        missing = sorted(
            r for r in cfg.successors_of(culture) if block is None or not names(tokens, block, r)
        )
        # The block must be one whose members are alternatives (or a list).
        alone = block is None or (form != "list" and block.key not in ALTERNATIVE_BLOCKS)
        if not missing and not alone:
            continue
        excusing = [
            n
            for n in {tok.line, block.open_line if block is not None else tok.line}
            if n in comments and REVIEWED_RE.search(comments[n])
        ]
        if excusing:
            used.update(excusing)
            continue
        where = block.key or "the file" if block is not None else "the file"
        if alone:
            problems.append(
                "%s:%d: `%s` sits alone in %s; wrap it in OR = { } with %s, or end the line with "
                "# REVIEWED YYYY-MM-DD (culture_merge_ref): why" % (path, tok.line, tok.text, where, ", ".join(missing))
            )
        else:
            problems.append(
                "%s:%d: `%s` sits in %s without %s; add %s beside it, or end the line with "
                "# REVIEWED YYYY-MM-DD (culture_merge_ref): why"
                % (path, tok.line, tok.text, where, ", ".join(missing), "it" if len(missing) == 1 else "them")
            )
    return problems, used


def stale_reviews(path, text, used):
    """REVIEWED comments that excuse nothing."""
    _tokens, comments, _ = tokenize(text)
    return [
        "%s:%d: a REVIEWED (culture_merge_ref) comment that excuses nothing; delete it" % (path, n)
        for n, comment in sorted(comments.items())
        if REVIEWED_RE.search(comment) and n not in used
    ]


def read(path):
    with open(os.path.join(REPO, path), encoding="utf-8-sig") as f:
        return f.read()


def mod_files():
    """Relative posix paths of every .txt under common/ and events/."""
    out = []
    for root_name in SCAN_ROOTS:
        for dirpath, dirnames, filenames in os.walk(os.path.join(REPO, root_name)):
            dirnames.sort()
            for name in sorted(filenames):
                if name.endswith(".txt"):
                    out.append(os.path.relpath(os.path.join(dirpath, name), REPO).replace(os.sep, "/"))
    return out


def is_generated(text):
    return GENERATED_MARK in "\n".join(text.split("\n", 6)[:6])


def scanned_files():
    """(path, text) of every file the rule covers, and the generated ones apart."""
    scanned, generated = [], []
    for path in mod_files():
        if path.startswith(EXEMPT_DIRS) or EXEMPT_NAMES.match(os.path.basename(path)):
            continue
        text = read(path)
        (generated if is_generated(text) else scanned).append((path, text))
    return scanned, generated


class ScannerTest(unittest.TestCase):
    """The scan finds what it should, on small inputs."""

    PARTS = {"north_german", "south_german", "corsican", "spanish", "french"}

    def scan(self, text, parts=None):
        problems, used = scan_text("f.txt", text, parts or self.PARTS)
        return problems, used

    def test_a_part_beside_its_result_passes(self):
        problems, _ = self.scan(
            "x = { OR = {\n country_has_primary_culture = cu:north_german\n"
            " country_has_primary_culture = cu:south_german\n"
            " country_has_primary_culture = cu:cm_german\n } }\n"
        )
        self.assertEqual(problems, [])

    def test_a_part_without_its_result_fails(self):
        problems, _ = self.scan(
            "x = { OR = {\n country_has_primary_culture = cu:north_german\n"
            " country_has_primary_culture = cu:south_german\n } }\n"
        )
        self.assertEqual(len(problems), 2)
        self.assertIn("cm_german", problems[0])

    def test_a_part_alone_fails_and_names_the_wrap(self):
        problems, _ = self.scan("x = {\n country_has_primary_culture = cu:north_german\n}\n")
        self.assertEqual(len(problems), 1)
        self.assertIn("sits alone", problems[0])

    def test_the_result_beside_a_part_in_an_and_still_fails(self):
        problems, _ = self.scan(
            "x = { AND = {\n country_has_primary_culture = cu:north_german\n"
            " country_has_primary_culture = cu:cm_german\n } }\n"
        )
        self.assertEqual(len(problems), 1)
        self.assertIn("sits alone", problems[0])

    def test_nor_and_not_count_as_alternatives(self):
        for key in ("NOR", "NOT"):
            problems, _ = self.scan(
                "x = { %s = {\n has_pop_culture = north_german\n has_pop_culture = cm_german\n } }\n" % key
            )
            self.assertEqual(problems, [], key)

    def test_a_bare_key_value_form_counts(self):
        problems, _ = self.scan("x = { OR = {\n has_pop_culture = north_german\n } }\n")
        self.assertEqual(len(problems), 1)
        self.assertIn("cm_german", problems[0])

    def test_a_bare_culture_list_is_checked(self):
        bad, _ = self.scan("x = { cultures = {\n north_german south_german\n } }\n")
        self.assertEqual(len(bad), 2)
        good, _ = self.scan("x = { cultures = {\n north_german south_german cm_german\n } }\n")
        self.assertEqual(good, [])

    def test_a_bare_word_outside_a_culture_context_is_not_a_hit(self):
        problems, _ = self.scan("x = {\n desc = north_german\n tags = { north_german }\n}\n")
        self.assertEqual(problems, [])

    def test_a_commented_mention_is_ignored(self):
        problems, _ = self.scan("x = {\n # country_has_primary_culture = cu:north_german\n a = 1\n}\n")
        self.assertEqual(problems, [])

    def test_every_successor_in_the_chain_is_required(self):
        problems, _ = self.scan("x = { OR = {\n country_has_primary_culture = cu:corsican\n"
                                " country_has_primary_culture = cu:cm_italian\n } }\n")
        self.assertEqual(len(problems), 1)
        self.assertIn("cm_latin", problems[0])
        self.assertNotIn("cm_italian,", problems[0])

    def test_reviewed_on_the_line_excuses_it(self):
        problems, used = self.scan(
            "x = { OR = {\n country_has_primary_culture = cu:spanish"
            " # REVIEWED 2026-11-07 (culture_merge_ref): Spain only\n } }\n"
        )
        self.assertEqual(problems, [])
        self.assertEqual(used, {2})

    def test_reviewed_on_the_block_opener_excuses_the_block(self):
        problems, used = self.scan(
            "x = { OR = { # REVIEWED 2026-11-07 (culture_merge_ref): Spain and France only\n"
            " country_has_primary_culture = cu:spanish\n country_has_primary_culture = cu:french\n } }\n"
        )
        self.assertEqual(problems, [])
        self.assertEqual(used, {1})

    def test_a_reviewed_comment_needs_the_tag_and_a_reason(self):
        for comment in (
            "# REVIEWED 2026-11-07: Spain only",
            "# REVIEWED 2026-11-07 (culture_merge_ref):",
            "# REVIEWED 2026-11-07 (other_audit): Spain only",
            "# reviewed (culture_merge_ref): Spain only",
        ):
            problems, _ = self.scan(
                "x = { OR = {\n country_has_primary_culture = cu:spanish %s\n } }\n" % comment
            )
            self.assertEqual(len(problems), 1, comment)

    def test_a_reviewed_comment_that_excuses_nothing_is_stale(self):
        text = (
            "x = { OR = {\n country_has_primary_culture = cu:north_german"
            " # REVIEWED 2026-11-07 (culture_merge_ref): old\n"
            " country_has_primary_culture = cu:cm_german\n } }\n"
        )
        problems, used = self.scan(text)
        self.assertEqual(problems, [])
        self.assertEqual(len(stale_reviews("f.txt", text, used)), 1)

    def test_a_reviewed_comment_on_no_test_is_stale(self):
        text = "x = {\n a = 1 # REVIEWED 2026-11-07 (culture_merge_ref): nothing here\n}\n"
        problems, used = self.scan(text)
        self.assertEqual(len(stale_reviews("f.txt", text, used)), 1)

    def test_part_cultures_match_the_roster(self):
        parts = part_cultures()
        for result in {m.result for m in cfg.MERGES}:
            for part in cfg.parts_of(result):
                self.assertIn(part, parts, "%s -> %s" % (part, result))
        self.assertNotIn("han", parts)
        self.assertNotIn("hungarian", parts)
        self.assertIn("french", parts)
        self.assertIn("cm_italian", parts)


class ModContentTest(unittest.TestCase):
    """The mod's own files, as committed."""

    @classmethod
    def setUpClass(cls):
        cls.scanned, cls.generated = scanned_files()
        cls.parts = part_cultures()
        cls.results = {path: scan_text(path, text, cls.parts) for path, text in cls.scanned}

    def test_every_part_test_names_its_result(self):
        problems = [p for found, _used in self.results.values() for p in found]
        self.assertEqual(problems, [], "\n" + "\n".join(problems))

    def test_no_reviewed_comment_is_stale(self):
        problems = []
        for path, text in self.scanned:
            problems.extend(stale_reviews(path, text, self.results[path][1]))
        self.assertEqual(problems, [], "\n" + "\n".join(problems))

    def test_the_scan_sees_the_files_it_was_written_for(self):
        paths = {path for path, _ in self.scanned}
        for expected in (
            "common/parties/populist_party.txt",
            "common/parties/green_party.txt",
            "common/parties/technocratic_party.txt",
            "common/company_types/extra_companies_flavored.txt",
            "common/dynamic_country_names/te_formable_countries.txt",
            "common/scripted_triggers/te_fptp_triggers.txt",
        ):
            self.assertIn(expected, paths)
            text = dict(self.scanned)[expected]
            tokens, _comments, _lines = tokenize(text)
            hits, _blocks = find_hits(tokens, self.parts)
            self.assertTrue(hits, expected + " has part tests the scan should find")

    def test_the_system_and_definition_files_are_not_scanned(self):
        paths = {path for path, _ in self.scanned} | {path for path, _ in self.generated}
        for path in paths:
            self.assertFalse(path.startswith(EXEMPT_DIRS), path)
            self.assertIsNone(EXEMPT_NAMES.match(os.path.basename(path)), path)

    def test_generated_files_that_test_a_part_are_the_known_restatements(self):
        with_hits = set()
        for path, text in self.generated:
            tokens, _comments, _lines = tokenize(text)
            hits, _blocks = find_hits(tokens, self.parts)
            if hits:
                with_hits.add(path)
        self.assertEqual(
            with_hits,
            set(GENERATED_RESTATEMENTS),
            "a generated file that tests a part culture needs its generator fixed (or, if it copies "
            "vanilla's condition, a line in GENERATED_RESTATEMENTS saying so)",
        )

    def test_the_restatement_reasons_are_given(self):
        for path, why in GENERATED_RESTATEMENTS.items():
            self.assertTrue(os.path.exists(os.path.join(REPO, path)), path)
            self.assertGreater(len(why), 40, path)


if __name__ == "__main__":
    unittest.main()
