"""
backend/app/models/admin.py
---------------------------
ORM models for the phase-one admin workflow.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class AdminUser(Base):
    __tablename__ = "admin_users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    role: Mapped[str] = mapped_column(String(32), default="admin", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class AdminSession(Base):
    __tablename__ = "admin_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("admin_users.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)


class AdminUpload(Base):
    __tablename__ = "admin_uploads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    path: Mapped[str] = mapped_column(String(512), nullable=False)
    content_type: Mapped[Optional[str]] = mapped_column(String(128))
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    data_type: Mapped[str] = mapped_column(String(64), nullable=False, default="auto")
    uploaded_by: Mapped[int] = mapped_column(Integer, ForeignKey("admin_users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class DataImportJob(Base):
    __tablename__ = "data_import_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    upload_id: Mapped[int] = mapped_column(Integer, ForeignKey("admin_uploads.id", ondelete="CASCADE"), nullable=False)
    data_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    message: Mapped[Optional[str]] = mapped_column(Text)
    field_mapping: Mapped[Optional[str]] = mapped_column(Text)
    log_path: Mapped[Optional[str]] = mapped_column(String(512))
    error_report_path: Mapped[Optional[str]] = mapped_column(String(512))
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("admin_users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)


class BackupJob(Base):
    __tablename__ = "backup_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="success")
    action: Mapped[str] = mapped_column(String(32), nullable=False, default="backup")
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    path: Mapped[str] = mapped_column(String(512), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    message: Mapped[Optional[str]] = mapped_column(Text)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("admin_users.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("admin_users.id", ondelete="SET NULL"))
    username: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    action: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    target_type: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    target_id: Mapped[Optional[str]] = mapped_column(String(128), index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="success")
    detail: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class FunctionalFeature(Base):
    __tablename__ = "functional_features"

    __table_args__ = (
        UniqueConstraint(
            "feature_type",
            "feature_id",
            "stratification",
            name="uq_functional_feature_type_id_stratification",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    feature_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    feature_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    feature_name: Mapped[Optional[str]] = mapped_column(String(512))
    stratification: Mapped[str] = mapped_column(String(512), nullable=False, default="unstratified")
    raw_name: Mapped[str] = mapped_column(String(1024), nullable=False)


class FunctionalAbundance(Base):
    __tablename__ = "functional_abundance"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sample_id: Mapped[int] = mapped_column(Integer, ForeignKey("samples.id", ondelete="CASCADE"), index=True, nullable=False)
    feature_id: Mapped[int] = mapped_column(Integer, ForeignKey("functional_features.id", ondelete="CASCADE"), index=True, nullable=False)
    abundance: Mapped[float] = mapped_column(nullable=False)
    source_upload_id: Mapped[int] = mapped_column(Integer, ForeignKey("admin_uploads.id", ondelete="CASCADE"), index=True, nullable=False)
