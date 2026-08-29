import { useState } from "react";
import { AlertCircle, Pencil } from "lucide-react";
import ManualCorrectionPanel from "../question/ManualCorrectionPanel.jsx";
import { useAssessment } from "../../hooks/useAssessment.jsx";
import { classNames } from "../../utils/formatters.js";

function UnmatchedAnswerRow({ mapping, isSelected, onSelect }) {
  const { assessment, correctMapping, correctingMapping } = useAssessment();
  const [showCorrection, setShowCorrection] = useState(false);

  const questionOptions = (assessment?.questions || []).map((q) => ({
    id: q.number,
    label: `Question ${q.number}`,
    sublabel: q.text,
  }));

  const handleConfirm = async (questionNumber) => {
    if (!questionNumber) return; // "question" mode has no "No Answer" equivalent
    await correctMapping(questionNumber, mapping.answer_question_number);
    setShowCorrection(false);
  };

  return (
    <div className={classNames("rounded-2xl border bg-white", isSelected ? "border-red-400 shadow-card" : "border-gray-100")}>
      <button onClick={onSelect} className="w-full flex items-start gap-3 p-3 text-left">
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

      {isSelected && (
        <div className="px-3 pb-3">
          {!showCorrection ? (
            <button
              onClick={() => setShowCorrection(true)}
              className="flex items-center gap-1.5 text-xs font-semibold text-brand-orange"
            >
              <Pencil size={12} />
              Assign to a question
            </button>
          ) : (
            <ManualCorrectionPanel
              mode="question"
              options={questionOptions}
              onConfirm={handleConfirm}
              onCancel={() => setShowCorrection(false)}
              busy={correctingMapping}
            />
          )}
        </div>
      )}
    </div>
  );
}

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
          return (
            <UnmatchedAnswerRow
              key={key}
              mapping={mapping}
              isSelected={activeKey === key}
              onSelect={() => onSelect(mapping)}
            />
          );
        })}
      </div>
    </div>
  );
}
