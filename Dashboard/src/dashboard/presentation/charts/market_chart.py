"""A lightweight price/volume chart suitable for bounded recent windows."""

from datetime import datetime
from decimal import Decimal

import pyqtgraph as pg  # type: ignore[import-untyped]
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget


class MarketChart(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        toolbar = QHBoxLayout()
        hint = QLabel("Scrollen en slepen zijn begrensd om de koers zichtbaar te houden")
        hint.setObjectName("muted")
        self.reset_button = QPushButton("Reset weergave")
        self.reset_button.setObjectName("chartReset")
        toolbar.addWidget(hint)
        toolbar.addStretch()
        toolbar.addWidget(self.reset_button)
        layout.addLayout(toolbar)
        self.plot = pg.PlotWidget(background="#11161f")
        self.plot.showGrid(x=True, y=True, alpha=0.09)
        self.plot.setLabel("left", "Price", units="EUR")
        self.plot.setLabel("bottom", "Recent observations")
        self.plot.getAxis("left").setTextPen(QColor("#7d899c"))
        self.plot.getAxis("bottom").setTextPen(QColor("#7d899c"))
        self.plot.setMenuEnabled(False)
        self.plot.hideButtons()
        layout.addWidget(self.plot)
        self.setMinimumHeight(275)
        self._view_range: tuple[tuple[float, float], tuple[float, float]] | None = None
        self.reset_button.clicked.connect(self.reset_view)

    def set_series(
        self,
        candles: tuple[tuple[datetime, Decimal, Decimal, Decimal, Decimal, Decimal], ...],
    ) -> None:
        self.plot.clear()
        self._view_range = None
        if not candles:
            self.plot.setTitle("Waiting for market history", color="#7d899c", size="11pt")
            return
        self.plot.setTitle("")
        closes = [float(item[4]) for item in candles]
        x_min, x_max = 0.0, float(max(1, len(closes) - 1))
        price_min, price_max = min(closes), max(closes)
        price_span = max(price_max - price_min, abs(price_max) * 0.01, 0.01)
        y_min = price_min - price_span * 0.12
        y_max = price_max + price_span * 0.12
        self._view_range = ((x_min, x_max), (y_min, y_max))
        self.plot.setLimits(
            xMin=x_min,
            xMax=x_max,
            minXRange=min(1.0, x_max - x_min),
            maxXRange=max(1.0, x_max - x_min),
            yMin=y_min,
            yMax=y_max,
            minYRange=price_span * 0.05,
            maxYRange=y_max - y_min,
        )
        self.plot.plot(
            list(range(len(closes))),
            closes,
            pen=pg.mkPen("#4f7cff", width=2),
            symbol="o" if len(closes) < 20 else None,
            symbolSize=4,
        )
        self.reset_view()

    def reset_view(self) -> None:
        """Restore the full bounded data window after any user interaction."""
        if self._view_range is None:
            return
        x_range, y_range = self._view_range
        self.plot.setRange(xRange=x_range, yRange=y_range, padding=0)
