-- ============================================================
-- PO Management System - PostgreSQL Schema
-- ============================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- VENDORS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS vendors (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(255) NOT NULL,
    contact     VARCHAR(255) NOT NULL,
    email       VARCHAR(255) UNIQUE,
    phone       VARCHAR(50),
    address     TEXT,
    rating      NUMERIC(2,1) CHECK (rating >= 1.0 AND rating <= 5.0) DEFAULT 3.0,
    is_active   BOOLEAN DEFAULT TRUE,
    created_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================
-- PRODUCTS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS products (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(255) NOT NULL,
    sku             VARCHAR(100) UNIQUE NOT NULL,
    description     TEXT,
    category        VARCHAR(100),
    unit_price      NUMERIC(12,2) NOT NULL CHECK (unit_price >= 0),
    stock_level     INTEGER NOT NULL DEFAULT 0 CHECK (stock_level >= 0),
    unit_of_measure VARCHAR(50) DEFAULT 'UNIT',
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================
-- PURCHASE ORDERS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS purchase_orders (
    id              SERIAL PRIMARY KEY,
    reference_no    VARCHAR(50) UNIQUE NOT NULL,
    vendor_id       INTEGER NOT NULL REFERENCES vendors(id) ON DELETE RESTRICT,
    subtotal        NUMERIC(14,2) NOT NULL DEFAULT 0.00,
    tax_rate        NUMERIC(5,4) NOT NULL DEFAULT 0.0500,   -- 5% tax
    tax_amount      NUMERIC(14,2) NOT NULL DEFAULT 0.00,
    total_amount    NUMERIC(14,2) NOT NULL DEFAULT 0.00,
    status          VARCHAR(50) NOT NULL DEFAULT 'DRAFT'
                        CHECK (status IN ('DRAFT','PENDING','APPROVED','ORDERED','RECEIVED','CANCELLED')),
    notes           TEXT,
    created_by      VARCHAR(255),
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================
-- PURCHASE ORDER LINE ITEMS TABLE
-- ============================================================
CREATE TABLE IF NOT EXISTS po_line_items (
    id              SERIAL PRIMARY KEY,
    po_id           INTEGER NOT NULL REFERENCES purchase_orders(id) ON DELETE CASCADE,
    product_id      INTEGER NOT NULL REFERENCES products(id) ON DELETE RESTRICT,
    quantity        INTEGER NOT NULL CHECK (quantity > 0),
    unit_price      NUMERIC(12,2) NOT NULL CHECK (unit_price >= 0),
    line_total      NUMERIC(14,2) GENERATED ALWAYS AS (quantity * unit_price) STORED,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================
-- AI DESCRIPTIONS LOG TABLE (for GenAI audit trail)
-- ============================================================
CREATE TABLE IF NOT EXISTS ai_description_logs (
    id              SERIAL PRIMARY KEY,
    product_id      INTEGER REFERENCES products(id) ON DELETE SET NULL,
    product_name    VARCHAR(255),
    category        VARCHAR(100),
    prompt_used     TEXT,
    generated_text  TEXT,
    model_used      VARCHAR(100),
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================
-- INDEXES
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_po_vendor    ON purchase_orders(vendor_id);
CREATE INDEX IF NOT EXISTS idx_po_status    ON purchase_orders(status);
CREATE INDEX IF NOT EXISTS idx_po_ref       ON purchase_orders(reference_no);
CREATE INDEX IF NOT EXISTS idx_li_po        ON po_line_items(po_id);
CREATE INDEX IF NOT EXISTS idx_li_product   ON po_line_items(product_id);
CREATE INDEX IF NOT EXISTS idx_prod_sku     ON products(sku);

-- ============================================================
-- AUTO-UPDATE updated_at TRIGGER
-- ============================================================
CREATE OR REPLACE FUNCTION update_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_vendors_updated
    BEFORE UPDATE ON vendors
    FOR EACH ROW EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER trg_products_updated
    BEFORE UPDATE ON products
    FOR EACH ROW EXECUTE FUNCTION update_timestamp();

CREATE TRIGGER trg_po_updated
    BEFORE UPDATE ON purchase_orders
    FOR EACH ROW EXECUTE FUNCTION update_timestamp();

-- ============================================================
-- SEED DATA
-- ============================================================
INSERT INTO vendors (name, contact, email, phone, rating) VALUES
    ('TechSource Pvt Ltd',    'Ravi Kumar',   'ravi@techsource.in',    '+91-9876543210', 4.5),
    ('Global Supply Co.',     'Priya Sharma', 'priya@globalsupply.in', '+91-9123456789', 3.8),
    ('FastTrack Distributors','Amit Singh',   'amit@fasttrack.in',     '+91-9012345678', 4.2),
    ('Prime Vendors Inc.',    'Neha Gupta',   'neha@primevendors.in',  '+91-8901234567', 4.7)
ON CONFLICT DO NOTHING;

INSERT INTO products (name, sku, category, unit_price, stock_level, unit_of_measure) VALUES
    ('Dell Laptop 15"',        'DELL-LAP-001', 'Electronics',  75000.00, 50,  'UNIT'),
    ('HP Wireless Mouse',      'HP-MSE-002',   'Peripherals',    850.00, 200, 'UNIT'),
    ('Samsung 24" Monitor',    'SAM-MON-003',  'Electronics',  18500.00, 30,  'UNIT'),
    ('Logitech Keyboard',      'LOG-KB-004',   'Peripherals',   2200.00, 150, 'UNIT'),
    ('A4 Printing Paper (Rm)', 'PPR-A4-005',   'Stationery',    350.00, 500, 'REAM'),
    ('UPS 1KVA',               'UPS-1K-006',   'Electronics',   6500.00, 20,  'UNIT'),
    ('Cat6 LAN Cable 50m',     'CAB-LAN-007',  'Networking',    1200.00, 100, 'ROLL'),
    ('Office Chair Ergonomic', 'CHR-ERG-008',  'Furniture',    12000.00, 25,  'UNIT')
ON CONFLICT DO NOTHING;
