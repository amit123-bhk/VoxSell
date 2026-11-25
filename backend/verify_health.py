"""
Standalone verification script to test VoxSell configuration and health endpoint.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from app.api.health import health_check
from app.config import get_settings


def main() -> None:
    settings = get_settings()
    print(f"[*] Configuration Loaded: {settings.APP_NAME} ({settings.APP_ENV})")
    print(f"[*] Target LLM: {settings.LLM_PROVIDER} ({settings.LLM_MODEL})")
    print(f"[*] Target TTS: {settings.TTS_PROVIDER} ({settings.TTS_VOICE_ID})")

    res = asyncio.run(health_check())
    print(f"[*] Health Check Response: {res}")
    assert res["status"] == "ok"
    assert res["app"] == "VoxSell"
    print("\n[SUCCESS] /health endpoint returned 200 OK.")


if __name__ == "__main__":
    main()
