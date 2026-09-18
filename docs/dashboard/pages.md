# Dashboard pages and data flow

- **Overview**: live market status plus aggregate values when supplied.
- **Markets**: current public price/book and bounded candle history.
- **Bots / Experiments / Trades**: empty until persisted query data exists.
- **News / Social**: empty until normalized DataCollector output exists.
- **Data / System**: actual adapter states; unavailable telemetry remains `N/A`.
- **Training**: future boundary with controls disabled.
- **Settings**: safe external configuration; no secret display or storage.

Widgets receive a bounded `DashboardSnapshot`. No widget invokes DataCollector, AiTrainer,
PaperTrading, or Bitvavo directly.
