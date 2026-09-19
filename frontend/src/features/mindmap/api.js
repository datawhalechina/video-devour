export function mindmapApi(taskId, run = "") {
  const url = `/api/mindmap/${encodeURIComponent(taskId)}${run ? `?run=${encodeURIComponent(run)}` : ""}`;
  const request = async (options) => {
    const r = await fetch(url, options);
    const data = await r.json();
    if (!r.ok)
      throw Object.assign(new Error(data.detail || "导图保存失败"), {
        status: r.status,
      });
    return data;
  };
  return {
    load: () => request(),
    save: (body) =>
      request({
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      }),
  };
}
