"""QML styles per collection and layer (styles/{collection}_{table}.qml,
e.g. fastighetsindelning_granspunkt.qml).

Mirrors the sibling plugin's core/styles.py (matself/LM-STAC-Downloader).
The QML files are extracted from Lantmäteriet's official QGIS style package
(a .qlr manér file published on the product's Geotorget documentation page)
by loading it with QgsLayerDefinition and re-saving each layer's symbology
and labeling on their own - see docs/stilfiler.md for how a given file was
produced and which Geotorget product page it came from.
"""

from __future__ import annotations

from pathlib import Path

from qgis.core import QgsMapLayer, QgsVectorLayer
from qgis.PyQt.QtXml import QDomDocument

from ..config import PLUGIN_NAME
from .fonts import ensure_font, font_referenced_in

STYLES_DIR = Path(__file__).resolve().parent.parent / "styles"
# Only symbology and labels: the rest of the QML (fields, forms) belongs to the data.
CATEGORIES = QgsMapLayer.StyleCategory.Symbology | QgsMapLayer.StyleCategory.Labeling


def find_style(collection_id: str, table: str) -> Path | None:
    """The style file for a collection's table, if one has been extracted."""
    path = STYLES_DIR / f"{collection_id}_{table}.qml"
    return path if path.exists() else None


# Layer stacking order within a collection, top of the QGIS layer tree first
# (drawn last, i.e. on top of everything below it). Taken directly from the
# layer-tree-group order in Lantmäteriet's own QLR files, which they
# document as "en föreslagen ritordning av skikten" (a suggested draw order
# for the layers) - see docs/stilfiler.md for exactly how this was read out
# of each QLR.
DRAW_ORDER: dict[str, list[str]] = {
    "fastighetsindelning": [
        "granspunkt",
        "registerenhetsomradespunkt",
        "registerenhetsomradeslinje",
        "registerenhetsomradesgrans",
        "traktyta",
        "registerenhetsomradesyta",
    ],
    "marktacke": ["markkantlinje", "sankmark", "mark"],
    # No official Lantmäteriet QLR exists for this collection (see
    # docs/stilfiler.md) - smaller units on top of bigger ones, same
    # principle as the other collections above.
    "kommun-lan-rike": ["kommun", "lan", "rike"],
}


def sort_by_draw_order(collection_id: str, tables: list[str]) -> list[str]:
    """Tables in the order they should appear in the QGIS layer tree (top
    first), per DRAW_ORDER. Tables with no known order (e.g. a non-spatial
    table, or a collection without an extracted style) keep their original
    relative order and are appended after the known ones."""
    order = DRAW_ORDER.get(collection_id)
    if not order:
        return tables
    known = [t for t in order if t in tables]
    unknown = [t for t in tables if t not in order]
    return known + unknown


def apply_style(layer: QgsVectorLayer, collection_id: str, table: str) -> tuple[bool, bool]:
    """Apply the collection table's style if there is one, and store it as
    default in the GeoPackage.

    Returns (applied, font_missing). font_missing is only True when the
    style we actually applied references a font that isn't available -
    callers should warn about the font once per batch, not for every
    download regardless of whether it needed it at all.
    """
    path = find_style(collection_id, table)
    if path is None:
        return False, False
    font_missing = font_referenced_in(path) and not ensure_font()
    # QgsMapLayer.loadNamedStyle(path, ...) can silently resolve to a style already
    # saved in the layer's own provider (e.g. a GeoPackage's layer_styles table, which
    # apply_style itself writes to below) instead of reading the QML file - reading the
    # file ourselves and importing it via QDomDocument avoids that ambiguity.
    doc = QDomDocument()
    doc.setContent(path.read_text(encoding="utf-8"), True)
    ok, _message = layer.importNamedStyle(doc, CATEGORIES)
    if ok:
        # Default style in the GeoPackage's layer_styles table: the file opens
        # styled in any QGIS, also without this plugin.
        if hasattr(layer, "saveStyleToDatabaseV2"):  # QGIS >= 3.40
            layer.saveStyleToDatabaseV2(f"{collection_id}_{table}", PLUGIN_NAME, True, "", CATEGORIES)
        else:
            layer.saveStyleToDatabase(f"{collection_id}_{table}", PLUGIN_NAME, True, "", CATEGORIES)
        layer.triggerRepaint()
    return ok, font_missing
