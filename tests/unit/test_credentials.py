from trading_ig_assistant.adapters.credentials import (
    IGCredentials,
    InMemoryCredentialStore,
    SecretValue,
)
from trading_ig_assistant.utils.redaction import REDACTED, redact_mapping, redact_text


def test_secret_value_redacts_str_and_repr() -> None:
    secret = SecretValue("fake-secret")

    assert str(secret) == REDACTED
    assert repr(secret) == REDACTED
    assert secret.reveal() == "fake-secret"


def test_ig_credentials_repr_does_not_leak_secrets() -> None:
    credentials = IGCredentials("demo-user", "fake-password", "fake-api-key")

    rendered = repr(credentials)

    assert "demo-user" in rendered
    assert "fake-password" not in rendered
    assert "fake-api-key" not in rendered
    assert REDACTED in rendered


def test_redact_mapping_masks_known_secret_keys() -> None:
    redacted = redact_mapping(
        {
            "password": "fake-password",
            "X-SECURITY-TOKEN": "fake-token",
            "X-IG-API-KEY": "fake-api-key",
            "accountId": "ABCDEF123456",
            "nested": {"api_key": "fake-api-key", "safe": "value"},
        }
    )

    assert redacted["password"] == REDACTED
    assert redacted["X-SECURITY-TOKEN"] == REDACTED
    assert redacted["X-IG-API-KEY"] == REDACTED
    assert redacted["accountId"] == "AB...56"
    assert redacted["nested"]["api_key"] == REDACTED
    assert redacted["nested"]["safe"] == "value"


def test_redact_text_removes_known_secret_values() -> None:
    redacted = redact_text(
        "password=fake-password api=fake-api-key",
        ["fake-password", "fake-api-key"],
    )

    assert "fake-password" not in redacted
    assert "fake-api-key" not in redacted


def test_in_memory_credential_store_round_trip() -> None:
    store = InMemoryCredentialStore()
    credentials = IGCredentials("demo-user", "fake-password", "fake-api-key")

    store.save(credentials)

    loaded = store.load("demo-user")
    assert loaded is not None
    assert loaded.username == "demo-user"
    assert loaded.password.reveal() == "fake-password"
    assert loaded.api_key.reveal() == "fake-api-key"
