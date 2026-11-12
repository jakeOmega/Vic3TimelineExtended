"""Route modules split out of mod_state_server.py (#1537), one group per PR.

mod_state_server.py stays the entry point: startup, the post-load chain, the
dispatcher, and every piece of module-level state (`ms`, `engine_docs`, the
caches). A route module holds code only. It reaches that state through
`server_module()` at call time and never imports mod_state_server at import
time, for one reason:

`python3 mod_state_server.py` runs the server as `__main__`. A plain
`import mod_state_server` from there loads a SECOND copy of the file with its
own, empty, globals (modifier_visibility_audit.py and modifier_field_audit.py
work around the same trap), so a route module that imported it would serve
the copy's empty `engine_docs` while the real one sat in `__main__`.
"""
import sys


def server_module():
    """The mod_state_server module whose state the routes serve: `__main__`
    when the server runs as a script, else the imported `mod_state_server`
    (the tests, `scripts/query.py --offline`, an audit's CLI)."""
    main = sys.modules.get("__main__")
    if getattr(main, "_MOD_STATE_SERVER_ENTRY_POINT", False):
        return main
    import mod_state_server
    return mod_state_server
