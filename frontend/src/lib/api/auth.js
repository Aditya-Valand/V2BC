import apiClient from "./client";

export const authApi = {
  register: (data) => apiClient.post("/auth/register", data),

  verifyOtp: (userId, otp) =>
    apiClient.post("/auth/verify-otp", { user_id: userId, otp }),

  resendOtp: (userId) =>
    apiClient.post("/auth/resend-otp", { user_id: userId }),

  login: (email, password) =>
    apiClient.post("/auth/login", { email, password }),

  clientLogin: (phone, pin) =>
    apiClient.post("/auth/client-login", { phone, pin }),

  refresh: (refreshToken) =>
    apiClient.post("/auth/refresh", null, {
      headers: { Authorization: `Bearer ${refreshToken}` },
    }),

  me: () => apiClient.get("/auth/me"),

  logout: (token) =>
    apiClient.post("/auth/logout", null, {
      headers: { Authorization: `Bearer ${token}` },
    }),

  updateProfile: (data) => apiClient.put("/auth/me", data),

  changePassword: (currentPassword, newPassword) =>
    apiClient.put("/auth/me/password", {
      current_password: currentPassword,
      new_password: newPassword,
    }),

  registerFcmToken: (fcmToken) =>
    apiClient.put("/auth/fcm-token", { fcm_token: fcmToken }),
};
