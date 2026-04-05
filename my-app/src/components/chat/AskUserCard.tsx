import { useState, useRef, useEffect, useCallback } from "react";
import { cn } from "@/lib/utils";
import { HelpCircle, Check, ArrowRight, ChevronLeft, ChevronRight } from "lucide-react";
import type { AskUserQuestion } from "@/types/assistant";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface AskUserOption {
  label: string;
  description?: string;
}

interface AskUserCardProps {
  questions: AskUserQuestion[];
  onAnswer: (answer: string) => void;
  disabled: boolean;
  /** Already-answered content (from tool_result) — renders selected state when disabled */
  selectedAnswer?: string;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function normalizeOptions(options: (string | AskUserOption)[]): AskUserOption[] {
  return options.map(opt => typeof opt === "string" ? { label: opt } : opt);
}

/** Parse a comma-separated answer string into a set of selected labels */
function parseSelectedLabels(answer: string, options: AskUserOption[]): Set<string> {
  const labels = new Set<string>();
  const parts = answer.split(",").map(s => s.trim());
  for (const part of parts) {
    const match = options.find(o => o.label === part);
    if (match) labels.add(match.label);
  }
  return labels;
}

/** Try to parse a multi-question JSON answer */
function parseMultiAnswer(answer: string): string[] | null {
  try {
    const parsed = JSON.parse(answer);
    if (parsed && Array.isArray(parsed.answers)) return parsed.answers as string[];
  } catch { /* not JSON, fall back */ }
  return null;
}

// ---------------------------------------------------------------------------
// Checkbox icon for multiple mode
// ---------------------------------------------------------------------------

function CheckboxIcon({ checked }: { checked: boolean }) {
  return (
    <span
      className={cn(
        "inline-flex items-center justify-center h-4 w-4 rounded border shrink-0 transition-colors",
        checked
          ? "bg-[var(--cyan-mid)] border-[var(--cyan-mid)]"
          : "border-[var(--paper-border)] bg-white",
      )}
    >
      {checked && <Check className="h-2.5 w-2.5 text-white" strokeWidth={3} />}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Step indicator for multi-question mode
// ---------------------------------------------------------------------------

function StepIndicator({
  current,
  total,
  answers,
}: {
  current: number;
  total: number;
  answers: string[];
}) {
  return (
    <div className="flex items-center justify-between mb-2">
      <span className="text-xs text-[var(--muted-foreground)]">
        第 {current + 1} / {total} 题
      </span>
      <div className="flex items-center gap-1">
        {Array.from({ length: total }, (_, i) => {
          const isActive = i === current;
          const isComplete = answers[i] !== "";
          return (
            <span
              key={i}
              className={cn(
                "h-1.5 w-1.5 rounded-full transition-colors",
                isActive
                  ? "bg-[var(--cyan-mid)]"
                  : isComplete
                    ? "border border-[var(--cyan-mid)] bg-transparent"
                    : "bg-[var(--paper-border)]",
              )}
            />
          );
        })}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Freetext input — for questions without predefined options
// ---------------------------------------------------------------------------

function FreetextInput({
  value,
  onChange,
  onSubmit,
  placeholder = "请输入回答...",
}: {
  value: string;
  onChange: (v: string) => void;
  onSubmit: () => void;
  placeholder?: string;
}) {
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  return (
    <div className="flex items-center gap-1.5">
      <input
        ref={inputRef}
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && value.trim()) {
            e.preventDefault();
            onSubmit();
          }
        }}
        placeholder={placeholder}
        className={cn(
          "flex-1 min-w-0 px-2.5 py-1.5 rounded-md border text-sm bg-white",
          "border-[var(--paper-border)]",
          "focus:outline-none focus:border-[var(--cyan-mid)] focus:ring-2 focus:ring-[var(--cyan-mid)]/10",
          "placeholder:text-[var(--muted-foreground)]/50",
        )}
      />
      <button
        type="button"
        onClick={onSubmit}
        disabled={!value.trim()}
        className={cn(
          "shrink-0 p-1.5 rounded-md transition-colors",
          value.trim()
            ? "text-[var(--cyan-mid)] hover:bg-[var(--cyan-mid)]/10"
            : "text-[var(--paper-border)] cursor-not-allowed",
        )}
      >
        <ArrowRight className="h-4 w-4" />
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// "Other" inline text input row
// ---------------------------------------------------------------------------

function OtherInput({
  isSelected,
  onToggle,
  onSubmit,
  value,
  onChange,
  mode,
  disabled,
}: {
  isSelected: boolean;
  onToggle: () => void;
  onSubmit: () => void;
  value: string;
  onChange: (v: string) => void;
  mode: "single" | "multiple";
  disabled: boolean;
}) {
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isSelected && inputRef.current) {
      inputRef.current.focus();
    }
  }, [isSelected]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && value.trim()) {
      e.preventDefault();
      onSubmit();
    }
  };

