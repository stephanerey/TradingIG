from __future__ import annotations

from dataclasses import dataclass

from trading_ig_assistant.adapters.ig_rest import IGSession
from trading_ig_assistant.adapters.ig_streaming import (
    IGStreamingAdapter,
    _account_metrics_from_update,
    _chart_update_from_update,
    _quote_from_update,
    build_stream_items,
)
from trading_ig_assistant.domain.market_data import AccountMetricsUpdate, ChartCandleUpdate
from trading_ig_assistant.domain.streaming import (
    ACCOUNT_METRICS_SPEC,
    CHART_CANDLE_SPEC,
    MARKET_QUOTE_SPEC,
    PRICE_QUOTE_SPEC,
)


class FakeConnectionDetails:
    def __init__(self) -> None:
        self.user = None
        self.password = None

    def setUser(self, value):  # noqa: N802
        self.user = value

    def setPassword(self, value):  # noqa: N802
        self.password = value


class FakeLightstreamerClient:
    def __init__(self, server_address: str, adapter_set: str) -> None:
        self.server_address = server_address
        self.adapter_set = adapter_set
        self.connectionDetails = FakeConnectionDetails()
        self.listeners = []
        self.subscriptions = []
        self.connect_called = False
        self.disconnect_called = False
        self.unsubscribed = []

    def addListener(self, listener):  # noqa: N802
        self.listeners.append(listener)

    def connect(self):  # noqa: N802
        self.connect_called = True

    def disconnect(self):  # noqa: N802
        self.disconnect_called = True

    def subscribe(self, subscription):  # noqa: N802
        self.subscriptions.append(subscription)

    def unsubscribe(self, subscription):  # noqa: N802
        self.unsubscribed.append(subscription)


@dataclass
class FakeUpdate:
    fields: dict[str, str]
    snapshot: bool = False
    item_name: str | None = None

    def getFields(self):  # noqa: N802
        return self.fields

    def getValue(self, name):  # noqa: N802
        return self.fields.get(name)

    def isSnapshot(self):  # noqa: N802
        return self.snapshot

    def getItemName(self):  # noqa: N802
        return self.item_name


class RecordingSink:
    def __init__(self) -> None:
        self.statuses: list[str] = []
        self.quotes = []
        self.charts = []
        self.account_metrics = []
        self.errors: list[str] = []

    def on_stream_status(self, status: str) -> None:
        self.statuses.append(status)

    def on_quote(self, quote) -> None:
        self.quotes.append(quote)

    def on_chart(self, chart_update) -> None:
        self.charts.append(chart_update)

    def on_account_metrics(self, update) -> None:
        self.account_metrics.append(update)

    def on_stream_error(self, message: str) -> None:
        self.errors.append(message)


def test_reference_quote_probe_is_isolated_and_cleaned_up(caplog) -> None:
    import logging

    client = FakeLightstreamerClient("https://stream.example", "DEFAULT")
    sink = RecordingSink()
    adapter = IGStreamingAdapter(
        session=IGSession(
            cst="fake-cst",
            security_token="fake-security-token",
            current_account_id="ACC123",
            lightstreamer_endpoint="https://stream.example",
        ),
        account_id="ACC123",
        event_sink=sink,
        client_factory=lambda server_address, adapter_set: client,
    )
    adapter.start()
    adapter.subscribe_market("PRODUCT")
    adapter.probe_reference_quote("REFERENCE")
    adapter.probe_reference_quote("REFERENCE")
    product, probe = client.subscriptions
    assert probe.getItems() == ["MARKET:REFERENCE"]
    listener = probe.getListeners()[0]
    with caplog.at_level(logging.DEBUG):
        listener.onSubscriptionError(21, "Invalid group")
        listener.onItemUpdate(FakeUpdate({"BID": "100"}, item_name="MARKET:REFERENCE"))
    assert "Reference MARKET probe rejected epic=REFERENCE" in caplog.text
    assert "Reference MARKET probe received epic=REFERENCE" in caplog.text
    assert sink.errors == []
    assert sink.quotes == []
    assert product not in client.unsubscribed
    adapter.stop()
    assert product in client.unsubscribed
    assert probe in client.unsubscribed


