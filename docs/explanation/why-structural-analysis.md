# Why structural analysis for LLMs

## The problem

An LLM reading a codebase faces a fundamental constraint: the context window is finite. A 200-file project cannot fit in context all at once. The LLM must decide which files to read, and it makes that decision with incomplete information about how the files relate.

Humans face the same problem. A new developer joining a project doesn't read every file — they look for a map. Architecture diagrams, module overviews, class hierarchies. These compressed representations let them reason about structure without holding every implementation detail in their head.

## Why raw call graphs don't help

Traditional call graph tools (like pycg) produce every function-to-function edge. For a 200-file project, that's thousands of edges:

```
main -> parse_args
parse_args -> _build_parser
_build_parser -> ArgumentParser
ArgumentParser -> add_argument
...
```

This is too granular. Most of these calls are internal to a module — they tell you how a module works, not how modules relate. Dumping this into an LLM context window wastes tokens on implementation details the LLM could infer by reading the source directly.

## What helps instead: compressed structural summaries

What an LLM needs is the same thing a human architect needs — a map at the right resolution:

1. **Module dependency graph** — which packages import from which. Not every file, just the package-level edges. This reveals coupling shape: which packages are foundations (depended on by many), which are orchestrators (depend on many), and where circular dependencies lurk.

2. **Class hierarchy** — inheritance trees with method counts. In object-oriented codebases (especially ML/PyTorch), the class hierarchy IS the architecture. Knowing that `ImportCollector` inherits from `ast.NodeVisitor` tells you where to look for behavior: the child overrides the parent's visitor methods.

3. **Entry points** — CLI commands and what they call. This is the "where does execution start?" question. An LLM asked to debug a training crash needs to know that `myapp-train` calls `resolve_trainer` then `trainer.train`. Without this, it would have to read the CLI module, trace imports, find the function, and read it — burning context on navigation.

4. **Cross-boundary calls (ELD)** — only the calls that cross subpackage boundaries. If `config` makes 94 calls into `types`, that's a tight coupling signal. If `tools` makes 1 call into `utils`, it's well-isolated. This is the most distinctive output — it filters thousands of calls down to the architecturally significant ones.

## Why this is different from just reading imports

An LLM can read `from scaffoldr.core.graphs import generate_dependency_graph` and know that one file depends on another. But it cannot efficiently:

- **Aggregate** — see that `cli/output.py` imports 6 functions from `core/formatters`, making `cli -> core` the heaviest coupling in the project.
- **Detect circularity** — two packages importing each other is invisible when reading files one at a time.
- **See the hierarchy** — tracing inheritance across multiple files to reconstruct `FunctionCollector -> ast.NodeVisitor -> object` requires reading all those files.
- **Prioritize** — knowing that `FunctionCollector` has 3 methods while `CallCollector` has 2 tells you where the complexity lives, without reading either.

The structural summary pre-computes these aggregations. It trades a few hundred tokens of context for information that would otherwise cost thousands of tokens (or multiple file-reading rounds) to reconstruct.

## When it helps and when it doesn't

**Helps most:**
- Codebase too large for context (100+ files)
- ML/PyTorch projects with deep inheritance
- Multi-package workspaces where cross-package coupling matters
- Entry point tracing ("what happens when I run this command?")
- Architectural reasoning ("which modules are coupled?")

**Helps least:**
- Single-file changes where the dependency context is obvious
- Small projects (under 20 files) that fit in context
- Projects with flat structure (no subpackages, no inheritance)

## The design choice: AST-only, stdlib-only

scaffoldr uses Python's built-in `ast` module and nothing else. No pycg, no pylint, no external dependencies.

This is deliberate:

- **pycg** is archived (Nov 2023), has Python 3.11+ compatibility issues, and produces function-level graphs that are too detailed.
- **pyreverse** (from pylint) requires installing pylint and its dependency chain.
- **Custom AST** gives exact control over what resolution to operate at: package-level for dependencies, class-level for hierarchy, function-level only for entry points.

The tradeoff is that AST analysis is static — it cannot resolve dynamic dispatch (`getattr`, `registry[name]()`). For the architectural questions scaffoldr answers, this is acceptable. The module-level shape is determined by import statements, not by runtime behavior.
