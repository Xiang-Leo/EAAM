'use client';

import { useState, useEffect, useCallback, FormEvent } from 'react';
import Link from 'next/link';
import dynamic from 'next/dynamic';
import { getTopTaxa } from '@/lib/api';
import type { TopTaxonResult, GetTopTaxaParams } from '@/types/api';

const ReactECharts = dynamic(() => import('echarts-for-react'), { ssr: false });

const RANKS        = ['phylum', 'class', 'order', 'family', 'genus', 'species'];
const DYNASTIES    = ['', 'Tang', 'Han', 'Ming', 'Zhou', 'Shang'];
const PROVINCES    = ['', 'Henan', 'Shaanxi', 'Shanxi', 'Sichuan', 'Gansu', 'Xinjiang'];
const REGIONS      = ['', 'North', 'South', 'Central', 'East', 'Southwest', 'Northwest'];
const SEXES        = ['', 'M', 'F', 'Unknown'];
const SUBSISTENCES = ['', 'Agriculture', 'Pastoralism', 'Mixed', 'Foraging'];
const TOP_NS       = [10, 20, 30, 50];

function FilterSelect({
  label, value, options, onChange,
}: {
  label: string;
  value: string | number;
  options: (string | number)[];
  onChange: (v: string) => void;
}) {
  return (
    <label className="flex flex-col gap-1 text-xs text-gray-500">
      {label}
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="border border-gray-200 rounded-lg px-2 py-1.5 text-sm text-gray-800 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-300 w-32"
      >
        {options.map((o) => (
          <option key={o} value={o}>{o || 'All'}</option>
        ))}
      </select>
    </label>
  );
}

