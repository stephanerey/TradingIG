"""Strict Trading Economics economic-calendar adapter with injected credentials and transport."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from trading_ig_assistant.adapters.credentials import SecretValue
from trading_ig_assistant.domain.context_sources import (
    ContextCategory,
    ContextImportance,
    MacroEvent,
    SourceUsageRights,
)

TRADING_ECONOMICS_API_ORIGIN = "https://api.tradingeconomics.com"


class TradingEconomicsCalendarError(RuntimeError):
    """Raised when calendar data cannot satisfy the normalized contract."""


@dataclass(frozen=True)
class CalendarHttpResponse:
    body: bytes
    final_url: str
    content_type: str


CalendarTransport = Callable[
    [str, Mapping[str, str], float, int],
    CalendarHttpResponse,
]


@dataclass(frozen=True, repr=False)
class TradingEconomicsCalendarConfig:
    api_key: SecretValue
    countries: tuple[str, ...]
    category_map: tuple[tuple[str, ContextCategory], ...] = ()
    usage_rights: SourceUsageRights = SourceUsageRights.UNKNOWN
    endpoint_origin: str = TRADING_ECONOMICS_API_ORIGIN
    timeout_seconds: float = 8.0
    max_payload_bytes: int = 1_000_000
    max_events: int = 500
    max_window: timedelta = timedelta(days=31)

    def __init__(
        self,
        *,
        api_key: SecretValue | str,
        countries: Sequence[str],
        category_map: Sequence[tuple[str, ContextCategory]] = (),
        usage_rights: SourceUsageRights = SourceUsageRights.UNKNOWN,
        endpoint_origin: str = TRADING_ECONOMICS_API_ORIGIN,
        timeout_seconds: float = 8.0,
        max_payload_bytes: int = 1_000_000,
        max_events: int = 500,
        max_window: timedelta = timedelta(days=31),
    ) -> None:
        object.__setattr__(
            self,
            "api_key",
            api_key if isinstance(api_key, SecretValue) else SecretValue(api_key),
        )
        object.__setattr__(self, "countries", tuple(item.strip() for item in countries))
        object.__setattr__(
            self,
            "category_map",
            tuple((name.strip(), category) for name, category in category_map),
        )
        object.__setattr__(self, "usage_rights", usage_rights)
        object.__setattr__(self, "endpoint_origin", endpoint_origin)
        object.__setattr__(self, "timeout_seconds", timeout_seconds)
        object.__setattr__(self, "max_payload_bytes", max_payload_bytes)
        object.__setattr__(self, "max_events", max_events)
        object.__setattr__(self, "max_window", max_window)
        self._validate()

    def _validate(self) -> None:
        if self.endpoint_origin != TRADING_ECONOMICS_API_ORIGIN:
            raise ValueError("Trading Economics endpoint must use the pinned official HTTPS origin")
        if not self.countries or any(not country for country in self.countries):
            raise ValueError("Trading Economics calendar requires explicit countries")
        if len(self.countries) > 10 or len(set(item.casefold() for item in self.countries)) != len(
            self.countries
        ):
            raise ValueError("Trading Economics countries must be unique and bounded")
        category_names = tuple(name.casefold() for name, _category in self.category_map)
        if any(not name for name in category_names) or len(set(category_names)) != len(
            category_names
        ):
            raise ValueError("Trading Economics category mappings must be non-empty and unique")
        if self.timeout_seconds <= 0 or self.max_payload_bytes <= 0 or self.max_events <= 0:
            raise ValueError("Trading Economics network and event limits must be positive")
        if self.max_window <= timedelta(0):
            raise ValueError("Trading Economics maximum window must be positive")


class TradingEconomicsCalendarProvider:
    """Fetch a bounded calendar window without inferring categories or usage rights."""

    def __init__(
        self,
        config: TradingEconomicsCalendarConfig,
        *,
        transport: CalendarTransport | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._config = config
        self._transport = transport or _fetch_calendar
        self._clock = clock or (lambda: datetime.now(UTC))
        self._category_map = {
            name.casefold(): category for name, category in self._config.category_map
        }

    @property
    def provider_id(self) -> str:
        return "trading-economics-calendar"

    def fetch_events(
        self,
        *,
        window_start_utc: datetime,
        window_end_utc: datetime,
    ) -> tuple[MacroEvent, ...]:
        _require_utc(window_start_utc, "calendar window start")
        _require_utc(window_end_utc, "calendar window end")
        if window_end_utc <= window_start_utc:
            raise ValueError("calendar window end must follow its start")
        if window_end_utc - window_start_utc > self._config.max_window:
            raise ValueError("calendar window exceeds the configured maximum")
        observed_at_utc = self._clock()
        _require_utc(observed_at_utc, "calendar observation")
        url = _calendar_url(self._config, window_start_utc, window_end_utc)
        headers = {
            "Accept": "application/json",
            "Authorization": self._config.api_key.reveal(),
            "User-Agent": "TradingIG-context/0.1",
        }
        try:
            response = self._transport(
                url,
                headers,
                self._config.timeout_seconds,
                self._config.max_payload_bytes,
            )
            return self._parse_response(
                response,
                expected_url=url,
                window_start_utc=window_start_utc,
                window_end_utc=window_end_utc,
                observed_at_utc=observed_at_utc,
            )
        except TradingEconomicsCalendarError:
            raise
        except Exception as exc:
            raise TradingEconomicsCalendarError(
                "Trading Economics calendar retrieval failed"
            ) from exc

    def _parse_response(
        self,
        response: CalendarHttpResponse,
        *,
        expected_url: str,
        window_start_utc: datetime,
        window_end_utc: datetime,
        observed_at_utc: datetime,
    ) -> tuple[MacroEvent, ...]:
        if response.final_url != expected_url:
            raise TradingEconomicsCalendarError("Trading Economics response redirected")
        content_type = response.content_type.partition(";")[0].strip().lower()
        if content_type != "application/json":
            raise TradingEconomicsCalendarError(
                "Trading Economics response has an unsupported content type"
            )
        if not response.body or len(response.body) > self._config.max_payload_bytes:
            raise TradingEconomicsCalendarError(
                "Trading Economics response violates the payload size limit"
            )
        try:
            payload = json.loads(response.body)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise TradingEconomicsCalendarError(
                "Trading Economics response is invalid JSON"
            ) from exc
        if not _is_sequence(payload):
            raise TradingEconomicsCalendarError("Trading Economics response must be a JSON array")
        if len(payload) > self._config.max_events:
            raise TradingEconomicsCalendarError(
                "Trading Economics response exceeds the event limit"
            )

        events: list[MacroEvent] = []
        seen_ids: set[str] = set()
        for raw_event in payload:
            event = self._parse_event(raw_event, observed_at_utc)
            if event.event_id in seen_ids:
                raise TradingEconomicsCalendarError(
                    "Trading Economics response contains duplicate event IDs"
                )
            seen_ids.add(event.event_id)
            if window_start_utc <= event.scheduled_at_utc <= window_end_utc:
                events.append(event)
        events.sort(key=lambda item: (item.scheduled_at_utc, item.event_id))
        return tuple(events)

    def _parse_event(self, value: object, observed_at_utc: datetime) -> MacroEvent:
        if not isinstance(value, Mapping):
            raise TradingEconomicsCalendarError("Trading Economics event must be an object")
        calendar_id = _required_text(value, "CalendarId", allow_int=True)
        event_name = _required_text(value, "Event")
        country = _required_text(value, "Country")
        provider_category = _required_text(value, "Category")
        source = _required_text(value, "Source")
        date_span = _required_text(value, "DateSpan")
        if date_span not in {"0", "1"}:
            raise TradingEconomicsCalendarError(
                "Trading Economics event has unsupported timing precision"
            )
        scheduled_at_utc = _parse_provider_timestamp(_required_text(value, "Date"))
        importance = _parse_importance(value.get("Importance"))
        source_url = _optional_https_url(value.get("SourceURL"))
        timing_tag = "scheduled_time_exact" if date_span == "0" else "scheduled_time_estimated"
        category = self._category_map.get(provider_category.casefold(), ContextCategory.OTHER)
        return MacroEvent(
            schema_version=1,
            event_id=f"trading-economics:{calendar_id}",
            title=event_name,
            category=category,
            importance=importance,
            scheduled_at_utc=scheduled_at_utc,
            observed_at_utc=observed_at_utc,
            source=source,
            source_url=source_url,
            usage_rights=self._config.usage_rights,
            tags=(
                self.provider_id,
                f"country:{_slug(country)}",
                f"provider_category:{_slug(provider_category)}",
                timing_tag,
            ),
        )


def _calendar_url(
    config: TradingEconomicsCalendarConfig,
    window_start_utc: datetime,
    window_end_utc: datetime,
) -> str:
    countries = quote(",".join(config.countries), safe=",")
    start = window_start_utc.date().isoformat()
    end = window_end_utc.date().isoformat()
    return f"{config.endpoint_origin}/calendar/country/{countries}/{start}/{end}?f=json"


def _required_text(value: Mapping[str, object], key: str, *, allow_int: bool = False) -> str:
    item = value.get(key)
    if isinstance(item, bool) or not isinstance(item, str | int if allow_int else str):
        raise TradingEconomicsCalendarError(f"Trading Economics event has invalid {key}")
    text = str(item).strip()
    if not text:
        raise TradingEconomicsCalendarError(f"Trading Economics event has invalid {key}")
    return text


def _parse_provider_timestamp(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise TradingEconomicsCalendarError(
            "Trading Economics event has an invalid timestamp"
        ) from exc
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _parse_importance(value: object) -> ContextImportance:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TradingEconomicsCalendarError("Trading Economics event has invalid importance")
    try:
        return {
            1: ContextImportance.LOW,
            2: ContextImportance.MEDIUM,
            3: ContextImportance.HIGH,
        }[value]
    except KeyError as exc:
        raise TradingEconomicsCalendarError(
            "Trading Economics event has unsupported importance"
        ) from exc


def _optional_https_url(value: object) -> str | None:
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        raise TradingEconomicsCalendarError("Trading Economics event has invalid source URL")
    parsed = urlparse(value.strip())
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        return None
    return value.strip()


def _slug(value: str) -> str:
    return "-".join(value.casefold().split())


def _require_utc(value: datetime, label: str) -> None:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError(f"{label} must use UTC")


def _is_sequence(value: object) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))


class _NoRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _fetch_calendar(
    url: str,
    headers: Mapping[str, str],
    timeout_seconds: float,
    max_payload_bytes: int,
) -> CalendarHttpResponse:
    request = Request(url, headers=dict(headers), method="GET")
    opener = build_opener(_NoRedirectHandler())
    try:
        with opener.open(request, timeout=timeout_seconds) as response:
            body = response.read(max_payload_bytes + 1)
            final_url = response.geturl()
            content_type = response.headers.get("Content-Type", "")
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise TradingEconomicsCalendarError("Trading Economics calendar retrieval failed") from exc
    if len(body) > max_payload_bytes:
        raise TradingEconomicsCalendarError(
            "Trading Economics response exceeds the payload size limit"
        )
    return CalendarHttpResponse(body=body, final_url=final_url, content_type=content_type)
