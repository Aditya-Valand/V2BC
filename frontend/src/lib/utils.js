import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import { format, formatDistanceToNow, isToday, isYesterday } from "date-fns";

// Tailwind class merger (shadcn pattern)
export function cn(...inputs) {
  return twMerge(clsx(inputs));
}

// Format currency in Indian Rupees
export function formatINR(amount) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(amount || 0);
}

// Format date for display
export function formatDate(dateStr, fmt = "dd MMM yyyy") {
  if (!dateStr) return "—";
  try {
    return format(new Date(dateStr), fmt);
  } catch {
    return dateStr;
  }
}

// Relative time (e.g. "2 days ago")
export function timeAgo(dateStr) {
  if (!dateStr) return "—";
  try {
    const d = new Date(dateStr);
    if (isToday(d)) return "Today";
    if (isYesterday(d)) return "Yesterday";
    return formatDistanceToNow(d, { addSuffix: true });
  } catch {
    return dateStr;
  }
}

// Truncate text
export function truncate(str, n = 40) {
  if (!str) return "";
  return str.length > n ? str.slice(0, n) + "…" : str;
}

// Get initials from name
export function getInitials(name = "") {
  return name
    .split(" ")
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase())
    .join("");
}

// Download blob as file
export function downloadBlob(blob, filename) {
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  window.URL.revokeObjectURL(url);
}
