"""Add provider-neutral social intelligence. Revision ID: 20260918_0004"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision = "20260918_0004"
down_revision = "20260918_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    score = sa.Numeric(12, 10)
    money = sa.Numeric(38, 18)
    op.create_table(
        "tracked_social_accounts",
        sa.Column("account_id", sa.Uuid(), primary_key=True),
        sa.Column("provider", sa.String(30), nullable=False),
        sa.Column("provider_user_id", sa.String(100)),
        sa.Column("username", sa.String(100), nullable=False),
        sa.Column("display_name", sa.String(200)),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("category", sa.String(30), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("followers", sa.Integer()),
        sa.Column("typical_engagement", money),
        sa.Column("posts_per_day", money),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("provider", "username", name="uq_social_provider_username"),
    )
    op.create_index("ix_tracked_social_accounts_provider", "tracked_social_accounts", ["provider"])
    op.create_index("ix_tracked_social_accounts_enabled", "tracked_social_accounts", ["enabled"])
    op.create_table(
        "raw_social_posts",
        sa.Column("raw_post_id", sa.Uuid(), primary_key=True),
        sa.Column("provider", sa.String(30), nullable=False),
        sa.Column("external_post_id", sa.String(100), nullable=False),
        sa.Column("provider_user_id", sa.String(100), nullable=False),
        sa.Column("username", sa.String(100), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("language", sa.String(20)),
        sa.Column("reply_to", sa.String(100)),
        sa.Column("quote_of", sa.String(100)),
        sa.Column("repost_of", sa.String(100)),
        sa.Column("public_metrics", sa.JSON()),
        sa.Column("raw_metadata", sa.JSON(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.UniqueConstraint(
            "provider", "external_post_id", "content_hash", name="uq_raw_social_version"
        ),
    )
    op.create_index("ix_raw_social_posts_received_at", "raw_social_posts", ["received_at"])
    op.create_index("ix_raw_social_posts_username", "raw_social_posts", ["username"])
    op.create_table(
        "social_events",
        sa.Column("social_event_id", sa.Uuid(), primary_key=True),
        sa.Column(
            "raw_post_id",
            sa.Uuid(),
            sa.ForeignKey("raw_social_posts.raw_post_id"),
            unique=True,
            nullable=False,
        ),
        sa.Column("provider", sa.String(30), nullable=False),
        sa.Column(
            "source_account_id",
            sa.Uuid(),
            sa.ForeignKey("tracked_social_accounts.account_id"),
            nullable=False,
        ),
        sa.Column("external_post_id", sa.String(100), nullable=False),
        sa.Column("username", sa.String(100), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("language", sa.String(20), nullable=False),
        sa.Column("mentioned_assets", sa.JSON(), nullable=False),
        sa.Column("asset_relevance", sa.JSON(), nullable=False),
        sa.Column("post_type", sa.String(20), nullable=False),
        sa.Column("reply_to", sa.String(100)),
        sa.Column("quote_of", sa.String(100)),
        sa.Column("repost_of", sa.String(100)),
        sa.Column("story_cluster_id", sa.Uuid()),
    )
    op.create_index("ix_social_events_received_at", "social_events", ["received_at"])
    op.create_index("ix_social_events_source_account_id", "social_events", ["source_account_id"])
    op.create_index("ix_social_events_story_cluster_id", "social_events", ["story_cluster_id"])
    op.create_table(
        "social_engagement_snapshots",
        sa.Column("snapshot_id", sa.Uuid(), primary_key=True),
        sa.Column(
            "social_event_id",
            sa.Uuid(),
            sa.ForeignKey("social_events.social_event_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        *[
            sa.Column(name, sa.Integer())
            for name in ("likes", "replies", "reposts", "quotes", "bookmarks", "views")
        ],
    )
    op.create_index(
        "ix_social_engagement_snapshots_social_event_id",
        "social_engagement_snapshots",
        ["social_event_id"],
    )
    op.create_index(
        "ix_social_engagement_snapshots_observed_at", "social_engagement_snapshots", ["observed_at"]
    )
    op.create_table(
        "social_intelligence",
        sa.Column("intelligence_id", sa.Uuid(), primary_key=True),
        sa.Column(
            "social_event_id",
            sa.Uuid(),
            sa.ForeignKey("social_events.social_event_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("asset", sa.String(20), nullable=False),
        *[
            sa.Column(name, score, nullable=False)
            for name in (
                "relevance",
                "sentiment",
                "sentiment_confidence",
                "importance",
                "event_confidence",
                "novelty",
                "account_influence",
            )
        ],
        sa.Column("event_type", sa.String(40), nullable=False),
        sa.Column("verification_status", sa.String(30), nullable=False),
        sa.Column("versions", sa.JSON(), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("explanation", sa.JSON(), nullable=False),
    )
    for name in ("social_event_id", "asset", "importance", "event_type", "account_influence"):
        op.create_index(f"ix_social_intelligence_{name}", "social_intelligence", [name])
    op.create_table(
        "social_feature_snapshots",
        sa.Column("snapshot_id", sa.Uuid(), primary_key=True),
        sa.Column("market", sa.String(32), nullable=False),
        sa.Column("feature_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("feature_version", sa.String(100), nullable=False),
        sa.Column("analyzer_versions", sa.JSON(), nullable=False),
        sa.Column("features", sa.JSON(), nullable=False),
        sa.UniqueConstraint(
            "market", "feature_time", "feature_version", name="uq_social_feature_identity"
        ),
    )
    op.create_index("ix_social_feature_snapshots_market", "social_feature_snapshots", ["market"])
    op.create_index(
        "ix_social_feature_snapshots_feature_time", "social_feature_snapshots", ["feature_time"]
    )
    op.create_table(
        "social_market_reactions",
        sa.Column("reaction_id", sa.Uuid(), primary_key=True),
        sa.Column(
            "social_event_id",
            sa.Uuid(),
            sa.ForeignKey("social_events.social_event_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("market", sa.String(32), nullable=False),
        sa.Column("window_minutes", sa.Integer(), nullable=False),
        sa.Column("event_price", money, nullable=False),
        sa.Column("post_price", money, nullable=False),
        sa.Column("price_return", score, nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("volume_before", money),
        sa.Column("volume_after", money),
        sa.UniqueConstraint(
            "social_event_id", "market", "window_minutes", name="uq_social_market_window"
        ),
    )
    op.create_index(
        "ix_social_market_reactions_social_event_id", "social_market_reactions", ["social_event_id"]
    )
    op.create_table(
        "social_market_impact",
        sa.Column(
            "social_event_id",
            sa.Uuid(),
            sa.ForeignKey("social_events.social_event_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("asset", sa.String(20), primary_key=True),
        sa.Column("score", score, nullable=False),
        sa.Column("available_windows", sa.JSON(), nullable=False),
        sa.Column("pending_windows", sa.JSON(), nullable=False),
        sa.Column("analyzer_version", sa.String(100), nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("components", sa.JSON(), nullable=False),
    )
    op.create_index("ix_social_market_impact_score", "social_market_impact", ["score"])


def downgrade() -> None:
    for table in (
        "social_market_impact",
        "social_market_reactions",
        "social_feature_snapshots",
        "social_intelligence",
        "social_engagement_snapshots",
        "social_events",
        "raw_social_posts",
        "tracked_social_accounts",
    ):
        op.drop_table(table)
