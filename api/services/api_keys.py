"""API key management with rotation and scopes"""
import secrets
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional
from enum import Enum

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class KeyScope(str, Enum):
    """API key permission scopes"""
    READ = "read"           # Read-only access
    WRITE = "write"         # Create/update resources
    DELETE = "delete"       # Delete resources
    ADMIN = "admin"         # Full access including team management
    BILLING = "billing"     # Billing operations


class APIKey(BaseModel):
    """API key with metadata"""
    id: str
    tenant_id: str
    name: str
    key_hash: str           # Store hash, not plaintext
    key_prefix: str         # First 8 chars for identification
    scopes: list[KeyScope]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    is_active: bool = True
    created_by: Optional[str] = None

    # Rate limit overrides
    rate_limit_rpm: Optional[int] = None
    rate_limit_rpd: Optional[int] = None


class APIKeyManager:
    """Manage API keys with rotation and scopes"""

    def __init__(self):
        self._keys: dict[str, APIKey] = {}
        self._key_lookup: dict[str, str] = {}  # hash -> key_id

    def generate_key(
        self,
        tenant_id: str,
        name: str,
        scopes: list[KeyScope],
        expires_days: Optional[int] = None,
        created_by: Optional[str] = None,
        rate_limit_rpm: Optional[int] = None,
        rate_limit_rpd: Optional[int] = None,
    ) -> tuple[str, APIKey]:
        """
        Generate a new API key.

        Returns:
            (plaintext_key, key_metadata)

        The plaintext key is only returned once and should be
        shown to the user immediately.
        """
        # Generate key: tenant_id:random_secret
        secret = secrets.token_urlsafe(32)
        plaintext_key = f"{tenant_id}:{secret}"

        # Hash for storage
        key_hash = self._hash_key(plaintext_key)
        key_prefix = plaintext_key[:12] + "..."

        key_id = secrets.token_urlsafe(16)

        expires_at = None
        if expires_days:
            expires_at = datetime.utcnow() + timedelta(days=expires_days)

        api_key = APIKey(
            id=key_id,
            tenant_id=tenant_id,
            name=name,
            key_hash=key_hash,
            key_prefix=key_prefix,
            scopes=scopes,
            expires_at=expires_at,
            created_by=created_by,
            rate_limit_rpm=rate_limit_rpm,
            rate_limit_rpd=rate_limit_rpd,
        )

        self._keys[key_id] = api_key
        self._key_lookup[key_hash] = key_id

        logger.info(f"Generated API key {key_id} for tenant {tenant_id}")
        return plaintext_key, api_key

    def validate_key(self, plaintext_key: str) -> Optional[APIKey]:
        """
        Validate an API key and return metadata.

        Returns None if key is invalid, expired, or inactive.
        """
        key_hash = self._hash_key(plaintext_key)
        key_id = self._key_lookup.get(key_hash)

        if not key_id:
            return None

        api_key = self._keys.get(key_id)
        if not api_key:
            return None

        # Check if active
        if not api_key.is_active:
            return None

        # Check expiration
        if api_key.expires_at and datetime.utcnow() > api_key.expires_at:
            return None

        # Update last used
        api_key.last_used_at = datetime.utcnow()

        return api_key

    def has_scope(self, api_key: APIKey, scope: KeyScope) -> bool:
        """Check if key has a specific scope"""
        if KeyScope.ADMIN in api_key.scopes:
            return True
        return scope in api_key.scopes

    def list_keys(self, tenant_id: str) -> list[APIKey]:
        """List all keys for a tenant (without hashes)"""
        return [
            k for k in self._keys.values()
            if k.tenant_id == tenant_id
        ]

    def get_key(self, key_id: str, tenant_id: str) -> Optional[APIKey]:
        """Get a specific key"""
        key = self._keys.get(key_id)
        if key and key.tenant_id == tenant_id:
            return key
        return None

    def revoke_key(self, key_id: str, tenant_id: str) -> bool:
        """Revoke an API key"""
        key = self._keys.get(key_id)
        if not key or key.tenant_id != tenant_id:
            return False

        key.is_active = False
        logger.info(f"Revoked API key {key_id}")
        return True

    def rotate_key(
        self,
        key_id: str,
        tenant_id: str,
    ) -> Optional[tuple[str, APIKey]]:
        """
        Rotate an API key.

        Creates a new key with same settings and revokes the old one.
        Returns the new plaintext key and metadata.
        """
        old_key = self._keys.get(key_id)
        if not old_key or old_key.tenant_id != tenant_id:
            return None

        # Generate new key with same settings
        new_plaintext, new_key = self.generate_key(
            tenant_id=tenant_id,
            name=f"{old_key.name} (rotated)",
            scopes=old_key.scopes,
            expires_days=None if not old_key.expires_at else
                (old_key.expires_at - datetime.utcnow()).days,
            created_by=old_key.created_by,
            rate_limit_rpm=old_key.rate_limit_rpm,
            rate_limit_rpd=old_key.rate_limit_rpd,
        )

        # Revoke old key
        old_key.is_active = False

        logger.info(f"Rotated API key {key_id} -> {new_key.id}")
        return new_plaintext, new_key

    def update_scopes(
        self,
        key_id: str,
        tenant_id: str,
        scopes: list[KeyScope],
    ) -> Optional[APIKey]:
        """Update key scopes"""
        key = self._keys.get(key_id)
        if not key or key.tenant_id != tenant_id:
            return None

        key.scopes = scopes
        return key

    def delete_key(self, key_id: str, tenant_id: str) -> bool:
        """Permanently delete an API key"""
        key = self._keys.get(key_id)
        if not key or key.tenant_id != tenant_id:
            return False

        # Remove from lookup
        if key.key_hash in self._key_lookup:
            del self._key_lookup[key.key_hash]

        del self._keys[key_id]
        logger.info(f"Deleted API key {key_id}")
        return True

    def _hash_key(self, plaintext_key: str) -> str:
        """Hash a key for secure storage"""
        return hashlib.sha256(plaintext_key.encode()).hexdigest()


# Global key manager
_key_manager: Optional[APIKeyManager] = None


def get_api_key_manager() -> APIKeyManager:
    global _key_manager
    if _key_manager is None:
        _key_manager = APIKeyManager()
    return _key_manager
