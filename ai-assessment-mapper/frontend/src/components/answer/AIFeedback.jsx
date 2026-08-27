import { AlertTriangle } from "lucide-react";

export default function AIFeedback({ feedback, mismatchSuspected }) {
  return (
    <div className={mismatchSuspected ? "bg-amber-50 rounded-xl p-3" : "bg-gray-50 rounded-xl p-3"}>
      {mismatchSuspected && (
        <p className="flex items-center gap-1.5 text-xs font-semibold text-amber-700 mb-2">
          <AlertTriangle size={13} />
          This answer may belong to a different question - please verify against the answer sheet
        </p>
      )}
      <p className="text-xs font-semibold text-ink mb-1">AI Feedback</p>
      <p className="text-sm text-gray-500">{feedback}</p>
    </div>
  );
}
