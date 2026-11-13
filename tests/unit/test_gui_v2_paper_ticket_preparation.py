from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from PyQt5 import QtCore, QtWidgets

from trading_ig_assistant.app.projections.catalogue import CatalogueVM, ProductRowVM
from trading_ig_assistant.app.projections.common import Availability, DataProvenance
from trading_ig_assistant.app.projections.paper_ticket import build_paper_ticket_preparation
from trading_ig_assistant.domain.market_navigation import IGProductMarketBinding
from trading_ig_assistant.domain.markets import CanonicalUnderlyingId

NOW = datetime(2026, 11, 9, 18, 0, tzinfo=UTC)


def _application() -> QtWidgets.QApplication:
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _product(*, live: bool = True, received_at: datetime = NOW) -> ProductRowVM:
    return ProductRowVM(
        epic="CS.D.FRANCE40.CFD.IP",
        name="France 40 CFD",
        product_type="cash_or_dfb",
        direction="unknown",
        asset_class="indices",
        status="TRADEABLE",
        currency="EUR",
        bid=Decimal("8120.0"),
        offer=Decimal("8121.0"),
        net_change=Decimal("10"),
        percent_change=Decimal("0.12"),
        provenance=DataProvenance(
            source="ig-lightstreamer" if live else "local-discovery-cache",
            observed_at_utc=received_at,
            received_at_utc=received_at,
            scope="ig-stream:CS.D.FRANCE40.CFD.IP",
            availability=Availability.READY,
            reason_codes=("LIVE_QUOTE",) if live else ("CACHED_INVENTORY",),
        ),
    )


def _binding() -> IGProductMarketBinding:
    return IGProductMarketBinding(
        product_epic="CS.D.FRANCE40.CFD.IP",
        canonical_underlying_id=CanonicalUnderlyingId.FRANCE_40,
        reference_epic="IX.D.CAC.IMF.IP",
        provenance=("human-approved-test-binding",),
    )


def test_paper_ticket_preparation_requires_exact_binding_without_name_inference() -> None:
    snapshot = build_paper_ticket_preparation(
        product=_product(),
        binding=None,
        evaluated_at_utc=NOW,
    )

    assert snapshot.availability is Availability.NOT_APPLICABLE
    assert snapshot.canonical_underlying_id is None
    assert snapshot.reference_epic is None
    assert snapshot.reason_codes == ("EXACT_PRODUCT_BINDING_REQUIRED",)


def test_paper_ticket_preparation_requires_fresh_live_quote() -> None:
    ready = build_paper_ticket_preparation(
        product=_product(),
        binding=_binding(),
        evaluated_at_utc=NOW,
    )
    stale = build_paper_ticket_preparation(
        product=_product(received_at=NOW - timedelta(minutes=1)),
        binding=_binding(),
        evaluated_at_utc=NOW,
    )

    assert ready.availability is Availability.READY
    assert ready.canonical_underlying_id == "FRANCE_40"
    assert ready.reference_epic == "IX.D.CAC.IMF.IP"
    assert stale.availability is Availability.STALE
    assert "LIVE_QUOTE_STALE" in stale.reason_codes


def test_catalogue_double_click_opens_read_only_ticket_draft() -> None:
    from trading_ig_assistant.ui.i18n.language_manager import LanguageManager
    from trading_ig_assistant.ui.pages.scanner_page import ScannerPage
    from trading_ig_assistant.ui.pages.watchlist_page import WatchlistPage

    app = _application()
    language = LanguageManager("fr_FR")
    scanner = ScannerPage(language)
    watchlist = WatchlistPage(language)
    product = _product(received_at=datetime.now(UTC))
    scanner.set_snapshot(
        CatalogueVM(
            generation_id=0,
            query=None,
            rows=(product,),
            availability=Availability.READY,
            generated_at_utc=NOW,
            kind="inventory",
        )
    )
    opened: list[ProductRowVM] = []
    scanner.product_open_requested.connect(opened.append)
    scanner._open_product(scanner.proxy.index(0, 1))
    assert opened == [product]

    watchlist.select_catalogue_product(product, _binding())
    app.processEvents()
    assert watchlist.tabs.currentIndex() == 3
    assert "PRÊT POUR PRÉPARATION" in watchlist.paper_ticket_preparation.status.text()
    assert watchlist.paper_ticket_preparation.table.rowCount() == 12
    preparation = watchlist.paper_ticket_preparation
    assert preparation.prepare_button.isEnabled()
    preparation.prepare_button.click()
    app.processEvents()
    assert not preparation.draft.isHidden()
    assert not preparation.draft.execute_button.isHidden()

    preparation.draft.evaluate_proposal()
    assert preparation.draft.last_submission is not None
    assert preparation.draft.last_submission.ticket.intent.product_id == product.epic
    assert preparation.draft.last_submission.ticket.intent.underlying_id == "FRANCE_40"
    assert "EXACT_PRODUCT_BINDING_VERIFIED" in preparation.draft.summary.toPlainText()
    updated_product = replace(product, bid=Decimal("8122.0"), offer=Decimal("8123.0"))
    preparation.set_snapshot(
        build_paper_ticket_preparation(
            product=updated_product,
            binding=_binding(),
            evaluated_at_utc=datetime.now(UTC),
        )
    )
    assert preparation.draft.execute_button.isEnabled()
    emitted: list[object] = []
    preparation.paper_submission_requested.connect(emitted.append)
    preparation.draft.request_paper_execution()
    assert len(emitted) == 1
    assert emitted[0].ticket.intent.product_id == product.epic
    assert emitted[0].ticket.entry_price == Decimal("8123.0")
    assert not preparation.draft.execute_button.isEnabled()

    language.set_locale("en_US")
    watchlist.retranslate_ui()
    assert "READY FOR PREPARATION" in watchlist.paper_ticket_preparation.status.text()
    assert preparation.back_button.text() == "Back to checks"
    scanner.close()
    watchlist.close()
    language.close()
    app.processEvents()


