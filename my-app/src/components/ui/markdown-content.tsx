import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkBreaks from "remark-breaks";
import rehypeHighlight from "rehype-highlight";
import { cn } from "@/lib/utils";
import { ChatCodeBlock } from "@/components/chat/ChatCodeBlock";
import "@/styles/chat-code-theme.css";
import type { Components } from "react-markdown";

interface MarkdownContentProps {
  content: string;
  className?: string;
}

/**
 * Preserve blank lines so that edit and preview look consistent.
 * Each blank line (\n\n) is converted to include a &nbsp; spacer,
 * making 2 newlines visually distinct from 1 newline (<br>).
 *
 * Code blocks (fenced with ```) are protected via placeholder substitution
 * to avoid mangling blank lines inside code.
 */
function preserveBlankLines(text: string): string {
  // Extract fenced code blocks and replace with placeholders
  const codeBlocks: string[] = [];
  const placeholder = (i: number) => `\x00CODEBLOCK_${i}\x00`;

  const withPlaceholders = text.replace(/(`{3,})[^\n]*\n[\s\S]*?\1/g, (match) => {
    const idx = codeBlocks.length;
    codeBlocks.push(match);
    return placeholder(idx);
  });

  // Apply blank-line spacing only in non-code regions
  const processed = withPlaceholders.replace(/\n\n/g, "\n\n&nbsp;\n\n");

  // Restore code blocks
  let result = processed;
  for (let i = 0; i < codeBlocks.length; i++) {
    result = result.replace(placeholder(i), codeBlocks[i]);
  }
  return result;
}

const markdownComponents: Components = {
  code({ className, children, ...props }) {
    // rehype-highlight injects className like "language-python hljs ..."
    const match = className?.match(/language-(\w+)/);
    if (match) {
      return (
        <ChatCodeBlock language={match[1]}>
          {children}
        </ChatCodeBlock>
      );
    }
    // Inline code — styling handled by chat-code-theme.css
    return (
      <code className={className} {...props}>
        {children}
      </code>
    );
  },
  // Links open in new tab
  a({ children, ...props }) {
    return (
      <a target="_blank" rel="noopener noreferrer" {...props}>
        {children}
      </a>
    );
  },
  // 表格包裹滚动容器，防止长内容撑破消息气泡
  table({ children, ...props }) {
    return (
      <div className="table-wrapper">
        <table {...props}>{children}</table>
      </div>
    );
  },
};

export function MarkdownContent({ content, className }: MarkdownContentProps) {
  if (!content) return null;

  return (
    <div className={cn("chat-markdown prose prose-sm dark:prose-invert max-w-none", className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkBreaks]}
        rehypePlugins={[rehypeHighlight]}
        components={markdownComponents}
      >
        {preserveBlankLines(content)}
      </ReactMarkdown>
    </div>
  );
}
