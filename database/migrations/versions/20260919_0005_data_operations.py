"""Research data operations and coverage provenance.

Revision ID: 20260919_0005
Revises: 20260918_0004
"""

import sqlalchemy as sa
from alembic import op

revision = "20260919_0005"
down_revision = "20260918_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "market_candles",
        sa.Column("market", sa.String(32), primary_key=True),
        sa.Column("interval", sa.String(16), primary_key=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), primary_key=True),
        sa.Column("open", sa.Numeric(38, 18), nullable=False),
        sa.Column("high", sa.Numeric(38, 18), nullable=False),
        sa.Column("low", sa.Numeric(38, 18), nullable=False),
        sa.Column("close", sa.Numeric(38, 18), nullable=False),
        sa.Column("volume", sa.Numeric(38, 18), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_market_candle_range", "market_candles", ["market", "interval", "timestamp"])
    op.create_table(
        "collection_checkpoints",
        sa.Column("source", sa.String(200), primary_key=True),
        sa.Column("last_successful_event_time", sa.DateTime(timezone=True)),
        sa.Column("last_poll_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("external_cursor", sa.Text()),
        sa.Column("last_processed_event", sa.String(500)),
    )
    op.create_table(
        "collector_health_observations",
        sa.Column("source", sa.String(200), primary_key=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), primary_key=True),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("latency_ms", sa.Integer()),
        sa.Column("events_received", sa.Integer(), nullable=False),
        sa.Column("error_category", sa.String(200)),
        sa.Column("details", sa.JSON(), nullable=False),
    )
    op.create_index(
        "ix_collector_health_range", "collector_health_observations", ["source", "timestamp"]
    )
    op.create_index(
        "ix_collector_health_observations_status", "collector_health_observations", ["status"]
    )
    op.create_table(
        "coverage_limitations",
        sa.Column("source", sa.String(200), primary_key=True),
        sa.Column("first_known_complete_time", sa.DateTime(timezone=True)),
        sa.Column("unavailable_before", sa.DateTime(timezone=True)),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "dataset_manifests",
        sa.Column("manifest_id", sa.String(64), primary_key=True),
        sa.Column("market", sa.String(32), nullable=False),
        sa.Column("interval", sa.String(16), nullable=False),
        sa.Column("start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("canonical_rows", sa.Integer(), nullable=False),
        sa.Column("feature_versions", sa.JSON(), nullable=False),
        sa.Column("analyzer_versions", sa.JSON(), nullable=False),
        sa.Column("coverage_summary", sa.JSON(), nullable=False),
        sa.Column("dataset_fingerprint", sa.String(64), nullable=False),
        sa.Column("readiness_policy_version", sa.String(100), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("git_commit", sa.String(64)),
    )
    op.create_index(
        "ix_dataset_manifests_dataset_fingerprint", "dataset_manifests", ["dataset_fingerprint"]
    )


def downgrade() -> None:
    for name in (
        "dataset_manifests",
        "coverage_limitations",
        "collector_health_observations",
        "collection_checkpoints",
        "market_candles",
    ):
        op.drop_table(name)
