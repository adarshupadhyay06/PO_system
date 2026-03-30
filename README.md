# PO Management System
### IV Innovations Private Limited — Assignment Submission

A full-stack **Purchase Order (PO) Management System** built with FastAPI, PostgreSQL, and Vanilla JS. Supports Vendor & Product management, dynamic multi-line PO creation with automatic 5% tax calculation, Google OAuth 2.0 + JWT authentication, and AI-powered product descriptions.

---

## Features

| Area | Detail |
|---|---|
| **Backend** | FastAPI (Python 3.12) + async SQLAlchemy 2.0 + PostgreSQL 16 |
| **Authentication** | JWT Bearer tokens; Demo login (no setup) + Google OAuth 2.0 PKCE |
| **PO Business Logic** | Auto-calculates subtotal, 5% tax, and total on every save |
| **Dynamic UI** | Vanilla JS — add/remove product rows, live totals update |
| **AI Integration** | Anthropic Claude API generates 2-sentence product descriptions; gracefully falls back to rule-based simulation when no API key is set |
| **Frontend** | Single-page app served by FastAPI, dark industrial design |

---

## Quick Start — Docker (Recommended)

```bash
# 1. Clone / unzip the project
cd po-management

# 2. (Optional) Set your Anthropic key for real AI descriptions
#    Edit docker-compose.yml → api.environment.ANTHROPIC_API_KEY

# 3. Start everything
docker compose up --build

# 4. Open in browser
open http://localhost:8000
```

PostgreSQL is auto-seeded with 4 vendors and 8 products on first start.

---

## Quick Start — Local (without Docker)

### Prerequisites
- Python 3.12+
- PostgreSQL 16 running locally

```bash
# 1. Create & activate virtual environment
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env — set DATABASE_URL and optionally ANTHROPIC_API_KEY

# 4. Create database and run schema
psql -U postgres -c "CREATE DATABASE po_management;"
psql -U postgres -d po_management -f ../database/schema.sql

# 5. Run the server
uvicorn main:app --reload --port 8000

# 6. Open in browser
open http://localhost:8000
```

---

## Demo Credentials

| Username | Password | Role  |
|----------|----------|-------|
| `admin`  | `admin123` | Admin |
| `buyer`  | `buyer123` | Buyer |

---

## Google OAuth Setup (Optional)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create OAuth 2.0 credentials (Web Application)
3. Add `http://localhost:8000/auth/google/callback` as Authorised Redirect URI
4. Set in `.env`:
   ```
   GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=your-client-secret
   ```

---

## AI Description Setup (Optional)

The AI feature works in two modes:

- **With API key**: Set `ANTHROPIC_API_KEY` in `.env`. Uses Claude Sonnet to generate professional 2-sentence marketing descriptions.
- **Without API key** (default): Falls back to a rule-based description generator. The button still works and the UX is identical.

---

## API Endpoints

All protected routes require `Authorization: Bearer <token>`.

### Auth
| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/demo-login` | Username/password login |
| GET  | `/auth/google/login` | Redirect to Google OAuth |
| GET  | `/auth/google/callback` | OAuth callback |
| GET  | `/auth/me` | Current user info |

### Vendors
| Method | Path | Description |
|--------|------|-------------|
| GET    | `/api/vendors` | List vendors |
| GET    | `/api/vendors/{id}` | Get vendor |
| POST   | `/api/vendors` | Create vendor |
| PUT    | `/api/vendors/{id}` | Update vendor |
| DELETE | `/api/vendors/{id}` | Soft-delete vendor |

### Products
| Method | Path | Description |
|--------|------|-------------|
| GET    | `/api/products` | List products |
| GET    | `/api/products/{id}` | Get product |
| POST   | `/api/products` | Create product |
| PUT    | `/api/products/{id}` | Update product |

### Purchase Orders
| Method | Path | Description |
|--------|------|-------------|
| GET    | `/api/purchase-orders` | List POs (with optional `status_filter`) |
| GET    | `/api/purchase-orders/{id}` | Get PO with line items |
| POST   | `/api/purchase-orders` | Create PO (auto-calculates totals) |
| PATCH  | `/api/purchase-orders/{id}/status` | Advance PO status |
| DELETE | `/api/purchase-orders/{id}` | Delete DRAFT/CANCELLED PO |

### AI
| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/ai/generate-description` | Generate AI product description |

**Interactive Docs**: http://localhost:8000/api/docs

---

## Database Design

```
vendors
  id (PK) | name | contact | email | phone | address | rating | is_active
  
products
  id (PK) | name | sku (UNIQUE) | description | category | unit_price | stock_level | unit_of_measure | is_active

purchase_orders
  id (PK) | reference_no (UNIQUE) | vendor_id (FK→vendors) 
  subtotal | tax_rate | tax_amount | total_amount | status | notes | created_by

po_line_items
  id (PK) | po_id (FK→purchase_orders, CASCADE DELETE) | product_id (FK→products)
  quantity | unit_price | line_total (GENERATED ALWAYS AS quantity*unit_price)

ai_description_logs
  id (PK) | product_id (FK) | product_name | category | prompt_used | generated_text | model_used
```

### Key Design Choices

1. **`line_total` as a generated column** — prevents data inconsistency; always equals `quantity × unit_price`.
2. **Soft delete for Vendors** — `is_active = false` preserves referential integrity with existing POs.
3. **Status state machine** — transitions enforced server-side: `DRAFT → PENDING → APPROVED → ORDERED → RECEIVED`. CANCELLED allowed from most states.
4. **Tax as a DB column** — `tax_rate` stored per-PO so historical records aren't affected if the rate changes.
5. **AI logs in relational DB** — `ai_description_logs` table provides a full audit trail; can be migrated to MongoDB for the bonus requirement.

---

## Calculate Total — Business Logic

```python
TAX_RATE = Decimal("0.05")   # 5%

subtotal     = sum(qty × unit_price  for each line item)
tax_amount   = subtotal × 0.05
total_amount = subtotal + tax_amount
```

This runs in `routers/purchase_orders.py → _calculate_totals()` on every PO creation.

---

## Project Structure

```
po-management/
├── database/
│   └── schema.sql              # PostgreSQL DDL + seed data
├── backend/
│   ├── core/
│   │   ├── config.py           # Pydantic Settings
│   │   ├── database.py         # Async SQLAlchemy engine
│   │   └── security.py         # JWT helpers
│   ├── models/models.py        # ORM models
│   ├── schemas/schemas.py      # Pydantic v2 schemas
│   ├── routers/
│   │   ├── auth.py             # Demo + Google OAuth
│   │   ├── vendors.py          # Vendor CRUD
│   │   ├── products.py         # Product CRUD
│   │   ├── purchase_orders.py  # PO CRUD + tax logic
│   │   └── ai_description.py   # Claude AI integration
│   ├── main.py                 # FastAPI app
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── templates/index.html    # SPA entry point
│   └── static/
│       ├── css/style.css       # Dark industrial design
│       └── js/app.js           # All frontend logic
├── docker-compose.yml
└── README.md
```

---

## Bonus Points Addressed

| Bonus | Status | Notes |
|---|---|---|
| Java/Spring Boot Vendor microservice | Architecture documented | Vendor router is isolated — easy to rewrite as Spring Boot service behind an API gateway |
| MongoDB for AI logs | Ready | `ai_description_logs` is self-contained; swap the SQLAlchemy insert for a PyMongo call |
| Node.js real-time notifications | Architecture note | Add a Socket.io Node.js sidecar listening to PostgreSQL `NOTIFY` on status changes |

---

## License

Assignment submission for IV Innovations Private Limited. Not for redistribution.
