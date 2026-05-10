"""
backend/app/services/sample_service.py
----------------------------------------
业务逻辑层：Sample 相关查询。
将 SQL 操作从路由层解耦，便于单元测试和复用。
"""

from __future__ import annotations

from typing import Literal

from sqlalchemy import desc, asc
from sqlalchemy.orm import Session, joinedload

from app.models import Sample, Taxon, TaxonomyAbundance
from app.schemas.sample import SampleRead, PaginatedSamples
from app.schemas.abundance import SampleTaxonProfileResult

# ---------------------------------------------------------------------------
# 合法枚举值（用于参数校验）
# ---------------------------------------------------------------------------

VALID_RANKS = frozenset(
    {"phylum", "class", "order", "family", "genus", "genus_sublevel", "species"}
)
VALID_ABUNDANCE_TYPES = frozenset(
    {"relative_abundance_all", "relative_abundance_lvl"}
)


# ---------------------------------------------------------------------------
# 1. 样品列表查询
# ---------------------------------------------------------------------------

def get_samples(
    db: Session,
    dynasty: str | None = None,
    province: str | None = None,
    region: str | None = None,
    sex: str | None = None,
    subsistence_pattern: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> PaginatedSamples:
    """
    分页查询样品列表，支持多维度筛选。
    返回 PaginatedSamples（含总数 + 当页数据）。
    """
    query = db.query(Sample)

    if dynasty:
        query = query.filter(Sample.dynasty == dynasty)
    if province:
        query = query.filter(Sample.province == province)
    if region:
        query = query.filter(Sample.region == region)
    if sex:
        query = query.filter(Sample.sex == sex)
    if subsistence_pattern:
        query = query.filter(Sample.subsistence_pattern == subsistence_pattern)

    total = query.count()

    items = (
        query
        .order_by(asc(Sample.sample_id))
        .offset(offset)
        .limit(limit)
        .all()
    )

    return PaginatedSamples(
        total=total,
        items=[SampleRead.model_validate(s) for s in items],
        page=offset // limit + 1 if limit else 1,
        size=limit,
    )


# ---------------------------------------------------------------------------
# 2. 单个样品详情
# ---------------------------------------------------------------------------

def get_sample_by_sample_id(db: Session, sample_id: str) -> Sample | None:
    """
    按业务 sample_id 查询 Sample ORM 对象。
    未找到时返回 None（由路由层负责抛出 404）。
    """
    return db.query(Sample).filter(Sample.sample_id == sample_id).first()


# ---------------------------------------------------------------------------
# 3. 单个样品的 top taxa
# ---------------------------------------------------------------------------

def get_sample_taxa(
    db: Session,
    sample_id: str,
    rank: str | None = None,
    top_n: int = 20,
    abundance_type: str = "relative_abundance_all",
) -> list[SampleTaxonProfileResult]:
    """
    返回指定样品的 top N taxon。

    Parameters
    ----------
    db             : SQLAlchemy Session
    sample_id      : 业务样品 ID（非数据库主键）
    rank           : 可选，按 rank 过滤（如 "species"）
    top_n          : 返回前 N 条，默认 20
    abundance_type : 排序依据字段，"relative_abundance_all" 或 "relative_abundance_lvl"
    """
    # 确认样品存在（由路由层做，但这里做防御性查询）
    sample = db.query(Sample).filter(Sample.sample_id == sample_id).first()
    if sample is None:
        return []

    # 构建联合查询：TaxonomyAbundance JOIN Taxon
    query = (
        db.query(TaxonomyAbundance, Taxon)
        .join(Taxon, TaxonomyAbundance.taxon_id == Taxon.id)
        .filter(TaxonomyAbundance.sample_id == sample.id)
    )

    if rank:
        query = query.filter(Taxon.rank == rank)

    # 按指定丰度字段降序
    if abundance_type == "relative_abundance_all":
        query = query.order_by(desc(TaxonomyAbundance.relative_abundance_all))
    else:
        query = query.order_by(desc(TaxonomyAbundance.relative_abundance_lvl))

    rows = query.limit(top_n).all()

    return [
        SampleTaxonProfileResult(
            taxid=taxon.taxid,
            name=taxon.name,
            rank=taxon.rank,
            reads_all=abund.reads_all,
            reads_lvl=abund.reads_lvl,
            relative_abundance_all=abund.relative_abundance_all,
            relative_abundance_lvl=abund.relative_abundance_lvl,
        )
        for abund, taxon in rows
    ]
