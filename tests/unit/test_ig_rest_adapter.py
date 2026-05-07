import pytest

from trading_ig_assistant.adapters.credentials import IGCredentials
from trading_ig_assistant.adapters.ig_rest import (
    HttpResponse,
    IGRestAdapter,
    LiveTradingDisabledError,
)
from trading_ig_assistant.app.config import IGEnvironment


class FakeHttpClient:
    def __init__(self) -> None:
        self.requests = []

    def request(self, method, url, *, headers, json_body=None, timeout):
        self.requests.append(
            {
                "method": method,
                "url": url,
                "headers": headers,
                "json_body": json_body,
                "timeout": timeout,
            }
        )
        if url.endswith("/session") and method == "POST":
            return HttpResponse(
                status_code=200,
                headers={"CST": "fake-cst", "X-SECURITY-TOKEN": "fake-security-token"},
                body={"currentAccountId": "SANITIZED_ACCOUNT", "lightstreamerEndpoint": "demo"},
            )
        if url.endswith("/session") and method == "DELETE":
            return HttpResponse(status_code=200, headers={}, body={})
        if url.endswith("/accounts"):
            return HttpResponse(
                status_code=200,
                headers={},
                body={
                    "accounts": [
                        {
                            "accountId": "SANITIZED_ACCOUNT",
                            "accountName": "Demo CFD",
                            "accountType": "CFD",
                            "currency": "EUR",
                            "balance": {
                                "balance": 10000,
                                "available": 9500.25,
                                "deposit": 10000,
                                "profitLoss": -499.75,
                            },
                            "preferred": True,
                        }
                    ]
                },
            )
        if "/markets?searchTerm=US+Tech" in url:
            return HttpResponse(
                status_code=200,
                headers={},
                body={
                    "markets": [
                        {
                            "epic": "IX.D.NASDAQ.IFD.IP",
                            "instrumentName": "US Tech 100",
                            "instrumentType": "INDICES",
                            "marketStatus": "TRADEABLE",
                        }
                    ]
                },
            )
        if "/markets/IX.D.NASDAQ.IFD.IP" in url:
            return HttpResponse(
                status_code=200,
                headers={},
                body={"instrument": {"epic": "IX.D.NASDAQ.IFD.IP", "name": "US Tech 100"}},
            )
        if "/prices/IX.D.NASDAQ.IFD.IP/MINUTE/2" in url:
            return HttpResponse(
                status_code=200,
                headers={},
                body={"prices": [{"snapshotTime": "2026/05/07 10:00:00"}]},
            )
        raise AssertionError(f"Unexpected request: {method} {url}")


def test_login_and_read_only_calls_use_demo_base_url() -> None:
    http_client = FakeHttpClient()
    adapter = IGRestAdapter(environment=IGEnvironment.DEMO, http_client=http_client)

    session = adapter.login(IGCredentials("demo-user", "fake-password", "fake-api-key"))
    accounts = adapter.get_accounts()
    markets = adapter.search_markets("US Tech")
    details = adapter.get_market_details("IX.D.NASDAQ.IFD.IP")
    prices = adapter.get_prices("IX.D.NASDAQ.IFD.IP", max_points=2)

    assert session.current_account_id == "SANITIZED_ACCOUNT"
    assert accounts[0].account_name == "Demo CFD"
    assert accounts[0].currency == "EUR"
    assert accounts[0].balance == 10000.0
    assert accounts[0].available == 9500.25
    assert accounts[0].deposit == 10000.0
    assert accounts[0].profit_loss == -499.75
    assert markets[0].instrument_name == "US Tech 100"
    assert details.instrument_name == "US Tech 100"
    assert len(prices.prices) == 1
    assert all(
        request["url"].startswith("https://demo-api.ig.com") for request in http_client.requests
    )


def test_order_execution_methods_are_hard_blocked_in_p00() -> None:
    adapter = IGRestAdapter(environment=IGEnvironment.DEMO, http_client=FakeHttpClient())

    with pytest.raises(LiveTradingDisabledError):
        adapter.create_otc_position({})
    with pytest.raises(LiveTradingDisabledError):
        adapter.update_position("deal-id", {})
    with pytest.raises(LiveTradingDisabledError):
        adapter.close_position("deal-id", {})
    with pytest.raises(LiveTradingDisabledError):
        adapter.create_working_order({})


def test_logout_ignores_invalid_security_token() -> None:
    class LogoutTokenExpiredClient(FakeHttpClient):
        def request(self, method, url, *, headers, json_body=None, timeout):
            if url.endswith("/session") and method == "DELETE":
                return HttpResponse(
                    status_code=401,
                    headers={},
                    body={"errorCode": "error.security.invalid-security-token"},
                )
            return super().request(
                method,
                url,
                headers=headers,
                json_body=json_body,
                timeout=timeout,
            )

    adapter = IGRestAdapter(environment=IGEnvironment.DEMO, http_client=LogoutTokenExpiredClient())
    adapter.login(IGCredentials("demo-user", "fake-password", "fake-api-key"))

    adapter.logout()

    assert adapter.session is None
