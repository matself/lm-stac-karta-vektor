"""Split a nationwide vector GeoPackage table into one file per attribute
value, e.g. `ortnamn` by `lanskod` - see docs/stilfiler.md.
"""

from __future__ import annotations

from pathlib import Path

from qgis.core import (
    QgsCoordinateTransformContext,
    QgsVectorFileWriter,
    QgsVectorLayer,
)

from .lan import lan_name, lan_slug

# Collections known to be delivered as a single nationwide file rather than
# one item per kommun, and the field to split them by - see dock.py's
# _add_vector_or_split, the only caller.
SPLITTABLE: dict[str, str] = {"ortnamn": "lanskod"}


def split_by_lan(path: str, table: str, field: str, out_dir: Path) -> list[tuple[str, Path]]:
    """Write one GeoPackage per distinct value of `field` found in `path`'s
    `table` layer, into `out_dir`. Returns (display name, file path) pairs,
    sorted by län name. The source file/layer is left untouched."""
    source = QgsVectorLayer(f"{path}|layername={table}", table, "ogr")
    if not source.isValid():
        return []

    field_idx = source.fields().indexOf(field)
    if field_idx < 0:
        return []

    codes = sorted(str(v) for v in source.uniqueValues(field_idx) if v not in (None, ""))
    stem = Path(path).stem
    transform_context = QgsCoordinateTransformContext()

    results: list[tuple[str, Path]] = []
    for code in codes:
        out_path = out_dir / f"{stem}_{lan_slug(code)}.gpkg"
        # QgsVectorFileWriter.SaveVectorOptions has no attribute-filter option
        # of its own (only filterExtent, a spatial bbox) - a subset string on
        # the source layer is how you restrict which features get written.
        source.setSubsetString(f'"{field}" = \'{code}\'')
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = "GPKG"
        options.layerName = table
        error, _error_message, _new_path, _new_layer = QgsVectorFileWriter.writeAsVectorFormatV3(
            source, str(out_path), transform_context, options
        )
        if error == QgsVectorFileWriter.WriterError.NoError:
            results.append((lan_name(code), out_path))
    source.setSubsetString("")

    results.sort(key=lambda pair: pair[0])
    return results
