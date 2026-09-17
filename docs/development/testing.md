# Testing

Tests verify that code behaves as expected. Project-local unit/integration/contract/simulation tests remain with their owner; cross-project architecture, contract, and end-to-end tests live under root `tests/`.

```bash
pytest
pytest -m unit
pytest -m "not slow"
pytest PaperTrading/tests
pytest AiTrainer/tests
pytest DataCollector/tests
```

Markers include `unit`, `integration`, `contract`, `simulation`, `training`, `validation`, `e2e`, and `slow`. Coverage starts at a 70% repository baseline; meaningful tests matter more than mechanically inflating it. PaperTrading domain/application and shared contracts should trend toward especially strong coverage.
