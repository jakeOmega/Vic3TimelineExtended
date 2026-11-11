import sys, time
from pathlib import Path
sys.path.insert(0, "/home/<user>/src/vic3te-game-qa-part2")
from game_qa import gate, dap
from game_qa.helper import ProcessHelper, HelperError

HIST = Path("/mnt/c/Users/<winuser>/OneDrive/Documents/Paradox Interactive/Victoria 3/console_history.txt")
games = gate.list_games(); assert len(games) == 1, games
game = games[0]; print("game (PowerShell):", game)
h = ProcessHelper()
t0 = time.time(); print("U1 ping:", h.ping(), f"({time.time()-t0:.1f}s to start)")
try:
    h.adopt(gate.ProcId(game.pid, "1999-01-01T00:00:00.0000000Z")); print("adopt with a wrong time: ACCEPTED (BAD)")
except HelperError as e:
    print("adopt with a wrong creation time refused:", e.code)
h.adopt(game); print("adopt: created string equals PowerShell's -> OK")
w = h.window(game.pid); print("window:", w)
print("idle_ms:", h.idle_ms())
print("focus:", h.focus(game.pid)); print("window after focus:", h.window(game.pid).foreground)
before = HIST.read_text(encoding="utf-8", errors="replace").splitlines()
h.keys(game.pid, [{"text": "help observe"}, {"scan": 0x1C}]); time.sleep(1.0)
after = HIST.read_text(encoding="utf-8", errors="replace").splitlines()
print("U2 keys: history gained", after[len(before):])
print("idle_ms after our keys:", h.idle_ms())
shot = h.screenshot(game.pid, Path("/mnt/c/Users/<winuser>/AppData/Local/Temp/te_qa/helper_shot.png"), max_width=1300)
print("U2 screenshot:", shot, Path(shot).stat().st_size, "bytes")
# debugger over the helper's TCP relay
h.tcp_open(6111)
def recv(timeout):
    try: return h.tcp_recv(timeout)
    except HelperError as e: print("recv error", e.code); return b""
dbg = dap.Debugger(h.tcp_send, recv)
print("debugger attach over relay:", dbg.attach({}))
ev = dbg.evaluate("c:FRA.gdp"); print("evaluate while running:", ev.ok, ev.raw)
h.tcp_close()
print("ping at the end:", h.ping())
if "--kill" in sys.argv:
    h.kill(game); time.sleep(3); print("kill sent; games now:", gate.list_games())
h.close()
