import { useState } from "react";
import MobileTabs from "./MobileTabs.jsx";

export default function AssessmentLayout({ left, right }) {
  const [mobileTab, setMobileTab] = useState("questions");

  return (
    <div className="flex-1 min-h-0">
      <MobileTabs active={mobileTab} onChange={setMobileTab} />

      <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)] gap-5 h-full">
        <div className={mobileTab === "questions" ? "block" : "hidden lg:block"}>{left}</div>
        <div className={mobileTab === "answer" ? "block h-[70vh] lg:h-auto" : "hidden lg:block"}>{right}</div>
      </div>
    </div>
  );
}
