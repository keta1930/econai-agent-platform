import { useState } from "react";
import { cn } from "@/lib/utils";
import { HelpCircle, Check } from "lucide-react";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface AskUserOption {
  label: string;
  description?: string;
}

interface AskUserCardProps {
  question: string;
  options?: (string | AskUserOption)[];
  selectMode?: "single" | "multiple";
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
// AskUserCard
// ---------------------------------------------------------------------------

export function AskUserCard({
  question,
  options,
  selectMode = "single",
  onAnswer,
  disabled,
  selectedAnswer,
}: AskUserCardProps) {
  const [multiSelected, setMultiSelected] = useState<Set<string>>(new Set());

  const normalized = options?.length ? normalizeOptions(options) : [];

  // Determine which labels are "answered" for disabled state rendering
  const answeredLabels = disabled && selectedAnswer != null
    ? parseSelectedLabels(selectedAnswer, normalized)
    : new Set<string>();

  // If disabled, selectedAnswer exists, and it doesn't match any option
  const isFreetextAnswer = disabled
    && selectedAnswer != null
    && answeredLabels.size === 0
    && normalized.length > 0;

  // --- Single mode handler ---
  function handleSingleSelect(label: string) {
    if (disabled) return;
    onAnswer(label);
  }

  // --- Multiple mode handlers ---
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
    if (disabled || multiSelected.size === 0) return;
    const answer = normalized
      .filter(o => multiSelected.has(o.label))
      .map(o => o.label)
      .join(", ");
    onAnswer(answer);
  }

  // --- Determine if an option is "selected" (for visual state) ---
  function isOptionSelected(label: string): boolean {
    if (disabled && selectedAnswer != null) return answeredLabels.has(label);
    if (selectMode === "multiple") return multiSelected.has(label);
    return false;
  }

  return (
    <div
      className={cn(
        "rounded-lg bg-white border border-[var(--paper-border)] p-4 my-1",
        "shadow-[var(--shadow-sm)]",
        "border-l-[3px] border-l-transparent",
        // Left accent: cyan gradient via border-image
      )}
      style={{
        borderLeftWidth: "3px",
        borderLeftStyle: "solid",
        borderImage: "linear-gradient(to bottom, var(--cyan-mid), var(--cyan-light)) 1",
      }}
    >
      {/* Question */}
      <div className="flex items-start gap-2 mb-3">
        <HelpCircle className="h-4 w-4 text-[var(--cyan-mid)] mt-0.5 shrink-0" />
        <p className="text-sm font-heading text-foreground">{question}</p>
      </div>

      {/* Options */}
      {normalized.length > 0 && (
        <div className="flex flex-col gap-1.5 mb-2">
          {normalized.map((option) => {
            const selected = isOptionSelected(option.label);
            const isDisabledUnselected = disabled && selectedAnswer != null && !selected;

            return (
              <button
                key={option.label}
                type="button"
                disabled={disabled}
                onClick={() =>
                  selectMode === "single"
                    ? handleSingleSelect(option.label)
                    : handleToggle(option.label)
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
        </div>
      )}

      {/* Submit button for multiple mode */}
      {selectMode === "multiple" && !disabled && (
        <button
          type="button"
          onClick={handleMultiSubmit}
          disabled={multiSelected.size === 0}
          className={cn(
            "w-full py-1.5 rounded-md text-sm font-medium transition-colors mb-2",
            "bg-[var(--cyan-mid)] text-white",
            "hover:bg-[var(--cyan-deep)]",
            "focus-visible:ring-2 focus-visible:ring-[var(--cyan-mid)]/10",
            multiSelected.size === 0 && "opacity-50 cursor-not-allowed",
          )}
        >
          提交选择
        </button>
      )}

      {/* Freetext answer fallback (answered with input box, not matching any option) */}
      {isFreetextAnswer && (
        <div className="mt-2 px-3 py-2 rounded-md bg-[var(--paper)] border border-[var(--paper-border)]">
          <span className="text-xs text-[var(--muted-foreground)]">回答：</span>
          <span className="text-sm text-foreground ml-1">{selectedAnswer}</span>
        </div>
      )}

      {/* Hint */}
      {!disabled && normalized.length > 0 && (
        <p className="text-[11px] text-[var(--muted-foreground)]">
          或在输入框中输入其他内容
        </p>
      )}
    </div>
  );
}
