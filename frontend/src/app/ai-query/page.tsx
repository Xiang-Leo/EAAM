'use client';

import { useState } from 'react';
import { API_BASE_URL, askAI } from '@/lib/api';
import type { AIQueryResponse } from '@/types/api';

const EXAMPLES = [
  '请帮我查看唐代样品中 Actinomyces 的丰度',
  'Show me the top genus in Han dynasty',
  'Search for Streptococcus',
  '列出所有明代样品',
];

export default function AIQueryPage() {
  const [question, setQuestion] = useState('');
  const [result, setResult]     = useState<AIQueryResponse | null>(null);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState<string | null>(null);

  const handleSubmit = async () => {
    if (!question.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    
    try {
      const data = await askAI(question);
      setResult(data);
    } catch (e: any) {
      setError(e.message || 'Failed to analyze query.');
    } finally {
      setLoading(false);
    }
  };

  const plan = result?.suggested_query_plan;

  return (
    <div className="max-w-4xl space-y-8">
      {/* Header section */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
          <span>✨</span> AI Query Assistant
        </h1>
        <p className="text-sm text-gray-500 mt-2 max-w-3xl leading-relaxed">
          Ask complex database queries in plain natural language. Our semantic layer will automatically figure out 
          the right tables to join and the right filters to apply.
        </p>
      </div>

      {/* Notice Banner */}
      <div className="bg-amber-50 border border-amber-200 rounded-xl p-5 shadow-sm">
        <h3 className="text-amber-800 font-bold flex items-center gap-2 text-sm uppercase tracking-wide mb-2">
          <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" /></svg>
          MVP Placeholder Notice
        </h3>
        <p className="text-sm text-amber-700 leading-relaxed">
          The current interface uses a lightweight <strong>Rule-Based Query Planner</strong> on the backend to demonstrate intent recognition. 
          It does <strong>not</strong> perform real calls to DeepSeek or any LLM yet. 
        </p>
        <div className="mt-4 pt-4 border-t border-amber-200/50">
          <p className="text-xs font-semibold text-amber-800 mb-2 uppercase">Coming in Future Releases:</p>
          <ul className="text-sm text-amber-700 list-disc list-inside space-y-1 ml-1">
            <li><strong>DeepSeek Integration:</strong> Calling DeepSeek API to generate complex, unconstrained query plans.</li>
            <li><strong>Natural Language Distribution:</strong> Directly parsing complex requests like <i>&quot;How does taxonomy X change over dynasties?&quot;</i></li>
            <li><strong>Auto Chart Selection:</strong> Dynamically rendering Pie, Bar, or Box plots based on AI inference of the returned data shape.</li>
            <li><strong>Auto Result Explanation:</strong> AI-generated biological insights and summaries on the returned microbiome profile.</li>
          </ul>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Left Column: Input */}
        <div className="space-y-4">
          <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-sm flex flex-col h-full">
            <label className="block text-sm font-semibold text-gray-700 mb-2 uppercase tracking-wider flex items-center gap-2">
               <span className="w-1.5 h-4 bg-indigo-500 rounded-full"></span>
               Your Question
            </label>
            <textarea
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              onKeyDown={(e) => { 
                if (e.key === 'Enter' && !e.shiftKey) { 
                  e.preventDefault(); 
                  handleSubmit(); 
                } 
              }}
              placeholder="Type your question here (e.g. Show me the top genus in Tang dynasty...)"
              rows={5}
              className="w-full flex-1 border border-gray-200 rounded-xl p-4 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-300 resize-none shadow-inner bg-gray-50/50"
            />
            
            <div className="mt-4 flex flex-col gap-3">
              <span className="text-xs font-semibold text-gray-400 uppercase">Try an example:</span>
              <div className="flex flex-wrap gap-2">
                {EXAMPLES.map((ex) => (
                  <button
                    key={ex}
                    onClick={() => setQuestion(ex)}
                    className="px-3 py-1.5 text-xs bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition-colors border border-gray-200"
                  >
                    {ex}
                  </button>
                ))}
              </div>
            </div>

            <div className="mt-6 pt-4 border-t border-gray-100">
              <button
                onClick={handleSubmit}
                disabled={!question.trim() || loading}
                className="w-full py-3 bg-indigo-600 text-white font-medium rounded-xl hover:bg-indigo-700 disabled:opacity-40 disabled:cursor-not-allowed transition-all shadow-sm flex items-center justify-center gap-2"
              >
                {loading ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                    Analyzing Intent...
                  </>
                ) : 'Ask AI Planner'}
              </button>
            </div>
          </div>
        </div>

        {/* Right Column: Output */}
        <div className="space-y-4">
           {error && (
            <div className="bg-red-50 text-red-700 border border-red-200 rounded-xl p-6 shadow-sm">
              <h3 className="font-bold mb-1">Request Failed</h3>
              <p className="text-sm">{error}</p>
            </div>
          )}

          {!result && !loading && !error && (
            <div className="h-full min-h-[300px] bg-white border border-gray-200 border-dashed rounded-xl flex items-center justify-center text-center p-6 shadow-sm">
              <div>
                <span className="text-4xl text-gray-300 mb-4 block">🤖</span>
                <p className="text-gray-500 font-medium">Awaiting question...</p>
                <p className="text-xs text-gray-400 mt-1">Submit a query to see the generated execution plan.</p>
              </div>
            </div>
          )}

          {loading && (
             <div className="h-full min-h-[300px] bg-white border border-gray-200 rounded-xl flex items-center justify-center p-6 shadow-sm">
               <div className="flex flex-col items-center gap-3 text-indigo-500">
                 <div className="w-8 h-8 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin"></div>
                 <span className="text-sm font-medium animate-pulse">Running semantic analysis...</span>
               </div>
             </div>
          )}

          {result && plan && !loading && (
            <div className="bg-white border border-gray-200 rounded-xl shadow-sm overflow-hidden flex flex-col h-full">
              {/* Header Status */}
              <div className="bg-gray-50 px-6 py-4 border-b border-gray-100 flex items-center justify-between">
                <h2 className="text-sm font-bold text-gray-800 uppercase tracking-wider flex items-center gap-2">
                  <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                  Execution Plan Generated
                </h2>
                <span className="px-2 py-1 bg-green-100 text-green-700 text-xs font-bold rounded-md uppercase tracking-wide border border-green-200">
                  {result.status}
                </span>
              </div>
              
              <div className="p-6 space-y-5 flex-1">
                <p className="text-sm text-gray-600 italic bg-gray-50 p-3 rounded-lg border border-gray-100">
                  &quot;{result.message}&quot;
                </p>

                <div>
                   <h3 className="text-xs font-semibold text-gray-400 uppercase mb-3">Parsed Context</h3>
                   <div className="grid grid-cols-2 gap-4">
                     <div className="bg-gray-50 p-3 rounded-lg border border-gray-100">
                       <p className="text-xs text-gray-500 mb-1">Intent</p>
                       <p className="text-sm font-mono text-indigo-700 font-medium">{plan.intent || 'Unknown'}</p>
                     </div>
                     <div className="bg-gray-50 p-3 rounded-lg border border-gray-100">
                       <p className="text-xs text-gray-500 mb-1">Confidence</p>
                       <p className="text-sm font-mono text-indigo-700 font-medium">{(plan.confidence * 100).toFixed(0)}%</p>
                     </div>
                     <div className="bg-gray-50 p-3 rounded-lg border border-gray-100 col-span-2">
                       <p className="text-xs text-gray-500 mb-1">Extracted Taxon Name</p>
                       <p className="text-sm font-mono text-indigo-700">{plan.taxon_name || 'None detected'}</p>
                     </div>
                     <div className="bg-gray-50 p-3 rounded-lg border border-gray-100 col-span-2">
                       <p className="text-xs text-gray-500 mb-1">Extracted Filters</p>
                       <p className="text-sm font-mono text-indigo-700 break-words">
                         {Object.keys(plan.filters).length > 0 ? JSON.stringify(plan.filters) : 'No filters detected'}
                       </p>
                     </div>
                   </div>
                </div>

                {plan.notes && (
                  <div className="bg-blue-50 border border-blue-100 text-blue-800 p-3 rounded-lg text-sm">
                    <strong>Note:</strong> {plan.notes}
                  </div>
                )}

                <div className="pt-4 border-t border-gray-100">
                   <h3 className="text-xs font-semibold text-gray-400 uppercase mb-2">Recommended API Route</h3>
                   <a
                    href={`${API_BASE_URL}${plan.recommended_endpoint}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="block w-full p-3 bg-gray-900 text-green-400 font-mono text-xs rounded-lg hover:bg-gray-800 transition-colors break-all border border-gray-700"
                  >
                    GET {plan.recommended_endpoint}
                  </a>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
