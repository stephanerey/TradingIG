from __future__ import annotations

from dataclasses import dataclass

from trading_ig_assistant.adapters.ig_rest import IGSession
from trading_ig_assistant.adapters.ig_streaming import IGStreamingAdapter


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

    def getFields(self):  # noqa: N802
        return self.fields

    def getValue(self, name):  # noqa: N802
        return self.fields.get(name)

    def isSnapshot(self):  # noqa: N802
        return self.snapshot


class RecordingSink:
    def __init__(self) -> None:
        self.statuses: list[str] = []
        self.quotes = []
        self.errors: list[str] = []

    def on_stream_status(self, status: str) -> None:
        self.statuses.append(status)

    def on_quote(self, quote) -> None:
        self.quotes.append(quote)

    def on_stream_error(self, message: str) -> None:
        self.errors.append(message)


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
    assert client.subscriptions[0].getItems() == ["MARKET:EPIC.ONE"]

    listener = client.subscriptions[0].getListeners()[0]
    listener.onItemUpdate(
        FakeUpdate(
            {
                "BID": "2311.9",
                "OFFER": "2313.1",
                "CHANGE": "-38.7",
                "CHANGE_PCT": "-1.64",
                "MARKET_STATE": "TRADEABLE",
            },
            snapshot=True,
        )
    )

    assert sink.quotes[0].epic == "EPIC.ONE"
    assert sink.quotes[0].bid == 2311.9
    assert sink.quotes[0].offer == 2313.1
    assert sink.quotes[0].net_change == -38.7
    assert sink.quotes[0].percent_change == -1.64
    assert sink.quotes[0].market_state == "TRADEABLE"
    assert sink.quotes[0].snapshot is True

    adapter.stop()

    assert client.unsubscribed
    assert client.disconnect_called is True
    assert sink.statuses[-1] == "DISCONNECTED"


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
