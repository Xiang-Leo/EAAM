'use client';

import { useState, useEffect, useCallback, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import dynamic from 'next/dynamic';
import { searchTaxa, getTaxonDistribution } from '@/lib/api';
import type { TaxonSearchResult, TaxonDistributionResponse } from '@/types/api';

const ReactECharts = dynamic(() => import('echarts-for-react'), { ssr: false });

const GROUP_BY_OPTIONS = [
  { value: 'dynasty',             label: 'Dynasty' },
  { value: 'region',              label: 'Region' },
  { value: 'province',            label: 'Province' },
  { value: 'subsistence_pattern', label: 'Subsistence' },
];

const RANKS        = ['phylum', 'class', 'order', 'family', 'genus', 'species'];
const DYNASTIES    = ['', 'Tang', 'Han', 'Ming', 'Zhou', 'Shang'];
const PROVINCES    = ['', 'Henan', 'Shaanxi', 'Shanxi', 'Sichuan', 'Gansu', 'Xinjiang'];
const REGIONS      = ['', 'North', 'South', 'Central', 'East', 'Southwest', 'Northwest'];
const SEXES        = ['', 'M', 'F', 'Unknown'];
const SUBSISTENCES = ['', 'Agriculture', 'Pastoralism', 'Mixed', 'Foraging'];

function FilterSelect({
  label, value, options, onChange,
}: {
  label: string;
  value: string;
  options: (string)[];
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

// Inner component to handle search params
function DistributionPageContent() {
  const searchParams = useSearchParams();
  const initTaxid = searchParams.get('taxid');
  const initRank = searchParams.get('rank') || 'genus';

  // State 1: Taxon Search & Selection
  const [q, setQ] = useState('');
  const [searchRank, setSearchRank] = useState('genus');
  const [searchResults, setSearchResults] = useState<TaxonSearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  
  // State 2: Selected Target
  const [selectedTaxid, setSelectedTaxid] = useState<string | null>(initTaxid);
  const [selectedTaxonName, setSelectedTaxonName] = useState<string | null>(null); // For display

  // State 3: Distribution Config
  const [groupBy, setGroupBy]         = useState('dynasty');
  const [dynasty, setDynasty]         = useState('');
  const [province, setProvince]       = useState('');
  const [region, setRegion]           = useState('');
  const [sex, setSex]                 = useState('');
  const [subsistence, setSubsistence] = useState('');

  // State 4: Distribution Results
  const [dist, setDist]       = useState<TaxonDistributionResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState<string | null>(null);

  // If initial taxid is provided via URL, automatically attempt to fetch distribution.
  // We need to fetch the distribution to implicitly get the name if we only have the taxid.
  useEffect(() => {
    if (initTaxid) {
      setSelectedTaxid(initTaxid);
      setSearchRank(initRank);
    }
  }, [initTaxid, initRank]);

  const handleSearch = useCallback(async () => {
    if (!q.trim()) return;
    setSearching(true);
    try {
      const results = await searchTaxa(q, searchRank, 20);
      setSearchResults(results);
    } catch (e) {
      console.error(e);
      setSearchResults([]);
    } finally {
      setSearching(false);
    }
  }, [q, searchRank]);

  // Debounced search
  useEffect(() => {
    const timer = setTimeout(() => {
      if (q.trim().length >= 2) handleSearch();
    }, 500);
    return () => clearTimeout(timer);
  }, [q, handleSearch]);

  const handleSelectTaxon = (taxon: TaxonSearchResult) => {
    setSelectedTaxid(taxon.taxid);
    setSelectedTaxonName(taxon.name);
    setSearchRank(taxon.rank);
    setQ('');
    setSearchResults([]);
  };

  const loadDistribution = useCallback(() => {
    if (!selectedTaxid) return;
    setLoading(true);
    setError(null);

    getTaxonDistribution(selectedTaxid, {
      group_by: groupBy,
      rank: searchRank,
      dynasty: dynasty || undefined,
      province: province || undefined,
      region: region || undefined,
      sex: sex || undefined,
      subsistence_pattern: subsistence || undefined,
    })
      .then((data) => {
        setDist(data);
        if (!selectedTaxonName) setSelectedTaxonName(data.name); // Set name from response if it came from URL
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [selectedTaxid, groupBy, searchRank, dynasty, province, region, sex, subsistence, selectedTaxonName]);

  // Auto-load distribution when selected taxid or configs change
  useEffect(() => {
    if (selectedTaxid) {
      loadDistribution();
    }
  }, [selectedTaxid, groupBy, dynasty, province, region, sex, subsistence, loadDistribution]);

  const chartOption = dist ? {
    tooltip: { 
      trigger: 'axis', 
      axisPointer: { type: 'shadow' },
      formatter: (params: { name: string; value: number }[]) => {
        const p = params[0];
        return `${p.name}<br/>Mean: ${(p.value * 100).toFixed(4)}%`;
      }
    },
    grid: { left: '3%', right: '4%', bottom: '12%', containLabel: true },
    xAxis: {
      type: 'category',
      data: dist.data.map((d) => d.group),
      axisLabel: { rotate: 30, interval: 0, textStyle: { fontSize: 11 } },
    },
    yAxis: {
      type: 'value',
      name: 'Mean Rel. Abundance',
      axisLabel: { formatter: (v: number) => `${(v * 100).toFixed(1)}%` },
    },
    series: [
      {
        name: 'Mean',
        type: 'bar',
        data: dist.data.map((d) => d.mean_abundance),
        itemStyle: { color: '#6366f1', borderRadius: [4, 4, 0, 0] },
        barMaxWidth: 60
      }
    ],
  } : null;

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Taxon Distribution</h1>
        <p className="text-sm text-gray-500 mt-1">
          Select a taxon to visualize its abundance distribution across different stratifications.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left Column: Taxon Selection */}
        <div className="lg:col-span-1 space-y-6">
          <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
            <h2 className="text-sm font-semibold text-gray-700 mb-4 uppercase tracking-wider flex items-center gap-2">
              <span className="w-1.5 h-4 bg-indigo-500 rounded-full"></span>
              Target Taxon
            </h2>

            {selectedTaxid && (
              <div className="mb-6 p-4 bg-indigo-50 border border-indigo-100 rounded-lg">
                <p className="text-xs text-indigo-500 font-semibold mb-1 uppercase">Currently Selected</p>
                <div className="flex justify-between items-start">
                  <div>
                    <p className="text-base font-medium italic text-indigo-900">{selectedTaxonName || 'Loading name...'}</p>
                    <p className="text-xs text-indigo-700 font-mono mt-1">TaxID: {selectedTaxid}</p>
                  </div>
                  <span className="px-2 py-0.5 bg-indigo-200 text-indigo-800 rounded text-xs font-semibold">{searchRank}</span>
                </div>
                <button 
                  onClick={() => { setSelectedTaxid(null); setSelectedTaxonName(null); setDist(null); }}
                  className="mt-3 text-xs text-indigo-600 hover:text-indigo-800 underline"
                >
                  Change Taxon
                </button>
              </div>
            )}

            {!selectedTaxid && (
              <div className="space-y-4">
                <FilterSelect label="Target Rank" value={searchRank} options={RANKS} onChange={setSearchRank} />
                <div className="relative">
                  <label className="flex flex-col gap-1 text-xs text-gray-500">
                    Search Taxon Name
                    <input
                      value={q}
                      onChange={(e) => setQ(e.target.value)}
                      placeholder="e.g. Streptococcus"
                      className="border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300"
                    />
                  </label>
                  
                  {searching && <div className="absolute right-3 top-7 w-4 h-4 border-2 border-indigo-200 border-t-indigo-600 rounded-full animate-spin"></div>}

                  {searchResults.length > 0 && (
                    <ul className="absolute z-20 mt-1 w-full bg-white border border-gray-200 rounded-lg shadow-lg max-h-64 overflow-y-auto">
                      {searchResults.map((t) => (
                        <li
                          key={`${t.taxid}-${t.name}`}
                          onClick={() => handleSelectTaxon(t)}
                          className="px-4 py-2 hover:bg-indigo-50 cursor-pointer flex justify-between border-b border-gray-50 last:border-0"
                        >
                          <span className="italic text-sm text-gray-800">{t.name}</span>
                          <span className="text-xs text-gray-400">{t.rank}</span>
                        </li>
                      ))}
                    </ul>
                  )}
                  {q.length >= 2 && !searching && searchResults.length === 0 && (
                    <p className="mt-2 text-xs text-gray-400">No taxa found for this rank.</p>
                  )}
                </div>
              </div>
            )}
          </div>
          
          {/* Filters config */}
          <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
            <h2 className="text-sm font-semibold text-gray-700 mb-4 uppercase tracking-wider flex items-center gap-2">
              <span className="w-1.5 h-4 bg-indigo-500 rounded-full"></span>
              Stratification Config
            </h2>
            <div className="space-y-4">
              <label className="flex flex-col gap-1 text-xs font-semibold text-gray-700">
                Primary Grouping Dimension
                <select 
                  value={groupBy} 
                  onChange={(e) => setGroupBy(e.target.value)}
                  className="border border-gray-300 bg-gray-50 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-300 outline-none font-medium"
                >
                  {GROUP_BY_OPTIONS.map(({ value, label }) => (
                    <option key={value} value={value}>{label}</option>
                  ))}
                </select>
              </label>

              <div className="pt-2 border-t border-gray-100">
                <p className="text-xs font-semibold text-gray-500 mb-3 uppercase">Sample Filters</p>
                <div className="grid grid-cols-2 gap-3">
                  <FilterSelect label="Dynasty" value={dynasty} options={DYNASTIES} onChange={setDynasty} />
                  <FilterSelect label="Province" value={province} options={PROVINCES} onChange={setProvince} />
                  <FilterSelect label="Region" value={region} options={REGIONS} onChange={setRegion} />
                  <FilterSelect label="Sex" value={sex} options={SEXES} onChange={setSex} />
                  <div className="col-span-2">
                    <FilterSelect label="Subsistence" value={subsistence} options={SUBSISTENCES} onChange={setSubsistence} />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Visualization & Results */}
        <div className="lg:col-span-2 space-y-6">
          
          {error && (
            <div className="bg-red-50 text-red-700 border border-red-200 rounded-xl p-5 shadow-sm">
              <p className="font-semibold">Error loading distribution</p>
              <p className="text-sm mt-1">{error}</p>
            </div>
          )}

          {!selectedTaxid ? (
            <div className="h-[600px] bg-white border border-gray-200 border-dashed rounded-xl flex items-center justify-center text-center p-6 text-gray-400">
              <div>
                <div className="text-4xl mb-4">🔍</div>
                <p className="font-medium">No taxon selected</p>
                <p className="text-sm mt-1">Search and select a taxon on the left to view its distribution.</p>
              </div>
            </div>
          ) : loading ? (
             <div className="h-[600px] bg-white border border-gray-200 rounded-xl flex items-center justify-center">
               <div className="text-indigo-500 flex flex-col items-center gap-3">
                 <div className="w-8 h-8 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin"></div>
                 <span className="text-sm font-medium">Aggregating distribution...</span>
               </div>
             </div>
          ) : dist ? (
            <>
              {/* Chart */}
              <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm">
                <h2 className="text-sm font-semibold text-gray-700 mb-1 uppercase tracking-wider flex items-center gap-2">
                  <span className="w-1.5 h-4 bg-indigo-500 rounded-full"></span>
                  Mean Abundance by {dist.group_by}
                </h2>
                <ReactECharts option={chartOption} style={{ height: 350 }} />
              </div>

              {/* Table */}
              <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
                <div className="px-6 py-4 border-b border-gray-100 bg-gray-50 flex justify-between items-center">
                  <h3 className="text-sm font-semibold text-gray-700">Detailed Statistics</h3>
                  <span className="text-xs text-gray-500">Total Groups: {dist.data.length}</span>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm whitespace-nowrap">
                    <thead className="bg-white border-b border-gray-200">
                      <tr>
                        <th className="px-4 py-3 text-xs font-bold text-gray-500 uppercase">{dist.group_by}</th>
                        <th className="px-4 py-3 text-xs font-bold text-gray-500 uppercase text-right">Samples</th>
                        <th className="px-4 py-3 text-xs font-bold text-gray-500 uppercase text-right">Mean</th>
                        <th className="px-4 py-3 text-xs font-bold text-gray-500 uppercase text-right">Median</th>
                        <th className="px-4 py-3 text-xs font-bold text-gray-500 uppercase text-right">Min</th>
                        <th className="px-4 py-3 text-xs font-bold text-gray-500 uppercase text-right">Max</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-100">
                      {dist.data.map((d) => (
                        <tr key={d.group} className="hover:bg-indigo-50/50 transition-colors">
                          <td className="px-4 py-3 font-medium text-gray-900">{d.group}</td>
                          <td className="px-4 py-3 text-right text-gray-600 font-mono">{d.sample_count}</td>
                          <td className="px-4 py-3 text-right font-mono text-indigo-700 font-semibold">{(d.mean_abundance * 100).toFixed(4)}%</td>
                          <td className="px-4 py-3 text-right font-mono text-gray-600">{(d.median_abundance * 100).toFixed(4)}%</td>
                          <td className="px-4 py-3 text-right font-mono text-gray-500">{(d.min_abundance * 100).toFixed(4)}%</td>
                          <td className="px-4 py-3 text-right font-mono text-gray-500">{(d.max_abundance * 100).toFixed(4)}%</td>
                        </tr>
                      ))}
                      {dist.data.length === 0 && (
                        <tr>
                          <td colSpan={6} className="px-4 py-8 text-center text-sm text-gray-400">
                            No matching distribution records found for this configuration.
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          ) : null}
        </div>
      </div>
    </div>
  );
}

export default function TaxonDistributionPage() {
  return (
    <Suspense fallback={<div className="p-12 text-center text-gray-400">Loading component...</div>}>
      <DistributionPageContent />
    </Suspense>
  );
}
