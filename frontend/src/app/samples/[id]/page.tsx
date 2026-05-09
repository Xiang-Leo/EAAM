'use client';
import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { fetchSampleTaxa } from '@/lib/api';
import BarChart from '@/components/charts/BarChart';

export default function SampleDetailPage() {
  const { id } = useParams();
  const [taxa, setTaxa] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (id) {
      fetchSampleTaxa(id as string, 15, 'S')
        .then(data => setTaxa(data))
        .catch(console.error)
        .finally(() => setLoading(false));
    }
  }, [id]);

  if (loading) return <div>Loading...</div>;

  const chartData = taxa.map(t => ({
    name: t.taxonomy.name,
    value: t.relative_abundance_all
  }));

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-slate-900">Sample: {id}</h1>
        <p className="text-slate-500 mt-2">Top 15 Species Abundance</p>
      </div>
      
      <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
        <BarChart 
          data={chartData} 
          title="Relative Abundance (Species Level)"
          xAxisName="Species"
          yAxisName="Relative Abundance"
        />
      </div>
    </div>
  );
}
