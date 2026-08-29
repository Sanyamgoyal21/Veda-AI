import React, { createContext, useContext, useMemo, useRef, useState, useCallback } from "react";
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
  // Monotonic request identity prevents an old assessment GET from writing
  // its result/error after the user has processed or opened a newer one.
  const assessmentLoadSequence = useRef(0);
  const [correctingMapping, setCorrectingMapping] = useState(false);
  const [correctionError, setCorrectionError] = useState(null);
  const [correctingGrade, setCorrectingGrade] = useState(false);
  const [gradeCorrectionError, setGradeCorrectionError] = useState(null);

  const SETTERS = {
    question: setQuestionFile,
    answer: setAnswerFile,
  };

  const uploadSlot = useCallback(async (slot, file) => {
    setUploadErrors((prev) => ({ ...prev, [slot]: null }));
    setUploading((prev) => ({ ...prev, [slot]: true }));
    try {
      const meta = await api.uploadFile(file);
      const record = { ...meta, localName: file.name };
      SETTERS[slot](record);
      return record;
    } catch (err) {
      setUploadErrors((prev) => ({ ...prev, [slot]: err.message }));
      throw err;
    } finally {
      setUploading((prev) => ({ ...prev, [slot]: false }));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
      assessmentLoadSequence.current += 1;
      setLoadError(null);
      setAssessment(result);
      return result;
    } catch (err) {
      setProcessingError(err.message);
      throw err;
    }
  }, [questionFile, answerFile]);

  const loadAssessmentById = useCallback(async (id) => {
    const sequence = ++assessmentLoadSequence.current;
    setLoadError(null);
    try {
      const result = await api.getAssessment(id);
      if (sequence === assessmentLoadSequence.current) {
        setAssessment(result);
      }
      return result;
    } catch (err) {
      if (sequence === assessmentLoadSequence.current) {
        setLoadError(err.message);
      }
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

  /** answerId: an answer's detected_question_number, or null for "No Answer". */
  const correctMapping = useCallback(
    async (questionNumber, answerId) => {
      if (!assessment) return;
      setCorrectingMapping(true);
      setCorrectionError(null);
      try {
        const updated = await api.correctMapping(assessment.assessmentId, questionNumber, answerId);
        setAssessment(updated);
        return updated;
      } catch (err) {
        setCorrectionError(err.message);
        throw err;
      } finally {
        setCorrectingMapping(false);
      }
    },
    [assessment]
  );

  /** overrides: { score?: number, feedback?: string } - either or both. */
  const correctGrade = useCallback(
    async (questionNumber, overrides) => {
      if (!assessment) return;
      setCorrectingGrade(true);
      setGradeCorrectionError(null);
      try {
        const updated = await api.correctGrade(assessment.assessmentId, questionNumber, overrides);
        setAssessment(updated);
        return updated;
      } catch (err) {
        setGradeCorrectionError(err.message);
        throw err;
      } finally {
        setCorrectingGrade(false);
      }
    },
    [assessment]
  );

  const reset = useCallback(() => {
    assessmentLoadSequence.current += 1;
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

  /** Finds which question (if any) currently holds a given answer, so the UI
   * can warn before reassigning it away from its current question. */
  const mappingForAnswer = useCallback(
    (answerId) => {
      if (!assessment || !answerId) return null;
      return assessment.mappings?.find((m) => m.answer_question_number === answerId && m.question_number) || null;
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
      mappingForAnswer,
      gradeForQuestion,
      unmatchedMappings,

      correctMapping,
      correctingMapping,
      correctionError,

      correctGrade,
      correctingGrade,
      gradeCorrectionError,

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
      mappingForAnswer,
      gradeForQuestion,
      unmatchedMappings,
      correctMapping,
      correctingMapping,
      correctionError,
      correctGrade,
      correctingGrade,
      gradeCorrectionError,
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
