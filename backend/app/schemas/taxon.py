"""
backend/app/schemas/taxon.py
-----------------------------
Taxon 相关 Pydantic v2 schemas。
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# 基础 schema
# ---------------------------------------------------------------------------

class TaxonBase(BaseModel):
    """Taxon 表的共享字段。"""

    taxid:    str = Field(..., description="NCBI Taxonomy ID（字符串）")
    name:     str = Field(..., description="分类单元名称")
    lvl_type: str = Field(..., description="Kraken2 原始层级代码，如 S / G / P")
    rank:     str = Field(..., description="映射后的层级名称，如 species / genus / phylum")


# ---------------------------------------------------------------------------
# Read schema
# ---------------------------------------------------------------------------

class TaxonRead(TaxonBase):
    """从数据库读取 Taxon 时的响应 schema。"""

    id: int = Field(..., description="数据库自增主键")

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Search result schema（用于模糊搜索接口）
# ---------------------------------------------------------------------------

class TaxonSearchResult(BaseModel):
    """
    Taxon 搜索结果条目。
    用于 GET /api/taxa/search?q=xxx 接口，返回轻量摘要，不含 id。
    """

    taxid:    str = Field(..., description="NCBI Taxonomy ID")
    name:     str = Field(..., description="分类单元名称")
    rank:     str = Field(..., description="层级名称")
    lvl_type: str = Field(..., description="Kraken2 原始层级代码")

    model_config = ConfigDict(from_attributes=True)
