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

REGION_COORDINATES = {
    "China": (35.8617, 104.1954),
    "East Asia": (35.0, 105.0),
    "North China": (39.9, 116.4),
    "South China": (23.1, 113.3),
    "East China": (31.2, 121.5),
    "Central China": (30.6, 114.3),
    "Northwest China": (36.1, 103.8),
    "Southwest China": (30.7, 104.1),
    "Northeast China": (41.8, 123.4),
    "中国": (35.8617, 104.1954),
    "东亚": (35.0, 105.0),
    "华北": (39.9, 116.4),
    "华南": (23.1, 113.3),
    "华东": (31.2, 121.5),
    "华中": (30.6, 114.3),
    "西北": (36.1, 103.8),
    "西南": (30.7, 104.1),
    "东北": (41.8, 123.4),
}

PROVINCE_COORDINATES = {
    "Anhui": (31.86, 117.28), "安徽": (31.86, 117.28),
    "Beijing": (39.90, 116.41), "北京": (39.90, 116.41),
    "Chongqing": (29.56, 106.55), "重庆": (29.56, 106.55),
    "Fujian": (26.08, 119.30), "福建": (26.08, 119.30),
    "Gansu": (36.06, 103.83), "甘肃": (36.06, 103.83),
    "Guangdong": (23.13, 113.27), "广东": (23.13, 113.27),
    "Guangxi": (22.82, 108.32), "广西": (22.82, 108.32),
    "Guizhou": (26.65, 106.63), "贵州": (26.65, 106.63),
    "Hainan": (20.02, 110.35), "海南": (20.02, 110.35),
    "Hebei": (38.04, 114.51), "河北": (38.04, 114.51),
    "Heilongjiang": (45.80, 126.53), "黑龙江": (45.80, 126.53),
    "Henan": (34.76, 113.65), "河南": (34.76, 113.65),
    "Hubei": (30.59, 114.30), "湖北": (30.59, 114.30),
    "Hunan": (28.23, 112.94), "湖南": (28.23, 112.94),
    "Inner Mongolia": (40.82, 111.77), "内蒙古": (40.82, 111.77),
    "Jiangsu": (32.06, 118.76), "江苏": (32.06, 118.76),
    "Jiangxi": (28.68, 115.86), "江西": (28.68, 115.86),
    "Jilin": (43.82, 125.32), "吉林": (43.82, 125.32),
    "Liaoning": (41.80, 123.43), "辽宁": (41.80, 123.43),
    "Ningxia": (38.49, 106.23), "宁夏": (38.49, 106.23),
    "Qinghai": (36.62, 101.78), "青海": (36.62, 101.78),
    "Shaanxi": (34.34, 108.94), "陕西": (34.34, 108.94),
    "Shandong": (36.67, 117.02), "山东": (36.67, 117.02),
    "Shanghai": (31.23, 121.47), "上海": (31.23, 121.47),
    "Shanxi": (37.87, 112.55), "山西": (37.87, 112.55),
    "Sichuan": (30.65, 104.07), "四川": (30.65, 104.07),
    "Tianjin": (39.08, 117.20), "天津": (39.08, 117.20),
    "Tibet": (29.65, 91.13), "西藏": (29.65, 91.13),
    "Xinjiang": (43.82, 87.62), "新疆": (43.82, 87.62),
    "Yunnan": (25.04, 102.71), "云南": (25.04, 102.71),
    "Zhejiang": (30.27, 120.15), "浙江": (30.27, 120.15),
    "Japan": (35.68, 139.76), "日本": (35.68, 139.76),
    "Korea": (37.57, 126.98), "韩国": (37.57, 126.98), "朝鲜半岛": (37.57, 126.98),
    "Mongolia": (47.92, 106.92), "蒙古": (47.92, 106.92),
}


def _fallback_coordinates(province: str | None, region: str | None) -> tuple[float, float] | None:
    if province:
        match = PROVINCE_COORDINATES.get(province.strip())
        if match:
            return match
    if region:
        match = REGION_COORDINATES.get(region.strip()) or PROVINCE_COORDINATES.get(region.strip())
        if match:
            return match
    return None


def _build_sample_locations(samples: list[Sample]) -> list[dict]:
    grouped: dict[tuple[float, float, str | None, str | None, str | None, bool], int] = {}
    for sample in samples:
        estimated = False
        if sample.latitude is not None and sample.longitude is not None:
            latitude = sample.latitude
            longitude = sample.longitude
        else:
            fallback = _fallback_coordinates(sample.province, sample.region)
            if fallback is None:
                continue
            latitude, longitude = fallback
            estimated = True
        key = (round(latitude, 5), round(longitude, 5), sample.province, sample.region, sample.dynasty, estimated)
        grouped[key] = grouped.get(key, 0) + 1

    return [
        {
            "latitude": lat,
            "longitude": lon,
            "province": province,
            "region": region,
            "dynasty": dynasty,
            "count": count,
            "estimated": estimated,
        }
        for (lat, lon, province, region, dynasty, estimated), count in sorted(
            grouped.items(),
            key=lambda item: item[1],
            reverse=True,
        )
    ]


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

    # ---- 采样点位：优先使用样品经纬度，缺失时按省份/地区中心点展示 ----------
    samples_for_map = db.query(Sample).all()

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
        "sample_locations": _build_sample_locations(samples_for_map),
    }
