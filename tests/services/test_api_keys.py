"""Tests for API key management service"""
import pytest
from datetime import datetime, timedelta

from api.services.api_keys import APIKeyManager, KeyScope


class TestAPIKeyManager:
    """Test API key manager functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        self.manager = APIKeyManager()
        self.tenant_id = "test-tenant"

    def test_generate_key(self):
        """Test generating a new API key"""
        plaintext, api_key = self.manager.generate_key(
            tenant_id=self.tenant_id,
            name="test-key",
            scopes=[KeyScope.READ, KeyScope.WRITE]
        )

        assert plaintext is not None
        assert len(plaintext) > 20
        assert api_key.name == "test-key"
        assert api_key.tenant_id == self.tenant_id
        assert KeyScope.READ in api_key.scopes
        assert KeyScope.WRITE in api_key.scopes
        assert api_key.is_active is True

    def test_generate_key_with_expiry(self):
        """Test generating key with expiration"""
        plaintext, api_key = self.manager.generate_key(
            tenant_id=self.tenant_id,
            name="expiring-key",
            scopes=[KeyScope.READ],
            expires_days=30
        )

        assert api_key.expires_at is not None
        assert api_key.expires_at > datetime.utcnow()

    def test_validate_key(self):
        """Test validating a key"""
        plaintext, api_key = self.manager.generate_key(
            tenant_id=self.tenant_id,
            name="validate-test",
            scopes=[KeyScope.READ]
        )

        validated = self.manager.validate_key(plaintext)
        assert validated is not None
        assert validated.id == api_key.id
        assert validated.last_used_at is not None

    def test_validate_invalid_key(self):
        """Test validating an invalid key"""
        result = self.manager.validate_key("invalid-key-12345")
        assert result is None

    def test_rotate_key(self):
        """Test rotating a key"""
        plaintext, api_key = self.manager.generate_key(
            tenant_id=self.tenant_id,
            name="rotate-test",
            scopes=[KeyScope.READ, KeyScope.WRITE]
        )

        result = self.manager.rotate_key(api_key.id, self.tenant_id)
        assert result is not None

        new_plaintext, new_key = result
        assert new_plaintext != plaintext
        assert new_key.id != api_key.id
        assert new_key.name == api_key.name
        assert new_key.scopes == api_key.scopes

        # Old key should be revoked
        old_key = self.manager.get_key(api_key.id, self.tenant_id)
        assert old_key.is_active is False

    def test_revoke_key(self):
        """Test revoking a key"""
        plaintext, api_key = self.manager.generate_key(
            tenant_id=self.tenant_id,
            name="revoke-test",
            scopes=[KeyScope.READ]
        )

        success = self.manager.revoke_key(api_key.id, self.tenant_id)
        assert success is True

        key = self.manager.get_key(api_key.id, self.tenant_id)
        assert key.is_active is False

    def test_update_scopes(self):
        """Test updating key scopes"""
        plaintext, api_key = self.manager.generate_key(
            tenant_id=self.tenant_id,
            name="scope-test",
            scopes=[KeyScope.READ]
        )

        updated = self.manager.update_scopes(
            api_key.id,
            self.tenant_id,
            [KeyScope.READ, KeyScope.WRITE, KeyScope.ADMIN]
        )

        assert updated is not None
        assert KeyScope.ADMIN in updated.scopes
        assert len(updated.scopes) == 3

    def test_list_keys(self):
        """Test listing keys for a tenant"""
        # Create multiple keys
        for i in range(3):
            self.manager.generate_key(
                tenant_id=self.tenant_id,
                name=f"list-test-{i}",
                scopes=[KeyScope.READ]
            )

        keys = self.manager.list_keys(self.tenant_id)
        assert len(keys) >= 3

    def test_delete_key(self):
        """Test permanently deleting a key"""
        plaintext, api_key = self.manager.generate_key(
            tenant_id=self.tenant_id,
            name="delete-test",
            scopes=[KeyScope.READ]
        )

        success = self.manager.delete_key(api_key.id, self.tenant_id)
        assert success is True

        key = self.manager.get_key(api_key.id, self.tenant_id)
        assert key is None

    def test_key_isolation_by_tenant(self):
        """Test that keys are isolated by tenant"""
        plaintext, api_key = self.manager.generate_key(
            tenant_id="tenant-a",
            name="isolation-test",
            scopes=[KeyScope.READ]
        )

        # Should not find key for different tenant
        key = self.manager.get_key(api_key.id, "tenant-b")
        assert key is None

    def test_rate_limits(self):
        """Test key rate limit configuration"""
        plaintext, api_key = self.manager.generate_key(
            tenant_id=self.tenant_id,
            name="rate-limit-test",
            scopes=[KeyScope.READ],
            rate_limit_rpm=100,
            rate_limit_rpd=5000
        )

        assert api_key.rate_limit_rpm == 100
        assert api_key.rate_limit_rpd == 5000
