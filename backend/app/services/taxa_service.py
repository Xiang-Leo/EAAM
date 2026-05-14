"""
backend/app/services/taxa_service.py
--------------------------------------
业务逻辑层：Taxa 相关查询。

包含：
  search_taxa          — 模糊搜索 taxon name
  get_top_taxa         — 筛选样品集合下的 top N taxa（含统计）
  get_taxon_distribution — 某 taxon 在分组维度下的丰度分布
"""

from __future__ import annotations

import statistics
from typing import Optional

import pandas as pd
from sqlalchemy import func, and_
from sqlalchemy.orm import Session

from app.models import Sample, Taxon, TaxonomyAbundance
from app.schemas.taxon import TaxonSearchResult
from app.schemas.abundance import (
    TopTaxonResult,
    TaxonDistributionResult,
    TaxonDistributionResponse,
)

# ---------------------------------------------------------------------------
# 合法枚举值
# ---------------------------------------------------------------------------

VALID_RANKS = frozenset(
    {"phylum", "class", "order", "family", "genus", "genus_sublevel", "species"}
)
VALID_GROUP_BY = frozenset(
    {"dynasty", "province", "region", "subsistence_pattern"}
)
VALID_ABUNDANCE_TYPES = frozenset(
    {"relative_abundance_all", "relative_abundance_lvl"}
)


# ---------------------------------------------------------------------------
# 内部辅助：构建 Sample 过滤条件
# ---------------------------------------------------------------------------

def _sample_filters(
    dynasty: str | None,
    province: str | None,
    region: str | None,
    sex: str | None,
    subsistence_pattern: str | None,
) -> list:
    """返回 SQLAlchemy filter 表达式列表。"""
    filters = []
    if dynasty:
        filters.append(Sample.dynasty == dynasty)
    if province:
        filters.append(Sample.province == province)
    if region:
        filters.append(Sample.region == region)
    if sex:
        filters.append(Sample.sex == sex)
    if subsistence_pattern:
        filters.append(Sample.subsistence_pattern == subsistence_pattern)
    return filters


# ---------------------------------------------------------------------------
# 1. 模糊搜索 taxa
# ---------------------------------------------------------------------------

def search_taxa(
    db: Session,
    q: str,
    rank: str | None = None,
    limit: int = 20,
) -> list[TaxonSearchResult]:
    """
    按名称模糊搜索 taxa（LIKE %q%）。
    可选按 rank 过滤。
    """
    query = db.query(Taxon).filter(Taxon.name.ilike(f"%{q}%"))

    if rank:
        query = query.filter(Taxon.rank == rank)

    rows = query.order_by(Taxon.name).limit(limit).all()

    return [
        TaxonSearchResult(
            taxid=t.taxid,
            name=t.name,
            rank=t.rank,
            lvl_type=t.lvl_type,
        )
        for t in rows
    ]


# ---------------------------------------------------------------------------
# 2. 筛选条件下的 Top N Taxa
# ---------------------------------------------------------------------------

def get_top_taxa(
    db: Session,
    rank: str,
    dynasty: str | None = None,
    province: str | None = None,
    region: str | None = None,
    sex: str | None = None,
    subsistence_pattern: str | None = None,
    top_n: int = 20,
    abundance_type: str = "relative_abundance_all",
) -> list[TopTaxonResult]:
    """
    在满足样品筛选条件的子集中，计算各 taxon 的统计摘要（均值、中位、样品数、总读数），
    按均值丰度降序返回 top N。

    因 SQLite 不支持 MEDIAN，采用 Python/Pandas 在取回数据后计算。
    """
    # 1. 获取满足条件的样品 ID 列表
    sample_query = db.query(Sample.id)
    filters = _sample_filters(dynasty, province, region, sex, subsistence_pattern)
    if filters:
        sample_query = sample_query.filter(*filters)
    sample_pk_list = [row[0] for row in sample_query.all()]

    if not sample_pk_list:
        return []

    # 2. 获取这些样品 × 指定 rank 的 abundance 原始数据
    abund_col = (
        TaxonomyAbundance.relative_abundance_all
        if abundance_type == "relative_abundance_all"
        else TaxonomyAbundance.relative_abundance_lvl
    )

    rows = (
        db.query(
            Taxon.taxid,
            Taxon.name,
            Taxon.rank,
            abund_col.label("abundance"),
            TaxonomyAbundance.reads_all,
        )
        .join(TaxonomyAbundance, Taxon.id == TaxonomyAbundance.taxon_id)
        .filter(
            TaxonomyAbundance.sample_id.in_(sample_pk_list),
            Taxon.rank == rank,
        )
        .all()
    )

    if not rows:
        return []

    # 3. pandas 聚合（均值、中位数、样品数、总 reads）
    df = pd.DataFrame(rows, columns=["taxid", "name", "rank", "abundance", "reads_all"])

    agg = (
        df.groupby(["taxid", "name", "rank"])
        .agg(
            mean_abundance=("abundance", "mean"),
            median_abundance=("abundance", "median"),
            sample_count=("abundance", "count"),
            total_reads=("reads_all", "sum"),
        )
        .reset_index()
        .sort_values("mean_abundance", ascending=False)
        .head(top_n)
    )

    return [
        TopTaxonResult(
            taxid=row["taxid"],
            name=row["name"],
            rank=row["rank"],
            mean_abundance=round(row["mean_abundance"], 8),
            median_abundance=round(row["median_abundance"], 8),
            sample_count=int(row["sample_count"]),
            total_reads=float(row["total_reads"]),
        )
        for _, row in agg.iterrows()
    ]


