"""Deterministic, extensible alias-based crypto asset detection."""

import re
from dataclasses import dataclass, field
from decimal import Decimal

DEFAULT_ALIASES: dict[str, tuple[str, ...]] = {
    "BTC": ("bitcoin", "btc", "xbt"),
    "ETH": ("ethereum", "ether", "eth"),
    "SOL": ("solana", "sol"),
}


@dataclass(slots=True)
class AssetDetector:
    aliases: dict[str, tuple[str, ...]] = field(default_factory=lambda: dict(DEFAULT_ALIASES))

    def detect(self, title: str, summary: str | None = None) -> dict[str, Decimal]:
        title_text = title.casefold()
        combined = f"{title} {summary or ''}".casefold()
        scores: dict[str, Decimal] = {}
        for asset, aliases in self.aliases.items():
            title_hits = sum(_contains(title_text, alias) for alias in aliases)
            all_hits = sum(_contains(combined, alias) for alias in aliases)
            if all_hits:
                score = Decimal("0.6") + Decimal("0.2") * min(title_hits, 1)
                score += Decimal("0.05") * min(all_hits - min(title_hits, all_hits), 4)
                scores[asset] = min(score, Decimal("1"))
        return scores


def _contains(text: str, alias: str) -> bool:
    return re.search(rf"(?<![\w]){re.escape(alias.casefold())}(?![\w])", text) is not None
