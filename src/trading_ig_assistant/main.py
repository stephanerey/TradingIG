"""Console entry point for Trading IG Assistant."""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from pathlib import Path

from trading_ig_assistant.adapters.credentials import IGCredentials
from trading_ig_assistant.adapters.ig_rest import (
    IGAPIError,
    IGRestAdapter,
    load_prices_with_adaptive_fallback,
)
from trading_ig_assistant.adapters.ig_streaming import IGStreamingAdapter
from trading_ig_assistant.app.config import AppConfig, IGEnvironment, load_config
from trading_ig_assistant.domain.streaming import (
    CHART_CANDLE_SPEC,
    GENERIC_QUOTE_FIELDS,
    MARKET_QUOTE_FIELDS,
    MARKET_QUOTE_SPEC,
    PRICE_QUOTE_FIELDS,
    PRICE_QUOTE_SPEC,
    StreamDiagnosticResult,
    StreamState,
    StreamSubscriptionSpec,
)
from trading_ig_assistant.services.product_discovery_service import (
    DEFAULT_WATCHLIST_SEARCH_TERMS,
    ProductDiscoveryResult,
    ProductDiscoveryService,
    write_discovery_report,
)
from trading_ig_assistant.utils.logging_config import configure_logging
from trading_ig_assistant.utils.redaction import mask_identifier, redact_mapping, redact_text

LOGGER = logging.getLogger(__name__)


def main(argv: list[str] | None = None) -> int:
    log_path = configure_logging()
    LOGGER.debug(
        "Application entry start argv=%s log_path=%s",
        argv if argv is not None else sys.argv[1:],
        log_path,
    )
    effective_argv = sys.argv[1:] if argv is None else argv
    if not effective_argv:
        return launch_gui(argparse.Namespace())

    parser = build_parser()
    args = parser.parse_args(effective_argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 0
    apply_log_level(getattr(args, "log_level", None))
    return args.func(args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading-ig-assistant",
        description="Trading IG Assistant command line tools.",
    )
    subparsers = parser.add_subparsers()

    check = subparsers.add_parser(
        "check-ig-connectivity",
        help="Validate IG REST connectivity with read-only calls.",
    )
    check.add_argument("--config", type=Path, help="Optional non-secret JSON config path.")
    check.add_argument("--environment", choices=[item.value for item in IGEnvironment])
    check.add_argument("--username")
    check.add_argument("--username-env", default="TRADING_IG_USERNAME")
    check.add_argument("--password-env", default="TRADING_IG_PASSWORD")
    check.add_argument("--api-key-env", default="TRADING_IG_API_KEY")
    check.add_argument("--search", help="Optional market search term.")
    check.add_argument("--epic", help="Optional epic for market details/prices.")
    check.add_argument("--prices", action="store_true", help="Fetch recent prices for --epic.")
    check.set_defaults(func=check_ig_connectivity)

    discover = subparsers.add_parser(
        "discover-products",
        help="Run read-only IG product discovery.",
    )
    add_credential_arguments(discover)
    discover.add_argument("--search", action="append", help="Market search term. Can be repeated.")
    discover.add_argument(
        "--watchlist",
        action="store_true",
        help="Use the initial P01 watchlist search terms.",
    )
    discover.add_argument("--output", type=Path, help="Optional sanitized JSON report path.")
    discover.set_defaults(func=discover_products)

    stream_market_parser = subparsers.add_parser(
        "stream-market",
        help="Run streaming diagnostics for a single IG epic.",
    )
    add_credential_arguments(stream_market_parser)
    stream_market_parser.add_argument("--epic", required=True)
    stream_market_parser.add_argument("--duration", type=float, default=60.0)
    stream_market_parser.add_argument(
        "--try-price-template",
        action="append",
        default=[],
        help="Repeatable custom subscription template, for example MARKET:{epic}.",
    )
    stream_market_parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    )
    stream_market_parser.set_defaults(func=stream_market)

    history_market_parser = subparsers.add_parser(
        "history-market",
        help="Run historical backfill diagnostics for a single IG epic.",
    )
    add_credential_arguments(history_market_parser)
    history_market_parser.add_argument("--epic", required=True)
    history_market_parser.add_argument("--resolution", required=True)
    history_market_parser.add_argument("--max-points", type=int, required=True)
    history_market_parser.add_argument("--fallback-ladder", action="store_true")
    history_market_parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
    )
    history_market_parser.set_defaults(func=history_market)

    gui = subparsers.add_parser("gui", help="Launch the minimal GUI shell.")
    gui.set_defaults(func=launch_gui)

    return parser


