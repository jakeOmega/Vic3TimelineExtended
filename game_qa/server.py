"""The session server: one process that holds one `Session`, for the life of one game, and answers its verbs.

    POST http://127.0.0.1:<port>/<verb>       a JSON object of the verb's arguments, and the server's token
    -> {"code": 0 | 2, "reply": {...}}       the verb's reply, and the exit code its command-line verb gives

`python3 -m game_qa start` runs `python3 -m game_qa session-serve` detached and then posts `start` to it; every
other verb is a thin client of it (`game_qa/client.py`). The server binds 127.0.0.1 only, answers one request at
a time, and holds exactly one `Session`. While it listens, `<backup root>/session.json` names it: `port`, `pid`,
`started`, then `snapshot` once the session has started, and `token`, which every request must carry, so that no
other program on the machine (a web page in a browser included) can type into the game. The file is its owner's
alone to read (0600), and the server removes it when it exits by any route it controls, never one another server
wrote. Every request also carries its client's expiry (`X-Game-QA-Expires`: when the client stops waiting, by
`machine_clock`); the server never begins a request whose expiry has passed (`expired`), so a verb whose client
gave up behind a long one is not run later, out of its sight. A connection that sends nothing is dropped after
HANDLER_TIMEOUT_S, so it cannot keep `stop` waiting.

The server never touches the owner's files itself: only the `Session` does, through part 1's verbs. If the
server is killed outright nothing here restores anything. `watch`, its own process, still records the game's
exit, and the next `start` is refused: the dead run's overlay is still there (`overlay_left`), and `snapshot`
refuses while that run is unfinished. `recover` finishes it, and then `python3 -m game_qa remove-overlay`
removes the folder (spec § 5.2, Review Focus 1).

    start      the session's start. Any error stops the session; the server then ends as after `stop`. A second
               `start` is refused `session_running`, touching nothing
    fixture    instead of `start`: one unattended run that makes a dated fixture (`Session.make_fixture`, #1602),
               then the session's stop, whatever happened; the server then ends as after `stop`. It may run for
               hours, and nothing else is answered meanwhile (`status` included: a client sees `no_answer`)
    stop       the session's stop. The server answers with its reply, then exits, unless the stop can be run again
               to effect (`final_stop`: a restore refused for a reason waiting can clear, a game left up that is
               known by pid and start time): then it serves on, and `stop` again runs the stop again
    selfchecks the verdicts of the mod's TE_SELF_CHECK lines in the session's run so far, the game's log
               flushed first (`Session.self_checks`)
    status     the server and the session, answered here without asking the game anything
    the rest   console, run-setup, add-setup, press, events, pick, read, tag, enter-game, advance, shot, click, try-event,
               profiler-roots, wheel, drag

An error inside a verb becomes a refusal, `{"refused": <code>, "detail": …}`, with `entered` for a console error
and whatever else the error carries (a `SessionError`'s `info`), and the server keeps running.

SIGTERM and SIGINT stop the session (again, when the last stop can be run again), then remove the file. A signal
while a verb runs is noted and acted on once that verb has answered: a verb is never cut short, since it may be
typing into the game, waiting on the helper's pipe (whose lock `stop` would then wait on for ever) or running a
protective verb (which a cut would leave holding the backup root's lock).
"""
from __future__ import annotations

import hmac
import json
import math
import os
import signal
import socketserver
import time
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
EXPIRES_HEADER = "X-Game-QA-Expires"    # machine_clock seconds: the client has stopped waiting by then
HANDLER_TIMEOUT_S = 5.0                 # a connection that sends nothing for that long is dropped: well inside the
                                        # client's STATUS_TIMEOUT_S, so `status` and `stop` answer past one
RETRYABLE = ("refused", "game_left_up", "in_progress")     # a stop that ended so may end otherwise when run again
MAX_BODY = 1 << 20                      # a request's JSON: setup scripts are the largest part
START_ARGS = ("permission", "as_tag", "setups", "save", "playset", "owner_confirmed_busy", "switch_rules",
              "fixture_date")
FIXTURE_ARGS = ("permission", "until", "playset", "owner_confirmed_busy", "max_hours")


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
    """Whether a stop's reply says the owner's files are back (or that no snapshot was ever taken) and nothing of
    the run is left: not an overlay kept, nor a snapshot that may have been taken when its reply was lost."""
    return (reply.get("held") is not True and not reply.get("refused") and reply.get("outcome") in ("restored", None)
            and not reply.get("overlay_kept") and not reply.get("snapshot_unknown"))


