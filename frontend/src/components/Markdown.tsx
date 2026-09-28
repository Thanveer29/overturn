import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

/** The LLM (both Groq completions and Hindsight's reflect()) returns
 * markdown -- headings, bold, tables. Rendering it as plain text made
 * appeal strategies and drafts look like raw text dumps, which reads as
 * unpolished for a "professional platform" positioning. */
export function Markdown({ text }: { text: string }) {
  return (
    <div className="markdown-body">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{text}</ReactMarkdown>
    </div>
  );
}
