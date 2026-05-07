import argparse

import trading_ig_assistant.main as main_module


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
    assert "gui" in captured.out
