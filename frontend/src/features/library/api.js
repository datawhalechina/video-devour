export async function readLibrary(query = "", scope = "all", signal) {
  const url = query.trim()
    ? `/api/library/search?q=${encodeURIComponent(query)}&scope=${encodeURIComponent(scope)}&top_k=30`
    : "/api/library/videos";
  const response = await fetch(url, { signal });
  if (!response.ok) throw new Error(`读取知识库失败 (${response.status})`);
  return response.json();
}