def add_credential_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--config", type=Path, help="Optional non-secret JSON config path.")
    parser.add_argument("--environment", choices=[item.value for item in IGEnvironment])
    parser.add_argument("--username")
    parser.add_argument("--username-env", default="TRADING_IG_USERNAME")
    parser.add_argument("--password-env", default="TRADING_IG_PASSWORD")
    parser.add_argument("--api-key-env", default="TRADING_IG_API_KEY")


def check_ig_connectivity(args: argparse.Namespace) -> int:
    LOGGER.debug("CLI check connectivity start environment=%s", args.environment or "<config>")
    loaded = load_read_only_runtime(args)
    if loaded is None:
        print(
            "Missing IG credentials. Provide username and set password/API key environment "
            "variables. No secrets should be placed in config files.",
            file=sys.stderr,
        )
        return 2
    environment, credentials = loaded

    adapter = IGRestAdapter(environment=environment, read_only=True)

    try:
        session = adapter.login(credentials)
        print(
            "Authenticated with IG REST "
            f"environment={environment.value} "
            f"current_account_id={session.current_account_id or 'unknown'}"
        )

        accounts = adapter.get_accounts()
        print(f"Accounts fetched: {len(accounts)}")

        if args.search:
            markets = adapter.search_markets(args.search)
            print(f"Markets matched for {args.search!r}: {len(markets)}")
            for market in markets[:5]:
                print(
                    f"- {market.instrument_name} | epic={market.epic} | "
                    f"type={market.instrument_type or 'unknown'} | "
                    f"status={market.market_status or 'unknown'}"
                )

        if args.epic:
            details = adapter.get_market_details(args.epic)
            print(f"Market details fetched: {details.instrument_name or details.epic}")

        if args.prices:
            if not args.epic:
                print("--prices requires --epic", file=sys.stderr)
                return 2
            prices = adapter.get_prices(args.epic)
            print(f"Prices fetched for {args.epic}: {len(prices.prices)}")

        return 0
    except IGAPIError as exc:
        LOGGER.debug("CLI check connectivity failed error=%s", exc)
        print(f"IG connectivity check failed: {exc}", file=sys.stderr)
        return 1
    finally:
        try:
            adapter.logout()
        except IGAPIError:
            pass


def discover_products(args: argparse.Namespace) -> int:
    LOGGER.debug("CLI discover products start environment=%s", args.environment or "<config>")
    loaded = load_read_only_runtime(args)
    if loaded is None:
        print(
            "Missing IG credentials. Provide username and set password/API key environment "
            "variables. No secrets should be placed in config files.",
            file=sys.stderr,
        )
        return 2
    environment, credentials = loaded
    search_terms = build_search_terms(args)

    adapter = IGRestAdapter(environment=environment, read_only=True)
    service = ProductDiscoveryService(adapter)

    try:
        adapter.login(credentials)
        results = [service.discover_products(search_term) for search_term in search_terms]
        print_discovery_results(results)
        if args.output:
            write_discovery_report(results, args.output)
            print(f"Sanitized discovery report written to {args.output}")
        return 0
    except IGAPIError as exc:
        LOGGER.debug("CLI discover products failed error=%s", exc)
        print(f"IG product discovery failed: {exc}", file=sys.stderr)
        return 1
    finally:
        try:
            adapter.logout()
        except IGAPIError:
            pass


