/**
 * Presentation-layer helpers over the mapping result the agentic-ai service
 * returns. The actual question<->answer matching happens in the AI service;
 * this module only derives summary stats and attaches URLs the frontend can
 * fetch the original documents from - it never re-decides a mapping.
 */
function buildSummary(assessment) {
  const { mappings, grading } = assessment;

  const answered = mappings.filter((m) => m.match_level !== "unanswered" && m.match_level !== "unmatched");
  const unanswered = mappings.filter((m) => m.match_level === "unanswered");
  const unmatched = mappings.filter((m) => m.match_level === "unmatched");
  const lowConfidence = mappings.filter((m) => m.match_level === "low-confidence");

  const summary = {
    totalQuestions: assessment.questions.length,
    answered: answered.length,
    unanswered: unanswered.length,
    unmatched: unmatched.length,
    lowConfidence: lowConfidence.length,
  };

  if (grading && grading.total_score !== null && grading.total_score !== undefined) {
    summary.totalScore = grading.total_score;
    summary.totalMaxScore = grading.total_max_score;
    summary.percentage = grading.percentage;
    summary.mismatchesSuspected = (grading.grades || []).filter((g) => g.mismatch_suspected).length;
  }

  return summary;
}

function attachFileUrls(assessment, assessmentId, fileMeta = {}) {
  return {
    ...assessment,
    files: {
      questionPaperUrl: `/api/assessment/${assessmentId}/file/question`,
      answerSheetUrl: `/api/assessment/${assessmentId}/file/answer`,
      questionPaper: fileMeta.question,
      answerSheet: fileMeta.answer,
    },
    summary: buildSummary(assessment),
  };
}

module.exports = { buildSummary, attachFileUrls };
