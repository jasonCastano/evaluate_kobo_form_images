# Contract: User interface

## Evaluation panel (inside the existing evaluation form)

```text
Is the image valid?   ( ) Valid  ( ) Invalid
If invalid, select at least one reason:
  [ ] Low lighting
  [ ] Too bright / overexposed
  [ ] Out of focus / blurry
  [ ] Invalid image content
  [ ] Finger over the lens          ← custom reasons, creation order
New reason  [______________________]  (max 60 characters)
[➕ Add reason]  [💾 Save]  [💾 Save & next]
```

- **➕ Add reason**: validates the text; on success the reason is stored, appears in the list
  **already ticked** for the current image, the text box is cleared and a toast says
  `Added reason 'Finger over the lens'.`; the evaluation is *not* saved. On failure an
  error is shown under the form (`'Low lighting' already exists.`, `Enter a reason name.`,
  `Reason names can have at most 60 characters.`, `Reason names cannot contain ';'.`).
  Verdict, ticked reasons and comments are preserved in all cases.
- Hidden custom reasons are listed only when the current image's saved evaluation uses them.
- A warning is shown once per session when the custom reasons file is unreadable.

## Sidebar: "Manage invalid reasons" expander (P3)

- Default reasons listed read-only with a "default" tag.
- Each custom reason: name, a text input + **Rename** button, and **Hide** / **Restore**.
- Rename confirms with `Renamed 'A' to 'B' in N saved evaluation file(s).`
- Hidden reasons are shown greyed with "(hidden)".

## Report import summary

Adds a line when applicable: `Added invalid reasons: Finger over the lens, Wrong plant part.`
