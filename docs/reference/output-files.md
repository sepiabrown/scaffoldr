# Output files

scaffoldr produces up to eight output files from a single `analyze` run. By default, only `facade_leaks.txt` is written. Use format flags to produce additional outputs.

## Default output

Always written, regardless of flags.

| File | Format | What it contains |
|------|--------|-----------------|
| `facade_leaks.txt` | Plain text | Imports that bypass package facades |

## Text outputs

Written when `--full` is used, or when `--toon` is used.

| File | Format | What it contains |
|------|--------|-----------------|
| [`structure_summary.txt`](structure-summary.md) | Plain text | All four views combined into one file |
| [`dependencies.md`](dependencies-md.md) | Mermaid + text | Package-level dependency graph |
| [`class_hierarchy.txt`](class-hierarchy.md) | Indented tree | Inheritance tree with method counts |
| [`entry_points.txt`](entry-points.md) | Plain text | CLI entry points with call chains |
| [`coupling_density.txt`](coupling-density.md) | Plain text | ELD view: only calls that cross module boundaries |

## Machine-readable outputs

| File | Format | Flag | What it contains |
|------|--------|------|-----------------|
| [`structure_full.json`](structure-full-json.md) | JSON | `--json` or `--full` | Complete structured data for programmatic access |
| [`structure_full.toon`](structure-full-toon.md) | TOON | `--toon` or `--full` | Token-optimized notation: YAML structure + CSV density |

## Format flags

| Flag | Files written |
|------|--------------|
| *(none)* | `facade_leaks.txt` only |
| `--json` | `facade_leaks.txt` + `structure_full.json` |
| `--toon` | `facade_leaks.txt` + 5 text files + `structure_full.toon` |
| `--full` | All 8 files |

## Output directory

By default, files are written to `<workspace>/.scaffoldr/`. Override with `--output-dir DIR`.
