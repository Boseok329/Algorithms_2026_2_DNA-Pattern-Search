"""보존한 원본과 공통 입력으로 세 검색 알고리즘을 동일 조건에서 측정한다."""
import argparse
import csv
import gc
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import random
import statistics
import sys
from datetime import datetime, timedelta, timezone
from time import perf_counter_ns
import tracemalloc

ROOT = Path(__file__).resolve().parent.parent
ALGORITHMS = ('Naive', 'KMP', 'Boyer-Moore')
KST = timezone(timedelta(hours=9))
SEED = 20261104


def now():
    return datetime.now(KST).isoformat()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def load_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def implementations():
    naive = load_module('frozen_naive', ROOT / 'originals' / 'naive.py')
    kmp = load_module('frozen_kmp', ROOT / 'originals' / 'kmp.py')
    bm = load_module('frozen_bm', ROOT / 'originals' / 'boyer_moore.py')
    timed_kmp = load_module('derived_kmp', ROOT / 'code' / 'kmp_timed.py')
    # 세 알고리즘 모두 같은 (pattern, text) 호출 계층을 거친다.
    timed = {
        'Naive': lambda p, t: naive.search(p, t),
        'KMP': lambda p, t: timed_kmp.kmp_search(p, t),
        'Boyer-Moore': lambda p, t: bm.search_text(t, p),
    }

    def count_naive(p, t):
        positions, count = naive.search_counted(p, t)
        return positions, 0, count

    def count_bm(p, t):
        result = bm.search_text_counted(t, p)
        return result.positions, result.preprocessing_comparisons, result.search_comparisons

    counted = {'Naive': count_naive, 'KMP': kmp.kmp_search, 'Boyer-Moore': count_bm}
    return timed, counted


def reference_positions(text, pattern):
    positions, start = [], 0
    while True:
        index = text.find(pattern, start)
        if index < 0:
            return positions
        positions.append(index)
        start = index + 1


def load_cases():
    manifest = load_json(ROOT / 'snapshot_manifest.json')
    for item in manifest['files']:
        if sha(ROOT / item['snapshot']) != item['sha256']:
            raise ValueError(f"보존 사본 해시 불일치: {item['snapshot']}")
    cases, cache = [], {}
    for experiment, count in ((1, 30), (2, 54), (3, 27)):
        ref = ROOT / 'reference' / f'실험 {experiment}'
        package = load_json(ref / 'cases.json')
        answers = load_json(ref / 'expected_positions.json')
        if len(package['cases']) != count:
            raise ValueError('실험 조건 수 불일치')
        for row in package['cases']:
            c = dict(row)
            if experiment < 3:
                pattern_name = f"pattern_{c['source']}_{c['pattern_id']}_m{c['m']}.txt"
            else:
                pattern_name = f"pattern_{c['repeat_unit']}_{c['condition']}.txt"
            folder = ROOT / 'inputs' / f'실험 {experiment}'
            tp = folder / c['text_file']
            if tp not in cache:
                data = tp.read_bytes()
                cache[tp] = (data.decode('ascii'), hashlib.sha256(data).hexdigest())
            text, text_hash = cache[tp]
            raw_pattern = (folder / '패턴' / pattern_name).read_bytes()
            pattern = raw_pattern.decode('ascii')
            if (not pattern or set(pattern + text) - set('ACGT') or len(text) != c['n']
                    or len(pattern) != c['m'] or pattern != c['pattern'] or text_hash != c['text_sha256']):
                raise ValueError(f"입력 불일치: {c['case_id']}")
            expected = answers[c['case_id']]
            if reference_positions(text, pattern) != expected or len(expected) != c['expected_match_count']:
                raise ValueError(f"기준 정답 불일치: {c['case_id']}")
            c.update(experiment=experiment, text=text, pattern=pattern, expected=expected,
                     pattern_file=pattern_name, pattern_sha256=hashlib.sha256(raw_pattern).hexdigest())
            cases.append(c)
    if len({c['case_id'] for c in cases}) != 111:
        raise ValueError('조건 ID 중복')
    return cases


def verify(positions, case, algorithm, phase):
    if positions != case['expected']:
        raise ValueError(f"전체 위치 불일치: {phase} / {algorithm} / {case['case_id']}")


