"""Stripe billing integration for usage-based pricing"""
import logging
import os
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# Stripe integration
try:
    import stripe
    HAS_STRIPE = True
except ImportError:
    HAS_STRIPE = False
    logger.warning("Stripe not installed. Billing features disabled.")


class BillingManager:
    """Manage Stripe billing and usage tracking"""

    def __init__(self, api_key: Optional[str] = None):
        if not HAS_STRIPE:
            raise RuntimeError("Stripe package required for billing")

        self.api_key = api_key or os.getenv("STRIPE_API_KEY")
        if self.api_key:
            stripe.api_key = self.api_key

        # Price IDs for different plans
        self.prices = {
            "free": None,
            "starter": os.getenv("STRIPE_PRICE_STARTER"),
            "pro": os.getenv("STRIPE_PRICE_PRO"),
            "enterprise": os.getenv("STRIPE_PRICE_ENTERPRISE"),
        }

        # Metered usage price ID
        self.usage_price_id = os.getenv("STRIPE_PRICE_USAGE")

    async def create_customer(
        self,
        tenant_id: str,
        email: str,
        name: str,
        metadata: Optional[dict] = None,
    ) -> str:
        """Create a Stripe customer for a tenant"""
        customer = stripe.Customer.create(
            email=email,
            name=name,
            metadata={
                "tenant_id": tenant_id,
                **(metadata or {}),
            },
        )
        logger.info(f"Created Stripe customer {customer.id} for tenant {tenant_id}")
        return customer.id

    async def create_subscription(
        self,
        customer_id: str,
        plan: str,
    ) -> dict:
        """Create a subscription for a customer"""
        price_id = self.prices.get(plan)
        if not price_id and plan != "free":
            raise ValueError(f"Unknown plan: {plan}")

        items = []

        # Base plan subscription
        if price_id:
            items.append({"price": price_id})

        # Add metered usage item
        if self.usage_price_id:
            items.append({"price": self.usage_price_id})

        if not items:
            return {"status": "free", "plan": "free"}

        subscription = stripe.Subscription.create(
            customer=customer_id,
            items=items,
            payment_behavior="default_incomplete",
            expand=["latest_invoice.payment_intent"],
        )

        return {
            "subscription_id": subscription.id,
            "status": subscription.status,
            "client_secret": subscription.latest_invoice.payment_intent.client_secret
            if subscription.latest_invoice.payment_intent
            else None,
        }

    async def report_usage(
        self,
        subscription_item_id: str,
        quantity: int,
        timestamp: Optional[int] = None,
        action: str = "increment",
    ) -> dict:
        """Report metered usage to Stripe"""
        usage_record = stripe.SubscriptionItem.create_usage_record(
            subscription_item_id,
            quantity=quantity,
            timestamp=timestamp or int(datetime.utcnow().timestamp()),
            action=action,
        )
        return {
            "id": usage_record.id,
            "quantity": usage_record.quantity,
            "timestamp": usage_record.timestamp,
        }

    async def get_usage_summary(
        self,
        subscription_item_id: str,
    ) -> dict:
        """Get usage summary for current billing period"""
        summary = stripe.SubscriptionItem.list_usage_record_summaries(
            subscription_item_id,
            limit=1,
        )
        if summary.data:
            return {
                "total_usage": summary.data[0].total_usage,
                "period_start": summary.data[0].period.start,
                "period_end": summary.data[0].period.end,
            }
        return {"total_usage": 0}

    async def create_portal_session(
        self,
        customer_id: str,
        return_url: str,
    ) -> str:
        """Create a Stripe billing portal session"""
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url,
        )
        return session.url

    async def create_checkout_session(
        self,
        customer_id: str,
        price_id: str,
        success_url: str,
        cancel_url: str,
    ) -> str:
        """Create a Stripe checkout session"""
        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=["card"],
            line_items=[{"price": price_id, "quantity": 1}],
            mode="subscription",
            success_url=success_url,
            cancel_url=cancel_url,
        )
        return session.url

    async def cancel_subscription(
        self,
        subscription_id: str,
        at_period_end: bool = True,
    ) -> dict:
        """Cancel a subscription"""
        subscription = stripe.Subscription.modify(
            subscription_id,
            cancel_at_period_end=at_period_end,
        )
        return {
            "subscription_id": subscription.id,
            "status": subscription.status,
            "cancel_at_period_end": subscription.cancel_at_period_end,
        }

    async def get_invoices(
        self,
        customer_id: str,
        limit: int = 10,
    ) -> list:
        """Get customer invoices"""
        invoices = stripe.Invoice.list(customer=customer_id, limit=limit)
        return [
            {
                "id": inv.id,
                "amount_due": inv.amount_due,
                "amount_paid": inv.amount_paid,
                "status": inv.status,
                "created": inv.created,
                "invoice_pdf": inv.invoice_pdf,
            }
            for inv in invoices.data
        ]


# Global billing manager
_billing: Optional[BillingManager] = None


def get_billing_manager() -> Optional[BillingManager]:
    return _billing


def initialize_billing(api_key: Optional[str] = None) -> BillingManager:
    global _billing
    if HAS_STRIPE:
        _billing = BillingManager(api_key)
        logger.info("Billing manager initialized")
    return _billing
