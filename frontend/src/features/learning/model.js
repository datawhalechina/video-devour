import { marked } from "marked";

export const learningKinds = ["mindmap", "graph", "cards", "quiz"];
export const textOnly = (value) =>
  String(value || "")
    .replace(/!\[[^\]]*\]\([^)]*\)/g, "")
    .replace(/\[([^\]]+)\]\([^)]*\)/g, "$1")
    .replace(/[#*_`>]/g, "")
    .trim();

// 保留章节原文，复习答案不使用临时编造的内容。
export function reportSections(markdown) {
  const tokens = marked.lexer(markdown || "");
  const sections = [];
  let title = "";
  let current = null;
  for (const token of tokens) {
    if (token.type === "heading") {
      if (!title) title = textOnly(token.text);
      if (token.depth === 1 && !current) continue;
      current = {
        id: `section-${sections.length}`,
        title: textOnly(token.text),
        content: "",
      };
      sections.push(current);
    } else if (token.raw?.trim()) {
      if (!current) {
        current = { id: "section-0", title: title || "内容摘要", content: "" };
        sections.push(current);
      }
      current.content += token.raw;
    }
  }
  return {
    title,
    sections: sections.filter((section) => section.content.trim()),
  };
}

export function cachedMindmap(html) {
  return (
    html?.match(
      /<script\b[^>]*type=["']text\/template["'][^>]*>([\s\S]*?)<\/script>/i,
    )?.[1] || ""
  );
}

export function cachedGraph(html) {
  const raw = html?.match(
    /const graphData\s*=\s*([\s\S]*?);\s*(?:const|let|var)\b/,
  )?.[1];
  if (!raw) return null;
  try {
    const graph = JSON.parse(raw);
    return Array.isArray(graph.nodes) && Array.isArray(graph.links)
      ? graph
      : null;
  } catch {
    return null;
  }
}

export function markdownGraph(markdown, title) {
  const root = { id: "root", name: title || "知识脉络", desc: "", depth: 0 };
  const nodes = [root],
    links = [],
    stack = [root];
  for (const token of marked.lexer(markdown || "")) {
    if (token.type === "heading") {
      if (token.depth === 1) {
        root.name = textOnly(token.text);
        continue;
      }
      const node = {
        id: `node-${nodes.length}`,
        name: textOnly(token.text),
        desc: "",
        depth: token.depth - 1,
      };
      while (stack.length > 1 && stack.at(-1).depth >= node.depth) stack.pop();
      links.push({ source: stack.at(-1).id, target: node.id });
      nodes.push(node);
      stack.push(node);
    } else if (token.type === "list") {
      for (const item of token.items) {
        const node = {
          id: `node-${nodes.length}`,
          name: textOnly(item.text).split("\n")[0],
          desc: item.text,
          depth: stack.at(-1).depth + 1,
        };
        nodes.push(node);
        links.push({ source: stack.at(-1).id, target: node.id });
      }
    } else if (token.raw?.trim()) stack.at(-1).desc += token.raw;
  }
  return { nodes, links };
}

// 图谱允许交叉边与环。先建立用于排版的生成树，再保留全部原始关系。
export function layoutGraph(graph) {
  if (!graph?.nodes?.length)
    return { nodes: [], links: [], width: 1100, height: 560 };
  const nodes = graph.nodes.map((node, index) => ({
    ...node,
    id: node.id ?? node.name ?? `node-${index}`,
    children: [],
    root: index === 0,
  }));
  const byId = new Map(
    nodes.flatMap((node) => [
      [node.id, node],
      [node.name, node],
    ]),
  );
  const links = (graph.links || [])
    .map((link) => ({
      ...link,
      from: byId.get(link.source),
      to: byId.get(link.target),
    }))
    .filter((link) => link.from && link.to);
  const adjacency = new Map(nodes.map((node) => [node, []]));
  links.forEach(({ from, to }) => {
    adjacency.get(from).push(to);
    adjacency.get(to).push(from);
  });
  const visited = new Set([nodes[0]]);
  const grow = (root) => {
    const queue = [root];
    for (let index = 0; index < queue.length; index += 1) {
      for (const next of adjacency.get(queue[index])) {
        if (visited.has(next)) continue;
        visited.add(next);
        queue[index].children.push(next);
        queue.push(next);
      }
    }
  };
  grow(nodes[0]);
  for (const node of nodes) {
    if (visited.has(node)) continue;
    visited.add(node);
    nodes[0].children.push(node);
    grow(node);
  }
  const leafCount = (node) =>
    node.children.length
      ? node.children.reduce((sum, child) => sum + leafCount(child), 0)
      : 1;
  const depth = (node) =>
    node.children.length ? 1 + Math.max(...node.children.map(depth)) : 0;
  const sides = [[], []];
  nodes[0].children.forEach((branch, index) => sides[index % 2].push(branch));
  const counts = sides.map((branches) =>
    branches.reduce((sum, branch) => sum + leafCount(branch), 0),
  );
  const height = Math.max(560, Math.max(...counts) * 100 + 120);
  const width = Math.max(1100, depth(nodes[0]) * 520 + 280);
  nodes[0].x = width / 2;
  nodes[0].y = height / 2;
  sides.forEach((branches, side) => {
    let cursor = 0;
    const place = (node, level) => {
      node.x = width / 2 + (side ? 1 : -1) * level * 260;
      if (node.children.length) {
        node.children.forEach((child) => place(child, level + 1));
        node.y = (node.children[0].y + node.children.at(-1).y) / 2;
      } else {
        node.y = height / 2 + (cursor - (counts[side] - 1) / 2) * 100;
        cursor += 1;
      }
    };
    branches.forEach((branch) => place(branch, 1));
  });
  return { nodes, links, width, height };
}
