# OpenCode rule: tgrep

This rule tells the OpenCode agent to use `tgrep` (Microsoft trigram-indexed grep) for fast
regex and symbol searches over the code.

## Guidelines for the agent

1. **Use `tgrep` instead of `grep` or `find`** when available (pre-computed trigram index in
   `.tgrep/`).
2. **Execution rules:**
   - Always put `--` before the pattern: `tgrep -- "pattern" .`
   - Use `-F` for literal symbols: `tgrep -F -- "scan_export" .`
   - Filter by type or path: `tgrep -t py -- "class " .`, `tgrep -g "src/**" -- "keyword" .`
   - List matching files only: `tgrep -l -- "import streamlit" .`
   - Re-index after large changes: `tgrep index .`
3. **Fallback:** if `tgrep` is not installed, use `rg`/`grep` normally.