def check_originals():
    """Verify the three preserved implementations inside this repository."""
    files = [item for item in load_json(ROOT / 'snapshot_manifest.json')['files']
             if item['snapshot'].startswith('originals/')]
    changed = [item['snapshot'] for item in files
               if not (ROOT / item['snapshot']).is_file()
               or sha(ROOT / item['snapshot']) != item['sha256']]
    expected = {item['snapshot'] for item in files}
    actual = {p.relative_to(ROOT).as_posix() for p in (ROOT / 'originals').glob('*.py')}
    return {'checked_files': len(files), 'changed_or_missing': changed,
            'added_files': sorted(actual - expected),
            'unchanged': not changed and actual == expected}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repeats', type=int, default=5)
    ap.add_argument('--out', type=Path)
    ap.add_argument('--validate-only', action='store_true', help='111조건 입력·정답·함수 동등성만 검증')
    args = ap.parse_args()
    if args.repeats < 2:
        ap.error('반복 측정은 2회 이상이어야 합니다.')
    timed, counted = implementations()
    cases = load_cases()
    if args.validate_only:
        for c in cases:
            for name in ALGORITHMS:
                verify(timed[name](c['pattern'], c['text']), c, name, 'validation')
                verify(counted[name](c['pattern'], c['text'])[0], c, name, 'counted validation')
        integrity = check_originals()
        if not integrity['unchanged']:
            raise ValueError(integrity)
        print(json.dumps({'verified_cases_per_algorithm': 111, 'original_integrity': integrity}, ensure_ascii=False))
        return

    out = args.out.resolve() if args.out else ROOT / 'results' / datetime.now(KST).strftime('%Y%m%d_%H%M%S')
    out.mkdir(parents=True, exist_ok=False)
    metadata = dict(status='running', phase='warmup_and_timing', started_at=now(),
                    python=sys.version, executable=Path(sys.executable).name, platform=platform.platform(),
                    processor=platform.processor(), logical_cpus=os.cpu_count(),
                    host={'background_policy': 'No controlled OS isolation; other applications may affect timings.'}, algorithms=list(ALGORITHMS),
                    cases=111, conditions_by_experiment={'1': 30, '2': 54, '3': 27},
                    repeats=args.repeats, warmups=1, timer='time.perf_counter_ns', time_unit='ms',
                    order_seed=SEED, order_policy='seeded shuffle of cases; cyclic algorithm order by case_index + repeat_index',
                    timing_scope='preprocessing + search + complete positions list; excludes file I/O, validation, counters, memory tracing, output',
                    gc_policy='collect outside timing once per case; disable cyclic GC for all timed calls, then restore',
                    comparison_scope='explicit pattern-pattern preprocessing and text-pattern search character comparisons; integer/hash operations excluded',
                    memory_scope='one separate tracemalloc(1) session per condition and algorithm; peak traced Python allocations during full function call, including preprocessing and output list; excludes preexisting inputs; not process RSS',
                    memory_unit='bytes', memory_repeats=1,
                    input_policy='exact frozen ASCII ACGT bytes, nonempty pattern, zero-based overlapping positions',
                    kmp_timing_variant='original LPS/search control flow with comparison counter operations removed; original kmp.py used for counted run',
                    code_sha256={p.relative_to(ROOT).as_posix(): sha(p) for folder in ('code', 'originals') for p in sorted((ROOT / folder).glob('*.py'))},
                    input_manifest_sha256=sha(ROOT / 'snapshot_manifest.json'),
                    original_integrity_before=check_originals())
    if not metadata['original_integrity_before']['unchanged']:
        raise ValueError('측정 전 원본 무결성 확인 실패')
    write_json(out / 'metadata.json', metadata)
    case_fields = ['case_id', 'experiment', 'source', 'suite', 'repeat_unit', 'condition', 'n', 'm',
                   'pattern_id', 'pattern_start_0based', 'text_file', 'pattern_file', 'text_sha256', 'pattern_sha256']
    with (out / 'conditions.csv').open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=case_fields)
        w.writeheader()
        w.writerows({k: c.get(k, '') for k in case_fields} for c in cases)
    schedule = list(cases)
    random.Random(SEED).shuffle(schedule)
    times = {(c['case_id'], a): [] for c in cases for a in ALGORITHMS}
    raw_fields = ['case_id', 'algorithm', 'experiment', 'repeat', 'order_in_round', 'case_execution_order', 'time_ms', 'match_count', 'correct']
    try:
        with (out / 'runs.csv').open('w', encoding='utf-8-sig', newline='') as f:
            w = csv.DictWriter(f, fieldnames=raw_fields)
            w.writeheader()
            for idx, c in enumerate(schedule):
                p, text = c['pattern'], c['text']
                for k in range(3):
                    name = ALGORITHMS[(idx + k) % 3]
                    positions = timed[name](p, text)
                    verify(positions, c, name, 'warmup')
                    del positions
                gc.collect()
                enabled = gc.isenabled()
                gc.disable()
                try:
                    for repeat in range(args.repeats):
                        for order in range(3):
                            name = ALGORITHMS[(idx + repeat + order) % 3]
                            fn = timed[name]
                            start = perf_counter_ns()
                            positions = fn(p, text)
                            elapsed = (perf_counter_ns() - start) / 1_000_000
                            verify(positions, c, name, 'timed')
                            times[(c['case_id'], name)].append(elapsed)
                            w.writerow(dict(case_id=c['case_id'], algorithm=name, experiment=c['experiment'],
                                            repeat=repeat + 1, order_in_round=order + 1, case_execution_order=idx + 1,
                                            time_ms=repr(elapsed), match_count=len(positions), correct=True))
                            del positions
                finally:
                    if enabled:
                        gc.enable()
                f.flush()
                if (idx + 1) % 5 == 0 or idx == 110:
                    print(f'TIMING {idx + 1}/111 cases; {(idx + 1) * 3 * args.repeats} samples', flush=True)

        metadata.update(phase='counts_and_memory', timing_finished_at=now(), timed_runs=111 * 3 * args.repeats)
        write_json(out / 'metadata.json', metadata)
        print('TIMING COMPLETE; starting separate comparison counts and memory measurements', flush=True)
        summary_fields = case_fields + ['algorithm', 'match_count', 'repeats', 'mean_ms', 'median_ms', 'min_ms', 'max_ms', 'stdev_ms',
                                        'preprocessing_comparisons', 'search_comparisons', 'total_comparisons',
                                        'peak_python_bytes', 'retained_python_bytes', 'correct', 'positions_sha256']
        with (out / 'summary.csv').open('w', encoding='utf-8-sig', newline='') as f:
            w = csv.DictWriter(f, fieldnames=summary_fields)
            w.writeheader()
            for idx, c in enumerate(cases):
                p, text = c['pattern'], c['text']
                for name in ALGORITHMS:
                    positions, pre, search = counted[name](p, text)
                    verify(positions, c, name, 'counted')
                    digest = hashlib.sha256(json.dumps(positions, separators=(',', ':')).encode('ascii')).hexdigest()
                    del positions
                    if name == 'Naive' and c.get('repeat_unit') == 'A':
                        expected_count = (c['n'] - c['m'] + 1) * (1 if c['condition'] == 'start_mismatch' else c['m'])
                        if search != expected_count:
                            raise ValueError('Naive A 반복 비교 횟수 검산 실패')
                    fn = timed[name]
                    gc.collect()
                    enabled = gc.isenabled()
                    gc.disable()
                    tracemalloc.start(1)
                    try:
                        positions = fn(p, text)
                        retained, peak = tracemalloc.get_traced_memory()
                    finally:
                        tracemalloc.stop()
                        if enabled:
                            gc.enable()
                    verify(positions, c, name, 'memory')
                    del positions
                    samples = times[(c['case_id'], name)]
                    row = {k: c.get(k, '') for k in case_fields}
                    row.update(algorithm=name, match_count=len(c['expected']), repeats=args.repeats,
                               mean_ms=statistics.mean(samples), median_ms=statistics.median(samples),
                               min_ms=min(samples), max_ms=max(samples), stdev_ms=statistics.stdev(samples),
                               preprocessing_comparisons=pre, search_comparisons=search, total_comparisons=pre + search,
                               peak_python_bytes=peak, retained_python_bytes=retained, correct=True, positions_sha256=digest)
                    w.writerow(row)
                    f.flush()
                if (idx + 1) % 3 == 0 or idx == 110:
                    print(f'MEMORY/COUNTS {idx + 1}/111 cases; {(idx + 1) * 3} algorithm cases', flush=True)
        integrity = check_originals()
        if not integrity['unchanged']:
            raise ValueError(f'원본 변경 감지: {integrity}')
        metadata.update(status='complete', phase='complete', finished_at=now(), verified_algorithm_cases=333,
                        all_positions_verified=True, counted_runs=333, memory_runs=333,
                        original_integrity_after=integrity)
        write_json(out / 'metadata.json', metadata)
        print(f'COMPLETE: {out}', flush=True)
    except BaseException as exc:
        metadata.update(status='failed', failed_at=now(), error=f'{type(exc).__name__}: {exc}')
        write_json(out / 'metadata.json', metadata)
        raise


if __name__ == '__main__':
    main()
