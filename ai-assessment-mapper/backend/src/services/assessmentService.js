/**
 * In-memory assessment store. A real deployment would swap this for a
 * database/Redis, but the API surface (create/get/update/delete) would stay
 * identical - controllers never touch storage directly.
 */
const { v4: uuidv4 } = require("uuid");
const { ApiError } = require("../utils/validation");
const fileService = require("./fileService");

const assessments = new Map(); // assessmentId -> { result, questionFileId, answerFileId, createdAt }

function create(result, questionFileId, answerFileId) {
  const id = uuidv4();
  assessments.set(id, { result, questionFileId, answerFileId, createdAt: Date.now() });
  return id;
}

function get(id) {
  const record = assessments.get(id);
  if (!record) {
    throw new ApiError(404, `No assessment found with id ${id}`);
  }
  return record;
}

function updateGrading(id, grading) {
  const record = get(id);
  record.result.grading = grading;
  return record;
}

function remove(id) {
  const record = get(id);
  fileService.releaseFile(record.questionFileId);
  fileService.releaseFile(record.answerFileId);
  assessments.delete(id);
}

module.exports = { create, get, updateGrading, remove };
