"""SQLAlchemy ORM models mirroring the PostgreSQL schema."""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Integer,
    Numeric, String, Text, func, CheckConstraint,
)
from sqlalchemy.orm import relationship

from core.database import Base


class Vendor(Base):
    __tablename__ = "vendors"

    id         = Column(Integer, primary_key=True, index=True)
    name       = Column(String(255), nullable=False)
    contact    = Column(String(255), nullable=False)
    email      = Column(String(255), unique=True)
    phone      = Column(String(50))
    address    = Column(Text)
    rating     = Column(Numeric(2, 1), default=Decimal("3.0"))
    is_active  = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    purchase_orders = relationship("PurchaseOrder", back_populates="vendor")


class Product(Base):
    __tablename__ = "products"

    id              = Column(Integer, primary_key=True, index=True)
    name            = Column(String(255), nullable=False)
    sku             = Column(String(100), unique=True, nullable=False)
    description     = Column(Text)
    category        = Column(String(100))
    unit_price      = Column(Numeric(12, 2), nullable=False)
    stock_level     = Column(Integer, default=0, nullable=False)
    unit_of_measure = Column(String(50), default="UNIT")
    is_active       = Column(Boolean, default=True)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    line_items = relationship("POLineItem", back_populates="product")


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id           = Column(Integer, primary_key=True, index=True)
    reference_no = Column(String(50), unique=True, nullable=False, index=True)
    vendor_id    = Column(Integer, ForeignKey("vendors.id"), nullable=False)
    subtotal     = Column(Numeric(14, 2), default=Decimal("0.00"))
    tax_rate     = Column(Numeric(5, 4), default=Decimal("0.0500"))
    tax_amount   = Column(Numeric(14, 2), default=Decimal("0.00"))
    total_amount = Column(Numeric(14, 2), default=Decimal("0.00"))
    status       = Column(String(50), default="DRAFT")
    notes        = Column(Text)
    created_by   = Column(String(255))
    created_at   = Column(DateTime(timezone=True), server_default=func.now())
    updated_at   = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    vendor     = relationship("Vendor", back_populates="purchase_orders")
    line_items = relationship("POLineItem", back_populates="purchase_order", cascade="all, delete-orphan")


class POLineItem(Base):
    __tablename__ = "po_line_items"

    id         = Column(Integer, primary_key=True, index=True)
    po_id      = Column(Integer, ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity   = Column(Integer, nullable=False)
    unit_price = Column(Numeric(12, 2), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    purchase_order = relationship("PurchaseOrder", back_populates="line_items")
    product        = relationship("Product", back_populates="line_items")

    @property
    def line_total(self) -> Decimal:
        return Decimal(str(self.quantity)) * Decimal(str(self.unit_price))


class AIDescriptionLog(Base):
    __tablename__ = "ai_description_logs"

    id             = Column(Integer, primary_key=True, index=True)
    product_id     = Column(Integer, ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    product_name   = Column(String(255))
    category       = Column(String(100))
    prompt_used    = Column(Text)
    generated_text = Column(Text)
    model_used     = Column(String(100))
    created_at     = Column(DateTime(timezone=True), server_default=func.now())
