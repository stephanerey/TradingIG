"""Console entry point for Trading IG Assistant."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from trading_ig_assistant.adapters.credentials import IGCredentials
from trading_ig_assistant.adapters.ig_rest import IGAPIError, IGRestAdapter
from trading_ig_assistant.app.config import AppConfig, IGEnvironment, load_config
from trading_ig_assistant.services.product_discovery_service import (
    DEFAULT_WATCHLIST_SEARCH_TERMS,
    ProductDiscoveryResult,
    ProductDiscoveryService,
    write_discovery_report,
)
from trading_ig_assistant.utils.logging_config import configure_logging

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


if __name__ == "__main__":
    raise SystemExit(main())
