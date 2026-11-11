"""Wait for the harness's own game window; print presence readings; take one screenshot. Reads only."""
import sys, time, pathlib
sys.path.insert(0, '/home/<user>/src/vic3te-game-qa-session')
import path_constants as pc
from game_qa import gate
from game_qa.helper import ProcessHelper, HelperError
PROC = gate.ProcId(28572, '2026-11-11T08:10:19.9916174Z')
f = pathlib.Path(pc.game_user_data_path) / 'content_load.json'
h = ProcessHelper()
print('ping', h.ping())
try:
    h.adopt(gate.ProcId(PROC.pid, '1999-01-01T00:00:00.0000000Z')); print('adopt wrong time ACCEPTED (BAD)')
except HelperError as e:
    print('adopt with a wrong start time refused:', e.code)
h.adopt(PROC); print('adopt ok')
t0 = time.time(); last = None
while time.time() - t0 < float(sys.argv[1]):
    w = h.window(PROC.pid); p = h.presence(); st = f.stat()
    line = (w.exists, w.foreground, w.responding, w.title, w.client)
    print('%5.0fs window=%s presence=%s content_load=(%d, %d)' % (time.time() - t0, line, p, st.st_size, st.st_mtime_ns), flush=True)
    time.sleep(15)
shot = pathlib.Path(sys.argv[2])
try:
    print('screenshot', h.screenshot(PROC.pid, shot, max_width=1600))
except HelperError as e:
    print('screenshot refused', e.code, e.detail)
h.close()
