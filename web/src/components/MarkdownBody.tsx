import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

/**
 * Render artifact markdown as HTML. Raw HTML in the source is ignored
 * (react-markdown default) so proposal/spec/design bodies stay safe.
 */
export default function MarkdownBody({
  children,
  className,
  testId,
}: {
  children: string;
  className?: string;
  testId?: string;
}) {
  const source = children.trim();
  if (!source) return null;
  return (
    <div className={className ? `md-body ${className}` : "md-body"} data-testid={testId}>
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{source}</ReactMarkdown>
    </div>
  );
}
