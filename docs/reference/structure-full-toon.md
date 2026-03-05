# structure_full.toon

The complete structural data in human-readable TOON format. Written when `--toon` or `--full` is passed. Contains the same data as `structure_full.json`.

## TOON syntax primer

The minimum syntax needed to read this file:

| Pattern | Meaning |
|---------|---------|
| `key: value` | Scalar field (YAML-like) |
| `key[N]: val1,val2,...` | Simple array of N comma-separated values |
| `key[N]{f1,f2,...}:` | Tabular array header — N rows, each with named fields |
| (indented CSV rows) | One row per record under a tabular header |
| `"val1,val2"` | Double quotes escape commas inside a value |

Indentation indicates nesting. Reference: <https://github.com/toon-format/toon>

## Top-level sections

```
metadata:
dependency_graph:
class_hierarchy:
entry_points[N]{...}:
coupling_density[N]{...}:
```

Five sections, same as `structure_full.json`. `metadata` and `dependency_graph` use nested key-value pairs. `class_hierarchy` contains a nested tabular array. `entry_points` and `coupling_density` are top-level tabular arrays.

## metadata

```toon
metadata:
  total_modules: 221
  parsed_modules: 221
  parse_errors: 0
```

| Field | Description |
|-------|-------------|
| `total_modules` | Total `.py` files discovered |
| `parsed_modules` | Successfully parsed (AST produced) |
| `parse_errors` | Files that failed to parse |

## dependency_graph

```toon
dependency_graph:
  package_level:
    scaffoldr.cli[3]: scaffoldr.core,scaffoldr.langs,scaffoldr
    scaffoldr.core[1]: scaffoldr.langs
```

Uses `key[N]: val1,val2,...` syntax. Each line is one subpackage followed by the count of its dependencies in brackets, then a comma-separated list of subpackages it imports. Self-imports within a subpackage are excluded.

## class_hierarchy

```toon
class_hierarchy:
  total_classes: 7
  classes[7]{depth,name,module,bases,method_count,key_methods}:
    0,AnalyzeCommand,cli.parser,TypedDict,0,
    0,CallCollector,core.graphs,ast.NodeVisitor,2,"__init__,visit_Call"
    0,FunctionCollector,langs.python.parsing,ast.NodeVisitor,3,"__init__,visit_FunctionDef,visit_AsyncFunctionDef"
    0,ImportCollector,langs.python.parsing,ast.NodeVisitor,3,"__init__,visit_Import,visit_ImportFrom"
```

The header `classes[N]{depth,name,module,bases,method_count,key_methods}:` declares the field order. Each subsequent indented line is one class as a CSV row.

| Column | Type | Description |
|--------|------|-------------|
| `depth` | int | Tree depth. `0` = root class (no parent in the codebase). `1` = direct child, `2` = grandchild, etc. |
| `name` | string | Class name |
| `module` | string | Module path (root package prefix stripped) |
| `bases` | string | Parent class names as written in source. Empty = no base class found in the codebase. Multiple bases are comma-joined inside double quotes (e.g. `"ast.NodeVisitor,ABC"`). |
| `method_count` | int | Total methods defined in the class body |
| `key_methods` | string | Up to 8 key methods (public + `__init__`, `__call__`, `__post_init__`). Multiple methods are comma-joined inside double quotes. Empty = no key methods. |

The `depth` field encodes parent-child relationships through ordering: a row with depth N is a child of the nearest preceding row with depth N-1. This replaces the nested `children` arrays used in the JSON format.

## entry_points

```toon
entry_points[5]{name,module,function,calls,imports}:
  scaffoldr,__main__,main,"_analyze,parse_args,sys.exit","cli.output,cli.parser,core.graphs,langs,langs.python"
  scaffoldr-web,cli.server,main,"create_app,parse_args","cli.output,core.graphs"
```

| Column | Type | Description |
|--------|------|-------------|
| `name` | string | Command name (from `[project.scripts]`) |
| `module` | string | Module path (root package prefix stripped) |
| `function` | string | Entry point function name |
| `calls` | string | Functions directly called (up to 15, builtins filtered). Comma-joined inside double quotes when multiple. |
| `imports` | string | Modules imported by the entry point module (up to 8). Comma-joined inside double quotes when multiple. Empty = no imports. |

## coupling_density

```toon
coupling_density[3]{source,target,call_count,callers}:
  scaffoldr.cli,scaffoldr.core,7,_write_toon->format_toon;_write_text_files->format_coupling_density_text;...
  scaffoldr,scaffoldr.core,6,_analyze->generate_coupling_density;_analyze->generate_dependency_graph;...
```

| Column | Type | Description |
|--------|------|-------------|
| `source` | string | Source subpackage (full name) |
| `target` | string | Target subpackage (full name) |
| `call_count` | int | Number of cross-boundary calls |
| `callers` | string | Individual calls as `caller->callee` pairs, semicolon-separated. Sorted by call count (most coupled boundary first). |
