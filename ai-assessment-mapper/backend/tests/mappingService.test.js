/**
 * Regression tests for the deterministic manual-mapping-correction logic.
 * Uses Node's built-in test runner (node:test) - no extra test framework
 * dependency needed for a backend this size.
 *
 * Run with: npm test  (or: node --test tests/)
 */
const test = require("node:test");
const assert = require("node:assert/strict");
const mappingService = require("../src/services/mappingService");

function makeAssessment() {
  return {
    questions: [
      { number: "7", text: "Q7" },
      { number: "8", text: "Q8" },
      { number: "9", text: "Q9" },
    ],
    answers: [
      { detected_question_number: "8", text: "Answer 8 text" },
      { detected_question_number: "9", text: "Answer 9 text" },
      { detected_question_number: "18", text: "Stray answer" },
    ],
    mappings: [
      { question_number: "7", answer_question_number: null, match_level: "unanswered", match_score: 0, source: "ai", question: { number: "7" }, answer: null },
      { question_number: "8", answer_question_number: "9", match_level: "semantic", match_score: 0.48, source: "ai", question: { number: "8" }, answer: { detected_question_number: "9" } },
      { question_number: "9", answer_question_number: null, match_level: "unanswered", match_score: 0, source: "ai", question: { number: "9" }, answer: null },
      { question_number: null, answer_question_number: "18", match_level: "unmatched", match_score: 0, source: "ai", question: null, answer: { detected_question_number: "18" } },
    ],
    validation: {
      valid: true,
      warnings: [
        "Mapping for question '8' has low confidence (0.48)",
        "Answer detected as '18' has no matching question",
        "Possible missing question number(s): 10, 11",
      ],
      errors: [],
      stats: {},
    },
  };
}

test("reassigning an already-claimed answer resets its previous question to unanswered", () => {
  const a = makeAssessment();
  mappingService.applyManualCorrection(a, "7", "9"); // Q7 <- Answer 9, previously on Q8

  const q7 = a.mappings.find((m) => m.question_number === "7");
  const q8 = a.mappings.find((m) => m.question_number === "8");

  assert.equal(q7.answer_question_number, "9");
  assert.equal(q7.source, "teacher");
  assert.equal(q7.match_level, "exact");
  assert.equal(q8.answer_question_number, null);
  assert.equal(q8.match_level, "unanswered");

  const claimants = a.mappings.filter((m) => m.answer_question_number === "9");
  assert.equal(claimants.length, 1, "an answer must belong to exactly one question at a time");
});

test("teacher can explicitly mark a question as No Answer", () => {
  const a = makeAssessment();
  mappingService.applyManualCorrection(a, "8", null);

  const q8 = a.mappings.find((m) => m.question_number === "8");
  assert.equal(q8.match_level, "unanswered");
  assert.equal(q8.source, "teacher");
  assert.equal(q8.answer, null);

  // The answer that used to be on Q8 is simply freed, not auto-reassigned.
  const q9 = a.mappings.find((m) => m.question_number === "9");
  assert.equal(q9.answer_question_number, null);
});

test("assigning a previously-unmatched answer removes it from the unmatched list", () => {
  const a = makeAssessment();
  const startingCount = a.mappings.length;
  mappingService.applyManualCorrection(a, "9", "18");

  const q9 = a.mappings.find((m) => m.question_number === "9");
  assert.equal(q9.answer_question_number, "18");
  assert.equal(q9.source, "teacher");

  const stillUnmatched = a.mappings.some((m) => m.match_level === "unmatched" && m.answer_question_number === "18");
  assert.equal(stillUnmatched, false);

  // Regression: the unmatched entry (question_number=null) must be removed
  // outright, not "reset" into a phantom question_number=null "unanswered"
  // mapping that would silently inflate the unanswered count. Total mapping
  // count must stay the same (one entry removed, one added for Q9).
  const phantoms = a.mappings.filter((m) => m.question_number === null);
  assert.equal(phantoms.length, 0, "no mapping should ever have a null question_number after a correction");
  // Q9's own entry is replaced 1-for-1; the unmatched "18" entry is deleted
  // outright with no replacement, so the net count drops by exactly one.
  assert.equal(a.mappings.length, startingCount - 1);
});

test("correcting an unknown question number throws a 404 ApiError", () => {
  const a = makeAssessment();
  assert.throws(() => mappingService.applyManualCorrection(a, "999", "9"), (err) => err.statusCode === 404);
});

test("assigning an unknown answer id throws a 404 ApiError", () => {
  const a = makeAssessment();
  assert.throws(() => mappingService.applyManualCorrection(a, "7", "does-not-exist"), (err) => err.statusCode === 404);
});

test("resolving a low-confidence mapping removes only its own stale warning", () => {
  const a = makeAssessment();
  mappingService.applyManualCorrection(a, "8", "9"); // confirms Q8's existing (low-confidence) answer

  assert.ok(!a.validation.warnings.some((w) => w.includes("question '8' has low confidence")));
  // Unrelated warnings must survive untouched.
  assert.ok(a.validation.warnings.some((w) => w.includes("no matching question")));
  assert.ok(a.validation.warnings.some((w) => w.includes("missing question number")));
});

test("resolving an unmatched answer removes only its own stale warning", () => {
  const a = makeAssessment();
  mappingService.applyManualCorrection(a, "9", "18");

  assert.ok(!a.validation.warnings.some((w) => w.includes("no matching question")));
  assert.ok(a.validation.warnings.some((w) => w.includes("question '8' has low confidence")));
  assert.ok(a.validation.warnings.some((w) => w.includes("missing question number")));
});

test("summary.teacherVerified reflects manual corrections live", () => {
  const a = makeAssessment();
  mappingService.applyManualCorrection(a, "7", "9");
  const summary = mappingService.buildSummary(a);
  assert.equal(summary.teacherVerified, 1);
});
