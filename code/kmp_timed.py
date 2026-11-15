"""팀원 KMP 원본에서 비교 횟수 계측만 분리한 시간 측정용 구현.

원본: 00 kmp 실험/kmp.py
원본 SHA-256: 94c97a4c245f27c8cd1e16e9db1494c52f6325680e9f1bb778f6dce48401f37a

LPS의 comparisons 초기화·증가·반환과 검색의 pre_cmp/search_cmp
저장·초기화·증가·반환만 제거했다. 문자 비교, LPS 후퇴, 일치 후 이동,
결과 목록 생성과 원래 조기 종료 조건은 그대로이며 최적화하지 않았다.
파일 읽기와 테스트 진입점은 측정 대상에서 제외했다.

통합 실험 입력 계약: pattern은 한 글자 이상인 DNA 문자열이다.
빈 패턴 거부는 공통 실행기의 입력 검증에서 처리한다. 아래의 빈 패턴
조기 종료는 원본과 동일하게 보존했으며 실험 조건에 포함하지 않는다.
"""


def build_lps(pattern):
    """원본과 같은 LPS 배열을 만들고 문자 비교 횟수는 세지 않는다."""
    m = len(pattern)
    lps = [0] * m
    length = 0
    i = 1
    while i < m:
        if pattern[i] == pattern[length]:
            length += 1
            lps[i] = length
            i += 1
        elif length > 0:
            length = lps[length - 1]
        else:
            i += 1
    return lps


def kmp_search(pattern, text):
    """전처리를 포함해 검색하고 겹치는 일치의 모든 시작 위치를 반환한다."""
    n, m = len(text), len(pattern)
    if m == 0 or n < m:
        return []

    lps = build_lps(pattern)
    result = []
    i = j = 0
    while i < n:
        if text[i] == pattern[j]:
            i += 1
            j += 1
            if j == m:
                result.append(i - m)
                j = lps[j - 1]
        elif j > 0:
            j = lps[j - 1]
        else:
            i += 1
    return result
