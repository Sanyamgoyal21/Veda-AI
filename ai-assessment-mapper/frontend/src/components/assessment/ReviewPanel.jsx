import { AlertTriangle, ChevronRight } from "lucide-react";

export default function ReviewPanel({ mappings, onSelect }) {
  if (!mappings || mappings.length === 0) return null;

  return (
    <div className="bg-amber-50 border border-amber-200 rounded-2xl p-4 mb-5">
      <p className="flex items-center gap-1.5 text-sm font-semibold text-amber-800 mb-2">
        <AlertTriangle size={15} />
        Needs Review
      </p>
      <div className="space-y-1 mb-2">
        {mappings.map((m) => (
          <button
            key={m.question_number}
            onClick={() => onSelect(m.question_number)}
            className="w-full flex items-center justify-between px-2 py-1.5 rounded-lg hover:bg-amber-100 text-left"
          >
            <span className="text-sm text-amber-900">Question {m.question_number}</span>
            <span className="flex items-center gap-1 text-xs font-semibold text-amber-700">
              {Math.round(m.match_score * 100)}%
              <ChevronRight size={13} />
            </span>
          </button>
        ))}
      </div>
      <p className="text-xs text-amber-600">
        {mappings.length} mapping{mappings.length === 1 ? "" : "s"} need attention
      </p>
    </div>
  );
}
