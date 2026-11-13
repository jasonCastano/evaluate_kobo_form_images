# Contract: Python module interface

Business logic stays out of `app.py` (Principle IV).

## `evaluate_kobo_form_images.report` (extended)

```python
class ReportSaveError(Exception):
    path: Path
    reason: str                      # plain English (research R3)

@dataclass(frozen=True)
class ReportOutput:
    path: Path                       # absolute
    rows: int

def report_file_name(form_file: str, now: datetime) -> str
    # "image_evaluation__<form stem>__YYYYMMDD-HHMMSS.xlsx"

def save_report(
    content: bytes, folder: str | Path, form_file: str, *,
    now: datetime | None = None, timeout: float = 30.0,
) -> Path
    # creates folder, picks a non-existing name (-2, -3, ...), atomic write,
    # returns absolute path; raises ReportSaveError
```

`build_report(...)` keeps its signature and output format (FR-006).

## `evaluate_kobo_form_images.report_import` (new)

```python
REQUIRED_COLUMNS: tuple[str, ...]    # see contracts/report-format.md

class ReportImportError(Exception):  # whole file rejected (FR-013)
    message: str

@dataclass(frozen=True)
class RejectedRow:
    row_number: int
    reason: str

@dataclass
class ImportResult:                  # fields per data-model.md
    ...

def read_report(source: str | Path | BinaryIO, file_name: str) -> ParsedReport
    # parses + validates rows; raises ReportImportError on missing sheet/columns

def import_report(
    source: str | Path | BinaryIO, file_name: str,
    records: Sequence[ImageRecord], store: EvaluationStore,
) -> ImportResult
    # read → match (key, then URL+question) → store.merge → resume position
```

## `evaluate_kobo_form_images.evaluation` (extended)

```python
@dataclass(frozen=True)
class MergeResult:
    added: int
    updated: int
    unchanged: int

class EvaluationStore:
    def merge(self, evaluations: Iterable[Evaluation]) -> MergeResult
        # R7 rule; single save(); never deletes
```

## Resume helper

```python
def resume_target(
    records: Sequence[ImageRecord], store: EvaluationStore, last_key: str | None
) -> str | None
    # first pending after last_key (export order), else first pending, else None
```
