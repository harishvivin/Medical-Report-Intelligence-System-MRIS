import React from 'react';
import { HelpCircle, User, Droplet, Activity, Heart, ShieldAlert, FileSearch } from 'lucide-react';

const SUGGESTIONS = [
  { label: "Patient Name & Age", icon: User, query: "What is the patient name, age, and gender?" },
  { label: "Hemoglobin Level", icon: Droplet, query: "What is the Hemoglobin level in the report?" },
  { label: "Serum Creatinine", icon: Activity, query: "What is the Creatinine level?" },
  { label: "HbA1c / Glucose", icon: Droplet, query: "What is the HbA1c or Fasting Blood Sugar?" },
  { label: "Blood Pressure", icon: Heart, query: "What is the Blood Pressure reading?" },
  { label: "HIV Test Status", icon: ShieldAlert, query: "What is the HIV test status?" },
  { label: "ECG Findings", icon: Activity, query: "What are the ECG or Heart findings?" },
  { label: "Abnormal Values", icon: FileSearch, query: "Are there any high or low abnormal values?" },
];

export default function QuickQuestions({ onSelectQuestion, disabled }) {
  return (
    <div className="w-full">
      <div className="flex items-center gap-2 mb-2">
        <HelpCircle className="w-4 h-4 text-emerald-500 dark:text-emerald-400" />
        <span className="text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider">
          Suggested Questions
        </span>
      </div>

      <div className="flex flex-wrap gap-2">
        {SUGGESTIONS.map((item, idx) => {
          const Icon = item.icon;
          return (
            <button
              key={idx}
              type="button"
              disabled={disabled}
              onClick={() => onSelectQuestion(item.query)}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs font-medium transition-all ${
                disabled
                  ? 'glass-card opacity-50 text-slate-400 cursor-not-allowed'
                  : 'glass-card hover:bg-emerald-500/10 text-slate-700 dark:text-slate-300 hover:text-emerald-600 dark:hover:text-emerald-400 border border-slate-300 dark:border-slate-700 hover:border-emerald-500/40 shadow-sm'
              }`}
            >
              <Icon className="w-3.5 h-3.5 text-emerald-500 dark:text-emerald-400" />
              <span>{item.label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
