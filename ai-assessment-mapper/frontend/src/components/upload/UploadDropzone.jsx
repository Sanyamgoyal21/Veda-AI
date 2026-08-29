import { useRef } from "react";
import { Upload, FileText, X, AlertCircle } from "lucide-react";
import Spinner from "../common/Spinner.jsx";
import { formatBytes, formatPageLabel, classNames } from "../../utils/formatters.js";
import { ACCEPTED_FILE_INPUT, MAX_FILE_SIZE_MB } from "../../constants/index.js";

export default function UploadDropzone({
  label,
  accentLabel,
  file,
  uploading,
  error,
  onSelect,
  onRemove,
  testId,
}) {
  const inputRef = useRef(null);

  const handleFiles = (fileList) => {
    const selected = fileList?.[0];
    if (selected) onSelect(selected);
  };

  return (
    <div
      className={classNames(
        "flex-1 min-h-[170px] rounded-2xl border-2 border-dashed p-4 flex flex-col items-center justify-center gap-2 transition-colors",
        error ? "border-red-300 bg-red-50/30" : "border-gray-200 bg-white/60"
      )}
      onDragOver={(e) => e.preventDefault()}
      onDrop={(e) => {
        e.preventDefault();
        handleFiles(e.dataTransfer.files);
      }}
    >
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED_FILE_INPUT}
        className="hidden"
        onChange={(e) => handleFiles(e.target.files)}
        data-testid={testId}
      />

      {!file && !uploading && (
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          className="flex flex-col items-center gap-3 text-center"
        >
          <span className="w-11 h-11 rounded-xl bg-gray-100 flex items-center justify-center">
            <Upload size={18} className="text-gray-500" />
          </span>
          <span className="text-sm font-medium text-ink">
            Upload <span className="text-brand-orange font-semibold">{accentLabel}</span>
          </span>
          <span className="text-xs text-gray-400">Max {MAX_FILE_SIZE_MB}MB</span>
        </button>
      )}

      {uploading && (
        <div className="flex flex-col items-center gap-3 text-center">
          <Spinner size={24} />
          <span className="text-sm text-gray-500">Uploading {label.toLowerCase()}...</span>
        </div>
      )}

      {!uploading && file && (
        <div className="relative w-full bg-white rounded-xl shadow-card p-3 flex items-center gap-3">
          <span className="w-9 h-9 rounded-lg bg-red-50 flex items-center justify-center shrink-0">
            <FileText size={18} className="text-red-500" />
          </span>
          <div className="min-w-0">
            <p className="text-sm font-semibold text-ink truncate">{file.localName}</p>
            <p className="text-xs text-gray-400">
              {formatBytes(file.size)} • {formatPageLabel(file.pageCount)}
            </p>
          </div>
          <button
            type="button"
            onClick={onRemove}
            className="absolute -top-2 -right-2 w-6 h-6 rounded-full bg-ink text-white flex items-center justify-center hover:bg-black"
            aria-label={`Remove ${label}`}
          >
            <X size={13} />
          </button>
        </div>
      )}

      {error && (
        <div className="flex items-center gap-1.5 text-xs text-red-500 text-center">
          <AlertCircle size={13} />
          {error}
        </div>
      )}
    </div>
  );
}
