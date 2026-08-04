"""Validated API contracts."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .domain import (
    AssetStatus,
    AssetType,
    DispatchStatus,
    FlexDirection,
    OfferStatus,
    ReservationStatus,
)


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class AssetCreate(ApiModel):
    external_id: str = Field(min_length=3, max_length=100)
    owner_id: str = Field(min_length=3, max_length=100)
    asset_type: AssetType
    capacity_kw: Decimal = Field(gt=0, max_digits=18, decimal_places=6)
    location_code: str = Field(min_length=2, max_length=80)


class AssetRead(AssetCreate):
    id: str
    status: AssetStatus
    created_at: datetime


class OfferCreate(ApiModel):
    asset_id: str
    window_start: datetime
    window_end: datetime
    direction: FlexDirection
    quantity_kw: Decimal = Field(gt=0, max_digits=18, decimal_places=6)
    price_per_kwh: Decimal = Field(ge=0, max_digits=18, decimal_places=6)

    @model_validator(mode="after")
    def validate_window(self) -> OfferCreate:
        if self.window_start.tzinfo is None or self.window_end.tzinfo is None:
            raise ValueError("offer timestamps must include a timezone")
        if self.window_end <= self.window_start:
            raise ValueError("window_end must be later than window_start")
        return self


class OfferRead(OfferCreate):
    id: str
    status: OfferStatus
    created_by: str
    created_at: datetime


class ReservationCreate(ApiModel):
    quantity_kw: Decimal = Field(gt=0, max_digits=18, decimal_places=6)


class ReservationRead(ApiModel):
    id: str
    offer_id: str
    quantity_kw: Decimal
    status: ReservationStatus
    requested_by: str
    created_at: datetime


class DispatchCreate(ApiModel):
    target_kw: Decimal = Field(gt=0, max_digits=18, decimal_places=6)
    starts_at: datetime
    ends_at: datetime

    @model_validator(mode="after")
    def validate_window(self) -> DispatchCreate:
        if self.starts_at.tzinfo is None or self.ends_at.tzinfo is None:
            raise ValueError("dispatch timestamps must include a timezone")
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be later than starts_at")
        return self


class DispatchRead(DispatchCreate):
    id: str
    reservation_id: str
    status: DispatchStatus
    issued_by: str
    adapter_reference: str | None
    created_at: datetime


class MeterReadingCreate(ApiModel):
    asset_id: str
    interval_start: datetime
    interval_end: datetime
    energy_kwh: Decimal = Field(ge=0, max_digits=18, decimal_places=6)
    source: str = Field(min_length=2, max_length=100)

    @model_validator(mode="after")
    def validate_interval(self) -> MeterReadingCreate:
        if self.interval_start.tzinfo is None or self.interval_end.tzinfo is None:
            raise ValueError("meter timestamps must include a timezone")
        if self.interval_end <= self.interval_start:
            raise ValueError("interval_end must be later than interval_start")
        return self


class MeterReadingRead(MeterReadingCreate):
    id: str
    fingerprint: str
    recorded_by: str
    received_at: datetime


class SettlementRead(ApiModel):
    id: str
    reservation_id: str
    delivered_kwh: Decimal
    price_per_kwh: Decimal
    amount: Decimal
    evidence_hash: str
    settled_by: str
    created_at: datetime


class EvidenceRead(ApiModel):
    manifest: dict[str, Any]
    evidence_hash: str
    hash_valid: bool


class AuditVerificationRead(ApiModel):
    valid: bool
    event_count: int
    head_hash: str
    broken_sequence: int | None = None


class HealthRead(ApiModel):
    status: str
    version: str
    environment: str


class ErrorRead(ApiModel):
    code: str
    message: str
