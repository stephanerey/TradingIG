from trading_ig_assistant.ui.main_window import humanize_ig_error


def test_humanize_ig_error_for_invalid_api_key() -> None:
    message = humanize_ig_error("{'errorCode': 'error.security.api-key-invalid'}")

    assert "environment matches the key" in message


def test_humanize_ig_error_for_invalid_identifier() -> None:
    message = humanize_ig_error("{'errorCode': 'validation.pattern.invalid.auth.identifier'}")

    assert "not your email address" in message


def test_humanize_ig_error_for_client_suspended() -> None:
    message = humanize_ig_error("{'errorCode': 'error.security.client-suspended'}")

    assert "client is suspended" in message
    assert "Stop retrying" in message


def test_humanize_ig_error_for_too_many_failed_attempts() -> None:
    message = humanize_ig_error("{'errorCode': 'error.security.too-many-failed-attempts'}")

    assert "too many failed login attempts" in message.lower()
    assert "wait" in message.lower()


def test_humanize_ig_error_for_demo_stopbrocking() -> None:
    message = humanize_ig_error("{'errorCode': 'stopbrocking'}")

    assert "demo connection" in message.lower()
    assert "demo api identifier" in message.lower()
