import apiClient from "./client";

export const validationApi = {
  check: (data) => apiClient.post("/validation/check", data),

  anomalies: (businessId) =>
    apiClient.get(`/validation/clients/${businessId}/anomalies`),
};