def test_quote_subscription_log_masks_account_but_keeps_wire_item(caplog) -> None:
    import logging

    client = FakeLightstreamerClient("https://stream.example", "DEFAULT")
    adapter = IGStreamingAdapter(
        session=IGSession(
            cst="fake-cst",
            security_token="fake-security-token",
            current_account_id="SYNTHETIC123",
            lightstreamer_endpoint="https://stream.example",
        ),
        account_id="SYNTHETIC123",
        client_factory=lambda server_address, adapter_set: client,
    )
    with caplog.at_level(logging.DEBUG):
        adapter.start()
        adapter.subscribe_market("EPIC.ONE")
    assert client.subscriptions[0].getItems() == ["PRICE:SYNTHETIC123:EPIC.ONE"]
    assert "SYNTHETIC123" not in caplog.text
    assert "PRICE:SY...23:EPIC.ONE" in caplog.text
    adapter.stop()


def test_delay_marker_is_preserved_in_normalized_ig_quote() -> None:
    quote = _quote_from_update(
        FakeUpdate(
            {"BIDPRICE1": "100", "ASKPRICE1": "101", "DELAY": "1"},
            item_name="PRICE:FAKE:EPIC.ONE",
        )
    )
    assert quote.delayed is True


def test_streaming_adapter_connects_and_parses_quotes() -> None:
    client = FakeLightstreamerClient("https://stream.example", "DEFAULT")
    sink = RecordingSink()
    adapter = IGStreamingAdapter(
        session=IGSession(
            cst="fake-cst",
            security_token="fake-security-token",
            current_account_id="ACC123",
            lightstreamer_endpoint="https://stream.example",
        ),
        account_id="ACC123",
        event_sink=sink,
        client_factory=lambda server_address, adapter_set: client,
    )

    adapter.start()
    adapter.subscribe_market("EPIC.ONE")

    assert client.server_address == "https://stream.example"
    assert client.adapter_set == "DEFAULT"
    assert client.connectionDetails.user == "ACC123"
    assert client.connectionDetails.password == "CST-fake-cst|XST-fake-security-token"
    assert client.connect_called is True
    assert len(client.subscriptions) == 1
    assert client.subscriptions[0].getItems() == ["PRICE:ACC123:EPIC.ONE"]
    assert client.subscriptions[0].getDataAdapter() == "Pricing"

    listener = client.subscriptions[0].getListeners()[0]
    listener.onItemUpdate(
        FakeUpdate(
            {
                "BIDPRICE1": "2311.9",
                "ASKPRICE1": "2313.1",
                "NET_CHG": "-38.7",
                "NET_CHG_PCT": "-1.64",
                "TIMESTAMP": "1778490000000",
            },
            snapshot=True,
            item_name="PRICE:ACC123:EPIC.ONE",
        )
    )

    assert sink.quotes[0].epic == "EPIC.ONE"
    assert sink.quotes[0].bid == 2311.9
    assert sink.quotes[0].offer == 2313.1
    assert sink.quotes[0].net_change == -38.7
    assert sink.quotes[0].percent_change == -1.64
    assert sink.quotes[0].snapshot is True
    assert sink.quotes[0].timestamp_ms == 1778490000000

    adapter.stop()

    assert client.unsubscribed
    assert client.disconnect_called is True
    assert sink.statuses[-1] == "DISCONNECTED"


def test_streaming_adapter_subscribes_and_parses_account_metrics() -> None:
    client = FakeLightstreamerClient("https://stream.example", "DEFAULT")
    sink = RecordingSink()
    adapter = IGStreamingAdapter(
        session=IGSession(
            cst="fake-cst",
            security_token="fake-security-token",
            current_account_id="ACC123",
            lightstreamer_endpoint="https://stream.example",
        ),
        account_id="ACC123",
        event_sink=sink,
        client_factory=lambda server_address, adapter_set: client,
    )

    adapter.subscribe_account()
    adapter.subscribe_account()

    assert len(client.subscriptions) == 1
    subscription = client.subscriptions[0]
    assert subscription.getItems() == ["ACCOUNT:ACC123"]
    assert subscription.getFields() == list(ACCOUNT_METRICS_SPEC.fields)
    subscription.getListeners()[0].onItemUpdate(
        FakeUpdate(
            {
                "FUNDS": "10000.50",
                "AVAILABLE_TO_DEAL": "9250.25",
                "PNL": "-12.5",
                "MARGIN": "750.25",
                "EQUITY": "9988.0",
            },
            snapshot=True,
            item_name="ACCOUNT:ACC123",
        )
    )

    assert sink.account_metrics == [
        AccountMetricsUpdate(
            account_id="ACC123",
            funds=10000.5,
            available_to_deal=9250.25,
            profit_loss=-12.5,
            equity=9988.0,
            margin=750.25,
            snapshot=True,
            raw={
                "FUNDS": "10000.50",
                "AVAILABLE_TO_DEAL": "9250.25",
                "PNL": "-12.5",
                "MARGIN": "750.25",
                "EQUITY": "9988.0",
            },
        )
    ]

    adapter.stop()
    assert subscription in client.unsubscribed


