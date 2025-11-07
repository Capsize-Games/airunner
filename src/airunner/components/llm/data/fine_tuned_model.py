import datetime
from typing import Optional, List

from sqlalchemy import (
    Column,
    Integer,
    DateTime,
    String,
    JSON,
)

from airunner.components.data.models.base import BaseModel


class FineTunedModel(BaseModel):
    __tablename__ = "fine_tuned_models"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    adapter_path = Column(String, nullable=True)
    date_added = Column(
        DateTime, default=datetime.datetime.now(datetime.timezone.utc)
    )
    last_trained = Column(DateTime, nullable=True)
    files_used = Column(JSON, nullable=True, default=[])
    settings = Column(JSON, nullable=True, default={})
    tags = Column(JSON, nullable=True, default=[])

    @classmethod
    def create_record(
        cls,
        name: str,
        adapter_path: Optional[str] = None,
        files: Optional[List[str]] = None,
        settings: Optional[dict] = None,
        tags: Optional[List[str]] = None,
    ):
        try:
            # Check if record already exists
            existing = cls.objects.filter_by_first(name=name)
            if existing:
                # Update existing record using update_by
                cls.objects.update_by(
                    filter={"name": name},
                    adapter_path=adapter_path,
                    last_trained=datetime.datetime.now(datetime.timezone.utc),
                    files_used=files or [],
                    settings=settings or {},
                    tags=tags if tags is not None else existing.tags,
                )
                return cls.objects.filter_by_first(name=name)

            # Create new record
            return cls.objects.create(
                name=name,
                adapter_path=adapter_path,
                date_added=datetime.datetime.now(datetime.timezone.utc),
                last_trained=datetime.datetime.now(datetime.timezone.utc),
                files_used=files or [],
                settings=settings or {},
                tags=tags or [],
            )
        except Exception as e:
            # Attempt to create missing tables (common in fresh installs)
            try:
                # Import engine and Base metadata and attempt to create tables
                from airunner.components.data.session_manager import (
                    _get_engine,
                )
                from airunner.components.data.models.base import Base

                Base.metadata.create_all(bind=_get_engine())

                # Try again after creating tables
                existing = cls.objects.filter_by_first(name=name)
                if existing:
                    # Update existing record using update_by
                    cls.objects.update_by(
                        filter={"name": name},
                        adapter_path=adapter_path,
                        last_trained=datetime.datetime.now(
                            datetime.timezone.utc
                        ),
                        files_used=files or [],
                        settings=settings or {},
                        tags=tags if tags is not None else existing.tags,
                    )
                    return cls.objects.filter_by_first(name=name)

                return cls.objects.create(
                    name=name,
                    adapter_path=adapter_path,
                    date_added=datetime.datetime.now(datetime.timezone.utc),
                    last_trained=datetime.datetime.now(datetime.timezone.utc),
                    files_used=files or [],
                    settings=settings or {},
                    tags=tags or [],
                )
            except Exception:
                # If creating tables failed, raise a clearer error so callers
                # can understand how to bootstrapping the DB.
                raise RuntimeError(
                    "Failed to create database tables for FineTunedModel. "
                    "Ensure the application's database is initialized and writable."
                )
