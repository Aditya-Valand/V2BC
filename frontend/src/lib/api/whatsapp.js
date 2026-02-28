import apiClient from "./client";

export const whatsappApi = {
  messages: (businessId, params = {}) =>
    apiClient.get(`/whatsapp/businesses/${businessId}/messages`, { params }),

  message: (id) => apiClient.get(`/whatsapp/messages/${id}`),
};
