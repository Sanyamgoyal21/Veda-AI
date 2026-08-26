export default function AIFeedback({ feedback }) {
  return (
    <div className="bg-gray-50 rounded-xl p-3">
      <p className="text-xs font-semibold text-ink mb-1">AI Feedback</p>
      <p className="text-sm text-gray-500">{feedback}</p>
    </div>
  );
}
