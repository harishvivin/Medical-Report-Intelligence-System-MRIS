import React, { useState } from 'react';
import { X, Download, ZoomIn, ZoomOut, RotateCcw, MapPin } from 'lucide-react';

export default function CropPreviewModal({ imageUrl, pageNumber, answerText, onClose }) {
  const [zoom, setZoom] = useState(1);

  if (!imageUrl) return null;

  const handleDownload = () => {
    const link = document.createElement('a');
    link.href = imageUrl;
    link.download = `medical_report_crop_p${pageNumber || 1}.png`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/70 backdrop-blur-md animate-fade-in">
      <div className="relative w-full max-w-4xl glass-panel border border-slate-300 dark:border-slate-700/80 rounded-2xl overflow-hidden shadow-2xl flex flex-col max-h-[90vh]">
        
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-slate-200 dark:border-slate-800 bg-white/90 dark:bg-slate-900/90 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="px-2.5 py-1 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-xs font-semibold text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
              <MapPin className="w-3.5 h-3.5" /> Page {pageNumber} Snippet
            </span>
            <h3 className="text-sm font-semibold text-slate-800 dark:text-slate-200 truncate max-w-md">
              Green Highlighted Bounding Box Screenshot
            </h3>
          </div>

          {/* Action Toolbar */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => setZoom((z) => Math.min(z + 0.3, 2.5))}
              className="p-2 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 text-xs flex items-center gap-1 transition"
              title="Zoom In"
            >
              <ZoomIn className="w-4 h-4" />
            </button>
            <button
              onClick={() => setZoom((z) => Math.max(z - 0.3, 0.7))}
              className="p-2 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 text-xs flex items-center gap-1 transition"
              title="Zoom Out"
            >
              <ZoomOut className="w-4 h-4" />
            </button>
            <button
              onClick={() => setZoom(1)}
              className="p-2 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 text-xs flex items-center gap-1 transition"
              title="Reset Zoom"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
            <button
              onClick={handleDownload}
              className="px-3 py-2 rounded-lg bg-emerald-500 hover:bg-emerald-400 text-slate-950 text-xs font-semibold flex items-center gap-1.5 transition shadow-glow-emerald"
            >
              <Download className="w-4 h-4" />
              <span>Download Crop</span>
            </button>
            <button
              onClick={onClose}
              className="p-2 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-500 hover:text-slate-900 dark:hover:text-slate-100 transition ml-2"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Modal Image Viewport */}
        <div className="flex-1 overflow-auto p-6 bg-slate-900/10 dark:bg-slate-950/90 flex items-center justify-center min-h-[350px]">
          <div
            style={{ transform: `scale(${zoom})`, transformOrigin: 'center center' }}
            className="transition-transform duration-200"
          >
            <img
              src={imageUrl}
              alt="Highlight Crop Preview"
              className="max-w-full rounded-xl border border-emerald-500/40 shadow-2xl"
            />
          </div>
        </div>

        {/* Modal Footer Caption */}
        {answerText && (
          <div className="px-6 py-3 border-t border-slate-200 dark:border-slate-800 bg-white/90 dark:bg-slate-900/90 text-xs text-slate-700 dark:text-slate-300 flex items-center justify-between">
            <span className="text-slate-500 dark:text-slate-400">Extracted Answer Snippet:</span>
            <span className="font-semibold text-emerald-600 dark:text-emerald-400 truncate max-w-xl">{answerText}</span>
          </div>
        )}

      </div>
    </div>
  );
}
