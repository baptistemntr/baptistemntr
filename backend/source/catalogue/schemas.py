from datetime import datetime

from pydantic import BaseModel


class OptionOut(BaseModel):
    id: int
    code: str
    label: str
    technical_label: str | None = None
    help_text: str | None = None


class OptionGroupOut(BaseModel):
    id: int
    code: str
    label: str
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


class ConfigurationResult(BaseModel):
    item_number: str
    designation: str | None = None
    commercial_ref: str | None = None
    product_line: str | None = None
    matched_on: list[dict]
    license: dict | None = None
    warnings: list[str] = []


class SyncReport(BaseModel):
    fetched: int
    created: int
    updated: int
    synced_at: datetime
