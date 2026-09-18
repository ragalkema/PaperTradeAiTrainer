"""Research-focused pages with safe empty states."""

from decimal import Decimal

from pyqtgraph import PlotWidget, mkPen  # type: ignore[import-untyped]
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
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
        self.impact_table = _table(["Headline", "Asset", "Impact", "Maturity"])
        intelligence.content.addWidget(self.impact_table)
        lower.addWidget(bots, 3)
        lower.addWidget(intelligence, 2)
        layout.addLayout(lower, 1)
        sentiment = Card("News sentiment · analyzed last 24 hours")
        self.sentiment_summary = QLabel("Insufficient analyzed news")
        sentiment.content.addWidget(self.sentiment_summary)
        self.social_sentiment_summary = QLabel("Social: insufficient analyzed posts")
        sentiment.content.addWidget(self.social_sentiment_summary)
        layout.addWidget(sentiment)
        online_rankings = QHBoxLayout()
        important = Card("Most important news · ONLINE")
        self.importance_table = _table(["Headline", "Asset", "Importance"])
        important.content.addWidget(self.importance_table)
        relevant = Card("Most relevant · ONLINE")
        self.relevance_table = _table(["Headline", "Asset", "Relevance"])
        relevant.content.addWidget(self.relevance_table)
        online_rankings.addWidget(important)
        online_rankings.addWidget(relevant)
        layout.addLayout(online_rankings)

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
        impact_events = DashboardService.top_intelligence(snapshot.news)
        self.impact_table.setRowCount(len(impact_events))
        for row, impact_event in enumerate(impact_events):
            impact_values = (
                impact_event.title,
                ", ".join(impact_event.assets),
                format_score(impact_event.estimated_impact),
                impact_event.impact_maturity or "Pending",
            )
            for column, value in enumerate(impact_values):
                self.impact_table.setItem(row, column, QTableWidgetItem(value))
        summaries = []
        for asset in ("BTC", "ETH", "SOL"):
            sentiment_values = [
                item.sentiment
                for item in snapshot.news
                if asset in item.assets and item.sentiment is not None
            ]
            if sentiment_values:
                mean = sum(sentiment_values, start=sentiment_values[0] * 0) / len(sentiment_values)
                summaries.append(f"{asset} {mean:+.2f} (n={len(sentiment_values)})")
        self.sentiment_summary.setText(
            "  ·  ".join(summaries) if summaries else "Insufficient analyzed news"
        )
        social_summaries = []
        for asset in ("BTC", "ETH", "SOL"):
            values = [
                item.sentiment
                for item in snapshot.social
                if asset in item.assets and item.sentiment is not None
            ]
            if values:
                mean = sum(values, start=values[0] * 0) / len(values)
                social_summaries.append(f"{asset} {mean:+.2f} (n={len(values)})")
        self.social_sentiment_summary.setText(
            "Social: "
            + (" · ".join(social_summaries) if social_summaries else "insufficient analyzed posts")
        )
        for table, ranked_events, field in (
            (self.importance_table, DashboardService.top_importance(snapshot.news), "importance"),
            (self.relevance_table, DashboardService.top_relevance(snapshot.news), "relevance"),
        ):
            table.setRowCount(len(ranked_events))
            for row, ranked_event in enumerate(ranked_events):
                ranking_values = (
                    ranked_event.title,
                    ", ".join(ranked_event.assets),
                    format_score(getattr(ranked_event, field)),
                )
                for column, value in enumerate(ranking_values):
                    table.setItem(row, column, QTableWidgetItem(value))


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
        self.content_layout = layout
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


