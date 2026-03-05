# structure_summary.txt

The combined summary file. Contains the module dependency graph, class hierarchy, entry point map, and cross-boundary calls concatenated into a single text file with section headers.

This is the file to reach for when you need one artifact that captures the full project structure. It is designed to be small enough to paste into an LLM context window.

## Sections

The file contains four sections, separated by blank lines:

### 1. Module Dependency Graph

Header: `# Module Dependency Graph (package-level)`

Each line follows the format:

```
  <source_package> -> <dep1>, <dep2>, <dep3>
```

Lines are grouped under `## <root_package>` headers when the workspace contains multiple packages.

The arrow means "imports from." Source is a subpackage (two levels deep: `scaffoldr.cli`, `scaffoldr.core`). Dependencies are also subpackages.

Example:

```
## scaffoldr
  scaffoldr.cli -> scaffoldr.core
  scaffoldr.core -> scaffoldr.core
```

### 2. Class Hierarchy

Header: `# Class Hierarchy (<N> classes)`

Indented tree format. Each line:

```
<indent>+- ClassName(BaseClass) @ subpackage.module (<N>m) [method1, method2, +K more]
```

| Field | Meaning |
|-------|---------|
| Indentation | 2 spaces per inheritance level. Root classes have no indent. |
| `ClassName` | The class name |
| `(BaseClass)` | Parent class(es), omitted for root classes |
| `@ subpackage.module` | Module path relative to the root package |
| `(<N>m)` | Total method count for the class |
| `[method1, ...]` | Up to 5 key public methods (non-underscore, plus `__init__`, `__call__`, `__post_init__`) |
| `+K more` | How many methods beyond the 5 shown |

Only classes with more than 2 methods or that have children are included (noise filter).

### 3. Entry Points

Header: `# Entry Points`

Each entry point has 1-3 lines:

```
  <command-name> -> <module>:<function>
    calls: <func1>, <func2>, ...
    deps: <module1>, <module2>, ...
```

| Line | Meaning |
|------|---------|
| First line | CLI command name and the `module:function` it maps to (from `[project.scripts]` in pyproject.toml) |
| `calls:` | Functions directly called by the entry point function (1-level deep, up to 15). Builtins are filtered out. |
| `deps:` | Modules imported by the entry point module (up to 8). |

If the entry point module was not found during parsing, the line reads `[NOT FOUND]`.

### 4. Cross-Boundary Calls (ELD)

Header: `# Cross-Boundary Calls (ELD) -- <N> calls across <M> boundary pairs`

Grouped by boundary pair (source subpackage -> target subpackage), sorted by call count descending:

```
## scaffoldr.cli -> scaffoldr.core (5 calls)
  write_outputs -> format_dependency_mermaid
  write_outputs -> format_dependency_text
  write_outputs -> format_class_tree_text
```

Only calls where the source subpackage differs from the target subpackage are included. Internal calls within a subpackage are filtered out.

### Footer

```
---
Modules: <N> | Classes: <N> | Entry points: <N> | Cross-boundary calls: <N>
```

Aggregate counts for quick reference.
