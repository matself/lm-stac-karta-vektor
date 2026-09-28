"""Light-weight view of a STAC item with a downloadable `data` asset."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

RASTER_EXTENSIONS = {".tif", ".tiff", ".jp2"}
ARCHIVE_EXTENSIONS = {".zip"}
DIRECT_VECTOR_EXTENSIONS = {".gpkg", ".shp", ".gml", ".geojson", ".json"}

# Lantmäteriet's titles for per-kommun collections all end "<preposition>
# <Kommun> kommun", but the preposition isn't consistent across collections:
# "Byggnader för Skellefteå kommun" / "Belägenhetsadresser för Sjöbo kommun"
# / "Marktäcke för Sjöbo kommun", but "Fastighetsindelning i Sjöbo kommun".
# The item id is the kommunkod itself (e.g. "2482"), so the title is the
# only place the human-readable name shows up.
_KOMMUN_RE = re.compile(r"\b(?:för|i)\s+(.+?)\s+kommun\b", re.IGNORECASE)


@dataclass(frozen=True)
class StacItem:
    id: str
    collection: str
    title: str
    date: str | None
    size: int | None
    href: str
    bbox: tuple[float, ...]
    geometry: dict[str, Any] | None

    @property
    def filename(self) -> str:
        return self.href.rstrip("/").rsplit("/", 1)[-1]

    @property
    def extension(self) -> str:
        name = self.filename.lower()
        return name[name.rfind("."):] if "." in name else ""

    @property
    def kommun(self) -> str | None:
        """The kommun name extracted from the STAC title, if the title
        follows Lantmäteriet's "<Tema> för <Kommun> kommun" phrasing."""
        match = _KOMMUN_RE.search(self.title)
        return match.group(1) if match else None

    @property
    def label(self) -> str:
        """What to show for this item in a results list: the kommun name
        with its code if we could tell them apart, otherwise just the id."""
        kommun = self.kommun
        return f"{kommun} ({self.id})" if kommun else self.id

    @property
    def kind(self) -> str:
        ext = self.extension
        if ext in RASTER_EXTENSIONS:
            return "raster"
        if ext in ARCHIVE_EXTENSIONS:
            return "arkiv (vektor)"
        if ext in DIRECT_VECTOR_EXTENSIONS:
            return "vektor"
        return ext.lstrip(".") or "okänd"


def parse_item(feature: dict[str, Any]) -> StacItem | None:
    """Return None for items without a downloadable `data` asset."""
    assets = feature.get("assets") or {}
    data = assets.get("data") or next(
        (a for a in assets.values() if "data" in (a.get("roles") or [])), None
    )
    if not data or not data.get("href"):
        return None

    props = feature.get("properties") or {}
    return StacItem(
        id=feature["id"],
        collection=feature.get("collection", ""),
        title=props.get("title") or feature.get("id", ""),
        date=(props.get("datetime") or "")[:10] or None,
        size=data.get("file:size"),
        href=data["href"],
        bbox=tuple(feature.get("bbox") or ()),
        geometry=feature.get("geometry"),
    )
