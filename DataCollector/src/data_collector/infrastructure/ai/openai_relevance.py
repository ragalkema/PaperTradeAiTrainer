"""Strict-schema OpenAI relevance assessment behind a provider-neutral port."""

import json
from decimal import Decimal
from typing import Any

import httpx

from data_collector.application.services.reference_dataset import (
    ReferenceCandidate,
    RelevanceAssessment,
)

SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "usefulness": {"type": "number", "minimum": 0, "maximum": 1},
        "relevance": {"type": "number", "minimum": 0, "maximum": 1},
        "importance": {"type": "number", "minimum": 0, "maximum": 1},
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        "event_type": {"type": "string"},
        "explanation": {"type": "string"},
    },
    "required": [
        "usefulness",
        "relevance",
        "importance",
        "confidence",
        "event_type",
        "explanation",
    ],
    "additionalProperties": False,
}


class OpenAIRelevanceAssessor:
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required for AI assessment")
        self._model = model
        self._client = client or httpx.AsyncClient(
            base_url="https://api.openai.com/v1",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=60,
        )
        self._owns_client = client is None

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def assess(self, candidate: ReferenceCandidate) -> RelevanceAssessment:
        response = await self._client.post(
            "/responses",
            json={
                "model": self._model,
                "store": False,
                "input": [
                    {
                        "role": "system",
                        "content": (
                            "Assess crypto-market research value using only the supplied text. "
                            "Do not infer price impact from future data. Low-value spam, vague "
                            "opinions and unrelated content must receive low usefulness."
                        ),
                    },
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "source_type": candidate.source_type,
                                "source": candidate.source,
                                "author": candidate.author,
                                "asset": candidate.asset,
                                "text": candidate.text,
                            },
                            ensure_ascii=False,
                        ),
                    },
                ],
                "text": {
                    "format": {
                        "type": "json_schema",
                        "name": "market_relevance_assessment",
                        "strict": True,
                        "schema": SCHEMA,
                    }
                },
            },
        )
        response.raise_for_status()
        payload = response.json()
        data = json.loads(_output_text(payload))
        return RelevanceAssessment(
            _score(data, "usefulness"),
            _score(data, "relevance"),
            _score(data, "importance"),
            _score(data, "confidence"),
            str(data["event_type"]),
            str(data["explanation"]),
            f"openai_responses:{self._model}:market_relevance_v1",
        )


def _output_text(payload: dict[str, Any]) -> str:
    for output in payload.get("output", []):
        if output.get("type") != "message":
            continue
        for content in output.get("content", []):
            if content.get("type") == "output_text" and content.get("text"):
                return str(content["text"])
    raise ValueError("OpenAI response contained no structured output text")


def _score(payload: dict[str, Any], name: str) -> Decimal:
    value = Decimal(str(payload[name]))
    if not Decimal("0") <= value <= Decimal("1"):
        raise ValueError(f"{name} must be between zero and one")
    return value
