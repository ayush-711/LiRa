"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

/**
 * Renders user-authored Markdown (issue descriptions, comments).
 *
 * Safety: raw HTML is NOT enabled, so react-markdown escapes any HTML in the
 * source — user content can't inject markup. Links are forced to open in a new
 * tab with `rel="noopener noreferrer"`.
 */
export function Markdown({ children }: { children: string }) {
  return (
    <div className="prose-lira">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ href, children }) => (
            <a href={href} target="_blank" rel="noopener noreferrer"
               className="text-brand underline underline-offset-2 hover:opacity-80">
              {children}
            </a>
          ),
          code: ({ className, children, ...props }) => {
            const isBlock = /language-/.test(className || "");
            if (isBlock) {
              return (
                <code className="block overflow-x-auto rounded-lg border bg-surface-2 p-3 font-mono text-[13px]" {...props}>
                  {children}
                </code>
              );
            }
            return (
              <code className="rounded bg-surface-2 px-1 py-0.5 font-mono text-[0.85em]" {...props}>
                {children}
              </code>
            );
          },
        }}
      >
        {children}
      </ReactMarkdown>
    </div>
  );
}
