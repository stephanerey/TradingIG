import pytest

from trading_ig_assistant.adapters.credentials import IGCredentials
from trading_ig_assistant.adapters.ig_rest import (
    HttpResponse,
    IGRestAdapter,
    LiveTradingDisabledError,
    build_historical_fallback_ladder,
    is_historical_allowance_error,
    load_prices_with_adaptive_fallback,
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
        if url.endswith("/session") and method == "PUT":
            return HttpResponse(
                status_code=200,
                headers={"X-SECURITY-TOKEN": "fake-switched-security-token"},
                body={},
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
        if url.endswith("/categories"):
            return HttpResponse(
                status_code=200,
                headers={},
                body={"categories": [{"id": "shares", "name": "Shares"}]},
            )
        if url.endswith("/categories/shares/instruments"):
            return HttpResponse(
                status_code=200,
                headers={},
                body={
                    "instruments": [
                        {
                            "epic": "KA.D.CARR.CASH.IP",
                            "name": "Carrefour SA",
                            "instrumentType": "SHARES",
                            "marketStatus": "TRADEABLE",
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
        if url.endswith("/market-navigation"):
            return HttpResponse(
                status_code=200,
                headers={},
                body={
                    "nodes": [{"id": "indices", "name": "Indices"}],
                    "markets": [
                        {
                            "epic": "IX.D.NASDAQ.IFD.IP",
                            "instrumentName": "US Tech 100",
                            "instrumentType": "INDICES",
                        }
                    ],
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
    prices = adapter.get_prices("IX.D.NASDAQ.IFD.IP", resolution="MINUTE", max_points=2)

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
    assert http_client.requests[-1]["headers"]["VERSION"] == "2"


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


def test_switch_account_reuses_new_security_token() -> None:
    http_client = FakeHttpClient()
    adapter = IGRestAdapter(environment=IGEnvironment.DEMO, http_client=http_client)
    adapter.login(IGCredentials("demo-user", "fake-password", "fake-api-key"))

    session = adapter.switch_account("BARRIER_ACCOUNT")
    adapter.get_accounts()

    assert session.current_account_id == "BARRIER_ACCOUNT"
    account_request = http_client.requests[-1]
    assert account_request["headers"]["X-SECURITY-TOKEN"] == "fake-switched-security-token"
    assert account_request["headers"]["CST"] == "fake-cst"


def test_market_navigation_uses_hyphenated_endpoint() -> None:
    http_client = FakeHttpClient()
    adapter = IGRestAdapter(environment=IGEnvironment.DEMO, http_client=http_client)
    adapter.login(IGCredentials("demo-user", "fake-password", "fake-api-key"))

    navigation = adapter.get_market_navigation()

    assert navigation.nodes[0].node_id == "indices"
    assert navigation.markets[0].epic == "IX.D.NASDAQ.IFD.IP"
    assert http_client.requests[-1]["url"].endswith("/market-navigation")


def test_categories_and_category_instruments_are_read_only() -> None:
    http_client = FakeHttpClient()
    adapter = IGRestAdapter(environment=IGEnvironment.DEMO, http_client=http_client)
    adapter.login(IGCredentials("demo-user", "fake-password", "fake-api-key"))

    categories = adapter.get_categories()
    instruments = adapter.get_category_instruments(categories[0].category_id)

    assert categories[0].category_id == "shares"
    assert instruments[0].epic == "KA.D.CARR.CASH.IP"
    assert instruments[0].instrument_name == "Carrefour SA"


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


def test_get_prices_max_points_mode_uses_expected_path() -> None:
    http_client = FakeHttpClient()
    adapter = IGRestAdapter(environment=IGEnvironment.DEMO, http_client=http_client)
    adapter.login(IGCredentials("demo-user", "fake-password", "fake-api-key"))

    prices = adapter.get_prices("IX.D.NASDAQ.IFD.IP", resolution="MINUTE", max_points=2)

    assert len(prices.prices) == 1
    assert http_client.requests[-1]["url"].endswith("/prices/IX.D.NASDAQ.IFD.IP/MINUTE/2")


def test_get_prices_falls_back_from_malformed_date_to_max_points() -> None:
    class RangeFallbackClient(FakeHttpClient):
        def request(self, method, url, *, headers, json_body=None, timeout):
            if "/prices/IX.D.NASDAQ.IFD.IP/MINUTE?" in url:
                return HttpResponse(
                    status_code=400,
                    headers={},
                    body={"errorCode": "error.malformed.date"},
                )
            return super().request(
                method,
                url,
                headers=headers,
                json_body=json_body,
                timeout=timeout,
            )

    http_client = RangeFallbackClient()
    adapter = IGRestAdapter(environment=IGEnvironment.DEMO, http_client=http_client)
    adapter.login(IGCredentials("demo-user", "fake-password", "fake-api-key"))

    prices = adapter.get_prices(
        "IX.D.NASDAQ.IFD.IP",
        resolution="MINUTE",
        start_time=__import__("datetime").datetime(2026, 5, 11, 10, 0, 0),
        end_time=__import__("datetime").datetime(2026, 5, 11, 11, 0, 0),
        max_points=2,
    )

    assert len(prices.prices) == 1
    assert "/prices/IX.D.NASDAQ.IFD.IP/MINUTE/2" in http_client.requests[-1]["url"]


def test_build_historical_fallback_ladder_skips_larger_values() -> None:
    assert build_historical_fallback_ladder(8640) == [8640, 5000, 3000, 2000, 1000, 600, 300, 120]
    assert build_historical_fallback_ladder(700) == [700, 600, 300, 120]


def test_is_historical_allowance_error_matches_ig_error_code() -> None:
    assert is_historical_allowance_error(
        "HTTP 403 {'errorCode': 'error.public-api.exceeded-account-historical-data-allowance'}"
    )
    assert is_historical_allowance_error("exceeded-account-historical-data-allowance")
    assert not is_historical_allowance_error("error.public-api.exceeded-api-key-allowance")


def test_adaptive_history_fallback_uses_first_successful_attempt() -> None:
    class FallbackClient(FakeHttpClient):
        def request(self, method, url, *, headers, json_body=None, timeout):
            if "/prices/IX.D.NASDAQ.IFD.IP/MINUTE_5/8640" in url:
                return HttpResponse(
                    status_code=403,
                    headers={},
                    body={
                        "errorCode": "error.public-api.exceeded-account-historical-data-allowance"
                    },
                )
            if "/prices/IX.D.NASDAQ.IFD.IP/MINUTE_5/5000" in url:
                return HttpResponse(
                    status_code=200,
                    headers={},
                    body={"prices": [{"snapshotTime": "2026/05/07 10:00:00"}]},
                )
            return super().request(
                method,
                url,
                headers=headers,
                json_body=json_body,
                timeout=timeout,
            )

    adapter = IGRestAdapter(environment=IGEnvironment.DEMO, http_client=FallbackClient())
    adapter.login(IGCredentials("demo-user", "fake-password", "fake-api-key"))

    result = load_prices_with_adaptive_fallback(
        adapter,
        "IX.D.NASDAQ.IFD.IP",
        resolution="MINUTE_5",
        requested_max_points=8640,
    )

    assert result.succeeded is True
    assert result.selected_max_points == 5000
    assert len(result.attempts) == 2
    assert result.attempts[0].success is False
    assert result.attempts[1].success is True


def test_adaptive_history_fallback_allows_all_fail_result() -> None:
    class FailingFallbackClient(FakeHttpClient):
        def request(self, method, url, *, headers, json_body=None, timeout):
            if "/prices/IX.D.NASDAQ.IFD.IP/MINUTE_5/" in url:
                return HttpResponse(
                    status_code=403,
                    headers={},
                    body={
                        "errorCode": "error.public-api.exceeded-account-historical-data-allowance"
                    },
                )
            return super().request(
                method,
                url,
                headers=headers,
                json_body=json_body,
                timeout=timeout,
            )

    adapter = IGRestAdapter(environment=IGEnvironment.DEMO, http_client=FailingFallbackClient())
    adapter.login(IGCredentials("demo-user", "fake-password", "fake-api-key"))

    result = load_prices_with_adaptive_fallback(
        adapter,
        "IX.D.NASDAQ.IFD.IP",
        resolution="MINUTE_5",
        requested_max_points=8640,
    )

    assert result.succeeded is False
    assert result.series is None
    assert result.selected_max_points is None
    assert len(result.attempts) == len(build_historical_fallback_ladder(8640))
