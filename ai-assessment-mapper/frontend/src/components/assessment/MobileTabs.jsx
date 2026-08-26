import { classNames } from "../../utils/formatters.js";

export default function MobileTabs({ active, onChange }) {
  return (
    <div className="lg:hidden flex bg-gray-100 rounded-full p-1 mb-4">
      {["questions", "answer"].map((tab) => (
        <button
          key={tab}
          onClick={() => onChange(tab)}
          className={classNames(
            "flex-1 text-sm font-semibold py-2 rounded-full transition-colors",
            active === tab ? "bg-ink text-white" : "text-gray-500"
          )}
        >
          {tab === "questions" ? "Questions" : "Answer Sheet"}
        </button>
      ))}
    </div>
  );
}
