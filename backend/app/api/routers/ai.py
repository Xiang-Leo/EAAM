"""
backend/app/api/routers/ai.py
--------------------------------
/api/ai 路由。

端点：
  POST /api/ai/query  — 自然语言查询（第一阶段：规则引擎占位）
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.ai_service import process_ai_query

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / Response schemas（局部定义，避免与全局 schemas 耦合）
# ---------------------------------------------------------------------------

class AIQueryRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="自然语言查询问题，例如：'请帮我查看唐代样品中 Actinomyces 的丰度'",
        examples=["请帮我查看唐代样品中 Actinomyces 的丰度"],
    )


class SuggestedQueryPlan(BaseModel):
    intent:               str            = Field(..., description="识别出的意图")
    taxon_name:           Optional[str]  = Field(None, description="提取的 taxon 名称")
    taxon_query:          Optional[str]  = Field(None, description="供搜索接口使用的查询词")
    filters:              dict[str, Any] = Field(default_factory=dict, description="样品过滤条件")
    group_by:             Optional[str]  = Field(None, description="推断的分组维度")
    rank:                 Optional[str]  = Field(None, description="推断的分类层级")
    recommended_endpoint: str            = Field(..., description="推荐调用的 REST 端点")
    confidence:           float          = Field(..., ge=0, le=1, description="规则匹配置信度")
    notes:                str            = Field("", description="额外说明或操作建议")


class AIQueryResponse(BaseModel):
    question:             str                = Field(..., description="原始问题")
    status:               str                = Field(..., description="处理状态：placeholder / success / error")
    message:              str                = Field(..., description="状态说明")
    suggested_query_plan: SuggestedQueryPlan = Field(..., description="结构化查询计划")


# ---------------------------------------------------------------------------
# POST /api/ai/query
# ---------------------------------------------------------------------------

@router.post(
    "/query",
    response_model=AIQueryResponse,
    summary="AI natural language query (rule-based MVP)",
    description=(
        "接受自然语言问题，返回结构化查询计划和推荐 API 端点。\n\n"
        "**第一阶段**：使用规则引擎识别意图（taxon 名称、朝代、大区等关键词匹配），"
        "不调用真实大模型。\n\n"
        "**未来计划**：将底层 `RuleBasedQueryPlanner` 替换为 `DeepSeekQueryPlanner`，"
        "接口不变。"
    ),
)
def ai_query(request: AIQueryRequest) -> AIQueryResponse:
    result = process_ai_query(request.question)

    return AIQueryResponse(
        question=result.question,
        status=result.status,
        message=result.message,
        suggested_query_plan=SuggestedQueryPlan(
            intent=result.suggested_query_plan.intent,
            taxon_name=result.suggested_query_plan.taxon_name,
            taxon_query=result.suggested_query_plan.taxon_query,
            filters=result.suggested_query_plan.filters,
            group_by=result.suggested_query_plan.group_by,
            rank=result.suggested_query_plan.rank,
            recommended_endpoint=result.suggested_query_plan.recommended_endpoint,
            confidence=result.suggested_query_plan.confidence,
            notes=result.suggested_query_plan.notes,
        ),
    )
