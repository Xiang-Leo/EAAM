"""
backend/app/schemas/sample.py
------------------------------
Sample 相关 Pydantic v2 schemas。
"""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# 基础 schema（共享字段）
# ---------------------------------------------------------------------------

class SampleBase(BaseModel):
    """Sample 表的共享字段，用于 Create / Read 的公共基类。"""

    sample_id:           str            = Field(...,   description="业务样品 ID，如 GX_Tang_1")
    province:            Optional[str]  = Field(None,  description="省份")
    region:              Optional[str]  = Field(None,  description="大区，如 North / South")
    dynasty:             Optional[str]  = Field(None,  description="朝代，如 Tang / Ming")
    period:              Optional[str]  = Field(None,  description="时期，如 Late")
    estimated_year:      Optional[int]  = Field(None,  description="估计年份（公元年，负数为 BC）")
    sex:                 Optional[str]  = Field(None,  description="性别：M / F / Unknown")
    subsistence_pattern: Optional[str]  = Field(None,  description="生业模式，如 Agriculture")
    site_name:           Optional[str]  = Field(None,  description="遗址名称")
    latitude:            Optional[float]= Field(None,  description="纬度")
    longitude:           Optional[float]= Field(None,  description="经度")
    source:              Optional[str]  = Field(None,  description="数据来源描述")


# ---------------------------------------------------------------------------
# Create schema（写入时使用）
# ---------------------------------------------------------------------------

class SampleCreate(SampleBase):
    """创建 Sample 时的请求体 schema（写入 API 使用）。"""
    pass


# ---------------------------------------------------------------------------
# Read schema（读取时使用，含数据库主键）
# ---------------------------------------------------------------------------

class SampleRead(SampleBase):
    """从数据库读取 Sample 时的响应 schema。"""

    id: int = Field(..., description="数据库自增主键")

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Filter params schema（查询参数）
# ---------------------------------------------------------------------------

class SampleFilterParams(BaseModel):
    """
    GET /api/samples 接口的筛选参数。
    所有字段均为可选，不传则不筛选。
    """

    dynasty:             Optional[str] = Field(None, description="按朝代筛选")
    region:              Optional[str] = Field(None, description="按大区筛选")
    province:            Optional[str] = Field(None, description="按省份筛选")
    sex:                 Optional[str] = Field(None, description="按性别筛选")
    subsistence_pattern: Optional[str] = Field(None, description="按生业模式筛选")

    # 分页
    page: int = Field(1,  ge=1,         description="页码，从 1 开始")
    size: int = Field(50, ge=1, le=200, description="每页条数，最大 200")


# ---------------------------------------------------------------------------
# Paginated response
# ---------------------------------------------------------------------------

class PaginatedSamples(BaseModel):
    """分页样品列表响应体。"""

    items: list[SampleRead]
    total: int = Field(..., description="满足筛选条件的总样品数")
    page:  int
    size:  int
