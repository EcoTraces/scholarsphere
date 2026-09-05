import json
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services import payment_service
from app.services.payment_provider import PaymentProviderError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/premium/webhooks", tags=["premium-webhooks"])

_SIGNATURE_HEADERS = {"stripe": "Stripe-Signature"}


@router.post("/{provider_name}", status_code=200)
async def receive_webhook(
    provider_name: str,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    """Intentionally unauthenticated (webhooks aren't Firebase-authenticated

    callers) - security instead comes entirely from
    ``verify_webhook_signature`` inside process_webhook_event, over the
    raw, untouched request body. Never derives any success/failure
    outcome from anything except that verified signature plus a live
    server-side read of the event.
    """
    raw_body = await request.body()
    header_name = _SIGNATURE_HEADERS.get(provider_name.lower(), "")
    signature_header = request.headers.get(header_name, "") if header_name else ""
    correlation_id = getattr(request.state, "correlation_id", "webhook")

    try:
        parsed_body = json.loads(raw_body)
    except ValueError as error:
        raise HTTPException(status_code=400, detail="Invalid webhook payload.") from error
    if not isinstance(parsed_body, dict):
        raise HTTPException(status_code=400, detail="Invalid webhook payload.")

    async with session.begin():
        try:
            result = await payment_service.process_webhook_event(
                session,
                provider_name=provider_name.lower(),
                raw_body=raw_body,
                signature_header=signature_header,
                parsed_body=parsed_body,
                correlation_id=correlation_id,
            )
        except PaymentProviderError as error:
            logger.warning("webhook_rejected provider=%s error=%s", provider_name, error)
            raise HTTPException(status_code=400, detail="Webhook could not be verified.") from error

    return {"result": result}