def stream_market(args: argparse.Namespace) -> int:
    LOGGER.debug("CLI stream market start environment=%s epic=%s", args.environment, args.epic)
    loaded = load_read_only_runtime(args)
    if loaded is None:
        print(
            "Missing IG credentials. Provide username and set password/API key environment "
            "variables. No secrets should be placed in config files.",
            file=sys.stderr,
        )
        return 2
    environment, credentials = loaded
    adapter = IGRestAdapter(environment=environment, read_only=True)

    try:
        session = adapter.login(credentials)
        masked_account_id = mask_identifier(session.current_account_id)
        print(f"Environment: {environment.value}")
        print(f"Account: {masked_account_id}")
        endpoint_present = "yes" if session.lightstreamer_endpoint else "no"
        print(f"Lightstreamer endpoint present: {endpoint_present}")
        print("")
        if session.current_account_id is None:
            print(
                "Streaming diagnostics failed: no active account id returned by IG.",
                file=sys.stderr,
            )
            return 1

        for spec in _diagnostic_specs_from_args(args):
            result = run_stream_diagnostic(
                session=session,
                account_id=session.current_account_id,
                epic=args.epic,
                spec=spec,
                duration_seconds=args.duration,
                secrets=[
                    credentials.password.reveal(),
                    credentials.api_key.reveal(),
                    session.cst,
                    session.security_token,
                ],
            )
            print_stream_diagnostic_result(result, account_id=session.current_account_id)
            print("")
        return 0
    except IGAPIError as exc:
        print(f"Streaming diagnostics failed: {exc}", file=sys.stderr)
        return 1
    finally:
        try:
            adapter.logout()
        except IGAPIError:
            pass


def history_market(args: argparse.Namespace) -> int:
    LOGGER.debug(
        "CLI history market start environment=%s epic=%s resolution=%s max_points=%s ladder=%s",
        args.environment,
        args.epic,
        args.resolution,
        args.max_points,
        args.fallback_ladder,
    )
    loaded = load_read_only_runtime(args)
    if loaded is None:
        print(
            "Missing IG credentials. Provide username and set password/API key environment "
            "variables. No secrets should be placed in config files.",
            file=sys.stderr,
        )
        return 2
    environment, credentials = loaded
    adapter = IGRestAdapter(environment=environment, read_only=True)
    try:
        session = adapter.login(credentials)
        print(f"Environment: {environment.value}")
        print(f"Account: {mask_identifier(session.current_account_id)}")
        print(f"Epic: {args.epic}")
        print(f"Resolution: {args.resolution}")
        print(f"Requested max_points: {args.max_points}")
        result = load_prices_with_adaptive_fallback(
            adapter,
            args.epic,
            resolution=args.resolution,
            requested_max_points=args.max_points,
            use_fallback_ladder=bool(args.fallback_ladder),
        )
        for attempt in result.attempts:
            if attempt.success:
                print(
                    f"Attempt {attempt.max_points}: success "
                    f"({attempt.price_count} candles)"
                )
            else:
                sanitized_error = redact_text(
                    attempt.error or "unknown",
                    [credentials.password.reveal(), credentials.api_key.reveal()],
                )
                print(
                    f"Attempt {attempt.max_points}: failed "
                    f"({sanitized_error})"
                )
        print(
            f"Final selected max_points: "
            f"{result.selected_max_points if result.selected_max_points is not None else 'none'}"
        )
        if result.series is None or not result.series.prices:
            print("Number of candles returned: 0")
            return 1
        first_timestamp = result.series.prices[0].get("snapshotTimeUTC") or result.series.prices[
            0
        ].get("snapshotTime")
        last_timestamp = result.series.prices[-1].get("snapshotTimeUTC") or result.series.prices[
            -1
        ].get("snapshotTime")
        print(f"Number of candles returned: {len(result.series.prices)}")
        print(f"First timestamp: {first_timestamp}")
        print(f"Last timestamp: {last_timestamp}")
        return 0
    except IGAPIError as exc:
        print(f"History diagnostics failed: {exc}", file=sys.stderr)
        return 1
    finally:
        try:
            adapter.logout()
        except IGAPIError:
            pass


def launch_gui(_args: argparse.Namespace) -> int:
    LOGGER.debug("CLI launch GUI")
    try:
        from trading_ig_assistant.ui.main_window import run_gui
    except ImportError as exc:
        print(
            "GUI dependencies are missing. Install them with: "
            "python -m pip install -e .[gui,dev]",
            file=sys.stderr,
        )
        print(str(exc), file=sys.stderr)
        return 2
    return run_gui()


