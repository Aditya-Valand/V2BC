"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Download, ChevronLeft, ChevronRight, AlertTriangle, RefreshCw } from "lucide-react";
import { format } from "date-fns";
import { transactionsApi } from "@/lib/api/transactions";
import { formatINR } from "@/lib/utils";
import useAuthStore from "@/store/authStore";
import { useLang } from "@/lib/i18n";

// ── Month row ─────────────────────────────────────────────────────────

function MonthRow({ row, isCurrentMonth }) {
  const hasData = row.transaction_count > 0;
  return (
    <tr className={`border-b border-slate-100 print:border-slate-300 ${isCurrentMonth ? "bg-blue-50 print:bg-transparent font-semibold" : ""}`}>
      <td className="py-2.5 px-3 text-sm text-slate-700 print:text-black">{row.month_label}</td>
      <td className="py-2.5 px-3 text-sm text-right font-medium text-green-700 print:text-black">
        {hasData ? formatINR(row.sales) : "—"}
      </td>
      <td className="py-2.5 px-3 text-sm text-right font-medium text-red-600 print:text-black">
        {hasData ? formatINR(row.expenses) : "—"}
      </td>
      <td className={`py-2.5 px-3 text-sm text-right font-bold print:text-black ${row.net >= 0 ? "text-green-700" : "text-red-600"}`}>
        {hasData ? formatINR(row.net) : "—"}
      </td>
      <td className="py-2.5 px-3 text-sm text-right text-slate-500 print:text-black">
        {hasData ? row.transaction_count : "—"}
      </td>
    </tr>
  );
}

// ── Yearly bar chart (CSS only) ───────────────────────────────────────

function YearlyChart({ months }) {
  if (!months?.length) return null;
  const maxVal = Math.max(...months.flatMap((m) => [m.sales, m.expenses]), 1);

  return (
    <div className="print:hidden bg-white rounded-2xl border border-slate-200 p-4">
      <p className="text-sm font-bold text-slate-700 mb-3">Sales vs Expenses</p>
      <div className="flex items-end gap-1 h-24">
        {months.map((m) => {
          const salePct    = (m.sales    / maxVal) * 100;
          const expPct     = (m.expenses / maxVal) * 100;
          return (
            <div key={m.month} className="flex-1 flex flex-col items-center gap-px h-full justify-end">
              <div className="w-full flex gap-px justify-center">
                {m.sales > 0 && (
                  <div
                    className="flex-1 bg-green-400 rounded-t-sm min-h-[2px]"
                    style={{ height: `${Math.max(salePct * 0.9, 2)}px` }}
                  />
                )}
                {m.expenses > 0 && (
                  <div
                    className="flex-1 bg-red-300 rounded-t-sm min-h-[2px]"
                    style={{ height: `${Math.max(expPct * 0.9, 2)}px` }}
                  />
                )}
                {!m.sales && !m.expenses && (
                  <div className="flex-1 bg-slate-100 rounded-t-sm" style={{ height: "2px" }} />
                )}
              </div>
              <span className="text-[8px] text-slate-400">{m.month_short}</span>
            </div>
          );
        })}
      </div>
      <div className="flex items-center gap-4 mt-2 justify-center">
        <span className="flex items-center gap-1 text-[11px] text-slate-500">
          <span className="w-2.5 h-2.5 rounded-sm bg-green-400 inline-block" />Sales
        </span>
        <span className="flex items-center gap-1 text-[11px] text-slate-500">
          <span className="w-2.5 h-2.5 rounded-sm bg-red-300 inline-block" />Expenses
        </span>
      </div>
    </div>
  );
}

// ── Print-only header (hidden on screen) ─────────────────────────────

