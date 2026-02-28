import apiClient from "./client";

export const transactionsApi = {
  // Client: create a transaction (JSON or multipart with photo)
  create: (data, file = null) => {
    if (file) {
      const form = new FormData();
      Object.entries(data).forEach(([k, v]) => {
        if (v !== undefined && v !== null) form.append(k, v);
      });
      form.append("evidence_file", file);
      return apiClient.post("/transactions", form, {
        headers: { "Content-Type": "multipart/form-data" },
      });
    }
    return apiClient.post("/transactions", data);
  },

  // Client: confirm amount after OCR conflict
  confirmAmount: (id, amount) =>
    apiClient.patch(`/transactions/${id}`, { amount }),

  // Client: list own transactions
  list: (params = {}) => apiClient.get("/my/transactions", { params }),

  // Client: monthly summary
  summary: (month) => apiClient.get("/my/summary", { params: { month } }),

  // Client: compliance score + grade
  complianceScore: () => apiClient.get("/my/compliance-score"),

  // Client: 12-month annual summary
  annualSummary: (year) => apiClient.get("/my/annual-summary", { params: { year } }),
};
