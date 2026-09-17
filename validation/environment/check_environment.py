"""Validate the minimum local runtime without exposing environment values."""

import sys


def environment_violations() -> list[str]:
    """Return unsupported runtime conditions."""
    if sys.version_info < (3, 12):  # noqa: UP036 - this script validates external runtimes
        return ["Python 3.12 or newer is required"]
    return []


if __name__ == "__main__":
    found = environment_violations()
    if found:
        raise SystemExit("\n".join(found))
    print("Environment validation passed.")
