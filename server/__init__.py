"""Route modules split out of mod_state_server.py (#1537), one group per PR.

mod_state_server.py stays the entry point: startup, the post-load chain, the
dispatcher, and every piece of module-level state (`ms`, `engine_docs`, the
caches). A route module holds code only. It reaches that state through
`server_state()` at call time and never imports mod_state_server, because the
running server's globals are often not the module an import would give:

* `python3 mod_state_server.py` and `python3 -m mod_state_server` run the file
  as `__main__`; an `import mod_state_server` there loads a SECOND copy with
  empty globals (modifier_visibility_audit.py and modifier_field_audit.py work
  around the same trap).
* `python3 -m cProfile|profile|trace mod_state_server.py` exec the file into a
  plain dict: no module in `sys.modules` holds its globals at all.

So the file registers its own globals dict (`register_state(globals())`) as it
runs, however it was run. `server_state()` serves from the last registered
dict named `__main__` (the script) when there is one, else from the last one
registered (an `import mod_state_server`: the tests, `scripts/query.py
--offline`, an audit's command line). It imports nothing, and raises when
nothing registered rather than serve empty state.
"""

_registered: list[dict] = []


def register_state(server_globals: dict) -> None:
    """Called by mod_state_server.py with its own `globals()` as it runs."""
    if not any(g is server_globals for g in _registered):
        _registered.append(server_globals)


class _ServerState:
    """Attribute access over a server globals dict, read and written live:
    `srv.engine_docs` is whatever the dict holds at that moment."""

    __slots__ = ("_globals",)

    def __init__(self, server_globals: dict):
        object.__setattr__(self, "_globals", server_globals)

    def __getattr__(self, name):
        try:
            return self._globals[name]
        except KeyError:
            raise AttributeError(f"mod_state_server has no {name!r}") from None

    def __setattr__(self, name, value):
        self._globals[name] = value


def server_globals() -> dict:
    """The globals dict of the mod_state_server whose state the routes serve."""
    for g in reversed(_registered):
        if g.get("__name__") == "__main__":
            return g
    if _registered:
        return _registered[-1]
    raise RuntimeError(
        "server.server_state(): mod_state_server has not run in this process; "
        "import or run it before calling its routes."
    )


def server_state() -> _ServerState:
    """The running server's state, as `srv.<name>`."""
    return _ServerState(server_globals())
