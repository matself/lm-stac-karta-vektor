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


_ALL_SERVICES = {
    "stac-karta": Service("stac-karta", "STAC-karta (raster)", "/stac-karta/v1"),
    "stac-vektor": Service("stac-vektor", "STAC-vektor (vektor)", "/stac-vektor/v1"),
}

# STAC-karta is disabled: none of its collections can usefully be fetched
# through this plugin right now. nmk50/nmk250 are access-restricted military
# maps (see RESTRICTED_COLLECTIONS below). Its one open collection, topowebb
# (CC-BY-4.0), isn't tiled by area at all - GET /collections/topowebb reports
# a global bbox, and searching it from anywhere in Sweden returns the same 4
# items (145-175 GB each, one per style/projection variant of the whole
# country). Lantmäteriet's own Geotorget product page for it says the
# product can't be ordered there and points to a plain FTP mirror instead
# (ftp://download-opendata.lantmateriet.se/) - i.e. it isn't meant to be
# fetched through the STAC API yet. Flip this back to _ALL_SERVICES (or add
# "stac-karta" back in) if that changes.
SERVICES = {k: v for k, v in _ALL_SERVICES.items() if k != "stac-karta"}
DEFAULT_SERVICE = "stac-vektor"

# Nationell militär karta (nmk50, nmk250) is access-restricted and requires
# a system account with a separate order - it can't be downloaded through
# plain STAC access, so it's hidden from the interface.
RESTRICTED_COLLECTIONS = {"nmk50", "nmk250"}


def search_base_url(service_key: str) -> str:
    return API_URL + SERVICES[service_key].path
