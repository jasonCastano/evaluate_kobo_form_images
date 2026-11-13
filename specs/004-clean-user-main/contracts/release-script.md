# Contract: `scripts/release_to_main.py` (developer-only)

Standard library only; runs with the project interpreter
(`.venv/Scripts/python.exe scripts/release_to_main.py …`). Never pushes, never force-pushes,
never touches untracked or ignored files.

## Usage

```text
python scripts/release_to_main.py [--source REF] [--target REF] [--branch NAME] [--check]
```

| Option | Default | Meaning |
|--------|---------|---------|
| `--source` | `origin/develop` | Ref whose allowed paths are published |
| `--target` | `origin/main` | Ref the release branch starts from |
| `--branch` | `release/<YYYYMMDD-HHMM>` | Name of the local release branch to create |
| `--check` | off | Read-only: report non-allowed files on `--target` and the pending diff; create nothing |

## Behaviour

1. Refuses to run if the working tree has tracked changes (`git status --porcelain
   --untracked-files=no` not empty) → exit 2, message "Commit or stash your changes first."
2. `git fetch origin` (skipped with `--no-fetch`, used by tests).
3. Normal mode: `git switch -c <branch> <target>`; remove every tracked file from index and
   working tree; for each published path of `<source>` (`git ls-tree -r --name-only <source>`
   filtered by allowlist/denylist) `git checkout <source> -- <paths>`; `git add -A` restricted to
   those paths; if nothing changed → print "main is already up to date with <source>." and exit 0
   (branch deleted); else commit with message
   `release: sync user files from <source short sha>` using the local git identity (no trailers).
4. Prints `git diff --name-status <target> HEAD` and the next steps:
   `git push -u origin <branch>` and `gh pr create --base main --head <branch> …`.
5. `--check`: prints "Not allowed on <target>:" + list (exit 1 if any), and "Pending release
   diff:" + list.

## Public functions (tested)

```python
ALLOWLIST: tuple[str, ...]
DENYLIST: tuple[str, ...]
def is_published(path: str) -> bool        # allowlist ∧ ¬denylist, POSIX paths, ** globs
def published_paths(paths: Iterable[str]) -> list[str]
def main(argv: Sequence[str] | None = None) -> int
```
