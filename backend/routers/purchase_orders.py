"""Purchase Order endpoints with calculate-total business logic."""
from decimal import Decimal
from typing import List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import get_current_user
from models.models import PurchaseOrder, POLineItem, Vendor, Product
from schemas.schemas import POCreate, POOut, POSummary, POUpdate

router = APIRouter(prefix="/purchase-orders", tags=["Purchase Orders"])

TAX_RATE = Decimal("0.05")  # 5%


def _generate_ref_no() -> str:
    """Generate a time-based unique PO reference number."""
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    return f"PO-{ts}"


def _calculate_totals(line_items: list[POLineItem]) -> tuple[Decimal, Decimal, Decimal]:
    """
    Business Logic: Calculate subtotal, tax (5%), and total.
    Returns (subtotal, tax_amount, total_amount).
    """
    subtotal = sum(
        Decimal(str(li.quantity)) * Decimal(str(li.unit_price))
        for li in line_items
    )
    tax_amount = (subtotal * TAX_RATE).quantize(Decimal("0.01"))
    total_amount = subtotal + tax_amount
    return subtotal, tax_amount, total_amount


@router.get("/", response_model=List[POSummary])
async def list_purchase_orders(
    skip: int = 0,
    limit: int = 50,
    status_filter: str | None = None,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    query = (
        select(PurchaseOrder)
        .options(selectinload(PurchaseOrder.vendor))
        .order_by(PurchaseOrder.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    if status_filter:
        query = query.where(PurchaseOrder.status == status_filter.upper())
    result = await db.execute(query)
    pos = result.scalars().all()
    summaries = []
    for po in pos:
        summaries.append(
            POSummary(
                id=po.id,
                reference_no=po.reference_no,
                vendor_id=po.vendor_id,
                vendor_name=po.vendor.name if po.vendor else None,
                total_amount=po.total_amount,
                status=po.status,
                created_at=po.created_at,
            )
        )
    return summaries


@router.get("/{po_id}", response_model=POOut)
async def get_purchase_order(
    po_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    result = await db.execute(
        select(PurchaseOrder)
        .where(PurchaseOrder.id == po_id)
        .options(
            selectinload(PurchaseOrder.vendor),
            selectinload(PurchaseOrder.line_items).selectinload(POLineItem.product),
        )
    )
    po = result.scalar_one_or_none()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase Order not found")
    return _po_to_out(po)


@router.post("/", response_model=POOut, status_code=status.HTTP_201_CREATED)
async def create_purchase_order(
    payload: POCreate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    # Validate vendor
    vendor = await db.get(Vendor, payload.vendor_id)
    if not vendor or not vendor.is_active:
        raise HTTPException(status_code=404, detail="Vendor not found or inactive")

    # Validate products and build line items
    line_items = []
    for li_in in payload.line_items:
        product = await db.get(Product, li_in.product_id)
        if not product or not product.is_active:
            raise HTTPException(
                status_code=404,
                detail=f"Product ID {li_in.product_id} not found or inactive",
            )
        line_items.append(
            POLineItem(
                product_id=li_in.product_id,
                quantity=li_in.quantity,
                unit_price=li_in.unit_price,
            )
        )

    # Business logic: compute totals with 5% tax
    subtotal, tax_amount, total_amount = _calculate_totals(line_items)

    po = PurchaseOrder(
        reference_no=_generate_ref_no(),
        vendor_id=payload.vendor_id,
        subtotal=subtotal,
        tax_rate=TAX_RATE,
        tax_amount=tax_amount,
        total_amount=total_amount,
        status="DRAFT",
        notes=payload.notes,
        created_by=user.get("email", "unknown"),
    )
    db.add(po)
    await db.flush()  # get po.id

    for li in line_items:
        li.po_id = po.id
        db.add(li)

    await db.flush()

    # Reload with relationships
    result = await db.execute(
        select(PurchaseOrder)
        .where(PurchaseOrder.id == po.id)
        .options(
            selectinload(PurchaseOrder.vendor),
            selectinload(PurchaseOrder.line_items).selectinload(POLineItem.product),
        )
    )
    po = result.scalar_one()
    return _po_to_out(po)


@router.patch("/{po_id}/status", response_model=POOut)
async def update_po_status(
    po_id: int,
    payload: POUpdate,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    result = await db.execute(
        select(PurchaseOrder)
        .where(PurchaseOrder.id == po_id)
        .options(
            selectinload(PurchaseOrder.vendor),
            selectinload(PurchaseOrder.line_items).selectinload(POLineItem.product),
        )
    )
    po = result.scalar_one_or_none()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase Order not found")

    allowed_transitions = {
        "DRAFT": ["PENDING", "CANCELLED"],
        "PENDING": ["APPROVED", "CANCELLED"],
        "APPROVED": ["ORDERED", "CANCELLED"],
        "ORDERED": ["RECEIVED"],
        "RECEIVED": [],
        "CANCELLED": [],
    }
    new_status = payload.status.upper() if payload.status else po.status
    if new_status not in allowed_transitions.get(po.status, []) and new_status != po.status:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot transition from {po.status} to {new_status}",
        )
    if payload.status:
        po.status = new_status
    if payload.notes is not None:
        po.notes = payload.notes

    await db.flush()
    await db.refresh(po)
    return _po_to_out(po)


@router.delete("/{po_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_purchase_order(
    po_id: int,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    po = await db.get(PurchaseOrder, po_id)
    if not po:
        raise HTTPException(status_code=404, detail="Purchase Order not found")
    if po.status not in ("DRAFT", "CANCELLED"):
        raise HTTPException(
            status_code=400,
            detail="Only DRAFT or CANCELLED orders can be deleted",
        )
    await db.delete(po)
    await db.flush()


# ── Helper ─────────────────────────────────────────────────────────────────

def _po_to_out(po: PurchaseOrder) -> POOut:
    from schemas.schemas import LineItemOut, ProductOut, VendorOut

    line_items_out = []
    for li in po.line_items:
        line_items_out.append(
            LineItemOut(
                id=li.id,
                product_id=li.product_id,
                quantity=li.quantity,
                unit_price=li.unit_price,
                line_total=Decimal(str(li.quantity)) * Decimal(str(li.unit_price)),
                product=ProductOut.model_validate(li.product) if li.product else None,
            )
        )

    return POOut(
        id=po.id,
        reference_no=po.reference_no,
        vendor_id=po.vendor_id,
        vendor=VendorOut.model_validate(po.vendor) if po.vendor else None,
        subtotal=po.subtotal,
        tax_rate=po.tax_rate,
        tax_amount=po.tax_amount,
        total_amount=po.total_amount,
        status=po.status,
        notes=po.notes,
        created_by=po.created_by,
        line_items=line_items_out,
        created_at=po.created_at,
        updated_at=po.updated_at,
    )