def test_account_metric_parser_rejects_no_identity_by_returning_empty_account() -> None:
    update = _account_metrics_from_update(FakeUpdate({"EQUITY": "100"}))
    assert update.account_id == ""
    assert update.equity == 100.0


def test_streaming_adapter_emits_chart_updates() -> None:
    client = FakeLightstreamerClient("https://stream.example", "DEFAULT")
    sink = RecordingSink()
    adapter = IGStreamingAdapter(
        session=IGSession(
            cst="fake-cst",
            security_token="fake-security-token",
            current_account_id="ACC123",
            lightstreamer_endpoint="https://stream.example",
        ),
        account_id="ACC123",
        event_sink=sink,
        client_factory=lambda server_address, adapter_set: client,
    )

    adapter.start()
    adapter.subscribe_chart("EPIC.ONE", "1MINUTE")

    assert len(client.subscriptions) == 1
    assert client.subscriptions[0].getItems() == ["CHART:EPIC.ONE:1MINUTE"]

    listener = client.subscriptions[0].getListeners()[0]
    listener.onItemUpdate(
        FakeUpdate(
            {
                "UTM": "1778490000000",
                "BID_OPEN": "10.0",
                "BID_HIGH": "12.0",
                "BID_LOW": "9.5",
                "BID_CLOSE": "11.5",
                "CONS_END": "1",
                "CONS_TICK_COUNT": "8",
            },
            snapshot=True,
        )
    )

    assert isinstance(sink.charts[0], ChartCandleUpdate)
    assert sink.charts[0].epic == "EPIC.ONE"
    assert sink.charts[0].interval == "1MINUTE"
    assert sink.charts[0].close == 11.5
    assert sink.charts[0].end_of_candle is True


def test_streaming_adapter_subscribes_multiple_chart_markets_in_one_subscription() -> None:
    client = FakeLightstreamerClient("https://stream.example", "DEFAULT")
    sink = RecordingSink()
    adapter = IGStreamingAdapter(
        session=IGSession(
            cst="fake-cst",
            security_token="fake-security-token",
            current_account_id="ACC123",
            lightstreamer_endpoint="https://stream.example",
        ),
        account_id="ACC123",
        event_sink=sink,
        client_factory=lambda server_address, adapter_set: client,
    )

    adapter.subscribe_charts(["EPIC.ONE", "EPIC.TWO", "EPIC.ONE"], "1MINUTE")

    assert len(client.subscriptions) == 1
    subscription = client.subscriptions[0]
    assert subscription.getItems() == [
        "CHART:EPIC.ONE:1MINUTE",
        "CHART:EPIC.TWO:1MINUTE",
    ]
    listener = subscription.getListeners()[0]
    listener.onItemUpdate(
        FakeUpdate(
            {"UTM": "1778490000000", "BID_CLOSE": "11.5", "CONS_END": "1"},
            item_name="CHART:EPIC.TWO:1MINUTE",
        )
    )

    assert sink.charts[0].epic == "EPIC.TWO"
    assert sink.charts[0].interval == "1MINUTE"
    adapter.subscribe_charts(["EPIC.ONE", "EPIC.TWO"], "1MINUTE")
    assert len(client.subscriptions) == 1
    assert client.unsubscribed == []


