# entry_points.txt

Maps CLI command names to the code they invoke. Shows which function handles each command, what it calls directly, and what modules it imports.

## Format

Header line:

```
# Entry Points
```

Each entry point has 1-3 lines:

```
  <command-name> -> <module>:<function>
    calls: <func1>, <func2>, ...
    deps: <module1>, <module2>, ...
```

### Fields

| Line | Description |
|------|-------------|
| `<command-name>` | The CLI command as defined in `[project.scripts]` in pyproject.toml |
| `<module>:<function>` | The Python module path and function name that handles the command. Module paths have the root package prefix stripped. |
| `calls:` | Functions called directly by the entry point function (1-level deep, up to 15). Built-in functions (`len`, `str`, `print`, `isinstance`, etc.) are filtered out. This line is omitted if the function makes no interesting calls. |
| `deps:` | Modules imported at the top of the entry point's module file (up to 8). Root package prefixes are stripped. This line is omitted if there are no project-internal imports. |

### Not-found entries

If the entry point's module could not be parsed (missing file, syntax error), the line reads:

```
  <command-name>: [NOT FOUND] <module>:<function>
```

## Example

```
# Entry Points

  scaffoldr -> __main__:main
    calls: _analyze, parse_args
    deps: cli.output, cli.parser, core.graphs, langs
```

This tells you: the `scaffoldr` command runs `__main__:main`, which calls `parse_args` and `_analyze`. The module depends on `cli.output`, `cli.parser`, `core.graphs`, and `langs`.

## Discovery

Entry points are discovered from `[project.scripts]` in pyproject.toml files. In a uv workspace, each member package's pyproject.toml is scanned.
