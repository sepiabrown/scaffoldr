# class_hierarchy.txt

The full inheritance tree for all classes in the workspace. Identical content to the Class Hierarchy section of `structure_summary.txt`, as a standalone file.

## Format

Header line:

```
# Class Hierarchy (<N> classes)
```

Each class occupies one line:

```
<indent>+- ClassName(BaseClass) @ subpackage.module (<N>m) [method1, method2, +K more]
```

### Fields

| Component | Description |
|-----------|-------------|
| Indentation | 2 spaces per inheritance depth. 0 = root class, 2 = direct child, 4 = grandchild. |
| `+-` | Tree branch marker |
| `ClassName` | The class name as defined in source |
| `(BaseClass)` | Parent class name(s), comma-separated. Omitted for root classes (no recognized parent in the codebase). |
| `@ subpackage.module` | Module path with the root package prefix stripped. `@ core.graphs` means `scaffoldr.core.graphs`. |
| `(<N>m)` | Total number of methods defined in the class body (includes all defs, including private). |
| `[method1, ...]` | Up to 5 key methods: public methods (no leading underscore) plus `__init__`, `__call__`, `__post_init__`. |
| `+K more` | Remaining method count beyond the 5 shown. Only appears when the class has more than 5 key methods. |

### Filtering

Classes with 2 or fewer methods **and** no children in the inheritance tree are omitted. This filters out trivial dataclasses, empty base classes, and similar noise.

### Sorting

Root classes are sorted alphabetically by fully-qualified name. Children are sorted alphabetically under their parent.

## Example

```
# Class Hierarchy (4 classes)

+- AnalyzeCommand @ cli.parser (0m)
+- CallCollector @ core.graphs (3m) [__init__, visit_Call]
+- AnalysisResult @ core.types (0m)
+- ModuleAnalysis @ core.types (0m)
```

This tells you scaffoldr has 4 classes. `CallCollector` is the only one with meaningful behavior (3 methods). The TypedDicts (`AnalyzeCommand`, `AnalysisResult`, `ModuleAnalysis`) have 0 methods — they are pure data contracts.
