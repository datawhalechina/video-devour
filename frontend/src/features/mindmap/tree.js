export function fromGraph(graph) {
  const nodes = new Map(
    (graph?.nodes || []).map((n) => [
      n.id,
      {
        id: n.id,
        title: n.name || "未命名",
        notes: n.desc || "",
        children: [],
        collapsed: false,
      },
    ]),
  );
  const root = nodes.values().next().value || {
    id: "root",
    title: "中心主题",
    notes: "",
    children: [],
  };
  const attached = new Set([root.id]);
  for (const edge of graph?.links || []) {
    const parent = nodes.get(edge.source),
      child = nodes.get(edge.target);
    if (parent && child && !attached.has(child.id) && !find(child, parent.id)) {
      parent.children.push(child);
      attached.add(child.id);
    }
  }
  for (const n of nodes.values())
    if (!attached.has(n.id)) root.children.push(n);
  return root;
}
export function find(tree, id) {
  if (tree.id === id) return tree;
  for (const child of tree.children) {
    const n = find(child, id);
    if (n) return n;
  }
  return null;
}
export function parentOf(tree, id) {
  if (tree.children.some((n) => n.id === id)) return tree;
  for (const c of tree.children) {
    const p = parentOf(c, id);
    if (p) return p;
  }
  return null;
}
export function change(tree, action) {
  const next = structuredClone(tree),
    node = find(next, action.id);
  if (!node) return tree;
  const parent = parentOf(next, action.id);
  if (action.type === "update") Object.assign(node, action.patch);
  if (action.type === "add") {
    const target = action.sibling && parent ? parent : node;
    const fresh = {
      id: action.newId || crypto.randomUUID(),
      title: "新主题",
      notes: "",
      collapsed: false,
      children: [],
    };
    const index =
      action.sibling && parent
        ? parent.children.findIndex((n) => n.id === node.id) + 1
        : target.children.length;
    target.children.splice(index, 0, fresh);
    target.collapsed = false;
  }
  if (action.type === "delete") {
    if (!parent) return tree;
    parent.children = parent.children.filter((n) => n.id !== node.id);
  }
  if (action.type === "move") {
    const target = find(next, action.target);
    if (!parent || !target || find(node, target.id)) return tree;
    const destination = action.before ? parentOf(next, target.id) : target;
    if (!destination) return tree;
    parent.children = parent.children.filter((n) => n.id !== node.id);
    const index = action.before
      ? destination.children.findIndex((n) => n.id === target.id)
      : destination.children.length;
    destination.children.splice(index, 0, node);
    destination.collapsed = false;
  }
  return next;
}
export function flatten(tree, depth = 0) {
  return [
    { ...tree, depth },
    ...tree.children.flatMap((n) => flatten(n, depth + 1)),
  ];
}
export function layoutTree(tree) {
  const nodes = [],
    links = [];
  const count = (n) =>
    n.collapsed || !n.children.length
      ? 1
      : n.children.reduce((s, c) => s + count(c), 0);
  const wrap = (text) =>
    Array.from(text || "未命名")
      .join("")
      .match(/.{1,16}/gu) || ["未命名"];
  const measure = (n) => Math.max(3.2, wrap(n.title).length * 1.3 + 1.5);
  const span = (n) =>
    n.collapsed || !n.children.length
      ? measure(n) + 1
      : Math.max(
          measure(n) + 1,
          n.children.reduce((s, c) => s + span(c), 0),
        );
  const widthOf = (n) =>
    Math.min(
      18,
      Math.max(
        n.id === tree.id ? 12 : 7,
        Array.from(n.title || "").length * 0.85 + 2,
      ),
    );
  const widths = [];
  function scan(n, depth) {
    widths[depth] = Math.max(widths[depth] || 0, widthOf(n));
    if (!n.collapsed) n.children.forEach((c) => scan(c, depth + 1));
  }
  scan(tree, 0);
  const offsets = [0];
  for (let d = 1; d < widths.length; d++)
    offsets[d] = offsets[d - 1] + widths[d - 1] / 2 + widths[d] / 2 + 2.5;
  const root = {
    ...tree,
    x: 0,
    y: 0,
    width: widthOf(tree),
    height: measure(tree),
    depth: 0,
  };
  nodes.push(root);
  const sides = [
    tree.children.filter((_, i) => i % 2 === 0),
    tree.children.filter((_, i) => i % 2 !== 0),
  ];
  function place(n, depth, side, start, parent) {
    const height = span(n),
      placed = {
        ...n,
        x: side * offsets[depth],
        y: start + height / 2,
        width: widthOf(n),
        height: measure(n),
        depth,
      };
    nodes.push(placed);
    links.push({ from: parent, to: placed });
    if (!n.collapsed) {
      let cursor = start;
      for (const c of n.children) {
        place(c, depth + 1, side, cursor, placed);
        cursor += span(c);
      }
    }
  }
  if (!tree.collapsed)
    sides.forEach((branches, i) => {
      let y = -branches.reduce((s, n) => s + span(n), 0) / 2;
      for (const n of branches) {
        place(n, 1, i === 0 ? 1 : -1, y, root);
        y += span(n);
      }
    });
  return { nodes, links, count: count(tree) };
}