def test_streaming_adapter_can_isolate_chart_permissions_per_market() -> None:
    client = FakeLightstreamerClient("https://stream.example", "DEFAULT")
    sink = RecordingSink()
    adapter = IGStreamingAdapter(
        session=IGSession(
            cst="fake-cst",
            security_token="fake-security-token",
            current_account_id="ACC123",
            lightstreamer_endpoint="https://stream.example",
        ),
        account_id="ACC123",
        event_sink=sink,
        client_factory=lambda server_address, adapter_set: client,
    )
    adapter.subscribe_charts(["EPIC.ONE", "EPIC.TWO"], "1MINUTE")
    grouped = client.subscriptions[0]

    adapter.subscribe_charts_individually(["EPIC.ONE", "EPIC.TWO"], "1MINUTE")

    assert grouped in client.unsubscribed
    assert [subscription.getItems() for subscription in client.subscriptions[1:]] == [
        ["CHART:EPIC.ONE:1MINUTE"],
        ["CHART:EPIC.TWO:1MINUTE"],
    ]
    client.subscriptions[1].getListeners()[0].onItemUpdate(
        FakeUpdate(
            {"UTM": "1778490000000", "BID_CLOSE": "11.5", "CONS_END": "1"},
            item_name="CHART:EPIC.ONE:1MINUTE",
        )
    )
    assert sink.charts[0].epic == "EPIC.ONE"
    adapter.stop()
    assert all(
        subscription in client.unsubscribed for subscription in client.subscriptions[1:]
    )


def test_streaming_adapter_can_isolate_invalid_price_market() -> None:
    client = FakeLightstreamerClient("https://stream.example", "DEFAULT")
    sink = RecordingSink()
    adapter = IGStreamingAdapter(
        session=IGSession(
            cst="fake-cst",
            security_token="fake-security-token",
            current_account_id="ACC123",
            lightstreamer_endpoint="https://stream.example",
        ),
        account_id="ACC123",
        event_sink=sink,
        client_factory=lambda server_address, adapter_set: client,
    )
    adapter.subscribe_markets(["EPIC.ONE", "EPIC.TWO"])
    grouped = client.subscriptions[0]

    adapter.subscribe_markets_individually(["EPIC.ONE", "EPIC.TWO"])

    assert grouped in client.unsubscribed
    assert [subscription.getItems() for subscription in client.subscriptions[1:]] == [
        ["PRICE:ACC123:EPIC.ONE"],
        ["PRICE:ACC123:EPIC.TWO"],
    ]
    listener = client.subscriptions[2].getListeners()[0]
    listener.onSubscriptionError(21, "Invalid group")
    assert sink.errors == ["Subscription error for PRICE:EPIC.TWO: 21 Invalid group"]
    listener.onItemUpdate(
        FakeUpdate(
            {"BID": "11.5", "OFFER": "11.7"},
            item_name="PRICE:ACC123:EPIC.TWO",
        )
    )
    assert sink.quotes[0].epic == "EPIC.TWO"
    adapter.stop()
    assert all(
        subscription in client.unsubscribed for subscription in client.subscriptions[1:]
    )


def test_multi_chart_subscription_rejects_unexpected_update_identity() -> None:
    client = FakeLightstreamerClient("https://stream.example", "DEFAULT")
    sink = RecordingSink()
    adapter = IGStreamingAdapter(
        session=IGSession(
            cst="fake-cst",
            security_token="fake-security-token",
            current_account_id="ACC123",
            lightstreamer_endpoint="https://stream.example",
        ),
        account_id="ACC123",
        event_sink=sink,
        client_factory=lambda server_address, adapter_set: client,
    )
    adapter.subscribe_charts(["EPIC.ONE", "EPIC.TWO"], "1MINUTE")
    listener = client.subscriptions[0].getListeners()[0]

    listener.onItemUpdate(
        FakeUpdate(
            {"UTM": "1778490000000", "BID_CLOSE": "11.5"},
            item_name="CHART:UNEXPECTED:1MINUTE",
        )
    )

    assert sink.charts == []
    assert sink.errors == ["Lightstreamer chart update has an unexpected item identity"]


