# Research persistence and queries

PaperTrading owns the relational schema and repository ports for paper sessions, bot definitions,
session participants, portfolio snapshots, positions, trades, decisions, and experiments.
AiTrainer knows only an optional runner observer. Dashboard consumes bounded query results through
an infrastructure adapter and never imports SQLAlchemy in its application or presentation layers.

```text
AiTrainer MultiBotRunner -> RunObserver -> ResearchRunRecorder
                                      -> ResearchWritePort -> PostgreSQL
DashboardDataPort <- LiveDashboardRepository <- ResearchQueryPort <- PostgreSQL
```

Each `SessionBot` has its own starting balance and paper account. The runner broadcasts the same
ordered `MarketState` to all participants. Bot definitions are reusable identities; SessionBot is
the run-specific participant.

Financial fields use `NUMERIC(38,18)`. Snapshot, trade, decision, and position observations are
append-oriented. Queries have explicit limits. Default snapshots are sampled every five seconds;
HOLD decisions are not persisted unless enabled with a separate sampling interval.

## Point-in-time safety

`DecisionContext` is written from the market and portfolio state present when `decide()` ran.
Its market timestamp must be at or before the decision timestamp. Feature/news/social references
are optional identifiers only; no future dataset may be joined later and represented as original
decision input.

## Metrics

Return, realized/unrealized P&L, fees, win/loss statistics, profit factor, and drawdown are computed
in the PaperTrading application layer. Maximum and current drawdown use ordered equity snapshots,
not individual trade P&L. Sharpe, Sortino, and Calmar are intentionally absent because sampling and
annualization assumptions have not been defined.
