# Why cross-boundary call analysis matters

## The core idea: boundaries define architecture

At every scale, a codebase decomposes into opaque units with contracts. This is Effective Local Decomposition (ELD) — the principle that at any resolution, you should see units and their interactions, not the internals of those units.

Internal calls within a unit are implementation details. They tell you HOW a module works. A function calling a helper in the same subpackage is refactoring — you can rearrange it without affecting anything else. Cross-boundary calls tell you how modules RELATE. They reveal coupling, isolation, and where the real facades are.

## Why filtering to boundaries matters

A 200-module project might have 10,000+ function calls. Showing all of them is worse than showing none — the architectural signal drowns in noise. An LLM reading a raw call graph of 10,000 edges will waste its entire context window on implementation details it could infer by reading the source files directly.

By filtering to only the calls that cross subpackage boundaries, you might reduce 10,000 edges to 300. The coupling SHAPE becomes visible. You can see, at a glance, which modules depend on which, how tightly, and in what direction.

This is the same filtering a human architect does instinctively. Nobody draws architecture diagrams showing every private method call. They draw boxes and arrows between the boxes.

## What the coupling shape tells you

Here is scaffoldr analyzing itself (from `structure_full.toon`):

```toon
coupling_density[5]{source,target,call_count,callers}:
  scaffoldr.cli,scaffoldr.core,6,write_outputs->format_dependency_graph_text;write_outputs->format_class_hierarchy_text;...
  scaffoldr.__main__,scaffoldr.cli,4,main->parse_args;main->write_outputs;...
  scaffoldr.__main__,scaffoldr.core,4,main->generate_dependency_graph;main->generate_class_hierarchy;...
  scaffoldr.__main__,scaffoldr.langs,2,main->detect_language;main->get_analyzer
  scaffoldr.langs,scaffoldr.core,1,PythonAnalyzer->AnalysisResult
```

The tabular header declares the fields once; each row is one boundary pair. You can read the coupling shape at a glance:

- **`__main__` is the coupling hub** — 10 outgoing cross-boundary calls, 0 incoming. It wires everything together. This is the orchestrator.
- **`core` has 0 outgoing calls** — it depends on nothing else in the project. It is the foundation layer.
- **`cli` calls into `core` but not the reverse** — clean layering. Higher-level modules depend on lower-level modules, never the reverse.
- **`langs -> core` is a single call** — the language plugin barely touches the core. It references a contract type and nothing else. Nearly independent.

Here is the same data from scaffoldr analyzing itself:

```toon
coupling_density[7]{source,target,call_count,callers}:
  scaffoldr.cli,scaffoldr.core,7,_write_toon->format_toon;_write_text_files->format_coupling_density_text;...
  scaffoldr,scaffoldr.core,6,_analyze->generate_coupling_density;_analyze->generate_dependency_graph;...
  scaffoldr.langs.python,scaffoldr.core,1,analyze->AnalysisResult
```

7 calls from `cli` to `core` means the CLI layer depends heavily on core formatters. 6 calls from `__main__` to `core` means the entry point orchestrates all graph algorithms. This coupling is expected — higher layers depend on lower layers.

The number matters. One call is a thin wire. Seven calls is a meaningful dependency.

## Why subpackage is the right boundary

scaffoldr uses 2-level deep boundaries — `scaffoldr.cli`, not `scaffoldr.cli.parser`. This is the resolution where architectural decisions live.

- **File-level** is too detailed. `cli/output.py` calling `cli/parser.py` is internal refactoring, not architecture.
- **Package-level** is too coarse. A monorepo has one package — no boundaries to analyze.
- **Subpackage-level** corresponds to the natural "module" concept in most codebases. It is the unit that has a clear responsibility, a public interface, and internal implementation files.

When a developer says "the config module" or "the CLI layer," they mean the subpackage. This is the resolution humans already think at.

## Relation to the dependency graph

The dependency graph shows IMPORT-level coupling: module A imports module B. The cross-boundary call graph shows CALL-level coupling: function in A calls function in B.

These are different:

- You can have an import without a call — an unused import, or an import used only for type annotations.
- You can have many calls through one import — importing `core` once and calling 7 of its formatters.
- The dependency graph tells you THAT two modules are coupled. The call graph tells you HOW MUCH.

Both are useful. The dependency graph reveals the shape (cycles, layers, foundations). The call graph reveals the density (thin wires vs. load-bearing walls).

## Limitations

Cross-boundary call analysis in scaffoldr is static and approximate:

- **Import-name matching, not type inference.** If a function is imported as `from core import foo` and called as `foo()`, scaffoldr sees it. If it's aliased through a variable or passed as a callback, scaffoldr doesn't.
- **Dynamic dispatch is invisible.** `getattr(module, name)()`, plugin registries, and decorator-based routing produce calls that don't appear in the AST.
- **Only direct calls, not transitive dependencies.** If A calls B and B calls C, the analysis shows A→B and B→C separately. It does not show that A transitively depends on C.
- **Resolution is per-subpackage, not per-function.** Two very different functions in the same subpackage are aggregated together.

These limitations are acceptable because the goal is showing SHAPE, not proving correctness. A human architect's whiteboard diagram has the same limitations — and it's still the most useful artifact in the room.
