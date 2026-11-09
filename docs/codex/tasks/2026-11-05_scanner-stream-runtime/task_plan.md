# Scanner stream runtime

## Skills

- `python-planning-with-files`
- `python-tdd`
- `python-pyqt-threading`
- `python-data-pipeline`
- `python-review-diff`

## Objective

Wire the five human-approved IG reference markets, plus the selected product's exact reference when
different, into the existing Qt read-only Lightstreamer runtime.

## Boundaries

- Session memory only; no REST history or persistent candle cache.
- Maximum six exact M1 chart items in one subscription.
- Background references must not replace or redraw the selected chart.
- No ticket, order, IG mutation, AUTO or LIVE-trading activation.
