import React from "react";

interface MarkdownViewProps {
  content: string;
  isUser?: boolean;
  className?: string;
}

/**
 * Lightweight, zero-dependency, XSS-safe Markdown renderer for ALIGN chat messages.
 * Uses pure React element generation (zero dangerouslySetInnerHTML).
 */
export default function MarkdownView({ content, isUser = false, className = "" }: MarkdownViewProps) {
  if (!content) return null;

  // Split lines
  const lines = content.split("\n");
  const elements: React.ReactNode[] = [];
  let inCodeBlock = false;
  let codeBlockLang = "";
  let codeBlockBuffer: string[] = [];

  function parseInline(text: string): React.ReactNode[] {
    // Regex matches bold (**bold**), italic (*italic*), code (`code`), or link ([text](url))
    const tokenRegex = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`|\[[^\]]+\]\([^)]+\))/g;
    const parts = text.split(tokenRegex);

    return parts.map((part, idx) => {
      if (!part) return null;

      // Bold: **text**
      if (part.startsWith("**") && part.endsWith("**") && part.length >= 4) {
        return <strong key={idx} style={{ fontWeight: 700 }}>{part.slice(2, -2)}</strong>;
      }

      // Italic: *text*
      if (part.startsWith("*") && part.endsWith("*") && part.length >= 2) {
        return <em key={idx} style={{ fontStyle: "italic" }}>{part.slice(1, -1)}</em>;
      }

      // Inline code: `text`
      if (part.startsWith("`") && part.endsWith("`") && part.length >= 2) {
        return (
          <code
            key={idx}
            style={{
              padding: "2px 6px",
              borderRadius: "4px",
              background: isUser ? "rgba(0,0,0,0.2)" : "rgba(224, 138, 154, 0.15)",
              color: isUser ? "#FFFFFF" : "var(--accent-pink, #E08A9A)",
              fontSize: "0.88em",
              fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
            }}
          >
            {part.slice(1, -1)}
          </code>
        );
      }

      // Link: [text](url)
      const linkMatch = part.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
      if (linkMatch) {
        const linkText = linkMatch[1];
        const linkUrl = linkMatch[2];
        const isExternal = linkUrl.startsWith("http://") || linkUrl.startsWith("https://");
        return (
          <a
            key={idx}
            href={linkUrl}
            target={isExternal ? "_blank" : undefined}
            rel={isExternal ? "noopener noreferrer" : undefined}
            style={{
              color: isUser ? "#FFFFFF" : "var(--accent-pink, #E08A9A)",
              textDecoration: "underline",
              fontWeight: 600,
            }}
          >
            {linkText}
          </a>
        );
      }

      return <React.Fragment key={idx}>{part}</React.Fragment>;
    });
  }

  for (let i = 0; i < lines.length; i++) {
    const rawLine = lines[i];

    // Fenced Code Block delimiter
    if (rawLine.trim().startsWith("```")) {
      if (!inCodeBlock) {
        inCodeBlock = true;
        codeBlockLang = rawLine.trim().replace(/^```/, "").trim();
        codeBlockBuffer = [];
      } else {
        inCodeBlock = false;
        elements.push(
          <div
            key={`code-${i}`}
            style={{
              margin: "8px 0",
              padding: "10px 14px",
              borderRadius: "10px",
              background: "rgba(0,0,0,0.4)",
              color: "#E2E8F0",
              fontFamily: "ui-monospace, SFMono-Regular, monospace",
              fontSize: "12px",
              overflowX: "auto",
              border: "1px solid rgba(255,255,255,0.1)",
            }}
          >
            {codeBlockLang && (
              <div style={{ fontSize: "10px", color: "var(--secondary-text, #94A3B8)", marginBottom: "4px", textTransform: "uppercase", fontWeight: 700 }}>
                {codeBlockLang}
              </div>
            )}
            <pre style={{ margin: 0, whiteSpace: "pre-wrap" }}>{codeBlockBuffer.join("\n")}</pre>
          </div>
        );
      }
      continue;
    }

    if (inCodeBlock) {
      codeBlockBuffer.push(rawLine);
      continue;
    }

    const trimmed = rawLine.trim();

    // Empty line
    if (!trimmed) {
      elements.push(<div key={`blank-${i}`} style={{ height: "6px" }} />);
      continue;
    }

    // Headings
    if (trimmed.startsWith("### ")) {
      elements.push(
        <h4
          key={`h3-${i}`}
          style={{
            fontSize: "15px",
            fontWeight: 800,
            margin: "12px 0 6px 0",
            color: isUser ? "#FFFFFF" : "var(--primary-text, #F1F5F9)",
            letterSpacing: "-0.01em",
          }}
        >
          {parseInline(trimmed.slice(4))}
        </h4>
      );
      continue;
    }

    if (trimmed.startsWith("## ")) {
      elements.push(
        <h3
          key={`h2-${i}`}
          style={{
            fontSize: "17px",
            fontWeight: 800,
            margin: "14px 0 6px 0",
            color: isUser ? "#FFFFFF" : "var(--primary-text, #F1F5F9)",
          }}
        >
          {parseInline(trimmed.slice(3))}
        </h3>
      );
      continue;
    }

    if (trimmed.startsWith("# ")) {
      elements.push(
        <h2
          key={`h1-${i}`}
          style={{
            fontSize: "19px",
            fontWeight: 800,
            margin: "16px 0 8px 0",
            color: isUser ? "#FFFFFF" : "var(--primary-text, #F1F5F9)",
          }}
        >
          {parseInline(trimmed.slice(2))}
        </h2>
      );
      continue;
    }

    // Task Checklist: - [ ] or - [x]
    const taskMatch = trimmed.match(/^-\s+\[([ xX])\]\s+(.*)$/);
    if (taskMatch) {
      const isChecked = taskMatch[1].toLowerCase() === "x";
      const taskBody = taskMatch[2];
      elements.push(
        <div
          key={`task-${i}`}
          style={{
            display: "flex",
            alignItems: "flex-start",
            gap: "8px",
            margin: "4px 0",
            fontSize: "13.5px",
            lineHeight: "1.5",
          }}
        >
          <span
            style={{
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              width: "16px",
              height: "16px",
              borderRadius: "4px",
              marginTop: "2px",
              border: isChecked ? "none" : "1.5px solid var(--border-subtle, #64748B)",
              background: isChecked ? "var(--primary-pink, #E08A9A)" : "transparent",
              color: "#FFFFFF",
              fontSize: "11px",
              fontWeight: 800,
              flexShrink: 0,
            }}
          >
            {isChecked ? "✓" : ""}
          </span>
          <span style={{ textDecoration: isChecked ? "line-through" : "none", opacity: isChecked ? 0.7 : 1 }}>
            {parseInline(taskBody)}
          </span>
        </div>
      );
      continue;
    }

    // Bullet List: - item or * item
    if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
      elements.push(
        <div
          key={`bullet-${i}`}
          style={{
            display: "flex",
            alignItems: "flex-start",
            gap: "8px",
            margin: "3px 0",
            fontSize: "13.5px",
            lineHeight: "1.5",
          }}
        >
          <span style={{ color: "var(--accent-pink, #E08A9A)", fontWeight: 700, marginTop: "-1px" }}>•</span>
          <span>{parseInline(trimmed.slice(2))}</span>
        </div>
      );
      continue;
    }

    // Numbered List: 1. item
    const numMatch = trimmed.match(/^(\d+)\.\s+(.*)$/);
    if (numMatch) {
      elements.push(
        <div
          key={`num-${i}`}
          style={{
            display: "flex",
            alignItems: "flex-start",
            gap: "6px",
            margin: "3px 0",
            fontSize: "13.5px",
            lineHeight: "1.5",
          }}
        >
          <span style={{ fontWeight: 700, color: isUser ? "#FFFFFF" : "var(--accent-pink, #E08A9A)", minWidth: "18px" }}>
            {numMatch[1]}.
          </span>
          <span>{parseInline(numMatch[2])}</span>
        </div>
      );
      continue;
    }

    // Blockquote: > text
    if (trimmed.startsWith("> ")) {
      elements.push(
        <blockquote
          key={`quote-${i}`}
          style={{
            margin: "6px 0",
            padding: "4px 12px",
            borderLeft: "3px solid var(--accent-pink, #E08A9A)",
            color: "var(--secondary-text, #94A3B8)",
            fontStyle: "italic",
            fontSize: "13px",
          }}
        >
          {parseInline(trimmed.slice(2))}
        </blockquote>
      );
      continue;
    }

    // Default Paragraph
    elements.push(
      <p
        key={`p-${i}`}
        style={{
          margin: "4px 0",
          fontSize: "13.5px",
          lineHeight: "1.6",
          color: isUser ? "#FFFFFF" : "var(--primary-text, #F1F5F9)",
        }}
      >
        {parseInline(trimmed)}
      </p>
    );
  }

  return <div className={`markdown-view ${className}`}>{elements}</div>;
}
