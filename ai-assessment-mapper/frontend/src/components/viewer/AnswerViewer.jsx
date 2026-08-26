import { useEffect, useRef, useState } from "react";
import { Document, Page, pdfjs } from "react-pdf";
import { ChevronLeft, ChevronRight, Minus, Plus, FileQuestion } from "lucide-react";
import HighlightOverlay from "./HighlightOverlay.jsx";
import { pagesFromRegions } from "../../utils/highlight.js";

pdfjs.GlobalWorkerOptions.workerSrc = `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.min.mjs`;

const ZOOM_STEP = 10;
const ZOOM_MIN = 50;
const ZOOM_MAX = 250;

/**
 * Renders the original answer-sheet page (PDF or image) and overlays the
 * exact handwritten-answer region using normalized coordinates. Works for
 * any page size/zoom because the overlay is recomputed from the rendered
 * element's live pixel size, never a hard-coded value.
 */
export default function AnswerViewer({ fileUrl, fileMeta, activeKey, regions = [], tag, tone = "matched", emptyMessage }) {
  const [numPages, setNumPages] = useState(fileMeta?.pageCount || 1);
  const [currentPage, setCurrentPage] = useState(1);
  const [zoom, setZoom] = useState(100);
  const [renderedSize, setRenderedSize] = useState({ width: 0, height: 0 });
  const containerRef = useRef(null);

  const isPdf = fileMeta?.mimeType === "application/pdf";
  const relevantPages = pagesFromRegions(regions);

  useEffect(() => {
    setCurrentPage(relevantPages[0] || 1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeKey]);

  useEffect(() => {
    const node = containerRef.current;
    if (!node) return undefined;

    const observer = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (entry) {
        setRenderedSize({ width: entry.contentRect.width, height: entry.contentRect.height });
      }
    });
    observer.observe(node);
    return () => observer.disconnect();
  }, [currentPage, zoom, fileUrl]);

  const regionsOnPage = regions.filter((r) => r.page === currentPage);

  const goToPage = (delta) => {
    setCurrentPage((p) => Math.min(Math.max(1, p + delta), numPages));
  };

  return (
    <div className="flex flex-col h-full bg-ink rounded-2xl overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 text-white">
        <span className="text-sm font-semibold">Answer Sheet</span>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5 bg-white/10 rounded-full px-2 py-1">
            <button
              onClick={() => setZoom((z) => Math.max(ZOOM_MIN, z - ZOOM_STEP))}
              className="p-1 hover:bg-white/10 rounded-full"
              aria-label="Zoom out"
            >
              <Minus size={14} />
            </button>
            <span className="text-xs w-10 text-center tabular-nums">{zoom}%</span>
            <button
              onClick={() => setZoom((z) => Math.min(ZOOM_MAX, z + ZOOM_STEP))}
              className="p-1 hover:bg-white/10 rounded-full"
              aria-label="Zoom in"
            >
              <Plus size={14} />
            </button>
          </div>

          <div className="flex items-center gap-2 bg-white/10 rounded-full px-2 py-1">
            <button
              onClick={() => goToPage(-1)}
              disabled={currentPage <= 1}
              className="p-1 hover:bg-white/10 rounded-full disabled:opacity-30"
              aria-label="Previous page"
            >
              <ChevronLeft size={14} />
            </button>
            <span className="text-xs tabular-nums">
              Page {currentPage} of {numPages}
            </span>
            <button
              onClick={() => goToPage(1)}
              disabled={currentPage >= numPages}
              className="p-1 hover:bg-white/10 rounded-full disabled:opacity-30"
              aria-label="Next page"
            >
              <ChevronRight size={14} />
            </button>
          </div>
        </div>
      </div>

      {relevantPages.length > 1 && (
        <div className="flex items-center gap-2 px-4 pb-2 flex-wrap">
          {relevantPages.map((page, index) => (
            <button
              key={page}
              onClick={() => setCurrentPage(page)}
              className={`text-[11px] px-2.5 py-1 rounded-full font-medium ${
                page === currentPage ? "bg-brand-orange text-white" : "bg-white/10 text-white/70 hover:bg-white/20"
              }`}
            >
              Region {index + 1} · Page {page}
            </button>
          ))}
        </div>
      )}

      <div className="relative flex-1 overflow-auto bg-[#e9e9e6] p-6 flex items-start justify-center">
        {!fileUrl ? (
          <div className="flex flex-col items-center gap-2 text-gray-400 mt-16">
            <FileQuestion size={28} />
            <p className="text-sm">No answer sheet available</p>
          </div>
        ) : (
          <div className="relative inline-block" ref={containerRef}>
            {isPdf ? (
              <Document
                file={fileUrl}
                onLoadSuccess={({ numPages: n }) => setNumPages(n)}
                loading={<PageSkeleton />}
                error={<PageError />}
              >
                <Page
                  pageNumber={currentPage}
                  scale={zoom / 100}
                  renderAnnotationLayer={false}
                  renderTextLayer={false}
                  loading={<PageSkeleton />}
                />
              </Document>
            ) : (
              <img
                src={fileUrl}
                alt="Answer sheet"
                style={{ width: `${(zoom / 100) * 700}px`, maxWidth: "none" }}
                className="rounded-xl shadow-lg"
              />
            )}

            {regionsOnPage.length > 0 && (
              <HighlightOverlay
                regions={regionsOnPage}
                renderedWidth={renderedSize.width}
                renderedHeight={renderedSize.height}
                tag={tag}
                tone={tone}
              />
            )}
          </div>
        )}

        {fileUrl && regions.length === 0 && emptyMessage && (
          <div className="absolute inset-x-0 bottom-6 flex justify-center">
            <span className="bg-white/95 text-sm text-gray-500 px-4 py-2 rounded-full shadow-card">
              {emptyMessage}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

function PageSkeleton() {
  return <div className="w-[600px] h-[800px] max-w-full bg-white/40 animate-pulse rounded-xl" />;
}

function PageError() {
  return (
    <div className="w-[400px] max-w-full bg-white/80 rounded-xl p-6 text-center text-sm text-red-500">
      Couldn't render this document.
    </div>
  );
}
