import { Routes, Route, Navigate } from "react-router-dom";
import { AssessmentProvider } from "./hooks/useAssessment.jsx";
import Home from "./pages/Home.jsx";
import Processing from "./pages/Processing.jsx";
import Assessment from "./pages/Assessment.jsx";

export default function App() {
  return (
    <AssessmentProvider>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/processing" element={<Processing />} />
        <Route path="/assessment/:assessmentId" element={<Assessment />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AssessmentProvider>
  );
}
