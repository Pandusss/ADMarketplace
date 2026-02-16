"""
TON webhook processing router.
Receives transaction notifications from TonCenter,
checks the escrow sub-wallet balance and transitions the deal to funded status.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Request, Response

from app.db.session import SessionLocal
from app.db.models.deal import Deal, DealStatus
from app.domain.deals.state_machine import BALANCE_TOLERANCE_TON
from app.domain.deals.mappers import deal_to_dict, apply_deal_dict
from app.domain.deals.service import transition
from app.infra.ton.escrow import TonEscrowService
from app.infra.ton.webhook_manager import ton_webhook_manager
from app.infra.events import bus as signals

logger = logging.getLogger(__name__)

router = APIRouter()

escrow_service = TonEscrowService()


@router.post("/ton")
async def ton_webhook(request: Request) -> Response:
    body = await request.json()
    account_id: str = body.get("account_id", "")
    tx_hash: str = body.get("tx_hash", "")
    lt: int = body.get("lt", 0)

    logger.info("TON webhook: account=%s tx=%s lt=%s", account_id, tx_hash, lt)

    db = SessionLocal()
    try:
        deals = (
            db.query(Deal)
            .filter(
                Deal.status == DealStatus.pending_payment.value,
                Deal.escrow_address.isnot(None),
            )
            .all()
        )

        matched_deal: Deal | None = None
        for deal in deals:
            raw = await _resolve_raw(str(deal.escrow_address))
            if raw == account_id:
                matched_deal = deal
                break

        if not matched_deal:
            logger.debug("No pending deal for account %s", account_id)
            return Response(status_code=200)

        balance = await escrow_service.check_balance(str(matched_deal.escrow_address))
        expected = float(matched_deal.expected_amount_ton or matched_deal.price_ton or 0)

        if balance < (expected - BALANCE_TOLERANCE_TON):
            logger.info("Balance %.4f < expected %.4f for deal %s", balance, expected, matched_deal.id)
            return Response(status_code=200)

        res = await transition(
            deal=deal_to_dict(matched_deal),
            action="confirm_payment",
            actor="advertiser",
            escrow=escrow_service,
        )

        apply_deal_dict(matched_deal, res.deal)
        if tx_hash:
            matched_deal.payment_tx_hash = tx_hash
        db.commit()

        await signals.deal_updated.emit(
            signals.DealEvent(deal_id=matched_deal.id, actor_id="system", event_type="payment_confirmed")
        )

        await ton_webhook_manager.unsubscribe_account(str(matched_deal.escrow_address))

        logger.info("Payment confirmed via webhook for deal %s", matched_deal.id)
    except Exception:
        logger.error("Error processing TON webhook", exc_info=True)
    finally:
        db.close()

    return Response(status_code=200)


async def _resolve_raw(address: str) -> str:
    return await ton_webhook_manager._to_raw_address(address)
