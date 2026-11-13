"""Install a lightweight QTranslator backed by stable in-process catalogs."""

from __future__ import annotations

import logging

from PyQt5 import QtCore

from trading_ig_assistant.ui.i18n.catalogs import CATALOGS, SUPPORTED_LOCALES

LOGGER = logging.getLogger(__name__)


class _CatalogTranslator(QtCore.QTranslator):
    def __init__(self, locale: str) -> None:
        super().__init__()
        self._catalog = CATALOGS[locale]

    def translate(
        self,
        context: str,
        source_text: str,
        disambiguation: str | None = None,
        n: int = -1,
    ) -> str:
        del context, disambiguation, n
        return self._catalog.get(source_text, "")


class LanguageManager(QtCore.QObject):
    language_changed = QtCore.pyqtSignal(str)

    def __init__(self, locale: str = "fr_FR") -> None:
        super().__init__()
        self._locale = ""
        self._translator: _CatalogTranslator | None = None
        self.set_locale(locale, emit=False)

    @property
    def locale(self) -> str:
        return self._locale

    @property
    def available_locales(self) -> tuple[str, ...]:
        return SUPPORTED_LOCALES

    def text(self, message_id: str) -> str:
        translated = CATALOGS[self._locale].get(message_id)
        if translated is not None:
            return translated
        fallback = CATALOGS["en_US"].get(message_id)
        if fallback is not None:
            LOGGER.warning("Missing translation locale=%s message_id=%s", self._locale, message_id)
            return fallback
        LOGGER.warning("Unknown translation message_id=%s", message_id)
        return message_id.replace(".", " ").replace("_", " ").strip().title()

    def set_locale(self, locale: str, *, emit: bool = True) -> None:
        if locale not in CATALOGS:
            raise ValueError(f"unsupported locale: {locale}")
        if locale == self._locale:
            return
        application = QtCore.QCoreApplication.instance()
        if application is not None and self._translator is not None:
            application.removeTranslator(self._translator)
        translator = _CatalogTranslator(locale)
        if application is not None:
            application.installTranslator(translator)
        self._translator = translator
        self._locale = locale
        QtCore.QLocale.setDefault(QtCore.QLocale(locale))
        if emit:
            self.language_changed.emit(locale)

    def close(self) -> None:
        application = QtCore.QCoreApplication.instance()
        if application is not None and self._translator is not None:
            application.removeTranslator(self._translator)
        self._translator = None
