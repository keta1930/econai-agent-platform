import { useEffect, useRef } from "react";
import hljs from "highlight.js/lib/core";
import python from "highlight.js/lib/languages/python";
import json from "highlight.js/lib/languages/json";
import yaml from "highlight.js/lib/languages/yaml";
import "highlight.js/styles/github.css";
import { cn } from "@/lib/utils";

hljs.registerLanguage("python", python);
hljs.registerLanguage("json", json);
hljs.registerLanguage("yaml", yaml);

const EXTENSION_TO_LANGUAGE: Record<string, string> = {
  ".py": "python",
  ".json": "json",
  ".jsonl": "json",
  ".yaml": "yaml",
};

interface CodeBlockProps {
  code: string;
  language: string;
  className?: string;
}

export function CodeBlock({ code, language, className }: CodeBlockProps) {
  const codeRef = useRef<HTMLElement>(null);

  useEffect(() => {
    if (codeRef.current) {
      codeRef.current.removeAttribute("data-highlighted");
      hljs.highlightElement(codeRef.current);
    }
  }, [code, language]);

  const lines = code.split("\n");

  return (
    <div className={cn("relative rounded-md border bg-muted/30 overflow-auto", className)}>
      <div className="absolute top-2 right-3 text-xs text-muted-foreground select-none">
        {language}
      </div>
      <div className="flex text-sm">
        <div className="select-none py-4 pl-4 pr-3 text-right text-muted-foreground/50 leading-relaxed">
          {lines.map((_, i) => (
            <div key={i}>{i + 1}</div>
          ))}
        </div>
        <pre className="flex-1 overflow-x-auto py-4 pr-4">
          <code ref={codeRef} className={`language-${language} !bg-transparent !p-0 leading-relaxed`}>
            {code}
          </code>
        </pre>
      </div>
    </div>
  );
}

/** Resolve file extension to highlight.js language name. */
export function extensionToLanguage(ext: string): string {
  return EXTENSION_TO_LANGUAGE[ext] ?? "plaintext";
}
