"use client";

import { useState } from "react";
import { useInfiniteQuery } from "@tanstack/react-query";
import {
  TrendingUp, TrendingDown, ChevronLeft, ChevronRight,
  Receipt, SlidersHorizontal, Image as ImageIcon,
} from "lucide-react";
import { format, addMonths, subMonths, startOfMonth } from "date-fns";
import { transactionsApi } from "@/lib/api/transactions";
import { formatINR, formatDate, getInitials } from "@/lib/utils";

// ── Constants ─────────────────────────────────────────────────────────

const CONFIDENCE_BADGE = {
  high:   { label: "✓ High",   cls: "bg-green-100 text-green-700"  },
  medium: { label: "~ Medium", cls: "bg-yellow-100 text-yellow-700" },
  low:    { label: "! Low",    cls: "bg-red-100 text-red-700"       },
};

// ── Sub-components ────────────────────────────────────────────────────

function MonthNav({ current, onChange }) {
  const label = format(current, "MMMM yyyy");
  const now   = startOfMonth(new Date());
  return (
    <div className="flex items-center justify-between bg-white rounded-2xl border border-slate-200 px-4 py-3">
      <button
        onClick={() => onChange(subMonths(current, 1))}
        className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-slate-100 text-slate-500"
      >
        <ChevronLeft size={18} />
      </button>
      <span className="text-sm font-semibold text-slate-700">{label}</span>
      <button
        onClick={() => onChange(addMonths(current, 1))}
        disabled={current >= now}
        className="w-8 h-8 flex items-center justify-center rounded-lg hover:bg-slate-100 text-slate-500 disabled:opacity-30 disabled:cursor-not-allowed"
      >
        <ChevronRight size={18} />
      </button>
    </div>
  );
}

function SummaryBar({ transactions }) {
  const sales    = transactions.filter((t) => t.type === "sale").reduce((s, t) => s + t.amount, 0);
  const expenses = transactions.filter((t) => t.type === "expense").reduce((s, t) => s + t.amount, 0);

  return (
    <div className="grid grid-cols-2 gap-3">
      <div className="bg-green-50 rounded-2xl p-4">
        <p className="text-xs font-medium text-green-600 opacity-70">Total Sales</p>
        <p className="text-xl font-bold text-green-700 mt-1">{formatINR(sales)}</p>
      </div>
      <div className="bg-red-50 rounded-2xl p-4">
        <p className="text-xs font-medium text-red-600 opacity-70">Total Expenses</p>
        <p className="text-xl font-bold text-red-700 mt-1">{formatINR(expenses)}</p>
      </div>
    </div>
  );
}

