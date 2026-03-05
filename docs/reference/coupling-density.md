# coupling_density.txt

Cross-boundary function and method calls between subpackages, grouped by boundary pair.

## Format

Header line:

```
# Cross-Boundary Calls (ELD) — <N> calls across <M> boundary pairs
```

Each boundary pair is a section:

```
## <source_subpackage> -> <target_subpackage> (<N> calls)
  <caller> -> <callee>
  <caller> -> <callee>
```

### Fields

| Component | Description |
|-----------|-------------|
| `source_subpackage` | The subpackage containing the calling code (2 levels deep: `scaffoldr.cli`, `scaffoldr.core`). |
| `target_subpackage` | The subpackage containing the called function or class. |
| `(<N> calls)` | Number of unique caller→callee pairs for this boundary. Singular `call` when N = 1. |
| `caller` | A bare function name (`_analyze`) or `ClassName.method_name` (`CallCollector.visit_Call`). |
| `callee` | The imported name being called — a function or class name (`generate_dependency_graph`, `AnalysisResult`). |

Each call line is indented 2 spaces.

### Filtering

- Only **cross-boundary** calls are shown: source subpackage ≠ target subpackage. Calls within a subpackage are excluded.
- Subpackage is the first 2 levels of the module path (e.g., `scaffoldr.core.graphs` → `scaffoldr.core`).
- Calls to `self.*` are excluded (internal to the class).
- Python builtins (`len`, `str`, `isinstance`, `print`, etc.) are excluded.
- Duplicate caller→callee pairs within the same boundary are deduplicated.
- At most 50 boundary pairs are shown. If more exist, a summary line reports the remainder.

### Sorting

Boundary pairs are sorted by call count, highest first. Within a boundary, calls are grouped by caller in source order.

### Resolution

Call targets are resolved by matching the called name against `from ... import` statements in the source module. This is name-based, not type-inferred — if a function calls a local variable that shadows an import, the result may be inaccurate.

## Example

```
# Cross-Boundary Calls (ELD) — 15 calls across 3 boundary pairs

## scaffoldr.cli -> scaffoldr.core (7 calls)
  _write_toon -> format_toon
  _write_text_files -> format_coupling_density_text
  _write_text_files -> format_dependency_graph_text
  _write_text_files -> format_class_hierarchy_text
  _write_text_files -> format_entry_points_text
  ...

## scaffoldr -> scaffoldr.core (6 calls)
  _analyze -> generate_coupling_density
  _analyze -> generate_dependency_graph
  _analyze -> generate_class_hierarchy
  ...

## scaffoldr.cli -> scaffoldr.langs (2 calls)
  _analyze -> detect_language
  _analyze -> parse_modules
```

The first section shows 7 cross-boundary calls. `_write_toon` and `_write_text_files` are bare function callers. `_analyze -> detect_language` is a bare function call.
