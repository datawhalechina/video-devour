import { useLayoutEffect, useMemo, useRef, useState } from "react";
import { Download, Maximize, Minus, Plus, X } from "lucide-react";
import { Button, EmptyState } from "../../shared/ui/Workspace";
import { layoutGraph, textOnly } from "./model";

export default function MapCanvas({ graph }) {
  const [scale, setScale] = useState(1);
  const [selected, setSelected] = useState(null);
  const svgRef = useRef(null);
  const viewportRef = useRef(null);
  const drag = useRef(null);
  const [size, setSize] = useState({ width: 1, height: 1 });
  const [pan, setPan] = useState({ x: 0, y: 0 });
  useLayoutEffect(() => {
    if (!viewportRef.current) return;
    const observer = new ResizeObserver(([entry]) => setSize({ width: entry.contentRect.width, height: entry.contentRect.height }));
    observer.observe(viewportRef.current);
    return () => observer.disconnect();
  }, []);
  const layout = useMemo(() => layoutGraph(graph), [graph]);
  const bounds = useMemo(() => {
    if (!layout.nodes.length) return { x: 0, y: 0, width: 1, height: 1 };
    const left = Math.min(...layout.nodes.map(n => n.x - (n.root ? 130 : 110))) - 48;
    const right = Math.max(...layout.nodes.map(n => n.x + (n.root ? 130 : 110))) + 48;
    const top = Math.min(...layout.nodes.map(n => n.y)) - 80;
    const bottom = Math.max(...layout.nodes.map(n => n.y)) + 80;
    return { x: (left + right) / 2, y: (top + bottom) / 2, width: right - left, height: bottom - top };
  }, [layout]);
  const fit = Math.min(1, size.width / bounds.width, size.height / bounds.height);
  const zoom = Math.max(0.001, fit * scale);
  const viewWidth = size.width / zoom, viewHeight = size.height / zoom;
  const reset = () => { setScale(1); setPan({ x: 0, y: 0 }); };
  const exportImage = () => {
    // 导出使用完整画布尺寸，不把当前浏览器缩放比例写进文件。
    const snapshot = svgRef.current.cloneNode(true);
    snapshot.setAttribute("viewBox", `0 0 ${layout.width} ${layout.height}`);
    snapshot.setAttribute("width", String(layout.width));
    snapshot.setAttribute("height", String(layout.height));
    const data = new XMLSerializer().serializeToString(snapshot);
    const url = URL.createObjectURL(
      new Blob([data], { type: "image/svg+xml" }),
    );
    const link = document.createElement("a");
    link.href = url;
    link.download = "知识导图.svg";
    document.body.appendChild(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 10000);
  };
  if (!layout.nodes.length)
    return (
      <EmptyState
        title="还没有知识图谱"
        description="生成后，可以在这里查看概念之间的关系。"
      />
    );
  return (
    <div className="vd-map-panel">
      <div className="vd-map-scroll" ref={viewportRef}
        onPointerDown={(event) => {
          if (event.button !== 0 || event.target.closest('[role="button"]')) return;
          drag.current = { x: event.clientX, y: event.clientY, pan };
          event.currentTarget.setPointerCapture(event.pointerId);
        }}
        onPointerMove={(event) => {
          if (!drag.current) return;
          setPan({ x: drag.current.pan.x - (event.clientX - drag.current.x) / zoom, y: drag.current.pan.y - (event.clientY - drag.current.y) / zoom });
        }}
        onPointerUp={() => { drag.current = null; }}
        onPointerCancel={() => { drag.current = null; }}
      >
        <svg
          ref={svgRef}
          xmlns="http://www.w3.org/2000/svg"
          viewBox={`${bounds.x - viewWidth / 2 + pan.x} ${bounds.y - viewHeight / 2 + pan.y} ${viewWidth} ${viewHeight}`}
          width="100%"
          height="100%"
          preserveAspectRatio="xMidYMid meet"
          role="group"
          aria-label="知识导图，点击节点查看详情"
        >
          {layout.links.map((link, index) => (
            <g key={index}>
              <path
                d={`M ${link.from.x} ${link.from.y} C ${(link.from.x + link.to.x) / 2} ${link.from.y}, ${(link.from.x + link.to.x) / 2} ${link.to.y}, ${link.to.x} ${link.to.y}`}
                fill="none"
                stroke={["#c8b994", "#a7b19c", "#c7b6b0"][index % 3]}
                strokeWidth="2"
              />
              {link.relation && (
                <text
                  x={(link.from.x + link.to.x) / 2}
                  y={(link.from.y + link.to.y) / 2 - 8}
                  fontSize="11"
                  fill="#818579"
                  textAnchor="middle"
                >
                  {link.relation}
                </text>
              )}
            </g>
          ))}
          {layout.nodes.map((node, index) => {
            const name = textOnly(node.name),
              lines = name.match(/.{1,14}/gu) || [""];
            return (
              <g
                key={node.id || node.name}
                role="button"
                aria-label={`查看节点：${name}`}
                tabIndex={0}
                onClick={() => setSelected(node)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    setSelected(node);
                  }
                }}
                style={{ cursor: "pointer" }}
              >
                <rect
                  x={node.x - (node.root ? 130 : 110)}
                  y={node.y - 32}
                  width={node.root ? 260 : 220}
                  height="64"
                  rx="32"
                  fill={
                    node.root
                      ? "#efe5d5"
                      : index % 3 === 0
                        ? "#f0f2eb"
                        : "#ffffff"
                  }
                  stroke="#d8d7d4"
                  strokeWidth="1.2"
                />
                <text
                  x={node.x}
                  y={node.y - (Math.min(lines.length, 2) - 1) * 9}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fill="#242832"
                  fontSize={node.root ? "26" : node.children.length ? "21" : "18"}
                  fontFamily="sans-serif"
                  fontWeight={node.root ? "600" : node.children.length ? "500" : "400"}
                >
                  {lines.slice(0, 2).map((line, i) => (
                    <tspan key={i} x={node.x} dy={i ? 20 : 0}>
                      {line}
                      {i === 1 && lines.length > 2 ? "…" : ""}
                    </tspan>
                  ))}
                </text>
              </g>
            );
          })}
        </svg>
      </div>
      {selected && (
        <aside className="vd-map-detail">
          <Button
            variant="quiet"
            aria-label="关闭节点详情"
            onClick={() => setSelected(null)}
          >
            <X />
          </Button>
          <h3>{selected.name}</h3>
          <p>{textOnly(selected.desc) || "该节点来自报告中的章节或知识点。"}</p>
        </aside>
      )}
      <div className="vd-map-controls">
        <Button
          aria-label="缩小"
          onClick={() => setScale((n) => Math.max(0.25, n - 0.25))}
        >
          <Minus />
        </Button>
        <span>{Math.round(scale * 100)}%</span>
        <Button
          aria-label="放大"
          onClick={() => setScale((n) => Math.min(8, n + 0.25))}
        >
          <Plus />
        </Button>
        <Button onClick={reset}>
          <Maximize />
          适应画布
        </Button>
        <Button onClick={exportImage}>
          <Download />
          导出图片
        </Button>
      </div>
    </div>
  );
}
