"""
backend/app/api/routers/summary.py
-------------------------------------
/api/summary 路由 — 全局统计摘要
"""
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Sample, Taxon, TaxonomyAbundance

router = APIRouter()


@router.get("", summary="Global database summary")
def get_summary(db: Session = Depends(get_db)):
    """
    返回数据库整体统计摘要：
    - sample_count          总样品数
    - taxon_count           唯一 taxon 数
    - abundance_count       Abundance 记录总数
    - dynasty_count         涉及朝代数
    - province_count        涉及省份数
    - dynasty_distribution  各朝代样品数列表
    - province_distribution 各省份样品数列表
    - rank_distribution     各 rank 的 taxon 数列表
    """
    n_samples   = db.query(Sample).count()
    n_taxa      = db.query(Taxon).count()
    n_abundance = db.query(TaxonomyAbundance).count()

    # ---- 朝代分布 ----------------------------------------------------------
    dynasty_dist = (
        db.query(Sample.dynasty, func.count(Sample.id).label("count"))
        .filter(Sample.dynasty.isnot(None))
        .group_by(Sample.dynasty)
        .order_by(func.count(Sample.id).desc())
        .all()
    )

    # ---- 省份分布 ----------------------------------------------------------
    province_dist = (
        db.query(Sample.province, func.count(Sample.id).label("count"))
        .filter(Sample.province.isnot(None))
        .group_by(Sample.province)
        .order_by(func.count(Sample.id).desc())
        .all()
    )

    # ---- 采样点位：按经纬度聚合 ------------------------------------------
    location_rows = (
        db.query(
            Sample.latitude,
            Sample.longitude,
            Sample.province,
            Sample.region,
            Sample.dynasty,
            func.count(Sample.id).label("count"),
        )
        .filter(Sample.latitude.isnot(None), Sample.longitude.isnot(None))
        .group_by(Sample.latitude, Sample.longitude, Sample.province, Sample.region, Sample.dynasty)
        .order_by(func.count(Sample.id).desc())
        .all()
    )

    # ---- rank 分布（各层级 taxon 数量）--------------------------------------
    rank_dist = (
        db.query(Taxon.rank, func.count(Taxon.id).label("count"))
        .group_by(Taxon.rank)
        .order_by(func.count(Taxon.id).desc())
        .all()
    )

    return {
        "sample_count":    n_samples,
        "taxon_count":     n_taxa,
        "abundance_count": n_abundance,
        "dynasty_count":   len(dynasty_dist),
        "province_count":  len(province_dist),
        "dynasty_distribution": [
            {"group": d, "count": c} for d, c in dynasty_dist
        ],
        "province_distribution": [
            {"group": p, "count": c} for p, c in province_dist
        ],
        "rank_distribution": [
            {"rank": r, "count": c} for r, c in rank_dist
        ],
        "sample_locations": [
            {
                "latitude": lat,
                "longitude": lon,
                "province": province,
                "region": region,
                "dynasty": dynasty,
                "count": count,
            }
            for lat, lon, province, region, dynasty, count in location_rows
        ],
    }
