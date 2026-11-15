"""Run the archived Naive implementation on small, readable examples.

Added for the public documentation on 2026-11-15. This script is a usage
example; it does not reproduce or replace the November 4 benchmark timings.
"""

from pathlib import Path
import sys

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT))

from originals.naive import search, search_counted


def main() -> None:
    examples = [
        ("Overlapping matches", "ACAC", "ACACACGT"),
        ("Repeated full matches", "AAA", "AAAAA"),
        ("Final-character mismatch", "AAC", "AAAAA"),
        ("First-character mismatch", "CAA", "AAAAA"),
    ]
    for label, pattern, text in examples:
        positions, comparisons = search_counted(pattern, text)
        if positions != search(pattern, text):
            raise RuntimeError("Counted and uninstrumented search results differ")
        print(f"{label}: pattern={pattern!r}, text={text!r}")
        print(f"  positions={positions}, character_comparisons={comparisons}")


if __name__ == "__main__":
    main()
