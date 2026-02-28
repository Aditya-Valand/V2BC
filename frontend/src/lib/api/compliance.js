import apiClient from "./client";

export const complianceApi = {
  riskSummary: (orgId) =>
    apiClient.get(`/compliance/orgs/${orgId}/risk-summary`),

  businessProfile: (businessId) =>
    apiClient.get(`/compliance/businesses/${businessId}/profile`),

  openAlerts: (orgId, params = {}) =>
    apiClient.get(`/compliance/orgs/${orgId}/alerts/open`, { params }),

  acknowledgeAlert: (alertId) =>
    apiClient.post(`/compliance/compliance/alerts/${alertId}/acknowledge`),

  resolveAlert: (alertId) =>
    apiClient.post(`/compliance/compliance/alerts/${alertId}/resolve`),

  disciplineRanking: (orgId) =>
    apiClient.get(`/compliance/orgs/${orgId}/discipline-ranking`),

  orgSummary: (orgId) =>
    apiClient.get(`/compliance/orgs/${orgId}/summary`),

  businessStatements: (businessId) =>
    apiClient.get(`/compliance/businesses/${businessId}/statements`),

  businessEvidence: (businessId) =>
    apiClient.get(`/compliance/businesses/${businessId}/evidence`),

  weakEvidence: (businessId) =>
    apiClient.get(`/compliance/businesses/${businessId}/weak-evidence`),
};
