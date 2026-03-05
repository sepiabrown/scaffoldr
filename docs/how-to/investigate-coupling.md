# How to investigate coupling between modules

Use scaffoldr's outputs to find where modules are tightly coupled, identify circular dependencies, and decide where to draw module boundaries.

## Find the most coupled package pairs

Open `coupling_density.txt`. The boundary pairs are sorted by call count, most coupled first:

```
## scaffoldr.cli -> scaffoldr.core (7 calls)
  _write_toon -> format_toon
  _write_text_files -> format_coupling_density_text
  ...
```

The first few entries are the tightest couplings in your codebase. Ask: is this coupling expected? `cli -> core` is natural (the CLI layer calls core formatters). But a boundary pair at 50+ calls might indicate that one module knows too much about another's internals.

## Detect circular dependencies

Open `dependencies.md` and render the Mermaid diagram (paste into mermaid.live or a Mermaid-capable editor).

Look for cycles: arrows that form a loop. In the text summary (`structure_summary.txt`), check whether both directions appear:

```
  package_a -> package_b
  package_b -> package_a    # <- circular!
```

If you find a cycle, trace the actual calls by checking both boundary pairs in `coupling_density.txt`:

```
## package_a -> package_b (12 calls)
  ...
## package_b -> package_a (3 calls)
  ...
```

The smaller side (3 calls) is usually easier to fix — move those 3 dependencies to break the cycle.

## Find god classes

Open `class_hierarchy.txt` and look for high method counts:

```
+- RequestHandler @ server.handler (35m) [...]
+- DataPipeline @ pipeline.manager (32m) [...]
```

Classes above 25-30 methods are candidates for decomposition. Check whether their methods cluster into groups (e.g., "setup methods", "training loop methods", "logging methods") that could become separate classes or mixins.

## Identify unused modules

Open `structure_full.json` and look at `dependency_graph.module_level`. Modules that appear as keys but never appear as values in any other module's dependency list are not imported by anything in the project. They may be dead code, standalone scripts, or test utilities.

```bash
# Quick check with jq:
jq -r '.dependency_graph.module_level | keys[]' structure_full.json > all_modules.txt
jq -r '.dependency_graph.module_level | [.[] | .[]] | unique | .[]' structure_full.json > imported_modules.txt
diff all_modules.txt imported_modules.txt
```

For a human-readable view of the same data, check the `dependency_graph` section of `structure_full.toon`.

## Evaluate a proposed refactor

Before moving code between modules:

1. Check the current dependency graph to see what depends on the source module
2. Check cross-boundary calls to see exactly which functions are called across the boundary you're about to change
3. After the refactor, regenerate and compare (see [How to regenerate](regenerate-after-changes.md))