def load_read_only_runtime(args: argparse.Namespace) -> tuple[IGEnvironment, IGCredentials] | None:
    config = load_config(args.config) if getattr(args, "config", None) else AppConfig()
    environment = IGEnvironment(args.environment) if args.environment else config.environment
    username = args.username or os.environ.get(args.username_env) or config.ig_username
    password = os.environ.get(args.password_env)
    api_key = os.environ.get(args.api_key_env)
    if not username or not password or not api_key:
        return None
    return environment, IGCredentials(username=username, password=password, api_key=api_key)


def build_search_terms(args: argparse.Namespace) -> list[str]:
    terms: list[str] = []
    if args.watchlist:
        terms.extend(DEFAULT_WATCHLIST_SEARCH_TERMS)
    terms.extend(args.search or [])
    return terms or DEFAULT_WATCHLIST_SEARCH_TERMS


def print_discovery_results(results: list[ProductDiscoveryResult]) -> None:
    for result in results:
        print(
            f"Search {result.search_term!r}: "
            f"{result.candidates_count} candidates, "
            f"{len(result.products)} classified, "
            f"{len(result.errors)} errors"
        )
        for product in result.products[:10]:
            print(
                f"- {product.name or product.epic} | epic={product.epic} | "
                f"type={product.product_type.value} | direction={product.direction.value} | "
                f"expiry={product.expiry or 'unknown'} | status={product.status or 'unknown'}"
            )
        for error in result.errors[:5]:
            print(f"- discovery error epic={error.epic or 'unknown'}: {error.message}")


def apply_log_level(level_name: str | None) -> None:
    if not level_name:
        return
    level = getattr(logging, level_name.upper(), logging.INFO)
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    for handler in root_logger.handlers:
        handler.setLevel(level)


def run_stream_diagnostic(
    *,
    session,
    account_id: str,
    epic: str,
    spec: StreamSubscriptionSpec,
    duration_seconds: float,
    secrets: list[str],
) -> StreamDiagnosticResult:
    item = spec.render_item(epic=epic, account_id=account_id, scale=spec.scale)
    sink = _DiagnosticStreamSink(
        StreamDiagnosticResult(
            spec_name=spec.name,
            item=item,
            fields=spec.fields,
            state=StreamState.DISCONNECTED,
        ),
        account_id=account_id,
        secrets=secrets,
    )
    adapter = IGStreamingAdapter(
        session=session,
        account_id=account_id,
        event_sink=sink,
    )
    started_at = time.monotonic()
    try:
        adapter.start()
        if spec.kind == "chart":
            adapter.subscribe_chart(epic, scale=spec.scale or "1MINUTE", spec=spec)
        else:
            adapter.subscribe_quote(epic, spec=spec)
        deadline = started_at + max(duration_seconds, 0.0)
        while time.monotonic() < deadline:
            time.sleep(0.05)
    except Exception as exc:
        sink.fail(str(exc))
    finally:
        adapter.stop()
    if sink.result.first_update_received and sink._first_update_monotonic is not None:
        sink.result.first_update_latency_seconds = sink._first_update_monotonic - started_at
    return sink.result


def print_stream_diagnostic_result(
    result: StreamDiagnosticResult,
    *,
    account_id: str,
) -> None:
    print(f"Subscription item: {_sanitize_account_text(result.item, account_id)}")
    print(f"Fields requested: {', '.join(result.fields)}")
    print(f"State: {result.state.value}")
    print(f"Connected: {'yes' if result.connected else 'no'}")
    print(f"Subscribed: {'yes' if result.subscribed else 'no'}")
    print(f"First update received: {'yes' if result.first_update_received else 'no'}")
    if result.first_update_latency_seconds is None:
        print("First update latency: n/a")
    else:
        print(f"First update latency: {result.first_update_latency_seconds:.3f}s")
    print(f"Updates received: {result.update_count}")
    print(f"Sample raw fields: {result.sample_raw_fields}")
    if result.error:
        print(f"Error: {_sanitize_account_text(result.error, account_id)}")


