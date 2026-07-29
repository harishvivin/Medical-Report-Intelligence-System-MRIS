import React, { useState, useEffect } from 'react';
import { User, Building, TestTube, Activity, AlertCircle, FileCheck, Loader2, Stethoscope } from 'lucide-react';
import { safeFetchJson } from '../config';

export default function SummaryView({ documentId }) {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!documentId) return;

    const fetchSummary = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await safeFetchJson('/api/summary', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ document_id: documentId }),
        });

        setSummary(data.summary);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchSummary();
  }, [documentId]);

  if (!documentId) {
    return (
      <div className="glass-panel p-8 rounded-2xl border border-slate-200 dark:border-slate-800 text-center py-12">
        <FileCheck className="w-12 h-12 text-slate-400 dark:text-slate-600 mx-auto mb-3" />
        <h3 className="text-base font-semibold text-slate-700 dark:text-slate-300">No Medical Report Loaded</h3>
        <p className="text-xs text-slate-500 mt-1">Upload a PDF report above to view structured summary & findings.</p>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="glass-panel p-12 rounded-2xl border border-slate-200 dark:border-slate-800 text-center flex flex-col items-center justify-center gap-3">
        <Loader2 className="w-8 h-8 text-sky-500 dark:text-sky-400 animate-spin" />
        <p className="text-xs text-slate-700 dark:text-slate-300 font-medium">Extracting patient info, test panels, and abnormal flags...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="glass-panel p-6 rounded-2xl border border-red-500/30 text-red-600 dark:text-red-400 text-xs flex items-center gap-2">
        <AlertCircle className="w-5 h-5 shrink-0" />
        <span>{error}</span>
      </div>
    );
  }

  if (!summary) return null;

  const { patient_info, hospital, tests_performed, important_findings, abnormal_values, recommendations } = summary;

  return (
    <div className="w-full space-y-6">
      
      {/* Top Banner: Patient Info & Hospital Header */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Patient Card */}
        <div className="glass-panel p-5 rounded-2xl border border-slate-200 dark:border-slate-800 relative overflow-hidden">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2.5 rounded-xl bg-sky-500/10 text-sky-600 dark:text-sky-400 border border-sky-500/20">
              <User className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">Patient Details</h3>
              <p className="text-base font-bold text-slate-900 dark:text-slate-100">{patient_info.name}</p>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3 text-xs">
            <div className="glass-card p-2.5 rounded-lg border border-slate-200 dark:border-slate-800">
              <span className="text-slate-500 dark:text-slate-400 block text-[10px]">Age & Gender</span>
              <span className="text-slate-800 dark:text-slate-200 font-medium">{patient_info.age} • {patient_info.gender}</span>
            </div>
            <div className="glass-card p-2.5 rounded-lg border border-slate-200 dark:border-slate-800">
              <span className="text-slate-500 dark:text-slate-400 block text-[10px]">Report Date</span>
              <span className="text-slate-800 dark:text-slate-200 font-medium">{patient_info.date}</span>
            </div>
          </div>
        </div>

        {/* Hospital Card */}
        <div className="glass-panel p-5 rounded-2xl border border-slate-200 dark:border-slate-800 relative overflow-hidden">
          <div className="flex items-center gap-3 mb-4">
            <div className="p-2.5 rounded-xl bg-blue-500/10 text-blue-600 dark:text-blue-400 border border-blue-500/20">
              <Building className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">Hospital / Facility</h3>
              <p className="text-base font-bold text-slate-900 dark:text-slate-100">{hospital}</p>
            </div>
          </div>
          <div className="glass-card p-2.5 rounded-lg border border-slate-200 dark:border-slate-800 text-xs">
            <span className="text-slate-500 dark:text-slate-400 block text-[10px]">Referred By Doctor</span>
            <span className="text-slate-800 dark:text-slate-200 font-medium">{patient_info.ref_doctor}</span>
          </div>
        </div>
      </div>

      {/* Tests Performed Tags */}
      <div className="glass-panel p-5 rounded-2xl border border-slate-200 dark:border-slate-800">
        <div className="flex items-center gap-2 mb-3">
          <TestTube className="w-4 h-4 text-sky-500 dark:text-sky-400" />
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-700 dark:text-slate-300">Tests Performed</h3>
        </div>
        <div className="flex flex-wrap gap-2">
          {tests_performed.map((t, idx) => (
            <span
              key={idx}
              className="px-3 py-1.5 rounded-lg bg-sky-500/10 border border-sky-500/20 text-xs font-medium text-sky-700 dark:text-sky-300"
            >
              {t}
            </span>
          ))}
        </div>
      </div>

      {/* Flagged Abnormal Values Section (If present) */}
      {abnormal_values && abnormal_values.length > 0 && (
        <div className="glass-panel p-5 rounded-2xl border border-amber-500/30 bg-amber-500/5">
          <div className="flex items-center gap-2 mb-3">
            <AlertCircle className="w-4 h-4 text-amber-500 dark:text-amber-400" />
            <h3 className="text-xs font-semibold uppercase tracking-wider text-amber-600 dark:text-amber-400">
              Flagged Abnormal Values ({abnormal_values.length})
            </h3>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {abnormal_values.map((item, idx) => (
              <div key={idx} className="p-3 rounded-xl glass-card border border-amber-500/30 text-xs">
                <p className="font-semibold text-slate-900 dark:text-slate-200">{item.parameter}</p>
                <div className="flex items-center justify-between mt-1.5">
                  <span className="text-amber-600 dark:text-amber-400 font-bold">{item.value}</span>
                  <span className="px-1.5 py-0.5 rounded bg-amber-500/20 text-[10px] text-amber-700 dark:text-amber-300 font-semibold">
                    {item.status}
                  </span>
                </div>
                <p className="text-[10px] text-slate-500 mt-1">Ref Range: {item.reference_range}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Detailed Findings Table */}
      <div className="glass-panel p-5 rounded-2xl border border-slate-200 dark:border-slate-800">
        <div className="flex items-center gap-2 mb-4">
          <Activity className="w-4 h-4 text-sky-500 dark:text-sky-400" />
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-700 dark:text-slate-300">
            Important Lab Findings ({important_findings.length})
          </h3>
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-800 text-slate-500 dark:text-slate-400 font-semibold uppercase text-[10px]">
                <th className="py-2.5 px-3">Parameter / Test</th>
                <th className="py-2.5 px-3">Result Value</th>
                <th className="py-2.5 px-3">Reference Range</th>
                <th className="py-2.5 px-3 text-right">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-slate-800/60 text-slate-800 dark:text-slate-200">
              {important_findings.map((f, idx) => (
                <tr key={idx} className="hover:bg-slate-100/50 dark:hover:bg-slate-900/50 transition">
                  <td className="py-2.5 px-3 font-medium">{f.parameter}</td>
                  <td className="py-2.5 px-3 font-semibold text-sky-600 dark:text-sky-400">{f.value}</td>
                  <td className="py-2.5 px-3 text-slate-500 dark:text-slate-400">{f.reference_range}</td>
                  <td className="py-2.5 px-3 text-right">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                        f.status.toLowerCase().includes('abnormal')
                          ? 'bg-amber-500/20 text-amber-600 dark:text-amber-300'
                          : 'bg-sky-500/20 text-sky-700 dark:text-sky-300'
                      }`}
                    >
                      {f.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Doctor Recommendations (Only if present in document) */}
      {recommendations && recommendations.length > 0 && (
        <div className="glass-panel p-5 rounded-2xl border border-sky-500/30">
          <div className="flex items-center gap-2 mb-3">
            <Stethoscope className="w-4 h-4 text-sky-500 dark:text-sky-400" />
            <h3 className="text-xs font-semibold uppercase tracking-wider text-sky-600 dark:text-sky-300">
              Doctor Recommendations & Notes
            </h3>
          </div>
          <ul className="space-y-2 text-xs text-slate-700 dark:text-slate-200">
            {recommendations.map((rec, idx) => (
              <li key={idx} className="p-3 rounded-xl bg-white/80 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-800 flex items-start gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-sky-500 mt-1.5 shrink-0" />
                <span>{rec}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

    </div>
  );
}
