# How to use scaffoldr output with an AI assistant

scaffoldr's primary purpose is to produce compressed structural summaries that fit in an LLM context window. Here's how to use them effectively.

## Provide the summary as context

Paste `structure_summary.txt` at the start of a conversation. It typically runs 200-500 tokens — small enough to include alongside your actual question.

```
Here is the structural summary of my project:

<paste structure_summary.txt>

Now, I want to add a new data augmentation pipeline. Which modules would I need to modify?
```

The LLM can use the dependency graph to identify that `dataset` and `dataprep` are the relevant packages, that `config` will need new configuration types, and that `train` imports from `dataset` so the training loop may need updates.

## When to include which file

| Task | Include |
|------|---------|
| General architecture question | `structure_summary.txt` |
| "Where does this class inherit from?" | `class_hierarchy.txt` |
| "What happens when I run this command?" | `entry_points.txt` |
| "Which modules will this change affect?" | `structure_summary.txt` (dependency section) |
| "How tightly coupled are X and Y?" | `coupling_density.txt` (relevant sections) |

For focused work on a specific subsystem, paste only the relevant section of the summary rather than the whole file.

## Use JSON for programmatic questions

When asking an LLM to write a script that processes your project structure, provide `structure_full.json` or relevant excerpts. The JSON is machine-parseable and unambiguous.

Example prompt:

```
Here is the module dependency graph for my project (from structure_full.json):

{
  "scaffoldr.cli.output": ["scaffoldr.core.formatters", "scaffoldr.core.types"],
  "scaffoldr.cli.parser": [],
  "scaffoldr.__main__": ["scaffoldr.cli.output", "scaffoldr.cli.parser", "scaffoldr.core.graphs", "scaffoldr.langs"]
}

Write a Python script that finds all modules with no dependents (not imported by anything).
```

## Use TOON for token-efficient context

When feeding structural data directly to an LLM (not a script), `structure_full.toon` uses ~40% fewer tokens than the JSON equivalent. The tabular format is particularly compact for class hierarchies and boundary call tables — the data scaffoldr produces most of.

Paste the TOON file (or relevant sections) when token budget is tight. For detailed comparison, see [TOON format: why and when](../explanation/toon-format.md).

## Keep artifacts fresh

If you've made significant structural changes since the last `scaffoldr analyze` run, the LLM will reason about stale data. Regenerate before starting a new conversation about architecture. See [How to regenerate](regenerate-after-changes.md).

## Token budget

Approximate token counts for scaffoldr output on a ~200-module project:

| File | Tokens |
|------|--------|
| `structure_summary.txt` | ~500 |
| `class_hierarchy.txt` | ~3,000 |
| `entry_points.txt` | ~200 |
| `coupling_density.txt` | ~1,500 |
| `structure_full.json` | ~50,000 |
| `structure_full.toon` | ~30,000 |

The summary file is designed to fit within even aggressive context budgets. The JSON is for targeted extraction, not for pasting wholesale. The TOON file is a middle ground — more detail than the summary, fewer tokens than the JSON.
