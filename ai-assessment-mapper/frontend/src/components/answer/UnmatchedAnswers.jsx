import { AlertCircle } from "lucide-react";
import { classNames } from "../../utils/formatters.js";

export default function UnmatchedAnswers({ mappings, activeKey, onSelect }) {
  if (mappings.length === 0) return null;

  return (
    <div className="mt-6">
      <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide mb-2 px-1">
        Unmatched answers
      </p>
      <div className="space-y-2">
        {mappings.map((mapping) => {
          const key = `unmatched-${mapping.answer_question_number}`;
          const isSelected = activeKey === key;
          return (
            <button
              key={key}
              onClick={() => onSelect(mapping)}
              className={classNames(
                "w-full flex items-start gap-3 p-3 rounded-2xl border text-left bg-white",
                isSelected ? "border-red-400 shadow-card" : "border-gray-100"
              )}
            >
              <span className="w-7 h-7 rounded-full bg-red-50 flex items-center justify-center shrink-0">
                <AlertCircle size={14} className="text-red-500" />
              </span>
              <span className="min-w-0">
                <p className="text-sm font-semibold text-ink">Unmatched Answer</p>
                <p className="text-xs text-gray-400">
                  Detected question number: {mapping.answer_question_number} — no matching question found.
                </p>
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
