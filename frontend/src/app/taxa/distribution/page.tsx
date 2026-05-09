'use client';
import { useState, useEffect } from 'react';
import BoxPlot from '@/components/charts/BoxPlot';
import { fetchTaxonDistribution } from '@/lib/api';

// Helper to calculate quartiles
function calculateBoxPlotData(values: number[]) {
  if (values.length === 0) return [0, 0, 0, 0, 0];
  const sorted = [...values].sort((a, b) => a - b);
  const min = sorted[0];
  const max = sorted[sorted.length - 1];
  
  const q1 = sorted[Math.floor(sorted.length * 0.25)];
  const median = sorted[Math.floor(sorted.length * 0.5)];
  const q3 = sorted[Math.floor(sorted.length * 0.75)];
  
  return [min, q1, median, q3, max];
}

export default function TaxonDistributionPage() {
  const [taxid, setTaxid] = useState('1000'); // Default mock taxid
  const [groupBy, setGroupBy] = useState('dynasty');
  const [chartData, setChartData] = useState<{categories: string[], data: number[][]}>({ categories: [], data: [] });
  const [loading, setLoading] = useState(false);

  const loadData = async () => {
    if (!taxid) return;
    setLoading(true);
    try {
      const data = await fetchTaxonDistribution(taxid, groupBy);
      
      const categories = data.map((d: any) => d.group_by);
      const boxData = data.map((d: any) => calculateBoxPlotData(d.abundances));
      
      setChartData({ categories, data: boxData });
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [groupBy]);

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6 text-slate-900">Taxon Distribution</h1>
      
      <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200 mb-8 flex gap-4 items-end">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Taxon ID</label>
          <input 
            type="text" 
            value={taxid} 
            onChange={e => setTaxid(e.target.value)}
            className="rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm p-2 border"
            placeholder="e.g. 1000"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Group By</label>
          <select 
            value={groupBy} 
            onChange={e => setGroupBy(e.target.value)}
            className="rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm p-2 border"
          >
            <option value="dynasty">Dynasty</option>
            <option value="region">Region</option>
          </select>
        </div>
        <button 
          onClick={loadData}
          className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 transition-colors"
        >
          Update Chart
        </button>
      </div>

      <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
        {loading ? (
          <div className="h-96 flex items-center justify-center text-slate-500">Loading chart...</div>
        ) : (
          <BoxPlot 
            categories={chartData.categories} 
            data={chartData.data} 
            title={`Abundance Distribution by ${groupBy.charAt(0).toUpperCase() + groupBy.slice(1)}`} 
          />
        )}
      </div>
    </div>
  );
}
