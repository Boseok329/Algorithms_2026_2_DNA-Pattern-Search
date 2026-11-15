# Code guide and recorded use

The repository separates the implementations used in the experiment from the scripts that prepare inputs, measure performance, and present the results. All paths below are relative to the repository root unless linked otherwise.

## Where to start

| Task | Entry point | What it does |
|---|---|---|
| Read the Naive implementation | [`originals/naive.py`](../originals/naive.py) | Searches every possible alignment and provides a separate comparison-counting function. |
| Run the Naive example | [`examples/naive_demo.py`](../examples/naive_demo.py) | Demonstrates overlapping matches and mismatch positions using the archived implementation. Added for the November 15 documentation. |
| Read the KMP implementation | [`originals/kmp.py`](../originals/kmp.py) | Builds the LPS table, searches for all matches, and counts preprocessing and search comparisons. |
| Read the Boyer–Moore implementation | [`originals/boyer_moore.py`](../originals/boyer_moore.py) | Combines bad-character and strong good-suffix shifts. It does not implement the Galil rule. |
| Validate or measure all algorithms | [`code/run_benchmark.py`](../code/run_benchmark.py) | Loads the frozen inputs, checks complete match-position lists, and runs the common measurement protocol. |
| Inspect the KMP timing variant | [`code/kmp_timed.py`](../code/kmp_timed.py) | Preserves the original KMP control flow while removing comparison-counter operations from timed calls. |
| Check saved measurements | [`code/verify_results.py`](../code/verify_results.py) | Recomputes timing statistics and checks result, input, and code consistency. |
| Generate the original report format | [`code/render_results.py`](../code/render_results.py) | Reads an existing result folder and produces the original Korean charts and a local HTML report within that folder. It does not run a benchmark. |
| Generate the English publication figures | [`code/plot_figures.py`](../code/plot_figures.py) | Reads the archived summary CSV and renders the Naive-only and team-comparison figures. Added for the November 15 documentation. |
| Recreate the experimental inputs | [`dataset_tools/generate_datasets.py`](../dataset_tools/generate_datasets.py) | Generates the three experiments from the normalized genome and deterministic synthetic data. |

Run the command-line tools from the repository root. Python 3.10 or later is required by the source syntax. Search, measurement, and validation use the standard library; figure generation additionally requires matplotlib.

```sh
# Check all 111 conditions without collecting new timings.
python -B -X utf8 code/run_benchmark.py --validate-only

# Check the saved November 4 measurements.
python -B -X utf8 code/verify_results.py results/20261104

# Collect a new benchmark in a new timestamped result folder.
python -B -X utf8 code/run_benchmark.py --repeats 5

# Install the optional dependency before generating either set of figures.
python -m pip install -r requirements.txt

# Rebuild figures and HTML from saved measurements.
python -B -X utf8 code/render_results.py results/20261104

# Rebuild the English figures used in the personal and team reports.
python -B code/plot_figures.py
```

The verifier writes `verification.json` in the result folder. The original renderer updates that folder's figures and HTML. The English publication plotter instead writes to `figures/naive/` and `figures/team/` and verifies the archived November 4 CSV hash before plotting. It is intended for the recorded experiment, not arbitrary new result files. A benchmark creates a new output directory and does not overwrite the archived November 4 measurements. Use a copy of the result folder if you want to retain its current verification and rendered artifacts unchanged.

## Original algorithm interfaces

These files retain their original interfaces. In particular, the Boyer–Moore in-memory functions take `text` first, while Naive and KMP take `pattern` first. The common runner adapts those differences.

| Module and call | Return value |
|---|---|
| `naive.search(pattern, text)` | List of all matching start positions. |
| `naive.search_counted(pattern, text)` | `(positions, comparisons)`. |
| `kmp.build_lps(pattern)` | `(lps, preprocessing_comparisons)`. |
| `kmp.kmp_search(pattern, text)` | `(positions, preprocessing_comparisons, search_comparisons)`. |
| `kmp.kmp_search_file(pattern, txt_path)` | The same three-part tuple after reading the file. |
| `boyer_moore.search_text(text, pattern)` | List of all matching start positions. |
| `boyer_moore.search_text_counted(text, pattern)` | A `SearchResult` with `positions`, `preprocessing_comparisons`, `search_comparisons`, `alignments`, and `total_shift`. |
| `boyer_moore.boyer_moore(pattern, txt_file)` | Positions from a UTF-8 text file. The module's `search` name is an alias for this file-based function. |
| `boyer_moore.boyer_moore_counted(pattern, txt_file)` | A `SearchResult` from a UTF-8 text file. |
| `kmp_timed.kmp_search(pattern, text)` | Positions only, with preprocessing included and no comparison counters. |

