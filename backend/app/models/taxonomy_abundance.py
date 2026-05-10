"""
backend/app/models/taxonomy_abundance.py
-----------------------------------------
ORM 模型：TaxonomyAbundance（样品 × 分类单元的丰度关联表）
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base

if TYPE_CHECKING:
    from .sample import Sample
    from .taxon import Taxon


class TaxonomyAbundance(Base):
    """
    对应数据表 `taxonomy_abundance`。
    记录每个样品中每个分类单元的读数（reads）与相对丰度（relative_abundance）。

    外键：
      - sample_id -> samples.id
      - taxon_id  -> taxa.id

    组合索引 (sample_id, taxon_id) 覆盖最常见的查询模式。
    """

    __tablename__ = "taxonomy_abundance"

    __table_args__ = (
        # 覆盖 "某样品的所有 taxon" 与 "某 taxon 的所有样品" 两种查询
        Index("ix_ta_sample_taxon", "sample_id", "taxon_id"),
        Index("ix_ta_taxon_sample", "taxon_id", "sample_id"),
    )

    # ---- 主键 --------------------------------------------------------------
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # ---- 外键 --------------------------------------------------------------
    sample_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("samples.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    taxon_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("taxa.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ---- 丰度数据 ----------------------------------------------------------
    reads_all: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="clade 累计读数（含子节点）",
    )
    reads_lvl: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="该层级独有读数（不含子节点）",
    )
    relative_abundance_all: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="reads_all / 样品总 reads",
    )
    relative_abundance_lvl: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="reads_lvl / 样品总 reads",
    )

    # ---- 关系 --------------------------------------------------------------
    sample: Mapped["Sample"] = relationship(
        "Sample",
        back_populates="abundance_records",
        lazy="joined",
    )
    taxon: Mapped["Taxon"] = relationship(
        "Taxon",
        back_populates="abundance_records",
        lazy="joined",
    )

    def __repr__(self) -> str:
        return (
            f"<TaxonomyAbundance id={self.id} "
            f"sample_id={self.sample_id} taxon_id={self.taxon_id} "
            f"rel_abund_all={self.relative_abundance_all:.4f}>"
        )
