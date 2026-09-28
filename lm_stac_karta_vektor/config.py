"""Endpoints and constants for Lantmäteriet's STAC-karta and STAC-vektor services."""

from __future__ import annotations

from dataclasses import dataclass

PLUGIN_NAME = "Geodata Downloader – Karta/Vektor (Lantmäteriet)"
SETTINGS_PREFIX = "lm_stac_karta_vektor"

API_URL = "https://api.lantmateriet.se"
TOKEN_URL = "https://apimanager.lantmateriet.se/oauth2/token"

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
    "stac-karta": Service("stac-karta", "STAC-karta (raster)", "/stac-karta/v1"),
    "stac-vektor": Service("stac-vektor", "STAC-vektor (vektor)", "/stac-vektor/v1"),
}
DEFAULT_SERVICE = "stac-karta"

# Nationell militär karta (nmk50, nmk250) är behörighetsskyddad och kräver
# ett systemkonto med särskild beställning - den går inte att ladda ned med
# vanlig STAC-åtkomst och döljs därför i gränssnittet.
RESTRICTED_COLLECTIONS = {"nmk50", "nmk250"}


def search_base_url(service_key: str) -> str:
    return API_URL + SERVICES[service_key].path
