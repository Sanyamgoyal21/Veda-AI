const express = require("express");
const {
  processAssessment,
  getAssessment,
  deleteAssessment,
  streamFile,
  correctMapping,
} = require("../controllers/assessmentController");

const router = express.Router();

router.post("/process", processAssessment);
router.get("/:id", getAssessment);
router.delete("/:id", deleteAssessment);
router.get("/:id/file/:type", streamFile);
router.patch("/:id/mapping", correctMapping);

module.exports = router;
