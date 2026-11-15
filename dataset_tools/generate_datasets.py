# 실험 1과 2와 3의 데이터셋과 정답을 한 번에 생성하는 코드
import argparse
import hashlib
import json
from pathlib import Path
import platform
import random
import shutil

# 실험별 생성 코드와 같은 시드 및 길이 조건을 사용한다
SEED = 20261103
ECOLI_SHA256 = 'e999dceccb76562d40e49a10d9e6d4cf1c05d184f4f80b92bb32d4a2420c11d0'
STARTS = [1000, 20000, 70000]
TEXT_LENGTHS = [100000, 500000, 1000000, 2000000, 4000000]
PATTERN_LENGTHS = [4, 8, 16, 32, 64, 128, 256, 512, 1000]
REPEAT_LENGTHS = [10000, 20000, 70000]

def sha(data):
    return hashlib.sha256(data).hexdigest()

def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')

def all_positions(text, pattern):
    # 겹치는 일치를 포함한 모든 정답 위치를 구한다
    result = []
    pos = text.find(pattern)
    while pos != -1:
        result.append(pos)
        # 다음 검색을 한 칸 뒤에서 시작해 겹치는 일치를 포함한다
        pos = text.find(pattern, pos + 1)
    return result

def build(source_path, out):
    # 대장균 원본의 해시와 길이 및 염기 구성을 확인한다
    raw = source_path.read_bytes()
    if sha(raw) != ECOLI_SHA256:
        raise ValueError('The NC_000913.3 source hash differs from the verified reference.')
    ecoli = raw.decode('ascii')
    assert len(ecoli) == 4641652 and set(ecoli) == set('ACGT')
    # 비어 있는 출력 폴더에 실험별 하위 폴더를 만든다
    if out.exists() and any(out.iterdir()):
        raise ValueError('Output folder must be empty. Choose a new directory.')
    out.mkdir(parents=True, exist_ok=True)
    folders = {i: out / f'실험 {i}' for i in [1, 2, 3]}
    for p in folders.values():
        p.mkdir()
    # 최장 무작위 DNA를 한 번 만들고 세 시작점의 기준 패턴을 추출한다
    random_dna = ''.join(random.Random(SEED).choices('ACGT', k=4000000))
    sources = {'random': random_dna, 'ecoli': ecoli}
    masters = {
        src: [{'pattern_id': f'p{i+1:02d}', 'start_0based': s, 'length': 1000,
               'pattern': text[s:s+1000]} for i, s in enumerate(STARTS)]
        for src, text in sources.items()
    }
    write_json(out / 'master_patterns.json', masters)
    packs = {i: {'schema_version': 1, 'experiment': i, 'index_base': 0,
                 'include_overlaps': True, 'cases': []} for i in folders}
    answers = {i: {} for i in folders}

    def add_case(exp, case, text):
        p = case['pattern']
        assert case['n'] == len(text) and case['m'] == len(p)
        assert 0 < len(p) <= len(text) and set(p) <= set('ACGT')
        # 각 조건의 전체 정답 위치와 입력 해시를 기록한다
        positions = all_positions(text, p)
        case['expected_match_count'] = len(positions)
        case['text_sha256'] = sha(text.encode('ascii'))
        packs[exp]['cases'].append(case)
        answers[exp][case['case_id']] = positions

    # 실험 1은 DNA 길이를 바꾸고 동일한 32자 패턴 세 개를 적용한다
    for src, source in sources.items():
        for n in TEXT_LENGTHS:
            text = source[:n]
            filename = f'text_{src}_n{n}.txt'
            (folders[1] / filename).write_bytes(text.encode('ascii'))
            for master in masters[src]:
                add_case(1, {
                    'case_id': f'E1_{src}_n{n}_{master["pattern_id"]}',
                    'suite': 'primary_random' if src == 'random' else 'supplement_ecoli',
                    'source': src, 'text_file': filename, 'n': n,
                    'pattern_id': master['pattern_id'], 'pattern_start_0based': master['start_0based'],
                    'pattern': master['pattern'][:32], 'm': 32,
                    'seed': SEED if src == 'random' else None,
                }, text)
        # 실험 2는 DNA를 100만 자로 고정하고 패턴 길이를 바꾼다
        text = source[:1000000]
        filename = f'text_{src}_n1000000.txt'
        (folders[2] / filename).write_bytes(text.encode('ascii'))
        for master in masters[src]:
            for m in PATTERN_LENGTHS:
                add_case(2, {
                    'case_id': f'E2_{src}_n1000000_{master["pattern_id"]}_m{m}',
                    'suite': 'primary_random' if src == 'random' else 'supplement_ecoli',
                    'source': src, 'text_file': filename, 'n': 1000000,
                    'pattern_id': master['pattern_id'], 'pattern_start_0based': master['start_0based'],
                    'pattern': master['pattern'][:m], 'm': m,
                    'seed': SEED if src == 'random' else None,
                }, text)

    # 실험 3은 세 반복 유형에 불일치 두 종류와 완전 일치를 적용한다
    for motif in ['A', 'AC', 'ACGT']:
        matched = (motif * 32)[:32]
        # 첫 글자와 마지막 글자를 바꿔 불일치 패턴을 만든다
        wrong_first = 'C' if motif in ['A', 'ACGT'] else 'G'
        wrong_last = {'A': 'C', 'AC': 'G', 'ACGT': 'A'}[motif]
        patterns = {'end_mismatch': matched[:-1] + wrong_last,
                    'start_mismatch': wrong_first + matched[1:],
                    'many_matches': matched}
        for n in REPEAT_LENGTHS:
            text = (motif * ((n + len(motif) - 1) // len(motif)))[:n]
            filename = f'text_repeat_{motif}_n{n}.txt'
            (folders[3] / filename).write_bytes(text.encode('ascii'))
            for name, pattern in patterns.items():
                case = {
                    'case_id': f'E3_{motif}_n{n}_{name}',
                    'suite': 'core_A' if motif == 'A' else 'supplement_periodic',
                    'source': 'synthetic_repeat', 'repeat_unit': motif,
                    'condition': name, 'text_file': filename, 'n': n,
                    'pattern': pattern, 'm': 32, 'seed': None,
                }
                add_case(3, case, text)
                # 반복 단위 간격으로 계산한 위치와 검색 정답을 대조한다
                expected = list(range(0, n - 32 + 1, len(motif))) if name == 'many_matches' else []
                assert answers[3][case['case_id']] == expected

    # 실험별 조건 명세와 정답 위치를 별도 JSON으로 저장한다
    for i in folders:
        write_json(folders[i] / 'cases.json', packs[i])
        write_json(folders[i] / 'expected_positions.json', answers[i])

    # 원패키지에 함께 저장할 공통 안내와 실험별 설명을 구성한다
    common = '''
## 사용 방법

1. `cases.json`의 `cases` 목록에서 조건을 하나씩 읽는다.
2. `text_file`을 **이 실험 폴더 기준**으로 열어 T로 사용한다. TXT는 설명·줄바꿈 없이 DNA 문자만 담았다.
3. 같은 항목의 `pattern` 문자열을 P로 그대로 사용한다. 팀원별로 패턴을 다시 추출하거나 생성하지 않는다.
4. Naive·KMP·Boyer–Moore 모두 같은 T·P를 입력받고, 겹치는 일치를 포함한 모든 시작 위치를 0부터 시작하는 인덱스로 반환한다.
5. `expected_positions.json`의 같은 `case_id`에 있는 정답 목록과 비교한다. 파일 읽기·정답 대조·결과 저장은 시간 측정에서 제외한다.

`expected_match_count`는 정답 개수이며 속도 측정 결과가 아니다. 패턴 전처리 비용의 포함 범위와 반복 횟수는 공통 벤치마크에서 통일한다. 최종 속도 비교는 같은 PC·환경에서 한다.
'''
    docs = {
      1: '''# 실험 1 텍스트 길이 변화

DNA 길이가 늘어날 때 세 알고리즘의 비용이 어떻게 바뀌는지 비교한다.

- 변경: T 길이 100,000 / 500,000 / 1,000,000 / 2,000,000 / 4,000,000자.
- 고정: 패턴 길이 32자. 같은 원천 서열에서는 동일한 세 패턴을 모든 T 길이에 사용한다.
- 패턴: 원천 서열의 시작 인덱스 1000·20000·70000에서 뽑은 1000자 기준 패턴의 앞 32자.
- 무작위 DNA 15조건 + 대장균 15조건 = 총 30조건. 원천별로 별도 비교한다.
- 모든 패턴은 최소 길이인 10만 자 안에도 존재한다. 길이마다 패턴을 바꾸지 않는다.

`source=random`은 제안서의 주 실험, `source=ecoli`는 실제 유전체 보조 실험이다. 길이만으로 Naive와 KMP의 시간 차이가 항상 커진다고 가정하지 않는다.
''',
      2: '''# 실험 2 패턴 길이 변화

DNA를 고정하고 찾을 패턴 길이를 바꿔 전처리·검색 비용과 일치 개수의 변화를 비교한다.

- 고정: 각 원천 DNA의 앞 1,000,000자.
- 변경: P 길이 4 / 8 / 16 / 32 / 64 / 128 / 256 / 512 / 1000자.
- 시작 인덱스 1000·20000·70000의 1000자 기준 패턴을 준비하고, 각 기준 패턴의 앞 m자를 사용한다.
- 무작위 DNA 27조건 + 대장균 27조건 = 총 54조건.
- 같은 원천·시작점의 32자 패턴은 실험 1과 동일하다. 모든 패턴은 T 안에서 추출했다.

짧은 패턴은 일치 위치가 많아 결과 목록 저장 비용이 커질 수 있다. 시간·비교 횟수와 함께 실제 일치 개수도 기록한다. 무작위 DNA와 대장균 결과를 구분한다.
''',
      3: '''# 실험 3 반복 구조와 패턴 조건

의도적으로 반복 문자열을 만들어, 불일치 위치와 겹치는 일치가 세 알고리즘에 주는 영향을 비교한다. 실제 유전체의 성능을 대표하는 데이터로 해석하지 않는다.

## 기본 A 반복 세트

T는 A 10,000 / 20,000 / 70,000개이며, 각 길이에서 아래 세 패턴을 모두 검색한다. P 길이는 항상 32자다.

| condition | 패턴 | 정답 |
|---|---|---|
| end_mismatch | A 31개 + C | 일치 없음 |
| start_mismatch | C + A 31개 | 일치 없음 |
| many_matches | A 32개 | n − 31개 일치 |

3개 길이 × 3개 패턴 = **9조건**이다. `suite=core_A`로 선택한다. A 32개의 정답은 n=10,000일 때 9,969개, 20,000일 때 19,969개, 70,000일 때 69,969개다.

## 보조 주기 반복 세트

`ACAC…`와 `ACGTACGT…`도 같은 세 길이에서 비교한다. 각 반복에 정확히 맞는 32자 패턴과, 그 패턴의 첫 글자 또는 마지막 글자를 바꾼 패턴을 제공한다. 구체적인 P는 `cases.json`에 저장했다.

- AC의 변경 문자는 G, ACGT의 첫 글자는 C·마지막 글자는 A로 바꿔 반복 순서를 깨뜨린다.
- 두 불일치 조건의 정답은 빈 목록이다.
- 완전 반복 패턴은 각각 2칸·4칸 간격으로 일치한다. 겹치는 일치를 모두 반환해야 한다.
- 2개 반복 유형 × 3개 길이 × 3개 패턴 = **18조건**, `suite=supplement_periodic`이다.

기본 9조건과 보조 18조건을 합하면 총 27조건이다. 결과표에서 반복 유형·불일치 조건을 구분하고, 서로 다른 조건을 한 평균으로 섞지 않는다. 세 알고리즘이 기본 9조건을 각각 실행하면 반복 측정 전 27개 측정 조합이다.
'''
    }
    for i, content in docs.items():
        (folders[i] / '00_설명.md').write_text(content + common, encoding='utf-8', newline='\n')

    root_readme = '''# DNA 패턴 검색 공통 실험 데이터셋

Naive·KMP·Boyer–Moore가 동일한 DNA와 패턴을 검색하기 위한 공유 입력이다. 데이터 생성과 정답 검증용이며, 알고리즘 구현이나 성능 측정 결과는 포함하지 않는다.

| 폴더 | 바꾸는 조건 | 조건 수 |
|---|---|---:|
| 실험 1 | DNA 길이, 패턴 32자 고정 | 무작위 15 + 대장균 15 = 30 |
| 실험 2 | 패턴 길이, DNA 100만 자 고정 | 무작위 27 + 대장균 27 = 54 |
| 실험 3 | 반복 구조와 불일치·일치 조건 | A 기본 9 + AC·ACGT 보조 18 = 27 |

총 111조건이다. 세 알고리즘이 모두 실행하면 반복 측정 전 333개 조합이다. 처음에는 대장균 예제 한 조건과 실험 3의 A 기본 세트로 입출력을 확인한 뒤 전체로 확대한다. 이 패키지의 최대 DNA 길이는 400만 자이며 제안서의 1000만 자 확장은 포함하지 않았다.

## 팀원이 읽을 파일

각 실험 폴더는 독립적으로 전달해도 사용할 수 있다.

- `00_설명.md`: 실험 목적, 변경·고정 조건, 실행 규칙.
- `text_*.txt`: 검색할 DNA T. ASCII A/C/G/T만 포함하며 공백·설명·끝 줄바꿈이 없다.
- `cases.json`: `cases` 목록에 입력 ID, DNA 파일명, 실제 패턴 문자열, n·m, 원천·생성 조건, 정답 개수를 저장했다.
- `expected_positions.json`: `case_id`별 모든 정답 시작 위치. 0부터 시작하며 겹치는 일치를 포함한다.

각자 패턴을 새로 정하지 않고 **cases.json에 저장된 pattern을 그대로 사용**한다. n은 문자열 길이이고 pattern_start_0based는 패턴 추출 시작 위치다. 두 값을 혼동하지 않는다. 같은 실험 번호 안에도 여러 입력 조건이 있다.

## Python으로 한 조건 읽기

아래 예제의 base는 현재 코드에서 접근할 실험 폴더 경로로 맞춘다. 코드는 입력과 정답을 읽는 예시이며 검색 알고리즘이 아니다.

```python
import json
from pathlib import Path

base = Path('실험 1')
cases = json.loads((base / 'cases.json').read_text(encoding='utf-8'))['cases']
case = cases[0]
T = (base / case['text_file']).read_text(encoding='ascii')
P = case['pattern']
expected = json.loads((base / 'expected_positions.json').read_text(encoding='utf-8'))[case['case_id']]
# actual = 담당_알고리즘(T, P)
# assert actual == expected
```

다른 언어에서도 같은 JSON과 TXT를 읽으면 된다. 같은 T·P에 대한 전체 위치 목록이 정답과 일치하는지 확인한 뒤, 같은 PC에서 최종 실행 시간·비교 횟수를 측정한다. KMP·Boyer–Moore의 패턴 전처리 비용은 공통 기준으로 처리한다. 데이터 읽기·정답 검사 시간은 검색 시간에서 제외한다.

## 출처와 생성 규칙

- 주 실험: Python `random.Random(20261103).choices('ACGT', k=4000000)`로 생성한 균등 무작위 DNA. 패키지의 파일 자체를 공통 입력으로 사용한다.
- 실제 DNA: [NCBI NC_000913.3](https://www.ncbi.nlm.nih.gov/nuccore/NC_000913.3), E. coli K-12 substr. MG1655. 전체 4,641,652자 중 앞부분을 사용한다. 원본은 프로젝트의 01_원자료에 보존되어 있다.
- 패턴: 각 원천 서열의 0-based 시작점 1000·20000·70000에서 1000자씩 뽑았다. `master_patterns.json`에 기준 패턴을 보존했다.
- 실험 1·2의 무작위 DNA와 실제 DNA는 별도 결과로 분석한다. 실험 3은 통제된 합성 반복 입력이다.
- 모든 입력은 저장된 방향의 선형 정확 검색용이다. 원형 유전체의 끝과 처음 연결, 역상보 검색, 오차·갭 허용은 포함하지 않는다.

`dataset_manifest.json`에는 원천 해시·생성 설정·파일별 SHA-256이 있다. `generate_datasets.py`는 같은 자료를 재생성하며 비어 있지 않은 출력 폴더를 덮어쓰지 않는다. `verify_datasets.py`는 정답·길이·해시·패턴 조건을 검사한다. 정답 생성에 사용한 내장 검색은 벤치마크 대상 구현이 아니다.

재생성 예: `python generate_datasets.py --ecoli NC_000913.3_sequence.txt --out 새_출력폴더`

검증 예: 데이터셋 루트에서 `python verify_datasets.py --root .`
'''
    (out / '00_공유안내.md').write_text(root_readme, encoding='utf-8', newline='\n')
    # 재생성에 사용한 생성 및 검증 코드도 원패키지에 보관한다
    shutil.copyfile(__file__, out / 'generate_datasets.py')
    validator = Path(__file__).with_name('verify_datasets.py')
    if not validator.exists():
        raise FileNotFoundError('Keep verify_datasets.py alongside the generator.')
    shutil.copyfile(validator, out / 'verify_datasets.py')
    # 파일별 크기와 해시를 기록해 이후 검증의 기준으로 사용한다
    ledger = {p.relative_to(out).as_posix(): {'bytes': p.stat().st_size, 'sha256': sha(p.read_bytes())}
              for p in sorted(out.rglob('*')) if p.is_file()}
    # 출처와 생성 환경 및 실험 조건을 패키지 명세에 기록한다
    manifest = {
        'schema_version': 1, 'package_version': '2026-11-03-v1', 'created_date_kst': '2026-11-03',
        'algorithms_for_comparison': ['Naive', 'KMP', 'Boyer-Moore (bad-character + good-suffix)'],
        'status': 'inputs_and_answer_keys_only; no algorithm benchmark performed',
        'index_base': 0, 'include_overlaps': True,
        'sources': {
            'ecoli': {'accession': 'NC_000913.3', 'length': len(ecoli), 'sha256': sha(raw),
                      'url': 'https://www.ncbi.nlm.nih.gov/nuccore/NC_000913.3'},
            'random': {'length': len(random_dna), 'sha256': sha(random_dna.encode('ascii')),
                       'seed': SEED, 'generator': "random.Random(seed).choices('ACGT', k=4000000)",
                       'python_version': platform.python_version(), 'distribution': 'uniform A/C/G/T'},
        },
        'parameters': {'experiment1_n': TEXT_LENGTHS, 'experiment1_m': 32,
                       'experiment2_n': 1000000, 'experiment2_m': PATTERN_LENGTHS,
                       'pattern_starts_0based': STARTS, 'master_pattern_length': 1000,
                       'experiment3_n': REPEAT_LENGTHS, 'experiment3_m': 32,
                       'experiment3_core_motif': 'A', 'experiment3_supplement_motifs': ['AC', 'ACGT']},
        'case_counts': {str(i): len(packs[i]['cases']) for i in folders},
        'answer_method': 'Python str.find advancing by 1; validated independently using regex lookahead and periodic formulas',
        'files': ledger,
    }
    write_json(out / 'dataset_manifest.json', manifest)
    print(json.dumps({'out': str(out), 'cases': manifest['case_counts'],
                      'files': len(ledger)+1, 'bytes': sum(x['bytes'] for x in ledger.values())}, ensure_ascii=False))

if __name__ == '__main__':
    import sys
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    # 실행 인자로 원본 서열과 출력 폴더를 받는다
    parser = argparse.ArgumentParser(description="실험 1과 2와 3의 데이터셋과 정답을 한 번에 생성하는 코드")
    parser.add_argument('--ecoli', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    build(args.ecoli.resolve(), args.out.resolve())
