from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

TONAPI_WEBHOOK_BASE = "https://rt.tonapi.io"
TONAPI_WEBHOOK_BASE_TESTNET = "https://rt-testnet.tonapi.io"


class TonWebhookManager:
    def __init__(self) -> None:
        self._api_key = settings.ton_api_key
        self._is_testnet = settings.ton_network == "testnet"
        self._base = TONAPI_WEBHOOK_BASE_TESTNET if self._is_testnet else TONAPI_WEBHOOK_BASE
        self._headers = {"Authorization": f"Bearer {self._api_key}"}
        self._webhook_id: int | None = None

    async def ensure_webhook(self, endpoint_url: str) -> int:
        if self._webhook_id is not None:
            return self._webhook_id

        existing = await self._list_webhooks()
        for wh in existing:
            if wh.get("endpoint") == endpoint_url:
                self._webhook_id = wh["id"]
                logger.info("Reusing existing TON webhook id=%s", self._webhook_id)
                return self._webhook_id

        self._webhook_id = await self._create_webhook(endpoint_url)
        logger.info("Created new TON webhook id=%s endpoint=%s", self._webhook_id, endpoint_url)
        return self._webhook_id

    async def subscribe_account(self, address: str) -> None:
        if self._webhook_id is None:
            raise RuntimeError("Webhook not initialised. Call ensure_webhook first.")
        raw_address = await self._to_raw_address(address)
        url = f"{self._base}/webhooks/{self._webhook_id}/account-tx/subscribe"
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, headers=self._headers, json={"accounts": [{"account_id": raw_address}]})
        if resp.status_code not in (200, 201):
            logger.error("Failed to subscribe %s: %s %s", address, resp.status_code, resp.text)
        else:
            logger.info("Subscribed to account tx: %s (raw: %s)", address, raw_address)

    async def unsubscribe_account(self, address: str) -> None:
        if self._webhook_id is None:
            return
        raw_address = await self._to_raw_address(address)
        url = f"{self._base}/webhooks/{self._webhook_id}/account-tx/unsubscribe"
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, headers=self._headers, json={"accounts": [raw_address]})
        if resp.status_code not in (200, 201):
            logger.warning("Failed to unsubscribe %s: %s", address, resp.text)

    async def _list_webhooks(self) -> list[dict[str, Any]]:
        url = f"{self._base}/webhooks"
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=self._headers)
        if resp.status_code == 200:
            return resp.json().get("webhooks", [])
        return []

    async def _create_webhook(self, endpoint_url: str) -> int:
        url = f"{self._base}/webhooks"
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, headers=self._headers, json={"endpoint": endpoint_url})
        resp.raise_for_status()
        return resp.json()["webhook_id"]

    async def _to_raw_address(self, address: str) -> str:
        if address.startswith("0:") or address.startswith("-1:"):
            return address
        api_url = settings.ton_api_url
        url = f"{api_url}/address/{address}/parse"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=self._headers)
        if resp.status_code == 200:
            data = resp.json()
            return data.get("raw_form", address)
        logger.warning("Could not parse address %s, using as-is", address)
        return address


ton_webhook_manager = TonWebhookManager()
