/**
 * The only module allowed to talk to the agentic-ai (Python/FastAPI) service.
 * No AI prompts or provider details live here or anywhere else in the
 * backend - this is a plain HTTP client for the agentic-ai HTTP contract.
 */
const fs = require("fs");
const axios = require("axios");
const FormData = require("form-data");
const config = require("../config/config");

const client = axios.create({
  baseURL: config.aiServiceUrl,
  // Grading iterates every answered question sequentially (a rubric call
  // plus a grading vision call each), so a long exam with 30+ answered
  // questions can legitimately take several minutes end-to-end - this must
  // stay well above that, not just above a single vision call's latency.
  timeout: 600000,
});

async function processAssessment(questionFilePath, answerFilePath) {
  const form = new FormData();
  form.append("question_file", fs.createReadStream(questionFilePath));
  form.append("answer_file", fs.createReadStream(answerFilePath));

  const response = await client.post("/api/process", form, {
    headers: form.getHeaders(),
    maxBodyLength: Infinity,
    maxContentLength: Infinity,
  });

  return response.data;
}

async function gradeAssessment(mappings, answerFilePath) {
  const form = new FormData();
  form.append("mappings", JSON.stringify(mappings));
  if (answerFilePath) {
    form.append("answer_file", fs.createReadStream(answerFilePath));
  }

  const response = await client.post("/api/grade", form, {
    headers: form.getHeaders(),
    maxBodyLength: Infinity,
    maxContentLength: Infinity,
  });

  return response.data;
}

async function checkHealth() {
  const response = await client.get("/health", { timeout: 5000 });
  return response.data;
}

module.exports = { processAssessment, gradeAssessment, checkHealth };