function PrintHeader({ businessName, caName, year }) {
  return (
    <div className="hidden print:block mb-6 pb-4 border-b-2 border-slate-800">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-2xl font-black text-slate-900">BharatCompliance</p>
          <p className="text-sm text-slate-500">Annual Financial Report</p>
        </div>
        <div className="text-right">
          <p className="text-sm font-bold text-slate-700">{businessName}</p>
          {caName && <p className="text-xs text-slate-500">CA: {caName}</p>}
          <p className="text-xs text-slate-500">FY {year}–{String(year + 1).slice(-2)}</p>
        </div>
      </div>
    </div>
  );
}

// ── Main Page ─────────────────────────────────────────────────────────

export default function AnnualReportPage() {
  const { user } = useAuthStore();
  const { t }    = useLang();
  const currentYear = new Date().getFullYear();
  const [year, setYear] = useState(currentYear);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["annual-summary", year],
    queryFn:  () => transactionsApi.annualSummary(year).then((r) => r.data.data),
    staleTime: 1000 * 60 * 5,
  });

  const handleDownload = () => {
    window.print();
  };

  const currentMonth = new Date().getMonth() + 1; // 1-12

  if (isLoading) {
    return (
      <div className="p-4 space-y-4">
        <div className="h-8 bg-slate-200 animate-pulse rounded w-40" />
        <div className="h-32 bg-slate-200 animate-pulse rounded-2xl" />
        <div className="h-64 bg-slate-200 animate-pulse rounded-2xl" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="p-4 flex flex-col items-center justify-center min-h-[50vh] gap-4">
        <AlertTriangle size={40} className="text-orange-400" />
        <p className="text-sm text-slate-500 text-center">{t("common.error")}</p>
        <button onClick={() => refetch()} className="flex items-center gap-2 text-sm font-semibold text-blue-700">
          <RefreshCw size={14} /> {t("common.retry")}
        </button>
      </div>
    );
  }

  const totals = data?.totals || {};
  const months = data?.months || [];

  const businessName = user?.name || "My Business";
  // Ca name if stored
  const caName = null; // Would need to be fetched from store/business data

  return (
    <>
      {/* ── Print stylesheet injected inline ── */}
      <style>{`
        @media print {
          body * { visibility: hidden; }
          #annual-report-print, #annual-report-print * { visibility: visible; }
          #annual-report-print {
            position: absolute; left: 0; top: 0; width: 100%;
            padding: 24px; font-size: 12px;
          }
          @page { margin: 15mm; }
        }
      `}</style>

      <div id="annual-report-print" className="p-4 pb-8 space-y-4">

        {/* Print-only header */}
        <PrintHeader businessName={businessName} caName={caName} year={year} />

        {/* ── Screen header ── */}
        <div className="print:hidden">
          <p className="text-xs font-medium text-slate-400 uppercase tracking-wide">
            {user?.name?.split(" ")[0]}
          </p>
          <h1 className="text-xl font-bold text-slate-800">{t("report.title")}</h1>
        </div>

        {/* ── Year picker ── */}
        <div className="print:hidden flex items-center justify-between bg-white rounded-2xl border border-slate-200 px-4 py-3">
          <p className="text-sm font-semibold text-slate-600">{t("report.year")}</p>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setYear((y) => Math.max(2020, y - 1))}
              disabled={year <= 2020}
              className="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center text-slate-600 disabled:opacity-30 active:scale-95 transition-all"
            >
              <ChevronLeft size={16} />
            </button>
            <span className="text-sm font-bold text-slate-800 w-12 text-center">{year}</span>
            <button
              onClick={() => setYear((y) => Math.min(currentYear, y + 1))}
              disabled={year >= currentYear}
              className="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center text-slate-600 disabled:opacity-30 active:scale-95 transition-all"
            >
              <ChevronRight size={16} />
            </button>
          </div>
        </div>

        {/* ── Summary hero cards ── */}
        <div className="grid grid-cols-2 gap-3">
          {[
            { label: t("report.sales"),    value: formatINR(totals.sales    || 0), color: "text-green-700",  bg: "bg-green-50",  border: "border-green-100"  },
            { label: t("report.expenses"), value: formatINR(totals.expenses || 0), color: "text-red-600",    bg: "bg-red-50",    border: "border-red-100"    },
            { label: t("report.net"),      value: formatINR(totals.net      || 0), color: (totals.net || 0) >= 0 ? "text-blue-700" : "text-red-600", bg: "bg-blue-50", border: "border-blue-100" },
            { label: t("report.entries"),  value: totals.transaction_count  || 0,  color: "text-slate-700",  bg: "bg-slate-50",  border: "border-slate-100"  },
          ].map(({ label, value, color, bg, border }) => (
            <div key={label} className={`${bg} ${border} border rounded-2xl p-3.5 print:border-slate-300`}>
              <p className="text-[11px] font-medium text-slate-500 print:text-slate-600">{label}</p>
              <p className={`text-lg font-black mt-0.5 ${color} print:text-black`}>{value}</p>
            </div>
          ))}
        </div>

        {/* ── Year bar chart (screen only) ── */}
        {months.length > 0 && <YearlyChart months={months} />}

        {/* ── Monthly breakdown table ── */}
        <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden print:border-slate-400">
          {/* Table header */}
          <div className="px-4 py-3 border-b border-slate-100 print:border-slate-300 bg-slate-50 print:bg-transparent">
            <p className="text-sm font-bold text-slate-700 print:text-black">
              FY {year} — Month by Month
            </p>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full min-w-[400px]">
              <thead>
                <tr className="text-[11px] font-bold text-slate-400 uppercase tracking-wide border-b border-slate-100 print:border-slate-300 print:text-slate-700">
                  <th className="py-2.5 px-3 text-left">{t("report.month")}</th>
                  <th className="py-2.5 px-3 text-right">{t("report.sales")}</th>
                  <th className="py-2.5 px-3 text-right">{t("report.expenses")}</th>
                  <th className="py-2.5 px-3 text-right">{t("report.net")}</th>
                  <th className="py-2.5 px-3 text-right">{t("report.entries")}</th>
                </tr>
              </thead>
              <tbody>
                {months.map((row) => (
                  <MonthRow
                    key={row.month}
                    row={row}
                    isCurrentMonth={year === currentYear && row.month === currentMonth}
                  />
                ))}
              </tbody>
              {/* Totals row */}
              <tfoot>
                <tr className="bg-slate-800 print:bg-transparent print:border-t-2 print:border-slate-800 text-white print:text-black">
                  <td className="py-3 px-3 text-sm font-black">{t("report.total")}</td>
                  <td className="py-3 px-3 text-sm text-right font-black">{formatINR(totals.sales || 0)}</td>
                  <td className="py-3 px-3 text-sm text-right font-black">{formatINR(totals.expenses || 0)}</td>
                  <td className="py-3 px-3 text-sm text-right font-black">{formatINR(totals.net || 0)}</td>
                  <td className="py-3 px-3 text-sm text-right font-black">{totals.transaction_count || 0}</td>
                </tr>
              </tfoot>
            </table>
          </div>
        </div>

        {/* ── Print footer (screen hidden) ── */}
        <div className="hidden print:block mt-6 pt-4 border-t border-slate-300 text-center">
          <p className="text-xs text-slate-500">
            {t("report.generated")} {format(new Date(), "d MMMM yyyy")} &nbsp;|&nbsp; {t("report.powered_by")}
          </p>
        </div>

        {/* ── Download button ── */}
        <button
          onClick={handleDownload}
          className="print:hidden w-full flex items-center justify-center gap-2.5 bg-blue-700 hover:bg-blue-800 active:scale-[0.98] text-white font-bold text-sm py-3.5 rounded-2xl transition-all shadow-md"
        >
          <Download size={18} />
          {t("report.download")}
        </button>

        {/* Hint */}
        <p className="print:hidden text-center text-[11px] text-slate-400">
          Opens your browser's print dialog — choose "Save as PDF"
        </p>

      </div>
    </>
  );
}
