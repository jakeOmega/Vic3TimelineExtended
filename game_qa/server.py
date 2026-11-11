"""The session server: one process that holds one `Session`, for the life of one game, and answers its verbs.

    POST http://127.0.0.1:<port>/<verb>       a JSON object of the verb's arguments, and the server's token
    -> {"code": 0 | 2, "reply": {...}}       the verb's reply, and the exit code its command-line verb gives

`python3 -m game_qa start` runs `python3 -m game_qa session-serve` detached and then posts `start` to it; every
other verb is a thin client of it (`game_qa/client.py`). The server binds 127.0.0.1 only, answers one request at
a time, and holds exactly one `Session`. While it listens, `<backup root>/session.json` names it: `port`, `pid`,
`started`, then `snapshot` once the session has started, and `token`, which every request must carry, so that no
other program on the machine (a web page in a browser included) can type into the game. The server removes the
file when it exits by any route it controls, and never removes one another server wrote.

The server never touches the owner's files itself: only the `Session` does, through part 1's verbs. If the
server is killed outright nothing here restores anything. `watch`, its own process, still records the game's
exit, and the next `start` is refused because `snapshot` refuses while that run is unfinished; `recover`
finishes it (spec § 5.2, Review Focus 1).

    start      the session's start. Any error stops the session and ends the server; a second `start` is
               refused `session_running`, touching nothing
    stop       the session's stop: the server answers with its reply, then exits
    status     the server and the session, answered here without asking the game anything
    the rest   console, run-setup, events, pick, read, tag, enter-game, advance, shot, try-event

An error inside a verb becomes a refusal, `{"refused": <code>, "detail": …}`, with `entered` for a console error
and whatever else the error carries (a `SessionError`'s `info`), and the server keeps running.

SIGTERM and SIGINT stop the session, then remove the file. A signal while a verb runs is noted and acted on once
that verb has answered: a verb is never cut short, since it may be typing into the game, waiting on the helper's
pipe (whose lock `stop` would then wait on for ever) or running a protective verb (which a cut would leave
holding the backup root's lock).
"""
from __future__ import annotations

import json
import os
import signal
import socketserver
import traceback
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Callable, TextIO

from game_qa.console import ConsoleError
from game_qa.dap import DebuggerError
from game_qa.fixture import FixtureError
from game_qa.helper import HelperError
from game_qa.overlay import OverlayError
from game_qa.report import stamp, utc_now
from game_qa.session import SessionError

HOST = "127.0.0.1"
PORT = 8951
SESSION_FILE = "session.json"
TOKEN_HEADER = "X-Game-QA-Token"
MAX_BODY = 1 << 20                      # a request's JSON: setup scripts are the largest part
START_ARGS = ("permission", "as_tag", "setups", "save", "playset", "owner_confirmed_busy")


class ServerError(Exception):
    """The server could not begin: its session.json could not be claimed."""


class _Signalled(BaseException):
    """SIGTERM or SIGINT while no verb runs: out of the serve loop, past every `except Exception`."""


class _BadBody(Exception):
    """A request body that does not hold what its verb needs."""


