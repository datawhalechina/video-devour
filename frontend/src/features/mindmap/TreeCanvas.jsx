import { useLayoutEffect, useMemo, useRef, useState } from "react";
import { layoutTree } from "./tree";
import { download } from "../editor/document";

export default function TreeCanvas({
  tree,
  selected,
  onSelect,
  onEdit,
  onMove,
  editing,
  editField,
}) {
  const ref = useRef(),
    svg = useRef(),
    gesture = useRef();
  const [size, setSize] = useState({ w: 80, h: 30 }),
    [scale, setScale] = useState(1),
    [pan, setPan] = useState({ x: 0, y: 0 }),
    [target, setTarget] = useState(null);
  useLayoutEffect(() => {
    const observer = new ResizeObserver(([e]) =>
      setSize({ w: e.contentRect.width / 16, h: e.contentRect.height / 16 }),
    );
    observer.observe(ref.current);
    return () => observer.disconnect();
  }, []);
  const layout = useMemo(() => {
    const expand = node => ({...node, collapsed: false, children: node.children.map(expand)});
    return layoutTree(expand(tree));
  }, [tree]);
  const bounds = useMemo(() => {
    const minX = Math.min(...layout.nodes.map((n) => n.x - n.width / 2)) - 3,
      maxX = Math.max(...layout.nodes.map((n) => n.x + n.width / 2)) + 3;
    const minY = Math.min(...layout.nodes.map((n) => n.y - n.height / 2)) - 3,
      maxY = Math.max(...layout.nodes.map((n) => n.y + n.height / 2)) + 3;
    return {
      x: (minX + maxX) / 2,
      y: (minY + maxY) / 2,
      w: maxX - minX,
      h: maxY - minY,
    };
  }, [layout]);
  const fit = Math.min(1, size.w / bounds.w, size.h / bounds.h),
    zoom = Math.max(0.005, fit * scale),
    w = size.w / zoom,
    h = size.h / zoom;
  const reset = () => {
    setPan({ x: 0, y: 0 });
    setScale(1);
  };
  const exportSVG = () => {
    const clone = svg.current.cloneNode(true);
    clone.setAttribute(
      "viewBox",
      `${bounds.x - bounds.w / 2} ${bounds.y - bounds.h / 2} ${bounds.w} ${bounds.h}`,
    );
    clone.setAttribute("width", String(bounds.w * 16));
    clone.setAttribute("height", String(bounds.h * 16));
    download(
      new XMLSerializer().serializeToString(clone),
      "思维导图.svg",
      "image/svg+xml",
    );
  };
  const editingNode = layout.nodes.find((n) => n.id === editing);
  const editPosition = editingNode
    ? {
        left: `${Math.max(0.5, Math.min(size.w - 15, (editingNode.x - editingNode.width / 2 - (bounds.x - w / 2 + pan.x)) * zoom))}rem`,
        top: `${Math.max(0.5, Math.min(size.h - 5, (editingNode.y - editingNode.height / 2 - (bounds.y - h / 2 + pan.y)) * zoom))}rem`,
        width: `${Math.max(14, editingNode.width * zoom)}rem`,
      }
    : null;
  return (
    <div className="mm-canvas-wrapper">
      <div
        className="mm-canvas"
        ref={ref}
        onPointerDown={(e) => {
          if (e.button !== 0 || e.target.closest("textarea"))
            return;
          const id = e.target.closest("[data-node]")?.getAttribute("data-node");
          gesture.current = {
            x: e.clientX,
            y: e.clientY,
            id,
            pan,
            moved: false,
          };
        }}
        onPointerMove={(e) => {
          const g = gesture.current;
          if (!g) return;
          if (Math.hypot(e.clientX - g.x, e.clientY - g.y) < 5 && !g.moved)
            return;
          g.moved = true;
          e.currentTarget.setPointerCapture(e.pointerId);
          if (g.id) {
            const el = document
              .elementFromPoint(e.clientX, e.clientY)
              ?.closest("[data-node]");
            setTarget(
              el
                ? {
                    id: el.getAttribute("data-node"),
                    before:
                      e.clientY <
                      el.getBoundingClientRect().top +
                        el.getBoundingClientRect().height * 0.25,
                  }
                : null,
            );
          } else
            setPan({
              x: g.pan.x - (e.clientX - g.x) / 16 / zoom,
              y: g.pan.y - (e.clientY - g.y) / 16 / zoom,
            });
        }}
        onPointerUp={() => {
          const g = gesture.current;
          if (g?.moved && g.id && target)
            onMove(g.id, target.id, target.before);
          gesture.current = null;
          setTarget(null);
        }}
        onPointerCancel={() => {
          gesture.current = null;
          setTarget(null);
        }}
      >
        <svg
          ref={svg}
          xmlns="http://www.w3.org/2000/svg"
          width="100%"
          height="100%"
          viewBox={`${bounds.x - w / 2 + pan.x} ${bounds.y - h / 2 + pan.y} ${w} ${h}`}
          aria-label="可编辑思维导图"
        >
          {layout.links.map(({ from, to }) => {
            const direction = to.x > from.x ? 1 : -1,
              x1 = from.x + (direction * from.width) / 2,
              x2 = to.x - (direction * to.width) / 2;
            return (
              <path
                key={to.id}
                d={`M${x1},${from.y} C${(x1 + x2) / 2},${from.y} ${(x1 + x2) / 2},${to.y} ${x2},${to.y}`}
                stroke={to.x > 0 ? "#819b9b" : "#b6a17e"}
                strokeWidth="0.12"
                fill="none"
              />
            );
          })}
          {layout.nodes.map((node) => {
            const lines = Array.from(node.title || "未命名")
              .join("")
              .match(/.{1,16}/gu) || ["未命名"];
            return (
              <g
                key={node.id}
                data-node={node.id}
                role="button"
                tabIndex={0}
                aria-label={`节点：${node.title}`}
                aria-pressed={node.id === selected}
                onClick={() => onSelect(node.id)}
                onContextMenu={() => onSelect(node.id)}
                onDoubleClick={() => onEdit(node.id)}
                onFocus={() => onSelect(node.id)}
                style={{ cursor: "grab" }}
              >
                <rect
                  x={node.x - node.width / 2}
                  y={node.y - node.height / 2}
                  width={node.width}
                  height={node.height}
                  rx={node.depth === 0 ? 1.4 : 0.6}
                  fill={
                    node.depth === 0
                      ? "#e9ddc9"
                      : node.depth === 1
                        ? "#edf2f1"
                        : "#ffffff"
                  }
                  stroke={
                    target?.id === node.id
                      ? "#4c9583"
                      : selected === node.id
                        ? "#4e708d"
                        : "#b9c5ca"
                  }
                  strokeWidth={selected === node.id ? 0.16 : 0.07}
                />
                {target?.id === node.id && target.before && (
                  <path
                    d={`M${node.x - node.width / 2} ${node.y - node.height / 2}h${node.width}`}
                    stroke="#388b79"
                    strokeWidth=".3"
                  />
                )}
                <text
                  x={node.x}
                  y={node.y - (lines.length - 1) * 0.65}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  fontSize={node.depth === 0 ? 1.25 : 1}
                  fontWeight={node.depth < 2 ? 600 : 400}
                  fill="#263440"
                  fontFamily="sans-serif"
                >
                  {lines.map((line, i) => (
                    <tspan x={node.x} dy={i ? 1.3 : 0} key={i}>
                      {line}
                    </tspan>
                  ))}
                </text>

              </g>
            );
          })}
        </svg>
        {editingNode && (
          <div className="mm-edit-inline" style={editPosition}>
            {editField}
          </div>
        )}
        {target && (
          <div className="mm-drop-hint">
            {target.before ? "放到该节点前面" : "作为该节点的子主题"}
          </div>
        )}
      </div>
      <div className="mm-zoom">
        <button
          onClick={() => setScale((s) => Math.max(0.25, s - 0.25))}
          aria-label="缩小"
        >
          −
        </button>
        <span>{Math.round(scale * 100)}%</span>
        <button
          onClick={() => setScale((s) => Math.min(8, s + 0.25))}
          aria-label="放大"
        >
          ＋
        </button>
        <button onClick={reset}>适应画布</button>
        <button onClick={exportSVG}>导出图片</button>
      </div>
    </div>
  );
}
