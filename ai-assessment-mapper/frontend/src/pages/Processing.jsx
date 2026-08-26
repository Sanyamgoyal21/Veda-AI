import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import Sidebar from "../components/common/Sidebar.jsx";
import Topbar from "../components/common/Topbar.jsx";
import ProcessingView from "../components/processing/ProcessingView.jsx";
import ProcessingError from "../components/processing/ProcessingError.jsx";
import { useAssessment } from "../hooks/useAssessment.jsx";

export default function Processing() {
  const navigate = useNavigate();
  const { questionFile, answerFile, startMapping, processingError } = useAssessment();
  const [failed, setFailed] = useState(false);
  const started = useRef(false);

  useEffect(() => {
    if (!questionFile || !answerFile) {
      navigate("/", { replace: true });
      return;
    }
    if (started.current) return;
    started.current = true;
    run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function run() {
    setFailed(false);
    try {
      const result = await startMapping();
      navigate(`/assessment/${result.assessmentId}`, { replace: true });
    } catch {
      setFailed(true);
    }
  }

  const retry = () => {
    started.current = true;
    run();
  };

  return (
    <div className="flex min-h-screen bg-[#f2f2f0]">
      <Sidebar variant="collapsed" />
      <div className="flex-1 flex flex-col">
        <Topbar title="Exams" />
        <main className="flex-1 flex items-center justify-center">
          {failed ? (
            <ProcessingError message={processingError} onRetry={retry} onBack={() => navigate("/")} />
          ) : (
            <ProcessingView />
          )}
        </main>
      </div>
    </div>
  );
}
