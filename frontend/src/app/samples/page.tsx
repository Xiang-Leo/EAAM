'use client';

import { useEffect, useState, useCallback, FormEvent } from 'react';
import Link from 'next/link';
import { getSamples } from '@/lib/api';
import type { Sample, SampleFilterParams } from '@/types/api';

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
  options: string[];
  onChange: (v: string) => void;
}) {
  return (
    <label className="flex flex-col gap-1 text-xs text-gray-500">
      {label}
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="border border-gray-200 rounded-lg px-2 py-1.5 text-sm text-gray-800 bg-white focus:outline-none focus:ring-2 focus:ring-indigo-300 w-36"
      >
        {options.map((o) => (
          <option key={o} value={o}>{o || 'All'}</option>
        ))}
      </select>
    </label>
  );
}

function SampleRow({ sample }: { sample: Sample }) {
  return (
    <tr className="hover:bg-indigo-50 transition-colors">
      <td className="px-4 py-3 font-mono text-sm text-indigo-700">
        <Link href={`/samples/${sample.sample_id}`} className="hover:underline">
          {sample.sample_id}
        </Link>
      </td>
      <td className="px-4 py-3 text-sm">{sample.dynasty ?? '—'}</td>
      <td className="px-4 py-3 text-sm">{sample.province ?? '—'}</td>
      <td className="px-4 py-3 text-sm">{sample.region ?? '—'}</td>
      <td className="px-4 py-3 text-sm">{sample.sex ?? '—'}</td>
      <td className="px-4 py-3 text-sm">{sample.subsistence_pattern ?? '—'}</td>
      <td className="px-4 py-3 text-sm text-right">{sample.estimated_year ?? '—'}</td>
    </tr>
  );
}

export default function SamplesPage() {
  const [filters, setFilters] = useState<SampleFilterParams>({ limit: 50, offset: 0 });
  const [dynasty, setDynasty] = useState('');
  const [province, setProvince] = useState('');
  const [region, setRegion] = useState('');
  const [sex, setSex] = useState('');
  const [subsistence, setSubsistence] = useState('');

  const [samples, setSamples] = useState<Sample[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    setLoading(true);
    setError(null);
    getSamples(filters)
      .then((data) => {
        setSamples(data.items);
        setTotal(data.total);
      })
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [filters]);

  useEffect(() => {
    load();
  }, [load]);

  const handleSearch = (e?: FormEvent) => {
    if (e) e.preventDefault();
    setFilters({
      dynasty: dynasty || undefined,
      province: province || undefined,
      region: region || undefined,
      sex: sex || undefined,
      subsistence_pattern: subsistence || undefined,
      limit: filters.limit,
      offset: 0, // Reset to first page on new search
    });
  };

  const handleReset = () => {
    setDynasty('');
    setProvince('');
    setRegion('');
    setSex('');
    setSubsistence('');
    setFilters({ limit: 50, offset: 0 });
  };

  const page = Math.floor((filters.offset ?? 0) / (filters.limit ?? 50)) + 1;
  const totalPages = Math.ceil(total / (filters.limit ?? 50));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Samples</h1>
        <p className="text-sm text-gray-500 mt-1">Browse and filter all samples in the database</p>
      </div>

      {/* Filters Form */}
      <form onSubmit={handleSearch} className="bg-white border border-gray-200 rounded-xl p-5 shadow-sm">
        <div className="flex flex-wrap gap-4 items-end">
          <FilterSelect label="Dynasty" value={dynasty} options={DYNASTIES} onChange={setDynasty} />
          <FilterSelect label="Province" value={province} options={PROVINCES} onChange={setProvince} />
          <FilterSelect label="Region"  value={region}  options={REGIONS}  onChange={setRegion} />
          <FilterSelect label="Sex"     value={sex}     options={SEXES}    onChange={setSex} />
          <FilterSelect label="Subsistence" value={subsistence} options={SUBSISTENCES} onChange={setSubsistence} />
          
          <div className="flex gap-2">
            <button
              type="submit"
              className="px-5 py-1.5 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-700 transition-colors font-medium shadow-sm"
            >
              Search
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

      {/* Error State */}
      {error && (
        <div className="bg-red-50 text-red-700 border border-red-200 rounded-lg px-4 py-3 text-sm">
          {error}
        </div>
      )}

      {/* Results Header */}
      {!error && (
        <div className="flex justify-between items-end">
          <span className="text-sm font-medium text-gray-700">
            {total.toLocaleString()} result{total !== 1 ? 's' : ''} found
          </span>
        </div>
      )}

      {/* Table */}
      <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden">
        {loading ? (
          <div className="p-8 text-center space-y-4">
            <div className="text-sm text-gray-400 animate-pulse">Loading samples...</div>
            <div className="flex flex-col gap-2 opacity-50">
               {[1, 2, 3, 4, 5].map((i) => <div key={i} className="h-8 bg-gray-100 rounded w-full animate-pulse"></div>)}
            </div>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead className="bg-gray-50 border-b border-gray-200">
                <tr>
                  {['Sample ID', 'Dynasty', 'Province', 'Region', 'Sex', 'Subsistence'].map((h) => (
                    <th key={h} className="px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">{h}</th>
                  ))}
                  <th className="px-4 py-3 text-xs font-semibold text-gray-500 uppercase tracking-wide text-right">Est. Year</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {samples.map((s) => <SampleRow key={s.id} sample={s} />)}
              </tbody>
            </table>
            {samples.length === 0 && !loading && (
              <p className="p-8 text-center text-sm text-gray-400">No samples match the current filters.</p>
            )}
          </div>
        )}
      </div>

      {/* Pagination */}
      {!loading && totalPages > 1 && (
        <div className="flex items-center justify-between bg-white px-4 py-3 border border-gray-200 rounded-xl shadow-sm">
          <button
            disabled={page <= 1}
            onClick={() => setFilters((f) => ({ ...f, offset: Math.max(0, (f.offset ?? 0) - (f.limit ?? 50)) }))}
            className="px-4 py-2 text-sm border border-gray-200 text-gray-700 rounded-lg disabled:opacity-40 hover:bg-gray-50 transition-colors"
          >
            Previous
          </button>
          <span className="text-sm text-gray-600 font-medium">
            Page {page} of {totalPages}
          </span>
          <button
            disabled={page >= totalPages}
            onClick={() => setFilters((f) => ({ ...f, offset: (f.offset ?? 0) + (f.limit ?? 50) }))}
            className="px-4 py-2 text-sm border border-gray-200 text-gray-700 rounded-lg disabled:opacity-40 hover:bg-gray-50 transition-colors"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}
