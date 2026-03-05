# structure_full.json

The complete structural data in machine-readable JSON format. Written when `--json` or `--full` is passed.

## Top-level structure

```json
{
  "dependency_graph": { ... },
  "class_hierarchy": { ... },
  "entry_points": { ... },
  "coupling_density": { ... },
  "metadata": { ... }
}
```

## dependency_graph

```json
{
  "module_level": {
    "<full.module.name>": ["<dep1>", "<dep2>"],
    ...
  },
  "package_level": {
    "<subpackage>": ["<dep_subpackage1>", "<dep_subpackage2>"],
    ...
  }
}
```

| Key | Description |
|-----|-------------|
| `module_level` | File-by-file import resolution. Keys are full module names (e.g. `scaffoldr.core.graphs`). Values are sorted lists of modules that this module imports. |
| `package_level` | Collapsed to subpackage level (2 levels deep). Same structure but with subpackage names as keys. Self-imports within a subpackage are excluded. |

## class_hierarchy

```json
{
  "total_classes": 4,
  "hierarchy": [
    {
      "name": "CallCollector",
      "module": "core.graphs",
      "bases": [],
      "method_count": 3,
      "key_methods": ["__init__", "visit_Call"],
      "children": [
        { "name": "...", "module": "...", ... }
      ]
    }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `total_classes` | int | Total number of classes found across all modules |
| `hierarchy` | array | Nested tree of class nodes |
| `hierarchy[].name` | string | Class name |
| `hierarchy[].module` | string | Module path (root package prefix stripped) |
| `hierarchy[].bases` | string[] | Parent class names as written in source |
| `hierarchy[].method_count` | int | Total methods defined in the class body |
| `hierarchy[].key_methods` | string[] | Up to 8 key methods (public + `__init__`, `__call__`, `__post_init__`) |
| `hierarchy[].children` | array? | Child classes (same structure, recursive). Absent if no children. |

## entry_points

```json
{
  "<command-name>": {
    "module": "<module.path>",
    "function": "<func_name>",
    "calls": ["<func1>", "<func2>"],
    "imports": ["<module1>", "<module2>"]
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `module` | string | Module path (root package prefix stripped) |
| `function` | string | Function name |
| `calls` | string[] | Functions directly called (up to 15, builtins filtered) |
| `imports` | string[] | Modules imported by the entry point module (up to 8) |
| `status` | string? | `"not_found"` if the module could not be parsed. Only present on error. |

## coupling_density

```json
{
  "boundaries": [
    {
      "source": "scaffoldr.cli",
      "target": "scaffoldr.core",
      "calls": [
        { "caller": "write_outputs", "callee": "format_dependency_mermaid" },
        { "caller": "write_outputs", "callee": "format_dependency_text" }
      ]
    }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `boundaries` | array | Boundary pairs sorted by call count (most coupled first) |
| `boundaries[].source` | string | Source subpackage (full name) |
| `boundaries[].target` | string | Target subpackage (full name) |
| `boundaries[].calls` | array | Individual cross-boundary calls |
| `boundaries[].calls[].caller` | string | Calling function or `ClassName.method_name` |
| `boundaries[].calls[].callee` | string | Called function or class name |

## metadata

```json
{
  "total_modules": 10,
  "parsed_modules": 10,
  "parse_errors": 0
}
```

| Field | Type | Description |
|-------|------|-------------|
| `total_modules` | int | Total .py files discovered |
| `parsed_modules` | int | Successfully parsed (AST produced) |
| `parse_errors` | int | Files that failed to parse (syntax errors, encoding issues) |
