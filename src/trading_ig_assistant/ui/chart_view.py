"""Candlestick chart foundation using pyqtgraph."""

from __future__ import annotations

from dataclasses import dataclass

import pyqtgraph as pg
from PyQt5 import QtCore, QtGui, QtWidgets


@dataclass(frozen=True)
class OhlcBar:
    index: int
    open: float
    high: float
    low: float
    close: float


class ChartDataModel:
    def __init__(self, bars: list[OhlcBar] | None = None) -> None:
        self._bars = bars or []

    @property
    def bars(self) -> list[OhlcBar]:
        return list(self._bars)

    def set_bars(self, bars: list[OhlcBar]) -> None:
        self._bars = list(bars)

    @classmethod
    def sample(cls) -> ChartDataModel:
        return cls(
            [
                OhlcBar(0, 100.0, 104.0, 98.0, 103.0),
                OhlcBar(1, 103.0, 105.0, 101.0, 102.0),
                OhlcBar(2, 102.0, 108.0, 101.0, 107.0),
                OhlcBar(3, 107.0, 109.0, 104.0, 105.0),
                OhlcBar(4, 105.0, 111.0, 104.0, 110.0),
            ]
        )


class CandlestickItem(pg.GraphicsObject):
    def __init__(self, bars: list[OhlcBar]) -> None:
        super().__init__()
        self._picture = QtGui.QPicture()
        self._generate_picture(bars)

    def _generate_picture(self, bars: list[OhlcBar]) -> None:
        painter = QtGui.QPainter(self._picture)
        candle_width = 0.35
        for bar in bars:
            color = QtGui.QColor("#0f7b45" if bar.close >= bar.open else "#a61b1b")
            painter.setPen(pg.mkPen(color))
            painter.setBrush(pg.mkBrush(color))
            painter.drawLine(
                QtCore.QPointF(bar.index, bar.low),
                QtCore.QPointF(bar.index, bar.high),
            )
            top = max(bar.open, bar.close)
            bottom = min(bar.open, bar.close)
            painter.drawRect(
                QtCore.QRectF(
                    bar.index - candle_width,
                    bottom,
                    candle_width * 2,
                    max(top - bottom, 0.01),
                )
            )
        painter.end()

    def paint(self, painter: QtGui.QPainter, *_args: object) -> None:
        painter.drawPicture(0, 0, self._picture)

    def boundingRect(self) -> QtCore.QRectF:
        return QtCore.QRectF(self._picture.boundingRect())


class ChartView(QtWidgets.QWidget):
    def __init__(
        self,
        model: ChartDataModel | None = None,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._model = model or ChartDataModel.sample()
        layout = QtWidgets.QVBoxLayout(self)
        self._plot = pg.PlotWidget()
        self._plot.setBackground("#fbfaf7")
        self._plot.showGrid(x=True, y=True, alpha=0.25)
        self._plot.setLabel("left", "Price")
        self._plot.setLabel("bottom", "Bar")
        layout.addWidget(self._plot)
        self.set_bars(self._model.bars)

    def set_bars(self, bars: list[OhlcBar]) -> None:
        self._model.set_bars(bars)
        self._plot.clear()
        self._plot.addItem(CandlestickItem(self._model.bars))
        if bars:
            last_close = bars[-1].close
            self._add_level("Entry", last_close, "#254f8f")
            self._add_level("Stop", last_close * 0.98, "#a61b1b")
            self._add_level("Limit", last_close * 1.03, "#0f7b45")
            self._add_level("KO", last_close * 0.95, "#6f42c1")
            self._plot.setXRange(max(0, bars[0].index - 1), bars[-1].index + 1)

    def _add_level(self, label: str, value: float, color: str) -> None:
        line = pg.InfiniteLine(
            pos=value,
            angle=0,
            pen=pg.mkPen(color, width=1.5, style=QtCore.Qt.DashLine),
            label=label,
            labelOpts={"position": 0.92, "color": color},
        )
        self._plot.addItem(line)
