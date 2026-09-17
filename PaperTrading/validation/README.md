# PaperTrading validation

Contracts reject non-positive/non-finite prices, negative volumes, crossed books, naive timestamps, and invalid quantities. The paper exchange validates non-negative balances, fee accounting, quote-value conservation, and asset conservation after execution. `scripts/validate.ps1` runs a deterministic BUY/SELL round-trip system check to detect impossible state or simulator exploitation regressions.
