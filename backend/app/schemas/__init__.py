"""
backend/app/schemas/__init__.py
--------------------------------
统一导出所有 Pydantic schemas，方便在 API 路由中一行导入。

用法：
    from app.schemas import SampleRead, TopTaxonResult, ...
"""

# Sample
from .sample import (
    SampleBase,
    SampleCreate,
    SampleRead,
    SampleFilterParams,
    PaginatedSamples,
)

# Taxon
from .taxon import (
    TaxonBase,
    TaxonRead,
    TaxonSearchResult,
)

# Abundance
from .abundance import (
    TaxonomyAbundanceRead,
    SampleTaxonProfileResult,
    TopTaxonResult,
    TaxonDistributionResult,
    TaxonDistributionResponse,
)

__all__ = [
    # Sample
    "SampleBase",
    "SampleCreate",
    "SampleRead",
    "SampleFilterParams",
    "PaginatedSamples",
    # Taxon
    "TaxonBase",
    "TaxonRead",
    "TaxonSearchResult",
    # Abundance
    "TaxonomyAbundanceRead",
    "SampleTaxonProfileResult",
    "TopTaxonResult",
    "TaxonDistributionResult",
    "TaxonDistributionResponse",
]
