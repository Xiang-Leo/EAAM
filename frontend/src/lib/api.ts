// frontend/src/lib/api.ts
// 统一封装所有后端 API 调用。
// 默认使用同源 /api，由 Next.js rewrites 代理到后端；如需直连后端，可设置
// NEXT_PUBLIC_API_BASE_URL，例如 http://localhost:8000。

import type {
  SampleListResponse,
  Sample,
  SampleFilterParams,
  SampleTaxonProfileResult,
  GetSampleTaxaParams,
  TaxonSearchResult,
  TopTaxonResult,
  GetTopTaxaParams,
  TaxonDistributionResponse,
  GetTaxonDistributionParams,
  SummaryResponse,
  AIQueryResponse,
} from '@/types/api';

// ---------------------------------------------------------------------------
// 基础配置
// ---------------------------------------------------------------------------

const _rawEnv = process.env.NEXT_PUBLIC_API_BASE_URL;
export const API_BASE_URL = (_rawEnv && _rawEnv.trim() !== '' ? _rawEnv : '').replace(/\/$/, '');

// ---------------------------------------------------------------------------
// 内部工具函数
// ---------------------------------------------------------------------------

/**
 * 将参数对象序列化为 query string，自动跳过 undefined / 空字符串。
 * 例如：{ dynasty: 'Tang', sex: undefined } → "?dynasty=Tang"
 */
function toQueryString(
  params: Record<string, string | number | boolean | undefined>
): string {
  const entries = Object.entries(params).filter(
    ([, v]) => v !== undefined && v !== ''
  );
  if (entries.length === 0) return '';
  const qs = entries
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`)
    .join('&');
  return `?${qs}`;
}

/**
 * 通用 fetch 包装：
 * - 自动设置 Content-Type: application/json
 * - 非 2xx 响应抛出带 status + message 的 Error
 */
async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, {
      headers: { 'Content-Type': 'application/json' },
      ...init,
    });
  } catch (error: any) {
    throw new Error(`${error.message} [Target: ${API_BASE_URL || 'same-origin'}${path}]`);
  }

  if (!res.ok) {
    let message = `HTTP ${res.status}: ${res.statusText} [Target: ${API_BASE_URL || 'same-origin'}${path}]`;
    try {
      const body = await res.json();
      if (typeof body.detail === 'string') {
        message = body.detail;
      } else if (Array.isArray(body.detail)) {
        // FastAPI 验证错误格式
        message = body.detail.map((e: { msg: string }) => e.msg).join('; ');
      }
    } catch {
      // 忽略 JSON 解析失败
    }
    throw new Error(message);
  }

  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Summary
// ---------------------------------------------------------------------------

/** 获取数据库整体统计摘要（样品数、taxa 数、丰度记录数、朝代分布）。 */
export function getSummary(): Promise<SummaryResponse> {
  return apiFetch('/api/summary');
}

// ---------------------------------------------------------------------------
// Samples
// ---------------------------------------------------------------------------

/** 分页获取样品列表，支持按 dynasty / province / region / sex / subsistence_pattern 筛选。 */
export function getSamples(filters: SampleFilterParams = {}): Promise<SampleListResponse> {
  const qs = toQueryString(
    filters as Record<string, string | number | boolean | undefined>
  );
  return apiFetch(`/api/samples${qs}`);
}

/** 获取单个样品的 metadata，不存在时 API 返回 404 → 抛出 Error。 */
export function getSample(sampleId: string): Promise<Sample> {
  return apiFetch(`/api/samples/${encodeURIComponent(sampleId)}`);
}

/**
 * 获取单个样品的 top taxa。
 * @param sampleId - 业务样品 ID，如 GX_Tang_1
 * @param params   - 可选：rank 过滤、top_n 条数、abundance_type 排序依据
 */
export function getSampleTaxa(
  sampleId: string,
  params: GetSampleTaxaParams = {}
): Promise<SampleTaxonProfileResult[]> {
  const qs = toQueryString(
    params as unknown as Record<string, string | number | boolean | undefined>
  );
  return apiFetch(`/api/samples/${encodeURIComponent(sampleId)}/taxa${qs}`);
}

// ---------------------------------------------------------------------------
// Taxa
// ---------------------------------------------------------------------------

/**
 * 按名称模糊搜索 taxa。
 * @param q    - 搜索关键词（最少 1 个字符）
 * @param rank - 可选，按 rank 过滤
 * @param limit - 返回上限，默认 20
 */
export function searchTaxa(
  q: string,
  rank?: string,
  limit = 20
): Promise<TaxonSearchResult[]> {
  const qs = toQueryString({ q, rank, limit });
  return apiFetch(`/api/taxa/search${qs}`);
}

/**
 * 获取筛选样品集合中的 top N taxa。
 * @param params - 必须包含 rank；其余为可选样品过滤参数
 */
export function getTopTaxa(params: GetTopTaxaParams): Promise<TopTaxonResult[]> {
  const qs = toQueryString(
    params as unknown as Record<string, string | number | boolean | undefined>
  );
  return apiFetch(`/api/taxa/top${qs}`);
}

/**
 * 获取某 taxon 在指定分组维度下的丰度分布。
 * @param taxid  - NCBI Taxonomy ID（字符串）
 * @param params - group_by 等配置
 */
export function getTaxonDistribution(
  taxid: string,
  params: GetTaxonDistributionParams = {}
): Promise<TaxonDistributionResponse> {
  const qs = toQueryString(
    params as unknown as Record<string, string | number | boolean | undefined>
  );
  return apiFetch(`/api/taxa/${encodeURIComponent(taxid)}/distribution${qs}`);
}

// ---------------------------------------------------------------------------
// AI Query
// ---------------------------------------------------------------------------

/**
 * 向 AI 查询接口提交自然语言问题。
 * 第一阶段返回规则引擎的查询计划（status: "placeholder"）。
 * @param question - 自然语言问题，最长 500 字符
 */
export function askAI(question: string): Promise<AIQueryResponse> {
  return apiFetch('/api/ai/query', {
    method: 'POST',
    body: JSON.stringify({ question }),
  });
}
