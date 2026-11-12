#!/usr/bin/env python3
"""Answer the common mod state server lookups without a running server.

    .venv/bin/python scripts/query.py modifier-search goods_output
    .venv/bin/python scripts/query.py localize law_monarchy
    .venv/bin/python scripts/query.py references law_anarchy
    .venv/bin/python scripts/query.py script-args [te_some_helper]
    .venv/bin/python scripts/query.py modifier-grants country_prestige_mult scope=mod

Prints the JSON the endpoint would (`/modifier-search?q=goods_output`,
`/localize/law_monarchy`, ...), byte for byte: the request goes through the
server's own routing (`ModStateHandler.get_result`) and serialization
(`mod_state_server.encode_response`), with no HTTP. Arguments of the form
`name=value` become query parameters (`limit=20`, `scope=mod`,
`include_reviewed=true`).

When a server for this checkout is up on :8950 (its `/status` answers 200
and reports this checkout's `mod_path`), the lookup goes to it instead, and a
line on stderr says so; if it stops answering before the lookup, the lookup is
answered offline, with a note. `--offline` skips the server. Otherwise the parsed data come from where a
server load takes them: the game files where the game is installed, else the
committed `vanilla_parsed/` snapshot, plus the mod's working tree as it stands
(about 10 s; `script-args` and `modifier-grants` scan files and skip it).
Nothing is written and no regenerator runs. Without a game install,
`modifier-grants` covers the mod only, as the server does there.

Exit code: 0 for an answer (HTTP 200), 1 for an endpoint error (its JSON body
is still printed: 400, 404, 500), 2 for an unknown lookup or bad arguments.
"""
from __future__ import annotations

import contextlib
import http.client
import json
import os
import sys
import urllib.error
import urllib.request
from urllib.parse import quote, urlencode

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

SERVER_PORT = 8950

# lookup -> (argument name, argument required, where it goes, needs ModState).
# "path" puts the argument in the URL path (/localize/<key>); any other value
# names the query parameter it fills (/modifier-search?q=<pattern>).
LOOKUPS: dict[str, tuple[str, bool, str, bool]] = {
    "modifier-search": ("pattern", True, "q", True),
    "localize": ("key", True, "path", True),
    "references": ("key", True, "path", True),
    "script-args": ("helper", False, "path", False),
    "modifier-grants": ("modifier", True, "path", False),
}

# Game paths the server module resolves at import. Where the machine has
# none, a dummy (as conftest.py and CI set) leaves those sources empty.
_GAME_PATH_ENV = {
    "base_game_path": "VIC3_BASE_GAME",
    "mod_deploy_target": "VIC3_MOD_DEPLOY_TARGET",
    "vanilla_source_repo_path": "VIC3_VANILLA_REPO",
    "vanilla_docs_path": "VIC3_VANILLA_DOCS_RUNTIME",
    "game_logs_path": "VIC3_GAME_LOGS",
}


class UsageError(Exception):
    pass


def usage() -> str:
    lines = [
        "usage: scripts/query.py [--offline] <lookup> [argument] [name=value ...]",
        "",
        "supported lookups:",
    ]
    for name, (arg, required, where, _needs) in LOOKUPS.items():
        shown = f"<{arg}>" if required else f"[{arg}]"
        if where != "path":
            url = f"/{name}?{where}={shown}"
        else:
            url = f"/{name}/<{arg}>" if required else f"/{name}[/<{arg}>]"
        lines.append(f"  {name + ' ' + shown:<30} GET {url}")
    lines.append("name=value arguments become query parameters, e.g. limit=20 scope=mod.")
    return "\n".join(lines)