# ---------------------------------------------------------------------------
# 3. 某 taxon 在各分组的丰度分布
# ---------------------------------------------------------------------------

def get_taxon_distribution(
    db: Session,
    taxid: str,
    group_by: str,
    rank: str | None = None,
    dynasty: str | None = None,
    province: str | None = None,
    region: str | None = None,
    sex: str | None = None,
    subsistence_pattern: str | None = None,
    abundance_type: str = "relative_abundance_all",
) -> TaxonDistributionResponse | None:
    """
    返回指定 taxid 在 group_by 维度上的丰度统计分布。
    若 taxid 不存在则返回 None（由路由层抛出 404）。

    当同一 taxid 有多个 (name, rank) 组合时，优先按 rank 过滤；
    仍有多个时取第一个（按 name 排序）。
    """
    # 1. 找到 Taxon 记录
    taxon_query = db.query(Taxon).filter(Taxon.taxid == taxid)
    if rank:
        taxon_query = taxon_query.filter(Taxon.rank == rank)
    taxon_obj = taxon_query.order_by(Taxon.name).first()

    if taxon_obj is None:
        return None

    # 2. 获取满足样品筛选条件的 sample PK
    sample_query = db.query(Sample.id, getattr(Sample, group_by))
    filters = _sample_filters(dynasty, province, region, sex, subsistence_pattern)
    if filters:
        sample_query = sample_query.filter(*filters)

    sample_rows = sample_query.all()
    if not sample_rows:
        return TaxonDistributionResponse(
            taxid=taxid,
            name=taxon_obj.name,
            rank=taxon_obj.rank,
            group_by=group_by,
            data=[],
        )

    sample_pk_list = [r[0] for r in sample_rows]
    sample_pk_to_group: dict[int, str] = {
        r[0]: str(r[1]) if r[1] is not None else "Unknown"
        for r in sample_rows
    }

    # 3. 拉取该 taxon × 所有筛选样品的 abundance 数据
    abund_col = (
        TaxonomyAbundance.relative_abundance_all
        if abundance_type == "relative_abundance_all"
        else TaxonomyAbundance.relative_abundance_lvl
    )

    rows = (
        db.query(
            TaxonomyAbundance.sample_id,
            abund_col.label("abundance"),
        )
        .filter(
            TaxonomyAbundance.taxon_id == taxon_obj.id,
            TaxonomyAbundance.sample_id.in_(sample_pk_list),
        )
        .all()
    )

    # 4. 构建 sample_id → abundance 映射（无记录的样品 abundance 记为 0）
    abund_map: dict[int, float] = {r[0]: float(r[1]) for r in rows}
    records = [
        {"group": sample_pk_to_group[pk], "abundance": abund_map.get(pk, 0.0)}
        for pk in sample_pk_list
    ]

    # 5. pandas 分组统计
    df = pd.DataFrame(records)
    agg = (
        df.groupby("group")["abundance"]
        .agg(
            mean_abundance="mean",
            median_abundance="median",
            min_abundance="min",
            max_abundance="max",
            sample_count="count",
        )
        .reset_index()
        .sort_values("group")
    )

    data = [
        TaxonDistributionResult(
            group=row["group"],
            mean_abundance=round(row["mean_abundance"], 8),
            median_abundance=round(row["median_abundance"], 8),
            min_abundance=round(row["min_abundance"], 8),
            max_abundance=round(row["max_abundance"], 8),
            sample_count=int(row["sample_count"]),
        )
        for _, row in agg.iterrows()
    ]

    return TaxonDistributionResponse(
        taxid=taxid,
        name=taxon_obj.name,
        rank=taxon_obj.rank,
        group_by=group_by,
        data=data,
    )


def export_abundance_table(
    db: Session,
    rank: str = "species",
    dynasty: str | None = None,
    province: str | None = None,
    region: str | None = None,
    sex: str | None = None,
    subsistence_pattern: str | None = None,
    abundance_type: str = "relative_abundance_all",
    table_format: str = "matrix",
) -> str:
    """Export filtered taxonomic abundance as CSV text."""
    abund_col = (
        TaxonomyAbundance.relative_abundance_all
        if abundance_type == "relative_abundance_all"
        else TaxonomyAbundance.relative_abundance_lvl
    )
    filters = _sample_filters(dynasty, province, region, sex, subsistence_pattern)

    query = (
        db.query(
            Sample.sample_id,
            Sample.dynasty,
            Sample.province,
            Sample.region,
            Taxon.taxid,
            Taxon.name,
            Taxon.rank,
            abund_col.label("abundance"),
        )
        .join(TaxonomyAbundance, TaxonomyAbundance.sample_id == Sample.id)
        .join(Taxon, Taxon.id == TaxonomyAbundance.taxon_id)
        .filter(Taxon.rank == rank)
    )
    if filters:
        query = query.filter(*filters)

    rows = query.order_by(Sample.sample_id, Taxon.name).all()
    if not rows:
        if table_format == "long":
            return "sample_id,dynasty,province,region,taxid,name,rank,abundance\n"
        return "sample_id,dynasty,province,region\n"

    df = pd.DataFrame(
        rows,
        columns=["sample_id", "dynasty", "province", "region", "taxid", "name", "rank", "abundance"],
    )
    if table_format == "long":
        return df.to_csv(index=False)

    df["feature"] = df["name"].astype(str) + "|" + df["taxid"].astype(str)
    matrix = (
        df.pivot_table(
            index=["sample_id", "dynasty", "province", "region"],
            columns="feature",
            values="abundance",
            aggfunc="sum",
            fill_value=0,
        )
        .reset_index()
    )
    matrix.columns.name = None
    return matrix.to_csv(index=False)
