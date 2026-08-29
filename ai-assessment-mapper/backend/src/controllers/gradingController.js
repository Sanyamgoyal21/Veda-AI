const assessmentService = require("../services/assessmentService");
const aiService = require("../services/aiService");
const mappingService = require("../services/mappingService");
const fileService = require("../services/fileService");
const { ApiError, requireFields } = require("../utils/validation");

async function gradeAssessment(req, res, next) {
  try {
    const { id } = req.params;
    const record = assessmentService.get(id);

    const answerFile = fileService.getFile(record.answerFileId);
    const markingSchemeFile = record.markingSchemeFileId
      ? fileService.getFile(record.markingSchemeFileId)
      : null;

    const grading = await aiService.gradeAssessment(
      record.result.mappings,
      answerFile.path,
      markingSchemeFile?.path
    );
    assessmentService.updateGrading(id, grading);

    const updated = assessmentService.get(id);
    const fileMeta = fileService.getFileMetaPair(updated.questionFileId, updated.answerFileId);
    res.json({
      assessmentId: id,
      ...mappingService.attachFileUrls(updated.result, id, fileMeta, Boolean(updated.markingSchemeFileId)),
    });
  } catch (err) {
    next(err);
  }
}

function correctGrade(req, res, next) {
  try {
    const { id } = req.params;
    requireFields(req.body, ["questionNumber"]);
    const { questionNumber, score, feedback } = req.body;

    if (score === undefined && feedback === undefined) {
      throw new ApiError(400, "Provide a score, feedback, or both");
    }

    const record = assessmentService.get(id);
    mappingService.applyGradeCorrection(record.result, questionNumber, { score, feedback });

    const fileMeta = fileService.getFileMetaPair(record.questionFileId, record.answerFileId);
    res.json({
      assessmentId: id,
      ...mappingService.attachFileUrls(record.result, id, fileMeta, Boolean(record.markingSchemeFileId)),
    });
  } catch (err) {
    next(err);
  }
}

module.exports = { gradeAssessment, correctGrade };
