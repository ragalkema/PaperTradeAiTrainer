# DataCollector architecture

DataCollector owns external textual acquisition, immutable raw capture, normalization, and future lightweight NLP preprocessing. Provider code belongs in infrastructure adapters for official news APIs, RSS, social APIs, or—only where appropriate and permitted—scrapers. Application use cases coordinate ports; domain entities describe source-neutral content.

It emits normalized data through shared schemas or future messaging/API adapters. It does not import AiTrainer, PaperTrading internals, or model code.
