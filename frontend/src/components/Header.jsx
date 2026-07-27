import React from 'react';
import { Activity, FileText, Sparkles, ShieldCheck } from 'lucide-react';

export default function Header({ activeDoc }) {
  return (
    <header className="sticky top-0 z-40 w-full glass-panel border-b border-slate-800 bg-slate-950/80 backdrop-blur-md px-6 py-4">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        
        {/* Brand Logo & Title */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-400 to-teal-600 flex items-center justify-center shadow-glow-emerald">
            <Activity className="w-6 h-6 text-slate-950 stroke-[2.5]" />
          </div>
          <div>
            <h1 className="text-xl font-bold bg-gradient-to-r from-emerald-400 via-teal-300 to-cyan-400 bg-clip-text text-transparent flex items-center gap-2">
              Medical Report Extract AI
              <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 font-semibold">
                Zero Hallucination
              </span>
            </h1>
            <p className="text-xs text-slate-400 font-medium">
              Exact Bounding Box Screenshot Snippets & Precision Medical Extraction
            </p>
          </div>
        </div>

        {/* Right Badges / Active Document Indicator */}
        <div className="flex items-center gap-4">
          {activeDoc ? (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900/80 border border-emerald-500/30 text-xs text-emerald-300">
              <FileText className="w-4 h-4 text-emerald-400" />
              <span className="font-semibold truncate max-w-[200px]">{activeDoc.filename}</span>
              <span className="px-1.5 py-0.5 rounded bg-emerald-500/20 text-[10px] text-emerald-300">
                {activeDoc.page_count} {activeDoc.page_count === 1 ? 'Page' : 'Pages'}
              </span>
            </div>
          ) : (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900/50 border border-slate-800 text-xs text-slate-400">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              <span>PyMuPDF TF-IDF Engine</span>
            </div>
          )}
        </div>

      </div>
    </header>
  );
}
