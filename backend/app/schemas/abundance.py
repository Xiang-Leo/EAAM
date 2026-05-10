"""
backend/app/schemas/abundance.py
---------------------------------
TaxonomyAbundance 相关 Pydantic v2 schemas，
包括原始读取结果、样品-Taxon 组合结果和分析结果。
"""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field

from .taxon import TaxonRead
from .sample import SampleRead


# ---------------------------------------------------------------------------
# 原始 abundance 读取 schema
# ---------------------------------------------------------------------------

class TaxonomyAbundanceRead(BaseModel):
    """
    从 taxonomy_abundance 表读取的单条记录。
    含关联的 Sample 和 Taxon 摘要，适用于详情展示。
    """

    id:                     int   = Field(..., description="记录主键")
    sample_id:              int   = Field(..., description="关联 samples.id")
    taxon_id:               int   = Field(..., description="关联 taxa.id")
    reads_all:              float = Field(..., description="clade 累计读数")
    reads_lvl:              float = Field(..., description="该层级独有读数")
    relative_abundance_all: float = Field(..., description="reads_all 相对丰度")
    relative_abundance_lvl: float = Field(..., description="reads_lvl 相对丰度")

    # 嵌套对象（由 ORM joined load 填充）
    taxon:  Optional[TaxonRead]  = None
    sample: Optional[SampleRead] = None

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# 样品 Taxon 组合结果（用于 "某样品的 top taxa" 接口）
# ---------------------------------------------------------------------------

class SampleTaxonProfileResult(BaseModel):
    """
    GET /api/samples/{sample_id}/taxa 接口的单条返回项。
    展示某样品中某 taxon 的读数与丰度，不嵌套完整对象，保持响应紧凑。
    """

    taxid:                  str   = Field(..., description="NCBI Taxonomy ID")
    name:                   str   = Field(..., description="分类单元名称")
    rank:                   str   = Field(..., description="层级，如 species / genus")
    reads_all:              float = Field(..., description="clade 累计读数")
    reads_lvl:              float = Field(..., description="层级独有读数")
    relative_abundance_all: float = Field(..., ge=0, description="reads_all 相对丰度 [0, 1]")
    relative_abundance_lvl: float = Field(..., ge=0, description="reads_lvl 相对丰度 [0, 1]")

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Top Taxa 分析结果（用于 "某朝代/地区 top N taxa" 接口）
# ---------------------------------------------------------------------------

class TopTaxonResult(BaseModel):
    """
    GET /api/taxa/top 接口的单条返回项。
    描述某个分组（朝代/地区）下，某 taxon 的统计汇总。
    """

    taxid:           str   = Field(..., description="NCBI Taxonomy ID")
    name:            str   = Field(..., description="分类单元名称")
    rank:            str   = Field(..., description="层级名称")
    mean_abundance:  float = Field(..., description="组内样品的平均相对丰度")
    median_abundance:float = Field(..., description="组内样品的中位相对丰度")
    sample_count:    int   = Field(..., description="包含该 taxon 的样品数量")
    total_reads:     float = Field(..., description="组内所有样品的 reads_all 合计")


# ---------------------------------------------------------------------------
# Taxon 分布分析结果（用于 "某 taxon 在各朝代/地区的分布" 接口）
# ---------------------------------------------------------------------------

class TaxonDistributionResult(BaseModel):
    """
    GET /api/taxa/{taxid}/distribution 接口的单条返回项。
    描述某 taxon 在某个分组（朝代/地区/省份）内的丰度统计分布。
    """

    group:            str   = Field(..., description="分组值，如 'Tang' / 'North'")
    mean_abundance:   float = Field(..., description="该组样品的平均相对丰度")
    median_abundance: float = Field(..., description="该组样品的中位相对丰度")
    min_abundance:    float = Field(..., description="该组样品的最小相对丰度")
    max_abundance:    float = Field(..., description="该组样品的最大相对丰度")
    sample_count:     int   = Field(..., description="该组拥有该 taxon 数据的样品数量")


# ---------------------------------------------------------------------------
# Distribution 包装响应（用于 GET /api/taxa/{taxid}/distribution）
# ---------------------------------------------------------------------------

class TaxonDistributionResponse(BaseModel):
    """
    GET /api/taxa/{taxid}/distribution 接口的完整响应体。
    包含 taxon 基本信息 + 按分组的统计分布数据。
    """

    taxid:    str = Field(..., description="NCBI Taxonomy ID")
    name:     str = Field(..., description="分类单元名称")
    rank:     str = Field(..., description="层级名称")
    group_by: str = Field(..., description="分组维度，如 dynasty / region")
    data:     list[TaxonDistributionResult] = Field(
        default_factory=list,
        description="各分组的丰度统计列表",
    )

