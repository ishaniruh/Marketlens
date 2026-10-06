"""
MarketLens — AI Business Insights Route (Gemini Integration)

Passes already-computed analytical metrics to Gemini and asks for
structured business observations. The AI does NOT invent numbers —
it interprets data we supply.

If GEMINI_API_KEY is not set, the endpoint returns a mock response
so the rest of the app still works.
"""

import os
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()
logger = logging.getLogger(__name__)


class InsightRequest(BaseModel):
    context: str          # Pre-formatted analytical summary passed from frontend
    ticker: Optional[str] = None
    sector: Optional[str] = None


def _build_prompt(req: InsightRequest) -> str:
    return f"""You are a financial market analyst assistant for the MarketLens platform.

The following analytical metrics have been computed from historical market data:

{req.context}

Based ONLY on the above computed metrics (do not invent any numbers or statistics), please provide:

1. **Key Performance Observations** (2-3 bullet points)
2. **Risk Observations** (2-3 bullet points)
3. **Business / Investment Insight** (1-2 sentences — balanced and nuanced)
4. **Limitations to note** (1 sentence)

Format your response in clean markdown. Keep it concise (under 250 words total).

IMPORTANT: Only reference the metrics provided above. Do not add external financial data or predictions.
End with: "⚠️ AI-generated summary based on computed historical metrics. Not financial advice."
"""


@router.post("/generate")
async def generate_insights(req: InsightRequest):
    """
    Generate AI business insights from pre-computed analytics.

    Pass a context string containing the metrics (e.g., sector return, Sharpe ratio, etc.)
    and Gemini will interpret them in plain English.

    Requires GEMINI_API_KEY environment variable.
    """
    api_key = os.getenv("GEMINI_API_KEY", "")

    if not api_key or api_key == "your_gemini_api_key_here":
        # Return a graceful fallback so the UI still renders
        return {
            "insight": (
                "### AI Insights (Demo Mode)\n\n"
                "**Key Performance Observations**\n"
                "- Historical metrics have been computed from Yahoo Finance data across the selected assets.\n"
                "- Set `GEMINI_API_KEY` in your `.env` file to enable live AI-generated commentary.\n\n"
                "**To enable AI insights:**\n"
                "1. Get a free API key from [Google AI Studio](https://aistudio.google.com/)\n"
                "2. Add `GEMINI_API_KEY=your_key` to your `.env` file\n"
                "3. Restart the backend server\n\n"
                "⚠️ AI-generated summary based on computed historical metrics. Not financial advice."
            ),
            "model":  "demo_mode",
            "status": "api_key_not_configured",
        }

    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-1.5-flash")

        prompt   = _build_prompt(req)
        response = model.generate_content(prompt)
        insight  = response.text

        return {
            "insight": insight,
            "model":   "gemini-1.5-flash",
            "status":  "success",
        }

    except ImportError:
        raise HTTPException(
            status_code=500,
            detail="google-generativeai package not installed. Run: pip install google-generativeai",
        )
    except Exception as e:
        logger.exception("Gemini API call failed")
        raise HTTPException(status_code=500, detail=f"Gemini API error: {str(e)}")
