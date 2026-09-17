import { isLearningPreview, learningPreview } from "./preview";
export async function learningRequest(taskId, endpoint, body, signal) {
  if (isLearningPreview(taskId)) return learningPreview(endpoint, body);
  const response = await fetch(
    `/api/task/${encodeURIComponent(taskId)}/${endpoint}`,
    {
      signal,
      ...(body === undefined
        ? {}
        : {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
          }),
    },
  );
  if (response.status === 404 && body === undefined && endpoint !== "report")
    return null;
  const data = await response.json();
  if (!response.ok)
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : `读取失败 (${response.status})`,
    );
  return data;
}