def build_request(argv: list[str]) -> tuple[str, str, bool]:
    """(lookup, request path, offline) for a command line; UsageError when it
    names no supported lookup or its arguments don't fit."""
    offline = False
    args = []
    for arg in argv:
        if arg == "--offline":
            offline = True
        elif arg in ("-h", "--help"):
            raise UsageError("")
        else:
            args.append(arg)
    if not args:
        raise UsageError("no lookup given")
    lookup, rest = args[0], args[1:]
    if lookup not in LOOKUPS:
        raise UsageError(f"unknown lookup {lookup!r}")
    arg_name, required, where, _needs = LOOKUPS[lookup]
    positional = [a for a in rest if "=" not in a]
    params = []
    for a in rest:
        if "=" in a:
            key, value = a.split("=", 1)
            if not key:
                raise UsageError(f"bad parameter {a!r}: expected name=value")
            params.append((key, value))
    if len(positional) > 1:
        raise UsageError(f"{lookup} takes one {arg_name}, got {len(positional)}: "
                         + " ".join(positional))
    if required and not positional:
        raise UsageError(f"{lookup} needs a {arg_name}")
    path = "/" + lookup
    if positional:
        if where == "path":
            path += "/" + quote(positional[0], safe="")
        else:
            params.insert(0, (where, positional[0]))
    if params:
        path += "?" + urlencode(params)
    return lookup, path, offline


def server_for_this_checkout(port: int = SERVER_PORT, timeout: float = 2.0) -> str | None:
    """The base URL of the server on `port` when its `/status` answers 200
    and names this checkout as its `mod_path`, else None: nothing listening,
    something there that is not this server, a server for another checkout,
    or one whose `/status` is a 503 (vanilla data not loaded)."""
    import path_constants

    base = f"http://127.0.0.1:{port}"
    try:
        with urllib.request.urlopen(f"{base}/status", timeout=timeout) as resp:
            status = json.loads(resp.read())
    except (urllib.error.URLError, http.client.HTTPException, OSError, ValueError):
        return None
    served = status.get("mod_path") if isinstance(status, dict) else None
    if not served or os.path.realpath(served) != os.path.realpath(path_constants.mod_path):
        return None
    return base


def fetch(base: str, path: str) -> tuple[bytes, int] | None:
    """(body, status) from the server, an endpoint error included; None when
    the server could not be reached for this request (it went away after
    `/status`, or the connection broke)."""
    try:
        with urllib.request.urlopen(base + path, timeout=600) as resp:
            return resp.read(), resp.status
    except urllib.error.HTTPError as exc:
        return exc.read(), exc.code
    except (urllib.error.URLError, http.client.HTTPException, OSError):
        return None


def _ensure_game_paths() -> None:
    import path_constants

    for name, env_var in _GAME_PATH_ENV.items():
        try:
            getattr(path_constants, name)
        except RuntimeError:
            os.environ.setdefault(env_var, f"/nonexistent/{name}")


def answer_offline(path: str, needs_mod_state: bool) -> tuple[bytes, int]:
    """(body, status) for GET `path`, answered in this process by the
    server's own handler."""
    _ensure_game_paths()
    import mod_state_server as mss

    if needs_mod_state and mss.ms is None:
        # Keep stdout for the JSON alone.
        with contextlib.redirect_stdout(sys.stderr):
            mss.ms = mss.cli_mod_state()
    handler = object.__new__(mss.ModStateHandler)
    data, status = handler.get_result(path)
    return mss.encode_response(data, status, f"GET {path}")


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    try:
        lookup, path, offline = build_request(argv)
    except UsageError as exc:
        if str(exc):
            print(f"query.py: {exc}", file=sys.stderr)
        print(usage(), file=sys.stderr)
        return 2
    base = None if offline else server_for_this_checkout()
    answer = fetch(base, path) if base else None
    if answer is not None:
        print(f"[query] answered by the mod state server on :{SERVER_PORT} "
              "(it serves this checkout)", file=sys.stderr)
        body, status = answer
    else:
        if base:
            print(f"[query] the mod state server on :{SERVER_PORT} stopped answering; "
                  "answering offline", file=sys.stderr)
        needs = LOOKUPS[lookup][3] or "annotate=" in path
        body, status = answer_offline(path, needs)
    sys.stdout.buffer.write(body)
    if sys.stdout.isatty():
        sys.stdout.buffer.write(b"\n")
    sys.stdout.flush()
    return 0 if status == 200 else 1


if __name__ == "__main__":
    sys.exit(main())
