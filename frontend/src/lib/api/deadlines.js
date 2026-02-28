import apiClient from "./client";

export const deadlinesApi = {
  forClient: (businessId, status = null) =>
    apiClient.get(`/deadlines/clients/${businessId}`, {
      params: status ? { status } : {},
    }),

  upcoming: (days = 30) =>
    apiClient.get("/deadlines/upcoming", { params: { days } }),

  complete: (deadlineId, notes = null) =>
    apiClient.post(`/deadlines/${deadlineId}/complete`, notes ? { notes } : {}),

  acknowledge: (deadlineId) =>
    apiClient.post(`/deadlines/${deadlineId}/acknowledge`),

  generate: (businessId) =>
    apiClient.post(`/deadlines/generate/${businessId}`),
};