def _diagnostic_specs_from_args(args: argparse.Namespace) -> list[StreamSubscriptionSpec]:
    if args.try_price_template:
        specs = [
            _custom_stream_spec(template, index)
            for index, template in enumerate(args.try_price_template, start=1)
        ]
        specs.append(CHART_CANDLE_SPEC)
        return specs
    return [MARKET_QUOTE_SPEC, PRICE_QUOTE_SPEC, CHART_CANDLE_SPEC]


def _custom_stream_spec(template: str, index: int) -> StreamSubscriptionSpec:
    upper = template.upper()
    if upper.startswith("MARKET:"):
        fields = MARKET_QUOTE_FIELDS
    elif upper.startswith("PRICE:"):
        fields = PRICE_QUOTE_FIELDS
    else:
        fields = GENERIC_QUOTE_FIELDS
    kind = "chart" if upper.startswith("CHART:") else "quote"
    scale = "1MINUTE" if "{scale}" in template and kind == "chart" else None
    return StreamSubscriptionSpec(
        name=f"CUSTOM_{index}",
        item_template=template,
        fields=fields if kind == "quote" else CHART_CANDLE_SPEC.fields,
        kind=kind,
        scale=scale,
    )


def _sanitize_account_text(text: str, account_id: str) -> str:
    return text.replace(account_id, mask_identifier(account_id))


class _DiagnosticStreamSink:
    def __init__(
        self,
        result: StreamDiagnosticResult,
        *,
        account_id: str,
        secrets: list[str],
    ) -> None:
        self.result = result
        self._account_id = account_id
        self._secrets = list(secrets)
        self._first_update_monotonic: float | None = None

    def on_stream_status(self, status: str) -> None:
        normalized = status.upper()
        if normalized.startswith("CONNECTED"):
            self.result.connected = True
            self.result.state = StreamState.CONNECTED
        elif normalized.startswith("SUBSCRIBED"):
            self.result.subscribed = True
            self.result.state = StreamState.SUBSCRIBED_WAITING_FIRST_TICK
        elif normalized.startswith("RECONNECTING"):
            self.result.state = StreamState.RECONNECTING
        elif normalized.startswith("DISCONNECTED"):
            if self.result.update_count == 0 and self.result.error is None:
                self.result.state = StreamState.DISCONNECTED

    def on_quote(self, quote) -> None:
        self._record_update(getattr(quote, "raw", {}))

    def on_chart(self, chart_update) -> None:
        self._record_update(getattr(chart_update, "raw", {}))

    def on_stream_error(self, message: str) -> None:
        self.fail(message)

    def fail(self, message: str) -> None:
        self.result.state = StreamState.FAILED
        self.result.error = _sanitize_stream_text(
            message,
            account_id=self._account_id,
            secrets=self._secrets,
        )

    def _record_update(self, raw_fields: dict[str, object]) -> None:
        if self._first_update_monotonic is None:
            self._first_update_monotonic = time.monotonic()
            self.result.first_update_received = True
        self.result.state = StreamState.LIVE
        self.result.update_count += 1
        if not self.result.sample_raw_fields:
            self.result.sample_raw_fields = _sanitize_stream_mapping(
                raw_fields,
                account_id=self._account_id,
                secrets=self._secrets,
            )


def _sanitize_stream_mapping(
    mapping: dict[str, object],
    *,
    account_id: str,
    secrets: list[str],
) -> dict[str, object]:
    redacted = redact_mapping(mapping)
    sanitized: dict[str, object] = {}
    for key, value in redacted.items():
        if isinstance(value, str):
            sanitized[key] = _sanitize_stream_text(
                value,
                account_id=account_id,
                secrets=secrets,
            )
        else:
            sanitized[key] = value
    return sanitized


def _sanitize_stream_text(
    text: str,
    *,
    account_id: str,
    secrets: list[str],
) -> str:
    safe_text = redact_text(text, secrets)
    return safe_text.replace(account_id, mask_identifier(account_id))


if __name__ == "__main__":
    raise SystemExit(main())
