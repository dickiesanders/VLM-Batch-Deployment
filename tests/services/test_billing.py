"""Tests for billing service"""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from api.services.billing import BillingManager, Plan


class TestBillingManager:
    """Test billing manager functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mock_stripe = MagicMock()

        with patch('api.services.billing.stripe', self.mock_stripe):
            self.manager = BillingManager("sk_test_123")

    @pytest.mark.asyncio
    async def test_create_customer(self):
        """Test creating a Stripe customer"""
        self.mock_stripe.Customer.create.return_value = MagicMock(id="cus_test123")

        customer_id = await self.manager.create_customer(
            tenant_id="tenant-123",
            email="test@example.com",
            name="Test User"
        )

        assert customer_id == "cus_test123"
        self.mock_stripe.Customer.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_customer_with_metadata(self):
        """Test creating customer with metadata"""
        self.mock_stripe.Customer.create.return_value = MagicMock(id="cus_meta")

        await self.manager.create_customer(
            tenant_id="tenant-456",
            email="meta@example.com",
            name="Meta User",
            metadata={"company": "Test Corp"}
        )

        call_args = self.mock_stripe.Customer.create.call_args
        assert "metadata" in call_args.kwargs

    @pytest.mark.asyncio
    async def test_create_subscription(self):
        """Test creating a subscription"""
        mock_sub = MagicMock()
        mock_sub.id = "sub_test123"
        mock_sub.status = "active"
        mock_sub.current_period_end = 1234567890
        mock_sub.items.data = [MagicMock(id="si_item123")]

        self.mock_stripe.Subscription.create.return_value = mock_sub

        result = await self.manager.create_subscription(
            customer_id="cus_test123",
            plan=Plan.STARTER
        )

        assert result["subscription_id"] == "sub_test123"
        assert result["status"] == "active"

    @pytest.mark.asyncio
    async def test_report_usage(self):
        """Test reporting usage"""
        self.mock_stripe.SubscriptionItem.create_usage_record.return_value = MagicMock(
            id="mbur_123",
            quantity=100
        )

        result = await self.manager.report_usage(
            subscription_item_id="si_item123",
            quantity=100
        )

        assert result["quantity"] == 100
        self.mock_stripe.SubscriptionItem.create_usage_record.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_portal_session(self):
        """Test creating billing portal session"""
        self.mock_stripe.billing_portal.Session.create.return_value = MagicMock(
            url="https://billing.stripe.com/session/test"
        )

        url = await self.manager.create_portal_session(
            customer_id="cus_test123",
            return_url="https://app.example.com/billing"
        )

        assert "billing.stripe.com" in url

    @pytest.mark.asyncio
    async def test_cancel_subscription(self):
        """Test canceling subscription"""
        mock_sub = MagicMock()
        mock_sub.id = "sub_cancel"
        mock_sub.status = "active"
        mock_sub.cancel_at_period_end = True

        self.mock_stripe.Subscription.modify.return_value = mock_sub

        result = await self.manager.cancel_subscription(
            subscription_id="sub_cancel",
            at_period_end=True
        )

        assert result["cancel_at_period_end"] is True

    @pytest.mark.asyncio
    async def test_cancel_subscription_immediately(self):
        """Test canceling subscription immediately"""
        mock_sub = MagicMock()
        mock_sub.id = "sub_cancel_now"
        mock_sub.status = "canceled"

        self.mock_stripe.Subscription.delete.return_value = mock_sub

        result = await self.manager.cancel_subscription(
            subscription_id="sub_cancel_now",
            at_period_end=False
        )

        assert result["status"] == "canceled"

    @pytest.mark.asyncio
    async def test_get_invoices(self):
        """Test getting invoices"""
        mock_invoice = MagicMock()
        mock_invoice.id = "inv_123"
        mock_invoice.amount_due = 5000
        mock_invoice.status = "paid"
        mock_invoice.created = 1234567890
        mock_invoice.hosted_invoice_url = "https://invoice.stripe.com/i/test"

        self.mock_stripe.Invoice.list.return_value = MagicMock(
            data=[mock_invoice]
        )

        invoices = await self.manager.get_invoices(
            customer_id="cus_test123",
            limit=10
        )

        assert len(invoices) == 1
        assert invoices[0]["id"] == "inv_123"
        assert invoices[0]["amount_due"] == 5000

    def test_plan_enum(self):
        """Test plan enum values"""
        assert Plan.FREE.value == "free"
        assert Plan.STARTER.value == "starter"
        assert Plan.PROFESSIONAL.value == "professional"
        assert Plan.ENTERPRISE.value == "enterprise"
