import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import FileUpload from './components/FileUpload';
import QaSection from './components/QaSection';
import SummaryView from './components/SummaryView';
import CropPreviewModal from './components/CropPreviewModal';
import { MessageSquare, FileText } from 'lucide-react';

export default function App() {
  const [activeDoc, setActiveDoc] = useState(null);
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
  };

  return (
    <div className={`min-h-screen flex flex-col font-sans transition-colors duration-300 ${
      theme === 'dark'
        ? 'dark bg-slate-950 text-slate-100 selection:bg-sky-500 selection:text-slate-950'
        : 'bg-slate-50 text-slate-800 selection:bg-sky-500 selection:text-white'
    }`}>
      
      {/* Ambient background glow effects */}
      <div className="fixed top-0 left-1/4 w-[600px] h-[600px] bg-sky-500/10 dark:bg-sky-500/5 rounded-full blur-[120px] pointer-events-none -z-10" />
      <div className="fixed bottom-0 right-1/4 w-[600px] h-[600px] bg-blue-500/10 dark:bg-cyan-500/5 rounded-full blur-[120px] pointer-events-none -z-10" />

      {/* Top Application Header */}
      <Header
        activeDoc={activeDoc}
        theme={theme}
        onToggleTheme={toggleTheme}
      />

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-8 space-y-8 relative z-10">
        
        {/* Upload Section */}
        <section>
          <FileUpload
            activeDoc={activeDoc}
            onUploadSuccess={handleUploadSuccess}
          />
        </section>

        {/* Tab Selection */}
        {activeDoc && (
          <section className="flex items-center justify-between border-b border-slate-200 dark:border-slate-800 pb-4">
            <div className="flex items-center gap-3">
              <button
                onClick={() => setActiveTab('qa')}
                className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-bold transition-all ${
                  activeTab === 'qa'
                    ? 'bg-gradient-to-r from-sky-500 to-blue-600 text-white shadow-glow-sky'
                    : 'glass-panel text-slate-700 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 border border-slate-200 dark:border-slate-800'
                }`}
              >
                <MessageSquare className="w-4 h-4" />
                <span>Natural Language Q&A</span>
              </button>

              <button
                onClick={() => setActiveTab('summary')}
                className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-bold transition-all ${
                  activeTab === 'summary'
                    ? 'bg-gradient-to-r from-sky-500 to-blue-600 text-white shadow-glow-sky'
                    : 'glass-panel text-slate-700 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 border border-slate-200 dark:border-slate-800'
                }`}
              >
                <FileText className="w-4 h-4" />
                <span>Report Summary & Findings</span>
              </button>
            </div>
          </section>
        )}

        {/* Tab View Contents */}
        <section className="min-h-[400px]">
          {activeTab === 'qa' ? (
            <QaSection
              documentId={activeDoc?.document_id}
              onOpenCropModal={(url, page, text) =>
                setCropModalData({ imageUrl: url, pageNumber: page, answerText: text })
              }
            />
          ) : (
            <SummaryView documentId={activeDoc?.document_id} />
          )}
        </section>

      </main>

      {/* Footer */}
      <footer className="w-full border-t border-slate-200/80 dark:border-slate-900 py-6 text-center text-xs text-slate-500 dark:text-slate-400 glass-panel">
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
