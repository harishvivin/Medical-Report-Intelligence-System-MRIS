import React from 'react';
import { Activity, FileText, Sun, Moon } from 'lucide-react';

export default function Header({ activeDoc, theme, onToggleTheme }) {
  return (
    <header className="sticky top-0 z-40 w-full glass-panel border-b border-slate-200/80 dark:border-slate-800 bg-white/80 dark:bg-slate-950/80 backdrop-blur-md px-6 py-4 transition-colors">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        
        {/* Brand Logo & Title */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-sky-400 via-blue-500 to-indigo-600 flex items-center justify-center shadow-glow-sky">
            <Activity className="w-6 h-6 text-white stroke-[2.5]" />
          </div>
          <div>
            <h1 className="text-xl font-bold bg-gradient-to-r from-sky-600 via-blue-600 to-indigo-600 dark:from-sky-400 dark:via-blue-300 dark:to-cyan-400 bg-clip-text text-transparent flex items-center gap-2">
              Medical Report Extract AI
              <span className="text-[10px] uppercase tracking-wider px-2 py-0.5 rounded-full bg-sky-500/10 border border-sky-500/20 text-sky-600 dark:text-sky-400 font-semibold">
                Zero Hallucination
              </span>
            </h1>
            <p className="text-xs text-slate-500 dark:text-slate-400 font-medium">
              Exact Bounding Box Screenshot Snippets & Precision Medical Extraction
            </p>
          </div>
        </div>

        {/* Right Badges / Active Document / Theme Switcher */}
        <div className="flex items-center gap-3">
          
          {/* Light / Dark Mode Toggle Button */}
          <button
            onClick={onToggleTheme}
            className="flex items-center gap-2 px-3 py-1.5 rounded-xl glass-card hover:bg-slate-100 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-700 text-xs font-semibold text-slate-700 dark:text-slate-200 transition-all shadow-sm"
            title={`Switch to ${theme === 'dark' ? 'Light' : 'Dark'} Mode`}
          >
            {theme === 'dark' ? (
              <>
                <Sun className="w-4 h-4 text-amber-400" />
                <span className="hidden sm:inline">Light Mode</span>
              </>
            ) : (
              <>
                <Moon className="w-4 h-4 text-sky-600" />
                <span className="hidden sm:inline">Dark Mode</span>
              </>
            )}
          </button>

          {activeDoc && (
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl glass-card border border-sky-500/40 text-xs text-sky-700 dark:text-sky-300 shadow-sm">
              <FileText className="w-4 h-4 text-sky-500 dark:text-sky-400" />
              <span className="font-semibold truncate max-w-[180px]">{activeDoc.filename}</span>
              <span className="px-1.5 py-0.5 rounded bg-sky-500/20 text-[10px] text-sky-700 dark:text-sky-300 font-medium">
                {activeDoc.page_count} {activeDoc.page_count === 1 ? 'Page' : 'Pages'}
              </span>
            </div>
          )}
        </div>

      </div>
    </header>
  );
}
