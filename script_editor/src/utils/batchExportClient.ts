export interface BatchExportFile {
  relativePath: string;
  fileName: string;
  outputRelativePath: string;
}

export interface BatchExportManifest {
  root: string;
  total: number;
  files: BatchExportFile[];
}

export function isBatchExportMode() {
  return typeof window !== "undefined" && new URLSearchParams(window.location.search).has("batchExport");
}

export function batchExportLimit() {
  if (typeof window === "undefined") {
    return 0;
  }
  const limit = Number(new URLSearchParams(window.location.search).get("batchLimit") || 0);
  return Number.isFinite(limit) && limit > 0 ? Math.floor(limit) : 0;
}

export function batchExportFilter() {
  if (typeof window === "undefined") {
    return "";
  }
  return new URLSearchParams(window.location.search).get("batchFilter")?.trim() ?? "";
}

export async function loadBatchExportManifest() {
  const limit = batchExportLimit();
  const filter = batchExportFilter();
  const params = new URLSearchParams();
  if (limit) {
    params.set("limit", String(limit));
  }
  if (filter) {
    params.set("filter", filter);
  }
  const url = params.size ? `/__batch_export_manifest?${params}` : "/__batch_export_manifest";
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return await response.json() as BatchExportManifest;
}

export async function loadBatchExportJson(relativePath: string) {
  const response = await fetch("/__batch_export_json", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ relativePath }),
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  const body = await response.json() as { text: string };
  return body.text;
}

export async function saveBatchExportImage(relativePath: string, dataUrl: string) {
  const response = await fetch("/__batch_export_image", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ relativePath, dataUrl }),
  });
  if (!response.ok) {
    throw new Error(await response.text());
  }
  return await response.json() as { outputRelativePath: string };
}
