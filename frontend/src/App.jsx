import React, { useState } from 'react';
import Header from './components/Header';
import FileUpload from './components/FileUpload';
import QaSection from './components/QaSection';
import SummaryView from './components/SummaryView';
import CropPreviewModal from './components/CropPreviewModal';
import { MessageSquare, FileText, Sparkles, Activity } from 'lucide-react';

export default function App() {
  const [activeDoc, setActiveDoc] = useState(null);
  const [activeTab, setActiveTab] = useState('qa'); // 'qa' or 'summary'
  const [cropModalData, setCropModalData] = useState(null);

  const handleUploadSuccess = (data) => {
    setActiveDoc(data);
    setActiveTab('qa');
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-emerald-500 selection:text-slate-950">
      
      {/* Top Application Header */}
      <Header activeDoc={activeDoc} />

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 py-8 space-y-8">
        
        {/* Upload Section */}
        <section>
          <FileUpload
            activeDoc={activeDoc}
            onUploadSuccess={handleUploadSuccess}
          />
        </section>

        {/* Tab Selection */}
        {activeDoc && (
          <section className="flex items-center justify-between border-b border-slate-800 pb-4">
            <div className="flex items-center gap-3">
              <button
                onClick={() => setActiveTab('qa')}
                className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-bold transition-all ${
                  activeTab === 'qa'
                    ? 'bg-emerald-500 text-slate-950 shadow-glow-emerald'
                    : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800'
                }`}
              >
                <MessageSquare className="w-4 h-4" />
                <span>Natural Language Q&A</span>
              </button>

              <button
                onClick={() => setActiveTab('summary')}
                className={`flex items-center gap-2 px-5 py-2.5 rounded-xl text-xs font-bold transition-all ${
                  activeTab === 'summary'
                    ? 'bg-emerald-500 text-slate-950 shadow-glow-emerald'
                    : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800'
                }`}
              >
                <FileText className="w-4 h-4" />
                <span>Report Summary & Findings</span>
              </button>
            </div>

            <div className="hidden sm:flex items-center gap-2 text-xs text-emerald-400 font-medium">
              <Activity className="w-4 h-4" />
              <span>Interactive PyMuPDF Index Active</span>
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
      <footer className="w-full border-t border-slate-900 py-6 text-center text-xs text-slate-500 glass-panel">
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
