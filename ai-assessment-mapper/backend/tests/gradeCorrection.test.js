/**
 * Regression tests for the deterministic teacher grade-correction logic
 * (score override, feedback override, or both). Uses Node's built-in test
 * runner (node:test) - no extra test framework dependency.
 *
 * Run with: npm test
 */
const test = require("node:test");
const assert = require("node:assert/strict");
const mappingService = require("../src/services/mappingService");

function makeAssessment() {
  return {
    questions: [{ number: "1" }, { number: "2" }],
    answers: [],
    mappings: [],
    grading: {
      grades: [
        { question_number: "1", score: 2, max_score: 5, feedback: "AI feedback for Q1", criteria: [] },
        { question_number: "2", score: 5, max_score: 5, feedback: "AI feedback for Q2", criteria: [] },
      ],
      total_score: 7,
      total_max_score: 10,
      percentage: 70,
      warnings: [],
    },
  };
}

test("teacher can override a question's score", () => {
  const a = makeAssessment();
  mappingService.applyGradeCorrection(a, "1", { score: 4 });

  const g1 = a.grading.grades.find((g) => g.question_number === "1");
  assert.equal(g1.score, 4);
  assert.equal(g1.teacher_edited, true);
  assert.equal(g1.feedback, "AI feedback for Q1", "feedback must be untouched when only score is sent");
});

test("teacher can override a question's feedback", () => {
  const a = makeAssessment();
  mappingService.applyGradeCorrection(a, "2", { feedback: "Well explained, full marks." });

  const g2 = a.grading.grades.find((g) => g.question_number === "2");
  assert.equal(g2.feedback, "Well explained, full marks.");
  assert.equal(g2.score, 5, "score must be untouched when only feedback is sent");
  assert.equal(g2.teacher_edited, true);
});

test("a score override is clamped to the question's max_score", () => {
  const a = makeAssessment();
  mappingService.applyGradeCorrection(a, "1", { score: 999 });

  const g1 = a.grading.grades.find((g) => g.question_number === "1");
  assert.equal(g1.score, 5, "score must never exceed max_score, even from a teacher override");
});

test("a negative score override is clamped to zero", () => {
  const a = makeAssessment();
  mappingService.applyGradeCorrection(a, "1", { score: -3 });

  const g1 = a.grading.grades.find((g) => g.question_number === "1");
  assert.equal(g1.score, 0);
});

test("the assessment total recomputes deterministically after a score override", () => {
  const a = makeAssessment();
  mappingService.applyGradeCorrection(a, "1", { score: 5 }); // was 2, now 5 -> total 7 -> 10

  assert.equal(a.grading.total_score, 10);
  assert.equal(a.grading.total_max_score, 10);
  assert.equal(a.grading.percentage, 100);
});

test("correcting a grade for an ungraded assessment throws a 400 ApiError", () => {
  const a = makeAssessment();
  delete a.grading;
  assert.throws(() => mappingService.applyGradeCorrection(a, "1", { score: 1 }), (err) => err.statusCode === 400);
});

test("correcting an unknown question number throws a 404 ApiError", () => {
  const a = makeAssessment();
  assert.throws(() => mappingService.applyGradeCorrection(a, "999", { score: 1 }), (err) => err.statusCode === 404);
});

test("a non-numeric score throws a 400 ApiError", () => {
  const a = makeAssessment();
  assert.throws(() => mappingService.applyGradeCorrection(a, "1", { score: "five" }), (err) => err.statusCode === 400);
});
