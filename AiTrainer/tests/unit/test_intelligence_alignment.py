from datetime import timedelta
from decimal import Decimal

from ai_trainer.application.services.dataset import UnifiedDatasetBuilder
from ai_trainer.domain.entities import DatasetConfiguration
from data_collector.domain.entities import NewsFeatureSnapshot, SocialFeatureSnapshot
from test_unified_dataset import _candles


def test_future_intelligence_does_not_change_earlier_row() -> None:
    candles = _candles(30)
    first_decision = candles[0].timestamp + timedelta(hours=1)
    future = first_decision + timedelta(hours=1)
    news = NewsFeatureSnapshot(
        "BTC-EUR",
        future,
        future,
        "online_news_features_v1",
        (),
        (15, 60, 360),
        1,
        1,
        1,
        Decimal(".9"),
        Decimal(".5"),
        Decimal(".5"),
        Decimal(".5"),
        Decimal(".5"),
        Decimal(".8"),
        Decimal(".8"),
        Decimal(".7"),
        1,
    )
    social = SocialFeatureSnapshot(
        "BTC-EUR",
        future,
        future,
        "online_social_features_v1",
        (),
        1,
        1,
        1,
        1,
        Decimal(".5"),
        Decimal(".5"),
        Decimal(".5"),
        Decimal(".5"),
        Decimal(".9"),
        Decimal(".8"),
        Decimal(".7"),
        1,
        1,
        None,
        Decimal("2"),
    )
    config = DatasetConfiguration(
        "BTC-EUR", "1h", candles[0].timestamp, candles[-1].timestamp + timedelta(hours=1)
    )
    dataset = UnifiedDatasetBuilder().build(
        candles, config, news={future: news}, social={future: social}
    )
    assert dataset.rows[0].features["news_news_count_1h"] is None
    assert dataset.rows[0].features["social_count_1h"] is None
    assert dataset.rows[1].features["news_news_count_1h"] == 1.0
    assert dataset.rows[1].features["social_count_1h"] == 1.0


def test_retrospective_objects_cannot_enter_builder_contract() -> None:
    assert "impact" not in " ".join(UnifiedDatasetBuilder.build.__annotations__)
