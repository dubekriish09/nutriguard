import React, { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { chatApi } from '../api/services';
import { RecommendationResult, ChatResponse } from '../types/api.types';
import { CLASSIFICATION_CONFIG, ClassificationType } from '../utils/classification';

export function Dashboard() {
  const [query, setQuery] = useState('');
  const [result, setResult] = useState<ChatResponse | null>(null);

  const chatMutation = useMutation({
    mutationFn: (msg: string) => chatApi.foodChat({ message: msg, user_context: {} })
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    chatMutation.mutate(query, {
      onSuccess: (data) => setResult(data)
    });
  };

  return (
    <div className="min-h-screen bg-slate-50 p-6 md:p-12">
      <div className="max-w-3xl mx-auto space-y-8">
        
        <header>
          <h1 className="text-3xl font-bold text-slate-900">Good morning</h1>
          <p className="text-slate-600 mt-2">Check your personalized food safety.</p>
        </header>

        <form onSubmit={handleSubmit} className="relative">
          <input 
            type="text" 
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask about any food... e.g. Can I eat peanuts?"
            className="w-full px-6 py-4 text-lg rounded-2xl border border-slate-200 shadow-sm focus:ring-2 focus:ring-green-500 focus:outline-none pr-32"
          />
          <button 
            type="submit" 
            disabled={chatMutation.isPending}
            className="absolute right-2 top-2 bottom-2 px-6 bg-green-600 text-white rounded-xl font-medium hover:bg-green-700 disabled:opacity-50"
          >
            {chatMutation.isPending ? 'Checking...' : 'Check Food'}
          </button>
        </form>

        {result && (
          <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm animate-in fade-in slide-in-from-bottom-4 duration-300">
            {result.clarification_required ? (
              <p className="text-slate-800 text-lg">{result.question}</p>
            ) : result.deterministic_result ? (
              <RecommendationCard data={result.deterministic_result} explanation={result.explanation} />
            ) : null}
          </div>
        )}

      </div>
    </div>
  );
}

function RecommendationCard({ data, explanation }: { data: RecommendationResult, explanation?: string }) {
  const config = CLASSIFICATION_CONFIG[(data.classification as ClassificationType) || 'neutral'];
  
  return (
    <div className="space-y-4">
      <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full border ${config.bg} ${config.border} ${config.color}`}>
        <span className="font-bold">{config.icon}</span>
        <span className="text-sm font-bold tracking-wide uppercase">{config.label}</span>
      </div>
      
      <h2 className="text-2xl font-bold text-slate-900">{data.food_name || 'Food Evaluation'}</h2>
      
      {explanation && (
        <p className="text-slate-600 leading-relaxed text-lg">{explanation}</p>
      )}

      {data.reason && (
        <div className="p-4 bg-red-50 border border-red-100 rounded-xl mt-4 text-red-800">
          <strong>Deterministic Rule Fired:</strong> {data.reason}
        </div>
      )}
    </div>
  );
}
