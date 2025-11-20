"""Pytest configuration and fixtures"""
import pytest
from unittest.mock import MagicMock, AsyncMock


@pytest.fixture
def mock_stripe():
    """Mock Stripe module"""
    mock = MagicMock()
    mock.Customer.create = MagicMock(return_value=MagicMock(id="cus_test123"))
    mock.Subscription.create = MagicMock(return_value=MagicMock(
        id="sub_test123",
        status="active",
        current_period_end=1234567890
    ))
    mock.billing_portal.Session.create = MagicMock(return_value=MagicMock(
        url="https://billing.stripe.com/session/test"
    ))
    return mock


@pytest.fixture
def sample_schema():
    """Sample JSON schema for testing"""
    return {
        "type": "object",
        "properties": {
            "invoice_number": {"type": "string"},
            "total": {"type": "number"},
            "vendor": {"type": "string"}
        },
        "required": ["invoice_number", "total"]
    }


@pytest.fixture
def tenant_id():
    """Test tenant ID"""
    return "test-tenant-123"


@pytest.fixture
def user_id():
    """Test user ID"""
    return "user-456"
