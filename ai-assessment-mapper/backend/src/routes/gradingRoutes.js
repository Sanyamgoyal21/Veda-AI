const express = require("express");
const { gradeAssessment } = require("../controllers/gradingController");

const router = express.Router();

router.post("/:id/grade", gradeAssessment);

module.exports = router;
