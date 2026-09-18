"""Research-focused pages with safe empty states."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from dashboard.application.services.dashboard_service import (
    DashboardService,
    format_money,
    format_percent,
    format_score,
)
from dashboard.application.view_models import DashboardSnapshot, IntelligenceEvent, MarketSummary
from dashboard.presentation.charts import MarketChart
from dashboard.presentation.widgets import Card, EmptyState, MetricCard, SectionTitle


def _table(headers: list[str]) -> QTableWidget:
    table = QTableWidget(0, len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.horizontalHeader().setStretchLastSection(True)
    table.setAlternatingRowColors(True)
    table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    table.verticalHeader().hide()
    return table


def _page(title: str, subtitle: str) -> tuple[QWidget, QVBoxLayout]:
    container = QWidget()
    layout = QVBoxLayout(container)
    layout.setContentsMargins(24, 20, 24, 24)
    layout.setSpacing(16)
    layout.addWidget(SectionTitle(title, subtitle))
    return container, layout


class OverviewPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(14)
        layout.addWidget(SectionTitle("Overview", "Live research environment at a glance"))
        metrics = QGridLayout()
        self.capital = MetricCard("Total paper capital")
        self.pnl = MetricCard("Total bot P&L")
        self.best = MetricCard("Best performing bot")
        self.regime = MetricCard("Market regime", "N/A", "No regime model connected")
        self.active = MetricCard("Active bots")
        self.trades = MetricCard("Today's paper trades")
        for index, card in enumerate(
            [self.capital, self.pnl, self.best, self.regime, self.active, self.trades]
        ):
            metrics.addWidget(card, index // 3, index % 3)
        layout.addLayout(metrics)
        market_row = QHBoxLayout()
        self.market_cards: dict[str, MetricCard] = {}
        for market in ("BTC-EUR", "ETH-EUR", "SOL-EUR"):
            card = MetricCard(market.replace("-", "/"), "N/A", "Waiting for market data")
            self.market_cards[market] = card
            market_row.addWidget(card)
        layout.addLayout(market_row)
        lower = QHBoxLayout()
        bots = Card("Bot leaderboard")
        bots.content.addWidget(
            EmptyState("No bot results", "Run or load an experiment to compare bots.")
        )
        intelligence = Card("Top market impact · last 24 hours")
        intelligence.content.addWidget(
            EmptyState("No intelligence collected", "News and social collectors are not connected.")
        )
        lower.addWidget(bots, 3)
        lower.addWidget(intelligence, 2)
        layout.addLayout(lower, 1)

    def update_snapshot(self, snapshot: DashboardSnapshot) -> None:
        self.capital.set_metric(
            format_money(snapshot.portfolio.total_capital), "Virtual funds only"
        )
        self.pnl.set_metric(
            format_money(snapshot.portfolio.total_pnl), "Across available bot results"
        )
        active = [bot for bot in snapshot.bots if bot.status in {"PAPER LIVE", "TRAINING"}]
        self.active.set_metric(str(len(active)), "Bots reporting an active state")
        self.trades.set_metric(str(len(snapshot.trades)), "Loaded trade window")
        ranked = [
            bot
            for bot in DashboardService.rank_bots(snapshot.bots)
            if bot.percentage_return is not None
        ]
        self.best.set_metric(
            ranked[0].name if ranked else "N/A",
            "No experiment results" if not ranked else "By return",
        )
        for market in snapshot.markets:
            card = self.market_cards.get(market.market)
            if card:
                card.set_metric(
                    format_money(market.current_price),
                    f"{format_percent(market.change_24h)} 24h · {market.state}",
                )


class MarketsPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.addWidget(SectionTitle("Markets", "Public observations; no exchange order access"))
        controls = QHBoxLayout()
        self.selector = QComboBox()
        self.selector.addItems(["BTC-EUR", "ETH-EUR", "SOL-EUR"])
        self.timeframe = QComboBox()
        self.timeframe.addItems(["1h (live)", "1m", "5m", "15m", "4h", "1d"])
        for index in range(1, self.timeframe.count()):
            item = self.timeframe.model().item(index)  # type: ignore[attr-defined]
            if item is not None:
                item.setEnabled(False)
        controls.addWidget(self.selector)
        controls.addWidget(self.timeframe)
        controls.addStretch()
        layout.addLayout(controls)
        stats = QHBoxLayout()
        self.price = MetricCard("Current price")
        self.change = MetricCard("24h change")
        self.range = MetricCard("24h high / low")
        self.spread = MetricCard("Bid / ask spread")
        for card in [self.price, self.change, self.range, self.spread]:
            stats.addWidget(card)
        layout.addLayout(stats)
        self.chart = MarketChart()
        layout.addWidget(self.chart, 1)
        related = QHBoxLayout()
        related.addWidget(Card("Related news"))
        related.addWidget(Card("Related social posts"))
        layout.addLayout(related)
        self._snapshot = DashboardSnapshot()
        self.selector.currentTextChanged.connect(lambda _: self._render())

    def update_snapshot(self, snapshot: DashboardSnapshot) -> None:
        self._snapshot = snapshot
        self._render()

    def _render(self) -> None:
        market = next(
            (item for item in self._snapshot.markets if item.market == self.selector.currentText()),
            MarketSummary(self.selector.currentText()),
        )
        self.price.set_metric(format_money(market.current_price), str(market.state))
        self.change.set_metric(
            format_percent(market.change_24h), "Calculated from available candles"
        )
        self.range.set_metric(
            f"{format_money(market.high_24h)} / {format_money(market.low_24h)}", "High / low"
        )
        self.spread.set_metric(format_percent(market.spread_percent), "Relative top-of-book spread")
        self.chart.set_series(market.candles)


class TablePage(QWidget):
    def __init__(self, title: str, subtitle: str, headers: list[str], empty: str) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.addWidget(SectionTitle(title, subtitle))
        self.table = _table(headers)
        layout.addWidget(self.table, 1)
        self.empty = QLabel(empty)
        self.empty.setObjectName("muted")
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.empty)


class SystemPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.addWidget(SectionTitle("System", "Connection state and data health"))
        self.table = _table(["Data source", "State", "Last event", "Notes"])
        layout.addWidget(self.table)
        health = Card("Data health")
        health.content.addWidget(
            EmptyState(
                "No collector counters available",
                "Invalid, duplicate, and missing-data metrics require collector telemetry.",
            )
        )
        layout.addWidget(health, 1)

    def update_snapshot(self, snapshot: DashboardSnapshot) -> None:
        self.table.setRowCount(len(snapshot.connections))
        for row, (name, state) in enumerate(snapshot.connections.items()):
            values = [name, str(state), "N/A", "Live" if name == "Bitvavo" else "Not integrated"]
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(value))


class SettingsPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.addWidget(
            SectionTitle("Settings", "Local dashboard preferences and safe configuration")
        )
        warning = QLabel("PAPER TRADING ONLY · There is no real-trading mode")
        warning.setObjectName("paperBadge")
        layout.addWidget(warning, alignment=Qt.AlignmentFlag.AlignLeft)
        groups = QHBoxLayout()
        for title, rows in {
            "General": ["Markets", "Update frequency", "Appearance", "Logging"],
            "Paper Trading": ["Starting capital", "Fee rate", "Slippage model"],
            "Data Sources": ["Bitvavo public data", "News (disabled)", "Social/X (disabled)"],
        }.items():
            group = QGroupBox(title)
            form = QFormLayout(group)
            for row in rows:
                value = QLabel(
                    "Configured externally" if "disabled" not in row else "Not implemented"
                )
                value.setObjectName("muted")
                form.addRow(row, value)
            groups.addWidget(group)
        layout.addLayout(groups)
        layout.addStretch()


class DashboardPages:
    def __init__(self) -> None:
        self.overview = OverviewPage()
        self.markets = MarketsPage()
        self.bots = TablePage(
            "Bots",
            "Comparable paper performance on identical periods",
            ["Bot", "Type", "Status", "Value", "Return", "Max DD", "Trades", "Fees"],
            "No bot results available. Decision confidence and explanations "
            "will never be inferred.",
        )
        self.experiments = TablePage(
            "Experiments",
            "Reproducible research runs",
            ["Experiment", "Market", "Period", "Bots", "Starting balance", "Status", "Created"],
            "No persisted experiments available.",
        )
        self.news = TablePage(
            "News Intelligence",
            "Observed associations are not evidence of causality",
            [
                "Headline",
                "Source",
                "Published",
                "Assets",
                "Sentiment",
                "Relevance",
                "Estimated impact",
            ],
            "No news collected yet. Dashboard never scrapes sources directly.",
        )
        self.social = TablePage(
            "Social Intelligence",
            "Normalized collector output only",
            ["Author", "Time", "Preview", "Assets", "Sentiment", "Influence", "Estimated impact"],
            "Social collector disabled.",
        )
        self.trades = TablePage(
            "Paper Trades",
            "Virtual executions only",
            ["Time", "Bot", "Market", "Side", "Price", "P&L"],
            "No paper trades available.",
        )
        self.data = SystemPage()
        self.training = self._training_page()
        self.system = SystemPage()
        self.settings = SettingsPage()
        self.items: list[tuple[str, QWidget]] = [
            ("Overview", self.overview),
            ("Markets", self.markets),
            ("Bots", self.bots),
            ("Experiments", self.experiments),
            ("News", self.news),
            ("Social", self.social),
            ("Trades", self.trades),
            ("Data", self.data),
            ("Training", self.training),
            ("System", self.system),
            ("Settings", self.settings),
        ]

    @staticmethod
    def _training_page() -> QWidget:
        page, layout = _page(
            "AI Training", "Training controls activate only when AiTrainer supports them safely"
        )
        controls = QHBoxLayout()
        for name in ("Start training", "Pause", "Stop"):
            button = QPushButton(name)
            button.setEnabled(False)
            controls.addWidget(button)
        controls.addStretch()
        layout.addLayout(controls)
        layout.addWidget(
            EmptyState(
                "Training is not implemented",
                "Baseline bots and historical comparison are currently available "
                "through AiTrainer.",
            ),
            1,
        )
        return page

    def update_snapshot(self, snapshot: DashboardSnapshot) -> None:
        self.overview.update_snapshot(snapshot)
        self.markets.update_snapshot(snapshot)
        self.data.update_snapshot(snapshot)
        self.system.update_snapshot(snapshot)
        self._update_bots(snapshot)
        self._update_trades(snapshot)
        self._update_intelligence(self.news, snapshot.news)
        self._update_intelligence(self.social, snapshot.social)

    def _update_bots(self, snapshot: DashboardSnapshot) -> None:
        rows = [
            [
                bot.name,
                bot.bot_type,
                bot.status,
                format_money(bot.portfolio_value),
                format_percent(bot.percentage_return),
                format_percent(bot.maximum_drawdown),
                str(bot.trades) if bot.trades is not None else "N/A",
                format_money(bot.fees),
            ]
            for bot in DashboardService.rank_bots(snapshot.bots)
        ]
        self._set_rows(self.bots, rows)

    def _update_trades(self, snapshot: DashboardSnapshot) -> None:
        rows = [
            [
                trade.timestamp.astimezone().strftime("%H:%M:%S"),
                trade.bot,
                trade.market,
                trade.side.upper(),
                format_money(trade.price),
                format_money(trade.pnl),
            ]
            for trade in snapshot.trades
        ]
        self._set_rows(self.trades, rows)

    def _update_intelligence(self, page: TablePage, events: tuple[IntelligenceEvent, ...]) -> None:
        rows = [
            [
                event.title,
                event.source or "N/A",
                event.occurred_at.astimezone().strftime("%Y-%m-%d %H:%M"),
                ", ".join(event.assets) or "N/A",
                format_percent(event.sentiment),
                format_score(event.relevance),
                format_score(event.estimated_impact),
            ]
            for event in events
        ]
        self._set_rows(page, rows)

    @staticmethod
    def _set_rows(page: TablePage, rows: list[list[str]]) -> None:
        page.table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            for column_index, value in enumerate(row):
                page.table.setItem(row_index, column_index, QTableWidgetItem(value))
        page.empty.setVisible(not rows)