def read_info(backup_root: Path) -> dict | None:
    """What `<backup root>/session.json` says, or None when there is no such file or it does not read as one
    (a server writes it in one call, so that is a moment at most, or what a crash left)."""
    try:
        info = json.loads((Path(backup_root) / SESSION_FILE).read_text("utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(info, dict) or not isinstance(info.get("port"), int) or not isinstance(info.get("pid"), int):
        return None
    return info


def refusal(error: Exception) -> dict:
    """The reply for an error inside a verb: what it was and what it carries."""
    if isinstance(error, SessionError):
        out = {"refused": error.code, "detail": error.detail}
        out.update((k, v) for k, v in error.info.items() if k not in out)
        return out
    if isinstance(error, ConsoleError):
        return {"refused": error.code, "detail": error.detail, "entered": error.entered}
    if isinstance(error, DebuggerError):
        return {"refused": "debugger", "detail": str(error)}
    if isinstance(error, HelperError):
        return {"refused": "helper: " + error.code, "detail": error.detail}
    if isinstance(error, FixtureError):
        return {"refused": "fixture_failed", "detail": str(error), "step": error.step, "reply": error.reply,
                "snapshot": error.snapshot}
    if isinstance(error, OverlayError):
        return {"refused": "overlay_refused", "detail": str(error)}
    return {"refused": "error", "detail": "%s: %s" % (type(error).__name__, error)}


def clean_stop(reply: dict) -> bool:
    """Whether a stop's reply says the owner's files are back (or that no snapshot was ever taken)."""
    return reply.get("held") is not True and not reply.get("refused") and reply.get("outcome") in ("restored", None)


class SessionServer:
    """Serves one `Session` (or anything with its public methods) on HOST until `stop`, a failed `start` or a
    signal; `serve` returns what it did. `log` gets one line per request and per event, or nothing when None."""

    def __init__(self, session, backup_root: Path, port: int = PORT, log: TextIO | None = None) -> None:
        self._session = session
        self._backup_root = Path(backup_root)
        self._port = port
        self._log = log
        self.token = os.urandom(16).hex()
        self.address: tuple[str, int] | None = None
        self._started = stamp(utc_now())
        self._info: dict | None = None
        self._done = False                  # the loop ends after the request in progress
        self._busy = False                  # a request is being answered: a signal waits for it
        self._signalled: int | None = None
        self._start_posted = False
        self._served = 0
        self._verbs: dict[str, Callable[[dict], tuple[dict, int]]] = {
            "console": self._console, "run-setup": self._run_setup, "events": self._events, "pick": self._pick,
            "read": self._read, "tag": self._tag, "enter-game": self._enter_game, "advance": self._advance,
            "shot": self._shot, "try-event": self._try_event,
        }

    @property
    def path(self) -> Path:
        return self._backup_root / SESSION_FILE

    # ---- the loop

    def serve(self, signals: bool = False) -> dict:
        """Listen, claim session.json, answer requests one at a time until the session is over, then stop the
        session (`stop` is idempotent: after a `stop` verb it returns that reply again) and remove the file.
        With `signals` (the real server, in its main thread), SIGTERM and SIGINT end it the same way."""
        httpd = _HTTPServer((HOST, self._port), _Handler)
        httpd.game_qa = self
        httpd.timeout = None
        self.address = httpd.server_address[:2]
        stopped = None
        try:
            # The handlers come first: from the moment session.json names this server, a signal must stop the
            # session and remove the file (a signal before the claim finds no file of ours, and nothing started).
            previous = self._take_signals() if signals else {}
            try:
                try:
                    self._claim(self.address[1])
                    while True:
                        httpd.handle_request()
                        if self._done or self._signalled is not None:
                            break           # still busy: a signal from here on is only noted
                        self._busy = False
                except _Signalled:
                    pass
                finally:
                    self._busy = True       # from here a signal is only noted: nothing may cut the stop short
                    if self._signalled is not None:
                        self._note("signal %d: stopping the session" % self._signalled)
                    stopped = self._stop_session()
                    self._release()
            finally:
                for signum, handler in previous.items():
                    signal.signal(signum, handler)
        finally:
            httpd.server_close()
        self._note("exited after %d requests" % self._served)
        return {"served": self._served, "signal": self._signalled, "stop": stopped}

    def _take_signals(self) -> dict:
        previous = {}
        for signum in (signal.SIGTERM, signal.SIGINT):
            previous[signum] = signal.signal(signum, self._on_signal)
        return previous

    def _on_signal(self, signum, _frame) -> None:
        if self._signalled is not None:
            return                          # one is enough: the stop is under way, or comes after the verb
        self._signalled = signum
        if not self._busy:
            raise _Signalled(signum)
        # A verb is being answered: the loop ends once it has answered (no write here: the main thread may be
        # inside a write to the same stream).

    # ---- one request

    def handle(self, verb: str, body: dict) -> tuple[dict, int]:
        """One verb's reply and exit code. Never raises for an error inside a verb."""
        self._served += 1
        self._note("verb %s" % verb)
        if verb == "status":
            return self._status(), 0
        if verb == "start":
            return self._start(body)
        if verb == "stop":
            self._done = True
            reply = self._stop_session()
            return reply, 0 if clean_stop(reply) else 2
        run = self._verbs.get(verb)
        if run is None:
            return {"refused": "unknown_verb", "detail": "%r is not a verb of the session server; it has %s" % (
                verb, ", ".join(sorted(["start", "stop", "status", *self._verbs])))}, 2
        try:
            return run(body)
        except _BadBody as e:
            return {"refused": "bad_argument", "detail": str(e)}, 2
        except Exception as e:
            return refusal(e), 2

    def _start(self, body: dict) -> tuple[dict, int]:
        if self._start_posted:
            return {"refused": "session_running", "detail": "this server's session has had its start: one server "
                                                            "holds one session, for one game"}, 2
        self._start_posted = True
        try:
            unknown = sorted(set(body) - set(START_ARGS))
            if unknown or "permission" not in body:
                raise _BadBody("start takes %s (permission required), not %s" % (", ".join(START_ARGS), unknown))
            reply = self._session.start(**{k: body[k] for k in START_ARGS if k in body})
        except Exception as e:
            out = {"refused": "bad_argument", "detail": str(e)} if isinstance(e, _BadBody) else refusal(e)
            out.setdefault("stop", self._stop_session())
            self._done = True
            return out, 2
        if isinstance(reply, dict) and reply.get("snapshot"):
            self._update_info(snapshot=reply["snapshot"])
        return reply, 0

    def _status(self) -> dict:
        try:
            state = self._session.status()
        except Exception as e:
            state = {"error": "%s: %s" % (type(e).__name__, e)}
        return {"server": {"pid": os.getpid(), "port": self.address[1] if self.address else None,
                           "started": self._started, "served": self._served}, "session": state}

    def _stop_session(self) -> dict:
        try:
            return self._session.stop()
        except Exception as e:              # Session.stop never raises; anything else that does is still answered
            return {"outcome": "error", "notes": ["stop failed: %s" % refusal(e)["detail"]]}

    # ---- the verbs: the body's arguments in, a JSON-able reply out

    def _console(self, body: dict) -> tuple[dict, int]:
        return asdict(self._session.console(_arg(body, "text"))), 0

    def _run_setup(self, body: dict) -> tuple[dict, int]:
        name = _arg(body, "name")
        return {"name": name, "lines": self._session.run_setup(name)}, 0

    def _events(self, body: dict) -> tuple[dict, int]:
        return {"pending": [asdict(p) for p in self._session.events()]}, 0

    def _pick(self, body: dict) -> tuple[dict, int]:
        return self._session.pick(_arg(body, "index"), body.get("event")), 0

    def _read(self, body: dict) -> tuple[dict, int]:
        return {"reads": [asdict(r) for r in self._session.read(_arg(body, "exprs"))]}, 0

    def _tag(self, body: dict) -> tuple[dict, int]:
        tag = _arg(body, "tag")
        self._session.tag(tag)
        return {"tag": tag}, 0

    def _enter_game(self, body: dict) -> tuple[dict, int]:
        return self._session.enter_game(), 0

    def _advance(self, body: dict) -> tuple[dict, int]:
        return {"reached": list(self._session.advance(_arg(body, "days")))}, 0

    def _shot(self, body: dict) -> tuple[dict, int]:
        return {"path": str(self._session.shot())}, 0

    def _try_event(self, body: dict) -> tuple[dict, int]:
        reply = self._session.try_event(_arg(body, "event"), body.get("setup"), _arg(body, "reads"))
        return reply, 0 if reply.get("complete") is True else 2         # a did-not-fire is never a pass

    # ---- session.json

    def _claim(self, port: int) -> None:
        """Create session.json, refusing (ServerError) one that is there: that names another server, live or dead,
        and `start` is the one that judges it. Written in one call, so a reader sees all of it or nothing."""
        self._info = {"port": port, "pid": os.getpid(), "started": self._started, "token": self.token}
        try:
            fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            raise ServerError("%s is there already: another session's server is running, or one died and left it "
                              "(`start` removes a stale one, `doctor` says which)" % self.path) from None
        try:
            os.write(fd, (json.dumps(self._info) + "\n").encode("utf-8"))
            os.fsync(fd)
        finally:
            os.close(fd)
        self._note("listening on %s:%d" % (HOST, port))

    def _update_info(self, **fields: Any) -> None:
        if not self._is_mine():
            return
        self._info.update(fields)
        temp = self.path.with_name("%s.%d.tmp" % (SESSION_FILE, os.getpid()))
        try:
            temp.write_text(json.dumps(self._info) + "\n", encoding="utf-8")
            os.replace(temp, self.path)
        except OSError as e:
            self._note("session.json could not be updated: %s" % e)
            temp.unlink(missing_ok=True)

    def _release(self) -> None:
        if self._is_mine():
            try:
                self.path.unlink()
            except OSError as e:
                self._note("session.json could not be removed: %s" % e)

    def _is_mine(self) -> bool:
        info = read_info(self._backup_root)
        return info is not None and info.get("pid") == os.getpid() and info.get("token") == self.token

    def _note(self, text: str) -> None:
        if self._log is None:
            return
        try:
            self._log.write("[%s] %s\n" % (stamp(utc_now()), text))
            self._log.flush()
        except (OSError, ValueError):
            pass


def _arg(body: dict, name: str):
    if name not in body:
        raise _BadBody("the request has no %r" % name)
    return body[name]


class _HTTPServer(HTTPServer):
    game_qa: SessionServer

    def server_bind(self) -> None:
        # HTTPServer.server_bind also looks the host's name up, which can stall; the name is never used here.
        socketserver.TCPServer.server_bind(self)
        self.server_name, self.server_port = self.server_address[:2]

    def handle_error(self, request, client_address) -> None:
        self.game_qa._note("a request from %s failed: %s" % (client_address, traceback.format_exc()))


class _Handler(BaseHTTPRequestHandler):
    server_version = "game_qa"

    def do_POST(self) -> None:
        owner = self.server.game_qa
        owner._busy = True
        if self.headers.get(TOKEN_HEADER) != owner.token:
            self._answer(403, {"refused": "forbidden", "detail": "the request did not carry this server's token "
                                                                 "(session.json)"}, 2)
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
            if not 0 <= length <= MAX_BODY:
                raise ValueError("a body of %d bytes" % length)
            body = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            if not isinstance(body, dict):
                raise ValueError("the body is not a JSON object")
        except ValueError as e:             # UnicodeDecodeError and JSONDecodeError are ValueErrors
            self._answer(400, {"refused": "bad_request", "detail": str(e)}, 2)
            return
        reply, code = owner.handle(self.path.lstrip("/"), body)
        self._answer(200, reply, code)

    def do_GET(self) -> None:
        self._answer(405, {"refused": "bad_request", "detail": "POST /<verb>"}, 2)

    def _answer(self, status: int, reply: dict, code: int) -> None:
        data = json.dumps({"code": code, "reply": reply}, ensure_ascii=False, default=str).encode("utf-8")
        try:
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except OSError as e:                # the client gave up waiting (its timeout): the verb ran all the same
            self.server.game_qa._note("the answer could not be sent: %s" % e)

    def log_message(self, format: str, *args) -> None:
        self.server.game_qa._note("%s %s" % (self.address_string(), format % args))
