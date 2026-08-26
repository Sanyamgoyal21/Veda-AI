import { AlertTriangle, RotateCcw, ArrowLeft } from "lucide-react";
import Button from "../common/Button.jsx";

export default function ProcessingError({ message, onRetry, onBack }) {
  return (
    <div className="flex flex-col items-center text-center px-6 max-w-sm">
      <div className="w-14 h-14 rounded-2xl bg-red-50 flex items-center justify-center mb-5">
        <AlertTriangle size={24} className="text-red-500" />
      </div>
      <h2 className="text-xl font-bold mb-1">Something went wrong</h2>
      <p className="text-gray-400 mb-6 text-sm">
        {message || "We couldn't process these documents. Please try again."}
      </p>
      <div className="flex gap-3">
        <Button variant="outline" onClick={onBack}>
          <ArrowLeft size={15} />
          Back to upload
        </Button>
        <Button onClick={onRetry}>
          <RotateCcw size={15} />
          Retry
        </Button>
      </div>
    </div>
  );
}