class MLResearchPage(QWidget):
    """Read-only persisted supervised research; training never runs on the UI thread."""

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.addWidget(
            SectionTitle("ML Research", "Point-in-time out-of-sample feature comparison")
        )
        self.dataset = QLabel("No dataset or trained models available.")
        self.dataset.setObjectName("muted")
        layout.addWidget(self.dataset)
        layout.addWidget(QLabel("XGBOOST FEATURE GROUP COMPARISON"))
        self.models = _table(
            ["Model", "Features", "MAE", "RMSE", "R²", "Pearson", "Spearman", "Direction"]
        )
        layout.addWidget(self.models)
        layout.addWidget(QLabel("TOP MODEL-DERIVED FEATURE IMPORTANCE (GAIN, NOT CAUSALITY)"))
        self.importance = _table(["Model", "Feature", "Gain"])
        layout.addWidget(self.importance)
        charts = QHBoxLayout()
        self.prediction_chart = PlotWidget(title="Predicted vs actual return over test rows")
        self.scatter_chart = PlotWidget(title="Predicted return vs actual return")
        self.prediction_chart.setLabel("left", "Return")
        self.prediction_chart.setLabel("bottom", "Chronological test row")
        self.scatter_chart.setLabel("left", "Actual return")
        self.scatter_chart.setLabel("bottom", "Predicted return")
        charts.addWidget(self.prediction_chart)
        charts.addWidget(self.scatter_chart)
        layout.addLayout(charts)

    def update_snapshot(self, snapshot: DashboardSnapshot) -> None:
        research = snapshot.ml_research
        if research is None:
            self.dataset.setText("No dataset or trained models available.")
            self.models.setRowCount(0)
            self.importance.setRowCount(0)
            self.prediction_chart.clear()
            self.scatter_chart.clear()
            return
        self.dataset.setText(
            f"{research.market} · {research.interval} · {research.target} · "
            f"{research.start_time:%Y-%m-%d} — {research.end_time:%Y-%m-%d} · "
            f"dataset {research.dataset_id[:8]} · rows {research.row_count or 'N/A'} · "
            f"news {_number(research.news_coverage)} · social {_number(research.social_coverage)}"
        )
        self.models.setRowCount(len(research.models))
        importance: list[tuple[str, str, float]] = []
        for row, model in enumerate(research.models):
            values = [
                model.name,
                model.features,
                _number(model.mae),
                _number(model.rmse),
                _number(model.r_squared),
                _number(model.correlation),
                _number(model.spearman),
                format_percent(Decimal(str(model.directional_accuracy)))
                if model.directional_accuracy is not None
                else "N/A",
            ]
            for column, value in enumerate(values):
                self.models.setItem(row, column, QTableWidgetItem(value))
            importance.extend((model.name, name, gain) for name, gain in model.feature_importance)
        self.importance.setRowCount(len(importance))
        for row, (model_name, name, gain) in enumerate(importance):
            for column, value in enumerate((model_name, name, f"{gain:.6g}")):
                self.importance.setItem(row, column, QTableWidgetItem(value))
        selected = next((item for item in research.models if item.algorithm == "xgboost"), None)
        self.prediction_chart.clear()
        self.scatter_chart.clear()
        if selected and selected.predictions and selected.actuals:
            self.prediction_chart.plot(selected.predictions, pen=mkPen("#46a0ff", width=2))
            self.prediction_chart.plot(selected.actuals, pen=mkPen("#f6c85f", width=2))
            self.scatter_chart.plot(
                selected.predictions,
                selected.actuals,
                pen=None,
                symbol="o",
                symbolSize=5,
                symbolBrush="#46a0ff",
            )


