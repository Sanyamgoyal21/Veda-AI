const express = require("express");
const { gradeAssessment, correctGrade } = require("../controllers/gradingController");

const router = express.Router();

router.post("/:id/grade", gradeAssessment);
router.patch("/:id/grade", correctGrade);

module.exports = router;
