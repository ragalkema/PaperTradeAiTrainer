"""Preview or recover old interrupted news ingestion; no network calls."""

import argparse
import asyncio
import json

from data_collector.infrastructure.persistence.recovery import recover_pending_news
from data_collector.infrastructure.persistence.session import data_collector_session_factory

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    print(
        json.dumps(
            asyncio.run(recover_pending_news(data_collector_session_factory, apply=args.apply)),
            indent=2,
        )
    )
