import { useState } from "react";
import QuestionItem from "./QuestionItem.jsx";
import UnmatchedAnswers from "../answer/UnmatchedAnswers.jsx";
import { classNames } from "../../utils/formatters.js";

const FILTERS = ["All", "Answered", "Unanswered", "Needs Review", "Unmatched", "Teacher Verified"];

function matchesFilter(filter, mapping) {
  if (filter === "All") return true;
  if (!mapping) return filter === "Unanswered";
  if (filter === "Teacher Verified") return mapping.source === "teacher";
  if (filter === "Needs Review") return mapping.match_level === "low-confidence";
  if (filter === "Unanswered") return mapping.match_level === "unanswered";
  if (filter === "Answered") return !["unanswered", "low-confidence"].includes(mapping.match_level);
  return true;
}

export default function QuestionList({
  questions,
  mappingForQuestion,
  gradeForQuestion,
  selectedKey,
  onSelectQuestion,
  unmatchedMappings,
  onSelectUnmatched,
}) {
  const [expandAll, setExpandAll] = useState(false);
  const [expandedOne, setExpandedOne] = useState(null);
  const [filter, setFilter] = useState("All");

  const isExpanded = (number) => expandAll || expandedOne === number;

  const handleSelect = (question) => {
    onSelectQuestion(question);
    setExpandedOne((prev) => (prev === question.number ? null : question.number));
  };

  const showUnmatched = filter === "All" || filter === "Unmatched";
  const visibleQuestions =
    filter === "Unmatched" ? [] : questions.filter((q) => matchesFilter(filter, mappingForQuestion(q.number)));

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between mb-3 px-1">
        <h2 className="text-sm font-semibold text-ink">Extracted Questions (from question paper)</h2>
        <button
          onClick={() => setExpandAll((v) => !v)}
          className="text-xs font-semibold text-brand-orange"
        >
          {expandAll ? "Collapse All" : "Expand All"}
        </button>
      </div>

      <div className="flex items-center gap-1.5 mb-3 px-1 overflow-x-auto pb-1">
        {FILTERS.map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={classNames(
              "shrink-0 text-xs font-semibold px-2.5 py-1.5 rounded-full transition-colors",
              filter === f ? "bg-ink text-white" : "bg-gray-100 text-gray-500 hover:bg-gray-200"
            )}
          >
            {f}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto space-y-2 pr-1">
        {visibleQuestions.length === 0 && filter !== "Unmatched" && filter !== "All" && (
          <p className="text-sm text-gray-400 text-center py-6">No questions match this filter.</p>
        )}

        {visibleQuestions.map((question) => (
          <QuestionItem
            key={question.number}
            question={question}
            mapping={mappingForQuestion(question.number)}
            grade={gradeForQuestion(question.number)}
            isSelected={selectedKey === question.number}
            isExpanded={isExpanded(question.number)}
            onSelect={() => handleSelect(question)}
          />
        ))}

        {showUnmatched && (
          <UnmatchedAnswers
            mappings={unmatchedMappings}
            activeKey={selectedKey}
            onSelect={onSelectUnmatched}
          />
        )}
      </div>
    </div>
  );
}
