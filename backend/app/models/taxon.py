"""
backend/app/models/taxon.py
----------------------------
ORM 模型：Taxon（分类单元）
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base

if TYPE_CHECKING:
    from .taxonomy_abundance import TaxonomyAbundance


class Taxon(Base):
    """
    对应数据表 `taxa`。
    存储 Kraken2 分类单元的分类学信息。

    唯一约束 (taxid, name, rank) 防止同一分类单元在不同 rank 层级重复录入。
    """

    __tablename__ = "taxa"

    __table_args__ = (
        UniqueConstraint("taxid", "name", "rank", name="uq_taxon_taxid_name_rank"),
    )

    # ---- 主键 --------------------------------------------------------------
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # ---- 分类学字段 --------------------------------------------------------
    taxid: Mapped[str] = mapped_column(
        String(32),
        index=True,
        nullable=False,
        comment="NCBI taxid（字符串，方便处理特殊值）",
    )
    name: Mapped[str] = mapped_column(
        String(256),
        index=True,
        nullable=False,
        comment="分类单元名称（strip 后存储）",
    )
    lvl_type: Mapped[str] = mapped_column(
        String(8),
        nullable=False,
        comment="Kraken2 原始层级代码，如 S、G、P",
    )
    rank: Mapped[str] = mapped_column(
        String(32),
        index=True,
        nullable=False,
        comment="映射后的层级名称，如 species、genus、phylum",
    )

    # ---- 关系 --------------------------------------------------------------
    abundance_records: Mapped[list["TaxonomyAbundance"]] = relationship(
        "TaxonomyAbundance",
        back_populates="taxon",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    def __repr__(self) -> str:
        return f"<Taxon id={self.id} taxid={self.taxid!r} name={self.name!r} rank={self.rank!r}>"
