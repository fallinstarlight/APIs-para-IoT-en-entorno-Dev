"""Pydantic v2 schemas with strict, server-side validation."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------------------
# Shared validators
# ---------------------------------------------------------------------------
ALLOWED_SOURCES = {"MANUAL", "DEMO", "API", "SYSTEM"}


def _non_blank(value: Optional[str], field: str, max_len: int) -> Optional[str]:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string")
    v = value.strip()
    if not v:
        raise ValueError(f"{field} must not be blank")
    if len(v) > max_len:
        raise ValueError(f"{field} must be at most {max_len} characters")
    return v


# ---------------------------------------------------------------------------
# Vehicles
# ---------------------------------------------------------------------------
class VehicleCreate(BaseModel):
    name: str = Field(..., max_length=80)
    model: Optional[str] = Field(None, max_length=80)
    description: Optional[str] = Field(None, max_length=255)
    microcontroller: Optional[str] = Field(None, max_length=50)

    @field_validator("name")
    @classmethod
    def _v_name(cls, v: str) -> str:
        return _non_blank(v, "name", 80)

    @field_validator("model", "description", "microcontroller")
    @classmethod
    def _v_opt(cls, v, info):
        return _non_blank(v, info.field_name, 255)


class VehicleUpdate(VehicleCreate):
    isActive: bool = True


class Vehicle(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    vehicleId: int
    name: str
    model: Optional[str] = None
    description: Optional[str] = None
    microcontroller: Optional[str] = None
    registrationDate: Optional[datetime] = None
    isActive: bool = True


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------
class CommandCreate(BaseModel):
    vehicleId: int = Field(..., gt=0)
    name: str = Field(..., max_length=60)
    code: int = Field(..., ge=0, le=2_147_483_647)
    description: Optional[str] = Field(None, max_length=255)

    @field_validator("name")
    @classmethod
    def _v_name(cls, v: str) -> str:
        return _non_blank(v, "name", 60)

    @field_validator("description")
    @classmethod
    def _v_desc(cls, v):
        return _non_blank(v, "description", 255)


class CommandUpdate(BaseModel):
    name: str = Field(..., max_length=60)
    code: int = Field(..., ge=0, le=2_147_483_647)
    description: Optional[str] = Field(None, max_length=255)
    isActive: bool = True

    @field_validator("name")
    @classmethod
    def _v_name(cls, v: str) -> str:
        return _non_blank(v, "name", 60)

    @field_validator("description")
    @classmethod
    def _v_desc(cls, v):
        return _non_blank(v, "description", 255)


class Command(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    commandId: int
    vehicleId: int
    name: str
    code: int
    description: Optional[str] = None
    isActive: bool = True


# ---------------------------------------------------------------------------
# Status
# ---------------------------------------------------------------------------
class StatusUpdate(BaseModel):
    vehicleId: int = Field(..., gt=0)
    commandId: Optional[int] = Field(None, gt=0)
    isConnected: bool = False
    source: str = Field("MANUAL", max_length=30)

    @field_validator("source")
    @classmethod
    def _v_source(cls, v: str) -> str:
        v2 = (v or "").strip().upper()
        if v2 not in ALLOWED_SOURCES:
            raise ValueError(
                f"source must be one of {sorted(ALLOWED_SOURCES)}"
            )
        return v2


class Status(BaseModel):
    vehicleId: int
    vehicleName: str
    commandId: Optional[int] = None
    commandName: Optional[str] = None
    code: Optional[int] = None
    isConnected: bool
    lastUpdate: Optional[datetime] = None


# ---------------------------------------------------------------------------
# History
# ---------------------------------------------------------------------------
class HistoryRegister(BaseModel):
    vehicleId: int = Field(..., gt=0)
    commandId: Optional[int] = Field(None, gt=0)
    source: str = Field("MANUAL", max_length=30)

    @field_validator("source")
    @classmethod
    def _v_source(cls, v: str) -> str:
        v2 = (v or "").strip().upper()
        if v2 not in ALLOWED_SOURCES:
            raise ValueError(
                f"source must be one of {sorted(ALLOWED_SOURCES)}"
            )
        return v2


class HistoryEntry(BaseModel):
    historyId: int
    vehicleId: int
    commandName: Optional[str] = None
    code: Optional[int] = None
    timestamp: Optional[datetime] = None
    source: str


# ---------------------------------------------------------------------------
# Demos
# ---------------------------------------------------------------------------
class DemoCreate(BaseModel):
    vehicleId: int = Field(..., gt=0)
    name: str = Field(..., max_length=80)
    description: Optional[str] = Field(None, max_length=255)

    @field_validator("name")
    @classmethod
    def _v_name(cls, v: str) -> str:
        return _non_blank(v, "name", 80)

    @field_validator("description")
    @classmethod
    def _v_desc(cls, v):
        return _non_blank(v, "description", 255)


class DemoUpdate(BaseModel):
    name: str = Field(..., max_length=80)
    description: Optional[str] = Field(None, max_length=255)
    isActive: bool = True

    @field_validator("name")
    @classmethod
    def _v_name(cls, v: str) -> str:
        return _non_blank(v, "name", 80)

    @field_validator("description")
    @classmethod
    def _v_desc(cls, v):
        return _non_blank(v, "description", 255)


class Demo(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    demoId: int
    vehicleId: int
    name: str
    description: Optional[str] = None
    isActive: bool = True


class DemoMovementCreate(BaseModel):
    demoId: int = Field(..., gt=0)
    commandId: int = Field(..., gt=0)
    sortOrder: int = Field(..., ge=0, le=10_000)
    durationMs: int = Field(..., ge=0, le=3_600_000)  # ≤ 1 hour
    pauseMs: int = Field(0, ge=0, le=3_600_000)


class DemoMovementUpdate(BaseModel):
    commandId: int = Field(..., gt=0)
    sortOrder: int = Field(..., ge=0, le=10_000)
    durationMs: int = Field(..., ge=0, le=3_600_000)
    pauseMs: int = Field(0, ge=0, le=3_600_000)


class DemoMovement(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    demoMovementId: int
    sortOrder: int
    commandId: int
    commandName: Optional[str] = None
    code: Optional[int] = None
    durationMs: int
    pauseMs: int