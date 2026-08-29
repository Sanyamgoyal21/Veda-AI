import { AlertTriangle, Check, Minus, X } from "lucide-react";
import { classNames } from "../../utils/formatters.js";

const CONFIDENCE_STYLE = {
  high: "bg-emerald-50 text-emerald-600",
  medium: "bg-amber-50 text-amber-600",
  low: "bg-red-50 text-red-500",
};

function CriterionRow({ criterion }) {
  const ratio = criterion.max_marks > 0 ? criterion.awarded_marks / criterion.max_marks : 0;
  const Icon = ratio >= 1 ? Check : ratio > 0 ? Minus : X;
  const color = ratio >= 1 ? "text-emerald-600" : ratio > 0 ? "text-amber-600" : "text-red-500";

  return (
    <div className="flex items-start gap-2 py-1">
      <Icon size={14} className={classNames(color, "mt-0.5 shrink-0")} />
      <div className="min-w-0 flex-1">
        <p className="text-sm text-ink">
          {criterion.criterion}{" "}
          <span className="text-gray-400">
            ({criterion.awarded_marks}/{criterion.max_marks})
          </span>
        </p>
        {criterion.evidence && <p className="text-xs text-gray-400">{criterion.evidence}</p>}
      </div>
    </div>
  );
}

export default function AIFeedback({ grade }) {
  if (!grade) return null;
  const {
    feedback,
    mismatch_suspected: mismatchSuspected,
    criteria,
    confidence,
    rubric_source: rubricSource,
    teacher_edited: teacherEdited,
  } = grade;

  return (
    <div className={mismatchSuspected ? "bg-amber-50 rounded-xl p-3" : "bg-gray-50 rounded-xl p-3"}>
      {mismatchSuspected && (
        <p className="flex items-center gap-1.5 text-xs font-semibold text-amber-700 mb-2">
          <AlertTriangle size={13} />
          This answer may belong to a different question - please verify against the answer sheet
        </p>
      )}

      <div className="flex items-center justify-between mb-2">
        <p className="text-xs font-semibold text-ink">AI Feedback</p>
        <div className="flex items-center gap-1.5">
          {teacherEdited && (
            <span className="text-[10px] font-semibold text-emerald-600 uppercase tracking-wide">
              Teacher Edited
            </span>
          )}
          {rubricSource === "teacher" && (
            <span className="text-[10px] font-medium text-gray-400 uppercase tracking-wide">
              Teacher rubric
            </span>
          )}
          {confidence && (
            <span
              className={classNames(
                "text-[10px] font-semibold px-2 py-0.5 rounded-full capitalize",
                CONFIDENCE_STYLE[confidence] || "bg-gray-100 text-gray-500"
              )}
            >
              {confidence} confidence
            </span>
          )}
        </div>
      </div>

      {criteria && criteria.length > 0 && (
        <div className="mb-2 border-b border-gray-200 pb-2">
          {criteria.map((c, i) => (
            <CriterionRow key={i} criterion={c} />
          ))}
        </div>
      )}

      <p className="text-sm text-gray-500">{feedback}</p>
    </div>
  );
}
