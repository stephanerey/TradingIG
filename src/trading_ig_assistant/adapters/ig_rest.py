"""Read-only IG REST adapter skeleton for P00 validation."""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any, Protocol

from trading_ig_assistant.adapters.credentials import IGCredentials
from trading_ig_assistant.app.config import IGEnvironment
from trading_ig_assistant.domain.instruments import (
    Account,
    MarketCategory,
    MarketDetails,
    MarketNavigation,
    MarketNavigationNode,
    MarketSummary,
)
from trading_ig_assistant.domain.market_data import PriceSeries
from trading_ig_assistant.utils.redaction import mask_identifier, redact_mapping

IG_DEMO_BASE_URL = "https://demo-api.ig.com/gateway/deal"
IG_LIVE_BASE_URL = "https://api.ig.com/gateway/deal"
LOGGER = logging.getLogger(__name__)


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
            LOGGER.debug(
                "HTTP request start method=%s url=%s headers=%s has_body=%s timeout=%s",
                method.upper(),
                _safe_url_for_log(url),
                redact_mapping(headers),
                json_body is not None,
                timeout,
            )
            with urllib.request.urlopen(request, timeout=timeout) as response:
                raw_body = response.read().decode("utf-8")
                parsed_body = json.loads(raw_body) if raw_body else {}
                LOGGER.debug(
                    "HTTP request success method=%s url=%s status=%s",
                    method.upper(),
                    _safe_url_for_log(url),
                    response.status,
                )
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
            LOGGER.debug(
                "HTTP request HTTPError method=%s url=%s status=%s body=%s",
                method.upper(),
                _safe_url_for_log(url),
                exc.code,
                redact_mapping(parsed_body),
            )
            raise IGAPIError(
                f"IG REST request failed with HTTP {exc.code}: {redact_mapping(parsed_body)}"
            ) from exc
        except urllib.error.URLError as exc:
            LOGGER.debug(
                "HTTP request URLError method=%s url=%s reason=%s",
                method.upper(),
                _safe_url_for_log(url),
                exc.reason,
            )
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
        LOGGER.debug(
            "IG login start environment=%s identifier=%s",
            self.environment.value,
            credentials.username,
        )
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
        LOGGER.debug(
            "IG login success environment=%s current_account=%s lightstreamer=%s",
            self.environment.value,
            mask_identifier(self._session.current_account_id),
            bool(self._session.lightstreamer_endpoint),
        )
        return self._session

    def logout(self) -> None:
        LOGGER.debug(
            "IG logout start environment=%s has_session=%s",
            self.environment.value,
            self._session is not None,
        )
        if self._session is not None:
            try:
                self._request("DELETE", "/session", version="1", include_session=True)
            except IGAPIError as exc:
                if not is_invalid_security_token_error(exc):
                    raise
                LOGGER.debug("IG logout ignored invalid security token")
        self._session = None
        LOGGER.debug("IG logout complete environment=%s", self.environment.value)

    def switch_account(self, account_id: str, *, set_default: bool = False) -> IGSession:
        """Switch the active IG account for subsequent read-only calls.

        IG may return a new security token when changing account context. Preserve and reuse it
        immediately so later requests do not keep using a stale token.
        """

        if self._session is None:
            raise IGAPIError("IG REST session is not authenticated.")
        LOGGER.debug(
            "IG switch account start environment=%s account=%s set_default=%s",
            self.environment.value,
            mask_identifier(account_id),
            set_default,
        )
        response = self._request(
            "PUT",
            "/session",
            version="1",
            json_body={"accountId": account_id, "defaultAccount": set_default},
            include_session=True,
        )
        cst = _case_insensitive_header(response.headers, "CST") or self._session.cst
        security_token = (
            _case_insensitive_header(response.headers, "X-SECURITY-TOKEN")
            or self._session.security_token
        )
        self._session = IGSession(
            cst=cst,
            security_token=security_token,
            current_account_id=account_id,
            lightstreamer_endpoint=self._session.lightstreamer_endpoint,
        )
        LOGGER.debug(
            "IG switch account success environment=%s account=%s token_refreshed=%s",
            self.environment.value,
            mask_identifier(account_id),
            bool(_case_insensitive_header(response.headers, "X-SECURITY-TOKEN")),
        )
        return self._session

    def get_accounts(self) -> list[Account]:
        LOGGER.debug("IG get accounts start environment=%s", self.environment.value)
        response = self._request("GET", "/accounts", version="1")
        accounts = response.body.get("accounts", [])
        parsed_accounts = [
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
        LOGGER.debug("IG get accounts success count=%s", len(parsed_accounts))
        return parsed_accounts

    def search_markets(self, query: str) -> list[MarketSummary]:
        LOGGER.debug("IG search markets start query=%r", query)
        encoded_query = urllib.parse.urlencode({"searchTerm": query})
        response = self._request("GET", f"/markets?{encoded_query}", version="1")
        markets = response.body.get("markets", [])
        parsed_markets = [_market_summary_from_mapping(item) for item in markets]
        LOGGER.debug("IG search markets success query=%r count=%s", query, len(parsed_markets))
        return parsed_markets

    def get_categories(self) -> list[MarketCategory]:
        LOGGER.debug("IG categories start environment=%s", self.environment.value)
        response = self._request("GET", "/categories", version="1")
        categories = response.body.get("categories", [])
        parsed_categories = [
            MarketCategory(
                category_id=str(item.get("id") or item.get("categoryId") or ""),
                name=str(item.get("name") or item.get("categoryName") or ""),
                raw=item,
            )
            for item in categories
        ]
        LOGGER.debug("IG categories success count=%s", len(parsed_categories))
        return parsed_categories

    def get_category_instruments(self, category_id: str) -> list[MarketSummary]:
        LOGGER.debug("IG category instruments start category_id=%s", category_id)
        encoded_id = urllib.parse.quote(category_id, safe="")
        response = self._request("GET", f"/categories/{encoded_id}/instruments", version="1")
        instruments = (
            response.body.get("instruments")
            or response.body.get("markets")
            or response.body.get("marketDetails")
            or []
        )
        parsed_instruments = [_market_summary_from_mapping(item) for item in instruments]
        LOGGER.debug(
            "IG category instruments success category_id=%s count=%s",
            category_id,
            len(parsed_instruments),
        )
        return parsed_instruments

    def get_market_navigation(self, node_id: str | None = None) -> MarketNavigation:
        LOGGER.debug("IG market navigation start node_id=%s", node_id or "<root>")
        response = self._request_market_navigation(node_id)
        nodes = [
            MarketNavigationNode(
                node_id=str(item.get("id", "")),
                name=str(item.get("name", "")),
                raw=item,
            )
            for item in response.body.get("nodes", [])
        ]
        markets = [_market_summary_from_mapping(item) for item in response.body.get("markets", [])]
        LOGGER.debug(
            "IG market navigation success node_id=%s nodes=%s markets=%s",
            node_id or "<root>",
            len(nodes),
            len(markets),
        )
        return MarketNavigation(nodes=nodes, markets=markets, raw=response.body)

    def _request_market_navigation(self, node_id: str | None = None) -> HttpResponse:
        suffix = f"/{urllib.parse.quote(node_id, safe='')}" if node_id else ""
        primary_path = f"/market-navigation{suffix}"
        try:
            return self._request("GET", primary_path, version="1")
        except IGAPIError as exc:
            if "HTTP 404" not in str(exc):
                raise
            LOGGER.debug(
                "IG market navigation primary path unavailable; trying legacy path node_id=%s",
                node_id or "<root>",
            )
        return self._request("GET", f"/marketnavigation{suffix}", version="1")

    def get_market_details(self, epic: str) -> MarketDetails:
        LOGGER.debug("IG market details start epic=%s", epic)
        encoded_epic = urllib.parse.quote(epic, safe="")
        response = self._request("GET", f"/markets/{encoded_epic}", version="3")
        instrument = response.body.get("instrument", {})
        details = MarketDetails(
            epic=str(instrument.get("epic") or response.body.get("epic") or epic),
            instrument_name=str(instrument.get("name") or instrument.get("instrumentName") or ""),
            raw=response.body,
        )
        LOGGER.debug("IG market details success epic=%s name=%r", epic, details.instrument_name)
        return details

    def get_prices(
        self,
        epic: str,
        *,
        resolution: str = "MINUTE",
        max_points: int = 10,
    ) -> PriceSeries:
        LOGGER.debug(
            "IG prices start epic=%s resolution=%s max_points=%s",
            epic,
            resolution,
            max_points,
        )
        encoded_epic = urllib.parse.quote(epic, safe="")
        response = self._request(
            "GET",
            f"/prices/{encoded_epic}/{resolution}/{max_points}",
            version="3",
        )
        series = PriceSeries(
            epic=epic,
            prices=list(response.body.get("prices", [])),
            raw=response.body,
        )
        LOGGER.debug("IG prices success epic=%s count=%s", epic, len(series.prices))
        return series

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


def is_invalid_security_token_error(error: Exception | str) -> bool:
    message = str(error).lower()
    return (
        "invalid-security-token" in message
        or "client-token-invalid" in message
        or "invalid security token" in message
    )


def _safe_url_for_log(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, "", ""))


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _market_summary_from_mapping(item: dict[str, Any]) -> MarketSummary:
    return MarketSummary(
        epic=str(item.get("epic", "")),
        instrument_name=str(
            item.get("instrumentName") or item.get("name") or item.get("instrument") or ""
        ),
        instrument_type=item.get("instrumentType"),
        expiry=item.get("expiry"),
        market_status=item.get("marketStatus"),
        raw=item,
    )
