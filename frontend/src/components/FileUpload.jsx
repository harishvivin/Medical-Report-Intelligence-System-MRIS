import React, { useState, useRef } from 'react';
import { UploadCloud, CheckCircle2, AlertCircle, Loader2, Link2 } from 'lucide-react';
import { safeFetchJson, getApiBase, setCustomApiBase } from '../config';

export default function FileUpload({ onUploadSuccess, isProcessing, activeDoc }) {
  const [dragActive, setDragActive] = useState(false);
  const [progress, setProgress] = useState(0);
  const [errorMsg, setErrorMsg] = useState(null);
  const [customUrlInput, setCustomUrlInput] = useState(getApiBase());
  const fileInputRef = useRef(null);

  const handleFileSelect = async (file) => {
    if (!file) return;

    if (!file.name.endsWith('.pdf') && file.type !== 'application/pdf') {
      setErrorMsg('Invalid file format. Please upload a PDF medical report.');
      return;
    }

    setErrorMsg(null);
    setProgress(15);

    const formData = new FormData();
    formData.append('file', file);

    const progressInterval = setInterval(() => {
      setProgress((prev) => (prev < 85 ? prev + 10 : prev));
    }, 200);

    try {
      const data = await safeFetchJson('/api/process', {
        method: 'POST',
        body: formData,
      });

      clearInterval(progressInterval);
      setProgress(100);

      setTimeout(() => {
        onUploadSuccess(data);
        setProgress(0);
      }, 400);

    } catch (err) {
      clearInterval(progressInterval);
      setProgress(0);
      setErrorMsg(err.message || 'Error uploading file.');
    }
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelect(e.dataTransfer.files[0]);
    }
  };

  return (
    <div className="w-full">
      <div
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`relative overflow-hidden cursor-pointer rounded-2xl p-8 text-center transition-all duration-300 glass-panel border-2 ${
          dragActive
            ? 'border-sky-500 bg-sky-500/10 shadow-glow-sky scale-[1.01]'
            : activeDoc
            ? 'border-sky-500/40 bg-white/80 dark:bg-slate-900/60'
            : 'border-slate-200/90 dark:border-slate-800 hover:border-sky-500/50 hover:bg-white dark:hover:bg-slate-900/80'
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,application/pdf"
          className="hidden"
          onChange={(e) => e.target.files && handleFileSelect(e.target.files[0])}
        />

        {/* Ambient background accent glow */}
        <div className="absolute -top-24 -right-24 w-48 h-48 bg-sky-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute -bottom-24 -left-24 w-48 h-48 bg-blue-500/10 rounded-full blur-3xl pointer-events-none" />

        <div className="relative z-10 flex flex-col items-center justify-center gap-3">
          {progress > 0 ? (
            <div className="flex flex-col items-center gap-3 w-full max-w-md py-4">
              <Loader2 className="w-10 h-10 text-sky-500 dark:text-sky-400 animate-spin" />
              <div className="w-full bg-slate-200 dark:bg-slate-800 h-2 rounded-full overflow-hidden">
                <div
                  className="bg-gradient-to-r from-sky-400 to-blue-600 h-full transition-all duration-300 rounded-full"
                  style={{ width: `${progress}%` }}
                />
              </div>
              <p className="text-xs text-slate-700 dark:text-slate-300 font-medium animate-pulse">
                Extracting text spans & indexing multi-page document... {progress}%
              </p>
            </div>
          ) : activeDoc ? (
            <div className="flex items-center justify-between w-full max-w-xl glass-card border border-sky-500/40 p-4 rounded-xl">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-lg bg-sky-500/20 text-sky-600 dark:text-sky-400">
                  <CheckCircle2 className="w-6 h-6" />
                </div>
                <div className="text-left">
                  <p className="text-sm font-semibold text-slate-900 dark:text-slate-100">{activeDoc.filename}</p>
                  <p className="text-xs text-sky-600 dark:text-sky-400 font-medium">
                    Document processed • {activeDoc.page_count} {activeDoc.page_count === 1 ? 'page' : 'pages'} indexed
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  fileInputRef.current?.click();
                }}
                className="px-3 py-1.5 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-xs font-medium text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700 transition"
              >
                Upload Different PDF
              </button>
            </div>
          ) : (
            <>
              <div className="w-14 h-14 rounded-2xl bg-sky-500/10 border border-sky-500/20 flex items-center justify-center text-sky-500 dark:text-sky-400 mb-1 group-hover:scale-110 transition">
                <UploadCloud className="w-7 h-7" />
              </div>
              <div>
                <p className="text-base font-semibold text-slate-800 dark:text-slate-200">
                  Drag & drop your medical report PDF here, or <span className="text-sky-600 dark:text-sky-400 underline underline-offset-4">browse file</span>
                </p>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                  Supports blood tests, discharge summaries, ECG diagnostic reports, radiology & lipid profiles
                </p>
              </div>
            </>
          )}

          {errorMsg && (
            <div
              onClick={(e) => e.stopPropagation()}
              className="flex flex-col items-center gap-3 mt-3 p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-xs text-red-600 dark:text-red-300 w-full max-w-lg"
            >
              <div className="flex items-center gap-2 text-red-600 dark:text-red-400 font-medium">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{errorMsg}</span>
              </div>

              <div className="w-full pt-2 border-t border-red-500/20 flex flex-col gap-2">
                <label className="text-[11px] text-slate-700 dark:text-slate-300 font-medium text-left flex items-center gap-1">
                  <Link2 className="w-3 h-3 text-sky-500" />
                  Connect Backend API URL:
                </label>
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    value={customUrlInput}
                    onChange={(e) => setCustomUrlInput(e.target.value)}
                    placeholder="https://your-backend-app.onrender.com"
                    className="flex-1 px-3 py-1.5 rounded-lg bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 text-slate-900 dark:text-slate-100 text-xs focus:ring-1 focus:ring-sky-500 focus:outline-none"
                  />
                  <button
                    type="button"
                    onClick={() => {
                      setCustomApiBase(customUrlInput);
                      setErrorMsg(null);
                      window.location.reload();
                    }}
                    className="px-3.5 py-1.5 rounded-lg bg-sky-500 hover:bg-sky-400 text-white font-semibold text-xs transition shrink-0"
                  >
                    Connect
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
