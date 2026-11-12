"""End the harness's own game: adopt by pid AND start time, kill, confirm by the process listing."""
import sys, time, pathlib
sys.path.insert(0, '/home/<user>/src/vic3te-game-qa-session')
import path_constants as pc
from game_qa import gate
from game_qa.helper import ProcessHelper
PROC = gate.ProcId(28572, '2026-11-11T08:10:19.9916174Z')
f = pathlib.Path(pc.game_user_data_path) / 'content_load.json'
games = gate.list_games(); print('listed before:', games); assert games == [PROC], games
h = ProcessHelper(); h.adopt(PROC)
print('presence before kill', h.presence(), 'content_load', f.stat().st_size, f.stat().st_mtime_ns)
print('kill: already_exited =', h.kill(PROC))
for i in range(20):
    time.sleep(1.5); games = gate.list_games()
    if not games: break
print('listed after %.0fs:' % ((i + 1) * 1.5), games, '; content_load', f.stat().st_size, f.stat().st_mtime_ns)
h.close()
