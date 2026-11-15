# 실험 1의 DNA 길이별 입력과 고정 패턴을 생성하는 코드
import argparse
from pathlib import Path
from dataset_common import load_sources, CaseWriter, SEED, TEXT_LENGTHS

def generate(ecoli_file, output):
    # 대장균과 무작위 DNA에 같은 길이 조건을 적용한다
    sources, masters = load_sources(ecoli_file)
    writer = CaseWriter(output,1)
    for src, source in sources.items():
        for n in TEXT_LENGTHS:
            # 같은 원천의 앞부분을 잘라 DNA 길이를 바꾼다
            text = source[:n]
            filename = f'text_{src}_n{n}.txt'
            writer.text(filename,text)
            # 세 기준 패턴의 앞 32자를 모든 DNA 길이에서 공통으로 사용한다
            for master in masters[src]:
                writer.add({
                    'case_id':f'E1_{src}_n{n}_{master["pattern_id"]}',
                    'suite':'primary_random' if src=='random' else 'supplement_ecoli',
                    'source':src,'text_file':filename,'n':n,
                    'pattern_id':master['pattern_id'],'pattern_start_0based':master['start_0based'],
                    'pattern':master['pattern'][:32],'m':32,
                    'seed':SEED if src=='random' else None,
                },text)
    # DNA 파일과 30조건의 명세 및 정답을 저장한다
    writer.finish()

if __name__=='__main__':
    import sys
    if hasattr(sys.stdout,'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
    # 실행 인자로 원본 서열과 출력 폴더를 받는다
    parser=argparse.ArgumentParser(description="실험 1의 DNA 길이별 입력과 고정 패턴을 생성하는 코드")
    parser.add_argument('--ecoli',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    generate(args.ecoli,args.out)
