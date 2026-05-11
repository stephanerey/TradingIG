"""Candlestick chart foundation using pyqtgraph."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

import pyqtgraph as pg
from PyQt5 import QtCore, QtGui, QtWidgets

from trading_ig_assistant.domain.market_data import PriceSeries, Quote


@dataclass(frozen=True)
class OhlcBar:
    timestamp_ms: int
    open: float
    high: float
    low: float
    close: float
    volume: float | None = None


class ChartDataModel:
    def __init__(self, bars: list[OhlcBar] | None = None) -> None:
        self._bars = bars or []

    @property
    def bars(self) -> list[OhlcBar]:
        return list(self._bars)

    def set_bars(self, bars: list[OhlcBar]) -> None:
        self._bars = list(bars)

    @classmethod
    def sample(cls, anchor_price: float | None = None) -> ChartDataModel:
        return cls(_build_placeholder_bars(anchor_price or 100.0))

    @classmethod
    def from_price_series(
        cls,
        series: PriceSeries,
        anchor_price: float | None = None,
    ) -> ChartDataModel:
        bars = _bars_from_price_series(series, anchor_price=anchor_price)
        if not bars and anchor_price is not None:
            bars = _build_placeholder_bars(anchor_price)
        return cls(bars)

    def resampled(self, interval_seconds: int) -> list[OhlcBar]:
        if interval_seconds <= 1:
            return self.bars
        return _resample_bars(self.bars, interval_seconds)


class CandlestickItem(pg.GraphicsObject):
    def __init__(self, bars: list[OhlcBar], bar_width_seconds: float) -> None:
        super().__init__()
        self._picture = QtGui.QPicture()
        self._generate_picture(bars, bar_width_seconds)

    def _generate_picture(self, bars: list[OhlcBar], bar_width_seconds: float) -> None:
        painter = QtGui.QPainter(self._picture)
        candle_width = max(bar_width_seconds * 0.33, 20.0)
        for bar in bars:
            color = QtGui.QColor("#0f7b45" if bar.close >= bar.open else "#a61b1b")
            painter.setPen(pg.mkPen(color))
            painter.setBrush(pg.mkBrush(color))
            painter.drawLine(
                QtCore.QPointF(bar.timestamp_ms / 1000.0, bar.low),
                QtCore.QPointF(bar.timestamp_ms / 1000.0, bar.high),
            )
            top = max(bar.open, bar.close)
            bottom = min(bar.open, bar.close)
            painter.drawRect(
                QtCore.QRectF(
                    bar.timestamp_ms / 1000.0 - candle_width / 2,
                    bottom,
                    candle_width,
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
        self._source_model = ChartDataModel(list(self._model.bars))
        self._live_price_line: pg.InfiniteLine | None = None
        self._last_quote: Quote | None = None
        self._selected_anchor_price: float | None = None
        self._current_interval_seconds = 60
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
        self.resolution_combo = QtWidgets.QComboBox()
        for label, interval_seconds in CHART_RESOLUTIONS:
            self.resolution_combo.addItem(label, interval_seconds)
        self.resolution_combo.currentIndexChanged.connect(self._on_resolution_changed)
        self.resolution_combo.setMinimumWidth(110)

        header.addWidget(self.product_label, 0, 0, 1, 2)
        header.addWidget(self.stream_status_label, 0, 2, 1, 1)
        header.addWidget(self.resolution_combo, 0, 3, 1, 1)
        header.addWidget(self.bid_label, 1, 0)
        header.addWidget(self.offer_label, 1, 1)
        header.addWidget(self.change_label, 1, 2)
        header.addWidget(self.percent_change_label, 1, 3)

        self._plot = pg.PlotWidget(axisItems={"bottom": pg.DateAxisItem(orientation="bottom")})
        self._plot.setBackground("#fbfaf7")
        self._plot.showGrid(x=True, y=True, alpha=0.25)
        self._plot.setLabel("left", "Price")
        self._plot.setLabel("bottom", "Time")
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
        if self._model.bars:
            self._plot.addItem(CandlestickItem(self._model.bars, self._bar_width_seconds()))
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
            first_ts = bars[0].timestamp_ms / 1000.0
            last_ts = bars[-1].timestamp_ms / 1000.0
            span = max(last_ts - first_ts, 60.0)
            padding = span * 0.08
            self._plot.setXRange(first_ts - padding, last_ts + padding)
            lows = [bar.low for bar in bars]
            highs = [bar.high for bar in bars]
            low = min(lows)
            high = max(highs)
            y_padding = max((high - low) * 0.12, 1.0)
            self._plot.setYRange(low - y_padding, high + y_padding)

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
        self._selected_anchor_price = _product_anchor_price(product)
        self._refresh_snapshot_labels(product)
        if self._selected_anchor_price is not None and not self._source_model.bars:
            self._source_model = ChartDataModel.sample(self._selected_anchor_price)
            self._apply_resolution()
        elif self._source_model.bars:
            self._apply_resolution()

    def set_stream_status(self, status: str) -> None:
        self.stream_status_label.setText(f"Stream: {status}")

    def set_live_quote(self, quote: Quote | None) -> None:
        self._last_quote = quote
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
        live_value = quote.offer if quote.offer is not None else quote.bid
        if live_value is not None:
            if self._is_out_of_view(live_value):
                self._source_model = ChartDataModel.sample(live_value)
                self._apply_resolution()
            if self._live_price_line is not None:
                self._live_price_line.setValue(live_value)

    def set_price_series(self, series: PriceSeries, anchor_price: float | None = None) -> None:
        self._source_model = ChartDataModel.from_price_series(series, anchor_price=anchor_price)
        self._apply_resolution()

    def _refresh_snapshot_labels(self, product: object) -> None:
        self.bid_label.setText(f"Vente: {_format_number(getattr(product, 'bid', None))}")
        self.offer_label.setText(f"Achat: {_format_number(getattr(product, 'offer', None))}")
        self.change_label.setText(
            f"Variation: {_format_signed_number(getattr(product, 'net_change', None))}"
        )
        self.percent_change_label.setText(
            f"% Variation: {_format_signed_number(getattr(product, 'percent_change', None))}"
        )

    def _on_resolution_changed(self, _index: int) -> None:
        self._current_interval_seconds = int(self.resolution_combo.currentData() or 60)
        self._apply_resolution()

    def _apply_resolution(self) -> None:
        if not self._source_model.bars:
            return
        bars = self._source_model.resampled(self._current_interval_seconds)
        self.set_bars(bars)
        if self._last_quote is not None:
            self.set_live_quote(self._last_quote)

    def current_interval_seconds(self) -> int:
        return self._current_interval_seconds

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

    def _is_out_of_view(self, value: float) -> bool:
        if not self._model.bars:
            return True
        lows = [bar.low for bar in self._model.bars]
        highs = [bar.high for bar in self._model.bars]
        low = min(lows)
        high = max(highs)
        span = max(high - low, 1.0)
        buffer = span * 0.5
        return value < low - buffer or value > high + buffer

    def _bar_width_seconds(self) -> float:
        return max(self._current_interval_seconds * 0.65, 20.0)


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


def _product_anchor_price(product: object) -> float | None:
    for field_name in ("offer", "bid", "strike", "ko_level"):
        value = getattr(product, field_name, None)
        if isinstance(value, (int, float)) and value > 0:
            return float(value)
    return None


def _build_placeholder_bars(anchor_price: float) -> list[OhlcBar]:
    step = max(abs(anchor_price) * 0.00015, 0.5)
    now = int(datetime.now(tz=UTC).timestamp())
    patterns = [
        (-2.8, -1.1, -3.8, 0.6),
        (-1.2, -2.0, -2.8, 1.0),
        (-2.1, 1.0, -3.2, 2.0),
        (0.8, -0.4, -0.8, 2.0),
        (-0.2, 2.1, -1.0, 3.0),
    ]
    bars: list[OhlcBar] = []
    for index, (open_delta, close_delta, low_delta, high_delta) in enumerate(patterns):
        open_price = anchor_price + open_delta * step
        close_price = anchor_price + close_delta * step
        low_price = min(open_price, close_price) + low_delta * step
        high_price = max(open_price, close_price) + high_delta * step
        bars.append(
            OhlcBar(
                timestamp_ms=(now - (len(patterns) - index) * 300) * 1000,
                open=open_price,
                high=max(high_price, open_price, close_price),
                low=min(low_price, open_price, close_price),
                close=close_price,
            )
        )
    return bars


def _bars_from_price_series(
    series: PriceSeries,
    anchor_price: float | None = None,
) -> list[OhlcBar]:
    bars: list[OhlcBar] = []
    for index, price in enumerate(series.prices):
        timestamp_ms = _parse_price_timestamp_ms(price)
        open_price = _first_float_value(
            price,
            ["openPrice", "open", "open_price", "OFR_OPEN", "BID_OPEN"],
        )
        high_price = _first_float_value(
            price,
            ["highPrice", "high", "high_price", "OFR_HIGH", "BID_HIGH"],
        )
        low_price = _first_float_value(
            price,
            ["lowPrice", "low", "low_price", "OFR_LOW", "BID_LOW"],
        )
        close_price = _first_float_value(
            price,
            [
                "closePrice",
                "close",
                "close_price",
                "OFR_CLOSE",
                "BID_CLOSE",
                "bid",
                "offer",
            ],
        )
        if close_price is None:
            continue
        if open_price is None:
            open_price = close_price
        if high_price is None:
            high_price = max(open_price, close_price)
        if low_price is None:
            low_price = min(open_price, close_price)
        bars.append(
            OhlcBar(
                timestamp_ms=timestamp_ms if timestamp_ms is not None else index * 60_000,
                open=open_price,
                high=max(high_price, open_price, close_price),
                low=min(low_price, open_price, close_price),
                close=close_price,
                volume=_first_float_value(price, ["volume", "volumeTraded", "LTV", "TTV"]),
            )
        )
    return bars


def _parse_price_timestamp_ms(price: dict[str, object]) -> int | None:
    raw_timestamp = None
    for key in ("snapshotTimeUTC", "snapshotTime", "snapshot_time", "timestamp", "UTM"):
        value = price.get(key)
        if value not in (None, ""):
            raw_timestamp = value
            break
    if raw_timestamp is None:
        return None
    if isinstance(raw_timestamp, (int, float)):
        return int(float(raw_timestamp))
    text = str(raw_timestamp).strip()
    parsed = _parse_datetime_string(text)
    if parsed is not None:
        return int(parsed.timestamp() * 1000)
    return None


def _parse_datetime_string(text: str) -> datetime | None:
    patterns = [
        "%Y/%m/%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%SZ",
    ]
    for pattern in patterns:
        try:
            return datetime.strptime(text, pattern).replace(tzinfo=UTC)
        except ValueError:
            continue
    return None


def _first_float_value(payload: dict[str, object], keys: list[str]) -> float | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, dict):
            for nested_key in ("value", "price", "bid", "offer", "mid", "close"):
                candidate = value.get(nested_key)
                if candidate is not None:
                    value = candidate
                    break
        if value is None:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _resample_bars(bars: list[OhlcBar], interval_seconds: int) -> list[OhlcBar]:
    if interval_seconds <= 1:
        return list(bars)
    grouped: dict[int, list[OhlcBar]] = {}
    for bar in bars:
        bucket = (bar.timestamp_ms // 1000 // interval_seconds) * interval_seconds
        grouped.setdefault(bucket, []).append(bar)
    resampled: list[OhlcBar] = []
    for bucket in sorted(grouped):
        group = grouped[bucket]
        if not group:
            continue
        resampled.append(
            OhlcBar(
                timestamp_ms=bucket * 1000,
                open=group[0].open,
                high=max(bar.high for bar in group),
                low=min(bar.low for bar in group),
                close=group[-1].close,
                volume=sum(bar.volume or 0.0 for bar in group) or None,
            )
        )
    return resampled


CHART_RESOLUTIONS: list[tuple[str, int]] = [
    ("1 Min", 60),
    ("5 Min", 300),
    ("10 Min", 600),
    ("15 Min", 900),
    ("30 Min", 1800),
    ("1 Hour", 3600),
    ("2 Hours", 7200),
    ("4 Hours", 14_400),
    ("1 Day", 86_400),
]
