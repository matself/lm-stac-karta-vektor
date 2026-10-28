"""Cut an area out of a topowebb GeoPackage without downloading the whole file.

The topowebb items are single 140-175 GB GeoPackages of raster tiles. The
download server answers HTTP Range requests and GDAL can open a GeoPackage
through /vsicurl/, so QGIS' raster provider reads only the tiles (and, for
coarser output, the overview levels) that the requested extent needs. The
credentials come from the QGIS auth config: the headers it would send (Basic
or OAuth2 Bearer) are handed to GDAL for the clip's thread only, because
/vsicurl/ with `authcfg` in the URI works for Basic but not for OAuth2.
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass
from pathlib import Path

from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsCoordinateTransformContext,
    QgsMessageLog,
    QgsProject,
    QgsRasterBlockFeedback,
    QgsRasterFileWriter,
    QgsRasterLayer,
    QgsRasterPipe,
    QgsRectangle,
    QgsTask,
)
from osgeo import gdal
from qgis.PyQt.QtCore import pyqtSignal

from ..config import PLUGIN_NAME, TOPOWEBB_NATIVE_RES
from .auth import auth_headers
from .items import StacItem

SEARCH_CRS = "EPSG:4326"

# (label, QgsRasterFileWriter format, file extension, creation options)
OUTPUT_FORMATS = {
    "gtiff": ("GeoTIFF", "GTiff", ".tif", ["COMPRESS=DEFLATE", "TILED=YES", "BIGTIFF=IF_SAFER"]),
    "gpkg": ("GeoPackage", "GPKG", ".gpkg", ["TILE_FORMAT=PNG"]),
}
DEFAULT_FORMAT = "gtiff"


def native_resolution(item: StacItem) -> float | None:
    """Pixel size of the item's full-resolution level, in its CRS units."""
    return TOPOWEBB_NATIVE_RES.get(item.epsg) if item.epsg else None


def item_crs(item: StacItem) -> QgsCoordinateReferenceSystem:
    return QgsCoordinateReferenceSystem(f"EPSG:{item.epsg}")


def clip_extent(extent_wgs84: QgsRectangle, item: StacItem) -> QgsRectangle:
    """The search extent (EPSG:4326) as a bounding box in the item's CRS."""
    transform = QgsCoordinateTransform(
        QgsCoordinateReferenceSystem(SEARCH_CRS), item_crs(item), QgsProject.instance()
    )
    return transform.transformBoundingBox(extent_wgs84)


def grid_size(extent: QgsRectangle, resolution: float) -> tuple[int, int]:
    return (
        max(1, math.ceil(extent.width() / resolution)),
        max(1, math.ceil(extent.height() / resolution)),
    )


def uncompressed_bytes(cols: int, rows: int) -> int:
    return cols * rows * 4  # RGBA


def output_path(output_dir: Path, item: StacItem, extent: QgsRectangle, resolution: float, fmt: str) -> Path:
    ext = OUTPUT_FORMATS[fmt][2]
    res = f"{resolution:.2f}".rstrip("0").rstrip(".").replace(".", "_")
    name = f"{item.id}_{int(extent.xMinimum())}_{int(extent.yMinimum())}_{res}m{ext}"
    return output_dir / item.collection / name


def remote_uri(href: str) -> str:
    return f"/vsicurl/{href}"


@dataclass(frozen=True)
class ClipJob:
    item: StacItem
    extent: QgsRectangle  # in the item's CRS
    resolution: float
    fmt: str
    path: Path


def _is_success(result) -> bool:
    # QgsRasterFileWriter.WriterError (3.x) or Qgis.RasterFileWriterResult (4.x)
    return getattr(result, "value", result) == 0


