import React, { useState, useRef } from 'react';
import { UploadCloud, FileText, CheckCircle2, AlertCircle, Loader2, ArrowRight } from 'lucide-react';
import { safeFetchJson } from '../config';

export default function FileUpload({ onUploadSuccess, isProcessing, activeDoc }) {
  const [dragActive, setDragActive] = useState(false);
  const [progress, setProgress] = useState(0);
  const [errorMsg, setErrorMsg] = useState(null);
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

    // Simulate smooth progress bar while sending request
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
            ? 'border-emerald-400 bg-emerald-500/10 shadow-glow-emerald scale-[1.01]'
            : activeDoc
            ? 'border-emerald-500/40 bg-slate-900/60'
            : 'border-slate-800 hover:border-emerald-500/50 hover:bg-slate-900/80'
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
        <div className="absolute -top-24 -right-24 w-48 h-48 bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute -bottom-24 -left-24 w-48 h-48 bg-teal-500/10 rounded-full blur-3xl pointer-events-none" />

        <div className="relative z-10 flex flex-col items-center justify-center gap-3">
          {progress > 0 ? (
            <div className="flex flex-col items-center gap-3 w-full max-w-md py-4">
              <Loader2 className="w-10 h-10 text-emerald-400 animate-spin" />
              <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                <div
                  className="bg-gradient-to-r from-emerald-400 to-teal-500 h-full transition-all duration-300 rounded-full"
                  style={{ width: `${progress}%` }}
                />
              </div>
              <p className="text-xs text-slate-300 font-medium animate-pulse">
                Extracting text spans & building TF-IDF index... {progress}%
              </p>
            </div>
          ) : activeDoc ? (
            <div className="flex items-center justify-between w-full max-w-xl bg-slate-900/90 border border-emerald-500/30 p-4 rounded-xl">
              <div className="flex items-center gap-3">
                <div className="p-2.5 rounded-lg bg-emerald-500/20 text-emerald-400">
                  <CheckCircle2 className="w-6 h-6" />
                </div>
                <div className="text-left">
                  <p className="text-sm font-semibold text-slate-100">{activeDoc.filename}</p>
                  <p className="text-xs text-emerald-400">
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
                className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-medium text-slate-300 border border-slate-700 transition"
              >
                Upload Different PDF
              </button>
            </div>
          ) : (
            <>
              <div className="w-14 h-14 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 mb-1 group-hover:scale-110 transition">
                <UploadCloud className="w-7 h-7" />
              </div>
              <div>
                <p className="text-base font-semibold text-slate-200">
                  Drag & drop your medical report PDF here, or <span className="text-emerald-400 underline underline-offset-4">browse file</span>
                </p>
                <p className="text-xs text-slate-400 mt-1">
                  Supports blood tests, discharge summaries, ECG diagnostic reports, radiology & lipid profiles
                </p>
              </div>
            </>
          )}

          {errorMsg && (
            <div className="flex items-center gap-2 mt-2 px-4 py-2 rounded-lg bg-red-500/10 border border-red-500/20 text-xs text-red-400">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{errorMsg}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
