"""Add versioned online intelligence, feature snapshots and retrospective impact.

Revision ID: 20260918_0003
Revises: 20260918_0002
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260918_0003"
down_revision: str | None = "20260918_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    score = sa.Numeric(12, 10)
    op.create_table(
        "news_intelligence",
        sa.Column("intelligence_id", sa.Uuid(), primary_key=True),
        sa.Column("news_event_id", sa.Uuid(), nullable=False),
        sa.Column("asset", sa.String(20), nullable=False),
        sa.Column("relevance", score, nullable=False),
        sa.Column("sentiment", score, nullable=False),
        sa.Column("sentiment_confidence", score, nullable=False),
        sa.Column("importance", score, nullable=False),
        sa.Column("importance_confidence", score, nullable=False),
        sa.Column("event_type", sa.String(40), nullable=False),
        sa.Column("event_confidence", score, nullable=False),
        sa.Column("secondary_tags", sa.JSON(), nullable=False),
        sa.Column("novelty", score, nullable=False),
        sa.Column("novelty_confidence", score, nullable=False),
        sa.Column("story_cluster_id", sa.Uuid(), nullable=False),
        sa.Column("sentiment_version", sa.String(100), nullable=False),
        sa.Column("importance_version", sa.String(100), nullable=False),
        sa.Column("classifier_version", sa.String(100), nullable=False),
        sa.Column("novelty_version", sa.String(100), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("explanation", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["news_event_id"], ["news_events.news_event_id"], ondelete="CASCADE"
        ),
    )
    for column in (
        "news_event_id",
        "asset",
        "importance",
        "event_type",
        "story_cluster_id",
        "processed_at",
    ):
        op.create_index(f"ix_news_intelligence_{column}", "news_intelligence", [column])
    op.create_index(
        "uq_news_intelligence_versions",
        "news_intelligence",
        [
            "news_event_id",
            "asset",
            "sentiment_version",
            "importance_version",
            "classifier_version",
            "novelty_version",
        ],
        unique=True,
    )

    op.create_table(
        "news_feature_snapshots",
        sa.Column("snapshot_id", sa.Uuid(), primary_key=True),
        sa.Column("market", sa.String(32), nullable=False),
        sa.Column("feature_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("feature_version", sa.String(100), nullable=False),
        sa.Column("analyzer_versions", sa.JSON(), nullable=False),
        sa.Column("lookbacks_minutes", sa.JSON(), nullable=False),
        sa.Column("features", sa.JSON(), nullable=False),
    )
    op.create_index("ix_news_feature_snapshots_market", "news_feature_snapshots", ["market"])
    op.create_index(
        "ix_news_feature_snapshots_feature_time", "news_feature_snapshots", ["feature_time"]
    )
    op.create_index(
        "uq_news_feature_identity",
        "news_feature_snapshots",
        ["market", "feature_time", "feature_version"],
        unique=True,
    )

    op.create_table(
        "news_market_impact",
        sa.Column("news_event_id", sa.Uuid(), primary_key=True),
        sa.Column("asset", sa.String(20), primary_key=True),
        sa.Column("score", score, nullable=False),
        sa.Column("available_windows", sa.JSON(), nullable=False),
        sa.Column("pending_windows", sa.JSON(), nullable=False),
        sa.Column("analyzer_version", sa.String(100), nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("components", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["news_event_id"], ["news_events.news_event_id"], ondelete="CASCADE"
        ),
    )
    op.create_index("ix_news_market_impact_score", "news_market_impact", ["score"])


def downgrade() -> None:
    op.drop_table("news_market_impact")
    op.drop_table("news_feature_snapshots")
    op.drop_table("news_intelligence")
