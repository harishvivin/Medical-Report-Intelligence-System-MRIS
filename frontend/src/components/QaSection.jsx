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

      if (!data) {
        throw new Error("No response received from the QA engine.");
      }

      const rawSnippetUrl = data?.snippet_url;
      const fullSnippetUrl = rawSnippetUrl
        ? (rawSnippetUrl.startsWith('http') ? rawSnippetUrl : `${getApiBase()}${rawSnippetUrl}`)
        : null;

      setQaHistory((prev) => [
        {
          id: Date.now(),
          question: targetQ,
          answer: data?.answer || "The uploaded report does not contain this information.",
          pageNumber: data?.page_number || null,
          confidence: data?.confidence || 0,
          snippetUrl: fullSnippetUrl,
          boundingBox: data?.bounding_box || null,
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
      {/* Search Input Bar Panel */}
      <div className="bg-white dark:bg-slate-900 p-6 rounded-2xl border-2 border-slate-300 dark:border-slate-700/80 shadow-xl">
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
              className="w-full pl-5 pr-28 py-4 rounded-xl bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 placeholder-slate-500 dark:placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-sky-500 border-2 border-slate-300 dark:border-slate-700 transition text-sm font-semibold shadow-inner"
            />
            <button
              type="submit"
              disabled={!documentId || !question.trim() || loading}
              className={`absolute right-2 px-5 py-2.5 rounded-lg text-xs font-bold flex items-center gap-2 transition shadow-md ${
                !documentId || !question.trim() || loading
                  ? 'bg-slate-200 dark:bg-slate-800 text-slate-400 dark:text-slate-500 cursor-not-allowed border border-slate-300 dark:border-slate-700'
                  : 'bg-gradient-to-r from-sky-500 to-blue-600 hover:from-sky-400 hover:to-blue-500 text-white shadow-glow-sky cursor-pointer'
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
          <div className="mt-4 p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-xs text-red-600 dark:text-red-400 flex items-center gap-2 font-semibold">
            <AlertTriangle className="w-4 h-4 shrink-0" />
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
              className="bg-white dark:bg-slate-900 p-6 rounded-2xl border-2 border-slate-300 dark:border-slate-800/80 shadow-lg transition-all hover:border-slate-400 dark:hover:border-slate-700"
            >
              {/* Question Header */}
              <div className="flex items-start justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-3 mb-4">
                <div className="flex items-center gap-2">
                  <div className="w-2.5 h-2.5 rounded-full bg-sky-500 dark:bg-sky-400 animate-pulse" />
                  <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">{item.question}</h3>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  {item.pageNumber && (
                    <span className="px-2.5 py-1 rounded-md bg-slate-100 dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-[11px] text-slate-800 dark:text-slate-200 font-bold flex items-center gap-1">
                      <MapPin className="w-3 h-3 text-sky-600 dark:text-sky-400" />
                      Page {item.pageNumber}
                    </span>
                  )}
                  {!isNotFound && (
                    <span
                      className={`px-2.5 py-1 rounded-md text-[11px] font-bold flex items-center gap-1 border ${
                        confidencePct > 50
                          ? 'bg-sky-500/10 border-sky-500/40 text-sky-700 dark:text-sky-300'
                          : 'bg-amber-500/10 border-amber-500/40 text-amber-700 dark:text-amber-300'
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
                  <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-800">
                    <p
                      className={`text-sm leading-relaxed ${
                        isNotFound ? 'text-amber-700 dark:text-amber-400/90 font-semibold italic' : 'text-slate-900 dark:text-slate-100 font-semibold'
                      }`}
                    >
                      {item.answer}
                    </p>
                  </div>
                  {item.boundingBox && (
                    <p className="text-[11px] text-slate-600 dark:text-slate-400 font-mono font-medium">
                      Bounding Box [x0, y0, x1, y1]: [{item.boundingBox.join(', ')}]
                    </p>
                  )}
                </div>

                {/* Screenshot Crop Preview Card */}
                {item.snippetUrl && (
                  <div className="lg:col-span-5 flex flex-col items-center">
                    <div
                      onClick={() => onOpenCropModal(item.snippetUrl, item.pageNumber, item.answer)}
                      className="group relative w-full overflow-hidden rounded-xl bg-slate-900 border-2 border-sky-500/40 cursor-pointer hover:border-sky-400 hover:shadow-glow-sky transition-all duration-300"
                    >
                      <div className="relative aspect-[4/3] w-full bg-slate-950 flex items-center justify-center">
                        <img
                          src={item.snippetUrl}
                          alt="Cropped Answer Bounding Box Snippet"
                          className="w-full h-full object-contain p-2"
                        />
                        <div className="absolute inset-0 bg-slate-950/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2 text-xs font-bold text-sky-300 backdrop-blur-xs">
                          <Eye className="w-4 h-4" />
                          <span>Click to Zoom & Download</span>
                        </div>
                      </div>
                      <div className="px-3 py-2 bg-slate-900/90 border-t border-slate-800 flex items-center justify-between text-[11px] text-slate-300 font-medium">
                        <span className="flex items-center gap-1 text-sky-400 font-bold">
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
