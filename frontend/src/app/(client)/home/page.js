"use client";

import { useState, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import {
  TrendingUp, TrendingDown, ArrowRight,
  Plus, Receipt, Zap, Sparkles, Bell, X,
} from "lucide-react";
import { toast } from "sonner";
import { format, differenceInDays, parseISO } from "date-fns";
import { transactionsApi } from "@/lib/api/transactions";
import { deadlinesApi } from "@/lib/api/deadlines";
import { authApi } from "@/lib/api/auth";
import { formatINR, formatDate } from "@/lib/utils";
import useAuthStore from "@/store/authStore";

// ── Notification permission prompt ────────────────────────────────────

function NotificationPrompt({ onEnable, onDismiss }) {
  return (
    <div className="bg-blue-50 border border-blue-200 rounded-2xl p-4 flex items-start gap-3">
      <div className="w-9 h-9 bg-blue-100 rounded-xl flex items-center justify-center shrink-0 mt-0.5">
        <Bell size={16} className="text-blue-700" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-bold text-blue-900">Enable notifications</p>
        <p className="text-xs text-blue-700 mt-0.5 leading-relaxed">
          Get deadline reminders so you never miss a GST filing or tax due date.
        </p>
        <div className="flex items-center gap-2 mt-3">
          <button
            onClick={onEnable}
            className="text-xs font-bold bg-blue-700 text-white px-4 py-1.5 rounded-xl active:scale-95 transition-all"
          >
            Enable
          </button>
          <button
            onClick={onDismiss}
            className="text-xs font-medium text-blue-500 px-3 py-1.5"
          >
            Not now
          </button>
        </div>
      </div>
      <button onClick={onDismiss} className="text-blue-400 hover:text-blue-600 mt-0.5 shrink-0">
        <X size={14} />
      </button>
    </div>
  );
}

// ── Helpers ───────────────────────────────────────────────────────────

function greeting() {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
}

function deadlineUrgency(dueDateStr, status) {
  if (status === "completed") return null;
  const today = new Date(); today.setHours(0, 0, 0, 0);
  const diff = differenceInDays(parseISO(dueDateStr), today);
  if (diff < 0)  return { label: `${Math.abs(diff)}d overdue`, cls: "text-red-600 bg-red-50 border-red-200"    };
  if (diff === 0) return { label: "Due today",                  cls: "text-red-600 bg-red-50 border-red-200"    };
  if (diff === 1) return { label: "Tomorrow",                   cls: "text-orange-600 bg-orange-50 border-orange-200" };
  if (diff <= 7)  return { label: `${diff}d left`,              cls: "text-yellow-700 bg-yellow-50 border-yellow-200" };
  return { label: `${diff}d left`, cls: "text-slate-500 bg-slate-100 border-slate-200" };
}

// ── Mini bar chart (CSS only, no libs) ───────────────────────────────

function ActivityChart({ daily }) {
  if (!daily?.length) return null;

  // Last 14 days, take the last 14 entries (or all if fewer)
  const entries = daily.slice(-14);
  const maxVal  = Math.max(...entries.map((d) => Math.max(d.sales || 0, d.expenses || 0)), 1);

  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-4">
      <div className="flex items-center justify-between mb-3">
        <p className="text-sm font-bold text-slate-700">Daily Activity</p>
        <div className="flex items-center gap-3 text-[11px] font-medium text-slate-400">
          <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-sm bg-green-400 inline-block" />Sales</span>
          <span className="flex items-center gap-1"><span className="w-2.5 h-2.5 rounded-sm bg-red-300 inline-block" />Expenses</span>
        </div>
      </div>
      <div className="flex items-end gap-1 h-20">
        {entries.map((d, i) => {
          const salePct    = ((d.sales    || 0) / maxVal) * 100;
          const expensePct = ((d.expenses || 0) / maxVal) * 100;
          return (
            <div key={i} className="flex-1 flex flex-col items-center gap-0.5 h-full justify-end group relative">
              {/* Tooltip */}
              <div className="absolute -top-14 left-1/2 -translate-x-1/2 hidden group-hover:flex flex-col items-center z-10 pointer-events-none">
                <div className="bg-slate-800 text-white text-[10px] rounded-lg px-2 py-1.5 whitespace-nowrap shadow-xl">
                  <p className="font-semibold">{formatDate(d.date, "d MMM")}</p>
                  {d.sales    > 0 && <p className="text-green-300">+{formatINR(d.sales)}</p>}
                  {d.expenses > 0 && <p className="text-red-300">−{formatINR(d.expenses)}</p>}
                </div>
                <div className="w-2 h-2 bg-slate-800 rotate-45 -mt-1" />
              </div>
              {/* Bars */}
              <div className="w-full flex gap-px justify-center">
                {d.sales > 0 && (
                  <div
                    className="flex-1 bg-green-400 rounded-t-sm min-h-[2px] transition-all"
                    style={{ height: `${Math.max(salePct * 0.75, 2)}px` }}
                  />
                )}
                {d.expenses > 0 && (
                  <div
                    className="flex-1 bg-red-300 rounded-t-sm min-h-[2px] transition-all"
                    style={{ height: `${Math.max(expensePct * 0.75, 2)}px` }}
                  />
                )}
                {!d.sales && !d.expenses && (
                  <div className="flex-1 bg-slate-100 rounded-t-sm" style={{ height: "2px" }} />
                )}
              </div>
            </div>
          );
        })}
      </div>
      {/* X-axis labels: first and last */}
      <div className="flex justify-between mt-1">
        <span className="text-[10px] text-slate-400">{formatDate(entries[0]?.date, "d MMM")}</span>
        <span className="text-[10px] text-slate-400">{formatDate(entries[entries.length - 1]?.date, "d MMM")}</span>
      </div>
    </div>
  );
}

