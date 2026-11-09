# Verification

- Local skill validation: `python scripts/codex/validate_skills.py --path docs/codex/project-skills` -> 3 skills valid.
- Targeted R05 tests: 19 passed across indicators, macro context/ribbon and setup scoring.
- Full offline suite: `pytest -q` -> 153 passed.
- Targeted `ruff check` and `ruff format --check` on every R05 source/test file -> passed.
- Numeric fixtures cover SMA/EMA/RSI/ATR; invalid/unclosed/out-of-order data and warmup are explicit.
- Missing context, veto precedence, configurable thresholds, deterministic rank and BUY/SELL divergence are covered.
- Macro expiry, provenance, unknown degradation and accessible Qt rendering are covered.
- No authenticated IG call, dependency, database migration or order path was added.

Remaining boundary: no external macro/news/LLM provider and no invented concrete strategy formula. Repository-wide format check retains pre-existing unrelated differences; targeted R05 formatting is green.
