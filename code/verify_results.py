"""저장된 통합 실험 결과의 완전성·통계·정답 해시·원본 보존을 검증한다."""
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
import math
from pathlib import Path
import statistics

from run_benchmark import ROOT, ALGORITHMS, check_originals, load_json, sha, write_json


def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def main():
    if not __debug__:
        raise RuntimeError("Validation requires assertions; do not run Python with -O or -OO.")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('result_folder', type=Path)
    out = ap.parse_args().result_folder.resolve()
    meta = load_json(out / 'metadata.json')
    assert meta['status'] == 'complete'
    repeats = meta['repeats']
    conditions = read_csv(out / 'conditions.csv')
    raw = read_csv(out / 'runs.csv')
    summary = read_csv(out / 'summary.csv')
    ids = {r['case_id'] for r in conditions}
    assert len(ids) == len(conditions) == 111
    assert Counter(r['experiment'] for r in conditions) == {'1': 30, '2': 54, '3': 27}
    keys = {(case, name) for case in ids for name in ALGORITHMS}
    assert len(raw) == 333 * repeats and len(summary) == 333
    assert len({(r['case_id'], r['algorithm']) for r in summary}) == 333
    assert {(r['case_id'], r['algorithm']) for r in summary} == keys
    runs, rounds = defaultdict(list), defaultdict(list)
    positions_per_algorithm = defaultdict(Counter)
    for r in raw:
        key = (r['case_id'], r['algorithm'])
        assert key in keys and r['correct'] == 'True'
        assert math.isfinite(float(r['time_ms'])) and float(r['time_ms']) > 0
        runs[key].append(r)
        rounds[(r['case_id'], int(r['repeat']))].append(r)
        positions_per_algorithm[r['algorithm']][r['order_in_round']] += 1
    assert set(runs) == keys
    for rows in runs.values():
        assert len(rows) == repeats
        assert {int(r['repeat']) for r in rows} == set(range(1, repeats + 1))
    for rows in rounds.values():
        assert {r['algorithm'] for r in rows} == set(ALGORITHMS)
        assert {r['order_in_round'] for r in rows} == {'1', '2', '3'}
        assert len({r['case_execution_order'] for r in rows}) == 1
    for counts in positions_per_algorithm.values():
        assert set(counts.values()) == {111 * repeats // 3}
    # Check archived row metadata against the preserved reference conditions.
    reference_cases = {}
    for experiment in (1, 2, 3):
        package = load_json(ROOT / 'reference' / f'실험 {experiment}' / 'cases.json')
        for case in package['cases']:
            reference_cases[case['case_id']] = dict(case, experiment=experiment)
    conditions_by_id = {r['case_id']: r for r in conditions}
    assert set(reference_cases) == ids
    for row in conditions:
        case = reference_cases[row['case_id']]
        for field in ('experiment', 'source', 'n', 'm', 'text_file', 'text_sha256',
                      'pattern_id', 'pattern_start_0based', 'repeat_unit', 'condition', 'suite'):
            assert row.get(field, '') == str(case.get(field, '')), (row['case_id'], field)
        if case['experiment'] < 3:
            name = f"pattern_{case['source']}_{case['pattern_id']}_m{case['m']}.txt"
        else:
            name = f"pattern_{case['repeat_unit']}_{case['condition']}.txt"
        assert row['pattern_file'] == name
        assert row['pattern_sha256'] == sha(ROOT / 'inputs' / f"실험 {case['experiment']}" / '패턴' / name)
    for row in summary:
        expected_row = conditions_by_id[row['case_id']]
        assert all(row.get(field) == value for field, value in expected_row.items())
    case_orders = defaultdict(set)
    for row in raw:
        assert row['experiment'] == conditions_by_id[row['case_id']]['experiment']
        case_orders[row['case_id']].add(int(row['case_execution_order']))
    assert all(len(values) == 1 for values in case_orders.values())
    assert {next(iter(values)) for values in case_orders.values()} == set(range(1, 112))
    expected = {}
    for e in (1, 2, 3):
        expected.update(load_json(ROOT / 'reference' / f'실험 {e}' / 'expected_positions.json'))
    for r in summary:
        key = r['case_id'], r['algorithm']
        samples = [float(x['time_ms']) for x in runs[key]]
        assert r['correct'] == 'True' and int(r['repeats']) == repeats
        for field, value in [('mean_ms', statistics.mean(samples)), ('median_ms', statistics.median(samples)),
                             ('min_ms', min(samples)), ('max_ms', max(samples)), ('stdev_ms', statistics.stdev(samples))]:
            assert math.isclose(float(r[field]), value, rel_tol=1e-12, abs_tol=1e-12), (key, field)
        truth = expected[r['case_id']]
        assert int(r['match_count']) == len(truth)
        assert all(int(x['match_count']) == len(truth) for x in runs[key])
        digest = hashlib.sha256(json.dumps(truth, separators=(',', ':')).encode('ascii')).hexdigest()
        assert r['positions_sha256'] == digest
        pre, search, total = (int(r[f]) for f in ('preprocessing_comparisons', 'search_comparisons', 'total_comparisons'))
        assert pre >= 0 and search >= 0 and pre + search == total
        assert int(r['peak_python_bytes']) >= int(r['retained_python_bytes']) >= 0
    for item in load_json(ROOT / 'reference' / 'snapshot_manifest.json')['files']:
        assert sha(ROOT / item['snapshot']) == item['sha256']
    for path, digest in meta.get('package_code_sha256', meta['code_sha256']).items():
        assert sha(ROOT / path.replace('\\', '/')) == digest, path
    integrity = check_originals()
    assert integrity['unchanged']
    result = dict(status='pass', algorithm_cases=333, timed_runs=len(raw),
                  counts_and_memory_rows=len(summary), exact_position_hashes_verified=333,
                  statistics_recomputed=True, balanced_algorithm_order=True,
                  original_integrity=integrity, result_files_sha256={p.name: sha(p) for p in (out / 'conditions.csv', out / 'runs.csv', out / 'summary.csv', out / 'metadata.json')})
    write_json(out / 'verification.json', result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
