// Compliance colors used across CA dashboard
export const COMPLIANCE_COLORS = {
  green: { label: "Active", bg: "bg-green-100", text: "text-green-700", dot: "bg-green-500" },
  yellow: { label: "Needs Attention", bg: "bg-yellow-100", text: "text-yellow-700", dot: "bg-yellow-500" },
  red: { label: "Urgent", bg: "bg-red-100", text: "text-red-700", dot: "bg-red-500" },
};

// Deadline types with human-readable labels
export const DEADLINE_TYPES = {
  gstr1_monthly: "GSTR-1 Monthly",
  gstr1_quarterly: "GSTR-1 Quarterly",
  gstr3b: "GSTR-3B",
  cmp08: "CMP-08",
  advance_tax_q1: "Advance Tax Q1",
  advance_tax_q2: "Advance Tax Q2",
  advance_tax_q3: "Advance Tax Q3",
  advance_tax_q4: "Advance Tax Q4",
  fssai_renewal: "FSSAI Renewal",
};

// Deadline status badge styles
export const DEADLINE_STATUS = {
  pending: { label: "Pending", bg: "bg-gray-100", text: "text-gray-700" },
  reminded: { label: "Reminded", bg: "bg-blue-100", text: "text-blue-700" },
  acknowledged: { label: "Acknowledged", bg: "bg-yellow-100", text: "text-yellow-700" },
  completed: { label: "Completed", bg: "bg-green-100", text: "text-green-700" },
  missed: { label: "Missed", bg: "bg-red-100", text: "text-red-700" },
};

// Alert severity styles
export const ALERT_SEVERITY = {
  critical: { label: "Critical", bg: "bg-red-100", text: "text-red-800", border: "border-red-300" },
  high: { label: "High", bg: "bg-orange-100", text: "text-orange-800", border: "border-orange-300" },
  medium: { label: "Medium", bg: "bg-yellow-100", text: "text-yellow-800", border: "border-yellow-300" },
  low: { label: "Low", bg: "bg-blue-100", text: "text-blue-800", border: "border-blue-300" },
};

// Validation warning severity
export const WARNING_SEVERITY = {
  high: { label: "High", color: "text-red-600" },
  medium: { label: "Medium", color: "text-yellow-600" },
  low: { label: "Low", color: "text-blue-600" },
};

// Indian rupee formatter
export const formatINR = (amount) =>
  new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(amount || 0);

// Evidence strength styles
export const EVIDENCE_STRENGTH = {
  strong: { label: "Strong", bg: "bg-green-100", text: "text-green-700" },
  medium: { label: "Medium", bg: "bg-yellow-100", text: "text-yellow-700" },
  weak: { label: "Weak", bg: "bg-red-100", text: "text-red-700" },
};

// Transaction types
export const TX_TYPES = [
  { value: "sale", label: "Sale" },
  { value: "expense", label: "Expense" },
];

// Reminder types
export const REMINDER_TYPES = [
  { value: "general", label: "General" },
  { value: "deadline", label: "Deadline" },
  { value: "missing", label: "Missing Data" },
  { value: "urgent", label: "Urgent" },
];
