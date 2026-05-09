'use client';
import { useState, useEffect } from 'react';
import BarChart from '@/components/charts/BarChart';
import { fetchTopTaxa } from '@/lib/api';

export default function TopTaxaPage() {
  const [groupBy, setGroupBy] = useState('dynasty');
  const [groupValue, setGroupValue] = useState('Tang');
  const [loading, setLoading] = useState(false);
  const [taxa, setTaxa] = useState<any[]>([]);

  const loadData = async () => {
    if (!groupValue) return;
    setLoading(true);
    try {
      const data = await fetchTopTaxa(groupBy, groupValue, 10, 'S');
      setTaxa(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [groupBy, groupValue]);

  const chartData = taxa.map(t => ({
    name: t.name,
    value: t.mean_abundance
  }));

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6 text-slate-900">Top Taxa Discovery</h1>
      
      <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200 mb-8 flex gap-4 items-end">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Group By</label>
          <select 
            value={groupBy} 
            onChange={e => { setGroupBy(e.target.value); setGroupValue(''); }}
            className="rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm p-2 border"
          >
            <option value="dynasty">Dynasty</option>
            <option value="region">Region</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Value</label>
          {groupBy === 'dynasty' ? (
            <select 
              value={groupValue} 
              onChange={e => setGroupValue(e.target.value)}
              className="rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm p-2 border"
            >
              <option value="">Select...</option>
              <option value="Shang">Shang</option>
              <option value="Zhou">Zhou</option>
              <option value="Han">Han</option>
              <option value="Tang">Tang</option>
              <option value="Ming">Ming</option>
            </select>
          ) : (
            <select 
              value={groupValue} 
              onChange={e => setGroupValue(e.target.value)}
              className="rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm p-2 border"
            >
              <option value="">Select...</option>
              <option value="North">North</option>
              <option value="South">South</option>
              <option value="Central">Central</option>
              <option value="East">East</option>
              <option value="Southwest">Southwest</option>
            </select>
          )}
        </div>
        <button 
          onClick={loadData}
          disabled={!groupValue}
          className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 transition-colors disabled:opacity-50"
        >
          Update Chart
        </button>
      </div>

      <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
        {loading ? (
          <div className="h-96 flex items-center justify-center text-slate-500">Loading chart...</div>
        ) : (
          <BarChart 
            data={chartData} 
            title={`Top 10 Species in ${groupValue || 'Selection'}`} 
            xAxisName="Species"
            yAxisName="Mean Relative Abundance"
          />
        )}
      </div>
    </div>
  );
}
