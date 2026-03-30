"""AI auto-description endpoint using Anthropic Claude."""
import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import get_db
from core.security import get_current_user
from models.models import AIDescriptionLog
from schemas.schemas import AIDescriptionRequest, AIDescriptionResponse

router = APIRouter(prefix="/ai", tags=["AI"])

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
MODEL = "claude-sonnet-4-20250514"


def _build_prompt(name: str, category: str | None) -> str:
    cat_str = f" in the {category} category" if category else ""
    return (
        f"Write exactly 2 professional marketing sentences for a B2B product called '{name}'{cat_str}. "
        "The description should highlight its quality, utility in a business context, and value proposition. "
        "Do NOT use bullet points. Return only the 2 sentences, nothing else."
    )


@router.post("/generate-description", response_model=AIDescriptionResponse)
async def generate_description(
    payload: AIDescriptionRequest,
    db: AsyncSession = Depends(get_db),
    _user: dict = Depends(get_current_user),
):
    prompt = _build_prompt(payload.product_name, payload.category)
    description = ""
    model_used = MODEL

    if settings.ANTHROPIC_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    ANTHROPIC_URL,
                    headers={
                        "x-api-key": settings.ANTHROPIC_API_KEY,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": MODEL,
                        "max_tokens": 200,
                        "messages": [{"role": "user", "content": prompt}],
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                description = data["content"][0]["text"].strip()
        except Exception as exc:
            # Fallback to simulated description
            description = _simulate_description(payload.product_name, payload.category)
            model_used = "simulated-fallback"
    else:
        # Simulated mode when no API key is configured
        description = _simulate_description(payload.product_name, payload.category)
        model_used = "simulated"

    # Log to DB (audit trail)
    log = AIDescriptionLog(
        product_id=payload.product_id,
        product_name=payload.product_name,
        category=payload.category,
        prompt_used=prompt,
        generated_text=description,
        model_used=model_used,
    )
    db.add(log)

    return AIDescriptionResponse(description=description, model_used=model_used)


def _simulate_description(name: str, category: str | None) -> str:
    """Rule-based fallback that generates a sensible placeholder description."""
    cat = category or "business"
    return (
        f"The {name} is a premium {cat.lower()} solution engineered to maximize productivity "
        f"and streamline operations for modern enterprises. "
        f"Trusted by procurement teams worldwide, it delivers exceptional reliability, "
        f"seamless integration, and outstanding value at every scale."
    )
