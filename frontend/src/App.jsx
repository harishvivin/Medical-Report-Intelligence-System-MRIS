import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import FileUpload from './components/FileUpload';
import QaSection from './components/QaSection';
import SummaryView from './components/SummaryView';
import CropPreviewModal from './components/CropPreviewModal';
import { MessageSquare, FileText, ArrowLeft, FileCheck, Sparkles, ShieldCheck, Zap } from 'lucide-react';

export default function App() {
  const [activeDoc, setActiveDoc] = useState(null);
  const [page, setPage] = useState(1); // 1 = Main Upload Page, 2 = Q&A Workspace Page
  const [activeTab, setActiveTab] = useState('qa'); // 'qa' or 'summary'
  const [cropModalData, setCropModalData] = useState(null);
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem('mris_theme') || 'dark';
  });

  useEffect(() => {
    localStorage.setItem('mris_theme', theme);
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'));
  };

  const handleUploadSuccess = (data) => {
    setActiveDoc(data);
    setActiveTab('qa');
    setPage(2); // Smoothly transition to Page 2 (Q&A Workspace)
  };

  const handleBackToUpload = () => {
    setPage(1); // Return to Page 1 (Main Upload Page)
  };

  return (
    <div className={`min-h-screen flex flex-col font-sans transition-colors duration-300 ${
      theme === 'dark'
        ? 'dark bg-slate-950 text-slate-100 selection:bg-sky-500 selection:text-slate-950'
        : 'bg-slate-100/70 text-slate-900 selection:bg-sky-500 selection:text-white'
    }`}>
      
      {/* Ambient background glow effects */}
      <div className="fixed top-0 left-1/4 w-[600px] h-[600px] bg-sky-500/10 dark:bg-sky-500/5 rounded-full blur-[120px] pointer-events-none -z-10" />
      <div className="fixed bottom-0 right-1/4 w-[600px] h-[600px] bg-blue-500/10 dark:bg-cyan-500/5 rounded-full blur-[120px] pointer-events-none -z-10" />

      {/* Top Header */}
      <Header
        activeDoc={activeDoc}
        currentPage={page}
        theme={theme}
        onToggleTheme={toggleTheme}
        onBackToUpload={handleBackToUpload}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-8 relative z-10">
        
        {/* ==================== PAGE 1: MAIN UPLOAD PAGE ==================== */}
        {page === 1 && (
          <div className="space-y-8 animate-page-enter">
            {/* Hero Banner */}
            <div className="text-center max-w-2xl mx-auto space-y-3 py-4">
              <span className="px-3.5 py-1 rounded-full bg-sky-500/10 border border-sky-500/30 text-sky-600 dark:text-sky-400 text-xs font-bold uppercase tracking-wider inline-flex items-center gap-1.5 shadow-sm">
                <Sparkles className="w-3.5 h-3.5" /> AI Medical Report Intelligence
              </span>
              <h2 className="text-3xl sm:text-4xl font-extrabold text-slate-900 dark:text-slate-100 tracking-tight">
                Upload Medical Report PDF
              </h2>
              <p className="text-sm text-slate-600 dark:text-slate-400 font-medium leading-relaxed">
                Extract precise medical answers, abnormal lab test flags, and visual screenshot snippets across all document pages automatically.
              </p>
            </div>

            {/* Upload Box */}
            <div className="max-w-3xl mx-auto">
              <FileUpload
                activeDoc={activeDoc}
                onUploadSuccess={handleUploadSuccess}
              />
            </div>

            {/* Feature Cards Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-5xl mx-auto pt-4">
              <div className="bg-white dark:bg-slate-900 p-5 rounded-2xl border-2 border-slate-300 dark:border-slate-800 shadow-md space-y-2">
                <div className="w-9 h-9 rounded-xl bg-sky-500/10 text-sky-600 dark:text-sky-400 flex items-center justify-center font-bold">
                  <Zap className="w-5 h-5" />
                </div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">Full 20+ Page Scanning</h3>
                <p className="text-xs text-slate-600 dark:text-slate-400">
                  Scans every single page from Page 1 to end without early stopping or text truncation.
                </p>
              </div>

              <div className="bg-white dark:bg-slate-900 p-5 rounded-2xl border-2 border-slate-300 dark:border-slate-800 shadow-md space-y-2">
                <div className="w-9 h-9 rounded-xl bg-blue-500/10 text-blue-600 dark:text-blue-400 flex items-center justify-center font-bold">
                  <ShieldCheck className="w-5 h-5" />
                </div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">Exact Visual Crops</h3>
                <p className="text-xs text-slate-600 dark:text-slate-400">
                  PyMuPDF coordinate cropper renders high-res PNG screenshots with green highlight boxes.
                </p>
              </div>

              <div className="bg-white dark:bg-slate-900 p-5 rounded-2xl border-2 border-slate-300 dark:border-slate-800 shadow-md space-y-2">
                <div className="w-9 h-9 rounded-xl bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 flex items-center justify-center font-bold">
                  <FileCheck className="w-5 h-5" />
                </div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">Structured Summary</h3>
                <p className="text-xs text-slate-600 dark:text-slate-400">
                  Generates instant patient summary, abnormal value alerts, and lab panel tables.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* ==================== PAGE 2: Q&A WORKSPACE PAGE ==================== */}
        {page === 2 && activeDoc && (
          <div className="space-y-6 animate-page-enter">
            
            {/* Top Workspace Navigation Bar */}
            <div className="bg-white dark:bg-slate-900 p-4 rounded-2xl border-2 border-slate-300 dark:border-slate-800 shadow-lg flex flex-wrap items-center justify-between gap-4">
              
              {/* Back to Upload Button */}
              <button
                onClick={handleBackToUpload}
                className="flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 text-xs font-bold border border-slate-300 dark:border-slate-700 transition shadow-sm"
              >
                <ArrowLeft className="w-4 h-4 text-sky-500" />
                <span>Upload Another Report</span>
              </button>

              {/* Active Document Info Pill */}
              <div className="flex items-center gap-2 px-3.5 py-1.5 rounded-xl bg-sky-500/10 border border-sky-500/30 text-xs text-sky-700 dark:text-sky-300 font-bold">
                <FileCheck className="w-4 h-4 text-sky-500" />
                <span className="truncate max-w-[200px]">{activeDoc.filename}</span>
                <span className="px-1.5 py-0.5 rounded bg-sky-500/20 text-[10px] text-sky-800 dark:text-sky-200 font-extrabold">
                  {activeDoc.page_count} {activeDoc.page_count === 1 ? 'Page' : 'Pages'}
                </span>
              </div>

              {/* Tab Switcher */}
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setActiveTab('qa')}
                  className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all ${
                    activeTab === 'qa'
                      ? 'bg-gradient-to-r from-sky-500 to-blue-600 text-white shadow-glow-sky'
                      : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-300 dark:border-slate-700 hover:bg-slate-200'
                  }`}
                >
                  <MessageSquare className="w-3.5 h-3.5" />
                  <span>Natural Language Q&A</span>
                </button>

                <button
                  onClick={() => setActiveTab('summary')}
                  className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold transition-all ${
                    activeTab === 'summary'
                      ? 'bg-gradient-to-r from-sky-500 to-blue-600 text-white shadow-glow-sky'
                      : 'bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border border-slate-300 dark:border-slate-700 hover:bg-slate-200'
                  }`}
                >
                  <FileText className="w-3.5 h-3.5" />
                  <span>Report Summary</span>
                </button>
              </div>

            </div>

            {/* Q&A / Summary Workspace View */}
            <div className="min-h-[450px]">
              {activeTab === 'qa' ? (
                <QaSection
                  documentId={activeDoc.document_id}
                  onOpenCropModal={(url, pNum, text) =>
                    setCropModalData({ imageUrl: url, pageNumber: pNum, answerText: text })
                  }
                />
              ) : (
                <SummaryView documentId={activeDoc.document_id} />
              )}
            </div>

          </div>
        )}

      </main>

      {/* Footer */}
      <footer className="w-full border-t border-slate-300 dark:border-slate-900 py-6 text-center text-xs font-medium text-slate-600 dark:text-slate-400 bg-white dark:bg-slate-950">
        <p>Medical Report Extract AI • Senior AI Engineering System • Production Ready</p>
      </footer>

      {/* Crop Zoom & Download Modal */}
      {cropModalData && (
        <CropPreviewModal
          imageUrl={cropModalData.imageUrl}
          pageNumber={cropModalData.pageNumber}
          answerText={cropModalData.answerText}
          onClose={() => setCropModalData(null)}
        />
      )}

    </div>
  );
}
