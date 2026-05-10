'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import dynamic from 'next/dynamic';
import { getSample, getSampleTaxa } from '@/lib/api';
import type { Sample, SampleTaxonProfileResult } from '@/types/api';

const ReactECharts = dynamic(() => import('echarts-for-react'), { ssr: false });

const RANKS = ['', 'phylum', 'class', 'order', 'family', 'genus', 'species'];
const TOP_NS = [10, 20, 50];

function MetaRow({ label, value }: { label: string; value: string | number | null | undefined }) {
  return (
    <div className="flex gap-2 py-2 border-b border-gray-100 last:border-0 items-center hover:bg-gray-50 transition-colors px-2 -mx-2 rounded">
      <span className="w-1/3 text-xs font-medium text-gray-500 shrink-0">{label}</span>
      <span className="text-sm text-gray-900">{value ?? '—'}</span>
    </div>
  );
}

export default function SampleDetailPage({ params }: { params: { sample_id: string } }) {
  const sampleId = decodeURIComponent(params.sample_id);

  const [sample, setSample]   = useState<Sample | null>(null);
  const [taxa, setTaxa]       = useState<SampleTaxonProfileResult[]>([]);
  const [rank, setRank]       = useState('genus'); // Default to genus for meaningful bar charts
  const [topN, setTopN]       = useState(20);
  
  const [loadingSample, setLoadingSample] = useState(true);
  const [loadingTaxa, setLoadingTaxa]     = useState(false);
  const [error, setError]                 = useState<string | null>(null);

  // Load sample metadata
  useEffect(() => {
    setLoadingSample(true);
    getSample(sampleId)
      .then(setSample)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoadingSample(false));
  }, [sampleId]);

  // Load taxa
  useEffect(() => {
    // Only load taxa if sample loaded successfully (no error)
    if (error && !sample) return;
    
    setLoadingTaxa(true);
    getSampleTaxa(sampleId, { rank: rank || undefined, top_n: topN })
      .then(setTaxa)
      .catch((e: Error) => console.error("Failed to load taxa:", e))
      .finally(() => setLoadingTaxa(false));
  }, [sampleId, rank, topN, error, sample]);

  const chartOption = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params: { name: string; value: number }[]) => {
        const p = params[0];
        return `${p.name}<br/>Abundance: ${(p.value * 100).toFixed(4)}%`;
      },
    },
    grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
    xAxis: {
      type: 'category',
      data: taxa.map((t) => t.name),
      axisLabel: { rotate: 45, fontSize: 11, fontStyle: 'italic', interval: 0 },
    },
    yAxis: {
      type: 'value',
      name: 'Relative Abundance',
      axisLabel: { formatter: (v: number) => `${(v * 100).toFixed(1)}%` },
    },
    series: [{
      type: 'bar',
      data: taxa.map((t) => t.relative_abundance_all),
      itemStyle: { color: '#6366f1', borderRadius: [4, 4, 0, 0] },
    }],
  };

  if (loadingSample) return (
    <div className="space-y-6">
      <div className="flex gap-4 items-center">
        <div className="h-6 w-24 bg-gray-200 rounded animate-pulse"></div>
        <div className="h-8 w-48 bg-gray-200 rounded animate-pulse"></div>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="h-96 bg-gray-100 rounded-xl animate-pulse lg:col-span-1" />
        <div className="h-96 bg-gray-100 rounded-xl animate-pulse lg:col-span-2" />
      </div>
    </div>
  );

  if (error || !sample) return (
    <div className="max-w-2xl mx-auto mt-12 bg-white rounded-xl border border-red-200 shadow-sm overflow-hidden text-center">
      <div className="bg-red-50 p-6 border-b border-red-200">
        <h2 className="text-xl font-bold text-red-800">Sample Not Found</h2>
        <p className="text-sm text-red-600 mt-2">
          {error || `Could not find any data for sample ID '${sampleId}'.`}
        </p>
      </div>
      <div className="p-6">
        <Link 
          href="/samples" 
          className="inline-flex items-center justify-center px-6 py-2.5 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors font-medium shadow-sm"
        >
          ← Back to Samples List
        </Link>
      </div>
    </div>
  );

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center gap-3 border-b border-gray-200 pb-4">
        <Link 
          href="/samples" 
          className="text-sm font-medium text-gray-500 hover:text-indigo-600 transition-colors flex items-center gap-1 bg-gray-50 hover:bg-gray-100 px-3 py-1.5 rounded-lg border border-gray-200"
        >
          ← Back
        </Link>
        <div className="h-6 w-px bg-gray-300 mx-2"></div>
        <h1 className="text-2xl font-bold text-gray-900 font-mono tracking-tight">{sample.sample_id}</h1>
        {sample.dynasty && (
          <span className="px-3 py-1 bg-indigo-100 text-indigo-800 text-xs font-semibold rounded-full border border-indigo-200 shadow-sm ml-2">
            {sample.dynasty} Dynasty
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Metadata Sidebar */}
        <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm h-fit lg:col-span-1 sticky top-20">
          <h2 className="text-sm font-bold text-gray-800 mb-4 uppercase tracking-wider flex items-center gap-2">
            <span className="w-1.5 h-4 bg-indigo-500 rounded-full"></span>
            Sample Metadata
          </h2>
          <div className="space-y-1">
            <MetaRow label="Dynasty"        value={sample.dynasty} />
            <MetaRow label="Period"         value={sample.period} />
            <MetaRow label="Estimated Year" value={sample.estimated_year} />
            <MetaRow label="Province"       value={sample.province} />
            <MetaRow label="Region"         value={sample.region} />
            <MetaRow label="Site"           value={sample.site_name} />
            <MetaRow label="Lat / Lon"      value={sample.latitude != null ? `${sample.latitude.toFixed(4)}, ${sample.longitude?.toFixed(4)}` : null} />
            <MetaRow label="Sex"            value={sample.sex} />
            <MetaRow label="Subsistence"    value={sample.subsistence_pattern} />
            <MetaRow label="Source"         value={sample.source} />
          </div>
        </div>

        {/* Chart and Table Area */}
        <div className="lg:col-span-2 space-y-6">
          
          {/* Controls */}
          <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm flex flex-wrap items-center justify-between gap-4">
            <h2 className="text-sm font-bold text-gray-800 uppercase tracking-wider flex items-center gap-2">
               <span className="w-1.5 h-4 bg-indigo-500 rounded-full"></span>
               Microbiome Profile
            </h2>
            <div className="flex gap-4">
              <label className="flex items-center gap-2 text-sm text-gray-600">
                <span className="font-medium">Rank:</span>
                <select
                  value={rank}
                  onChange={(e) => setRank(e.target.value)}
                  className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm bg-white focus:ring-2 focus:ring-indigo-300 outline-none w-32"
                >
                  {RANKS.map((r) => (
                    <option key={r} value={r}>{r || 'All ranks'}</option>
                  ))}
                </select>
              </label>
              <label className="flex items-center gap-2 text-sm text-gray-600">
                <span className="font-medium">Show:</span>
                <select
                  value={topN}
                  onChange={(e) => setTopN(Number(e.target.value))}
                  className="border border-gray-200 rounded-lg px-3 py-1.5 text-sm bg-white focus:ring-2 focus:ring-indigo-300 outline-none w-24"
                >
                  {TOP_NS.map((n) => <option key={n} value={n}>Top {n}</option>)}
                </select>
              </label>
            </div>
          </div>

          {/* Bar chart */}
          <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
            {loadingTaxa ? (
              <div className="h-80 flex items-center justify-center">
                 <div className="text-indigo-500 flex flex-col items-center gap-3">
                   <div className="w-8 h-8 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin"></div>
                   <span className="text-sm font-medium">Loading composition...</span>
                 </div>
              </div>
            ) : taxa.length > 0 ? (
              <ReactECharts option={chartOption} style={{ height: 350 }} />
            ) : (
              <div className="h-80 flex items-center justify-center flex-col gap-2">
                <span className="text-4xl">🧫</span>
                <span className="text-sm text-gray-400 font-medium">No taxonomic records found for this rank.</span>
              </div>
            )}
          </div>

          {/* Taxa table */}
          <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-100 flex justify-between items-center bg-gray-50">
              <h3 className="text-sm font-semibold text-gray-700">Detailed Abundance ({taxa.length} taxa)</h3>
            </div>
            <div className="overflow-x-auto max-h-[500px] overflow-y-auto">
              <table className="w-full text-left text-sm whitespace-nowrap">
                <thead className="bg-white border-b border-gray-200 sticky top-0 z-10 shadow-sm">
                  <tr>
                    {['Taxon Name', 'Rank', 'Tax ID', 'Reads (Clade)', 'Rel. Abundance'].map((h, i) => (
                      <th key={h} className={`px-4 py-3 text-xs font-bold text-gray-500 uppercase tracking-wider ${i > 2 ? 'text-right' : ''}`}>
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {taxa.map((t) => (
                    <tr key={`${t.taxid}-${t.name}`} className="hover:bg-indigo-50/50 transition-colors">
                      <td className="px-4 py-2.5 italic text-gray-900 font-medium">{t.name}</td>
                      <td className="px-4 py-2.5">
                        <span className="px-2 py-0.5 bg-gray-100 text-gray-600 rounded text-xs font-medium border border-gray-200/60">
                          {t.rank}
                        </span>
                      </td>
                      <td className="px-4 py-2.5 font-mono text-xs text-gray-400">{t.taxid}</td>
                      <td className="px-4 py-2.5 text-right font-mono text-gray-600">{t.reads_all.toLocaleString()}</td>
                      <td className="px-4 py-2.5 text-right font-mono font-medium text-indigo-700">
                        {(t.relative_abundance_all * 100).toFixed(4)}%
                      </td>
                    </tr>
                  ))}
                  {!loadingTaxa && taxa.length === 0 && (
                    <tr>
                      <td colSpan={5} className="px-4 py-8 text-center text-gray-400 text-sm">
                        No records available to display in table.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
