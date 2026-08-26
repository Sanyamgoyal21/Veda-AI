const assessmentService = require("../services/assessmentService");
const aiService = require("../services/aiService");
const mappingService = require("../services/mappingService");
const fileService = require("../services/fileService");

async function gradeAssessment(req, res, next) {
  try {
    const { id } = req.params;
    const record = assessmentService.get(id);

    const grading = await aiService.gradeAssessment(record.result.mappings);
    assessmentService.updateGrading(id, grading);

    const updated = assessmentService.get(id);
    const fileMeta = fileService.getFileMetaPair(updated.questionFileId, updated.answerFileId);
    res.json({ assessmentId: id, ...mappingService.attachFileUrls(updated.result, id, fileMeta) });
  } catch (err) {
    next(err);
  }
}

module.exports = { gradeAssessment };
