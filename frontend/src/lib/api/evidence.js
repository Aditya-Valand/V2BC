import apiClient from "./client";

export const evidenceApi = {
  upload: (file, businessId = null, statementId = null) => {
    const form = new FormData();
    form.append("file", file);
    if (businessId) form.append("business_id", businessId);
    if (statementId) form.append("statement_id", statementId);
    return apiClient.post("/evidence/upload", form, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },

  get: (id) => apiClient.get(`/evidence/${id}`),

  listForClient: (businessId, params = {}) =>
    apiClient.get(`/evidence/clients/${businessId}`, { params }),
};
