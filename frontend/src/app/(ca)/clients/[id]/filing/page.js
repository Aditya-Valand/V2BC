"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import {
  ArrowLeft, Download, ChevronLeft, ChevronRight,
  TrendingUp, TrendingDown, AlertTriangle, CheckCircle2,
  FileText, BarChart3, Shield, Receipt,
} from "lucide-react";
import { toast } from "sonner";
import { format, addMonths, subMonths, startOfMonth } from "date-fns";
import { clientsApi } from "@/lib/api/clients";
import { getApiError } from "@/lib/api/client";
import { formatINR, formatDate, downloadBlob } from "@/lib/utils";

// ── Helpers ───────────────────────────────────────────────────────────

const CONFIDENCE = {
  high:   { label: "High",   cls: "bg-green-100 text-green-700",  dot: "bg-green-500"  },
  medium: { label: "Medium", cls: "bg-yellow-100 text-yellow-700", dot: "bg-yellow-500" },
  low:    { label: "Low",    cls: "bg-red-100 text-red-700",      dot: "bg-red-500"    },
};

// ── Sub-components ────────────────────────────────────────────────────

function MonthNav({ current, onChange }) {
  const now = startOfMonth(new Date());
  return (
    <div className="flex items-center gap-3">
      <button
        onClick={() => onChange(subMonths(current, 1))}
        className="w-9 h-9 flex items-center justify-center rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 transition-colors"
      >
        <ChevronLeft size={18} />
      </button>
      <div className="text-center min-w-[140px]">
        <p className="text-base font-bold text-slate-800">{format(current, "MMMM yyyy")}</p>
      </div>
      <button
        onClick={() => onChange(addMonths(current, 1))}
        disabled={current >= now}
        className="w-9 h-9 flex items-center justify-center rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-slate-600 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
      >
        <ChevronRight size={18} />
      </button>
    </div>
  );
}

function HeroStat({ label, value, icon: Icon, color }) {
  const colors = {
    green: "bg-green-50 text-green-700 border-green-200",
    red:   "bg-red-50 text-red-700 border-red-200",
    blue:  "bg-blue-50 text-blue-700 border-blue-200",
    amber: "bg-amber-50 text-amber-700 border-amber-200",
  };
  return (
    <div className={`rounded-2xl border p-4 flex flex-col gap-2 ${colors[color] || colors.blue}`}>
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold opacity-70 uppercase tracking-wide">{label}</p>
        <Icon size={16} className="opacity-50" />
      </div>
      <p className="text-2xl font-bold tracking-tight">{value}</p>
    </div>
  );
}

