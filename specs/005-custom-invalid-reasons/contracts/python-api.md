# Contract: Python API

New module `src/evaluate_kobo_form_images/reasons.py` (no Streamlit imports):

```python
MAX_REASON_LENGTH = 60
DEFAULT_REASONS: tuple[str, ...]          # InvalidReason values, fixed order

class ReasonError(ValueError):            # .message: plain English for the evaluator
    ...

def normalize_reason(name: str) -> str    # trimmed + collapsed whitespace + casefold
def clean_reason_name(name: str) -> str   # trimmed + collapsed; raises ReasonError on rule failure
def reason_widget_id(name: str) -> str    # sha1(normalize)[:10], for widget keys

@dataclass(frozen=True)
class CustomReason:
    name: str
    hidden: bool
    created_at: str

class ReasonCatalogue:
    def __init__(self, path: Path) -> None
    path: Path
    load_error: str | None                # set by the last read
    def custom(self) -> list[CustomReason]
    def all_names(self) -> list[str]
    def offered_names(self, selected: Iterable[str] = ()) -> list[str]
    def canonical(self, name: str) -> str | None
    def is_default(self, name: str) -> bool
    def add(self, name: str) -> str
    def rename(self, old: str, new: str) -> str
    def set_hidden(self, name: str, hidden: bool) -> None
    def ensure(self, names: Iterable[str]) -> list[str]

def catalogue_path(evaluations_dir: Path) -> Path   # honours CUSTOM_REASONS_FILE
def rename_reason_in_stores(directory: Path, old: str, new: str) -> int  # files rewritten
def report_reasons(catalogue: ReasonCatalogue | None, evaluations: Iterable[Evaluation]) -> list[str]
```

Changed signatures:

```python
# evaluation.py
Evaluation.reasons: list[str]            # format-validated names, deduplicated by key

# report.py
evaluation_row(record, evaluation, reasons: Sequence[str] = DEFAULT_REASONS) -> list[object]
evaluation_columns(reasons: Sequence[str] = DEFAULT_REASONS) -> list[str]
build_report(records, evaluations, *, evaluator="", include_pending=True,
             reasons: Sequence[str] | None = None) -> bytes   # None → report_reasons(None, …)
# EVALUATION_COLUMNS stays = evaluation_columns(DEFAULT_REASONS) for compatibility

# report_import.py
read_report(source, file_name, catalogue: ReasonCatalogue | None = None) -> ParsedReport
import_report(source, file_name, records, store,
              catalogue: ReasonCatalogue | None = None) -> ImportResult   # + new_reasons, reasons_error
```

`InvalidReason` stays in `evaluation.py` as the enum of defaults.
