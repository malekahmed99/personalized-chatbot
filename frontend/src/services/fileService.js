import { apiFetch } from "./api";

export const fileService = {
  async downloadFile(token, fileId, filename, onUnauthorized) {
    const res = await apiFetch(`/api/files/${fileId}`, {}, token, onUnauthorized);
    if (!res.ok) throw new Error("Failed to download file");

    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename || "report.md";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  },
};