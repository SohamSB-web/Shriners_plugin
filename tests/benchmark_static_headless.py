"""Compare isolated static runs. Live QTM is never contacted by the probes."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
from statistics import median
import subprocess
import sys
import tempfile
from time import perf_counter


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--session', required=True, type=Path)
    parser.add_argument('--filename', required=True)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--repeats', default=3, type=int)
    args = parser.parse_args()
    source = args.session.resolve(strict=True)
    if Path(args.filename).name != args.filename or args.output.suffix.lower() != '.json':
        raise ValueError('Use a measurement filename and a .json benchmark destination')
    if source == args.output.resolve() or source in args.output.resolve().parents:
        raise ValueError('Write the benchmark report outside the original clinical session')
    root = Path(__file__).resolve().parents[1]
    paths = [p for p in source.rglob('*') if p.is_file() and
             (p.name in ('session.xml', args.filename.split('.')[0]+'.c3d') or
              p.name.startswith(('Static_', 'SittingFootStatic_')) and p.suffix == '.py')]
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    with tempfile.TemporaryDirectory(prefix='.static-benchmark-', dir=args.output.parent) as scratch:
        for mode in ('legacy', 'legacy-normalized', 'engine'):
            for repeat in range(args.repeats):
                folder = Path(scratch) / f'{mode}-{repeat}'
                folder.mkdir()
                (folder / '.static-refactor-disposable').touch()
                for path in paths:
                    destination = folder / path.relative_to(source)
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(path, destination)
                result_path = Path(scratch) / f'{mode}-{repeat}.json'
                started = perf_counter()
                completed = subprocess.run([sys.executable, '-B', str(root/'tests/static_calibration_probe.py'),
                                            mode, str(folder/'session.xml'), args.filename, str(result_path)],
                                           capture_output=True, text=True, cwd=root,
                                           env=dict(os.environ, QT_QPA_PLATFORM='offscreen'), timeout=120)
                wall = perf_counter() - started
                if completed.returncode:
                    raise RuntimeError(completed.stdout[-1000:] + completed.stderr[-2000:])
                result = json.loads(result_path.read_text(encoding='utf8'))
                rows.append({'mode': mode, 'repeat': repeat+1, 'wall_seconds': wall,
                             'timings': result['timings'], 'marker_error': result['marker_error'],
                             'modeled_commands': len(result['commands'])})
    assert {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in paths} == before
    summary = {}
    for mode in ('legacy', 'legacy-normalized', 'engine'):
        selected = [row for row in rows if row['mode'] == mode]
        keys = selected[0]['timings'].keys()
        summary[mode] = {'wall_seconds': median(row['wall_seconds'] for row in selected),
                         'timings': {key: median(row['timings'][key] for row in selected) for key in keys},
                         'marker_error': selected[0]['marker_error'],
                         'modeled_commands': selected[0]['modeled_commands']}
    report = {'workload': 'Static trial copies; offline QTM acknowledgements; medians of repeated child processes',
              'reference_commit': 'e6b06a1', 'logical_cpus': os.cpu_count(), 'repeats': args.repeats,
              'source_hashes_unchanged': True, 'summary': summary, 'runs': rows}
    args.output.write_text(json.dumps(report, indent=2), encoding='utf8')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
