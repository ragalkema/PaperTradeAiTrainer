"""Build auditable, deduplicated relevance datasets without inventing samples."""

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import Protocol


class UsefulnessBand(StrEnum):
    INFLUENTIAL = "influential"
    REVIEW = "review"
    LOW_VALUE = "low_value"


@dataclass(frozen=True, slots=True)
class ReferenceCandidate:
    candidate_id: str
    source_type: str
    source: str
    author: str | None
    text: str
    occurred_at: datetime
    asset: str
    relevance: Decimal
    importance: Decimal
    novelty: Decimal
    influence: Decimal
    sentiment: Decimal


@dataclass(frozen=True, slots=True)
class RelevanceAssessment:
    usefulness: Decimal
    relevance: Decimal
    importance: Decimal
    confidence: Decimal
    event_type: str
    explanation: str
    label_origin: str

    @property
    def band(self) -> UsefulnessBand:
        if self.usefulness >= Decimal("0.70"):
            return UsefulnessBand.INFLUENTIAL
        if self.usefulness <= Decimal("0.35"):
            return UsefulnessBand.LOW_VALUE
        return UsefulnessBand.REVIEW


class RelevanceAssessor(Protocol):
    async def assess(self, candidate: ReferenceCandidate) -> RelevanceAssessment: ...


class ExistingIntelligenceAssessor:
    """Weak supervision baseline from point-in-time intelligence only."""

    version = "existing_online_intelligence_v1"

    async def assess(self, candidate: ReferenceCandidate) -> RelevanceAssessment:
        usefulness = min(
            Decimal("1"),
            candidate.relevance * Decimal("0.35")
            + candidate.importance * Decimal("0.35")
            + candidate.novelty * Decimal("0.15")
            + candidate.influence * Decimal("0.15"),
        )
        return RelevanceAssessment(
            usefulness,
            candidate.relevance,
            candidate.importance,
            Decimal("0.55"),
            "existing_classification",
            "Weak label composed from versioned online scores; requires human/LLM review.",
            self.version,
        )


@dataclass(frozen=True, slots=True)
class DatasetTargets:
    total: int = 10_000
    influential: int = 2_000
    low_value: int = 4_000

    def __post_init__(self) -> None:
        if min(self.total, self.influential, self.low_value) < 0:
            raise ValueError("dataset targets cannot be negative")
        if self.influential + self.low_value > self.total:
            raise ValueError("band targets cannot exceed total target")


@dataclass(frozen=True, slots=True)
class DatasetBuildReport:
    selected: int
    influential: int
    review: int
    low_value: int
    shortfall: int


class ReferenceDatasetBuilder:
    async def build(
        self,
        candidates: tuple[ReferenceCandidate, ...],
        assessor: RelevanceAssessor,
        targets: DatasetTargets | None = None,
    ) -> tuple[tuple[dict[str, object], ...], DatasetBuildReport]:
        targets = targets or DatasetTargets()
        unique = {item.candidate_id: item for item in candidates}
        assessed = [(item, await assessor.assess(item)) for item in unique.values()]
        buckets = {
            band: sorted(
                ((item, result) for item, result in assessed if result.band is band),
                key=lambda pair: (-pair[1].usefulness, pair[0].candidate_id),
            )
            for band in UsefulnessBand
        }
        chosen = buckets[UsefulnessBand.INFLUENTIAL][: targets.influential]
        chosen += buckets[UsefulnessBand.LOW_VALUE][: targets.low_value]
        review_target = targets.total - targets.influential - targets.low_value
        chosen += buckets[UsefulnessBand.REVIEW][:review_target]
        if len(chosen) < targets.total:
            selected_ids = {item.candidate_id for item, _ in chosen}
            remainder = sorted(
                (pair for pair in assessed if pair[0].candidate_id not in selected_ids),
                key=lambda pair: (-pair[1].confidence, pair[0].candidate_id),
            )
            chosen += remainder[: targets.total - len(chosen)]
        rows = tuple(self._row(item, result) for item, result in chosen)
        counts = {band: sum(row["band"] == band.value for row in rows) for band in UsefulnessBand}
        return rows, DatasetBuildReport(
            len(rows),
            counts[UsefulnessBand.INFLUENTIAL],
            counts[UsefulnessBand.REVIEW],
            counts[UsefulnessBand.LOW_VALUE],
            max(0, targets.total - len(rows)),
        )

    @staticmethod
    def write_jsonl(rows: tuple[dict[str, object], ...], path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="\n") as output:
            for row in rows:
                output.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    @staticmethod
    def _row(candidate: ReferenceCandidate, assessment: RelevanceAssessment) -> dict[str, object]:
        row = asdict(candidate)
        row["occurred_at"] = candidate.occurred_at.isoformat()
        for name in ("relevance", "importance", "novelty", "influence", "sentiment"):
            row[name] = str(row[name])
        row.update(
            {
                "band": assessment.band.value,
                "usefulness": str(assessment.usefulness),
                "assessment_relevance": str(assessment.relevance),
                "assessment_importance": str(assessment.importance),
                "assessment_confidence": str(assessment.confidence),
                "event_type": assessment.event_type,
                "explanation": assessment.explanation,
                "label_origin": assessment.label_origin,
            }
        )
        return row
