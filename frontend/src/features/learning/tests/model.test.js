import test from "node:test";
import assert from "node:assert/strict";
import {
  reportSections,
  markdownGraph,
  cachedGraph,
  layoutGraph,
} from "../model.js";

test("复习卡片保留章节中的原文，代码块标题不被误拆分", () => {
  const result = reportSections(
    "# 视频\n\n## 一\n\n内容。\n\n```js\n# 非标题\n```\n\n## 二\n\n结论。",
  );
  assert.equal(result.title, "视频");
  assert.equal(result.sections.length, 2);
  assert.match(result.sections[0].content, /# 非标题/);
  assert.match(result.sections[1].content, /结论/);
});
test("没有小标题也保留正文，空报告不会伪造知识卡片", () => {
  assert.equal(
    reportSections("直接一段正文").sections[0].content,
    "直接一段正文",
  );
  assert.equal(reportSections("").sections.length, 0);
});
test("图谱仅解析 JSON，不执行生成文档中的脚本", () => {
  assert.equal(
    cachedGraph(
      "<script>const graphData = alert(1); const chart = 1;</script>",
    ),
    null,
  );
  assert.deepEqual(
    cachedGraph('const graphData = {"nodes":[],"links":[]}; const chart = 1;'),
    { nodes: [], links: [] },
  );
});
test("章节层级建立真实父子关系，布局仅使用存在的节点", () => {
  const graph = markdownGraph(
    "# 标题\n## 第一节\n### 子节\n内容\n## 第二节\n内容",
    "标题",
  );
  assert.equal(graph.links[1].source, "node-1");
  const layout = layoutGraph(graph);
  assert.equal(layout.links.length, 3);
  assert.ok(
    layout.nodes.every(
      (node) => Number.isFinite(node.x) && Number.isFinite(node.y),
    ),
  );
  const root = layout.nodes[0];
  const branch = layout.nodes.find((node) => node.id === "node-1");
  const child = layout.nodes.find((node) => node.id === "node-2");
  assert.ok(Math.abs(child.x - root.x) > Math.abs(branch.x - root.x));
});

test("循环关系和孤立节点不会破坏图谱布局", () => {
  const layout = layoutGraph({
    nodes: [{ id: "a" }, { id: "b" }, { id: "c" }, { id: "d" }],
    links: [
      { source: "a", target: "b" },
      { source: "b", target: "c" },
      { source: "c", target: "a" },
      { source: "missing", target: "a" },
    ],
  });
  assert.equal(layout.nodes.length, 4);
  assert.equal(layout.links.length, 3);
  assert.ok(
    layout.nodes.every(
      (node) => Number.isFinite(node.x) && Number.isFinite(node.y),
    ),
  );
});
