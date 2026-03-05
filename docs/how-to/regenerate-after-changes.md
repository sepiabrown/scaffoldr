# How to regenerate after code changes

When you add, remove, or rename modules, classes, or entry points, the structural artifacts become stale. Re-run scaffoldr to update them.

## Quick regeneration

From the workspace root:

```bash
scaffoldr analyze . --full
```

This overwrites all files in `.scaffoldr/` with fresh output.

## Regenerate text files only

If you only need the compressed summaries (not JSON or TOON):

```bash
scaffoldr analyze .
```

This writes the 5 text files without the heavier JSON and TOON outputs.

## Regenerate to a different directory

```bash
scaffoldr analyze . --full --output-dir /tmp/structure
```

Useful for comparing before/after a refactor: generate to a temporary directory and diff against the existing artifacts.

## When to regenerate

**Regenerate after:**
- Adding or removing Python source files
- Renaming modules or packages
- Changing class inheritance
- Adding or removing CLI entry points in pyproject.toml
- Significant refactoring (moving functions between modules)

**No need to regenerate after:**
- Changing function implementations (bodies, not signatures)
- Modifying docstrings or comments
- Updating dependencies in pyproject.toml (external deps are not tracked)
- Changing test files (scaffoldr only analyzes `src/` directories)

## Comparing structural changes

To see what changed structurally after a refactor:

```bash
# Before refactoring
scaffoldr analyze . --full --output-dir /tmp/before

# ... make changes ...

# After refactoring
scaffoldr analyze . --full --output-dir /tmp/after

# Compare
diff /tmp/before/structure_summary.txt /tmp/after/structure_summary.txt
diff /tmp/before/class_hierarchy.txt /tmp/after/class_hierarchy.txt
```

The diff will show new/removed classes, changed dependency edges, and shifted method counts.
