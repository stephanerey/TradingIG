"""Explicit, bounded API connection probes used only from the Settings worker."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener

from trading_ig_assistant.adapters.credentials import SecretValue
from trading_ig_assistant.adapters.gdelt_news import GdeltNewsError, GdeltNewsProvider
from trading_ig_assistant.adapters.tavily_news import (
    TavilyNewsConfig,
    TavilyNewsError,
    TavilyNewsProvider,
)
from trading_ig_assistant.domain.api_credentials import (
    ApiConnectionTestResult,
    ApiProviderDefinition,
    ApiProviderStatus,
)
from trading_ig_assistant.domain.context_sources import ContextCategory
from trading_ig_assistant.domain.market_intelligence import NewsSearchRequest


class TavilyConnectionTester:
    """One explicit Basic search; it may consume one Tavily credit."""

    def __call__(
        self,
        definition: ApiProviderDefinition,
        key: SecretValue | None,
    ) -> ApiConnectionTestResult:
        now = datetime.now(UTC)
        if key is None:
            return ApiConnectionTestResult(
                provider_id=definition.provider_id,
                status=ApiProviderStatus.NOT_CONFIGURED,
                reason_code="API_KEY_MISSING",
                tested_at_utc=now,
            )
        try:
            result = TavilyNewsProvider(TavilyNewsConfig(api_key=key)).search_news(
                NewsSearchRequest(
                    "global financial markets",
                    ContextCategory.OTHER,
                    recent_window=timedelta(hours=1),
                    max_results=1,
                ),
                as_of_utc=now,
            )
        except TavilyNewsError as exc:
            if exc.reason_code == "TAVILY_QUOTA_EXHAUSTED":
                return ApiConnectionTestResult(
                    provider_id=definition.provider_id,
                    status=ApiProviderStatus.QUOTA_EXHAUSTED,
                    reason_code=exc.reason_code,
                    tested_at_utc=now,
                    quota_remaining=0,
                )
            raise
        return ApiConnectionTestResult(
            provider_id=definition.provider_id,
            status=ApiProviderStatus.CONNECTED,
            reason_code="CONNECTION_TEST_SUCCEEDED",
            tested_at_utc=now,
            quota_used=result.usage.credits if result.usage is not None else None,
        )


class GdeltConnectionTester:
    """One public bounded metadata query; no API key or subscription."""

    def __call__(
        self,
        definition: ApiProviderDefinition,
        key: SecretValue | None,
    ) -> ApiConnectionTestResult:
        del key
        now = datetime.now(UTC)
        try:
            GdeltNewsProvider().search_news(
                NewsSearchRequest(
                    "global markets",
                    ContextCategory.GEOPOLITICAL,
                    recent_window=timedelta(hours=1),
                    max_results=1,
                ),
                as_of_utc=now,
            )
        except GdeltNewsError as exc:
            if exc.reason_code == "GDELT_RATE_LIMITED":
                return ApiConnectionTestResult(
                    provider_id=definition.provider_id,
                    status=ApiProviderStatus.QUOTA_EXHAUSTED,
                    reason_code=exc.reason_code,
                    tested_at_utc=now,
                )
            raise
        return ApiConnectionTestResult(
            provider_id=definition.provider_id,
            status=ApiProviderStatus.CONNECTED,
            reason_code="CONNECTION_TEST_SUCCEEDED",
            tested_at_utc=now,
        )


class BoundedJsonConnectionTester:
    """Read-only bounded probes for FRED, EIA and OpenAI metadata endpoints."""

    _endpoints = {
        "fred": "https://api.stlouisfed.org/fred/series",
        "eia": "https://api.eia.gov/v2/",
        "openai": "https://api.openai.com/v1/models",
    }

    def __call__(
        self,
        definition: ApiProviderDefinition,
        key: SecretValue | None,
    ) -> ApiConnectionTestResult:
        now = datetime.now(UTC)
        if key is None:
            return ApiConnectionTestResult(
                provider_id=definition.provider_id,
                status=ApiProviderStatus.NOT_CONFIGURED,
                reason_code="API_KEY_MISSING",
                tested_at_utc=now,
            )
        endpoint = self._endpoints[definition.provider_id]
        headers = {
            "Accept": "application/json",
            "User-Agent": "TradingIG-api-credential-test/0.1",
        }
        if definition.provider_id == "fred":
            endpoint += "?" + urlencode(
                {
                    "series_id": "GDP",
                    "file_type": "json",
                    "api_key": key.reveal(),
                }
            )
        elif definition.provider_id == "eia":
            endpoint += "?" + urlencode({"api_key": key.reveal()})
        else:
            headers["Authorization"] = f"Bearer {key.reveal()}"
        request = Request(endpoint, headers=headers, method="GET")
        try:
            with build_opener(_NoRedirect()).open(  # noqa: S310 - pinned HTTPS
                request,
                timeout=8.0,
            ) as response:
                response.read(262_145)
                remaining = _optional_int(
                    response.headers.get("x-ratelimit-remaining-requests")
                )
        except HTTPError as exc:
            status = (
                ApiProviderStatus.QUOTA_EXHAUSTED
                if exc.code == 429
                else ApiProviderStatus.ERROR
            )
            reason = "PROVIDER_QUOTA_EXHAUSTED" if exc.code == 429 else "PROVIDER_HTTP_ERROR"
            return ApiConnectionTestResult(
                provider_id=definition.provider_id,
                status=status,
                reason_code=reason,
                tested_at_utc=now,
                quota_remaining=0 if exc.code == 429 else None,
            )
        except (URLError, TimeoutError):
            return ApiConnectionTestResult(
                provider_id=definition.provider_id,
                status=ApiProviderStatus.ERROR,
                reason_code="PROVIDER_NETWORK_ERROR",
                tested_at_utc=now,
            )
        return ApiConnectionTestResult(
            provider_id=definition.provider_id,
            status=ApiProviderStatus.CONNECTED,
            reason_code="CONNECTION_TEST_SUCCEEDED",
            tested_at_utc=now,
            quota_remaining=remaining,
        )


def _optional_int(value: object) -> int | None:
    try:
        return int(str(value)) if value is not None else None
    except ValueError:
        return None


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001, ANN201
        return None
