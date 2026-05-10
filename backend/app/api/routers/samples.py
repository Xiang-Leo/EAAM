"""
backend/app/api/routers/samples.py
------------------------------------
/api/samples 路由。

端点：
  GET  /api/samples                     — 样品列表（分页 + 筛选）
  GET  /api/samples/{sample_id}         — 单个样品 metadata
  GET  /api/samples/{sample_id}/taxa    — 单个样品 top taxa
"""

from __future__ import annotations

from typing import Annotated, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.sample import SampleRead, PaginatedSamples
from app.schemas.abundance import SampleTaxonProfileResult
from app.services import sample_service
from app.services.sample_service import VALID_RANKS, VALID_ABUNDANCE_TYPES

router = APIRouter()


# ---------------------------------------------------------------------------
# 1. GET /api/samples
# ---------------------------------------------------------------------------

@router.get(
    "",
    response_model=PaginatedSamples,
    summary="List samples",
    description="分页查询样品列表，支持按朝代、省份、地区、性别、生业模式筛选。",
)
def list_samples(
    dynasty:             Optional[str] = Query(None, description="按朝代筛选，如 Tang"),
    province:            Optional[str] = Query(None, description="按省份筛选，如 Henan"),
    region:              Optional[str] = Query(None, description="按大区筛选，如 North"),
    sex:                 Optional[str] = Query(None, description="按性别筛选：M / F / Unknown"),
    subsistence_pattern: Optional[str] = Query(None, description="按生业模式筛选，如 Agriculture"),
    limit:               int           = Query(50, ge=1, le=500, description="每页条数"),
    offset:              int           = Query(0,  ge=0,         description="跳过条数"),
    db: Session = Depends(get_db),
) -> PaginatedSamples:
    return sample_service.get_samples(
        db=db,
        dynasty=dynasty,
        province=province,
        region=region,
        sex=sex,
        subsistence_pattern=subsistence_pattern,
        limit=limit,
        offset=offset,
    )


# ---------------------------------------------------------------------------
# 2. GET /api/samples/{sample_id}
# ---------------------------------------------------------------------------

@router.get(
    "/{sample_id}",
    response_model=SampleRead,
    summary="Get sample metadata",
    description="返回单个样品的 metadata，sample_id 不存在时返回 404。",
)
def get_sample(
    sample_id: str,
    db: Session = Depends(get_db),
) -> SampleRead:
    sample = sample_service.get_sample_by_sample_id(db, sample_id)
    if sample is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sample '{sample_id}' not found.",
        )
    return SampleRead.model_validate(sample)


# ---------------------------------------------------------------------------
# 3. GET /api/samples/{sample_id}/taxa
# ---------------------------------------------------------------------------

@router.get(
    "/{sample_id}/taxa",
    response_model=list[SampleTaxonProfileResult],
    summary="Get sample top taxa",
    description=(
        "返回指定样品中丰度最高的 top N taxon。\n"
        "可按 rank 过滤（phylum/class/order/family/genus/species），"
        "并选择按 relative_abundance_all 或 relative_abundance_lvl 排序。"
    ),
)
def get_sample_taxa(
    sample_id:      str,
    rank:           Optional[str] = Query(
        None,
        description=(
            "可选。按 rank 过滤，合法值：phylum / class / order / family / "
            "genus / genus_sublevel / species"
        ),
    ),
    top_n:          int = Query(20, ge=1, le=200, description="返回前 N 条，默认 20"),
    abundance_type: str = Query(
        "relative_abundance_all",
        description="排序依据：relative_abundance_all（默认）或 relative_abundance_lvl",
    ),
    db: Session = Depends(get_db),
) -> list[SampleTaxonProfileResult]:
    # --- 参数校验（422）---
    if rank is not None and rank not in VALID_RANKS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Invalid rank '{rank}'. "
                f"Valid values: {sorted(VALID_RANKS)}"
            ),
        )
    if abundance_type not in VALID_ABUNDANCE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Invalid abundance_type '{abundance_type}'. "
                f"Valid values: {sorted(VALID_ABUNDANCE_TYPES)}"
            ),
        )

    # --- 样品存在性检查（404）---
    sample = sample_service.get_sample_by_sample_id(db, sample_id)
    if sample is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sample '{sample_id}' not found.",
        )

    return sample_service.get_sample_taxa(
        db=db,
        sample_id=sample_id,
        rank=rank,
        top_n=top_n,
        abundance_type=abundance_type,
    )
