"""Main dock widget: pick auth, service, collections and area, search, select
and download.

UI shape (Anslutning / Sökning / Träffar / Hämta groups, auth-config picker,
QgsFileDownloader-based queue) mirrors the sibling plugin's gui/dock.py
(matself/LM-STAC-Downloader, covering stac-bild/stac-hojd) so the two plugins
feel like one family. This one adds a collection picker (STAC-karta/STAC-vektor
expose several collections, unlike the two fixed raster services) and extracts
vector `.zip` assets after download instead of only handling rasters.
"""

from __future__ import annotations

import os
import zipfile
from pathlib import Path

from qgis.core import (
    Qgis,
    QgsApplication,
    QgsCoordinateReferenceSystem,
    QgsProject,
    QgsProviderRegistry,
    QgsRasterLayer,
    QgsRectangle,
    QgsSettings,
    QgsVectorLayer,
)
from qgis.gui import QgsAuthConfigSelect, QgsExtentGroupBox, QgsFileWidget
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDockWidget,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..config import (
    DEFAULT_SERVICE,
    MAX_RESULTS,
    PLUGIN_NAME,
    SEARCH_CRS,
    SERVICES,
    SETTINGS_PREFIX,
    WARN_BYTES,
    search_base_url,
)
from ..core.auth import authcfg_exists
from ..core.downloader import DownloadQueue
from ..core.items import (
    ARCHIVE_EXTENSIONS,
    DIRECT_VECTOR_EXTENSIONS,
    RASTER_EXTENSIONS,
    StacItem,
)
from ..core.task import CollectionsTask, SearchTask
from .auth_dialog import CreateAuthDialog

COL_NAME, COL_COLLECTION, COL_TYPE, COL_DATE, COL_SIZE = range(5)


