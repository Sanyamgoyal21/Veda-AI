import { useState } from "react";
import { AlertTriangle, ChevronDown, ChevronUp } from "lucide-react";

const COLLAPSE_THRESHOLD = 3;

export default function ValidationWarnings({ validation }) {
  const [expanded, setExpanded] = useState(false);

  if (!validation) return null;
  const items = [...(validation.errors || []), ...(validation.warnings || [])];
  if (items.length === 0) return null;

  const visible = expanded ? items : items.slice(0, COLLAPSE_THRESHOLD);
  const hiddenCount = items.length - visible.length;

  return (
    <div className="bg-amber-50 border border-amber-200 rounded-2xl px-4 py-3 mb-5">
      <div className="flex items-start gap-2">
        <AlertTriangle size={16} className="text-amber-600 mt-0.5 shrink-0" />
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold text-amber-800 mb-1">
            {items.length} item{items.length === 1 ? "" : "s"} to review
          </p>
          <ul className="space-y-1">
            {visible.map((item, i) => (
              <li key={i} className="text-sm text-amber-700">
                {item}
              </li>
            ))}
          </ul>
          {hiddenCount > 0 && (
            <button
              onClick={() => setExpanded(true)}
              className="mt-1 inline-flex items-center gap-1 text-xs font-semibold text-amber-700 hover:text-amber-900"
            >
              Show {hiddenCount} more <ChevronDown size={12} />
            </button>
          )}
          {expanded && items.length > COLLAPSE_THRESHOLD && (
            <button
              onClick={() => setExpanded(false)}
              className="mt-1 inline-flex items-center gap-1 text-xs font-semibold text-amber-700 hover:text-amber-900"
            >
              Show less <ChevronUp size={12} />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
