import {
  LayoutGrid,
  School,
  FileText,
  ClipboardList,
  History,
  Settings,
  Sparkles,
  PanelLeftClose,
  ChevronRight,
} from "lucide-react";
import { classNames } from "../../utils/formatters";

const NAV_ITEMS = [
  { icon: LayoutGrid, label: "Home" },
  { icon: School, label: "My Classroom" },
  { icon: FileText, label: "Assignments" },
  { icon: ClipboardList, label: "Exams", active: true },
  { icon: History, label: "My Library" },
];

export default function Sidebar({ variant = "expanded" }) {
  const collapsed = variant === "collapsed";

  return (
    <aside
      className={classNames(
        "hidden md:flex flex-col justify-between bg-white shrink-0 h-screen sticky top-0 py-6 border-r border-gray-100 transition-all",
        collapsed ? "w-20 px-3" : "w-64 px-5"
      )}
    >
      <div>
        <div className={classNames("flex items-center gap-2 mb-6", collapsed && "justify-center")}>
          <div className="w-9 h-9 rounded-xl bg-ink flex items-center justify-center shrink-0">
            <span className="text-white font-extrabold text-lg">V</span>
          </div>
          {!collapsed && <span className="font-extrabold text-lg tracking-tight">VedaAI</span>}
          {!collapsed && (
            <button className="ml-auto text-gray-300 hover:text-gray-500" aria-label="Collapse sidebar">
              <PanelLeftClose size={18} />
            </button>
          )}
        </div>

        {collapsed ? (
          <div className="w-11 h-11 mx-auto rounded-xl bg-ink flex items-center justify-center mb-6 ring-2 ring-brand-orange">
            <Sparkles size={18} className="text-brand-orange" fill="currentColor" />
          </div>
        ) : (
          <button className="w-full flex items-center justify-center gap-2 bg-ink text-white text-sm font-semibold rounded-full py-2.5 mb-8 ring-2 ring-brand-orange">
            <Sparkles size={16} className="text-brand-orange" fill="currentColor" />
            AI Teacher's Toolkit
          </button>
        )}

        <nav className="flex flex-col gap-1">
          {NAV_ITEMS.map(({ icon: Icon, label, active }) => (
            <button
              key={label}
              title={collapsed ? label : undefined}
              className={classNames(
                "flex items-center gap-3 rounded-xl text-sm font-medium transition-colors",
                collapsed ? "justify-center w-11 h-11 mx-auto" : "px-3 py-2.5",
                active ? "bg-gray-100 text-ink shadow-sm" : "text-gray-400 hover:text-gray-600"
              )}
            >
              <Icon size={18} />
              {!collapsed && <span>{label}</span>}
            </button>
          ))}
        </nav>
      </div>

      <div className="flex flex-col gap-3">
        <button
          title={collapsed ? "Settings" : undefined}
          className={classNames(
            "flex items-center gap-3 text-sm font-medium text-gray-400 hover:text-gray-600",
            collapsed ? "justify-center w-11 h-11 mx-auto" : "px-3 py-2.5"
          )}
        >
          <Settings size={18} />
          {!collapsed && <span>Settings</span>}
        </button>

        {collapsed ? (
          <div className="w-11 h-11 mx-auto rounded-full bg-emerald-50 flex items-center justify-center">
            <School size={18} className="text-emerald-700" />
          </div>
        ) : (
          <div className="flex items-center gap-3 bg-gray-50 rounded-2xl p-3">
            <div className="w-9 h-9 rounded-full bg-emerald-50 flex items-center justify-center shrink-0">
              <School size={16} className="text-emerald-700" />
            </div>
            <div className="min-w-0">
              <p className="text-sm font-semibold truncate">Delhi Public School</p>
              <p className="text-xs text-gray-400 truncate">Bokaro Steel City</p>
            </div>
          </div>
        )}

        {collapsed && (
          <button className="w-11 h-11 mx-auto text-gray-300 hover:text-gray-500 flex items-center justify-center">
            <ChevronRight size={16} />
          </button>
        )}
      </div>
    </aside>
  );
}
