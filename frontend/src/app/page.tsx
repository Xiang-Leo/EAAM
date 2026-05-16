'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import dynamic from 'next/dynamic';
import { getSummary } from '@/lib/api';
import type { SummaryResponse } from '@/types/api';

const ReactECharts = dynamic(() => import('echarts-for-react'), { ssr: false });
const TILE_SIZE = 256;
const MAP_ZOOM = 4;
const MAP_WIDTH = 960;
const MAP_HEIGHT = 420;
const MAP_CENTER = { lon: 105, lat: 35 };

function lonLatToWorld(lon: number, lat: number, zoom: number) {
  const scale = TILE_SIZE * 2 ** zoom;
  const sinLat = Math.sin((lat * Math.PI) / 180);
  return {
    x: ((lon + 180) / 360) * scale,
    y: (0.5 - Math.log((1 + sinLat) / (1 - sinLat)) / (4 * Math.PI)) * scale,
  };
}

function SamplingTileMap({ locations }: { locations: SummaryResponse['sample_locations'] }) {
  const center = lonLatToWorld(MAP_CENTER.lon, MAP_CENTER.lat, MAP_ZOOM);
  const topLeft = { x: center.x - MAP_WIDTH / 2, y: center.y - MAP_HEIGHT / 2 };
  const startX = Math.floor(topLeft.x / TILE_SIZE);
  const endX = Math.floor((topLeft.x + MAP_WIDTH) / TILE_SIZE);
  const startY = Math.floor(topLeft.y / TILE_SIZE);
  const endY = Math.floor((topLeft.y + MAP_HEIGHT) / TILE_SIZE);
  const tileCount = 2 ** MAP_ZOOM;
  const tiles = [];

  for (let x = startX; x <= endX; x += 1) {
    for (let y = startY; y <= endY; y += 1) {
      if (y < 0 || y >= tileCount) continue;
      const wrappedX = ((x % tileCount) + tileCount) % tileCount;
      const subdomain = ['a', 'b', 'c'][Math.abs(x + y) % 3];
      tiles.push({
        key: `${x}-${y}`,
        src: `https://${subdomain}.basemaps.cartocdn.com/light_all/${MAP_ZOOM}/${wrappedX}/${y}.png`,
        left: x * TILE_SIZE - topLeft.x,
        top: y * TILE_SIZE - topLeft.y,
      });
    }
  }

  const points = locations
    .map((site) => {
      const longitude = Number(site.longitude);
      const latitude = Number(site.latitude);
      if (!Number.isFinite(longitude) || !Number.isFinite(latitude)) return null;
      const pos = lonLatToWorld(longitude, latitude, MAP_ZOOM);
      return {
        ...site,
        left: pos.x - topLeft.x,
        top: pos.y - topLeft.y,
        size: Math.max(10, Math.min(34, 10 + site.count * 3)),
      };
    })
    .filter((site): site is NonNullable<typeof site> => site !== null)
    .filter((site) => site.left >= -40 && site.left <= MAP_WIDTH + 40 && site.top >= -40 && site.top <= MAP_HEIGHT + 40);

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
      <div className="mb-4">
        <h2 className="text-base font-semibold text-gray-700">Sampling Map</h2>
        <p className="text-xs text-gray-500 mt-1">CartoDB Positron basemap with sampling locations scaled by sample count.</p>
      </div>
      <div className="relative overflow-hidden rounded-lg border border-gray-200 bg-gray-100" style={{ height: MAP_HEIGHT }}>
        {tiles.map((tile) => (
          <img
            key={tile.key}
            src={tile.src}
            alt=""
            className="absolute h-64 w-64 select-none"
            style={{ left: tile.left, top: tile.top }}
            draggable={false}
          />
        ))}
        {points.map((site, index) => (
          <div
            key={`${site.longitude}-${site.latitude}-${site.province}-${site.dynasty}-${index}`}
            className="group absolute -translate-x-1/2 -translate-y-1/2"
            style={{ left: site.left, top: site.top }}
          >
            <div
              className="rounded-full border-2 border-white bg-teal-600/80 shadow"
              style={{ width: site.size, height: site.size }}
            />
            <div className="pointer-events-none absolute left-1/2 top-full z-10 mt-2 hidden min-w-44 -translate-x-1/2 rounded-md bg-white px-3 py-2 text-xs shadow-lg ring-1 ring-gray-200 group-hover:block">
              <div className="font-medium text-gray-900">{site.province || 'Unknown'} · {site.dynasty || 'Unknown'}</div>
              <div className="text-gray-500">Region: {site.region || 'Unknown'}</div>
              <div className="text-gray-500">Samples: {site.count}</div>
              {site.estimated && <div className="text-amber-600">Approximate province/region point</div>}
            </div>
          </div>
        ))}
        {points.length === 0 && (
          <div className="absolute inset-0 flex items-center justify-center bg-white/70 px-6 text-center text-sm text-gray-600">
            No sampling coordinates are available yet. Upload metadata with latitude/longitude, or at least province/region names.
          </div>
        )}
        <div className="absolute bottom-2 right-2 rounded bg-white/90 px-2 py-1 text-[10px] text-gray-500 shadow-sm">
          Tiles © CARTO © OpenStreetMap contributors
        </div>
      </div>
    </div>
  );
}

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
          East Asian Ancient Microbiome — explore microbial composition across
          periods, regions, archaeological contexts, and subsistence patterns.
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

          <SamplingTileMap locations={data.sample_locations} />

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
