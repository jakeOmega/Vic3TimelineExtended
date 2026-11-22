"""Live click proof on the main menu: refusals, then ONE real click on Credits (harmless), Esc back. Calls only the reviewed helper."""
import sys, time, pathlib
sys.path.insert(0, '/home/<user>/src/vic3te-game-qa-session')
from game_qa import gate
from game_qa.helper import ProcessHelper, HelperError
PROC = gate.ProcId(28572, '2026-11-11T08:10:19.9916174Z')
S = pathlib.Path(sys.argv[1])
h = ProcessHelper(); h.adopt(PROC)
w = h.window(PROC.pid); print('window', w); print('presence before', h.presence())
for pt in ((-5, 100), (3840, 100), (100, 2160), (99999, 5)):
    try:
        h.click(PROC.pid, *pt); print('click', pt, 'ACCEPTED (BAD)')
    except HelperError as e:
        print('click', pt, 'refused:', e.code)
print('presence after refusals', h.presence())
t = time.time(); h.click(PROC.pid, 799, 1613); print('click Credits (799, 1613) sent in %.2fs' % (time.time() - t))
print('presence after click', h.presence())
time.sleep(2.5); h.screenshot(PROC.pid, S / 'after_click.png', max_width=1200)
h.keys(PROC.pid, [{"scan": 0x01}]); time.sleep(2.0)
h.screenshot(PROC.pid, S / 'after_esc.png', max_width=1200)
p1 = h.presence(); time.sleep(3.2); p2 = h.presence(); time.sleep(3.2); p3 = h.presence()
print('three presence readings 3.2 s apart:', p1, p2, p3)
print('window at end', h.window(PROC.pid))
h.close()
