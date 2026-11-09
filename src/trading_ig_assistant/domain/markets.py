"""Stable business identifiers for the initially approved market universe."""

from enum import StrEnum


class CanonicalUnderlyingId(StrEnum):
    """Provider-independent underlyings approved for initial Scanner profiles."""

    US_TECH_100 = "US_TECH_100"
    FRANCE_40 = "FRANCE_40"
    GERMANY_40 = "GERMANY_40"
    SPOT_GOLD = "SPOT_GOLD"
    US_CRUDE = "US_CRUDE"
