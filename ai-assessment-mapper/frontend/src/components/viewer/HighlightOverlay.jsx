import { normalizedToPixelRect } from "../../utils/highlight.js";

const COLOR_STYLES = {
  matched: "border-emerald-500 bg-emerald-400/10",
  "low-confidence": "border-amber-500 bg-amber-400/10",
  unmatched: "border-red-500 bg-red-400/10",
};

const TAG_STYLES = {
  matched: "bg-emerald-500",
  "low-confidence": "bg-amber-500",
  unmatched: "bg-red-500",
};

/**
 * Renders one highlight box per region that belongs to the currently visible
 * page. Coordinates are recomputed from normalized (0-1) values on every
 * render, so resizing or zooming the page keeps highlights pixel-accurate.
 */
export default function HighlightOverlay({ regions, renderedWidth, renderedHeight, tag, tone = "matched" }) {
  if (!renderedWidth || !renderedHeight) return null;

  return (
    <div className="absolute inset-0 pointer-events-none">
      {regions.map((region, index) => {
        const rect = normalizedToPixelRect(region, renderedWidth, renderedHeight);
        return (
          <div
            key={index}
            className={`absolute rounded-lg border-2 ${COLOR_STYLES[tone]}`}
            style={{ left: rect.left, top: rect.top, width: rect.width, height: rect.height }}
          >
            {tag && (
              <span
                className={`absolute -top-3 left-2 text-[11px] font-semibold text-white px-2 py-0.5 rounded-full ${TAG_STYLES[tone]}`}
              >
                {tag}
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}
