# Timestamp semantics

External content preserves:

- `published_at`: when the publisher claims the content appeared.
- `received_at`: when this system first had access to it.
- `processed_at`: when normalized or derived output became usable.

All timestamps are timezone-aware and normalized to UTC at boundaries. Backtests use availability time—not publication time alone—because delayed collection and processing must not make information visible early. Market observations similarly carry an event/observation time and later may retain receipt time for latency analysis.
