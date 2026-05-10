// frontend/types/api.ts
// TypeScript 类型定义，与后端 Pydantic schemas 保持一致。

// ---------------------------------------------------------------------------
// Sample
// ---------------------------------------------------------------------------

export interface Sample {
  id: number;
  sample_id: string;
  province: string | null;
  region: string | null;
  dynasty: string | null;
  period: string | null;
  estimated_year: number | null;
  sex: string | null;
  subsistence_pattern: string | null;
  site_name: string | null;
  latitude: number | null;
  longitude: number | null;
  source: string | null;
}

export interface PaginatedSamples {
  total: number;
  items: Sample[];
  page: number;
  size: number;
}

export interface SampleFilterParams {
  dynasty?: string;
  province?: string;
  region?: string;
  sex?: string;
  subsistence_pattern?: string;
  limit?: number;
  offset?: number;
}

// ---------------------------------------------------------------------------
// Taxon
// ---------------------------------------------------------------------------

export interface TaxonSearchResult {
  taxid: string;
  name: string;
  rank: string;
  lvl_type: string;
}

// ---------------------------------------------------------------------------
// Abundance
// ---------------------------------------------------------------------------

export interface SampleTaxonProfile {
  taxid: string;
  name: string;
  rank: string;
  reads_all: number;
  reads_lvl: number;
  relative_abundance_all: number;
  relative_abundance_lvl: number;
}

export interface TopTaxonResult {
  taxid: string;
  name: string;
  rank: string;
  mean_abundance: number;
  median_abundance: number;
  sample_count: number;
  total_reads: number;
}

export interface TaxonDistributionGroup {
  group: string;
  mean_abundance: number;
  median_abundance: number;
  min_abundance: number;
  max_abundance: number;
  sample_count: number;
}

export interface TaxonDistributionResponse {
  taxid: string;
  name: string;
  rank: string;
  group_by: string;
  data: TaxonDistributionGroup[];
}

// ---------------------------------------------------------------------------
// Summary
// ---------------------------------------------------------------------------

export interface DynastyCount {
  dynasty: string;
  count: number;
}

export interface SummaryResponse {
  sample_count: number;
  taxon_count: number;
  abundance_count: number;
  dynasty_distribution: DynastyCount[];
}

// ---------------------------------------------------------------------------
// AI Query
// ---------------------------------------------------------------------------

export interface SuggestedQueryPlan {
  intent: string;
  taxon_name: string | null;
  taxon_query: string | null;
  filters: Record<string, string>;
  group_by: string | null;
  rank: string | null;
  recommended_endpoint: string;
  confidence: number;
  notes: string;
}

export interface AIQueryResponse {
  question: string;
  status: string;
  message: string;
  suggested_query_plan: SuggestedQueryPlan;
}
