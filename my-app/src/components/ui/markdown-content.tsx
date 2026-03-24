import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkBreaks from "remark-breaks";
import { cn } from "@/lib/utils";

interface MarkdownContentProps {
  content: string;
  className?: string;
}

/**
 * Preserve blank lines so that edit and preview look consistent.
 * Each blank line (\n\n) is converted to include a &nbsp; spacer,
 * making 2 newlines visually distinct from 1 newline (<br>).
 */
function preserveBlankLines(text: string): string {
  // Replace every occurrence of \n\n (blank line) with \n\n&nbsp;\n\n
  // so the empty line is visible in the rendered output.
  return text.replace(/\n\n/g, "\n\n&nbsp;\n\n");
}

export function MarkdownContent({ content, className }: MarkdownContentProps) {
  if (!content) return null;

  return (
    <div className={cn("prose prose-sm dark:prose-invert max-w-none", className)}>
      <ReactMarkdown remarkPlugins={[remarkGfm, remarkBreaks]}>
        {preserveBlankLines(content)}
      </ReactMarkdown>
    </div>
  );
}
