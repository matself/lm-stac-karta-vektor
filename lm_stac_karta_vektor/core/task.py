"""Background tasks: list collections and search a STAC service."""

from __future__ import annotations

from typing import Any

from qgis.core import Qgis, QgsFeedback, QgsMessageLog, QgsTask
from qgis.PyQt.QtCore import pyqtSignal

from ..config import MAX_RESULTS, PAGE_LIMIT, PLUGIN_NAME, RESTRICTED_COLLECTIONS
from .client import StacClient, StacError
from .items import StacItem, parse_item


def _log(message: str, level=Qgis.MessageLevel.Info) -> None:
    QgsMessageLog.logMessage(message, PLUGIN_NAME, level)


class CollectionsTask(QgsTask):
    completed = pyqtSignal(list)  # list[dict]: id, title
    failed = pyqtSignal(str)

    def __init__(self, base_url: str, authcfg: str):
        super().__init__("Geodata: hämtar samlingar", QgsTask.Flag.CanCancel)
        self.base_url = base_url
        self.authcfg = authcfg
        self.collections: list[dict] = []
        self.error: str | None = None
        self._feedback = QgsFeedback()

    def cancel(self) -> None:
        self._feedback.cancel()
        super().cancel()

    def run(self) -> bool:
        client = StacClient(self.base_url, self.authcfg, self._feedback)
        try:
            collections = client.collections()
        except StacError as e:
            self.error = e.describe()
            return False
        self.collections = [
            c for c in collections if c.get("id") not in RESTRICTED_COLLECTIONS
        ]
        return True

    def finished(self, result: bool) -> None:
        if result:
            self.completed.emit(self.collections)
        elif not self.isCanceled():
            _log(self.error or "Okänt fel", Qgis.MessageLevel.Critical)
            self.failed.emit(self.error or "Okänt fel")


class SearchTask(QgsTask):
    # Emitted in the main thread via QgsTask.finished → safe for UI work.
    completed = pyqtSignal(list, bool)  # items, truncated at MAX_RESULTS
    failed = pyqtSignal(str)
    status = pyqtSignal(str)

    def __init__(self, base_url: str, authcfg: str, search_body: dict[str, Any]):
        super().__init__("Geodata: söker", QgsTask.Flag.CanCancel)
        self.base_url = base_url
        self.authcfg = authcfg
        self.search_body = {**search_body, "limit": PAGE_LIMIT}
        self.items: list[StacItem] = []
        self.truncated = False
        self.error: str | None = None
        self._feedback = QgsFeedback()

    def cancel(self) -> None:
        self._feedback.cancel()
        super().cancel()

    def run(self) -> bool:
        client = StacClient(self.base_url, self.authcfg, self._feedback)
        _log(f"POST {self.base_url}/search {self.search_body}")
        self.status.emit("söker…")
        try:
            for page_no, page in enumerate(client.search(self.search_body), start=1):
                if self.isCanceled():
                    return False
                for feature in page.get("features", []):
                    item = parse_item(feature)
                    if item and item.collection not in RESTRICTED_COLLECTIONS:
                        self.items.append(item)
                self.status.emit(f"{len(self.items)} träffar (anrop {page_no})")
                if len(self.items) >= MAX_RESULTS:
                    self.items = self.items[:MAX_RESULTS]
                    self.truncated = True
                    break
        except StacError as e:
            self.error = e.describe()
            return False
        return True

    def finished(self, result: bool) -> None:
        if result:
            self.completed.emit(self.items, self.truncated)
        elif not self.isCanceled():
            _log(self.error or "Okänt fel", Qgis.MessageLevel.Critical)
            self.failed.emit(self.error or "Okänt fel")
