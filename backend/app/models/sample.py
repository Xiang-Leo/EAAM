"""
backend/app/models/sample.py
-----------------------------
ORM 模型：Sample（古代样品元数据）
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, Integer, Float, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base

if TYPE_CHECKING:
    from .taxonomy_abundance import TaxonomyAbundance


class Sample(Base):
    """
    对应数据表 `samples`。
    存储古代牙结石样品的元数据信息。
    """

    __tablename__ = "samples"

    # ---- 主键 & 唯一业务键 -------------------------------------------------
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sample_id: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
        comment="业务样品 ID，如 GX_Tang_1",
    )

    # ---- 地理信息 ----------------------------------------------------------
    province: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    region:   Mapped[Optional[str]] = mapped_column(String(64), index=True)

    # ---- 时间 / 历史信息 ---------------------------------------------------
    dynasty:        Mapped[Optional[str]] = mapped_column(String(64), index=True)
    period:         Mapped[Optional[str]] = mapped_column(String(64))
    estimated_year: Mapped[Optional[int]] = mapped_column(Integer, comment="估计年份（公元年，负数为 BC）")

    # ---- 个体信息 ----------------------------------------------------------
    sex:                 Mapped[Optional[str]] = mapped_column(String(32), index=True)
    subsistence_pattern: Mapped[Optional[str]] = mapped_column(String(64), index=True)

    # ---- 遗址信息 ----------------------------------------------------------
    site_name:  Mapped[Optional[str]]   = mapped_column(String(128))
    latitude:   Mapped[Optional[float]] = mapped_column(Float)
    longitude:  Mapped[Optional[float]] = mapped_column(Float)

    # ---- 数据来源 ----------------------------------------------------------
    source: Mapped[Optional[str]] = mapped_column(String(256))

    # ---- 关系 --------------------------------------------------------------
    abundance_records: Mapped[list["TaxonomyAbundance"]] = relationship(
        "TaxonomyAbundance",
        back_populates="sample",
        cascade="all, delete-orphan",
        lazy="dynamic",
    )

    def __repr__(self) -> str:
        return f"<Sample id={self.id} sample_id={self.sample_id!r} dynasty={self.dynasty!r}>"
