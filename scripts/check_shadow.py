"""Read-only journal audit, optionally saved for comparing process restarts."""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from ai_trainer.infrastructure.models.shadow_status import journal_status


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--journal", type=Path, default=Path("experiments/results/content-shadow.db")
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = journal_status(args.journal, datetime.now(UTC))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with args.output.open("x", encoding="utf-8") as stream:
            json.dump(report, stream, indent=2)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
