import React, { createContext, useContext, useMemo, useState, useCallback } from "react";
import * as api from "../services/api";
import { MATCH_LEVEL } from "../constants";

const AssessmentContext = createContext(null);

export function AssessmentProvider({ children }) {
  const [questionFile, setQuestionFile] = useState(null);
  const [answerFile, setAnswerFile] = useState(null);
  const [uploading, setUploading] = useState({ question: false, answer: false });
  const [uploadErrors, setUploadErrors] = useState({ question: null, answer: null });

  const [assessment, setAssessment] = useState(null);
  const [processingError, setProcessingError] = useState(null);
  const [gradingInProgress, setGradingInProgress] = useState(false);
  const [loadError, setLoadError] = useState(null);

  const uploadSlot = useCallback(async (slot, file) => {
    setUploadErrors((prev) => ({ ...prev, [slot]: null }));
    setUploading((prev) => ({ ...prev, [slot]: true }));
    try {
      const meta = await api.uploadFile(file);
      const record = { ...meta, localName: file.name };
      if (slot === "question") setQuestionFile(record);
      else setAnswerFile(record);
      return record;
    } catch (err) {
      setUploadErrors((prev) => ({ ...prev, [slot]: err.message }));
      throw err;
    } finally {
      setUploading((prev) => ({ ...prev, [slot]: false }));
    }
  }, []);

  const uploadQuestionPaper = useCallback((file) => uploadSlot("question", file), [uploadSlot]);
  const uploadAnswerSheet = useCallback((file) => uploadSlot("answer", file), [uploadSlot]);

  const removeQuestionPaper = useCallback(() => {
    setQuestionFile(null);
    setUploadErrors((prev) => ({ ...prev, question: null }));
  }, []);

  const removeAnswerSheet = useCallback(() => {
    setAnswerFile(null);
    setUploadErrors((prev) => ({ ...prev, answer: null }));
  }, []);

  const startMapping = useCallback(async () => {
    if (!questionFile || !answerFile) {
      throw new Error("Both files must be uploaded before mapping can start.");
    }
    setProcessingError(null);
    try {
      const result = await api.processAssessment(questionFile.fileId, answerFile.fileId);
      setAssessment(result);
      return result;
    } catch (err) {
      setProcessingError(err.message);
      throw err;
    }
  }, [questionFile, answerFile]);

  const loadAssessmentById = useCallback(async (id) => {
    setLoadError(null);
    try {
      const result = await api.getAssessment(id);
      setAssessment(result);
      return result;
    } catch (err) {
      setLoadError(err.message);
      throw err;
    }
  }, []);

  const runGrading = useCallback(async () => {
    if (!assessment) return;
    setGradingInProgress(true);
    try {
      const updated = await api.gradeAssessment(assessment.assessmentId);
      setAssessment(updated);
    } finally {
      setGradingInProgress(false);
    }
  }, [assessment]);

  const reset = useCallback(() => {
    setQuestionFile(null);
    setAnswerFile(null);
    setAssessment(null);
    setProcessingError(null);
    setUploadErrors({ question: null, answer: null });
  }, []);

  const mappingForQuestion = useCallback(
    (questionNumber) => {
      if (!assessment) return null;
      return (
        assessment.mappings?.find((m) => m.question_number === questionNumber) || null
      );
    },
    [assessment]
  );

  const gradeForQuestion = useCallback(
    (questionNumber) => {
      if (!assessment?.grading) return null;
      return assessment.grading.grades?.find((g) => g.question_number === questionNumber) || null;
    },
    [assessment]
  );

  const unmatchedMappings = useMemo(
    () => assessment?.mappings?.filter((m) => m.match_level === MATCH_LEVEL.UNMATCHED) || [],
    [assessment]
  );

  const value = useMemo(
    () => ({
      questionFile,
      answerFile,
      uploading,
      uploadErrors,
      uploadQuestionPaper,
      uploadAnswerSheet,
      removeQuestionPaper,
      removeAnswerSheet,
      bothUploaded: Boolean(questionFile && answerFile),

      assessment,
      startMapping,
      loadAssessmentById,
      loadError,
      processingError,

      runGrading,
      gradingInProgress,

      mappingForQuestion,
      gradeForQuestion,
      unmatchedMappings,

      reset,
    }),
    [
      questionFile,
      answerFile,
      uploading,
      uploadErrors,
      uploadQuestionPaper,
      uploadAnswerSheet,
      removeQuestionPaper,
      removeAnswerSheet,
      assessment,
      startMapping,
      loadAssessmentById,
      loadError,
      processingError,
      runGrading,
      gradingInProgress,
      mappingForQuestion,
      gradeForQuestion,
      unmatchedMappings,
      reset,
    ]
  );

  return <AssessmentContext.Provider value={value}>{children}</AssessmentContext.Provider>;
}

export function useAssessment() {
  const ctx = useContext(AssessmentContext);
  if (!ctx) throw new Error("useAssessment must be used within an AssessmentProvider");
  return ctx;
}
