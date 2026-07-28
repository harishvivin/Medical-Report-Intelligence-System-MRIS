import React, { useState } from 'react';
import { Send, Sparkles, Image as ImageIcon, MapPin, CheckCircle, AlertTriangle, Eye, Loader2 } from 'lucide-react';
import QuickQuestions from './QuickQuestions';
import { safeFetchJson, getApiBase } from '../config';

export default function QaSection({ documentId, onOpenCropModal }) {
  const [question, setQuestion] = useState('');
  const [qaHistory, setQaHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleAsk = async (qToSubmit) => {
    const targetQ = qToSubmit || question;
    if (!targetQ.trim() || !documentId || loading) return;

    setLoading(true);
    setError(null);

    try {
      const data = await safeFetchJson('/api/qa/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          document_id: documentId,
          question: targetQ.trim(),
        }),
      });

      const fullSnippetUrl = data.snippet_url
        ? (data.snippet_url.startsWith('http') ? data.snippet_url : `${getApiBase()}${data.snippet_url}`)
        : null;

      setQaHistory((prev) => [
        {
          id: Date.now(),
          question: targetQ,
          answer: data.answer,
          pageNumber: data.page_number,
          confidence: data.confidence,
          snippetUrl: fullSnippetUrl,
          boundingBox: data.bounding_box,
        },
        ...prev,
      ]);

      setQuestion('');
    } catch (err) {
      setError(err.message || 'Failed to answer question.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-full flex flex-col gap-6">
      {/* Search Input Bar */}
      <div className="glass-panel p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-xl">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleAsk();
          }}
          className="flex flex-col gap-4"
        >
          <div className="relative flex items-center">
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              disabled={!documentId || loading}
              placeholder={
                documentId
                  ? 'Ask any question about the uploaded medical report...'
                  : 'Please upload a medical report PDF above first...'
              }
              className="w-full pl-5 pr-28 py-4 rounded-xl glass-input text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-500/50 border border-slate-300 dark:border-slate-700/60 transition text-sm font-medium"
            />
            <button
              type="submit"
              disabled={!documentId || !question.trim() || loading}
              className={`absolute right-2 px-5 py-2.5 rounded-lg text-xs font-semibold flex items-center gap-2 transition ${
                !documentId || !question.trim() || loading
                  ? 'bg-slate-200 dark:bg-slate-800 text-slate-400 dark:text-slate-500 cursor-not-allowed'
                  : 'bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 text-slate-950 shadow-glow-emerald cursor-pointer'
              }`}
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Searching...</span>
                </>
              ) : (
                <>
                  <span>Ask AI</span>
                  <Send className="w-3.5 h-3.5" />
                </>
              )}
            </button>
          </div>

          <QuickQuestions
            disabled={!documentId || loading}
            onSelectQuestion={(q) => {
              setQuestion(q);
              handleAsk(q);
            }}
          />
        </form>

        {error && (
          <div className="mt-4 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-xs text-red-500 dark:text-red-400 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4" />
            <span>{error}</span>
          </div>
        )}
      </div>

      {/* Answer History List */}
      <div className="space-y-4">
        {qaHistory.map((item) => {
          const isNotFound = item.answer.includes("does not contain this information");
          const confidencePct = Math.round((item.confidence || 0) * 100);

          return (
            <div
              key={item.id}
              className="glass-panel p-6 rounded-2xl border border-slate-200 dark:border-slate-800/80 transition-all hover:border-slate-300 dark:hover:border-slate-700"
            >
              {/* Question Header */}
              <div className="flex items-start justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-3 mb-4">
                <div className="flex items-center gap-2">
                  <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 dark:bg-emerald-400 animate-pulse" />
                  <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-200">{item.question}</h3>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  {item.pageNumber && (
                    <span className="px-2.5 py-1 rounded-md glass-card border border-slate-300 dark:border-slate-800 text-[11px] text-slate-700 dark:text-slate-300 font-medium flex items-center gap-1">
                      <MapPin className="w-3 h-3 text-emerald-500 dark:text-emerald-400" />
                      Page {item.pageNumber}
                    </span>
                  )}
                  {!isNotFound && (
                    <span
                      className={`px-2.5 py-1 rounded-md text-[11px] font-semibold flex items-center gap-1 border ${
                        confidencePct > 50
                          ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-600 dark:text-emerald-400'
                          : 'bg-amber-500/10 border-amber-500/30 text-amber-600 dark:text-amber-400'
                      }`}
                    >
                      <CheckCircle className="w-3 h-3" />
                      {confidencePct}% Match
                    </span>
                  )}
                </div>
              </div>

              {/* Answer Content */}
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
                <div className={`${item.snippetUrl ? 'lg:col-span-7' : 'lg:col-span-12'} space-y-3`}>
                  <div className="p-4 rounded-xl glass-card border border-slate-200 dark:border-slate-800/80">
                    <p
                      className={`text-sm leading-relaxed ${
                        isNotFound ? 'text-amber-600 dark:text-amber-400/90 font-medium italic' : 'text-slate-800 dark:text-slate-100 font-medium'
                      }`}
                    >
                      {item.answer}
                    </p>
                  </div>
                  {item.boundingBox && (
                    <p className="text-[11px] text-slate-500 font-mono">
                      Bounding Box [x0, y0, x1, y1]: [{item.boundingBox.join(', ')}]
                    </p>
                  )}
                </div>

                {/* Screenshot Crop Preview Card */}
                {item.snippetUrl && (
                  <div className="lg:col-span-5 flex flex-col items-center">
                    <div
                      onClick={() => onOpenCropModal(item.snippetUrl, item.pageNumber, item.answer)}
                      className="group relative w-full overflow-hidden rounded-xl bg-slate-900 border border-emerald-500/30 cursor-pointer hover:border-emerald-400 hover:shadow-glow-emerald transition-all duration-300"
                    >
                      <div className="relative aspect-[4/3] w-full bg-slate-950 flex items-center justify-center">
                        <img
                          src={item.snippetUrl}
                          alt="Cropped Answer Bounding Box Snippet"
                          className="w-full h-full object-contain p-2"
                        />
                        <div className="absolute inset-0 bg-slate-950/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2 text-xs font-semibold text-emerald-300 backdrop-blur-xs">
                          <Eye className="w-4 h-4" />
                          <span>Click to Zoom & Download</span>
                        </div>
                      </div>
                      <div className="px-3 py-2 bg-slate-900/90 border-t border-slate-800 flex items-center justify-between text-[11px] text-slate-400">
                        <span className="flex items-center gap-1 text-emerald-400 font-medium">
                          <ImageIcon className="w-3.5 h-3.5" /> Exact Crop Snippet
                        </span>
                        <span>Page {item.pageNumber}</span>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
