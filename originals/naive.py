#Naive 방식으로 DNA 패턴에서 모든 일치 위치와 문자 비교 횟수를 구하는 코드.


def search(pattern: str, text: str) -> list[int]:
    #겹치는 일치를 포함한 시작 위치를 오름차순으로 반환한다.
    if not pattern:
        raise ValueError("패턴은 한 글자 이상이어야 합니다.")

    positions = []
    m = len(pattern)
    # 패턴 전체가 들어갈 수 있는 시작 위치를 한 칸씩 확인한다.
    for start in range(len(text) - m + 1):
        j = 0
        # 왼쪽부터 비교하고 첫 불일치에서 다음 시작 위치로 이동한다.
        while j < m and text[start + j] == pattern[j]:
            j += 1
        if j == m:
            positions.append(start)
    return positions


def search_counted(pattern: str, text: str) -> tuple[list[int], int]:
    # 같은 검색을 수행하면서 실제 문자 비교 횟수를 함께 반환한다.
    if not pattern:
        raise ValueError("패턴은 한 글자 이상이어야 합니다.")

    positions = []
    comparisons = 0
    m = len(pattern)
    for start in range(len(text) - m + 1):
        j = 0
        while j < m:
            # 일치와 불일치 모두 문자끼리 비교할 때마다 한 번 센다.
            comparisons += 1
            if text[start + j] != pattern[j]:
                break
            j += 1
        if j == m:
            positions.append(start)
    return positions, comparisons
