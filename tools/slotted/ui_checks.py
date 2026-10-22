"""Slotted-specific full-screen theme checks inside the temporary GUI transaction."""
import argparse
import json
import subprocess
from tools.tabletop.device_probe import Remote, ROOT
from tools.tabletop.transition_ui_checks import PRELUDE

BASE = ROOT / 'build/slotted-phase2'
MENUS = r'''
esdev.press(['start']);time.sleep(.8);shot('slotted-room-menu')
esdev.press(['b']);time.sleep(.5)
esdev.press(['select']);time.sleep(.8);shot('slotted-game-options')
esdev.press(['b']);time.sleep(.5)
esdev.press(['b']);time.sleep(1);shot('slotted-system-view')
esdev.press(['start']);time.sleep(.8);shot('slotted-system-menu')
esdev.press(['b']);time.sleep(.5)
esdev.press(['a']);time.sleep(2);shot('slotted-room-return')
assert json.loads(esdev.api('/runningGame'))=={'msg':'NO GAME RUNNING'}
result=dict(roomMenu=True,gameOptions=True,systemView=True,systemMenu=True,returned=True,noGame=True,state='complete')
(job/'menus-checks.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result))
'''
FINISH = r'''
checks={name:json.loads((job/(name+'-checks.json')).read_text()) for name in ('initial','smoke','rapid','launch','menus')}
assert all(value.get('state')=='complete' for value in checks.values()),checks
assert checks['launch']['exactlyOnce']
assert checks['smoke']['firstAHeldInsertsOnly']
assert checks['rapid']['rapidRequests']==16
result=dict(passed=True,checks=checks)
(job/'finish.json').write_text(json.dumps(result,indent=2))
print('All requested GUI checks passed; restoring the prior frontend/theme/data')
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('step', choices=('menus', 'finish'))
    args = parser.parse_args()
    job = json.loads((BASE / 'trial-job.json').read_text())['job']
    code = PRELUDE.replace('JOB', repr(job)) + '\n' + (MENUS if args.step == 'menus' else FINISH)
    try:
        print(Remote().python(code, timeout=60).decode())
    except subprocess.CalledProcessError as error:
        raise SystemExit(error.stderr.decode('utf-8', 'replace')) from None


if __name__ == '__main__':
    main()
