# Data Model: Custom Invalid Reasons

Feature: [spec.md](./spec.md) · Decisions: [research.md](./research.md)

## Invalid reason (conceptual)

| Attribute | Type | Rules |
|-----------|------|-------|
| `name` | str | Display name. Trimmed, inner whitespace collapsed; 1–60 chars; no `;`; no control characters. |
| `key` | str (derived) | `" ".join(name.split()).casefold()`; unique across defaults and custom reasons (hidden included). |
| `origin` | `default` \| `custom` | Defaults come from `InvalidReason`; custom from the catalogue file. |
| `hidden` | bool | Always `False` for defaults. Hidden custom reasons are not offered for new selections. |
| `created_at` | ISO-8601 UTC str | Custom only; creation order = list order in the file. |

Default reasons (fixed order, cannot be renamed or hidden): `Low lighting`,
`Too bright / overexposed`, `Out of focus / blurry`, `Invalid image content`.

## CustomReason (persisted)

```text
CustomReason(name: str, hidden: bool = False, created_at: str)
```

## ReasonCatalogue (persisted file + operations)

- **Location**: `CUSTOM_REASONS_FILE` env, default `<EVALUATIONS_DIR>/custom_reasons.json`.
  Format: [contracts/custom-reasons-file.md](./contracts/custom-reasons-file.md).
- **State read on demand**: every query/mutation re-reads the file (R3).
- **Derived views**:
  - `all_names()` → defaults + every custom (hidden included), in order.
  - `offered_names(selected=())` → defaults + visible custom + any hidden name in `selected`
    (so an image already evaluated with a hidden reason still shows it ticked).
  - `canonical(name)` → known display name with the same key, else `None`.
- **Mutations** (all validate per the name rules, raise `ReasonError(message)` with a
  plain-English message):
  - `add(name) -> str` — duplicate key → `"'<existing>' already exists."`
  - `rename(old, new) -> str` — `old` must be custom; `new` must be unique (except equal to
    `old`'s key, i.e. a pure case/spacing fix is allowed).
  - `set_hidden(name, hidden: bool)` — custom only.
  - `ensure(names) -> list[str]` — adds unknown, valid names (import); returns those added.
- **Load failure**: `load_error: str | None`; defaults still returned; file preserved and
  renamed to `custom_reasons.json.unreadable-<ts>` only on the next successful mutation.

## Evaluation (existing, changed)

| Field | Before | After |
|-------|--------|-------|
| `reasons` | `list[InvalidReason]` | `list[str]` — each passes the name format rules; duplicates (same key) removed keeping first; Invalid requires ≥ 1; Valid clears the list. |

Autosave JSON (`<form>__<data>.json`) is unchanged: `"reasons": ["Low lighting", ...]`.

## ImportResult (existing, extended)

| New field | Type | Meaning |
|-----------|------|---------|
| `new_reasons` | `list[str]` | Reasons added to the catalogue by this import. |
| `reasons_error` | `str \| None` | Set when the catalogue could not be written; evaluations were still merged. |

## State transitions (custom reason)

```text
(absent) --add / ensure--> visible --hide--> hidden --restore--> visible
visible|hidden --rename--> same state, new name (evaluations rewritten)
(no delete transition)
```
