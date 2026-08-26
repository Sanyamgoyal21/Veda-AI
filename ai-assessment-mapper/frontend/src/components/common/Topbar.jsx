import { ArrowLeft, Clipboard, HelpCircle, Bell, Sparkles, ChevronDown } from "lucide-react";
import { useNavigate } from "react-router-dom";

export default function Topbar({ title = "Exams", dropdown = false, onBack }) {
  const navigate = useNavigate();

  return (
    <header className="flex items-center gap-4 px-6 py-4 bg-white border-b border-gray-100 sticky top-0 z-20">
      <button
        onClick={onBack || (() => navigate(-1))}
        className="text-gray-500 hover:text-ink"
        aria-label="Go back"
      >
        <ArrowLeft size={20} />
      </button>

      <div className="flex items-center gap-2 text-gray-500">
        <Clipboard size={16} />
        <span className="text-sm font-medium">{title}</span>
        {dropdown && <ChevronDown size={14} />}
      </div>

      <div className="ml-auto flex items-center gap-4">
        <button className="text-gray-400 hover:text-gray-600" aria-label="Help">
          <HelpCircle size={19} />
        </button>
        <button className="relative text-gray-400 hover:text-gray-600" aria-label="Notifications">
          <Bell size={19} />
          <span className="absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full bg-brand-orange" />
        </button>
        <button className="text-brand-orange" aria-label="AI Assistant">
          <Sparkles size={19} fill="currentColor" />
        </button>
        <div className="flex items-center gap-2 pl-3 border-l border-gray-100">
          <div className="w-8 h-8 rounded-full bg-gray-200 overflow-hidden flex items-center justify-center text-xs font-semibold text-gray-500">
            MR
          </div>
          <span className="text-sm font-medium hidden sm:inline">Madhur Rastogi</span>
          <ChevronDown size={14} className="text-gray-400" />
        </div>
      </div>
    </header>
  );
}
