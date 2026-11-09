# Findings

- Indicator/strategy/scanner and macro-context services are placeholders.
- The existing macro ribbon is static UI and is not yet fed by a domain state.
- R05 requires advisory output only; every future ticket still passes the independent Risk Engine.
- No external macro/news/LLM provider is required to satisfy the offline R05 acceptance criteria.
- The implemented initial numeric set is SMA, EMA, RSI and ATR; unsupported formulas are not guessed.
- The static ribbon boundary now accepts normalized `MacroRibbonState`; missing context remains visibly gray/unknown.
- No scanner or ribbon code imports a broker adapter or creates an order command.
