"""Console entry point for Trading IG Assistant."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from trading_ig_assistant.adapters.credentials import IGCredentials
from trading_ig_assistant.adapters.ig_rest import IGAPIError, IGRestAdapter
from trading_ig_assistant.app.config import AppConfig, IGEnvironment, load_config


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "func"):
        parser.print_help()
        return 0
    return args.func(args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading-ig-assistant",
        description="Trading IG Assistant P00 command line tools.",
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

    return parser


def check_ig_connectivity(args: argparse.Namespace) -> int:
    config = load_config(args.config) if args.config else AppConfig()
    environment = IGEnvironment(args.environment) if args.environment else config.environment
    username = args.username or os.environ.get(args.username_env) or config.ig_username
    password = os.environ.get(args.password_env)
    api_key = os.environ.get(args.api_key_env)

    if not username or not password or not api_key:
        print(
            "Missing IG credentials. Provide username and set password/API key environment "
            "variables. No secrets should be placed in config files.",
            file=sys.stderr,
        )
        return 2

    adapter = IGRestAdapter(environment=environment, read_only=True)
    credentials = IGCredentials(username=username, password=password, api_key=api_key)

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
        print(f"IG connectivity check failed: {exc}", file=sys.stderr)
        return 1
    finally:
        try:
            adapter.logout()
        except IGAPIError:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
