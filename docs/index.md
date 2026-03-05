# scaffoldr documentation

scaffoldr produces compressed codebase maps for LLM consumption. It analyzes workspace structure, parses source code via language-specific plugins, and outputs structural summaries that capture the architectural signal an LLM needs.

This documentation is organized following the [Diataxis](https://diataxis.fr/) framework into four quadrants.

## Tutorials

Learn scaffoldr by doing.

- [Your first structural analysis](tutorials/first-analysis.md) — Run scaffoldr on a workspace and read each output file step by step.

## How-to guides

Solve specific problems.

- [Regenerate after code changes](how-to/regenerate-after-changes.md) — When and how to re-run scaffoldr to keep artifacts fresh.
- [Investigate coupling between modules](how-to/investigate-coupling.md) — Find tight coupling, circular dependencies, and god classes.
- [Use output with an AI assistant](how-to/feed-to-ai-assistant.md) — Best practices for feeding structural context to LLMs.

## Reference

Technical descriptions of every output file.

- [Output files overview](reference/output-files.md) — All 7 output files, their formats, and which flags produce them.
- [structure_summary.txt](reference/structure-summary.md) — Combined summary: dependency graph, class hierarchy, entry points, cross-boundary calls.
- [dependencies.md](reference/dependencies-md.md) — Mermaid diagram and text dependency graph.
- [class_hierarchy.txt](reference/class-hierarchy.md) — Inheritance tree with method counts.
- [entry_points.txt](reference/entry-points.md) — CLI command to code mapping.
- [structure_full.json](reference/structure-full-json.md) — Complete JSON schema reference.
- [coupling_density.txt](reference/coupling-density.md) — Cross-boundary call pairs with caller/callee details.
- [structure_full.toon](reference/structure-full-toon.md) — TOON format: same data as JSON, fewer tokens.

## Explanation

Understand why scaffoldr works the way it does.

- [Why structural analysis for LLMs](explanation/why-structural-analysis.md) — Why compressed structural summaries help AI assistants more than raw call graphs.
- [Reading the outputs](explanation/reading-the-outputs.md) — How to interpret patterns, signals, and anomalies in scaffoldr output.
- [ELD: cross-boundary call analysis](explanation/eld-cross-boundary-analysis.md) — Why filtering to cross-boundary calls reveals coupling shape.
- [TOON format: why and when](explanation/toon-format.md) — Token-efficient structured data for LLM consumption.
