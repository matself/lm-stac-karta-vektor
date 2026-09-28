"""Swedish län (county) codes, for splitting the nationwide `ortnamn`
download into more manageable per-län files.

`ortnamn` is the one STAC-vektor collection Lantmäteriet delivers as a
single national item instead of one item per kommun (see docs/stilfiler.md
and README.md's "STAC-karta is disabled" section for the general pattern -
some STAC-vektor collections just aren't tiled). Every `ortnamn` feature
carries a `lanskod` field with one of these 21 standard 2-digit codes.
"""

from __future__ import annotations

LAN_NAMES: dict[str, str] = {
    "01": "Stockholms län",
    "03": "Uppsala län",
    "04": "Södermanlands län",
    "05": "Östergötlands län",
    "06": "Jönköpings län",
    "07": "Kronobergs län",
    "08": "Kalmar län",
    "09": "Gotlands län",
    "10": "Blekinge län",
    "12": "Skåne län",
    "13": "Hallands län",
    "14": "Västra Götalands län",
    "17": "Värmlands län",
    "18": "Örebro län",
    "19": "Västmanlands län",
    "20": "Dalarnas län",
    "21": "Gävleborgs län",
    "22": "Västernorrlands län",
    "23": "Jämtlands län",
    "24": "Västerbottens län",
    "25": "Norrbottens län",
}

_TRANSLIT = str.maketrans("åäöÅÄÖ", "aaoAAO")


def lan_name(lanskod: str) -> str:
    """Human-readable name for a lanskod, or the raw code if unknown."""
    return LAN_NAMES.get(lanskod, lanskod)


def lan_slug(lanskod: str) -> str:
    """Filesystem-safe, ASCII slug for a lanskod, e.g. "01" -> "stockholms_lan"."""
    name = lan_name(lanskod)
    if name == lanskod:
        return lanskod
    name = name.removesuffix(" län")
    return name.translate(_TRANSLIT).lower().replace(" ", "_")
