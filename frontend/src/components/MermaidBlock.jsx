import { useEffect, useRef, useState } from "react";

let mermaidSeq = 0;

/**
 * 把 Mermaid 代码块渲染成 SVG（详细报告里的思维导图）。
 * 渲染失败时回退为纯文本代码块，避免整页空白。
 */
function MermaidBlock({ chart, className = "" }) {
  const ref = useRef(null);
  const idRef = useRef(`mermaid-${++mermaidSeq}`);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const mermaid = (await import("mermaid")).default;
        mermaid.initialize({ startOnLoad: false, theme: "neutral", securityLevel: "loose" });
        const { svg } = await mermaid.render(idRef.current, chart);
        if (!cancelled && ref.current) ref.current.innerHTML = svg;
      } catch (err) {
        console.error("思维导图渲染失败:", err);
        if (!cancelled) setFailed(true);
      }
    })();
    return () => { cancelled = true; };
  }, [chart]);

  if (failed) {
    return <pre className="text-xs bg-slate-100 p-3 rounded-lg overflow-x-auto">{chart}</pre>;
  }
  return <div ref={ref} className={`mermaid-diagram my-4 overflow-x-auto ${className}`} />;
}

/** ReactMarkdown 的 pre/code 覆写：把 mermaid 代码块交给 MermaidBlock，其余保持原样。 */
export const mermaidMarkdownComponents = {
  pre: ({ children }) => {
    const child = Array.isArray(children) ? children[0] : children;
    if (/language-mermaid/.test(child?.props?.className || "")) {
      return <MermaidBlock chart={String(child.props.children).replace(/\n$/, "")} />;
    }
    return <pre className="bg-slate-100 p-4 rounded-lg overflow-x-auto text-sm">{children}</pre>;
  },
  code: ({ node, className, children, ...props }) => {
    if (/language-mermaid/.test(className || "")) {
      return <MermaidBlock chart={String(children).replace(/\n$/, "")} />;
    }
    return <code className={className} {...props}>{children}</code>;
  },
};

export default MermaidBlock;
