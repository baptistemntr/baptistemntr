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


# --- Espace IMI (admin) -----------------------------------------------------------------
#
# `caption` n'apparaît jamais en écriture ici : c'est la clé stable qui relie une option à
# sa colonne de grille (voir `Option` dans models.py), la renommer casserait la
# correspondance article. Elle ne se fixe qu'à la création.


class AdminOptionOut(BaseModel):
    id: int
    group_id: int
    caption: str
    label: str
    technical_label: str | None = None
    help_text: str | None = None
    kind: str
    component_item_number: str | None = None
    unit_price: float | None = None
    position: int


class AdminOptionCreate(BaseModel):
    group_id: int
    caption: str
    label: str
    technical_label: str | None = None
    help_text: str | None = None
    kind: str = "grid"
    component_item_number: str | None = None
    unit_price: float | None = None
    position: int = 0


class AdminOptionUpdate(BaseModel):
    label: str
    technical_label: str | None = None
    help_text: str | None = None
    kind: str
    component_item_number: str | None = None
    unit_price: float | None = None
    position: int = 0


class AdminGroupOut(BaseModel):
    id: int
    family_code: str
    code: str
    label: str
    section: str | None = None
    help_text: str | None = None
    selection: str
    required: bool
    position: int
    options: list[AdminOptionOut]


class AdminGroupCreate(BaseModel):
    family_code: str
    code: str
    label: str
    section: str | None = None
    help_text: str | None = None
    selection: str = "single"
    required: bool = False
    position: int = 0


class AdminGroupUpdate(BaseModel):
    label: str
    section: str | None = None
    help_text: str | None = None
    selection: str
    required: bool
    position: int = 0


class AdminArticleOut(BaseModel):
    id: int
    family_code: str
    item_number: str | None = None
    designation: str | None = None
    commercial_ref: str | None = None
    standard_price: float | None = None
    option_ids: list[int]
    captions: list[str]


class AdminArticleCreate(BaseModel):
    family_code: str
    item_number: str | None = None
    designation: str | None = None
    commercial_ref: str | None = None
    standard_price: float | None = None
    option_ids: list[int] = []


class AdminArticleUpdate(BaseModel):
    item_number: str | None = None
    designation: str | None = None
    commercial_ref: str | None = None
    standard_price: float | None = None
    option_ids: list[int] = []


class AdminRuleOut(BaseModel):
    id: int
    family_code: str
    kind: str
    source_option_id: int
    target_option_id: int
    message: str | None = None


class AdminRuleCreate(BaseModel):
    family_code: str
    kind: str
    source_option_id: int
    target_option_id: int
    message: str | None = None


class AdminFamilyUpdate(BaseModel):
    label: str
    description: str | None = None


class AdminFamilyDetailOut(FamilyOut):
    groups: list[AdminGroupOut]
    articles: list[AdminArticleOut]
    rules: list[AdminRuleOut]
