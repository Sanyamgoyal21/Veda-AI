import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import Sidebar from "../components/common/Sidebar.jsx";
import Topbar from "../components/common/Topbar.jsx";
import Spinner from "../components/common/Spinner.jsx";
import SummaryPanel from "../components/summary/SummaryPanel.jsx";
import ValidationWarnings from "../components/assessment/ValidationWarnings.jsx";
import ReviewPanel from "../components/assessment/ReviewPanel.jsx";
import AssessmentLayout from "../components/assessment/AssessmentLayout.jsx";
import QuestionList from "../components/question/QuestionList.jsx";
import AnswerViewer from "../components/viewer/AnswerViewer.jsx";
import ProcessingError from "../components/processing/ProcessingError.jsx";
import { useAssessment } from "../hooks/useAssessment.jsx";
import { resolveFileUrl } from "../services/api.js";
import { MATCH_LEVEL } from "../constants/index.js";

export default function Assessment() {
  const { assessmentId } = useParams();
  const navigate = useNavigate();
  const {
    assessment,
    loadAssessmentById,
    loadError,
    mappingForQuestion,
    gradeForQuestion,
    unmatchedMappings,
    runGrading,
    gradingInProgress,
  } = useAssessment();

  const [selectedKey, setSelectedKey] = useState(null);
  const [loading, setLoading] = useState(!assessment || assessment.assessmentId !== assessmentId);

  useEffect(() => {
    if (assessment && assessment.assessmentId === assessmentId) {
      setLoading(false);
      return;
    }
    setLoading(true);
    loadAssessmentById(assessmentId)
      .catch(() => {})
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [assessmentId]);

  useEffect(() => {
    if (assessment?.questions?.length && !selectedKey) {
      setSelectedKey(assessment.questions[0].number);
    }
  }, [assessment, selectedKey]);

  const selectedMapping = useMemo(() => {
    if (!selectedKey || !assessment) return null;
    if (selectedKey.startsWith("unmatched-")) {
      const number = selectedKey.replace("unmatched-", "");
      return unmatchedMappings.find((m) => m.answer_question_number === number) || null;
    }
    return mappingForQuestion(selectedKey);
  }, [selectedKey, assessment, unmatchedMappings, mappingForQuestion]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#f2f2f0]">
        <Spinner size={28} />
      </div>
    );
  }

  if (!assessment || loadError) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#f2f2f0]">
        <ProcessingError message={loadError} onRetry={() => loadAssessmentById(assessmentId)} onBack={() => navigate("/")} />
      </div>
    );
  }

  const tone = selectedMapping?.match_level === MATCH_LEVEL.UNMATCHED
    ? "unmatched"
    : selectedMapping?.match_level === MATCH_LEVEL.LOW_CONFIDENCE
    ? "low-confidence"
    : "matched";

  const questionLabel = selectedMapping?.question_number || selectedMapping?.answer_question_number;
  const needsReviewMappings = assessment.mappings.filter((m) => m.match_level === MATCH_LEVEL.LOW_CONFIDENCE);

  return (
    <div className="flex min-h-screen bg-[#f2f2f0]">
      <Sidebar variant="collapsed" />
      <div className="flex-1 flex flex-col min-w-0">
        <Topbar title={assessment.files?.questionPaper?.originalName || "Exams"} />

        <main className="flex-1 flex flex-col p-5 min-h-0">
          <SummaryPanel
            summary={assessment.summary}
            onGrade={runGrading}
            grading={gradingInProgress}
            hasGrading={Boolean(assessment.grading)}
          />

          <ValidationWarnings validation={assessment.validation} />

          <ReviewPanel mappings={needsReviewMappings} onSelect={setSelectedKey} />

          <AssessmentLayout
            left={
              <QuestionList
                questions={assessment.questions}
                mappingForQuestion={mappingForQuestion}
                gradeForQuestion={gradeForQuestion}
                selectedKey={selectedKey}
                onSelectQuestion={(q) => setSelectedKey(q.number)}
                unmatchedMappings={unmatchedMappings}
                onSelectUnmatched={(m) => setSelectedKey(`unmatched-${m.answer_question_number}`)}
              />
            }
            right={
              <AnswerViewer
                fileUrl={resolveFileUrl(assessment.files?.answerSheetUrl)}
                fileMeta={assessment.files?.answerSheet}
                activeKey={selectedKey}
                regions={selectedMapping?.answer?.regions || []}
                tag={questionLabel}
                tone={tone}
                emptyMessage={
                  selectedMapping?.match_level === MATCH_LEVEL.UNANSWERED
                    ? "This question was not answered"
                    : undefined
                }
              />
            }
          />
        </main>
      </div>
    </div>
  );
}
