export const MAX_FILE_SIZE_MB = 10;
export const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024;
export const ACCEPTED_FILE_EXTENSIONS = [".pdf", ".png", ".jpg", ".jpeg"];
export const ACCEPTED_FILE_INPUT = ".pdf,.png,.jpg,.jpeg";

export const MATCH_LEVEL = {
  EXACT: "exact",
  NORMALIZED: "normalized",
  FUZZY: "fuzzy",
  SEMANTIC: "semantic",
  LOW_CONFIDENCE: "low-confidence",
  UNANSWERED: "unanswered",
  UNMATCHED: "unmatched",
};

export const MATCH_LEVEL_LABEL = {
  [MATCH_LEVEL.EXACT]: "Answered",
  [MATCH_LEVEL.NORMALIZED]: "Answered",
  [MATCH_LEVEL.FUZZY]: "Answered",
  [MATCH_LEVEL.SEMANTIC]: "Answered",
  [MATCH_LEVEL.LOW_CONFIDENCE]: "Needs Review",
  [MATCH_LEVEL.UNANSWERED]: "Unanswered",
  [MATCH_LEVEL.UNMATCHED]: "Unmatched",
};

export const MATCH_LEVEL_STYLE = {
  [MATCH_LEVEL.EXACT]: "bg-emerald-50 text-emerald-600",
  [MATCH_LEVEL.NORMALIZED]: "bg-emerald-50 text-emerald-600",
  [MATCH_LEVEL.FUZZY]: "bg-emerald-50 text-emerald-600",
  [MATCH_LEVEL.SEMANTIC]: "bg-emerald-50 text-emerald-600",
  [MATCH_LEVEL.LOW_CONFIDENCE]: "bg-amber-50 text-amber-600",
  [MATCH_LEVEL.UNANSWERED]: "bg-gray-100 text-gray-500",
  [MATCH_LEVEL.UNMATCHED]: "bg-red-50 text-red-600",
};

export const PROCESSING_STEPS = [
  "Extracting questions from the question paper...",
  "Reading handwritten answers...",
  "Mapping answers to questions...",
  "Validating the results...",
];
