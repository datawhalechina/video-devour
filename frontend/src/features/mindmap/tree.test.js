import { test } from "node:test";
import assert from "node:assert/strict";
import { change, find, parentOf, fromGraph, layoutTree } from "./tree.js";
const tree = {
  id: "root",
  title: "中心",
  children: [
    {
      id: "a",
      title: "分支A",
      children: [{ id: "aa", title: "子主题", children: [] }],
    },
    { id: "b", title: "分支B", children: [] },
  ],
};
test("moves a subtree, preserves identity and forbids cycles and root deletion", () => {
  const moved = change(tree, { type: "move", id: "a", target: "b" });
  assert.equal(parentOf(moved, "a").id, "b");
  assert.equal(find(moved, "a").children[0].id, "aa");
  assert.equal(change(tree, { type: "move", id: "a", target: "aa" }), tree);
  assert.equal(change(tree, { type: "delete", id: "root" }), tree);
  assert.equal(tree.children.length, 2);
});
test("inserts siblings and reorders without duplication", () => {
  const added = change(tree, {
    type: "add",
    id: "a",
    sibling: true,
    newId: "c",
  });
  assert.deepEqual(
    added.children.map((n) => n.id),
    ["a", "c", "b"],
  );
  const moved = change(added, {
    type: "move",
    id: "b",
    target: "a",
    before: true,
  });
  assert.deepEqual(
    moved.children.map((n) => n.id),
    ["b", "a", "c"],
  );
});
test("collapsed branches keep their data and layout hides descendants", () => {
  const collapsed = change(tree, {
    type: "update",
    id: "a",
    patch: { collapsed: true },
  });
  assert.ok(find(collapsed, "aa"));
  assert.ok(!layoutTree(collapsed).nodes.some((n) => n.id === "aa"));
});
test("imports graph with stable ids, notes and child order", () => {
  const result = fromGraph({
    nodes: [
      { id: "root", name: "标题" },
      { id: "a", name: "一", desc: "来源" },
      { id: "b", name: "二" },
    ],
    links: [
      { source: "root", target: "a" },
      { source: "a", target: "b" },
    ],
  });
  assert.equal(result.children[0].notes, "来源");
  assert.equal(result.children[0].children[0].id, "b");
});
