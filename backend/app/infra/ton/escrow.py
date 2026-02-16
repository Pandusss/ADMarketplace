from __future__ import annotations

"""
Escrow-oriented adapter on top of existing TON primitives.
Async-first implementation.
"""

from dataclasses import dataclass
from decimal import Decimal
import hashlib
import logging
from typing import Any, Optional

from app.core.config import settings
from app.infra.ton.checker import ton_checker
from app.infra.ton.sender import ton_sender

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TonEscrowResult:
    success: bool
    tx_hash: str | None = None
    error: str | None = None
    details: dict[str, Any] | None = None


class TonEscrowService:
    """
    Real TON escrow integration.
    """

    def __init__(self) -> None:
        self._checker = ton_checker
        self._sender = ton_sender
        
        # Ensure utf-8 output if possible (legacy reasons)
        try:
            import sys
            if hasattr(sys.stdout, "reconfigure"):
                sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    @staticmethod
    def _deterministic_subwallet_id(deal_id: str) -> int:
        """
        Deterministic, stable subwallet id derived from deal UUID/string id.
        """
        h = hashlib.sha256(deal_id.encode("utf-8")).hexdigest()
        val32 = int(h[:8], 16)
        val31 = val32 & 0x7FFF_FFFF
        return val31 or 1

    def create_escrow(self, deal: dict) -> dict:
        """
        Creates (derives) a unique escrow wallet for a deal and returns its address.
        Deterministic derivation (offline).
        """
        if deal.get("escrow_wallet_id") and deal.get("escrow_address"):
            return {
                "wallet_id": str(deal["escrow_wallet_id"]),
                "address": str(deal["escrow_address"]),
                "network": str(deal.get("escrow_network") or settings.ton_network),
            }

        if not settings.ton_mnemonic:
            raise RuntimeError("TON mnemonic is not configured")

        subwallet_id = self._deterministic_subwallet_id(str(deal["id"]))

        try:
            # We import here to avoid crash if tonutils not installed, though it should be check globally
            from tonutils.client import ToncenterV3Client
            from tonutils.wallet import WalletV4R2
        except ImportError as e:
            raise RuntimeError(f"tonutils is required: {e}") from e

        is_testnet = settings.ton_network == "testnet"
        
        # We need client just for context, usually
        client = ToncenterV3Client(is_testnet=is_testnet)
        try:
            wallet = WalletV4R2.from_mnemonic(
                client,
                settings.ton_mnemonic.strip().split(),
                subwallet_id,
            )
            if isinstance(wallet, tuple):
                wallet = wallet[0]

            addr_obj = getattr(wallet, "address", None)
            if hasattr(addr_obj, "to_str"):
                address = addr_obj.to_str()
            else:
                address = str(addr_obj)
        except Exception as e:
            logger.error(f"Failed to derive escrow wallet for deal {deal['id']}: {e}", exc_info=True)
            raise RuntimeError(f"Failed to derive escrow wallet: {e}") from e
        finally:
            try:
                if hasattr(client, "close"): client.close()
            except: pass

        deal["escrow_wallet_id"] = str(subwallet_id)
        deal["subwallet_id"] = subwallet_id
        deal["escrow_address"] = address
        deal["escrow_network"] = settings.ton_network

        return {"wallet_id": str(subwallet_id), "address": address, "network": settings.ton_network}

    async def check_balance(self, address: str) -> float:
        """
        Native TON balance for address (float TON).
        """
        # improved: use async method
        return await self._checker.get_balance_async(address)

    async def get_last_transaction_hash(self, address: str) -> str | None:
        """
        Get the hash of the last incoming transaction to the address.
        """
        tx = await self._checker._get_last_transaction_async(address)
        if tx and tx.get('hash'):
            return tx['hash']
        return None

    async def release(self, escrow_wallet_id: str, to_address: str, amount_ton: float) -> TonEscrowResult:
        """
        Send TON from escrow wallet to seller wallet.
        """
        try:
            res = await self._sender.send_ton(
                subwallet_id=int(escrow_wallet_id),
                destination=to_address,
                amount=Decimal(str(amount_ton)),
                comment="Deal payout",
            )
            if res and res.get("success"):
                return TonEscrowResult(success=True, tx_hash=res.get("tx_hash"), details=res)
            return TonEscrowResult(success=False, error=(res.get("error") if res else "Unknown error"), details=res)
        except Exception as e:
            return TonEscrowResult(success=False, error=str(e))

    async def refund(self, escrow_wallet_id: str, to_address: str) -> TonEscrowResult:
        """
        Send ENTIRE balance from escrow wallet back to advertiser (refund).
        """
        try:
            res = await self._sender.send_ton(
                subwallet_id=int(escrow_wallet_id),
                destination=to_address,
                amount=Decimal("0"),
                comment="Deal refund (full)",
                send_mode=128,
            )
            if res and res.get("success"):
                return TonEscrowResult(success=True, tx_hash=res.get("tx_hash"), details=res)
            return TonEscrowResult(success=False, error=(res.get("error") if res else "Unknown error"), details=res)
        except Exception as e:
            return TonEscrowResult(success=False, error=str(e))
