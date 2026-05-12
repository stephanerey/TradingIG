"""Candlestick chart foundation using pyqtgraph."""

from __future__ import annotations

from bisect import bisect_left
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum

import pyqtgraph as pg
from PyQt5 import QtCore, QtGui, QtWidgets

from trading_ig_assistant.domain.market_data import (
    Candle,
    ChartCandleUpdate,
    ChartPriceBasis,
    PriceSeries,
    Quote,
)
from trading_ig_assistant.services.candle_aggregation_service import (
    chart_update_ohlc,
    live_price_for_quote,
    price_ohlc_from_payload,
)


@dataclass(frozen=True)
class OhlcBar:
    timestamp_ms: int
    open: float
    high: float
    low: float
    close: float
    volume: float | None = None
    display_x: float | None = None


class TimeAxisMode(StrEnum):
    COMPRESSED = "compressed"
    REAL = "real"


class ChartDataModel:
    def __init__(
        self,
        bars: list[OhlcBar] | None = None,
        *,
        is_placeholder: bool = False,
    ) -> None:
        self._bars = bars or []
        self._is_placeholder = is_placeholder

    @property
    def bars(self) -> list[OhlcBar]:
        return list(self._bars)

    @property
    def is_placeholder(self) -> bool:
        return self._is_placeholder

    def set_bars(self, bars: list[OhlcBar], *, placeholder: bool | None = None) -> None:
        self._bars = list(bars)
        if placeholder is not None:
            self._is_placeholder = placeholder

    @classmethod
    def sample(cls, anchor_price: float | None = None) -> ChartDataModel:
        return cls(_build_placeholder_bars(anchor_price or 100.0, count=60), is_placeholder=True)

    @classmethod
    def from_price_series(
        cls,
        series: PriceSeries,
        *,
        price_basis: ChartPriceBasis = ChartPriceBasis.MID,
        anchor_price: float | None = None,  # kept for API compatibility
    ) -> ChartDataModel:
        del anchor_price
        bars = _bars_from_price_series(series, price_basis=price_basis)
        return cls(bars, is_placeholder=False)

    def resampled(self, interval_seconds: int) -> list[OhlcBar]:
        if interval_seconds <= 1:
            return self.bars
        return _resample_bars(self.bars, interval_seconds)


class ChartAxisItem(pg.AxisItem):
    def __init__(
        self,
        *,
        timestamp_lookup: Callable[[float], int | None],
        mode_getter: Callable[[], TimeAxisMode],
        interval_getter: Callable[[], int],
        orientation: str = "bottom",
    ) -> None:
        super().__init__(orientation=orientation)
        self._timestamp_lookup = timestamp_lookup
        self._mode_getter = mode_getter
        self._interval_getter = interval_getter

    def tickStrings(self, values, scale, spacing):  # noqa: N802
        del scale, spacing
        labels: list[str] = []
        interval_seconds = self._interval_getter()
        for value in values:
            timestamp_ms = self._timestamp_lookup(float(value))
            if timestamp_ms is None:
                labels.append("")
                continue
            timestamp = datetime.fromtimestamp(timestamp_ms / 1000.0).astimezone()
            labels.append(_format_axis_timestamp(timestamp, interval_seconds))
        return labels


