import apiClient from "./client";

export const remindersApi = {
  send: (data) => apiClient.post("/reminders/send", data),

  sendBulk: (data) => apiClient.post("/reminders/send-bulk", data),
};
