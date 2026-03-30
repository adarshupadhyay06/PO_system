import sys
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from core.config import settings
from routers import auth, vendors, products, purchase_orders, ai_description

app = FastAPI(title="PO Management System", docs_url="/api/docs", redoc_url="/api/redoc")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

FRONTEND_DIR = BASE_DIR.parent / "frontend"
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(FRONTEND_DIR / "templates"))

app.include_router(auth.router)
app.include_router(vendors.router,         prefix="/api")
app.include_router(products.router,        prefix="/api")
app.include_router(purchase_orders.router, prefix="/api")
app.include_router(ai_description.router,  prefix="/api")

@app.get("/", include_in_schema=False)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html")

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return HTMLResponse("")