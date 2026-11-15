# 실험 3의 반복 DNA와 비교 패턴을 생성하는 코드
import argparse
from pathlib import Path
from dataset_common import CaseWriter, REPEAT_LENGTHS

def generate(output):
    writer=CaseWriter(output,3)
    # A는 기본 반복 실험이고 AC와 ACGT는 보조 반복 실험이다
    for motif in ['A','AC','ACGT']:
        # 반복 유형마다 정확히 맞는 32자 패턴을 만든다
        matched=(motif*32)[:32]
        # 첫 글자와 마지막 글자를 각각 바꿔 두 불일치 조건을 만든다
        wrong_first='C' if motif in ['A','ACGT'] else 'G'
        wrong_last={'A':'C','AC':'G','ACGT':'A'}[motif]
        patterns={'end_mismatch':matched[:-1]+wrong_last,
                  'start_mismatch':wrong_first+matched[1:],
                  'many_matches':matched}
        for n in REPEAT_LENGTHS:
            # 반복 문자열을 충분히 이어 붙인 뒤 n자 길이로 자른다
            text=(motif*((n+len(motif)-1)//len(motif)))[:n]
            filename=f'text_repeat_{motif}_n{n}.txt'
            writer.text(filename,text)
            for name,pattern in patterns.items():
                case={
                    'case_id':f'E3_{motif}_n{n}_{name}',
                    'suite':'core_A' if motif=='A' else 'supplement_periodic',
                    'source':'synthetic_repeat','repeat_unit':motif,
                    'condition':name,'text_file':filename,'n':n,
                    'pattern':pattern,'m':32,'seed':None,
                }
                writer.add(case,text)
                # 완전 일치 위치는 반복 단위 길이만큼 간격을 두고 나타난다
                expected=list(range(0,n-32+1,len(motif))) if name=='many_matches' else []
                assert writer.answers[case['case_id']]==expected
    # 기본 9조건과 보조 18조건을 저장한다
    writer.finish()

if __name__=='__main__':
    import sys
    if hasattr(sys.stdout,'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
    # 실행 인자로 출력 폴더를 받는다
    parser=argparse.ArgumentParser(description="실험 3의 반복 DNA와 비교 패턴을 생성하는 코드")
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    generate(args.out)
