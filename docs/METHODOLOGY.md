# Experimental design and measurement protocol

## Search contract and implementations

Given a text of length `n` and a nonempty pattern of length `m`, each implementation returns every matching start position in ascending, zero-based order, including overlapping matches. The output list contains `k` positions, so its construction contributes to both runtime and memory use.

- **Naive** examines every possible alignment and compares characters from left to right. It has a worst-case comparison cost of `O(nm)`.
- **KMP** reuses matched-prefix information through an LPS table. Preprocessing and search take `O(n + m)` time.
- **Boyer–Moore** compares from right to left and combines bad-character and strong good-suffix shifts. This implementation has no Galil rule. Repeated overlapping full matches can therefore cause it to compare the same characters again.

See the [code guide](CODE_GUIDE.md) for the original interfaces and the functions used by the common runner.

## Input conditions

| Experiment | Variable conditions | Fixed conditions | Count |
|---|---|---|---:|
| 1. Text length | `n`: 100,000; 500,000; 1,000,000; 2,000,000; 4,000,000 | `m = 32`; random and *E. coli* DNA; three patterns per source and length | 30 |
| 2. Pattern length | `m`: 4, 8, 16, 32, 64, 128, 256, 512, 1,000 | `n = 1,000,000`; random and *E. coli* DNA; three patterns per source and length | 54 |
| 3. Repetition structure | Repeated `A`, `AC`, or `ACGT`; first-character mismatch, last-character mismatch, or full match | `n`: 10,000; 20,000; 70,000; `m = 32` | 27 |

The nine `A`-repeat conditions form the core of Experiment 3; the 18 `AC` and `ACGT` conditions supplement them. The full comparison includes all **111 conditions**.

Random DNA generation uses seed `20261103`. The *E. coli* inputs are prefixes of NCBI RefSeq `NC_000913.3`. The frozen definitions, patterns, and expected positions are preserved in [`reference/`](../reference/); provenance and regeneration instructions are in [DATA.md](DATA.md).

## Runtime

Each algorithm-condition combination receives one warm-up followed by five timed calls, for **1,665 timed executions**. Timing uses `time.perf_counter_ns()` and is reported in milliseconds.

The timed call includes pattern preprocessing, search, and construction of the complete result-position list. File I/O, correctness checks, comparison counting, memory tracing, and result-file output are excluded.

Condition order is shuffled with seed `20261104`. Algorithm order rotates by condition and repetition to balance execution positions over the full run. Cyclic garbage collection is collected once before each condition's timing, disabled during timed calls, and then restored.

The original KMP implementation counts comparisons. Its timing and memory variant removes those counter operations while retaining the original LPS and search control flow. The original implementation is called separately to collect comparison counts.

## Character comparisons

The measurements distinguish pattern-to-pattern character comparisons during preprocessing from text-to-pattern comparisons during search. Integer comparisons, array access, and hash operations are not counted as character comparisons.

The figures that compare search work use **search-stage counts**. A reduction in these counts does not imply the same proportional reduction in runtime: control flow, data structures, result construction, and interpreter overhead also contribute.

## Memory

Each algorithm-condition combination is measured once in a separate `tracemalloc(1)` session. The reported peak is the maximum new traced Python allocation during the function call. It includes preprocessing structures and the output list, and excludes input strings loaded before the call.

This metric is not process RSS or total computer memory. Memory measurements are separate from the five timed repetitions.

## Correctness and limitations

Complete overlapping match-position lists are compared with both the stored reference answers and an independent search based on repeated `str.find` calls. Empty patterns are excluded because their behavior differs across the original implementations.

The November 4 experiment used Windows 11, Python 3.14.6, and an Intel Core Ultra 7 265F with 20 logical processors. Background application load and power-management effects were not fully controlled. The results include the mean, median, and sample standard deviation of five timed calls per combination. They do not establish statistical significance or a universal ranking across hardware, programming languages, or possible DNA inputs.

For the saved measurements, see [RESULTS.md](RESULTS.md) and the [run metadata](../results/20261104/metadata.json).
