"""
backend/app/api/routers/taxa.py
---------------------------------
/api/taxa 路由。

端点：
  GET  /api/taxa/search                  — 模糊搜索 taxon name
  GET  /api/taxa/top                     — 筛选条件下的 top N taxa
  GET  /api/taxa/{taxid}/distribution    — 某 taxon 的跨分组丰度分布
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.taxon import TaxonSearchResult
from app.schemas.abundance import TopTaxonResult, TaxonDistributionResponse
from app.services import taxa_service
from app.services.taxa_service import VALID_RANKS, VALID_GROUP_BY, VALID_ABUNDANCE_TYPES

router = APIRouter()


# ---------------------------------------------------------------------------
# 辅助：参数校验（422）
# ---------------------------------------------------------------------------

def _require_valid_rank(rank: str | None, required: bool = False) -> None:
    if required and not rank:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Query parameter 'rank' is required. Valid values: {sorted(VALID_RANKS)}",
        )
    if rank and rank not in VALID_RANKS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid rank '{rank}'. Valid values: {sorted(VALID_RANKS)}",
        )


def _require_valid_group_by(group_by: str) -> None:
    if group_by not in VALID_GROUP_BY:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid group_by '{group_by}'. Valid values: {sorted(VALID_GROUP_BY)}",
        )


def _require_valid_abundance_type(abundance_type: str) -> None:
    if abundance_type not in VALID_ABUNDANCE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Invalid abundance_type '{abundance_type}'. "
                f"Valid values: {sorted(VALID_ABUNDANCE_TYPES)}"
            ),
        )


# ---------------------------------------------------------------------------
# 1. GET /api/taxa/search
# ---------------------------------------------------------------------------

@router.get(
    "/search",
    response_model=list[TaxonSearchResult],
    summary="Search taxa by name",
    description="按名称模糊搜索 taxa（LIKE %q%），可按 rank 过滤。",
)
def search_taxa(
    q:     str           = Query(..., min_length=1, description="搜索关键词（模糊匹配 taxon name）"),
    rank:  Optional[str] = Query(None, description=f"可选，按 rank 过滤。合法值：{sorted(VALID_RANKS)}"),
    limit: int           = Query(20, ge=1, le=200, description="返回条数上限，默认 20"),
    db: Session = Depends(get_db),
) -> list[TaxonSearchResult]:
    _require_valid_rank(rank)
    return taxa_service.search_taxa(db, q=q, rank=rank, limit=limit)


# ---------------------------------------------------------------------------
# 2. GET /api/taxa/top
# ---------------------------------------------------------------------------

@router.get(
    "/top",
    response_model=list[TopTaxonResult],
    summary="Get top taxa for filtered samples",
    description=(
        "在满足样品筛选条件的子集中，按平均丰度返回 top N taxa。\n"
        "`rank` 为必填参数，决定返回哪个层级的 taxa。"
    ),
)
def get_top_taxa(
    rank:                str           = Query(..., description=f"必填。层级，合法值：{sorted(VALID_RANKS)}"),
    dynasty:             Optional[str] = Query(None, description="按朝代筛选样品"),
    province:            Optional[str] = Query(None, description="按省份筛选样品"),
    region:              Optional[str] = Query(None, description="按大区筛选样品"),
    sex:                 Optional[str] = Query(None, description="按性别筛选样品"),
    subsistence_pattern: Optional[str] = Query(None, description="按生业模式筛选样品"),
    top_n:               int           = Query(20, ge=1, le=100, description="返回前 N 条，默认 20"),
    abundance_type:      str           = Query(
        "relative_abundance_all",
        description="排序依据：relative_abundance_all（默认）或 relative_abundance_lvl",
    ),
    db: Session = Depends(get_db),
) -> list[TopTaxonResult]:
    _require_valid_rank(rank, required=True)
    _require_valid_abundance_type(abundance_type)

    return taxa_service.get_top_taxa(
        db=db,
        rank=rank,
        dynasty=dynasty,
        province=province,
        region=region,
        sex=sex,
        subsistence_pattern=subsistence_pattern,
        top_n=top_n,
        abundance_type=abundance_type,
    )


# ---------------------------------------------------------------------------
# 3. GET /api/taxa/{taxid}/distribution
# ---------------------------------------------------------------------------

@router.get(
    "/{taxid}/distribution",
    response_model=TaxonDistributionResponse,
    summary="Get taxon abundance distribution across groups",
    description=(
        "查询某个 taxon 在 group_by 维度（dynasty/province/region/subsistence_pattern）"
        "下各组的丰度统计分布（均值、中位、最小、最大、样品数）。\n"
        "taxid 不存在时返回 404。"
    ),
)
def get_taxon_distribution(
    taxid:               str,
    group_by:            str           = Query(
        "dynasty",
        description=f"分组维度。合法值：{sorted(VALID_GROUP_BY)}",
    ),
    rank:                Optional[str] = Query(
        None,
        description="可选。同一 taxid 有多 rank 时用于过滤，如 'genus'",
    ),
    dynasty:             Optional[str] = Query(None, description="仅含此朝代的样品"),
    province:            Optional[str] = Query(None, description="仅含此省份的样品"),
    region:              Optional[str] = Query(None, description="仅含此大区的样品"),
    sex:                 Optional[str] = Query(None, description="仅含此性别的样品"),
    subsistence_pattern: Optional[str] = Query(None, description="仅含此生业模式的样品"),
    abundance_type:      str           = Query(
        "relative_abundance_all",
        description="丰度字段：relative_abundance_all（默认）或 relative_abundance_lvl",
    ),
    db: Session = Depends(get_db),
) -> TaxonDistributionResponse:
    _require_valid_group_by(group_by)
    _require_valid_rank(rank)
    _require_valid_abundance_type(abundance_type)

    result = taxa_service.get_taxon_distribution(
        db=db,
        taxid=taxid,
        group_by=group_by,
        rank=rank,
        dynasty=dynasty,
        province=province,
        region=region,
        sex=sex,
        subsistence_pattern=subsistence_pattern,
        abundance_type=abundance_type,
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Taxon with taxid='{taxid}'"
                   + (f" and rank='{rank}'" if rank else "")
                   + " not found.",
        )

    return result
