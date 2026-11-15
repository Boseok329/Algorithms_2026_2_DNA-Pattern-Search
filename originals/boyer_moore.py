"""Full Boyer-Moore, strong good-suffix + bad-character. No Galil rule."""
from dataclasses import dataclass
from pathlib import Path
@dataclass
class SearchResult:
    positions: list
    preprocessing_comparisons: int
    search_comparisons: int
    alignments: int
    total_shift: int

def _preprocess(p, counted=False):
    m = len(p)
    last = {c: i for i, c in enumerate(p)}
    shift, border = [0]*(m+1), [0]*(m+1)
    i, j, count = m, m+1, 0
    border[i] = j
    while i > 0:
        while j <= m:
            if counted: count += 1
            if p[i-1] == p[j-1]: break
            if shift[j] == 0: shift[j] = j-i
            j = border[j]
        i -= 1
        j -= 1
        border[i] = j
    j = border[0]
    for i in range(m+1):
        if shift[i] == 0: shift[i] = j
        if i == j: j = border[j]
    return last, shift, count

def search_text(text: str, pattern: str) -> list[int]:
    """All overlapping positions (zero-based); preprocessing included."""
    n, m = len(text), len(pattern)
    if m == 0: return list(range(n+1))
    last, shift, _ = _preprocess(pattern)
    result, s = [], 0
    while s <= n-m:
        j = m-1
        while j >= 0 and pattern[j] == text[s+j]: j -= 1
        if j < 0:
            result.append(s)
            s += shift[0]
        else:
            s += max(shift[j+1], j-last.get(text[s+j], -1))
    return result

def search_text_counted(text: str, pattern: str) -> SearchResult:
    """Count evaluated character comparisons, excluding hash/integer operations."""
    n, m = len(text), len(pattern)
    if m == 0: return SearchResult(list(range(n+1)),0,0,0,0)
    last, shift, prep = _preprocess(pattern, True)
    result, s, count, alignments, total_shift = [], 0, 0, 0, 0
    while s <= n-m:
        alignments += 1
        j = m-1
        while j >= 0:
            count += 1
            if pattern[j] != text[s+j]: break
            j -= 1
        if j < 0:
            result.append(s)
            distance = shift[0]
        else:
            distance = max(shift[j+1], j-last.get(text[s+j],-1))
        total_shift += distance
        s += distance
    return SearchResult(result, prep, count, alignments, total_shift)
def _read_text(txt_file: str | Path) -> str:
    # Preserve whitespace and line endings: positions refer to file characters.
    with Path(txt_file).open("r", encoding="utf-8-sig", newline="") as stream:
        return stream.read()


def boyer_moore(pattern: str, txt_file: str | Path) -> list[int]:
    """Search a UTF-8 TXT file. Arguments: (pattern, file path)."""
    return search_text(_read_text(txt_file), pattern)


def boyer_moore_counted(pattern: str, txt_file: str | Path) -> SearchResult:
    """File-based search with preprocessing and search comparison counts."""
    return search_text_counted(_read_text(txt_file), pattern)


search = boyer_moore

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Boyer-Moore TXT search")
    parser.add_argument("pattern", help="String to find")
    parser.add_argument("txt_file", type=Path, help="UTF-8 TXT file path")
    args = parser.parse_args()
    print(boyer_moore(args.pattern, args.txt_file))
