"""Publish the user-facing files of ``develop`` to ``main`` (developer-only tool).

``main`` is the user branch: it only contains what a user needs to install and run the app.
``develop`` is the full project. This script builds a ``release/<stamp>`` branch from ``main``
whose tree is exactly the **published** subset of ``develop`` (allowlist minus denylist), commits
it with your local Git identity and prints the diff. It never pushes; open the pull request to
``main`` yourself (see DEVELOPMENT.md).

Usage::

    .venv/Scripts/python.exe scripts/release_to_main.py            # create the release branch
    .venv/Scripts/python.exe scripts/release_to_main.py --check    # read-only verification
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections.abc import Iterable, Sequence
from datetime import datetime
from functools import cache

ALLOWLIST: tuple[str, ...] = (
    "src/**",
    "tests/**",
    ".github/workflows/ci.yml",
    ".streamlit/config.toml",
    "pyproject.toml",
    "uv.lock",
    ".python-version",
    ".env.example",
    ".gitignore",
    ".gitattributes",
    ".editorconfig",
    ".pre-commit-config.yaml",
    "Makefile",
    "LICENSE",
    "README.md",
)
DENYLIST: tuple[str, ...] = (
    "tests/test_release_to_main.py",
    "**/__pycache__/**",
)
_CHUNK = 100


@cache
def _compile(pattern: str) -> re.Pattern[str]:
    """Translate a glob with ``**`` (any depth) and ``*`` (one segment) into a regex."""
    out = ""
    index = 0
    while index < len(pattern):
        if pattern.startswith("**/", index):
            out += "(?:.*/)?"
            index += 3
        elif pattern.startswith("**", index):
            out += ".*"
            index += 2
        elif pattern[index] == "*":
            out += "[^/]*"
            index += 1
        else:
            out += re.escape(pattern[index])
            index += 1
    return re.compile(f"^{out}$")


def _matches(path: str, patterns: Iterable[str]) -> bool:
    return any(_compile(pattern).match(path) for pattern in patterns)


def is_published(path: str) -> bool:
    """Return whether a repository-relative POSIX path belongs on ``main``."""
    path = path.replace("\\", "/").removeprefix("./")
    return _matches(path, ALLOWLIST) and not _matches(path, DENYLIST)


def published_paths(paths: Iterable[str]) -> list[str]:
    """Filter ``paths`` to the published ones, keeping their order."""
    return [path for path in paths if is_published(path)]


# --------------------------------------------------------------------------- git helpers
def _git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args], check=check, text=True, capture_output=True, encoding="utf-8"
    )


def _tree(ref: str) -> dict[str, str]:
    """Map path -> blob id for every file of ``ref``."""
    entries: dict[str, str] = {}
    for line in _git("ls-tree", "-r", "-z", ref).stdout.split("\0"):
        if not line:
            continue
        meta, path = line.split("\t", 1)
        entries[path] = meta.split()[2]
    return entries


def _pending(source: str, target: str) -> list[str]:
    """Name-status lines of the release that would be produced (A/M/D)."""
    wanted = {p: blob for p, blob in _tree(source).items() if is_published(p)}
    current = _tree(target)
    lines = [f"A\t{p}" for p in sorted(wanted) if p not in current]
    lines += [f"M\t{p}" for p in sorted(wanted) if p in current and current[p] != wanted[p]]
    lines += [f"D\t{p}" for p in sorted(current) if p not in wanted]
    return lines


def _check(source: str, target: str) -> int:
    not_allowed = [p for p in sorted(_tree(target)) if not is_published(p)]
    print(f"Not allowed on {target}:")
    print("\n".join(f"  {p}" for p in not_allowed) or "  (none)")
    pending = _pending(source, target)
    print(f"Pending release diff ({source} -> {target}):")
    print("\n".join(f"  {line}" for line in pending) or "  (none)")
    return 1 if not_allowed else 0


def _release(source: str, target: str, branch: str) -> int:
    original = _git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    paths = published_paths(_tree(source))
    source_sha = _git("rev-parse", "--short", source).stdout.strip()
    _git("switch", "-q", "-c", branch, target)
    _git("rm", "-r", "-q", "--ignore-unmatch", "--", ".")
    for start in range(0, len(paths), _CHUNK):
        _git("checkout", source, "--", *paths[start : start + _CHUNK])
    if _git("diff", "--cached", "--quiet", check=False).returncode == 0:
        _git("reset", "-q", "--hard", "HEAD")
        _git("switch", "-q", original)
        _git("branch", "-q", "-D", branch)
        print(f"main is already up to date with {source}.")
        return 0
    _git("commit", "-q", "-m", f"release: sync user files from {source} @ {source_sha}")
    print(f"Created {branch} from {target} with the published files of {source} @ {source_sha}:")
    print(_git("diff", "--name-status", target, "HEAD").stdout.rstrip())
    print("\nNext steps:")
    print(f"  git push -u origin {branch}")
    print(
        f'  gh pr create --base main --head {branch} --title "release: '
        f'{datetime.now():%Y-%m-%d}" --body "<summary of changes>"'
    )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Command-line entry point. Returns the process exit code."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--source", default="origin/develop", help="ref to publish from")
    parser.add_argument("--target", default="origin/main", help="ref the release starts from")
    parser.add_argument("--branch", default=f"release/{datetime.now():%Y%m%d-%H%M}")
    parser.add_argument("--check", action="store_true", help="read-only verification")
    parser.add_argument("--no-fetch", action="store_true", help="do not run 'git fetch origin'")
    args = parser.parse_args(argv)

    status = _git("status", "--porcelain", "--untracked-files=no").stdout.strip()
    if status and not args.check:
        print("Commit or stash your changes first.", file=sys.stderr)
        return 2
    if not args.no_fetch:
        _git("fetch", "-q", "origin")
    if args.check:
        return _check(args.source, args.target)
    return _release(args.source, args.target, args.branch)


if __name__ == "__main__":
    sys.exit(main())