For nonempty patterns, the search functions return ascending, zero-based positions and retain overlapping matches. They return no positions when the pattern is longer than the text. Empty-pattern behavior differs: Naive raises `ValueError`, KMP returns an empty result, and Boyer–Moore returns every boundary from `0` to `len(text)`. The benchmark excludes empty patterns.

The KMP file reader removes whitespace. The Boyer–Moore file reader accepts a UTF-8 BOM and preserves other whitespace and line endings, so its returned positions refer to those file characters. The common benchmark reads the same frozen A/C/G/T input bytes for all three algorithms and excludes file I/O from timing.

The original KMP file's standalone test entry point imports the historical `test_common` module. Use the common runner above for repository-wide validation. Naive is an importable module; its file has no command-line entry point. Boyer–Moore also supports `python originals/boyer_moore.py PATTERN FILE`.

## How the directories fit together

- **`originals/`** contains the three archived implementations. Preserve their bytes when comparing against the recorded hashes. These are the source versions behind the stored experiment, not a unified package API.
- **`code/`** contains the common benchmark, the KMP timing variant, the saved-result verifier, and the report renderer. Packaging changes that make scripts portable are documented separately from algorithm changes.
- **`examples/`** contains a small Naive demonstration. **`figures/naive/`** and **`figures/team/`** contain the English figures generated for the individual and team reports.
- **`dataset_tools/`** contains input-generation and validation tools. `experiment_1.py`, `experiment_2.py`, and `experiment_3.py` generate individual experiments; `dataset_common.py` supplies shared routines. `verify_datasets.py` checks the generated package, and `export_shared_datasets.py` produces the text-file layout used for sharing. See the commands in [Data provenance and regeneration](DATA.md).
- **`data/`** holds the normalized *E. coli* sequence and its source metadata. **`inputs/`** holds the frozen text and pattern files used by the benchmark. **`reference/`** holds the condition definitions and complete expected-position lists.
- **`results/20261104/`** holds the historical measurement tables, environment record, verification records, and figures. Later benchmark runs belong in separate result folders.
- **`snapshot_manifest.json`** records the frozen file paths, sizes, and SHA-256 hashes. [`source_provenance.json`](source_provenance.json) records source/package hash comparisons. [Packaging notes](PACKAGING.md) explain the difference between historical measurement artifacts and portable repository scripts.

## When the code was used

The dates below describe recorded project activity. They do not establish the original creation date of every source file, and a later documentation edit does not imply a new benchmark run.

| Date | Recorded use | Evidence and scope |
|---|---|---|
| **November 3, 2026** | Data preparation and the initial Naive experiment. | The genome metadata records retrieval on November 3 at 07:56 UTC. The project's initial Naive run record starts at 19:46 KST that day. Dataset preparation and the separate Naive measurement preceded the combined comparison. |
| **November 4, 2026** | Frozen inputs and all three implementations were used in the integrated benchmark. | The snapshot was recorded at 12:40 KST; the combined run ran from 12:42 to 12:44 KST. The stored comparison contains 111 conditions, 333 algorithm-condition summaries, and 1,665 timed executions. These are the measurements cited in this repository. |
| **November 8, 2026** | The GitHub package was assembled and missing files were restored from the preserved experiment. | The packaging record documents restoration of 72 missing snapshot files and the archived CSV files and figures. This was a packaging and documentation step; timings were not rerun. |
| **November 15, 2026** | English documentation and code-navigation material were prepared for GitHub publication. | This guide and the supporting English documents describe the existing implementation and measurements. This date is a documentation revision date, not a new measurement date or a claim about the original authorship date of the code. |

The repository includes the [genome metadata](../data/NC_000913.3_metadata.json), [snapshot manifest](../snapshot_manifest.json), [integrated-run metadata](../results/20261104/metadata.json), and [packaging record](PACKAGING.md). The earlier standalone Naive run remains a separate project record; its timings are not mixed into the three-algorithm comparison.
