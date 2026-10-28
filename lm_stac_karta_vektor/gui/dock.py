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
    QgsGeometry,
    QgsLayerTreeGroup,
    QgsProject,
    QgsProviderRegistry,
    QgsRasterLayer,
    QgsRectangle,
    QgsSettings,
    QgsVectorLayer,
)
from qgis.gui import (
    QgsAuthConfigSelect,
    QgsExtentGroupBox,
    QgsExtentWidget,
    QgsFileWidget,
    QgsRubberBand,
)
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QColor
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
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..config import (
    CLIP_FACTORS,
    DEFAULT_SERVICE,
    MAX_CLIP_PIXELS,
    MAX_RESULTS,
    PLUGIN_NAME,
    RASTER_COLLECTIONS,
    SEARCH_CRS,
    SERVICES,
    SETTINGS_PREFIX,
    WARN_BYTES,
    search_base_url,
)
from ..core.auth import authcfg_exists
from ..core.clip import (
    DEFAULT_FORMAT,
    OUTPUT_FORMATS,
    ClipJob,
    ClipTask,
    clip_extent,
    extent_in_crs,
    item_crs,
    grid_size,
    native_resolution,
    output_path,
    uncompressed_bytes,
)
from ..core.downloader import DownloadQueue
from ..core.fonts import FONT_FAMILY
from ..core.items import (
    ARCHIVE_EXTENSIONS,
    DIRECT_VECTOR_EXTENSIONS,
    RASTER_EXTENSIONS,
    StacItem,
)
from ..core.split import SPLITTABLE, split_by_lan
from ..core.styles import apply_style, sort_by_draw_order
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
        self._clip_task: ClipTask | None = None
        self._clip_jobs: list[ClipJob] = []
        self._clip_total = 0
        self._clip_paths: list[tuple[str, str]] = []
        self._clip_failures: list[str] = []
        self._clip_cancelled = False
        self._clip_authcfg = ""
        self._rows: dict[tuple[str, str], QTreeWidgetItem] = {}

        body = QWidget()
        layout = QVBoxLayout(body)
        layout.addWidget(self._build_connection_group())
        layout.addWidget(self._build_search_group())
        layout.addWidget(self._build_results_group())
        layout.addWidget(self._build_clip_group())
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

        # Outlines the area a topowebb clip will cover; the extent widget
        # itself draws nothing while it follows the map view.
        self._extent_band = QgsRubberBand(self.canvas, Qgis.GeometryType.Polygon)
        self._extent_band.setColor(QColor(220, 30, 30))
        self._extent_band.setFillColor(QColor(0, 0, 0, 0))  # outline only
        self._extent_band.setWidth(2)
        self.visibilityChanged.connect(self._update_clip_info)
        # Set by "Rensa ruta"; the outline stays hidden until a new extent is
        # drawn or chosen, or a new search is made.
        self._band_cleared = False

        self._restore_settings()
        self._reload_collections()

    def cleanup(self) -> None:
        if self._queue:
            self._queue.cancel()
        self._clip_jobs = []
        if self._clip_task:
            self._clip_task.cancel()
        self._extent_band.reset(Qgis.GeometryType.Polygon)
        self.canvas.scene().removeItem(self._extent_band)
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
        self.extent_group.extentChanged.connect(self._on_extent_changed)
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

        # The topowebb clip area is outlined on the canvas (see
        # _update_extent_band); this hides the outline, e.g. when it covers a
        # freshly added clip. Only shown for STAC-karta.
        self.clear_band_btn = QPushButton("Rensa ruta")
        self.clear_band_btn.setToolTip(
            "Döljer rutan på kartan tills du ritar eller väljer en ny utbredning."
        )
        self.clear_band_btn.clicked.connect(self._clear_band)
        layout.addWidget(self.clear_band_btn)

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
        self.tree.itemChanged.connect(self._update_clip_info)
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

    def _build_clip_group(self) -> QGroupBox:
        """Options for the topowebb raster map: its items are 140-175 GB
        whole-country files, so by default only the Utbredning is cut out of
        the remote file (see core/clip.py). Shown only when results include
        such items."""
        self.clip_group = QGroupBox("Rasterkarta (topowebb)")
        form = QFormLayout(self.clip_group)

        self.clip_mode = QComboBox()
        self.clip_mode.addItem("Klipp ut området i Utbredning", "clip")
        self.clip_mode.addItem("Hämta hela filen (140-175 GB)", "full")
        self.clip_mode.currentIndexChanged.connect(self._update_clip_info)
        form.addRow("Läge", self.clip_mode)

        self.clip_res = QComboBox()
        for factor in CLIP_FACTORS:
            self.clip_res.addItem(f"{factor}×", factor)
        self.clip_res.currentIndexChanged.connect(self._update_clip_info)
        form.addRow("Upplösning", self.clip_res)

        self.clip_format = QComboBox()
        for key, (label, _driver, ext, _opts) in OUTPUT_FORMATS.items():
            self.clip_format.addItem(f"{label} ({ext})", key)
        form.addRow("Format", self.clip_format)

        self.clip_info = QLabel("")
        self.clip_info.setWordWrap(True)
        form.addRow(self.clip_info)

        self.clip_group.setVisible(False)
        return self.clip_group

    def _build_output_group(self) -> QGroupBox:
        group = QGroupBox("Hämta")
        layout = QVBoxLayout(group)

        self.output_widget = QgsFileWidget()
        self.output_widget.setStorageMode(QgsFileWidget.StorageMode.GetDirectory)
        layout.addWidget(self.output_widget)

        self.add_to_project = QCheckBox("Lägg till i projektet när klart")
        self.add_to_project.setChecked(True)
        layout.addWidget(self.add_to_project)

        # ortnamn is the one collection Lantmäteriet delivers as a single
        # nationwide file (~989 000 objekt) instead of one file per kommun -
        # see core/split.SPLITTABLE and docs/stilfiler.md.
        self.split_ortnamn = QCheckBox("Dela upp ortnamn per län (en fil per län)")
        self.split_ortnamn.setChecked(False)
        layout.addWidget(self.split_ortnamn)

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
        self.split_ortnamn.setChecked(self.settings.value(self._key("split_ortnamn"), False, type=bool))
        for combo, name, default in (
            (self.clip_mode, "clip_mode", "clip"),
            (self.clip_res, "clip_factor", 1),
            (self.clip_format, "clip_format", DEFAULT_FORMAT),
        ):
            value = self.settings.value(self._key(name), default)
            if name == "clip_factor":
                value = int(value)
            combo.setCurrentIndex(max(0, combo.findData(value)))

    def _save_settings(self) -> None:
        self.settings.setValue(self._key("authcfg"), self.auth_select.configId())
        self.settings.setValue(self._key("service"), self.service_combo.currentData())
        self.settings.setValue(self._key("output"), self.output_widget.filePath())
        self.settings.setValue(self._key("split_ortnamn"), self.split_ortnamn.isChecked())
        self.settings.setValue(self._key("clip_mode"), self.clip_mode.currentData())
        self.settings.setValue(self._key("clip_factor"), self.clip_res.currentData())
        self.settings.setValue(self._key("clip_format"), self.clip_format.currentData())

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
        self._update_clip_info()

    def _fill_results(self) -> None:
        self.tree.blockSignals(True)
        self.tree.setSortingEnabled(False)
        self.tree.clear()
        self._rows = {}
        for item in self.items:
            row = _SortableItem(
                [item.label, item.collection, item.kind, item.date or "", _format_bytes(item.size)]
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
        self._band_cleared = False
        self._update_summary()
        self._update_clip_info()

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
        self._update_clip_info()

    def _update_summary(self, *_args) -> None:
        checked = self._checked_items()
        if self._clipping(checked):
            self.summary_label.setText(f"{len(checked)} av {len(self.items)} valda (utklipp)")
            return
        known = sum(i.size for i in checked if i.size)
        unknown = sum(1 for i in checked if not i.size)
        text = f"{len(checked)} av {len(self.items)} valda, {_format_bytes(known)}"
        if unknown:
            text += f" (+{unknown} med okänd storlek)"
        self.summary_label.setText(text)

    # -- topowebb clip ---------------------------------------------------

    def _clipping(self, checked: list[StacItem] | None = None) -> bool:
        """True when the checked rows are raster maps to be cut out rather
        than downloaded whole."""
        checked = self._checked_items() if checked is None else checked
        return (
            self.clip_mode.currentData() == "clip"
            and bool(checked)
            and all(i.is_raster_map for i in checked)
        )

    @staticmethod
    def _format_resolution(resolution: float, epsg: int | None) -> str:
        text = f"{resolution:.2f}".rstrip("0").rstrip(".").replace(".", ",")
        return f"{text} m" if epsg == 3006 else f"{text} kartenheter"

    def _on_extent_changed(self, *_args) -> None:
        # While the extent just follows the map view, panning must not bring
        # a cleared outline back; a drawn or chosen extent does.
        if self.extent_group.extentState() != QgsExtentWidget.ExtentState.CurrentExtent:
            self._band_cleared = False
        self._update_clip_info()

    def _clear_band(self) -> None:
        self._band_cleared = True
        self._update_clip_info()

    def _update_extent_band(self) -> None:
        """Outline the area a topowebb clip would cover, in the file's CRS.
        Shown for STAC-karta while in clip mode, even before a search (the
        CRS then defaults to SWEREF 99 TM), unless cleared."""
        self._extent_band.reset(Qgis.GeometryType.Polygon)
        is_karta = self.service_combo.currentData() == "stac-karta"
        self.clear_band_btn.setVisible(is_karta)
        if not (
            is_karta
            and self.clip_mode.currentData() == "clip"
            and self.isVisible()
            and not self._band_cleared
        ):
            return
        extent = self.extent_group.outputExtent()
        if extent.isEmpty():
            return
        raster_items = [i for i in self._checked_items() if i.is_raster_map] or [
            i for i in self.items if i.is_raster_map
        ]
        crs = item_crs(raster_items[0]) if raster_items else QgsCoordinateReferenceSystem("EPSG:3006")
        self._extent_band.setToGeometry(QgsGeometry.fromRect(extent_in_crs(extent, crs)), crs)

    def _update_clip_info(self, *_args) -> None:
        """Show/hide the topowebb group and refresh the resolution labels and
        the size estimate for the current extent and selection."""
        self._update_extent_band()
        raster_items = [i for i in self.items if i.is_raster_map]
        self.clip_group.setVisible(bool(raster_items))
        if not raster_items:
            return
        clipping = self.clip_mode.currentData() == "clip"
        self.clip_res.setEnabled(clipping)
        self.clip_format.setEnabled(clipping)
        if not clipping:
            self.clip_info.setText("Hela filen laddas ned. Välj Klipp ut för att bara hämta området.")
            return

        checked = [i for i in self._checked_items() if i.is_raster_map]
        reference = checked[0] if checked else raster_items[0]
        native = native_resolution(reference)
        if native:
            self.clip_res.blockSignals(True)
            for index in range(self.clip_res.count()):
                factor = self.clip_res.itemData(index)
                label = self._format_resolution(native * factor, reference.epsg)
                self.clip_res.setItemText(index, f"{label} (full)" if factor == 1 else label)
            self.clip_res.blockSignals(False)

        extent = self.extent_group.outputExtent()
        if not checked:
            self.clip_info.setText("Markera en eller flera rader att klippa ut.")
            return
        if extent.isEmpty():
            self.clip_info.setText("Ange en giltig utbredning.")
            return
        factor = self.clip_res.currentData()
        lines = []
        for item in checked:
            item_native = native_resolution(item)
            if not item_native:
                continue
            cols, rows = grid_size(clip_extent(extent, item), item_native * factor)
            lines.append(
                f"{item.id}: {cols} × {rows} px, högst {_format_bytes(uncompressed_bytes(cols, rows))}"
            )
        self.clip_info.setText("\n".join(lines))

    def _start_clip(self, items: list[StacItem], authcfg: str, output: str) -> None:
        extent = self.extent_group.outputExtent()
        if extent.isEmpty():
            self._message("Ange en giltig utbredning.", Qgis.MessageLevel.Warning)
            return
        factor = self.clip_res.currentData()
        fmt = self.clip_format.currentData()

        jobs: list[ClipJob] = []
        total_bytes = 0
        for item in items:
            native = native_resolution(item)
            if not native:
                self._message(f"{item.id}: okänd upplösning, kan inte klippas.", Qgis.MessageLevel.Warning)
                return
            item_extent = clip_extent(extent, item)
            resolution = native * factor
            cols, rows = grid_size(item_extent, resolution)
            if cols * rows > MAX_CLIP_PIXELS:
                self._message(
                    f"{item.id}: {cols} × {rows} px är för stort. Minska utbredningen "
                    "eller välj en lägre upplösning.",
                    Qgis.MessageLevel.Warning,
                )
                return
            total_bytes += uncompressed_bytes(cols, rows)
            path = output_path(Path(output), item, item_extent, resolution, fmt)
            jobs.append(ClipJob(item, item_extent, resolution, fmt, path))

        if total_bytes > WARN_BYTES:
            answer = QMessageBox.question(
                self,
                PLUGIN_NAME,
                f"Utklippet blir som mest {_format_bytes(total_bytes)} okomprimerat och kan ta lång tid. Fortsätta?",
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        self._save_settings()

        self._clip_jobs = jobs
        self._clip_total = len(jobs)
        self._clip_paths = []
        self._clip_failures = []
        self._clip_cancelled = False
        self._clip_authcfg = authcfg
        self._begin_download_ui()
        self._run_next_clip()

    def _run_next_clip(self) -> None:
        if self._clip_cancelled or not self._clip_jobs:
            self._finish_clips()
            return
        job = self._clip_jobs.pop(0)
        index = self._clip_total - len(self._clip_jobs)
        task = ClipTask(job, self._clip_authcfg)
        task.progressChanged.connect(lambda pct, i=index, j=job: self._on_clip_progress(i, j, pct))
        task.ended.connect(lambda path, error, j=job: self._on_clip_ended(j, path, error))
        self._clip_task = task
        self.progress.setRange(0, 1000)
        self.progress.setValue(0)
        self.progress_label.setText(f"Klipper ut {index} av {self._clip_total}: {job.item.id}…")
        QgsApplication.taskManager().addTask(task)

    def _on_clip_progress(self, index: int, job: ClipJob, percent: float) -> None:
        self.progress.setRange(0, 1000)
        self.progress.setValue(int(percent * 10))
        self.progress_label.setText(
            f"Klipper ut {index} av {self._clip_total}: {job.item.id} ({percent:.0f} %)"
        )

    def _on_clip_ended(self, job: ClipJob, path: str, error: str) -> None:
        self._clip_task = None
        if path:
            self._clip_paths.append((job.item.collection, path))
        elif error:
            self._clip_failures.append(f"{job.item.id}: {error}")
        self._run_next_clip()

    def _finish_clips(self) -> None:
        paths, failures = self._clip_paths, list(self._clip_failures)
        cancelled = self._clip_cancelled
        self._clip_jobs = []
        self._finish_download_ui()

        if self.add_to_project.isChecked():
            for _collection, path in paths:
                self._add_raster(path, QgsProject.instance(), failures)
        self._report_result(len(paths), failures, cancelled, "utklipp klara")

    # -- download --------------------------------------------------------

    def _start_download(self) -> None:
        if self._queue or self._clip_task:
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

        if self._clipping(items):
            self._start_clip(items, authcfg, output)
            return

        total = sum(i.size for i in items if i.size)
        if total > WARN_BYTES:
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
        if self._clip_task:
            self._clip_cancelled = True
            self._clip_jobs = []
            self._clip_task.cancel()

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
        self._finish_download_ui()

        if self.add_to_project.isChecked():
            failures = list(failures)
            font_missing: list[bool] = []
            for collection, path in paths:
                self._add_to_project(collection, path, failures, font_missing)
            if font_missing:
                self._message(
                    f"Fonten {FONT_FAMILY} kunde inte registreras - punktsymboler i "
                    "stilsatta lager kan se fel ut.",
                    Qgis.MessageLevel.Warning,
                )

        self._report_result(len(paths), failures, cancelled, "filer hämtade")

    def _finish_download_ui(self) -> None:
        self.download_btn.setVisible(True)
        self.cancel_btn.setVisible(False)
        self.progress.setVisible(False)
        self.progress_label.setText("")

    def _report_result(self, count: int, failures: list, cancelled: bool, noun: str) -> None:
        if failures:
            self._message(
                f"{count} {noun}, {len(failures)} misslyckades: " + "; ".join(failures[:3]),
                Qgis.MessageLevel.Warning,
            )
        elif cancelled:
            self._message(f"Avbrutet. {count} {noun}.", Qgis.MessageLevel.Warning)
        else:
            self._message(f"{count} {noun}.", Qgis.MessageLevel.Success)

    def _add_to_project(
        self, collection: str, path: str, failures: list, font_missing: list
    ) -> None:
        project = QgsProject.instance()
        ext = Path(path).suffix.lower()
        if collection in RASTER_COLLECTIONS:
            self._add_raster(path, project, failures)
        elif ext in ARCHIVE_EXTENSIONS:
            self._add_zip_contents(collection, path, project, failures, font_missing)
        elif ext in RASTER_EXTENSIONS:
            self._add_raster(path, project, failures)
        elif ext in DIRECT_VECTOR_EXTENSIONS:
            self._add_vector_or_split(collection, path, project, failures, font_missing)

    def _add_vector_or_split(
        self,
        collection: str,
        path: str,
        project: QgsProject,
        failures: list,
        font_missing: list,
        group: QgsLayerTreeGroup | None = None,
    ) -> None:
        """Split off per-län files first when the user asked for it and this
        collection is known to come as a single nationwide file (see
        core/split.SPLITTABLE) - otherwise just add the file as usual."""
        field = SPLITTABLE.get(collection)
        if field and self.split_ortnamn.isChecked():
            try:
                sublayers = QgsProviderRegistry.instance().querySublayers(path)
            except Exception:  # pragma: no cover - defensive, provider quirks vary
                sublayers = []
            vector_sublayers = [s for s in sublayers if s.type() == Qgis.LayerType.Vector]
            if len(vector_sublayers) <= 1:
                table = vector_sublayers[0].name() if vector_sublayers else collection
                split_results = split_by_lan(path, table, field, Path(path).parent)
                if split_results:
                    for _lan_name, split_path in split_results:
                        self._add_vector(collection, str(split_path), project, failures, font_missing, group)
                    return
                failures.append(f"{Path(path).name}: kunde inte delas upp per län, lägger till odelad")
        self._add_vector(collection, path, project, failures, font_missing, group)

    def _add_zip_contents(
        self, collection: str, zip_path: str, project: QgsProject, failures: list, font_missing: list
    ) -> None:
        extract_dir = os.path.splitext(zip_path)[0]
        try:
            with zipfile.ZipFile(zip_path) as archive:
                archive.extractall(extract_dir)
                names = archive.namelist()
        except (zipfile.BadZipFile, OSError) as exc:
            failures.append(f"{Path(zip_path).name}: kunde inte packas upp ({exc})")
            return

        # One group per download, at the top of the TOC, so a kommun's layers
        # stay together and can be told apart from the next one downloaded.
        group = project.layerTreeRoot().insertGroup(0, Path(zip_path).stem)

        for name in names:
            ext = os.path.splitext(name)[1].lower()
            full_path = os.path.join(extract_dir, name)
            if ext in RASTER_EXTENSIONS:
                self._add_raster(full_path, project, failures, group)
            elif ext in DIRECT_VECTOR_EXTENSIONS:
                self._add_vector_or_split(collection, full_path, project, failures, font_missing, group)

    @staticmethod
    def _add_raster(
        path: str, project: QgsProject, failures: list, group: QgsLayerTreeGroup | None = None
    ) -> None:
        layer = QgsRasterLayer(path, Path(path).stem)
        if layer.isValid():
            project.addMapLayer(layer, group is None)
            if group is not None:
                group.insertLayer(len(group.children()), layer)
        else:
            failures.append(f"{Path(path).name}: kunde inte öppnas som raster")

    @staticmethod
    def _add_vector(
        collection: str,
        path: str,
        project: QgsProject,
        failures: list,
        font_missing: list,
        group: QgsLayerTreeGroup | None = None,
    ) -> None:
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
                _applied, missing = apply_style(layer, collection, Path(path).stem)
                if missing:
                    font_missing.append(True)
                project.addMapLayer(layer, group is None)
                if group is not None:
                    group.insertLayer(len(group.children()), layer)
            else:
                failures.append(f"{Path(path).name}: kunde inte öppnas som vektorlager")
            return

        stem = Path(path).stem
        multiple = len(vector_sublayers) > 1
        by_table = {s.name(): s for s in vector_sublayers}
        # Cartographic order (points on top, then lines, then polygon fills
        # at the bottom) per Lantmäteriet's own QLR - see core/styles.DRAW_ORDER.
        ordered_tables = sort_by_draw_order(collection, list(by_table.keys()))
        for index, table in enumerate(ordered_tables):
            sublayer = by_table[table]
            name = f"{stem} - {table}" if multiple else stem
            layer = QgsVectorLayer(sublayer.uri(), name, sublayer.providerKey())
            if layer.isValid():
                _applied, missing = apply_style(layer, collection, table)
                if missing:
                    font_missing.append(True)
                project.addMapLayer(layer, group is None)
                if group is not None:
                    group.insertLayer(index, layer)
            else:
                failures.append(f"{Path(path).name} ({table}): kunde inte öppnas som vektorlager")
