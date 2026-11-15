# 실험 데이터셋의 파일과 조건 및 정답을 검증하는 코드
import argparse
import hashlib
import json
from pathlib import Path
import re

def load(path):
    return json.loads(path.read_text(encoding='utf-8'))

def verify(root):
    # 생성 당시 기록한 파일 크기와 해시를 실제 파일과 대조한다
    manifest = load(root / 'dataset_manifest.json')
    for path, info in manifest['files'].items():
        data = (root / path).read_bytes()
        assert len(data) == info['bytes'], path
        assert hashlib.sha256(data).hexdigest() == info['sha256'], path
    masters = load(root / 'master_patterns.json')
    texts, all_cases, seen = {}, {}, set()
    total_positions = 0
    for exp in [1, 2, 3]:
        folder = root / f'실험 {exp}'
        cases = load(folder / 'cases.json')['cases']
        answers = load(folder / 'expected_positions.json')
        # 조건 수와 정답 키가 명세에 맞는지 확인한다
        assert len(cases) == manifest['case_counts'][str(exp)]
        assert set(answers) == {c['case_id'] for c in cases}
        for c in cases:
            cid = c['case_id']
            assert cid not in seen
            seen.add(cid)
            path = folder / c['text_file']
            assert path.resolve().parent == folder.resolve(), 'Unexpected external path'
            # 공통 DNA는 한 번 읽고 여러 패턴의 검증에 재사용한다
            if path not in texts:
                data = path.read_bytes()
                assert data and set(data) <= set(b'ACGT'), path
                texts[path] = data.decode('ascii')
            text, pattern = texts[path], c['pattern']
            assert len(text) == c['n'] and len(pattern) == c['m']
            assert set(pattern) <= set('ACGT')
            assert hashlib.sha256(text.encode('ascii')).hexdigest() == c['text_sha256']
            # 정규식으로 겹치는 일치 위치를 검증한다
            positions = [m.start() for m in re.finditer('(?=' + re.escape(pattern) + ')', text)]
            assert positions == answers[cid], cid
            assert len(positions) == c['expected_match_count'], cid
            total_positions += len(positions)
            # 실험 1과 2는 패턴의 시작점과 기준 패턴 관계를 확인한다
            if exp in [1, 2]:
                master = next(p for p in masters[c['source']] if p['pattern_id'] == c['pattern_id'])
                assert pattern == master['pattern'][:c['m']]
                assert c['pattern_start_0based'] == master['start_0based']
                assert text[master['start_0based']:master['start_0based']+1000] == master['pattern']
                assert c['pattern_start_0based'] in positions
            else:
                # 실험 3은 반복 구조와 주기식으로 계산한 정답을 확인한다
                motif = c['repeat_unit']
                assert text == (motif * ((len(text)+len(motif)-1)//len(motif)))[:len(text)]
                formula = list(range(0, c['n']-c['m']+1, len(motif))) if c['condition']=='many_matches' else []
                assert positions == formula
            all_cases[cid] = (c, text, pattern)

    # 같은 원천의 앞부분과 고정 패턴 사용을 검증한다
    for src in ['random', 'ecoli']:
        longest = texts[root / '실험 1' / f'text_{src}_n4000000.txt']
        for n in manifest['parameters']['experiment1_n']:
            assert texts[root/'실험 1'/f'text_{src}_n{n}.txt'] == longest[:n]
        assert texts[root/'실험 2'/f'text_{src}_n1000000.txt'] == longest[:1000000]
        for master in masters[src]:
            pid = master['pattern_id']
            fixed = [v[2] for k,v in all_cases.items() if k.startswith(f'E1_{src}_') and k.endswith(pid)]
            assert len(fixed)==5 and len(set(fixed))==1
            assert all_cases[f'E2_{src}_n1000000_{pid}_m32'][2] == fixed[0]
    # 전체 조건 수와 검증한 정답 위치 수를 보고서로 반환한다
    assert len(all_cases) == 111
    return {'status': 'passed', 'case_count': len(all_cases), 'verified_input_files': len(texts),
            'verified_answer_positions': total_positions, 'hash_checked_files': len(manifest['files']),
            'checks': ['file hashes and lengths', 'ACGT-only inputs', 'pattern lengths and provenance',
                       'fixed-pattern controls', 'same-source prefix controls',
                       'all overlapping positions via independent regex', 'periodic analytical formulas'],
            'algorithms_benchmarked': False}

if __name__ == '__main__':
    import sys
    if hasattr(sys.stdout,'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    # 실행 인자로 검증할 데이터셋 폴더를 받는다
    parser=argparse.ArgumentParser(description="실험 데이터셋의 파일과 조건 및 정답을 검증하는 코드")
    parser.add_argument('--root', type=Path, default=Path(__file__).parent)
    args=parser.parse_args()
    # 검증 결과를 JSON으로 저장하고 화면에 출력한다
    report=verify(args.root.resolve())
    (args.root/'검증_결과.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(report,ensure_ascii=False))
