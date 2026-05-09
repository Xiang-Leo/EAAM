'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { fetchSamples } from '@/lib/api';

export default function SamplesPage() {
  const [samples, setSamples] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  
  // Filters
  const [dynasty, setDynasty] = useState('');
  const [region, setRegion] = useState('');
  const [sex, setSex] = useState('');

  const loadSamples = async () => {
    setLoading(true);
    try {
      const params: any = {};
      if (dynasty) params.dynasty = dynasty;
      if (region) params.region = region;
      if (sex) params.sex = sex;
      
      const data = await fetchSamples(params);
      setSamples(data.items);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSamples();
  }, [dynasty, region, sex]);

  return (
    <div className="flex gap-8">
      {/* Sidebar Filters */}
      <div className="w-64 flex-shrink-0">
        <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
          <h2 className="font-bold text-lg mb-4 text-slate-800">Filters</h2>
          
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Dynasty</label>
              <select 
                value={dynasty} 
                onChange={e => setDynasty(e.target.value)}
                className="w-full rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm p-2 border"
              >
                <option value="">All</option>
                <option value="Shang">Shang</option>
                <option value="Zhou">Zhou</option>
                <option value="Han">Han</option>
                <option value="Tang">Tang</option>
                <option value="Ming">Ming</option>
              </select>
            </div>
            
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Region</label>
              <select 
                value={region} 
                onChange={e => setRegion(e.target.value)}
                className="w-full rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm p-2 border"
              >
                <option value="">All</option>
                <option value="North">North</option>
                <option value="South">South</option>
                <option value="Central">Central</option>
                <option value="East">East</option>
                <option value="Southwest">Southwest</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">Sex</label>
              <select 
                value={sex} 
                onChange={e => setSex(e.target.value)}
                className="w-full rounded-md border-slate-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 text-sm p-2 border"
              >
                <option value="">All</option>
                <option value="M">Male</option>
                <option value="F">Female</option>
                <option value="Unknown">Unknown</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1">
        <h1 className="text-2xl font-bold mb-6 text-slate-900">Samples Archive</h1>
        
        {loading ? (
          <div className="animate-pulse space-y-4">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-16 bg-slate-200 rounded-lg"></div>
            ))}
          </div>
        ) : samples.length === 0 ? (
          <div className="text-center py-12 text-slate-500">No samples found.</div>
        ) : (
          <div className="bg-white shadow-sm rounded-xl border border-slate-200 overflow-hidden">
            <table className="min-w-full divide-y divide-slate-200">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Sample ID</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Dynasty</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Region</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Sex</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Subsistence</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 uppercase tracking-wider">Action</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-slate-200">
                {samples.map((sample: any) => (
                  <tr key={sample.id} className="hover:bg-slate-50 transition-colors">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-blue-600">
                      <Link href={`/samples/${sample.id}`}>{sample.id}</Link>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-700">{sample.dynasty}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-700">{sample.region}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-700">{sample.sex}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-700">{sample.subsistence_pattern}</td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                      <Link href={`/samples/${sample.id}`} className="text-blue-600 hover:text-blue-900">View Details</Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