class ClipTask(QgsTask):
    # Emitted in the main thread via QgsTask.finished → safe for UI work.
    # Always emitted exactly once from finished(): (written path, error text).
    # Both are empty when the task was cancelled.
    ended = pyqtSignal(str, str)

    def __init__(self, job: ClipJob, authcfg: str):
        super().__init__(f"Geodata: klipper ut {job.item.id}", QgsTask.Flag.CanCancel)
        self.job = job
        self.authcfg = authcfg
        # Fetched here, on the main thread, right before the clip starts so
        # an OAuth2 token is fresh for it.
        self._headers = auth_headers(authcfg, job.item.href)
        self.error: str | None = None
        self._feedback = QgsRasterBlockFeedback()
        self._feedback.progressChanged.connect(self.setProgress)
        self._transform_context: QgsCoordinateTransformContext = (
            QgsProject.instance().transformContext()
        )

    def cancel(self) -> None:
        self._feedback.cancel()
        super().cancel()

    def run(self) -> bool:
        job = self.job
        label, driver, _ext, options = OUTPUT_FORMATS[job.fmt]
        QgsMessageLog.logMessage(
            f"Klipper ut {job.item.id} {job.extent.toString(1)} @ {job.resolution:g} -> {job.path}",
            PLUGIN_NAME,
            Qgis.MessageLevel.Info,
        )

        if not self._headers:
            self.error = "Autentiseringen gav inga HTTP-rubriker. Kontrollera inloggningen."
            return False

        # Thread-local, so the token never leaks to other threads' requests.
        gdal.SetThreadLocalConfigOption("GDAL_HTTP_HEADERS", "\n".join(self._headers))
        try:
            return self._clip(job, label, driver, options)
        finally:
            gdal.SetThreadLocalConfigOption("GDAL_HTTP_HEADERS", None)

    def _clip(self, job: ClipJob, label: str, driver: str, options: list[str]) -> bool:
        layer = QgsRasterLayer(remote_uri(job.item.href), job.item.id, "gdal")
        if not layer.isValid():
            self.error = (
                "Kunde inte öppna kartfilen på distans. Kontrollera att autentiseringen "
                f"har åtkomst till STAC-karta. {layer.error().summary()}"
            ).strip()
            return False
        if not layer.extent().intersects(job.extent):
            self.error = "Området ligger utanför kartans utbredning."
            return False

        job.path.parent.mkdir(parents=True, exist_ok=True)
        # Written next to the target under a temporary name and renamed on
        # success, so a cancelled or failed clip never looks complete.
        part = job.path.with_name(job.path.stem + ".part" + job.path.suffix)
        if part.exists():
            part.unlink()

        cols, rows = grid_size(job.extent, job.resolution)
        pipe = QgsRasterPipe()
        pipe.set(layer.dataProvider().clone())
        writer = QgsRasterFileWriter(str(part))
        writer.setOutputFormat(driver)
        # GeoPackage names its raster table after the file, which here is the
        # ".part" temp name - give it a stable one instead.
        writer.setCreationOptions(
            options + ([f"RASTER_TABLE={job.item.collection}"] if driver == "GPKG" else [])
        )
        result = writer.writeRaster(
            pipe, cols, rows, job.extent, layer.crs(), self._transform_context, self._feedback
        )

        if self.isCanceled():
            self._discard(part)
            return False
        if not _is_success(result) or not part.exists():
            self.error = f"Kunde inte skriva {label}-filen ({result})."
            self._discard(part)
            return False

        os.replace(part, job.path)
        # GDAL may have left a statistics sidecar under the temporary name.
        aux = Path(str(part) + ".aux.xml")
        if aux.exists():
            os.replace(aux, Path(str(job.path) + ".aux.xml"))
        return True

    @staticmethod
    def _discard(part: Path) -> None:
        for leftover in (part, Path(str(part) + ".aux.xml")):
            try:
                if leftover.exists():
                    leftover.unlink()
            except OSError:
                pass

    def finished(self, result: bool) -> None:
        if result:
            self.ended.emit(str(self.job.path), "")
        elif self.isCanceled():
            self.ended.emit("", "")
        else:
            QgsMessageLog.logMessage(self.error or "Okänt fel", PLUGIN_NAME, Qgis.MessageLevel.Critical)
            self.ended.emit("", self.error or "Okänt fel")
