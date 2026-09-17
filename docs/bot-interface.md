# Bot interface

Every strategy implements `TradingBot`: `reset`, `observe`, `decide`, and `on_trade_result`. The runtime supplies a normalized `MarketState`; the bot returns a `BotAction` (`BUY`, `SELL`, or `HOLD`); only the `PaperExchange` interprets that intent as a virtual order.

The interface deliberately excludes exchange clients, credentials, portfolio mutation, and wall-clock data access. A runtime can therefore execute Random, Buy-and-Hold, technical-analysis, XGBoost, PPO, SAC, news-sentiment, or hybrid bots under identical observations without changing the exchange.

Bots should be deterministic when supplied the same observations, configuration, state, and random seed. They may keep internal state, but `reset` must restore episode state. A future runtime should inject a read-only portfolio view separately when needed, record every observation/action pair, and validate that observations are available as of the simulation clock.

Actions express intent, not fills. Rejections, slippage, partial fills, fees, and eventual order types belong to the paper exchange and are reported through `TradeResult`.
