"""Add persistent paper sessions, experiments, participants and research facts.

Revision ID: 20260918_0001
Revises:
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260918_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

money = sa.Numeric(38, 18)


def upgrade() -> None:
    op.create_table(
        "experiments",
        sa.Column("experiment_id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("ended_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("markets", sa.JSON(), nullable=False),
        sa.Column("start_period", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_period", sa.DateTime(timezone=True), nullable=False),
        sa.Column("starting_balance", money, nullable=False),
        sa.Column("fee_rate", money, nullable=False),
        sa.Column("slippage_rate", money, nullable=False),
        sa.Column("random_seed", sa.Integer(), nullable=False),
        sa.Column("dataset_version", sa.String(200)),
        sa.Column("feature_version", sa.String(200)),
        sa.Column("git_commit", sa.String(64)),
    )
    op.create_index("ix_experiments_created_at", "experiments", ["created_at"])
    op.create_index("ix_experiments_name", "experiments", ["name"])
    op.create_index("ix_experiments_status", "experiments", ["status"])

    op.create_table(
        "paper_sessions",
        sa.Column("session_id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("ended_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("starting_balance", money, nullable=False),
        sa.Column("markets", sa.JSON(), nullable=False),
        sa.Column("fee_rate", money, nullable=False),
        sa.Column("slippage_rate", money, nullable=False),
        sa.Column("mode", sa.String(16), nullable=False),
        sa.Column("experiment_id", sa.Uuid()),
        sa.ForeignKeyConstraint(["experiment_id"], ["experiments.experiment_id"]),
    )
    for column in ("created_at", "status", "experiment_id"):
        op.create_index(f"ix_paper_sessions_{column}", "paper_sessions", [column])

    op.create_table(
        "bot_definitions",
        sa.Column("bot_id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("bot_type", sa.String(100), nullable=False),
        sa.Column("version", sa.String(100), nullable=False),
        sa.Column("configuration", sa.JSON(), nullable=False),
        sa.UniqueConstraint("name", "bot_type", "version", name="uq_bot_identity"),
    )
    op.create_index("ix_bot_definitions_name", "bot_definitions", ["name"])

    op.create_table(
        "session_bots",
        sa.Column("session_bot_id", sa.Uuid(), primary_key=True),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("bot_id", sa.Uuid(), nullable=False),
        sa.Column("starting_balance", money, nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("participant_configuration", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["paper_sessions.session_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["bot_id"], ["bot_definitions.bot_id"]),
        sa.UniqueConstraint("session_id", "bot_id", name="uq_session_bot"),
    )
    for column in ("session_id", "bot_id", "status"):
        op.create_index(f"ix_session_bots_{column}", "session_bots", [column])

    op.create_table(
        "portfolio_snapshots",
        sa.Column("snapshot_id", sa.Uuid(), primary_key=True),
        sa.Column("session_bot_id", sa.Uuid(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("cash", money, nullable=False),
        sa.Column("asset_value", money, nullable=False),
        sa.Column("portfolio_value", money, nullable=False),
        sa.Column("realized_pnl", money, nullable=False),
        sa.Column("unrealized_pnl", money, nullable=False),
        sa.Column("fees_paid", money, nullable=False),
        sa.ForeignKeyConstraint(
            ["session_bot_id"], ["session_bots.session_bot_id"], ondelete="CASCADE"
        ),
    )
    op.create_index(
        "ix_portfolio_snapshots_session_bot_id", "portfolio_snapshots", ["session_bot_id"]
    )
    op.create_index("ix_portfolio_bot_time", "portfolio_snapshots", ["session_bot_id", "timestamp"])

    op.create_table(
        "paper_positions",
        sa.Column("position_id", sa.Uuid(), primary_key=True),
        sa.Column("session_bot_id", sa.Uuid(), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("market", sa.String(32), nullable=False),
        sa.Column("side", sa.String(16), nullable=False),
        sa.Column("quantity", money, nullable=False),
        sa.Column("average_entry_price", money, nullable=False),
        sa.Column("current_price", money, nullable=False),
        sa.Column("realized_pnl", money, nullable=False),
        sa.Column("unrealized_pnl", money, nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(16), nullable=False),
        sa.ForeignKeyConstraint(
            ["session_bot_id"], ["session_bots.session_bot_id"], ondelete="CASCADE"
        ),
    )
    for column in ("session_bot_id", "recorded_at", "market", "status"):
        op.create_index(f"ix_paper_positions_{column}", "paper_positions", [column])
    op.create_index("ix_position_bot_time", "paper_positions", ["session_bot_id", "recorded_at"])

    op.create_table(
        "paper_trades",
        sa.Column("trade_id", sa.Uuid(), primary_key=True),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("session_bot_id", sa.Uuid(), nullable=False),
        sa.Column("market", sa.String(32), nullable=False),
        sa.Column("side", sa.String(16), nullable=False),
        sa.Column("requested_quantity", money, nullable=False),
        sa.Column("executed_quantity", money, nullable=False),
        sa.Column("market_price", money, nullable=False),
        sa.Column("execution_price", money, nullable=False),
        sa.Column("gross_value", money, nullable=False),
        sa.Column("fee", money, nullable=False),
        sa.Column("slippage_cost", money, nullable=False),
        sa.Column("realized_pnl", money, nullable=False),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["paper_sessions.session_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["session_bot_id"], ["session_bots.session_bot_id"], ondelete="CASCADE"
        ),
    )
    for column in ("session_id", "session_bot_id", "market", "executed_at"):
        op.create_index(f"ix_paper_trades_{column}", "paper_trades", [column])
    op.create_index("ix_trade_session_time", "paper_trades", ["session_id", "executed_at"])

    op.create_table(
        "bot_decisions",
        sa.Column("decision_id", sa.Uuid(), primary_key=True),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("session_bot_id", sa.Uuid(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("market", sa.String(32), nullable=False),
        sa.Column("action", sa.String(16), nullable=False),
        sa.Column("requested_size", money, nullable=False),
        sa.Column("confidence", money),
        sa.Column("market_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("price", money, nullable=False),
        sa.Column("bid", money, nullable=False),
        sa.Column("ask", money, nullable=False),
        sa.Column("spread", money, nullable=False),
        sa.Column("portfolio_value", money, nullable=False),
        sa.Column("cash", money, nullable=False),
        sa.Column("position_quantity", money, nullable=False),
        sa.Column("feature_snapshot_reference", sa.String(500)),
        sa.Column("news_snapshot_reference", sa.String(500)),
        sa.Column("social_snapshot_reference", sa.String(500)),
        sa.Column("explanation_reference", sa.String(500)),
        sa.Column("executed_trade_id", sa.Uuid()),
        sa.ForeignKeyConstraint(["session_id"], ["paper_sessions.session_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["session_bot_id"], ["session_bots.session_bot_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["executed_trade_id"], ["paper_trades.trade_id"]),
    )
    for column in ("session_id", "session_bot_id", "market", "executed_trade_id"):
        op.create_index(f"ix_bot_decisions_{column}", "bot_decisions", [column])
    op.create_index("ix_decision_bot_time", "bot_decisions", ["session_bot_id", "timestamp"])


def downgrade() -> None:
    for table in (
        "bot_decisions",
        "paper_trades",
        "paper_positions",
        "portfolio_snapshots",
        "session_bots",
        "bot_definitions",
        "paper_sessions",
        "experiments",
    ):
        op.drop_table(table)
