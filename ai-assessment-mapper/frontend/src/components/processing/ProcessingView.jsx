import { useEffect, useState } from "react";
import { Sparkles } from "lucide-react";
import { PROCESSING_STEPS } from "../../constants/index.js";

export default function ProcessingView() {
  const [stepIndex, setStepIndex] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setStepIndex((i) => (i + 1) % PROCESSING_STEPS.length);
    }, 2600);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex flex-col items-center text-center px-6">
      <Sparkles size={56} className="text-brand-orange animate-pulse mb-6" fill="currentColor" />
      <h2 className="text-xl font-bold mb-1">Extracting...</h2>
      <p className="text-gray-400 mb-6">This may take a while</p>
      <p className="text-sm text-gray-500 transition-opacity duration-500">
        {PROCESSING_STEPS[stepIndex]}
      </p>
    </div>
  );
}
