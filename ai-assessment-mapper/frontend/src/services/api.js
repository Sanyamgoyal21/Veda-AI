/**
 * The only module in the frontend that talks to the backend. Components and
 * hooks call these functions instead of using axios directly. The backend is
 * the only thing this app ever talks to - there is no AI provider key or
 * AI endpoint reachable from here.
 */
import axios from "axios";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:5000/api";
const ORIGIN = API_URL.replace(/\/api\/?$/, "");

// Matches the backend's own timeout to the AI service (600000ms) - grading
// a long exam iterates every answered question sequentially and can
// legitimately take several minutes, so the browser must not give up
// before the backend itself would.
const client = axios.create({ baseURL: API_URL, timeout: 600000 });

function unwrapError(error) {
  const message =
    error.response?.data?.error ||
    error.message ||
    "Something went wrong. Please try again.";
  return new Error(message);
}

export async function uploadFile(file) {
  const formData = new FormData();
  formData.append("file", file);
  try {
    const { data } = await client.post("/upload", formData);
    return data;
  } catch (err) {
    throw unwrapError(err);
  }
}

export async function processAssessment(questionFileId, answerFileId) {
  try {
    const { data } = await client.post("/assessment/process", {
      questionFileId,
      answerFileId,
    });
    return data;
  } catch (err) {
    throw unwrapError(err);
  }
}

export async function getAssessment(assessmentId) {
  try {
    const { data } = await client.get(`/assessment/${assessmentId}`);
    return data;
  } catch (err) {
    throw unwrapError(err);
  }
}

export async function gradeAssessment(assessmentId) {
  try {
    const { data } = await client.post(`/assessment/${assessmentId}/grade`);
    return data;
  } catch (err) {
    throw unwrapError(err);
  }
}

/** answerId: the answer's detected_question_number, or null for "No Answer". */
export async function correctMapping(assessmentId, questionNumber, answerId) {
  try {
    const { data } = await client.patch(`/assessment/${assessmentId}/mapping`, {
      questionNumber,
      answerId,
    });
    return data;
  } catch (err) {
    throw unwrapError(err);
  }
}

/** Sends a teacher's edited score, feedback, or both for one question's grade. */
export async function correctGrade(assessmentId, questionNumber, { score, feedback } = {}) {
  try {
    const { data } = await client.patch(`/assessment/${assessmentId}/grade`, {
      questionNumber,
      ...(score !== undefined ? { score } : {}),
      ...(feedback !== undefined ? { feedback } : {}),
    });
    return data;
  } catch (err) {
    throw unwrapError(err);
  }
}

export async function deleteAssessment(assessmentId) {
  try {
    await client.delete(`/assessment/${assessmentId}`);
  } catch (err) {
    throw unwrapError(err);
  }
}

/** Resolves a backend-relative file URL (e.g. "/api/assessment/x/file/question") to an absolute URL. */
export function resolveFileUrl(path) {
  if (!path) return null;
  return `${ORIGIN}${path}`;
}

export default client;