def machine_clock() -> float:
    """The clock a request's expiry is set and judged by: CLOCK_MONOTONIC, one clock for every process on this
    machine (the client and its server always share one: the server binds 127.0.0.1), and never stepped. Not
    `time.time()`: under WSL2 the wall clock steps back about 2 s every half minute or so (measured 2026-11-11,
    3 runs in 300), which would let a request whose client gave up run after all."""
    return time.clock_gettime(time.CLOCK_MONOTONIC)


def final_stop(reply: Any) -> bool:
    """Whether a stop's reply ends the server: running the stop again cannot change it. The session says so in
    `stop_again`; a reply without it is judged by its outcome (RETRYABLE). Anything that is not a reply is final."""
    if not isinstance(reply, dict):
        return True
    again = reply.get("stop_again")
    if isinstance(again, bool):
        return not again
    return reply.get("outcome") not in RETRYABLE


class SessionServer:
    """Serves one `Session` (or anything with its public methods) on HOST until a final stop (from `stop` or a
    failed `start`) or a signal; `serve` returns what it did. `log` gets one line per request and per event, or
    nothing when None. `now` is the clock a request's expiry is judged by (`machine_clock`)."""

    def __init__(self, session, backup_root: Path, port: int = PORT, log: TextIO | None = None,
                 now: Callable[[], float] = machine_clock) -> None:
        self._session = session
        self._backup_root = Path(backup_root)
        self._port = port
        self._log = log
        self._now = now
        self.token = os.urandom(16).hex()
        self.address: tuple[str, int] | None = None
        self._started = stamp(utc_now())
        self._info: dict | None = None
        self._done = False                  # the loop ends after the request in progress
        self._busy = False                  # a request is being answered: a signal waits for it
        self._signalled: int | None = None
        self._start_posted = False
        self._stop_reply: dict | None = None    # the last stop's reply, from the `stop` verb or a failed start
        self._served = 0
        self._verbs: dict[str, Callable[[dict], tuple[dict, int]]] = {
            "console": self._console, "run-setup": self._run_setup, "add-setup": self._add_setup,
            "events": self._events, "pick": self._pick, "press": self._press,
            "read": self._read, "tag": self._tag, "enter-game": self._enter_game, "advance": self._advance,
            "shot": self._shot, "click": self._click, "try-event": self._try_event,
            "selfchecks": self._selfchecks,
            "profiler-roots": self._profiler_roots,
            "wheel": self._wheel, "drag": self._drag,
        }

    @property
    def path(self) -> Path:
        return self._backup_root / SESSION_FILE

    # ---- the loop

    def serve(self, signals: bool = False) -> dict:
        """Listen, claim session.json, answer requests one at a time until the session is over, then stop the
        session unless a `stop` verb or a failed start already has, and remove the file. After a signal a stop
        whose reply can change when run again (not `final_stop`) is run once more; otherwise the last stop's reply
        stands, since `Session.stop` would run a refused stop again, out of the caller's sight.
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
                    if self._stop_reply is None or (self._signalled is not None and not final_stop(self._stop_reply)):
                        stopped = self._stop_session()
                    else:
                        stopped = self._stop_reply
                    if not final_stop(stopped):
                        # Its `next` says `stop` again, and this server is going: say what works instead.
                        self._note("exiting with a stop that could be run again (outcome %s), so its run is left "
                                   "unfinished: once no Victoria 3 process runs, `python3 -m game_qa recover` "
                                   "finishes it, then `python3 -m game_qa remove-overlay`"
                                   % (stopped or {}).get("outcome"))
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
        if verb == "fixture":
            return self._fixture(body)
        if verb == "stop":
            reply = self._stop_reply = self._stop_session()
            self._done = final_stop(reply)
            if not self._done:
                self._note("the stop ended %s and can be run again: serving on" % reply.get("outcome"))
            return reply, 0 if clean_stop(reply) else 2
        run = self._verbs.get(verb)
        if run is None:
            return {"refused": "unknown_verb", "detail": "%r is not a verb of the session server; it has %s" % (
                verb, ", ".join(sorted(["start", "fixture", "stop", "status", *self._verbs])))}, 2
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
            if "stop" not in out:               # not setdefault: its argument, a stop, would run every time
                out["stop"] = self._stop_session()
            self._stop_reply = out["stop"] if isinstance(out["stop"], dict) else None
            self._done = final_stop(out["stop"])     # a stop that can be run again leaves the server for `stop`
            return out, 2
        if isinstance(reply, dict) and reply.get("snapshot"):
            self._update_info(snapshot=reply["snapshot"])
        return reply, 0

    def _fixture(self, body: dict) -> tuple[dict, int]:
        """`make_fixture`, once per server and only instead of `start`; the session is stopped after it either
        way, and the server ends as after a final stop."""
        if self._start_posted:
            return {"refused": "session_running", "detail": "this server's session has had its start: one server "
                                                            "holds one session, for one game"}, 2
        self._start_posted = True
        code = 0
        try:
            unknown = sorted(set(body) - set(FIXTURE_ARGS))
            if unknown or "permission" not in body or "until" not in body:
                raise _BadBody("fixture takes %s (permission and until required), not %s"
                               % (", ".join(FIXTURE_ARGS), unknown))
            out = self._session.make_fixture(**{k: body[k] for k in FIXTURE_ARGS if k in body})
        except Exception as e:
            out = {"refused": "bad_argument", "detail": str(e)} if isinstance(e, _BadBody) else refusal(e)
            code = 2
        if "stop" not in out:
            out["stop"] = self._stop_session()
        self._stop_reply = out["stop"] if isinstance(out["stop"], dict) else None
        self._done = final_stop(out["stop"])
        if code == 0 and not clean_stop(out["stop"] if isinstance(out["stop"], dict) else {}):
            code = 2
        return out, code

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

    def _add_setup(self, body: dict) -> tuple[dict, int]:
        return self._session.add_setup(_arg(body, "name"), _arg(body, "script")), 0

    def _press(self, body: dict) -> tuple[dict, int]:
        return self._session.press(_arg(body, "key")), 0

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

    def _click(self, body: dict) -> tuple[dict, int]:
        return self._session.click(body.get("x"), body.get("y"), console=body.get("console") is True,
                                   input_line=body.get("input_line")), 0

    def _wheel(self, body: dict) -> tuple[dict, int]:
        return self._session.wheel(_arg(body, "x"), _arg(body, "y"), _arg(body, "notches")), 0

    def _drag(self, body: dict) -> tuple[dict, int]:
        return self._session.drag(_arg(body, "x1"), _arg(body, "y1"), _arg(body, "x2"), _arg(body, "y2")), 0

    def _profiler_roots(self, body: dict) -> tuple[dict, int]:
        return self._session.profiler_roots(body.get("box"), as_shown=body.get("as_shown") is True), 0

    def _try_event(self, body: dict) -> tuple[dict, int]:
        reply = self._session.try_event(_arg(body, "event"), body.get("setup"), _arg(body, "reads"))
        return reply, 0 if reply.get("complete") is True else 2         # a did-not-fire is never a pass

    def _selfchecks(self, body: dict) -> tuple[dict, int]:
        return self._session.self_checks(), 0

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
            # 0600 like the claim: the file holds the token. fchmod too, for a temp file an earlier server of this
            # pid left with other bits (O_CREAT's mode applies only to a file it creates).
            fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            try:
                os.fchmod(fd, 0o600)
                os.write(fd, (json.dumps(self._info) + "\n").encode("utf-8"))
                os.fsync(fd)
            finally:
                os.close(fd)
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
    timeout = HANDLER_TIMEOUT_S             # each read and write of a connection: a silent one cannot stall the loop

    def do_POST(self) -> None:
        owner = self.server.game_qa
        owner._busy = True
        given = (self.headers.get(TOKEN_HEADER) or "").encode("utf-8", "replace")
        if not hmac.compare_digest(given, owner.token.encode("ascii")):
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
        try:
            expires = float(self.headers.get(EXPIRES_HEADER) or "")
            if not math.isfinite(expires):
                raise ValueError(expires)
        except ValueError:
            self._answer(400, {"refused": "bad_request",
                               "detail": "the request carries no expiry (%s: seconds of the machine's monotonic clock)"
                                         % EXPIRES_HEADER}, 2)
            return
        verb = self.path.lstrip("/")
        late = owner._now() - expires
        if late >= 0:
            # Its client has stopped waiting (it queued behind a long verb): it is never begun, so nothing it does
            # happens out of its caller's sight.
            owner._note("verb %s not run: its client stopped waiting %.1f s ago" % (verb, late))
            self._answer(200, {"refused": "expired", "detail": "%s was not run: its client had stopped waiting %.1f s "
                                                               "before the server could begin it" % (verb, late)}, 2)
            return
        reply, code = owner.handle(verb, body)
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
