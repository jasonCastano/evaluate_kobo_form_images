"""Tests for the developer-only release script (scripts/release_to_main.py).

This file is denylisted from releases, so it never reaches the user-facing ``main`` branch.
Git operations run in a temporary repository; the real repository is never touched.
"""

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "release_to_main.py"
pytestmark = pytest.mark.skipif(not SCRIPT.exists(), reason="developer-only script")


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("release_to_main", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def release() -> ModuleType:
    return _load()


PUBLISHED = [
    "src/evaluate_kobo_form_images/app.py",
    "tests/test_report.py",
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
]
NOT_PUBLISHED = [
    "tests/test_release_to_main.py",
    "src/x/__pycache__/a.pyc",
    "CONSTITUTION.md",
    "AGENTS.md",
    "CLAUDE.md",
    "CONTRIBUTING.md",
    "CODE_OF_CONDUCT.md",
    "DEVELOPMENT.md",
    "docs/README.md",
    "specs/001-x/spec.md",
    ".specify/memory/constitution.md",
    ".claude/settings.json",
    ".opencode/rules/tgrep.md",
    "scripts/release_to_main.py",
    ".github/workflows/labels.yml",
    ".github/labels.yml",
    ".github/pull_request_template.md",
    ".github/ISSUE_TEMPLATE/bug_report.yml",
    "newfile.txt",
]


@pytest.mark.parametrize("path", PUBLISHED)
def test_user_files_are_published(release: ModuleType, path: str) -> None:
    assert release.is_published(path)


@pytest.mark.parametrize("path", NOT_PUBLISHED)
def test_developer_files_are_not_published(release: ModuleType, path: str) -> None:
    assert not release.is_published(path)


def test_paths_are_normalized(release: ModuleType) -> None:
    assert release.is_published("./.github/workflows/ci.yml")
    assert release.is_published("src\evaluate_kobo_form_images\app.py")
    assert not release.is_published("./CLAUDE.md")


def test_published_paths_filters_and_keeps_order(release: ModuleType) -> None:
    assert release.published_paths(["CLAUDE.md", "src/a.py", "specs/x.md", "README.md"]) == [
        "src/a.py",
        "README.md",
    ]


# --------------------------------------------------------------------------- temp git repo
def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=repo, check=True, text=True, capture_output=True, encoding="utf-8"
    )
    return result.stdout


def _write(repo: Path, path: str, text: str) -> None:
    target = repo / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """main: README, CONSTITUTION, src/a.py — develop: + specs/s.md, changed a.py, new b.py."""
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.name", "Test Maintainer")
    _git(root, "config", "user.email", "maintainer@example.org")
    _git(root, "config", "commit.gpgsign", "false")
    _write(root, "README.md", "readme\n")
    _write(root, "CONSTITUTION.md", "rules\n")
    _write(root, "src/a.py", "a = 1\n")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "init")
    _git(root, "switch", "-q", "-c", "develop")
    _write(root, "specs/s.md", "spec\n")
    _write(root, "src/a.py", "a = 2\n")
    _write(root, "src/b.py", "b = 1\n")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "work")
    monkeypatch.chdir(root)
    return root


def _args(*extra: str) -> list[str]:
    return ["--source", "develop", "--target", "main", "--no-fetch", *extra]


def test_release_publishes_only_allowed_files(release: ModuleType, repo: Path) -> None:
    # Act
    code = release.main(_args("--branch", "release/test"))

    # Assert
    assert code == 0
    assert _git(repo, "rev-parse", "--abbrev-ref", "HEAD").strip() == "release/test"
    files = set(_git(repo, "ls-tree", "-r", "--name-only", "HEAD").split())
    assert files == {"README.md", "src/a.py", "src/b.py"}
    assert (repo / "src/a.py").read_text(encoding="utf-8") == "a = 2\n"
    message = _git(repo, "log", "-1", "--format=%B")
    assert message.startswith("release: sync user files from develop")
    assert "co-authored-by" not in message.lower()


def test_release_with_nothing_new_creates_no_commit(
    release: ModuleType, repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    release.main(_args("--branch", "release/one"))
    head = _git(repo, "rev-parse", "HEAD")

    code = release.main(
        ["--source", "develop", "--target", "release/one", "--no-fetch", "--branch", "release/two"]
    )

    assert code == 0
    assert "already up to date" in capsys.readouterr().out
    assert _git(repo, "rev-parse", "release/one") == head
    assert "release/two" not in _git(repo, "branch", "--list")


def test_check_reports_non_allowed_files(
    release: ModuleType, repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = release.main(_args("--check"))

    out = capsys.readouterr().out
    assert code == 1
    assert "CONSTITUTION.md" in out
    assert "src/b.py" in out  # pending addition


def test_refuses_with_tracked_changes(release: ModuleType, repo: Path) -> None:
    _write(repo, "src/a.py", "a = 99\n")
    assert release.main(_args("--branch", "release/x")) == 2


def test_untracked_local_data_is_untouched(release: ModuleType, repo: Path) -> None:
    _write(repo, "data/x.xlsx", "field data")

    release.main(_args("--branch", "release/data"))

    assert (repo / "data/x.xlsx").read_text(encoding="utf-8") == "field data"
