"""Candlestick chart foundation using pyqtgraph."""

from __future__ import annotations

from dataclasses import dataclass

import pyqtgraph as pg
from PyQt5 import QtCore, QtGui, QtWidgets

from trading_ig_assistant.domain.market_data import Quote


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
        self._live_price_line: pg.InfiniteLine | None = None
        layout = QtWidgets.QVBoxLayout(self)
        header = QtWidgets.QGridLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setHorizontalSpacing(8)
        header.setVerticalSpacing(6)

        self.product_label = QtWidgets.QLabel("No product selected")
        self.product_label.setStyleSheet("font-weight: 700; font-size: 14px;")
        self.stream_status_label = _chip_label("Stream", "DISCONNECTED")
        self.bid_label = _chip_label("Vente", "-")
        self.offer_label = _chip_label("Achat", "-")
        self.change_label = _chip_label("Variation", "-")
        self.percent_change_label = _chip_label("% Variation", "-")

        header.addWidget(self.product_label, 0, 0, 1, 2)
        header.addWidget(self.stream_status_label, 0, 2, 1, 1)
        header.addWidget(self.bid_label, 1, 0)
        header.addWidget(self.offer_label, 1, 1)
        header.addWidget(self.change_label, 1, 2)
        header.addWidget(self.percent_change_label, 1, 3)

        self._plot = pg.PlotWidget()
        self._plot.setBackground("#fbfaf7")
        self._plot.showGrid(x=True, y=True, alpha=0.25)
        self._plot.setLabel("left", "Price")
        self._plot.setLabel("bottom", "Bar")
        self._plot.setMinimumHeight(420)
        self._plot.setMouseEnabled(x=False, y=False)
        self._plot.hideButtons()
        self._plot.setMenuEnabled(False)

        layout.addLayout(header)
        layout.addWidget(self._plot)
        self.set_bars(self._model.bars)

    def set_bars(self, bars: list[OhlcBar]) -> None:
        self._model.set_bars(bars)
        self._plot.clear()
        self._plot.addItem(CandlestickItem(self._model.bars))
        self._live_price_line = None
        if bars:
            last_close = bars[-1].close
            self._add_level("Entry", last_close, "#254f8f")
            self._add_level("Stop", last_close * 0.98, "#a61b1b")
            self._add_level("Limit", last_close * 1.03, "#0f7b45")
            self._add_level("KO", last_close * 0.95, "#6f42c1")
            self._live_price_line = self._add_level(
                "Live",
                last_close,
                "#0b6bcb",
                dashed=False,
            )
            self._plot.setXRange(max(0, bars[0].index - 1), bars[-1].index + 1)

    def set_selected_product(self, product: object) -> None:
        name = getattr(product, "name", "Unknown product")
        epic = getattr(product, "epic", "")
        product_type = getattr(getattr(product, "product_type", None), "value", "")
        direction = getattr(getattr(product, "direction", None), "value", "")
        label_parts = [name]
        if epic:
            label_parts.append(f"({epic})")
        if product_type or direction:
            label_parts.append(f"{product_type} {direction}".strip())
        self.product_label.setText(" ".join(part for part in label_parts if part))

    def set_stream_status(self, status: str) -> None:
        self.stream_status_label.setText(f"Stream: {status}")

    def set_live_quote(self, quote: Quote | None) -> None:
        if quote is None:
            self.bid_label.setText("Vente: -")
            self.offer_label.setText("Achat: -")
            self.change_label.setText("Variation: -")
            self.percent_change_label.setText("% Variation: -")
            return
        self.bid_label.setText(f"Vente: {_format_number(quote.bid)}")
        self.offer_label.setText(f"Achat: {_format_number(quote.offer)}")
        self.change_label.setText(f"Variation: {_format_signed_number(quote.net_change)}")
        self.percent_change_label.setText(
            f"% Variation: {_format_signed_number(quote.percent_change)}"
        )
        if self._live_price_line is not None:
            live_value = quote.offer if quote.offer is not None else quote.bid
            if live_value is not None:
                self._live_price_line.setValue(live_value)

    def _add_level(
        self,
        label: str,
        value: float,
        color: str,
        *,
        dashed: bool = True,
    ) -> pg.InfiniteLine:
        line = pg.InfiniteLine(
            pos=value,
            angle=0,
            pen=pg.mkPen(
                color,
                width=1.5,
                style=QtCore.Qt.DashLine if dashed else QtCore.Qt.SolidLine,
            ),
            label=label,
            labelOpts={"position": 0.92, "color": color},
        )
        self._plot.addItem(line)
        return line


def _format_number(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:g}"


def _format_signed_number(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:+g}"


def _chip_label(label: str, value: str) -> QtWidgets.QLabel:
    chip = QtWidgets.QLabel(f"{label}: {value}")
    if label == "Stream":
        chip.setMinimumWidth(210)
        chip.setAlignment(QtCore.Qt.AlignCenter)
    chip.setStyleSheet(
        "QLabel {"
        "color: #203040;"
        "background: #e9f0f7;"
        "border: 1px solid #c6d3df;"
        "border-radius: 9px;"
        "padding: 4px 9px;"
        "font-weight: 600;"
        "}"
    )
    return chip
