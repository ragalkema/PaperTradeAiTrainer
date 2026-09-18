"""Repository-level Clean Architecture dependency tests."""

from pathlib import Path

import pytest

from validation.architecture.check_boundaries import boundary_violations


@pytest.mark.contract
def test_clean_architecture_dependencies() -> None:
    assert boundary_violations() == []


@pytest.mark.contract
def test_online_news_features_do_not_import_retrospective_research() -> None:
    source = Path(
        "DataCollector/src/data_collector/application/services/news_features.py"
    ).read_text(encoding="utf-8")
    assert "retrospective_impact" not in source
    assert "MarketAssociation" not in source
    assert "RetrospectiveImpact" not in source


@pytest.mark.contract
def test_online_social_features_do_not_import_retrospective_research() -> None:
    source = Path(
        "DataCollector/src/data_collector/application/services/social_features.py"
    ).read_text(encoding="utf-8")
    assert "social_retrospective" not in source
    assert "SocialMarketReaction" not in source
    assert "SocialMarketImpact" not in source
