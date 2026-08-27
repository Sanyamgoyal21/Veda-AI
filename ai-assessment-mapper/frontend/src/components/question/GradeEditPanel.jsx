import { useState } from "react";
import { Check } from "lucide-react";
import Button from "../common/Button.jsx";
import Spinner from "../common/Spinner.jsx";

/**
 * Lets a teacher override the AI-assigned score and/or feedback for one
 * question. The score is clamped to [0, maxScore] here too (matching the
 * backend's own clamp in applyGradeCorrection) purely so the input gives
 * immediate feedback - the backend clamp is still the source of truth.
 */
export default function GradeEditPanel({ score, maxScore, feedback, onConfirm, onCancel, busy }) {
  const [scoreInput, setScoreInput] = useState(score ?? "");
  const [feedbackInput, setFeedbackInput] = useState(feedback ?? "");
  const [error, setError] = useState(null);

  const handleConfirmClick = () => {
    const parsed = Number(scoreInput);
    if (scoreInput === "" || Number.isNaN(parsed)) {
      setError("Enter a valid number for the score.");
      return;
    }
    if (maxScore !== null && maxScore !== undefined && parsed > maxScore) {
      setError(`Score cannot exceed ${maxScore}.`);
      return;
    }
    if (parsed < 0) {
      setError("Score cannot be negative.");
      return;
    }
    setError(null);
    onConfirm({ score: parsed, feedback: feedbackInput });
  };

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-3 mt-2">
      <p className="text-xs font-semibold text-ink mb-2">Edit Grade</p>

      <label className="block mb-2">
        <span className="text-xs text-gray-500">
          Score {maxScore !== null && maxScore !== undefined ? `(out of ${maxScore})` : ""}
        </span>
        <input
          type="number"
          min={0}
          max={maxScore ?? undefined}
          step="0.5"
          value={scoreInput}
          disabled={busy}
          onChange={(e) => setScoreInput(e.target.value)}
          className="mt-1 w-24 text-sm border border-gray-200 rounded-lg px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-brand-orange/40"
        />
      </label>

      <label className="block mb-2">
        <span className="text-xs text-gray-500">Feedback</span>
        <textarea
          value={feedbackInput}
          disabled={busy}
          onChange={(e) => setFeedbackInput(e.target.value)}
          rows={3}
          placeholder="Write feedback for the student..."
          className="mt-1 w-full text-sm text-ink border border-gray-200 rounded-lg px-2.5 py-2 resize-y focus:outline-none focus:ring-2 focus:ring-brand-orange/40"
        />
      </label>

      {error && <p className="text-xs text-red-500 mb-2">{error}</p>}

      <div className="flex items-center gap-2">
        <Button onClick={handleConfirmClick} disabled={busy} className="text-xs py-2 px-3">
          {busy ? <Spinner size={12} /> : <Check size={13} />}
          Save Grade
        </Button>
        <Button variant="outline" onClick={onCancel} disabled={busy} className="text-xs py-2 px-3">
          Cancel
        </Button>
      </div>
    </div>
  );
}
