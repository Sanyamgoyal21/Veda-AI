import { AlertTriangle } from "lucide-react";
import { MATCH_LEVEL } from "../../constants/index.js";

export default function AnswerStatusNote({ matchLevel, answerText }) {
  if (matchLevel === MATCH_LEVEL.UNANSWERED) {
    return (
      <div className="bg-gray-50 rounded-xl p-3">
        <p className="text-sm text-gray-400">Unanswered — no matching handwritten response was found.</p>
      </div>
    );
  }

  return (
    <div className="bg-gray-50 rounded-xl p-3 space-y-2">
      {matchLevel === MATCH_LEVEL.LOW_CONFIDENCE && (
        <p className="flex items-center gap-1.5 text-xs font-medium text-amber-600">
          <AlertTriangle size={13} />
          Low-confidence match — please verify against the answer sheet
        </p>
      )}
      <p className="text-xs font-semibold text-ink">Transcribed answer</p>
      <p className="text-sm text-gray-500 line-clamp-4">{answerText}</p>
    </div>
  );
}