class CandlestickItem(pg.GraphicsObject):
    def __init__(self, bars: list[OhlcBar], bar_width: float) -> None:
        super().__init__()
        self._picture = QtGui.QPicture()
        self._generate_picture(bars, bar_width)

    def _generate_picture(self, bars: list[OhlcBar], bar_width: float) -> None:
        painter = QtGui.QPainter(self._picture)
        candle_width = max(bar_width, 0.72)
        for bar in bars:
            x_value = _bar_x_value(bar)
            color = QtGui.QColor("#0f7b45" if bar.close >= bar.open else "#a61b1b")
            painter.setPen(pg.mkPen(color))
            painter.setBrush(pg.mkBrush(color))
            painter.drawLine(
                QtCore.QPointF(x_value, bar.low),
                QtCore.QPointF(x_value, bar.high),
            )
            top = max(bar.open, bar.close)
            bottom = min(bar.open, bar.close)
            painter.drawRect(
                QtCore.QRectF(
                    x_value - candle_width / 2,
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


class ChartPlotWidget(pg.PlotWidget):
    zoom_requested = QtCore.pyqtSignal(float, float)
    pan_requested = QtCore.pyqtSignal(float)

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self._dragging = False
        self._last_drag_x: float | None = None

    def wheelEvent(self, event: QtGui.QWheelEvent) -> None:  # noqa: N802
        delta = event.angleDelta().y()
        if delta == 0:
            super().wheelEvent(event)
            return
        scene_pos = self.mapToScene(event.pos())
        view_point = self.plotItem.vb.mapSceneToView(scene_pos)
        self.zoom_requested.emit(0.85 if delta > 0 else 1.15, float(view_point.x()))
        event.accept()

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:  # noqa: N802
        if event.button() == QtCore.Qt.LeftButton:
            scene_pos = self.mapToScene(event.pos())
            if self.plotItem.vb.sceneBoundingRect().contains(scene_pos):
                view_point = self.plotItem.vb.mapSceneToView(scene_pos)
                self._dragging = True
                self._last_drag_x = float(view_point.x())
                self.setCursor(QtCore.Qt.ClosedHandCursor)
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:  # noqa: N802
        if self._dragging and self._last_drag_x is not None:
            scene_pos = self.mapToScene(event.pos())
            view_point = self.plotItem.vb.mapSceneToView(scene_pos)
            current_x = float(view_point.x())
            delta_x = current_x - self._last_drag_x
            if abs(delta_x) > 0:
                self.pan_requested.emit(delta_x)
            self._last_drag_x = current_x
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:  # noqa: N802
        if event.button() == QtCore.Qt.LeftButton and self._dragging:
            self._dragging = False
            self._last_drag_x = None
            self.unsetCursor()
            event.accept()
            return
        super().mouseReleaseEvent(event)


class ChartView(QtWidgets.QWidget):
    resolution_changed = QtCore.pyqtSignal(int)
    history_range_changed = QtCore.pyqtSignal(str)
    price_basis_changed = QtCore.pyqtSignal(object)

    def __init__(
        self,
        model: ChartDataModel | None = None,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._model = model or ChartDataModel()
        self._source_model = ChartDataModel(list(self._model.bars), is_placeholder=False)
        self._last_price_series: PriceSeries | None = None
        self._live_price_line: pg.InfiniteLine | None = None
        self._live_price_label: QtWidgets.QLabel | None = None
        self._hover_vline: pg.InfiniteLine | None = None
        self._hover_hline: pg.InfiniteLine | None = None
        self._hover_label: pg.TextItem | None = None
        self._hover_state_bar_timestamp_ms: int | None = None
        self._hover_state_x_value: float | None = None
        self._hover_state_y_value: float | None = None
        self._last_quote: Quote | None = None
        self._selected_anchor_price: float | None = None
        self._display_bars: list[OhlcBar] = []
        self._compressed_timestamps: list[int] = []
        self._compressed_index_by_timestamp: dict[int, int] = {}
        self._view_center_x: float | None = None
        self._view_span_x: float | None = None
        self._manual_zoom = False
        self._current_interval_seconds = 300
        self._current_range_key = "1M"
        self._current_price_basis = ChartPriceBasis.MID
        self._time_axis_mode = TimeAxisMode.COMPRESSED

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
        default_resolution_index = self.resolution_combo.findData(300)
        if default_resolution_index >= 0:
            self.resolution_combo.setCurrentIndex(default_resolution_index)
        self.resolution_combo.currentIndexChanged.connect(self._on_resolution_changed)
        self.resolution_combo.setMinimumWidth(110)

        self.range_combo = QtWidgets.QComboBox()
        for label in HISTORY_RANGE_KEYS:
            self.range_combo.addItem(label, label)
        default_range_index = self.range_combo.findData("1M")
        if default_range_index >= 0:
            self.range_combo.setCurrentIndex(default_range_index)
        self.range_combo.currentIndexChanged.connect(self._on_range_changed)
        self.range_combo.setMinimumWidth(80)

        self.price_basis_combo = QtWidgets.QComboBox()
        self.price_basis_combo.addItem("Bid", ChartPriceBasis.BID)
        self.price_basis_combo.addItem("Mid", ChartPriceBasis.MID)
        self.price_basis_combo.addItem("Ask", ChartPriceBasis.ASK)
        default_basis_index = self.price_basis_combo.findData(ChartPriceBasis.MID)
        if default_basis_index >= 0:
            self.price_basis_combo.setCurrentIndex(default_basis_index)
        self.price_basis_combo.currentIndexChanged.connect(self._on_price_basis_changed)
        self.price_basis_combo.setMinimumWidth(90)

        self.axis_mode_combo = QtWidgets.QComboBox()
        self.axis_mode_combo.addItem("Compressed", TimeAxisMode.COMPRESSED)
        self.axis_mode_combo.addItem("Real", TimeAxisMode.REAL)
        self.axis_mode_combo.currentIndexChanged.connect(self._on_axis_mode_changed)
        self.axis_mode_combo.setMinimumWidth(110)

        self._current_interval_seconds = int(self.resolution_combo.currentData() or 300)
        self._current_range_key = str(self.range_combo.currentData() or "1M")
        self._current_price_basis = self.price_basis_combo.currentData() or ChartPriceBasis.MID
        self._time_axis_mode = self.axis_mode_combo.currentData() or TimeAxisMode.COMPRESSED

        header.addWidget(self.product_label, 0, 0, 1, 2)
        header.addWidget(self.stream_status_label, 0, 2, 1, 1)
        header.addWidget(self.resolution_combo, 0, 3, 1, 1)
        header.addWidget(self.range_combo, 0, 4, 1, 1)
        header.addWidget(self.price_basis_combo, 0, 5, 1, 1)
        header.addWidget(self.axis_mode_combo, 0, 6, 1, 1)
        header.addWidget(self.bid_label, 1, 0, 1, 2)
        header.addWidget(self.offer_label, 1, 2, 1, 2)
        header.addWidget(self.change_label, 1, 4, 1, 1)
        header.addWidget(self.percent_change_label, 1, 5, 1, 2)

        axis_item = ChartAxisItem(
            timestamp_lookup=self._timestamp_ms_for_x,
            mode_getter=self.current_time_axis_mode,
            interval_getter=self.current_interval_seconds,
        )
        self._plot = ChartPlotWidget(axisItems={"bottom": axis_item})
        self._plot.setBackground("#fbfaf7")
        self._plot.showGrid(x=True, y=True, alpha=0.25)
        self._plot.setLabel("left", "Price")
        self._plot.setLabel("bottom", "Time")
        self._plot.setMinimumHeight(420)
        self._plot.setMouseEnabled(x=False, y=False)
        self._plot.hideButtons()
        self._plot.setMenuEnabled(False)
        self._plot.getAxis("left").setWidth(112)
        self._plot.zoom_requested.connect(self._on_zoom_requested)
        self._plot.pan_requested.connect(self._on_pan_requested)
        self._plot.scene().sigMouseMoved.connect(self._on_mouse_moved)

        layout.addLayout(header)
        layout.addWidget(self._plot)

    def current_interval_seconds(self) -> int:
        return self._current_interval_seconds

    def current_range_key(self) -> str:
        return self._current_range_key

    def current_price_basis(self) -> ChartPriceBasis:
        return self._current_price_basis

    def current_time_axis_mode(self) -> TimeAxisMode:
        return self._time_axis_mode

    def display_bar_count(self) -> int:
        return len(self._display_bars)

    def set_bars(self, bars: list[OhlcBar]) -> None:
        self._source_model.set_bars(bars, placeholder=False)
        self._manual_zoom = False
        self._render_display_bars(self._source_model.bars)

    def set_candles(
        self,
        candles: tuple[Candle, ...] | list[Candle],
        *,
        preserve_view: bool = False,
    ) -> None:
        bars = _bars_from_candles(candles)
        self._source_model.set_bars(bars, placeholder=False)
        if not preserve_view:
            self._manual_zoom = False
        self._render_display_bars(self._source_model.bars)

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
        if self._source_model.bars:
            self._render_display_bars(self._source_model.bars)
        else:
            self._plot.clear()
            self._live_price_line = None
            self._detach_live_price_label()
            self._hover_vline = None
            self._hover_hline = None
            self._hover_label = None

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
        live_value = live_price_for_quote(quote, self._current_price_basis)
        if live_value is not None:
            if self._live_price_line is not None:
                self._live_price_line.setValue(live_value)
            if self._live_price_label is not None:
                self._live_price_label.setText(_format_number(live_value))
                self._position_live_price_label(live_value)

    def set_price_series(self, series: PriceSeries, anchor_price: float | None = None) -> None:
        self._last_price_series = series
        self._selected_anchor_price = anchor_price
        self._source_model = ChartDataModel.from_price_series(
            series,
            price_basis=self._current_price_basis,
            anchor_price=anchor_price,
        )
        self._manual_zoom = False
        self._render_display_bars(self._source_model.bars)

    def apply_chart_update(self, chart_update: ChartCandleUpdate) -> None:
        bar = _bar_from_chart_update(
            chart_update,
            interval_seconds=self._current_interval_seconds,
            price_basis=self._current_price_basis,
        )
        if bar is None:
            return
        if not self._source_model.bars:
            self._source_model = ChartDataModel([bar], is_placeholder=False)
        else:
            bars = list(self._source_model.bars)
            timestamps = [existing_bar.timestamp_ms for existing_bar in bars]
            index = bisect_left(timestamps, bar.timestamp_ms)
            if index < len(bars) and bars[index].timestamp_ms == bar.timestamp_ms:
                bars[index] = bar
            else:
                bars.insert(index, bar)
            self._source_model.set_bars(bars, placeholder=False)
        self._render_display_bars(self._source_model.bars)

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
        self._current_interval_seconds = int(self.resolution_combo.currentData() or 300)
        self._apply_resolution()
        self.resolution_changed.emit(self._current_interval_seconds)

    def _on_range_changed(self, _index: int) -> None:
        self._current_range_key = str(self.range_combo.currentData() or "1M")
        self.history_range_changed.emit(self._current_range_key)

    def _on_price_basis_changed(self, _index: int) -> None:
        price_basis = self.price_basis_combo.currentData() or ChartPriceBasis.MID
        if price_basis == self._current_price_basis:
            return
        self._current_price_basis = price_basis
        if self._last_price_series is not None:
            self._source_model = ChartDataModel.from_price_series(
                self._last_price_series,
                price_basis=self._current_price_basis,
                anchor_price=self._selected_anchor_price,
            )
        self._render_display_bars(self._source_model.bars)
        if self._last_quote is not None:
            self.set_live_quote(self._last_quote)
        self.price_basis_changed.emit(self._current_price_basis)

    def _on_axis_mode_changed(self, _index: int) -> None:
        self._time_axis_mode = self.axis_mode_combo.currentData() or TimeAxisMode.COMPRESSED
        self._render_display_bars(self._source_model.bars)

    def _apply_resolution(self) -> None:
        if not self._source_model.bars:
            return
        self._render_display_bars(self._source_model.bars)
        if self._last_quote is not None:
            self.set_live_quote(self._last_quote)

    def _on_zoom_requested(self, factor: float, anchor_x: float | None = None) -> None:
        if not self._display_bars:
            return
        if self._view_center_x is None or self._view_span_x is None:
            first_x = _bar_x_value(self._display_bars[0])
            last_x = _bar_x_value(self._display_bars[-1])
            self._view_center_x = (first_x + last_x) / 2
            self._view_span_x = max(last_x - first_x, _minimum_x_span(self._time_axis_mode))
        old_span = self._view_span_x
        old_min = self._view_center_x - old_span / 2
        old_max = self._view_center_x + old_span / 2
        self._manual_zoom = True
        new_span = max(old_span * factor, _minimum_x_span(self._time_axis_mode))
        if anchor_x is None or old_max <= old_min:
            self._view_span_x = new_span
        else:
            anchor_ratio = (anchor_x - old_min) / (old_max - old_min)
            anchor_ratio = max(0.0, min(anchor_ratio, 1.0))
            new_min = anchor_x - anchor_ratio * new_span
            new_max = new_min + new_span
            self._view_center_x = (new_min + new_max) / 2
            self._view_span_x = new_span
        self._apply_view_range()

    def _on_pan_requested(self, delta_x: float) -> None:
        if not self._display_bars:
            return
        if self._view_center_x is None or self._view_span_x is None:
            first_x = _bar_x_value(self._display_bars[0])
            last_x = _bar_x_value(self._display_bars[-1])
            self._view_center_x = (first_x + last_x) / 2
            self._view_span_x = max(last_x - first_x, _minimum_x_span(self._time_axis_mode))
        self._manual_zoom = True
        self._view_center_x -= delta_x
        self._apply_view_range()

    def _add_level(
        self,
        label: str | None,
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
        )
        if label is not None:
            line.label = label
            line.labelOpts = {"position": 0.92, "color": color}
        self._plot.addItem(line)
        return line

    def _render_display_bars(self, bars: list[OhlcBar]) -> None:
        self._model.set_bars(list(bars), placeholder=False)
        self._display_bars = _map_bars_for_display(bars, self._time_axis_mode)
        self._compressed_timestamps = [bar.timestamp_ms for bar in self._display_bars]
        self._compressed_index_by_timestamp = {
            bar.timestamp_ms: index for index, bar in enumerate(self._display_bars)
        }
        self._plot.clear()
        self._live_price_line = None
        self._detach_live_price_label()
        self._hover_vline = None
        self._hover_hline = None
        self._hover_label = None
        if not self._display_bars:
            return

        self._plot.addItem(CandlestickItem(self._display_bars, self._bar_width_units()))
        last_close = self._display_bars[-1].close
        self._add_level(None, last_close, "#254f8f")
        self._add_level("Stop", last_close * 0.98, "#a61b1b")
        self._add_level("Limit", last_close * 1.03, "#0f7b45")
        self._add_level("KO", last_close * 0.95, "#6f42c1")
        self._live_price_line = self._add_level(None, last_close, "#0b6bcb", dashed=False)
        self._live_price_label = _build_live_price_label(
            _format_number(last_close),
            "#0b6bcb",
            self._plot,
        )
        self._hover_vline = pg.InfiniteLine(
            angle=90,
            movable=False,
            pen=pg.mkPen("#3b4a5a", width=1),
        )
        self._hover_hline = pg.InfiniteLine(
            angle=0,
            movable=False,
            pen=pg.mkPen("#3b4a5a", width=1),
        )
        self._hover_label = _build_hover_label()
        self._plot.addItem(self._hover_vline)
        self._plot.addItem(self._hover_hline)
        self._plot.addItem(self._hover_label)
        if self._view_center_x is None or self._view_span_x is None or not self._manual_zoom:
            first_x = _bar_x_value(self._display_bars[0])
            last_x = _bar_x_value(self._display_bars[-1])
            span = max(last_x - first_x, _minimum_x_span(self._time_axis_mode))
            padding = span * 0.06
            self._view_center_x = (first_x + last_x) / 2
            self._view_span_x = max(span + padding * 2, _minimum_x_span(self._time_axis_mode))
        self._apply_view_range()
        self._position_live_price_label()
        self._restore_hover_state()

    def _apply_view_range(self) -> None:
        if not self._display_bars:
            return
        if self._view_center_x is None or self._view_span_x is None:
            first_x = _bar_x_value(self._display_bars[0])
            last_x = _bar_x_value(self._display_bars[-1])
            self._view_center_x = (first_x + last_x) / 2
            self._view_span_x = max(last_x - first_x, _minimum_x_span(self._time_axis_mode))
        half_span = self._view_span_x / 2
        left_padding, right_padding = _x_padding(
            self._time_axis_mode,
            self._current_interval_seconds,
        )
        self._plot.setXRange(
            self._view_center_x - half_span - left_padding,
            self._view_center_x + half_span + right_padding,
        )
        lows = [bar.low for bar in self._display_bars]
        highs = [bar.high for bar in self._display_bars]
        low = min(lows)
        high = max(highs)
        y_padding = max((high - low) * 0.12, 1.0)
        self._plot.setYRange(low - y_padding, high + y_padding)
        self._position_live_price_label()
        self._position_hover_label()

    def _position_live_price_label(self, live_value: float | None = None) -> None:
        if self._live_price_label is None or not self._display_bars:
            return
        if live_value is None:
            live_value = self._display_bars[-1].close
        view_box = self._plot.plotItem.vb
        left_x = view_box.viewRange()[0][0]
        scene_point = view_box.mapViewToScene(QtCore.QPointF(left_x, live_value))
        widget_point = self._plot.mapFromScene(scene_point.toPoint())
        self._live_price_label.adjustSize()
        axis_width = int(self._plot.getAxis("left").width())
        x_pos = max(axis_width - self._live_price_label.width() - 12, 6)
        y_pos = int(widget_point.y() - (self._live_price_label.height() / 2))
        y_pos = max(0, min(y_pos, self._plot.height() - self._live_price_label.height() - 2))
        self._live_price_label.move(x_pos, y_pos)
        self._live_price_label.raise_()
        self._live_price_label.show()

    def _position_hover_label(self) -> None:
        if self._hover_label is None or self._hover_label.isVisible() is False:
            return
        if not self._display_bars:
            return
        if self._view_center_x is None or self._view_span_x is None:
            return
        self._position_hover_label_at(self._hover_state_x_value, self._hover_state_y_value)

    def _on_mouse_moved(self, scene_pos: QtCore.QPointF) -> None:
        if not self._display_bars:
            return
        if not self._plot.sceneBoundingRect().contains(scene_pos):
            self._hide_hover_state()
            return
        mouse_point = self._plot.plotItem.vb.mapSceneToView(scene_pos)
        x_value = float(mouse_point.x())
        y_value = float(mouse_point.y())
        bar = self._nearest_bar(x_value)
        if bar is None:
            self._hide_hover_state()
            return
        self._hover_state_bar_timestamp_ms = bar.timestamp_ms
        self._hover_state_x_value = x_value
        self._hover_state_y_value = y_value
        if self._hover_vline is not None:
            self._hover_vline.setPos(_bar_x_value(bar))
            self._hover_vline.show()
        if self._hover_hline is not None:
            self._hover_hline.setPos(y_value)
            self._hover_hline.show()
        self._show_hover_label(bar, x_value, y_value)

    def _nearest_bar(self, x_value: float) -> OhlcBar | None:
        if not self._display_bars:
            return None
        if self._time_axis_mode == TimeAxisMode.COMPRESSED:
            index = max(0, min(int(round(x_value)), len(self._display_bars) - 1))
            return self._display_bars[index]
        x_values = [_bar_x_value(bar) for bar in self._display_bars]
        index = bisect_left(x_values, x_value)
        if index <= 0:
            return self._display_bars[0]
        if index >= len(self._display_bars):
            return self._display_bars[-1]
        previous_bar = self._display_bars[index - 1]
        next_bar = self._display_bars[index]
        if abs(_bar_x_value(previous_bar) - x_value) <= abs(_bar_x_value(next_bar) - x_value):
            return previous_bar
        return next_bar

    def _hide_hover_state(self) -> None:
        if self._hover_vline is not None:
            self._hover_vline.hide()
        if self._hover_hline is not None:
            self._hover_hline.hide()
        if self._hover_label is not None:
            self._hover_label.hide()
        self._hover_state_bar_timestamp_ms = None
        self._hover_state_x_value = None
        self._hover_state_y_value = None

    def _show_hover_label(self, bar: OhlcBar, x_value: float, y_value: float) -> None:
        if self._hover_label is None:
            return
        self._hover_label.setHtml(_hover_label_html(bar))
        self._hover_label.setVisible(True)
        self._position_hover_label_at(x_value, y_value)

    def _restore_hover_state(self) -> None:
        if (
            self._hover_label is None
            or self._hover_state_bar_timestamp_ms is None
            or self._hover_state_x_value is None
            or self._hover_state_y_value is None
        ):
            return
        bar = self._bar_by_timestamp_ms(self._hover_state_bar_timestamp_ms)
        if bar is None:
            return
        if self._hover_vline is not None:
            self._hover_vline.setPos(_bar_x_value(bar))
            self._hover_vline.show()
        if self._hover_hline is not None:
            self._hover_hline.setPos(self._hover_state_y_value)
            self._hover_hline.show()
        self._show_hover_label(bar, self._hover_state_x_value, self._hover_state_y_value)

    def _position_hover_label_at(
        self,
        x_value: float | None,
        y_value: float | None,
    ) -> None:
        if self._hover_label is None:
            return
        if (
            x_value is None
            or y_value is None
            or self._view_center_x is None
            or self._view_span_x is None
            or not self._display_bars
        ):
            return
        x_min = self._view_center_x - self._view_span_x / 2
        x_max = self._view_center_x + self._view_span_x / 2
        y_min = min(bar.low for bar in self._display_bars)
        y_max = max(bar.high for bar in self._display_bars)
        x_offset = max(self._bar_width_units() * 1.8, 1.0)
        y_offset = max((y_max - y_min) * 0.05, 2.0)
        tooltip_x = x_value + x_offset
        if tooltip_x > x_max - x_offset:
            tooltip_x = x_value - (x_offset * 2.4)
        if tooltip_x < x_min + 0.4:
            tooltip_x = x_min + 0.4
        tooltip_y = y_value + y_offset
        if tooltip_y > y_max - y_offset:
            tooltip_y = y_value - (y_offset * 4.0)
        if tooltip_y < y_min + y_offset:
            tooltip_y = y_min + y_offset
        self._hover_label.setPos(tooltip_x, tooltip_y)

    def _timestamp_ms_for_x(self, x_value: float) -> int | None:
        if not self._display_bars:
            return None
        if self._time_axis_mode == TimeAxisMode.COMPRESSED:
            index = max(0, min(int(round(x_value)), len(self._compressed_timestamps) - 1))
            return self._compressed_timestamps[index]
        return int(x_value * 1000.0)

    def _bar_by_timestamp_ms(self, timestamp_ms: int) -> OhlcBar | None:
        if self._time_axis_mode == TimeAxisMode.COMPRESSED:
            index = self._compressed_index_by_timestamp.get(timestamp_ms)
            if index is not None and 0 <= index < len(self._display_bars):
                return self._display_bars[index]
        for bar in self._display_bars:
            if bar.timestamp_ms == timestamp_ms:
                return bar
        return None

    def _bar_width_units(self) -> float:
        if self._time_axis_mode == TimeAxisMode.COMPRESSED:
            return 0.82
        return max(self._current_interval_seconds * 0.8, 36.0)

    def _detach_live_price_label(self) -> None:
        if self._live_price_label is None:
            return
        self._live_price_label.hide()
        self._live_price_label.deleteLater()
        self._live_price_label = None

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._position_live_price_label()
        self._position_hover_label()


def _format_number(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{value:.1f}"


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


def _build_placeholder_bars(anchor_price: float, *, count: int = 60) -> list[OhlcBar]:
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
    for index in range(count):
        open_delta, close_delta, low_delta, high_delta = patterns[index % len(patterns)]
        drift = (index // len(patterns)) * 0.25 * step
        open_price = anchor_price + open_delta * step + drift
        close_price = anchor_price + close_delta * step + drift
        low_price = min(open_price, close_price) + low_delta * step
        high_price = max(open_price, close_price) + high_delta * step
        bars.append(
            OhlcBar(
                timestamp_ms=(now - (count - index) * 60) * 1000,
                open=open_price,
                high=max(high_price, open_price, close_price),
                low=min(low_price, open_price, close_price),
                close=close_price,
            )
        )
    return bars


def _bar_from_chart_update(
    chart_update: ChartCandleUpdate,
    *,
    interval_seconds: int,
    price_basis: ChartPriceBasis,
) -> OhlcBar | None:
    ohlc = chart_update_ohlc(chart_update, price_basis=price_basis)
    if ohlc is None:
        return None
    open_price, high_price, low_price, close_price = ohlc
    timestamp_ms = chart_update.timestamp_ms
    if timestamp_ms is None:
        timestamp_ms = int(datetime.now(tz=UTC).timestamp() * 1000)
    timestamp_ms = _bucket_timestamp_ms(timestamp_ms, interval_seconds)
    return OhlcBar(
        timestamp_ms=timestamp_ms,
        open=open_price,
        high=max(high_price, open_price, close_price),
        low=min(low_price, open_price, close_price),
        close=close_price,
        volume=chart_update.volume,
    )


def _build_live_price_label(
    text: str,
    color: str,
    parent: QtWidgets.QWidget,
) -> QtWidgets.QLabel:
    label = QtWidgets.QLabel(text, parent)
    font = QtGui.QFont("Consolas", 9)
    font.setStyleHint(QtGui.QFont.Monospace)
    label.setFont(font)
    label.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
    label.setStyleSheet(
        "QLabel {"
        f"color: {color};"
        "background: #f4f8fc;"
        f"border: 1px solid {color};"
        "padding: 1px 4px;"
        "border-radius: 2px;"
        "}"
    )
    label.adjustSize()
    label.hide()
    return label


def _build_hover_label() -> pg.TextItem:
    label = pg.TextItem(
        text="",
        anchor=(0, 0),
        fill=QtGui.QColor("#f4f8fc"),
        border=pg.mkPen("#607080", width=1),
    )
    label.setZValue(10_000)
    label.hide()
    return label


def _hover_label_html(bar: OhlcBar) -> str:
    timestamp = datetime.fromtimestamp(bar.timestamp_ms / 1000.0).astimezone()
    return (
        "<div style='font-size: 10pt; line-height: 1.2; color: #1d2a36;'>"
        f"<b>{timestamp:%Y-%m-%d %H:%M}</b><br>"
        f"O: {bar.open:g}<br>"
        f"H: {bar.high:g}<br>"
        f"L: {bar.low:g}<br>"
        f"C: {bar.close:g}"
        "</div>"
    )


def _bucket_timestamp_ms(timestamp_ms: int, interval_seconds: int) -> int:
    bucket = (timestamp_ms // 1000 // interval_seconds) * interval_seconds
    return bucket * 1000


def _bars_from_price_series(
    series: PriceSeries,
    *,
    price_basis: ChartPriceBasis = ChartPriceBasis.MID,
    anchor_price: float | None = None,  # compatibility
) -> list[OhlcBar]:
    del anchor_price
    bars: list[OhlcBar] = []
    for index, price in enumerate(series.prices):
        timestamp_ms = _parse_price_timestamp_ms(price)
        ohlc = price_ohlc_from_payload(price, price_basis=price_basis)
        if ohlc is None:
            continue
        open_price, high_price, low_price, close_price = ohlc
        bars.append(
            OhlcBar(
                timestamp_ms=timestamp_ms if timestamp_ms is not None else index * 60_000,
                open=float(open_price),
                high=float(high_price),
                low=float(low_price),
                close=float(close_price),
                volume=_first_float_value(price, ["volume", "volumeTraded", "LTV", "TTV"]),
            )
        )
    return bars


def _bars_from_candles(candles: tuple[Candle, ...] | list[Candle]) -> list[OhlcBar]:
    bars: list[OhlcBar] = []
    for candle in candles:
        timestamp_ms = int(candle.timestamp.timestamp() * 1000)
        bars.append(
            OhlcBar(
                timestamp_ms=timestamp_ms,
                open=float(candle.open),
                high=float(candle.high),
                low=float(candle.low),
                close=float(candle.close),
                volume=float(candle.volume) if candle.volume is not None else None,
            )
        )
    return bars


def _parse_price_timestamp_ms(price: dict[str, object]) -> int | None:
    utc_timestamp = price.get("snapshotTimeUTC")
    if utc_timestamp not in (None, ""):
        if isinstance(utc_timestamp, (int, float)):
            return int(float(utc_timestamp))
        parsed = _parse_datetime_string(str(utc_timestamp).strip(), assume_utc=True)
        if parsed is not None:
            return int(parsed.timestamp() * 1000)

    local_timestamp = price.get("snapshotTime")
    if local_timestamp not in (None, ""):
        if isinstance(local_timestamp, (int, float)):
            return int(float(local_timestamp))
        parsed = _parse_datetime_string(str(local_timestamp).strip(), assume_utc=False)
        if parsed is not None:
            return int(parsed.timestamp() * 1000)

    for key in ("snapshot_time", "timestamp", "UTM"):
        value = price.get(key)
        if value in (None, ""):
            continue
        if isinstance(value, (int, float)):
            return int(float(value))
        parsed = _parse_datetime_string(str(value).strip(), assume_utc=True)
        if parsed is not None:
            return int(parsed.timestamp() * 1000)
    return None


def _parse_datetime_string(text: str, *, assume_utc: bool) -> datetime | None:
    patterns = [
        "%Y/%m/%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%SZ",
    ]
    for pattern in patterns:
        try:
            parsed = datetime.strptime(text, pattern)
            if assume_utc:
                return parsed.replace(tzinfo=UTC)
            local_timezone = datetime.now().astimezone().tzinfo or UTC
            return parsed.replace(tzinfo=local_timezone)
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


def _map_bars_for_display(bars: list[OhlcBar], mode: TimeAxisMode) -> list[OhlcBar]:
    if mode == TimeAxisMode.REAL:
        return [replace(bar, display_x=bar.timestamp_ms / 1000.0) for bar in bars]
    return [replace(bar, display_x=float(index)) for index, bar in enumerate(bars)]


def _bar_x_value(bar: OhlcBar) -> float:
    return bar.display_x if bar.display_x is not None else (bar.timestamp_ms / 1000.0)


def _minimum_x_span(mode: TimeAxisMode) -> float:
    return 10.0 if mode == TimeAxisMode.COMPRESSED else 60.0


def _x_padding(mode: TimeAxisMode, interval_seconds: int) -> tuple[float, float]:
    if mode == TimeAxisMode.COMPRESSED:
        return (1.2, 0.8)
    return (max(interval_seconds * 1.5, 30.0), max(interval_seconds * 0.6, 15.0))


def _format_axis_timestamp(timestamp: datetime, interval_seconds: int) -> str:
    if interval_seconds >= 86_400:
        return timestamp.strftime("%d %b %Y")
    if interval_seconds >= 3_600:
        return timestamp.strftime("%d %b %H:%M")
    if timestamp.hour == 0 and timestamp.minute == 0:
        return timestamp.strftime("%d %b")
    return timestamp.strftime("%H:%M")


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

HISTORY_RANGE_KEYS = ["1D", "5D", "1M", "3M", "6M", "1Y", "Max"]
