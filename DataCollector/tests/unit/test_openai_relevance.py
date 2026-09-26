import asyncio
import json
from datetime import UTC, datetime
from decimal import Decimal

import httpx
import pytest
from data_collector.application.services.reference_dataset import ReferenceCandidate
from data_collector.infrastructure.ai import OpenAIRelevanceAssessor


@pytest.mark.unit
def test_openai_assessor_requests_strict_schema_and_parses_scores() -> None:
    captured: dict[str, object] = {}

    def respond(request: httpx.Request) -> httpx.Response:
        captured.update(request.read() and json.loads(request.content))
        result = {
            "usefulness": 0.82,
            "relevance": 0.91,
            "importance": 0.74,
            "confidence": 0.88,
            "event_type": "regulation",
            "explanation": "Direct regulatory event.",
        }
        return httpx.Response(
            200,
            json={
                "output": [
                    {
                        "type": "message",
                        "content": [{"type": "output_text", "text": json.dumps(result)}],
                    }
                ]
            },
        )

    client = httpx.AsyncClient(
        transport=httpx.MockTransport(respond), base_url="https://api.openai.com/v1"
    )
    assessor = OpenAIRelevanceAssessor("test", client=client)

    async def run_assessment() -> object:
        try:
            return await assessor.assess(
                ReferenceCandidate(
                    "news:1:BTC",
                    "news",
                    "Reuters",
                    None,
                    "Regulator approves a Bitcoin custody framework.",
                    datetime(2026, 1, 1, tzinfo=UTC),
                    "BTC",
                    Decimal("1"),
                    Decimal("1"),
                    Decimal("1"),
                    Decimal("1"),
                    Decimal("0"),
                )
            )
        finally:
            await client.aclose()

    result = asyncio.run(run_assessment())

    assert result.usefulness == Decimal("0.82")
    assert result.event_type == "regulation"
    assert captured["store"] is False
    text_format = captured["text"]
    assert isinstance(text_format, dict)
    assert text_format["format"]["strict"] is True
