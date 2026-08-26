const { ApiError, requireFields } = require("../utils/validation");
const fileService = require("../services/fileService");
const assessmentService = require("../services/assessmentService");
const aiService = require("../services/aiService");
const mappingService = require("../services/mappingService");

async function processAssessment(req, res, next) {
  try {
    requireFields(req.body, ["questionFileId", "answerFileId"]);
    const { questionFileId, answerFileId } = req.body;

    const questionFile = fileService.getFile(questionFileId);
    const answerFile = fileService.getFile(answerFileId);

    const result = await aiService.processAssessment(questionFile.path, answerFile.path);

    const assessmentId = assessmentService.create(result, questionFileId, answerFileId);
    const fileMeta = fileService.getFileMetaPair(questionFileId, answerFileId);

    res.status(201).json({
      assessmentId,
      ...mappingService.attachFileUrls(result, assessmentId, fileMeta),
    });
  } catch (err) {
    next(err);
  }
}

function getAssessment(req, res, next) {
  try {
    const { id } = req.params;
    const record = assessmentService.get(id);
    const fileMeta = fileService.getFileMetaPair(record.questionFileId, record.answerFileId);
    res.json({ assessmentId: id, ...mappingService.attachFileUrls(record.result, id, fileMeta) });
  } catch (err) {
    next(err);
  }
}

function deleteAssessment(req, res, next) {
  try {
    const { id } = req.params;
    assessmentService.remove(id);
    res.status(204).send();
  } catch (err) {
    next(err);
  }
}

function streamFile(req, res, next) {
  try {
    const { id, type } = req.params;
    if (!["question", "answer"].includes(type)) {
      throw new ApiError(400, "type must be 'question' or 'answer'");
    }

    const record = assessmentService.get(id);
    const fileId = type === "question" ? record.questionFileId : record.answerFileId;
    const file = fileService.getFile(fileId);

    res.setHeader("Content-Type", file.mimeType);
    res.sendFile(file.path);
  } catch (err) {
    next(err);
  }
}

module.exports = { processAssessment, getAssessment, deleteAssessment, streamFile };