export default function TaxaPage() {
  const [filters, setFilters] = useState<GetTopTaxaParams>({
    rank: 'genus',
    top_n: 20,
  });

  const [rank, setRank]               = useState('genus');
  const [dynasty, setDynasty]         = useState('');
  const [province, setProvince]       = useState('');
  const [region, setRegion]           = useState('');
  const [sex, setSex]                 = useState('');
  const [subsistence, setSubsistence] = useState('');
  const [topN, setTopN]               = useState('20');

  const [data, setData]       = useState<TopTaxonResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    getTopTaxa(filters)
      .then(setData)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [filters]);

  useEffect(() => {
    load();
  }, [load]);

  const handleSearch = (e?: FormEvent) => {
    if (e) e.preventDefault();
    setFilters({
      rank,
      dynasty: dynasty || undefined,
      province: province || undefined,
      region: region || undefined,
      sex: sex || undefined,
      subsistence_pattern: subsistence || undefined,
      top_n: Number(topN),
    });
  };

  const handleReset = () => {
    setRank('genus');
    setDynasty('');
    setProvince('');
    setRegion('');
    setSex('');
    setSubsistence('');
    setTopN('20');
    setFilters({ rank: 'genus', top_n: 20 });
  };

  const chartOption = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params: { name: string; value: number }[]) => {
        const p = params[0];
        return `${p.name}<br/>Mean Abundance: ${(p.value * 100).toFixed(4)}%`;
      },
    },
    grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
    xAxis: {
      type: 'category',
      data: data.map((d) => d.name),
      axisLabel: { rotate: 35, fontSize: 11, fontStyle: 'italic', interval: 0 },
    },
    yAxis: {
      type: 'value',
      name: 'Mean Rel. Abundance',
      axisLabel: { formatter: (v: number) => `${(v * 100).toFixed(1)}%` },
    },
    series: [{
      type: 'bar',
      data: data.map((d) => d.mean_abundance),
      itemStyle: { color: '#6366f1', borderRadius: [4, 4, 0, 0] },
    }],
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Top Taxa Explorer</h1>
        <p className="text-sm text-gray-500 mt-1">Discover the most abundant taxa across filtered sample groups.</p>
      </div>

      {/* Query Form */}
      <form onSubmit={handleSearch} className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm">
        <div className="flex flex-wrap gap-4 items-end">
          <FilterSelect label="Rank (Required)" value={rank} options={RANKS} onChange={setRank} />
          <FilterSelect label="Dynasty" value={dynasty} options={DYNASTIES} onChange={setDynasty} />
          <FilterSelect label="Province" value={province} options={PROVINCES} onChange={setProvince} />
          <FilterSelect label="Region" value={region} options={REGIONS} onChange={setRegion} />
          <FilterSelect label="Sex" value={sex} options={SEXES} onChange={setSex} />
          <FilterSelect label="Subsistence" value={subsistence} options={SUBSISTENCES} onChange={setSubsistence} />
          <FilterSelect label="Top N" value={topN} options={TOP_NS} onChange={setTopN} />
          
          <div className="flex gap-2">
            <button
              type="submit"
              className="px-5 py-1.5 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700 transition-colors font-medium shadow-sm"
            >
              Analyze
            </button>
            <button
              type="button"
              onClick={handleReset}
              className="px-4 py-1.5 text-sm border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
            >
              Reset
            </button>
          </div>
        </div>
      </form>

      {error && (
        <div className="bg-red-50 text-red-700 border border-red-200 rounded-lg px-4 py-3 text-sm">
          {error}
        </div>
      )}

      {/* Charts & Table Area */}
      {!error && (
        <div className="space-y-6">
          
          {/* Bar chart */}
          <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
            <h2 className="text-sm font-semibold text-gray-700 mb-3 uppercase tracking-wider flex items-center gap-2">
               <span className="w-1.5 h-4 bg-indigo-500 rounded-full"></span>
               Top {filters.top_n} {filters.rank}s (by Mean Abundance)
            </h2>
            {loading ? (
              <div className="h-80 flex items-center justify-center">
                 <div className="text-indigo-500 flex flex-col items-center gap-3">
                   <div className="w-8 h-8 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin"></div>
                   <span className="text-sm font-medium">Aggregating data...</span>
                 </div>
              </div>
            ) : data.length > 0 ? (
              <ReactECharts option={chartOption} style={{ height: 350 }} />
            ) : (
              <div className="h-80 flex items-center justify-center flex-col gap-2">
                <span className="text-4xl">🧫</span>
                <span className="text-sm text-gray-400 font-medium">No taxonomic records found for this subset.</span>
              </div>
            )}
          </div>

          {/* Table */}
          <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
             <div className="px-6 py-4 border-b border-gray-100 bg-gray-50">
              <h3 className="text-sm font-semibold text-gray-700">Abundance Statistics ({data.length} records)</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm whitespace-nowrap">
                <thead className="bg-white border-b border-gray-200">
                  <tr>
                    <th className="px-4 py-3 text-xs font-bold text-gray-500 uppercase">Taxon Name</th>
                    <th className="px-4 py-3 text-xs font-bold text-gray-500 uppercase">Tax ID</th>
                    <th className="px-4 py-3 text-xs font-bold text-gray-500 uppercase text-right">Mean Abundance</th>
                    <th className="px-4 py-3 text-xs font-bold text-gray-500 uppercase text-right">Median Abundance</th>
                    <th className="px-4 py-3 text-xs font-bold text-gray-500 uppercase text-right">Prevalence (Samples)</th>
                    <th className="px-4 py-3 text-xs font-bold text-gray-500 uppercase text-right">Total Reads</th>
                    <th className="px-4 py-3 text-xs font-bold text-gray-500 uppercase text-center">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {loading ? (
                    <tr>
                      <td colSpan={7} className="px-4 py-12 text-center text-sm text-gray-400 animate-pulse">
                        Calculating statistics...
                      </td>
                    </tr>
                  ) : data.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="px-4 py-8 text-center text-sm text-gray-400">
                        No records available.
                      </td>
                    </tr>
                  ) : (
                    data.map((t) => (
                      <tr key={t.taxid} className="hover:bg-indigo-50/50 transition-colors">
                        <td className="px-4 py-2.5 italic text-gray-900 font-medium">{t.name}</td>
                        <td className="px-4 py-2.5 font-mono text-xs text-gray-400">{t.taxid}</td>
                        <td className="px-4 py-2.5 text-right font-mono font-medium text-indigo-700">
                          {(t.mean_abundance * 100).toFixed(4)}%
                        </td>
                        <td className="px-4 py-2.5 text-right font-mono text-gray-600">
                          {(t.median_abundance * 100).toFixed(4)}%
                        </td>
                        <td className="px-4 py-2.5 text-right text-gray-800">{t.sample_count}</td>
                        <td className="px-4 py-2.5 text-right font-mono text-gray-600">
                          {t.total_reads.toLocaleString()}
                        </td>
                        <td className="px-4 py-2.5 text-center">
                          <Link
                            href={`/taxa/distribution?taxid=${t.taxid}&rank=${filters.rank}`}
                            className="inline-block px-3 py-1 bg-white border border-gray-200 text-indigo-600 hover:bg-indigo-50 hover:border-indigo-200 text-xs rounded transition-colors"
                          >
                            View distribution →
                          </Link>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
          
        </div>
      )}
    </div>
  );
}
