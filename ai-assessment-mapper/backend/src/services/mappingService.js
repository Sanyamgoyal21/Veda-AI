/**
 * Presentation-layer helpers over the mapping result the agentic-ai service
 * returns, PLUS deterministic manual-correction logic. The AI always
 * proposes a mapping (source: "ai"); a teacher can override any of it
 * through applyManualCorrection below, which is pure Node.js logic - no AI
 * call is ever made to apply a correction the teacher already decided on.
 */
const { ApiError } = require("../utils/validation");

function buildSummary(assessment) {
  const { mappings, grading } = assessment;

  const answered = mappings.filter((m) => m.match_level !== "unanswered" && m.match_level !== "unmatched");
  const unanswered = mappings.filter((m) => m.match_level === "unanswered");
  const unmatched = mappings.filter((m) => m.match_level === "unmatched");
  const lowConfidence = mappings.filter((m) => m.match_level === "low-confidence");
  const teacherVerified = mappings.filter((m) => m.source === "teacher");

  const summary = {
    totalQuestions: assessment.questions.length,
    answered: answered.length,
    unanswered: unanswered.length,
    unmatched: unmatched.length,
    lowConfidence: lowConfidence.length,
    teacherVerified: teacherVerified.length,
  };

  if (grading && grading.total_score !== null && grading.total_score !== undefined) {
    summary.totalScore = grading.total_score;
    summary.totalMaxScore = grading.total_max_score;
    summary.percentage = grading.percentage;
    summary.mismatchesSuspected = (grading.grades || []).filter((g) => g.mismatch_suspected).length;
  }

  return summary;
}

/**
 * Deterministically applies a teacher's manual mapping correction.
 *
 *   answerId === null   -> "No Answer": the question is explicitly marked
 *                          unanswered by the teacher (distinct from an AI
 *                          extraction failure - the teacher is asserting
 *                          this question genuinely has no answer).
 *   answerId === <id>   -> assigns that answer to the question. If the
 *                          answer was already mapped to a DIFFERENT
 *                          question, that question is reset to unanswered
 *                          first - an answer belongs to exactly one
 *                          question at a time, enforced here rather than
 *                          left to chance.
 *
 * Mutates and returns `assessment` in place (the caller holds the only
 * reference, from the in-memory store).
 */
function applyManualCorrection(assessment, questionNumber, answerId) {
  const question = assessment.questions.find((q) => q.number === questionNumber);
  if (!question) {
    throw new ApiError(404, `Unknown question number: ${questionNumber}`);
  }

  let mappings = assessment.mappings.filter((m) => m.question_number !== questionNumber);

  if (answerId === null || answerId === undefined) {
    mappings.push({
      question_number: questionNumber,
      answer_question_number: null,
      match_level: "unanswered",
      match_score: 0,
      source: "teacher",
      question,
      answer: null,
    });
  } else {
    const answer = assessment.answers.find((a) => a.detected_question_number === answerId);
    if (!answer) {
      throw new ApiError(404, `Unknown answer: ${answerId}`);
    }

    // Drop the old "unmatched" entry for this answer, if any - it's matched
    // now. Must happen before the reassignment step below: an unmatched
    // entry has no question_number, so if left in place that step would
    // "reset" it into a phantom question_number=null "unanswered" mapping
    // instead of being cleanly removed here.
    mappings = mappings.filter((m) => !(m.match_level === "unmatched" && m.answer_question_number === answerId));

    // Detach this exact answer from any OTHER question it's currently
    // mapped to - an answer can only belong to one question at a time.
    mappings = mappings.map((m) =>
      m.question_number && m.answer && m.answer.detected_question_number === answerId
        ? { ...m, answer_question_number: null, match_level: "unanswered", match_score: 0, answer: null }
        : m
    );

    mappings.push({
      question_number: questionNumber,
      answer_question_number: answerId,
      match_level: "exact",
      match_score: 1,
      source: "teacher",
      question,
      answer,
    });
  }

  assessment.mappings = mappings;

  // The AI-time validation warnings are a frozen snapshot from when the
  // document was first processed - if the teacher just fixed exactly what
  // one of them was complaining about, showing it forever afterward would
  // be actively confusing ("why does it still say this is unmatched?").
  // Strip only the warnings this specific correction resolved; anything
  // else (duplicates, other low-confidence mappings, etc.) is left alone.
  if (assessment.validation?.warnings) {
    assessment.validation.warnings = assessment.validation.warnings.filter((w) => {
      if (answerId && w.includes(`Answer detected as '${answerId}' has no matching question`)) return false;
      if (w.includes(`Mapping for question '${questionNumber}' has low confidence`)) return false;
      return true;
    });
  }

  return assessment;
}

/**
 * Recomputes grading.total_score/total_max_score/percentage from the
 * current per-question grades - mirrors the Python grading agent's own
 * arithmetic exactly (see grading_agent.py) so a teacher-edited score is
 * reflected in the assessment total the same way an AI-computed one is.
 */
function recomputeGradingTotals(grading) {
  const grades = grading.grades || [];
  if (grades.length === 0) {
    grading.total_score = null;
    grading.total_max_score = null;
    grading.percentage = null;
    return;
  }

  const totalScore = grades.reduce((sum, g) => (g.score !== null && g.score !== undefined ? sum + g.score : sum), 0);
  const totalMaxScore = grades.reduce(
    (sum, g) => (g.max_score !== null && g.max_score !== undefined ? sum + g.max_score : sum),
    0
  );

  grading.total_score = totalScore;
  grading.total_max_score = totalMaxScore;
  grading.percentage = totalMaxScore ? Math.round((totalScore / totalMaxScore) * 1000) / 10 : null;
}

/**
 * Deterministically applies a teacher's override to one question's grade -
 * a corrected score, replacement feedback, or both. Never calls the AI:
 * the teacher has already made the judgment call, this just records it and
 * recomputes the assessment total so it stays consistent.
 */
function applyGradeCorrection(assessment, questionNumber, { score, feedback } = {}) {
  if (!assessment.grading || !Array.isArray(assessment.grading.grades)) {
    throw new ApiError(400, "This assessment has not been graded yet");
  }

  const grade = assessment.grading.grades.find((g) => g.question_number === questionNumber);
  if (!grade) {
    throw new ApiError(404, `No grade found for question '${questionNumber}'`);
  }

  if (score !== undefined) {
    if (typeof score !== "number" || Number.isNaN(score)) {
      throw new ApiError(400, "score must be a number");
    }
    // Clamped exactly like the AI-computed score is (Python never lets the
    // model's own arithmetic exceed the rubric total) - a teacher override
    // gets the same guarantee, not just a bare trust of client input.
    const maxScore = grade.max_score ?? score;
    grade.score = Math.min(Math.max(score, 0), maxScore);
  }

  if (feedback !== undefined) {
    if (typeof feedback !== "string") {
      throw new ApiError(400, "feedback must be a string");
    }
    grade.feedback = feedback;
  }

  grade.teacher_edited = true;
  recomputeGradingTotals(assessment.grading);

  return assessment;
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

module.exports = { buildSummary, attachFileUrls, applyManualCorrection, applyGradeCorrection };