// ── Expense category breakdown ────────────────────────────────────────

function ExpenseBreakdown({ categories }) {
  if (!categories || Object.keys(categories).length === 0) return null;

  const entries = Object.entries(categories)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 5);
  const total = entries.reduce((s, [, v]) => s + v, 0);

  const COLORS = ["bg-blue-500", "bg-purple-500", "bg-pink-500", "bg-orange-400", "bg-slate-400"];

  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-4">
      <p className="text-sm font-bold text-slate-700 mb-3">Expenses by Category</p>
      <div className="space-y-2.5">
        {entries.map(([cat, amount], i) => {
          const pct   = Math.round((amount / total) * 100);
          const label = cat.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
          return (
            <div key={cat}>
              <div className="flex items-center justify-between text-xs mb-1">
                <div className="flex items-center gap-1.5">
                  <span className={`w-2 h-2 rounded-full ${COLORS[i] || COLORS[4]}`} />
                  <span className="text-slate-600 capitalize">{label}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-slate-400">{pct}%</span>
                  <span className="font-semibold text-slate-700">{formatINR(amount)}</span>
                </div>
              </div>
              <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full ${COLORS[i] || COLORS[4]} transition-all`}
                  style={{ width: `${pct}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Recent transactions ───────────────────────────────────────────────

function RecentTransactions({ transactions }) {
  if (!transactions?.length) return null;

  return (
    <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100">
        <p className="text-sm font-bold text-slate-700">Recent Entries</p>
        <Link href="/transactions" className="text-xs font-semibold text-blue-700 flex items-center gap-1 hover:underline">
          All <ArrowRight size={11} />
        </Link>
      </div>
      <div className="divide-y divide-slate-100">
        {transactions.slice(0, 5).map((tx) => {
          const isIncome = tx.type === "sale";
          const label = tx.description || tx.category?.replace(/_/g, " ") || (isIncome ? "Sale" : "Expense");
          return (
            <div key={tx.id} className="flex items-center gap-3 px-4 py-3">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
                isIncome ? "bg-green-100" : "bg-red-100"
              }`}>
                {isIncome
                  ? <TrendingUp size={13} className="text-green-600" />
                  : <TrendingDown size={13} className="text-red-600" />}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-slate-700 truncate capitalize">{label}</p>
                <p className="text-xs text-slate-400">{formatDate(tx.transaction_date, "d MMM")}</p>
              </div>
              <span className={`text-sm font-bold shrink-0 ${isIncome ? "text-green-700" : "text-red-600"}`}>
                {isIncome ? "+" : "−"}{formatINR(tx.amount)}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────

export default function ClientHomePage() {
  const { user, org } = useAuthStore();
  const monthDate  = new Date();
  const month      = format(monthDate, "yyyy-MM");
  const businessId = org?.id;

  // ── Notification permission prompt ──────────────────────────────────
  const [showNotifPrompt, setShowNotifPrompt] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined" || !("Notification" in window)) return;
    if (Notification.permission === "default") {
      const dismissed = sessionStorage.getItem("bc_notif_dismissed");
      if (!dismissed) setShowNotifPrompt(true);
    }
  }, []);

  const handleEnableNotifications = async () => {
    setShowNotifPrompt(false);
    try {
      const reg = await navigator.serviceWorker.ready;
      const { requestFcmToken } = await import("@/lib/firebase");
      const token = await requestFcmToken(reg);
      if (token) {
        await authApi.registerFcmToken(token).catch(() => {});
        localStorage.setItem("bc_fcm_token", token);
        toast.success("Notifications enabled! You'll get deadline reminders.");
      } else if (Notification.permission === "denied") {
        toast.error("Notifications blocked. Enable in browser settings.");
      }
    } catch {
      toast.error("Could not enable notifications. Try again later.");
    }
  };

  const handleDismissNotifPrompt = () => {
    setShowNotifPrompt(false);
    sessionStorage.setItem("bc_notif_dismissed", "1");
  };

  const { data: summaryData, isLoading: loadingSummary } = useQuery({
    queryKey: ["my-summary", month],
    queryFn: () => transactionsApi.summary(month).then((r) => r.data.data.summary),
  });

  const { data: txData, isLoading: loadingTx } = useQuery({
    queryKey: ["my-transactions-recent"],
    queryFn: () => transactionsApi.list({ page: 1, per_page: 5 }).then((r) => r.data.data),
  });

  const { data: deadlineData } = useQuery({
    queryKey: ["my-upcoming-deadlines"],
    queryFn: () => deadlinesApi.upcoming(14).then((r) => r.data.data),
    enabled: !!businessId,
  });

  const s = summaryData || {};
  const net     = (s.net_income) ?? ((s.total_sales || 0) - (s.total_expenses || 0));
  const netPct  = s.total_sales > 0
    ? Math.round(((s.total_sales - (s.total_expenses || 0)) / s.total_sales) * 100)
    : 0;

  const urgentDeadlines = [
    ...(deadlineData?.overdue   || []),
    ...(deadlineData?.this_week || []),
  ].slice(0, 3);

  return (
    <div className="p-4 space-y-4 pb-6">

      {/* ── Greeting header ── */}
      <div className="pt-1">
        <p className="text-xs font-medium text-slate-400 uppercase tracking-wide">
          {format(new Date(), "EEEE, d MMMM yyyy")}
        </p>
        <h1 className="text-xl font-bold text-slate-800 mt-0.5">
          {greeting()}, {user?.name?.split(" ")[0]} 👋
        </h1>
      </div>

      {/* ── BharatBot daily prompt ── */}
      <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-sm">
        {/* Bot header */}
        <div className="flex items-center gap-2.5 px-4 py-3 border-b border-slate-100">
          <div className="w-8 h-8 rounded-full bg-blue-700 flex items-center justify-center shrink-0">
            <Sparkles size={14} className="text-white" />
          </div>
          <div className="flex-1">
            <p className="text-xs font-bold text-slate-700 leading-none">BharatBot</p>
            <p className="text-[10px] text-green-500 font-medium mt-0.5">Ready to help</p>
          </div>
          <span className="text-[10px] text-slate-400">{format(new Date(), "h:mm a")}</span>
        </div>

        {/* Bot message bubble */}
        <div className="px-4 py-3">
          <div className="bg-slate-100 rounded-2xl rounded-tl-sm px-3.5 py-2.5 inline-block max-w-full">
            <p className="text-sm text-slate-700 leading-relaxed">
              {summaryData?.transaction_count > 0
                ? `You have ${summaryData.transaction_count} entries this month. Want to add today's transactions?`
                : `Let's get started! Record today's sales or expenses.`
              }
            </p>
          </div>
        </div>

        {/* Quick action buttons */}
        <div className="grid grid-cols-2 gap-2.5 px-4 pb-4">
          <Link
            href="/transactions/new?type=sale"
            className="flex items-center gap-2.5 bg-green-600 hover:bg-green-700 active:scale-[0.97] text-white rounded-xl px-3.5 py-3 transition-all"
          >
            <div className="w-7 h-7 bg-white/20 rounded-lg flex items-center justify-center shrink-0">
              <TrendingUp size={14} />
            </div>
            <div>
              <p className="text-xs font-bold">Add Sale</p>
              <p className="text-[10px] opacity-75">Record income</p>
            </div>
          </Link>
          <Link
            href="/transactions/new?type=expense"
            className="flex items-center gap-2.5 bg-white border border-slate-200 hover:bg-slate-50 active:scale-[0.97] text-slate-700 rounded-xl px-3.5 py-3 transition-all"
          >
            <div className="w-7 h-7 bg-red-100 rounded-lg flex items-center justify-center shrink-0">
              <TrendingDown size={14} className="text-red-600" />
            </div>
            <div>
              <p className="text-xs font-bold">Add Expense</p>
              <p className="text-[10px] text-slate-400">Record purchase</p>
            </div>
          </Link>
        </div>
      </div>

      {/* ── Notification permission prompt ── */}
      {showNotifPrompt && (
        <NotificationPrompt
          onEnable={handleEnableNotifications}
          onDismiss={handleDismissNotifPrompt}
        />
      )}

      {/* ── Monthly summary hero ── */}
      <div className="bg-gradient-to-br from-blue-700 to-blue-800 rounded-2xl p-5 text-white shadow-lg">
        <div className="flex items-center justify-between mb-4">
          <p className="text-sm font-semibold opacity-80">{format(monthDate, "MMMM yyyy")}</p>
          <span className="text-xs bg-white/20 px-2.5 py-1 rounded-full font-medium">
            {s.transaction_count ?? 0} entries
          </span>
        </div>

        {/* Net income */}
        <div className="mb-4">
          <p className="text-xs opacity-70 uppercase tracking-wide">Net Income</p>
          {loadingSummary ? (
            <div className="h-10 bg-white/20 animate-pulse rounded-xl mt-1 w-32" />
          ) : (
            <p className="text-4xl font-bold tracking-tight mt-1">{formatINR(net)}</p>
          )}
        </div>

        {/* Sales vs expenses row */}
        <div className="flex gap-4">
          <div className="flex-1">
            <div className="flex items-center gap-1.5 mb-0.5">
              <TrendingUp size={12} className="opacity-70" />
              <p className="text-xs opacity-70">Sales</p>
            </div>
            {loadingSummary
              ? <div className="h-5 bg-white/20 animate-pulse rounded w-20" />
              : <p className="text-base font-bold">{formatINR(s.total_sales)}</p>}
          </div>
          <div className="w-px bg-white/20" />
          <div className="flex-1">
            <div className="flex items-center gap-1.5 mb-0.5">
              <TrendingDown size={12} className="opacity-70" />
              <p className="text-xs opacity-70">Expenses</p>
            </div>
            {loadingSummary
              ? <div className="h-5 bg-white/20 animate-pulse rounded w-20" />
              : <p className="text-base font-bold">{formatINR(s.total_expenses)}</p>}
          </div>
        </div>

        {/* Profit margin bar */}
        {!loadingSummary && s.total_sales > 0 && (
          <div className="mt-4 pt-3 border-t border-white/20">
            <div className="flex items-center justify-between text-xs opacity-70 mb-1.5">
              <span>Profit margin</span>
              <span className="font-semibold">{netPct}%</span>
            </div>
            <div className="h-1.5 bg-white/20 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all ${netPct >= 0 ? "bg-green-400" : "bg-red-400"}`}
                style={{ width: `${Math.min(100, Math.abs(netPct))}%` }}
              />
            </div>
          </div>
        )}
      </div>

      {/* ── Urgent deadlines ── */}
      {urgentDeadlines.length > 0 && (
        <div className="bg-orange-50 border border-orange-200 rounded-2xl overflow-hidden">
          <div className="flex items-center justify-between px-4 py-3 border-b border-orange-200">
            <div className="flex items-center gap-2">
              <Zap size={15} className="text-orange-500" />
              <p className="text-sm font-bold text-orange-800">Action Required</p>
            </div>
            <Link href="/my-deadlines" className="text-xs font-semibold text-orange-600 flex items-center gap-1 hover:underline">
              All <ArrowRight size={11} />
            </Link>
          </div>
          <div className="divide-y divide-orange-200">
            {urgentDeadlines.map((d) => {
              const u = deadlineUrgency(d.due_date, d.status);
              return (
                <div key={d.id} className="flex items-center justify-between px-4 py-3 gap-3">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-orange-900 truncate">{d.description}</p>
                    <p className="text-xs text-orange-600">{formatDate(d.due_date)}</p>
                  </div>
                  {u && (
                    <span className={`shrink-0 text-[11px] font-bold px-2 py-0.5 rounded-full border ${u.cls}`}>
                      {u.label}
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ── Daily activity chart ── */}
      {!loadingSummary && s.daily_breakdown?.length > 0 && (
        <ActivityChart daily={s.daily_breakdown} />
      )}

      {/* ── Expense breakdown ── */}
      {!loadingSummary && s.expense_by_category && (
        <ExpenseBreakdown categories={s.expense_by_category} />
      )}

      {/* ── Recent transactions ── */}
      {!loadingTx && (
        <RecentTransactions transactions={txData?.transactions} />
      )}

      {/* ── Empty state: no entries yet ── */}
      {!loadingSummary && !s.transaction_count && (
        <div className="bg-white rounded-2xl border border-dashed border-slate-300 p-8 text-center">
          <div className="w-14 h-14 bg-blue-50 rounded-full flex items-center justify-center mx-auto mb-3">
            <Plus size={24} className="text-blue-600" />
          </div>
          <p className="text-sm font-bold text-slate-600">No entries yet</p>
          <p className="text-xs text-slate-400 mt-1 mb-4">
            Start recording your sales and expenses to track your finances.
          </p>
          <Link href="/transactions/new" className="btn-primary text-sm">
            Add First Entry
          </Link>
        </div>
      )}

      {/* ── View history link ── */}
      {!loadingTx && txData?.total > 5 && (
        <Link
          href="/transactions"
          className="flex items-center justify-center gap-2 text-sm font-semibold text-blue-700 py-3 hover:underline"
        >
          <Receipt size={15} />
          View all {txData.total} entries
        </Link>
      )}
    </div>
  );
}
