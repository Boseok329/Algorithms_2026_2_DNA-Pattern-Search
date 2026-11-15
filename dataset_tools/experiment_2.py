# 실험 2의 패턴 길이별 입력을 생성하는 코드
import argparse
from pathlib import Path
from dataset_common import load_sources, CaseWriter, SEED, PATTERN_LENGTHS

def generate(ecoli_file, output):
    # 실험 1과 같은 원천 DNA와 기준 패턴을 불러온다
    sources, masters = load_sources(ecoli_file)
    writer = CaseWriter(output,2)
    for src, source in sources.items():
        # 검색할 DNA는 원천별 앞 100만 자로 고정한다
        text = source[:1000000]
        filename = f'text_{src}_n1000000.txt'
        writer.text(filename,text)
        for master in masters[src]:
            # 같은 시작점의 패턴을 앞 m자씩 추출해 길이만 바꾼다
            for m in PATTERN_LENGTHS:
                writer.add({
                    'case_id':f'E2_{src}_n1000000_{master["pattern_id"]}_m{m}',
                    'suite':'primary_random' if src=='random' else 'supplement_ecoli',
                    'source':src,'text_file':filename,'n':1000000,
                    'pattern_id':master['pattern_id'],'pattern_start_0based':master['start_0based'],
                    'pattern':master['pattern'][:m],'m':m,
                    'seed':SEED if src=='random' else None,
                },text)
    # 원천 2개와 패턴 3개 및 길이 9개를 조합한 54조건을 저장한다
    writer.finish()

if __name__=='__main__':
    import sys
    if hasattr(sys.stdout,'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
    # 실행 인자로 원본 서열과 출력 폴더를 받는다
    parser=argparse.ArgumentParser(description="실험 2의 패턴 길이별 입력을 생성하는 코드")
    parser.add_argument('--ecoli',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    generate(args.ecoli,args.out)
