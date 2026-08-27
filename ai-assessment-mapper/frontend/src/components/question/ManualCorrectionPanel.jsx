import { useState } from "react";
import { AlertTriangle, Check } from "lucide-react";
import Button from "../common/Button.jsx";
import Spinner from "../common/Spinner.jsx";
import { classNames } from "../../utils/formatters.js";

const NO_ANSWER_ID = "__no_answer__";

/**
 * Human-in-the-loop mapping correction. Two symmetric modes:
 *  - "answer": editing a QUESTION - the teacher picks which answer belongs
 *    to it (or "No Answer").
 *  - "question": editing an UNMATCHED ANSWER - the teacher picks which
 *    question it actually belongs to.
 * Reassigning an answer/question that's already claimed elsewhere requires
 * an explicit second confirmation - it's never silently stolen.
 */
export default function ManualCorrectionPanel({
  mode,
  options,
  currentId = null,
  currentOwnerNumber = null,
  allowNoAnswer = false,
  mappingForAnswer,
  onConfirm,
  onCancel,
  busy,
}) {
  const [selected, setSelected] = useState(currentId ?? (allowNoAnswer ? NO_ANSWER_ID : options[0]?.id ?? null));
  const [confirmingReassign, setConfirmingReassign] = useState(false);
  const [conflictLabel, setConflictLabel] = useState(null);

  const handleSelect = (id) => {
    setSelected(id);
    setConfirmingReassign(false);
    setConflictLabel(null);
  };

  const handleConfirmClick = () => {
    const finalId = selected === NO_ANSWER_ID ? null : selected;

    if (mode === "answer" && finalId && !confirmingReassign) {
      const existing = mappingForAnswer?.(finalId);
      if (existing && existing.question_number !== currentOwnerNumber) {
        setConflictLabel(existing.question_number);
        setConfirmingReassign(true);
        return;
      }
    }

    onConfirm(finalId);
  };

  const title = mode === "answer" ? "Select Student Answer" : "Assign this answer to";

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-3 mt-2">
      <p className="text-xs font-semibold text-ink mb-2">{title}</p>

      <div className="space-y-1 max-h-56 overflow-y-auto">
        {options.map((option) => (
          <button
            key={option.id}
            onClick={() => handleSelect(option.id)}
            disabled={busy}
            className={classNames(
              "w-full flex items-start gap-2 px-2 py-1.5 rounded-lg text-left transition-colors",
              selected === option.id ? "bg-brand-orangeSoft" : "hover:bg-gray-50"
            )}
          >
            <span
              className={classNames(
                "w-4 h-4 rounded-full border-2 mt-0.5 shrink-0 flex items-center justify-center",
                selected === option.id ? "border-brand-orange" : "border-gray-300"
              )}
            >
              {selected === option.id && <span className="w-2 h-2 rounded-full bg-brand-orange" />}
            </span>
            <span className="min-w-0">
              <p className="text-sm text-ink truncate">{option.label}</p>
              {option.sublabel && <p className="text-xs text-gray-400 truncate">{option.sublabel}</p>}
            </span>
          </button>
        ))}

        {allowNoAnswer && (
          <button
            onClick={() => handleSelect(NO_ANSWER_ID)}
            disabled={busy}
            className={classNames(
              "w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-left transition-colors",
              selected === NO_ANSWER_ID ? "bg-brand-orangeSoft" : "hover:bg-gray-50"
            )}
          >
            <span
              className={classNames(
                "w-4 h-4 rounded-full border-2 shrink-0 flex items-center justify-center",
                selected === NO_ANSWER_ID ? "border-brand-orange" : "border-gray-300"
              )}
            >
              {selected === NO_ANSWER_ID && <span className="w-2 h-2 rounded-full bg-brand-orange" />}
            </span>
            <span className="text-sm text-gray-500">No Answer</span>
          </button>
        )}
      </div>

      {confirmingReassign && (
        <div className="mt-3 bg-amber-50 rounded-lg p-2.5">
          <p className="flex items-start gap-1.5 text-xs text-amber-700">
            <AlertTriangle size={13} className="mt-0.5 shrink-0" />
            This answer is already assigned to Question {conflictLabel}. Reassigning will mark
            that question as unanswered.
          </p>
        </div>
      )}

      <div className="flex items-center gap-2 mt-3">
        <Button onClick={handleConfirmClick} disabled={busy} className="text-xs py-2 px-3">
          {busy ? <Spinner size={12} /> : <Check size={13} />}
          {confirmingReassign ? "Reassign Anyway" : mode === "answer" ? "Confirm Mapping" : "Assign Answer"}
        </Button>
        <Button variant="outline" onClick={onCancel} disabled={busy} className="text-xs py-2 px-3">
          Cancel
        </Button>
      </div>
    </div>
  );
}