  return (
    <div>
      <button
        type="button"
        disabled={disabled}
        onClick={onToggle}
        className={cn(
          "flex items-center gap-2.5 w-full text-left px-3 py-2 rounded-md border transition-colors",
          "focus-visible:border-[var(--cyan-mid)] focus-visible:ring-2 focus-visible:ring-[var(--cyan-mid)]/10",
          isSelected
            ? "border-l-[3px] border-l-[var(--cyan-mid)] border-[var(--cyan-mid)]/20 bg-[var(--cyan-mid)]/5"
            : "border-[var(--paper-border)] bg-[var(--paper)]",
          !disabled && !isSelected && "hover:border-[var(--cyan-light)] hover:bg-[var(--paper-warm)]",
          disabled && "cursor-default",
        )}
      >
        {mode === "multiple" && <CheckboxIcon checked={isSelected} />}
        <span
          className={cn(
            "text-sm font-medium",
            isSelected ? "text-[var(--cyan-deep)]" : "text-foreground",
          )}
        >
          其他
        </span>
      </button>

      {/* Inline text input — shown when "Other" is selected */}
      {isSelected && !disabled && (
        <div className="flex items-center gap-1.5 mt-1.5 ml-0.5">
          <input
            ref={inputRef}
            type="text"
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="请输入..."
            className={cn(
              "flex-1 min-w-0 px-2.5 py-1.5 rounded-md border text-sm bg-white",
              "border-[var(--paper-border)]",
              "focus:outline-none focus:border-[var(--cyan-mid)] focus:ring-2 focus:ring-[var(--cyan-mid)]/10",
              "placeholder:text-[var(--muted-foreground)]/50",
            )}
          />
          {mode === "single" && (
            <button
              type="button"
              onClick={onSubmit}
              disabled={!value.trim()}
              className={cn(
                "shrink-0 p-1.5 rounded-md transition-colors",
                value.trim()
                  ? "text-[var(--cyan-mid)] hover:bg-[var(--cyan-mid)]/10"
                  : "text-[var(--paper-border)] cursor-not-allowed",
              )}
            >
              <ArrowRight className="h-4 w-4" />
            </button>
          )}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// OptionList — renders options + "Other" row for a single question
// ---------------------------------------------------------------------------

function OptionList({
  normalized,
  selectMode,
  disabled,
  answeredLabels,
  isFreetextAnswer,
  selectedAnswer,
  multiSelected,
  onSingleSelect,
  onToggle,
  otherSelected,
  onOtherToggle,
  otherValue,
  onOtherChange,
  onOtherSubmit,
}: {
  normalized: AskUserOption[];
  selectMode: "single" | "multiple";
  disabled: boolean;
  answeredLabels: Set<string>;
  isFreetextAnswer: boolean;
  selectedAnswer?: string;
  multiSelected: Set<string>;
  onSingleSelect: (label: string) => void;
  onToggle: (label: string) => void;
  otherSelected: boolean;
  onOtherToggle: () => void;
  otherValue: string;
  onOtherChange: (v: string) => void;
  onOtherSubmit: () => void;
}) {
  function isOptionSelected(label: string): boolean {
    if (disabled && selectedAnswer != null) return answeredLabels.has(label);
    if (selectMode === "multiple") return multiSelected.has(label);
    return false;
  }

  return (
    <div className="flex flex-col gap-1.5 mb-2">
      {normalized.map((option) => {
        const selected = isOptionSelected(option.label);
        const isDisabledUnselected = disabled && selectedAnswer != null && !selected && !isFreetextAnswer;

        return (
          <button
            key={option.label}
            type="button"
            disabled={disabled}
            onClick={() =>
              selectMode === "single"
                ? onSingleSelect(option.label)
                : onToggle(option.label)
            }
            className={cn(
              "flex items-center gap-2.5 w-full text-left px-3 py-2 rounded-md border transition-colors",
              "focus-visible:border-[var(--cyan-mid)] focus-visible:ring-2 focus-visible:ring-[var(--cyan-mid)]/10",
              selected
                ? "border-l-[3px] border-l-[var(--cyan-mid)] border-[var(--cyan-mid)]/20 bg-[var(--cyan-mid)]/5"
                : "border-[var(--paper-border)] bg-[var(--paper)]",
              !disabled && !selected && "hover:border-[var(--cyan-light)] hover:bg-[var(--paper-warm)]",
              isDisabledUnselected && "opacity-40",
              disabled && "cursor-default",
            )}
          >
            {selectMode === "multiple" && (
              <CheckboxIcon checked={selected} />
            )}
            <div className="flex flex-col min-w-0">
              <span
                className={cn(
                  "text-sm font-medium",
                  selected ? "text-[var(--cyan-deep)]" : "text-foreground",
                )}
              >
                {option.label}
              </span>
              {option.description && (
                <span className="text-xs text-[var(--muted-foreground)] mt-0.5">
                  {option.description}
                </span>
              )}
            </div>
          </button>
        );
      })}

      {/* "Other" option — only when options exist and not disabled */}
      {!disabled && (
        <OtherInput
          isSelected={otherSelected}
          onToggle={onOtherToggle}
          onSubmit={onOtherSubmit}
          value={otherValue}
          onChange={onOtherChange}
          mode={selectMode}
          disabled={disabled}
        />
      )}

      {/* Disabled state: show "Other" as selected if freetext answer */}
      {isFreetextAnswer && (
        <div
          className={cn(
            "flex items-center gap-2.5 w-full text-left px-3 py-2 rounded-md border",
            "border-l-[3px] border-l-[var(--cyan-mid)] border-[var(--cyan-mid)]/20 bg-[var(--cyan-mid)]/5",
            "cursor-default",
          )}
        >
          {selectMode === "multiple" && <CheckboxIcon checked />}
          <div className="flex flex-col min-w-0">
            <span className="text-sm font-medium text-[var(--cyan-deep)]">
              其他
            </span>
            <span className="text-xs text-[var(--muted-foreground)] mt-0.5">
              {selectedAnswer}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// SingleQuestionView — one question with options + "Other"
// ---------------------------------------------------------------------------

function SingleQuestionView({
  question,
  options,
  selectMode = "single",
  onAnswer,
  disabled,
  selectedAnswer,
}: {
  question: string;
  options?: (string | AskUserOption)[];
  selectMode?: "single" | "multiple";
  onAnswer: (answer: string) => void;
  disabled: boolean;
  selectedAnswer?: string;
}) {
  const [multiSelected, setMultiSelected] = useState<Set<string>>(new Set());
  const [otherSelected, setOtherSelected] = useState(false);
  const [otherValue, setOtherValue] = useState("");
  // Preserve the submitted answer locally so it shows between submission and refetch
  const [submittedAnswer, setSubmittedAnswer] = useState<string | null>(null);

  const normalized = options?.length ? normalizeOptions(options) : [];

  // Use selectedAnswer from tool_result if available, otherwise fall back to local submission
  const effectiveAnswer = selectedAnswer ?? submittedAnswer;

  const answeredLabels = disabled && effectiveAnswer != null
    ? parseSelectedLabels(effectiveAnswer, normalized)
    : new Set<string>();

  const isFreetextAnswer = disabled
    && effectiveAnswer != null
    && answeredLabels.size === 0
    && normalized.length > 0;

  function handleSingleSelect(label: string) {
    if (disabled) return;
    setOtherSelected(false);
    setSubmittedAnswer(label);
    onAnswer(label);
  }

  function handleToggle(label: string) {
    if (disabled) return;
    setMultiSelected(prev => {
      const next = new Set(prev);
      if (next.has(label)) next.delete(label);
      else next.add(label);
      return next;
    });
  }

  function handleMultiSubmit() {
    if (disabled) return;
    const parts = normalized
      .filter(o => multiSelected.has(o.label))
      .map(o => o.label);
    if (otherSelected && otherValue.trim()) {
      parts.push(otherValue.trim());
    }
    if (parts.length === 0) return;
    const answer = parts.join(", ");
    setSubmittedAnswer(answer);
    onAnswer(answer);
  }

  function handleOtherToggle() {
    if (selectMode === "single") {
      setOtherSelected(!otherSelected);
    } else {
      setOtherSelected(prev => !prev);
    }
  }

  function handleOtherSubmit() {
    if (!otherValue.trim()) return;
    if (selectMode === "single") {
      const answer = otherValue.trim();
      setSubmittedAnswer(answer);
      onAnswer(answer);
    }
    // In multiple mode, submit is handled by handleMultiSubmit
  }

  const canSubmitMulti = selectMode === "multiple"
    && (multiSelected.size > 0 || (otherSelected && otherValue.trim()));

  return (
    <>
      {/* Question */}
      <div className="flex items-start gap-2 mb-3">
        <HelpCircle className="h-4 w-4 text-[var(--cyan-mid)] mt-0.5 shrink-0" />
        <p className="text-sm font-heading text-foreground">{question}</p>
      </div>

      {/* Options */}
      {normalized.length > 0 && (
        <OptionList
          normalized={normalized}
          selectMode={selectMode}
          disabled={disabled}
          answeredLabels={answeredLabels}
          isFreetextAnswer={isFreetextAnswer}
          selectedAnswer={effectiveAnswer}
          multiSelected={multiSelected}
          onSingleSelect={handleSingleSelect}
          onToggle={handleToggle}
          otherSelected={otherSelected}
          onOtherToggle={handleOtherToggle}
          otherValue={otherValue}
          onOtherChange={setOtherValue}
          onOtherSubmit={handleOtherSubmit}
        />
      )}

      {/* Submit button for multiple mode */}
      {selectMode === "multiple" && !disabled && (
        <button
          type="button"
          onClick={handleMultiSubmit}
          disabled={!canSubmitMulti}
          className={cn(
            "w-full py-1.5 rounded-md text-sm font-medium transition-colors mb-2",
            "bg-[var(--cyan-mid)] text-white",
            "hover:bg-[var(--cyan-deep)]",
            "focus-visible:ring-2 focus-visible:ring-[var(--cyan-mid)]/10",
            !canSubmitMulti && "opacity-50 cursor-not-allowed",
          )}
        >
          提交选择
        </button>
      )}

      {/* Inline text input for questions without options */}
      {!disabled && normalized.length === 0 && (
        <FreetextInput
          value={otherValue}
          onChange={setOtherValue}
          onSubmit={() => {
            if (otherValue.trim()) {
              const answer = otherValue.trim();
              setSubmittedAnswer(answer);
              onAnswer(answer);
            }
          }}
        />
      )}

      {/* Show freetext answer when disabled and no options */}
      {disabled && normalized.length === 0 && effectiveAnswer && (
        <div className="px-3 py-2 rounded-md bg-[var(--paper)] border border-[var(--paper-border)]">
          <span className="text-sm text-foreground">{effectiveAnswer}</span>
        </div>
      )}
    </>
  );
}

// ---------------------------------------------------------------------------
// MultiQuestionView — step-by-step navigation through multiple questions
// ---------------------------------------------------------------------------

function MultiQuestionView({
  questions,
  onAnswer,
  disabled,
  selectedAnswer,
}: {
  questions: AskUserQuestion[];
  onAnswer: (answer: string) => void;
  disabled: boolean;
  selectedAnswer?: string;
}) {
  const [currentStep, setCurrentStep] = useState(0);
  const [answers, setAnswers] = useState<string[]>(() => new Array(questions.length).fill(""));
  const [stepMultiSelected, setStepMultiSelected] = useState<Set<string>>(new Set());
  const [otherSelected, setOtherSelected] = useState(false);
  const [otherValue, setOtherValue] = useState("");

  const isLastStep = currentStep === questions.length - 1;
  const currentQ = questions[currentStep];
  const currentNormalized = currentQ.options?.length ? normalizeOptions(currentQ.options) : [];
  const currentMode = currentQ.select_mode ?? "single";

  // Reset step-level state when navigating
  const resetStepState = useCallback((step: number) => {
    const q = questions[step];
    const mode = q.select_mode ?? "single";
    const existingAnswer = answers[step];

    if (mode === "multiple" && existingAnswer) {
      const opts = q.options?.length ? normalizeOptions(q.options) : [];
      const labels = parseSelectedLabels(existingAnswer, opts);
      setStepMultiSelected(labels);
      // Check if there's a freetext part
      const parts = existingAnswer.split(",").map(s => s.trim());
      const freetextPart = parts.find(p => !opts.some(o => o.label === p));
      setOtherSelected(!!freetextPart);
      setOtherValue(freetextPart ?? "");
    } else {
      setStepMultiSelected(new Set());
      setOtherSelected(false);
      setOtherValue("");
    }
  }, [questions, answers]);

  // --- Disabled state: show all answers ---
  if (disabled) {
    const parsedAnswers = selectedAnswer ? parseMultiAnswer(selectedAnswer) : null;

    return (
      <div className="space-y-3">
        {questions.map((q, i) => {
          const opts = q.options?.length ? normalizeOptions(q.options) : [];
          const answer = parsedAnswers?.[i] ?? "";
          const answeredLabels = parseSelectedLabels(answer, opts);
          const isFreetextAnswer = answeredLabels.size === 0 && opts.length > 0 && answer !== "";

          return (
            <div key={i}>
              <div className="flex items-start gap-2 mb-2">
                <span className="text-xs text-[var(--muted-foreground)] shrink-0 mt-0.5">
                  {i + 1}.
                </span>
                <p className="text-sm font-heading text-foreground">{q.question}</p>
              </div>
              {opts.length > 0 ? (
                <div className="flex flex-col gap-1 ml-4">
                  {opts.map((option) => {
                    const selected = answeredLabels.has(option.label);
                    return (
                      <div
                        key={option.label}
                        className={cn(
                          "flex items-center gap-2.5 px-3 py-1.5 rounded-md border",
                          selected
                            ? "border-l-[3px] border-l-[var(--cyan-mid)] border-[var(--cyan-mid)]/20 bg-[var(--cyan-mid)]/5"
                            : "border-[var(--paper-border)] bg-[var(--paper)] opacity-40",
                        )}
                      >
                        {(q.select_mode ?? "single") === "multiple" && (
                          <CheckboxIcon checked={selected} />
                        )}
                        <span
                          className={cn(
                            "text-sm",
                            selected ? "text-[var(--cyan-deep)] font-medium" : "text-foreground",
                          )}
                        >
                          {option.label}
                        </span>
                      </div>
                    );
                  })}
                  {isFreetextAnswer && (
                    <div className="flex items-center gap-2.5 px-3 py-1.5 rounded-md border border-l-[3px] border-l-[var(--cyan-mid)] border-[var(--cyan-mid)]/20 bg-[var(--cyan-mid)]/5">
                      <span className="text-sm font-medium text-[var(--cyan-deep)]">其他：</span>
                      <span className="text-sm text-foreground">{answer}</span>
                    </div>
                  )}
                </div>
              ) : (
                answer && (
                  <div className="ml-4 px-3 py-1.5 rounded-md bg-[var(--paper)] border border-[var(--paper-border)]">
                    <span className="text-sm text-foreground">{answer}</span>
                  </div>
                )
              )}
            </div>
          );
        })}
      </div>
    );
  }

  // --- Active state: step-by-step ---

  function recordAnswer(answer: string) {
    setAnswers(prev => {
      const next = [...prev];
      next[currentStep] = answer;
      return next;
    });
  }

  function handleSingleSelect(label: string) {
    recordAnswer(label);
    setOtherSelected(false);
    setOtherValue("");
    // Auto-advance for single mode
    if (!isLastStep) {
      const nextStep = currentStep + 1;
      setCurrentStep(nextStep);
      resetStepState(nextStep);
    }
  }

  function handleToggle(label: string) {
    setStepMultiSelected(prev => {
      const next = new Set(prev);
      if (next.has(label)) next.delete(label);
      else next.add(label);
      return next;
    });
  }

  function handleNext() {
    // For multiple mode, commit current selections as answer
    if (currentMode === "multiple") {
      const parts = currentNormalized
        .filter(o => stepMultiSelected.has(o.label))
        .map(o => o.label);
      if (otherSelected && otherValue.trim()) {
        parts.push(otherValue.trim());
      }
      recordAnswer(parts.join(", "));
    }
    const nextStep = currentStep + 1;
    setCurrentStep(nextStep);
    resetStepState(nextStep);
  }

  function handlePrev() {
    // Save current step state before going back
    if (currentMode === "multiple") {
      const parts = currentNormalized
        .filter(o => stepMultiSelected.has(o.label))
        .map(o => o.label);
      if (otherSelected && otherValue.trim()) {
        parts.push(otherValue.trim());
      }
      recordAnswer(parts.join(", "));
    }
    const prevStep = currentStep - 1;
    setCurrentStep(prevStep);
    resetStepState(prevStep);
  }

  function handleSubmitAll() {
    // Commit last step if multiple
    const finalAnswers = [...answers];
    if (currentMode === "multiple") {
      const parts = currentNormalized
        .filter(o => stepMultiSelected.has(o.label))
        .map(o => o.label);
      if (otherSelected && otherValue.trim()) {
        parts.push(otherValue.trim());
      }
      finalAnswers[currentStep] = parts.join(", ");
    }
    onAnswer(JSON.stringify({ answers: finalAnswers }));
  }

  function handleOtherToggle() {
    if (currentMode === "single") {
      setOtherSelected(!otherSelected);
    } else {
      setOtherSelected(prev => !prev);
    }
  }

  function handleOtherSubmitSingle() {
    if (!otherValue.trim()) return;
    recordAnswer(otherValue.trim());
    // Auto-advance
    if (!isLastStep) {
      const nextStep = currentStep + 1;
      setCurrentStep(nextStep);
      resetStepState(nextStep);
    }
  }

  const canAdvance = currentMode === "multiple"
    ? (stepMultiSelected.size > 0 || (otherSelected && otherValue.trim()))
    : answers[currentStep] !== "";

  const canSubmitAll = isLastStep && (
    currentMode === "multiple"
      ? (stepMultiSelected.size > 0 || (otherSelected && otherValue.trim()))
      : answers[currentStep] !== ""
  );

  return (
    <>
      {/* Step indicator */}
      <StepIndicator current={currentStep} total={questions.length} answers={answers} />

      {/* Question */}
      <div className="flex items-start gap-2 mb-3">
        <HelpCircle className="h-4 w-4 text-[var(--cyan-mid)] mt-0.5 shrink-0" />
        <p className="text-sm font-heading text-foreground">{currentQ.question}</p>
      </div>

      {/* Options */}
      {currentNormalized.length > 0 ? (
        <OptionList
          normalized={currentNormalized}
          selectMode={currentMode}
          disabled={false}
          answeredLabels={new Set<string>()}
          isFreetextAnswer={false}
          multiSelected={stepMultiSelected}
          onSingleSelect={handleSingleSelect}
          onToggle={handleToggle}
          otherSelected={otherSelected}
          onOtherToggle={handleOtherToggle}
          otherValue={otherValue}
          onOtherChange={setOtherValue}
          onOtherSubmit={handleOtherSubmitSingle}
        />
      ) : (
        /* Freetext input for questions without options */
        <div className="mb-2">
          <FreetextInput
            value={otherValue}
            onChange={setOtherValue}
            onSubmit={() => {
              if (!otherValue.trim()) return;
              if (isLastStep) {
                // Last step: record and submit all at once
                const finalAnswers = [...answers];
                finalAnswers[currentStep] = otherValue.trim();
                onAnswer(JSON.stringify({ answers: finalAnswers }));
              } else {
                recordAnswer(otherValue.trim());
                setOtherValue("");
                const nextStep = currentStep + 1;
                setCurrentStep(nextStep);
                resetStepState(nextStep);
              }
            }}
          />
        </div>
      )}

      {/* Navigation buttons */}
      <div className="flex items-center justify-between mt-2">
        {currentStep > 0 ? (
          <button
            type="button"
            onClick={handlePrev}
            className="flex items-center gap-1 text-sm text-[var(--muted-foreground)] hover:text-foreground transition-colors"
          >
            <ChevronLeft className="h-3.5 w-3.5" />
            上一步
          </button>
        ) : (
          <div />
        )}

        {isLastStep ? (
          <button
            type="button"
            onClick={handleSubmitAll}
            disabled={!canSubmitAll}
            className={cn(
              "px-4 py-1.5 rounded-md text-sm font-medium transition-colors",
              "bg-[var(--cyan-mid)] text-white",
              "hover:bg-[var(--cyan-deep)]",
              "focus-visible:ring-2 focus-visible:ring-[var(--cyan-mid)]/10",
              !canSubmitAll && "opacity-50 cursor-not-allowed",
            )}
          >
            提交全部
          </button>
        ) : (
          currentMode === "multiple" && (
            <button
              type="button"
              onClick={handleNext}
              disabled={!canAdvance}
              className={cn(
                "flex items-center gap-1 px-4 py-1.5 rounded-md text-sm font-medium transition-colors",
                "bg-[var(--cyan-mid)] text-white",
                "hover:bg-[var(--cyan-deep)]",
                "focus-visible:ring-2 focus-visible:ring-[var(--cyan-mid)]/10",
                !canAdvance && "opacity-50 cursor-not-allowed",
              )}
            >
              下一步
              <ChevronRight className="h-3.5 w-3.5" />
            </button>
          )
        )}
      </div>
    </>
  );
}

// ---------------------------------------------------------------------------
// AskUserCard — main wrapper
// ---------------------------------------------------------------------------

export function AskUserCard({
  questions,
  onAnswer,
  disabled,
  selectedAnswer,
}: AskUserCardProps) {
  const isMultiQuestion = questions.length > 1;

  return (
    <div
      className={cn(
        "rounded-lg bg-white border border-[var(--paper-border)] p-4 my-1",
        "shadow-[var(--shadow-sm)]",
        "border-l-[3px] border-l-transparent",
      )}
      style={{
        borderLeftWidth: "3px",
        borderLeftStyle: "solid",
        borderImage: "linear-gradient(to bottom, var(--cyan-mid), var(--cyan-light)) 1",
      }}
    >
      {isMultiQuestion ? (
        <MultiQuestionView
          questions={questions}
          onAnswer={onAnswer}
          disabled={disabled}
          selectedAnswer={selectedAnswer}
        />
      ) : (
        <SingleQuestionView
          question={questions[0].question}
          options={questions[0].options}
          selectMode={questions[0].select_mode}
          onAnswer={onAnswer}
          disabled={disabled}
          selectedAnswer={selectedAnswer}
        />
      )}
    </div>
  );
}