function TxRow({ tx }) {
  const isIncome = tx.type === "sale";
  const conf     = CONFIDENCE_BADGE[tx.confidence_level] || CONFIDENCE_BADGE.medium;
  const label    = tx.description || tx.category?.replace(/_/g, " ") || (isIncome ? "Sale" : "Expense");

  return (
    <div className="flex items-center gap-3 px-4 py-3">
      {/* Icon */}
      <div className={`w-10 h-10 rounded-full flex items-center justify-center shrink-0 ${
        isIncome ? "bg-green-100" : "bg-red-100"
      }`}>
        {isIncome
          ? <TrendingUp size={16} className="text-green-600" />
          : <TrendingDown size={16} className="text-red-600" />}
      </div>

      {/* Details */}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-slate-700 truncate capitalize">{label}</p>
        <div className="flex items-center gap-2 mt-0.5">
          <p className="text-xs text-slate-400">{formatDate(tx.transaction_date, "d MMM")}</p>
          {tx.evidence_id && (
            <span className="flex items-center gap-0.5 text-[10px] text-blue-600">
              <ImageIcon size={10} />
              {tx.evidence_status === "success" ? "Scanned" : "Receipt"}
            </span>
          )}
        </div>
      </div>

      {/* Amount + confidence */}
      <div className="text-right shrink-0">
        <p className={`text-sm font-bold ${isIncome ? "text-green-700" : "text-red-600"}`}>
          {isIncome ? "+" : "−"}{formatINR(tx.amount)}
        </p>
        <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded-full ${conf.cls}`}>
          {conf.label}
        </span>
      </div>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────

export default function TransactionHistoryPage() {
  const [month,  setMonth]  = useState(startOfMonth(new Date()));
  const [filter, setFilter] = useState("all");  // all | sale | expense

  const monthStr = format(month, "yyyy-MM");

  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading,
  } = useInfiniteQuery({
    queryKey: ["my-transactions", monthStr, filter],
    queryFn: ({ pageParam = 1 }) =>
      transactionsApi
        .list({
          page:     pageParam,
          per_page: 30,
          from:     `${monthStr}-01`,
          to:       format(new Date(month.getFullYear(), month.getMonth() + 1, 0), "yyyy-MM-dd"),
          ...(filter !== "all" ? { type: filter } : {}),
        })
        .then((r) => r.data.data),
    getNextPageParam: (last) =>
      last.page < last.pages ? last.page + 1 : undefined,
    initialPageParam: 1,
  });

  const allTx  = data?.pages.flatMap((p) => p.transactions) || [];
  const total  = data?.pages[0]?.total || 0;

  // Group by date
  const grouped = allTx.reduce((acc, tx) => {
    const d = tx.transaction_date?.slice(0, 10) || "Unknown";
    if (!acc[d]) acc[d] = [];
    acc[d].push(tx);
    return acc;
  }, {});
  const dates = Object.keys(grouped).sort((a, b) => (b > a ? 1 : -1));

  return (
    <div className="p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-800">History</h1>
          <p className="text-sm text-slate-400 mt-0.5">
            {isLoading ? "Loading…" : `${total} entries`}
          </p>
        </div>
      </div>

      {/* Month nav */}
      <MonthNav current={month} onChange={setMonth} />

      {/* Filter tabs */}
      <div className="flex bg-slate-100 rounded-xl p-1 gap-1">
        {[
          { key: "all",     label: "All" },
          { key: "sale",    label: "Sales" },
          { key: "expense", label: "Expenses" },
        ].map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setFilter(key)}
            className={`flex-1 py-1.5 text-xs font-semibold rounded-lg transition-all ${
              filter === key ? "bg-white text-blue-700 shadow-sm" : "text-slate-500"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Summary bar */}
      {!isLoading && allTx.length > 0 && <SummaryBar transactions={allTx} />}

      {/* Transaction list */}
      {isLoading ? (
        <div className="bg-white rounded-2xl border border-slate-200 divide-y divide-slate-100">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="px-4 py-3 flex items-center gap-3 animate-pulse">
              <div className="w-10 h-10 rounded-full bg-slate-200 shrink-0" />
              <div className="flex-1 space-y-2">
                <div className="h-3 bg-slate-200 rounded w-32" />
                <div className="h-2 bg-slate-100 rounded w-20" />
              </div>
              <div className="h-4 bg-slate-200 rounded w-16" />
            </div>
          ))}
        </div>
      ) : allTx.length === 0 ? (
        <div className="bg-white rounded-2xl border border-slate-200 py-16 text-center">
          <Receipt size={36} className="mx-auto text-slate-300 mb-3" />
          <p className="text-sm font-medium text-slate-500">No entries for {format(month, "MMMM")}</p>
          <p className="text-xs text-slate-400 mt-1">Tap "Add Entry" to record your first transaction.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {dates.map((date) => (
            <div key={date} className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
              {/* Date header */}
              <div className="px-4 py-2 bg-slate-50 border-b border-slate-100">
                <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
                  {formatDate(date, "EEEE, d MMMM")}
                </p>
              </div>
              {/* Rows */}
              <div className="divide-y divide-slate-100">
                {grouped[date].map((tx) => <TxRow key={tx.id} tx={tx} />)}
              </div>
              {/* Day subtotal */}
              <div className="px-4 py-2 bg-slate-50 border-t border-slate-100 flex justify-between text-xs text-slate-500">
                <span>{grouped[date].length} entries</span>
                <span className="font-semibold">
                  {formatINR(
                    grouped[date].reduce(
                      (sum, tx) => sum + (tx.type === "sale" ? tx.amount : -tx.amount),
                      0,
                    ),
                  )}
                </span>
              </div>
            </div>
          ))}

          {/* Load more */}
          {hasNextPage && (
            <button
              onClick={() => fetchNextPage()}
              disabled={isFetchingNextPage}
              className="w-full py-3 text-sm text-blue-700 font-medium hover:underline"
            >
              {isFetchingNextPage ? "Loading…" : "Load more"}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
