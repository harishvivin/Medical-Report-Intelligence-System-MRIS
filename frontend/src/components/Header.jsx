import React, { useState } from 'react';
import { Activity, FileText, ShieldCheck, Server, Save, X, Sun, Moon } from 'lucide-react';
import { getApiBase, setCustomApiBase } from '../config';

export default function Header({ activeDoc, theme, onToggleTheme }) {
  const [showSettings, setShowSettings] = useState(false);
  const [apiUrl, setApiUrl] = useState(getApiBase());

  const handleSaveApiUrl = () => {
    setCustomApiBase(apiUrl);
    setShowSettings(false);
    window.location.reload();
  };

  return (
    <header className="sticky top-0 z-40 w-full glass-panel border-b border-slate-200 dark:border-slate-800 bg-white/70 dark:bg-slate-950/80 backdrop-blur-md px-6 py-4 transition-colors">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        
        {/* Brand Logo & Title */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-400 to-teal-600 flex items-center justify-center shadow-glow-emerald">
            <Activity className="w-6 h-6 text-slate-950 stroke-[2.5]" />
          </div>
          <div>
            <h1 className="text-xl font-bold bg-gradient-to-r from-emerald-600 via-teal-600 to-cyan-600 dark:from-emerald-400 dark:via-teal-300 dark:to-cyan-400 bg-clip-text text-transparent flex items-center gap-2">
              Medical Report Extract AI
              <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 dark:text-emerald-400 font-semibold">
                Zero Hallucination
              </span>
            </h1>
            <p className="text-xs text-slate-600 dark:text-slate-400 font-medium">
              Exact Bounding Box Screenshot Snippets & Precision Medical Extraction
            </p>
          </div>
        </div>

        {/* Right Badges / Active Document / Theme Switcher / API Server Config */}
        <div className="flex items-center gap-3">
          
          {/* Light / Dark Mode Toggle Button */}
          <button
            onClick={onToggleTheme}
            className="flex items-center gap-2 px-3 py-1.5 rounded-xl glass-card hover:bg-slate-200 dark:hover:bg-slate-800 border border-slate-300 dark:border-slate-700 text-xs font-semibold text-slate-700 dark:text-slate-200 transition-all shadow-sm"
            title={`Switch to ${theme === 'dark' ? 'Light' : 'Dark'} Mode`}
          >
            {theme === 'dark' ? (
              <>
                <Sun className="w-4 h-4 text-amber-400" />
                <span className="hidden sm:inline">Light Mode</span>
              </>
            ) : (
              <>
                <Moon className="w-4 h-4 text-indigo-600" />
                <span className="hidden sm:inline">Dark Mode</span>
              </>
            )}
          </button>

          <button
            onClick={() => setShowSettings(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl glass-card hover:bg-slate-200 dark:hover:bg-slate-800 border border-slate-300 dark:border-slate-700 text-xs text-slate-700 dark:text-slate-300 font-medium transition shadow-sm"
            title="Configure Backend API Server URL"
          >
            <Server className="w-3.5 h-3.5 text-emerald-500 dark:text-emerald-400" />
            <span className="hidden sm:inline">API Server</span>
          </button>

          {activeDoc ? (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl glass-card border border-emerald-500/40 text-xs text-emerald-700 dark:text-emerald-300 shadow-sm">
              <FileText className="w-4 h-4 text-emerald-500 dark:text-emerald-400" />
              <span className="font-semibold truncate max-w-[180px]">{activeDoc.filename}</span>
              <span className="px-1.5 py-0.5 rounded bg-emerald-500/20 text-[10px] text-emerald-700 dark:text-emerald-300">
                {activeDoc.page_count} {activeDoc.page_count === 1 ? 'Page' : 'Pages'}
              </span>
            </div>
          ) : (
            <div className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-xl glass-card text-xs text-slate-600 dark:text-slate-400">
              <ShieldCheck className="w-4 h-4 text-emerald-500 dark:text-emerald-400" />
              <span>PyMuPDF TF-IDF Engine</span>
            </div>
          )}
        </div>

      </div>

      {/* API Server Settings Modal */}
      {showSettings && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/60 backdrop-blur-sm">
          <div className="w-full max-w-md p-6 rounded-2xl glass-panel border border-slate-300 dark:border-slate-700 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-3">
              <div className="flex items-center gap-2 text-slate-900 dark:text-slate-100 font-semibold text-sm">
                <Server className="w-4 h-4 text-emerald-500 dark:text-emerald-400" />
                <span>Backend API Server URL</span>
              </div>
              <button
                onClick={() => setShowSettings(false)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
              If running on GitHub Pages, paste your hosted Render backend URL (e.g. <code className="text-emerald-600 dark:text-emerald-400 bg-slate-100 dark:bg-slate-900 px-1 py-0.5 rounded font-mono">https://medical-report-mris.onrender.com</code>). Leave empty when running locally or directly on Render.
            </p>

            <div>
              <input
                type="text"
                value={apiUrl}
                onChange={(e) => setApiUrl(e.target.value)}
                placeholder="https://your-render-backend-url.onrender.com"
                className="w-full px-4 py-2.5 rounded-xl glass-input text-slate-900 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500 border border-slate-300 dark:border-slate-700 text-xs focus:ring-2 focus:ring-emerald-500/50 focus:outline-none"
              />
            </div>

            <div className="flex items-center justify-end gap-2 pt-2">
              <button
                onClick={() => {
                  setCustomApiBase('');
                  setApiUrl('');
                  setShowSettings(false);
                  window.location.reload();
                }}
                className="px-3 py-1.5 rounded-lg bg-slate-200 dark:bg-slate-800 hover:bg-slate-300 dark:hover:bg-slate-700 text-xs font-medium text-slate-600 dark:text-slate-400"
              >
                Reset Default
              </button>
              <button
                onClick={handleSaveApiUrl}
                className="px-4 py-1.5 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-slate-950 text-xs font-semibold flex items-center gap-1.5 shadow-glow-emerald"
              >
                <Save className="w-3.5 h-3.5" />
                <span>Save API URL</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </header>
  );
}
