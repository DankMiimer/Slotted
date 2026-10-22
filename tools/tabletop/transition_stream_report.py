"""Per-request switch timings from a frontend trial's stream.tsv.

python -m tools.tabletop.transition_stream_report STREAM.tsv [STREAM.tsv ...]

Counts each request that settled itself (not superseded): request -> first
motion (depart), ready, commit, landed and settled. Ticks restart when the
frontend restarts (after a game), which starts a new session.
"""
import json
import statistics
import sys


def sessions(path):
    current, previous = [], -1
    for line in open(path, encoding='utf8'):
        parts = line.rstrip('\n').split('\t')
        if len(parts) < 5:
            continue
        tick = int(parts[0])
        if tick < previous and current:
            yield current
            current = []
        previous = tick
        detail = dict(kv.split('=', 1) for kv in parts[5].split()) if len(parts) > 5 else {}
        current.append(dict(tick=tick, name=parts[1], generation=int(parts[2]), key=parts[3], detail=detail))
    if current:
        yield current


def requests(path):
    out = []
    for events in sessions(path):
        by = {}
        for e in events:
            if e['generation']:
                by.setdefault(e['generation'], {}).setdefault(e['name'], e)
        for gen, named in sorted(by.items()):
            end = named.get('settled') or named.get('items')
            if 'request' not in named or not end:
                continue
            base = named['request']['tick']
            rel = lambda name: named[name]['tick']-base if name in named else None
            ready = named.get('ready')
            out.append(dict(generation=gen, key=named['request']['key'], total=end['tick']-base,
                            motion=rel('depart'), ready=rel('ready'), release=rel('release'), commit=rel('commit'),
                            landed=rel('landed'), settled=rel('settled'), items=end['name'] == 'items',
                            prepare_ms=float(ready['detail']['prepare_ms']) if ready and 'prepare_ms' in ready['detail'] else None,
                            upload_ms=float(ready['detail']['upload_ms']) if ready and 'upload_ms' in ready['detail'] else None,
                            cached=ready['detail'].get('cached') if ready else None))
    return out


def describe(values):
    values = [v for v in values if v is not None]
    if not values:
        return 'n/a'
    return f'{min(values)}-{max(values)} ms, median {statistics.median(values):.0f}'


def main():
    for path in sys.argv[1:]:
        rows = [r for r in requests(path) if not r['items']]
        print('==', path, len(rows), 'settled switches')
        print('  request -> settled:', describe([r['total'] for r in rows]))
        print('  request -> first motion:', describe([r['motion'] for r in rows]))
        print('  request -> ready:', describe([r['ready'] for r in rows]))
        print('  request -> commit:', describe([r['commit'] for r in rows]))
        print('  commit -> landed:', describe([r['landed']-r['commit'] for r in rows if r['landed'] is not None and r['commit'] is not None]))
        print('  landed -> settled, PVM:', describe([r['settled']-r['landed'] for r in rows if r['settled'] is not None and r['landed'] is not None and '|pvm|' in r['key']]))
        print('  landed -> settled, Panasonic:', describe([r['settled']-r['landed'] for r in rows if r['settled'] is not None and r['landed'] is not None and '|panasonic|' in r['key']]))
        print('  commit -> settled:', describe([r['settled']-r['commit'] for r in rows if r['settled'] is not None and r['commit'] is not None]))
        with open(path+'.summary.json', 'w', encoding='utf8') as out:
            json.dump(rows, out, indent=2)


if __name__ == '__main__':
    main()
