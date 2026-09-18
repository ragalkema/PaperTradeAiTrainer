"""A lightweight price/volume chart suitable for bounded recent windows."""

from datetime import datetime
from decimal import Decimal

import pyqtgraph as pg  # type: ignore[import-untyped]
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QVBoxLayout, QWidget


class MarketChart(QWidget):
    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.plot = pg.PlotWidget(background="#101925")
        self.plot.showGrid(x=True, y=True, alpha=0.12)
        self.plot.setLabel("left", "Price", units="EUR")
        self.plot.setLabel("bottom", "Recent observations")
        self.plot.getAxis("left").setTextPen(QColor("#8392a5"))
        self.plot.getAxis("bottom").setTextPen(QColor("#8392a5"))
        layout.addWidget(self.plot)
        self.setMinimumHeight(275)

    def set_series(
        self,
        candles: tuple[tuple[datetime, Decimal, Decimal, Decimal, Decimal, Decimal], ...],
    ) -> None:
        self.plot.clear()
        if not candles:
            self.plot.setTitle("Waiting for market history", color="#8392a5", size="11pt")
            return
        self.plot.setTitle("")
        closes = [float(item[4]) for item in candles]
        self.plot.plot(
            list(range(len(closes))),
            closes,
            pen=pg.mkPen("#2cc6f4", width=2),
            symbol="o" if len(closes) < 20 else None,
            symbolSize=4,
        )
