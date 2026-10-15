from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


# ---------- Vehicles ----------
class VehicleCreate(BaseModel):
    name: str = Field(..., max_length=80)
    model: Optional[str] = Field(None, max_length=80)
    description: Optional[str] = Field(None, max_length=255)
    microcontroller: Optional[str] = Field(None, max_length=50)


class VehicleUpdate(BaseModel):
    name: str = Field(..., max_length=80)
    model: Optional[str] = Field(None, max_length=80)
    description: Optional[str] = Field(None, max_length=255)
    microcontroller: Optional[str] = Field(None, max_length=50)
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


# ---------- Commands ----------
class CommandCreate(BaseModel):
    vehicleId: int
    name: str = Field(..., max_length=60)
    code: int
    description: Optional[str] = Field(None, max_length=255)


class CommandUpdate(BaseModel):
    name: str = Field(..., max_length=60)
    code: int
    description: Optional[str] = Field(None, max_length=255)
    isActive: bool = True


class Command(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    commandId: int
    vehicleId: int
    name: str
    code: int
    description: Optional[str] = None
    isActive: bool = True


# ---------- Status ----------
class StatusUpdate(BaseModel):
    vehicleId: int
    commandId: Optional[int] = None
    isConnected: bool = False
    # Optional override for the source field of the resulting history entry
    source: str = Field("MANUAL", max_length=30)


class Status(BaseModel):
    vehicleId: int
    vehicleName: str
    commandId: Optional[int] = None
    commandName: Optional[str] = None
    code: Optional[int] = None
    isConnected: bool
    lastUpdate: Optional[datetime] = None


# ---------- History ----------
class HistoryRegister(BaseModel):
    vehicleId: int
    commandId: Optional[int] = None
    source: str = Field("MANUAL", max_length=30)


class HistoryEntry(BaseModel):
    historyId: int
    vehicleId: int
    commandName: Optional[str] = None
    code: Optional[int] = None
    timestamp: Optional[datetime] = None
    source: str


# ---------- Demos ----------
class DemoCreate(BaseModel):
    vehicleId: int
    name: str = Field(..., max_length=80)
    description: Optional[str] = Field(None, max_length=255)


class DemoUpdate(BaseModel):
    name: str = Field(..., max_length=80)
    description: Optional[str] = Field(None, max_length=255)
    isActive: bool = True


class Demo(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    demoId: int
    vehicleId: int
    name: str
    description: Optional[str] = None
    isActive: bool = True


class DemoMovementCreate(BaseModel):
    demoId: int
    commandId: int
    sortOrder: int
    durationMs: int = Field(..., ge=0)
    pauseMs: int = Field(0, ge=0)


class DemoMovementUpdate(BaseModel):
    commandId: int
    sortOrder: int
    durationMs: int = Field(..., ge=0)
    pauseMs: int = Field(0, ge=0)


class DemoMovement(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    demoMovementId: int
    sortOrder: int
    commandId: int
    commandName: Optional[str] = None
    code: Optional[int] = None
    durationMs: int
    pauseMs: int