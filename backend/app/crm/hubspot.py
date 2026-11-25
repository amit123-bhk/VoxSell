"""
HubSpot CRM Integration Adapter.

Provides standardized payloads for HubSpot Contacts, Deals, and Engagement Notes APIs.
"""

import logging
from typing import Dict, Any, Optional
import httpx

from app.config import get_settings

logger = logging.getLogger("voxsell.crm.hubspot")
settings = get_settings()


class HubSpotCRMAdapter:
    """
    HTTP client for HubSpot v3 CRM Objects API.
    """

    BASE_URL = "https://api.hubapi.com/crm/v3/objects"

    def __init__(self, access_token: Optional[str] = None):
        self.access_token = access_token or settings.HUBSPOT_ACCESS_TOKEN
        self.client = httpx.AsyncClient(timeout=8.0)

    async def sync_contact(self, email: str, name: str, phone: str, score: int) -> Dict[str, Any]:
        """Upserts a contact in HubSpot."""
        if not self.access_token:
            logger.debug(f"[Simulated HubSpot] Upsert Contact: {name} ({email}) - Score: {score}")
            return {"status": "simulated", "hubspot_id": "hs_sim_12345", "email": email}

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        properties = {
            "email": email,
            "firstname": name.split()[0] if name else "",
            "lastname": name.split()[-1] if name and len(name.split()) > 1 else "",
            "phone": phone,
            "lead_score": str(score),
        }
        try:
            res = await self.client.post(
                f"{self.BASE_URL}/contacts",
                headers=headers,
                json={"properties": properties},
            )
            return res.json()
        except Exception as e:
            logger.warning(f"HubSpot sync error: {e}")
            return {"status": "error", "message": str(e)}

    async def close(self):
        await self.client.aclose()


HubSpotCRM = HubSpotCRMAdapter
