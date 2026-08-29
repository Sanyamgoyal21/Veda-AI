import { useNavigate } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import Sidebar from "../components/common/Sidebar.jsx";
import Topbar from "../components/common/Topbar.jsx";
import Button from "../components/common/Button.jsx";
import TeacherAvatar from "../components/upload/TeacherAvatar.jsx";
import UploadDropzone from "../components/upload/UploadDropzone.jsx";
import { useAssessment } from "../hooks/useAssessment.jsx";

function useSubtitle(questionFile, answerFile) {
  if (questionFile && answerFile) return "Both files uploaded — you're ready to start mapping";
  if (questionFile && !answerFile) return "Question paper uploaded — answer sheet missing";
  if (!questionFile && answerFile) return "Answer sheet uploaded — question paper missing";
  return "Upload both files to get started";
}

export default function Home() {
  const navigate = useNavigate();
  const {
    questionFile,
    answerFile,
    uploading,
    uploadErrors,
    uploadQuestionPaper,
    uploadAnswerSheet,
    removeQuestionPaper,
    removeAnswerSheet,
    bothUploaded,
  } = useAssessment();

  const subtitle = useSubtitle(questionFile, answerFile);

  const UPLOAD_FNS = {
    question: uploadQuestionPaper,
    answer: uploadAnswerSheet,
  };

  const handleSelect = (slot, file) => {
    UPLOAD_FNS[slot](file).catch(() => {});
  };

  return (
    <div className="flex min-h-screen bg-[#f2f2f0]">
      <Sidebar variant="expanded" />

      <div className="flex-1 flex flex-col">
        <Topbar title="Exams" />

        <main className="flex-1 flex flex-col items-center px-6 py-16">
          <h1 className="text-3xl md:text-4xl font-extrabold text-center leading-tight mb-3">
            Upload{" "}
            <span className="bg-brand-orangeSoft text-brand-orange px-3 py-1 rounded-lg underline decoration-2 underline-offset-4">
              Question Paper &amp; Answer Sheets
            </span>
          </h1>
          <p className="text-gray-500 mb-8">{subtitle}</p>

          <TeacherAvatar />

          <div className="w-full max-w-3xl flex flex-col sm:flex-row gap-5">
            <UploadDropzone
              label="Question Paper"
              accentLabel="Question Paper"
              file={questionFile}
              uploading={uploading.question}
              error={uploadErrors.question}
              onSelect={(file) => handleSelect("question", file)}
              onRemove={removeQuestionPaper}
              testId="upload-question"
            />
            <UploadDropzone
              label="Answer Sheet"
              accentLabel="Answer Sheet"
              file={answerFile}
              uploading={uploading.answer}
              error={uploadErrors.answer}
              onSelect={(file) => handleSelect("answer", file)}
              onRemove={removeAnswerSheet}
              testId="upload-answer"
            />
          </div>

          <Button
            className="mt-10"
            disabled={!bothUploaded}
            onClick={() => navigate("/processing")}
          >
            Start Mapping
            <ArrowRight size={16} />
          </Button>

          <p className="text-xs text-gray-400 mt-3">
            Once both files are uploaded, you'll be able to map answers with questions
          </p>
        </main>
      </div>
    </div>
  );
}