def test_product_role_remains_exact_epic_for_stream_scope() -> None:
    from trading_ig_assistant.ui.i18n.language_manager import LanguageManager
    from trading_ig_assistant.ui.models.product_table_model import ProductTableModel

    language = LanguageManager("fr_FR")
    model = ProductTableModel(language)
    model.set_rows((_product(),))

    assert model.data(model.index(0, 0), QtCore.Qt.UserRole) == "CS.D.FRANCE40.CFD.IP"
    assert model.row_at(0) == _product()
    language.close()


def test_router_requests_details_only_for_an_exact_configured_binding() -> None:
    from trading_ig_assistant.app.config import AppConfig
    from trading_ig_assistant.ui.i18n.language_manager import LanguageManager
    from trading_ig_assistant.ui.shell.page_router import PageRouter

    app = _application()
    language = LanguageManager("fr_FR")
    router = PageRouter(
        QtWidgets.QStackedWidget(),
        language,
        AppConfig(product_market_bindings=(_binding(),)),
    )
    requested: list[ProductRowVM] = []
    router.catalogue_product_details_requested.connect(requested.append)

    product = _product(received_at=datetime.now(UTC))
    router._open_watchlist_product(product)
    assert requested == [product]

    unbound = ProductRowVM(
        **{**product.__dict__, "epic": "IX.D.FTSE.CFD.IP", "name": "FTSE 100"}
    )
    router._open_watchlist_product(unbound)
    assert requested == [product]
    language.close()
    app.processEvents()


def test_v2_local_paper_opening_requires_explicit_confirmation(monkeypatch, tmp_path) -> None:
    from trading_ig_assistant.app.qt_paper_session_controller import PaperSessionController
    from trading_ig_assistant.app.runtime.trading_runtime import TradingRuntime
    from trading_ig_assistant.app.ui_facade import RuntimeUIFacade
    from trading_ig_assistant.ui.i18n.language_manager import LanguageManager
    from trading_ig_assistant.ui.pages.watchlist_page import WatchlistPage
    from trading_ig_assistant.ui.shell.main_window_v2 import MainWindowV2

    app = _application()
    language = LanguageManager("fr_FR")
    watchlist = WatchlistPage(language)
    product = _product(received_at=datetime.now(UTC))
    watchlist.select_catalogue_product(product, _binding())
    preparation = watchlist.paper_ticket_preparation
    preparation._open_draft()
    preparation.draft.evaluate_proposal()
    submission = preparation.draft.last_submission
    assert submission is not None

    runtime = TradingRuntime(now_provider=lambda: submission.quote.observed_at_utc)
    controller = PaperSessionController(
        runtime=runtime,
        database_path=tmp_path / "paper.sqlite",
        now_provider=lambda: submission.quote.observed_at_utc,
    )
    window = MainWindowV2(
        facade=RuntimeUIFacade(runtime),
        paper_session_controller=controller,
    )
    monkeypatch.setattr(
        QtWidgets.QMessageBox,
        "question",
        lambda *_args, **_kwargs: QtWidgets.QMessageBox.No,
    )
    window._confirm_paper_submission(submission)
    assert controller.session.position_snapshots() == ()

    monkeypatch.setattr(
        QtWidgets.QMessageBox,
        "question",
        lambda *_args, **_kwargs: QtWidgets.QMessageBox.Yes,
    )
    window._confirm_paper_submission(submission)
    assert len(controller.session.position_snapshots()) == 1

    window.close()
    watchlist.close()
    language.close()
    app.processEvents()
