import { ChevronDown, ChevronUp, AlertTriangle } from "lucide-react";
import Badge from "../common/Badge.jsx";
import AIFeedback from "../answer/AIFeedback.jsx";
import AnswerStatusNote from "../answer/AnswerStatusNote.jsx";
import { MATCH_LEVEL_LABEL, MATCH_LEVEL_STYLE } from "../../constants/index.js";
import { classNames } from "../../utils/formatters.js";

export default function QuestionItem({ question, mapping, grade, isSelected, isExpanded, onSelect }) {
  const matchLevel = mapping?.match_level;
  const hasScore = grade && grade.score !== null && grade.score !== undefined;
  const scoreGood = hasScore && grade.max_score ? grade.score / grade.max_score >= 0.5 : grade?.correct;
  const mismatchSuspected = grade?.mismatch_suspected;

  return (
    <div
      className={classNames(
        "rounded-2xl border transition-colors bg-white",
        isSelected ? "border-brand-orange shadow-card" : "border-gray-100"
      )}
    >
      <button
        onClick={onSelect}
        className="w-full flex items-center gap-3 p-4 text-left"
      >
        <span
          className={classNames(
            "w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold shrink-0",
            isSelected ? "bg-brand-orange text-white" : "bg-gray-100 text-gray-500"
          )}
        >
          {question.order}
        </span>

        <span className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-ink">{question.number}</p>
          <p className="text-sm text-gray-500 truncate">{question.text}</p>
        </span>

        {mismatchSuspected ? (
          <Badge className="bg-amber-50 text-amber-700 gap-1">
            <AlertTriangle size={11} />
            Possible mismatch
          </Badge>
        ) : hasScore ? (
          <Badge className={scoreGood ? "bg-emerald-50 text-emerald-600" : "bg-red-50 text-red-600"}>
            {grade.score}/{grade.max_score}
          </Badge>
        ) : (
          <Badge className={MATCH_LEVEL_STYLE[matchLevel] || "bg-gray-100 text-gray-500"}>
            {MATCH_LEVEL_LABEL[matchLevel] || "Unknown"}
          </Badge>
        )}

        {isExpanded ? (
          <ChevronUp size={16} className="text-gray-400 shrink-0" />
        ) : (
          <ChevronDown size={16} className="text-gray-400 shrink-0" />
        )}
      </button>

      {isExpanded && (
        <div className="px-4 pb-4">
          {grade ? (
            <AIFeedback feedback={grade.feedback} mismatchSuspected={grade.mismatch_suspected} />
          ) : (
            <AnswerStatusNote matchLevel={matchLevel} answerText={mapping?.answer?.text} />
          )}
        </div>
      )}
    </div>
  );
}
