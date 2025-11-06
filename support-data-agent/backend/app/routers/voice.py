"""Voice chat endpoints for OpenAI Realtime API integration.

This module provides endpoints for:
1. Checking voice feature availability (based on OpenAI API key configuration)
2. Generating ephemeral tokens for secure client-side voice connections
"""

from __future__ import annotations

import logging
import os

import httpx
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException

# Load environment variables
load_dotenv()

# Setup logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/voice", tags=["voice"])


@router.get("/available")
async def check_voice_available() -> dict[str, bool]:
    """Check if voice chat feature is available.

    Voice chat requires an OpenAI API key to be configured in the environment.
    This endpoint allows the frontend to determine whether to enable or
    disable the voice features.

    Returns
    -------
    dict
        {"available": true} if OpenAI API key is set, {"available": false} otherwise
    """
    openai_key = os.getenv("OPENAI_API_KEY")
    available = bool(openai_key and openai_key.strip())

    logger.info(f"Voice availability check: {available}")
    return {"available": available}


@router.post("/token")
async def generate_voice_token() -> dict[str, str]:
    """Generate an ephemeral token for OpenAI Realtime API connection.

    This endpoint securely generates ephemeral tokens that the frontend
    can use to establish a WebSocket connection to OpenAI's Realtime API.
    The ephemeral token provides time-limited access without exposing the
    main API key to the client.

    Returns
    -------
    dict
        {"token": "ephemeral_token_value"}

    Raises
    ------
    HTTPException
        503 if OpenAI API key is not configured
        500 if token generation fails
    """
    openai_key = os.getenv("OPENAI_API_KEY")

    if not openai_key or not openai_key.strip():
        logger.error("Voice token requested but OPENAI_API_KEY not configured")
        raise HTTPException(status_code=503, detail="Voice chat is not configured. Please set OPENAI_API_KEY in environment.")

    try:
        logger.info("Generating ephemeral token for voice session")

        # Generate ephemeral token from OpenAI
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/realtime/client_secrets",
                headers={
                    "Authorization": f"Bearer {openai_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "session": {
                        "type": "realtime",
                        "model": "gpt-realtime",
                    },
                },
                timeout=30.0,
            )

            if response.status_code != 200:
                error_text = response.text
                logger.error(f"OpenAI token generation failed: {response.status_code} - {error_text}")
                raise HTTPException(status_code=500, detail=f"Failed to generate voice token: {error_text}")

            data = response.json()
            token = data.get("value")

            if not token:
                logger.error("OpenAI response missing token value")
                raise HTTPException(status_code=500, detail="Token generation response missing value")

            logger.info("Ephemeral token generated successfully")
            return {"token": token}

    except httpx.HTTPError as e:
        logger.error(f"HTTP error during token generation: {e}")
        raise HTTPException(status_code=500, detail=f"Network error generating voice token: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error generating token: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
