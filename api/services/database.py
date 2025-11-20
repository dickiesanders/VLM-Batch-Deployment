"""PostgreSQL database for schema persistence"""
import logging
from datetime import datetime
from typing import Any, Optional
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

# SQLAlchemy models and async support
try:
    from sqlalchemy import Column, String, DateTime, JSON, Boolean, Integer
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import declarative_base, sessionmaker
    from sqlalchemy import select, delete, update

    Base = declarative_base()

    class SchemaModel(Base):
        __tablename__ = "schemas"

        id = Column(String, primary_key=True)
        tenant_id = Column(String, nullable=False, index=True)
        name = Column(String, nullable=False)
        description = Column(String)
        json_schema = Column(JSON, nullable=False)
        prompt_template = Column(String)
        created_at = Column(DateTime, default=datetime.utcnow)
        updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    class TenantModel(Base):
        __tablename__ = "tenants"

        id = Column(String, primary_key=True)
        name = Column(String, nullable=False)
        email = Column(String, nullable=False)
        plan = Column(String, default="free")
        created_at = Column(DateTime, default=datetime.utcnow)
        usage_quota = Column(Integer, default=1000)
        is_active = Column(Boolean, default=True)

    class APIKeyModel(Base):
        __tablename__ = "api_keys"

        key = Column(String, primary_key=True)
        tenant_id = Column(String, nullable=False, index=True)
        name = Column(String, nullable=False)
        created_at = Column(DateTime, default=datetime.utcnow)
        is_active = Column(Boolean, default=True)

    HAS_SQLALCHEMY = True
except ImportError:
    HAS_SQLALCHEMY = False
    logger.warning("SQLAlchemy not installed. PostgreSQL persistence disabled.")


class DatabaseManager:
    """Async database manager for PostgreSQL"""

    def __init__(self, database_url: str):
        if not HAS_SQLALCHEMY:
            raise RuntimeError("SQLAlchemy required for PostgreSQL support")

        # Convert postgres:// to postgresql+asyncpg://
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

        self._engine = create_async_engine(database_url, echo=False)
        self._session_factory = sessionmaker(
            self._engine, class_=AsyncSession, expire_on_commit=False
        )

    async def init_db(self):
        """Create tables if they don't exist"""
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables initialized")

    @asynccontextmanager
    async def session(self):
        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    # Schema operations
    async def create_schema(
        self,
        schema_id: str,
        tenant_id: str,
        name: str,
        json_schema: dict,
        description: Optional[str] = None,
        prompt_template: Optional[str] = None,
    ) -> dict:
        async with self.session() as session:
            schema = SchemaModel(
                id=schema_id,
                tenant_id=tenant_id,
                name=name,
                description=description,
                json_schema=json_schema,
                prompt_template=prompt_template,
            )
            session.add(schema)
            return self._schema_to_dict(schema)

    async def get_schema(self, schema_id: str, tenant_id: str) -> Optional[dict]:
        async with self.session() as session:
            result = await session.execute(
                select(SchemaModel).where(
                    SchemaModel.id == schema_id,
                    SchemaModel.tenant_id == tenant_id
                )
            )
            schema = result.scalar_one_or_none()
            return self._schema_to_dict(schema) if schema else None

    async def list_schemas(self, tenant_id: str) -> list[dict]:
        async with self.session() as session:
            result = await session.execute(
                select(SchemaModel).where(SchemaModel.tenant_id == tenant_id)
            )
            return [self._schema_to_dict(s) for s in result.scalars().all()]

    async def update_schema(
        self,
        schema_id: str,
        tenant_id: str,
        **updates
    ) -> Optional[dict]:
        async with self.session() as session:
            result = await session.execute(
                select(SchemaModel).where(
                    SchemaModel.id == schema_id,
                    SchemaModel.tenant_id == tenant_id
                )
            )
            schema = result.scalar_one_or_none()
            if not schema:
                return None

            for key, value in updates.items():
                if value is not None and hasattr(schema, key):
                    setattr(schema, key, value)
            schema.updated_at = datetime.utcnow()

            return self._schema_to_dict(schema)

    async def delete_schema(self, schema_id: str, tenant_id: str) -> bool:
        async with self.session() as session:
            result = await session.execute(
                delete(SchemaModel).where(
                    SchemaModel.id == schema_id,
                    SchemaModel.tenant_id == tenant_id
                )
            )
            return result.rowcount > 0

    def _schema_to_dict(self, schema: "SchemaModel") -> dict:
        return {
            "id": schema.id,
            "tenant_id": schema.tenant_id,
            "name": schema.name,
            "description": schema.description,
            "json_schema": schema.json_schema,
            "prompt_template": schema.prompt_template,
            "created_at": schema.created_at,
            "updated_at": schema.updated_at,
        }

    # API Key operations
    async def validate_api_key(self, key: str) -> Optional[str]:
        """Validate API key and return tenant_id if valid"""
        async with self.session() as session:
            result = await session.execute(
                select(APIKeyModel).where(
                    APIKeyModel.key == key,
                    APIKeyModel.is_active == True
                )
            )
            api_key = result.scalar_one_or_none()
            return api_key.tenant_id if api_key else None

    async def close(self):
        await self._engine.dispose()


# Global database manager
_db: Optional[DatabaseManager] = None


def get_database() -> Optional[DatabaseManager]:
    return _db


def initialize_database(database_url: str) -> DatabaseManager:
    global _db
    _db = DatabaseManager(database_url)
    logger.info("Database manager initialized")
    return _db
