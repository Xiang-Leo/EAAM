const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

export async function fetchSamples(params: Record<string, string> = {}) {
  const query = new URLSearchParams(params).toString();
  const url = `${API_BASE_URL}/samples${query ? `?${query}` : ''}`;
  const res = await fetch(url, { cache: 'no-store' });
  if (!res.ok) throw new Error('Failed to fetch samples');
  return res.json();
}

export async function fetchSampleTaxa(sampleId: string, limit: number = 20, rank: string = 'S') {
  const res = await fetch(`${API_BASE_URL}/samples/${sampleId}/taxa?limit=${limit}&rank=${rank}`, { cache: 'no-store' });
  if (!res.ok) throw new Error('Failed to fetch sample taxa');
  return res.json();
}

export async function fetchTaxonDistribution(taxid: string, groupBy: string = 'dynasty') {
  const res = await fetch(`${API_BASE_URL}/taxa/${taxid}/distribution?group_by=${groupBy}`, { cache: 'no-store' });
  if (!res.ok) throw new Error('Failed to fetch taxon distribution');
  return res.json();
}

export async function fetchTopTaxa(groupBy: string, groupValue: string, limit: number = 10, rank: string = 'S') {
  const res = await fetch(`${API_BASE_URL}/top-taxa?group_by=${groupBy}&group_value=${groupValue}&limit=${limit}&rank=${rank}`, { cache: 'no-store' });
  if (!res.ok) throw new Error('Failed to fetch top taxa');
  return res.json();
}
