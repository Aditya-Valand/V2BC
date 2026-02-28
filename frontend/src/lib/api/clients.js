import apiClient from "./client";

export const clientsApi = {
  list: () => apiClient.get("/clients"),

  create: (data) => apiClient.post("/clients", data),

  get: (id) => apiClient.get(`/clients/${id}`),

  update: (id, data) => apiClient.put(`/clients/${id}`, data),

  detail: (id) => apiClient.get(`/clients/${id}/detail`),

  filingSummary: (id, month) =>
    apiClient.get(`/clients/${id}/filing-summary`, { params: { month } }),

  exportFiling: (id, month) =>
    apiClient.get(`/clients/${id}/filing-summary/export`, {
      params: { month },
      responseType: "blob",
    }),

  regenerateInvite: (id) =>
    apiClient.post(`/clients/${id}/regenerate-invite`),
};

export const inviteApi = {
  preview: (code) => apiClient.get(`/invite/${code}`),

  accept: (data) => apiClient.post("/invite/accept", data),

  verifyOtp: (userId, otp) =>
    apiClient.post("/invite/verify-otp", { user_id: userId, otp }),
};
