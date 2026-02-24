"""
Risk Configuration Versioning System
Allows versioning, tracking, and rollback of risk configurations
"""
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import uuid4
import json

from sqlalchemy import Column, String, DateTime, Text, JSON, Integer
from sqlalchemy.orm import declarative_base
from packages.shared.database import Base
from packages.shared.logger import logger


class ConfigVersion(Base):
    """Store risk configuration versions"""
    __tablename__ = "config_versions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid4()))
    config_type = Column(String(50), nullable=False, index=True)  # "risk"
    version_number = Column(Integer, nullable=False)
    config_json = Column(JSON, nullable=False)
    description = Column(Text, nullable=True)
    created_by = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    parent_version_id = Column(String(36), nullable=True)  # For rollback tracking

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "version_number": self.version_number,
            "config": self.config_json,
            "description": self.description,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
        }


class ConfigVersionManager:
    """Manage configuration versions"""

    def __init__(self, db_session):
        self.db = db_session

    async def get_current_config(self, config_type: str = "risk") -> Optional[Dict[str, Any]]:
        """Get current configuration"""
        from sqlalchemy import select

        result = await self.db.execute(
            select(ConfigVersion)
            .where(ConfigVersion.config_type == config_type)
            .order_by(ConfigVersion.created_at.desc())
            .limit(1)
        )
        latest = result.scalar_one_or_none()
        return latest.config_json if latest else None

    async def get_all_versions(
        self,
        config_type: str = "risk",
        limit: int = 50,
    ) -> List[ConfigVersion]:
        """Get all versions of a configuration"""
        from sqlalchemy import select

        result = await self.db.execute(
            select(ConfigVersion)
            .where(ConfigVersion.config_type == config_type)
            .order_by(ConfigVersion.created_at.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def create_version(
        self,
        config_type: str,
        config: Dict[str, Any],
        created_by: str,
        description: Optional[str] = None,
    ) -> ConfigVersion:
        """Create new configuration version"""
        # Get latest version number
        from sqlalchemy import select, func

        result = await self.db.execute(
            select(func.max(ConfigVersion.version_number))
            .where(ConfigVersion.config_type == config_type)
        )
        latest_version = result.scalar() or 0

        # Create new version
        version = ConfigVersion(
            config_type=config_type,
            version_number=latest_version + 1,
            config_json=config,
            description=description or f"Update by {created_by}",
            created_by=created_by,
            created_at=datetime.utcnow(),
        )

        self.db.add(version)
        await self.db.commit()

        logger.info(
            "config_version_created",
            config_type=config_type,
            version=version.version_number,
            created_by=created_by,
        )

        return version

    async def rollback_to_version(
        self,
        version_id: str,
        created_by: str,
    ) -> ConfigVersion:
        """Rollback to specific version"""
        from sqlalchemy import select

        # Get version
        result = await self.db.execute(
            select(ConfigVersion).where(ConfigVersion.id == version_id)
        )
        target_version = result.scalar_one_or_none()

        if not target_version:
            raise ValueError(f"Version not found: {version_id}")

        # Create new version from rollback
        new_version = await self.create_version(
            config_type=target_version.config_type,
            config=target_version.config_json.copy() if isinstance(target_version.config_json, dict) else target_version.config_json,
            created_by=created_by,
            description=f"Rolled back from v{target_version.version_number}",
        )

        new_version.parent_version_id = version_id
        await self.db.commit()

        logger.info(
            "config_rolled_back",
            from_version=target_version.version_number,
            to_version=new_version.version_number,
            rolled_back_by=created_by,
        )

        return new_version

    async def get_version_diff(
        self,
        version_id_1: str,
        version_id_2: str,
    ) -> Dict[str, Any]:
        """Get difference between two versions"""
        from sqlalchemy import select

        result1 = await self.db.execute(
            select(ConfigVersion).where(ConfigVersion.id == version_id_1)
        )
        v1 = result1.scalar_one_or_none()

        result2 = await self.db.execute(
            select(ConfigVersion).where(ConfigVersion.id == version_id_2)
        )
        v2 = result2.scalar_one_or_none()

        if not v1 or not v2:
            raise ValueError("Version not found")

        # Simple diff
        diff = {
            "changed_fields": [],
            "v1": v1.config_json,
            "v2": v2.config_json,
        }

        if isinstance(v1.config_json, dict) and isinstance(v2.config_json, dict):
            all_keys = set(v1.config_json.keys()) | set(v2.config_json.keys())
            for key in all_keys:
                if v1.config_json.get(key) != v2.config_json.get(key):
                    diff["changed_fields"].append({
                        "field": key,
                        "v1": v1.config_json.get(key),
                        "v2": v2.config_json.get(key),
                    })

        return diff
