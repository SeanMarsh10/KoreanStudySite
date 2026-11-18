export async function api(path, { method = "GET", body, form } = {}) {
  const headers = {};
  const token = localStorage.getItem("token");
  if (token) headers.Authorization = `Token ${token}`;
  let payload;
  if (form) payload = form;
  else if (body) { headers["Content-Type"] = "application/json"; payload = JSON.stringify(body); }
  const res = await fetch(`/api${path}`, { method, headers, body: payload });
  const data = res.status === 204 ? null : await res.json().catch(() => null);
  if (!res.ok) {
    const msg = data?.detail || data?.non_field_errors?.[0] || (data && Object.values(data).flat().join(" "));
    throw new Error(msg || "Something went wrong. Try again.");
  }
  return data;
}

export async function download(path, filename) {
  const token = localStorage.getItem("token");
  const res = await fetch(`/api${path}`, { headers: token ? { Authorization: `Token ${token}` } : {} });
  if (!res.ok) throw new Error("Export failed. Try again.");
  const url = URL.createObjectURL(await res.blob());
  Object.assign(document.createElement("a"), { href: url, download: filename }).click();
  URL.revokeObjectURL(url);
}
