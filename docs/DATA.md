# Data provenance and regeneration

## Reference genome

| Field | Value |
|---|---|
| Source | [NCBI RefSeq NC_000913.3](https://www.ncbi.nlm.nih.gov/nuccore/NC_000913.3) |
| Organism | *Escherichia coli* str. K-12 substr. MG1655 |
| Recorded retrieval | November 3, 2026, UTC |
| Normalized sequence | [`data/NC_000913.3_sequence.txt`](../data/NC_000913.3_sequence.txt) |
| Length | **4,641,652 bp** |
| SHA-256 | `e999dceccb76562d40e49a10d9e6d4cf1c05d184f4f80b92bb32d4a2420c11d0` |

Normalization removes the FASTA header and whitespace and converts letters to uppercase, preserving the bases and their order. The raw FASTA is omitted from this package to avoid storing the same sequence twice. Its source URL and hash are recorded in [`NC_000913.3_metadata.json`](../data/NC_000913.3_metadata.json).

The reference is a bacterial genome. Although the genome is circular, the experiment treats the stored forward strand as a linear string. It does not search across the end-to-start boundary, search the reverse complement, or allow mutations and gaps.

## Frozen benchmark inputs

[`inputs/`](../inputs/) contains **21 DNA text files and 69 pattern files**, for 90 TXT files in total. They contain only A/C/G/T and have no trailing newline. [`reference/`](../reference/) contains `cases.json` and `expected_positions.json` for each of the three experiments, for six JSON files.

The snapshot manifest covers those 96 input/reference files and the three archived implementations, **99 files** in total. It records their sizes and SHA-256 hashes. `.gitattributes` disables automatic line-ending conversion for the preserved artifacts so their byte-level identity can be checked. The common runner validates these hashes before using the inputs.

Existing directory names such as `실험 1` and `패턴` are retained because the source scripts and manifest refer to them. In English, these mean “Experiment 1” and “Patterns.”

## Regenerate the same data

Run the existing preparation tools from the repository root. The commands below write to a separate `reproduction/` directory rather than overwriting the frozen inputs.

```sh
python -B -X utf8 dataset_tools/generate_datasets.py --ecoli data/NC_000913.3_sequence.txt --out reproduction/full
python -B -X utf8 dataset_tools/verify_datasets.py --root reproduction/full
python -B -X utf8 dataset_tools/export_shared_datasets.py --source reproduction/full --out reproduction/shared --descriptions dataset_tools/share_descriptions.json
```

The experiment-specific TXT files in `reproduction/shared/` correspond to `inputs/`. The condition and answer JSON files in `reproduction/full/` correspond to `reference/`. `reproduction/` is excluded from Git tracking.

The preserved `experiment_1.py`, `experiment_2.py`, and `experiment_3.py` scripts can also generate the experiments individually. Use each script's `--help` to see its options. The random DNA seed is `20261103`; the separate benchmark-order seed is `20261104`.

## Attribution

Keep the genome's source, accession, and version with any redistributed inputs or derived results. External data retains its own source terms; a license applied to this project's code does not replace those terms. The [code guide](CODE_GUIDE.md) explains how preparation tools, frozen inputs, references, and measurements connect.
