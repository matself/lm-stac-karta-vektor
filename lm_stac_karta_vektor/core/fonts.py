"""Registers the LMTopografisymboler font Lantmäteriet's official styles use
for point symbols (e.g. fastighetsgränspunkter in fastighetsindelning).

Bundled with the plugin (fonts/lmtopografisymboler.ttf, from the same
Geotorget product documentation page as the style files, see
docs/stilfiler.md) and registered for the running QGIS session only via
QFontDatabase.addApplicationFont - never installed into the OS font
directory, so nothing outside this QGIS session is affected.
"""

from __future__ import annotations

from pathlib import Path

from qgis.PyQt.QtGui import QFontDatabase

FONT_FAMILY = "LMTopografisymboler"
FONT_PATH = Path(__file__).resolve().parent.parent / "fonts" / "lmtopografisymboler.ttf"

_attempted = False


def _families() -> list[str]:
    try:
        return list(QFontDatabase.families())  # Qt6: static
    except TypeError:
        return list(QFontDatabase().families())  # Qt5: instance method


def ensure_font() -> bool:
    """True if FONT_FAMILY is available - already installed on the system,
    or just registered from the bundled file for this session."""
    global _attempted
    if FONT_FAMILY in _families():
        return True
    if _attempted:
        return False  # already tried to register the bundled file and failed
    _attempted = True
    font_id = QFontDatabase.addApplicationFont(str(FONT_PATH))
    if font_id == -1:
        return False
    families = QFontDatabase.applicationFontFamilies(font_id)
    return FONT_FAMILY in families


def font_referenced_in(qml_path: Path) -> bool:
    """True if the given style file actually uses FONT_FAMILY (e.g. a
    FontMarker symbol layer), so callers only need to warn about the font
    when a style that needs it was actually applied - not for every
    download regardless of whether any downloaded layer's style uses it."""
    try:
        return FONT_FAMILY in qml_path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return False