def test_streaming_adapter_subscribes_multiple_market_prices() -> None:
    client = FakeLightstreamerClient("https://stream.example", "DEFAULT")
    sink = RecordingSink()
    adapter = IGStreamingAdapter(
        session=IGSession(
            cst="fake-cst",
            security_token="fake-security-token",
            current_account_id="ACC123",
            lightstreamer_endpoint="https://stream.example",
        ),
        account_id="ACC123",
        event_sink=sink,
        client_factory=lambda server_address, adapter_set: client,
    )

    adapter.start()
    adapter.subscribe_markets(["EPIC.ONE", "EPIC.TWO"])

    assert len(client.subscriptions) == 1
    assert client.subscriptions[0].getItems() == [
        "PRICE:ACC123:EPIC.ONE",
        "PRICE:ACC123:EPIC.TWO",
    ]
    assert client.subscriptions[0].getDataAdapter() == "Pricing"


def test_stream_item_template_generation_supports_market_and_chart() -> None:
    assert build_stream_items(MARKET_QUOTE_SPEC, epics=["EPIC.ONE"]) == ["MARKET:EPIC.ONE"]
    assert build_stream_items(
        PRICE_QUOTE_SPEC,
        epics=["EPIC.ONE"],
        account_id="ACC123",
    ) == ["PRICE:ACC123:EPIC.ONE"]
    assert build_stream_items(
        CHART_CANDLE_SPEC,
        epics=["EPIC.ONE"],
        scale="1MINUTE",
    ) == ["CHART:EPIC.ONE:1MINUTE"]


def test_quote_parser_supports_market_style_fields() -> None:
    quote = _quote_from_update(
        FakeUpdate(
            {
                "BID": "100.1",
                "OFFER": "100.4",
                "UPDATE_TIME": "1778490000000",
                "MARKET_STATE": "TRADEABLE",
                "CHANGE": "-2.5",
                "CHANGE_PCT": "-0.24",
            },
            item_name="MARKET:EPIC.ONE",
        )
    )

    assert quote.epic == "EPIC.ONE"
    assert quote.bid == 100.1
    assert quote.offer == 100.4
    assert quote.net_change == -2.5
    assert quote.percent_change == -0.24
    assert quote.market_state == "TRADEABLE"
    assert quote.timestamp_ms == 1_778_490_000_000


def test_quote_parser_supports_price_style_fields() -> None:
    quote = _quote_from_update(
        FakeUpdate(
            {
                "BIDPRICE1": "2311.9",
                "ASKPRICE1": "2313.1",
                "NET_CHG": "-38.7",
                "NET_CHG_PCT": "-1.64",
                "TIMESTAMP": "1778490000000",
            },
            item_name="PRICE:ACC123:EPIC.ONE",
        )
    )

    assert quote.epic == "EPIC.ONE"
    assert quote.bid == 2311.9
    assert quote.offer == 2313.1
    assert quote.net_change == -38.7
    assert quote.percent_change == -1.64


def test_chart_parser_supports_chart_subscription_item() -> None:
    chart_update = _chart_update_from_update(
        FakeUpdate(
            {
                "UTM": "1778490000000",
                "BID_OPEN": "10.0",
                "BID_HIGH": "12.0",
                "BID_LOW": "9.5",
                "BID_CLOSE": "11.5",
                "CONS_END": "1",
                "CONS_TICK_COUNT": "8",
            },
            item_name="CHART:EPIC.ONE:1MINUTE",
        ),
        "EPIC.ONE",
        "1MINUTE",
    )

    assert isinstance(chart_update, ChartCandleUpdate)
    assert chart_update.epic == "EPIC.ONE"
    assert chart_update.interval == "1MINUTE"
    assert chart_update.close == 11.5
    assert chart_update.end_of_candle is True


def test_streaming_adapter_reports_missing_endpoint() -> None:
    adapter = IGStreamingAdapter(
        session=IGSession(
            cst="fake-cst",
            security_token="fake-security-token",
            current_account_id="ACC123",
            lightstreamer_endpoint=None,
        ),
        account_id="ACC123",
        client_factory=lambda server_address, adapter_set: FakeLightstreamerClient(
            server_address,
            adapter_set,
        ),
    )

    try:
        adapter.start()
    except RuntimeError as exc:
        assert "Lightstreamer endpoint" in str(exc)
    else:
        raise AssertionError("Expected RuntimeError")
