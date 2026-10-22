"""Summarize a fetched switch-timing study: python -m tools.tabletop.transition_timing_report SESSION_DIR

Per switch: preparation, request -> first motion / commit / settled, and the
frame intervals while something moves (lift, flight, arrival, pan). A frame
interval is the paced loop's time between frame starts (60 Hz when on time).
"""
import csv
import json
from pathlib import Path
import statistics
import sys


def events(path):
    rows = []
    if path.is_file():
        for line in path.read_text().splitlines():
            parts = line.split('\t')
            detail = dict(kv.split('=', 1) for kv in parts[5].split()) if len(parts) > 5 else {}
            rows.append(dict(tick=int(parts[0]), name=parts[1], generation=int(parts[2]), key=parts[3], detail=detail))
    return rows


def percentile(values, p):
    if not values:
        return None
    values = sorted(values)
    return values[min(len(values)-1, int(len(values)*p))]


def summarize(run):
    frames = list(csv.DictReader((run/'frames.tsv').open(), delimiter='\t'))
    stream = events(run/'stream.tsv')
    steps = {}
    for f in frames:
        if int(f['step']) >= 0 and f['system'] != 'idle':
            steps.setdefault(int(f['step']), []).append(f)
    out = []
    requests = [e for e in stream if e['name'] == 'request']
    for index, (step, rows) in enumerate(sorted(steps.items())):
        system = rows[0]['system']
        first = int(rows[0]['ticks'])
        # The request event precedes the step's first frame by under a frame.
        request = max((e for e in requests if e['tick'] <= first), key=lambda e: e['tick'])
        gen = request['generation']
        mine = [e for e in stream if e['generation'] == gen]
        tick = lambda name: next((e['tick'] for e in mine if e['name'] == name), None)
        ready = next((e for e in mine if e['name'] == 'ready'), None)
        depart, release, commit, landed, settled = tick('depart'), tick('release'), tick('commit'), tick('landed'), tick('settled')
        base = request['tick']
        rel = lambda t: None if t is None else t-base
        moving = []
        held = any(e['name'] == 'release' for e in stream)  # n19 only departs once prepared
        lift_end = (depart or base)+230
        for f in rows:
            if float(f['since_request_ms']) < 0:
                continue
            t, phase, interval = int(f['ticks']), int(f['phase']), float(f['interval_ms'])
            if phase == 2:
                state = 'fly' if not held or (release is not None and t >= release) else 'lift' if t <= lift_end else 'hold'
            elif phase in (3, 4):
                state = 'arrive' if phase == 3 else 'pan'
            else:
                state = 'wait' if phase == 1 else 'stable'
            if state in ('lift', 'fly', 'arrive', 'pan') and (settled is None or t <= settled):
                moving.append(interval)
        out.append(dict(
            step=step, system=system, generation=gen, cached=ready['detail'].get('cached') if ready else None,
            prepare_ms=float(ready['detail']['prepare_ms']) if ready and 'prepare_ms' in ready['detail'] else rel(ready['tick'] if ready else None),
            upload_ms=float(ready['detail'].get('upload_ms', 'nan')) if ready else None,
            wait_ms=float(ready['detail'].get('wait_ms', 'nan')) if ready else None,
            uploads=int(ready['detail'].get('uploads', '0')) if ready else None,
            max_upload_ms=float(ready['detail'].get('max_upload_ms', 'nan')) if ready else None,
            ready=rel(ready['tick'] if ready else None), motion=rel(depart), release=rel(release), commit=rel(commit),
            landed=rel(landed), settled=rel(settled),
            moving_frames=len(moving), moving_p50=percentile(moving, .5), moving_p95=percentile(moving, .95),
            moving_max=max(moving) if moving else None, moving_over_34=sum(v > 34 for v in moving),
            moving_over_50=sum(v > 50 for v in moving)))
    return out


def main():
    session = Path(sys.argv[1])
    report = {}
    for run in sorted(p for p in session.iterdir() if (p/'frames.tsv').is_file()):
        rows = summarize(run)
        report[run.name] = rows
        settled = [r['settled'] for r in rows if r['settled'] is not None]
        motion = [r['motion'] for r in rows if r['motion'] is not None]
        moving = [r['moving_p95'] for r in rows if r['moving_p95'] is not None]
        print(f"== {run.name}: settled median {statistics.median(settled):.0f} ms (min {min(settled)}, max {max(settled)}), "
              f"first motion median {statistics.median(motion):.0f} ms (max {max(motion)}), "
              f"moving-frame p95 median {statistics.median(moving):.1f} ms, "
              f"moving frames >34 ms {sum(r['moving_over_34'] for r in rows)}/{sum(r['moving_frames'] for r in rows)}, "
              f">50 ms {sum(r['moving_over_50'] for r in rows)}")
        for r in rows:
            print('  {step:2d} {system:5s} cached={cached} prep={prepare_ms} up={upload_ms}/{uploads} max_up={max_upload_ms} '
                  'motion={motion} ready={ready} release={release} commit={commit} landed={landed} settled={settled} '
                  'moving p95={moving_p95} max={moving_max} >34={moving_over_34}'.format(**r))
    (session/'timing-summary.json').write_text(json.dumps(report, indent=2)+'\n')


if __name__ == '__main__':
    main()
