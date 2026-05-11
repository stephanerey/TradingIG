import argparse

import trading_ig_assistant.main as main_module
from trading_ig_assistant.adapters.ig_rest import IGSession


def test_main_without_arguments_launches_gui(monkeypatch) -> None:
    called = {}

    def fake_launch_gui(_args: argparse.Namespace) -> int:
        called["gui"] = True
        return 0

    monkeypatch.setattr(main_module, "launch_gui", fake_launch_gui)

    assert main_module.main([]) == 0
    assert called["gui"] is True


def test_main_help_still_prints_usage(capsys) -> None:
    try:
        main_module.main(["--help"])
    except SystemExit as exc:
        assert exc.code == 0

    captured = capsys.readouterr()
    assert "check-ig-connectivity" in captured.out
    assert "discover-products" in captured.out
    assert "stream-market" in captured.out
    assert "gui" in captured.out


def test_stream_market_redacts_account_and_secrets(monkeypatch, capsys) -> None:
    class FakeRestAdapter:
        def __init__(self, environment, read_only=True):
            self.environment = environment
            self.read_only = read_only

        def login(self, credentials):
            assert credentials.username == "user"
            assert credentials.password.reveal() == "pass123"
            assert credentials.api_key.reveal() == "key123"
            return IGSession(
                cst="secret-cst",
                security_token="secret-xst",
                current_account_id="ABCDEF1234",
                lightstreamer_endpoint="https://stream.example",
            )

        def logout(self):
            return None

    class FakeStreamingAdapter:
        def __init__(self, session, account_id, event_sink):
            self.event_sink = event_sink

        def start(self):
            self.event_sink.on_stream_status("CONNECTED:WS-STREAMING")

        def stop(self):
            self.event_sink.on_stream_status("DISCONNECTED")

        def subscribe_quote(self, epic, *, spec):
            self.event_sink.on_stream_status(f"SUBSCRIBED:{spec.name}")
            self.event_sink.on_quote(
                type(
                    "QuoteLike",
                    (),
                    {
                        "raw": {
                            "ACCOUNT": "ABCDEF1234",
                            "API_KEY": "key123",
                            "BID": "100.1",
                        }
                    },
                )()
            )

        def subscribe_chart(self, epic, scale="1MINUTE", *, spec):
            self.event_sink.on_stream_status(f"SUBSCRIBED:{spec.name}")

    monkeypatch.setattr(main_module, "IGRestAdapter", FakeRestAdapter)
    monkeypatch.setattr(main_module, "IGStreamingAdapter", FakeStreamingAdapter)
    monkeypatch.setenv("TRADING_IG_PASSWORD", "pass123")
    monkeypatch.setenv("TRADING_IG_API_KEY", "key123")

    exit_code = main_module.main(
        [
            "stream-market",
            "--environment",
            "live",
            "--username",
            "user",
            "--epic",
            "IX.D.TEST.IP",
            "--duration",
            "0",
        ]
    )

    assert exit_code == 0
    captured = capsys.readouterr()
    assert "ABCDEF1234" not in captured.out
    assert "key123" not in captured.out
    assert "pass123" not in captured.out
    assert "AB...34" in captured.out
    assert "First update received: yes" in captured.out
