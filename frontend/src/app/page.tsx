'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import dynamic from 'next/dynamic';
import { getSummary } from '@/lib/api';
import type { SummaryResponse } from '@/types/api';

const ReactECharts = dynamic(() => import('echarts-for-react'), { ssr: false });

function StatCard({ label, value }: { label: string; value: number | string }) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 flex flex-col gap-1 shadow-sm transition-shadow hover:shadow-md">
      <span className="text-3xl font-bold text-indigo-700">
        {typeof value === 'number' ? value.toLocaleString() : value}
      </span>
      <span className="text-sm text-gray-500">{label}</span>
    </div>
  );
}

const QUICK_LINKS = [
  { href: '/samples',          label: '→ Browse all samples',          desc: 'Filter by dynasty, region, sex, and more' },
  { href: '/taxa',             label: '→ Search & explore taxa',       desc: 'Find top taxa and compare groups' },
  { href: '/taxa/distribution',label: '→ Taxon distribution charts',   desc: 'Cross-group abundance visualizations' },
  { href: '/ai-query',         label: '→ AI query assistant',          desc: 'Ask questions in natural language' },
];

export default function DashboardPage() {
  const [data, setData] = useState<SummaryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  useEffect(() => {
    setLoading(true);
    getSummary()
      .then(setData)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const getBarChartOption = (title: string, dataArray: { group: string; count: number }[]) => {
    const sortedData = [...dataArray].sort((a, b) => b.count - a.count);
    return {
      title: { text: title, textStyle: { fontSize: 14, color: '#374151' } },
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
      xAxis: {
        type: 'category',
        data: sortedData.map(d => d.group),
        axisLabel: { rotate: 30, interval: 0, textStyle: { fontSize: 11 } }
      },
      yAxis: { type: 'value', name: 'Samples' },
      series: [
        {
          name: 'Samples',
          type: 'bar',
          data: sortedData.map(d => d.count),
          itemStyle: { color: '#6366f1', borderRadius: [4, 4, 0, 0] },
          label: { show: true, position: 'top', color: '#6b7280', fontSize: 10 }
        }
      ]
    };
  };

  return (
    <div className="space-y-10">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">EAAM Database</h1>
        <p className="mt-2 text-gray-500 max-w-2xl">
          Ancient Chinese Dental Calculus Microbiome — explore microbial composition
          across dynasties, regions, and subsistence patterns.
        </p>
      </div>

      {/* States */}
      {error && (
        <div className="bg-red-50 text-red-700 border border-red-200 rounded-lg px-4 py-3 text-sm">
          Failed to load summary: {error}
        </div>
      )}

      {loading && !error && (
        <div className="space-y-8 animate-pulse">
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="h-28 bg-gray-100 rounded-xl" />
            ))}
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="h-80 bg-gray-100 rounded-xl" />
            <div className="h-80 bg-gray-100 rounded-xl" />
          </div>
        </div>
      )}

      {data && !loading && (
        <>
          {/* Stats Cards */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
            <StatCard label="Total Samples" value={data.sample_count} />
            <StatCard label="Total Taxa" value={data.taxon_count} />
            <StatCard label="Abundance Rows" value={data.abundance_count} />
            <StatCard label="Dynasties" value={data.dynasty_count} />
            <StatCard label="Provinces" value={data.province_count} />
          </div>

          {/* Charts */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
              <ReactECharts 
                option={getBarChartOption('Samples by Dynasty', data.dynasty_distribution)} 
                style={{ height: 320 }} 
              />
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
              <ReactECharts 
                option={getBarChartOption('Samples by Province', data.province_distribution)} 
                style={{ height: 320 }} 
              />
            </div>
          </div>

          {/* Rank Distribution & Quick Links */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            
            {/* Rank counts table */}
            <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm lg:col-span-1">
              <h2 className="text-base font-semibold text-gray-700 mb-4">Taxa by Rank</h2>
              <div className="overflow-x-auto">
                <table className="w-full text-sm text-left">
                  <thead className="bg-gray-50 border-b border-gray-100">
                    <tr>
                      <th className="px-3 py-2 text-xs font-semibold text-gray-500 uppercase">Rank</th>
                      <th className="px-3 py-2 text-xs font-semibold text-gray-500 uppercase text-right">Count</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100">
                    {data.rank_distribution.map((r) => (
                      <tr key={r.rank} className="hover:bg-indigo-50 transition-colors">
                        <td className="px-3 py-2 text-gray-700 capitalize">{r.rank}</td>
                        <td className="px-3 py-2 text-gray-600 font-mono text-right">{r.count.toLocaleString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Quick links */}
            <div className="lg:col-span-2">
              <h2 className="text-base font-semibold text-gray-700 mb-3">Explore</h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {QUICK_LINKS.map(({ href, label, desc }) => (
                  <Link
                    key={href}
                    href={href}
                    className="block bg-white rounded-xl border border-gray-200 p-5 hover:border-indigo-300 hover:shadow-md transition-all group h-full"
                  >
                    <p className="text-sm font-medium text-indigo-700 group-hover:text-indigo-800">{label}</p>
                    <p className="text-xs text-gray-500 mt-1">{desc}</p>
                  </Link>
                ))}
              </div>
            </div>

          </div>
        </>
      )}
    </div>
  );
}
