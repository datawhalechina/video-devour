async function request(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const error = new Error(body.detail || `请求失败 (${response.status})`);
    error.status = response.status;
    throw error;
  }
  return response.json();
}
export function editorApi(taskId, kind, run = '') {
  const base = `/api/editor/${encodeURIComponent(taskId)}/${encodeURIComponent(kind)}`;
  const url = (suffix = '') => `${base}${suffix}${run ? `?run=${encodeURIComponent(run)}` : ''}`;
  return {
    load: () => request(url()),
    save: (body) => request(url(), { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }),
    versions: () => request(url('/versions')),
    version: (id) => request(url(`/versions/${encodeURIComponent(id)}`)),
    upload: async (file) => {
      const body = new FormData(); body.append('file', file);
      return (await request(url('/images'), { method: 'POST', body })).url;
    },
  };
}