function ConfidenceBreakdown({ breakdown, totals }) {
  const items = [
    { key: "high",   label: "High Confidence",   count: breakdown?.high   || 0 },
    { key: "medium", label: "Medium Confidence",  count: breakdown?.medium || 0 },
    { key: "low",    label: "Low Confidence",     count: breakdown?.low    || 0 },
  ];
  const total = breakdown?.total || 1;

  return (
    <div className="bg-white rounded-2xl border border-slate-200 p-5">
      <div className="flex items-center gap-2 mb-4">
        <Shield size={16} className="text-blue-600" />
        <h3 className="text-sm font-bold text-slate-700">Evidence & Confidence</h3>
      </div>

      {/* With evidence ratio */}
      <div className="flex items-center justify-between text-xs text-slate-500 mb-2">
        <span>Transactions with evidence</span>
        <span className="font-semibold text-slate-700">
          {breakdown?.with_evidence ?? 0} / {total}
        </span>
      </div>
      <div className="h-2 bg-slate-100 rounded-full overflow-hidden mb-4">
        <div
          className="h-full bg-blue-500 rounded-full transition-all"
          style={{ width: `${Math.round(((breakdown?.with_evidence || 0) / total) * 100)}%` }}
        />
      </div>

      {/* Breakdown bars */}
      <div className="space-y-2.5">
        {items.map(({ key, label, count }) => {
          const c = CONFIDENCE[key];
          const pct = total > 0 ? Math.round((count / total) * 100) : 0;
          return (
            <div key={key}>
              <div className="flex items-center justify-between text-xs mb-1">
                <div className="flex items-center gap-1.5">
                  <span className={`w-2 h-2 rounded-full ${c.dot}`} />
                  <span className="text-slate-600">{label}</span>
                </div>
                <span className="font-semibold text-slate-700">{count} <span className="text-slate-400 font-normal">({pct}%)</span></span>
              </div>
              <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full ${c.dot} transition-all`}
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

function TransactionTable({ transactions, title, showWarning }) {
  const [expanded, setExpanded] = useState(true);
  if (!transactions?.length) return null;

  return (
    <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden">
      <button
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-center justify-between px-5 py-4 border-b border-slate-100 hover:bg-slate-50 transition-colors"
      >
        <div className="flex items-center gap-2">
          {showWarning
            ? <AlertTriangle size={15} className="text-orange-500" />
            : <Receipt size={15} className="text-slate-500" />
          }
          <h3 className="text-sm font-bold text-slate-700">{title}</h3>
          <span className="text-xs text-slate-400 font-normal">({transactions.length})</span>
        </div>
        <ChevronRight size={16} className={`text-slate-400 transition-transform ${expanded ? "rotate-90" : ""}`} />
      </button>

      {expanded && (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50">
                {["Date", "Description", "Type", "Amount", "Confidence", "Evidence"].map((h) => (
                  <th
                    key={h}
                    className="text-left px-4 py-2.5 text-xs font-semibold text-slate-400 uppercase tracking-wide whitespace-nowrap"
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {transactions.map((tx) => {
                const c = CONFIDENCE[tx.confidence_level] || CONFIDENCE.medium;
                const isIncome = tx.type === "sale";
                return (
                  <tr key={tx.id} className={`hover:bg-slate-50 transition-colors ${showWarning ? "bg-orange-50/30" : ""}`}>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span className="text-xs text-slate-500">{formatDate(tx.transaction_date, "d MMM")}</span>
                    </td>
                    <td className="px-4 py-3 max-w-[200px]">
                      <p className="text-sm text-slate-700 truncate">
                        {tx.description || tx.category?.replace(/_/g, " ") || "—"}
                      </p>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center text-xs font-medium px-2 py-0.5 rounded-full ${
                        isIncome ? "bg-green-100 text-green-700" : "bg-red-100 text-red-700"
                      }`}>
                        {isIncome ? "Sale" : "Expense"}
                      </span>
                    </td>
                    <td className="px-4 py-3 font-semibold whitespace-nowrap">
                      <span className={isIncome ? "text-green-700" : "text-red-600"}>
                        {isIncome ? "+" : "−"}{formatINR(tx.amount)}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center gap-1 text-xs font-semibold px-2 py-0.5 rounded-full ${c.cls}`}>
                        <span className={`w-1.5 h-1.5 rounded-full ${c.dot}`} />
                        {c.label}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      {tx.evidence_id ? (
                        <span className="flex items-center gap-1 text-xs text-blue-600 font-medium">
                          <CheckCircle2 size={12} /> {tx.evidence_status === "success" ? "Scanned" : "Uploaded"}
                        </span>
                      ) : (
                        <span className="text-xs text-slate-400">None</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────

export default function FilingSummaryPage() {
  const { id }   = useParams();
  const router   = useRouter();
  const [month, setMonth] = useState(startOfMonth(new Date()));
  const [downloading, setDownloading] = useState(false);

  const monthStr = format(month, "yyyy-MM");

  const { data, isLoading, isError } = useQuery({
    queryKey: ["filing-summary", id, monthStr],
    queryFn: () => clientsApi.filingSummary(id, monthStr).then((r) => r.data.data),
    enabled: !!id,
  });

  const handleExport = async () => {
    setDownloading(true);
    try {
      const res = await clientsApi.exportFiling(id, monthStr);
      const clientName = data?.client?.name?.replace(/\s+/g, "-") || "client";
      downloadBlob(res.data, `filing-${clientName}-${monthStr}.xlsx`);
      toast.success("Export downloaded successfully.");
    } catch (err) {
      toast.error(getApiError(err));
    } finally {
      setDownloading(false);
    }
  };

  const { client, period, totals, confidence_breakdown, transactions = [], low_confidence_transactions = [] } = data || {};

  return (
    <div className="max-w-5xl mx-auto">
      {/* Back navigation */}
      <button
        onClick={() => router.back()}
        className="flex items-center gap-2 text-sm text-slate-500 hover:text-slate-800 mb-5 transition-colors"
      >
        <ArrowLeft size={16} />
        Back
      </button>

      {/* Page header */}
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 mb-6">
        <div>
          <h1 className="text-xl font-bold text-slate-800 flex items-center gap-2">
            <BarChart3 size={20} className="text-blue-600" />
            Filing Summary
          </h1>
          {client && (
            <div className="flex items-center gap-2 mt-1">
              <p className="text-sm font-semibold text-slate-600">{client.name}</p>
              {client.business_type && (
                <span className="text-xs bg-slate-100 text-slate-500 px-2 py-0.5 rounded-full capitalize">
                  {client.business_type}
                </span>
              )}
              {client.gstin && (
                <span className="text-xs text-slate-400">GSTIN: {client.gstin}</span>
              )}
            </div>
          )}
        </div>

        {/* Month nav + export */}
        <div className="flex items-center gap-3 flex-shrink-0">
          <MonthNav current={month} onChange={setMonth} />
          <button
            onClick={handleExport}
            disabled={downloading || isLoading || !data}
            className="flex items-center gap-2 px-4 py-2.5 bg-blue-700 hover:bg-blue-800 text-white text-sm font-semibold rounded-xl transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            <Download size={15} />
            {downloading ? "Exporting…" : "Export"}
          </button>
        </div>
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-24 bg-slate-200 animate-pulse rounded-2xl" />
            ))}
          </div>
          <div className="h-48 bg-slate-200 animate-pulse rounded-2xl" />
        </div>
      )}

      {/* Error */}
      {isError && (
        <div className="bg-red-50 border border-red-200 rounded-2xl p-8 text-center">
          <p className="text-red-600 font-medium">Failed to load filing summary.</p>
          <p className="text-sm text-red-400 mt-1">Check backend connection and try again.</p>
        </div>
      )}

      {/* No data */}
      {!isLoading && !isError && !data && (
        <div className="bg-slate-50 border border-slate-200 rounded-2xl p-12 text-center">
          <FileText size={40} className="mx-auto text-slate-300 mb-3" />
          <p className="text-slate-500 font-medium">No filing data for {format(month, "MMMM yyyy")}</p>
          <p className="text-sm text-slate-400 mt-1">No transactions recorded in this period.</p>
        </div>
      )}

      {data && !isLoading && (
        <div className="space-y-5">
          {/* Hero stats */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            <HeroStat label="Total Sales"    value={formatINR(totals?.sales)}         icon={TrendingUp}    color="green" />
            <HeroStat label="Total Expenses" value={formatINR(totals?.expenses)}       icon={TrendingDown}  color="red"   />
            <HeroStat label="Net Income"     value={formatINR(totals?.net)}            icon={BarChart3}     color="blue"  />
            <HeroStat
              label="Est. Tax"
              value={totals?.estimated_tax ? formatINR(totals.estimated_tax) : "N/A"}
              icon={FileText}
              color="amber"
            />
          </div>

          {/* Visual income bar */}
          {(totals?.sales || totals?.expenses) && (
            <div className="bg-white rounded-2xl border border-slate-200 p-5">
              <h3 className="text-sm font-bold text-slate-700 mb-4">Sales vs. Expenses</h3>
              <div className="space-y-3">
                {[
                  { label: "Sales",    value: totals.sales,    max: Math.max(totals.sales, totals.expenses, 1), color: "bg-green-500" },
                  { label: "Expenses", value: totals.expenses,  max: Math.max(totals.sales, totals.expenses, 1), color: "bg-red-400"   },
                ].map(({ label, value, max, color }) => {
                  const pct = Math.round((value / max) * 100);
                  return (
                    <div key={label} className="flex items-center gap-3">
                      <span className="text-xs text-slate-500 w-16 shrink-0">{label}</span>
                      <div className="flex-1 h-3 bg-slate-100 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full ${color} transition-all duration-500`}
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                      <span className="text-sm font-bold text-slate-700 w-24 text-right shrink-0">
                        {formatINR(value)}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* 2-column: confidence + client info */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <ConfidenceBreakdown breakdown={confidence_breakdown} totals={totals} />

            {/* Client metadata */}
            <div className="bg-white rounded-2xl border border-slate-200 p-5">
              <div className="flex items-center gap-2 mb-4">
                <FileText size={16} className="text-blue-600" />
                <h3 className="text-sm font-bold text-slate-700">Filing Period</h3>
              </div>
              <div className="space-y-3 text-sm">
                <div className="flex justify-between">
                  <span className="text-slate-500">Period</span>
                  <span className="font-semibold text-slate-700">{format(month, "MMMM yyyy")}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">Total Transactions</span>
                  <span className="font-semibold text-slate-700">{confidence_breakdown?.total ?? 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-500">With Evidence</span>
                  <span className="font-semibold text-slate-700">{confidence_breakdown?.with_evidence ?? 0}</span>
                </div>
                {client?.gstin && (
                  <div className="flex justify-between">
                    <span className="text-slate-500">GSTIN</span>
                    <span className="font-mono text-xs font-semibold text-slate-700 bg-slate-100 px-2 py-0.5 rounded">
                      {client.gstin}
                    </span>
                  </div>
                )}
                {totals?.net >= 0 ? (
                  <div className="mt-3 pt-3 border-t border-slate-100 flex justify-between">
                    <span className="text-slate-500 font-medium">Net Position</span>
                    <span className={`font-bold ${totals.net >= 0 ? "text-green-700" : "text-red-600"}`}>
                      {totals.net >= 0 ? "+" : ""}{formatINR(totals.net)}
                    </span>
                  </div>
                ) : null}
              </div>
            </div>
          </div>

          {/* Low confidence transactions — shown first, highlighted */}
          {low_confidence_transactions?.length > 0 && (
            <TransactionTable
              transactions={low_confidence_transactions}
              title="⚠ Low Confidence — Needs Review"
              showWarning
            />
          )}

          {/* All transactions */}
          <TransactionTable
            transactions={transactions}
            title="All Transactions"
            showWarning={false}
          />

          {/* Export CTA */}
          <div className="bg-blue-50 border border-blue-200 rounded-2xl p-5 flex items-center justify-between gap-4">
            <div>
              <p className="text-sm font-bold text-blue-800">Ready to file?</p>
              <p className="text-xs text-blue-600 mt-0.5">
                Download the Excel report with all transactions and confidence breakdown.
              </p>
            </div>
            <button
              onClick={handleExport}
              disabled={downloading}
              className="shrink-0 flex items-center gap-2 px-4 py-2.5 bg-blue-700 hover:bg-blue-800 text-white text-sm font-semibold rounded-xl transition-colors whitespace-nowrap"
            >
              <Download size={15} />
              {downloading ? "Exporting…" : "Download Excel"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
