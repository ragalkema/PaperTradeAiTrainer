# Shared contracts

This package contains only stable, framework-free definitions genuinely exchanged between bounded contexts. It must not contain database adapters, business workflows, provider clients, AI models, or miscellaneous utilities.

Current contracts cover `MarketState`, `BotAction`, and `TradeResult` communication between PaperTrading and AiTrainer.
