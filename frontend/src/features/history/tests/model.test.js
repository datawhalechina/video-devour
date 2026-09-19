import test from "node:test";
import assert from "node:assert/strict";
import { groupHistory } from "../model.js";

test("日期分组按本地自然日排序，未知时间不会混入今天", () => {
  const now = new Date(2026, 8, 16, 12);
  const result = groupHistory(
    [
      { id: 1, createdAt: new Date(2026, 8, 15, 23).toISOString() },
      { id: 2, createdAt: new Date(2026, 8, 16, 8).toISOString() },
      { id: 3, createdAt: "invalid" },
    ],
    now,
  );
  assert.deepEqual(
    result.map((group) => group.label),
    ["今天", "昨天", "时间未知"],
  );
  assert.deepEqual(
    result.flatMap((group) => group.items.map((item) => item.id)),
    [2, 1, 3],
  );
});
