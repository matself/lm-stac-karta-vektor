"""Endpoints and constants for Lantmäteriet's STAC-karta and STAC-vektor services."""

from __future__ import annotations

from dataclasses import dataclass

# Used everywhere in the runtime UI (dock title, message bar, menu entry,
# toolbar tooltip, task manager entries) - kept fully Swedish like the rest
# of the interface. metadata.txt's own `name=` field is the English display
# name plugins.qgis.org requires for the store listing; the two are
# deliberately different strings for different audiences.
PLUGIN_NAME = "Geodata: Vektor (Lantmäteriet)"
SETTINGS_PREFIX = "lm_stac_karta_vektor"

API_URL = "https://api.lantmateriet.se"
OAUTH_ENDPOINT_URL = "https://apimanager.lantmateriet.se/oauth2/token"

# The API takes the WGS 84 bbox of plain STAC.
SEARCH_CRS = "EPSG:4326"
PAGE_LIMIT = 100
MAX_RESULTS = 1000
# Ask for confirmation before downloading more than this.
WARN_BYTES = 2 * 1024**3


@dataclass(frozen=True)
class Service:
    key: str
    label: str
    path: str


SERVICES = {
    "stac-vektor": Service("stac-vektor", "STAC-vektor (vektor)", "/stac-vektor/v1"),
    "stac-karta": Service("stac-karta", "STAC-karta (raster)", "/stac-karta/v1"),
}

DEFAULT_SERVICE = "stac-vektor"

# Nationell militär karta (nmk50, nmk250) is access-restricted and requires
# a system account with a separate order - it can't be downloaded through
# plain STAC access, so it's hidden from the interface.
RESTRICTED_COLLECTIONS = {"nmk50", "nmk250"}

# STAC-karta's one open collection, topowebb (CC-BY-4.0), isn't tiled by
# area: it has 4 items (colour/greyscale x EPSG:3006/3857), each a single
# 140-175 GB GeoPackage of raster tiles covering the whole country (or
# world). The server supports HTTP Range requests and GDAL can open the file
# remotely, so the plugin can cut out just the requested extent instead of
# downloading it all - see core/clip.py.
RASTER_COLLECTIONS = {"topowebb"}

# Native pixel size (CRS units) of the topowebb GeoPackages, by EPSG code.
# EPSG:3857 is 2^25 pixels across the Web Mercator world.
TOPOWEBB_NATIVE_RES = {3006: 0.5, 3857: 40075016.68557849 / 2**25}
# Resolution choices offered for a clip, as multiples of the native pixel size.
CLIP_FACTORS = (1, 2, 4, 8, 16, 32, 64, 128)
# Ask for confirmation above this many (uncompressed RGBA) bytes, refuse above
# MAX_CLIP_PIXELS.
MAX_CLIP_PIXELS = 4_000_000_000


def search_base_url(service_key: str) -> str:
    return API_URL + SERVICES[service_key].path
