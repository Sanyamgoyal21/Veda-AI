import { useState } from "react";
import QuestionItem from "./QuestionItem.jsx";
import UnmatchedAnswers from "../answer/UnmatchedAnswers.jsx";

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

  const isExpanded = (number) => expandAll || expandedOne === number;

  const handleSelect = (question) => {
    onSelectQuestion(question);
    setExpandedOne((prev) => (prev === question.number ? null : question.number));
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between mb-4 px-1">
        <h2 className="text-sm font-semibold text-ink">Extracted Questions (from question paper)</h2>
        <button
          onClick={() => setExpandAll((v) => !v)}
          className="text-xs font-semibold text-brand-orange"
        >
          {expandAll ? "Collapse All" : "Expand All"}
        </button>
      </div>

      <div className="flex-1 overflow-y-auto space-y-2 pr-1">
        {questions.map((question) => (
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

        <UnmatchedAnswers
          mappings={unmatchedMappings}
          activeKey={selectedKey}
          onSelect={onSelectUnmatched}
        />
      </div>
    </div>
  );
}
