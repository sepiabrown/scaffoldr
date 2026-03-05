# Why TOON format

## The token budget problem

LLMs process text as tokens. When scaffoldr feeds structural data into a context window, every token counts — and JSON is wasteful for the kind of data scaffoldr produces.

JSON repeats every field name for every object. A class hierarchy with 100+ entries repeats `"name":`, `"module":`, `"bases":`, `"method_count":`, `"key_methods":` for every entry. The braces, brackets, and quotes add up. For a 221-module project, the JSON output can reach ~50,000 tokens — a quarter of a typical context window, spent on structural metadata alone.

## What TOON does differently

TOON (Token-Oriented Object Notation) declares field names once in a tabular header, then uses comma-separated rows for data:

```
classes[7]{depth,name,module,bases,method_count,key_methods}:
  0,CallCollector,core.graphs,ast.NodeVisitor,2,"__init__,visit_Call"
  0,FunctionCollector,langs.python.parsing,ast.NodeVisitor,3,"__init__,visit_FunctionDef,visit_AsyncFunctionDef"
```

The equivalent JSON:

```json
[
  {"name": "CallCollector", "module": "core.graphs", "bases": ["ast.NodeVisitor"], "method_count": 2, "key_methods": ["__init__", "visit_Call"]},
  {"name": "FunctionCollector", "module": "langs.python.parsing", "bases": ["ast.NodeVisitor"], "method_count": 3, "key_methods": ["__init__", "visit_FunctionDef", "visit_AsyncFunctionDef"]}
]
```

The header `classes[N]{depth,name,module,bases,method_count,key_methods}:` costs a few tokens once. In JSON, those six field names cost tokens N times each.

## Token savings

Approximate comparison for scaffoldr output:

| Project size | JSON tokens | TOON tokens | Savings |
|---|---|---|---|
| 13 modules | ~2,400 | ~1,400 | ~40% |
| 221 modules | ~50,000 | ~30,000 | ~40% |

The savings come almost entirely from uniform arrays — class hierarchies, dependency lists, cross-boundary call tables. These are scaffoldr's primary outputs. Nested objects like `metadata:` use YAML-like syntax with minimal savings over JSON, but they're a tiny fraction of the output.

## Human readability

TOON is more readable than JSON for tabular data. A list of 50 classes in JSON is a wall of braces and repeated keys. The same list in TOON looks like a spreadsheet — the header tells you what the columns mean, and each row is a compact data line.

For deeply nested structures, JSON is clearer. But scaffoldr's data is mostly tabular — class lists, dependency tables, entry point tables, boundary call tables — so TOON is a natural fit.

## When to use which format

scaffoldr outputs the same data in three formats. Each serves a different purpose:

- **TOON** (`--toon`) — feeding structural data to an LLM where token budget matters. This is the primary use case for scaffoldr.
- **JSON** (`--json`) — programmatic access, scripting, tooling integration. Parse it with any JSON library.
- **Text** (default) — human reading. A prose summary with the key findings, suitable for quick orientation at the start of a conversation.

All three contain the same structural data — modules, classes, entry points, cross-boundary calls — just encoded differently.

## The TOON spec

TOON is an open format ([github.com/toon-format/toon](https://github.com/toon-format/toon)). scaffoldr implements a subset:

- **Tabular arrays** — the header-plus-rows pattern for uniform data (`classes[N]{fields}:`)
- **Nested objects** — YAML-like indentation for metadata and grouped sections
- **Simple arrays** — comma-separated lists within values (e.g., dependency lists)

No full parser is needed on the consuming side. The format is designed to be straightforward to write and easy for LLMs to consume — an LLM can read TOON without any special instructions, because the header is self-describing.

## The design tradeoff

TOON optimizes for one specific consumer: LLMs with finite context windows. It sacrifices JSON's universality (every language has a JSON parser) for token efficiency on the kind of data scaffoldr produces. For projects where the structural output is small enough to fit comfortably in context, the savings don't matter much. For large codebases — hundreds of modules, hundreds of classes — the 40% reduction is the difference between fitting in context and not.
