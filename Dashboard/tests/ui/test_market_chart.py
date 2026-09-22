import os
from datetime import UTC, datetime, timedelta
from decimal import Decimal

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from dashboard.presentation.charts import MarketChart
from PySide6.QtWidgets import QApplication


@pytest.mark.unit
def test_market_chart_keeps_full_series_visible_and_resettable() -> None:
    application = QApplication.instance() or QApplication([])
    chart = MarketChart()
    start = datetime(2026, 1, 1, tzinfo=UTC)
    candles = tuple(
        (
            start + timedelta(hours=index),
            Decimal("100"),
            Decimal("110"),
            Decimal("90"),
            Decimal(str(close)),
            Decimal("5"),
        )
        for index, close in enumerate((100, 104, 98, 109))
    )

    chart.set_series(candles)
    chart.plot.setRange(xRange=(1, 2), yRange=(101, 105), padding=0)
    chart.reset_button.click()
    application.processEvents()

    x_range, y_range = chart.plot.viewRange()
    assert x_range == pytest.approx([0, 3])
    assert y_range[0] < 98
    assert y_range[1] > 109
    assert chart.plot.plotItem.vb.state["limits"]["xLimits"] == [0.0, 3.0]
