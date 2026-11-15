# 실험 데이터와 패턴 및 정답의 공통 처리를 위한 코드
from pathlib import Path
import hashlib
import json
import random

# 모든 실험에서 사용할 난수 시드와 DNA 및 패턴 길이를 고정한다
SEED = 20261103
ECOLI_SHA256 = 'e999dceccb76562d40e49a10d9e6d4cf1c05d184f4f80b92bb32d4a2420c11d0'
STARTS = [1000, 20000, 70000]
TEXT_LENGTHS = [100000, 500000, 1000000, 2000000, 4000000]
PATTERN_LENGTHS = [4, 8, 16, 32, 64, 128, 256, 512, 1000]
REPEAT_LENGTHS = [10000, 20000, 70000]

def sha(data):
    return hashlib.sha256(data).hexdigest()

def load_sources(ecoli_file):
    # 대장균 서열과 고정 시드의 무작위 DNA에서 기준 패턴을 생성한다
    # 원본 해시와 염기 구성을 확인해 동일한 대장균 서열을 사용한다
    raw = Path(ecoli_file).read_bytes()
    if sha(raw) != ECOLI_SHA256:
        raise ValueError('NC_000913.3 원천 파일의 SHA-256이 기준값과 다릅니다.')
    ecoli = raw.decode('ascii')
    assert len(ecoli) == 4641652 and set(ecoli) == set('ACGT')
    # 고정 시드로 최장 무작위 DNA를 만들고 각 실험에서 앞부분을 추출한다
    generated = ''.join(random.Random(SEED).choices('ACGT', k=4000000))
    sources = {'random': generated, 'ecoli': ecoli}
    # 세 시작점에서 1000자 기준 패턴을 뽑아 필요한 길이만큼 사용한다
    masters = {
        src: [{'pattern_id': f'p{i+1:02d}', 'start_0based': s, 'length': 1000,
               'pattern': text[s:s+1000]} for i, s in enumerate(STARTS)]
        for src, text in sources.items()
    }
    return sources, masters

def all_positions(text, pattern):
    # 겹치는 일치를 포함한 모든 정답 위치를 구한다
    result = []
    pos = text.find(pattern)
    while pos != -1:
        result.append(pos)
        # 다음 검색을 한 칸 뒤에서 시작해 겹치는 일치도 포함한다
        pos = text.find(pattern, pos + 1)
    return result

def write_json(path, value):
    Path(path).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')

class CaseWriter:
    def __init__(self, output, experiment):
        # 새 결과는 비어 있는 출력 폴더에 저장한다
        self.folder = Path(output)
        if self.folder.exists() and any(self.folder.iterdir()):
            raise ValueError('출력 폴더가 비어 있지 않습니다. 새 폴더를 지정하세요.')
        self.folder.mkdir(parents=True,exist_ok=True)
        self.experiment = experiment
        self.cases, self.answers = [], {}

    def text(self, filename, text):
        assert text and set(text) <= set('ACGT')
        # TXT에는 DNA 문자만 ASCII로 저장한다
        (self.folder / filename).write_bytes(text.encode('ascii'))

    def add(self, case, text):
        pattern = case['pattern']
        assert case['n']==len(text) and case['m']==len(pattern)
        assert 0 < len(pattern) <= len(text) and set(pattern) <= set('ACGT')
        # 조건별 정답 위치와 입력 해시를 함께 기록한다
        positions = all_positions(text,pattern)
        case['expected_match_count'] = len(positions)
        case['text_sha256'] = sha(text.encode('ascii'))
        self.cases.append(case)
        self.answers[case['case_id']] = positions

    def finish(self):
        # 조건 명세와 정답 목록을 분리해 실험 실행과 검증에 사용한다
        write_json(self.folder/'cases.json',{'schema_version':1,'experiment':self.experiment,
                   'index_base':0,'include_overlaps':True,'cases':self.cases})
        write_json(self.folder/'expected_positions.json',self.answers)
        # 실험별 설명은 공통 설명 파일에서 읽는다
        descriptions = json.loads(Path(__file__).with_name('experiment_descriptions.json').read_text(encoding='utf-8'))
        (self.folder/'00_설명.md').write_text(descriptions[str(self.experiment)],encoding='utf-8',newline='\n')
        print(f'Experiment {self.experiment}: {len(self.cases)} cases saved to {self.folder}')
