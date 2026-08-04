from datetime import datetime

from pydantic import BaseModel


class OptionOut(BaseModel):
    id: int
    caption: str
    label: str
    # Définition technique issue du classeur : c'est le texte de l'infobulle.
    technical_label: str | None = None
    help_text: str | None = None
    kind: str
    component_item_number: str | None = None


class OptionGroupOut(BaseModel):
    id: int
    code: str
    label: str
    section: str | None = None
    help_text: str | None = None
    selection: str
    required: bool
    options: list[OptionOut]


class FamilyOut(BaseModel):
    code: str
    label: str
    description: str | None = None
    has_license: bool


class FamilyDetailOut(FamilyOut):
    groups: list[OptionGroupOut]


class ConfigurationRequest(BaseModel):
    family_code: str
    option_ids: list[int]


class PriceOut(BaseModel):
    # standard (prix de l'article) | estimate (somme des options) | unavailable
    kind: str
    amount: float | None = None
    missing_prices: list[str] = []


class NeighbourOut(BaseModel):
    """Combinaison proche, pour expliquer une configuration sans article."""

    item_number: str | None = None
    designation: str | None = None
    missing: list[str] = []
    extra: list[str] = []


class ConfigurationResult(BaseModel):
    found: bool
    item_number: str
    designation: str | None = None
    commercial_ref: str | None = None
    product_line: str | None = None
    price: PriceOut
    matched_on: list[dict]
    closest: list[NeighbourOut] = []
    license: dict | None = None
    warnings: list[str] = []


class SeedReport(BaseModel):
    families: int
    options: int
    articles: int
    findings: int


class LicenseSeedReport(BaseModel):
    families: int
    words: int
    bits: int
    unmapped: int


class SyncReport(BaseModel):
    fetched: int
    created: int
    updated: int
    synced_at: datetime
