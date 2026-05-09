import Link from "next/link";
import { ArrowRight, Database, BarChart2, Search } from "lucide-react";

export default function Home() {
  return (
    <div className="flex flex-col items-center">
      {/* Hero Section */}
      <div className="w-full py-16 md:py-24 text-center">
        <h1 className="text-5xl md:text-6xl font-extrabold tracking-tight text-slate-900 mb-6">
          Ancient <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-600 to-indigo-600">Microbiome</span> Archive
        </h1>
        <p className="max-w-2xl mx-auto text-xl text-slate-600 mb-10">
          Explore the microbial composition of ancient Chinese dental calculus. Query, filter, and visualize Kraken2 classification results across different dynasties, regions, and subsistence patterns.
        </p>
        <div className="flex justify-center gap-4">
          <Link href="/samples" className="inline-flex items-center justify-center px-8 py-3 text-base font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-full shadow-lg hover:shadow-xl transition-all duration-200">
            Browse Samples
            <ArrowRight className="ml-2 w-5 h-5" />
          </Link>
          <Link href="/taxa/top" className="inline-flex items-center justify-center px-8 py-3 text-base font-medium text-blue-700 bg-blue-50 hover:bg-blue-100 rounded-full border border-blue-200 transition-all duration-200">
            Discover Top Taxa
          </Link>
        </div>
      </div>

      {/* Features Section */}
      <div className="grid md:grid-cols-3 gap-8 mt-12 w-full">
        <div className="bg-white p-8 rounded-2xl shadow-sm border border-slate-100 hover:shadow-md transition-shadow">
          <div className="w-12 h-12 bg-blue-100 rounded-xl flex items-center justify-center mb-6 text-blue-600">
            <Database className="w-6 h-6" />
          </div>
          <h3 className="text-xl font-bold mb-3 text-slate-900">Extensive Dataset</h3>
          <p className="text-slate-600 leading-relaxed">
            Access thousands of samples spanning multiple dynasties and geographic regions in ancient China.
          </p>
        </div>
        <div className="bg-white p-8 rounded-2xl shadow-sm border border-slate-100 hover:shadow-md transition-shadow">
          <div className="w-12 h-12 bg-indigo-100 rounded-xl flex items-center justify-center mb-6 text-indigo-600">
            <Search className="w-6 h-6" />
          </div>
          <h3 className="text-xl font-bold mb-3 text-slate-900">Advanced Filtering</h3>
          <p className="text-slate-600 leading-relaxed">
            Filter samples by province, region, dynasty, sex, and subsistence pattern to find exactly what you need.
          </p>
        </div>
        <div className="bg-white p-8 rounded-2xl shadow-sm border border-slate-100 hover:shadow-md transition-shadow">
          <div className="w-12 h-12 bg-purple-100 rounded-xl flex items-center justify-center mb-6 text-purple-600">
            <BarChart2 className="w-6 h-6" />
          </div>
          <h3 className="text-xl font-bold mb-3 text-slate-900">Dynamic Visualization</h3>
          <p className="text-slate-600 leading-relaxed">
            View interactive charts including taxon abundance distribution, top taxa by sample, and more.
          </p>
        </div>
      </div>
    </div>
  );
}
