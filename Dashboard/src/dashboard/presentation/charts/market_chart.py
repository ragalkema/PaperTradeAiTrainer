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
        self.plot = pg.PlotWidget(background="#11161f")
        self.plot.showGrid(x=True, y=True, alpha=0.09)
        self.plot.setLabel("left", "Price", units="EUR")
        self.plot.setLabel("bottom", "Recent observations")
        self.plot.getAxis("left").setTextPen(QColor("#7d899c"))
        self.plot.getAxis("bottom").setTextPen(QColor("#7d899c"))
        layout.addWidget(self.plot)
        self.setMinimumHeight(275)

    def set_series(
        self,
        candles: tuple[tuple[datetime, Decimal, Decimal, Decimal, Decimal, Decimal], ...],
    ) -> None:
        self.plot.clear()
        if not candles:
            self.plot.setTitle("Waiting for market history", color="#7d899c", size="11pt")
            return
        self.plot.setTitle("")
        closes = [float(item[4]) for item in candles]
        self.plot.plot(
            list(range(len(closes))),
            closes,
            pen=pg.mkPen("#4f7cff", width=2),
            symbol="o" if len(closes) < 20 else None,
            symbolSize=4,
        )
