"""
backend/app/models/__init__.py
-------------------------------
统一导出所有 ORM 模型，确保 SQLAlchemy 在调用 Base.metadata.create_all()
之前已经导入了所有表定义。
"""

from .sample import Sample
from .taxon import Taxon
from .taxonomy_abundance import TaxonomyAbundance
from .admin import (
    AdminSession,
    AdminUpload,
    AdminUser,
    AuditLog,
    BackupJob,
    DataImportJob,
    FunctionalAbundance,
    FunctionalFeature,
)

__all__ = [
    "Sample",
    "Taxon",
    "TaxonomyAbundance",
    "AdminSession",
    "AdminUpload",
    "AdminUser",
    "AuditLog",
    "BackupJob",
    "DataImportJob",
    "FunctionalAbundance",
    "FunctionalFeature",
]
