# Reading the outputs: what the numbers tell you

This page explains how to interpret the patterns, signals, and anomalies in scaffoldr's output. Where the [reference pages](../reference/output-files.md) describe the *format*, this page explains the *meaning*.

## Dependency graph: reading coupling shape

The dependency graph shows which subpackages import from which. The interesting signal is not any single edge — it's the shape of the whole graph.

### Foundation vs. orchestration packages

Count the arrows:

- **Many incoming arrows** = foundation package. Everyone depends on it. Examples: `types`, `utils`, `core`. These packages should be stable — changes here ripple widely.
- **Many outgoing arrows** = orchestration package. It coordinates many concerns. Examples: `cli`, `tasks`, `train`. These packages are where the wiring lives.
- **Few arrows in either direction** = isolated package. It has a narrow concern and limited coupling. Examples: `losses`, `algorithms`.

### Circular dependencies

If `A -> B` and `B -> A` both appear, you have a package-level cycle. This is a structural problem: neither package can be understood, tested, or modified independently.

In practice, cycles often arise from:
- A convenience import in `__init__.py` that pulls in too much
- A type defined in the wrong package (e.g., `dataset` importing from `dataprep` because a type it needs lives there)

The fix is usually to move the shared type into a third package that both depend on, or to invert the dependency with a callback/protocol.

### Self-loops

A line like `scaffoldr.core -> scaffoldr.core` means one module inside `core/` imports from another module inside `core/`. This is normal and expected — subpackages have internal structure. It only becomes a problem if the self-loop is the *only* significant edge, which would mean the subpackage is not well-decomposed internally.

## Class hierarchy: reading the tree

### The method count signal

The `(<N>m)` metric is the single most useful number in the class hierarchy.

| Range | Interpretation |
|-------|---------------|
| 0m | Pure data contract (TypedDict, dataclass with no methods, empty subclass) |
| 1-5m | Focused class with a narrow responsibility |
| 6-15m | Substantial class, probably the primary implementation for a concern |
| 16-30m | Complex class. Likely a key architectural component (orchestrator, manager). Worth understanding deeply. |
| 30m+ | Potential god class. Contains many responsibilities. May need decomposition. |

### Thin wrappers vs. behavioral subclasses

When a child class has 0m (no methods of its own), it is a *thin wrapper* — it exists only to specialize the parent via constructor arguments or class attributes. For example:

```
+- BaseProcessor @ processing.base (25m)
  +- FastProcessor(BaseProcessor) @ processing.fast (0m)
```

`FastProcessor` inherits all 25 methods unchanged. It exists for type identity or configuration, not for new behavior.

When a child has many methods, it is a *behavioral subclass* — it overrides or extends the parent significantly.

### Duplicate class names

If the same class name appears at two different module paths:

```
+- SubsetDataset(Dataset) @ dataset.manager.subsetting (5m)
+- SubsetDataset(Dataset) @ dataset.subsetting (5m)
```

This is usually a migration artifact. The class was moved or refactored but both versions still exist. The method counts can confirm: if they're identical, it's likely a copy.

### Strategy pattern detection

A cluster of small classes all inheriting from one ABC:

```
+- SubsetStrategy(ABC) @ dataset.manager.subsetting (2m)
  +- BootstrapSampler (3m)
  +- FirstNSampler (3m)
  +- RandomNSampler (3m)
```

This is the strategy pattern. The ABC defines the contract, each child is one implementation. The number of implementations tells you how extensible this particular concern is.

## Entry points: reading the code path

### The `calls` line as a debugging guide

The `calls` line shows what the entry point function calls directly (1 level deep). When something is broken, this is your triage list:

```
  scaffoldr -> __main__:main
    calls: _analyze, parse_args
    deps: cli.output, cli.parser, core.graphs, langs
```

If `scaffoldr analyze` crashes, the error is in one of: `parse_args`, `_analyze`, or something they call. The `deps` line tells you which modules must be importable for the command to even load.

### Missing entry points

If an entry point shows `[NOT FOUND]`, the module referenced in `[project.scripts]` doesn't exist or has a syntax error. This is a broken CLI command — it will crash at import time.

## Cross-boundary calls: reading the coupling density

### High-count boundaries

A boundary pair with many calls (e.g., `config -> types (94 calls)`) means those two subpackages are tightly coupled. This is not necessarily bad — `config` constructing typed config objects is expected. But it tells you: if you change the `types` interface, you will need to update `config` extensively.

### Low-count boundaries

A single call across a boundary (e.g., `tools -> utils (1 call)`) means the coupling is minimal. These packages are nearly independent — a change to one is unlikely to affect the other.

### Absent boundaries

If two subpackages have no cross-boundary calls, they are completely decoupled at the function level. They may still have import-level dependencies (visible in the dependency graph), but no actual code flows between them.

### Caller patterns

When one function appears as the caller in many cross-boundary calls, it is a *hub function* — a wiring point that connects multiple concerns. Hub functions are often entry points or orchestration functions (`main`, `_analyze`, `write_outputs`). They are the natural place to look when understanding how subsystems connect.

## Choosing the right file for the question

| Question | File |
|----------|------|
| "What's the overall shape of this project?" | `structure_summary.txt` |
| "How are the packages connected?" | `dependencies.md` (render the Mermaid) |
| "What classes exist and how do they relate?" | `class_hierarchy.txt` |
| "What does this CLI command actually run?" | `entry_points.txt` |
| "Which packages are most tightly coupled?" | `coupling_density.txt` |
| "I need to write a script that processes this data" | `structure_full.json` |
| "I need to feed full structural data to an LLM" | `structure_full.toon` (fewer tokens than JSON) |
| "I'm feeding context to an LLM" | `structure_summary.txt` (fits in ~500 tokens) |
