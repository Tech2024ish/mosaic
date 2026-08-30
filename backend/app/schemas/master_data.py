import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


def clean_code(value: str) -> str:
    value = value.strip().upper()
    if not value:
        raise ValueError("code must not be blank")
    return value


class ProductCreate(BaseModel):
    product_code: str = Field(min_length=1, max_length=200)
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    category: str | None = None
    unit_of_measure: str | None = Field(default=None, max_length=50)
    is_active: bool = True

    @field_validator("product_code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return clean_code(value)


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    category: str | None = None
    unit_of_measure: str | None = Field(default=None, max_length=50)
    is_active: bool | None = None


class ProductResponse(ProductCreate):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class WarehouseCreate(BaseModel):
    warehouse_code: str = Field(min_length=1, max_length=200)
    name: str = Field(min_length=1, max_length=200)
    location: str | None = None
    is_active: bool = True

    @field_validator("warehouse_code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return clean_code(value)


class WarehouseUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    location: str | None = None
    is_active: bool | None = None


class WarehouseResponse(WarehouseCreate):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class SupplierCreate(BaseModel):
    supplier_code: str = Field(min_length=1, max_length=200)
    name: str = Field(min_length=1, max_length=200)
    contact_name: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    is_active: bool = True

    @field_validator("supplier_code")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return clean_code(value)


class SupplierUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    contact_name: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    is_active: bool | None = None


class SupplierResponse(SupplierCreate):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class InventoryCreate(BaseModel):
    product_id: uuid.UUID
    warehouse_id: uuid.UUID
    snapshot_date: date
    quantity_on_hand: Decimal = Field(ge=0)
    unit_cost: Decimal | None = Field(default=None, ge=0)


class InventoryResponse(InventoryCreate):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
