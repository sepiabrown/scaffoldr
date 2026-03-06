# Your first structural analysis

This tutorial walks you through running scaffoldr on a workspace and reading each output file. By the end, you will be able to interpret the structural summary and use it to understand how a codebase is organized.

## Prerequisites

- Python 3.11+
- scaffoldr installed (`pip install -e .` or `uv pip install -e .` from the scaffoldr directory)
- A Python workspace to analyze (must have a `pyproject.toml` with `[tool.uv.workspace]` members, or subdirectories containing `pyproject.toml` files)

## Step 1: Run the analysis

From your workspace root directory, run:

```bash
scaffoldr analyze . --full
```

You will see progress output:

```
============================================================
Structural Analysis: my-workspace
============================================================

[0/4] Workspace: mypackage (mypackage-py/src/mypackage)
  Entry points: mypackage-cli

[1/4] Discovered 10 modules

[2/4] Parsed 10 modules (0 errors)

[3/4] Generating artifacts...
  Dependency graph: 3 package edges
  Class hierarchy: 4 classes
  Entry points: 1 endpoints
  Cross-boundary calls (ELD): 5 calls across 2 boundary pairs

[4/4] Writing to .scaffoldr/
  [OK] structure_full.json
  [OK] structure_full.toon
  [OK] structure_summary.txt
  [OK] dependencies.md
  [OK] class_hierarchy.txt
  [OK] entry_points.txt
  [OK] coupling_density.txt
  [OK] facade_leaks.txt

[DONE] Structural analysis complete!
```

The output directory (`.scaffoldr/` by default) now contains 8 files.

## Step 2: Read the summary

Open `.scaffoldr/structure_summary.txt`. This is the all-in-one map. It has four sections.

### The dependency graph

The first section shows which subpackages import from which:

```
# Module Dependency Graph (package-level)

## scaffoldr
  scaffoldr.cli -> scaffoldr.core
  scaffoldr.__main__ -> scaffoldr.cli, scaffoldr.core, scaffoldr.langs
  scaffoldr.langs -> scaffoldr.core
```

Read each line as "the left side imports from the right side." Here you can see:
- `cli` depends on `core` (it uses formatters to render output)
- `__main__` depends on everything (it wires the layers together)
- `langs` depends on `core` (language plugins produce `AnalysisResult`, a core type)
- `core` depends on nothing outside itself — it is the foundation

### The class hierarchy

The second section lists every class with its inheritance:

```
# Class Hierarchy (4 classes)

+- CallCollector @ core.graphs (3m) [__init__, visit_Call]
```

Read this as: `CallCollector` lives in `core.graphs`, has 3 methods, the key ones being `__init__` and `visit_Call`. There is no indentation, so it has no parent class in this codebase (it inherits from `ast.NodeVisitor`, which is external).

The `(3m)` tells you this class has moderate complexity. A class with `(0m)` is a pure data contract. A class with `(35m)` is a heavyweight that probably deserves careful understanding.

### The entry points

The third section maps CLI commands to code:

```
# Entry Points

  scaffoldr -> __main__:main
    calls: _analyze, parse_args
    deps: cli.output, cli.parser, core.graphs, langs
```

This tells you: the `scaffoldr` command runs `main()` in `__main__.py`. That function calls `parse_args` and `_analyze`. The module imports from 4 other modules.

If you needed to debug the CLI, you now know exactly where to start.

### The cross-boundary calls

The fourth section shows only the function calls that cross subpackage boundaries:

```
# Cross-Boundary Calls (ELD) -- 5 calls across 2 boundary pairs

## scaffoldr.__main__ -> scaffoldr.core (3 calls)
  _analyze -> generate_dependency_graph
  _analyze -> generate_class_hierarchy
  _analyze -> generate_entry_point_map
```

This tells you `__main__._analyze` is the hub function that connects the layers. It calls 3 functions in `core`. These are the cross-module wiring points.

### The footer

```
---
Modules: 10 | Classes: 4 | Entry points: 1 | Cross-boundary calls: 5
```

Quick aggregate counts for reference.

## Step 3: Visualize the dependencies

Open `.scaffoldr/dependencies.md` in a Markdown renderer that supports Mermaid (GitHub, VS Code with Mermaid extension, mermaid.live). You will see a flowchart with boxes and arrows showing the package-level dependency graph.

Boxes with many incoming arrows are foundations. Boxes with many outgoing arrows are orchestrators.

## Step 4: Explore the class tree

Open `.scaffoldr/class_hierarchy.txt`. Scan for classes with high method counts — these are the load-bearing components. Look at indentation to see inheritance: indented classes inherit from the class above them at a lower indentation level.

## Step 5: Check the JSON

Open `.scaffoldr/structure_full.json` if you need programmatic access. The `dependency_graph.module_level` section is especially useful — it gives file-level import resolution, not just package-level.

## Step 6: Check the TOON output

Open `structure_full.toon` if you plan to feed structural data to an LLM. It contains the same data as the JSON but uses ~40% fewer tokens. The class hierarchy section is particularly compact — each class is one comma-separated line instead of a multi-line JSON object.

For a detailed comparison, see [TOON format: why and when](../explanation/toon-format.md).

## What you learned

You now know how to:
- Run `scaffoldr analyze` on a workspace
- Read the four sections of `structure_summary.txt`
- Interpret method counts, dependency arrows, and entry point traces
- Use the Mermaid diagram for visual exploration
- Find the JSON data for programmatic queries
- Use the TOON format for token-efficient LLM context

For deeper interpretation of what the patterns mean, see [Reading the outputs](../explanation/reading-the-outputs.md).