def _format_bytes(size: int | None) -> str:
    if size is None:
        return "?"
    for unit in ("B", "kB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return ""


class _SortableItem(QTreeWidgetItem):
    """Tree item that sorts the size column by its numeric value, not text."""

    def __lt__(self, other) -> bool:
        column = self.treeWidget().sortColumn()
        a = self.data(column, Qt.ItemDataRole.UserRole)
        b = other.data(column, Qt.ItemDataRole.UserRole)
        if a is not None and b is not None:
            return a < b
        return super().__lt__(other)


class StacDock(QDockWidget):
    def __init__(self, iface, parent=None):
        super().__init__(PLUGIN_NAME, parent)
        self.iface = iface
        self.canvas = iface.mapCanvas()
        self.settings = QgsSettings()
        self.items: list[StacItem] = []
        self._collections_task: CollectionsTask | None = None
        self._search_task: SearchTask | None = None
        self._queue: DownloadQueue | None = None
        self._rows: dict[tuple[str, str], QTreeWidgetItem] = {}

        body = QWidget()
        layout = QVBoxLayout(body)
        layout.addWidget(self._build_connection_group())
        layout.addWidget(self._build_search_group())
        layout.addWidget(self._build_results_group())
        layout.addWidget(self._build_output_group())
        note = QLabel("Fristående plugin, inte utvecklat av Lantmäteriet.")
        note.setWordWrap(True)
        note.setEnabled(False)
        layout.addWidget(note)
        layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(body)
        self.setWidget(scroll)

        self._restore_settings()
        self._reload_collections()

    def cleanup(self) -> None:
        if self._queue:
            self._queue.cancel()
        if self._search_task:
            self._search_task.cancel()
        if self._collections_task:
            self._collections_task.cancel()
        self._save_settings()

    # -- UI construction ---------------------------------------------------

    def _build_connection_group(self) -> QGroupBox:
        group = QGroupBox("Anslutning")
        form = QFormLayout(group)
        # QGIS' own auth config picker: users can also create/edit configs here.
        self.auth_select = QgsAuthConfigSelect(self)
        form.addRow("Autentisering", self.auth_select)
        new_auth_btn = QPushButton("Ny Lantmäteriet-inloggning…")
        new_auth_btn.clicked.connect(self._create_auth)
        form.addRow("", new_auth_btn)
        return group

    def _build_search_group(self) -> QGroupBox:
        group = QGroupBox("Sökning")
        layout = QVBoxLayout(group)

        form = QFormLayout()
        self.service_combo = QComboBox()
        for service in SERVICES.values():
            self.service_combo.addItem(service.label, service.key)
        self.service_combo.currentIndexChanged.connect(self._reload_collections)
        form.addRow("Tjänst", self.service_combo)
        layout.addLayout(form)

        layout.addWidget(QLabel("Samlingar"))
        self.collections_list = QListWidget()
        self.collections_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.collections_list.setMaximumHeight(110)
        self.collections_list.itemChanged.connect(self._clear_results)
        layout.addWidget(self.collections_list)

        self.extent_group = QgsExtentGroupBox()
        self.extent_group.setTitle("Utbredning")
        self.extent_group.setOutputCrs(QgsCoordinateReferenceSystem(SEARCH_CRS))
        canvas_crs = self.canvas.mapSettings().destinationCrs()
        self.extent_group.setOriginalExtent(self.canvas.extent(), canvas_crs)
        self.extent_group.setCurrentExtent(self.canvas.extent(), canvas_crs)
        self.extent_group.setOutputExtentFromCurrent()
        self.extent_group.setMapCanvas(self.canvas)
        layout.addWidget(self.extent_group)

        self.date_group = QGroupBox("Tidsfilter")
        self.date_group.setCheckable(True)
        self.date_group.setChecked(False)
        date_row = QHBoxLayout()
        date_row.addWidget(QLabel("Från"))
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDisplayFormat("yyyy-MM-dd")
        self.date_from.setDate(self.date_from.date().addYears(-5))
        date_row.addWidget(self.date_from)
        date_row.addWidget(QLabel("Till"))
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDisplayFormat("yyyy-MM-dd")
        date_row.addWidget(self.date_to)
        self.date_group.setLayout(date_row)
        layout.addWidget(self.date_group)

        self.search_btn = QPushButton("Sök")
        self.search_btn.clicked.connect(self._start_search)
        layout.addWidget(self.search_btn)
        self.search_status = QLabel("")
        self.search_status.setWordWrap(True)
        layout.addWidget(self.search_status)
        return group

    def _build_results_group(self) -> QGroupBox:
        group = QGroupBox("Träffar")
        layout = QVBoxLayout(group)

        self.tree = QTreeWidget()
        self.tree.setRootIsDecorated(False)
        self.tree.setSortingEnabled(True)
        self.tree.setMinimumHeight(180)
        self.tree.setHeaderLabels(["Namn", "Samling", "Typ", "Datum", "Storlek"])
        self.tree.itemChanged.connect(self._update_summary)
        layout.addWidget(self.tree)

        row = QHBoxLayout()
        all_btn = QPushButton("Markera alla")
        all_btn.clicked.connect(lambda: self._set_all_checked(True))
        none_btn = QPushButton("Avmarkera alla")
        none_btn.clicked.connect(lambda: self._set_all_checked(False))
        row.addWidget(all_btn)
        row.addWidget(none_btn)
        layout.addLayout(row)

        self.summary_label = QLabel("")
        layout.addWidget(self.summary_label)
        return group

    def _build_output_group(self) -> QGroupBox:
        group = QGroupBox("Hämta")
        layout = QVBoxLayout(group)

        self.output_widget = QgsFileWidget()
        self.output_widget.setStorageMode(QgsFileWidget.StorageMode.GetDirectory)
        layout.addWidget(self.output_widget)

        self.add_to_project = QCheckBox("Lägg till i projektet när klart")
        self.add_to_project.setChecked(True)
        layout.addWidget(self.add_to_project)

        self.download_btn = QPushButton("Hämta valda")
        self.download_btn.clicked.connect(self._start_download)
        layout.addWidget(self.download_btn)

        self.cancel_btn = QPushButton("Avbryt")
        self.cancel_btn.clicked.connect(self._cancel)
        self.cancel_btn.setVisible(False)
        layout.addWidget(self.cancel_btn)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)
        self.progress_label = QLabel("")
        self.progress_label.setWordWrap(True)
        layout.addWidget(self.progress_label)
        return group

    # -- settings ------------------------------------------------------

    def _key(self, name: str) -> str:
        return f"{SETTINGS_PREFIX}/{name}"

    def _restore_settings(self) -> None:
        self.auth_select.setConfigId(self.settings.value(self._key("authcfg"), ""))
        service = self.settings.value(self._key("service"), DEFAULT_SERVICE)
        self.service_combo.setCurrentIndex(max(0, self.service_combo.findData(service)))
        self.output_widget.setFilePath(self.settings.value(self._key("output"), str(Path.home())))

    def _save_settings(self) -> None:
        self.settings.setValue(self._key("authcfg"), self.auth_select.configId())
        self.settings.setValue(self._key("service"), self.service_combo.currentData())
        self.settings.setValue(self._key("output"), self.output_widget.filePath())

    # -- helpers ---------------------------------------------------------

    def _message(self, text: str, level=Qgis.MessageLevel.Info) -> None:
        self.iface.messageBar().pushMessage(PLUGIN_NAME, text, level, 8)

    def _authcfg(self) -> str:
        """authcfg id, possibly empty (search works without one; download won't)."""
        return self.auth_select.configId()

    def _authcfg_or_warn(self) -> str | None:
        authcfg = self.auth_select.configId()
        if not authcfg_exists(authcfg):
            self._message(
                "Välj eller skapa en autentisering först.", Qgis.MessageLevel.Warning
            )
            return None
        return authcfg

    def _create_auth(self) -> None:
        dlg = CreateAuthDialog(self)
        if dlg.exec() and dlg.authcfg:
            self.auth_select.setConfigId(dlg.authcfg)
            self._save_settings()

    # -- collections ---------------------------------------------------

    def _reload_collections(self, *_args) -> None:
        service_key = self.service_combo.currentData()
        if not service_key:
            return
        if self._collections_task is not None:
            self._collections_task.cancel()
        if self._search_task is not None:
            self._search_task.cancel()
        self.collections_list.clear()
        self._clear_results()
        task = CollectionsTask(search_base_url(service_key), self._authcfg())
        task.completed.connect(self._on_collections_completed)
        task.failed.connect(self._on_collections_failed)
        task.taskTerminated.connect(self._clear_collections_task)
        task.taskCompleted.connect(self._clear_collections_task)
        self._collections_task = task
        QgsApplication.taskManager().addTask(task)

    def _clear_collections_task(self) -> None:
        self._collections_task = None

    def _on_collections_failed(self, error: str) -> None:
        self._message(f"Kunde inte hämta samlingar: {error}", Qgis.MessageLevel.Warning)

    def _on_collections_completed(self, collections: list) -> None:
        self.collections_list.blockSignals(True)
        self.collections_list.clear()
        for collection in collections:
            label = f"{collection.get('title') or collection['id']} ({collection['id']})"
            item = QListWidgetItem(label)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            item.setData(Qt.ItemDataRole.UserRole, collection["id"])
            self.collections_list.addItem(item)
        self.collections_list.blockSignals(False)

    def _selected_collection_ids(self) -> list[str]:
        ids = []
        for i in range(self.collections_list.count()):
            item = self.collections_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                ids.append(item.data(Qt.ItemDataRole.UserRole))
        return ids

    # -- search ----------------------------------------------------------

    def _search_body(self) -> dict | None:
        collection_ids = self._selected_collection_ids()
        if not collection_ids:
            self._message("Välj minst en samling.", Qgis.MessageLevel.Warning)
            return None

        extent: QgsRectangle = self.extent_group.outputExtent()
        if extent.isEmpty():
            self._message("Ange en giltig utbredning.", Qgis.MessageLevel.Warning)
            return None

        body: dict = {
            "collections": collection_ids,
            "bbox": [
                extent.xMinimum(),
                extent.yMinimum(),
                extent.xMaximum(),
                extent.yMaximum(),
            ],
        }
        if self.date_group.isChecked():
            date_from = self.date_from.date().toString("yyyy-MM-dd")
            date_to = self.date_to.date().toString("yyyy-MM-dd")
            body["datetime"] = f"{date_from}T00:00:00Z/{date_to}T23:59:59Z"
        return body

    def _start_search(self) -> None:
        if self._search_task:
            return
        body = self._search_body()
        if body is None:
            return
        self._save_settings()

        task = SearchTask(search_base_url(self.service_combo.currentData()), self._authcfg(), body)
        task.status.connect(self.search_status.setText)
        task.completed.connect(self._on_search_completed)
        task.failed.connect(self._on_search_failed)
        task.taskTerminated.connect(self._clear_search)
        task.taskCompleted.connect(self._clear_search)
        self._search_task = task
        self.search_btn.setEnabled(False)
        QgsApplication.taskManager().addTask(task)

    def _clear_search(self) -> None:
        self._search_task = None
        self.search_btn.setEnabled(True)

    def _on_search_failed(self, error: str) -> None:
        self.search_status.setText("")
        self._message(error, Qgis.MessageLevel.Critical)

    def _on_search_completed(self, items: list, truncated: bool) -> None:
        self.items = items
        text = f"{len(items)} träffar."
        if truncated:
            text += f" Sökningen begränsades till {MAX_RESULTS}; snäva in området eller tidsfiltret."
        self.search_status.setText(text)
        self._fill_results()

    # -- results ---------------------------------------------------------

    def _clear_results(self) -> None:
        """Drop stale hits, e.g. when the service or its collections change
        under the results (a hit's `collection` id is only meaningful for
        the service it was searched from)."""
        self.items = []
        self._rows = {}
        self.tree.clear()
        self.search_status.setText("")
        self._update_summary()

    def _fill_results(self) -> None:
        self.tree.blockSignals(True)
        self.tree.setSortingEnabled(False)
        self.tree.clear()
        self._rows = {}
        for item in self.items:
            row = _SortableItem(
                [item.id, item.collection, item.kind, item.date or "", _format_bytes(item.size)]
            )
            row.setFlags(row.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            row.setCheckState(COL_NAME, Qt.CheckState.Unchecked)
            row.setData(COL_NAME, Qt.ItemDataRole.UserRole + 1, item)
            row.setData(COL_SIZE, Qt.ItemDataRole.UserRole, item.size or 0)
            self.tree.addTopLevelItem(row)
            self._rows[(item.collection, item.id)] = row
        self.tree.setSortingEnabled(True)
        self.tree.blockSignals(False)
        for column in range(self.tree.columnCount()):
            self.tree.resizeColumnToContents(column)
        self._update_summary()

    def _checked_items(self) -> list[StacItem]:
        checked = []
        for i in range(self.tree.topLevelItemCount()):
            row = self.tree.topLevelItem(i)
            if row.checkState(COL_NAME) == Qt.CheckState.Checked:
                checked.append(row.data(COL_NAME, Qt.ItemDataRole.UserRole + 1))
        return checked

    def _set_all_checked(self, checked: bool) -> None:
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        self.tree.blockSignals(True)
        for i in range(self.tree.topLevelItemCount()):
            self.tree.topLevelItem(i).setCheckState(COL_NAME, state)
        self.tree.blockSignals(False)
        self._update_summary()

    def _update_summary(self, *_args) -> None:
        checked = self._checked_items()
        known = sum(i.size for i in checked if i.size)
        unknown = sum(1 for i in checked if not i.size)
        text = f"{len(checked)} av {len(self.items)} valda, {_format_bytes(known)}"
        if unknown:
            text += f" (+{unknown} med okänd storlek)"
        self.summary_label.setText(text)

    # -- download --------------------------------------------------------

    def _start_download(self) -> None:
        if self._queue:
            return
        authcfg = self._authcfg_or_warn()
        if not authcfg:
            return
        items = self._checked_items()
        if not items:
            self._message("Markera minst en rad att hämta.", Qgis.MessageLevel.Warning)
            return
        output = self.output_widget.filePath()
        if not output:
            self._message("Välj en målmapp.", Qgis.MessageLevel.Warning)
            return

        total = sum(i.size for i in items if i.size)
        if total > WARN_BYTES:
            from qgis.PyQt.QtWidgets import QMessageBox

            answer = QMessageBox.question(
                self,
                PLUGIN_NAME,
                f"Du är på väg att hämta {len(items)} filer, ungefär {_format_bytes(total)}. Fortsätta?",
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        self._save_settings()

        queue = DownloadQueue(items, authcfg, Path(output), self)
        queue.progress.connect(self._on_download_progress)
        queue.finished.connect(self._on_download_finished)
        self._queue = queue
        self._begin_download_ui()
        queue.start()

    def _begin_download_ui(self) -> None:
        self.download_btn.setVisible(False)
        self.cancel_btn.setVisible(True)
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)

    def _cancel(self) -> None:
        self.progress_label.setText("Avbryter…")
        if self._queue:
            self._queue.cancel()

    def _on_download_progress(self, index: int, count: int, name: str, received: int, total: int) -> None:
        if total > 0:
            self.progress.setRange(0, 1000)
            self.progress.setValue(int(1000 * received / total))
        else:
            self.progress.setRange(0, 0)
        self.progress_label.setText(
            f"Fil {index} av {count}: {name} ({_format_bytes(received)} av {_format_bytes(total or None)})"
        )

    def _on_download_finished(self, paths: list, failures: list, cancelled: bool) -> None:
        queue, self._queue = self._queue, None
        if queue:
            queue.deleteLater()
        self.download_btn.setVisible(True)
        self.cancel_btn.setVisible(False)
        self.progress.setVisible(False)
        self.progress_label.setText("")

        if self.add_to_project.isChecked():
            failures = list(failures)
            for path in paths:
                self._add_to_project(path, failures)

        if failures:
            self._message(
                f"{len(paths)} filer hämtade, {len(failures)} misslyckades: " + "; ".join(failures[:3]),
                Qgis.MessageLevel.Warning,
            )
        elif cancelled:
            self._message(f"Avbrutet. {len(paths)} filer hann hämtas.", Qgis.MessageLevel.Warning)
        else:
            self._message(f"{len(paths)} filer hämtade.", Qgis.MessageLevel.Success)

    def _add_to_project(self, path: str, failures: list) -> None:
        project = QgsProject.instance()
        ext = Path(path).suffix.lower()
        if ext in ARCHIVE_EXTENSIONS:
            self._add_zip_contents(path, project, failures)
        elif ext in RASTER_EXTENSIONS:
            self._add_raster(path, project, failures)
        elif ext in DIRECT_VECTOR_EXTENSIONS:
            self._add_vector(path, project, failures)

    def _add_zip_contents(self, zip_path: str, project: QgsProject, failures: list) -> None:
        extract_dir = os.path.splitext(zip_path)[0]
        try:
            with zipfile.ZipFile(zip_path) as archive:
                archive.extractall(extract_dir)
                names = archive.namelist()
        except (zipfile.BadZipFile, OSError) as exc:
            failures.append(f"{Path(zip_path).name}: kunde inte packas upp ({exc})")
            return

        for name in names:
            ext = os.path.splitext(name)[1].lower()
            full_path = os.path.join(extract_dir, name)
            if ext in RASTER_EXTENSIONS:
                self._add_raster(full_path, project, failures)
            elif ext in DIRECT_VECTOR_EXTENSIONS:
                self._add_vector(full_path, project, failures)

    @staticmethod
    def _add_raster(path: str, project: QgsProject, failures: list) -> None:
        layer = QgsRasterLayer(path, Path(path).stem)
        if layer.isValid():
            project.addMapLayer(layer)
        else:
            failures.append(f"{Path(path).name}: kunde inte öppnas som raster")

    @staticmethod
    def _add_vector(path: str, project: QgsProject, failures: list) -> None:
        # A vector container such as GeoPackage can hold several layers (e.g.
        # separate point/line/polygon tables in fastighetsindelning) - add
        # every one instead of just whichever QgsVectorLayer would default to.
        try:
            sublayers = QgsProviderRegistry.instance().querySublayers(path)
        except Exception:  # pragma: no cover - defensive, provider quirks vary
            sublayers = []
        vector_sublayers = [s for s in sublayers if s.type() == Qgis.LayerType.Vector]

        if not vector_sublayers:
            layer = QgsVectorLayer(path, Path(path).stem, "ogr")
            if layer.isValid():
                project.addMapLayer(layer)
            else:
                failures.append(f"{Path(path).name}: kunde inte öppnas som vektorlager")
            return

        stem = Path(path).stem
        multiple = len(vector_sublayers) > 1
        for sublayer in vector_sublayers:
            name = f"{stem} - {sublayer.name()}" if multiple else stem
            layer = QgsVectorLayer(sublayer.uri(), name, sublayer.providerKey())
            if layer.isValid():
                project.addMapLayer(layer)
            else:
                failures.append(
                    f"{Path(path).name} ({sublayer.name()}): kunde inte öppnas som vektorlager"
                )
