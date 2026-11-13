# Phase 1 Data Model: README structure and repository state

**Feature**: [spec.md](./spec.md) · **Research**: [research.md](./research.md)

This feature has no runtime data. Its "entities" are the README sections (with the content each
must carry) and the repository/PR states.

## README sections

| # | Section (heading) | Must contain | Spec |
|---|-------------------|--------------|------|
| 1 | Overview | One-paragraph purpose; link to CONSTITUTION | — |
| 2 | Table of contents | Links to every section below | FR-009 |
| 3 | Features | Table: any XLSForm, any Kobo export, no image lost, Kobo sign-in, fast review, autosave, local report, resume from report | FR-009 |
| 4 | How it works | Mermaid flow (form + export → image records → sign-in → evaluate → autosave → report → import/resume); short explanation of image discovery (`<header>_URL` columns, name/label matching, unmapped columns) and of storage (autosave JSON per form+export) | FR-001 |
| 5 | Getting started | Prerequisites; install (`make dev` / uv); optional `.env`; start (exe / `make run`); global `UV_PROJECT_ENVIRONMENT` note | FR-008, edge cases |
| 6 | Using the interface | Sidebar map; numbered walkthrough: 1 form, 2 data, 3 Kobo account, evaluator name, counters/progress, filters, navigation (First, Previous, Image #, Next, Next pending), image area + messages, details + "All data of this row", evaluation form (Valid/Invalid, 4 reasons, comments, Save, Save & next, Clear), 4 Report | FR-002, FR-003 |
| 7 | Kobo account | Server selection (Global, EU, Custom…); username & password; API key tab and where to find the key; SSO / two-factor; `.env` auto sign-in; sign out; privacy guarantees; mismatch warning | FR-004 |
| 8 | Reports: export and resume | Save to folder; naming rule; include pending; import steps; summary items (restored / added / updated / unchanged / not matched / rejected / complete); merge rule; resume position; "already imported" | FR-005 |
| 9 | Excel report reference | Sheets `Evaluations`, `Summary by question`, `Metadata`; key columns; columns required for re-import | FR-006 |
| 10 | Configuration | `KOBO_API_TOKEN`, `KOBO_FORMS_DIR`, `KOBO_DATA_DIR`, `EVALUATIONS_DIR`, `IMAGE_CACHE_DIR`, `REPORTS_DIR` with defaults | FR-008 |
| 11 | Troubleshooting | Table message → cause → what to do (see contracts/readme-content.md) | FR-007 |
| 12 | Quality and automation | `make` targets + non-make equivalents | edge cases |
| 13 | Repository structure | Includes `kobo_auth.py`, `report_import.py`, `exports/`, `specs/` | FR-009 |
| 14 | Contributing / License | Spec Kit workflow pointer; human-authorship rule; MIT | — |

Validation rules: English only; no real field data, tokens or personal names (FR-010); every
quoted UI string exists in `src/` (R4); every internal link resolves.

## Repository / PR state transitions

```text
#1 OPEN (001 → main) ──merge (merge commit, delete branch)──► MERGED
#2 OPEN (002 → 001) ──auto-retarget──► OPEN (002 → main) ──CI green──► merge ──► MERGED
main @ cbf2d47 ─────────────────────────────────────────────► main contains 001 + 002
003 branch from updated main ──PR (README + spec 003)──► CI green ──► MERGED (maintainer)
```

Guards: CI green before each merge (FR-014); no force-push; no direct push to `main` (FR-012).
