"""The server's route table (`mod_state_server.ROUTES`, #1537) against the code
that answers each route, against `/help`, and against the endpoint tables in
docs/guides/python_tools.md, the way test_audit_registry.py holds the audit
registry to the audits.

A new endpoint is one `ROUTES` entry, its handler on the right route module's
mixin, a row in python_tools.md and a line in `/help`; this file fails until
all four are there.
"""
import ast
import inspect
import os
import re
import textwrap
import unittest

import mod_state_server as mss

ROOT = os.path.dirname(os.path.abspath(__file__))
TOOLS_DOC = os.path.join(ROOT, "docs", "guides", "python_tools.md")

# Answered before the table is read (GET / and GET /status).
OUTSIDE_TABLE = {"status"}


def first_segment(path: str) -> str:
    """`/raw/<EntityType>/<id>?x=1` -> `raw`."""
    return re.split(r"[/?\[]", path.lstrip("/"), maxsplit=1)[0]


def documented_endpoints() -> list[tuple[str, str, int]]:
    """(method, path, line) for every path in the endpoint tables: from
    § "API Endpoints" up to § "Query Examples". A row's first cell holds one
    or more code spans, each a path (`POST /x` for a POST row); its second
    cell is the method."""
    with open(TOOLS_DOC, encoding="utf-8") as fh:
        lines = fh.read().splitlines()
    start = lines.index("### API Endpoints")
    end = next(i for i in range(start, len(lines)) if lines[i].startswith("### Query Examples"))
    rows = []
    for number in range(start, end):
        line = lines[number]
        if not line.startswith("| `"):
            continue
        cells = [c.strip() for c in re.split(r"(?<!\\)\|", line)[1:-1]]
        if len(cells) < 2 or cells[1] not in ("GET", "POST"):
            continue  # the /reload flag table: query strings and costs
        for span in re.findall(r"`([^`]+)`", cells[0]):
            path = span.split(" ", 1)[1] if span.startswith(("GET ", "POST ")) else span
            if path.startswith("/"):  # not a bare query (`?law=<law_x>`) or a value
                rows.append((cells[1], path, number + 1))
    return rows


def post_paths() -> set[str]:
    """The paths do_POST answers, read off its `parts == [...]` tests."""
    tree = ast.parse(textwrap.dedent(inspect.getsource(mss.ModStateHandler.do_POST)))
    out = set()
    for node in ast.walk(tree):
        if (isinstance(node, ast.Compare) and isinstance(node.left, ast.Name) and node.left.id == "parts"
                and isinstance(node.ops[0], ast.Eq) and isinstance(node.comparators[0], ast.List)):
            out.add("/".join(e.value for e in node.comparators[0].elts))
    return out


def help_paths() -> list[str]:
    handler = object.__new__(mss.ModStateHandler)
    return [entry["path"] for entry in mss.ModStateHandler._help(handler)["get"]]


class RouteTableTests(unittest.TestCase):

    def test_every_route_calls_a_handler_that_takes_its_arguments(self):
        for prefix, spec in mss.ROUTES.items():
            with self.subTest(prefix=prefix):
                method = getattr(mss.ModStateHandler, spec.method, None)
                self.assertIsNotNone(method, f"/{prefix}: no ModStateHandler.{spec.method}")
                self.assertTrue(set(spec.takes) <= {"rest", "params"}, spec.takes)
                # Raises TypeError when the call route() makes would.
                inspect.signature(method).bind(object(), *spec.fixed, *spec.takes)

    def test_handlers_live_in_the_route_modules(self):
        """Every handler but /help's is on a server/ route module's mixin."""
        for prefix, spec in mss.ROUTES.items():
            with self.subTest(prefix=prefix):
                module = getattr(mss.ModStateHandler, spec.method).__module__
                if prefix == "help":
                    self.assertEqual(module, mss.__name__)
                else:
                    self.assertTrue(module.startswith("server.routes_"), f"/{prefix} is answered in {module}")
                    self.assertNotIn(spec.method, vars(mss.ModStateHandler))

    def test_a_route_reaches_its_handler(self):
        """route() calls the table's method with the fixed values first, then
        the path segments after the prefix and the query, as `takes` says."""
        calls = []

        class Probe(mss.ModStateHandler):
            def __getattribute__(self, name):
                if name.startswith("_") and name in {s.method for s in mss.ROUTES.values()}:
                    return lambda *args: calls.append((name, args)) or {"ok": name}
                return object.__getattribute__(self, name)

        probe = object.__new__(Probe)
        for prefix, spec in mss.ROUTES.items():
            calls.clear()
            with self.subTest(prefix=prefix):
                params = {"q": ["x"]}
                self.assertEqual(probe.route([prefix, "a", "b"], params), {"ok": spec.method})
                given = {"rest": ["a", "b"], "params": params}
                self.assertEqual(calls, [(spec.method, (*spec.fixed, *(given[t] for t in spec.takes)))])
        with self.assertRaises(mss.NotFound):
            probe.route(["no-such-route"], {})


class RouteDocsTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.rows = documented_endpoints()
        assert len(cls.rows) > 100, "found no endpoint tables in python_tools.md"

    def test_the_docs_name_every_route(self):
        documented = {first_segment(path) for method, path, _ in self.rows if method == "GET"}
        missing = sorted(set(mss.ROUTES) - documented)
        self.assertEqual(missing, [], "routes with no row in docs/guides/python_tools.md § API Endpoints")

    def test_every_documented_get_endpoint_is_a_route(self):
        unknown = [(line, path) for method, path, line in self.rows
                   if method == "GET" and first_segment(path) not in set(mss.ROUTES) | OUTSIDE_TABLE]
        self.assertEqual(unknown, [], "python_tools.md documents a GET endpoint the server does not route")

    def test_every_documented_post_endpoint_is_answered(self):
        answered = post_paths()
        self.assertEqual(answered, {"reload", "validate/registries"})
        documented = {path.strip("/").split("?")[0] for method, path, _ in self.rows if method == "POST"}
        self.assertEqual(documented, answered)


class HelpTests(unittest.TestCase):

    def test_help_names_every_route(self):
        listed = {first_segment(p) for p in help_paths()}
        self.assertEqual(sorted(set(mss.ROUTES) - listed), [], "routes /help does not list")

    def test_help_lists_only_routes(self):
        unknown = [p for p in help_paths() if first_segment(p) not in set(mss.ROUTES) | OUTSIDE_TABLE]
        self.assertEqual(unknown, [])


if __name__ == "__main__":
    unittest.main()
