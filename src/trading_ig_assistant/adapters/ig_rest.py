"""Read-only IG REST adapter skeleton for P00 validation."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Protocol

from trading_ig_assistant.adapters.credentials import IGCredentials
from trading_ig_assistant.app.config import IGEnvironment
from trading_ig_assistant.domain.instruments import Account, MarketDetails, MarketSummary
from trading_ig_assistant.domain.market_data import PriceSeries
from trading_ig_assistant.utils.redaction import redact_mapping

IG_DEMO_BASE_URL = "https://demo-api.ig.com/gateway/deal"
IG_LIVE_BASE_URL = "https://api.ig.com/gateway/deal"


class IGAPIError(RuntimeError):
    """Raised when IG returns an error or a malformed response."""


class LiveTradingDisabledError(RuntimeError):
    """Raised for any order-execution attempt in P00."""


@dataclass(frozen=True)
class IGSession:
    cst: str = field(repr=False)
    security_token: str = field(repr=False)
    current_account_id: str | None = None
    lightstreamer_endpoint: str | None = None


@dataclass(frozen=True)
class HttpResponse:
    status_code: int
    headers: dict[str, str]
    body: dict[str, Any]


class HttpClient(Protocol):
    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        json_body: dict[str, Any] | None = None,
        timeout: float,
    ) -> HttpResponse:
        """Perform an HTTP request."""


class UrllibHttpClient:
    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str],
        json_body: dict[str, Any] | None = None,
        timeout: float,
    ) -> HttpResponse:
        body_bytes = None
        if json_body is not None:
            body_bytes = json.dumps(json_body).encode("utf-8")
            headers = {**headers, "Content-Type": "application/json; charset=UTF-8"}

        request = urllib.request.Request(
            url=url,
            data=body_bytes,
            headers=headers,
            method=method.upper(),
        )

        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw_body = response.read().decode("utf-8")
                parsed_body = json.loads(raw_body) if raw_body else {}
                return HttpResponse(
                    status_code=response.status,
                    headers=dict(response.headers.items()),
                    body=parsed_body,
                )
        except urllib.error.HTTPError as exc:
            raw_body = exc.read().decode("utf-8")
            try:
                parsed_body = json.loads(raw_body) if raw_body else {}
            except json.JSONDecodeError:
                parsed_body = {"error": raw_body}
            raise IGAPIError(
                f"IG REST request failed with HTTP {exc.code}: {redact_mapping(parsed_body)}"
            ) from exc
        except urllib.error.URLError as exc:
            raise IGAPIError(f"IG REST request failed: {exc.reason}") from exc


class IGRestAdapter:
    """Broker-facing REST adapter.

    P00 supports authentication and read-only data retrieval. All order paths are hard-blocked.
    """

    def __init__(
        self,
        environment: IGEnvironment = IGEnvironment.DEMO,
        *,
        http_client: HttpClient | None = None,
        timeout: float = 10.0,
        read_only: bool = True,
    ) -> None:
        self.environment = environment
        self.timeout = timeout
        self.read_only = read_only
        self._http_client = http_client or UrllibHttpClient()
        self._session: IGSession | None = None
        self._api_key: str | None = None

    @property
    def base_url(self) -> str:
        if self.environment == IGEnvironment.LIVE:
            return IG_LIVE_BASE_URL
        return IG_DEMO_BASE_URL

    @property
    def session(self) -> IGSession | None:
        return self._session

    def login(self, credentials: IGCredentials) -> IGSession:
        self._api_key = credentials.api_key.reveal()
        response = self._request(
            "POST",
            "/session",
            version="2",
            json_body={
                "identifier": credentials.username,
                "password": credentials.password.reveal(),
            },
            include_session=False,
        )
        cst = _case_insensitive_header(response.headers, "CST")
        security_token = _case_insensitive_header(response.headers, "X-SECURITY-TOKEN")
        if not cst or not security_token:
            raise IGAPIError("IG login succeeded without expected session tokens.")

        self._session = IGSession(
            cst=cst,
            security_token=security_token,
            current_account_id=response.body.get("currentAccountId"),
            lightstreamer_endpoint=response.body.get("lightstreamerEndpoint"),
        )
        return self._session

    def logout(self) -> None:
        if self._session is not None:
            try:
                self._request("DELETE", "/session", version="1", include_session=True)
            except IGAPIError as exc:
                if "invalid-security-token" not in str(exc):
                    raise
        self._session = None

    def get_accounts(self) -> list[Account]:
        response = self._request("GET", "/accounts", version="1")
        accounts = response.body.get("accounts", [])
        return [
            Account(
                account_id=str(item.get("accountId", "")),
                account_name=str(item.get("accountName", "")),
                account_type=item.get("accountType"),
                currency=item.get("currency"),
                balance=_optional_float(item.get("balance", {}).get("balance")),
                available=_optional_float(item.get("balance", {}).get("available")),
                deposit=_optional_float(item.get("balance", {}).get("deposit")),
                profit_loss=_optional_float(item.get("balance", {}).get("profitLoss")),
                preferred=bool(item.get("preferred", False)),
                raw=item,
            )
            for item in accounts
        ]

    def search_markets(self, query: str) -> list[MarketSummary]:
        encoded_query = urllib.parse.urlencode({"searchTerm": query})
        response = self._request("GET", f"/markets?{encoded_query}", version="1")
        markets = response.body.get("markets", [])
        return [
            MarketSummary(
                epic=str(item.get("epic", "")),
                instrument_name=str(item.get("instrumentName", "")),
                instrument_type=item.get("instrumentType"),
                expiry=item.get("expiry"),
                market_status=item.get("marketStatus"),
                raw=item,
            )
            for item in markets
        ]

    def get_market_details(self, epic: str) -> MarketDetails:
        encoded_epic = urllib.parse.quote(epic, safe="")
        response = self._request("GET", f"/markets/{encoded_epic}", version="3")
        instrument = response.body.get("instrument", {})
        return MarketDetails(
            epic=str(instrument.get("epic") or response.body.get("epic") or epic),
            instrument_name=str(instrument.get("name") or instrument.get("instrumentName") or ""),
            raw=response.body,
        )

    def get_prices(
        self,
        epic: str,
        *,
        resolution: str = "MINUTE",
        max_points: int = 10,
    ) -> PriceSeries:
        encoded_epic = urllib.parse.quote(epic, safe="")
        response = self._request(
            "GET",
            f"/prices/{encoded_epic}/{resolution}/{max_points}",
            version="3",
        )
        return PriceSeries(
            epic=epic,
            prices=list(response.body.get("prices", [])),
            raw=response.body,
        )

    def create_otc_position(self, *_args: Any, **_kwargs: Any) -> None:
        raise LiveTradingDisabledError("Live order execution is not implemented in P00.")

    def update_position(self, *_args: Any, **_kwargs: Any) -> None:
        raise LiveTradingDisabledError("Position updates are not implemented in P00.")

    def close_position(self, *_args: Any, **_kwargs: Any) -> None:
        raise LiveTradingDisabledError("Position closing is not implemented in P00.")

    def create_working_order(self, *_args: Any, **_kwargs: Any) -> None:
        raise LiveTradingDisabledError("Working-order execution is not implemented in P00.")

    def _request(
        self,
        method: str,
        path: str,
        *,
        version: str,
        json_body: dict[str, Any] | None = None,
        include_session: bool = True,
    ) -> HttpResponse:
        headers = {
            "Accept": "application/json; charset=UTF-8",
            "VERSION": version,
        }
        if self._api_key:
            headers["X-IG-API-KEY"] = self._api_key
        if include_session:
            if self._session is None:
                raise IGAPIError("IG REST session is not authenticated.")
            headers["CST"] = self._session.cst
            headers["X-SECURITY-TOKEN"] = self._session.security_token

        response = self._http_client.request(
            method,
            f"{self.base_url}{path}",
            headers=headers,
            json_body=json_body,
            timeout=self.timeout,
        )
        if response.status_code >= 400:
            raise IGAPIError(
                f"IG REST request failed with HTTP {response.status_code}: "
                f"{redact_mapping(response.body)}"
            )
        return response


def _case_insensitive_header(headers: dict[str, str], name: str) -> str | None:
    for key, value in headers.items():
        if key.lower() == name.lower():
            return value
    return None


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
