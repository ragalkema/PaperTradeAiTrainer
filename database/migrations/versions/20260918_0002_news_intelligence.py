"""Add immutable raw news, normalized events, sources and market associations.

Revision ID: 20260918_0002
Revises: 20260918_0001
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260918_0002"
down_revision: str | None = "20260918_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "news_sources",
        sa.Column("source_id", sa.String(100), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("poll_interval_seconds", sa.Integer(), nullable=False),
        sa.Column("feed_url", sa.String(1000), nullable=False),
        sa.Column("health", sa.String(20), nullable=False),
        sa.Column("last_success", sa.DateTime(timezone=True)),
        sa.Column("last_failure", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_news_sources_health", "news_sources", ["health"])

    op.create_table(
        "raw_news_items",
        sa.Column("raw_item_id", sa.Uuid(), primary_key=True),
        sa.Column("source_id", sa.String(100), nullable=False),
        sa.Column("external_id", sa.String(1000)),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text()),
        sa.Column("url", sa.String(2000), nullable=False),
        sa.Column("author", sa.String(500)),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("raw_metadata", sa.JSON(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("quarantine_reason", sa.Text()),
        sa.ForeignKeyConstraint(["source_id"], ["news_sources.source_id"]),
    )
    for column in ("source_id", "published_at", "received_at", "status"):
        op.create_index(f"ix_raw_news_items_{column}", "raw_news_items", [column])
    op.create_index(
        "uq_raw_news_source_hash", "raw_news_items", ["source_id", "content_hash"], unique=True
    )
    op.create_index("ix_raw_news_source_received", "raw_news_items", ["source_id", "received_at"])

    op.create_table(
        "news_events",
        sa.Column("news_event_id", sa.Uuid(), primary_key=True),
        sa.Column("raw_item_id", sa.Uuid(), nullable=False, unique=True),
        sa.Column("source_id", sa.String(100), nullable=False),
        sa.Column("source_name", sa.String(200), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text()),
        sa.Column("url", sa.String(2000), nullable=False),
        sa.Column("author", sa.String(500)),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("mentioned_assets", sa.JSON(), nullable=False),
        sa.Column("asset_relevance", sa.JSON(), nullable=False),
        sa.Column("importance", sa.Numeric(12, 10)),
        sa.Column("sentiment", sa.Numeric(12, 10)),
        sa.Column("language", sa.String(20), nullable=False),
        sa.Column("duplicate_group_id", sa.Uuid(), unique=True),
        sa.Column("story_cluster_id", sa.Uuid()),
        sa.ForeignKeyConstraint(["raw_item_id"], ["raw_news_items.raw_item_id"]),
        sa.ForeignKeyConstraint(["source_id"], ["news_sources.source_id"]),
    )
    for column in (
        "raw_item_id",
        "source_id",
        "published_at",
        "received_at",
        "processed_at",
        "duplicate_group_id",
        "story_cluster_id",
    ):
        op.create_index(f"ix_news_events_{column}", "news_events", [column])
    op.create_index("ix_news_availability", "news_events", ["received_at", "processed_at"])

    op.create_table(
        "news_market_associations",
        sa.Column("association_id", sa.Uuid(), primary_key=True),
        sa.Column("news_event_id", sa.Uuid(), nullable=False),
        sa.Column("market", sa.String(32), nullable=False),
        sa.Column("window_minutes", sa.Integer(), nullable=False),
        sa.Column("event_price", sa.Numeric(38, 18), nullable=False),
        sa.Column("post_event_price", sa.Numeric(38, 18), nullable=False),
        sa.Column("price_return", sa.Numeric(12, 10), nullable=False),
        sa.Column("volume_before", sa.Numeric(38, 18)),
        sa.Column("volume_after", sa.Numeric(38, 18)),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["news_event_id"], ["news_events.news_event_id"], ondelete="CASCADE"
        ),
    )
    op.create_index(
        "ix_news_market_associations_news_event_id",
        "news_market_associations",
        ["news_event_id"],
    )
    op.create_index("ix_news_market_associations_market", "news_market_associations", ["market"])
    op.create_index(
        "uq_news_market_window",
        "news_market_associations",
        ["news_event_id", "market", "window_minutes"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_table("news_market_associations")
    op.drop_table("news_events")
    op.drop_table("raw_news_items")
    op.drop_table("news_sources")
