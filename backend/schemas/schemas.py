"""Pydantic v2 request/response schemas."""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field, field_validator


# ── Vendor ────────────────────────────────────────────────────

class VendorBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    contact: str = Field(..., min_length=2, max_length=255)
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    rating: Optional[float] = Field(default=3.0, ge=1.0, le=5.0)
    is_active: bool = True


class VendorCreate(VendorBase):
    pass


class VendorUpdate(BaseModel):
    name: Optional[str] = None
    contact: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    rating: Optional[float] = Field(default=None, ge=1.0, le=5.0)
    is_active: Optional[bool] = None


class VendorOut(VendorBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Product ───────────────────────────────────────────────────

class ProductBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    sku: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None
    category: Optional[str] = None
    unit_price: Decimal = Field(..., ge=0)
    stock_level: int = Field(default=0, ge=0)
    unit_of_measure: str = "UNIT"
    is_active: bool = True


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    unit_price: Optional[Decimal] = Field(default=None, ge=0)
    stock_level: Optional[int] = Field(default=None, ge=0)
    unit_of_measure: Optional[str] = None
    is_active: Optional[bool] = None


class ProductOut(ProductBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Line Items ────────────────────────────────────────────────

class LineItemIn(BaseModel):
    product_id: int
    quantity: int = Field(..., gt=0)
    unit_price: Decimal = Field(..., ge=0)


class LineItemOut(BaseModel):
    id: int
    product_id: int
    quantity: int
    unit_price: Decimal
    line_total: Decimal
    product: Optional[ProductOut] = None

    model_config = {"from_attributes": True}


# ── Purchase Order ────────────────────────────────────────────

class POCreate(BaseModel):
    vendor_id: int
    notes: Optional[str] = None
    line_items: List[LineItemIn] = Field(..., min_length=1)


class POUpdate(BaseModel):
    status: Optional[str] = None
    notes: Optional[str] = None


class POOut(BaseModel):
    id: int
    reference_no: str
    vendor_id: int
    vendor: Optional[VendorOut] = None
    subtotal: Decimal
    tax_rate: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    status: str
    notes: Optional[str] = None
    created_by: Optional[str] = None
    line_items: List[LineItemOut] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class POSummary(BaseModel):
    id: int
    reference_no: str
    vendor_id: int
    vendor_name: Optional[str] = None
    total_amount: Decimal
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── AI Description ────────────────────────────────────────────

class AIDescriptionRequest(BaseModel):
    product_id: Optional[int] = None
    product_name: str
    category: Optional[str] = None


class AIDescriptionResponse(BaseModel):
    description: str
    model_used: str


# ── Auth ──────────────────────────────────────────────────────

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class DemoLoginRequest(BaseModel):
    username: str
    password: str
