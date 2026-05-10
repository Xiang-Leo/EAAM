"""
backend/app/services/ai_service.py
-------------------------------------
AI 查询服务层。

第一阶段：基于规则的意图识别与查询计划生成。
设计原则：抽象为 BaseQueryPlanner 接口，方便未来替换为 DeepSeek / LLM 实现。
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# 数据结构
# ---------------------------------------------------------------------------

@dataclass
class QueryPlan:
    """结构化查询计划，路由层将其序列化为 JSON 返回。"""

    intent: str                          # 识别出的意图
    taxon_name:  Optional[str] = None    # 提取的 taxon 名称
    taxon_query: Optional[str] = None    # 供搜索接口使用的查询词
    filters:     dict          = field(default_factory=dict)
    group_by:    Optional[str] = None
    rank:        Optional[str] = None
    recommended_endpoint: str  = ""      # 推荐调用的 REST 端点
    confidence:  float         = 0.0     # 规则匹配置信度 [0, 1]
    notes:       str           = ""      # 额外说明


@dataclass
class AIQueryResult:
    """接口最终响应结构。"""

    question:             str
    status:               str       # "placeholder" | "success" | "error"
    message:              str
    suggested_query_plan: QueryPlan


# ---------------------------------------------------------------------------
# 抽象接口：方便未来接入 LLM
# ---------------------------------------------------------------------------

class BaseQueryPlanner(ABC):
    """
    查询计划生成器的抽象基类。

    未来接入 DeepSeek：
        class DeepSeekQueryPlanner(BaseQueryPlanner):
            def __init__(self, api_key: str, model: str = "deepseek-chat"):
                ...
            def plan(self, question: str) -> QueryPlan:
                response = deepseek_client.chat(question, system_prompt=PROMPT)
                return parse_llm_response(response)
    """

    @abstractmethod
    def plan(self, question: str) -> QueryPlan:
        """给定自然语言问题，返回结构化查询计划。"""
        ...


# ---------------------------------------------------------------------------
# 规则字典
# ---------------------------------------------------------------------------

# 常见朝代（中英文）
_DYNASTY_PATTERNS: dict[str, str] = {
    r"唐[代朝]?": "Tang",
    r"Tang":      "Tang",
    r"汉[代朝]?": "Han",
    r"Han":       "Han",
    r"明[代朝]?": "Ming",
    r"Ming":      "Ming",
    r"周[代朝]?": "Zhou",
    r"Zhou":      "Zhou",
    r"商[代朝]?": "Shang",
    r"Shang":     "Shang",
}

# 常见大区（中英文）
_REGION_PATTERNS: dict[str, str] = {
    r"北方|华北|North":     "North",
    r"南方|华南|South":     "South",
    r"中原|Central":        "Central",
    r"东部|华东|East":      "East",
    r"西南|Southwest":      "Southwest",
}

# 常见 rank 关键词
_RANK_PATTERNS: dict[str, str] = {
    r"phylum|门":   "phylum",
    r"class|纲":    "class",
    r"order|目":    "order",
    r"family|科":   "family",
    r"genus|属":    "genus",
    r"species|种":  "species",
}

# 意图关键词（越靠前优先级越高）
_INTENT_RULES: list[tuple[str, str]] = [
    (r"top|前\s*\d*\s*|最多|最丰富|最常见|top[\s_]?taxa", "top_taxa"),
    (r"分布|distribution|在哪|哪个.*多|比较", "taxon_distribution"),
    (r"样品.*列表|list.*sample|查.*样品|所有样品", "sample_list"),
    (r"样品.*详情|sample.*detail|查看.*样品\s*\w+", "sample_detail"),
    (r"搜索|search|查找|找一下", "taxon_search"),
    (r"\w+", "taxon_distribution"),          # 默认兜底
]

# 常见微生物属名（用于名称提取）
_KNOWN_TAXA: list[str] = [
    "Actinomyces", "Streptococcus", "Treponema", "Porphyromonas",
    "Fusobacterium", "Prevotella", "Veillonella", "Rothia",
    "Capnocytophaga", "Haemophilus", "Neisseria", "Bacteroidetes",
    "Firmicutes", "Proteobacteria", "Actinobacteria", "Spirochaetes",
    "Mycobacterium", "Corynebacterium", "Bifidobacterium", "Lactobacillus",
    "Clostridium", "Bacteroides", "Ruminococcus", "Akkermansia",
    "Desulfovibrio", "Campylobacter", "Helicobacter",
]


# ---------------------------------------------------------------------------
# 规则实现
# ---------------------------------------------------------------------------

class RuleBasedQueryPlanner(BaseQueryPlanner):
    """
    基于关键词匹配的规则查询计划器。

    匹配流程：
      1. 提取 taxon 名称（优先已知属名，其次启发式识别）
      2. 提取样品过滤维度（朝代、大区）
      3. 提取 rank
      4. 识别意图
      5. 生成推荐 endpoint
    """

    def plan(self, question: str) -> QueryPlan:
        filters: dict[str, str] = {}

        taxon_name  = self._extract_taxon(question)
        dynasty     = self._match_dict(question, _DYNASTY_PATTERNS)
        region      = self._match_dict(question, _REGION_PATTERNS)
        rank        = self._match_dict(question, _RANK_PATTERNS)
        intent      = self._detect_intent(question)

        if dynasty:
            filters["dynasty"] = dynasty
        if region:
            filters["region"] = region

        group_by = self._infer_group_by(question, filters)

        endpoint, confidence = self._recommend_endpoint(
            intent, taxon_name, filters, rank, group_by
        )

        notes = self._build_notes(intent, taxon_name, filters)

        return QueryPlan(
            intent=intent,
            taxon_name=taxon_name,
            taxon_query=taxon_name,
            filters=filters,
            group_by=group_by,
            rank=rank or ("genus" if intent in ("taxon_distribution", "top_taxa") else None),
            recommended_endpoint=endpoint,
            confidence=confidence,
            notes=notes,
        )

    # ---- 内部方法 ----------------------------------------------------------

    @staticmethod
    def _match_dict(text: str, patterns: dict[str, str]) -> str | None:
        for pattern, value in patterns.items():
            if re.search(pattern, text, re.IGNORECASE):
                return value
        return None

    @staticmethod
    def _extract_taxon(text: str) -> str | None:
        # 优先匹配已知属名
        for name in _KNOWN_TAXA:
            if re.search(name, text, re.IGNORECASE):
                return name

        # 启发式：连续大写开头的英文单词（可能是学名）
        matches = re.findall(r"\b[A-Z][a-z]{3,}\b", text)
        # 排除常见介词/连词/朝代
        stopwords = {"Tang", "Han", "Ming", "Zhou", "Shang", "North", "South",
                     "East", "West", "Central", "Please", "Show", "What", "Which"}
        candidates = [m for m in matches if m not in stopwords]
        return candidates[0] if candidates else None

    @staticmethod
    def _detect_intent(text: str) -> str:
        for pattern, intent in _INTENT_RULES:
            if re.search(pattern, text, re.IGNORECASE):
                return intent
        return "unknown"

    @staticmethod
    def _infer_group_by(text: str, filters: dict) -> str:
        """若问题中没有明确 group_by 关键词，根据已提取的 filter 推断。"""
        if re.search(r"province|省|省份", text, re.IGNORECASE):
            return "province"
        if re.search(r"region|大区|地区", text, re.IGNORECASE):
            return "region"
        if re.search(r"subsistence|生业|生活方式", text, re.IGNORECASE):
            return "subsistence_pattern"
        # 已过滤 dynasty 则按 province 进一步细分；否则默认按 dynasty
        if "dynasty" in filters:
            return "province"
        return "dynasty"

    @staticmethod
    def _recommend_endpoint(
        intent: str,
        taxon_name: str | None,
        filters: dict,
        rank: str | None,
        group_by: str,
    ) -> tuple[str, float]:
        """返回 (推荐端点, 置信度)。"""
        params: list[str] = []

        if intent == "taxon_search" and taxon_name:
            ep = f"/api/taxa/search?q={taxon_name}"
            return ep, 0.85

        if intent == "top_taxa":
            params.append(f"rank={rank or 'genus'}")
            params.extend(f"{k}={v}" for k, v in filters.items())
            return "/api/taxa/top?" + "&".join(params), 0.80

        if intent == "taxon_distribution" and taxon_name:
            # 先要获取 taxid，所以第一步推荐搜索接口
            ep = f"/api/taxa/search?q={taxon_name}&limit=5"
            return ep, 0.75

        if intent == "sample_list":
            params.extend(f"{k}={v}" for k, v in filters.items())
            ep = "/api/samples" + ("?" + "&".join(params) if params else "")
            return ep, 0.80

        if intent == "sample_detail":
            return "/api/samples/{sample_id}", 0.60

        # 兜底
        if taxon_name:
            return f"/api/taxa/search?q={taxon_name}", 0.50
        return "/api/taxa/search", 0.30

    @staticmethod
    def _build_notes(intent: str, taxon_name: str | None, filters: dict) -> str:
        parts = []
        if intent == "taxon_distribution" and taxon_name:
            parts.append(
                f"建议先通过 /api/taxa/search?q={taxon_name} 获取 taxid，"
                f"再调用 /api/taxa/{{taxid}}/distribution 获取分布数据。"
            )
        if not taxon_name and intent in ("taxon_distribution", "taxon_search"):
            parts.append("未能从问题中识别出 taxon 名称，请在搜索框手动输入。")
        return " ".join(parts)


# ---------------------------------------------------------------------------
# 单例：默认使用规则引擎（未来可换为 DeepSeekQueryPlanner）
# ---------------------------------------------------------------------------

_default_planner: BaseQueryPlanner = RuleBasedQueryPlanner()


def get_planner() -> BaseQueryPlanner:
    """
    返回当前激活的查询计划器。
    未来替换为 LLM 时，只需修改此处：
        return DeepSeekQueryPlanner(api_key=settings.DEEPSEEK_API_KEY)
    """
    return _default_planner


def process_ai_query(question: str) -> AIQueryResult:
    """
    主入口：给定自然语言问题，返回 AIQueryResult。
    """
    planner = get_planner()
    plan = planner.plan(question)

    return AIQueryResult(
        question=question,
        status="placeholder",
        message="AI query module is not enabled in MVP. Query plan generated by rule-based engine.",
        suggested_query_plan=plan,
    )
