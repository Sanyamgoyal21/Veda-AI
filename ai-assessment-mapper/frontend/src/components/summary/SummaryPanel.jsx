import { Sparkles } from "lucide-react";
import Spinner from "../common/Spinner.jsx";

function Stat({ value, label, className = "text-ink" }) {
  return (
    <div className="text-center">
      <p className={`text-lg font-extrabold ${className}`}>{value}</p>
      <p className="text-xs text-gray-400">{label}</p>
    </div>
  );
}

export default function SummaryPanel({ summary, onGrade, grading, hasGrading }) {
  return (
    <div className="flex items-center justify-between bg-white rounded-2xl shadow-card px-6 py-4 mb-5 flex-wrap gap-4">
      <div className="flex items-center gap-6 flex-wrap">
        <Stat value={summary.totalQuestions} label="Questions" />
        <Stat value={summary.answered} label="Answered" className="text-emerald-600" />
        <Stat value={summary.unanswered} label="Unanswered" className="text-gray-400" />
        <Stat value={summary.unmatched} label="Unmatched" className="text-red-500" />
        {hasGrading && (
          <Stat
            value={`${summary.totalScore ?? 0}/${summary.totalMaxScore ?? 0}`}
            label={`${summary.percentage ?? 0}%`}
            className="text-brand-orange"
          />
        )}
        {hasGrading && summary.mismatchesSuspected > 0 && (
          <Stat value={summary.mismatchesSuspected} label="Possible mismatches" className="text-amber-600" />
        )}
      </div>

      <button
        onClick={onGrade}
        disabled={grading}
        className="inline-flex items-center gap-2 text-sm font-semibold bg-ink text-white rounded-full px-4 py-2 disabled:opacity-60"
      >
        {grading ? <Spinner size={14} /> : <Sparkles size={14} className="text-brand-orange" fill="currentColor" />}
        {hasGrading ? "Re-grade with AI" : "Grade with AI"}
      </button>
    </div>
  );
}
