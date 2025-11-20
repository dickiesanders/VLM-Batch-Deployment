"""Billing routes for Stripe integration"""
import os
from fastapi import APIRouter, HTTPException, Header, Request
from pydantic import BaseModel
from typing import Optional

from api.services.billing import get_billing_manager

router = APIRouter(prefix="/billing", tags=["billing"])


class CreateCustomerRequest(BaseModel):
    email: str
    name: str


class CreateSubscriptionRequest(BaseModel):
    customer_id: str
    plan: str  # free, starter, pro, enterprise


class PortalRequest(BaseModel):
    customer_id: str
    return_url: str


async def get_tenant_id(x_api_key: str = Header(...)) -> str:
    if ":" in x_api_key:
        return x_api_key.split(":")[0]
    return "default-tenant"


@router.post("/customers")
async def create_customer(
    request: CreateCustomerRequest,
    x_api_key: str = Header(...),
):
    """Create a Stripe customer"""
    billing = get_billing_manager()
    if not billing:
        raise HTTPException(status_code=501, detail="Billing not configured")

    tenant_id = await get_tenant_id(x_api_key)

    customer_id = await billing.create_customer(
        tenant_id=tenant_id,
        email=request.email,
        name=request.name,
    )

    return {"customer_id": customer_id}


@router.post("/subscriptions")
async def create_subscription(request: CreateSubscriptionRequest):
    """Create a subscription"""
    billing = get_billing_manager()
    if not billing:
        raise HTTPException(status_code=501, detail="Billing not configured")

    result = await billing.create_subscription(
        customer_id=request.customer_id,
        plan=request.plan,
    )

    return result


@router.post("/portal")
async def create_portal_session(request: PortalRequest):
    """Create a billing portal session for customer self-service"""
    billing = get_billing_manager()
    if not billing:
        raise HTTPException(status_code=501, detail="Billing not configured")

    url = await billing.create_portal_session(
        customer_id=request.customer_id,
        return_url=request.return_url,
    )

    return {"url": url}


@router.get("/invoices/{customer_id}")
async def get_invoices(customer_id: str, limit: int = 10):
    """Get customer invoices"""
    billing = get_billing_manager()
    if not billing:
        raise HTTPException(status_code=501, detail="Billing not configured")

    invoices = await billing.get_invoices(customer_id, limit)
    return {"invoices": invoices}


@router.post("/subscriptions/{subscription_id}/cancel")
async def cancel_subscription(
    subscription_id: str,
    at_period_end: bool = True,
):
    """Cancel a subscription"""
    billing = get_billing_manager()
    if not billing:
        raise HTTPException(status_code=501, detail="Billing not configured")

    result = await billing.cancel_subscription(subscription_id, at_period_end)
    return result


@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe webhooks"""
    import stripe

    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Handle events
    if event.type == "invoice.paid":
        # Handle successful payment
        pass
    elif event.type == "invoice.payment_failed":
        # Handle failed payment
        pass
    elif event.type == "customer.subscription.deleted":
        # Handle subscription cancellation
        pass

    return {"received": True}
