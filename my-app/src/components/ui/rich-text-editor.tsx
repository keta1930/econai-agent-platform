import { useEditor, EditorContent } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import { Table } from "@tiptap/extension-table";
import TableRow from "@tiptap/extension-table-row";
import TableCell from "@tiptap/extension-table-cell";
import TableHeader from "@tiptap/extension-table-header";
import { marked } from "marked";
import TurndownService from "turndown";
import { useEffect, useRef, useCallback } from "react";
import { cn } from "@/lib/utils";
import {
  Bold,
  Italic,
  List,
  ListOrdered,
  Heading2,
  Heading3,
  Undo,
  Redo,
  TableIcon,
} from "lucide-react";

const turndown = new TurndownService({
  headingStyle: "atx",
  codeBlockStyle: "fenced",
});

// Turndown table support
turndown.addRule("tableCell", {
  filter: ["th", "td"],
  replacement(content, _node) {
    return ` ${content.trim()} |`;
  },
});
turndown.addRule("tableRow", {
  filter: "tr",
  replacement(content) {
    return `|${content}\n`;
  },
});
turndown.addRule("table", {
  filter: "table",
  replacement(_content, node) {
    const el = node as HTMLTableElement;
    const rows = Array.from(el.rows);
    if (rows.length === 0) return "";

    const lines: string[] = [];
    rows.forEach((row, i) => {
      const cells = Array.from(row.cells).map((c) => ` ${c.textContent?.trim() || ""} `);
      lines.push(`|${cells.join("|")}|`);
      if (i === 0) {
        lines.push(`|${cells.map(() => "------").join("|")}|`);
      }
    });
    return lines.join("\n") + "\n";
  },
});

interface RichTextEditorProps {
  value: string;
  onChange: (markdown: string) => void;
  placeholder?: string;
  className?: string;
}

function ToolbarButton({
  onClick,
  active,
  children,
  title,
}: {
  onClick: () => void;
  active?: boolean;
  children: React.ReactNode;
  title: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      title={title}
      className={cn(
        "rounded p-1.5 hover:bg-muted transition-colors",
        active && "bg-muted text-foreground"
      )}
    >
      {children}
    </button>
  );
}

export function RichTextEditor({
  value,
  onChange,
  placeholder,
  className,
}: RichTextEditorProps) {
  const isExternalUpdate = useRef(false);

  const editor = useEditor({
    extensions: [
      StarterKit,
      Table.configure({ resizable: false }),
      TableRow,
      TableHeader,
      TableCell,
    ],
    content: "",
    editorProps: {
      attributes: {
        class:
          "prose prose-sm dark:prose-invert max-w-none min-h-[160px] px-3 py-2 focus:outline-none",
      },
    },
    onUpdate: ({ editor }) => {
      if (isExternalUpdate.current) return;
      const html = editor.getHTML();
      const md = turndown.turndown(html);
      onChange(md);
    },
  });

  // Sync external value changes (e.g. AI generation) into the editor
  useEffect(() => {
    if (!editor || !value) return;

    const currentMd = turndown.turndown(editor.getHTML());
    if (currentMd === value) return;

    isExternalUpdate.current = true;
    const html = marked.parse(value) as string;
    editor.commands.setContent(html);
    isExternalUpdate.current = false;
  }, [value, editor]);

  // Set placeholder
  useEffect(() => {
    if (!editor || !placeholder) return;
    if (!value) {
      // Only show placeholder when empty - handled via CSS below
    }
  }, [editor, placeholder, value]);

  const insertTable = useCallback(() => {
    editor
      ?.chain()
      .focus()
      .insertTable({ rows: 3, cols: 3, withHeaderRow: true })
      .run();
  }, [editor]);

  if (!editor) return null;

  return (
    <div
      className={cn(
        "rounded-lg border border-input overflow-hidden transition-colors focus-within:border-ring focus-within:ring-3 focus-within:ring-ring/50",
        className
      )}
    >
      {/* Toolbar */}
      <div className="flex items-center gap-0.5 border-b border-input bg-muted/30 px-2 py-1">
        <ToolbarButton
          onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
          active={editor.isActive("heading", { level: 2 })}
          title="标题 2"
        >
          <Heading2 className="h-4 w-4" />
        </ToolbarButton>
        <ToolbarButton
          onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()}
          active={editor.isActive("heading", { level: 3 })}
          title="标题 3"
        >
          <Heading3 className="h-4 w-4" />
        </ToolbarButton>
        <div className="mx-1 h-4 w-px bg-border" />
        <ToolbarButton
          onClick={() => editor.chain().focus().toggleBold().run()}
          active={editor.isActive("bold")}
          title="加粗"
        >
          <Bold className="h-4 w-4" />
        </ToolbarButton>
        <ToolbarButton
          onClick={() => editor.chain().focus().toggleItalic().run()}
          active={editor.isActive("italic")}
          title="斜体"
        >
          <Italic className="h-4 w-4" />
        </ToolbarButton>
        <div className="mx-1 h-4 w-px bg-border" />
        <ToolbarButton
          onClick={() => editor.chain().focus().toggleBulletList().run()}
          active={editor.isActive("bulletList")}
          title="无序列表"
        >
          <List className="h-4 w-4" />
        </ToolbarButton>
        <ToolbarButton
          onClick={() => editor.chain().focus().toggleOrderedList().run()}
          active={editor.isActive("orderedList")}
          title="有序列表"
        >
          <ListOrdered className="h-4 w-4" />
        </ToolbarButton>
        <div className="mx-1 h-4 w-px bg-border" />
        <ToolbarButton onClick={insertTable} title="插入表格">
          <TableIcon className="h-4 w-4" />
        </ToolbarButton>
        <div className="flex-1" />
        <ToolbarButton
          onClick={() => editor.chain().focus().undo().run()}
          title="撤销"
        >
          <Undo className="h-4 w-4" />
        </ToolbarButton>
        <ToolbarButton
          onClick={() => editor.chain().focus().redo().run()}
          title="重做"
        >
          <Redo className="h-4 w-4" />
        </ToolbarButton>
      </div>

      {/* Editor area */}
      <EditorContent editor={editor} />
    </div>
  );
}
