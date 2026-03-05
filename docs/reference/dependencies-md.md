# dependencies.md

The package-level dependency graph in two formats: a Mermaid diagram for visual rendering and a text summary for reading.

## Structure

The file has two sections:

### 1. Package-Level Graph (Mermaid)

A fenced Mermaid code block containing a `graph LR` (left-to-right) flowchart.

```markdown
## Package-Level Graph

` ` `mermaid
graph LR
    scaffoldr_cli[cli]
    scaffoldr_core[core]
    scaffoldr_langs[langs]
    scaffoldr_cli --> scaffoldr_core
` ` `
```

Each node is a subpackage. Node IDs use underscores (Mermaid does not allow dots). Node labels show the short name (without the root package prefix).

Each arrow `-->` means "imports from."

**Rendering:** Paste the Mermaid block into any Mermaid-compatible renderer: GitHub Markdown preview, VS Code with the Mermaid extension, mermaid.live, or Obsidian.

### 2. Text Summary

The same dependency data as plain text, identical to the Module Dependency Graph section of `structure_summary.txt`.

```markdown
## Text Summary

` ` `
# Module Dependency Graph (package-level)

## scaffoldr
  scaffoldr.cli -> scaffoldr.core
  scaffoldr.core -> scaffoldr.core
` ` `
```

## Reading the graph

- **Nodes with many incoming arrows** are foundation packages — many other packages depend on them.
- **Nodes with many outgoing arrows** are orchestration packages — they coordinate many concerns.
- **Leaf nodes** (only outgoing arrows to the root package) are self-contained.
- **Bidirectional arrows** (A -> B and B -> A) indicate circular package-level coupling.
