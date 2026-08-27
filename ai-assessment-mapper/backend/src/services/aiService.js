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
  timeout: 120000, // vision extraction over several pages can take a while
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

async function gradeAssessment(mappings, answerFilePath, markingSchemeFilePath) {
  const form = new FormData();
  form.append("mappings", JSON.stringify(mappings));
  if (answerFilePath) {
    form.append("answer_file", fs.createReadStream(answerFilePath));
  }
  if (markingSchemeFilePath) {
    form.append("marking_scheme_file", fs.createReadStream(markingSchemeFilePath));
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