def _number(value: float | None) -> str:
    return "N/A" if value is None else f"{value:.6g}"


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
                "Importance · ONLINE",
                "Event type · ONLINE",
                "Novelty · ONLINE",
                "Impact · RETROSPECTIVE",
                "Maturity",
            ],
            "No news collected yet. Dashboard never scrapes sources directly.",
        )
        news_filters = QWidget()
        news_filter_layout = QHBoxLayout(news_filters)
        self.news_asset_filter = QComboBox()
        self.news_asset_filter.addItems(["All assets", "BTC", "ETH", "SOL"])
        self.news_type_filter = QComboBox()
        self.news_type_filter.addItems(["All event types"])
        self.news_sentiment_filter = QComboBox()
        self.news_sentiment_filter.addItems(["All sentiment", "Positive", "Neutral", "Negative"])
        for label, control in (
            ("Asset", self.news_asset_filter),
            ("Event type", self.news_type_filter),
            ("Sentiment", self.news_sentiment_filter),
        ):
            news_filter_layout.addWidget(QLabel(label))
            news_filter_layout.addWidget(control)
        news_filter_layout.addStretch()
        self.news.content_layout.insertWidget(1, news_filters)
        self.news.table.cellDoubleClicked.connect(self._show_news_detail)
        self.social = TablePage(
            "Social Intelligence",
            "ONLINE scores and RETROSPECTIVE associations are distinct",
            [
                "Author",
                "Received",
                "Preview",
                "Asset",
                "Relevance · ONLINE",
                "Sentiment · ONLINE",
                "Importance · ONLINE",
                "Novelty · ONLINE",
                "Influence · ONLINE",
                "Event type",
                "Impact · RETROSPECTIVE",
            ],
            "No persisted social posts. Configure X access and tracked accounts to collect.",
        )
        self.intelligence = TablePage(
            "Market Intelligence",
            "Combined receipt-time feed; online metrics only",
            [
                "Type",
                "Received",
                "Source",
                "Preview",
                "Asset",
                "Sentiment",
                "Importance",
                "Relevance",
                "Event type",
            ],
            "No analyzed news or social intelligence available.",
        )
        self.trades = TablePage(
            "Paper Trades",
            "Virtual executions only",
            ["Time", "Bot", "Market", "Side", "Price", "P&L"],
            "No paper trades available.",
        )
        self.positions = TablePage(
            "Positions",
            "Current virtual spot positions",
            ["Market", "Side", "Quantity", "Average entry", "Current", "Unrealized P&L"],
            "No open paper positions available.",
        )
        self.decisions = TablePage(
            "Bot Decisions",
            "Point-in-time inputs captured without future information",
            ["Time", "Bot", "Market", "Action", "Requested size", "Confidence", "Price"],
            "No recorded bot decisions available.",
        )
        self.data = SystemPage()
        self.ml_research = MLResearchPage()
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
            ("Intelligence", self.intelligence),
            ("Trades", self.trades),
            ("Positions", self.positions),
            ("Decisions", self.decisions),
            ("Data", self.data),
            ("ML Research", self.ml_research),
            ("Training", self.training),
            ("System", self.system),
            ("Settings", self.settings),
        ]
        self._snapshot = DashboardSnapshot()
        self._visible_news: tuple[IntelligenceEvent, ...] = ()
        for control in (self.news_asset_filter, self.news_type_filter, self.news_sentiment_filter):
            control.currentTextChanged.connect(lambda _value: self._update_news())

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
        self._snapshot = snapshot
        self.overview.update_snapshot(snapshot)
        self.markets.update_snapshot(snapshot)
        self.data.update_snapshot(snapshot)
        self.system.update_snapshot(snapshot)
        self.ml_research.update_snapshot(snapshot)
        self._update_bots(snapshot)
        self._update_trades(snapshot)
        known_types = sorted({item.event_type for item in snapshot.news if item.event_type})
        current_type = self.news_type_filter.currentText()
        self.news_type_filter.blockSignals(True)
        self.news_type_filter.clear()
        self.news_type_filter.addItems(["All event types", *known_types])
        self.news_type_filter.setCurrentText(
            current_type if current_type in known_types else "All event types"
        )
        self.news_type_filter.blockSignals(False)
        self._update_news()
        self._update_intelligence(self.social, snapshot.social)
        combined = tuple(
            sorted(
                (*snapshot.news, *snapshot.social), key=lambda item: item.occurred_at, reverse=True
            )
        )
        combined_rows = [
            [
                event.kind.upper(),
                event.occurred_at.astimezone().strftime("%Y-%m-%d %H:%M"),
                event.source or "N/A",
                event.title,
                ", ".join(event.assets),
                format_percent(event.sentiment),
                format_score(event.importance),
                format_score(event.relevance),
                event.event_type or "N/A",
            ]
            for event in combined
        ]
        self._set_rows(self.intelligence, combined_rows)
        self._update_experiments(snapshot)
        self._update_positions(snapshot)
        self._update_decisions(snapshot)

    def _update_news(self) -> None:
        asset = self.news_asset_filter.currentText()
        event_type = self.news_type_filter.currentText()
        sentiment = self.news_sentiment_filter.currentText()
        events = self._snapshot.news
        if asset != "All assets":
            events = tuple(item for item in events if asset in item.assets)
        if event_type != "All event types":
            events = tuple(item for item in events if item.event_type == event_type)
        if sentiment == "Positive":
            events = tuple(
                item for item in events if item.sentiment is not None and item.sentiment > 0
            )
        elif sentiment == "Negative":
            events = tuple(
                item for item in events if item.sentiment is not None and item.sentiment < 0
            )
        elif sentiment == "Neutral":
            events = tuple(item for item in events if item.sentiment == 0)
        self._visible_news = events
        self._update_intelligence(self.news, events)

    def _show_news_detail(self, row: int, _column: int) -> None:
        if not 0 <= row < len(self._visible_news):
            return
        event = self._visible_news[row]
        reactions = (
            "\n".join(f"+{minutes}m: {format_percent(value)}" for minutes, value in event.reactions)
            or "Reaction windows pending"
        )
        explanation = "\n".join(event.explanation) or "Explanation unavailable"
        QMessageBox.information(
            self.news,
            "News intelligence detail",
            f"{event.title}\n\nSource: {event.source or 'N/A'}\n"
            f"Published: {event.published_at or 'N/A'}\nReceived: {event.occurred_at}\n"
            f"Processed: {event.processed_at or 'N/A'}\nAssets: {', '.join(event.assets)}\n\n"
            f"ONLINE INTELLIGENCE\nSentiment: {format_percent(event.sentiment)}\n"
            f"Relevance: {format_score(event.relevance)}\n"
            f"Importance: {format_score(event.importance)}\n"
            f"Event type: {event.event_type or 'N/A'}\nNovelty: {format_score(event.novelty)}\n\n"
            f"Importance factors:\n{explanation}\n\nRETROSPECTIVE RESEARCH\n"
            f"Estimated impact: {format_score(event.estimated_impact)} "
            f"({event.impact_maturity or 'Pending'})\n{reactions}\n\n"
            "Observed association does not establish causality.",
        )

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

    def _update_experiments(self, snapshot: DashboardSnapshot) -> None:
        rows = [
            [
                item.name,
                ", ".join(item.markets),
                f"{item.start_period:%Y-%m-%d} — {item.end_period:%Y-%m-%d}",
                "See participants",
                format_money(item.starting_balance),
                item.status.upper(),
                item.created_at.astimezone().strftime("%Y-%m-%d %H:%M"),
            ]
            for item in snapshot.experiments
        ]
        self._set_rows(self.experiments, rows)

    def _update_positions(self, snapshot: DashboardSnapshot) -> None:
        rows = [
            [
                item.market,
                item.side,
                f"{item.quantity:f}",
                format_money(item.average_entry_price),
                format_money(item.current_price),
                format_money(item.unrealized_pnl),
            ]
            for item in snapshot.positions
        ]
        self._set_rows(self.positions, rows)

    def _update_decisions(self, snapshot: DashboardSnapshot) -> None:
        rows = [
            [
                item.timestamp.astimezone().strftime("%Y-%m-%d %H:%M:%S"),
                item.bot,
                item.market,
                item.action.upper(),
                f"{item.requested_size:f}",
                format_score(item.confidence),
                format_money(item.price),
            ]
            for item in snapshot.decisions
        ]
        self._set_rows(self.decisions, rows)

    def _update_intelligence(self, page: TablePage, events: tuple[IntelligenceEvent, ...]) -> None:
        if page is self.social:
            rows = [
                [
                    event.source or "N/A",
                    event.occurred_at.astimezone().strftime("%Y-%m-%d %H:%M"),
                    event.title,
                    ", ".join(event.assets),
                    format_score(event.relevance),
                    format_percent(event.sentiment),
                    format_score(event.importance),
                    format_score(event.novelty),
                    format_score(event.author_influence),
                    event.event_type or "N/A",
                    format_score(event.estimated_impact),
                ]
                for event in events
            ]
            self._set_rows(page, rows)
            return
        rows = [
            [
                event.title,
                event.source or "N/A",
                event.occurred_at.astimezone().strftime("%Y-%m-%d %H:%M"),
                ", ".join(event.assets) or "N/A",
                format_percent(event.sentiment),
                format_score(event.relevance),
                format_score(event.importance),
                event.event_type or "Not available",
                format_score(event.novelty),
                format_score(event.estimated_impact),
                event.impact_maturity or "Pending",
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
