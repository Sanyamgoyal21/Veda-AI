import { useState } from "react";
import { ChevronDown, ChevronUp, AlertTriangle, CheckCircle2, Pencil } from "lucide-react";
import Badge from "../common/Badge.jsx";
import AIFeedback from "../answer/AIFeedback.jsx";
import AnswerStatusNote from "../answer/AnswerStatusNote.jsx";
import ManualCorrectionPanel from "./ManualCorrectionPanel.jsx";
import GradeEditPanel from "./GradeEditPanel.jsx";
import { useAssessment } from "../../hooks/useAssessment.jsx";
import { MATCH_LEVEL_LABEL, MATCH_LEVEL_STYLE } from "../../constants/index.js";
import { classNames } from "../../utils/formatters.js";

export default function QuestionItem({ question, mapping, grade, isSelected, isExpanded, onSelect }) {
  const { assessment, mappingForAnswer, correctMapping, correctingMapping, correctGrade, correctingGrade } =
    useAssessment();
  const [showCorrection, setShowCorrection] = useState(false);
  const [showGradeEdit, setShowGradeEdit] = useState(false);

  const matchLevel = mapping?.match_level;
  const isTeacherVerified = mapping?.source === "teacher";
  const hasScore = grade && grade.score !== null && grade.score !== undefined;
  const scoreGood = hasScore && grade.max_score ? grade.score / grade.max_score >= 0.5 : grade?.correct;
  const mismatchSuspected = grade?.mismatch_suspected;

  const showMappingConfidence =
    !grade && !isTeacherVerified && mapping && !["unanswered", "unmatched"].includes(matchLevel);
  const confidencePercent = showMappingConfidence ? Math.round(mapping.match_score * 100) : null;

  const handleConfirmCorrection = async (answerId) => {
    await correctMapping(question.number, answerId);
    setShowCorrection(false);
  };

  const handleConfirmGradeEdit = async (overrides) => {
    await correctGrade(question.number, overrides);
    setShowGradeEdit(false);
  };

  const answerOptions = (assessment?.answers || []).map((a) => ({
    id: a.detected_question_number,
    label: `Answer ${a.detected_question_number}`,
    sublabel: a.text,
  }));

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
          <p className={classNames("text-sm text-gray-500", isExpanded ? "" : "truncate")}>{question.text}</p>
          {isTeacherVerified && (
            <p className="flex items-center gap-1 text-xs mt-0.5 text-emerald-600 font-medium">
              <CheckCircle2 size={12} />
              Teacher Verified
            </p>
          )}
          {showMappingConfidence && (
            <p
              className={classNames(
                "text-xs mt-0.5",
                confidencePercent < 60 ? "text-amber-600" : "text-gray-400"
              )}
            >
              {confidencePercent}% mapping confidence
            </p>
          )}
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
        ) : isTeacherVerified ? (
          <Badge className="bg-emerald-50 text-emerald-600">Verified</Badge>
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
            <AIFeedback grade={grade} />
          ) : (
            <AnswerStatusNote matchLevel={matchLevel} answerText={mapping?.answer?.text} />
          )}

          <div className="flex items-center gap-4 mt-2">
            {!showCorrection && (
              <button
                onClick={() => {
                  setShowCorrection(true);
                  setShowGradeEdit(false);
                }}
                className="flex items-center gap-1.5 text-xs font-semibold text-brand-orange"
              >
                <Pencil size={12} />
                Change Answer
              </button>
            )}

            {grade && !showGradeEdit && (
              <button
                onClick={() => {
                  setShowGradeEdit(true);
                  setShowCorrection(false);
                }}
                className="flex items-center gap-1.5 text-xs font-semibold text-brand-orange"
              >
                <Pencil size={12} />
                Edit Grade
              </button>
            )}
          </div>

          {showCorrection && (
            <ManualCorrectionPanel
              mode="answer"
              options={answerOptions}
              currentId={mapping?.answer?.detected_question_number ?? null}
              currentOwnerNumber={question.number}
              allowNoAnswer
              mappingForAnswer={mappingForAnswer}
              onConfirm={handleConfirmCorrection}
              onCancel={() => setShowCorrection(false)}
              busy={correctingMapping}
            />
          )}

          {showGradeEdit && grade && (
            <GradeEditPanel
              score={grade.score}
              maxScore={grade.max_score}
              feedback={grade.feedback}
              onConfirm={handleConfirmGradeEdit}
              onCancel={() => setShowGradeEdit(false)}
              busy={correctingGrade}
            />
          )}
        </div>
      )}
    </div>
  );
}
